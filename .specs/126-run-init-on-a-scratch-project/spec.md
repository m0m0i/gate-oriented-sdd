# Spec: Run init at 0.7.0 on a scratch project, and record what it detected, asked, wrote and armed
- Slug: 126-run-init-on-a-scratch-project   Issue: 126   Type: chore   Status: approved
- Author: m0m0i   Date: 2026-09-12

## 1. Requirements (WHAT / WHY)
- What changes: build a scratch project with a real toolchain, run `init` (plugin **0.7.0**, identical to `skills/`) inside it, and record what was observed at each of the skill's four steps — detection and which candidate validators ran before adoption; the interview's questions and answers; what was written and what was merged rather than overwritten; and what step 4 proved. The record is `observations.md` beside this spec and a `docs/verified.md` section. **The scratch project is discarded.** Nothing in this repository's shipped surface changes.
- **What must NOT change:**
  - **This repository's gates and shipped paths.** Every `- Validators:` command at exit 0 and `scripts/test-gates.sh` at its count, before *and* after; the branch touches `docs/verified.md` and this spec directory only. Nothing under `skills/`, `agents/`, `hooks/`, `assets/` or `scripts/` moves, so **no version bump is owed** — `docs/` is in neither `Source globs` nor `check-version-bump.py`'s `SHIPPED`.
  - **`init` itself.** A defect it exhibits gets an **issue, not a fix** — #76's rule, and the reason a verification run stays a verification run. #81, #83 and #84 are all expected to fire; confirming them at 0.7.0 is a result.
  - **The reviewer's independence.** The run is observed and recorded; the reviewer reviews the record, not the run.
- Why now: **#76 ran this last at plugin 0.4.2 and the harness is at 0.7.0.** Three changes since have never been executed by `init` outside fixtures:
  - **#82** (0.7.0) — a shipped reviewer names the contract relative *and* concrete. Its justification came from a reviewer failing to open the file, not from reasoning, so only a run is evidence that it now works. **This is the observation `1.0.0` waits on.**
  - **#110** (0.6.0) — `init` writes `- Mode:` and installs `check-document-set.py` onto `- Validators:` and into CI.
  - **#109** (0.5.1) — the minimum set is ten skills, five documents, three issue templates.
- **The target is synthetic, and that is a real limitation rather than a caveat.** CAP-4 is "installation into a repository that already has opinions", and a repository whose opinions were chosen by the installer cannot prove it. #76 used a real project for exactly that reason. This run therefore tests **CAP-4 weakly**, and a run against a real project is still owed and is *not* discharged here. `docs/verified.md` must say so in the row itself, not only in this spec — a record that overstates what it observed is worse than no record.
- Acceptance criteria:
  - [ ] **AC1:** THE SYSTEM SHALL leave this repository behaving identically — every `- Validators:` command at exit 0 and `test-gates.sh` at the same count, captured **before** the run as a baseline and re-run after.
  - [ ] **AC2:** `git diff --name-only main` is confined to `docs/verified.md` and this spec directory. No shipped path changes, and `check-version-bump.py` reports none.
  - [ ] **AC3:** WHEN the record is written THE SYSTEM SHALL contain no identifier from the scratch project beyond the toolchain this spec declares — no generated name, path, or value that a reader could mistake for a real project's. `./scripts/check-leakage.sh` is run by hand before any push.
  - [ ] **AC4:** Each of `init`'s four steps is recorded with what was observed **and what could not be** (C-9). A step that could not be exercised is named as such rather than omitted.
  - [ ] **AC5:** WHEN `init` has finished THE SYSTEM SHALL record whether a shipped reviewer opened its contract **with no hand-edit** — the exact observation `1.0.0` waits on — stated either way, and by attempting it rather than by reading the file.
  - [ ] **AC6:** #81, #83 and #84 are each recorded as **confirmed or not reproduced at 0.7.0**, with what was observed. Any *new* defect gets an issue, and its number appears in the record.
  - [ ] **AC7:** `docs/verified.md` gains a section for this run that states the synthetic-target limitation in the row itself, and updates "Still to verify" so the real-project run remains listed as owed.
  - [ ] **AC8:** THE SYSTEM SHALL NOT modify `init` or any other shipped file in response to what the run finds.
- Out of scope: fixing #81, #83, #84 or anything new. Running the inception skills (`northstar`, `prd`, `epics`, `backlog`, `contract`, `design-doc`) in the scratch project — #55 and #56 covered those, and this run is about `init`. A real-project run, which stays owed. Any change to `docs/fidelity.md`'s Antigravity rows, which this run cannot observe from a Claude Code session.

