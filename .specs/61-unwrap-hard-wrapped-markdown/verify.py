#!/usr/bin/env python3
"""Prove the reflow preserved structure and content, using a check that can fail.

The self-test runs first and unconditionally, and it asserts on BOTH failure classes,
because the first version of this file only asserted on one. It compared `unwrap(unwrap(x))`
against `unwrap(x)` — true by construction for any idempotent transform — and reported
"0 render changes" on a diff that collapsed three issue templates' front matter and merged
every heading into the paragraph beneath it. Every word survived, so a word-level check saw
nothing. See canon.py.
"""
import subprocess
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from canon import canon  # noqa: E402
from unwrap import unwrap  # noqa: E402


def selftest():
    fm = "---\nname: Chore\nabout: Work\n---\n\n## Heading\n\nProse\nwrapped.\n"
    assert canon(fm) == canon(unwrap(fm)), "transform alters a known-good fixture"
    assert canon(fm) != canon("---\nname: Chore about: Work\n---\n\n## Heading Prose wrapped.\n"), \
        "cannot detect front-matter collapse or heading absorption — the defect that shipped"
    assert canon("- one\n- two\n") != canon("- one two\n"), "cannot detect a merged list item"
    assert canon("hello world\n") != canon("hello there\n"), "cannot detect an altered word"
    assert unwrap("- A: 1\n- B: 2\n") == "- A: 1\n- B: 2\n", "list items were joined"
    print("selftest: detects structural AND content defects; never joins list items")


if __name__ == "__main__":
    selftest()
    ref = sys.argv[1]
    files = subprocess.run(["git", "ls-files", "*.md"], capture_output=True, text=True).stdout.split()
    checked = bad = 0
    for f in files:
        old = subprocess.run(["git", "show", f"{ref}:{f}"], capture_output=True, text=True)
        if old.returncode:
            continue
        checked += 1
        if canon(old.stdout) != canon(open(f).read()):
            bad += 1
            print(f"  STRUCTURE OR CONTENT CHANGED: {f}", file=sys.stderr)
    print(f"verify: {checked} file(s) compared against {ref}, {bad} change(s)")
    sys.exit(1 if bad else 0)
