#!/usr/bin/env python3
"""Fail when a skill has lost an instruction something else depends on.

Skills are prose executed by a model, so their load-bearing sentences are not merely
documentation — other parts of the harness assume they are there. Nothing notices when one
is edited away, because prose has no compiler.

This is a PRESENCE check and it is worth being clear about what that means: it asserts the
instruction is written down, not that a model follows it. Only an eval can check the second,
and `evals/` has never been run. A presence check is the weaker claim, and stating that
plainly is better than implying the stronger one.

Keep the list short. A check that grows to police every sentence becomes an obstacle to
editing prose, and prose that cannot be edited rots — which is a worse failure than the one
this prevents.
"""

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

#: (skill file, required substring, why it must stay)
CONTRACTS = (
    (
        "skills/init/SKILL.md",
        "tell the user to restart before their first `implement`",
        "Without it, init leaves every project where implement's inline fallback is "
        "guaranteed, so the first review of the first spec is a self-review and the "
        "receipt cannot say otherwise. See #9, and #25 which depends on this.",
    ),
    (
        "skills/implement/SKILL.md",
        "Never record `subagent` for a review you ran inline",
        "reviewed_by is only worth having if it is written honestly. See #9.",
    ),
)

def flat(s: str) -> str:
    """Collapse whitespace runs so a phrase matches across a line wrap.

    Found the hard way: the first contract added here spanned two lines in the source, so a
    literal substring test reported it missing while it was plainly there. Prose gets
    rewrapped constantly, and a check that fails on reflowing is a check that gets deleted
    rather than fixed.
    """
    return re.sub(r"\s+", " ", s)


missing = []
for rel, needle, why in CONTRACTS:
    path = ROOT / rel
    if not path.is_file():
        missing.append((rel, needle, f"{rel} does not exist"))
    elif flat(needle) not in flat(path.read_text()):
        missing.append((rel, needle, why))

if missing:
    print("check-skill-contracts FAILED", file=sys.stderr)
    for rel, needle, why in missing:
        print(f"  {rel} no longer contains: {needle!r}", file=sys.stderr)
        print(f"      {why}", file=sys.stderr)
    sys.exit(1)

print(f"check-skill-contracts: {len(CONTRACTS)} skill contract(s) present")
