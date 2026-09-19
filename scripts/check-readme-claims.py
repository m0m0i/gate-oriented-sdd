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
import urllib.parse

READMES = ("README.md", "README.ja.md")
MANIFEST = pathlib.Path("plugin.json")

#: The version literal this guard used to verify, as `**v0.7.0 — pre-release.**` /
#: `**v0.7.0、pre-release です。**`. #133 removed it: the README no longer states a version, it
#: renders one from the manifest, so there is nothing left to disagree. The pattern is kept and
#: INVERTED — it now fails when it matches — because the number coming back is the root cause
#: returning, and an editor who reads the badge as decoration would reintroduce it.
VERSION = re.compile(r"\*\*v(\d+\.\d+\.\d+)")
#: No trailing delimiter: the first cut required a space or a Japanese comma after the
#: number and so let `**v1.2.3**` through — the root cause returning in a slightly
#: different costume. Broadening to a bare `v1.2.3` is deliberately NOT done: it would
#: fire on `Antigravity CLI 1.1.17` in the tested-against line, which is a different claim.

#: Any shields.io badge in the file. Deliberately loose: the question this answers is "is there
#: a version badge at all", and the narrower questions — is it dynamic, does it read OUR
#: manifest — are asked separately so their failures name different causes.
BADGE = re.compile(r"https://img\.shields\.io/[^\s)\]]+")
#: A stated limit, like the docstring's other ones: this is TEXTUAL. A badge inside an HTML
#: comment or a fenced example still counts as present here, while the rendered page shows no
#: version at all. Left as a limit rather than closed, because stripping comments buys a
#: false-block risk for a hazard that takes a deliberate edit and is visible to any reader.

#: The dynamic form, which is the only one that cannot drift. Matched on the path rather than
#: the whole URL so that reordering query parameters is not a failure.
DYNAMIC = "/badge/dynamic/"
#: A version baked into a badge's own URL. Three components deliberately: `Apache_2.0` in a
#: licence badge has two, and failing on that would be a gate firing on an ordinary edit.
BAKED_VERSION = re.compile(r"v?\d+\.\d+\.\d+")
#: What the badge must read. "Dynamic" on its own is not the property that matters — a dynamic
#: badge pointed at a fork or at `.claude-plugin/plugin.json` still renders a number, and a
#: wrong number rendered confidently is worse than no number at all.
BADGE_SOURCE = "https://raw.githubusercontent.com/m0m0i/gate-oriented-sdd/main/plugin.json"
#: The field it must ask for. `$.name` under a version label renders "gate-sdd" as the version.
BADGE_QUERY = "$.version"
#: Which dynamic badge is the VERSION badge. Selecting on `/badge/dynamic/` alone made the
#: subject "any dynamic badge", so a later badge measuring anything else would have failed for
#: reading its own source — a gate firing on an edit that broke nothing (LV-2). Selecting by
#: label fails CLOSED: rename it and no version badge is found, which is the absence branch.
BADGE_LABEL = "gate-sdd"

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
JA_ECHO = re.compile(r"その(\d+|[一二三四五六七八九十]+)件(?=は\s*inline)")

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
    r"(?:\d+\s*(?:[つ本件個]|通り|パターン|種類|種|ケース)?\s*(?:の|もの)?\s*"
    r"(?:paths?|behaviours?|behaviors?|通り|経路|挙動|パス|パターン|分岐)"
    r"[^.。\n]{0,45}?(?:gates?|guards?|ゲート|ガード)"
    r"|(?:gates?|guards?|ゲート|ガード)[^.。\n]{0,45}?"
    r"\d+\s*(?:[つ本件個]|通り|パターン|種類|種|ケース)?\s*(?:の|もの)?\s*"
    r"(?:paths?|behaviours?|behaviors?|通り|経路|挙動|パス|パターン|分岐))"
)

