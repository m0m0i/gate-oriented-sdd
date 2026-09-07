#!/usr/bin/env python3
"""Count hand-wrapped blocks. Shared by the scope survey, AC1, and the baseline.

A block is hand-wrapped when it spans more than one physical line and every line is short
enough that the break was a choice rather than an artefact. Fenced code, tables, headings
and front matter are excluded: their line breaks are structural.
"""
import subprocess
import sys

WIDTH = 105


def blocks(path):
    out, fence, block = [], False, []
    for ln in open(path).read().split("\n"):
        if ln.strip().startswith("```"):
            fence = not fence
            if block:
                out.append(block)
                block = []
            continue
        if fence:
            continue
        s = ln.strip()
        if not s or s.startswith("|") or s.startswith("#") or s == "---":
            if block:
                out.append(block)
                block = []
            continue
        block.append(ln)
    if block:
        out.append(block)
    return out


def wrapped(path):
    return sum(1 for b in blocks(path) if len(b) > 1 and max(len(l) for l in b) <= WIDTH)


if __name__ == "__main__":
    files = sys.argv[1:] or subprocess.run(
        ["git", "ls-files", "*.md"], capture_output=True, text=True
    ).stdout.split()
    total = 0
    for f in sorted(files):
        n = wrapped(f)
        if n:
            print(f"{n:4d}  {f}")
            total += n
    print(f"\n{total} hand-wrapped block(s) across "
          f"{sum(1 for f in files if wrapped(f))} of {len(files)} file(s)")
