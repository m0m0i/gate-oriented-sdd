# Spec: the quality gate skips a turn whose source change was committed before the turn ended
- Slug: 297-quality-gate-runs-on-committed-work   Issue: 297   Type: bug   Status: approved
- Author: m0m0i   Date: 2026-10-15

## 1. Requirements (WHAT / WHY)
- Reproduction: the fixture at `scripts/test-gates.sh:1866` — `- Validators: sh -c "echo RAN >&2; exit 1"`, `- Source globs: *.txt`, one commit holding `src.txt` and `NOTES.md`. Follow `implement` step 4 (`skills/implement/SKILL.md:22`): `echo more >> src.txt && git commit -qam 'task 1'`, then end the turn. The gate prints `{}` and exits 0, having run no validator. Re-measured at `b578e28` under macOS `sh` and `dash`, with the issue's variants: committed then a docs-only edit, committed on a feature branch — both `{}` exit 0. Two more from the same line: `- Source globs: :(globs)*.txt` with an uncommitted source change, and an untracked source file under `status.showUntrackedFiles=no` — both `{}` exit 0.
- Expected: a source change made during the turn runs the validators at that turn's end whether or not it was committed. `implement:66`, `docs/DESIGN.md:36`, `skills/spec/templates.md:7` and `hooks/quality-gate.sh:4-5` all say so: a red task cannot be committed without ending the turn red, and the bottom row is "not skippable".
- Actual: `hooks/quality-gate.sh:121` decides with `git status --porcelain -- <globs> 2>/dev/null | grep -q . || gate_pass`. `git status` sees only uncommitted change, so a committed task leaves nothing to see. On `implement`'s commit-per-task path the gate runs validators only when a turn ends with source still uncommitted, and a red commit is invisible to every later turn end until one leaves a source edit uncommitted — and is then reported against that turn's unrelated work. The pipeline's status is `grep`'s, so git's exit 128 on a rejected pathspec reads as "nothing changed".
- Impact: every `implement` run, in every project with a `- Source globs:` line — this repository and a real, unrelated project of the maintainer's that follows commit-per-task. `docs/reviews/2026-10-11-deep-review.md` §1.1 counted 183 of 200 source-touching commits never covered by a turn-end validator run (field transcripts, 2026-09-26 to 10-10; not re-measured). The `{}` it prints is indistinguishable from a clean pass. Under `- Owns: gates never fail open`, a gate that silently stops checking is a BLOCKER (`.steering/product.md`). CI is not a backstop everywhere: on consumers' private repositories the check cannot be made required (deep review §3).
- **Root cause:** the skip answers the wrong question. #15 added it to keep docs-only turns free, and asked "is any source uncommitted?" when the question that keeps the guarantee is "has the source changed since the validators last passed?". The two agree only while nothing is committed between turn ends, which was the assumption #10 was settled on three days later and which `implement`'s commit-per-task loop breaks on every task. The four cases #15 added (`scripts/test-gates.sh:1876-1894`) all leave the change uncommitted, so no case ever drove a commit through the gate. The rejected-pathspec half is the same line deciding from a pipeline whose status is not git's.
- Acceptance criteria:
  - [ ] **AC1:** WHEN a source change matching `- Source globs:` is committed during the turn and a validator fails on it, THE SYSTEM SHALL block at that turn's end and name the validator — including on the first turn end in a clone or worktree, and on the default branch.
  - [ ] **AC2:** WHEN a turn ends and the source matching `- Source globs:` is unchanged since the last turn end at which every validator passed — whether that source is committed, staged, or still uncommitted, and whatever non-source files changed — THE SYSTEM SHALL pass without running the validators. Staging or committing content that already passed is not a change.
  - [ ] **AC3:** WHEN a turn end's validators failed, THE SYSTEM SHALL run them at every later turn end, docs-only turns included, until a run passes.
  - [ ] **AC4:** WHEN no passing run has been recorded for this worktree — a fresh clone, a new worktree, the first turn after this change ships — THE SYSTEM SHALL run the validators.
  - [ ] **AC5:** WHEN any step that decides whether source changed fails — a rejected pathspec such as `:(globs)`, an unreadable index, a record that cannot be read or written — THE SYSTEM SHALL run the validators rather than pass, and say on stderr which step failed, whatever the validators' verdict. An untracked source file counts under `status.showUntrackedFiles=no`.
  - [ ] **AC6:** THE SYSTEM SHALL record a pass only for the source state the validators ran against: a source edit made while the validators run is not recorded as passed, and a same-size edit made within the same second as the last index write is still seen as a change.
  - [ ] **AC7:** WHEN the `- Validators:` line, the `- Source globs:` line, the gate's own code, or the plugin-root environment the gate runs under (#264's two environments) differs from the recorded pass, THE SYSTEM SHALL run the validators. `scripts/test-gates.sh` case 219 passes unchanged.
  - [ ] **AC8:** unchanged: with no `- Source globs:` line, or outside a git work tree, the gate runs the validators on every turn end as today; the `set -f` region (cases 202-204) and the bootstrap guard (case 159) are untouched; the gate leaves the real index unmodified and writes no git objects; the record is per worktree, under the git directory, and never tracked.
  - [ ] **AC9:** the tests — a `scripts/test-gates.sh` case for each of AC1 to AC8, placed after the fixture it uses. The cases for AC1, AC3, AC4, AC5 and AC7 fail on the tree before the fix. Those for AC2, AC6 and AC8 pin behaviour `main` already has, so each is shown red under a named mutation of the new code instead, recorded in the case's comment. The four cases that state when the gate is silent (`:1876`, `:1880`, case 164's and case 202's docs halves) keep their assertions, with fixtures that record a passing run first.
  - [ ] **AC10:** every statement of when the quality gate runs is true after the change — `README.md:108`, `README.ja.md:75`, `skills/init/SKILL.md:66`, `.github/workflows/ci.yml:84-89`, `assets/check-unreviewed-work.sh:17-18`, `scripts/test-gates.sh:1865` and `:4846-4848`, the comment above the skip in `hooks/quality-gate.sh` — and `docs/layout.md` and `docs/DESIGN.md` name the new record as harness-written state.
  - [ ] **AC11:** every command on the `- Validators:` line exits 0.
