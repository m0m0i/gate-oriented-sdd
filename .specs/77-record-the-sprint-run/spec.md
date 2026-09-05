# Spec: Record what sprint did on the groomed backlog

- Slug: 77-record-the-sprint-run Issue: 77 Type: chore Status: done
- Author: m0m0i Date: 2026-09-05

## 1. Requirements (WHAT / WHY)

- What changes: a `docs/verified.md` section for the `sprint` run of 2026-09-05 against `docs/BACKLOG.md` rows 1 and 2, written from the notes taken as it ran, plus `observations.md` beside this spec holding those notes verbatim. `sprint` writes no file by design; this branch is its record. Fourth skill in the test queue.

- **What must NOT change:**
  - The three issues `sprint` created (#76, #77, #78), the scope comment on #48, and milestone 1. This records; it does not re-decompose.
  - `docs/BACKLOG.md`, byte-identical. Row 1 now says *no issue yet* for work that has #76 and #77, and row 2 omits #78; that staleness is an observation for the next grooming, not an edit here.
  - Shipped paths, and every `- Validators:` command at exit 0.

- Why now: the observations exist only in a session transcript, and #48's README rewrite cites `verified.md` for every skill.

- Acceptance criteria:
  - [x] **AC1:** `docs/verified.md` gains a section for the run with, at least, rows for: what "take from the top" did with a row that is the sprint run itself; the decomposition of rows 1 and 2 with the before and after open-issue lists; whether the tracker could apply an issue template non-interactively; the type-label vocabulary mismatch; what step 6's milestone amounted to; and what was left out and why.
  - [x] **AC2:** The section records every seam not exercised, and every statement the run falsified — starting with `BACKLOG.md` rows 1 and 2, which the run made stale by construction.
  - [x] **AC3:** `git diff --stat main` is confined to `docs/verified.md` and `.specs/77-record-the-sprint-run/`; validators at exit 0.
  - [x] **AC4:** The defect the run found — `sprint` makes the backlog stale the moment it runs, and neither skill says who corrects it — is filed as an issue after the record lands, and the section names it.

- Out of scope: editing `BACKLOG.md`; re-running `sprint`; the `init` run (#76).

### Clarifications

None needed — requirements were unambiguous. The notes were taken during the run and the only judgment, whether the backlog/sprint staleness is a defect worth an issue, is AC4.

## 2. Design (HOW)

- **Approach.** The notes in `observations.md` are the source; the `verified.md` section is written from them in the shape of the three sections before it, then the tree is checked and the one issue filed.
- **Affected files.** `docs/verified.md`, `.specs/77-record-the-sprint-run/`.
- **Coverage gap.** None new; AC3 is the check that nothing else moved.
- **Rollback.** `git revert`.

## 3. Tasks (TDD-ordered)

> One task is one complete Red-Green-Refactor cycle, so one green commit.

- [x] T1: commit the run notes as `observations.md`, verbatim, with the before and after tracker state.
- [x] T2: write the `docs/verified.md` section (AC1, AC2).
- [x] T3: check AC3; file the AC4 issue; record its number.
