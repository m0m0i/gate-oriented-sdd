# Spec: a gate that outlives its hook timeout ends the turn as a pass
- Slug: 304-a-gate-past-its-budget-blocks   Issue: 304   Type: bug   Status: draft
- Author: m0m0i   Date: 2026-10-16

## 1. Requirements (WHAT / WHY)
- Reproduction:
  - **Claude Code 2.1.300**, re-measured 2026-10-16 with a plugin `Stop` hook set to `"timeout": 2` (the issue measured settings hooks). At +2 s the hook gets SIGTERM, and about 1.5 s later SIGKILL. Both reach its whole process group, so a grandchild with its descriptors on `/dev/null` dies too. The debug log reads `timed out after 2000ms` and then `Hook Stop (Stop) cancelled`, and the result is `success` with `num_turns` 1. A block written from a `TERM` trap at that moment (stderr text, `{"decision":"block"}`, exit 2) is captured in the debug log and discarded, so the turn still passes. The hook's stdin has no timeout field.
  - **Antigravity CLI 1.3.3:** `docs/verified.md:472` (A5). The hook is SIGKILLed, its output is discarded, and the turn ends with `status: SUCCESS`.
  - **In the gates:** `hooks/quality-gate.sh:199-211` runs each validator as `out=$(eval "$cmd" 2>&1)` and decides only after the last one returns (`:226-229`). `hooks/review-gate.sh:299-311` scans every other branch and blocks only after the loop. Nothing in `hooks/` reads the clock.
  - **A stray signal does the same today, with no timeout involved.** Validators share the gate's process group, so a validator that ends with the common `trap 'kill 0' EXIT` idiom sends TERM to the gate. The gate's trap at `hooks/quality-gate.sh:146` runs `exit 143` and writes nothing on stdout. Exit 143 is a non-blocking error on Claude Code, and on Antigravity it means no decision was made. Measured under macOS `sh`, `dash` and bash (spec review, 2026-10-16).
