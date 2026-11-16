"""gh_guard_lib — decides whether a Bash command may run, for gh_guard.py (#361).

run() takes the hook's arguments and its standard input, and returns (code, stdout, stderr):
(0, "", "") passes, (0, <one systemMessage object>, "") passes with a warning, and (2, "",
<reason>) blocks. It never exits and never prints; gh_guard.py turns anything else into a block.
It must run on Python 3.9: no syntax or library newer than that.
"""

import json
import os
import re
import sys

# The installer and the registration check compare this line; raise it with every change.
GH_GUARD_VERSION = 1

HEAD = "gate-sdd gh guard: blocked. "

PASS = (0, "", "")


def block(reason, advice=None):
    """A block, worded for the session that ran the command. reason ends with a full stop."""
    text = HEAD + reason + "\n"
    if advice:
        text += "  " + advice + "\n"
    return (2, "", text)


# For a gh word given to something that can run code (python3, a pipe, xargs, a file it writes):
# the hook cannot tell text about gh from a call of it, and it does not read a script run by name.
ADVICE_CODE = ("If it does not run gh, write the script to a file with the Write tool and run that"
               " file by its path, which the hook does not read; if it does, run gh as a plain"
               " command instead.")
ADVICE_UNEXPLAINED = ("Run gh as a plain command: `gh <subcommand> ...`, by its name or a path that"
                      " ends in /gh, not through a variable, a substitution or a wrapper the hook"
                      " does not list.")


# The fast path: a command passes unread unless `gh` stands as a word once quotes and backslashes
# are taken out: no letter, digit or `_` before it, and none of those, `.` or `-` after it. A gh
# that runs is never followed by `-` or `.`, and `${:-gh}` has a `-` before it. No file is read
# and no pattern is loaded before this (#361 AC4).
_GH_WORD = re.compile(r"(?<![A-Za-z0-9_])gh(?![A-Za-z0-9_.-])")


def mentions_gh(command):
    return _GH_WORD.search(re.sub(r"[\"'\\]", "", command)) is not None


# ---------------------------------------------------------------------------------------------
# The lexer. It reads a command as Claude Code's Bash tool runs it: `zsh -c`, zsh 5.9, with
# NO_EXTENDED_GLOB NO_BARE_GLOB_QUAL NO_BRACE_CCL NO_MAGIC_EQUAL_SUBST set and the command given
# to `eval` (measured, #361). What it does not handle it reports as unsupported: the rest of the
# command, from the start of the list item holding it, is then opaque text.

class Unsupported(Exception):
    def __init__(self, reason):
        Exception.__init__(self, reason)
        self.reason = reason


class Part(object):
    """One piece of a word. kind is "lit" (text as the command receives it), "param" ($NAME or
    ${NAME}: text is the name), "home" (a leading ~), "equals" (a leading =name: text is the
    name), "cmdsub" ($(...) or `...`: script is its parse), "procsub" (<(...), >(...), =(...)),
    or "opaque" (any other expansion). text is the source for the last three."""

    __slots__ = ("kind", "text", "quoted", "script")

    def __init__(self, kind, text, quoted=False, script=None):
        self.kind = kind
        self.text = text
        self.quoted = quoted
        self.script = script


class Word(object):
    """A word, its parts, and skel: its unquoted literal characters, with every other character
    as NUL, which is what decides whether zsh globs it or expands a brace in it."""

    __slots__ = ("parts", "skel", "raw")

    def __init__(self, parts, skel, raw):
        self.parts = parts
        self.skel = skel
        self.raw = raw

    def pattern(self):
        """True when zsh would glob the word or expand a brace in it."""
        s = self.skel
        if "*" in s or "?" in s:
            return True
        k = s.find("[")
        if k >= 0 and s.find("]", k + 1) > 0:
            return True
        return _has_brace(s)

    def literal(self, env=None, pattern_ok=False):
        """The word's value, or None when any part of it cannot be known before it runs."""
        out = []
        for p in self.parts:
            if p.kind == "lit":
                out.append(p.text)
            elif p.kind == "home" and env is not None and "HOME" in env:
                out.append(env["HOME"])
            elif p.kind == "param" and env is not None and p.text in env:
                out.append(env[p.text])
            else:
                return None
        if not pattern_ok and self.pattern():
            return None
        return "".join(out)

    def plain(self):
        """The word as a reader sees it with its quotes taken out: its literal text and the
        source of every expansion. A gh word is looked for in this."""
        out = []
        for p in self.parts:
            out.append(p.text if p.kind == "lit" else _source(p))
        return "".join(out)


def _source(p):
    if p.kind == "param":
        return "$" + p.text
    if p.kind == "home":
        return "~"
    if p.kind == "equals":
        return "=" + p.text
    return p.text


def _has_brace(s):
    # {a,b} and {a..b} expand; {}, {x} and an unbalanced brace do not.
    depth = 0
    opened = []
    for k, c in enumerate(s):
        if c == "{":
            opened.append(k)
        elif c == "}" and opened:
            body = s[opened.pop() + 1:k]
            if "," in body or ".." in body:
                return True
    return False


class Heredoc(object):
    __slots__ = ("delim", "quoted", "strip", "body", "word")

    def __init__(self, delim, quoted, strip):
        self.delim = delim
        self.quoted = quoted
        self.strip = strip
        self.body = None   # the raw lines, each ending in a newline
        self.word = None   # for an unquoted delimiter, the body as a Word with its expansions


class Redir(object):
    __slots__ = ("fd", "op", "target", "heredoc")

    def __init__(self, fd, op, target, heredoc=None):
        self.fd = fd
        self.op = op
        self.target = target
        self.heredoc = heredoc


class Simple(object):
    __slots__ = ("assigns", "words", "redirs")

    def __init__(self, assigns, words, redirs):
        self.assigns = assigns   # (name, Word, appends)
        self.words = words
        self.redirs = redirs


class Group(object):
    __slots__ = ("kind", "body", "redirs")

    def __init__(self, kind, body, redirs):
        self.kind = kind         # "subshell" for (...), "group" for { ...; }
        self.body = body
        self.redirs = redirs


class Compound(object):
    """if, while, until, for, and a function's definition. parts is a list of (condition,
    body), each a Script; a condition is None where there is none (for, else, a function).
    var is for's variable or the function's name, and words for's list, None for `for x;`."""

    __slots__ = ("kind", "parts", "var", "words", "redirs")

    def __init__(self, kind, parts, var=None, words=None, redirs=None):
        self.kind = kind
        self.parts = parts
        self.var = var
        self.words = words
        self.redirs = redirs or []


def _script_of(command):
    return Script([(AndOr([Pipeline([command], False)], []), "")])


class Pipeline(object):
    __slots__ = ("commands", "bang")

    def __init__(self, commands, bang):
        self.commands = commands
        self.bang = bang


class AndOr(object):
    __slots__ = ("pipelines", "ops")

    def __init__(self, pipelines, ops):
        self.pipelines = pipelines
        self.ops = ops


class Script(object):
    """items: (AndOr, separator). unsupported: (the opaque rest, why), or None."""

    __slots__ = ("items", "unsupported")

    def __init__(self, items, unsupported=None):
        self.items = items
        self.unsupported = unsupported


_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_ASSIGN = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)(\+?)=")
_REDIR = re.compile(r"(\d*)(&>>|&>|>>\||>>!|>>|>\||>!|>&|<&|<>|<<<|<<-|<<|>|<)")
_ENDS_WORD = " \t\n;&|()<>"
_RESERVED = {"if", "then", "else", "elif", "fi", "for", "while", "until", "do", "done", "case",
             "esac", "select", "repeat", "function", "coproc", "foreach", "end", "[[", "]]", "}"}
_MODIFIERS = "aAcehlpPqQrstuxX&gs"
_ESCAPES = {"a": "\a", "b": "\b", "e": "\x1b", "E": "\x1b", "f": "\f", "n": "\n", "r": "\r",
            "t": "\t", "v": "\v", "\\": "\\", "'": "'", '"': '"', "?": "?"}


