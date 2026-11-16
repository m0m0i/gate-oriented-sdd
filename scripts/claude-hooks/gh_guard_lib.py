"""gh_guard_lib — decides whether a Bash command may run, for gh_guard.py (#361).

run() takes the hook's arguments and its standard input, and returns (code, stdout, stderr):
(0, "", "") passes, (0, <one systemMessage object>, "") passes with a warning, and (2, "",
<reason>) blocks. It never exits and never prints; gh_guard.py turns anything else into a block.
It must run on Python 3.9: no syntax or library newer than that.
"""

import json
import os
import re

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


ADVICE_UNEXPLAINED = ("Run gh as a plain command: `gh <subcommand> ...`, by its name or a path that"
                      " ends in /gh, not through a variable, a substitution or a wrapper the hook"
                      " does not list.")


# The fast path: a command passes unread unless `gh` stands at a word boundary once quotes and
# backslashes are taken out. No file is read and no pattern is loaded before this (#361 AC4).
_GH_WORD = re.compile(r"\bgh\b", re.ASCII)


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
                raise Unsupported("a function definition or an array" if words or assigns
                                  else "a `(` inside a command")
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
            if end:
                raise Unsupported("a " + end + " is missing")
            return True
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

    __slots__ = ("vars", "exported", "tainted", "cwds", "files", "named", "events")

    def __init__(self, home, cwd):
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
        return c

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

    __slots__ = ("words", "assigns", "env", "redirs", "state", "piped", "simple")

    def __init__(self, words, assigns, env, redirs, state, piped, simple):
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


def git_quiet(vals):
    """True when git, given these arguments, runs none of them as a command."""
    k = 0
    while k < len(vals):
        a = vals[k]
        if a is None:
            return False
        if a in ("-C", "--git-dir", "--work-tree", "--namespace"):
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
        if isinstance(command, Group):
            inner = state if command.kind == "group" else state.copy()
            self.redirect_targets(command.redirs, inner)
            self.walk(command.body, inner)
            return
        self.simple(command, state, piped, downstream)

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
            self.problem("A command's name cannot be known before it runs, so the hook cannot"
                         " tell what it runs.")
            return
        base = _name(name)
        args = cmd.words[k + 1:]
        if is_gh(name):
            # The words after gh are what it sends; reading them is the classifier's work.
            self.invocations.append(Invocation(args, list(cmd.assigns), env, cmd.redirs,
                                               state.copy(), piped, cmd))
            self.check_words(cmd.words[:k], state, quiet=True)
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
        if base in ("git",) and k + 1 < len(vals) and vals[k + 1] in ("remote", "config"):
            state.events.append("git " + vals[k + 1])
        if base == "unset":
            for v in vals[k + 1:]:
                state.vars.pop(v or "", None)
                state.events.append("unset")

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
            if appends:
                if old is None or old.content is None or text.content is None:
                    text = Text(None, text.gh or (old is not None and old.gh), text.label)
                else:
                    text = Text(old.content + text.content, text.gh or old.gh, text.label)
            state.files[p] = text

    def printed(self, base, vals):
        if any(v is None for v in vals):
            return None, any(v is None or mentions_gh(v) for v in vals)
        gh = any(mentions_gh(v) for v in vals)
        if base == "echo":
            if vals and vals[0].startswith("-"):
                return None, gh
            text = " ".join(vals)
            return (None if "\\" in text else text + "\n"), gh
        if not vals or "%" in vals[0] or "\\" in vals[0] or len(vals) > 1:
            return None, gh
        return vals[0], gh

    def find(self, script):
        self.quiet_gh = []
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


def judge(inv):
    """The decision for one gh invocation, or None when it may run. Until the table lands,
    every subcommand is one the hook does not know, which blocks."""
    first = inv.words[0].literal(inv.state.env()) if inv.words else None
    return block("gh " + (first if first and first.isalnum() else "<this subcommand>")
                 + " is not a gh command the hook knows, so it can run anything: an alias,"
                 " an extension, or a command newer than the hook's table.",
                 "Run it yourself outside the session, or file the gap against the hook.")


def decide(command, cwd, home):
    """The slow path, for a command that holds a gh word."""
    found = Finder(home, cwd).find(parse(command))
    if found.problems:
        return block(found.problems[0], ADVICE_UNEXPLAINED)
    for inv in found.invocations:
        result = judge(inv)
        if result is not None:
            return result
    return PASS


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
    return decide(command, cwd, os.environ.get("HOME"))