- Expected: a gate that has not reached its verdict before the harness's timeout blocks, and says that it did not finish. Under `- Owns: gates never fail open` (`.steering/product.md`), a gate the harness treats as passing when it should have blocked is at least HIGH.
- Actual:
  - The turn passes silently. On Claude Code the timeout appears only in the debug log.
  - A partial verdict is lost as well. A validator that failed early, followed by one that ran past the budget, still ends the turn as a pass.
  - Since 0.32.0 a cut-off run records no pass (#297). So once a suite takes longer than the budget, every turn end in that worktree runs it, idle and docs-only turns included, and passes at the timeout.
  - **The budget cannot be raised on Claude Code.** Since #256 the `Stop` timeouts (180 s and 30 s) live only in the plugin's `.claude-plugin/hooks.json`, and no settings path changes a plugin hook's fields. A project that needs more time has to copy the gates back and stand the plugin down, which is the install ADR-8 removed. On Antigravity the rendered `.agents/hooks.json` can be edited, but nothing says to, and A5 shows that running out of time still passes.
- Impact:
  - **This repository:** the `- Validators:` line takes 68–71 s of its 180 s, measured 2026-10-15 and 10-16. `scripts/test-gates.sh` is 65–71 s of that, and grows with every case.
  - **Consumers:** a Flutter, JVM or monorepo suite over 180 s never gets a verdict.
  - **The review gate:** a replay of its git commands took 18 s on a synthetic repository with 20k commits and 100 branches (no commit-graph), and 42 s with 100k commits and 200 branches (with one). Its 30 s is overrun at a plausible scale.
  - **No backstop:** the deep review found no CI check wired in three of seven consumer projects (`docs/reviews/2026-10-11-deep-review.md` §3).
- **Root cause:** each gate hands its time bound to the harness, and neither harness turns a timed-out `Stop` hook into a block. On Claude Code, `"onFailure": "block"` has no effect on `Stop`, and a block written as the harness kills the hook is discarded. Antigravity's SIGKILL cannot be trapped at all. A gate therefore has a verdict only if it reaches one by its own deadline, ahead of the harness's, and neither gate has one. The same assumption covers every other way a gate's process ends early: the gate treats that end as something the harness will judge, and the harness has already judged it a pass. The quality gate's header (`:17-19`) treats a slow suite as a cost to keep down, not as a way the gate stops checking. #256 then moved the only budget a Claude Code project could edit into the plugin.
- Acceptance criteria:
  - [ ] **AC1:** WHEN the quality gate's validators have not all finished within its budget, THE SYSTEM SHALL block, on both channels (Claude Code: exit 2; Antigravity: exit 0 with `{"decision":"continue"}`), before the hook's timeout. The message names:
    - the budget in seconds, and what set it: the default, the `- Validator budget:` line, or the project's hook file (AC9);
    - the validator that was cut off, with its output tail;
    - each validator that did not run;
    - the remedy.
  - [ ] **AC2:** WHEN a validator failed before the budget ran out, THE SYSTEM SHALL carry that failure in the same block, with its output tail as today.
  - [ ] **AC3:** WHEN a run is cut off, THE SYSTEM SHALL leave no pass record, so the next turn end runs the validators again.
  - [ ] **AC4:** WHEN the budget runs out, THE SYSTEM SHALL leave no live descendant of the gate once it has decided, including one that ignores TERM. A validator that exits 124 or 143 by itself is a failure, not a cut-off. Two residuals are stated: a process that left the tree (double-forked, or `setsid`), and a host with no working `ps`, where only the gate's own child is killed and the block says so.
  - [ ] **AC5:** WHEN a gate's check ends without a verdict, THE SYSTEM SHALL block, naming what happened. That covers: the gate's temporary directory or watchdog cannot be created; the check is killed by a signal, a validator's `kill 0` included; the check exits with a status or stdout that is neither a pass nor a block; or the gate itself receives HUP, INT or TERM.
  - [ ] **AC6:** WHEN the review gate's whole check (the current branch, then every other branch) has not finished within its budget, THE SYSTEM SHALL block, naming what it was checking, the branches it did not check, and any unreviewed work it had already found.
  - [ ] **AC7:** a project sets the quality gate's budget with `- Validator budget: <seconds>` in its own `.steering/tech.md`, with no copied gate. With no line, the budget is 170 s. An integer from 1 to the maximum AC8 derives (590) takes effect. Any other value (empty, `0`, a leading zero, a sign, a unit, a fraction, or above the maximum) blocks when the validators are about to run, naming the line, the value and the accepted range. A turn the source skip passes is not blocked by it.
  - [ ] **AC8:** `hooks/gate-lib.sh` states each gate's ceiling once: 600 s for the quality gate and 120 s for the review gate. Each gate's largest budget is derived from its ceiling minus one 10 s margin: 590 and 110. `.claude-plugin/hooks.json`, `hooks/templates/antigravity.hooks.json` and this repository's `.claude/settings.json` carry exactly those ceilings. `scripts/check-manifests.py` fails if a file disagrees, if a file is missing, or if a constant cannot be found.
  - [ ] **AC9:** WHEN a gate runs from a copy inside the project (`.agents/hooks/`, `.claude/hooks/`, or this repository's `hooks/`), THE SYSTEM SHALL bound its deadline by the shortest `timeout` among the entries in the project's hook file that name it: budget = min(configured, timeout − 10). It SHALL block, naming the file and the field, when any of these happens:
    - that file cannot be read or parsed;
    - an entry that names the gate has no `timeout`;
    - the bound is not positive.

    A gate that no entry names, or that runs from the plugin, uses its ceiling.
  - [ ] **AC10:** `check-steering-anchors.sh` fails when any of these happens, each failure naming what it found:
    - the `- Validator budget:` line holds a value AC7 rejects;
    - an explicit line exceeds the bound AC9 would apply, which the gate would silently lower;
    - a project hook file AC9 reads cannot be read or parsed, or names a gate with no `timeout`;
    - the library it sources predates any function it calls.

    It uses the gates' own functions, so the two answers cannot drift apart.
  - [ ] **AC11:** unchanged:
    - every validator still runs after an earlier one fails, within the budget (case 17);
    - validators keep the hook's stdin, the gate's working directory and pathname expansion (case 203);
    - a failure's output tail reaches the block (case 16);
    - the bootstrap guard is byte-identical (case 159);
    - a full pass is recorded exactly as #297 records it, so the budget is not part of the fingerprint;
    - a matching fingerprint still skips the validators.
  - [ ] **AC12:** the tests: a `scripts/test-gates.sh` case for each of AC1–AC10, placed after the fixtures it uses.
    - The suite has no harness kill, so a gate with no deadline still finishes, just late. Every timing case therefore makes its slow step sleep at least 20 s and asserts both the deadline wording and an elapsed time of at most budget + 5 s, never the exit code alone.
    - Where an earlier step must finish before the deadline, the case uses a budget of at least 3.
    - Each case fails on `main` or under a named mutation, recorded in its comment.
  - [ ] **AC13:** every statement of the gates' budgets, of what a timeout or a signal does, of the machine-read lines, and of what the anchor check and the manifest check verify is true after the change. `docs/verified.md` records the Claude Code measurement beside A5. `docs/fidelity.md` says what is verified on each harness and what is not.
  - [ ] **AC14:** every command on the `- Validators:` line exits 0.
- Out of scope:
  - #320, filed at this spec's `clarify`: `init` times the validators and suggests a budget. This change adds the line to `init`'s template, and the block names it.
  - Making the review gate's scan cheaper: one batched history walk in place of the per-branch `rev-list` at `hooks/gate-lib.sh:349`. This is a performance change and is not needed to close the fail-open. It is recorded in backlog row 1's `Why here`.
  - Measuring on Antigravity whether a `Stop` timeout above 30 s is honoured, whether its SIGKILL reaches the process group, and whether its continuation cap resets. This needs a trusted-folder fixture. `docs/fidelity.md` marks each one unverified.
  - The official Antigravity hooks page now lists `SessionStart`, which contradicts `AGENTS.md` and `docs/fidelity.md:22`. It is recorded in the claim-drifts row's `Why here`.
  - #122, whitespace values in the anchor check. The new line's parser handles its own whitespace.

### Clarifications
Asked and answered 2026-10-16. Each answer took the recommended option.

- **Q1 — which gates the project's budget covers.** **A:** the quality gate only, through one line (AC7). The review gate gets a fixed budget, and its ceiling rises from 30 s to 120 s (AC8), so a large repository has headroom with nothing to configure. One line for both was rejected because the two gates' natural budgets differ about sixfold.
- **Q2 — the quality gate's ceiling.** **A:** 600 s (AC8). That is Claude Code's default for a command hook, and a plugin `Stop` hook was measured running 615 s under a larger timeout. 1800 s was rejected because it is unverified on both harnesses. 180 s was rejected because it leaves the issue's "cannot be raised" half open.
- **Q3 — installs where the timeout lives in the project's own hook file:** Antigravity's rendered `.agents/hooks.json`, a stand-down project's `.claude/settings.json`, and this repository's dogfood settings.
  - First answer: a shipped check fails.
  - **Asked again** after the spec review measured that a check on the `- Validators:` line runs inside the gate run it is meant to protect. When the hook file says 180 s and the budget says 300 s, the check fails, the harness kills the gate at 180 s, and the failure is thrown away with the rest of the run. The first framing had also overstated what a run-time read costs.
  - **A:** the gate bounds itself by the timeout it can see (AC9), and the anchor check reports in CI an explicit line that the file cannot honour (AC10). The parser is shared by both.
- **Q4 — `init` timing the validators (issue point 3).** **A:** filed separately as #320, and cited in backlog row 1.

**Revised 2026-10-16, before approval, from a four-lens spec review** (fail-open, portability, tests, conventions; 45 findings, each HIGH re-checked by a second agent). The first Design checked a wall-clock deadline between steps and ran each validator under its own watchdog. Ten confirmed HIGH findings replaced that design with the bounded child below:
- **A stray TERM ended the gate as a pass.** Folded into AC5.
- **The kill sequence let a descendant that ignores TERM survive.**
- **The output and marker files fell back to fixed names in the project's root** whenever `qg_tmp` was empty.
- **The review gate's unbounded steps** fell between its deadline checks.
- **The copied-hooks fail-open.** Q3 was asked again.
- **The tests:** a missing `ANCHORS` row reddened T1 through T4; none of the cases reached the review gate's real budget or the quality gate's no-line path; and the awk scoper failed on braces inside a JSON string.

Decided in Design rather than asked, because the repository answers them: the line's name and unit, the 10 s margin, the default, the treatment of an empty value, and how a copied path is recognised.

## 2. Design (HOW)
- **Fix approach: a bounded child.** Each gate's existing body runs as a child process of the gate, under one watchdog that is started before the child. The gate itself only does four things: it computes the budget, starts the watchdog, runs the child in the foreground, and judges what the child left. A verdict reaches the harness only in one of two ways:
  - the child printed a recognised pass or block, which the gate replays;
  - the gate builds a block itself, from the progress the child recorded.

  Any other ending is a block (AC5). This replaces the issue's candidate fix (a deadline checked between validators, plus a watchdog per validator) for four measured reasons:
  - **A wall-clock deadline moves when the clock is stepped.** An NTP step or a VM resume moves it, and a step backwards lets the gate outlive the harness. A `sleep` is a relative interval, and POSIX says setting the clock has no effect on it.
  - **Checks between steps leave the steps unbounded:** the fingerprint, `check_current_branch`, and any one branch's dozen git calls.
  - **A validator in a background job inherits SIGINT and SIGQUIT ignored**, and macOS `sh` and `dash` cannot restore them. The child runs in the foreground, so validators keep today's signal dispositions and the hook's stdin.
  - **Two gates and one mechanism.** The review gate gets the same bound with no second design.
- **Constants**, in `hooks/gate-lib.sh` next to `gate_block`. They are plain assignments, not environment reads, so an inherited variable cannot change them:
  - `_gate_margin=10`, `_gate_qg_ceiling=600`, `_gate_rg_ceiling=120` and `_gate_qg_default=170`.
  - `_gate_qg_max=$((_gate_qg_ceiling - _gate_margin))` and `_gate_rg_budget=$((_gate_rg_ceiling - _gate_margin))`. No other budget value is written as a literal anywhere in `hooks/`.
  - **The margin's invariant:** the block has to be written before the hook's timeout, and the harness's own TERM-to-KILL grace counts as zero, because a block written after TERM is discarded. What has to fit in the margin:
    - the time before the watchdog starts: `plugin-gate.sh`, the gate's setup, and AC9's parse, under 1 s;
    - the watchdog's kill phase: the walks, then a TERM grace of up to 2 s, cut short as soon as nothing is left alive;
    - the gate's block, under 1 s.

    That is about 4 s, leaving about 6 s of slack.
- **Library functions** (`hooks/gate-lib.sh`):
  - **`gate_validator_budget <tech.md>`** reads the line through `gate_steering_read` with the literal key `'Validator budget'`, the form test-gates case 30 extracts.
    - Absent (rc 0 with no line, or rc 1 for no `tech.md`) prints 170. An unreadable file is rc 2, and the gate has already blocked on it at `:89`.
    - Otherwise it strips one trailing `\r`, and spaces and tabs at both ends. It accepts only `[1-9]`, `[1-9][0-9]` or `[1-9][0-9][0-9]` by `case`, then `-le` the maximum. Anything else, the empty value included, prints a sentence naming the value and the range, and returns 2.
    - No arithmetic touches a value before the `case` check: in macOS `sh`, `abc` evaluates to 0, a variable name to that variable, `010` to octal, and `a[$(cmd)]` runs the command.
  - **`gate_hook_timeout <gate script> <hooks dir> <ceiling>`** prints `<seconds> <source>`.
    - **A copied path** is a hooks directory inside the repository root, compared with `pwd -P` on both sides, because macOS resolves `/tmp` as `/private/tmp`. Under `.agents/hooks` the gate reads `.agents/hooks.json`. Under any other directory inside the root it reads `.claude/settings.json` and `.claude/settings.local.json`, each one that exists.
    - It scans those files with a **string-aware POSIX `awk` tokenizer**. The tokenizer reads character by character with `substr`, honours `\"` and other escapes, ignores braces inside strings, and does not depend on line breaks or on the order of keys. It uses no gawk features, so it runs under mawk, BWK awk and busybox. For every object whose `"command"` string contains the gate script's name, it reads that object's `"timeout"` integer.
    - **The output:** the shortest timeout, with the file as its source. When nothing names the gate, or the path is not a copied path (the plugin, or a by-hand run from a checkout outside the project), it prints the ceiling, with `plugin` as the source.
    - **Return 2, with a sentence naming the file and the field**, when a file exists and cannot be read, a file does not parse, or a matching object has no integer `timeout`. A missing `timeout` is never given a default, because the harnesses' defaults (600 s on Claude Code, 30 s on Antigravity) are not something this project measured.
    - **Every entry that names the gate counts, live or dead.** A dead entry left after a migration can only lower the bound. That is a stated residual, and it never causes a pass.
  - **`gate_bounded <budget> <run dir> <command...>`** runs the command in the foreground, with stdout and stderr in `<run dir>/out` and `<run dir>/err`. The watchdog is a background subshell with its descriptors on `/dev/null`:
    1. It ignores TERM, INT and HUP before it forks anything, so a validator's `kill 0` cannot disarm it, and its `sleep "$budget"` inherits the same dispositions.
    2. It traps USR1, killing its `sleep` with KILL and exiting. USR1 is the gate's "finished in time" signal.
    3. When the sleep ends, it ignores USR1 too, and writes `<run dir>/fired`.
    4. **The kill.** It walks the gate's descendants with `ps -A -o pid= -o ppid=` and `awk`, leaving out its own subtree. It learns its own pid with `sh -c 'echo $PPID'`. It STOPs them, and repeats walk-and-STOP until the set stops growing, at most five times. It sends TERM to the accumulated set, then CONT, then polls `kill -0` for up to 2 s. Finally it sends KILL to the **saved set**, never a fresh walk, because a descendant reparented to pid 1 can no longer be found from the gate.
    5. **When `ps` fails**, it KILLs the pid the child wrote to `<run dir>/pid` at its start, and writes `<run dir>/nowalk`.

    The gate then:
    1. When `fired` exists, waits for the watchdog with `{ wait "$wd"; } 2>/dev/null`. Otherwise it sends USR1 and reaps the watchdog the same way. A watchdog that cannot be started blocks (AC5).
    2. Reports the child's status.
  - **`gate_replay <run dir>`** judges what the child left:
    - `out` exactly `{}` with status 0 is a pass: it replays `err` to stderr and calls `gate_pass`.
    - `out` one line beginning `{"decision":"continue","reason":"` and ending `"}` is a block. It replays both files and exits through the same harness test `gate_block` uses, which moves into a shared `_gate_block_exit`.
    - Anything else returns 1. A recognised verdict wins even when `fired` exists, because the child reached it within the budget plus a moment. A partial line written by a killed child is never recognised.
  - **Every new function goes on its gate's predates check**, and on the anchor check's (`assets/check-steering-anchors.sh:89`), because a library cut off after `gate_block` passes the bootstrap guard (#198).
- **Both gates take the same shape.** The bootstrap guard and the predates checks run as today. Then `if [ "${1-}" = --bounded ]; then shift; <the existing body, plus progress lines>; fi`, and the parent path follows:
  1. `run=$(mktemp -d "${TMPDIR:-/tmp}/gate-sdd-run.XXXXXX") || gate_block`.
  2. The EXIT trap removes `run`'s known files and then the directory, whatever else holds. This replaces `quality-gate.sh:145`'s guarded trap, which skipped removal whenever `qg_tmp` was empty and left `.out` in the project's root.
  3. The HUP, INT and TERM traps write `run/signalled`, kill the child's tree the way the watchdog does, and call `gate_block`, never `exit 1xx` (AC5). On the harness's own TERM that block is discarded, which costs nothing. On a stray TERM it is the correct outcome.
  4. The budget is computed, then `gate_bounded "$budget" "$run" sh "$DIR/<gate>.sh" --bounded "$run" …`.
  5. Then `gate_replay`. Failing that, when `fired` exists, the timeout block. Failing that, the no-verdict block, with `err`'s tail.

  - **The harness never passes an argument:** `plugin-gate.sh:199` runs `exec sh "$DIR/$gate"`, and the Antigravity template runs `sh {{HOOKS_DIR}}/<gate>.sh`. A hook entry that wrote `--bounded` by hand would run the body unbounded, which is today's behaviour, not a pass. That is a stated residual.
  - **The child's own HUP/INT/TERM traps** may still `exit 1xx`, because its parent judges that ending (AC5).
- **Quality gate** (`hooks/quality-gate.sh`):
  - **Parent:**
    - The budget is `gate_validator_budget`'s value, or 170 when the line is malformed. In that case the sentence goes to the child as `--budget-error <file>`, so the line blocks only when the validators are about to run (AC7).
    - That value is then bounded by `gate_hook_timeout quality-gate.sh "$DIR" "$_gate_qg_ceiling"` minus the margin. Return 2, or a bound that is not positive, blocks at once (AC9).
    - The source of the budget (default, line, or file) goes into the timeout block.
  - **Child:** today's body, with two changes.
    - After the skip, a `--budget-error` blocks before the record is removed.
    - The loop appends `start <cmd>`, then `ok <cmd>` or `fail <cmd>`, to `run/progress`, and writes each failure's tail to `run/fail.<n>`.
  - **The timeout block** (AC1, AC2) is built by the parent from three sources:
    - `progress`: the last `start` with no matching end is the cut-off command, and its tail is read from `out`;
    - the `- Validators:` line, split by the same function the child uses, for the commands that never started;
    - the `fail.<n>` files.

    The remedy names the line and its maximum. When the hook file set the bound, it also names that file's `timeout`.
  - **The record:** on any ending that is not a replayed verdict, the parent removes the pass record (`git rev-parse --git-path gate-sdd/quality-pass`) before it blocks (AC3). That covers a child cut off just after writing it. A removal that fails is named in the block.
  - **The header** (`:17-19`) and the comment at `:187-190` say that the deadline is part of the guarantee.
- **Review gate** (`hooks/review-gate.sh`):
  - **Parent:** the budget is `_gate_rg_budget`, bounded by `gate_hook_timeout review-gate.sh "$DIR" "$_gate_rg_ceiling"` minus the margin. No environment variable can change it. The tests set it through a copied-path fixture's own hook file.
  - **Child:** today's body. It writes:
    - `phase current` before `check_current_branch` and `phase scan` before `scan_other_branches`;
    - the listed refs to `run/refs`;
    - `checked <slug>` and `found <slug> — <sentence>` as the scan goes.
  - **The timeout block** (AC6) names one of two states:
    - "still checking the current branch";
    - for the scan: the branches found so far with their sentences, and the branches not checked (`refs` minus `checked`).

    The remedy is fewer live branches: merge, review or delete them.
- **Ceilings** (AC8):
  - The six `Stop` timeouts become 600 and 120: `.claude-plugin/hooks.json:6,11`, `hooks/templates/antigravity.hooks.json:27,32` and `.claude/settings.json:14,19`.
  - `scripts/check-manifests.py` reads `_gate_qg_ceiling` and `_gate_rg_ceiling` from `hooks/gate-lib.sh` with anchored regexes, and fails when either is missing. It reads each file's `Stop` timeouts, keyed by gate script name, in both shapes, the way `scripts_in` pairs the gates (`:288-296`), and fails on any difference.
  - `manifest_repo` (`scripts/test-gates.sh:7213`) gains `.claude/settings.json`. A missing file fails, because this is a check on this repository.
  - The anchor check also reads `.claude/settings.json` in this repository, but with AC9's rule (budget against timeout). Two checks over one file, for two different questions.
- **Anchor check** (AC10, `assets/check-steering-anchors.sh`):
  - `ANCHORS` gains `.steering/tech.md|Validator budget`, in T1 beside the function, so case 30 stays green.
  - Its existing loop already fails a loosely matched key with an empty value, which agrees with AC7's empty-is-malformed.
  - It then calls `gate_validator_budget`, and `gate_hook_timeout` for both gates with the directory of the library it sourced, which is the gates' `$DIR`. It fails on return 2. It fails when an explicit line exceeds the file's bound minus the margin.
  - **The header's "does NOT judge whether a value is any good"** becomes: it judges whether the value can be honoured by the hook that reads it. That is the question it already asks, whether the reader can see the line, taken one step further. `hooks/gate-lib.sh:359-360`, which quotes the header, follows it.
- **Steering line wiring** (AC13):
  - `init`'s tech.md template (`skills/init/SKILL.md:49-56`) describes `- Validator budget: <seconds>` as optional, to be omitted unless the suite needs more than 170 s, with the `- Target:` bullet's "omit if no view" wording. A `check-skill-contracts.py` pin pins that sentence.
  - `init`'s Antigravity bullet (`:71`) says the rendered timeouts are the hook's ceiling, and the budget lives in steering.
  - `init`'s anchor-check bullet (`:63`) says what the check now verifies.
  - `CONTRIBUTING.md:43` lists the line. `docs/DESIGN.md:17` and `:30` count it ("seven" becomes "eight"), and the Seams table gains a row: budget against timeout, guarded by `check-manifests.py` and the anchor check.
  - The key lists at `assets/check-document-set.py:189-190` and `scripts/test-gates.sh:5082` stay as they are. They list the keys `gate_steering_value` reads, and this line has its own parser.
  - This repository writes no line: 70 s against 170 s needs none, and the absent path is the one most projects take. T3 records the suite's measured time. If it is over 120 s, the line is written and the reason given.
- **Docs** (AC13):
  - `README.md:43` and `README.ja.md:45` (identical claims; the user reviews the Japanese), and `:226`/`:233`, the copied checks a plugin update does not reach.
  - `AGENTS.md:51` and `CONTRIBUTING.md:59`, which say what the anchor check verifies, and `docs/CONTRACT.md` M-2 (manifests agree, timeouts now included) and M-7.
  - `hooks/templates/README.md:17`.
  - `docs/verified.md`: a Claude Code row beside A5, from the four 2026-10-16 probes.
  - **`docs/fidelity.md`, verified on Claude Code:**
    - TERM and then KILL reach the hook's group;
    - a block written after TERM is discarded;
    - a hook ran past 600 s under a larger timeout.
  - **`docs/fidelity.md`, on Antigravity:** only a kill at a 1 s timeout is verified. Whether 120 s, 180 s or 600 s timeouts are honoured is not exercised.
  - **`docs/fidelity.md`, on both:** a suite always over its budget blocks every turn until the line is raised. Claude Code stops honouring that block after 8 continuations in a row with no tool call (`CLAUDE_CODE_STOP_HOOK_BLOCK_CAP`), and Antigravity after 10.
- **Release notes** (quoted by the PR body):
  - **Claude Code:** the new ceilings arrive by plugin update.
  - **Every project:** re-copy `check-steering-anchors.sh` for AC10.
  - **Antigravity:** re-run `init`, which re-renders `.agents/hooks.json` at 600/120 and re-copies the gates. A project that re-copies only `hooks/` keeps 180/30. Its gates then bound themselves to 170 s and 20 s (AC9), which blocks, never passes.
  - **Stand-down projects:** the same bound applies through their `.claude/settings.json`.
  - **Every pass record is invalidated once**, because `gate-lib.sh` is in the fingerprint.
- **Bump:** minor, 0.33.0, as a step of `implement` after the review. The change alters when both gates block and adds a machine-read line.
- Affected files: `hooks/gate-lib.sh`, `hooks/quality-gate.sh`, `hooks/review-gate.sh`, `.claude-plugin/hooks.json`, `hooks/templates/antigravity.hooks.json`, `hooks/templates/README.md`, `.claude/settings.json`, `assets/check-steering-anchors.sh`, `scripts/check-manifests.py`, `scripts/check-skill-contracts.py`, `scripts/test-gates.sh`, `skills/init/SKILL.md`, `README.md`, `README.ja.md`, `AGENTS.md`, `CONTRIBUTING.md`, `docs/CONTRACT.md`, `docs/DESIGN.md`, `docs/fidelity.md`, `docs/verified.md`, `docs/BACKLOG.md` (#304 to row 1's `Why here`, the two out-of-scope findings), and both manifests for the bump.
- **Blast radius:**
  - **A validator's leftover background child no longer holds the gate open.** It wrote into `$(...)` before, and now writes into `run/out`. The gate does not wait for it, and nothing kills it when the validator exits in time, which is the same as on Claude Code once a hook exits.
  - **One extra `sh` per gate per turn end**, plus the watchdog. The time stays well inside the margin.
  - **A slow review gate can hold a turn end for up to 110 s** where the harness killed it at 30 s. That time is spent reaching a verdict.
  - **Turn-end stdout and stderr are replayed after the child exits** instead of streamed. Neither harness shows a `Stop` hook's output before it exits.
- **Why this cannot recur:**
  - A verdict reaches the harness only as a replay the gate recognised, or as a block the gate wrote. The child's exit, a killed child, a stray signal and the deadline all end in one of those two.
  - The deadline is a `sleep`, not a clock, and it is checked against every timeout the gate can see: `check-manifests.py` for the plugin's files, AC9 at run time and the anchor check in CI for the project's own.
  - A temporary directory, watchdog or library function that is missing blocks.
  - AC12's cases assert elapsed time, so removing the deadline goes red even though the suite never reproduces the harness's kill.

## 3. Tasks (TDD-ordered)
> One task is one complete Red-Green-Refactor cycle, so one green commit. No task is sequenced after the review.
- [ ] T1: budget and hook-timeout readers. Cases in the shared-library section after `:2312`:
  - `gate_validator_budget` for absent, `1`, `590`, `591`, `0`, `010`, `-5`, `abc`, `12s`, `300\r`, tab-only and empty (AC7);
  - `gate_hook_timeout` for a non-copied path (ceiling, source `plugin`), `.agents/hooks.json` at 180/30, both `.claude/` files with the lower one winning, every spelling in case 221's `pd_spellings`, minified JSON, `timeout` before `command`, a `{` or `}` inside a command string, `\"` escapes, a missing `timeout`, an unparseable file, an unreadable file (under `note_skip`'s root guard), and a fast check holding `{}` ahead of the `Stop` entries (AC9);
  - the derived constants (AC8's library half).

  Red: the functions do not exist. Green: the constants, both functions, and the `ANCHORS` row. Case 30 stays green.
- [ ] T2: `gate_bounded` and `gate_replay`, driven by a small script under `$TMP` that sources the library. Cases:
  - a 20 s command at budget 2: `fired` is written and the elapsed time is ≤ 7;
  - a fast command: status passed through, no `fired`;
  - a command that exits 143 by itself: no `fired`;
  - a grandchild that ignores TERM, dead once the function returns;
  - a `kill 0` from inside the command leaves the watchdog armed;
  - a `PATH` without `ps`: the child is killed and `nowalk` is written;
  - `gate_replay` for `{}`, a block line, a torn line, empty output, and status 1 with `{}`.

  Each case names its mutation: kill the root only; decide by status; skip the KILL step; let TERM disarm the watchdog. Red: the functions do not exist. Green: both functions and `_gate_block_exit`.
- [ ] T3: quality gate, cases 259 and up after `:2310` (`qgp_repo`, `qgp_runs`, the second `run_qg`):
  - a 20 s validator after a fast one at budget 3;
  - a 20 s validator after a failing one at budget 3;
  - one validator alone at budget 2, on the Claude Code channel and on the Antigravity channel (parsed JSON);
  - the not-run list;
  - no pass record afterwards, and the next run runs;
  - a copied gate under `.agents/hooks/` with no budget line and `"timeout": 13`, which blocks at 3 s and names the file (the no-line path);
  - a malformed line that blocks only when the validators run;
  - a validator running `kill 0` blocks;
  - a validator's leftover background child does not hold the gate;
  - no file left in the work tree, with no `- Source globs:` line.

  Cases 16, 17, 159, 203 and 239–258 stay green. Then the parent and child split. Record the suite's measured time in the spec.
- [ ] T4: review gate:
  - a copied-gate fixture whose own hook file has review `"timeout": 13`;
  - a `git` shim on `PATH` that sleeps 20 s in `rev-parse --verify` for one branch, and one that sleeps in the current branch's `merge-base`;
  - each blocks within budget + 5 and names what it was checking, the branches not checked and the ones found;
  - the unbounded default prints 110 through the derivation case in T1.

  Then the review gate's parent and child split.
- [ ] T5: manifest and anchor checks:
  - check-manifests' section, after `:7236`: a mismatched timeout in each of the three files, a missing `.claude/settings.json`, and a missing constant each fail (AC8);
  - the anchor section, after `anchor_repo` at `:3111`: a malformed line fails; an explicit line above an `.agents/hooks.json` bound fails; an unparseable hook file fails; a library without the new functions fails with the "predates" diagnosis; a stand-down `.claude/settings.json` at 600/120 with a line of 300 passes; no hook file passes (AC10).

  Then the six timeouts, `check-manifests.py`'s reader and comparison, and the anchor check's additions with its header.
- [ ] T6: the `check-skill-contracts.py` pin for the template sentence, red until `skills/init/SKILL.md` carries it. Then the `init` bullets, every statement listed under Docs and Steering line wiring, and `docs/BACKLOG.md`: #304 moves from row 1's `Item` cell to its `Why here` beside #320 and the scan-cost finding, and the `SessionStart` contradiction goes to the claim-drifts row.