class Parser(object):
    def __init__(self, s):
        self.s = s
        self.i = 0
        self.pending = []

    def peek(self, k=0):
        j = self.i + k
        return self.s[j] if j < len(self.s) else ""

    def at(self, text):
        return self.s.startswith(text, self.i)

    # -- blanks, newlines, here-documents ----------------------------------------------------

    def blanks(self):
        while True:
            c = self.peek()
            if c in (" ", "\t"):
                self.i += 1
            elif self.at("\\\n"):
                self.i += 2
            elif c == "#":
                j = self.s.find("\n", self.i)
                self.i = len(self.s) if j < 0 else j
            else:
                return

    def newline(self):
        self.i += 1
        pending, self.pending = self.pending, []
        for h in pending:
            self.read_heredoc(h)

    def blank_lines(self):
        while True:
            self.blanks()
            if self.peek() == "\n":
                self.newline()
            else:
                return

    def read_heredoc(self, h):
        lines = []
        while True:
            if self.i >= len(self.s):
                raise Unsupported("a here-document has no end line")
            j = self.s.find("\n", self.i)
            line = self.s[self.i:] if j < 0 else self.s[self.i:j]
            self.i = len(self.s) if j < 0 else j + 1
            if h.strip:
                line = line.lstrip("\t")
            if line == h.delim:
                break
            lines.append(line)
        h.body = "".join(line + "\n" for line in lines)
        if not h.quoted:
            p = Parser(h.body)
            h.word = p.quoted_text(heredoc=True)

    # -- words ---------------------------------------------------------------------------------

    def word(self, assignment=False):
        """Reads one word, or returns None at an operator, a newline or the end."""
        start = self.i
        parts = []
        skel = []
        s = self.s
        while self.i < len(s):
            c = s[self.i]
            if c in "<>=" and not parts and self.peek(1) == "(":
                self.i += 2
                body = self.parse_list(")")
                self.expect(")")
                parts.append(Part("procsub", s[start:self.i], script=body))
                skel.append("\0")
                continue
            if c in _ENDS_WORD:
                break
            if c == "'":
                j = s.find("'", self.i + 1)
                if j < 0:
                    raise Unsupported("a quote is not closed")
                self.lit(parts, s[self.i + 1:j], True)
                skel.append("\0" * (j - self.i + 1))
                self.i = j + 1
            elif c == '"':
                self.i += 1
                w = self.quoted_text()
                parts.extend(w.parts)
                skel.append("\0")
            elif c == "\\":
                nx = self.peek(1)
                if nx == "\n":
                    self.i += 2
                elif nx == "":
                    raise Unsupported("the command ends in a backslash")
                else:
                    self.lit(parts, nx, True)
                    skel.append("\0")
                    self.i += 2
            elif c == "$":
                if self.peek(1) == "'":
                    self.ansi(parts)
                elif self.peek(1) == '"':
                    self.lit(parts, "$", False)
                    skel.append("$")
                    self.i += 1
                else:
                    self.dollar(parts, False)
                skel.append("\0")
            elif c == "`":
                self.backtick(parts, False)
                skel.append("\0")
            elif c == "~" and self.tilde_here(parts, assignment):
                j = self.i + 1
                while j < len(s) and s[j] not in _ENDS_WORD and s[j] not in "/:\"'\\$`":
                    j += 1
                if j == self.i + 1:
                    parts.append(Part("home", "~"))
                else:
                    parts.append(Part("opaque", s[self.i:j]))
                skel.append("\0")
                self.i = j
            elif c == "=" and not parts and _NAME.match(s, self.i + 1):
                m = re.compile(r"[^\s;&|()<>'\"\\$`]+").match(s, self.i + 1)
                parts.append(Part("equals", m.group(0)))
                skel.append("\0")
                self.i = m.end()
            else:
                self.lit(parts, c, False)
                skel.append(c)
                self.i += 1
        if self.i == start:
            return None
        return Word(parts, "".join(skel), s[start:self.i])

    def tilde_here(self, parts, assignment):
        # A ~ expands at the start of a word, and after the = of an assignment (measured).
        if not parts:
            return True
        if assignment and len(parts) == 1 and parts[0].kind == "lit" and not parts[0].quoted:
            return _ASSIGN.fullmatch(parts[0].text) is not None
        return False

    def lit(self, parts, text, quoted):
        if parts and parts[-1].kind == "lit" and parts[-1].quoted == quoted:
            parts[-1].text += text
        else:
            parts.append(Part("lit", text, quoted))

    def quoted_text(self, heredoc=False):
        """A double-quoted string from just after its quote, or a here-document's body."""
        parts = []
        s = self.s
        start = self.i
        specials = '$`\\\n' if heredoc else '$`"\\\n'
        while True:
            if self.i >= len(s):
                if heredoc:
                    break
                raise Unsupported("a quote is not closed")
            c = s[self.i]
            if c == '"' and not heredoc:
                self.i += 1
                break
            if c == "\\":
                nx = self.peek(1)
                if nx == "\n":
                    self.i += 2
                elif nx != "" and nx in specials:
                    self.lit(parts, nx, True)
                    self.i += 2
                else:
                    self.lit(parts, "\\", True)
                    self.i += 1
            elif c == "$":
                self.dollar(parts, True)
            elif c == "`":
                self.backtick(parts, True)
            else:
                self.lit(parts, c, True)
                self.i += 1
        if not parts:
            parts.append(Part("lit", "", True))
        for p in parts:
            p.quoted = True
        return Word(parts, "\0", s[start:self.i])

    def balanced(self, open_, close):
        """The source from self.i through the close that balances the open at self.i."""
        s = self.s
        depth = 0
        j = self.i
        while j < len(s):
            c = s[j]
            if c == "\\":
                j += 2
                continue
            if c == "'":
                k = s.find("'", j + 1)
                if k < 0:
                    break
                j = k + 1
                continue
            if c == open_:
                depth += 1
            elif c == close:
                depth -= 1
                if depth == 0:
                    raw = s[self.i:j + 1]
                    self.i = j + 1
                    return raw
            j += 1
        raise Unsupported("an expansion is not closed")

    def dollar(self, parts, quoted):
        s = self.s
        nx = self.peek(1)
        if nx == "(":
            if self.peek(2) == "(":
                self.i += 1
                raw = "$" + self.balanced("(", ")")
                parts.append(Part("opaque", raw, quoted))
                return
            start = self.i
            self.i += 2
            body = self.parse_list(")")
            self.expect(")")
            parts.append(Part("cmdsub", s[start:self.i], quoted, body))
        elif nx == "{":
            self.i += 1
            raw = "$" + self.balanced("{", "}")
            inner = raw[2:-1]
            if _NAME.fullmatch(inner):
                parts.append(Part("param", inner, quoted))
            else:
                parts.append(Part("opaque", raw, quoted))
        elif nx == "[":
            self.i += 1
            parts.append(Part("opaque", "$" + self.balanced("[", "]"), quoted))
        elif nx != "" and _NAME.match(nx):
            m = _NAME.match(s, self.i + 1)
            self.i = m.end()
            name = m.group(0)
            # zsh subscripts $NAME[...] and modifies $NAME:h (measured).
            if self.peek() == "[":
                raw = "$" + name + self.balanced("[", "]")
                parts.append(Part("opaque", raw, quoted))
            elif self.peek() == ":" and self.peek(1) != "" and self.peek(1) in _MODIFIERS:
                self.i += 2
                parts.append(Part("opaque", "$" + name + s[self.i - 2:self.i], quoted))
            else:
                parts.append(Part("param", name, quoted))
        elif nx != "" and nx in "0123456789#?$!@*-":
            self.i += 2
            parts.append(Part("opaque", "$" + nx, quoted))
        else:
            self.lit(parts, "$", quoted)
            self.i += 1

    def ansi(self, parts):
        s = self.s
        start = self.i
        self.i += 2
        out = []
        known = True
        while True:
            if self.i >= len(s):
                raise Unsupported("a quote is not closed")
            c = s[self.i]
            if c == "'":
                self.i += 1
                break
            if c != "\\":
                out.append(c)
                self.i += 1
                continue
            nx = self.peek(1)
            if nx in _ESCAPES:
                out.append(_ESCAPES[nx])
                self.i += 2
                continue
            m = re.compile(r"x([0-9A-Fa-f]{1,2})|u([0-9A-Fa-f]{1,4})|U([0-9A-Fa-f]{1,8})|([0-7]{1,3})")\
                .match(s, self.i + 1)
            if m and nx != "":
                code = int(next(g for g in m.groups() if g is not None),
                           8 if m.group(4) is not None else 16)
                try:
                    out.append(chr(code))
                except (ValueError, OverflowError):
                    known = False
                self.i = m.end()
                continue
            # \c, \M-, \C- and the rest: not decoded here.
            known = False
            self.i += 2 if nx != "" else 1
        if known:
            self.lit(parts, "".join(out), True)
        else:
            parts.append(Part("opaque", s[start:self.i], True))

    def backtick(self, parts, quoted):
        s = self.s
        start = self.i
        j = self.i + 1
        inner = []
        while j < len(s):
            c = s[j]
            if c == "\\" and j + 1 < len(s) and s[j + 1] in ("`$\\" + ('"' if quoted else "")):
                inner.append(s[j + 1])
                j += 2
            elif c == "`":
                break
            else:
                inner.append(c)
                j += 1
        if j >= len(s):
            raise Unsupported("a backtick is not closed")
        self.i = j + 1
        body = Parser("".join(inner)).parse_top(nested=True)
        parts.append(Part("cmdsub", s[start:self.i], quoted, body))

    def expect(self, c):
        if self.peek() != c:
            raise Unsupported("a " + c + " is missing")
        self.i += 1

    # -- commands ------------------------------------------------------------------------------

    def redirection(self):
        m = _REDIR.match(self.s, self.i)
        if not m:
            return None
        op = m.group(2)
        if op in ("<", ">") and self.s.startswith("(", m.end()):
            return None
        self.i = m.end()
        fd = m.group(1)
        self.blanks()
        if op in ("<<", "<<-"):
            w = self.word()
            if w is None:
                raise Unsupported("a here-document has no delimiter")
            delim = w.literal(pattern_ok=True)
            if delim is None:
                raise Unsupported("a here-document's delimiter is not literal")
            quoted = any(p.quoted for p in w.parts)
            h = Heredoc(delim, quoted, op == "<<-")
            self.pending.append(h)
            return Redir(fd, op, None, h)
        w = self.word()
        if w is None:
            raise Unsupported("a redirection has no target")
        return Redir(fd, op, w)

    def word_is(self, text):
        # True when the next word is exactly the unquoted text.
        return self.at(text) and (self.i + len(text) >= len(self.s)
                                  or self.s[self.i + len(text)] in _ENDS_WORD)

    def command(self):
        self.blanks()
        if self.peek() == "(":
            if self.peek(1) == "(":
                raise Unsupported("arithmetic `((`")
            self.i += 1
            body = self.parse_list(")")
            self.expect(")")
            return Group("subshell", body, self.redirections())
        if self.word_is("{"):
            self.i += 1
            body = self.parse_list("}")
            self.i += 1
            return Group("group", body, self.redirections())
        for keyword in ("if", "while", "until", "for", "function"):
            if self.word_is(keyword):
                self.i += len(keyword)
                return self.compound(keyword)
        assigns = []
        words = []
        redirs = []
        while True:
            self.blanks()
            r = self.redirection()
            if r is not None:
                redirs.append(r)
                continue
            c = self.peek()
            if c == "(":
                m = re.compile(r"\(\s*\)").match(self.s, self.i)
                if m and len(words) == 1 and not assigns and not redirs \
                        and words[0].literal(pattern_ok=True) is not None:
                    self.i = m.end()
                    return self.function(words[0].literal(pattern_ok=True))
                raise Unsupported("an array" if words or assigns else "a `(` inside a command")
            w = self.word(assignment=not words)
            if w is None:
                break
            if not words:
                first = w.parts[0] if w.parts else None
                m = _ASSIGN.match(first.text) if first is not None and first.kind == "lit" \
                    and not first.quoted else None
                if m:
                    if self.peek() == "(" and len(w.raw) == m.end():
                        raise Unsupported("an array assignment")
                    assigns.append((m.group(1), _after_assign(w, m.end()), m.group(2) == "+"))
                    continue
                if not assigns and w.literal(pattern_ok=True) in _RESERVED \
                        and not any(p.quoted for p in w.parts):
                    raise Unsupported("`" + w.raw + "`")
            words.append(w)
        if not (assigns or words or redirs):
            raise Unsupported("an empty command")
        return Simple(assigns, words, redirs)

    def expect_word(self, word):
        self.blank_lines()
        if not self.word_is(word):
            raise Unsupported("a `" + word + "` is missing")
        self.i += len(word)

    def function(self, name):
        self.blank_lines()
        body = self.command()
        return Compound("function", [(None, _script_of(body))], var=name,
                        redirs=self.redirections())

    def compound(self, kind):
        if kind == "function":
            self.blanks()
            w = self.word()
            name = w.literal(pattern_ok=True) if w is not None else None
            if name is None:
                raise Unsupported("a function whose name is not literal")
            self.blanks()
            m = re.compile(r"\(\s*\)").match(self.s, self.i)
            if m:
                self.i = m.end()
            return self.function(name)
        if kind in ("while", "until"):
            cond = self.parse_list(("do",))
            self.expect_word("do")
            body = self.parse_list(("done",))
            self.expect_word("done")
            return Compound(kind, [(cond, body)], redirs=self.redirections())
        if kind == "if":
            parts = []
            cond = self.parse_list(("then",))
            self.expect_word("then")
            body = self.parse_list(("elif", "else", "fi"))
            parts.append((cond, body))
            while True:
                self.blank_lines()
                if self.word_is("elif"):
                    self.i += 4
                    cond = self.parse_list(("then",))
                    self.expect_word("then")
                    parts.append((cond, self.parse_list(("elif", "else", "fi"))))
                elif self.word_is("else"):
                    self.i += 4
                    parts.append((None, self.parse_list(("fi",))))
                    self.expect_word("fi")
                    break
                else:
                    self.expect_word("fi")
                    break
            return Compound("if", parts, redirs=self.redirections())
        # for NAME [in WORDS] ; do LIST done
        self.blanks()
        m = _NAME.match(self.s, self.i)
        if not m or (m.end() < len(self.s) and self.s[m.end()] not in " \t\n;"):
            raise Unsupported("a `for` this hook does not read")
        var = m.group(0)
        self.i = m.end()
        self.blanks()
        if self.peek() == "(":
            raise Unsupported("a `for` this hook does not read")
        words = None
        if self.word_is("in"):
            self.i += 2
            words = []
            while True:
                self.blanks()
                if self.peek() in (";", "\n", ""):
                    break
                if self.peek() in "&|()<>":
                    raise Unsupported("a `for` this hook does not read")
                w = self.word()
                if w is None:
                    raise Unsupported("a `for` this hook does not read")
                words.append(w)
        if self.peek() == ";":
            self.i += 1
        self.expect_word("do")
        body = self.parse_list(("done",))
        self.expect_word("done")
        return Compound("for", [(None, body)], var=var, words=words, redirs=self.redirections())

    def redirections(self):
        out = []
        while True:
            self.blanks()
            r = self.redirection()
            if r is None:
                return out
            out.append(r)

    def pipeline(self):
        self.blanks()
        bang = False
        if self.peek() == "!" and self.peek(1) in (" ", "\t"):
            bang = True
            self.i += 1
        commands = [self.command()]
        while True:
            self.blanks()
            if self.at("||") or not self.at("|"):
                return Pipeline(commands, bang)
            self.i += 2 if self.at("|&") else 1
            self.blank_lines()
            commands.append(self.command())

    def andor(self):
        pipelines = [self.pipeline()]
        ops = []
        while True:
            self.blanks()
            if self.at("&&") or self.at("||"):
                ops.append(self.s[self.i:self.i + 2])
                self.i += 2
                self.blank_lines()
                pipelines.append(self.pipeline())
            else:
                return AndOr(pipelines, ops)

    def at_end(self, end):
        if self.i >= len(self.s):
            if isinstance(end, tuple):
                raise Unsupported("a `" + end[-1] + "` is missing")
            if end:
                raise Unsupported("a " + end + " is missing")
            return True
        if isinstance(end, tuple):
            return any(self.word_is(w) for w in end)
        if end == ")":
            return self.peek() == ")"
        if end == "}":
            return self.word_is("}")
        return False

    def parse_list(self, end, top=False):
        items = []
        # The item that declared the oldest here-document whose lines are still to come: its
        # lines follow it at the next newline, so when they never come, it is opaque too.
        held = None
        while True:
            try:
                self.blank_lines()
            except Unsupported as why:
                if not top:
                    raise
                return Script(items[:held[0]], (self.s[held[1]:], why.reason))
            if not self.pending:
                held = None
            if self.at_end(end):
                break
            start = self.i
            try:
                node = self.andor()
                self.blanks()
                if self.at(";;") or self.at(";&") or self.at(";|"):
                    raise Unsupported("a case pattern's end")
                if self.at("&|") or self.at("&!"):
                    sep = "&"
                    self.i += 2
                elif self.peek() in (";", "&"):
                    sep = self.peek()
                    self.i += 1
                elif self.peek() == "\n" or self.at_end(end):
                    sep = ""
                else:
                    raise Unsupported("an unexpected " + repr(self.peek()))
            except Unsupported as why:
                if not top:
                    raise
                if held is not None:
                    return Script(items[:held[0]], (self.s[held[1]:], why.reason))
                return Script(items, (self.s[start:], why.reason))
            if self.pending and held is None:
                held = (len(items), start)
            items.append((node, sep))
        if self.pending:
            if not top:
                raise Unsupported("a here-document has no end line")
            return Script(items[:held[0]], (self.s[held[1]:], "a here-document has no end line"))
        return Script(items)

    def parse_top(self, nested=False):
        return self.parse_list("", top=not nested)


def _after_assign(w, k):
    """The value of an assignment word, whose first part's first k characters are NAME=."""
    first = w.parts[0]
    rest = [Part("lit", first.text[k:], False)] if first.text[k:] else []
    parts = rest + w.parts[1:]
    if not parts:
        parts = [Part("lit", "", True)]
    # No glob and no brace expansion in a scalar assignment: the skeleton is all NUL.
    return Word(parts, "\0", w.raw[k:])


def parse(command):
    """The command's parse. A construct the lexer does not handle ends it, as `unsupported`."""
    return Parser(command).parse_top()


# ---------------------------------------------------------------------------------------------
# The finder. Every gh word in a command must be accounted for, or the command blocks: it is the
# command word of a gh invocation, an argument of a command that never runs its arguments, a
# value a gh invocation sends, or text written into a file that nothing in the command then runs
# (#361). It walks the parse in the order zsh runs it, tracking what a later word depends on.

class Text(object):
    """What a file or a stream holds: content, when it is known before the command runs, and
    whether its source holds a gh word."""

    __slots__ = ("content", "gh", "label")

    def __init__(self, content, gh, label):
        self.content = content
        self.gh = gh
        self.label = label


class State(object):
    """What the walk knows at a point in the command. vars maps a name to its value, None when
    it cannot be known; tainted holds the names whose unknown value was built from a gh word;
    cwds the directories the command may be in, None for one it cannot know; files what the
    command has written so far, by absolute path; named the paths it changed some other way;
    events what it did that changes where a later gh write goes."""

    __slots__ = ("vars", "exported", "tainted", "cwds", "files", "named", "events", "deferred")

    def __init__(self, home, cwd):
        # In a function's body, which runs where and when it is called: no file it reads can be
        # known from where it is defined.
        self.deferred = False
        self.vars = {"HOME": home} if home else {}
        self.exported = set(self.vars)
        self.tainted = set()
        self.cwds = (cwd,)
        self.files = {}
        self.named = {}
        self.events = []

    def copy(self):
        c = State(None, None)
        c.vars = dict(self.vars)
        c.exported = set(self.exported)
        c.tainted = set(self.tainted)
        c.cwds = self.cwds
        c.files = dict(self.files)
        c.named = dict(self.named)
        c.events = list(self.events)
        c.deferred = self.deferred
        return c

    def merge(self, others):
        """Becomes what is known after any one of these states: a value the states disagree on,
        or that one lacks, is unknown."""
        states = [self] + list(others)
        names = set()
        for s in states:
            names |= set(s.vars)
        merged = {}
        for n in names:
            values = [s.vars[n] if n in s.vars else None for s in states]
            merged[n] = values[0] if all(v == values[0] for v in values) else None
        self.vars = merged
        for s in others:
            self.exported |= s.exported
            self.tainted |= s.tainted
            self.named.update(s.named)
            self.events += [e for e in s.events if e not in self.events]
            self.deferred = self.deferred or s.deferred
        cwds = []
        for s in states:
            cwds += [c for c in s.cwds if c not in cwds]
        self.cwds = tuple(sorted(cwds, key=str))
        paths = set()
        for s in states:
            paths |= set(s.files)
        files = {}
        for path in paths:
            texts = [s.files.get(path) for s in states]
            first = texts[0]
            if all(x is not None and first is not None and x.content == first.content
                   for x in texts):
                files[path] = first
            else:
                files[path] = Text(None, any(x is not None and x.gh for x in texts),
                                   "a file this command may write")
        self.files = files

    def env(self):
        return dict((k, v) for k, v in self.vars.items() if v is not None)

    def path(self, value):
        """The absolute path a value names, or None when the directory is not known."""
        if value is None:
            return None
        if value.startswith("/"):
            return _norm(value)
        if len(self.cwds) != 1 or self.cwds[0] is None:
            return None
        return _norm(self.cwds[0] + "/" + value)


def _norm(path):
    out = []
    for bit in path.split("/"):
        if bit in ("", "."):
            continue
        if bit == "..":
            if out:
                out.pop()
            continue
        out.append(bit)
    return "/" + "/".join(out)


