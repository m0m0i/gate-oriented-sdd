# Spec: a receipt cannot distinguish an independent review from a self-review
- Slug: 9-receipt-review-provenance   Issue: 9   Type: bug   Status: approved
- Author: m0m0i   Date: 2026-08-23

## 1. Requirements (WHAT / WHY)
- Reproduction: run `init` in a project — it writes the reviewer into `.claude/agents/`. Continue in
  the same session and run `implement`. The reviewer is not spawnable, because it was registered
  mid-session, so `implement` step 2 applies: *"If it is not yet spawnable — added mid-session, needs
  a restart — run its procedure inline from its agent file."* The author reviews their own diff and
  writes the receipt.
- Expected: the receipt records how the review was obtained, so a self-review is visible as one.
- Actual: the Receipt block (`agents/_shared/reviewer-contract.md:76`) carries `reviewed_sha`,
  `reviewer`, `verdict`, `blockers`, `high`, `reviewed_at` and nothing else. An inline self-review
  and an independent subagent review produce byte-identical receipts, and `review-gate.sh` clears
  the turn on `verdict=CLEAN` either way.
- Impact: lands on the one thing in the harness that is a guarantee rather than guidance, and on
  every project's first spec — `init` registers the reviewer mid-session, so the next `implement` is
  guaranteed to take the inline path unless the user happens to restart in between. Observed in real
  use: the inline review of this project's first spec produced one HIGH and three MEDIUMs, all real.
  The finding rate says the procedure has value; it says nothing about whether independence held.
- **Root cause:** two mechanisms compounding. The receipt schema was designed to answer *did a review
  run* and never *who ran it*, so provenance has no field to live in. Separately, `init` leaves every
  project in the one state where the answer is guaranteed to be "the author" — it registers the
  reviewer mid-session and never checks that it became spawnable before the first `implement`. The
  schema gap makes the state invisible; `init` makes the state certain.
- Acceptance criteria:
  - [ ] **AC1:** the Receipt block SHALL carry a field recording how the review was obtained.
  - [ ] **AC2:** WHEN that field is absent from a receipt THE SYSTEM SHALL treat it as unknown and
        SHALL NOT infer independence — an old receipt must not be upgraded by silence.
  - [ ] **AC3:** `init` SHALL verify the reviewer is spawnable, and SHALL tell the user to restart
        before their first `implement` when it is not.
  - [ ] **AC4:** the regression test fails before the fix and passes after.
  - [ ] **AC5:** every AC above SHALL be checked mechanically, or the spec SHALL say plainly which
        check is a presence assertion rather than a behavioural one.
- Out of scope: **the gate refusing a CLEAN verdict on `reviewed_by=inline`.** Clarified as a
  separate issue, to be filed: gating before AC3 lands would hard-block every new project's first
  `implement`, which is #8's failure mode wearing different clothes. Sequencing is the point.
  Also out of scope: changing what the reviewer's procedure does; #8 and #10.

### Clarifications
- **Q: once a receipt records provenance, should the gate act on it?**
  A: record now, gate later. The field and the `init` fix ship here; refusing `CLEAN` on a
  self-review becomes its own issue, opened once `init` guarantees the reviewer is spawnable.
  Gating first would block every new project's first `implement`.
- **Q: the bug template demands a regression test — how are the prose halves handled?**
  A: every AC gets a mechanical check, and where that check can only assert presence rather than
  behaviour, the spec says so rather than implying more.

## 2. Design (HOW)
- Fix approach, and why this rather than the narrower or wider fix:
  Two changes, deliberately unequal in weight. The **schema** change adds
  `reviewed_by=subagent|inline` to the Receipt block in `agents/_shared/reviewer-contract.md` and to
  the copy `implement` step 4 tells the author to write. The **`init`** change is the load-bearing
  one: step 4 already verifies the gates behave, and gains a check that the reviewer is spawnable,
  telling the user to restart before their first `implement` when it is not.

  The order matters and is the whole design. Adding a field the gate ignores produces documentation,
  which `AGENTS.md` classifies as the layer that can be talked out of. It is worth shipping anyway
  *because* the `init` fix makes `inline` rare — and only once it is rare can the gate afford to
  refuse it. Removing the state beats labelling it; the label exists to make the residue visible.

  *Narrower, rejected:* field only, no `init` change. Leaves every project's first review a
  self-review and merely records that fact, which documents the hole rather than closing it.

  *Wider, rejected:* field, `init` change, and the gate refusing `inline` in one spec — see
  Out of scope.
- Affected files: `agents/_shared/reviewer-contract.md`, `skills/implement/SKILL.md`,
  `skills/init/SKILL.md`, `scripts/test-gates.sh`, `scripts/check-manifests.py` (or a new sibling
  check for the receipt schema).
- **Blast radius:** every receipt already written lacks the field, so the gate must keep clearing
  them. That is AC2, and it is the one place this change could break an existing install. The
  reviewer agents themselves are unaffected — the Receipt block is emitted by the shared contract
  they all include, so one edit reaches all three.
- Why this cannot recur: a receipt field that nothing reads decays silently, so the schema gets a
  check that fails when the contract and the `implement` copy disagree about what a receipt
  contains — the same argument `check-manifests.py` makes about the two plugin manifests.

## 3. Tasks (TDD-ordered)
> Folded red-and-green per #10.

- [x] T1: failing schema check — the Receipt block in `reviewer-contract.md` and the copy in
      `implement/SKILL.md` must agree field-for-field — then add `reviewed_by` to both so it passes
- [ ] T2: failing `test-gates.sh` case — a legacy receipt with no `reviewed_by` and `verdict=CLEAN`
      still clears the gate (AC2) — then confirm the gate genuinely ignores the field today
- [ ] T3: `init` step 4 verifies the reviewer is spawnable and instructs a restart when it is not,
      with a presence check that the step exists in the skill — **AC5 applies: this asserts the
      instruction is present, not that a model follows it. An eval is the only real check, and
      `evals/` is unrun.**
- [ ] T4: file the follow-up issue for gating `reviewed_by=inline`, and link it from Out of scope
- [ ] T5: refactor
