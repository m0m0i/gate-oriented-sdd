#!/usr/bin/env python3
"""Prove the transform preserved meaning, and prove this check can fail.

Two files that normalise identically render identically, so this is exact rather than a
spot inspection. The self-test runs first and unconditionally: a verifier nobody has seen
fail is indistinguishable from one that always passes, which is the defect this repository
exists to reject.
"""
import subprocess
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from unwrap import normalise, unwrap  # noqa: E402


def selftest():
    src = "A paragraph\nwrapped by hand.\n\n- an item\n  continued\n- a sibling\n"
    assert normalise(unwrap(src)) == normalise(src)
    assert normalise(unwrap(src.replace("paragraph", "para", 1))) != normalise(src), (
        "the checker cannot fail — it would pass a real difference"
    )
    assert unwrap("- A: 1\n- B: 2\n") == "- A: 1\n- B: 2\n", "list items were joined"
    print("selftest: the check detects an altered phrase and never joins list items")


if __name__ == "__main__":
    selftest()
    ref = sys.argv[1]
    files = subprocess.run(["git", "ls-files", "*.md"], capture_output=True, text=True).stdout.split()
    checked = mismatched = 0
    for f in files:
        old = subprocess.run(["git", "show", f"{ref}:{f}"], capture_output=True, text=True)
        if old.returncode:
            continue  # new on this branch, nothing to compare against
        new = open(f).read()
        checked += 1
        if normalise(old.stdout) != normalise(new):
            mismatched += 1
            print(f"  RENDER CHANGED: {f}", file=sys.stderr)
    print(f"verify: {checked} file(s) compared against {ref}, {mismatched} render change(s)")
    sys.exit(1 if mismatched else 0)
