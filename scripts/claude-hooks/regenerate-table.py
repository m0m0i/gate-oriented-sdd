#!/usr/bin/env python3
"""regenerate-table.py — rewrite gh_guard_lib.py's table of gh's commands from gh's own help (#361).

    python3 scripts/claude-hooks/regenerate-table.py [path to gh]

Reads every command path from `gh help reference`, then each path's `--help` for its aliases and
its flags, and rewrites the block between the TABLE markers in gh_guard_lib.py. What each path
does (read, write, local state or arbitrary execution) and what each flag means beyond taking a
value are not in gh's help, so they stay where they are written by hand: KINDS and FLAG_ROLES in
gh_guard_lib.py. A path the table gains with no kind blocks until it is given one.
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(HERE, "gh_guard_lib.py")
BEGIN = "# BEGIN TABLE (regenerate-table.py writes this block; do not edit it by hand)\n"
END = "# END TABLE\n"


# An empty configuration, so that no alias or extension of this machine's enters the table.
CONFIG = tempfile.mkdtemp()


def gh(binary, *args):
    env = {"GH_CONFIG_DIR": CONFIG, "PATH": "/usr/bin:/bin", "HOME": os.environ.get("HOME", "/"), "NO_COLOR": "1",
           "GH_PAGER": "cat", "GH_NO_UPDATE_NOTIFIER": "1", "GH_TELEMETRY": "false",
           "LC_ALL": "C"}
    r = subprocess.run([binary] + list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       env=env, check=False)
    return r.stdout.decode("utf-8")


def paths(binary):
    out = []
    for line in gh(binary, "help", "reference").splitlines():
        m = re.match(r"#{2,} gh (.*)", line)
        if not m:
            continue
        words = []
        for w in m.group(1).split():
            if w[0] in "[<{-":
                break
            words.append(w)
        out.append(" ".join(words))
    return out


FLAG = re.compile(r"^\s+(?:-(\w), )?--([\w-]+)(\[=true\|false\])?(?: (\S+))?\s{2,}")


def help_of(binary, path):
    text = gh(binary, *(path.split() + ["--help"]))
    aliases, flags, section = [], [], None
    for line in text.splitlines():
        if line and not line.startswith(" "):
            section = line.strip()
            continue
        if section == "ALIASES" and line.strip():
            for a in line.split(","):
                a = a.strip()
                if a.startswith("gh "):
                    aliases.append(a[3:])
        elif section in ("FLAGS", "INHERITED FLAGS") and line.strip():
            m = FLAG.match(line + "  ")
            if not m:
                raise SystemExit("unreadable flag line for gh " + path + ": " + line)
            short, name, boolean, typ = m.groups()
            takes = boolean is None and typ is not None
            flags.append((("-" + short + ",") if short else "") + "--" + name + ("=" if takes else ""))
    return aliases, flags


def main():
    binary = shutil.which(sys.argv[1] if len(sys.argv) > 1 else "gh")
    if not binary:
        raise SystemExit("regenerate-table: no gh to read")
    version = re.match(r"gh version (\d+)\.(\d+)\.(\d+)", gh(binary, "--version"))
    if not version:
        raise SystemExit("gh --version printed no version")
    lines = [BEGIN, 'TABLE_VERSION = "%s.%s"\n' % version.groups()[:2],
             "# gh %s.%s.%s: <path>|<aliases, by ;>|<flags, by space; = takes a value>\n"
             % version.groups(), 'TABLE = """\n']
    # gh writes its default aliases (`co`) into a new configuration. They are configuration,
    # which a user can redefine, so they stay out of the table and block like any alias.
    configured = set(re.findall(r"^([^:\s]+):", gh(binary, "alias", "list"), re.M))
    root_aliases, root_flags = help_of(binary, "")
    lines.append("|" + ";".join(root_aliases) + "|" + " ".join(root_flags) + "\n")
    for path in paths(binary):
        if path.split()[0] in configured:
            continue
        aliases, flags = help_of(binary, path)
        lines.append(path + "|" + ";".join(aliases) + "|" + " ".join(flags) + "\n")
    lines.append('"""\n')
    lines.append(END)
    text = open(LIB).read()
    a, b = text.index(BEGIN), text.index(END) + len(END)
    open(LIB, "w").write(text[:a] + "".join(lines) + text[b:])
    shutil.rmtree(CONFIG, ignore_errors=True)
    print("regenerate-table: %d paths from gh %s.%s.%s" % ((len(lines) - 6,) + version.groups()))


if __name__ == "__main__":
    main()