class Invocation(object):
    """A gh command the walk found. words are its words after gh; assigns the assignments and
    env options before it; state the walk's state where it runs; stdin what its standard input
    is, a Redir, "pipe" or None; where a label for the reason that names it."""

    __slots__ = ("words", "assigns", "env", "redirs", "state", "piped", "simple", "binary",
                 "assigns_named")

    def __init__(self, words, assigns, env, redirs, state, piped, simple, binary):
        self.binary = binary
        self.words = words
        self.assigns = assigns
        self.env = env
        self.redirs = redirs
        self.state = state
        self.piped = piped
        self.simple = simple


class Unknown(Exception):
    pass


# Commands that never run their arguments, by the name they run as. git and rg are decided
# by their own arguments.
QUIET = {"echo", "printf", "print", "which", "type", "whence", "where", "man", "grep", "egrep",
         "fgrep", "cat", "ls", "cd", "pwd", "test", "[", "head", "tail", "wc", "mkdir", "touch",
         "rm", "cp", "mv", "diff", "sort", "uniq", "cut", "basename", "dirname", "realpath",
         "readlink", "stat", "file", "tee", "true", "false", ":", "chmod"}
# Commands that read the files they name and change none of them.
READERS = {"cat", "head", "tail", "wc", "grep", "egrep", "fgrep", "rg", "ls", "test", "[", "stat",
           "file", "diff", "cd", "pwd", "echo", "printf", "print", "which", "type", "whence",
           "where", "man", "realpath", "readlink", "basename", "dirname", "true", "false", ":",
           "sort", "uniq", "cut"}
STDIN_OPS = ("<", "<<", "<<-", "<<<", "<>")
DECLARE = {"export", "typeset", "declare", "local", "readonly", "integer", "float"}
SHELLS = {"sh", "bash", "zsh", "dash", "ksh"}
# The git subcommands that never run their arguments. `git -c`, `config`, `rebase --exec`,
# `bisect`, `submodule`, `filter-branch`, `difftool` and `mergetool` can, so they are not here.
GIT_QUIET = {"status", "log", "show", "diff", "add", "commit", "push", "pull", "fetch",
             "checkout", "switch", "branch", "tag", "remote", "merge", "reset", "restore", "rm",
             "mv", "stash", "worktree", "clone", "init", "rev-parse", "ls-files", "grep", "blame",
             "cherry-pick", "revert", "describe", "shortlog", "reflog", "notes", "apply", "am",
             "format-patch", "rev-list", "cat-file", "ls-remote", "symbolic-ref", "for-each-ref",
             "merge-base", "name-rev", "check-ignore", "gc", "prune", "clean", "rebase"}


def _name(value):
    return value.rsplit("/", 1)[-1]


def is_gh(value):
    return value is not None and (value == "gh" or value.endswith("/gh"))


def unwrap(vals):
    """The index of the command that runs, after the wrappers that run their arguments as a
    command, with what env did to the environment. Raises Unknown for a wrapper's option this
    does not read. A lookup (`command -v`) runs nothing: its index is None."""
    k = 0
    env = {"assigns": [], "clears": False, "unsets": []}

    def need(j):
        if j >= len(vals) or vals[j] is None:
            raise Unknown("a wrapper's argument cannot be known")
        return vals[j]

    while k < len(vals) and vals[k] is not None:
        name = _name(vals[k])
        if name == "env":
            k += 1
            while k < len(vals):
                a = need(k)
                if a in ("-i", "-", "--ignore-environment"):
                    env["clears"] = True
                    k += 1
                elif a in ("-u", "--unset"):
                    env["unsets"].append(need(k + 1))
                    k += 2
                elif a.startswith("--unset="):
                    env["unsets"].append(a[8:])
                    k += 1
                elif a.startswith("-u"):
                    env["unsets"].append(a[2:])
                    k += 1
                elif a == "--":
                    k += 1
                    break
                elif a.startswith("-"):
                    raise Unknown("env " + a)
                elif _ASSIGN.match(a):
                    m = _ASSIGN.match(a)
                    env["assigns"].append((m.group(1), a[m.end():]))
                    k += 1
                else:
                    break
        elif name == "command":
            k += 1
            while k < len(vals) and need(k).startswith("-") and vals[k] != "-":
                a = vals[k]
                if a == "--":
                    k += 1
                    break
                if set(a[1:]) - set("pvV"):
                    raise Unknown("command " + a)
                if "v" in a or "V" in a:
                    return None, env
                k += 1
        elif name == "exec":
            k += 1
            while k < len(vals) and need(k).startswith("-"):
                a = vals[k]
                if a == "--":
                    k += 1
                    break
                if a == "-a":
                    k += 2
                elif set(a[1:]) <= set("cl"):
                    k += 1
                else:
                    raise Unknown("exec " + a)
        elif name in ("builtin", "noglob", "nocorrect", "nohup", "time"):
            k += 1
            if name == "nohup" and k < len(vals) and vals[k] == "--":
                k += 1
        elif name == "nice":
            k += 1
            while k < len(vals) and need(k).startswith("-"):
                a = vals[k]
                if a == "--":
                    k += 1
                    break
                if a == "-n":
                    k += 2
                elif re.fullmatch(r"-n?-?\d+|--adjustment=-?\d+", a):
                    k += 1
                else:
                    raise Unknown("nice " + a)
        elif name == "caffeinate":
            k += 1
            while k < len(vals) and need(k).startswith("-"):
                a = vals[k]
                if a in ("-t", "-w"):
                    k += 2
                elif re.fullmatch(r"-[dimsu]+", a):
                    k += 1
                else:
                    raise Unknown("caffeinate " + a)
        elif name in ("timeout", "gtimeout"):
            k += 1
            while k < len(vals) and need(k).startswith("-"):
                a = vals[k]
                if a == "--":
                    k += 1
                    break
                if a in ("-s", "-k"):
                    k += 2
                elif a in ("-v", "--verbose", "--preserve-status", "--foreground") \
                        or a.startswith("--signal=") or a.startswith("--kill-after="):
                    k += 1
                else:
                    raise Unknown("timeout " + a)
            need(k)
            k += 1
        else:
            break
    return k, env


def git_subcommand(vals):
    """git's subcommand, after its global options, or None when it cannot be known."""
    k = 0
    while k < len(vals):
        a = vals[k]
        if a is None:
            return None
        if a in ("-C", "--git-dir", "--work-tree", "--namespace", "-c"):
            k += 2
        elif a.startswith("-"):
            k += 1
        else:
            return a
    return ""


# The one `git -c` value that runs gh: its credential helper, which prints a token and sends
# nothing. Any other -c can name a command, so git with one is not quiet.
GH_CREDENTIAL = re.compile(r"credential(\.[^=]*)?\.helper=!gh auth git-credential")


def git_quiet(vals):
    """True when git, given these arguments, runs none of them as a command."""
    k = 0
    while k < len(vals):
        a = vals[k]
        if a is None:
            return False
        if a == "-c":
            v = vals[k + 1] if k + 1 < len(vals) else None
            if v is None or (mentions_gh(v) and not GH_CREDENTIAL.fullmatch(v)) \
                    or re.match(r"(alias\.|core\.(sshCommand|editor|pager|hooksPath|fsmonitor)|"
                                r".*\.(command|helper|cmd|textconv|process|clean|smudge)=)", v, re.I) \
                    and not GH_CREDENTIAL.fullmatch(v):
                return False
            k += 2
        elif a in ("-C", "--git-dir", "--work-tree", "--namespace"):
            k += 2
        elif a in ("--no-pager", "-P", "--bare", "--no-replace-objects", "--literal-pathspecs",
                   "--no-optional-locks") or a.startswith("--git-dir=") \
                or a.startswith("--work-tree=") or a.startswith("--namespace="):
            k += 1
        else:
            break
    if k >= len(vals) or vals[k] not in GIT_QUIET:
        return False
    rest = vals[k + 1:]
    if vals[k] == "rebase" and any(a is None or a in ("-x", "--exec") or a.startswith("--exec=")
                                   or (a.startswith("-x") and len(a) > 2) for a in rest):
        return False
    return True


def printed(base, vals):
    """What echo or printf prints, when it is literal text: zsh's echo reads backslash escapes,
    so one with a backslash is not known; printf's format is, with no % and a few escapes."""
    if base == "echo":
        if vals and vals[0].startswith("-") or any("\\" in v for v in vals):
            return None
        return " ".join(vals) + "\n"
    if len(vals) != 1 or "%" in vals[0]:
        return None
    text = re.sub(r"\\(.)", lambda m: {"n": "\n", "t": "\t", "\\": "\\", '"': '"', "'": "'"}
                  .get(m.group(1), "\0"), vals[0])
    return None if "\0" in text or vals[0].endswith("\\") else text


def on_disk(path):
    """A file's current content as a Text, for a command that appends to it: empty when it does
    not exist, and unknown when it is not a regular file the hook can read."""
    import stat
    try:
        st = os.stat(path)
    except FileNotFoundError:
        return Text("", False, "a file")
    except OSError:
        return Text(None, False, "a file")
    if not stat.S_ISREG(st.st_mode) or st.st_size > MAX_FILE:
        return Text(None, False, "a file")
    try:
        with open(path, "rb") as f:
            data = f.read().decode("utf-8", "surrogateescape")
    except OSError:
        return Text(None, False, "a file")
    return Text(data, mentions_gh(data), "a file")


def own_text(word):
    """A word's text with its substitutions left out: they are walked as commands of their own."""
    return "".join(p.text if p.kind == "lit" else _source(p) for p in word.parts
                   if p.kind not in ("cmdsub", "procsub"))


