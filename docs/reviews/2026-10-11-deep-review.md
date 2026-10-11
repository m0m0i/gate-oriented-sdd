# Deep review — 2026-10-11

- Reviewed: `origin/main` at `6f34165` (plugin 0.25.0).
- Method: 18 reviewers by subsystem and lens, 8 backlog-row re-verifiers, one reviewer of the backlog as a tool, and two completeness rounds (10 gap reviewers). Every finding was attacked by one or two independent verifiers, one reproducing it in a throwaway clone and one trying to refute it. 230 findings, about 175 confirmed; many are the same defect found from several angles.
- Status: **findings, not decisions.** Nothing here is filed or fixed. Each item names the open issue it widens, or says none tracks it. Consumer projects are labelled P1–P11.
- Antigravity items have their own run sheet: [`2026-10-11-antigravity-checklist.md`](./2026-10-11-antigravity-checklist.md).

## 1. Fail-opens reachable with no damage

1. **The quality gate skips every change committed during the turn.** `hooks/quality-gate.sh:118` asks `git status --porcelain -- <globs>`, which sees only uncommitted change. `implement` step 4 commits after every task, so on the prescribed path the gate passes without running a validator. In field transcripts from 2026-09-26 to 10-10, validators ran at 18 of 475 turn ends, and 183 of 200 source-touching commits were never covered. The skip came with #15, a day after #10 assumed the opposite; `implement:66` and `DESIGN.md:35` still claim it. No issue. Fix: run whenever the source tree differs from the last state that passed (a fingerprint under `git rev-parse --git-path gate-sdd/`), and run on any git failure.
2. **On Antigravity no gate blocks.** `gate_block` prints the JSON and exits 2. agy 1.2.16, CLI 1.3.3 and IDE 2.17.0 treat any non-zero hook exit as a failed hook, discard stdout and end the turn — reproduced at runtime. `docs/fidelity.md`'s "verified — both block" is false, and G-3 as written requires the exit code that causes it. No Antigravity session on the maintainer's machine has ever run a harness hook. No issue. See the checklist.
3. **Gates read "git failed" or "could not read" as "nothing here"** (#232, wider). Each of these silences one or both gates: a Source globs value git rejects (`:(globs)`); a CRLF `tech.md`; a pasted non-breaking space; one non-UTF-8 byte on macOS (BSD sed and awk abort under a UTF-8 locale); `status.showUntrackedFiles=no`; git refusing the repository for dubious ownership (`review-gate.sh:64`); a turn ending inside a submodule. Fix once, in the library: exit status rather than emptiness, `LC_ALL=C` on the text tools, strip CR and NBSP, `--untracked-files=all`, block on failure. Fold #122 into it.
4. **A formatter rewrites the machine-read lines.** Prettier at its defaults turns `*` in `- Source globs:` into `_`; mdformat and remark escape it as `\*`, a literal asterisk to git. All three layers go silent and the anchor check reports success. Prettier with `proseWrap=always` wraps `- Validators:`, and the gate drops every validator after the first physical line. mdformat escapes `- [x]` and remark rewrites bullets to `*`, so the review gate counts no tasks. Only this repository's `.vscode/settings.json` protects against this; `init` ships nothing. No issue. Measured fix: move the machine-read values into one fenced block every tested formatter leaves byte-identical.
5. **A spec is found only by the branch's name.** `feature/12-x`, a typo, or archiving the spec on its own branch passes the turn-end gate, the scan and CI with no review. #129 assumes a false block; the measured result is silence. Fix: derive a branch's specs from the spec files its diff adds or edits, and split #129's gate half.
6. **The receipt is barely checked.** A `reviewed_sha` of `HEAD` or the branch name resolves to the tip, so the receipt never goes stale; duplicate keys are read first-wins; the gate reads 2 of 7 fields, so `verdict=CLEAN` with `blockers=1` passes. This is what #35 should be rescoped to.
7. **A gate that outlives its hook timeout passes** on both harnesses. The budgets are fixed in the plugin's `hooks.json` (180 s, 30 s) and a consumer cannot change them since 0.23.0; a Flutter or monorepo suite exceeds 180 s on every turn. This repository's peak is 65.5 s and growing. No issue. Fix: a deadline inside the gate that blocks with "did not finish".
8. **A session started below the git root loads no plugin.** Claude Code reads the committed `.claude/settings.json` only from the starting directory, and that is where `init` enables the plugin, so `cd packages/api && claude` runs with no gate, digest or fast check, and nothing says so. Measured on 2.1.296. Missing from the README's drift table and ADR-8.
9. **Smaller fail-opens in the same class:** tasks under a sub-heading or written as `*` or numbered items are invisible to the gate; #117's deferred-task guard ships nowhere, so a task scheduled after the review passes in every install; in CI one unticked task waives review for the whole pull request, the check reads its globs and script from the pull request it judges, and `head.ref` is interpolated into a `run:` step that `init` teaches consumers to copy.

## 2. False blocks

- **The cross-branch scan blocks parallel sessions.** 27 of the 33 real blocks in the field were the scan naming another live worktree's branch mid-review; none could be cleared from the blocked session, and one looped 24 times. Fix: skip branches checked out in another worktree (`git worktree list --porcelain`); drop "merge it" from the remedies.
- A comma inside a validator command; Jira-style `PROJ-42-…` keys; merging the default branch into a reviewed branch; plan mode and headless runs (the gates never read their Stop input); GitHub issue forms (`.yml`); `check-steering-anchors.sh` on prose starting with `Docs:`.
- **Windows:** a CRLF clone of the plugin makes `plugin-gate.sh` exit 2 at `set -u` on every turn in every project; without Git Bash, Claude Code runs hooks under PowerShell, `sh` is not found and both gates are off.

## 3. Field measurements

- Verified-merge rate (the north-star metric): 141/172 = 82% — this repository 94%, consumers 77%. 24 of the 31 escapes are source changes with no spec at all, a path no gate examines.
- On the consumers' private repositories, rulesets and branch protection return HTTP 403 on the current plan, so the CI check cannot be made required; three of seven have no backstop wired.
- A real `init` → `spec` → `implement` run on fresh projects ended with a gating validator red: bootstrap mode expired at the first spec, the author told the reviewer the failure was pre-existing, and the reviewer wrote CLEAN.
- Claude Code's Stop-block cap is real: 8 consecutive blocks without a tool call, overridable with `CLAUDE_CODE_STOP_HOOK_BLOCK_CAP`; any tool call resets it, which is why the field never reached it.
- 62 of 139 review rounds ran after a pull request's first CLEAN.

## 4. Backlog

- Row 6's reason for sitting low — that what remains needs a damaged environment — is false: items 1–8 need none, and "a gate fix reaches projects by update" holds only for Claude Code. Recommended: a new top row for the gate fail-opens. This reverses the sixteenth refinement's order and is the maintainer's call.
- Verified consolidations: #227 into #188; #23 with #137; #122 into row 6; #69 into row 9 with #19; #71 into #168; #18 into #14's spec; #117 rescoped to "ship the live-spec half" on the install path; #249's template half onto the install path; close #170; #184's reopening condition has fired; #164, #165 and #166 need rescoping before their specs; #74 is partly fixed; #68 needs a tagging policy first.
- The document itself: 76 KB for 19 rows, 43% history, 40–70 positional pointers renumbered by hand per refinement; 9 of the last 11 failed CI runs were the tracker-agreement step. Recommended: stable row ids, a cap on `Why here`, history in the work logs, and a tracker check that does not fail a pull request for merges it did not make.

## 5. Structural refactors

1. One parser per format — eight formats have two to six independent parsers each, and the fail-opens above sit where they disagree.
2. One definition of "shipped" (#14): twelve copies disagree in four places; `check-version-bump.py` also misses a file moved out of a shipped directory.
3. Locks that cover the reviewer's agent file and contract, and fail on an unlisted rule file (#19, #227).
4. `scripts/test-gates.sh`: cases that parse every block's JSON, drive `implement`'s commit-per-task loop through the gates, and feed environment-dependent input; unique case names.
5. `check-leakage.sh` misses file names and symlink targets, skips binary files under GNU grep, and scans only the working tree. `release.yml` publishes through a tag-pinned third-party action with a workflow-wide write token.
