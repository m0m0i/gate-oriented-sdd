# Spec: Restate the places that say nothing cites the capability or epic ids

- Slug: 78-restate-nothing-cites Issue: 78 Type: chore Status: approved
- Author: m0m0i Date: 2026-09-05

## 1. Requirements (WHAT / WHY)

- What changes: three sentences are restated so each says what is true at HEAD — `.steering/product.md:27`, `docs/PRD.md:6`, `docs/EPICS.md:4`. `DESIGN.md` cites every `CAP-n` in its Serves column and `BACKLOG.md` cites every `EPIC-n` in its Epic column, both in prose; no check requires either id to exist. The fourth place the issue names, the `docs/verified.md` row at `:114`, is already corrected by two later sections (`:155`, `:174`) and is left alone: that file corrects by a later note, and the notes exist.

- **What must NOT change:**
  - `- Owns:` in `product.md` and the four machine-read lines in `tech.md`; `check-steering-anchors.sh` at 5 of 5.
  - The ids, the `Status: draft` lines, and the statement that neither document has a mechanical consumer — #22 owns that question and it is still true.
  - Every other line of the three files, and every line of `docs/verified.md`.

- Why now: #56 and #58 each falsified one of these and recorded rather than fixed, because the files were on their must-not-change lists. A steering file every session reads says something untrue, and sprint put this in the iteration (row 2, milestone 1).

- Acceptance criteria:
  - [ ] **AC1:** `grep -rn "othing cites" .steering docs/PRD.md docs/EPICS.md` returns nothing; the restated sentences name `DESIGN.md` and `BACKLOG.md` as the citing documents and keep "no check" and "no mechanical consumer".
  - [ ] **AC2:** `check-steering-anchors.sh` resolves 5 of 5 and the five anchor lines are byte-identical to baseline.
  - [ ] **AC3:** `git diff --numstat main` shows exactly one line changed in each of the three files and nothing else; `docs/verified.md` unchanged; every `- Validators:` command at exit 0.

- Out of scope: giving the ids a mechanical consumer (#22); editing `verified.md`; re-homing the post-`epics` issues (backlog row 13).

### Clarifications

None needed — requirements were unambiguous. Two calls were mine and are recorded here: `verified.md` is not edited because its later sections already carry the correction, and `EPICS.md` keeps `Status: draft` because the reason for it — no mechanical consumer — has not changed.

## 2. Design (HOW)

- **Approach.** Three one-line edits, each replacing the false clause with the true one and keeping the rest of the sentence. Baseline first: the five anchor lines, the three files' checksums, and the grep that AC1 turns to zero.
- **Affected files.** `.steering/product.md`, `docs/PRD.md`, `docs/EPICS.md`, and this directory.
- **Coverage gap.** Nothing checks a prose claim; AC1's grep is the test and T1 records its before-value (three hits).
- **Rollback.** `git revert`.

## 3. Tasks (TDD-ordered)

> One task is one complete Red-Green-Refactor cycle, so one green commit.

- [ ] T1: capture the baseline — anchors, checksums, the grep at three hits.
- [ ] T2: restate the three sentences; assert AC1–AC3.
