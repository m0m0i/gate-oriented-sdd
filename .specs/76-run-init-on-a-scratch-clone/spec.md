# Spec: Run init on a scratch clone of a real project, and record what it detected, asked, wrote and armed

- Slug: 76-run-init-on-a-scratch-clone Issue: 76 Type: chore Status: approved
- Author: m0m0i Date: 2026-09-05

## 1. Requirements (WHAT / WHY)

- What changes: run `init` (plugin 0.4.2, identical to `skills/`) inside a scratch clone of a real, unrelated Python project of the maintainer's — `uv`, `ruff`, `mypy`, `pytest`, a `src/` layout — after stripping the harness install it already carries, and record what was observed at each of the skill's four steps: what detection found and which candidate validators it ran before adopting; what the interview asked and what the author answered; what was written, and what was merged into rather than overwritten; and what step 4 proved, including whether the reviewer was spawnable. The record is `observations.md` beside this spec and a `docs/verified.md` section. The clone is discarded. Fifth and last skill in the test queue.

- **What must NOT change:**
  - The real project. The clone is local, from the working checkout, on its default branch; nothing is pushed anywhere.
  - This repository's shipped paths and gates: every `- Validators:` command at exit 0 and `test-gates.sh` at its count, before and after; the branch touches `docs/verified.md` and this directory only. A defect in `init` gets an issue, not a fix.
  - **No identifier from the target enters this repository.** The record names the toolchain, the counts, and the skill's behaviour — never the project, a path inside it, a test name, or a value from its steering. `check-leakage.sh` is run by hand before every push; #73's first CI run is the precedent.
  - The interview is answered by the author, live, in their own words. That is the cold interview `docs/verified.md` lists as unverified, as far as it can be run by someone who knows the project.

- Why now: CAP-4's falsifier — a first turn blocked by a failure that predates the user — has never been observed; `init` has run once here as a migration (#17) and never with detection or the interview; and #48's README rewrite waits on this run to say every skill has executed.

- Acceptance criteria:
  - [ ] **AC1:** WHEN the clone is prepared, `observations.md` SHALL list what was removed and what was kept, with the rule for each; and the clone SHALL have no `.steering/`, `.specs/`, `.work_logs/`, harness hooks or agents, while keeping the project's own `AGENTS.md`, `CLAUDE.md`, issue templates, and tool configuration.
  - [ ] **AC2:** WHEN step 1 completes, the record SHALL show, per candidate validator the skill proposed, the command, whether the skill ran it before adopting it, its exit code on the clean clone, and what the skill did with a failure — fix, omit, or record as known-failing.
  - [ ] **AC3:** WHEN step 2 completes, the record SHALL hold every question asked, its recommended answer, the author's answer, and whether the two differed — with the count of questions, which the skill caps at five.
  - [ ] **AC4:** WHEN step 3 completes, the five machine-read lines SHALL exist in the clone's `.steering/` and `check-steering-anchors.sh` SHALL resolve 5 of 5 there; the record SHALL say which files the skill created, which it merged into, and whether it showed a diff before touching `AGENTS.md` or an existing template.
  - [ ] **AC5:** WHEN step 4 completes, the record SHALL show `quality-gate.sh` and `review-gate.sh` each run in the clone with exit codes: both silent on the clean tree, the quality gate firing on an introduced lint violation and silent after the revert, and what the skill reported about the reviewer being spawnable.
  - [ ] **AC6:** THE SYSTEM SHALL record every seam that did not join and every seam not exercised, and whether the skill declared success before or after step 4's proof.
  - [ ] **AC7:** `git diff --stat main` here SHALL be confined to `docs/verified.md` and this directory; validators at exit 0; `check-leakage.sh` clean on every commit.
  - [ ] **AC8:** WHEN the run completes, `docs/verified.md` SHALL gain a section for it and its "Still to verify" list SHALL drop the `init` items it now covers and add what this run could not reach.

- Out of scope: the upgrade path — `init` on the unstripped clone, "diff and upgrade rather than reinstalling" — which is what every existing consumer hits and is a candidate for the next sprint; fixing anything found; pushing the clone anywhere; the README (#48).

### Clarifications

Resolved 2026-09-05.

1. **What does "stripped" remove?** Harness state only: `.steering/`, `.specs/`, `.work_logs/`, `.claude/agents/`, `.claude/hooks/`, the `hooks` key of `.claude/settings.json`, and any `check-*.py` or `check-*.sh` copy under the project's `scripts/`. Kept: `AGENTS.md`, `CLAUDE.md`, the issue templates, and every tool configuration, because `init` treats those as the project's own and must merge into them — the path worth watching. Removing everything `init` ever wrote was rejected: it tests the greenfield path the skill itself calls the special case, and never exercises merge.

## 2. Design (HOW)

- **Approach.** The #55/#56/#58 protocol, on a target outside this repository: prepare the clone and record its state, run the skill once end to end with its four steps recorded as they happen, write the `verified.md` section from the record, re-verify this repository, discard the clone.
- **Mechanics.** `git clone` from the working checkout by local path into this session's scratch directory, default branch checked out, dependencies synced so the candidate validators can run. `init` is invoked through the Skill tool in this session; every action it prescribes is performed by absolute path inside the clone, since the skill's own text says it runs inside the target. The reviewer it writes into the clone's `.claude/agents/` cannot be registered in this session, so step 4's spawnability check is expected to report a restart — that expectation is written down here so the observation can contradict it.
- **The interview.** Five questions at most, each put to the author with the skill's recommended answer, answered live. The record keeps recommendation and answer side by side (AC3), so accepted-as-recommended is visible as in #55.
- **Record hygiene.** `observations.md` and the `verified.md` section describe the target by toolchain, counts and behaviour only. Before every commit on this branch: `check-leakage.sh`, and a scratch-directory script — not committed — that greps the spec directory and `verified.md` for the target's name and path.
- **Affected files.** `docs/verified.md`, `.specs/76-run-init-on-a-scratch-clone/`. AC7 is the check.
- **Coverage gap.** None new here; the observation *is* the coverage, and the clone is the fixture.
- **Amendments** to an AC land alone, ahead of the artifact they judge (C-8).
- **Rollback.** Delete the branch and the clone.

## 3. Tasks (TDD-ordered)

> One task is one complete Red-Green-Refactor cycle, so one green commit.

- [x] T1: clone, strip per clarification 1, and record what was removed and kept with the rule for each (AC1).
- [x] T2: run `init` in the clone, steps 1–4, recording as it goes; assert AC2–AC6.
- [ ] T3: write the `docs/verified.md` section and update "Still to verify" (AC8).
- [ ] T4: re-verify this repository (AC7), discard the clone, list the defects found and file them.
