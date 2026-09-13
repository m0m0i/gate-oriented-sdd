# Spec: The README's Status section, true at 0.7.0
- Slug: 115-the-status-section-at-0-7-0   Issue: 115   Type: bug   Status: done
- Author: m0m0i   Date: 2026-09-13

## 1. Requirements (WHAT / WHY)
- Reproduction: read `## Status` in either README and compare each of its claims to the repository. Three are false.

  | Claim | README says | Actual | Where |
  | :-- | :-- | :-- | :-- |
  | version | `v0.4.3` | **0.7.0** | `README.md:170`, `README.ja.md:171` |
  | gate and guard behaviours | 67 | **76** | `README.md:174`, `README.ja.md:175` |
  | receipts from a spawned reviewer | "all but two" | all but **three** | `README.md:174`, `README.ja.md:175` |

- Expected: `## Status` states what is true of the repository it ships with. That is the section's entire job — #48 and #97 both exist to keep it so, and `.steering/product.md` makes verification claims the thing this project is least allowed to get wrong.
- Actual: all three are stale, in both languages, and they went stale by different mechanisms — which is why this is one spec rather than three corrections.
- Impact: **the version is the worst of the three.** `v0.4.3` predates #113 (the bump became an `implement` step), #109 (the minimum set), #110 (the mode) and #82 (the reviewer contract path). A reader is told the project is three releases behind where it is, on the line that establishes what they are looking at. The other two are C-2 count drift of the kind this repository has now corrected four times.
- **Root cause — three, and they are not the same.**
  - **The version is not carried by the bump.** `v0.4.3` was written by #47 on 2026-09-05 (`124a0c9`), and the README has been edited **since** — `3eb2299` touched it for #110 — without the line moving. `implement`'s post-receipt step bumps `plugin.json` and `.claude-plugin/plugin.json`; **nothing ties the README's version claim to either.** `check-manifests.py` verifies the two manifests agree with each other and knows nothing about the README. So the claim can only be corrected by someone noticing, which is what just happened, eight days and three releases late.
  - **The behaviour count is C-2 drift**, updated by hand whenever someone remembers. It has moved 67 → 76 across #113, #110, #82 and #126.
  - **The receipts count is #115 as filed**, and has since drifted further in the same direction: the sentence said two when three receipts already said `inline`, and the corpus has grown from 28 receipts to 33.
