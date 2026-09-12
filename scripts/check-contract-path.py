#!/usr/bin/env python3
"""Every statement of where the reviewer contract lives must name the same place.

#82: that one fact was written in five files and nothing compared them, so it drifted into
four different forms and stayed that way for months. Review did not catch it — it surfaced
only when `init` was run against a real project (#76), and by then a consumer copying a
reference reviewer got a reviewer whose first instruction did not resolve, which the contract
itself answers with "say so and stop".

**The path is relative to the reviewer, not to a harness root.** These files ship to Claude
Code (`.claude/agents/`) and to Antigravity (`.agents/`), so a single absolute root would be
wrong for one of them by construction. `_shared/reviewer-contract.md` resolves under both.

A separate guard rather than an extension of `check-receipt-schema.py`: that one already has a
subject, and #117 records what a guard acquiring a second one with a different lifetime costs.

Run from the repository root. Exits 0 when every source names the same placement.
"""
import pathlib
import re
import sys

#: The one placement, relative to whichever directory the reviewer sits in.
CANONICAL = "_shared/reviewer-contract.md"

#: The two concrete forms that placement takes, one per harness. A reviewer must name at
#: least one of these, and the reason is empirical rather than tidy: a reviewer reading its
#: own instruction is a tool-using agent whose working directory is the PROJECT ROOT, not the
#: directory its own file sits in. `_shared/reviewer-contract.md` resolves from neither root —
#: found by a reviewer following that line literally, failing, and guessing `agents/_shared/`,
#: which is the plugin's copy rather than the install's. Identical here only by luck. The bare
#: relative form is the right way to SAY where the file lives and is useless for opening it.
CONCRETE = (
    ".claude/agents/" + CANONICAL,   # Claude Code
    ".agents/" + CANONICAL,          # Antigravity
)
ALLOWED = (CANONICAL,) + CONCRETE

#: Files that state it, in two groups, because the rule genuinely differs between them.
#: Fixed rather than globbed: `.specs/` holds records, and rewriting a record to satisfy a
#: later guard destroys its value as evidence (#102).
#:
#: EXACT — an instruction a reviewer executes. It must be the relative form and nothing else.
#: `endswith` is NOT enough here and that is the whole bug: `agents/_shared/reviewer-contract.md`
#: ends with the canonical suffix and is exactly what was broken, because `agents/` is the
#: plugin's directory and does not exist in an install. So is `../_shared/…`. Only equality
#: separates a path that resolves from one that merely looks similar.
EXACT = (
    "agents/ts-reviewer.md",
    "agents/python-reviewer.md",
    "agents/dart-flutter-reviewer.md",
    "agents/_template/reviewer.md",
    # This repository's own install. It was already correct when #82 was filed — which is
    # precisely why dogfooding never surfaced the bug: the instance we run was right and the
    # product we ship was wrong, and nothing compared the two. Pinned here so that stays true.
    ".claude/agents/gate-sdd-reviewer.md",
)

#: SUFFIX — documents and sibling guards that draw or reference a CONCRETE tree, where
#: `.claude/agents/_shared/reviewer-contract.md` is correct and must stay allowed. They are
#: constrained to end in the canonical form, which is what rejects the flat sibling
#: `.claude/agents/reviewer-contract.md` that `docs/layout.md` drew.
SUFFIX = (
    "skills/init/SKILL.md",
    "docs/layout.md",
    "scripts/check-receipt-schema.py",
    # Both state the placement and were outside the comparison while the docstring, the CI
    # step name and the commit message all certified "every statement" — a guard's exemption
    # list is part of the guard, and an unstated omission is the defect this file exists for.
    "docs/CONTRACT.md",
    "AGENTS.md",
)

SOURCES = EXACT + SUFFIX

#: Floors. An empty work-set makes every loop below run zero times, `problems` stay empty, and
#: the success line print `0 source(s) agree` at exit 0 — a guard certifying a comparison it
#: never made. `check-receipt-schema.py:150,256` already carries this for its two tuples and
#: case 49 pins it; the same tuple arrived here without it one release later.
MIN_EXACT, MIN_SUFFIX = 5, 5

#: Constraint this imposes, stated because it is real and otherwise invisible: a document must
#: write the whole path on ONE physical line. Splitting `_shared/` onto its own tree row leaves
#: `reviewer-contract.md` bare, which reads here as the flat form and fails with a message
#: about a wrong path rather than a wrong line break. Teaching the guard to parse ASCII trees
#: was considered and rejected — that is materially more code between reading an input and
#: deciding, and every branch of it is a new way to match nothing and pass, which is G-1 risk
#: bought for a cosmetic gain. The dumb regex is the right trade; it just has to say so.
#:
#: Any path-shaped mention, including a bare filename — `docs/layout.md` drew the flat sibling
#: inside an ASCII tree, which is exactly the form a stricter pattern would have missed.
MENTION = re.compile(r"[\w./-]*reviewer-contract\.md")


def main():
    if len(EXACT) < MIN_EXACT or len(SUFFIX) < MIN_SUFFIX:
        print(
            f"check-contract-path FAILED\n"
            f"  work-set below its floor: {len(EXACT)} exact (min {MIN_EXACT}), "
            f"{len(SUFFIX)} suffix (min {MIN_SUFFIX}).\n"
            f"  A source removed from a tuple is a source that stopped being compared, and "
            f"that must not read as agreement.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    problems = []
    for name in SOURCES:
        path = pathlib.Path(name)
        if not path.is_file():
            # Not "nothing to compare". A source that has vanished is a source no longer
            # agreeing with anything, and four of five compared with a success line printed
            # is #16.
            problems.append(f"{name}: does not exist, so its statement cannot be compared")
            continue
        try:
            text = path.read_text()
        except OSError as exc:
            problems.append(f"{name}: cannot be read ({exc.strerror})")
            continue

        mentions = MENTION.findall(text)
        if not mentions:
            # The quieter half: nothing disagrees because nothing is left to disagree. A file
            # that stopped naming the contract has stopped being checked, silently.
            problems.append(f"{name}: names no reviewer-contract path at all")
            continue

        if name in EXACT:
            for stated in sorted(set(mentions)):
                if stated not in ALLOWED:
                    problems.append(
                        f"{name}: says `{stated}`, which is not one of the allowed forms "
                        f"({', '.join(ALLOWED)})"
                    )
            # …and at least one form a reader can actually open from the project root. Naming
            # only the relative form is how #82's replacement fix failed its own review.
            if not any(m in CONCRETE for m in mentions):
                problems.append(
                    f"{name}: names no concrete path. A reviewer reads its own instruction "
                    f"with the PROJECT ROOT as its working directory, so `{CANONICAL}` alone "
                    f"resolves to nothing — name {' or '.join(CONCRETE)} as well"
                )
        else:
            for stated in sorted(set(mentions)):
                if not stated.endswith(CANONICAL):
                    problems.append(
                        f"{name}: says `{stated}`, which does not end in `{CANONICAL}`"
                    )

    if problems:
        print("check-contract-path FAILED", file=sys.stderr)
        for p in problems:
            print(f"  {p}", file=sys.stderr)
        print(
            f"\n  The reviewer contract is named relative to the reviewer: `{CANONICAL}`.\n"
            f"  It resolves under .claude/agents/ and under .agents/, which an absolute\n"
            f"  path cannot do — these files ship to both harnesses.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    print(f"check-contract-path: {len(SOURCES)} source(s) agree on `{CANONICAL}`")


if __name__ == "__main__":
    main()
