# Spec: "Unverified" is the word

- Slug: 102-unverified-is-the-word Issue: 102 Type: chore Status: approved
- Author: m0m0i Date: 2026-09-07

## 1. Requirements (WHAT / WHY)

- What changes: thirteen phrasings in ten files that say the eval suite has never run, or that the Antigravity rows were not re-run, say "unverified" instead — the word `docs/NORTH_STAR.md`'s third law already uses for the same fact. The north star's quote of `evals/README.md`'s heading follows the heading. Records under `.specs/` and `.work_logs/` stay.
- **What must NOT change:** no sentence claims a check ran; the third law and the non-negotiable keep their meaning; the reviewer file keeps "Never treat it as passing evidence"; `verified.md`'s dates stay and its preamble agrees with its table; no shipped path.
- Why now: the author's wording, 2026-09-07. Unplanned work, entered out loud.
- Acceptance criteria:
  - [ ] **AC1:** `grep -rnE "never (been )?(run|executed)|no case has run|not re-run since"` over the ten files returns nothing.
  - [ ] **AC2:** Each of the ten still describes the suite or the rows as unverified or under development; `docs/NORTH_STAR.md:37` quotes `evals/README.md:14` verbatim; `docs/verified.md`'s preamble does not say the rows "say so" once they no longer do.
  - [ ] **AC3:** `git diff --name-only main` is confined to the ten files and this directory; every `- Validators:` command at exit 0 after the last write; `check-version-bump.py` reports no shipped file changed.

### Clarifications

None needed — the author supplied the word.

## 2. Design (HOW)

Thirteen exact substring replacements, each asserted to match once; the greps are the test.

## 3. Tasks (TDD-ordered)

- [x] T1: record the greps red.
- [ ] T2: replace; assert AC1–AC3, validators last.