class Finder(object):
    def __init__(self, home, cwd):
        self.home = home
        self.start = State(home, cwd)
        self.invocations = []
        self.problems = []

    def problem(self, reason):
        if reason not in self.problems:
            self.problems.append(reason)

    # -- words -----------------------------------------------------------------------------

    def value(self, word, state):
        if word is None:
            return None
        if len(word.parts) == 1 and word.parts[0].kind == "equals":
            return "=/" + word.parts[0].text
        return word.literal(state.env())

    def has_gh(self, word, state):
        if self.taints(word):
            return True
        if any(p.kind == "param" and p.text in state.tainted for p in word.parts):
            return True
        v = self.value(word, state)
        return v is not None and mentions_gh(v)

    def substitutions(self, word, state):
        # A substitution runs before the command holding it, in a subshell of its own.
        for p in word.parts:
            if p.kind in ("cmdsub", "procsub"):
                self.walk(p.script, state.copy())

    def heredoc_text(self, r, state):
        """The Text a here-document or a here-string gives its command."""
        if r.heredoc is not None:
            h = r.heredoc
            if h.quoted:
                return Text(h.body, mentions_gh(h.body), "a here-document")
            self.substitutions(h.word, state)
            return Text(h.word.literal(state.env(), pattern_ok=True), self.has_gh(h.word, state),
                        "a here-document")
        self.substitutions(r.target, state)
        v = r.target.literal(state.env(), pattern_ok=True)
        return Text(None if v is None else v + "\n", self.has_gh(r.target, state),
                    "a here-string")

    # -- the walk --------------------------------------------------------------------------

    def walk(self, script, state):
        for node, sep in script.items:
            if sep == "&":
                self.andor(node, state.copy())
            else:
                self.andor(node, state)
        if script.unsupported is not None and mentions_gh(script.unsupported[0]):
            self.problem("The hook does not read " + script.unsupported[1]
                         + ", and the command holds a gh word there or after it.")
        return state

    def andor(self, node, state):
        before = state.cwds
        for k, pipeline in enumerate(node.pipelines):
            self.pipeline(pipeline, state)
        # A cd that may have failed leaves the command in either directory, unless the item
        # ends in `|| exit` or `|| return`, which stops the command when it does.
        if state.cwds != before and not self.stops(node):
            state.cwds = tuple(sorted(set(before) | set(state.cwds), key=str))

    def stops(self, node):
        if not node.ops or node.ops[-1] != "||":
            return False
        last = node.pipelines[-1].commands
        if len(last) != 1 or not isinstance(last[0], Simple) or not last[0].words:
            return False
        return last[0].words[0].literal() in ("exit", "return")

    def pipeline(self, pipeline, state):
        n = len(pipeline.commands)
        marks = len(self.problems), len(self.quiet_gh)
        for k, command in enumerate(pipeline.commands):
            # Every command of a pipeline but the last runs in a subshell.
            here = state if k == n - 1 else state.copy()
            self.command(command, here, piped=k > 0, downstream=k < n - 1)
        # A gh word a quiet command printed is accounted for only if nothing after it in the
        # pipeline can run what it reads.
        if n > 1 and self.quiet_gh[marks[1]:]:
            for command in pipeline.commands[1:]:
                if not self.consumes_quietly(command, state):
                    self.problem("A gh word is printed into a pipe that a command which can run"
                                 " it reads.")
                    break
        del self.quiet_gh[marks[1]:]

    def consumes_quietly(self, command, state):
        if not isinstance(command, Simple):
            return False
        vals = [self.value(w, state) for w in command.words]
        try:
            k, _ = unwrap(vals)
        except Unknown:
            return False
        if k is None or k >= len(vals):
            return True
        name = vals[k]
        return name is not None and (is_gh(name) or self.quiet(name, vals[k + 1:]))

    def quiet(self, name, args):
        base = _name(name)
        if base == "git":
            return git_quiet(args)
        if base == "rg":
            return not any(a is None or a.startswith("--pre") for a in args)
        return base in QUIET

    def command(self, command, state, piped, downstream):
        if isinstance(command, Compound):
            self.redirect_targets(command.redirs, state)
            own = [r for r in command.redirs if r.op in STDIN_OPS]
            self.stdin.append((own, piped))
            try:
                self.compound(command, state)
            finally:
                self.stdin.pop()
            self.writes(Simple([], [], command.redirs), None, state, [])
            return
        if isinstance(command, Group):
            inner = state if command.kind == "group" else state.copy()
            self.redirect_targets(command.redirs, inner)
            # A group's standard input is every command's in it that has none of its own.
            own = [r for r in command.redirs if r.op in STDIN_OPS]
            self.stdin.append((own, piped))
            try:
                self.walk(command.body, inner)
            finally:
                self.stdin.pop()
            return
        self.simple(command, state, piped, downstream)

    def compound(self, c, state):
        if c.kind == "function":
            # Walked where it is defined, as if it ran there with nothing about the call known.
            body = state.copy()
            body.vars = dict((n, None) for n in state.vars)
            if self.home:
                body.vars["HOME"] = self.home
            body.cwds = (None,)
            body.deferred = True
            self.walk(c.parts[0][1], body)
            return
        if c.kind == "if":
            outcomes = []
            here = state.copy()
            for cond, body in c.parts:
                if cond is not None:
                    self.walk(cond, here)
                branch = here.copy()
                self.walk(body, branch)
                outcomes.append(branch)
                if cond is None:
                    break
            else:
                outcomes.append(here)
            first = outcomes[0]
            first.merge(outcomes[1:])
            self.adopt(state, first)
            return
        # while, until and for: the body may run no time, once, or again with what a run before
        # it changed, so it is walked twice, the second time from what either may leave.
        loop = state.copy()
        if c.kind == "for":
            for w in c.words or []:
                self.substitutions(w, loop)
            values = [w.literal(loop.env()) for w in c.words or []]
            if c.words and None not in values and len(values) <= 32:
                # A list of literal words: the body runs once with each, in order.
                for v in values:
                    loop.vars[c.var] = v
                    loop.tainted.discard(c.var)
                    if mentions_gh(v):
                        loop.tainted.add(c.var)
                    self.walk(c.parts[0][1], loop)
                merged = state.copy()
                merged.merge([loop])
                self.adopt(state, merged)
                return
            loop.vars[c.var] = None
            loop.tainted.discard(c.var)
            if any(self.has_gh(w, state) for w in c.words or []):
                loop.tainted.add(c.var)
        for _ in range(2):
            after = loop.copy()
            for cond, body in c.parts:
                if cond is not None:
                    self.walk(cond, after)
                self.walk(body, after)
            loop.merge([after])
        merged = state.copy()
        merged.merge([loop])
        self.adopt(state, merged)

    def adopt(self, state, other):
        for name in State.__slots__:
            setattr(state, name, getattr(other, name))

    def inherited_stdin(self, redirs, piped):
        own = [r for r in redirs if r.op in STDIN_OPS]
        for outer, outer_piped in reversed(self.stdin):
            piped = piped or outer_piped
            if not own:
                own = outer
        return own, piped

    def redirect_targets(self, redirs, state):
        for r in redirs:
            if r.target is not None:
                self.substitutions(r.target, state)

    def simple(self, cmd, state, piped, downstream):
        for _, w, _ in cmd.assigns:
            self.substitutions(w, state)
        for w in cmd.words:
            self.substitutions(w, state)
        self.redirect_targets(cmd.redirs, state)
        streams = [(r, self.heredoc_text(r, state)) for r in cmd.redirs if r.op in ("<<", "<<-", "<<<")]

        if not cmd.words:
            for name, w, appends in cmd.assigns:
                self.assign(name, w, appends, state, export=False)
            self.writes(cmd, None, state, streams)
            return

        vals = [self.value(w, state) for w in cmd.words]
        try:
            k, env = unwrap(vals)
        except Unknown as why:
            self.problem("The hook cannot read " + str(why) + ", so it cannot tell what the"
                         " command runs.")
            return
        if k is None:
            return
        if k >= len(vals):
            # env alone, and the like: it prints, and runs nothing.
            self.check_words(cmd.words, state, quiet=True)
            return
        name = vals[k]
        if name is None:
            # It cannot be gh unless a gh word is in it: the name, an argument, or a stream.
            if any(self.has_gh(w, state) for w in cmd.words) or any(x.gh for _, x in streams):
                self.problem("A command's name cannot be known before it runs, so the hook"
                             " cannot tell what it runs.")
                return
            self.names_files("", False, vals[k + 1:], state)
            self.writes(cmd, None, state, streams)
            return
        base = _name(name)
        args = cmd.words[k + 1:]
        if is_gh(name):
            # The words after gh are what it sends; reading them is the classifier's work.
            stdin, piped = self.inherited_stdin(cmd.redirs, piped)
            self.invocations.append(Invocation(args, list(cmd.assigns), env, stdin,
                                               state.copy(), piped, cmd, name))
            self.check_words(cmd.words[:k], state, quiet=True)
            self.writes(cmd, None, state, [])
            return
        if base in DECLARE:
            self.declare(base, args, vals[k + 1:], state)
            return
        if base in SHELLS:
            self.shell(cmd, args, vals[k + 1:], state, streams, piped)
            return
        if base == "cd":
            self.cd(vals[k + 1:], state)
        if base in ("source", ".") or name.startswith("/") or name.startswith("."):
            self.runs_file(state.path(name) if base not in ("source", ".")
                           else state.path(vals[k + 1] if k + 1 < len(vals) else None), state)
        quiet = self.quiet(name, vals[k + 1:])
        self.check_words(cmd.words, state, quiet)
        for r, text in streams:
            if text.gh and not quiet:
                self.problem("A gh word is in " + text.label + " that " + base
                             + " reads, and it can run what it reads.")
            elif text.gh:
                self.quiet_gh.append(text.label)
        self.names_files(base, quiet, vals[k + 1:], state)
        self.writes(cmd, (base, vals[k + 1:]), state, streams)
        if base == "git" and git_subcommand(vals[k + 1:]) in ("remote", "config", None):
            state.events.append("git " + (git_subcommand(vals[k + 1:]) or "with an unknown word"))
        if base == "unset":
            for v in vals[k + 1:]:
                state.vars.pop(v or "", None)
                if v is None or v.startswith("GH_") or v.startswith("GIT_"):
                    state.events.append("unset of " + (v or "a variable it cannot know"))

    quiet_gh = None

    def check_words(self, words, state, quiet):
        for w in words:
            if self.has_gh(w, state):
                if quiet:
                    self.quiet_gh.append("an argument")
                else:
                    self.problem("A gh word is an argument of a command that can run its"
                                 " arguments, so the hook cannot tell what it runs.")

    def assign(self, name, word, appends, state, export):
        value = word.literal(state.env(), pattern_ok=True)
        if appends:
            old = state.vars.get(name, "")
            value = None if old is None or value is None else old + value
        state.vars[name] = value
        if export:
            state.exported.add(name)
        state.tainted.discard(name)
        if value is None and self.taints(word):
            state.tainted.add(name)
        if name.startswith("GIT_") or name in ("GH_CONFIG_DIR", "GH_HOST", "GH_REPO"):
            state.events.append("assigns " + name)

    def taints(self, word):
        # An unknown value built from a gh word, unless it is only the output of a gh command.
        if mentions_gh(own_text(word)):
            return True
        for p in word.parts:
            if p.kind in ("cmdsub", "procsub") and mentions_gh(p.text):
                items = p.script.items
                first = items[0][0].pipelines[0].commands[0] if items else None
                if not (len(items) == 1 and isinstance(first, Simple) and first.words
                        and is_gh(first.words[0].literal())):
                    return True
        return False

    def declare(self, base, args, vals, state):
        for w, v in zip(args, vals):
            first = w.parts[0] if w.parts else None
            m = _ASSIGN.match(first.text) if first is not None and first.kind == "lit" \
                and not first.quoted else None
            if m:
                self.assign(m.group(1), _after_assign(w, m.end()), m.group(2) == "+", state,
                            export=base == "export")
            elif v is not None and _NAME.fullmatch(v):
                if base == "export":
                    state.exported.add(v)
            elif self.has_gh(w, state):
                self.problem("A gh word is an argument of " + base + " that the hook cannot read.")

    def cd(self, vals, state):
        if not vals:
            target = state.vars.get("HOME")
        elif len(vals) == 1 and vals[0] is not None and vals[0] != "-":
            target = vals[0] if vals[0].startswith("/") else None
            if target is None and len(state.cwds) == 1 and state.cwds[0] is not None:
                target = state.cwds[0] + "/" + vals[0]
        else:
            target = None
        state.cwds = (_norm(target) if target else None,)

    def shell(self, cmd, args, vals, state, streams, piped):
        # sh -c <script>, sh <file>, and sh reading its script from standard input.
        k = 0
        script = None
        while k < len(vals):
            a = vals[k]
            if a is None:
                if self.has_gh(args[k], state):
                    self.problem("A shell is given a gh word the hook cannot read.")
                return
            if a == "--":
                k += 1
                break
            if a in ("-o", "+o", "-O", "+O"):
                k += 2
                continue
            if a.startswith("-") or a.startswith("+"):
                if "c" in a[1:]:
                    script = k + 1
                    break
                k += 1
                continue
            break
        child = state.copy()
        child.vars = dict((n, v) for n, v in state.vars.items() if n in state.exported)
        if script is not None:
            if script >= len(vals) or vals[script] is None:
                if script < len(args) and self.has_gh(args[script], state):
                    self.problem("A shell is given a script the hook cannot read, and it holds"
                                 " a gh word.")
                return
            self.reparse(vals[script], child)
            return
        if k < len(vals):
            self.runs_file(state.path(vals[k]), state, ran_by_shell=True)
            return
        if piped:
            self.problem("A shell reads its script from a pipe, so the hook cannot tell what it"
                         " runs.")
            return
        for r, text in streams:
            if text.content is None:
                if text.gh:
                    self.problem("A shell reads " + text.label + " the hook cannot know.")
            else:
                self.reparse(text.content, child)

    def reparse(self, text, state):
        if not mentions_gh(text):
            return
        self.walk(parse(text), state)

    def runs_file(self, path, state, ran_by_shell=False):
        if path is None or path not in state.files:
            return
        text = state.files[path]
        if text.content is None:
            self.problem("The command runs a file it wrote, and the hook cannot know what it"
                         " holds.")
        else:
            self.reparse(text.content, state.copy())

    def names_files(self, base, quiet, vals, state):
        # A path any command but a reader names may change before gh reads it (T5).
        if base not in READERS:
            for v in vals:
                p = state.path(v) if v else None
                if p is not None and p not in state.named:
                    state.named[p] = base
        # A file this command wrote, with a gh word in it, named by a command that can run it.
        if quiet:
            return
        for v in vals:
            p = state.path(v) if v else None
            if p in state.files and state.files[p].gh:
                self.problem("A file the command wrote holds a gh word, and " + base
                             + " reads it and can run what it reads.")

    def writes(self, cmd, who, state, streams):
        """Records each file a command writes, a redirection's target or one of tee's files,
        with what it writes when that is known: a here-document cat or tee copies, or the
        literal text echo or printf prints. A file it cannot resolve is not recorded, and a
        later read of it is decided by where it is read (T5)."""
        base, vals = who if who is not None else ("", [])
        files = [v for v in vals if v is None or not v.startswith("-")]
        content, gh = None, False
        if base == "cat" and streams and not files or base == "tee" and streams:
            content, gh = streams[-1][1].content, streams[-1][1].gh
        elif base in ("echo", "printf"):
            content, gh = self.printed(base, vals)
        targets = []
        for r in cmd.redirs:
            if r.target is None or not (r.op.startswith(">") or r.op.startswith("&>")):
                continue
            v = r.target.literal(state.env())
            if r.op in (">&", "<&") and v is not None and (v.isdigit() or v == "-"):
                continue
            out = r.fd in ("", "1") or r.op.startswith("&>") or r.op == ">&"
            targets.append((v, r.op.startswith(">>") or r.op == "&>>", out))
        if base == "tee":
            appends = "-a" in vals or "--append" in vals
            targets += [(v, appends, True) for v in files]
        for v, appends, out in targets:
            p = state.path(v)
            if p is None or p == "/dev/null":
                continue
            text = Text(content if out else None, gh and out, "a file this command wrote")
            old = state.files.get(p)
            if appends and old is None and p not in state.named:
                old = on_disk(p)
            if appends:
                if old is None or old.content is None or text.content is None:
                    text = Text(None, text.gh or (old is not None and old.gh), text.label)
                else:
                    text = Text(old.content + text.content, text.gh or old.gh, text.label)
            state.files[p] = text

    def printed(self, base, vals):
        if any(v is None for v in vals):
            return None, any(v is None or mentions_gh(v) for v in vals)
        return printed(base, vals), any(mentions_gh(v) for v in vals)

    def find(self, script):
        self.quiet_gh = []
        self.stdin = []
        self.walk(script, self.start.copy())
        return self


def read_input(data):
    """The command and the directory it starts in, or None when the input is not a hook's."""
    try:
        hook = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return None
    if not isinstance(hook, dict):
        return None
    tool_input = hook.get("tool_input")
    if not isinstance(tool_input, dict):
        return None
    command = tool_input.get("command")
    if not isinstance(command, str):
        return None
    # The terminal tool carries its own directory; Bash and Monitor run in the session's (#361).
    cwd = tool_input.get("cwd")
    if not isinstance(cwd, str) or not cwd:
        cwd = hook.get("cwd")
    if not isinstance(cwd, str) or not cwd:
        cwd = None
    return command, cwd


# ---------------------------------------------------------------------------------------------
# The table: each path of gh, its built-in aliases and its flags, from gh's own help.