- Out of scope:
  - #304, a gate that outlives its hook timeout passing. This change makes it costlier (Q1), and #304 is taken next.
  - #232, the same "git failed reads as nothing changed" class in `gate-lib.sh`'s receipt comparison. This spec fixes the quality gate's own line only.
  - Inputs outside the globs that validators read — lint configuration, lockfiles, fixtures, and in this repository `README*.md`, `.specs/`, `docs/` and `.steering/`. Today a dirty source tree re-runs validators on every turn end; after this change a passed state is not re-run when only those change. Stated as a known limit, not fixed.
  - An `--assume-unchanged` source edit, invisible today and after. The record is a cache an agent could forge, the same trust class as `.review-receipt`; CI, which always runs the validators, is the backstop.

### Clarifications
Asked and answered 2026-10-15, each on the recommended option.

- **Q1 — #304.** A run cut off by the hook timeout records no pass, so after this change a suite slower than 180 s spends the whole budget on every turn that follows a source commit and then passes silently; today that happens only on turns ending with uncommitted source. **A:** ship this first, state the cost as a known limit, and take #304 next. This repository's suite runs in about 66 s.
- **Q2 — a git failure while deciding.** **A:** run the validators and name the failed step on stderr (AC5 amended). Blocking would turn a `- Source globs:` typo into a block on every turn even when the validators pass, and the library-wide policy for this class is #232's.
- **Q3 — no recorded pass.** **A:** run, with no shortcut (AC4). Seeding from `HEAD` was measured to reproduce this bug on the first turn, and seeding from the merge-base trusts the default branch to be green, which CI cannot enforce on consumers' private repositories. The cost is one full run per new clone or worktree.

Decided in Design rather than asked, because the repository answers them: the helper stays in `hooks/quality-gate.sh`, since nothing else reads the record; the inputs AC7 keys on; the cost of hashing untracked files is accepted and stated; and the bump is a minor, because the gate's behaviour changes.

