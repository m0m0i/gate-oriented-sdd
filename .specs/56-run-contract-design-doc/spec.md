# Spec: Run contract and design-doc on this repo and record what was observed

- Slug: 56-run-contract-design-doc Issue: 56 Type: chore Status: approved
- Author: m0m0i Date: 2026-09-05

## 1. Requirements (WHAT / WHY)

- What changes: run `contract`, then `design-doc`, against this repository, keeping what they write — `docs/CONTRACT.md`; `docs/DESIGN.md` and `docs/decisions/ADR-<n>-<slug>.md`; `.steering/structure.md` reconciled; the line `contract` step 6 adds to `.steering/tech.md`; whatever step 4 does to `.claude/agents/gate-sdd-reviewer/rules/` — plus `observations.md` beside this spec and a `docs/verified.md` section written from it. Second half of #55; as there, the observations are the deliverable.

- **What must NOT change:**
  - The 16 rule ids `G-1`…`G-9`, `C-1`…`C-7`, each at its severity and meaning. Receipts and merged PRs cite them. New rules may be added; existing ones may not move.
  - Every shipped path. The issue put the dogfood rulebook at `agents/gate-sdd-reviewer/`; it is at `.claude/agents/gate-sdd-reviewer/`, which is not shipped. So the three `agents/*/rules-lock.json` stay byte-identical and, contrary to the issue's last line, no version bump is needed.
  - The five anchors, verbatim. `contract` step 6 writes `tech.md`, the file the gates parse; no hook reads `structure.md`. The issue's AC4 guarded the wrong file.
  - Every gate and guard, `docs/{NORTH_STAR,PRD,EPICS,BACKLOG}.md`, and `CONTRIBUTING.md` (clarification 1).
  - No fixes mid-run; a defect gets an issue after. Clarifications 2 and 3 are the two protocol decisions taken outside that rule, in advance.

- Why now: these are the two skills that write state the gates read, and this repo is the only place to watch them meet a hand-authored rulebook and a live `structure.md` — every consumer's second `contract` run, never observed. #54 needs the incident, #22's gap is still real for these two documents, and #19 gets its first live instance: this reviewer has no lock, `--update` cannot create one, and step 4 says re-pin.

- Acceptance criteria:
  - [ ] **AC1:** `test-gates.sh` at the same passed count and 0 failed, and every `- Validators:` command at exit 0, before the first skill and after the last, both recorded verbatim.
  - [ ] **AC2:** WHEN `contract` completes, every rule in `docs/CONTRACT.md` carries a tier and an `Enforced by`, and every Judgment id grep-matches `.claude/agents/gate-sdd-reviewer/rules/`, count recorded.
  - [ ] **AC3:** WHEN `contract` step 4 completes, the 16 baseline ids are present at their baseline severities (diff of the extracted list), and `check-locks.py` reports the same 6 matching files with every lock byte-identical.
  - [ ] **AC4:** WHEN step 4 reaches "re-pin the lock", the command, stdout, exit code, and whether a lock exists afterwards are recorded, with no lock created by hand. #19, live.
  - [ ] **AC5:** WHEN step 4 completes, `git diff .claude/agents/gate-sdd-reviewer/rules/` is recorded as the answer to merged, regenerated, renumbered, or refused — and lands uncurated (clarification 3).
  - [ ] **AC6:** WHEN `design-doc` completes, `docs/DESIGN.md` and at least one ADR exist, each ADR carrying Status, Context, Decision, Consequences and Alternatives considered, numbered from 1 with no `ADR-` on any remote branch.
  - [ ] **AC7:** WHEN `design-doc` completes, a grep for `ADR` across the three files the reviewer reads is recorded. The skill says the reviewer's reconciliation clause escalates to an ADR; `reviewer-contract.md:52` does not mention one. Either finding is the result.
  - [ ] **AC8:** WHEN `structure.md` is updated, every baseline heading and table row survives in the diff, `check-steering-anchors.sh` resolves 5 of 5, and the five anchor lines are byte-identical.
  - [ ] **AC9:** WHEN the run completes, a `docs/verified.md` section records per handoff every seam that did not join or was not exercised, **and** every statement the run falsified in `docs/BACKLOG.md`'s preamble, both READMEs' Status sections, `structure.md`'s table, and the reviewer's no-lock paragraph. #55 recorded only what it went looking for.
  - [ ] **AC10:** `git diff --stat main` is confined to `docs/`, this spec's directory, `.steering/tech.md`, `.steering/structure.md`, and `.claude/agents/gate-sdd-reviewer/rules/`. Anything else is a finding; under a shipped path it is also reverted.
  - [ ] **AC11:** WHEN step 6 writes `tech.md`, the diff is additions only and states that `CONTRACT.md` was compiled from the rulebook, not the reverse; `observations.md` records that the step's literal wording would have been false here (clarification 2).

