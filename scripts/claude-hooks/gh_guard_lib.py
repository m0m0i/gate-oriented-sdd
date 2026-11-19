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
ADVICE_STRANGER = ("Run the gh write as a command of its own, or after only cd, assignments, echo,"
                   " printf, cat, tee, test, git and the readers.")
ADVICE_UNEXPLAINED = ("Run gh as a plain command: `gh <subcommand> ...`, by its name or a path that"
                      " ends in /gh, not through a variable, a substitution or a wrapper the hook"
                      " does not list.")


# The fast path: a command passes unread unless `gh` stands as a word once quotes and backslashes
# are taken out: no letter, digit, `_` or `.` before it, and none of those or `-` after it. A gh
# that runs is never next to `.` or followed by `-`, and `${:-gh}` has a `-` before it. No file
# is read and no pattern is loaded before this (#361 AC4).
_GH_WORD = re.compile(r"(?<![A-Za-z0-9_.])gh(?![A-Za-z0-9_.-])")


def mentions_gh(command):
    # A backslash both joins (`g\h` is gh to zsh) and separates (`\ngh` in a printf or $'...'
    # is a newline and gh): the command holds a gh word if either reading finds one.
    unquoted = re.sub(r"[\"']", "", command)
    return _GH_WORD.search(unquoted.replace("\\", "")) is not None \
        or _GH_WORD.search(re.sub(r"\\.?", " ", unquoted)) is not None


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
    __slots__ = ("fd", "op", "target", "heredoc", "pinned", "key")

    def __init__(self, fd, op, target, heredoc=None):
        self.fd = fd
        self.op = op
        self.target = target
        self.heredoc = heredoc
        self.pinned = None   # a compound's standard input, read at entry, or why it is lost
        self.key = None      # the file it opened, and what the walk knew of it at entry


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
_REDIR = re.compile(r"(\d*)(&>>[!|]|&>>|&>[!|]|&>|>>&[!|]?|>>\||>>!|>>|>\||>!|>&[!|]|>&|<&|<>"
                    r"|<<<|<<-|<<|>|<)")
# zsh's clobbering spellings of both streams to a file, as the walk reads them (#361, the fifth
# hunt): `>&!` is `&>`, and `>>&` is `&>>`.
_CLOBBER = {"&>>!": "&>>", "&>>|": "&>>", "&>!": "&>", "&>|": "&>", ">&!": "&>", ">&|": "&>",
            ">>&": "&>>", ">>&!": "&>>", ">>&|": "&>>"}
_ENDS_WORD = " \t\n;&|()<>"
_RESERVED = {"if", "then", "else", "elif", "fi", "for", "while", "until", "do", "done", "case",
             "esac", "select", "repeat", "function", "coproc", "foreach", "end", "]]", "}"}
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
            # In an unquoted here-document zsh joins a line that ends in an odd number of
            # backslashes with the next, and removes the join, before it compares the line
            # with the delimiter: where that ends the body is past this lexer (#361, the fifth
            # hunt).
            if not h.quoted and (len(line) - len(line.rstrip("\\"))) % 2 == 1:
                raise Unsupported("a backslash-newline in an unquoted here-document")
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
                    if self.peek(2) in ("<", ">"):
                        # zsh joins `2\<newline>>f` into the redirection `2>f`.
                        raise Unsupported("a backslash-newline before a redirection")
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
                if self.tilde_here(parts, assignment) == "opaque":
                    parts.append(Part("opaque", s[self.i:j]))
                elif j == self.i + 1 and (j >= len(s) or s[j] in _ENDS_WORD or s[j] == "/"):
                    parts.append(Part("home", "~"))
                elif j == self.i + 1:
                    # zsh takes the prefix after quote removal and expansion: ~\+, ~'-', ~$u
                    # and ~:x are not HOME (#361, the fourth hunt).
                    parts.append(Part("opaque", "~"))
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
        # It still does after an empty quote, '' or "", or an expansion that may be empty:
        # what it expands to then is not read here (#361, the fifth hunt).
        lead = parts
        if assignment and parts[0].kind == "lit" and not parts[0].quoted:
            m = _ASSIGN.match(parts[0].text)
            if m and m.end() == len(parts[0].text):
                lead = parts[1:]
        if lead and all((p.kind == "lit" and p.quoted and p.text == "") or p.kind != "lit"
                        for p in lead):
            return "opaque"
        if assignment and len(parts) == 1 and parts[0].kind == "lit" and not parts[0].quoted:
            return _ASSIGN.fullmatch(parts[0].text) is not None
        # And after an unquoted `:` in an assignment's value (measured, the fourth hunt).
        if assignment and parts[0].kind == "lit" and not parts[0].quoted \
                and _ASSIGN.match(parts[0].text) and parts[-1].kind == "lit" \
                and not parts[-1].quoted and parts[-1].text.endswith(":"):
            return True
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
            if c in "'\"" and open_ == "{":
                # zsh reads a quote inside ${...} by rules of its own, inside double quotes
                # and out of them.
                raise Unsupported("a quote inside ${...}")
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
        if nx == "\\" and self.peek(2) == "\n":
            # zsh removes a backslash-newline before it reads what follows the $.
            raise Unsupported("a `$` before a backslash-newline")
        if nx != "" and ord(nx) > 127:
            # A name zsh reads in a UTF-8 locale and this lexer does not.
            j = self.i + 1
            while j < len(s) and (s[j].isalnum() or s[j] == "_" or ord(s[j]) > 127):
                j += 1
            parts.append(Part("opaque", s[self.i:j], quoted))
            self.i = j
            return
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
            if self.peek() == "\\" and self.peek(1) == "\n":
                raise Unsupported("a name before a backslash-newline")
            if self.peek() != "" and ord(self.peek()) > 127:
                j = self.i
                while j < len(s) and (s[j].isalnum() or s[j] == "_" or ord(s[j]) > 127):
                    j += 1
                parts.append(Part("opaque", "$" + name + s[self.i:j], quoted))
                self.i = j
                return
            # zsh subscripts $NAME[...] and modifies $NAME:h (measured).
            if self.peek() == "[":
                raw = "$" + name + self.balanced("[", "]")
                parts.append(Part("opaque", raw, quoted))
            elif self.peek() == ":" and self.peek(1) != "" and (self.peek(1).isalpha()
                                                                 or self.peek(1) in _MODIFIERS):
                self.i += 2
                parts.append(Part("opaque", "$" + name + s[self.i - 2:self.i], quoted))
            else:
                parts.append(Part("param", name, quoted))
        elif nx != "" and nx in "=~^+" and re.compile(r"[=~^+]+([A-Za-z_{])").match(s, self.i + 1):
            # zsh's $=NAME, $~NAME and $^NAME: NAME's value, split, globbed or brace-expanded;
            # $+NAME, whether it is set.
            m = re.compile(r"[=~^+]+").match(s, self.i + 1)
            start = self.i
            self.i = m.end()
            if self.peek() == "{":
                self.balanced("{", "}")
            else:
                self.i = _NAME.match(s, self.i).end()
            parts.append(Part("opaque", s[start:self.i], quoted))
        elif nx != "" and nx in "=~^":
            # A flag before anything else still takes a parameter: an empty one before a quote,
            # or a special one, $$ or $1 (measured, the fifth hunt). $+ alone stays literal.
            start = self.i
            self.i = re.compile(r"[=~^+]+").match(s, self.i + 1).end()
            if self.peek() != "" and self.peek() in "0123456789#?$!@*-":
                self.i += 1
            parts.append(Part("opaque", s[start:self.i], quoted))
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
                if m.group(4) is not None:
                    code &= 0xff    # zsh keeps the low byte of \NNN
                if code > 0x7f and (m.group(1) is not None or m.group(4) is not None):
                    # A byte, not a character: zsh's word is not UTF-8 text.
                    known = False
                    self.i = m.end()
                    continue
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
        if op in _CLOBBER:
            if fd:
                raise Unsupported("a descriptor before " + op)
            op = _CLOBBER[op]
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
        if self.word_is("[["):
            return self.test_command()
        for keyword in ("if", "while", "until", "for", "function"):
            if self.word_is(keyword):
                self.i += len(keyword)
                return self.compound(keyword)
        assigns = []
        words = []
        redirs = []
        while True:
            self.blanks()
            if re.compile(r"\{[A-Za-z_][A-Za-z0-9_]*\}[<>]").match(self.s, self.i):
                raise Unsupported("a named descriptor, {NAME}> or {NAME}<")
            if re.compile(r"<\d*-\d*>").match(self.s, self.i):
                raise Unsupported("a numeric glob <N-M>")
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
            # The declare family takes NAME=value words as assignments, ~ after the = included,
            # in every word it is given, after noglob, builtin or nocorrect too, but not after
            # `-` (measured, the fifth hunt).
            lead = [x.literal() if not any(p.quoted for p in x.parts) else None for x in words]
            while lead and lead[0] in ("noglob", "builtin", "nocorrect"):
                lead = lead[1:]
            w = self.word(assignment=not words or (
                bool(lead) and lead[0] in ("export", "typeset", "declare", "local", "readonly",
                                           "integer", "float")))
            if w is None:
                break
            if not words and re.match(r"^[A-Za-z_][A-Za-z0-9_]*\[[^\]]*\]\+?=", w.raw):
                raise Unsupported("an array assignment")
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

    def test_command(self):
        """[[ ... ]]: its words, with &&, ||, !, (, ), < and > inside it taken as words."""
        start = self.i
        self.i += 2
        words = [Word([Part("lit", "[[")], "[[", "[[")]
        while True:
            self.blanks()
            if self.word_is("]]"):
                self.i += 2
                words.append(Word([Part("lit", "]]")], "]]", "]]"))
                break
            if self.i >= len(self.s) or self.peek() == "\n":
                raise Unsupported("a `]]` is missing")
            m = re.compile(r"&&|\|\||[!()<>]").match(self.s, self.i)
            if m:
                self.i = m.end()
                words.append(Word([Part("lit", m.group(0))], "\0", m.group(0)))
                continue
            w = self.word()
            if w is None:
                raise Unsupported("a `[[` this hook does not read")
            words.append(w)
        return Simple([], words, self.redirections())

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
            if "{" in name or "}" in name:
                # `function { ... }` runs at once, with scopes of its own (#361, the fifth hunt).
                raise Unsupported("an anonymous function")
            self.blanks()
            if self.peek() not in ("(", "{", "\n", ";", "") and not self.word_is("{"):
                # zsh defines every name before the body.
                raise Unsupported("a function with more than one name")
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

    __slots__ = ("content", "gh", "label", "path")

    def __init__(self, content, gh, label, path=None):
        self.content = content
        self.gh = gh
        self.label = label
        self.path = path     # where it was written, for a file


class State(object):
    """What the walk knows at a point in the command. vars maps a name to its value, None when
    it cannot be known; tainted holds the names whose unknown value was built from a gh word;
    cwds the directories the command may be in, None for one it cannot know; files what the
    command has written so far, by absolute path; named the paths it changed some other way;
    events what it did that changes where a later gh write goes."""

    __slots__ = ("vars", "exported", "tainted", "cwds", "files", "named", "events", "deferred",
                 "optioned", "stdin_unknown", "branches")

    def __init__(self, home, cwd):
        # deferred: no file a later word reads can be known (a program of unknown effect ran, or
        # this is a function's body, which runs where it is called). optioned: shell options or
        # IFS changed, so no later word's expansion can be known. stdin_unknown: `exec <` moved
        # standard input (#361, the second bypass hunt).
        self.deferred = False
        self.optioned = False
        self.stdin_unknown = False
        # branches: the names the current branch may have been given by the command, None
        # among them for one the hook cannot know; empty while it is the hook-time branch.
        self.branches = ()
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
        c.optioned = self.optioned
        c.stdin_unknown = self.stdin_unknown
        c.branches = self.branches
        return c

    def absorb(self, child):
        """Takes from a copy a subshell, a pipeline's earlier command, a background job, a
        substitution or a child shell walked what persists after it: the files it wrote or
        named, now of unknown content, and its events. Its variables and directory do not."""
        for k, text in child.files.items():
            old = self.files.get(k)
            if old is None or old.content != text.content:
                self.files[k] = Text(None, text.gh or (old is not None and old.gh),
                                     "a file a subshell or a child wrote")
        for k, who in child.named.items():
            _tag(self, k, who)
            for f in [f for f in self.files if f not in child.files
                      and (f == k or f.startswith(k.rstrip("/") + "/"))]:
                del self.files[f]
        self.events += [e for e in child.events if e not in self.events]
        self.deferred = self.deferred or child.deferred
        self.branches = self.branches + tuple(b for b in child.branches if b not in self.branches)

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
            for k, who in s.named.items():
                _tag(self, k, who)
            self.events += [e for e in s.events if e not in self.events]
            self.deferred = self.deferred or s.deferred
            self.optioned = self.optioned or s.optioned
            self.stdin_unknown = self.stdin_unknown or s.stdin_unknown
            self.branches = self.branches + tuple(b for b in s.branches if b not in self.branches)
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
            present = [x for x in texts if x is not None]
            first = present[0]
            # An outcome that did not write the file leaves what is on disk; when nothing is
            # there, gh fails to read it there, and sends nothing.
            absent_ok = first.path is not None and not os.path.lexists(first.path) \
                and not any(_fills(s, path) for s, x in zip(states, texts) if x is None)
            if all(x.content == first.content for x in present) and first.content is not None \
                    and (len(present) == len(texts) or absent_ok):
                files[path] = first
            else:
                files[path] = Text(None, any(x is not None and x.gh for x in texts),
                                   "a file this command may write")
        self.files = files

    def env(self):
        env = dict((k, v) for k, v in self.vars.items() if v is not None)
        # zsh sets PWD on every cd, whatever the command assigned it.
        env.pop("PWD", None)
        if len(self.cwds) == 1 and self.cwds[0] is not None:
            env["PWD"] = self.cwds[0]
        return env

    def path(self, value):
        """The absolute path a value names, as the kernel resolves it at hook time (a symlink,
        and a `..` after one, followed), or None when the directory is not known."""
        if value is None:
            return None
        if not value.startswith("/"):
            if len(self.cwds) != 1 or self.cwds[0] is None:
                return None
            value = self.cwds[0] + "/" + value
        return os.path.realpath(value)


def _fold(path):
    """A path as the command's files are keyed: on macOS without case and without Unicode
    normalization, as its volumes compare names."""
    if path is None:
        return None
    if sys.platform != "darwin":
        return path
    import unicodedata
    return unicodedata.normalize("NFD", path).lower()


def _loose(key):
    """A wider fold: two keys that agree here and not in _fold may still be one file."""
    import unicodedata
    return unicodedata.normalize("NFKD", key).casefold()


# Who names a path, by what it may have done there (#361, the fifth hunt): a mode change or a job
# still running outranks a copy, a copy outranks making, touching or removing it, and the later
# of two equal ones is kept.
MODE_TAGS = ("chmod", "chown", "chgrp", "a background job")
EMPTY_TAGS = ("mkdir", "touch", "rm", "rmdir")


