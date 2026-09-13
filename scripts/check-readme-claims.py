#!/usr/bin/env python3
"""The README's Status claims must agree with what they describe.

**The subject is the README, not `## Status`.** Scoping to the section is what shipped the defect
this guard exists for: the behaviour count was removed from `## Status` and left standing a section
above, in both languages, while the guard certified its absence over the whole file. A scope drawn
from where a defect was reported is not a scope drawn around where that defect lives.

#115: three claims in `## Status` were false at once. They drifted by different mechanisms, and
only one of those mechanisms was a reviewer missing a count.

**The version is the instructive one.** `v0.4.3` was written at 0.4.3 and survived three releases
*and an edit to the same file* — nothing tied it to the manifest bump, and `check-manifests.py`
verifies the two manifests agree with each other while knowing nothing about the README. So the
claim could only be corrected by someone noticing, which took eight days.

**What this guard deliberately does not check: the VALUE of a count of gate behaviours** — it
enforces that no such count appears at all. That number's only
source is running `scripts/test-gates.sh`, already the slowest validator, so guarding it would
double it on every turn to check one integer. The number was removed from the README instead —
one claim made checkable, the other made unnecessary, and the second is the stronger fix wherever
it is available. This docstring is the record of that choice, so the number does not quietly come
back.

Run from the repository root. Exits 0 when every claim agrees with its source.
"""
import json
import os
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
#: The Japanese states the count TWICE — `3件を除いて` … `その3件は inline` — where the English
#: states it once, so the two languages have different drift surfaces. Both are read, but the
#: VALUE comes only from the anchored one.
#:
#: The anchor is not optional. An earlier cut dropped it to reach the second occurrence and
#: matched any `N件` in the file — and 件 is one of the most common counters in Japanese. That is
#: a false red on a sentence about anything else, and a fail-open if the receipt sentence is ever
#: deleted while some unrelated `N件` remains: `search` would find it, it would happen to equal
#: the corpus, and the guard would pass over a README that no longer makes the claim. The English
#: kept its anchor throughout; this restores the symmetry.
INLINE_JA = re.compile(r"(\d+|[一二三四五六七八九十]+)件(?=を除いて)")
#: The echo, which must agree with the anchored value. Checked only once the anchor matched.
JA_ECHO = re.compile(r"その(\d+|[一二三四五六七八九十]+)件")

WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
         "eight": 8, "nine": 9, "ten": 10,
         "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}

#: A count of gate/guard behaviours must NOT appear ANYWHERE in the README — not merely in
#: `## Status`. The first cut of this pattern was written around the one sentence the spec was
#: looking at and missed the one a section above it, which said 67 while the suite said 78, in
#: BOTH languages: the English puts the digits before the noun ("67 paths across the gates and
#: guards") and the Japanese reads ガードを合わせた67通り. The guard then printed "no behaviour
#: count asserted" over two files that asserted one — a certification broader than the check.
#:
#: So: any digit within a short window of gates/guards, in either direction, in either language,
#: regardless of the noun. Deliberately loose — this is an ACCUSING pattern, and its failure
#: direction is a false red on a sentence that mentions a number near "gates", which a human
#: resolves in one edit. The opposite failure is what shipped.
BEHAVIOUR_COUNT = re.compile(
    r"(?:\d+\s*(?:[つ本件個]|通り|パターン|種類|種)?\s*(?:の|もの)?\s*"
    r"(?:paths?|behaviours?|behaviors?|通り|経路|挙動|パス|パターン|分岐)"
    r"[^.。\n]{0,45}?(?:gates?|guards?|ゲート|ガード)"
    r"|(?:gates?|guards?|ゲート|ガード)[^.。\n]{0,45}?"
    r"\d+\s*(?:[つ本件個]|通り|パターン|種類|種)?\s*(?:の|もの)?\s*"
    r"(?:paths?|behaviours?|behaviors?|通り|経路|挙動|パス|パターン|分岐))"
)


#: `reviewed_by` is a THREE-way fact and the README's sentence has room for two. An absent field
#: — receipts predate #105 — must not be read as `subagent`: the reviewer contract says silence is
#: not evidence of independence, which is the whole reason the field exists.
REVIEWED_BY = re.compile(r"^reviewed_by=(\S+)$", re.M)


def receipts():
    """(total, inline, unknown, problems) across live and archived specs.

    Walked with `os.scandir` rather than `Path.glob`, because glob swallows the OSError from an
    unreadable directory and returns fewer entries with no complaint — a partially scanned corpus
    that agrees. That is #16's shape, and `test-gates.sh` already pins it for a sibling guard.
    """
    total = inline = unknown = 0
    problems = []
    for d in (pathlib.Path(".specs"), pathlib.Path(".specs/_archive")):
        if not d.is_dir():
            continue
        try:
            entries = sorted(e.path for e in os.scandir(d) if e.is_dir())
        except OSError as exc:
            problems.append(f"{d}: cannot be read ({exc.strerror}), so the receipt corpus is partial")
            continue
        for sub in entries:
            f = pathlib.Path(sub, ".review-receipt")
            if not f.is_file():
                continue
            total += 1
            try:
                text = f.read_text()
            except OSError as exc:
                problems.append(f"{f}: cannot be read ({exc.strerror})")
                continue
            m = REVIEWED_BY.search(text)
            if m is None:
                unknown += 1
            elif m.group(1) == "inline":
                inline += 1
    return total, inline, unknown, problems


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

    total, inline, unknown, receipt_problems = receipts()
    problems += receipt_problems
    if unknown:
        problems.append(
            f"{unknown} receipt(s) carry no `reviewed_by` field. Silence is not evidence of "
            f"independence — the README's sentence has room for spawned and inline only, so an "
            f"unknown receipt is a claim this guard cannot verify."
        )
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

        found = {v for v in VERSION.findall(text)}
        m = VERSION.search(text)
        if len(found) > 1:
            # `README.md:41` is this repository's own proof that a Status claim gets restated
            # outside the section anyone is watching. If that ever happens to the version, a
            # first-match check verifies the decoy.
            problems.append(f"{name}: states more than one version — {sorted(found)}")
        if not m:
            problems.append(f"{name}: states no version in the form `**v<x.y.z>`")
        elif version is not None and m.group(1) != version:
            problems.append(
                f"{name}: says v{m.group(1)}, but plugin.json says {version}. "
                f"The version is bumped as a step of `implement` after the receipt; this line "
                f"is not carried by that step and has drifted three releases before."
            )

        for b in BEHAVIOUR_COUNT.finditer(text):
            problems.append(
                f"{name}: counts gates/guards — `{b.group(0).strip()}`. That number was removed on "
                f"purpose (#115) — its only source is running scripts/test-gates.sh, already the "
                f"slowest validator. Name the suite, not a count."
            )

        pat = INLINE_JA if name.endswith(".ja.md") else INLINE_EN
        w = pat.search(text)
        if name.endswith(".ja.md") and w is not None:
            echo = JA_ECHO.search(text)
            if echo is not None and echo.group(1) != w.group(1):
                problems.append(
                    f"{name}: states the receipt count twice and they disagree — "
                    f"`{w.group(1)}件を除いて` against `その{echo.group(1)}件`. An edit that moves "
                    f"one and not the other leaves an internally contradictory sentence."
                )
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
