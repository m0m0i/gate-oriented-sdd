# Spec: Drop the redundant clause from the eval sentence

- Slug: 95-drop-redundant-clause Issue: 95 Type: chore Status: approved
- Author: m0m0i Date: 2026-09-06

## 1. Requirements (WHAT / WHY)

- What changes: "— so none has run yet" leaves `README.md:152`; 「そのため、まだ一度も走っていません。」 leaves `README.ja.md:153`. Nothing else.
- **What must NOT change:** both sentences still say the invocation exits without running a case, and the next sentence still refuses a green claim for a suite that never ran; C-3 holds; no other line in either file.
- Why now: the author's request, out loud, 2026-09-06.
- Acceptance criteria:
  - [ ] **AC1:** `grep -c "none has run yet" README.md` and `grep -c "まだ一度も走っていません" README.ja.md` are both 0; "exits without running a case" and 「ケースは1つも実行されません」 remain.
  - [ ] **AC2:** `git diff --numstat main` shows 1/1 for each README and nothing else outside this directory; validators at exit 0 after the last write.

### Clarifications

None needed — requirements were unambiguous.

## 2. Design (HOW)

One substring removed per file; the greps are the test.

## 3. Tasks (TDD-ordered)

- [x] T1: record the greps red.
- [ ] T2: remove; assert AC1–AC2, validators last.