def _rank(who):
    return 3 if who in MODE_TAGS else 1 if who in EMPTY_TAGS else 2


def _tag(state, key, who):
    old = state.named.get(key)
    if old is None or _rank(who) >= _rank(old):
        state.named[key] = who


def _moded(state, key):
    """True when a mode change, or a job still running, reached the path or a directory above."""
    if key is None:
        return False
    return any(who in MODE_TAGS and (key == k or key.startswith(k.rstrip("/") + "/"))
               for k, who in state.named.items())


def _fills(state, key):
    """True when a command that may put files there named the path or a directory above it."""
    if key is None:
        return False
    return any(key == k or (key.startswith(k.rstrip("/") + "/") and who not in EMPTY_TAGS)
               for k, who in state.named.items())


def _above(state, key):
    """True when the command named a path under this one, which makes it a directory."""
    return key is not None and any(k.startswith(key.rstrip("/") + "/") for k in state.named)


def _named(state, key):
    """Who named the path or a directory above it earlier in the command, or None."""
    if key is None:
        return None
    for k, who in state.named.items():
        if key == k or key.startswith(k.rstrip("/") + "/"):
            return who
    return None


def _refused(path, state):
    """True when the kernel may refuse an absolute path that _norm reads as text: a part before
    a `..` or a `.` that is not a directory when the hook runs, or that the command names
    (#361, the fifth hunt)."""
    bits = path.split("/")
    for n in range(1, len(bits)):
        if bits[n] in ("..", ".") and bits[n - 1] != "":
            prefix = "/".join(bits[:n]) or "/"
            if not os.path.isdir(prefix) or _named(state, _fold(os.path.realpath(prefix))):
                return True
    return False


def _unfollowed(value, state):
    """The path a value names with its last part not followed, as cp and mv read a link."""
    if not value:
        return None
    head, leaf = os.path.split(value.rstrip("/") or "/")
    parent = state.path(head or ".")
    return None if parent is None else os.path.join(parent, leaf)


def _links(path, state, limit=2000):
    """True unless the path is known to be, and to hold, no symbolic link: on disk when the hook
    runs, unchanged by the command, and small enough to walk."""
    if path is None or _named(state, _fold(path)) or state.deferred:
        return True
    if _fold(path) in state.files:
        return os.path.islink(path)
    if not os.path.lexists(path):
        # Nothing there to copy: cp and mv fail.
        return False
    if os.path.islink(path):
        return True
    if not os.path.isdir(path):
        return False
    seen = 0
    for root, dirs, files in os.walk(path, followlinks=False):
        for n in dirs + files:
            seen += 1
            if seen > limit or os.path.islink(os.path.join(root, n)):
                return True
    return False


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
                 "assigns_named", "background", "strangers")

    def __init__(self, words, assigns, env, redirs, state, piped, simple, binary):
        self.background = False
        self.strangers = []
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
QUIET = {"[[", "echo", "printf", "print", "which", "type", "whence", "where", "man", "grep", "egrep",
         "fgrep", "cat", "ls", "cd", "pwd", "test", "[", "head", "tail", "wc", "mkdir", "touch",
         "rm", "diff", "sort", "uniq", "cut", "basename", "dirname", "realpath",
         "readlink", "stat", "file", "tee", "true", "false", ":", "chmod"}
# Builtins that assign variables the walk cannot follow (read and its relatives), and the ways a
# command changes the shell's state that the walk forgets rather than follows (#361).
ASSIGNERS = {"read", "getopts", "vared", "zparseopts", "let", "typeset", "declare", "local",
             "readonly", "integer", "float", "zstyle"}
_EXPANSION_ASSIGNS = re.compile(r"^\$\{.*?[A-Za-z0-9_\]]:{0,2}=(?!=)", re.S)
_ARITH_ASSIGNS = re.compile(r"(?<![=!<>])=(?!=)|\+\+|--")

# zsh 5.9's builtins (`print -l ${(k)builtins}` under zsh -f), how the walk takes each, and the
# programs whose effect on files it knows: what they name, and their redirections (#361).
ZSH_BUILTINS = set("""- . : [ [[ alias autoload bg bindkey break builtin bye cd chdir command compadd
comparguments compcall compctl compdescribe compfiles compgroups compquote compset comptags
comptry compvalues continue declare dirs disable disown echo echotc echoti emulate enable eval
exec exit export false fc fg float functions getln getopts hash history integer jobs kill let
limit local log logout noglob popd print printf private pushd pushln pwd r read readonly rehash
return sched set setopt shift source suspend test times trap true ttyctl type typeset ulimit
umask unalias unfunction unhash unlimit unset unsetopt vared wait whence where which zcompile
zformat zle zmodload zparseopts zregexparse zstyle""".split())
SAFE_BUILTINS = set(""": [ [[ test echo true false pwd type whence where which wait jobs dirs times
shift exit return break continue kill umask ulimit limit unlimit disown bg fg suspend log logout
bye history echotc echoti ttyctl rehash unhash zcompile alias unalias unfunction hash pushln
print printf builtin noglob command compadd comparguments compcall compctl compdescribe
compfiles compgroups compquote compset comptags comptry compvalues zle bindkey""".split())
VAR_BUILTINS = {"read", "getln", "vared", "getopts", "zparseopts", "zformat", "zregexparse",
                "let", "zstyle"}
# Options that change neither how a word expands nor whether a redirection writes.
SAFE_OPTIONS = {"errexit", "noerrexit", "nounset", "nonounset", "pipefail", "nopipefail",
                "xtrace", "noxtrace", "verbose", "noverbose", "errreturn", "noerrreturn"}
# Names zsh runs by itself when they are functions.
SELF_RUN = re.compile(r"^(TRAP[A-Z]+|chpwd|precmd|preexec|periodic|zshexit|zshaddhistory|"
                      r"command_not_found_handler)$")
# Files tools run by convention, without being named.
CONVENTIONAL = {"makefile", "gnumakefile", "justfile", "package.json", "rakefile",
                "taskfile.yml", "taskfile.yaml", ".envrc", "pre-commit", "pre-push", "commit-msg"}
# Variables programs run as commands.
RUNNER_VARS = {"GIT_SSH_COMMAND", "GIT_SSH", "GIT_EDITOR", "GIT_SEQUENCE_EDITOR", "GIT_PAGER",
               "GIT_ASKPASS", "SSH_ASKPASS", "EDITOR", "VISUAL", "PAGER", "MANPAGER", "LESSOPEN",
               "GH_EDITOR", "GH_BROWSER", "GH_PAGER", "BROWSER", "SHELL", "PROMPT_COMMAND"}
TARGET_VARS = {"HOME", "XDG_CONFIG_HOME", "GH_REPO", "GH_HOST", "GH_CONFIG_DIR", "CDPATH"}
# git subcommands the walk knows, and those of them that rewrite the working tree.
GIT_KNOWN = {"status", "log", "show", "diff", "rev-parse", "ls-files", "grep", "blame", "describe",
             "shortlog", "rev-list", "cat-file", "ls-remote", "symbolic-ref", "for-each-ref",
             "merge-base", "name-rev", "check-ignore", "fetch", "push", "add", "commit", "branch",
             "tag", "notes", "reflog", "gc", "prune", "remote", "config", "checkout", "switch",
             "restore", "reset", "merge", "pull", "rebase", "cherry-pick", "revert", "stash",
             "apply", "am", "clean", "rm", "mv", "worktree", "clone", "init", "submodule",
             "format-patch", "verify-commit", "count-objects", "var", "help", "version"}
GIT_TREE = {"checkout", "switch", "restore", "reset", "merge", "pull", "rebase", "cherry-pick",
            "revert", "stash", "apply", "am", "clean", "rm", "mv", "worktree", "clone", "init",
            "submodule", "format-patch"}

# The commands the walk models exactly. Before a gh write, and anywhere in a command that writes a
# gh word into a file, any other command blocks (#361, the third bypass hunt): what it does to the
# text, the files and the target is past what the walk can follow.
COMPANION_BUILTINS = {"cd", "chdir", "export", "local", "typeset", "declare", "readonly", "integer",
                      "float", "unset", "echo", "printf", "print", "test", "[", "[[", "true", "false",
                      ":", "exit", "return", "set", "wait", "which", "type", "whence", "where",
                      "pwd", "shift", "break", "continue", "noglob", "builtin"}
COMPANION_PROGRAMS = {"cat", "tee", "head", "tail", "wc", "grep", "egrep", "fgrep", "rg", "ls",
                      "mkdir", "rm", "rmdir", "touch", "chmod", "cp", "mv", "ln", "install", "sort",
                      "uniq", "cut", "basename", "dirname", "realpath", "readlink", "date", "jq",
                      "diff", "cmp", "stat", "file", "sleep", "tr", "nl", "column", "fold", "paste",
                      "comm", "md5", "shasum", "sha256sum", "sha1sum", "md5sum", "base64", "od",
                      "xxd", "printenv", "uname", "whoami", "id", "hostname", "seq", "expr", "du",
                      "df", "true", "false", "test", "echo", "printf"}

# Commands that read the files they name and change none of them.
READERS = {"cat", "head", "tail", "wc", "grep", "egrep", "fgrep", "rg", "ls", "test", "[", "[[", "stat",
           "file", "diff", "cd", "pwd", "echo", "printf", "print", "which", "type", "whence",
           "where", "man", "realpath", "readlink", "basename", "dirname", "true", "false", ":",
           "sort", "cut", "cmp", "md5", "shasum", "sha256sum",
           "sha1sum", "md5sum", "od", "nl", "jq", "du", "df", "less", "more", "printenv",
           "comm", "column", "fold", "paste", "tr"}
STDIN_OPS = ("<", "<<", "<<-", "<<<", "<>")
# Programs that write the files their arguments name, and nothing else.
FILE_WRITERS = {"cp", "mv", "ln", "install", "rm", "rmdir", "mkdir", "touch", "rsync", "tar",
                "unzip", "sed", "dd", "tee", "patch", "truncate", "gsed"}
# Programs whose only effect on files is on what they name and their redirections.
KNOWN_PROGRAMS = (FILE_WRITERS | {"cat", "head", "tail", "wc", "grep", "egrep", "fgrep", "rg",
                                  "ls", "stat", "file", "diff", "sort", "uniq", "cut", "basename",
                                  "dirname", "realpath", "readlink", "chmod", "chown", "chgrp",
                                  "sleep", "date", "jq", "env", "printenv", "uname", "whoami",
                                  "id", "hostname", "tr", "nl", "column", "fold", "paste", "comm",
                                  "md5", "shasum", "sha256sum", "base64", "od", "xxd", "less", "cmp", "sha1sum", "md5sum",
                                  "more", "man", "open", "pbcopy", "pbpaste", "say", "true",
                                  "false", "test", "seq", "yes", "expr", "printf", "echo", "tput",
                                  "sw_vers", "which", "type", "du", "df", "find"})
DECLARE = {"export", "typeset", "declare", "local", "readonly", "integer", "float"}
SHELLS = {"sh", "bash", "zsh", "dash", "ksh"}
# The long options bash and zsh take that change nothing the walk reads, alone or with a value.
SHELL_LONG = {"--norc", "--noprofile", "--login", "--posix", "--noediting", "--verbose",
              "--xtrace", "--restricted", "--no-rcs", "--no-globalrcs", "--no-zle", "--help",
              "--version"}
SHELL_LONG_ARG = {"--rcfile", "--init-file"}
# The git subcommands that never run their arguments. `git -c`, `config`, `rebase --exec`,
# `bisect`, `submodule`, `filter-branch`, `difftool` and `mergetool` can, so they are not here.
# The git subcommands that run hooks, or a remote's: once the command has written a gh word
# anywhere, they may run it (#361, the fifth hunt).
GIT_HOOKS = {"commit", "push", "merge", "am", "rebase", "checkout", "switch", "pull", "clone",
             "worktree", "gc", "fetch", "cherry-pick", "revert", "reset", "stash", "apply",
             "notes", "init", "submodule", "restore", "add", "mv", "rm", "status", "diff",
             "log", "show"}
GIT_QUIET = {"status", "log", "show", "diff", "add", "commit", "push", "pull", "fetch",
             "checkout", "switch", "branch", "tag", "remote", "merge", "reset", "restore", "rm",
             "mv", "stash", "worktree", "clone", "init", "rev-parse", "ls-files", "grep", "blame",
             "cherry-pick", "revert", "describe", "shortlog", "reflog", "notes", "apply", "am",
             "format-patch", "rev-list", "cat-file", "ls-remote", "symbolic-ref", "for-each-ref",
             "merge-base", "name-rev", "check-ignore", "gc", "prune", "clean", "rebase"}

