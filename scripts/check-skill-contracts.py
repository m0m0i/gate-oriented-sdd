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
        "copy `assets/check-steering-anchors.sh` to the project's `scripts/` directory and add it to the `- Validators:` line",
        "Without it a project's steering anchors are unchecked, and an anchor written in a "
        "form its reader cannot parse fails silently — the file looks right and the value "
        "never arrives. That is #34, and it cost this repo its quality anchor for a week.",
    ),
    (
        "skills/init/SKILL.md",
        "Check whether it can actually be invoked",
        "AC3 is a conjunction — verify AND instruct. Pinning only the instruction let the "
        "verification half be deleted with this check still green, which is a presence check "
        "asserting the wrong half rather than merely a weak one.",
    ),
    (
        "skills/init/SKILL.md",
        "tell the user to restart before their first `implement`",
        "Without it, init leaves every project where implement's inline fallback is "
        "guaranteed, so the first review of the first spec is a self-review and the "
        "receipt cannot say otherwise. See #9, and #25 which depends on this.",
    ),
    (
        "skills/implement/SKILL.md",
        "waiting means keeping the turn open",
        "The review gate fires on turn end. A turn stays open across tool calls, so a spawned "
        "review CAN be waited for — the failure is emitting a final message while it runs, "
        "because each one ends the turn and re-arms the gate. See #27, and docs/verified.md "
        "for the observation.",
    ),
    (
        "skills/spec/SKILL.md",
        "folded into a single task that ends green",
        "The shapes table states what the first task is, which is the same subject as "
        "`implement`'s loop and the templates' Tasks blocks. Left saying the first task is "
        "a failing test, it is a third document disagreeing with the two that were "
        "reconciled in #10 — and the one a spec author reads FIRST.",
    ),
    (
        "skills/implement/SKILL.md",
        "task is one COMPLETE Red-Green-Refactor cycle",
        "Without it, `implement`'s loop and the spec templates disagree about what a task "
        "is, and the templates lose the argument silently — a reader who splits red from "
        "green again gets a turn that ends red and no sentence explaining why. "
        "check-templates.py guards the templates; this guards the sentence that says what "
        "the templates were folded FOR. See #10.",
    ),
    (
        "skills/implement/SKILL.md",
        "Never record `subagent` for a review you ran inline",
        "reviewed_by is only worth having if it is written honestly. See #9.",
    ),
)

def flat(s: str) -> str:
    """Collapse whitespace runs so a phrase matches across a line wrap.

    Needles are hand-written on one line; the prose they match is wrapped and rewrapped
    constantly, so a literal substring test reports a phrase missing while it is plainly
    there. A check that fails on reflowing is a check that gets deleted rather than fixed.

    Deliberately names no example. Two earlier versions named one and each failed
    differently: naming the file became ambiguous when that file gained a second contract,
    and naming the needle was a paraphrase that could not be grepped for. The reason this
    function exists is general and needs no exhibit.
    """
    return re.sub(r"\s+", " ", s)


if len(CONTRACTS) < 2:
    print(
        "check-skill-contracts: fewer than two contracts listed, so this guard is checking "
        "almost nothing. An empty work-set must not report success — see #16.",
        file=sys.stderr,
    )
    sys.exit(1)

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
