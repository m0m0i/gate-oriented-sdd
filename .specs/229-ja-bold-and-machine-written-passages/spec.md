# Spec: Two unrendered bold spans, and the Japanese README's machine-written passages

- Slug: 229-ja-bold-and-machine-written-passages   Issue: 229   Type: chore   Status: approved
- Author: m0m0i   Date: 2026-10-03

## 1. Requirements (WHAT / WHY)

- What changes: in `README.ja.md` only. Two bold spans whose closing `**` sits between `。` and a CJK character, and so render as literal asterisks on GitHub, get the `。` moved outside the span. The passages a yomiyasu pass flagged as machine-written Japanese are recomposed: one em dash, the line-final colons and em dashes in the Antigravity install steps, six metaphors that give rules or sessions human traits, one word-for-word copy of "until it doesn't", the bold on two token counts, and one parenthetical that repeats the word before it. The roughly 900-character Mode paragraph is split into three paragraphs at its two bold lead sentences, with no sentence changed by the split.
- **What must NOT change:** C-3 — every claim in `README.md` keeps a Japanese counterpart with the same content **at the same strength**: no added verb the English lacks, and no assertion weakened to a possibility. The half-width space between Latin text and Japanese is house style and stays. The `AではなくB` contrasts stay. The two authorial closing lines (`毎ターン支払っている参照資料は、いずれ消される参照資料です。`, `確かめたうえでの沈黙`) stay. The `検証環境:` line stays, because #162 owns it. `README.md` and every other file are untouched, and there is no version bump.
- Why now: the author's request, 2026-10-03, after a trial run of the yomiyasu skill on this file. Unplanned work, entered out loud, like #90 and #104. The broken bold is a visible rendering defect on the Japanese landing page.
- Acceptance criteria:
  - [x] **AC1:** No bold span in `README.ja.md` has a closing `**` preceded by `。` and followed by a non-space character. The check pairs the `**` markers on each line and tests each closing one. It counts 2 before the change and 0 after, and the yomiyasu linter's `bold_not_rendered` agrees (2, then 0).
  - [x] **AC2:** `observations.md` lists every changed sentence before and after, each with the English sentence it carries. The record also states, for each one, that the claim and its strength are unchanged (C-3).
  - [x] **AC3:** No half-width space between Latin text and Japanese is removed where both of its neighbours survive the change. The count may fall only by spaces whose Latin neighbour the change itself removes or moves, and `observations.md` accounts for each one. The count of `ではなく` is unchanged.
  - *Amended 2026-10-03, during T2:* AC3 first read "the count does not fall". It fell 380 → 377, and all three were spaces next to a token the change removes: the `**` on the two token counts, and `#26` moving to the start of its own sentence. No surviving Latin–Japanese pair lost its space. A raw count could not tell the house style being stripped from bold markers being removed, so the criterion now states the property the invariant protects.
  - [x] **AC4:** `git diff --name-only origin/main` is confined to `README.ja.md` and this directory, and every validator on the `- Validators:` line exits 0 after the last write.
- Out of scope: the 検証環境 line (#162); `README.md`; the remaining "same sentence ending three times in a row" lint findings in passages that are otherwise natural, which the skill's own rules say to leave alone.

### Clarifications

None needed — requirements were unambiguous. The one reading that could have changed the diff, whether the half-width space between Latin text and Japanese is a defect (the yomiyasu linter flags 18 of them), was answered by the author on 2026-10-03 before this spec existed: it is intended house style. It is recorded as an invariant above rather than asked again.

## 2. Design (HOW)

- Approach: exact substring replacements, each asserted to match exactly once, applied by a throwaway script that is not committed. The before/after sentence pairs in `observations.md` are the record, and the reviewer's C-3 pass against `README.md` is the independent check. Every replacement is checked against its English sentence, not only against the old Japanese. During drafting, three replacements that read better than the original but weakened or added to the English claim were caught that way and reverted. The yomiyasu diff script cannot see those, because it compares Japanese to Japanese.
- Affected files: `README.ja.md`; `.specs/229-ja-bold-and-machine-written-passages/` (`spec.md`, `observations.md`, the receipt).
- **Coverage gap:** nothing in the repo tests that bold renders, and nothing tests the C-3 parity of prose. The bold check (AC1) and the two counts (AC3) are recorded before the change in T1, so the after-state is an observation, not an assertion. C-3 stays a reviewer judgment, as it was in #90 and #104.
- Rollback: `git revert`.

## 3. Tasks (TDD-ordered)

- [x] T1: record the baseline in `observations.md`: the bold check at 2, the Latin–Japanese space count, the `ではなく` count, and every sentence to be changed, with its English counterpart.
- [x] T2: apply the replacements; record each sentence after, with its C-3 note; assert AC1 (0), AC3 (counts held) and AC4 (diff confined, validators at exit 0 after the last write).