# BEGIN TABLE (regenerate-table.py writes this block; do not edit it by hand)
TABLE_VERSION = "2.104"
# gh 2.104.0: <path>|<aliases, by ;>|<flags, by space; = takes a value>
TABLE = """
||--help --version
agent-task|agent-tasks;agent;agents|--help
agent-task create||-b,--base= -a,--custom-agent= --follow -F,--from-file= -R,--repo= --help
agent-task list||-q,--jq= --json= -L,--limit= -t,--template= -w,--web --help
agent-task view||--follow -q,--jq= --json= --log -R,--repo= -t,--template= -w,--web --help
alias||--help
alias delete||--all --help
alias import||--clobber --help
alias list|alias ls|--help
alias set||--clobber -s,--shell --help
api||--allow-escape-sequences --cache= -F,--field= -H,--header= --hostname= -i,--include --input= -q,--jq= -X,--method= --paginate -p,--preview= -f,--raw-field= --silent --slurp -t,--template= --verbose --help
attestation|at|--help
attestation download||-d,--digest-alg= --hostname= -L,--limit= -o,--owner= --predicate-type= -R,--repo= --help
attestation trusted-root||--hostname= --tuf-root= --tuf-url= --verify-only --help
attestation verify||-b,--bundle= --bundle-from-oci --cert-identity= -i,--cert-identity-regex= --cert-oidc-issuer= --custom-trusted-root= --deny-self-hosted-runners -d,--digest-alg= --format= --hostname= -q,--jq= -L,--limit= --no-public-good -o,--owner= --predicate-type= -R,--repo= --signer-digest= --signer-repo= --signer-workflow= --source-digest= --source-ref= -t,--template= --help
auth||--help
auth login||-c,--clipboard --expiring -p,--git-protocol= -h,--hostname= --insecure-storage -s,--scopes= --skip-ssh-key -w,--web --with-token --help
auth logout||-h,--hostname= -u,--user= --help
auth refresh||-c,--clipboard --expiring -h,--hostname= --insecure-storage -r,--remove-scopes= --reset-scopes -s,--scopes= --help
auth setup-git||-f,--force -h,--hostname= --help
auth status||-a,--active -h,--hostname= --jq= --json= --no-refresh -t,--show-token --template= --help
auth switch||-h,--hostname= -u,--user= --help
auth token||-h,--hostname= --no-refresh -u,--user= --help
browse||-a,--actions --blame -b,--branch= -c,--commit= -n,--no-browser -p,--projects -r,--releases -R,--repo= -s,--settings -w,--wiki --help
cache||-R,--repo= --help
cache delete||-a,--all -r,--ref= --succeed-on-no-caches --help -R,--repo=
cache list|cache ls|-q,--jq= --json= -k,--key= -L,--limit= -O,--order= -r,--ref= -S,--sort= -t,--template= --help -R,--repo=
codespace|cs|--help
codespace code||-c,--codespace= --insiders -R,--repo= --repo-owner= -w,--web --help
codespace cp||-c,--codespace= -e,--expand -p,--profile= -r,--recursive -R,--repo= --repo-owner= --help
codespace create||-b,--branch= --default-permissions --devcontainer-path= -d,--display-name= --idle-timeout= -l,--location= -m,--machine= -R,--repo= --retention-period= -s,--status -w,--web --help
codespace delete||--all -c,--codespace= --days= -f,--force -o,--org= -R,--repo= --repo-owner= -u,--user= --help
codespace edit||-c,--codespace= -d,--display-name= -m,--machine= -R,--repo= --repo-owner= --help
codespace jupyter||-c,--codespace= -R,--repo= --repo-owner= --help
codespace list|codespace ls;cs ls|-q,--jq= --json= -L,--limit= -o,--org= -R,--repo= -t,--template= -u,--user= -w,--web --help
codespace logs||-c,--codespace= -f,--follow -R,--repo= --repo-owner= --help
codespace ports||-c,--codespace= -q,--jq= --json= -R,--repo= --repo-owner= -t,--template= --help
codespace ports forward||--all-interfaces -c,--codespace= --help -R,--repo= --repo-owner=
codespace ports visibility||-c,--codespace= --help -R,--repo= --repo-owner=
codespace rebuild||-c,--codespace= --full -R,--repo= --repo-owner= --help
codespace ssh||-c,--codespace= --config -d,--debug --debug-file= --profile= -R,--repo= --repo-owner= --server-port= --help
codespace stop||-c,--codespace= -o,--org= -R,--repo= --repo-owner= -u,--user= --help
codespace view||-c,--codespace= -q,--jq= --json= -R,--repo= --repo-owner= -t,--template= --help
completion||-s,--shell= --help
config||--help
config clear-cache||--help
config get||-h,--host= --help
config list|config ls|-h,--host= --help
config set||-h,--host= --help
copilot||--remove --help
discussion||-R,--repo= --help
discussion comment||-b,--body= -F,--body-file= --delete --edit -R,--repo= --yes --help
discussion create||-b,--body= -F,--body-file= -c,--category= -l,--label= -R,--repo= -t,--title= --help
discussion edit||--add-label= -b,--body= -F,--body-file= -c,--category= --remove-label= -R,--repo= -t,--title= --help
discussion list|discussion ls|--after= --answered -A,--author= -c,--category= -q,--jq= --json= -l,--label= -L,--limit= --order= -R,--repo= -S,--search= --sort= -s,--state= -t,--template= -w,--web --help
discussion view||--after= -c,--comments -q,--jq= --json= -L,--limit= --order= -R,--repo= -t,--template= -w,--web --help
extension|extensions;ext|--help
extension browse||--debug -s,--single-column --help
extension create||--precompiled= --help
extension exec||
extension install||--force --pin= --help
extension list|ext ls;extension ls;extensions ls|--help
extension remove|ext uninstall;extension uninstall;extensions uninstall|--help
extension search||-q,--jq= --json= --license= -L,--limit= --order= --owner= --sort= -t,--template= -w,--web --help
extension upgrade||--all --dry-run --force --help
gist||--help
gist clone||--help
gist create|gist new|-d,--desc= -f,--filename= -p,--public -w,--web --help
gist delete||--yes --help
gist edit||-a,--add= -d,--desc= -f,--filename= -r,--remove= --help
gist list|gist ls|--filter= --include-content -L,--limit= --public --secret --help
gist rename||--help
gist view||--allow-escape-sequences -f,--filename= --files -r,--raw -w,--web --help
gpg-key||--help
gpg-key add||-t,--title= --help
gpg-key delete||-y,--yes --help
gpg-key list|gpg-key ls|--help
issue||-R,--repo= --help
issue artifact||--help -R,--repo=
issue artifact create|issue artifact new|--attach= -b,--body= -F,--body-file= --name= --type= --help -R,--repo=
issue artifact delete||--yes --help -R,--repo=
issue artifact download||--clobber -D,--dir= -O,--output= --skip-existing --version= --help -R,--repo=
issue artifact edit||--attach= -b,--body= -F,--body-file= --name= --restore-version= --help -R,--repo=
issue artifact list|issue artifact ls|-q,--jq= --json= -L,--limit= -t,--template= --type= --help -R,--repo=
issue artifact view||-q,--jq= --json= -t,--template= --version= -w,--web --help -R,--repo=
issue close||-c,--comment= --duplicate-of= -r,--reason= --help -R,--repo=
issue comment||--attach= -b,--body= -F,--body-file= --create-if-none --delete-last --edit-last -e,--editor -w,--web --yes --help -R,--repo=
issue create|issue new|-a,--assignee= --attach= --blocked-by= --blocking= -b,--body= -F,--body-file= -e,--editor -l,--label= -m,--milestone= --parent= -p,--project= --recover= -T,--template= -t,--title= --type= -w,--web --help -R,--repo=
issue delete||--yes --help -R,--repo=
issue develop||-b,--base= --branch-repo= -c,--checkout -l,--list -n,--name= --worktree= --help -R,--repo=
issue edit||--add-assignee= --add-blocked-by= --add-blocking= --add-label= --add-project= --add-sub-issue= --attach= -b,--body= -F,--body-file= -m,--milestone= --parent= --remove-assignee= --remove-blocked-by= --remove-blocking= --remove-label= --remove-milestone --remove-parent --remove-project= --remove-sub-issue= --remove-type -t,--title= --type= --help -R,--repo=
issue list|issue ls|--app= -a,--assignee= -A,--author= -q,--jq= --json= -l,--label= -L,--limit= --mention= -m,--milestone= -S,--search= -s,--state= -t,--template= --type= -w,--web --help -R,--repo=
issue lock||-r,--reason= --help -R,--repo=
issue pin||--help -R,--repo=
issue reopen||-c,--comment= --help -R,--repo=
issue status||-q,--jq= --json= -t,--template= --help -R,--repo=
issue transfer||--help -R,--repo=
issue unlock||--help -R,--repo=
issue unpin||--help -R,--repo=
issue view||-c,--comments -q,--jq= --json= -t,--template= -w,--web --help -R,--repo=
label||-R,--repo= --help
label clone||-f,--force --help -R,--repo=
label create||-c,--color= -d,--description= -f,--force --help -R,--repo=
label delete||--yes --help -R,--repo=
label edit||-c,--color= -d,--description= -n,--name= --help -R,--repo=
label list|label ls|-q,--jq= --json= -L,--limit= --order= -S,--search= --sort= -t,--template= -w,--web --help -R,--repo=
licenses||--help
org||--help
org list|org ls|-L,--limit= --help
pr||-R,--repo= --help
pr checkout|pr co|-b,--branch= --detach -f,--force --recurse-submodules --worktree= --help -R,--repo=
pr checks||--fail-fast -i,--interval= -q,--jq= --json= --required -t,--template= --watch -w,--web --help -R,--repo=
pr close||-c,--comment= -d,--delete-branch --help -R,--repo=
pr comment||--attach= -b,--body= -F,--body-file= --create-if-none --delete-last --edit-last -e,--editor -w,--web --yes --help -R,--repo=
pr create|pr new|-a,--assignee= --attach= -B,--base= -b,--body= -F,--body-file= -d,--draft --dry-run -e,--editor -f,--fill --fill-first --fill-verbose -H,--head= -l,--label= -m,--milestone= --no-maintainer-edit -p,--project= --recover= -r,--reviewer= -T,--template= -t,--title= -w,--web --help -R,--repo=
pr diff||--allow-escape-sequences --color= -e,--exclude= --name-only --patch -w,--web --help -R,--repo=
pr edit||--add-assignee= --add-label= --add-project= --add-reviewer= --attach= -B,--base= -b,--body= -F,--body-file= -m,--milestone= --remove-assignee= --remove-label= --remove-milestone --remove-project= --remove-reviewer= -t,--title= --help -R,--repo=
pr list|pr ls|--app= -a,--assignee= -A,--author= -B,--base= -d,--draft -H,--head= -q,--jq= --json= -l,--label= -L,--limit= -S,--search= -s,--state= -t,--template= -w,--web --help -R,--repo=
pr lock||-r,--reason= --help -R,--repo=
pr merge||--admin -A,--author-email= --auto -b,--body= -F,--body-file= -d,--delete-branch --disable-auto --match-head-commit= -m,--merge -r,--rebase -s,--squash -t,--subject= --help -R,--repo=
pr ready||--undo --help -R,--repo=
pr reopen||-c,--comment= --help -R,--repo=
pr revert||-b,--body= -F,--body-file= -d,--draft -t,--title= --help -R,--repo=
pr review||-a,--approve -b,--body= -F,--body-file= -c,--comment -r,--request-changes --help -R,--repo=
pr status||-c,--conflict-status -q,--jq= --json= -t,--template= --help -R,--repo=
pr unlock||--help -R,--repo=
pr update-branch||--rebase --help -R,--repo=
pr view||-c,--comments -q,--jq= --json= -t,--template= -w,--web --help -R,--repo=
preview||--help
preview prompter||--help
project||--help
project close||--format= -q,--jq= --owner= -t,--template= --undo --help
project copy||--drafts --format= -q,--jq= --source-owner= --target-owner= -t,--template= --title= --help
project create||--format= -q,--jq= --owner= -t,--template= --title= --help
project delete||--format= -q,--jq= --owner= -t,--template= --help
project edit||-d,--description= --format= -q,--jq= --owner= --readme= -t,--template= --title= --visibility= --help
project field-create||--data-type= --format= -q,--jq= --name= --owner= --single-select-options= -t,--template= --help
project field-delete||--format= --id= -q,--jq= -t,--template= --help
project field-list||--format= -q,--jq= -L,--limit= --owner= -t,--template= --help
project item-add||--format= -q,--jq= --owner= -t,--template= --url= --help
project item-archive||--format= --id= -q,--jq= --owner= -t,--template= --undo --help
project item-create||--body= --format= -q,--jq= --owner= -t,--template= --title= --help
project item-delete||--format= --id= -q,--jq= --owner= -t,--template= --help
project item-edit||--body= --clear --date= --field= --field-id= --format= --id= --iteration-id= -q,--jq= --number= --owner= --project-id= --single-select-option-id= -t,--template= --text= --title= --url= --value= --help
project item-list||--field= --field-id= --format= -q,--jq= -L,--limit= --owner= --query= -t,--template= --help
project link||--owner= -R,--repo= -T,--team= --help
project list|project ls|--closed --format= -q,--jq= -L,--limit= --owner= -t,--template= -w,--web --help
project mark-template||--format= -q,--jq= --owner= -t,--template= --undo --help
project unlink||--owner= -R,--repo= -T,--team= --help
project view||--format= -q,--jq= --owner= -t,--template= -w,--web --help
release||-R,--repo= --help
release create|release new|--discussion-category= -d,--draft --fail-on-no-commits --generate-notes --latest -n,--notes= -F,--notes-file= --notes-from-tag --notes-start-tag= -p,--prerelease --target= -t,--title= --verify-tag --help -R,--repo=
release delete||--cleanup-tag -y,--yes --help -R,--repo=
release delete-asset||-y,--yes --help -R,--repo=
release download||--allow-escape-sequences -A,--archive= --clobber -D,--dir= -O,--output= -p,--pattern= --skip-existing --help -R,--repo=
release edit||--discussion-category= --draft --latest -n,--notes= -F,--notes-file= --prerelease --tag= --target= -t,--title= --verify-tag --help -R,--repo=
release list|release ls|--exclude-drafts --exclude-pre-releases -q,--jq= --json= -L,--limit= -O,--order= -t,--template= --help -R,--repo=
release upload||--clobber --help -R,--repo=
release verify||--format= -q,--jq= -t,--template= --help -R,--repo=
release verify-asset||--format= -q,--jq= -t,--template= --help -R,--repo=
release view||-q,--jq= --json= -t,--template= -w,--web --help -R,--repo=
repo||--help
repo archive||-y,--yes --help
repo autolink||-R,--repo= --help
repo autolink create|repo autolink new|-n,--numeric --help -R,--repo=
repo autolink delete||--yes --help -R,--repo=
repo autolink list|repo autolink ls|-q,--jq= --json= -t,--template= -w,--web --help -R,--repo=
repo autolink view||-q,--jq= --json= -t,--template= --help -R,--repo=
repo clone||--no-upstream -u,--upstream-remote-name= --help
repo create|repo new|--add-readme -c,--clone -d,--description= --disable-issues --disable-wiki -g,--gitignore= -h,--homepage= --include-all-branches --internal -l,--license= --private --public --push -r,--remote= -s,--source= -t,--team= -p,--template= --help
repo delete||--accept-cascading-deletion-of-private-forks --yes --help
repo deploy-key||-R,--repo= --help
repo deploy-key add||-w,--allow-write -t,--title= --help -R,--repo=
repo deploy-key delete||--help -R,--repo=
repo deploy-key list|repo deploy-key ls|-q,--jq= --json= -t,--template= --help -R,--repo=
repo edit||--accept-visibility-change-consequences --add-topic= --allow-forking --allow-update-branch --default-branch= --delete-branch-on-merge -d,--description= --enable-advanced-security --enable-auto-merge --enable-discussions --enable-issues --enable-merge-commit --enable-projects --enable-rebase-merge --enable-secret-scanning --enable-secret-scanning-push-protection --enable-squash-merge --enable-wiki -h,--homepage= --remove-topic= --squash-merge-commit-message= --template --visibility= --help
repo fork||--clone --default-branch-only --fork-name= --org= --remote --remote-name= --help
repo gitignore||--help
repo gitignore list|repo gitignore ls|--help
repo gitignore view||--help
repo license||--help
repo license list|repo license ls|--help
repo license view||-w,--web --help
repo list|repo ls|--archived --fork -q,--jq= --json= -l,--language= -L,--limit= --no-archived --source -t,--template= --topic= --visibility= --help
repo read-dir||-q,--jq= --json= --ref= -R,--repo= -t,--template= --help
repo read-file||--allow-escape-sequences --clobber -q,--jq= --json= -o,--output= --ref= -R,--repo= -t,--template= --help
repo rename||-R,--repo= -y,--yes --help
repo set-default||-u,--unset -v,--view --help
repo sync||-b,--branch= --force -s,--source= --help
repo unarchive||-y,--yes --help
repo view||-b,--branch= -q,--jq= --json= -t,--template= -w,--web --help
ruleset|rs|-R,--repo= --help
ruleset check||--default -w,--web --help -R,--repo=
ruleset list|rs ls;ruleset ls|-L,--limit= -o,--org= -p,--parents -w,--web --help -R,--repo=
ruleset view||-o,--org= -p,--parents -w,--web --help -R,--repo=
run||-R,--repo= --help
run cancel||--force --help -R,--repo=
run delete||--help -R,--repo=
run download||-D,--dir= -n,--name= -p,--pattern= --help -R,--repo=
run list|run ls|-a,--all -b,--branch= -c,--commit= --created= -e,--event= -q,--jq= --json= -L,--limit= -s,--status= -t,--template= -u,--user= -w,--workflow= --help -R,--repo=
run rerun||-d,--debug --failed -j,--job= --help -R,--repo=
run view||-a,--attempt= --exit-status -j,--job= -q,--jq= --json= --log --log-failed -t,--template= -v,--verbose -w,--web --help -R,--repo=
run watch||--compact --exit-status -i,--interval= --help -R,--repo=
search||--help
search code||--extension= --filename= -q,--jq= --json= --language= -L,--limit= --match= --owner= -R,--repo= --size= -t,--template= -w,--web --help
search commits||--author= --author-date= --author-email= --author-name= --committer= --committer-date= --committer-email= --committer-name= --hash= -q,--jq= --json= -L,--limit= --merge --order= --owner= --parent= -R,--repo= --sort= -t,--template= --tree= --visibility= -w,--web --help
search issues||--app= --archived --assignee= --author= --closed= --commenter= --comments= --created= --include-prs --interactions= --involves= -q,--jq= --json= --label= --language= -L,--limit= --locked --match= --mentions= --milestone= --no-assignee --no-label --no-milestone --no-project --order= --owner= --project= --reactions= -R,--repo= --search-type= --sort= --state= --team-mentions= -t,--template= --updated= --visibility= -w,--web --help
search prs||--app= --archived --assignee= --author= -B,--base= --checks= --closed= --commenter= --comments= --created= --draft -H,--head= --interactions= --involves= -q,--jq= --json= --label= --language= -L,--limit= --locked --match= --mentions= --merged --merged-at= --milestone= --no-assignee --no-label --no-milestone --no-project --order= --owner= --project= --reactions= -R,--repo= --review= --review-requested= --reviewed-by= --sort= --state= --team-mentions= -t,--template= --updated= --visibility= -w,--web --help
search repos||--archived --created= --followers= --forks= --good-first-issues= --help-wanted-issues= --include-forks= -q,--jq= --json= --language= --license= -L,--limit= --match= --number-topics= --order= --owner= --size= --sort= --stars= -t,--template= --topic= --updated= --visibility= -w,--web --help
secret||-R,--repo= --help
secret delete|secret remove|-a,--app= -e,--env= -o,--org= -u,--user --help -R,--repo=
secret list|secret ls|-a,--app= -e,--env= -q,--jq= --json= -o,--org= -t,--template= -u,--user --help -R,--repo=
secret set||-a,--app= -b,--body= -e,--env= -f,--env-file= --no-repos-selected --no-store -o,--org= -r,--repos= -u,--user -v,--visibility= --help -R,--repo=
skill|skills|--help
skill install|skill add;skills add|--agent= --all --allow-hidden-dirs --dir= -f,--force --from-local --pin= --scope= --upstream --help
skill list|skill ls;skills ls|--agent= --dir= -q,--jq= --json= --scope= -t,--template= --help
skill preview|skill show;skills show|--allow-hidden-dirs --help
skill publish||--dry-run --fix --tag= --help
skill search||-q,--jq= --json= -L,--limit= --owner= --page= -t,--template= --help
skill update||--all --dir= --dry-run --force --unpin --help
ssh-key||--help
ssh-key add||-t,--title= --type= --help
ssh-key delete||-y,--yes --help
ssh-key list|ssh-key ls|--help
status||-e,--exclude= -o,--org= --help
variable||-R,--repo= --help
variable delete|variable remove|-e,--env= -o,--org= --help -R,--repo=
variable get||-e,--env= -q,--jq= --json= -o,--org= -t,--template= --help -R,--repo=
variable list|variable ls|-e,--env= -q,--jq= --json= -o,--org= -t,--template= --help -R,--repo=
variable set||-b,--body= -e,--env= -f,--env-file= -o,--org= -r,--repos= -v,--visibility= --help -R,--repo=
workflow||-R,--repo= --help
workflow disable||--help -R,--repo=
workflow enable||--help -R,--repo=
workflow list|workflow ls|-a,--all -q,--jq= --json= -L,--limit= -t,--template= --help -R,--repo=
workflow run||-F,--field= --json -f,--raw-field= -r,--ref= --help -R,--repo=
workflow view||-r,--ref= -w,--web -y,--yaml --help -R,--repo=
"""
# END TABLE