### Clarifications

- 2026-09-12 — **Who answers `init`'s step-2 interview on a project the operator built?** Every question has a known answer, which makes the interview self-answered and proves nothing about whether the questions are good. **Answered: the operator answers, and the record says so.** It exercises that the questions are *asked*, in what order, and whether step 2 correctly asks only what step 1 could not detect — and it is evidence for nothing about whether they are the right questions. The rejected alternative was a genuine cold interview with someone who had not seen the project, which is exactly the thing `docs/verified.md` has listed as unverified since the start; it is not taken here, so **that entry stays unverified and the record must not imply otherwise.** Serving AC4.
- 2026-09-12 — **Which toolchain, and therefore which reference reviewer?** **Answered: TypeScript** — `tsc`, a linter, a test runner, a `src/` layout, existing issue templates and a commit convention. #76 used Python, so `agents/ts-reviewer.md` has never been installed by any run, and its contract line is one of the three #82 changed. That makes it the strongest target for AC5. Rejected: repeating Python, which gives a clean before/after against #76 and covers no new reviewer; and an unrecognised stack, which exercises the `agents/_template/` fallback and would surface more defects but is weaker evidence for AC5, since the question is whether a **shipped** reviewer opens its contract. Serving AC5, AC6.
- Not asked, because they are decisions rather than ambiguities: the scratch project lives in a temp directory outside this repository and is deleted at the end; a defect that stops `init` mid-run is recorded and the run continues as far as it can, because a run that halts on the first known defect observes less than one that does not.

## 2. Design (HOW)

**Approach: capture a baseline, run the skill as written, record continuously, then re-verify the baseline.** The order matters — the invariant is that *this* repository is unchanged, and "nothing broke" is an assertion unless the before-state was captured before anything ran.

The scratch project is built in a temp directory, given a TypeScript toolchain with genuinely runnable commands (so step 1's "run each candidate validator before adopting it" has something real to run), an existing `.github/ISSUE_TEMPLATE/` and a commit convention — the two things `init` is supposed to **merge into rather than replace**. It is a git repository, because `init` and both gates read git. Nothing is pushed. It is deleted in the last task.

**`init` is run exactly as written, with no help.** Where it fails, the run records the failure and continues; where it would need a fix, the fix is not made. That is the difference between a verification run and a repair, and it is the only thing keeping this spec's invariant true.

**Affected files:**

| Path | Change |
| :-- | :-- |
| `.specs/126-run-init-on-a-scratch-project/observations.md` | **new** — the record, written as the run proceeds |
| `docs/verified.md` | a section for this run, and "Still to verify" updated so the real-project run and the cold interview both stay owed |
| — | nothing else. No shipped path, so no version bump. |

**Coverage gap — the part of this that is not a test.** A verification run has no failing test to write first; its "baseline" is the state of *this* repository, and its findings are observations rather than assertions. So the honest analogue of the chore template's first task is: **capture the invariant mechanically before anything runs**, so AC1 is a comparison rather than a memory. That is T1, and it is why T1 produces a file rather than a green tick.

**What this run cannot observe, recorded now rather than discovered later (C-9):** Antigravity's half of everything — `.agents/` placement, whether a reviewer there picks the Antigravity-labelled path, and the subagent invocation contract `docs/fidelity.md` calls "partial — untested". A Claude Code session cannot see any of it. And CAP-4, because the target's opinions were chosen by the installer.

**Rollback:** delete the branch. Nothing outside it is touched, and the scratch project never existed in version control.

## 3. Tasks (TDD-ordered)
> One task is one complete Red-Green-Refactor cycle, so one green commit.

- [x] T1: capture this repository's baseline — every `- Validators:` command and `test-gates.sh`'s count, recorded to `observations.md` — then build the scratch project and record its pre-`init` state (AC1's before-half).
- [x] T2: run `init` steps 1–4 in the scratch project, recording each as it goes, including what could not be exercised; assert AC4, AC5, AC6.
- [ ] T3: write the `docs/verified.md` section with the synthetic-target limitation in the row itself, and update "Still to verify" (AC7).
- [ ] T4: re-run the baseline and compare, confirm the diff is confined and no shipped path moved, run `check-leakage.sh` by hand, file any new defect as an issue, and delete the scratch project (AC1's after-half, AC2, AC3, AC8).
