"""gh_guard.py — a Claude Code PreToolUse hook that scans what a gh write would publish (#361).

Registered in the maintainer's user-level settings, in exec form, as `<python> -I <this file>`.
The decision is gh_guard_lib's; this file is the frame that makes every way out of it a block
unless the module returned a pass. It must run on Python 3.9.

The protocol, measured on Claude Code 2.1.325: exit 2 with a reason on stderr blocks; exit 0
with nothing on stdout passes; exit 0 with one {"systemMessage": ...} object passes with a
warning to the user. A decision is never printed as JSON, because a JSON deny cut short reads
as plain text, which passes (#361).
"""

import sys

HEAD = "gate-sdd gh guard: blocked. "


def _finish(code, out, err):
    # Writes what was decided and leaves by os._exit, so nothing after it can change the code.
    import os
    try:
        if out:
            sys.__stdout__.write(out)
        sys.__stdout__.flush()
    except BaseException:
        code = 2
    try:
        if err:
            sys.__stderr__.write(err)
        sys.__stderr__.flush()
    except BaseException:
        pass
    os._exit(code)


def _failed(error, starting):
    # The type is printed and the message is not: a message can hold the text being scanned.
    name = type(error).__name__
    if not name.replace("_", "").isalnum():
        name = "an exception"
    if starting:
        detail = "The hook could not start (" + name + ")"
        module = getattr(error, "name", None)
        if isinstance(error, ImportError) and isinstance(module, str) \
                and module.replace("_", "").replace(".", "").isalnum():
            detail += ": the module " + module + " could not be imported"
        return (HEAD + detail + ", so no Bash command can run until it is reinstalled.\n"
                "  Run scripts/install-gh-hook.sh from a gate-oriented-sdd checkout, or edit the\n"
                "  PreToolUse entry in ~/.claude/settings.json with the Edit tool.\n")
    return (HEAD + "The hook failed with " + name + " before it could decide, so the command\n"
            "  was not run. The exception's message is withheld: it can hold the text being scanned.\n")


def _well_formed(out):
    # A pass prints nothing, or one object whose only key is systemMessage, holding a string.
    if out == "":
        return True
    import json
    try:
        value = json.loads(out)
    except BaseException:
        return False
    return isinstance(value, dict) and list(value) == ["systemMessage"] \
        and isinstance(value["systemMessage"], str)


def main():
    starting = True
    try:
        import io
        import os
        sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
        # Whatever the module prints is discarded: only _finish writes the hook's stdout.
        sys.stdout = io.StringIO()
        import gh_guard_lib
        starting = False
        data = sys.stdin.buffer.read()
        result = gh_guard_lib.run(sys.argv[1:], data)
        code, out, err = result
    except BaseException as error:  # SystemExit included: the module never exits (#361)
        _finish(2, "", _failed(error, starting))
        return
    if type(code) is not int or code not in (0, 2) or not isinstance(out, str) \
            or not isinstance(err, str):
        _finish(2, "", HEAD + "The hook's module returned no decision it can act on, so the\n"
                "  command was not run.\n")
        return
    checking = sys.argv[1:2] == ["--check-registration"]
    if code == 2:
        _finish(2, "", err if err.startswith(HEAD) or checking else HEAD + "The hook gave no reason.\n")
        return
    if checking:
        _finish(0, "", err)
        return
    if not _well_formed(out):
        _finish(2, "", HEAD + "The hook's module printed a pass that is not one systemMessage,\n"
                "  so the command was not run.\n")
        return
    _finish(0, out, "")


if __name__ == "__main__":
    try:
        main()
    except BaseException:
        import os
        os._exit(2)