## 2. Design (HOW)
- **Fix approach.** The skip stops asking "is any source uncommitted?" and asks "has the source changed since the validators last passed?". The gate fingerprints the source matching `- Source globs:`. It skips only when that fingerprint was computed without error and equals a record written by the last run in which every validator passed. Every other path runs the validators. This is the issue's candidate with three corrections that the 2026-10-15 measurements forced: the fingerprint is of content, not of index state; the index copy keeps its mtime; and the record is keyed on the environment as well as on the lines.
  - **The fingerprint** is built in a copy of the index, so the real index is never touched:
    - `cp -p` the index (`git rev-parse --git-path index`) to a `mktemp` file under `${TMPDIR:-/tmp}`.
    - List `git ls-files -z -c -o --exclude-standard -- <globs>` to a file.
    - Feed that list to `GIT_INDEX_FILE=<copy> git update-index -z --add --remove --info-only --stdin`.
    - Hash `GIT_INDEX_FILE=<copy> git ls-files -s -- <globs>` with `git hash-object --stdin`, together with the keys below.
    - The result follows worktree content after git's clean conversion. It is unchanged when validated content is staged or committed (AC2), and changes for committed, staged, unstaged, untracked-not-ignored, deleted, renamed and mode changes. It ignores ignored files and mtime-only changes.
    - `-o` lists untracked files regardless of `status.showUntrackedFiles` (AC5). `--info-only` writes no objects (AC8).
    - `cp -p` keeps git's racy-entry check working. A plain `cp` gives the copy a fresh mtime, and a same-size edit made within the same second as the last index write then matches on stat alone and keeps its old blob id. That was measured as a red tree passing (AC6).
  - **Keys hashed in with the listing** (AC7):
    - a format tag, `gate-sdd quality-pass 1`;
    - the `- Validators:` line and the `- Source globs:` line, so adding a validator runs it;
    - `${CLAUDE_PLUGIN_ROOT-}` and `${GATE_SDD_PLUGIN_ROOT-}`, so a pass recorded under one of #264's two environments is not trusted by the other. This is what keeps case 219 and `init` step 4.1's by-hand run honest;
    - `git hash-object` of `$DIR/quality-gate.sh` and `$DIR/gate-lib.sh`. The plugin's path already changes with its version, but an Antigravity copy has no such variable, so an upgrade by re-copy runs once.
  - **Every git step is checked on its own:** redirected to a file or captured alone with `$(...)`, never through a pipeline, because neither `sh` nor `dash` has a portable `pipefail`. Any failure leaves the fingerprint empty. The step's name goes to stderr (Q2), and the validators run (AC5). `git rev-parse --is-inside-work-tree` must print `true` before anything is computed: `--git-dir` succeeds in a bare repository and inside `.git/`, where `ls-files -s` prints nothing and exits 0.
  - **The record** is one line at `$(git rev-parse --git-path gate-sdd/quality-pass)`:
    - The path is relative, and safe because the gate has already changed to the toplevel. Validators run in a `$(eval ...)` subshell, so they cannot move it. No `--path-format`, which would need git 2.31.
    - git treats an unknown name under the git directory as per-worktree. The record is therefore `.git/gate-sdd/quality-pass` in the main checkout and `.git/worktrees/<name>/gate-sdd/quality-pass` in a linked one, is never tracked, and goes away with `git worktree remove`.
    - It is written only when every validator passed, and its value is the fingerprint computed **before** the first validator ran. A source edit made during the run therefore does not match next turn (AC6). It is written with `mktemp` in the same directory and then `mv -f`, so a concurrent reader never sees a torn value. Two sessions in one worktree can only cost each other a run, because every value written is a state that passed.
    - If the record cannot be written, the gate says so on stderr and the turn's verdict stands. Next turn runs again: a cost, never a pass.
  - **Temp files** are removed by a `trap` on `EXIT`, `INT` and `TERM`. `GIT_INDEX_FILE` prefixes external `git` commands only. On macOS `/bin/sh`, a prefix on a shell function call persists and is exported to every validator, measured.
  - **Unchanged (AC8):**
    - With no `- Source globs:` line, or outside a work tree, the gate runs on every turn as today.
    - The `set -f`/`set +f` split stays exactly as it is, and the new code uses the quoted `"$@"` and `"$globs"` only, so case 204's region check holds.
    - The bootstrap guard (`:23-63`, case 159) is not touched.
    - The stale comment at `:115` that says case 203 recognises the region is corrected to 204.
  - **Why not the narrower or wider fix:**
    - Comparing against the merge-base fails open on commits to the default branch, and it runs on every turn of a branch once it holds one source commit, which is the cost #15 removed.
    - A session-start baseline needs a second hook on each harness, Antigravity has no `SessionStart`, and it misses red commits from earlier sessions.
    - Reading the `Stop` input asks whether this turn touched source, which is the wrong question: a docs turn after a red commit touched none.
    - Dropping the skip is correct but costs about 26 times the runs (deep review §1.1), and on slow suites it turns this fail-open into #304's.
