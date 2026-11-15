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