# What each path does, by hand: gh's help does not say. A read passes; a write sends its values
# to the guard; local state passes and leaves a later write's target unknown; arbitrary
# execution blocks wherever it would run. A path the table holds with no kind here blocks.
KINDS_TEXT = """
read: |help|version|agent-task|agent-task list|agent-task view|alias|alias list|attestation
read: attestation download|attestation trusted-root|attestation verify|auth|auth status|auth token
read: auth git-credential|browse|cache|cache list|codespace|codespace list|codespace logs|codespace view|codespace ports
read: completion|config|config get|config list|discussion|discussion list|discussion view
read: extension|extension browse|extension create|extension list|extension search|gist|gist clone
read: gist list|gist view|gpg-key|gpg-key list|issue|issue artifact|issue artifact download
read: issue artifact list|issue artifact view|issue list|issue status|issue view|label|label list
read: licenses|org|org list|pr|pr checkout|pr checks|pr diff|pr list|pr status|pr view|preview
read: preview prompter|project|project field-list|project item-list|project list|project view
read: release|release download|release list|release verify|release verify-asset|release view|repo
read: repo autolink|repo autolink list|repo autolink view|repo clone|repo deploy-key
read: repo deploy-key list|repo gitignore|repo gitignore list|repo gitignore view|repo license
read: repo license list|repo license view|repo list|repo read-dir|repo read-file|repo view|ruleset
read: ruleset check|ruleset list|ruleset view|run|run download|run list|run view|run watch|search
read: search code|search commits|search issues|search prs|search repos|secret|secret list|skill
read: skill install|skill list|skill preview|skill search|skill update|ssh-key|ssh-key list|status
read: variable|variable get|variable list|workflow|workflow list|workflow view
local: alias delete|alias import|alias set|auth login|auth logout|auth refresh|auth setup-git
local: auth switch|config clear-cache|config set|extension remove|repo set-default
exec: copilot|extension exec|extension install|extension upgrade|codespace code|codespace cp
exec: codespace jupyter|codespace ports forward|codespace ssh
api: api
write: agent-task create|cache delete|codespace create|codespace delete|codespace edit
write: codespace ports visibility|codespace rebuild|codespace stop|discussion comment
write: discussion create|discussion edit|gist create|gist delete|gist edit|gist rename|gpg-key add
write: gpg-key delete|issue artifact create|issue artifact delete|issue artifact edit|issue close
write: issue comment|issue create|issue delete|issue develop|issue edit|issue lock|issue pin
write: issue reopen|issue transfer|issue unlock|issue unpin|label clone|label create|label delete
write: label edit|pr close|pr comment|pr create|pr edit|pr lock|pr merge|pr ready|pr reopen
write: pr revert|pr review|pr unlock|pr update-branch|project close|project copy|project create
write: project delete|project edit|project field-create|project field-delete|project item-add
write: project item-archive|project item-create|project item-delete|project item-edit|project link
write: project mark-template|project unlink|release create|release delete|release delete-asset
write: release edit|release upload|repo archive|repo autolink create|repo autolink delete
write: repo create|repo delete|repo deploy-key add|repo deploy-key delete|repo edit|repo fork
write: repo rename|repo sync|repo unarchive|run cancel|run delete|run rerun|secret delete
write: secret set|skill publish|ssh-key add|ssh-key delete|variable delete|variable set
write: workflow disable|workflow enable|workflow run
"""

KINDS = {}
for _line in KINDS_TEXT.strip().splitlines():
    _kind, _paths = _line.split(": ", 1)
    for _p in _paths.split("|"):
        KINDS[_p] = _kind

# What a flag of a write means beyond its value, by (path, long name), `*` for every path.
# "lost": gh composes the text from somewhere the hook cannot read when the flag is set.
# "file": the value is a path whose content is sent, `-` standard input. "attach": a path, then
# `#` and a label that is sent. "field": `key=value`, `key=@path` or `key=@-`. A flag with a
# value and no role here is text gh sends.
ROLES = {
    ("pr create", "fill"): "lost", ("pr create", "fill-first"): "lost",
    ("pr create", "fill-verbose"): "lost", ("pr create", "editor"): "lost",
    ("issue create", "editor"): "lost", ("issue comment", "editor"): "lost",
    ("pr comment", "editor"): "lost", ("pr create", "web"): "lost", ("issue create", "web"): "lost",
    ("issue comment", "web"): "lost", ("pr comment", "web"): "lost",
    ("pr create", "recover"): "lost", ("issue create", "recover"): "lost",
    ("pr create", "template"): "lost", ("issue create", "template"): "lost",
    ("release create", "notes-from-tag"): "lost", ("release create", "generate-notes"): "lost",
    ("issue comment", "edit-last"): "lost", ("pr comment", "edit-last"): "lost",
    ("*", "body-file"): "file", ("*", "notes-file"): "file", ("api", "input"): "file",
    ("agent-task create", "from-file"): "file", ("secret set", "env-file"): "file",
    # "unsent": the value shapes gh's own output or is checked and kept nowhere, so it is not
    # scanned and may be unknown. issue create's and pr create's --template are "lost" above.
    ("*", "jq"): "unsent", ("*", "template"): "unsent", ("*", "json"): "unsent",
    ("pr merge", "match-head-commit"): "unsent",
    ("variable set", "env-file"): "file", ("gist edit", "add"): "file",
    ("*", "attach"): "attach",
    ("api", "field"): "field", ("workflow run", "field"): "field",
}

# Which positionals of a write name files whose content is sent: `v` a value, `f` a file with an
# optional `#label`; a trailing `*` repeats the last.
POSITIONAL = {
    "gist create": "f*", "release create": "v f*", "release upload": "v f*",
    "issue artifact create": "v f*", "ssh-key add": "f", "gpg-key add": "f",
    "repo deploy-key add": "f",
}


class Node(object):
    __slots__ = ("path", "longs", "shorts", "children")

    def __init__(self, path):
        self.path = path
        self.longs = {}      # long name: takes a value
        self.shorts = {}     # letter: long name
        self.children = {}   # word: path


_NODES = None


def nodes():
    global _NODES
    if _NODES is not None:
        return _NODES
    found = {}
    aliases = []
    for line in TABLE.strip("\n").splitlines():
        path, alias_text, flag_text = line.split("|")
        n = Node(path)
        for f in flag_text.split():
            takes = f.endswith("=")
            f = f.rstrip("=")
            short = None
            if "," in f:
                short, f = f.split(",")
                short = short[1:]
            name = f[2:]
            n.longs[name] = takes
            if short:
                n.shorts[short] = name
        found[path] = n
        aliases += [(a, path) for a in alias_text.split(";") if a]
    for path in list(found):
        if path:
            parent = path.rsplit(" ", 1)[0] if " " in path else ""
            found[parent].children[path.rsplit(" ", 1)[-1]] = path
    # An alias is a whole path; its last word is a child of the path its other words name.
    for alias, path in aliases:
        words = alias.split()
        parent = ""
        for w in words[:-1]:
            parent = found[parent].children.get(w, parent + " " + w if parent else w)
        if parent in found:
            found[parent].children[words[-1]] = path
    for word in ("help", "version"):
        found[word] = Node(word)
        found[""].children[word] = word
    # gh's credential helper is hidden from its reference; git runs it as `gh auth git-credential`.
    found["auth git-credential"] = Node("auth git-credential")
    found["auth git-credential"].longs.update({"hostname": True, "help": False})
    found["auth"].children["git-credential"] = "auth git-credential"
    _NODES = found
    return found


class Verdict(object):
    """What one invocation is: kind, its path, and for a write, its sources."""

    __slots__ = ("kind", "path", "flags", "positionals", "result")

    def __init__(self, kind, path, flags=None, positionals=None, result=None):
        self.kind = kind
        self.path = path
        self.flags = flags or []
        self.positionals = positionals or []
        self.result = result


class Source(object):
    __slots__ = ("label", "data")

    def __init__(self, label, data):
        self.label = label
        self.data = data     # bytes


def _bytes(text):
    return text.encode("utf-8", "surrogatepass")


ADVICE_LOST = ("Give gh the text on the command line, or write it to a file first and give gh"
               " that file.")
ADVICE_FLAG = ("The hook's table lists every flag of gh 2.104 by subcommand; regenerate it with"
               " scripts/claude-hooks/regenerate-table.py if gh has gained one.")


def lost(what):
    return Verdict("block", None, result=block("Cannot recover the text gh would send: " + what
                                               + ".", ADVICE_LOST))


