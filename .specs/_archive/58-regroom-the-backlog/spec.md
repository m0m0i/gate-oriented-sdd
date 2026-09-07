# Spec: Run backlog on this repo, re-grooming BACKLOG.md against the tracker and the epics

- Slug: 58-regroom-the-backlog Issue: 58 Type: chore Status: done
- Author: m0m0i Date: 2026-09-05

## 1. Requirements (WHAT / WHY)

- What changes: run `backlog` against this repository, grooming `docs/BACKLOG.md` in place — the preamble made true at HEAD, every open issue in the table exactly once, closed ones out, the known work that has no issue yet added as rows (clarification 1), the `Epic` column the template has and the file lacks, and a "What changed" record — plus `observations.md` beside this spec and rows in `docs/verified.md`. Third skill in the test queue after #55 and #56, and the first grooming with epics to read.

- **What must NOT change:**
  - The ordering discipline: one list, one position per item, no priority field, no tiers, and `Why here` a comparison against the row below rather than a severity (#58).
  - `docs/EPICS.md`. `backlog` reads it; homing the issues filed since `epics` ran is `epics`' job and is observed here, not done.
  - Every other file. `git diff --stat main` confined to `docs/BACKLOG.md`, `docs/verified.md`, and this spec's directory; every `- Validators:` command at exit 0, though nothing machine-reads `BACKLOG.md`, so this is a check that nothing else moved.
  - The tracker. The skill creates no issues; the open-issue count is identical before and after.
  - No fixes mid-run; a defect in the skill gets an issue after.

- Why now: #56 is merged, so `EPICS.md` and `DESIGN.md`'s risk list exist to groom against for the first time; the preamble has been false since #55 (#58); ten of the twenty open issues are ordered nowhere and two ordered rows are closed; and `sprint` is next in the queue and reads the top of this list.

- Acceptance criteria:
  - [x] **AC1:** WHEN the grooming completes, the sorted set of issue numbers in the table's Item column equals the sorted set from `gh issue list --state open`, each appearing exactly once — except #58 itself, the grooming in flight, which is named in "What changed" rather than ordered — demonstrated by a recorded diff of the two lists; and every row carrying no issue number says so in its Item cell, with those rows listed in `observations.md` for `sprint` to take from. _Amended 2026-09-05, ahead of T2: a backlog row telling the reader to do the grooming they are reading is noise, and a grouped row may carry more than one issue._
  - [x] **AC2:** Every row's `Why here` is non-empty and states why the item sits above the row below it or what it unblocks; the `#` column runs 1…N with no gap and no tie.
  - [x] **AC3:** The file carries one ordering: no priority column, no tier heading, no second list of the same items. Demonstrated by grep for `priority`, `P0`–`P3`, `critical` as a heading or column, all zero.
  - [x] **AC4:** The table has the template's `Epic` column; each cell is an `EPIC-n` that appears verbatim in `docs/EPICS.md`, or `—` for an issue filed after `epics` ran, with those issues listed in `observations.md`.
  - [x] **AC5:** The preamble states what is true at HEAD — which inception documents exist, that `epics` has run — and keeps naming the inversion: the tracker held the plan before the backlog did.
  - [x] **AC6:** `git diff --stat main` confined to the three paths above; validators at exit 0; open-issue count unchanged, both recorded.
  - [x] **AC7:** `observations.md` records what step 1 — *"Start from the walking skeleton — it is always first"* — did against an `EPICS.md` that says no epic is one, and records the two sections the skill's rules and red flags name that its template does not define, "Next up" and "Not ready".
  - [x] **AC8:** `docs/verified.md` gains rows for this run, including every seam not exercised and every statement the run falsified — starting with `EPICS.md:4` and `verified.md`'s existing row, both of which say nothing cites the epic ids, which the `Epic` column will.

- Out of scope: creating issues (`sprint`, next); editing `EPICS.md` (`epics`); fixing anything found in the skill; the README.

### Clarifications

Resolved 2026-09-05.

1. **Does the backlog hold known work that has no issue yet?** Yes. The remaining test-queue runs — `sprint`, `init` on a scratch clone, the README update — and any `DESIGN.md` risk with no issue become rows, marked as having no issue. That is what the skill describes, and it is what gives the `sprint` run something to decompose. AC1 amended. Issues-only was rejected: it keeps the inversion the preamble apologises for and hands `sprint` a list of things that are already issues.
2. **Home the seven post-`epics` issues in `EPICS.md` here?** No. One skill per run; those rows carry `—` and the gap is recorded for a later `epics` re-run. Editing `EPICS.md` was rejected because the record could then no longer say what `backlog` alone did.

## 2. Design (HOW)

- **Approach.** The #55/#56 protocol, for one skill: a recorded baseline, the skill run once through the Skill tool on plugin 0.4.2, the draft order put to the author for correction before anything is committed, a grep-checked assertion per AC, a reread for what the run falsified, the baseline re-verified.
- **The interview is the order.** Steps 2 and 3 of the skill are judgment; the draft order and every `Why here` go to the author as one pause, and `observations.md` records what was changed and what was accepted as drafted, so the #55 caveat — accepted-as-recommended cannot be told from right — is stated rather than hidden.
- **Baseline (T1), recorded verbatim:** `gh issue list --state open` numbers; each validator's exit code; `sha256` of `docs/EPICS.md`, the three steering files and `docs/verified.md`; the current table's issue numbers, with the closed ones and the unordered ones identified. The final check is `git diff --stat main` and the same open-issue list.
- **Row shape.** Template columns `# | Item | Epic | Blocks | Rough size | Why here`. `Item` is `**#n** — <title>` for an issue and `<item> — *no issue yet*` for known work; `Epic` is `EPIC-n` or `—`. `What changed` names what shipped since the last grooming and what arrived, as the file already does; earlier groomings' notes stay, append-only.
- **Affected files.** `docs/BACKLOG.md`, `docs/verified.md`, `.specs/58-regroom-the-backlog/`. Nothing else, and AC6 is the check.
- **Coverage gap.** Nothing reads `BACKLOG.md`, so the only test is the AC1 set comparison; T1 records the before-value it needs. Manual, as before.
- **Amendments** to an AC land alone, ahead of the artifact they judge (C-8).
- **Rollback.** `git revert`; nothing consumes the file.

## 3. Tasks (TDD-ordered)

> One task is one complete Red-Green-Refactor cycle, so one green commit.

- [x] T1: capture the baseline and confirm it green.
- [x] T2: run `backlog`; put the draft order to the author; assert AC1–AC5 and AC7; record.
- [x] T3: reread `EPICS.md:4`, `verified.md`'s "nothing cites" row, `README*`, `docs/layout.md` and `.steering/product.md` for statements the run falsified; record each.
- [x] T4: write the `docs/verified.md` rows (AC8).
- [x] T5: re-verify the baseline; assert AC6; list the defects found and file them.
