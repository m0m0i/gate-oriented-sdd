#!/usr/bin/env python3
"""The README's Status claims must agree with what they describe.

#115: three claims in `## Status` were false at once. They drifted by different mechanisms, and
only one of those mechanisms was a reviewer missing a count.

**The version is the instructive one.** `v0.4.3` was written at 0.4.3 and survived three releases
*and an edit to the same file* — nothing tied it to the manifest bump, and `check-manifests.py`
verifies the two manifests agree with each other while knowing nothing about the README. So the
claim could only be corrected by someone noticing, which took eight days.

**What this guard deliberately does not check: a count of gate behaviours.** That number's only
source is running `scripts/test-gates.sh`, already the slowest validator, so guarding it would
double it on every turn to check one integer. The number was removed from the README instead —
one claim made checkable, the other made unnecessary, and the second is the stronger fix wherever
it is available. This docstring is the record of that choice, so the number does not quietly come
back.

Run from the repository root. Exits 0 when every claim agrees with its source.
"""
import json
import pathlib
import re
import sys

READMES = ("README.md", "README.ja.md")
MANIFEST = pathlib.Path("plugin.json")

#: The version, as `**v0.7.0 — pre-release.**` / `**v0.7.0、pre-release です。**`. The language
#: differs after the number and the number does not, so one pattern serves both.
VERSION = re.compile(r"\*\*v(\d+\.\d+\.\d+)[ ,、]")

#: How the receipts were obtained. English says "all but three"; Japanese says "3件を除いて".
#: Both are matched as a written-out or numeric count, because #115's defect was a word.
INLINE_EN = re.compile(r"from a spawned reviewer on all but (\w+)")
INLINE_JA = re.compile(r"(\d+|[一二三四五六七八九十]+)件を除いて")
WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
         "七": 7, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6}

#: A count of gate behaviours must NOT appear. See the docstring: it was removed rather than
#: guarded, and a guard that only checks what is present cannot notice it coming back.
BEHAVIOUR_COUNT = re.compile(r"(?:guards['’]|ガードの)\s*(\d+)\s*(?:behaviours|通り)")


def receipts():
    """(total, inline) across live and archived specs — the source the README describes."""
    total = inline = 0
    for d in (pathlib.Path(".specs"), pathlib.Path(".specs/_archive")):
        for f in sorted(d.glob("*/.review-receipt")):
            total += 1
            if "reviewed_by=inline" in f.read_text():
                inline += 1
    return total, inline


def as_int(token):
    if token.isdigit():
        return int(token)
    return WORDS.get(token.lower())


def main():
    problems = []

    if not MANIFEST.is_file():
        problems.append(f"{MANIFEST} does not exist, so the README's version claim has no source")
        version = None
    else:
        version = json.loads(MANIFEST.read_text())["version"]

    total, inline = receipts()
    if total == 0:
        # Not "nothing to check". Zero receipts means the source vanished, and comparing a claim
        # against an empty set would agree with anything.
        problems.append("no review receipts found, so the receipts claim cannot be verified")

    for name in READMES:
        path = pathlib.Path(name)
        if not path.is_file():
            problems.append(f"{name}: does not exist")
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            problems.append(f"{name}: cannot be read ({exc.strerror})")
            continue

        m = VERSION.search(text)
        if not m:
            problems.append(f"{name}: states no version in the form `**v<x.y.z>`")
        elif version is not None and m.group(1) != version:
            problems.append(
                f"{name}: says v{m.group(1)}, but plugin.json says {version}. "
                f"The version is bumped as a step of `implement` after the receipt; this line "
                f"is not carried by that step and has drifted three releases before."
            )

        if (b := BEHAVIOUR_COUNT.search(text)) is not None:
            problems.append(
                f"{name}: states `{b.group(1)}` gate/guard behaviours. That number was removed on "
                f"purpose (#115) — its only source is running scripts/test-gates.sh, already the "
                f"slowest validator. Name the suite, not a count."
            )

        pat = INLINE_JA if name.endswith(".ja.md") else INLINE_EN
        w = pat.search(text)
        if not w:
            problems.append(f"{name}: does not say how many receipts were not from a spawned reviewer")
        elif (claimed := as_int(w.group(1))) is None:
            problems.append(f"{name}: receipt count `{w.group(1)}` is not a number this guard can read")
        elif total and claimed != inline:
            problems.append(
                f"{name}: claims all but {w.group(1)} receipts came from a spawned reviewer, "
                f"but {inline} of {total} say reviewed_by=inline"
            )

    if problems:
        print("check-readme-claims FAILED", file=sys.stderr)
        for p in problems:
            print(f"  {p}", file=sys.stderr)
        raise SystemExit(1)

    print(
        f"check-readme-claims: {len(READMES)} README(s) agree — v{version}, "
        f"{inline} of {total} receipts inline, no behaviour count asserted"
    )


if __name__ == "__main__":
    main()
