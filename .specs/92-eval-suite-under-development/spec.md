# Spec: Say the eval suite is under development

- Slug: 92-eval-suite-under-development Issue: 92 Type: chore Status: done
- Author: m0m0i Date: 2026-09-06

## 1. Requirements (WHAT / WHY)

- What changes: six files stop describing `evals/` as merely "not yet run" and say it is under development, with the run fact kept: the cases are authored, the command is in early access here, none has run. `README.md`, `README.ja.md`, `docs/layout.md`, `.steering/structure.md`, `evals/README.md`, `AGENTS.md`.

- **What must NOT change:**
  - No sentence claims a case ran; both READMEs still list the suite under what is not verified.
  - The five machine-read steering lines; no shipped path; validators at exit 0.

- Why now: the author's preference, stated 2026-09-06. Unplanned work, entered out loud.

- Acceptance criteria:
  - [x] **AC1:** `grep -rn "not yet run\|authored, unrun\|has still not run\|authored but unrun"` over the six files returns nothing, and each carries "under development" (開発中 in the Japanese).
  - [x] **AC2:** Each of the six still states that no case has run; the READMEs' "what is not verified" sentences still name the suite; the Japanese Status section says the same as the English (C-3).
  - [x] **AC3:** `git diff --name-only main` is confined to the six files and this directory; `check-steering-anchors.sh` 5 of 5; every `- Validators:` command at exit 0 after the last write.

- Out of scope: `docs/BACKLOG.md`'s Unshaped item, which describes the block rather than the suite; `docs/verified.md`'s dated observations.

### Clarifications

None needed — requirements were unambiguous. The English wording is "under development"; the Japanese is 開発中.

## 2. Design (HOW)

- **Approach.** T1 records the greps red; T2 rewrites the six places and re-runs them, validators last.
- **Affected files.** The six, and this directory.
- **Rollback.** `git revert`.

## 3. Tasks (TDD-ordered)

> One task is one complete Red-Green-Refactor cycle, so one green commit.

- [x] T1: record the greps red.
- [x] T2: rewrite; assert AC1–AC3 with the validators run last.