#: Two gaps, named because an unrecorded one is how the round-1 defect survived.
#:
#: 1. **A trailing bare counter is missed** — 「…挙動を67件」, 「…を67個」 — because a counter can
#:    never terminate a match; a list-noun must follow. Letting it terminate would re-open
#:    「3件を除いて」 and 「13個の skill」, whose only remaining protection would be the 45-character
#:    proximity window. This pattern has already been wrong in BOTH directions on this branch, and
#:    here the two failure modes are closest together, so this is recorded rather than swung at a
#:    third time.
#: 2. **English `cases` is not matched**, deliberately. `ケース` lives in the counter group above,
#:    where a list-noun must follow it, so 「4つのケース」 stays green by construction. English has
#:    no equivalent safe position — `cases` can only be a noun — and the eval sentence in the same
#:    `## Status` paragraph says "its four cases are authored". So "the gates' 67 cases" is missed,
#:    and that is a chosen trade rather than an oversight.


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

        # The prohibition. The badge removed the second source; it cannot stop anyone adding
        # one back, and every badge check below still passes while the prose disagrees. Note it
        # fails even when the number is currently CORRECT: agreement today is not the property,
        # two sources that can diverge tomorrow is the defect, and a check that fired only on a
        # mismatch would wait for exactly the drift #133 exists to prevent.
        for stale in sorted(set(VERSION.findall(text))):
            problems.append(
                f"{name}: states a version in prose — `v{stale}`. The version is rendered from "
                f"{MANIFEST} by the badge (#133); writing it here restores the second source "
                f"that drifted three releases on #115, and it fails here whether or not the "
                f"two agree today."
            )

        badges = BADGE.findall(text)
        dynamic = [
            b for b in badges
            if DYNAMIC in b
            and (urllib.parse.parse_qs(urllib.parse.urlsplit(b).query).get("label") or [""])[0]
            == BADGE_LABEL
        ]
        for b in dynamic:
            # Parsed, not string-matched. A guard comparing the whole URL literally fails when
            # someone reorders the query string, which changes nothing — and a gate that fires
            # on an ordinary edit is one people switch off (LV-2).
            q = urllib.parse.parse_qs(urllib.parse.urlsplit(b).query)
            got = (q.get("url") or [""])[0]
            if got != BADGE_SOURCE:
                problems.append(
                    f"{name}: the version badge reads `{got or '(no url parameter)'}`, not "
                    f"`{BADGE_SOURCE}`. A badge pointed at another repository, another branch "
                    f"or another file still renders a number, and a confident wrong version is "
                    f"worse than none."
                )
            asked = (q.get("query") or [""])[0]
            if asked != BADGE_QUERY:
                problems.append(
                    f"{name}: the version badge asks for `{asked or '(no query parameter)'}`, "
                    f"not `{BADGE_QUERY}` — so whatever it renders under a version label is "
                    f"some other field of the manifest."
                )
        if not dynamic:
            # Absence and substitution are different causes and must not share a message.
            # "Carries no version badge" sends an author who is looking at one to add a second.
            baked = [b for b in badges if BAKED_VERSION.search(b.rsplit("/", 1)[-1])]
            if baked:
                problems.append(
                    f"{name}: the version badge is static — `{baked[0]}`. A static badge bakes "
                    f"the number into its own URL, which is the hand-edited literal #133 "
                    f"removed, wearing a badge. Use the dynamic form that reads {MANIFEST}."
                )
            else:
                problems.append(
                    f"{name}: carries no badge labelled `{BADGE_LABEL}`. The version is "
                    f"rendered from {MANIFEST} by that badge (#133), and the label is how it "
                    f"is identified — so this fires both when the badge is gone and when it "
                    f"is present under another label, which renders a version nothing here "
                    f"has checked. Without it the file states no version at all, and this "
                    f"guard would pass a README that had quietly stopped making the claim."
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

    # NOT "agree — v{version}". The READMEs no longer state a version, so saying they agree on
    # one would be this guard asserting a claim it stopped checking — the shape it exists to
    # catch, printed by the guard itself. What was verified is that each carries a version
    # badge; the number beside it is the manifest's, named as the manifest's.
    print(
        f"check-readme-claims: {len(READMES)} README(s) carry a version badge "
        f"({MANIFEST} is at v{version}), {inline} of {total} receipts inline, "
        f"no behaviour count asserted"
    )


if __name__ == "__main__":
    main()
