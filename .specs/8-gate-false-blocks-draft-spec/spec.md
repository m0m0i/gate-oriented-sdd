# Spec: review-gate.sh false-blocks a spec that is still being drafted
- Slug: 8-gate-false-blocks-draft-spec   Issue: 8   Type: bug   Status: draft
- Author: m0m0i   Date: 2026-08-23

## 1. Requirements (WHAT / WHY)
- Reproduction: on a branch `<n>-<slug>` one commit ahead of the default branch, create
  `.specs/<n>-<slug>/spec.md` containing a Requirements section and a section 3 whose body is a
  placeholder rather than checkboxes — the exact state `spec` step 3 instructs the author to
  create. Run `hooks/review-gate.sh`. Verified 2026-08-23: `exit=2`.
- Expected: silence. Nothing has been implemented, so there is nothing to review.
- Actual: the turn is blocked, with `Review gate: every task in <spec> is ticked, but no reviewer
  receipt exists.` The spec has no tasks at all, so the message asserts the opposite of the truth.
- Impact: every project's first spec, on the harness's own prescribed first step. It is the failure
  mode this repo names more than any other — README: *"A gate that fires on ordinary turns gets
  disabled, and a disabled gate protects nothing."* It escaped this repo's own use only because the
  draft branch was still an ancestor of `main`, so the merged-branch escape at `review-gate.sh:34`
  fired before the task check was reached.
- **Root cause:** `gate_open_tasks` (`hooks/gate-lib.sh:43`) greps `-c '^ *- \[ \]'` under section 3
  and returns a count of *unticked* boxes only. Zero is therefore ambiguous between two opposite
  states — "no tasks have been authored" and "every authored task is complete" — and
  `review-gate.sh:41` (`[ "$(gate_open_tasks "$spec")" -gt 0 ] && gate_pass`) resolves that
  ambiguity as "complete". The count that would disambiguate, total checkboxes present, is never
  taken.
- Acceptance criteria:
  - [ ] **AC1:** WHEN a spec's section 3 contains no checkboxes of any kind THE SYSTEM SHALL exit 0
        and emit nothing.
  - [ ] **AC2:** WHEN a spec has no section 3 at all THE SYSTEM SHALL exit 0 and emit nothing.
  - [ ] **AC3:** WHEN a spec's section 3 contains at least one checkbox, all are ticked, and no
        receipt exists THE SYSTEM SHALL block on both channels — existing behaviour, unchanged.
  - [ ] **AC4:** WHEN a spec's section 3 contains at least one unticked checkbox THE SYSTEM SHALL
        exit 0 and emit nothing — existing behaviour, unchanged.
  - [ ] **AC5:** no block message SHALL state that tasks are ticked unless at least one ticked
        checkbox exists in the spec.
  - [ ] **AC6:** the regression test fails before the fix and passes after.
- Out of scope: the message wording for the genuinely-all-ticked case; #9 and #10.

### Clarifications
None needed. The root cause determines the fix; no scope question was open.

## 2. Design (HOW)
- Fix approach, and why this rather than the narrower or wider fix:
  Add a sibling counter rather than widening the existing one. `gate_open_tasks` has exactly one
  caller but a precise documented meaning — unticked checkboxes under section 3 only, with a comment
  explaining why acceptance criteria are deliberately excluded. Teaching it to count ticked boxes as
  well would make its name false and its comment describe two things. So: add `gate_total_tasks`,
  keep each function answering one question, and let the caller compose them.

  ```sh
  [ "$(gate_total_tasks "$spec")" -eq 0 ] && gate_pass   # nothing authored — nothing to review
  [ "$(gate_open_tasks  "$spec")" -gt 0 ] && gate_pass   # in progress — existing behaviour
  ```

  *Narrower, rejected:* special-case a missing `## 3.` heading in `review-gate.sh`. It fixes the
  literal reproduction and leaves the more common case broken — `spec` step 3 produces a section 3
  that is **present** with placeholder text, not absent.

  *Wider, rejected:* read the spec's `Status:` field and gate on `approved`/`done`. Status is
  author-maintained prose, so the guarantee would rest on a human remembering to flip it. That is
  the judgment layer, and this gate is deliberately not built on it.
- Affected files: `hooks/gate-lib.sh`, `hooks/review-gate.sh`, `scripts/test-gates.sh`.
- **Blast radius:** `gate_open_tasks` has one caller (`review-gate.sh:41`); `quality-gate.sh` and
  `steering-digest.sh` never read the spec. The only behaviour that changes is specs with zero
  checkboxes under section 3, which go from blocking to silent. Every existing `test-gates.sh`
  fixture writes a task line via `make_repo`, so no existing case can change verdict — a claim T3
  checks rather than assumes.
- Why this cannot recur: the ambiguity is removed at its source. "No tasks authored" and "all tasks
  complete" stop sharing a representation, so no future caller can conflate them by reading a single
  count. Both boundaries plus the absent-section case are pinned in `test-gates.sh`.

## 3. Tasks (TDD-ordered)
> Tasks are folded red-and-green per the decision recorded in #10: one task is one complete
> Red-Green-Refactor cycle, and therefore one green commit.

- [x] T1: failing case in `test-gates.sh` — a spec whose section 3 has no checkboxes stays silent —
      then `gate_total_tasks` and the `review-gate.sh` guard that makes it pass
- [ ] T2: boundary cases — section 3 absent entirely stays silent; at least one ticked and none
      unticked still blocks; at least one unticked still stays silent
- [ ] T3: confirm no pre-existing case changed verdict, by running the suite against the unmodified
      fixtures and diffing the case list
- [ ] T4: refactor — the two guards read as one decision, and the comment says why zero is ambiguous
