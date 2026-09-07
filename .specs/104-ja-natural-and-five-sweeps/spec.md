# Spec: Five sweeps, and the Japanese README's remaining translated sentences

- Slug: 104-ja-natural-and-five-sweeps Issue: 104 Type: chore Status: approved
- Author: m0m0i Date: 2026-09-07

## 1. Requirements (WHAT / WHY)

- What changes: "four sweeps" becomes "five" in `README.md`, 「4回」 becomes 「5回」 in `README.ja.md`; and the sentences in `README.ja.md` that still read as translated are recomposed in the register the rest of the file uses, each carrying the claim its English counterpart makes. Two sentences whose claim had drifted from the English are brought back to it.
- **What must NOT change:** C-3 — every English claim keeps a Japanese counterpart with the same content; the English changes one word; the Status section, already recomposed under #90, is untouched except for the count; no other file.
- Why now: the author's request, 2026-09-07. Unplanned work, entered out loud.
- Acceptance criteria:
  - [ ] **AC1:** `grep -c "four sweeps" README.md` and `grep -c "4回のスイープ" README.ja.md` are 0; "five sweeps" and 「5回のスイープ」 present; the merged pull requests show five sweeps.
  - [ ] **AC2:** `observations.md` lists every recomposed sentence with the English it carries; the two claim corrections are named; ですます調 throughout; no line begins with `- `.
  - [ ] **AC3:** `git diff --name-only main` is confined to the two READMEs and this directory; `git diff --numstat main -- README.md` is 1/1; validators at exit 0 after the last write.

### Clarifications

None needed — the author asked for natural Japanese, and the English is the reference.

## 2. Design (HOW)

Exact substring replacements, each asserted to match once; the sentence pairs are the record; the reviewer's C-3 pass is the independent check.

## 3. Tasks (TDD-ordered)

- [ ] T1: record the count red and the sentences before.
- [ ] T2: rewrite; assert AC1–AC3, validators last.