- **This spec's scope is wider than the issue's title**, and that was said out loud on the issue before the spec was written rather than widened quietly here. #48 and #97 are the precedent for treating `## Status` as one subject.
- Acceptance criteria:
  - [ ] **AC1:** WHEN `## Status` states a version THE SYSTEM SHALL state the one in `plugin.json`. Verified by comparison, not by reading.
  - [ ] **AC2:** `## Status` SHALL state **no count** of gate and guard behaviours — the sentence names `scripts/test-gates.sh` and what it proves, without a number. _Amended at `clarify`, before the first commit: the first wording required the number to match the suite, which makes it hand-maintained forever or guarded by running the slowest validator twice per turn. Removing the number removes the drift surface instead of policing it._
  - [ ] **AC3:** WHEN `## Status` describes how review receipts were obtained THE SYSTEM SHALL state a count matching the receipts on disk, distinguishing `reviewed_by=inline` from `subagent`.
  - [ ] **AC4:** `README.ja.md` carries the same three corrections, as Japanese rather than as translation (C-3, #104's standard). The author judges the Japanese.
  - [ ] **AC5:** WHEN any of these three claims drifts again THE SYSTEM SHALL fail a validator naming the file and the disagreeing value. A fix that leaves three hand-maintained numbers re-opens on the next release — which is precisely how all three got here.
  - [ ] **AC6:** the regression checks fail before the fix and pass after, for each of the three independently.
  - [ ] **AC7:** `git diff --name-only main` is confined to both READMEs, this spec directory, and whatever AC5 adds; every `- Validators:` command exits 0 after the last write.
  - [ ] **AC8:** THE SYSTEM SHALL carry a version bump only if a shipped path changes. If AC5 lands entirely in `scripts/` — which is not shipped — **no bump is owed**, and the spec says so rather than leaving it to be discovered at the post-receipt step.
- Out of scope: every other claim in `## Status`, which was re-checked and is **true** — "thirteen skills", each executed at least once (strengthened by #126), the tested-against version matrix, and the eval suite's status. The `## Status` section's *structure*, settled by #97. Whether the README should state a version at all, which AC5 may make moot but which this spec does not reopen.

### Clarifications

- 2026-09-13 — **AC5 demands a validator, but the three claims have sources of very different cost. How should it work?** **Answered: guard the version and the receipt counts; remove the behaviour number.** The version's source is `plugin.json` and the receipts' source is the files on disk — both exact and cheap. The behaviour count's only source is running the suite, which is already the slowest validator, so guarding it would double it on every turn to check one integer, and #54's argument against guard growth applies with force. **Removing that number removes its drift surface entirely**, which is a better outcome than policing it: the sentence still names `scripts/test-gates.sh` and still says the behaviours are tested with no model in the loop, which is the claim that matters. Rejected: guarding all three (cost), and no guard at all (C-2 is exactly what failed here — it is a reviewer rule, and the version drifted *through* an edit to the same file). Amending AC2, serving AC5.
- Not asked, because they are decisions rather than ambiguities: the guard lives in `scripts/`, not `assets/`, because it checks claims **this repository** makes about itself and a consumer's README is not this harness's business — which also settles AC8, since `scripts/` is not a shipped path. And the scratch of whether the README should carry a version at all is left alone: a reader needs it, and once it is guarded it costs nothing to keep.

## 2. Design (HOW)

**Fix approach: correct the three, then remove the reason two of them can drift again.**

The version and the receipt description stay in the README and become **derived claims with a guard**. The behaviour count leaves, because the only way to check it is to run the thing it counts.

Why not narrower — correct the three and stop: that is what happened after #48 and after #97, and the section drifted again both times. The version reached three releases stale *while the file was being edited for other reasons*, which is the specific evidence that review does not catch this class.

Why not wider — deriving the whole section, or generating the README: the other claims in `## Status` were re-checked and are true, and #97 settled the section's structure. A generator would be a new subject in a repository that has spent two days learning what a second subject costs a guard (#117).

**Affected files:**

| Path | Change |
| :-- | :-- |
| `README.md:170,174` | `v0.4.3` → the manifest's version; the behaviour count removed; "all but two" → the real count |
| `README.ja.md:171,175` | the same three, as Japanese (C-3, #104's standard) |
| `scripts/check-readme-claims.py` | **new** — version against `plugin.json`, receipt counts against `.specs/**/.review-receipt`, in both READMEs |
| `.steering/tech.md`, `.github/workflows/ci.yml` | the guard on the `- Validators:` line and in CI |

**Blast radius:** `docs/verified.md` carries its own version matrix and is not touched — it records what was tested against, which is a different claim from what the plugin *is*. `check-manifests.py` keeps its subject (the two manifests agreeing with each other); this guard adds a third party to that agreement without changing it. No shipped path moves, so **no version bump** — and the guard must not become a fourth thing to update at release time, which is the point of deriving rather than asserting.

**Why this cannot recur.** Two of the three claims become unable to disagree with their sources, because a validator compares them on every turn that touches source and in CI. The third cannot disagree with anything, because it no longer asserts a number. That is the distinction worth keeping: **one claim was made checkable and the other was made unnecessary**, and the second is the stronger fix wherever it is available.

**The guard reads the receipts the way the README describes them** — counting `reviewed_by=inline` against `subagent` — so a future reviewer changing how receipts are written breaks the guard loudly rather than making the README quietly wrong.

## 3. Tasks (TDD-ordered)
> One task is one complete Red-Green-Refactor cycle, so one green commit.

- [x] T1: `scripts/check-readme-claims.py` and its cases — red against `main`'s README for the version and the receipt count, green on a corrected fixture — then correct all three claims in `README.md`, which is what turns the real repository green (AC1, AC2, AC3, AC6).
- [x] T2: `README.ja.md` as a mirror, and the guard extended to check it too; assert AC4 and that both languages state the same three things.
- [x] T3: the guard onto `- Validators:` and into CI; assert AC7's diff confinement, AC8's no-bump, and the full validator set green.
