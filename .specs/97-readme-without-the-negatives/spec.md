# Spec: The README Status section without the negatives

- Slug: 97-readme-without-the-negatives Issue: 97 Type: chore Status: approved
- Author: m0m0i Date: 2026-09-06

## 1. Requirements (WHAT / WHY)

- What changes: in both READMEs' Status sections, the "What is not" paragraph is removed and replaced by a one-line pointer to `docs/verified.md`'s "Still to verify" list and the tracker; the matrix line keeps versions and dates and drops "not re-run since"; the eval sentence ends at "in early access on this account". "What is verified" is untouched.
- **What must NOT change:** no sentence claims a check ran when it did not; the "What is verified" paragraph; C-3 between the two READMEs; every other section.
- Why now: the author's decision, 2026-09-06 — the harness is in use and the negative framing reads as awkward; the open work stays where a maintainer looks for it.
- Acceptance criteria:
  - [ ] **AC1:** `grep -cE "What is not|not re-run|never ran|no case has run" README.md` and `grep -cE "検証できていないこと|再実行していません|走らせたことのない" README.ja.md` are 0.
  - [ ] **AC2:** The "What is verified" paragraphs are byte-identical to `main`'s; the new pointer sentence names `docs/verified.md` in both; the matrix line still carries both dates; the two sections say the same thing (C-3).
  - [ ] **AC3:** `git diff --name-only main` is confined to the two READMEs and this directory; validators at exit 0 after the last write.
- Out of scope: "pre-release" and "not a supported product", which are a support statement, not a verification one; `docs/verified.md`, `evals/README.md`, `AGENTS.md`, which are maintainer documents and keep their run facts.

### Clarifications

None needed — requirements were unambiguous.

## 2. Design (HOW)

Three sentences per language; the greps are the test.

## 3. Tasks (TDD-ordered)

- [x] T1: record the greps red and the "What is verified" checksums.
- [ ] T2: rewrite; assert AC1–AC3, validators last.