def classify(inv):
    """Reads one gh invocation as gh would: the path, then every flag by that path's table."""
    table = nodes()
    vals = [resolve(w, inv.state) for w in inv.words]
    node = table[""]
    used = set()
    k = 0
    while k < len(vals):
        v = vals[k]
        if v is None:
            if node.children:
                return Verdict("block", None, result=block(
                    "Which gh command runs depends on a word the hook cannot know before the"
                    " command runs, so it cannot tell what gh would send.", ADVICE_UNEXPLAINED))
            break
        if v == "--":
            break
        if v.startswith("-") and v != "-":
            # cobra skips a flag's value while it finds the command, and takes an unknown flag
            # without `=` to have one.
            if v.startswith("--"):
                takes = node.longs.get(v[2:].split("=", 1)[0], True) and "=" not in v
            else:
                long = node.shorts.get(v[1:2])
                takes = len(v) == 2 and (long is None or node.longs.get(long, True))
            k += 2 if takes else 1
            continue
        child = node.children.get(v)
        if child is None:
            break
        node = table[child]
        used.add(k)
        k += 1
    path = node.path
    if node.children and k < len(vals) and vals[k] not in (None, "--") \
            and not vals[k].startswith("-"):
        word = vals[k]
        return Verdict("block", None, result=block(
            ("gh " + path + " " if path else "gh ") + ("<" + word + ">" if not word.isalnum()
                                                       else word)
            + " is not a gh command the hook knows, so it can run anything: an alias, an"
            " extension, or a command newer than the hook's table.",
            "Run it yourself outside the session, or regenerate the table if gh has gained it."))
    kind = KINDS.get(path)
    if kind is None:
        return Verdict("block", None, result=block(
            "gh " + path + " has no kind in the hook's table, so the hook cannot tell whether it"
            " writes.", "Give it one in KINDS in scripts/claude-hooks/gh_guard_lib.py."))
    if kind == "exec":
        return Verdict("block", path, result=block(
            "gh " + path + " can run anything, so the hook blocks it wherever it would run.",
            "Run it yourself outside the session."))

    # Every word that is not the path, by this path's flags.
    flags = []        # (long name, value or True/False, the word's index)
    positionals = []  # (index, value)
    rest = [(i, vals[i]) for i in range(len(vals)) if i not in used]
    flaglike = False
    j = 0
    while j < len(rest):
        i, a = rest[j]
        if a is None:
            if kind in ("read", "local", "exec", "api"):
                # A word whose literal start is not `-` is a positional; any other may be a
                # flag, which leaves an api call's method unknown.
                first = inv.words[i].parts[0] if inv.words[i].parts else None
                if not (first is not None and first.kind == "lit" and first.text
                        and not first.text.startswith("-")):
                    flaglike = True
                positionals.append((i, None))
                j += 1
                continue
            return lost("a word whose value cannot be known before the command runs (word "
                        + str(i + 1) + " after gh)")
        if a == "--":
            positionals += [(i2, a2) for i2, a2 in rest[j + 1:]]
            if path in ("repo clone", "gist clone") and len(rest) > j + 1:
                return Verdict("block", None, result=block(
                    "gh " + path + " passes the words after `--` to git, which can run them.",
                    "Clone without them."))
            break
        if a.startswith("--"):
            name, eq, value = a[2:].partition("=")
            if name not in node.longs:
                return unknown_flag(path, i)
            if node.longs[name]:
                if not eq:
                    j += 1
                    if j >= len(rest):
                        return unknown_flag(path, i)
                    i, value = rest[j]
                flags.append((name, value, i))
            else:
                flags.append((name, (value or "true").lower() != "false" if eq else True, i))
        elif a.startswith("-") and a != "-":
            c = 1
            while c < len(a):
                name = node.shorts.get(a[c])
                if name is None:
                    return unknown_flag(path, i)
                if node.longs[name]:
                    value = a[c + 1:]
                    if value.startswith("="):
                        value = value[1:]
                    if not value and c + 1 >= len(a):
                        j += 1
                        if j >= len(rest):
                            return unknown_flag(path, i)
                        i, value = rest[j]
                    flags.append((name, value, i))
                    break
                if a[c + 1:c + 2] == "=":
                    flags.append((name, a[c + 2:].lower() != "false", i))
                    break
                flags.append((name, True, i))
                c += 1
        else:
            positionals.append((i, a))
        j += 1

    helps = [v for n, v, _ in flags if n == "help"]
    if helps and helps[-1] is True:
        return Verdict("read", path)
    if kind == "api":
        kind = "write" if flaglike else api_kind(flags, positionals, inv.state)
    if kind in ("read", "local"):
        return Verdict(kind, path)
    return Verdict("write", path, flags, positionals)


def unknown_flag(path, i):
    return Verdict("block", path, result=block(
        "gh " + path + " was given a flag the hook's table does not list for it (word "
        + str(i + 1) + " after gh), so it cannot tell what gh would send.", ADVICE_FLAG))


def api_kind(flags, positionals, state):
    methods = [v for n, v, _ in flags if n == "method"]
    if methods:
        return "read" if isinstance(methods[-1], str) and methods[-1].upper() == "GET" else "write"
    if any(n in ("field", "raw-field", "input") for n, _, _ in flags):
        endpoint = positionals[0][1] if positionals else None
        if endpoint == "graphql":
            queries = [(n, v[6:]) for n, v, _ in flags if n in ("field", "raw-field")
                       and isinstance(v, str) and v.startswith("query=")]
            text = None
            if queries and queries[-1][0] == "field" and queries[-1][1].startswith("@"):
                try:
                    data = read_file(queries[-1][1][1:], state)
                    text = None if data is STDIN else data.decode("utf-8", "replace")
                except Lost:
                    text = None
            elif queries:
                text = queries[-1][1]
            if text is not None and not re.search(r"\bmutation\b", text) \
                    and not any(n == "input" for n, _, _ in flags):
                return "read"
        return "write"
    return "read"


# ---------------------------------------------------------------------------------------------
# Text off the command line: what a file, standard input or a substitution gives gh, read where
# gh would read it, at hook time (#361 AC2). Anything else is unrecoverable, which blocks.

MAX_FILE = 50 * 1024 * 1024
STDIN = object()


class Lost(Exception):
    pass


def resolve(word, state):
    """A word's value, with the substitutions whose output can be known before the command runs
    (cat of a here-document, a here-string or a file, and echo or printf of literal text), or
    None. An unquoted substitution is split into words by zsh, so one with a blank is None."""
    if word.pattern():
        return None
    env = state.env()
    out = []
    for p in word.parts:
        if p.kind == "lit":
            out.append(p.text)
        elif p.kind == "home" and "HOME" in env:
            out.append(env["HOME"])
        elif p.kind == "param" and p.text in env:
            out.append(env[p.text])
        elif p.kind == "cmdsub":
            try:
                v = substitution(p.script, state)
            except Lost:
                return None
            if v is None or (not p.quoted and (v == "" or re.search(r"[ \t\n]", v))):
                return None
            out.append(v)
        else:
            return None
    return "".join(out)


def substitution(script, state):
    if script.unsupported is not None or len(script.items) != 1:
        return None
    node = script.items[0][0]
    if len(node.pipelines) != 1 or len(node.pipelines[0].commands) != 1:
        return None
    cmd = node.pipelines[0].commands[0]
    if not isinstance(cmd, Simple) or cmd.assigns or not cmd.words:
        return None
    vals = [resolve(w, state) for w in cmd.words]
    if None in vals:
        return None
    stdin = [r for r in cmd.redirs if r.op in STDIN_OPS]
    if any(r.op not in STDIN_OPS for r in cmd.redirs):
        return None
    if vals[0] == "cat" and len(vals) == 1:
        data = b"".join(stream(r, state) for r in stdin)
    elif vals[0] == "cat" and len(vals) == 2 and not stdin and not vals[1].startswith("-"):
        data = read_file(vals[1], state)
        if data is STDIN:
            return None
    elif vals[0] in ("echo", "printf") and not stdin and printed(vals[0], vals[1:]) is not None:
        data = _bytes(printed(vals[0], vals[1:]))
    else:
        return None
    return data.decode("utf-8", "surrogateescape").rstrip("\n")


def stream(r, state):
    """What a redirection of standard input gives its command, as bytes. Raises Lost."""
    if r.heredoc is not None:
        h = r.heredoc
        if h.quoted:
            return _bytes(h.body)
        v = resolve(h.word, state)
        if v is None:
            raise Lost("a here-document whose expansions cannot be known before the command runs")
        return _bytes(v)
    v = resolve(r.target, state)
    if r.op == "<<<":
        if v is None:
            raise Lost("a here-string whose value cannot be known before the command runs")
        return _bytes(v + "\n")
    if r.fd not in ("", "0"):
        raise Lost("a file opened on descriptor " + r.fd)
    data = read_file(v, state)
    if data is STDIN:
        raise Lost("standard input redirected from standard input")
    return data


def read_file(value, state):
    """A file's content as gh would read it, or STDIN for a path that is standard input."""
    if value is None:
        raise Lost("a file whose path cannot be known before the command runs")
    if value == "-" or value in ("/dev/stdin", "/dev/fd/0") or re.fullmatch(r"/proc/[^/]+/fd/0", value):
        return STDIN
    if state.deferred:
        raise Lost(value + ", read in a function's body, where it is called")
    p = state.path(value)
    if p is None:
        raise Lost("a relative path, " + value + ", in a directory the hook cannot know")
    if p in state.files:
        text = state.files[p]
        if text.content is None:
            raise Lost(value + ", which the command writes before gh reads it")
        return _bytes(text.content)
    if p in state.named:
        raise Lost(value + ", which " + state.named[p] + " names earlier in the command")
    if p == "/dev/null":
        return b""
    if p.startswith("/dev/") or p.startswith("/proc/"):
        raise Lost(value + ", which is not a file")
    import stat
    try:
        st = os.stat(p)
    except OSError as e:
        raise Lost(value + ", which " + ("does not exist" if isinstance(e, FileNotFoundError)
                                         else "cannot be read") + " when the hook runs")
    if not stat.S_ISREG(st.st_mode):
        raise Lost(value + ", which is not a regular file")
    if st.st_size > MAX_FILE:
        raise Lost(value + ", which is over 50 MB")
    try:
        with open(p, "rb") as f:
            return f.read(MAX_FILE + 1)
    except OSError:
        raise Lost(value + ", which cannot be read when the hook runs")


def file_sources(value, label, state, published=False):
    """The sources a file argument gives: its content, and for a published file its name and
    the label after `#`."""
    path, sep, tag = value.partition("#") if published or label.startswith("the --attach") \
        else (value, "", "")
    out = []
    data = read_file(path, state)
    if data is not STDIN:
        out.append(Source(label + " (" + path + ")", data))
    if published and data is not STDIN:
        out.append(Source(label + "'s name (" + path + ")", _bytes(path.rsplit("/", 1)[-1])))
    if sep:
        out.append(Source(label + "'s label", _bytes(tag)))
    return out


def gather(inv, path, flags, positionals):
    state = inv.state
    sources = []
    for name, value, i in flags:
        role = ROLES.get((path, name)) or ROLES.get(("*", name))
        if role == "lost":
            if value is not False:
                raise Lost("--" + name)
            continue
        if value is True or value is False or role == "unsent":
            continue
        if value is None:
            raise Lost("a word whose value cannot be known before the command runs (word "
                       + str(i + 1) + " after gh)")
        if role in ("file", "attach"):
            sources += file_sources(value, "the --" + name + " file", state)
        elif role == "field" and value.partition("=")[2][:1] == "@":
            key, _, rest = value.partition("=")
            sources.append(Source("the --" + name + " key", _bytes(key)))
            sources += file_sources(rest[1:], "the --" + name + " file", state)
        else:
            sources.append(Source("the --" + name + " value", _bytes(value)))
    if path == "gist edit" and not any(n in ("add", "desc", "remove") for n, _, _ in flags):
        raise Lost("gh gist edit's editor")
    if path == "agent-task create" and not positionals \
            and not any(n == "from-file" for n, _, _ in flags):
        raise Lost("gh agent-task create's editor")
    spec = POSITIONAL.get(path, "v*").split()
    for n, (i, value) in enumerate(positionals):
        role = spec[min(n, len(spec) - 1)].rstrip("*")
        if value is None:
            raise Lost("a word whose value cannot be known before the command runs (word "
                       + str(i + 1) + " after gh)")
        if role == "f":
            sources += file_sources(value, "the file in argument " + str(n + 1), state,
                                    published=True)
        else:
            sources.append(Source("argument " + str(n + 1), _bytes(value)))
    # Standard input, for every write whatever its flags: gh reads it for more than `-`.
    if inv.piped:
        raise Lost("standard input from a pipe")
    for r in inv.redirs:
        label = "standard input (" + ("a here-document" if r.heredoc is not None else
                                      "a here-string" if r.op == "<<<" else
                                      (resolve(r.target, state) or "a file")) + ")"
        sources.append(Source(label, stream(r, state)))
    return sources


# ---------------------------------------------------------------------------------------------
# Targets: which repositories a write could reach, and the exempt list (#361 AC6). A write is
# exempt only when every repository it could reach is; anything the hook cannot resolve is
# guarded, and a guarded write is scanned.

class Guarded(Exception):
    """The write's target cannot be resolved to repositories the exempt list could name."""


# Paths whose writes reach an account or an owner, not a repository.
OWNER_LEVEL = ("gist ", "project ", "ssh-key ", "gpg-key ", "codespace ", "repo fork")
# The repo subcommands whose first positional names the repository they write to.
REPO_ARGUMENT = ("repo archive", "repo delete", "repo edit", "repo sync", "repo unarchive",
                 "repo create")
_SUSPECT = re.compile(r"\.\.|%2e|%2f|//|\\\\", re.I)
# What gh reads from its environment that changes which repository or host it writes to.
TARGET_ENV = ("GH_HOST", "GH_CONFIG_DIR", "GIT_DIR", "GIT_WORK_TREE", "GIT_CONFIG",
              "GIT_CONFIG_GLOBAL", "GIT_CONFIG_SYSTEM", "GIT_CONFIG_COUNT", "GIT_CONFIG_PARAMETERS",
              "GIT_COMMON_DIR", "GIT_NAMESPACE")


def repo_of(value):
    """OWNER/REPO, lower-cased, from what -R and a remote take: OWNER/REPO, HOST/OWNER/REPO, an
    https or ssh URL, or scp-style host:owner/repo. .git is stripped only from a URL. None when
    it does not parse."""
    if value is None:
        return None
    url = False
    if "://" in value:
        rest = value.split("://", 1)[1]
        path = rest.split("/", 1)[1] if "/" in rest else ""
        url = True
    elif re.match(r"^[^/:]+:[^/]", value):
        path = value.split(":", 1)[1]
        url = True
    else:
        path = value
    path = path.split("?", 1)[0].split("#", 1)[0].strip("/")
    bits = path.split("/")
    if not url and len(bits) == 3:
        bits = bits[1:]
    if url and len(bits) >= 2:
        bits = bits[:2]
    if len(bits) != 2 or not all(re.fullmatch(r"[A-Za-z0-9_.-]+", b) for b in bits):
        return None
    repo = bits[1][:-4] if url and bits[1].endswith(".git") else bits[1]
    if not repo or repo in (".", ".."):
        return None
    return (bits[0] + "/" + repo).lower()


def url_repo(value):
    """The repository of an issue, pull request or other GitHub URL given as an argument."""
    m = re.match(r"^https?://[^/]+/([^/]+)/([^/?#]+)(/|$)", value or "")
    return (m.group(1) + "/" + m.group(2)).lower() if m else None