- Out of scope: creating the dogfood lock (#19); correcting `gate-sdd-reviewer.md:43`, which still cites closed #16 as the reason there is none (an issue, after); `backlog`, `sprint`, `init`, evals, the README Status (#58, #48, two issues to file); fixing anything found in either skill.

### Clarifications

Resolved 2026-09-05.

1. **`CONTRACT.md` vs `CONTRIBUTING.md` — which states the shared rules?** `CONTRACT.md` holds the tiered Rules table and links to `CONTRIBUTING.md` for the prose it already has. `CONTRIBUTING.md` is untouched. Superseding it would edit a root file outside AC10 and move guidance out of the file GitHub shows contributors.
2. **Step 6 says to write "that the rulebook is generated from" the contract; here the contract is derived from the rulebook.** Write the true provenance and record the deviation. `tech.md` is read by both gates and every session, which is what made #55's equivalent choice — let a false statement land, file an issue — safe there and not here. This is AC11.
3. **New Judgment rules become ids receipts cite. Commit rule?** Commit what the skill writes; the reviewer gate and the PR review are the backstop, and a bad rule is withdrawn later with its id retired. Curating would make AC5 describe a diff that did not merge.

## 2. Design (HOW)

- **Approach.** Nothing here is code. As in #55: a recorded baseline, the skills run in their documented order without intervention, a grep-checked assertion after each, a reread for what the run falsified, and the baseline re-verified. There is no data seam between the two skills — `contract` writes `tech.md` and the rulebook, `design-doc` reads the PRD and writes `structure.md` — so what this run watches is each skill meeting pre-existing state.
- **Mechanics.** Skill tool, this session, installed plugin 0.4.2, which `diff -rq` shows identical to `skills/`. Interview per #55's clarification 2, propose-then-correct, with the same caveat: mechanics and seams, not whether the skills elicit good decisions cold.
- **Baseline (T1), recorded verbatim into `observations.md`:** the `test-gates.sh` summary; each validator's exit code; the `check-locks.py` line; the anchors count; `sha256` of the three steering files, `CONTRIBUTING.md`, the four upstream `docs/`, every file under the dogfood `rules/`, and every `agents/*/rules-lock.json`; the id-and-severity list from one recorded command over the rule bullets (16 lines expected); `ls docs/decisions/` failing; `git branch -r | grep ADR-` empty; the AC7 grep's before-value.
- **Affected files.** Exactly AC10's list plus `observations.md`. `tech.md` additions only; `structure.md` reconciled; the rulebook as the skill leaves it.
- **Coverage gap.** Nothing asserts a documentation run leaves ids, locks, anchors and upstream documents alone; T1 supplies the before-values. Manual, as #55 decided: `scripts/` is out of scope and a guard belongs with #22.
- **Amendments** to an AC land in their own commit ahead of the artifact they judge (#59).
- **Rollback.** Delete the branch; nothing on `main` reads the new files.

## 3. Tasks (TDD-ordered)

> One task is one complete Red-Green-Refactor cycle, so one green commit.

- [ ] T1: capture the baseline and confirm it green.
- [ ] T2: run `contract`; assert AC2–AC5 and AC11; record.
- [ ] T3: run `design-doc`; assert AC6–AC8; record.
- [ ] T4: reread the five places AC9 names for falsified statements; record each.
- [ ] T5: write the `docs/verified.md` section (AC9).
- [ ] T6: re-run the baseline; assert AC1 and AC10; list the defects found, one issue each, and file them.
