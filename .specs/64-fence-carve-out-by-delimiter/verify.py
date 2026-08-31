#!/usr/bin/env python3
"""AC4 and AC6 against the base revision, with a check that can fail.

Deliberately independent of `scripts/check-markdown-fences.py`. That guard asks whether the
tree satisfies a property NOW; this asks whether the change did only what it was meant to do,
by comparing against `3df25b0`. Sharing a predicate between the two would make the second a
restatement of the first — which is exactly how #61's verifier came to compare
`unwrap(unwrap(x))` against `unwrap(x)` and report success on a destructive diff.

AC6 was amended before this ran, and the reason is worth keeping here. It first asked for
rendering equivalence. A fenced block's content is literal, so joining two lines inside one
genuinely changes what the fence renders; the criterion would have had to be waived on the
only two files it needed to judge. `.specs/61-.../observations.md`: "it proves the HTML is
unchanged, and the HTML was never the thing at risk." For a join, the property that matters is
that the word stream survives and the edit stayed inside the fence.

Usage: python3 .specs/64-fence-carve-out-by-delimiter/verify.py [base-rev]
"""
import re
import subprocess
import sys

BASE = sys.argv[1] if len(sys.argv) > 1 else "3df25b0"
FENCE = re.compile(r"^(\s*)(`{3,}|~{3,})\s*(\S*)")

#: Untagged fences holding a format where a line break is meaningful. Unwrapping any of these
#: would destroy the format, so they are pinned byte-for-byte rather than merely unmodified by
#: intent. `check-receipt-schema.py` independently covers the receipt block across 3 copies.
LINE_SENSITIVE = (
    "skills/implement/SKILL.md",                     # the reviewed_sha= receipt block
    "agents/_shared/reviewer-contract.md",           # [SEVERITY] <file>:<line>
    ".claude/agents/_shared/reviewer-contract.md",   # ...and this repo's own mirror of it
)

#: The only files whose ```markdown fence bodies this branch changes.
JOINED = ("skills/backlog/SKILL.md", "skills/spec/templates.md")


def show(rev, path):
    r = subprocess.run(["git", "show", f"{rev}:{path}"], capture_output=True, text=True)
    if r.returncode:
        # An unreadable side must not read as a pass. #61's verifier exited 0 on a ref that
        # did not resolve, having compared nothing. See #16 and #39.
        sys.exit(f"verify FAILED — cannot read {rev}:{path}; nothing was compared")
    return r.stdout


def split_fences(text):
    """(every line outside a ```markdown fence, [bodies of the ```markdown fences])."""
    lines, i, outside, bodies = text.split("\n"), 0, [], []
    while i < len(lines):
        m = FENCE.match(lines[i])
        if not m:
            outside.append(lines[i])
            i += 1
            continue
        delim, tag = m.group(2), m.group(3).lower()
        outside.append(lines[i])
        i += 1
        body = []
        while i < len(lines):
            c = FENCE.match(lines[i])
            if c and c.group(2)[0] == delim[0] and len(c.group(2)) >= len(delim) and not c.group(3):
                break
            body.append(lines[i])
            i += 1
        # A non-Markdown fence's body is held to the same standard as ordinary text: byte
        # identity. Only a ```markdown body is allowed to have lost line breaks.
        if tag in ("markdown", "md"):
            bodies.append(body)
        else:
            outside.extend(body)
        if i < len(lines):
            outside.append(lines[i])
            i += 1
    return outside, bodies


def words(bodies):
    return [" ".join(b).split() for b in bodies]


if __name__ == "__main__":
    failures = []

    print(f"AC4 — fences holding a line-sensitive format, byte-identical to {BASE}")
    for path in LINE_SENSITIVE:
        same = show(BASE, path) == open(path).read()
        print(f"  {'OK  ' if same else 'FAIL'} {path}")
        if not same:
            failures.append(f"AC4: {path} changed")

    print("\nAC6 — the files whose ```markdown fence bodies changed")
    for path in JOINED:
        o_out, o_bod = split_fences(show(BASE, path))
        n_out, n_bod = split_fences(open(path).read())
        checks = {
            "outside the markdown fences, byte-identical": o_out == n_out,
            f"same number of markdown fences ({len(n_bod)})": len(o_bod) == len(n_bod),
            "fence word streams identical, in order": words(o_bod) == words(n_bod),
        }
        removed = sum(len(a) for a in o_bod) - sum(len(b) for b in n_bod)
        print(f"  {path}  ({removed} physical line(s) removed inside fences)")
        for label, ok in checks.items():
            print(f"    {'OK  ' if ok else 'FAIL'} {label}")
            if not ok:
                failures.append(f"AC6: {path} — {label}")

    # A check that cannot fail is decoration. Drop a word from a fence body and require the
    # comparison to notice, so a green run above means something.
    print("\nnegative control — a word dropped from a fence body must be caught")
    _, base_bodies = split_fences(show(BASE, JOINED[0]))
    tampered = [b[:] for b in base_bodies]
    for k, line in enumerate(tampered[0]):
        if "Ordered," in line:
            tampered[0][k] = line.replace("Ordered, ", "")
            break
    else:
        failures.append("negative control could not be constructed — the fixture line is gone")
        tampered = base_bodies
    caught = words(base_bodies) != words(tampered)
    print(f"  {'OK  ' if caught else 'FAIL'} tampered fence detected")
    if not caught:
        failures.append("the comparison cannot detect a dropped word")

    if failures:
        print("\nverify FAILED", file=sys.stderr)
        for f in failures:
            print(f"  {f}", file=sys.stderr)
        sys.exit(1)
    print("\nverify: AC4 and AC6 hold, and the comparison was shown to be able to fail")
