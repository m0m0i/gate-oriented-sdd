# Spec: Reconcile docs/layout.md with check-document-cascade and current layout
- Slug: 290-reconcile-layout-directory-trees   Issue: 290   Type: chore   Status: done
- Author: m0m0i   Date: 2026-10-12

## 1. Requirements (WHAT / WHY)

- What changes:
  Reconcile `docs/layout.md` with recent structural changes across the harness and installed project layouts:
  1. Under `## A project using the harness`:
     - In `scripts/` (lines 65–67), add `check-document-cascade.py` to the list of copied checks (`check-steering-anchors.sh`, `check-document-set.py`, `check-document-cascade.py`, `check-unreviewed-work.sh`, `check-locks.py`), reflecting the 5th check copied by `init` (introduced in #166).
  2. Under `## The harness repository`:
     - In `assets/` (line 123), reflect the canonical check scripts (`check-steering-anchors.sh`, `check-document-set.py`, `check-document-cascade.py`, `check-unreviewed-work.sh`, `check-locks.py`) alongside `assets/issue-templates/`, matching the files `init` copies into consumer projects.
     - Add `rules/` (and `rules/AGENTS.md`) and root `AGENTS.md` to the harness repository ASCII tree, reflecting the Antigravity rule discovery path symlink and release payload (`dist/gate-sdd.zip`).
     - Note `docs/reviews/` under `docs/` in the tree annotations.

- **What must NOT change:**
  - The document's existing prose, structure, and style (no hard wraps in agent-facing Markdown: one line per paragraph/list item).
  - The dual-target parity descriptions, invariant slug explanations, and fixed naming rules (`.specs/`, `.steering/`, `.work_logs/`).
  - No harness runtime or gate behavior changes.

- Why now:
  Issue #166 added `assets/check-document-cascade.py` and updated `skills/init/SKILL.md` to copy it to a consumer's `scripts/` directory and add it to `- Validators:`. `docs/layout.md` was not updated during #166 and currently under-reports the copied checks. Additionally, recent structural additions (`rules/AGENTS.md`, root `AGENTS.md`, `docs/reviews/`) are missing from the harness repository tree. A reader comparing `docs/layout.md` with `skills/init/SKILL.md` or the repository root finds discrepancies.

- Acceptance criteria:
  - [x] **AC1:** `docs/layout.md`'s project tree under `## A project using the harness` lists `check-document-cascade.py` among the copied checks in `scripts/`, exactly matching the five checks documented in `skills/init/SKILL.md` and `assets/`.
  - [x] **AC2:** `docs/layout.md`'s repository tree under `## The harness repository` reflects `assets/` containing the five check scripts alongside `issue-templates/`, matching what `init` copies.
  - [x] **AC3:** `docs/layout.md`'s repository tree includes `rules/` (with `rules/AGENTS.md`) and root `AGENTS.md`, and notes `reviews/` under `docs/`.
  - [x] **AC4:** `docs/layout.md` maintains single-line paragraphs and list items (no hard wraps) and passes `./scripts/check-markdown-fences.py`.
  - [x] **AC5:** Every contract statement in `docs/layout.md` continues to pass `./scripts/check-contract-path.py`.
  - [x] **AC6:** All existing validators on `- Validators:` exit 0.

- Out of scope:
  - Modifying any runtime gate scripts, hooks, skills, or validator logic.
  - Restructuring unrelated sections of `docs/layout.md`.

### Clarifications
None needed — requirements were unambiguous and completely specified by Issue #290.

## 2. Design (HOW)

- Approach, and the order of operations if it must land in steps:
  1. Update `docs/layout.md` project tree:
     - Under `## A project using the harness` (lines 65–67), add `check-document-cascade.py` to the `scripts/` entry so all five checks are listed.
  2. Update `docs/layout.md` harness repository tree:
     - Under `## The harness repository` (lines 101–130), insert `rules/` (`rules/AGENTS.md`) and `AGENTS.md` at their proper positions.
     - Expand `assets/` entry to show the check scripts alongside `issue-templates/`.
     - Update the `docs/` entry annotation to mention `reviews/`.
  3. Validate:
     - `./scripts/check-markdown-fences.py`
     - `./scripts/check-contract-path.py`
     - `./scripts/check-leakage.sh`
     - Full validator suite (`test-gates.sh` etc.).
- Affected files:
  - `docs/layout.md`
  - `.specs/290-reconcile-layout-directory-trees/spec.md`
- **Coverage gap:**
  - `docs/layout.md` is documentation; its structure and contract references are validated by `./scripts/check-markdown-fences.py` and `./scripts/check-contract-path.py`.
- Rollback:
  - `git revert` of the commit. `docs/layout.md` is documentation; nothing mechanical branches on its tree diagrams.

## 3. Tasks (TDD-ordered)
> One task is one complete Red-Green-Refactor cycle, so one green commit. No task is sequenced after the review.
- [x] T1: reconcile `docs/layout.md` project and harness directory trees with `check-document-cascade.py`, `rules/`, `AGENTS.md`, and `docs/reviews/`, and verify all validators pass (AC1–AC6)