- **Affected files** (`.steering/structure.md`):
  - `hooks/quality-gate.sh`, which is shipped;
  - `scripts/test-gates.sh`;
  - the prose AC10 lists: `README.md`, `README.ja.md`, `skills/init/SKILL.md`, `.github/workflows/ci.yml`, `assets/check-unreviewed-work.sh`'s comment, `docs/layout.md`, `docs/DESIGN.md`;
  - the version bump in both manifests and both READMEs' `## Status`, as `implement`'s post-review step: minor, 0.32.0, because the gate's behaviour changes.
- **Blast radius:**
  - **Claude Code** projects get the change by plugin update. `hooks/plugin-gate.sh` `exec`s the gate unchanged.
  - **Antigravity** projects run copies and get it only by re-running `init`. Until then their gates keep today's skip.
  - **A stale project copy running beside the plugin's gate** keys on a different gate hash, so the two overwrite one record and both run every turn: a cost, not a fail-open.
  - **Every fresh clone and worktree** pays one full run at its first turn end (Q3).
  - **A worktree whose base is red** now blocks docs-only turns too, until the base is fixed. Claude Code's 8-block and Antigravity's 10-block `Stop` caps bound the loop.
  - **The existing `test-gates.sh` cases:**
    - `pg_repo`'s validator never passes, so the cases built on it never record and are unaffected.
    - `:1876`, `:1880`, and case 164's and case 202's docs halves are re-seeded (AC9).
    - Case 219 passes unchanged, through the environment key.
  - **Known limits, stated rather than fixed:**
    - Inputs outside the globs are not re-checked across turns on a state that passed: in this repository the validators that read `README*.md`, `.specs/`, `docs/` and `.steering/`.
    - Untracked files matching the globs are re-hashed every turn, measured at 0.83 s for 20,000 untracked 20 KB files. Files the real index holds as stat-dirty are re-hashed too, since the copy's refreshed stat data is discarded.
    - An `--assume-unchanged` edit is invisible.
    - The record is a cache an agent could forge, so CI is the backstop.
    - #304: a timed-out run never records (Q1).
    - Two things were not measured: sparse indexes, and LFS clean filters with `filter.*.required`. A missing filter should make `update-index` fail, which runs the validators.
- **Why this cannot recur:**
  - The new cases drive a commit through the gate, which no case did.
  - The decision is made by checked git calls, not a pipeline, and a case pins a failing git step.
  - Each case that pins behaviour `main` already has names the mutation that turns it red.

## 3. Tasks (TDD-ordered)
> One task is one complete Red-Green-Refactor cycle, so one green commit. No task is sequenced after the review.
- [x] T1: AC1, AC3 and AC4 cases after `scripts/test-gates.sh:2002`, on the `:1866` fixture with a validator that fails only on a marker in `src.txt` (red on `main`): a red change committed before the first run blocks; a pass, then a red commit, blocks; a red commit, then a docs-only turn, blocks; red committed on a feature branch blocks. Then the fingerprint and record in `hooks/quality-gate.sh`, AC2's cases (an idle turn and a docs-only turn after a pass are silent; committing content that already passed is silent), and the four silence cases re-seeded with a passing run first. Suite green.
- [ ] T2: AC5 cases — a `:(globs)` typo with an uncommitted red change, and an untracked red file under `status.showUntrackedFiles=no`, both red on `main`; an unreadable record and an unwritable `gate-sdd/` directory — each runs the validators, and the failed step is named on stderr. Then the stderr notes. Suite green.
- [ ] T3: AC6 and AC7 cases. AC6: a validator that edits source during its run, so the next turn runs (mutation: record the post-run fingerprint); and a same-size red edit at the index's own mtime under `core.trustctime=false`, which blocks (mutation: `cp` without `-p`). AC7: a `- Validators:` line edited, the globs line edited, the gate file changed in a copied `hooks/`, and `CLAUDE_PLUGIN_ROOT` changed — each with an unchanged tree, each runs (red on `main`). Case 219 is left unchanged and green. Suite green.
- [ ] T4: AC8 cases — no globs line runs every turn; outside a work tree runs; the real index's bytes and `git count-objects` are unchanged by a run; a linked worktree keeps its own record. Each names its mutation. Suite green.
- [ ] T5: AC10 — every "when the gate runs" statement reworded to the fingerprint rule, both READMEs saying the same thing (C-3); `docs/layout.md` and `docs/DESIGN.md` name `gate-sdd/quality-pass` as harness-written state; and the known limits above stated where a consumer reads them. AC11: every `- Validators:` command exits 0.
