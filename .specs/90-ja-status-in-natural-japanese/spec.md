# Spec: Rewrite the Japanese README's Status section as Japanese

- Slug: 90-ja-status-in-natural-japanese Issue: 90 Type: chore Status: done
- Author: m0m0i Date: 2026-09-06

## 1. Requirements (WHAT / WHY)

- What changes: the ステータス section of `README.ja.md` is recomposed in natural Japanese — ですます調, paragraphs, no bullet lists, as the rest of the file is written — carrying every claim the English section makes.

- **What must NOT change:**
  - The set of claims. C-3: the Japanese README is a translation, not a separate document, so each English sentence's content has a Japanese counterpart, and nothing is added that the English does not say.
  - `README.md`, and every other section of `README.ja.md`.
  - No shipped path; validators at exit 0.

- Why now: the author asked, after reading #48's merge: the mirror was clause by clause and reads as one. Unplanned work entered out loud.

- Acceptance criteria:
  - [x] **AC1:** `observations.md` lists each claim of the English section and quotes the Japanese sentence that carries it; none is missing and none is added.
  - [x] **AC2:** The section matches the file's register — ですます調 throughout, no line beginning with `- `, the same bold labels the section had.
  - [x] **AC3:** `git diff --name-only main` is confined to `README.ja.md` and this directory; the diff touches only the lines between `## ステータス` and `## ライセンス`; every `- Validators:` command at exit 0 after the last write.

- Out of scope: the other sections of `README.ja.md`, which the original author wrote in Japanese to begin with.

### Clarifications

None needed — requirements were unambiguous.

## 2. Design (HOW)

- **Approach.** T1 records the current section and the English claim list. T2 writes the new section, maps each claim to its sentence, and runs the guards last.
- **Affected files.** `README.ja.md`, this directory.
- **Coverage gap.** No check reads a translation; the claim list is the test, and the reviewer's C-3 pass is the independent one.
- **Rollback.** `git revert`.

## 3. Tasks (TDD-ordered)

> One task is one complete Red-Green-Refactor cycle, so one green commit.

- [x] T1: record the current section and the English claims.
- [x] T2: rewrite; map every claim; assert AC1–AC3 with the validators run last.