# Parameters zsh sets by itself, or ties to another (#361, the fourth hunt): an assignment to one
# is never trusted, since zsh rewrites it on a cd, a set --, a shift, a =~ or any command.
ZSH_SPECIAL = set("""_ PWD OLDPWD argv ARGC MATCH MBEGIN MEND match mbegin mend BASH_REMATCH REPLY
reply status pipestatus RANDOM SECONDS LINENO EPOCHSECONDS EPOCHREALTIME SHLVL PPID UID EUID GID
EGID USERNAME HISTCMD ERRNO OPTARG OPTIND TRY_BLOCK_ERROR ZSH_SUBSHELL ZSH_EVAL_CONTEXT funcstack
funcfiletrace funcsourcetrace functrace PATH path MANPATH manpath FPATH fpath CDPATH cdpath
MAILPATH mailpath PSVAR psvar FIGNORE fignore MODULE_PATH module_path WATCH watch ZSH_ARGZERO
options parameters commands functions aliases builtins jobstates jobtexts history PS1 PS2 PS3
PS4 PROMPT PROMPT2 PROMPT3 PROMPT4 prompt RPS1 RPS2 RPROMPT RPROMPT2 histchars HISTCHARS
TERMINFO_DIRS terminfo_dirs ZSH_EVAL_CONTEXT zsh_eval_context""".split())
# The variables a companion program may be given, or inherit from the command, and still be
# modelled: any other may change what it runs (PERL5OPT, STRIPBIN, GIT_EXTERNAL_DIFF, PATH).
SAFE_ENV = set("""LANG LC_ALL LC_CTYPE LC_COLLATE LC_MESSAGES LC_NUMERIC LC_TIME LC_MONETARY TZ
NO_COLOR CLICOLOR CLICOLOR_FORCE FORCE_COLOR TERM COLUMNS LINES GIT_AUTHOR_NAME GIT_AUTHOR_EMAIL
GIT_AUTHOR_DATE GIT_COMMITTER_NAME GIT_COMMITTER_EMAIL GIT_COMMITTER_DATE GIT_TERMINAL_PROMPT
GIT_OPTIONAL_LOCKS GH_REPO GH_HOST GH_PROMPT_DISABLED GH_NO_UPDATE_NOTIFIER
GH_SPINNER_DISABLED""".split())
# The options a companion program is modelled with: an option word outside its pattern makes it
# a stranger (#361, the fourth hunt). A program not listed here writes nothing and runs nothing,
# whatever its options; sort, base64, uniq and tee name their output, and are listed.
COMPANION_OPTIONS = {
    "cp": r"-[aRrHLPfinpvXcxN]+",
    "mv": r"-[fhinv]+",
    "ln": r"-[FfhinsvwLP]+",
    "install": r"-[cdpvC]+|-m\S*",
    "mkdir": r"-[pv]+|-m\S*",
    "rm": r"-[dfiIPRrvWx]+",
    "rmdir": r"-[pv]+",
    "touch": r"-[acfhm]+|-[rtdA]",
    "tee": r"-[ai]+|--append|--ignore-interrupts",
    "cat": r"-[benstuvl]+",
    "sort": r"-[bdfghiMmnRrsuVcCz]+|-[bdfghiMmnRrsuVcCz]*[ktST].*|--(reverse|numeric-sort|unique"
            r"|ignore-case|version-sort|human-numeric-sort|general-numeric-sort|month-sort"
            r"|random-sort|stable|check|merge|dictionary-order|ignore-leading-blanks"
            r"|zero-terminated|ignore-nonprinting)|--(key|field-separator|buffer-size|parallel"
            r"|temporary-directory)(=.*)?",
    "uniq": r"-[cdiuD]+|-[fs]\d*|--(count|repeated|unique|ignore-case)",
    "base64": r"-[dDh]+|-b\d*|-i\S*|--decode|--break=\d+|--input=\S+",
    "file": r"-[^C-]*|--(brief|mime|mime-type|mime-encoding|no-dereference|dereference)",
    "rg": r"(?!--pre).*",
}
PRECOMMANDS = ("noglob", "builtin", "command", "exec", "-", "nocorrect")
# Their options that write a path the walk does not name: what any file holds after is unknown.
OUTPUT_OPTIONS = {"sort": r"-[^-]*o.*|--o.*", "base64": r"-o.*|--o.*"}


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
    # After env, nohup, nice, timeout, caffeinate, command or exec, the name is an external
    # program even when a builtin has it: `env cd x` changes no shell's directory.
    external = False

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
                    return None, env, external
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
        elif name in ("builtin", "noglob", "nocorrect", "nohup", "time", "-"):
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
    if k > 0:
        external = any(_name(v) in ("env", "nohup", "nice", "timeout", "gtimeout", "caffeinate",
                                    "command", "exec") for v in vals[:k] if v is not None)
    return k, env, external


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


GIT_CONFIG_READS = {"--get", "--get-all", "--get-regexp", "--get-urlmatch", "--get-color",
                    "--get-colorbool", "--list", "-l", "--show-origin", "--show-scope", "--null",
                    "-z", "--name-only", "--bool", "--int", "--bool-or-int", "--path",
                    "--expiry-date", "--local", "--global", "--system", "--worktree", "--includes",
                    "--no-includes"}


def git_companion(vals, seen=None):
    """True for git given a subcommand the walk models, that runs nothing it is given: no -c,
    no --exec-path, no template, no upload or receive pack, and `config` only to read. seen is
    each word, or for one the hook cannot know its literal text when that starts with `-`."""
    seen = seen or vals
    if any(v is not None and re.match(r"--(template|upload-pack|receive-pack|exec|ext-diff"
                                      r"|textconv|config)", v) for v in seen):
        return False
    sub = git_subcommand(vals)
    if not sub or sub not in GIT_KNOWN or "-c" in vals[:vals.index(sub)]:
        return False
    rest = vals[vals.index(sub) + 1:]
    if any(v is None for v in vals[:vals.index(sub)]) or any(
            v.startswith("--exec-path") or v.startswith("--config-env") for v in vals[:vals.index(sub)]):
        return False
    if any(v is not None and (v.startswith("--template") or v.startswith("--upload-pack")
                              or v.startswith("--receive-pack") or v.startswith("--exec")
                              or (sub == "clone" and v == "-u") or v.startswith("--ext-diff")
                              or v.startswith("--textconv") or v.startswith("--config"))
           for v in rest):
        return False
    if sub == "config":
        reads = False
        operands = []
        k = 0
        while k < len(rest):
            v = rest[k]
            if v is None:
                return False
            if v in ("-f", "--file", "--blob", "--type", "--default"):
                k += 2
                continue
            if v.startswith("--file=") or v.startswith("--blob=") or v.startswith("--type=") \
                    or v.startswith("--default="):
                k += 1
                continue
            if v.startswith("-"):
                if v not in GIT_CONFIG_READS:
                    return False
                reads = reads or v.startswith("--get") or v in ("--list", "-l")
            else:
                operands.append(v)
            k += 1
        if operands[:1] in (["get"], ["list"]):
            return True
        if operands[:1] and operands[0] in ("set", "unset", "rename-section", "remove-section",
                                             "edit"):
            return False
        return reads or len(operands) <= 1
    return git_quiet(vals)


def _git_remote_changes(rest):
    """True for a git remote that may change a remote: anything but a listing, show or get-url."""
    operands = _operands(rest)
    return bool(operands) and operands[0] not in ("show", "get-url") or any(
        v is None or v not in ("-v", "--verbose") for v in _options(rest))


def _new_branch(sub, rest):
    """The names the branch may have after git checkout, switch or branch -m: the one -b, -c or
    -m gives, or any word that could be one, and None for one the hook cannot know."""
    names = []
    k = 0
    while k < len(rest):
        v = rest[k]
        if v is None:
            return [None]
        if v == "--":
            break
        if v in ("-b", "-B", "-c", "-C", "--orphan", "-m", "-M", "--move", "--create",
                 "--force-create"):
            if k + 1 >= len(rest) or rest[k + 1] is None:
                return [None]
            names.append(rest[k + 1])
            k += 2
            continue
        if v == "-":
            return [None]
        if not v.startswith("-"):
            names.append(v)
        k += 1
    return names


def _stdin_of(redirs):
    """The redirections of standard input itself, descriptor 0: a here-document or a file on
    descriptor 3 is not gh's standard input, and `0<&3` is (#361, the fourth hunt)."""
    return [r for r in redirs if (r.op in STDIN_OPS or r.op == "<&") and r.fd in ("", "0")]


def _options(vals):
    """The option words before `--`."""
    out = []
    for v in vals:
        if v == "--":
            break
        if v is None or (v.startswith("-") and v != "-"):
            out.append(v)
    return out


def _operands(vals):
    """The words that are not options: every word after `--`, and `-` itself."""
    out = []
    after = False
    for v in vals:
        if not after and v == "--":
            after = True
            continue
        if after or v is None or not v.startswith("-") or v == "-":
            out.append(v)
    return out


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


def _failed(start, run):
    out = run.copy()
    cwds = list(start.cwds) + [c for c in run.cwds if c not in start.cwds]
    out.cwds = tuple(sorted(cwds, key=str))
    return out


def _kernel_refuses(v, state):
    """True when the kernel may refuse a path that realpath reads as text: one ending in `/` or
    `/.`, a `..` or `.` after a part that may not be a directory, or a name or path longer
    than the kernel takes (#361, the fifth hunt)."""
    if v is None:
        return False
    if v.endswith("/") or v.endswith("/.") or len(v.encode("utf-8", "surrogateescape")) >= 1024 \
            or any(len(b.encode("utf-8", "surrogateescape")) > 255 for b in v.split("/")):
        return True
    if v.startswith("/"):
        full = v
    elif len(state.cwds) == 1 and state.cwds[0] is not None:
        full = state.cwds[0] + "/" + v
    else:
        return False
    return _refused(full, state)


def _may_fail(redirs, state):
    """True when zsh may fail to open one of these redirections, and then runs nothing: a
    target that is empty, a directory, not writable, in a directory that does not exist, one a
    chmod or a copy changed, or a path the kernel refuses; a file read from that does not
    exist or cannot be read (#361, the fourth and fifth hunts)."""
    for r in redirs:
        if r.target is None or r.op in (">&", "<&") or r.op == "<<<":
            continue
        v = r.target.literal(state.env())
        q = state.path(v)
        if q is None:
            continue
        k = _fold(q)
        if v == "" or (q != "/dev/null" and os.path.isdir(q)) or _kernel_refuses(v, state) \
                or state.named.get(k) not in (None, "touch", "rm", "rmdir") or _moded(state, k) \
                or _above(state, k):
            return True
        if r.op == "<":
            if k not in state.files and (not os.path.exists(q) or not os.access(q, os.R_OK)):
                return True
            continue
        if q == "/dev/null":
            continue
        if not os.path.isdir(os.path.dirname(q)):
            # Made earlier in the command or not, both outcomes are followed.
            return True
        if os.path.lexists(q) and not os.access(q, os.W_OK):
            return True
    return False


LOOP_LIMIT = 8


def _same(a, b):
    """True when two states know the same."""
    return (a.vars == b.vars and a.cwds == b.cwds and a.tainted == b.tainted
            and set(a.named) == set(b.named) and a.deferred == b.deferred
            and a.optioned == b.optioned and a.stdin_unknown == b.stdin_unknown
            and a.branches == b.branches and a.events == b.events
            and set(a.files) == set(b.files)
            and all((a.files[k].content, a.files[k].gh) == (b.files[k].content, b.files[k].gh)
                    for k in a.files))


def _assigning_print(vals):
    """True when print or printf may be given -v or -z: an option before the first word that is
    not one, or a word the hook cannot know there."""
    for v in vals:
        if v is None:
            return True
        if not v.startswith("-") or v in ("-", "--"):
            return False
        if set("vz") & set(v[1:]):
            return True
    return False


def _runs_word(script, names):
    """True when a command named one of names appears anywhere in the script, after any
    precommand word (`noglob continue`)."""
    for node, _ in script.items:
        for p in node.pipelines:
            for c in p.commands:
                if isinstance(c, Simple):
                    for w in c.words:
                        v = w.literal()
                        if v in names:
                            return True
                        if v not in PRECOMMANDS:
                            break
                if isinstance(c, Group) and _runs_word(c.body, names):
                    return True
                if isinstance(c, Compound) and any(
                        (cond is not None and _runs_word(cond, names)) or _runs_word(body, names)
                        for cond, body in c.parts):
                    return True
    return False


def _vanishes(word):
    """True when the word is unquoted expansions alone, which zsh drops when they are empty."""
    return all(not p.quoted and p.kind != "lit" for p in word.parts) and bool(word.parts)


GH_STORES = {("config", "set"), ("alias", "set"), ("alias", "import"), ("extension", "install"),
             ("extension", "upgrade")}
GH_LOCAL = {("release", "download"), ("run", "download"), ("repo", "clone"), ("gist", "clone"),
            ("attestation", "download"), ("pr", "checkout"), ("repo", "sync"), ("repo", "read-file"),
            ("artifact", "download"), ("issue", "develop"), ("skill", "install"),
            ("skill", "update"), ("extension", "install"), ("extension", "upgrade"),
            ("repo", "create"), ("repo", "fork"), ("codespace", "cp"), ("cache", "download")}


def gh_writes_locally(vals):
    """True for the gh commands that may write files here: downloads, clones and checkouts,
    wherever global flags put their words (#361, the fourth hunt)."""
    if None in vals:
        return True
    words = [v for v in vals if not v.startswith("-")]
    return "co" in words[:3] or any(p in GH_LOCAL for p in zip(words, words[1:]))


def _either(a, b):
    """What is known after either of two states, either of which may be None (cannot happen)."""
    if a is None:
        return b
    if b is None:
        return a
    out = a.copy()
    out.merge([b])
    return out


def own_text(word):
    """A word's text with its substitutions left out: they are walked as commands of their own."""
    return "".join(p.text if p.kind == "lit" else _source(p) for p in word.parts
                   if p.kind not in ("cmdsub", "procsub"))


