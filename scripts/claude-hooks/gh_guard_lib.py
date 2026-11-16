"""gh_guard_lib — decides whether a Bash command may run, for gh_guard.py (#361).

run() takes the hook's arguments and its standard input, and returns (code, stdout, stderr):
(0, "", "") passes, (0, <one systemMessage object>, "") passes with a warning, and (2, "",
<reason>) blocks. It never exits and never prints; gh_guard.py turns anything else into a block.
It must run on Python 3.9: no syntax or library newer than that.
"""

import json
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
        last = 0
        while True:
            try:
                self.blank_lines()
            except Unsupported as why:
                # A here-document's lines follow the item that declared it, so it goes too.
                if not top:
                    raise
                return Script(items[:-1], (self.s[last:], why.reason))
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
                return Script(items, (self.s[start:], why.reason))
            items.append((node, sep))
            last = start
        if self.pending:
            if not top:
                raise Unsupported("a here-document has no end line")
            return Script(items[:-1], (self.s[last:], "a here-document has no end line"))
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


def decide(command, cwd):
    """The slow path, for a command that holds a gh word."""
    return block("The command holds a gh word the hook cannot account for, so it cannot tell"
                 " what the command runs.", ADVICE_UNEXPLAINED)


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
    return decide(command, cwd)