def named(inv, path, flags, positionals, events):
    """The repositories an invocation names itself, which decide alone, or None when it names
    none. Raises Guarded."""
    repos = [v for n, v, _ in flags if n == "repo"]
    if repos:
        r = repo_of(repos[-1])
        if r is None:
            raise Guarded("its --repo value does not parse")
        return [r]
    hosts = [v for n, v, _ in flags if n == "hostname"]
    if hosts and (not isinstance(hosts[-1], str) or hosts[-1].lower() != "github.com"):
        raise Guarded("it names a host other than github.com")
    if path.startswith(OWNER_LEVEL) or any(n in ("org", "owner", "user") for n, _, _ in flags):
        raise Guarded("it writes to an account or an owner, not a repository")
    found = []
    for _, v in positionals if path != "api" else []:
        if v is not None and re.match(r"^https?://", v):
            r = url_repo(v)
            if r is None:
                raise Guarded("a URL it is given does not parse")
            found.append(r)
    if path == "issue transfer" and len(positionals) >= 2:
        r = repo_of(positionals[1][1])
        if r is None:
            raise Guarded("the repository it transfers to does not parse")
        found.append(r)
    if found:
        return found
    assigned = [v for n, v in inv.assigns_named if n == "GH_REPO"]
    if assigned:
        r = repo_of(assigned[-1])
        if r is None:
            raise Guarded("its GH_REPO does not parse")
        return [r]
    if path in REPO_ARGUMENT:
        if not positionals:
            if path == "repo create":
                raise Guarded("gh repo create with no name writes to the account")
            return None
        v = positionals[0][1]
        if path == "repo create" and v is not None and "/" not in v:
            raise Guarded("gh repo create without an owner writes to the account")
        r = repo_of(v)
        if r is None:
            raise Guarded("the repository it names does not parse")
        return [r]
    if path == "api":
        endpoint = positionals[0][1] if positionals else None
        if endpoint is None:
            raise Guarded("its endpoint cannot be known")
        endpoint = re.sub(r"^https://(api|uploads)\.github\.com/", "", endpoint)
        if _SUSPECT.search(endpoint.split("?", 1)[0]):
            raise Guarded("its endpoint holds a sequence the hook does not resolve")
        if endpoint.startswith("/"):
            endpoint = endpoint[1:]
        m = re.match(r"^repos/([^/{}?#]+)/([^/{}?#]+)(/|\?|$)", endpoint)
        if m:
            return [(m.group(1) + "/" + m.group(2)).lower()]
        if re.match(r"^repos/\{owner\}/\{repo\}(/|\?|$)", endpoint):
            return None
        raise Guarded("its endpoint names no repository")
    return None


def candidates(inv, ctx):
    """Every repository the directory a write runs in could resolve to. Raises Guarded."""
    out = []
    for cwd in inv.state.cwds:
        if cwd is None:
            raise Guarded("the directory it runs in cannot be known")
        out += ctx.remotes(cwd)
    env_repo = ctx.environ.get("GH_REPO")
    if env_repo:
        r = repo_of(env_repo)
        if r is None:
            raise Guarded("GH_REPO in the environment does not parse")
        out.append(r)
    for name, value in inv.state.vars.items():
        if name == "GH_REPO":
            r = repo_of(value)
            if r is None:
                raise Guarded("the command sets GH_REPO to a value the hook cannot know")
            out.append(r)
    if not out:
        raise Guarded("the directory it runs in has no remote")
    return sorted(set(out))


def real_remotes(cwd, home, xdg):
    """The repositories of every remote's fetch and push URLs, insteadOf applied, and every
    gh-resolved value naming one. Raises Guarded."""
    import subprocess

    def git(*args):
        try:
            r = subprocess.run(["git", "-C", cwd] + list(args), stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL, env=child_env(home, xdg), timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            raise Guarded("git could not read the remotes")
        return r.returncode, r.stdout.decode("utf-8", "replace")

    code, inside = git("rev-parse", "--is-inside-work-tree")
    if code != 0:
        code, inside = git("rev-parse", "--is-bare-repository")
        if code != 0:
            raise Guarded("the directory it runs in is not in a git repository")
    code, names = git("remote")
    if code != 0:
        raise Guarded("git could not list the remotes")
    out = []
    for name in names.split():
        for args in (("remote", "get-url", "--all", name), ("remote", "get-url", "--push", "--all", name)):
            code, urls = git(*args)
            if code != 0:
                raise Guarded("git could not read a remote's URL")
            for url in urls.split():
                r = repo_of(url)
                if r is None:
                    raise Guarded("a remote's URL names no repository the hook can read")
                out.append(r)
    code, resolved = git("config", "--get-regexp", r"^remote\..*\.gh-resolved$")
    for line in resolved.splitlines():
        value = line.split(" ", 1)[1].strip() if " " in line else ""
        if value and value != "base":
            r = repo_of(value)
            if r is None:
                raise Guarded("a gh-resolved value does not parse")
            out.append(r)
    return out


class ExemptFault(Exception):
    pass


def exempt_path(home, xdg):
    base = xdg if xdg else (home or "") + "/.config"
    return base + "/gate-sdd/leakage-exempt-repositories"


def real_exempt(home, xdg):
    """The exempt entries, as (owner, repo or *), lower-cased. An absent list is empty."""
    path = exempt_path(home, xdg)
    try:
        with open(path, "rb") as f:
            data = f.read(1024 * 1024 + 1)
    except FileNotFoundError:
        return []
    except OSError:
        raise ExemptFault("the exempt list cannot be read")
    if len(data) > 1024 * 1024:
        raise ExemptFault("the exempt list is over 1 MB")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise ExemptFault("the exempt list is not UTF-8")
    entries = []
    for n, line in enumerate(text.splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = re.fullmatch(r"\s*([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+|\*)\s+(\S.*)", line)
        if not m:
            raise ExemptFault("line " + str(n) + " of the exempt list is not `<owner>/<repo>` or"
                              " `<owner>/*` followed by a reason")
        entries.append((m.group(1).lower(), m.group(2).lower()))
    return entries


def is_exempt(repo, entries):
    owner, name = repo.split("/", 1)
    return any(o == owner and (r == "*" or r == name) for o, r in entries)


def target_events(inv, events, environ):
    """Raises Guarded when something earlier in the command, on the invocation or in the
    environment gh runs with changes where gh writes in a way the hook does not follow."""
    for name in environ:
        if name in TARGET_ENV or name.startswith("GIT_CONFIG"):
            raise Guarded("its environment holds " + name)
    if inv.env["clears"] or inv.env["unsets"]:
        raise Guarded("env clears or unsets its environment")
    for name, value in inv.assigns_named:
        if name in TARGET_ENV or name.startswith("GIT_"):
            raise Guarded("it is given " + name)
    for e in inv.state.events + events:
        if e != "assigns GH_REPO":
            raise Guarded("the command runs " + e + " before it")


def placeholders(sources, repos, cwd, ctx):
    """gh expands {owner}, {repo} and {branch} in an api endpoint and its fields."""
    out = []
    for s in sources:
        if not re.search(rb"\{(owner|repo|branch)\}", s.data):
            out.append(s)
            continue
        if len(repos) != 1:
            raise Lost("{owner}, {repo} or {branch}, with more than one repository a candidate")
        owner, name = repos[0].split("/", 1)
        data = s.data.replace(b"{owner}", _bytes(owner)).replace(b"{repo}", _bytes(name))
        if b"{branch}" in data:
            branch = ctx.branch(cwd)
            if branch is None:
                raise Lost("{branch}, in a directory whose branch the hook cannot read")
            data = data.replace(b"{branch}", _bytes(branch))
        out.append(Source(s.label, data))
    return out


def real_branch(cwd, home, xdg):
    import subprocess
    try:
        r = subprocess.run(["git", "-C", cwd, "symbolic-ref", "--short", "HEAD"],
                           stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                           env=child_env(home, xdg), timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.stdout.decode("utf-8", "replace").strip() if r.returncode == 0 else None


# ---------------------------------------------------------------------------------------------
# The guard: one run of check-leakage.sh --text over every source, each starting on a line of
# its own, so its line numbers map back to a source and a line (#361).

class GuardFault(Exception):
    pass


HERE = os.path.dirname(os.path.abspath(__file__))
_REPORT = re.compile(r"^(LEAK|WARNING) \[([a-z -]+)\] input line\(s\): ([0-9 ]+)$")


def guard_path():
    for p in (os.path.join(HERE, "check-leakage.sh"), os.path.join(HERE, "..", "check-leakage.sh")):
        if os.path.isfile(p):
            return p
    return None


def child_env(home, xdg):
    """The environment every process the hook starts gets, built from nothing (#361 AC7)."""
    env = {"PATH": "/usr/bin:/bin",
           "LC_ALL": "en_US.UTF-8" if sys.platform == "darwin" else "C.UTF-8"}
    if home:
        env["HOME"] = home
    if xdg:
        env["XDG_CONFIG_HOME"] = xdg
    return env


def assemble(sources):
    """The text the guard is given, and (first line, line count, label) for each source."""
    chunks = []
    spans = []
    line = 1
    for s in sources:
        data = s.data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        if not data:
            continue
        if not data.endswith(b"\n"):
            data += b"\n"
        count = data.count(b"\n")
        spans.append((line, count, s.label))
        chunks.append(data)
        line += count
    return b"".join(chunks), spans


def locate(numbers, spans):
    out = []
    for n in numbers:
        for first, count, label in spans:
            if first <= n < first + count:
                out.append((label, n - first + 1))
                break
    return out


def real_scan(sources, home, xdg):
    """(hits, warnings), each a list of (tier, label, line). Raises GuardFault."""
    import subprocess
    guard = guard_path()
    if guard is None:
        raise GuardFault("the guard, check-leakage.sh, is not beside the hook")
    data, spans = assemble(sources)
    try:
        p = subprocess.Popen(["/bin/sh", guard, "--text"], stdin=subprocess.PIPE,
                             stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                             env=child_env(home, xdg), cwd="/")
        _, err = p.communicate(data, timeout=15)
    except subprocess.TimeoutExpired:
        p.kill()
        raise GuardFault("the guard did not finish within 15 seconds")
    except OSError as e:
        raise GuardFault("the guard could not be run (" + type(e).__name__ + ")")
    found = {"LEAK": [], "WARNING": []}
    first_fault = None
    for line in err.decode("utf-8", "replace").splitlines():
        m = _REPORT.match(line)
        if m:
            nums = [int(x) for x in m.group(3).split()]
            found[m.group(1)] += [(m.group(2), label, n) for label, n in locate(nums, spans)]
        elif first_fault is None and line.startswith("check-leakage FAILED — "):
            first_fault = line
    if p.returncode == 0:
        return [], found["WARNING"]
    if p.returncode == 1 and found["LEAK"]:
        return found["LEAK"], found["WARNING"]
    raise GuardFault(first_fault[len("check-leakage FAILED — "):] if first_fault and
                     len(first_fault) < 300 else "the guard exited " + str(p.returncode)
                     + " without naming a hit")


def real_gh_version(binary, cwd):
    import shutil
    import subprocess
    if binary.startswith("=/"):
        binary = binary[2:]
    if "/" not in binary:
        binary = shutil.which(binary, path=os.environ.get("PATH", ""))
    elif not binary.startswith("/") and cwd:
        binary = os.path.join(cwd, binary)
    if not binary:
        return None
    try:
        r = subprocess.run([binary, "--version"], stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL, env=child_env(None, None), timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return None
    m = re.match(rb"gh version (\d+)\.(\d+)\.", r.stdout)
    return m.group(1).decode() + "." + m.group(2).decode() if m else None


class Context(object):
    """What decide() reaches outside the command through: the guard, gh's version, the
    remotes of a directory, the exempt list, and the environment gh will run with."""

    def __init__(self, home, xdg=None, scan=None, gh_version=None, remotes=None, exempt=None,
                 environ=None, branch=None):
        self.home = home
        self.xdg = xdg
        self.scan = scan or (lambda sources: real_scan(sources, home, xdg))
        self.gh_version = gh_version or real_gh_version
        self.remotes = remotes or (lambda cwd: real_remotes(cwd, home, xdg))
        self.exempt = exempt or (lambda: real_exempt(home, xdg))
        self.environ = environ if environ is not None else {}
        self.branch = branch or (lambda cwd: real_branch(cwd, home, xdg))


def warning(text):
    return (0, json.dumps({"systemMessage": "gate-sdd gh guard: " + text}), "")


def decide(command, cwd, ctx):
    """The slow path, for a command that holds a gh word."""
    found = Finder(ctx.home, cwd).find(parse(command))
    if found.problems:
        reason = found.problems[0]
        code = re.search(r"can run (what it reads|its arguments|it reads)|into a pipe", reason)
        return block(reason, ADVICE_CODE if code else ADVICE_UNEXPLAINED)
    writes = []
    events = []
    for inv in found.invocations:
        verdict = classify(inv)
        if verdict.result is not None:
            return verdict.result
        if verdict.kind == "local" and verdict.path in ("repo set-default", "config set"):
            events.append("gh " + verdict.path)
        if verdict.kind == "write":
            writes.append((inv, verdict, list(events)))
    if not writes:
        return PASS
    try:
        entries = ctx.exempt()
    except ExemptFault as why:
        return block("The exempt list could not be loaded: " + str(why) + ", so no gh write can"
                     " be told apart.", "Fix " + exempt_path(ctx.home, ctx.xdg) + "; every"
                     " line is `<owner>/<repo>` or `<owner>/*` and a reason.")
    sources = []
    binaries = []
    for inv, verdict, earlier in writes:
        inv.assigns_named = [(n, resolve(w, inv.state)) for n, w, _ in inv.assigns] \
            + list(inv.env["assigns"])
        try:
            target_events(inv, earlier, ctx.environ)
            repos = named(inv, verdict.path, verdict.flags, verdict.positionals, earlier)
            if repos is None:
                repos = candidates(inv, ctx)
            if all(is_exempt(r, entries) for r in repos):
                continue
        except Guarded:
            repos = []
        try:
            got = gather(inv, verdict.path, verdict.flags, verdict.positionals)
            if verdict.path == "api":
                got = placeholders(got, repos, inv.state.cwds[0], ctx)
        except Lost as why:
            return lost(str(why)).result
        sources += got
        binaries.append((inv.binary, inv.state.cwds[0]))
    if not binaries:
        return PASS
    try:
        hits, warnings = ctx.scan(sources) if sources else ([], [])
    except GuardFault as why:
        return block("The guard could not scan what gh would send: " + str(why) + ".",
                     "Fix the guard or its pattern file; the command was not run.")
    if hits:
        where = " ".join("LEAK [" + t + "] in " + label + ", line " + str(n) + "."
                         for t, label, n in hits)
        return block(where + " The matched text is withheld.",
                     "Rewrite the text without it. If this repository may hold it, exempt it"
                     " with a reason in " + exempt_path(ctx.home, ctx.xdg) + ".")
    notes = ["WARNING [" + t + "] in " + label + ", line " + str(n)
             + ": confirm it is a generic example." for t, label, n in warnings]
    for binary, where in binaries:
        version = ctx.gh_version(binary, where)
        if version != TABLE_VERSION:
            notes.append("gh is " + (version or "a version the hook could not read")
                         + ", and the hook's table is gh " + TABLE_VERSION
                         + "'s; regenerate it with scripts/claude-hooks/regenerate-table.py.")
            break
    return warning(" ".join(notes)) if notes else PASS


def run(argv, data):
    if argv:
        return block("The hook was given an argument it does not take, so it looked at nothing.")
    hook = read_input(data)
    if hook is None:
        return block("The hook could not read its input as a PreToolUse event holding a"
                     " command, so it cannot tell what would run.")
    command, cwd = hook
    if not mentions_gh(command):
        return PASS
    return decide(command, cwd, Context(os.environ.get("HOME"), os.environ.get("XDG_CONFIG_HOME"),
                                        environ=dict(os.environ)))