class Finder(object):
    def __init__(self, home, cwd, environ=None):
        self.environ = environ or {}
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
        for p in word.parts:
            if p.kind == "opaque":
                for n in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", p.text):
                    v = state.vars.get(n)
                    if n in state.tainted or (v is not None and mentions_gh(v)):
                        return True
        v = self.value(word, state)
        return v is not None and mentions_gh(v)

    def substitutions(self, word, state):
        # A substitution runs before the command holding it, in a subshell of its own.
        for p in word.parts:
            if p.kind in ("cmdsub", "procsub"):
                sub = state.copy()
                self.walk(p.script, sub)
                state.absorb(sub)

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
                job = state.copy()
                marks = len(self.invocations)
                self.andor(node, job)
                for inv in self.invocations[marks:]:
                    inv.background = True
                state.absorb(job)
                for k in list(job.files) + list(job.named):
                    state.named[k] = "a background job"
            else:
                self.andor(node, state)
        if script.unsupported is not None:
            self.stranger(script.unsupported[1])
        if script.unsupported is not None and not mentions_gh(script.unsupported[0]) and any(
                n in state.tainted or mentions_gh(state.vars.get(n) or "")
                for n in re.findall(r"\$\{?([A-Za-z_][A-Za-z0-9_]*)", script.unsupported[0])):
            self.problem("The hook does not read " + script.unsupported[1] + ", and a variable"
                         " used there holds a gh word.")
        if script.unsupported is not None and mentions_gh(script.unsupported[0]):
            self.problem("The hook does not read " + script.unsupported[1]
                         + ", and the command holds a gh word there or after it.")
        return state

    def andor(self, node, state):
        # zsh runs `a && b || c` left to right: a pipeline after `&&` runs when the list so far
        # succeeded, one after `||` when it failed. Both outcomes are followed: ok is what is
        # known when the list so far succeeded, failed when it failed, None when it cannot be
        # (an exit). A pipeline that fails keeps what it assigned and wrote, and a cd in it may
        # not have moved: failed holds both directories.
        ok = state.copy()
        self.pipeline(node.pipelines[0], ok)
        failed = _failed(state, ok)
        if node.pipelines[0].bang:
            # `! p` succeeds when p fails (#361, the fifth hunt).
            ok, failed = failed, ok
        if self.exits(node.pipelines[0]):
            ok = failed = None
        for op, p in zip(node.ops, node.pipelines[1:]):
            start = ok if op == "&&" else failed
            if start is None:
                continue
            run = start.copy()
            self.pipeline(p, run)
            if self.exits(p):
                new_ok = new_failed = None
            else:
                new_ok = run
                new_failed = _failed(start, run)
                if p.bang:
                    new_ok, new_failed = new_failed, new_ok
            if op == "&&":
                ok, failed = new_ok, _either(failed, new_failed)
            else:
                ok, failed = _either(ok, new_ok), new_failed
        outcomes = [s for s in (ok, failed) if s is not None]
        if outcomes:
            first = outcomes[0]
            first.merge(outcomes[1:])
            self.adopt(state, first)

    def exits(self, pipeline):
        last = pipeline.commands
        if len(last) != 1 or not isinstance(last[0], Simple) or not last[0].words:
            return False
        word = last[0].words[0].literal()
        # exit with more than one argument, or a redirection that fails, does not exit.
        return word in ("exit", "return") and word not in self.functions \
            and len(last[0].words) <= 2 and not last[0].redirs

    def pipeline(self, pipeline, state):
        n = len(pipeline.commands)
        marks = len(self.problems), len(self.quiet_gh)
        stages = []
        for k, command in enumerate(pipeline.commands):
            # Every command of a pipeline but the last runs in a subshell, all at once.
            here = state if k == n - 1 else state.copy()
            before = (dict(here.files), dict(here.named))
            first = len(self.invocations)
            self.command(command, here, piped=k > 0, downstream=k < n - 1)
            wrote = here.files != before[0] or here.named != before[1]
            stages.append((self.invocations[first:], wrote))
            if here is not state:
                state.absorb(here)
        if n > 1:
            for j, (invs, _) in enumerate(stages):
                if any(w for i, (_, w) in enumerate(stages) if i != j):
                    for inv in invs:
                        inv.background = True
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
            k, _, _ = unwrap(vals)
        except Unknown:
            return False
        if k is None or k >= len(vals):
            return True
        name = vals[k]
        return name is not None and (is_gh(name) or self.quiet(name, vals[k + 1:]))

    def quiet(self, name, args):
        if self.aliased:
            return False
        base = _name(name)
        if base in self.functions or name in self.functions:
            return False
        if base == "git":
            return git_quiet(args)
        if base == "rg":
            return not any(a is None or a.startswith("--pre") for a in args)
        return base in QUIET

    def command(self, command, state, piped, downstream):
        redirs = command.redirs
        if _may_fail(redirs, state):
            # zsh runs nothing when a redirection fails to open: both outcomes are followed.
            start = state.copy()
            self.command_(command, state, piped, downstream)
            out = state.copy()
            out.merge([start])
            self.adopt(state, out)
            return
        self.command_(command, state, piped, downstream)

    def command_(self, command, state, piped, downstream):
        if isinstance(command, Compound):
            if self.expansion_assigns([r.target for r in command.redirs]
                                      + [r.heredoc.word for r in command.redirs if r.heredoc]):
                self.forget(state)
            self.redirect_targets(command.redirs, state)
            entry = state.copy()
            own = [self.pin(r, entry) for r in _stdin_of(command.redirs)]
            self.opens(command.redirs, state, entry)
            self.stdin.append((own, piped))
            try:
                self.compound(command, state)
            finally:
                self.stdin.pop()
            self.writes(Simple([], [], command.redirs), None, state, [], at=entry)
            return
        if isinstance(command, Group):
            if self.expansion_assigns([r.target for r in command.redirs]
                                      + [r.heredoc.word for r in command.redirs if r.heredoc]):
                self.forget(state)
            inner = state if command.kind == "group" else state.copy()
            self.redirect_targets(command.redirs, inner)
            entry = inner.copy()
            # A group's standard input is every command's in it that has none of its own.
            own = [self.pin(r, entry) for r in _stdin_of(command.redirs)]
            self.opens(command.redirs, inner, entry)
            if inner is not state:
                self.opens(command.redirs, state, entry)
            self.stdin.append((own, piped))
            try:
                self.walk(command.body, inner)
            finally:
                self.stdin.pop()
            if inner is not state:
                state.absorb(inner)
            self.writes(Simple([], [], command.redirs), None, state, [], at=entry)
            return
        self.simple(command, state, piped, downstream)

    def compound(self, c, state):
        if c.kind == "for" and self.expansion_assigns(c.words or []):
            self.forget(state)
        if c.kind == "function":
            self.functions.add(c.var)
            if SELF_RUN.match(c.var or ""):
                # zsh runs it by itself, at any later point: anything may change.
                self.forget(state, cwd=True, files=True)
                state.optioned = True
                state.events.append("a function zsh runs by itself (" + c.var + ")")
            # Walked where it is defined, as if it ran there with nothing about the call known.
            body = state.copy()
            body.vars = dict((n, None) for n in state.vars)
            if self.home:
                body.vars["HOME"] = self.home
            body.cwds = (None,)
            body.deferred = True
            body.stdin_unknown = True
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
        # it changed.
        loop = state.copy()
        if c.kind == "for":
            for w in c.words or []:
                self.substitutions(w, loop)
            values = [w.literal(loop.env()) for w in c.words or []]
            if c.words and None not in values and len(values) <= 32 \
                    and not _runs_word(c.parts[0][1], ("break", "continue")):
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
        # Walked until what it knows stops changing: each run starts from what any run before
        # it may leave. A while or until loop leaves after its condition fails, so its outcome
        # is the condition's, run from there (#361, the fourth hunt).
        cond, body = c.parts[0]
        exits = None
        for n in range(LOOP_LIMIT + 1):
            here = loop.copy()
            if cond is not None:
                self.walk(cond, here)
            exits = here.copy()
            self.walk(body, here)
            nxt = loop.copy()
            nxt.merge([here])
            if _same(nxt, loop):
                break
            if n == LOOP_LIMIT - 1:
                # It has not settled: what any run touches is unknown, and one more run from
                # there finds the gh commands it may run.
                self.forget(nxt, cwd=True, files=True)
            loop = nxt
        if cond is not None:
            loop = exits
        if any(_runs_word(body, ("break", "continue")) or (cond is not None and
                                                             _runs_word(cond, ("break", "continue")))
               for cond, body in c.parts):
            # A run cut short leaves any value or file the body was part way through.
            self.forget(loop, files=True)
        merged = state.copy()
        merged.merge([loop])
        self.adopt(state, merged)

    def pin(self, r, entry):
        """A compound's standard input as zsh opens it, once, before the body runs: its text from
        the state at entry, or why it is lost (#361, the fifth hunt)."""
        out = Redir(r.fd, r.op, r.target, r.heredoc)
        out.pinned = None
        out.key = None
        try:
            out.pinned = stream(r, entry)
        except Lost as why:
            out.pinned = why
        if r.op in ("<", "<>") and r.target is not None:
            v = resolve(r.target, entry)
            p = entry.path(v) if v is not None else None
            if p is not None:
                k = _fold(p)
                out.key = (k, entry.files.get(k), entry.named.get(k), entry.deferred)
        return out

    def opens(self, redirs, state, entry):
        """zsh opens a compound's output redirections, and empties those it truncates, before
        the body runs: in the body, what they hold is unknown (#361, the fifth hunt)."""
        for r in redirs:
            if r.target is None or not (r.op.startswith(">") or r.op.startswith("&>") or r.op == "<>"):
                continue
            v = r.target.literal(entry.env())
            if r.op in (">&", "<&") and v is not None and (v.isdigit() or v == "-"):
                continue
            p = entry.path(v)
            if p is None:
                state.deferred = True
                continue
            if p == "/dev/null":
                continue
            k = _fold(p)
            old = state.files.get(k)
            state.files[k] = Text(None, old is not None and old.gh,
                                  "a file a compound's redirection opens", p)

    def adopt(self, state, other):
        for name in State.__slots__:
            setattr(state, name, getattr(other, name))

    def inherited_stdin(self, redirs, piped):
        own = _stdin_of(redirs)
        for outer, outer_piped in reversed(self.stdin):
            piped = piped or outer_piped
            if not own:
                own = outer
        return own, piped

    def redirect_targets(self, redirs, state):
        for r in redirs:
            if r.target is not None:
                self.substitutions(r.target, state)

    def forget(self, state, vars_=True, cwd=False, files=False):
        """What a command did to the shell's state that the walk cannot follow: the variables
        but HOME become unknown, the directory unknown, and every file a later word reads."""
        if vars_:
            for n in list(state.vars):
                if n != "HOME":
                    state.vars[n] = None
        if cwd:
            state.cwds = (None,)
        if files:
            state.deferred = True

    def expansion_assigns(self, words, state=None):
        # ${N:=w}, ${N=w}, ${N::=w}, $((N=1)), $[N=1] and a subscript, $x[N=1], assign while
        # they expand; so does arithmetic over a name whose value is an expression.
        for w in words:
            if w is None:
                continue
            for p in w.parts:
                if p.kind != "opaque":
                    continue
                if _EXPANSION_ASSIGNS.match(p.text):
                    return True
                arith = p.text.startswith("$((") or p.text.startswith("$[")
                k = p.text.find("[")
                if (arith and _ARITH_ASSIGNS.search(p.text)) \
                        or (k >= 0 and _ARITH_ASSIGNS.search(p.text[k:])):
                    return True
        return False

    def arith_assigns(self, words, state):
        """True when arithmetic in these words runs over a name whose value is an expression,
        which may assign any variable, or one the hook cannot know."""
        for w in words:
            for p in (w.parts if w is not None else []):
                if p.kind == "opaque" and (p.text.startswith("$((") or p.text.startswith("$[")) \
                        and self.arith_names(p.text, state):
                    return True
        return False

    def arith_names(self, text, state):
        """True when arithmetic over this text may assign: a name in it holds anything but a
        number, or cannot be known."""
        for n in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", text):
            v = state.vars.get(n)
            if v is None or not re.fullmatch(r"\s*-?\d+\s*", v):
                return True
        return False

    def simple(self, cmd, state, piped, downstream):
        for _, w, _ in cmd.assigns:
            self.substitutions(w, state)
        for w in cmd.words:
            self.substitutions(w, state)
        self.redirect_targets(cmd.redirs, state)
        streams = [(r, self.heredoc_text(r, state)) for r in cmd.redirs if r.op in ("<<", "<<-", "<<<")]
        if self.expansion_assigns([w for _, w, _ in cmd.assigns] + list(cmd.words)
                                  + [r.target for r in cmd.redirs]
                                  + [r.heredoc.word for r in cmd.redirs if r.heredoc is not None]):
            # It may assign zsh's options array, or any variable by name: later words too.
            self.forget(state)
            state.optioned = True
        elif self.arith_assigns(list(cmd.words) + [w for _, w, _ in cmd.assigns]
                                + [r.target for r in cmd.redirs], state):
            self.forget(state)
        for w in list(cmd.words) + [x for _, x, _ in cmd.assigns] \
                + [r.target for r in cmd.redirs if r.target is not None] \
                + [r.heredoc.word for r in cmd.redirs if r.heredoc is not None and r.heredoc.word]:
            for part in w.parts:
                if part.kind == "opaque" and (mentions_gh(part.text) or any(
                        n in state.tainted or mentions_gh(state.vars.get(n) or "")
                        for n in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", part.text))):
                    # An expansion the hook does not read may hold a substitution that runs gh.
                    self.problem("A gh word is inside an expansion the hook does not read, so it"
                                 " cannot tell what the command runs.")

        # zsh drops a word that is only unquoted expansions and expands to nothing.
        pairs = [(w, self.value(w, state)) for w in cmd.words]
        pairs = [(w, v) for w, v in pairs if not (v == "" and _vanishes(w))]
        words = [w for w, _ in pairs]
        vals = [v for _, v in pairs]
        if not words:
            # Only assignments, or words that all expanded to nothing: the assignments persist.
            for name, w, appends in cmd.assigns:
                self.assign(name, w, appends, state, export=False)
            self.writes(cmd, None, state, streams)
            return
        if vals[0] is None and _vanishes(words[0]):
            # It may expand to nothing, which makes its assignments the shell's.
            for name, _, _ in cmd.assigns:
                state.vars[name] = None
        for v in vals:
            # A function named like a precommand word runs in its place (#361, the fourth hunt).
            if v is None or v not in PRECOMMANDS:
                break
            if v in self.functions:
                self.check_words(words, state, quiet=False)
                self.forget(state, cwd=True, files=True)
                self.stranger(v)
                return

        try:
            k, env, external = unwrap(vals)
        except Unknown as why:
            self.problem("The hook cannot read " + str(why) + ", so it cannot tell what the"
                         " command runs.")
            return
        if k is None:
            return
        if k >= len(vals):
            # env alone, and the like: it prints, and runs nothing. `exec` with redirections
            # alone moves the shell's own standard input and output for every later command.
            self.check_words(words, state, quiet=True)
            if not external:
                # `F=x noglob` and `F=x builtin` run nothing, so their assignments persist.
                for aname, w, appends in cmd.assigns:
                    self.assign(aname, w, appends, state, export=False)
            if any(x.gh for _, x in streams):
                self.problem("A gh word is in a here-document exec opens for later commands, so"
                             " the hook cannot tell what reads it.")
            if vals and vals[0] == "exec" and cmd.redirs:
                if any(r.op in STDIN_OPS or r.op == "<&" for r in cmd.redirs):
                    state.stdin_unknown = True
                if any(r.op not in STDIN_OPS for r in cmd.redirs):
                    self.forget(state, vars_=False, files=True)
            return
        name = vals[k]
        if name is None:
            # It cannot be gh unless a gh word is in it, or it runs a file the command wrote
            # that holds one. It may be a function, cd, read or source: everything is unknown.
            if any(self.has_gh(w, state) for w in words) or any(x.gh for _, x in streams) \
                    or any(t.gh for t in state.files.values()):
                self.problem("A command's name cannot be known before it runs, so the hook"
                             " cannot tell what it runs.")
                return
            self.forget(state, cwd=True, files=True)
            state.events.append("a command whose name cannot be known")
            self.stranger("a command whose name cannot be known")
            self.writes(cmd, None, state, streams)
            return
        base = _name(name)
        args = words[k + 1:]
        rest = vals[k + 1:]
        if is_gh(name):
            # The words after gh are what it sends; reading them is the classifier's work.
            stdin, piped = self.inherited_stdin(cmd.redirs, piped)
            inv = Invocation(args, list(cmd.assigns), env, stdin, state.copy(), piped, cmd, name)
            inv.strangers = list(self.strangers)
            self.invocations.append(inv)
            self.check_words(words[:k], state, quiet=True)
            for aname, w, _ in cmd.assigns:
                if self.has_gh(w, state):
                    self.problem("A gh word is in an assignment before gh, " + aname + ", which gh"
                                 " may run (a browser, a pager or an editor), so the hook cannot"
                                 " tell what the command runs.")
            plain = [v for v in rest if v is not None and not v.startswith("-")]
            if any(p in GH_STORES for p in zip(plain, plain[1:])):
                # What it stores, gh runs later: an editor, a browser, a pager or an alias.
                self.stranger("gh " + " ".join(next(p for p in zip(plain, plain[1:])
                                                    if p in GH_STORES)))
                if any(self.has_gh(w, state) for w in args):
                    self.problem("A gh word is in what gh stores for a later gh to run, so the"
                                 " hook cannot tell what the command runs.")
            self.writes(cmd, None, state, [])
            if gh_writes_locally(rest):
                self.forget(state, vars_=False, files=True)
            return
        # An assignment before any command but gh that holds a gh word may be how it runs gh:
        # GIT_SSH_COMMAND, EDITOR, PAGER.
        for _, w, _ in cmd.assigns:
            if self.has_gh(w, state):
                self.problem("A gh word is in an assignment before " + base + ", which may run"
                             " it, so the hook cannot tell what the command runs.")
        for _, v in env.get("assigns", []):
            if v is not None and mentions_gh(v):
                self.problem("A gh word is in an assignment env gives " + base + ", which may run"
                             " it, so the hook cannot tell what the command runs.")
        if not self.companion(name, base, rest, external, state, cmd, env,
                              [w.plain() for w in args]):
            self.stranger(base)
            # A command the walk does not model is given a gh word only to run it, or to write
            # it where something may: its words, its input and its substitutions included.
            if not self.quiet(name, rest) and (any(self.has_gh(w, state) for w in words[k + 1:])
                                               or any(x.gh for _, x in streams)
                                               or any(r.target is not None and self.has_gh(r.target, state)
                                                      for r in cmd.redirs)):
                self.problem("A gh word is given to " + base + ", which the hook does not"
                             " follow, so it cannot tell what the command runs.")
        if not external and (name in self.functions or base in self.functions):
            # A function defined in the command runs in this shell: it may set any variable,
            # change the directory and write any file.
            self.check_words(words, state, quiet=False)
            self.forget(state, cwd=True, files=True)
            return
        builtin = not external and "/" not in name and base in ZSH_BUILTINS
        if builtin:
            if self.builtin(base, cmd, words, k, rest, state, streams):
                return
        elif base in SHELLS:
            self.shell(cmd, args, rest, state, streams, piped, env)
            return
        elif "/" in name:
            self.runs_file(state.path(name), state, cmd, env)
            if _fold(state.path(name)) not in state.files:
                self.unknown_program(state, base)
            else:
                base = ""   # read already, as a script
        elif base == "git":
            if any(n.startswith("GIT_CONFIG") or n in RUNNER_VARS for n, _, _ in cmd.assigns) \
                    and any(x.gh for x in state.files.values()):
                self.problem("A file the command wrote holds a gh word, and git, through the"
                             " configuration it is given, can run it.")
            self.git(rest, state, [w.plain() for w in args])
        elif base not in KNOWN_PROGRAMS:
            self.unknown_program(state, base)
        quiet = self.quiet(name, rest)
        self.check_words(words, state, quiet)
        for r, text in streams:
            if text.gh and not quiet:
                self.problem("A gh word is in " + text.label + " that " + base
                             + " reads, and it can run what it reads.")
            elif text.gh:
                self.quiet_gh.append(text.label)
        if not quiet and not builtin and base and base not in KNOWN_PROGRAMS:
            self.runs_written(state, base)
        # What earlier commands named decides whether this one's writes may fail; its own
        # files, tee's, are named for later commands.
        before = state.copy()
        self.names_files(base, quiet, rest, state)
        self.writes(cmd, (base, rest), state, streams, piped, at=before)

    def companion(self, name, base, rest, external, state, cmd, env, raws=None):
        """True for a command the walk models exactly: a companion builtin, or a companion
        program given only the options it is modelled with, no variable that may change what
        it runs, and found on a PATH the command has not changed (#361, the fourth hunt)."""
        if external or "/" in name or name in self.functions or base in self.functions:
            return False
        if base in ZSH_BUILTINS and base != "git":
            return base in COMPANION_BUILTINS
        if base != "git" and base not in COMPANION_PROGRAMS:
            return False
        if "assigns PATH" in state.events:
            return False
        given = [n for n, _, _ in cmd.assigns] + [n for n, _ in env.get("assigns", [])]
        given += [n for n in state.exported if n != "HOME"]
        if state.vars.get("HOME", self.home) != self.home or any(
                "allexport" in e or e == "set -a" for e in state.events):
            return False
        if any(n not in SAFE_ENV and not (re.fullmatch(r"[a-z_][a-z0-9_]*", n)
                                           and n not in ZSH_SPECIAL) for n in given):
            return False
        # A word the hook cannot know is read by its own text: what it starts with is literal.
        seen = [v if v is not None else (r if r and r.startswith("-") else None)
                for v, r in zip(rest, raws or [None] * len(rest))]
        if base == "git":
            return git_companion(rest, seen)
        pattern = COMPANION_OPTIONS.get(base)
        if pattern is None:
            return True
        for v in seen:
            if v is None:
                continue
            if v == "--":
                break
            if v.startswith("-") and v != "-" and not re.fullmatch(pattern, v) \
                    and not re.fullmatch(OUTPUT_OPTIONS.get(base, "(?!)"), v):
                return False
        return True

    def test_arith(self, vals, state):
        """[[ evaluates the operands of -eq and the rest as arithmetic, which may assign."""
        for j, v in enumerate(vals):
            if v not in ("-eq", "-ne", "-lt", "-le", "-gt", "-ge"):
                continue
            for o in (vals[j - 1] if j > 0 else None, vals[j + 1] if j + 1 < len(vals) else None):
                if o is None or not (re.fullmatch(r"\s*-?\d+\s*", o) or (
                        _NAME.fullmatch(o) and re.fullmatch(r"\s*-?\d+\s*",
                                                            state.vars.get(o) or "x"))):
                    self.forget(state)
                    return

    def stranger(self, what):
        if what not in self.strangers:
            self.strangers.append(what or "a command")

    def unknown_program(self, state, base):
        # A program whose effect on files the walk does not know may change any of them, and
        # the configuration that decides where gh writes.
        state.deferred = True
        event = "a program the hook does not follow (" + (base or "?") + ")"
        if event not in state.events:
            state.events.append(event)

    def runs_written(self, state, base):
        # A file the command wrote that holds a gh word, run by a command that runs files by
        # convention: a build file, a git hook, a script with a shebang (#361, second hunt).
        for key, text in state.files.items():
            if not text.gh:
                continue
            leaf = key.rsplit("/", 1)[-1]
            if leaf in CONVENTIONAL or "/.git/hooks/" in key or "/hooks/" in key \
                    or (text.content or "").startswith("#!") or text.content is None:
                self.problem("A file the command wrote holds a gh word, and " + base
                             + " can run it.")
                return

    def builtin(self, base, cmd, words, k, rest, state, streams):
        """A zsh builtin's effect on what the walk tracks. Returns True when it is done."""
        if base in DECLARE:
            self.declare(base, words[k + 1:], rest, state, precommand=k > 0)
            return True
        if base == "[[":
            self.test_arith(rest, state)
        if base in ("cd", "chdir"):
            self.cd(rest, state, [n for n, _, _ in cmd.assigns])
        elif base in ("pushd", "popd"):
            self.forget(state, vars_=False, cwd=True)
        elif base == "eval":
            self.eval_(cmd, rest, state, words)
            return True
        elif base in ("source", "."):
            self.source(rest[0] if rest else None, cmd, state)
            return True
        elif base == "unset":
            for v in rest:
                if v is None:
                    self.forget(state)
                    state.events.append("unset of a variable it cannot know")
                    continue
                state.vars.pop(v, None)
                if v.startswith("GH_") or v.startswith("GIT_") or v in TARGET_VARS:
                    state.events.append("unset of " + v)
                if v == "IFS":
                    state.optioned = True
        elif base in ("set", "setopt", "unsetopt", "emulate"):
            self.options(base, rest, state)
        elif base in VAR_BUILTINS or (base in ("print", "printf") and _assigning_print(rest)):
            self.forget(state)
            for v in rest:
                if v is not None and _NAME.fullmatch(v):
                    state.vars[v] = None
                if v is None or "[" in v or v.startswith("options"):
                    state.optioned = True
        elif base == "alias" and rest:
            # Read when the line is run, not when this command is: every later name may differ.
            self.aliased = True
            state.optioned = True
        elif base in SAFE_BUILTINS:
            pass
        else:
            # trap, sched, zmodload, enable, functions, autoload, fc and any builtin the walk
            # does not model: code may run later, or anything may change.
            self.forget(state, cwd=True, files=True)
            state.events.append(base + ", whose effect the hook does not follow")
        return False

    def options(self, base, vals, state):
        # Shell options change how every later word expands, and noclobber whether a `>`
        # writes: any but a few the walk knows to change neither makes later writes unknown.
        names = []
        k = 0
        while k < len(vals):
            v = vals[k]
            if v is None:
                state.optioned = True
                return
            if base == "set":
                if v in ("-o", "+o"):
                    names.append(vals[k + 1] if k + 1 < len(vals) else None)
                    k += 2
                    continue
                if v == "--" or not (v.startswith("-") or v.startswith("+")):
                    break
                letters = v[1:]
                if "o" in letters:
                    # -o in a cluster takes the next word as an option's name.
                    names.append(vals[k + 1] if k + 1 < len(vals) else None)
                    letters = letters.replace("o", "")
                    k += 1
                if "A" in letters:
                    self.forget(state)
                    target = vals[k + 1] if k + 1 < len(vals) else None
                    if target is not None:
                        state.vars[target] = None
                    if target is None or target.endswith("_functions") or target == "options":
                        # zsh's hook arrays and its options array change what runs and expands.
                        state.optioned = True
                        self.forget(state, cwd=True, files=True)
                    return
                if "a" in letters:
                    state.events.append("set -a")
                if set(letters) - set("euxva"):
                    state.optioned = True
                k += 1
                continue
            if base == "emulate":
                state.optioned = True
                return
            names.append(("no" + v) if base == "unsetopt" else v)
            k += 1
        for n in names:
            norm = (n or "").lower().replace("_", "").replace("-", "")
            if norm in ("allexport",):
                state.events.append(base + " allexport")
            if norm not in SAFE_OPTIONS:
                state.optioned = True

    def git(self, vals, state, raws=None):
        sub = git_subcommand(vals)
        if sub is None or sub in GIT_HOOKS or sub not in GIT_KNOWN:
            self.runners.append("git " + (sub or "?"))
        for j, v in enumerate(vals):
            if sub and v == sub:
                break
            if v == "-c":
                c = vals[j + 1] if j + 1 < len(vals) else None
                if c is None or re.match(r"(alias|include|includeif|core\.hookspath|remote|url)\.",
                                         c, re.I):
                    state.events.append("git -c that changes what git runs or where it goes")
        if not sub or sub not in GIT_KNOWN or any("git -c" in e for e in state.events) \
                or any(n.startswith("GIT_CONFIG") for n in state.vars):
            if any(t.gh for t in state.files.values()):
                self.problem("A file the command wrote holds a gh word, and git, through an alias"
                             " or a config it is given, can run it.")
        if sub == "grep" and any(v is None or v.startswith("-O") or v.startswith("--open-files")
                                 for v in vals):
            self.stranger("git grep -O")
            self.unknown_program(state, "git grep -O")
        if not sub or sub not in GIT_KNOWN:
            self.unknown_program(state, "git " + (sub or "?"))
        elif sub == "config" and not git_companion(vals):
            state.events.append("git config")
        elif sub == "remote" and _git_remote_changes(vals[vals.index(sub) + 1:]):
            state.events.append("git remote")
        elif sub in GIT_TREE:
            self.forget(state, vars_=False, files=True)
        rest = vals[vals.index(sub) + 1:] if sub in vals else []
        seen = [v if v is not None else r for v, r in zip(vals, raws or [None] * len(vals))]
        seen = seen[vals.index(sub) + 1:] if sub in vals else []
        if any(v is not None and (v.startswith("--ou") or (sub == "config" and (
                v in ("-f", "--file") or v.startswith("--file=")))) for v in seen):
            # --output=FILE, and config --file FILE, write a file the walk does not name.
            self.forget(state, vars_=False, files=True)
        if sub in ("worktree", "clone", "init", "submodule"):
            # The directories it makes or fills: a later gh write there goes where they say.
            for v in _operands(rest):
                k = _fold(state.path(v)) if v is not None else None
                if k is not None:
                    _tag(state, k, "git " + sub)
        if sub in ("checkout", "switch") or (sub == "branch" and any(
                v is None or v in ("-m", "-M", "--move") for v in rest)):
            state.branches = state.branches + tuple(_new_branch(sub, rest))

    quiet_gh = None

    def check_words(self, words, state, quiet):
        for w in words:
            if self.has_gh(w, state):
                if quiet:
                    self.quiet_gh.append("an argument")
                else:
                    self.problem("A gh word is an argument of a command that can run its"
                                 " arguments, so the hook cannot tell what it runs.")

    def assign(self, name, word, appends, state, export, at=None):
        # at: the state the value expands in, a declare's from before any of its words assign.
        at = at or state
        if (export or name in RUNNER_VARS or name in state.exported) and self.has_gh(word, at):
            self.problem("A gh word is in " + name + ", which a later program may run, so the hook"
                         " cannot tell what the command runs.")
        value = word.literal(at.env(), pattern_ok=True)
        if name in ZSH_SPECIAL:
            # zsh sets it itself, or ties it to another (#361, the fourth hunt).
            value = None
        if name in ("PATH", "path"):
            state.events.append("assigns PATH")
        if appends:
            old = state.vars.get(name, "")
            value = None if old is None or value is None else old + value
        state.vars[name] = value
        if export:
            state.exported.add(name)
        state.tainted.discard(name)
        if value is None and (self.taints(word) or any(
                p.kind == "param" and p.text in at.tainted for p in word.parts)):
            state.tainted.add(name)
        if name.startswith("GIT_") or name in TARGET_VARS:
            state.events.append("assigns " + name)
        if name == "IFS":
            state.optioned = True

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

    def declare(self, base, args, vals, state, precommand=False):
        export = base == "export" or any(v is not None and v.startswith("-") and "x" in v[1:]
                                         for v in vals)
        letters = set()
        for v in vals:
            if v is not None and len(v) > 1 and v[0] in "-+" and not _ASSIGN.match(v[1:]):
                letters |= set(v[1:])
        if precommand or base in ("integer", "float") or letters - set("xgraA"):
            # An attribute that changes a value (-l, -u, -L, -Z, -i, -T, -n), one that does
            # not assign (-p, -f, -m), an option zsh refuses, or a declare under `builtin`,
            # which brace-expands its words: later words are past what the walk follows (#361,
            # the fourth hunt).
            self.forget(state)
            state.optioned = True
            return
        if letters & set("aAg"):
            # Arrays and globals in functions: not followed.
            self.forget(state)
        # zsh expands every word before it assigns any (#361, the fifth hunt).
        pre = state.copy()
        for w, v in zip(args, vals):
            first = w.parts[0] if w.parts else None
            m = _ASSIGN.match(first.text) if first is not None and first.kind == "lit" \
                and not first.quoted else None
            if m and m.end() <= len(first.text):
                # NAME=value with the name in plain sight: only NAME is assigned.
                self.assign(m.group(1), _after_assign(w, m.end()), m.group(2) == "+", state,
                            export=export, at=pre)
                continue
            if v is None:
                self.forget(state)
                state.events.append(base + " of a word the hook cannot know")
                if self.has_gh(w, state):
                    self.problem("A gh word is an argument of " + base + " that the hook cannot"
                                 " read.")
                continue
            if v.startswith("-") or v.startswith("+"):
                continue
            if "[" in v.split("=", 1)[0]:
                # NAME[...]=: an element, zsh's options array among them.
                self.forget(state)
                state.optioned = True
                continue
            m = _ASSIGN.match(v)
            if m:
                # A quoted "NAME=value": zsh still assigns it.
                value = Word([Part("lit", v[m.end():], True)], "\0", v[m.end():])
                self.assign(m.group(1), value, m.group(2) == "+", state, export=export)
            elif _NAME.fullmatch(v):
                if export:
                    state.exported.add(v)
                    if (v.startswith("GH_") or v.startswith("GIT_") or v in TARGET_VARS) \
                            and state.vars.get(v) is None:
                        state.events.append("export of " + v + ", whose value the hook cannot know")
            elif self.has_gh(w, state):
                self.problem("A gh word is an argument of " + base + " that the hook cannot read.")

    def cd(self, vals, state, given=()):
        if set(given) & {"CDPATH", "cdpath", "HOME", "PWD", "OLDPWD"}:
            # `CDPATH=x cd y` searches x first (#361, the fifth hunt).
            state.cwds = (None,)
            return
        cdpath = "CDPATH" in self.environ or "CDPATH" in state.vars or "cdpath" in state.vars
        if vals and vals[0] is not None and cdpath and not (
                vals[0].startswith("/") or vals[0].startswith("./") or vals[0].startswith("../")
                or vals[0] in (".", "..")):
            state.cwds = (None,)
            return
        if not vals:
            target = state.vars.get("HOME")
        elif len(vals) == 1 and vals[0] is not None and vals[0] != "-":
            target = vals[0] if vals[0].startswith("/") else None
            if target is None and len(state.cwds) == 1 and state.cwds[0] is not None:
                target = state.cwds[0] + "/" + vals[0]
        else:
            target = None
        if target and _refused(target, state):
            # The kernel refuses `missing/..`, which _norm takes as text.
            target = None
        state.cwds = (_norm(target) if target else None,)

    def child_of(self, state, cmd, env):
        """The state a child shell or a script starts with: the exported variables, and the
        assignments and env options the command gives it, each guarded when it moves gh."""
        child = state.copy()
        child.vars = dict((n, v) for n, v in state.vars.items() if n in state.exported)
        for name, w, _ in (cmd.assigns if cmd is not None else []):
            child.vars[name] = resolve(w, state)
            child.exported.add(name)
            if name.startswith("GIT_") or name in TARGET_VARS:
                child.events.append("assigns " + name)
        for name, value in (env or {}).get("assigns", []):
            child.vars[name] = value
            child.exported.add(name)
            if name.startswith("GIT_") or name in TARGET_VARS:
                child.events.append("assigns " + name)
        if env and (env.get("clears") or env.get("unsets")):
            child.events.append("env clears or unsets the environment")
        return child

    def shell(self, cmd, args, vals, state, streams, piped, env=None):
        # sh -c <script> [words], sh <file> [words], and sh reading its script from standard
        # input, with options read as bash and zsh read them.
        k = 0
        saw_c = False
        while k < len(vals):
            a = vals[k]
            if a is None:
                self.problem("A shell is given a word the hook cannot know, so it cannot tell"
                             " what it runs.")
                return
            if a == "--":
                k += 1
                break
            if a.startswith("--"):
                if a in SHELL_LONG:
                    k += 1
                elif a in SHELL_LONG_ARG:
                    k += 2
                else:
                    self.problem("A shell is given an option the hook does not read, so it cannot"
                                 " tell what it runs.")
                    return
                continue
            if a in ("-o", "+o", "-O", "+O"):
                k += 2
                continue
            if len(a) > 1 and a[0] in "-+":
                saw_c = saw_c or "c" in a[1:]
                k += 1
                continue
            break
        child = self.child_of(state, cmd, env)
        # The words after the script or the file are its $0, $1 and the rest.
        self.check_words(args[k + 1:], state, quiet=False)
        if saw_c:
            if k >= len(vals):
                return
            self.walk(parse(vals[k]), child)
            state.absorb(child)
            return
        if k < len(vals) and vals[k] not in ("-", "/dev/stdin", "/dev/fd/0"):
            self.runs_file(state.path(vals[k]), state, cmd, env)
            return
        if piped:
            self.problem("A shell reads its script from a pipe, so the hook cannot tell what it"
                         " runs.")
            return
        for r in cmd.redirs:
            if r.op in ("<", "<>") and r.fd in ("", "0"):
                self.runs_file(state.path(r.target.literal(state.env())), state, cmd, env,
                               on_disk=True)
                return
        for r, text in streams:
            if text.content is None:
                if text.gh:
                    self.problem("A shell reads " + text.label + " the hook cannot know.")
                else:
                    self.unknown_program(state, "a shell reading what it cannot know")
            else:
                self.walk(parse(text.content), child)
                state.absorb(child)

    def reparse(self, text, state):
        self.walk(parse(text), state)

    def eval_(self, cmd, vals, state, words=None):
        # eval runs its words, joined, in this shell: read as a command when all are known.
        if vals and None not in vals:
            self.walk(parse(" ".join(vals)), state)
            return
        if any(self.has_gh(w, state) for w in (words or cmd.words)[1:]):
            self.problem("A gh word is an argument of eval, whose words the hook cannot know.")
        self.forget(state, cwd=True, files=True)
        state.events.append("eval of words the hook cannot know")

    def source(self, value, cmd, state):
        # source and . run a file in this shell: one the command wrote is read; any other may
        # set any variable, change the directory and write any file.
        path = state.path(value) if value else None
        text = state.files.get(_fold(path)) if path else None
        if text is not None and text.content is not None:
            self.walk(parse(text.content), state)
            return
        if text is not None:
            self.problem("The command sources a file it wrote, and the hook cannot know what it"
                         " holds.")
            return
        self.forget(state, cwd=True, files=True)
        state.events.append("source of a file the hook does not read")

    def runs_file(self, path, state, cmd=None, env=None, on_disk=False):
        """A file run as a script, by a shell or by its path. One the command wrote is read; one
        it changed, or wrote with content it cannot know, blocks; one on disk is out of scope
        when run by name, and unknown when a shell reads it from `<`."""
        key = _fold(path)
        if key is not None and key not in state.files and _named(state, key):
            self.problem("The command runs a file it changed earlier, and the hook cannot know"
                         " what it holds.")
            return
        if key is None or key not in state.files:
            if on_disk or key is None:
                self.unknown_program(state, "a script the hook does not read")
            return
        text = state.files[key]
        if text.content is None:
            self.problem("The command runs a file it wrote, and the hook cannot know what it"
                         " holds.")
            return
        child = self.child_of(state, cmd, env)
        self.walk(parse(text.content), child)
        state.absorb(child)

    def config_path(self, p, state):
        """True when a path holds what decides where gh writes: a .git directory or file, or
        git's or gh's configuration under HOME."""
        if p is None:
            return False
        p = _fold(p)
        bits = p.split("/")
        if ".git" in bits or any(b.startswith(".git") and b != ".github" and b != ".gitignore"
                                 and b != ".gitattributes" and b != ".gitkeep" for b in bits):
            return True
        home = _fold(self.home or "")
        return bool(home) and (p.startswith(home + "/.config/git") or p.startswith(home + "/.config/gh")
                               or p == home + "/.gitconfig")

    def names_files(self, base, quiet, vals, state):
        # A file this command wrote, with a gh word in it, named by a program that can run it.
        if not quiet and base not in KNOWN_PROGRAMS and base not in ZSH_BUILTINS:
            for v in vals:
                k = _fold(state.path(v)) if v else None
                if k in state.files and state.files[k].gh:
                    self.problem("A file the command wrote holds a gh word, and " + base
                                 + " reads it and can run what it reads.")
        # A path any command but a reader names may change before gh reads it (T5). git's
        # subcommands are decided by what they do (Finder.git), and a flag names no path.
        outputs = OUTPUT_OPTIONS.get(base)
        if outputs and any(v is None or re.fullmatch(outputs, v) for v in _options(vals)):
            # An output it names inside an option: any file may hold anything after it.
            state.deferred = True
            state.events.append(base + " writing a file an option names")
            return
        if base == "ln":
            # A link makes two paths one file, which the walk keys apart (the fourth hunt).
            state.deferred = True
        if base in ("cp", "mv", "install", "ln") and (not _operands(vals) or any(
                v is None or state.path(v) is None for v in _operands(vals))):
            # A copy to a path the hook cannot know may be a git hook (#361, the fifth hunt).
            self.runners.append(base + " to a path the hook cannot know")
        if base == "mv" or (base == "cp" and any(v is None or (not v.startswith("--") and set(
                v[1:]) & set("RrPaH")) for v in _options(vals))):
            # mv, and cp -R, -P, -a or -H, copy a link as a link (#361, the fifth hunt).
            if any(_links(_unfollowed(v, state), state) for v in _operands(vals)[:-1]):
                state.deferred = True
        if base in READERS or base == "git":
            return
        for v in _operands(vals):
            p = state.path(v) if v else None
            k = _fold(p)
            if k is not None:
                # What it names may now hold anything, and so may whatever is under it; chmod
                # changes a file's mode, not what it holds.
                if base == "chmod" or (base in ("mkdir", "install") and any(
                        v is None or v.startswith("-m") for v in _options(vals))):
                    # A later redirection to it, or under it, may fail: the walk reads that
                    # from this name, a mode given to mkdir or install included.
                    _tag(state, k, "chmod")
                else:
                    _tag(state, k, base or "a command")
                if base != "chmod":
                    for f in [f for f in state.files if f == k or f.startswith(k + "/")]:
                        del state.files[f]
            if base and self.config_path(p, state):
                state.events.append(base + " of a path that decides where gh writes")
                if base != "chmod" or any(t.gh for t in state.files.values()):
                    self.stranger(base + " into .git or git's or gh's configuration")
            elif v is None and base in FILE_WRITERS:
                # An argument it cannot know may be any path, under .git included.
                state.deferred = True
                state.events.append(base + " of a path the hook cannot know")

    def writes(self, cmd, who, state, streams, piped=False, at=None):
        """Records each file a command writes, a redirection's target or one of tee's files,
        with what it writes when that is known: a here-document cat or tee copies, or the
        literal text echo or printf prints. A file it cannot resolve is not recorded, and a
        later read of it is decided by where it is read (T5). at is the state the targets are
        expanded in, a compound's from before its body (#361, the fifth hunt)."""
        at = at or state
        base, vals = who if who is not None else ("", [])
        files = _operands(vals)
        content, gh = None, False
        # zsh joins every input redirection a command has (MULTIOS), and a pipe into it, so cat
        # or tee copies a known text only when a here-document or a here-string on its standard
        # input is its one input, and cat only with no option, which may rewrite bytes.
        inputs = [r for r in cmd.redirs if (r.op in STDIN_OPS or r.op == "<&") and r.fd in ("", "0")]
        mine = [x for r, x in streams if r.fd in ("", "0")]
        one = len(inputs) == 1 and len(mine) == 1 and not piped
        if (base == "cat" and one and not files and not _options(vals)) or (
                base == "tee" and one and all(re.fullmatch(r"-[ai]+|--append|--ignore-interrupts", v)
                                              for v in _options(vals))):
            content, gh = mine[0].content, mine[0].gh
        elif base in ("echo", "printf"):
            content, gh = self.printed(base, vals)
        if base in ("cat", "head", "tail", "sort", "uniq", "cut", "tr", "base64", "tee", "fold",
                    "nl", "paste", "column"):
            # What it copies holds a gh word when what it reads does.
            gh = gh or any(x.gh for x in mine) or any(
                (state.files.get(_fold(state.path(f))) or Text(None, False, "")).gh
                for f in files if f is not None and state.path(f) is not None)
        targets = []
        for r in cmd.redirs:
            if r.target is None or not (r.op.startswith(">") or r.op.startswith("&>")
                                        or r.op == "<>"):
                continue
            v = r.target.literal(at.env())
            if r.op == "<>":
                # Opened to read and write, unshortened: what it ends up holding is unknown.
                targets.append((v, False, False))
                continue
            if r.op in (">&", "<&") and v is not None and (v.isdigit() or v == "-"):
                continue
            out = r.fd in ("", "1") or r.op.startswith("&>") or r.op == ">&"
            targets.append((v, r.op.startswith(">>") or r.op == "&>>", out))
        if base == "tee":
            appends = any(v == "--append" or (v and re.fullmatch(r"-[^-]*a.*", v))
                          for v in _options(vals))
            targets += [(v, appends, True) for v in files]
        fails = False
        # zsh opens the redirections in order and runs nothing when one fails: a target whose
        # directory is missing, and not made earlier in the command, leaves every target as it was.
        for r in cmd.redirs:
            if r.target is None or r.op in STDIN_OPS or r.op in (">&", "<&"):
                continue
            v = r.target.literal(at.env())
            q = at.path(v)
            if q is not None and q != "/dev/null" and (_kernel_refuses(v, at) or (
                    not os.path.isdir(os.path.dirname(q))
                    and _named(at, _fold(os.path.dirname(q))) in (None, "rm", "rmdir"))):
                fails = True
                break
        for v, appends, out in targets:
            p = at.path(v)
            if self.config_path(p, state) or (p is None and v is not None and ".git" in v):
                state.events.append("a write to a path that decides where gh writes")
                self.stranger("a write into .git or git's or gh's configuration")
            if p is None:
                # A path it cannot know may be any file, a body file, .git/config or a git
                # hook: a gh word written there counts as written (#361, the fifth hunt).
                state.deferred = True
                state.events.append("a write to a path the hook cannot know")
                if gh or content is None and any(x.gh for x in mine):
                    self.gh_text = True
                continue
            if p == "/dev/null":
                continue
            if (os.path.lexists(p) and not os.access(p, os.W_OK)) or _moded(at, _fold(p)) \
                    or at.named.get(_fold(p)) not in (None, "touch", "rm", "rmdir") \
                    or _above(at, _fold(p)) or _kernel_refuses(v, at):
                # The redirection may fail, or a job still running may write after it: a mode
                # changed there or above, or a copy that kept its source's mode, leaves the
                # file what it held (#361, the fifth hunt).
                out = False
            text = Text(content if out and not fails else None, gh and out,
                        "a file this command wrote", p)
            k = _fold(p)
            old = state.files.get(k)
            if appends and old is None and _named(state, k) is None:
                old = on_disk(p)
            if appends:
                if old is None or old.content is None or text.content is None:
                    text = Text(None, text.gh or (old is not None and old.gh), text.label, p)
                else:
                    text = Text(old.content + text.content, text.gh or old.gh, text.label, p)
            state.files[k] = text
            if text.gh:
                self.gh_text = True

    def printed(self, base, vals):
        if any(v is None for v in vals):
            return None, any(v is None or mentions_gh(v) for v in vals)
        return printed(base, vals), any(mentions_gh(v) for v in vals)

    def find(self, script):
        self.quiet_gh = []
        self.stdin = []
        self.functions = set()
        self.strangers = []
        self.runners = []
        self.gh_text = False
        self.aliased = False
        self.walk(script, self.start.copy())
        if self.gh_text and (self.strangers or self.runners):
            self.problem("The command writes a gh word into a file, and runs "
                         + ", ".join((self.strangers + self.runners)[:3]) + ", which the hook"
                         " does not follow and which may run it.")
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
    # GitHub takes --match-head-commit as a commit id, and stores nothing that is not one.
    ("pr merge", "match-head-commit"): "unsent",
    ("variable set", "env-file"): "file", ("gist edit", "add"): "file",
    ("*", "attach"): "attach",
    ("api", "field"): "field", ("workflow run", "field"): "field",
}

# Which positionals of a write name files whose content is sent: `v` a value, `f` a file with an
# optional `#label`; a trailing `*` repeats the last.
POSITIONAL = {
    "gist create": "f*", "gist edit": "v F", "release create": "v f*", "release upload": "v f*",
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
    if inv.state.optioned:
        return lost("its words, whose expansion shell options, IFS or a function zsh runs by"
                    " itself, set earlier in the command, change")
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
        if v in ("-", ""):
            k += 1
            continue
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
                        and not first.text.startswith("-")) or not _one_word(inv.words[i]):
                    # A word zsh may split may hold a flag after its first part (#361, the
                    # fifth hunt).
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
                    if value is None and not _one_word(inv.words[i]):
                        # zsh may split it into several words, a flag among them.
                        flaglike = True
                flags.append((name, value, i))
            else:
                b = parse_bool(value) if eq else True
                if b is None:
                    return unknown_flag(path, i)
                flags.append((name, b, i))
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
                        if value is None and not _one_word(inv.words[i]):
                            flaglike = True
                    flags.append((name, value, i))
                    break
                if a[c + 1:c + 2] == "=":
                    b = parse_bool(a[c + 2:])
                    if b is None:
                        return unknown_flag(path, i)
                    flags.append((name, b, i))
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
        kind = "write" if flaglike else api_kind(flags, positionals, inv.state, inv.words)
    if kind in ("read", "local"):
        return Verdict(kind, path)
    if inv.background:
        return lost("what a gh write run in the background reads, which later commands may change")
    return Verdict("write", path, flags, positionals)


def parse_bool(value):
    """A bool flag's value as Go's strconv.ParseBool reads it, or None for one gh refuses."""
    if value in ("1", "t", "T", "TRUE", "true", "True"):
        return True
    if value in ("0", "f", "F", "FALSE", "false", "False"):
        return False
    return None


def unknown_flag(path, i):
    return Verdict("block", path, result=block(
        "gh " + path + " was given a flag the hook's table does not list for it (word "
        + str(i + 1) + " after gh), so it cannot tell what gh would send.", ADVICE_FLAG))


def api_kind(flags, positionals, state, words=None):
    methods = [v for n, v, _ in flags if n == "method"]
    if methods:
        return "read" if isinstance(methods[-1], str) and methods[-1].upper() == "GET" else "write"
    if any(n in ("field", "raw-field", "input") for n, _, _ in flags):
        endpoint = positionals[0][1] if positionals else None
        if endpoint == "graphql":
            for n, v, i in flags:
                if n in ("field", "raw-field") and not isinstance(v, str):
                    # A value it cannot know is harmless only under a key in plain sight that
                    # is not the query.
                    first = words[i].parts[0] if words is not None and words[i].parts else None
                    key = first.text.split("=", 1)[0] if first is not None and first.kind == "lit" \
                        and "=" in first.text else None
                    if key is None or key == "query":
                        return "write"
            # gh applies every -f before every -F, so a -F query wins wherever it stands.
            queries = [(n, v[6:]) for n, v, _ in flags if n in ("field", "raw-field")
                       and isinstance(v, str) and v.startswith("query=")]
            queries = [q for q in queries if q[0] == "raw-field"] \
                + [q for q in queries if q[0] == "field"]
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
            if v is None or (not p.quoted and (v == "" or re.search(r"[ \t\n\0]", v))):
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
    stdin = _stdin_of(cmd.redirs)
    if any(r not in stdin for r in cmd.redirs):
        return None
    if vals[0] == "cat" and len(vals) == 1:
        if not stdin:
            # It reads the shell's own standard input, which a group or an exec may give it.
            return None
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
    pinned = getattr(r, "pinned", None)
    if pinned is not None:
        if isinstance(pinned, Lost):
            raise pinned
        key = r.key
        if key is not None and (state.deferred or state.files.get(key[0]) is not key[1]
                                or state.named.get(key[0]) != key[2]):
            raise Lost("standard input a compound opened, which its body may change")
        return pinned
    if r.op == "<&":
        v = r.target.literal() if r.target is not None else None
        if v == "-":
            return b""
        raise Lost("standard input taken from descriptor " + (v or "that cannot be known"))
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
    raw = value if value.startswith("/") else ((state.cwds[0] or "") + "/" + value
                                                if len(state.cwds) == 1 else value)
    bits = raw.split("/")
    for n, bit in enumerate(bits):
        if bit == ".." and _named(state, _fold(os.path.realpath("/".join(bits[:n]) or "/"))):
            raise Lost(value + ", whose `..` follows a path the command creates or changes")
    if state.deferred:
        raise Lost(value + ", which a function, a source, an eval or an exec earlier in the"
                   " command may change, or read in a function's body")
    p = state.path(value)
    if p is None:
        raise Lost("a relative path, " + value + ", in a directory the hook cannot know")
    k = _fold(p)
    if ".git" in _fold(raw).split("/") or ".git" in k.split("/"):
        raise Lost(value + ", inside .git, which git commands change")
    if any(_loose(x) == _loose(k) and x != k for x in list(state.files) + list(state.named)):
        raise Lost(value + ", which the command may write under another spelling")
    if k in state.files:
        text = state.files[k]
        if text.content is None:
            raise Lost(value + ", which the command writes before gh reads it")
        return _bytes(text.content)
    if _named(state, k):
        raise Lost(value + ", which " + _named(state, k) + " names earlier in the command")
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


def _one_word(word):
    """True when zsh gives the word as one word: no unquoted substitution or zsh flag form,
    which split, and no quoted $@ or [@], which spread; an unquoted $NAME does not split."""
    if word.pattern():
        return False
    for p in word.parts:
        if p.kind in ("cmdsub", "procsub", "opaque") and not p.quoted:
            return False
        if p.kind == "opaque" and "@" in p.text:
            return False
    return True


def file_sources(value, label, state, published=False):
    """The sources a file argument gives: its content, and for a published file its name and
    the label after `#`."""
    path, sep, tag = value.partition("#") if published == "label" \
        or label.startswith("the --attach") else (value, "", "")
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
        if value is True or value is False:
            continue
        if role == "unsent":
            # Not scanned, but a value zsh may split into several words could hold a flag.
            if value is None and not _one_word(inv.words[i]):
                raise Lost("a value of --" + name + " that zsh may split into several words")
            continue
        if value is None:
            raise Lost("a word whose value cannot be known before the command runs (word "
                       + str(i + 1) + " after gh)")
        if role in ("file", "attach"):
            # An attached file, and one gist edit --add adds, are published under their names.
            sources += file_sources(value, "the --" + name + " file", state,
                                    published=role == "attach" or (path, name) == ("gist edit", "add"))
        elif role == "field" and value.partition("=")[2][:1] == "@":
            key, _, rest = value.partition("=")
            sources.append(Source("the --" + name + " key", _bytes(key)))
            sources += file_sources(rest[1:], "the --" + name + " file", state)
        else:
            sources.append(Source("the --" + name + " value", _bytes(value)))
    if path == "gist edit" and not any(n in ("add", "desc", "remove") for n, _, _ in flags) \
            and len(positionals) < 2:
        raise Lost("gh gist edit's editor")
    if path == "skill publish":
        raise Lost("the files under the directory gh skill publish publishes")
    if path == "repo create" and not positionals:
        # gh names the repository after the --source directory (#361, the fourth hunt).
        for name, value, _ in flags:
            if name == "source":
                where = state.path(value) if isinstance(value, str) else None
                if where is None or _named(state, _fold(where)):
                    raise Lost("the name gh repo create takes from its --source directory")
                sources.append(Source("the repository name from --source",
                                      _bytes(os.path.basename(where))))
    if path == "agent-task create" and not positionals \
            and not any(n == "from-file" for n, _, _ in flags):
        raise Lost("gh agent-task create's editor")
    spec = POSITIONAL.get(path, "v*").split()
    for n, (i, value) in enumerate(positionals):
        role = spec[min(n, len(spec) - 1)].rstrip("*")
        if value is None:
            raise Lost("a word whose value cannot be known before the command runs (word "
                       + str(i + 1) + " after gh)")
        if role in ("f", "F"):
            sources += file_sources(value, "the file in argument " + str(n + 1), state,
                                    published="label" if path in ("release create", "release upload")
                                    else role == "f")
        else:
            sources.append(Source("argument " + str(n + 1), _bytes(value)))
    # Standard input, for every write whatever its flags: gh reads it for more than `-`.
    if inv.piped:
        raise Lost("standard input from a pipe")
    if inv.state.stdin_unknown and not inv.redirs:
        raise Lost("standard input, which an earlier exec moved, or a function's caller gives")
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
_SUSPECT = re.compile(r"\.\.|%2e|%2f|//|\\\\|[#;\s]|/\./|/\.$|\.$|(^|/)\.(/|$)", re.I)
# What gh reads from its environment that changes which repository or host it writes to.
TARGET_ENV = ("GH_HOST", "GH_CONFIG_DIR", "HOME", "XDG_CONFIG_HOME", "GIT_DIR", "GIT_WORK_TREE",
              "GIT_CONFIG",
              "GIT_CONFIG_GLOBAL", "GIT_CONFIG_SYSTEM", "GIT_CONFIG_COUNT", "GIT_CONFIG_PARAMETERS",
              "GIT_COMMON_DIR", "GIT_NAMESPACE")


def repo_of(value):
    """OWNER/REPO, lower-cased, from what -R and a remote take: OWNER/REPO, HOST/OWNER/REPO, an
    https or ssh URL, or scp-style host:owner/repo. .git is stripped only from a URL. None when
    it does not parse."""
    if value is None:
        return None
    url = False
    if _SUSPECT.search(value.split("://", 1)[-1]):
        return None
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
    m = re.match(r"^https?://[^/]+/([^/]+)/([^/?#]+)(/|$)", value or "", re.I)
    return (m.group(1) + "/" + m.group(2)).lower() if m else None


# The issue flags that name another issue, which the write changes too.
RELATIONS = {"parent", "blocked-by", "blocking", "add-blocked-by", "add-blocking", "add-sub-issue",
             "remove-blocked-by", "remove-blocking", "remove-sub-issue"}
# The paths whose URL arguments select the repository, beside -R.
SELECTS = ("issue ", "pr ", "discussion ")


def named(inv, path, flags, positionals, events, has_repo_flag=True):
    """The repositories an invocation names itself, which decide alone, or None when it names
    none. Raises Guarded."""
    if path.startswith(OWNER_LEVEL) or any(n in ("org", "owner", "user") for n, _, _ in flags):
        raise Guarded("it writes to an account or an owner, not a repository")
    hosts = [v for n, v, _ in flags if n == "hostname"]
    if hosts and (not isinstance(hosts[-1], str) or hosts[-1].lower() != "github.com"):
        raise Guarded("it names a host other than github.com")
    # A URL argument selects its repository whatever -R says, so both count.
    selectors = []
    if path.startswith(SELECTS):
        for _, v in positionals:
            if v is not None and re.match(r"^https?://", v, re.I):
                r = url_repo(v)
                if r is None:
                    raise Guarded("a URL it is given does not parse")
                selectors.append(r)
    extra = []
    if path == "issue develop":
        for n, v, _ in flags:
            if n == "branch-repo":
                r = repo_of(v)
                if r is None:
                    raise Guarded("its --branch-repo does not parse")
                extra.append(r)
    if path in ("issue create", "issue edit"):
        # A relation writes onto the other issue too (#361, the fifth hunt).
        for n, v, _ in flags:
            if n not in RELATIONS:
                continue
            for piece in (v if isinstance(v, str) else "?").split(","):
                piece = piece.strip()
                if re.fullmatch(r"#?\d+", piece):
                    continue
                r = url_repo(piece) if re.match(r"^https?://", piece, re.I) else repo_of(
                    piece.split("#", 1)[0] if re.fullmatch(r"[^#]+#\d+", piece) else None)
                if r is None:
                    raise Guarded("its --" + n + " does not parse")
                extra.append(r)
    if path == "issue transfer" and len(positionals) >= 2:
        r = repo_of(positionals[1][1])
        if r is None:
            raise Guarded("the repository it transfers to does not parse")
        extra.append(r)
    repos = [v for n, v, _ in flags if n == "repo"]
    if repos:
        out = []
        for v in repos:
            r = repo_of(v)
            if r is None:
                raise Guarded("its --repo value does not parse")
            out.append(r)
        return out + selectors + extra
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
    assigned = [v for n, v in inv.assigns_named if n == "GH_REPO"]
    if path == "api":
        endpoint = positionals[0][1] if positionals else None
        if endpoint is None:
            raise Guarded("its endpoint cannot be known")
        endpoint = re.sub(r"^https://(api|uploads)\.github\.com/", "", endpoint, flags=re.I)
        if _SUSPECT.search(endpoint):
            raise Guarded("its endpoint holds a sequence the hook does not resolve")
        if endpoint.startswith("/"):
            endpoint = endpoint[1:]
        if re.search(r"(generate|forks|transfer)", endpoint, re.I):
            raise Guarded("its endpoint makes or moves a repository under another owner")
        m = re.match(r"^repos/([^/{}:?#]+)/([^/{}:?#]+)(/|\?|$)", endpoint)
        if m:
            return [(m.group(1) + "/" + m.group(2)).lower()]
        if re.match(r"^repos/(\{owner\}|:owner)/(\{repo\}|:repo)(/|\?|$)", endpoint):
            if assigned:
                r = repo_of(assigned[-1])
                if r is None:
                    raise Guarded("its GH_REPO does not parse")
                return [r]
            return None
        raise Guarded("its endpoint names no repository")
    if selectors:
        return selectors + extra
    if extra:
        # The issue's own repository comes from the directory: both are reached.
        raise Guarded("it writes to a repository beside the one it names")
    # gh reads GH_REPO only where it takes --repo.
    if assigned and has_repo_flag:
        r = repo_of(assigned[-1])
        if r is None:
            raise Guarded("its GH_REPO does not parse")
        return [r]
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
        # HOME and XDG_CONFIG_HOME are where the hook itself reads git's and gh's configuration.
        if name in ("HOME", "XDG_CONFIG_HOME"):
            continue
        if name in TARGET_ENV or name.startswith("GIT_CONFIG"):
            raise Guarded("its environment holds " + name)
    if inv.env["clears"] or inv.env["unsets"]:
        raise Guarded("env clears or unsets its environment")
    for name, value in inv.assigns_named:
        if name in TARGET_ENV or name.startswith("GIT_"):
            raise Guarded("it is given " + name)
    if (any(n in ("PATH", "path") for n, _ in inv.assigns_named) or "assigns PATH" in inv.state.events) \
            and (inv.state.files or inv.state.named or inv.state.deferred):
        # A git the command wrote, found first on that PATH, answers gh's question of the remotes.
        raise Guarded("it runs with a PATH the command changed, after the command wrote files")
    for e in inv.state.events + events:
        if e not in ("assigns GH_REPO", "assigns PATH"):
            raise Guarded("the command runs " + e + " before it")
    for cwd in inv.state.cwds:
        k = _fold(os.path.realpath(cwd)) if cwd else None
        if k is not None and _named(inv.state, k):
            raise Guarded("the directory it runs in, or one above it, is changed earlier")


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


# The gh commands that change where a later gh command writes.
GH_RETARGETS = ("repo set-default", "config set", "repo create", "repo fork", "repo clone",
                "repo rename", "auth switch", "auth login", "auth logout", "alias set",
                "alias import")


def head_sources(inv, ctx):
    """gh pr create with no --head pushes the current branch and names it as the head: the
    branch the hook reads, and every name the command may give it (#361, the fourth hunt)."""
    if None in inv.state.branches:
        raise Lost("the branch gh pr create pushes, which the command changes to a name the hook"
                   " cannot know")
    cwd = inv.state.cwds[0] if len(inv.state.cwds) == 1 else None
    names = list(inv.state.branches)
    here = ctx.branch(cwd) if cwd else None
    if here:
        names.append(here)
    return [Source("the branch gh pushes as the head", _bytes(b)) for b in names]


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
    found = Finder(ctx.home, cwd, ctx.environ).find(parse(command))
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
        if verdict.kind == "write":
            if inv.strangers:
                return block("A gh write runs after " + ", ".join(inv.strangers[:3]) + ", which"
                             " the hook does not follow, so it cannot tell what gh would send or"
                             " where.", ADVICE_STRANGER)
            writes.append((inv, verdict, list(events)))
        if verdict.path in GH_RETARGETS:
            # It changes where a later gh command writes, not where it writes itself.
            events.append("gh " + verdict.path)
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
            repos = named(inv, verdict.path, verdict.flags, verdict.positionals, earlier,
                          "repo" in nodes()[verdict.path].longs)
            if repos is None:
                repos = candidates(inv, ctx)
            if all(is_exempt(r, entries) for r in repos):
                continue
        except Guarded:
            repos = []
        try:
            got = gather(inv, verdict.path, verdict.flags, verdict.positionals)
            if verdict.path == "api":
                if inv.state.branches and any(re.search(rb"\{branch\}", x.data) for x in got):
                    raise Lost("{branch}, after the command changes the branch")
                got = placeholders(got, repos, inv.state.cwds[0], ctx)
            if verdict.path == "pr create" and not any(n == "head" for n, _, _ in verdict.flags):
                got += head_sources(inv, ctx)
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


# ---------------------------------------------------------------------------------------------
# The registration check (#361 AC5): `gh_guard.py --check-registration <repository>`, run by this
# repository's working-tree guard from the default branch's copy of the hook, which is therefore
# the reference the installed copy is compared with. It prints one sentence per fault on stderr
# and exits 2, or exits 0, with "skipped: ..." on stderr when there is no Claude Code here.

MATCHED = ("Bash", "mcp__terminal__run_in_terminal")
PROBE_WORD = "Zq_Gh_Guard_Probe"


def managed_settings():
    if sys.platform == "darwin":
        return "/Library/Application Support/ClaudeCode/managed-settings.json"
    return "/etc/claude-code/managed-settings.json"


def managed_plists():
    """The macOS managed preferences files of the com.anthropic.claudecode domain."""
    if sys.platform != "darwin":
        return []
    import pwd
    try:
        user = pwd.getpwuid(os.getuid()).pw_name
    except KeyError:
        user = ""
    base = "/Library/Managed Preferences"
    return [os.path.join(base, "com.anthropic.claudecode.plist")] + \
        ([os.path.join(base, user, "com.anthropic.claudecode.plist")] if user else [])


def load_plist(path, faults):
    import plistlib
    try:
        with open(path, "rb") as f:
            value = plistlib.load(f)
    except FileNotFoundError:
        return None
    except Exception:
        faults.append(path + " cannot be read as a property list.")
        return None
    if not isinstance(value, dict):
        faults.append(path + " is not a dictionary.")
        return None
    return value


def managed_sources(faults):
    """Each managed settings object Claude Code reads from this machine, as (where, object): the
    managed preferences, managed-settings.json and managed-settings.d/*.json in name order."""
    out = []
    for path in managed_plists():
        value = load_plist(path, faults)
        if value is not None:
            out.append((path, value))
    path = managed_settings()
    value = load_json(path, faults, required=False)
    if value is not None:
        out.append((path, value))
    drops = os.path.join(os.path.dirname(path), "managed-settings.d")
    if os.path.lexists(drops):
        try:
            names = sorted(n for n in os.listdir(drops) if n.endswith(".json") and not n.startswith("."))
        except OSError:
            faults.append(drops + " cannot be read.")
            names = []
        for name in names:
            value = load_json(os.path.join(drops, name), faults, required=False)
            if value is not None:
                out.append((os.path.join(drops, name), value))
    return out


def off(value):
    """A switch counts as off only as JSON's false or null, or absent: any other value of a key
    that turns hooks off or restricts them is read as on, as Claude Code reads an invalid lock."""
    return value is None or value is False


def locks_hooks(value):
    """strictPluginOnlyCustomization: true, a list naming hooks, or a value of another type."""
    if off(value):
        return False
    if isinstance(value, list):
        return "hooks" in value
    return True


def load_json(path, faults, required):
    """The file's JSON object, None when it does not exist and is not required."""
    try:
        with open(path, "rb") as f:
            value = json.loads(f.read().decode("utf-8"))
    except FileNotFoundError:
        if required:
            faults.append(path + " does not exist.")
        return None
    except (OSError, ValueError):
        faults.append(path + " cannot be read as JSON.")
        return None
    if not isinstance(value, dict):
        faults.append(path + " is not a JSON object.")
        return None
    return value


def covers(matcher):
    """Whether a matcher covers both tools, read as Claude Code reads one: empty or `*` matches
    every tool, and one of letters, digits, `_`, `-`, spaces, `,` and `|` is a list of exact names
    split on `|` and `,`. Any other character makes it a regular expression, which is refused."""
    if not isinstance(matcher, str):
        return False
    if matcher.strip() in ("", "*"):
        return True
    if not re.fullmatch(r"[A-Za-z0-9_\- ,|]+", matcher):
        return False
    return set(MATCHED) <= {p.strip() for p in re.split(r"[|,]", matcher)}


def handlers(settings):
    """Every PreToolUse command handler of a settings object whose matcher covers both tools."""
    out = []
    groups = ((settings or {}).get("hooks") or {}).get("PreToolUse") or []
    for group in groups if isinstance(groups, list) else []:
        if isinstance(group, dict) and covers(group.get("matcher", "")):
            for h in group.get("hooks") or []:
                if isinstance(h, dict) and h.get("type") == "command":
                    out.append(h)
    return out


def version_of(path):
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                m = re.match(r"^GH_GUARD_VERSION = (\d+)$", line.rstrip("\n"))
                if m:
                    return int(m.group(1))
    except OSError:
        return None
    return None


def same_bytes(a, b):
    try:
        with open(a, "rb") as x, open(b, "rb") as y:
            return x.read() == y.read()
    except OSError:
        return False


def probe(handler):
    """Faults of the registered command, run exactly as registered against a scratch HOME."""
    import shutil
    import subprocess
    import tempfile
    faults = []
    home = tempfile.mkdtemp(prefix="gh-guard-probe-")
    try:
        os.makedirs(os.path.join(home, ".config", "gate-sdd"))
        with open(os.path.join(home, ".config", "gate-sdd", "leakage-patterns"), "w") as f:
            f.write("[fail]\n" + PROBE_WORD + "\n")
        argv = [handler["command"]] + list(handler.get("args") or [])
        env = {"PATH": "/usr/bin:/bin", "HOME": home}
        for command, want in (("ls -la", 0), ("gh issue create -t probe --body " + PROBE_WORD, 2)):
            data = json.dumps({"hook_event_name": "PreToolUse", "tool_name": "Bash",
                               "tool_input": {"command": command}, "cwd": home}).encode()
            try:
                r = subprocess.run(argv, input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   env=env, cwd=home, timeout=30)
            except (OSError, subprocess.TimeoutExpired) as e:
                faults.append("the registered command does not run (" + type(e).__name__ + ").")
                break
            said = r.stdout + r.stderr
            if r.returncode != want or (want == 0 and r.stdout):
                faults.append("the registered command " + ("did not pass a command without gh"
                              " in silence" if want == 0 else "did not block a write of a"
                              " synthetic word") + " (exit " + str(r.returncode) + ").")
            elif want == 2 and PROBE_WORD.encode() in said:
                faults.append("the registered command's block holds the text it matched.")
    finally:
        shutil.rmtree(home, ignore_errors=True)
    return faults


def snapshots_with_gh(config):
    """Claude Code shell snapshots defining an alias or a function whose body holds a gh word."""
    import glob
    found = []
    for path in sorted(glob.glob(os.path.join(config, "shell-snapshots", "*.sh"))):
        try:
            text = open(path, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        for m in re.finditer(r"^alias (?:-- )?[^=\n]+=(.*)$", text, re.M):
            if mentions_gh(m.group(1)):
                found.append(os.path.basename(path))
                break
        else:
            for m in re.finditer(r"^([^\s(){}]+) \(\) \{\n(.*?)^\}", text, re.M | re.S):
                if mentions_gh(m.group(2)):
                    found.append(os.path.basename(path))
                    break
    return found


def check_registration(repo, reference=None):
    """Faults, or "skip" when this machine has no Claude Code configuration. reference is the
    directory holding the reference's gh_guard.py, gh_guard_lib.py and check-leakage.sh: this
    module's own, as the guard runs it."""
    here = reference or os.path.dirname(os.path.realpath(__file__))
    home = os.environ.get("HOME", "")
    named = os.environ.get("CLAUDE_CONFIG_DIR", "")
    config = named or (os.path.join(home, ".claude") if home else "")
    # Skipped only when Claude Code has no configuration here at all: a CLAUDE_CONFIG_DIR that
    # names nothing beside a ~/.claude, or a HOME that is not set, is a fault, not a skip.
    if not (named and os.path.isdir(named)) and not (home and os.path.isdir(os.path.join(home, ".claude"))) \
            and not os.path.lexists(managed_settings()) \
            and not any(os.path.lexists(p) for p in managed_plists()):
        return "skip"
    faults = []
    if named and not os.path.isdir(named):
        faults.append("CLAUDE_CONFIG_DIR names " + named + ", which is not a directory.")
        return faults
    if not config:
        faults.append("HOME is not set, so the user settings cannot be found.")
        return faults
    user = load_json(os.path.join(config, "settings.json"), faults, required=False)
    managed = managed_sources(faults)
    if user and not off(user.get("disableAllHooks")):
        faults.append("disableAllHooks is true in the user settings, so no hook runs.")
    for where, settings in managed:
        if not off(settings.get("disableAllHooks")):
            faults.append("disableAllHooks is set in the managed settings (" + where + "), so no"
                          " hook runs.")
        if not off(settings.get("allowManagedHooksOnly")):
            faults.append("allowManagedHooksOnly is set in the managed settings (" + where + "), so"
                          " a user hook does not run.")
        if locks_hooks(settings.get("strictPluginOnlyCustomization")):
            faults.append("strictPluginOnlyCustomization locks hooks in the managed settings ("
                          + where + "), so a user hook does not run.")
    for local in ("settings.json", "settings.local.json"):
        settings = load_json(os.path.join(repo, ".claude", local), faults, required=False)
        if settings and not off(settings.get("disableAllHooks")):
            faults.append("disableAllHooks is true in this repository's .claude/" + local + ".")
    found = None
    for h in handlers(user) + [h for _, s in managed for h in handlers(s)]:
        args = h.get("args")
        if isinstance(h.get("command"), str) and isinstance(args, list) and len(args) == 2 \
                and args[0] == "-I" and isinstance(args[1], str) \
                and os.path.basename(args[1]) == "gh_guard.py":
            found = h
            break
    if found is None:
        faults.append("no PreToolUse entry in the user or managed settings runs the gh guard: one"
                      " whose matcher covers Bash and mcp__terminal__run_in_terminal, in exec form,"
                      " with an interpreter's absolute path as its command and -I and the"
                      " installed gh_guard.py as its arguments.")
        return faults
    command, hook = found["command"], found["args"][1]
    if not command.startswith("/") or not os.path.isfile(command) or "/shims/" in command:
        faults.append("the entry's interpreter is not an absolute path to an interpreter: "
                      + command + ".")
    if "if" in found:
        faults.append("the entry has an `if`, which does not match gh called by its path.")
    if not off(found.get("async")):
        faults.append("the entry is async, so it cannot block.")
    if not off(found.get("asyncRewake")):
        faults.append("the entry sets asyncRewake, so it runs in the background and cannot block.")
    if found.get("onFailure") != "block":
        faults.append("the entry lacks \"onFailure\": \"block\", so a hook that fails lets the"
                      " command run.")
    installed = os.path.dirname(os.path.realpath(hook))
    want = version_of(os.path.join(here, "gh_guard_lib.py"))
    have = version_of(os.path.join(installed, "gh_guard_lib.py"))
    if have is None:
        faults.append("the installed hook at " + hook + " holds no version line.")
    elif want is not None and have < want:
        faults.append("the installed hook is version " + str(have) + ", older than the reference's "
                      + str(want) + ".")
    elif have == want:
        for name in ("gh_guard.py", "gh_guard_lib.py", "check-leakage.sh"):
            if not same_bytes(os.path.join(here, name), os.path.join(installed, name)):
                faults.append("the installed " + name + " differs from the reference's at the same"
                              " version.")
    for name in snapshots_with_gh(config):
        faults.append("the shell snapshot " + name + " defines an alias or a function whose body"
                      " holds a gh word, which runs gh in every Bash call without the word.")
    if not faults:
        faults += probe(found)
    return faults


def run(argv, data):
    if argv[:1] == ["--check-registration"] and len(argv) == 2:
        result = check_registration(argv[1])
        if result == "skip":
            return (0, "", "skipped: there is no Claude Code configuration on this machine.\n")
        if not result:
            return PASS
        return (2, "", "".join("gate-sdd gh guard: not registered as installed: " + f + "\n"
                               for f in result))
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
