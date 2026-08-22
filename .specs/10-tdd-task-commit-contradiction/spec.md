# Spec: the TDD task/commit rule contradicts the quality gate
- Slug: 10-tdd-task-commit-contradiction   Issue: 10   Type: bug   Status: draft
- Author: m0m0i   Date: 2026-08-23

## 1. Requirements (WHAT / WHY)
- Reproduction: author a spec from the feature or bug template. Both split the pair across tasks —
  `T1: write the failing test for ...` / `T2: implement ... to make it pass`. Apply
  `implement`'s rule *"One task, one commit. No batching, no half-tasks."* literally, and end the
  turn after T1. `quality-gate.sh` runs the `Validators:` line and blocks, because the tests fail.
- Expected: the prescribed workflow can be followed literally without tripping the harness's own gate.
- Actual: it cannot. The only way forward is to ignore "one task, one commit", with no sanction and
  no guidance saying so.
- Impact: every TDD pair in every feature and bug spec, so several times per implementation. The
  chore template is unaffected — its T1/T2 are green by construction. Sharper since `quality-gate.sh`
  shipped in 0.2.3: before it, nothing ran the tests on turn end and the contradiction was theoretical.
  A rule that must be quietly broken to make progress erodes the rules next to it.
- **Root cause:** the two documents disagree about what a *task* is. `implement`'s loop is defined
  per task as Red → Green → Refactor → tick → one commit, which makes a task a **complete** cycle.
  The feature and bug templates split Red and Green into separate tasks, which makes a task **half**
  a cycle. Applying the loop to `T1: write the failing test` asks for a failing test for the writing
  of a failing test. The gate collision is a symptom of that disagreement, not its cause — and note
  `quality-gate.sh` never inspects commits, so a red *commit* is not what blocks; a turn that *ends*
  red is.
- Acceptance criteria:
  - [ ] **AC1:** following the templates and `implement`'s rules literally SHALL NOT produce a turn
        that ends with failing validators.
  - [ ] **AC2:** `implement` SHALL state the resolution explicitly, rather than leaving each user to
        rediscover it.
  - [ ] **AC3:** the feature and bug templates and `implement`'s loop SHALL agree on what one task is.
  - [ ] **AC4:** a check SHALL fail when a shipped task template contains a task that is only a red
        step, so the split cannot quietly return.
  - [ ] **AC5:** the regression test fails before the fix and passes after.
- Out of scope: the chore template, which does not have a red step; #8 and #9.

### Clarifications
- **Q: the templates and `implement`'s loop disagree on what a task is — which gives way?**
  A: the templates. `implement`'s loop already defines a task as a complete Red-Green-Refactor
  cycle, so the templates are the outlier and the loop needs no edit. Folding the pair makes one
  task genuinely one green commit. Accepted cost: the Red step stops being its own line in the
  written plan.
- **Q: redefine the rule instead (a red/green pair is one commit, tasks stay split)?**
  A: rejected. It is what the issue preferred, but it requires rewording "no half-tasks" — since
  `T1` is exactly half a task — and restructuring the per-task loop to permit a task that is part
  of a cycle. More edits, to the document that is currently correct.
- **Q: loosen the quality gate to tolerate test-only commits?**
  A: rejected. It makes the gate's behaviour depend on classifying a diff, and a misclassification
  fails open — the failure 0.2.1 was spent fixing.
- **Q: prose-only, or a mechanical check?**
  A: a check. AC4.

## 2. Design (HOW)
- Fix approach, and why this rather than the narrower or wider fix:
  Three edits and one new guard. The **feature** and **bug** templates fold their red and green
  tasks into one — `T1: failing test for X, then the implementation that passes it`. The **chore**
  template is untouched: its T1/T2 are green by construction, so it has no red step to strand.
  `implement/SKILL.md` states the resolution outright — a task is a full cycle, one task is one
  green commit, and a turn must not end with failing validators — because this is precisely the
  kind of thing every user otherwise rediscovers alone.

  A new `scripts/check-templates.py` fails when a Tasks block in `skills/spec/templates.md` contains
  a task line that names a failing or regression test without also naming the implementation that
  answers it. Wired into CI beside the existing guards.

  *Narrower, rejected:* edit the templates and say nothing in `implement`. The templates would be
  consistent and the contradiction would survive in any spec already written from the old ones,
  with nothing telling the author how to execute it.

  *Wider, rejected:* changing `quality-gate.sh` — see the third clarification.
- Affected files: `skills/spec/templates.md`, `skills/implement/SKILL.md`,
  `scripts/check-templates.py` (new), `.github/workflows/ci.yml`.
- **Blast radius:** specs already written are unaffected — templates are copied at authoring time,
  not read at gate time — so existing in-flight specs keep their split tasks and keep needing the
  workaround. `implement`'s new paragraph is what serves them. The chore template's behaviour must
  not change, which the new check must not accidentally flag.
- Why this cannot recur: the split is the thing that failed, so the check is written against the
  split rather than against the current text. A future edit that re-separates red from green fails
  CI on the day it is made rather than on the day someone follows it.

## 3. Tasks (TDD-ordered)
> Folded red-and-green — this spec is the first written under its own decision.

- [ ] T1: failing `check-templates.py` against the current `templates.md` — it must flag the feature
      and bug T1 lines and must NOT flag the chore template — then fold the two templates so it passes
- [ ] T2: state the resolution in `implement/SKILL.md` — a task is a full Red-Green-Refactor cycle,
      one task is one green commit, a turn must not end red — with a presence check that the
      paragraph exists (**AC-limited: presence, not adherence**)
- [ ] T3: wire `check-templates.py` into `.github/workflows/ci.yml` beside the other guards, and
      confirm it fails the build when the fold is reverted
- [ ] T4: blast radius — confirm the chore template is untouched and `test-gates.sh` still passes
- [ ] T5: refactor
