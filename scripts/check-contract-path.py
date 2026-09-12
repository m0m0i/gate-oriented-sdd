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
)

SOURCES = EXACT + SUFFIX

#: Any path-shaped mention, including a bare filename — `docs/layout.md` drew the flat sibling
#: inside an ASCII tree, which is exactly the form a stricter pattern would have missed.
MENTION = re.compile(r"[\w./-]*reviewer-contract\.md")


def main():
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

        exact = name in EXACT
        for stated in sorted(set(mentions)):
            if exact:
                if stated != CANONICAL:
                    problems.append(
                        f"{name}: says `{stated}`, but a reviewer's own instruction must be "
                        f"exactly `{CANONICAL}` — it is read from the reviewer's directory"
                    )
            elif not stated.endswith(CANONICAL):
                problems.append(f"{name}: says `{stated}`, which does not end in `{CANONICAL}`")

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
