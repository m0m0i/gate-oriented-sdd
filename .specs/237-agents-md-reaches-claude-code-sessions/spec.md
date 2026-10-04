# Spec: AGENTS.md reaches a Claude Code session, and two of its passages stop disagreeing with the tree

- Slug: 237-agents-md-reaches-claude-code-sessions   Issue: 237   Type: chore   Status: approved
- Author: m0m0i   Date: 2026-10-04

## 1. Requirements (WHAT / WHY)

- What changes: three files of this repository's own agent configuration, one per finding in #237.
  - `CLAUDE.md` gains an `@AGENTS.md` import below its existing sentence (finding 1).
  - `AGENTS.md`'s validator block gains the four commands on `.steering/tech.md`'s `- Validators:` line that it leaves out (finding 2).
  - The sentence giving the retired #16 reason for the unpinned rulebook is deleted from `AGENTS.md` and from `.claude/agents/gate-sdd-reviewer.md` (findings 3 and 4).
  - Beside them: `docs/BACKLOG.md` cites the two follow-ups (Clarification 4), and the version moves from 0.21.6 to 0.21.7 (Clarification 2).
- **What must NOT change:** every other line of those three files.
  - `CLAUDE.md`'s existing sentence stays verbatim, because it states the cross-tool rule.
  - `AGENTS.md:63` stays as it is. Its claims about where the reviewer contract lives and how many agents register belong to #235. It also carries the only `reviewer-contract.md` path in `AGENTS.md`, and `scripts/check-contract-path.py` fails a listed document that names none.
  - Each of the two edited paragraphs keeps its current reason (#19) and its pointer to `docs/decisions/ADR-6`.
  - Nothing under `skills/`, `agents/`, `hooks/` or `assets/` changes.
- Why now: finding 1 means every Claude Code session in this checkout runs without `AGENTS.md`, the unattended ones included. That leaves out the leakage rule, which `AGENTS.md` calls the guard that matters most, and the frontmatter prohibition. The other three findings are the same file disagreeing with the tree. Filed 2026-10-04 from a prompt audit, and taken now at the author's request. It is the smallest open item, and it lands ahead of #235, whose spec edits the neighbouring lines.
- Acceptance criteria:
  - [ ] **AC1:** WHEN a Claude Code session starts in this repository, with hooks disabled, no tools, and **Project instructions** pinned to its default `claude-md-or-agents-md`, THE SYSTEM SHALL answer both probe questions in `observations.md` from `AGENTS.md`'s text. Before the change it answers `NOT-IN-CONTEXT` to both. The same holds under `claude-md`. The record holds the probe, the command and settings, the Claude Code version, and every output before and after.
  - [ ] **AC2:** every command on the `- Validators:` line appears in `AGENTS.md`'s validator block, in the line's order. The two PR-only guards the block already names stay after them.
  - [ ] **AC3:** neither `AGENTS.md` nor `.claude/agents/gate-sdd-reviewer.md` states the #16 reason. In each, the diff of that paragraph is the one sentence removed.
  - [ ] **AC4:** `git diff --name-only origin/main...HEAD` names only these files: the three above, this spec's directory, `docs/BACKLOG.md`, `.work_logs/2026-10-04.md`, `plugin.json` and `.claude-plugin/plugin.json`. Every validator on the `- Validators:` line exits 0 after the last write.
- Out of scope:
  - `AGENTS.md:63` (#235).
  - `init`'s pointer instruction, and the fidelity and README claims that Claude Code reads a root `AGENTS.md` (#239).
  - `check-version-bump.py` not seeing a change to `AGENTS.md` (#240).

### Clarifications

Asked and answered 2026-10-04, before Design.

1. **How does a session get `AGENTS.md`: an `@AGENTS.md` import, or delete `CLAUDE.md` and rely on native reading?**
   - **Answer: the import.**
   - Why the question exists: mid-turn, the author asked whether Claude Code now reads `AGENTS.md` natively. It does, from v2.1.277. Under the default **Project instructions** value, `claude-md-or-agents-md`, it reads `AGENTS.md` only when there is no `CLAUDE.md`, `.claude/CLAUDE.md` or `CLAUDE.local.md` in the working directory or above it. Sources: code.claude.com/docs/en/memory, § AGENTS.md, and the changelog for 2.1.277 and 2.1.281.
   - The docs name this repository's exact setup, "a `CLAUDE.md` that tells Claude in words to read `AGENTS.md`", as a workaround to replace with either fix.
   - Why the import: it loads the file under every **Project instructions** value except `managed-only`, which loads no project instruction file in any form, and the docs say keeping it never loads the file twice. Native reading needs 2.1.277, or 2.1.281 on Bedrock, Vertex AI, Foundry, gateways and sessions with telemetry disabled. It also needs the built-in `agents-md` plugin enabled, and it may not happen in the first session after an upgrade.
   - Deleting `CLAUDE.md` would also clear one of 2.1.289's nine validator warnings. It would settle #235's third open question here, though, and that question is #235's. If #235 deletes `CLAUDE.md` later, native reading takes over.
2. **Does this carry a version bump?**
   - **Answer: yes, a patch.**
   - `AGENTS.md` ships. `scripts/package-release.py` puts it and `rules/AGENTS.md` in `gate-sdd.zip`, which `release.yml` builds only on a version tag. The repository documents that Antigravity's loader merges `rules/AGENTS.md` into an install (`AGENTS.md:26`, from #145). `docs/verified.md` records no direct observation of that merge.
   - The author noted that `main` was already past 0.21.5, and asked for a check before proceeding. On `origin/main`, `plugin.json` and `.claude-plugin/plugin.json` both read 0.21.6 (#234), the latest tag is `gate-sdd--v0.21.5`, and no open branch claims 0.21.7. So the bump is 0.21.6 → 0.21.7.
   - CI's guard passes this branch with or without a bump, which is #240. The bump lands as `implement` step 5, not as a task.
   - This overrides #72's "`AGENTS.md` is not a shipped path". That predates the `rules/` symlink (#145) and the release packager (#140).
3. **Delete the #16 sentence, although #72's AC1 required both paragraphs to "say #16 is closed"?**
   - **Answer: delete it.**
   - #72 corrected files that gave #16 as the *live* reason. That claim is gone from both files, and ADR-6 holds the history.
   - Once finding 1 lands, `AGENTS.md` loads into every session, so a sentence that prescribes nothing costs context on every turn.
   - This overrides that clause of #72's AC1. The rest of AC1, naming #19 and pointing at ADR-6, still holds.
4. **This branch has to cite #237 in `docs/BACKLOG.md`, or `check-backlog-tracker.py` fails its own pull request. Where, and do the two follow-ups get filed?**
   - **Answer: cite #237 in row 9's `Why here`, and file both follow-ups.**
   - A `Why here` cell may cite a closed issue, so the citation stays true after this branch closes #237. An Item cell would not.
   - #239 (`init`'s pointer) joins row 9's Item cell, which is the install path.
   - #240 (the version guard) joins row 11's Item cell, not row 12 as the question proposed. Row 11 is "the shipped-path definition has one home", and it already names `package-release.py` as the third copy of the list with no guard comparing them. #240 is the first case of those copies disagreeing. Reported to the author as a change from what was agreed.
   - *Amended 2026-10-04, before T1:* #238 now cites #237 in row 18's `Why here`, "the way #229 was", as work taken at once and closed by its own merge. #238 came from another session, and the author merged it at 01:09Z. This branch therefore does not cite #237. It cites only the two follow-ups, and row 9 gains no sentence about #237.

## 2. Design (HOW)

- Approach:
  - **`CLAUDE.md`:** a blank line, then `@AGENTS.md`, below the existing sentence. The sentence stays verbatim and first. The docs' example puts the import first and Claude-specific instructions after it. This sentence is not an instruction to Claude, so nothing depends on where it sits relative to the import.
  - **`AGENTS.md`'s validator block:** four lines after `./assets/check-locks.py`, in the Validators line's order: `check-document-set.py`, `check-contract-path.py`, `check-readme-claims.py`, `check-reviewer-allow-list.py`. Each gets a one-clause comment in the block's style, taken from its script's own docstring.
  - **The #16 sentence:** deleted in both files, with nothing else on either line changed.
  - **`docs/BACKLOG.md`:**
    - Row 9's Item cell gains **#239**, and its `Why here` gains one sentence for it.
    - Row 11's Item cell gains **#240**, and its `Why here` gains one sentence for it.
    - `Last refined` stays as it is. Like #236 placing #235, this is a placement made by a pull request, not a refinement.
- Affected files:
  - `CLAUDE.md`
  - `AGENTS.md`
  - `.claude/agents/gate-sdd-reviewer.md`
  - `docs/BACKLOG.md`
  - this directory: `spec.md`, `observations.md`, the receipt
  - after the receipt: `plugin.json`, `.claude-plugin/plugin.json`, `.work_logs/2026-10-04.md`
- **Coverage gap:**
  - Nothing in the repository tests that a session loads `AGENTS.md`. The probe in AC1 is run and recorded before the change in T1, so the after-state is an observation, not an assertion.
  - Nothing compares `AGENTS.md`'s block to the Validators line. AC2 is checked by a throwaway comparison, recorded with its output.
  - `scripts/check-contract-path.py` already guards the one preserved line whose loss would matter.
- Risks:
  - **Every session now pays for `AGENTS.md`'s 80 lines.** That is the intent. It is also why Clarification 3 removes the one sentence that prescribes nothing.
  - **`rules/AGENTS.md` is documented to deliver the edited text to Antigravity installs.** Every edit deletes a retired reason or adds a validator line, and none changes an instruction a consumer would act on.
  - **The review gate cannot see these files.** All three, and `docs/BACKLOG.md`, sit outside `Source globs`. `:(glob)rules/**/*.md` does not see through the `rules/AGENTS.md` symlink, which is #240's other half. So a receipt cannot go stale on an edit to them. Any change to them after the review is re-reviewed by discipline, because the gate will not ask.
- Rollback: `git revert`.

## 3. Tasks (TDD-ordered)

> One task is one complete Red-Green-Refactor cycle, so one green commit. No task is sequenced after the review.

- [ ] T1: record the baseline in `observations.md`: the AC1 probe before, the AC2 comparison before, the AC3 greps before, and the validators at exit 0.
- [ ] T2: make the three-file change. Record the probe and both comparisons after, and assert AC1–AC3 and AC4's validators.
- [ ] T3: cite #239 and #240 in `docs/BACKLOG.md` (Clarification 4). Record `./scripts/check-backlog-tracker.py` reporting no drift.
