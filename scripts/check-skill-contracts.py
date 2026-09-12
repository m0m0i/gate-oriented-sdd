#!/usr/bin/env python3
"""Fail when a skill has lost an instruction something else depends on.

Skills are prose executed by a model, so their load-bearing sentences are not merely
documentation — other parts of the harness assume they are there. Nothing notices when one
is edited away, because prose has no compiler.

This is a PRESENCE check and it is worth being clear about what that means: it asserts the
instruction is written down, not that a model follows it. Only an eval can check the second,
and `evals/` is unverified. A presence check is the weaker claim, and stating that
plainly is better than implying the stronger one.

Keep the list short. A check that grows to police every sentence becomes an obstacle to
editing prose, and prose that cannot be edited rots — which is a worse failure than the one
this prevents.

Fifteen today. A sixteenth needs an argument, in the spec that proposes it, for why review cannot
defend that sentence instead — "short" with no number attached is not a limit, and the list
grows one defensible entry at a time.
"""

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

#: (skill file, required substring, why it must stay)
CONTRACTS = (
    (
        "skills/init/SKILL.md",
        "A project that already carries a `- Mode:` line is an upgrade, never a fresh install",
        "Without it a re-run recreates documents the author deliberately declined, which is "
        "the exact failure the mode was recorded to prevent — the feature undoing itself. "
        "Review cannot defend it: the bullet reads as ordinary advice, and its deletion looks "
        "like trimming, while what it actually restores is `init` overwriting a deliberate "
        "choice. #110 AC9, promised by that spec's T2.",
    ),
    (
        "skills/spec/SKILL.md",
        "In a `minimum`-mode project the backlog is the queue and creating the issue from it is the normal path",
        "Without the scope, the side-door accusation fires on EVERY spec in a project that "
        "never runs sprint as a batch — and a rule that is wrong every time is a rule the "
        "user learns to skip, taking the real one ('no issue, no spec') with it. #110. "
        "Review cannot defend it: deleting the clause reads as tightening a rule, which is "
        "the direction a reviewer waves through, and the damage lands in installs that "
        "never appear in this repository's diffs.",
    ),
    (
        "skills/contract/SKILL.md",
        "The trigger is evidence, not scale",
        "contract's step 1 asks for the last fifty commits and its red flags name copying a "
        "style guide wholesale, so run early it produces a WORSE rulebook rather than an "
        "absent one. Stated as scale instead, a minimum-mode reader concludes the skill is "
        "unavailable to them rather than not yet useful — and mode governs documents and "
        "flow membership, never availability. #110, and #109's availability clause. Review "
        "cannot defend it — and the argument is about DELETION, since a presence check can "
        "only catch that: the sentence is the one place any document says a minimum-mode "
        "project may run this skill AT ALL. Remove it and the skill still reads complete, "
        "while a model executing it in a minimum project has no instruction saying it is "
        "permitted — so it defers or refuses, and the mode silently starts governing "
        "availability, which is the one thing every document here says it never does.",
    ),
    (
        "skills/init/SKILL.md",
        "`- Mode: minimum` or `- Mode: full` on one physical line",
        "Without the line, nothing downstream can tell a deliberate omission from an "
        "abandoned install, and check-document-set.py has nothing to verify against. The "
        "mode is declared, never derived — derivation cannot distinguish the two, which is "
        "the whole of #110. Review cannot defend it: an init that stops writing the line "
        "still installs a working harness, and every check stays green — the loss shows up "
        "only in a project nobody is reviewing, on the day someone asks which set it chose.",
    ),
    (
        "skills/init/SKILL.md",
        "copy `assets/check-document-set.py` to the project's `scripts/` directory and add it to the `- Validators:` line",
        "This is the ONLY route by which the mode reaches a gate. Delete it and the mode "
        "becomes a comment: declared, never checked. It must stay on the `- Validators:` "
        "line rather than in a hook, because a gate that branches on mode is a switch that "
        "turns enforcement down — #110's AC5. Review cannot defend it for the same reason "
        "the check-steering-anchors entry exists: what the deletion removes is a check that "
        "then says nothing, and a check saying nothing is indistinguishable from a check "
        "passing.",
    ),
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
        "Do not propose archiving, and do not open a follow-up pull request",
        "The closing step is where the chain says what comes next, and while it said "
        "archive, every merged spec bought a second pull request whose entire diff was a "
        "git mv. Deleting this clause restores that silently — the flow reads fine either "
        "way, which is exactly the failure prose has no compiler to catch. See #52.",
    ),
    (
        "skills/archive/SKILL.md",
        "to be noise — not after every merge",
        "Pins the `description:` line, and is worded so only that line can satisfy it — the "
        "body says the same thing twice in near-miss forms and README.md uses the bare "
        "phrase, so a shorter needle would let a reverted description pass on a match "
        "found elsewhere in the file. That line is what a harness surfaces "
        "before the body is ever loaded, so it alone decides whether the skill is invoked per "
        "merge or per noisy directory — reverting it puts a git mv back on the critical path "
        "of every issue for any consumer whose model never opens the file. The body's fuller "
        "statement of the same rule is deliberately left to review; one needle can assert one "
        "string, and this is the string a consumer acts on. See #52.",
    ),
    (
        "skills/implement/SKILL.md",
        "Never record `subagent` for a review you ran inline",
        "reviewed_by is only worth having if it is written honestly. See #9.",
    ),
    (
        "skills/implement/SKILL.md",
        "The version bump lands here, after the receipt — never as a task",
        "review-gate.sh arms when a spec has no unticked tasks. Delete this and the bump "
        "goes back to being the last task, which holds one box unticked for the whole "
        "review and keeps the gate silent through the one stretch it exists to cover. "
        "Review cannot defend the sentence: a deleted step is plainly visible in a diff, "
        "but its SIGNIFICANCE is not — the flow reads correctly either way — and what its "
        "removal restores is a gate that says nothing, not a defect anyone can see. "
        "See #113.",
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
