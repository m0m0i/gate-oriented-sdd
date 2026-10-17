# Spec: a gate that outlives its hook timeout ends the turn as a pass
- Slug: 304-a-gate-past-its-budget-blocks   Issue: 304   Type: bug   Status: approved
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
  - [ ] **AC4:** WHEN the budget runs out, THE SYSTEM SHALL leave no live descendant of the gate once it has decided, including one that ignores TERM and one that forks a replacement while it is being killed. A validator that exits 124 or 143 by itself is a failure, not a cut-off. The residuals are stated, in the block where they apply and in `docs/fidelity.md`:
    - a process that left the tree (double-forked, or `setsid`);
    - a host where the process walk fails or does not find the gate's child, where only that child is killed and the block says so;
    - a process the kernel cannot kill yet (uninterruptible sleep on a hung mount), or a `ps` that hangs rather than failing.
  - [ ] **AC5:** WHEN a gate's check ends without a verdict, THE SYSTEM SHALL block, naming what happened. That covers:
    - the gate's temporary directory cannot be created, or its watchdog does not confirm it is armed;
    - the check is killed by a signal, a validator's `kill 0` included;
    - the check exits with a status or stdout that is neither a pass nor a block;
    - the gate itself receives HUP, INT, QUIT, TERM, USR1, USR2 or ALRM, from anyone, a validator's group-wide send included.

    No signal a validator can send to its process group disarms the deadline. On every ending, no watchdog outlives the gate. KILL and STOP cannot be caught: a group-wide KILL from a validator ends the gate with nothing written, and that is a stated residual.
  - [ ] **AC6:** WHEN the review gate's whole check (the current branch, then every other branch) has not finished within its budget, THE SYSTEM SHALL block, naming what it was checking, the branches it did not check, and any unreviewed work it had already found.
  - [ ] **AC7:** a project sets the quality gate's budget with `- Validator budget: <seconds>` in its own `.steering/tech.md`, with no copied gate. With no line, the budget is 170 s. An integer from 1 to the maximum AC8 derives (590) takes effect. Any other value (empty, `0`, a leading zero, a sign, a unit, a fraction, or above the maximum) blocks when the validators are about to run, naming the line, the value and the accepted range. A turn the source skip passes is not blocked by it.
  - [ ] **AC8:** `hooks/gate-lib.sh` states each gate's ceiling once: 600 s for the quality gate and 120 s for the review gate. Each gate's largest budget is derived from its ceiling minus one 10 s margin: 590 and 110. `.claude-plugin/hooks.json`, `hooks/templates/antigravity.hooks.json` and this repository's `.claude/settings.json` carry exactly those ceilings. `scripts/check-manifests.py` fails if a file disagrees, if a file is missing or holds no object, or if a constant cannot be found. This repository's `.claude/settings.json` is required only in a tree with `.specs/`, the rule the directory-contract dogfood already uses, because the release workflow runs the check on the unzipped payload, which ships no `.claude/`.
  - [ ] **AC9:** THE SYSTEM SHALL bound each gate's deadline by the shortest `timeout` among the project hook entries that name it: budget = min(configured, timeout − 10). The files read are every one that could have run it, wherever the gate itself sits:
    - the settings this Claude Code launch read: `$CLAUDE_PROJECT_DIR/.claude/settings.json`, `$CLAUDE_PROJECT_DIR/.claude/settings.local.json`, and the `settings.local.json` at that directory's git root (`docs/verified.md` L2);
    - the git root's `.claude/settings.json` and `.claude/settings.local.json`, and its `.agents/hooks.json`;
    - when the gate sits in `<X>/.agents/hooks/` or `<X>/.claude/hooks/`, `<X>`'s own `.agents/hooks.json` or `.claude/settings.json` and `.claude/settings.local.json`.

    With no git root, the working directory stands in for it. An entry names a gate when its `"command"` string holds the gate's file name as a whole path component, so `code-review-gate.sh` does not name `review-gate.sh`. A file that is not there is skipped. An extra file can only lower the bound, never raise it. A gate that no entry names uses its ceiling. That covers the plugin, and also a copy run through a wrapper script, which is a stated residual. The gate SHALL block, naming the file and the field, when any of these happens:
    - a file exists and cannot be read or parsed;
    - an entry that names the gate has no integer `timeout`;
    - the bound is not positive.
  - [ ] **AC10:** `check-steering-anchors.sh` fails when any of these happens, each failure naming what it found:
    - the `- Validator budget:` line holds a value AC7 rejects;
    - an explicit line exceeds the bound AC9 would apply, which the gate would silently lower;
    - a project hook file AC9 reads cannot be read or parsed, or names a gate with no `timeout`;
    - the library it sources predates any function it calls.

    It uses the gates' own functions, so the two answers cannot drift apart. It has no `CLAUDE_PROJECT_DIR`, and it finds its library through `GATE_SDD_HOOKS` in CI, so it does not take the file set from either. It reads every tracked `.claude/settings.json`, `.claude/settings.local.json` and `.agents/hooks.json` in the tree, plus the git root's three, tracked or not: a project that gitignores `.claude/` or `.agents/`, or one not yet committed after `init`, still has the files the gate reads. That covers every launch from the root and every tracked file below it, so it can only report more. An untracked hook file below the root, read only by a launch from that directory, is a stated residual.
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
    - **A case whose command signals its process group runs the code under test as the leader of a new session**, through one helper defined before those cases. `kill 0` otherwise reaches `test-gates.sh` itself and, in this repository, the quality gate that is running it. macOS has no `setsid(1)` and dash refuses `set -m` without a tty, so the helper is a `python3` fork-then-`os.setsid()`-then-exec, which the suite already depends on. The validator stays in the gate's new group, so the case still tests the group-wide send. Each such case is followed by a canary line, so an escaped signal shows as a named failure and not as a suite that stopped early.
    - **The timing cases run concurrently.** Each one runs in the background and writes its result to its own file, and the suite waits for all of them, so the cases add roughly the time of the slowest one, not their sum.
    - Each case fails on `main` or under a named mutation, recorded in its comment.
  - [ ] **AC13:** every statement of the gates' budgets, of what a timeout or a signal does, of the machine-read lines, and of what the anchor check and the manifest check verify is true after the change. `docs/verified.md` records the Claude Code measurement beside A5. `docs/fidelity.md` says what is verified on each harness and what is not.
  - [ ] **AC14:** every command on the `- Validators:` line exits 0.
- Out of scope:
  - #320, filed at this spec's `clarify`: `init` times the validators and suggests a budget. This change adds the line to `init`'s template, and the block names it.
  - Making the review gate's scan cheaper: one batched history walk in place of the per-branch `rev-list` at `hooks/gate-lib.sh:349`. This is a performance change and is not needed to close the fail-open. It is recorded in backlog row 1's `Why here`.
  - Measuring on Antigravity whether a `Stop` timeout above 30 s is honoured, whether its SIGKILL reaches the process group, and whether its continuation cap resets. This needs a trusted-folder fixture. `docs/fidelity.md` marks each one unverified.
  - The official Antigravity hooks page now lists `SessionStart`, which contradicts `AGENTS.md` and `docs/fidelity.md:22`. It is recorded in the claim-drifts row's `Why here`.
  - #122, whitespace values in the anchor check. The new line's parser handles its own whitespace.
  - #302, `_gate_json_escape` passing raw control bytes through, which Antigravity's parser rejects, and a rejected `Stop` output is a pass there (`docs/fidelity.md:28`). AC1's cut-off tail makes such bytes more likely, because a runner killed mid-output leaves colour codes and progress bars. #302 is in row 1 and owns the escaping. This change only cites it from the block's tail in `fidelity.md`.

### Clarifications
Asked and answered 2026-10-16. Each answer took the recommended option.

- **Q1 — which gates the project's budget covers.** **A:** the quality gate only, through one line (AC7). The review gate gets a fixed budget, and its ceiling rises from 30 s to 120 s (AC8), so a large repository has headroom with nothing to configure. One line for both was rejected because the two gates' natural budgets differ about sixfold.
- **Q2 — the quality gate's ceiling.** **A:** 600 s (AC8). That is Claude Code's default for a command hook, and a plugin `Stop` hook was measured running 615 s under a larger timeout. 1800 s was rejected because it is unverified on both harnesses. 180 s was rejected because it leaves the issue's "cannot be raised" half open.
- **Q3 — installs where the timeout lives in the project's own hook file:** Antigravity's rendered `.agents/hooks.json`, a stand-down project's `.claude/settings.json`, and this repository's dogfood settings.
  - First answer: a shipped check fails.
  - **Asked again** after the spec review measured that a check on the `- Validators:` line runs inside the gate run it is meant to protect. When the hook file says 180 s and the budget says 300 s, the check fails, the harness kills the gate at 180 s, and the failure is thrown away with the rest of the run. The first framing had also overstated what a run-time read costs.
  - **A:** the gate bounds itself by the timeout it can see (AC9), and the anchor check reports in CI an explicit line that the file cannot honour (AC10). The parser is shared by both.
- **Q4 — `init` timing the validators (issue point 3).** **A:** filed separately as #320. T6 cites it in backlog row 1's `Why here`. Until then, `check-backlog-tracker.py` is red on this branch.

**Revised 2026-10-16, before approval, from a four-lens spec review** (fail-open, portability, tests, conventions; 45 findings, each HIGH re-checked by a second agent). The first Design checked a wall-clock deadline between steps and ran each validator under its own watchdog. Ten confirmed HIGH findings replaced that design with the bounded child below:
- **A stray TERM ended the gate as a pass.** Folded into AC5.
- **The kill sequence let a descendant that ignores TERM survive.**
- **The output and marker files fell back to fixed names in the project's root** whenever `qg_tmp` was empty.
- **The review gate's unbounded steps** fell between its deadline checks.
- **The copied-hooks fail-open.** Q3 was asked again.
- **The tests:** a missing `ANCHORS` row reddened T1 through T4; none of the cases reached the review gate's real budget or the quality gate's no-line path; and the awk scoper failed on braces inside a JSON string.

**Revised again 2026-10-16, before approval, from a second review of the bounded child.** It used four lenses (fail-open, portability, timing, consistency) and raised 45 findings. Each HIGH was re-checked by two agents, one with a probe and one against the text. Three HIGH held:
- **The child's stdout was both the verdict channel and the validators' output.** Every chatty passing run would have blocked, or the cut-off tail could not exist and a validator's leftover background child still held the gate. Each validator now writes to its own file.
- **The `kill 0` cases would have killed `test-gates.sh`** and this repository's own gate. AC12 now requires a new session for them.
- **AC9 read the git root's settings for a copy launched below the root,** which L2 measured is not the file set that launch reads. AC9 now reads every file that could have run the gate.

Fail-open MEDIUM findings were folded in as well:
- a group-wide USR1 disarmed the watchdog and killed the parent unhandled;
- the signal path left the watchdog armed after the gate exited;
- a `ps` that succeeds but misses the child killed nothing;
- a TERM-catching loop forked a survivor during the grace period;
- the watchdog's self-pid was fragile;
- the parse ahead of the watchdog was quadratic;
- an empty line read as an absent one.

Decided in Design rather than asked, because the repository answers them: the line's name and unit, the 10 s margin, the default, the treatment of an empty value, and which hook files bound a gate.

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
    - the time before the watchdog starts: `plugin-gate.sh`, the gate's setup, and AC9's parse, under 1 s. The parse is linear in the files' size, which a 1 MB minified fixture pins (T1). A tokenizer that indexes one long string with `substr` is quadratic in BWK awk: it measured 8.5 s at 749 KB, and a stand-down `settings.local.json` grows with every "don't ask again";
    - the watchdog's kill phase: the walks, then a TERM grace of up to 2 s, cut short as soon as nothing is left alive, then the re-walk before KILL;
    - the gate's block, under 1 s.

    That is about 4 s, leaving about 6 s of slack. `ps` measured 10 ms for about 900 processes.
- **Library functions** (`hooks/gate-lib.sh`):
  - **`gate_validator_budget <tech.md>`** reads the line through `gate_steering_read` with the literal key `'Validator budget'`, the form test-gates case 30 extracts.
    - `gate_steering_read` returns the same empty string for an absent line and an empty one (`hooks/gate-lib.sh:72`). So presence is tested on its own, with `grep -q '^ *- *Validator budget:'`, the same expression `gate_steering_read` uses. Absent (no such line, or rc 1 for no `tech.md`) prints 170 and returns 1, so the timeout block and the anchor check can tell the default from a written line. A valid line returns 0. A line that is present and empty is malformed.
    - An unreadable `tech.md` returns 3, not 2, so a caller can tell it from a malformed line. The parent then hands nothing to the child, and the child blocks on the unreadable file at `quality-gate.sh:89` as today.
    - Otherwise it strips one trailing `\r`, and spaces and tabs at both ends. It accepts only `[1-9]`, `[1-9][0-9]` or `[1-9][0-9][0-9]` by `case`, then `-le` the maximum. Anything else, the empty value included, prints a sentence naming the value and the range, and returns 2.
    - No arithmetic touches a value before the `case` check: in macOS `sh`, `abc` evaluates to 0, a variable name to that variable, `010` to octal, and `a[$(cmd)]` runs the command.
  - **`gate_hook_files <hooks dir>`** prints AC9's file set, one path per line, each one that exists. The parent calls it before its `cd` to the git root, because `CLAUDE_PROJECT_DIR` and the working directory are the launch's. The Claude Code half is the rule `plugin-gate.sh:133-143` already applies to stand down. `plugin-gate.sh` keeps its own copy, because it runs before any library is chosen. A T1 case pins that both give the same set for each L2 layout: launched at the root, launched below it, and with no `CLAUDE_PROJECT_DIR`. The `<X>` half compares `pwd -P` of the hooks dir, because macOS resolves `/tmp` as `/private/tmp`.
  - **`gate_hook_timeout <gate script> <ceiling> <file>...`** prints `<seconds> <source>`.
    - It scans the files with a **string-aware POSIX `awk` tokenizer**. Input goes through `fold -b -w 512` first, and the tokenizer carries its state (inside a string, an escape pending, the depth, the current object's keys) from one record to the next. So the scan is linear, and a minified file is no slower than a pretty-printed one.
    - The tokenizer honours `\"` and other escapes, ignores braces inside strings, skips `//` and `/* */` comments outside strings, and does not depend on line breaks or on the order of keys. It uses only POSIX awk. It is tested under the macOS awk and CI's awk. busybox awk is unverified, and `docs/fidelity.md` says so.
    - For every object whose `"command"` string names the gate (AC9's path-component rule), it reads every `"timeout"` key in that object, a duplicate included, and keeps the smallest.
    - **The output:** the shortest timeout, with its file as the source. When nothing names the gate, it prints the ceiling, with `ceiling` as the source.
    - **Return 2, with a sentence naming the file and the field**, when a file exists and cannot be read, a file does not parse, a matching object has no integer `timeout`, or the shortest timeout leaves nothing after the margin. A missing `timeout` is never given a default, because the harnesses' defaults (600 s on Claude Code, 30 s on Antigravity) are not something this project measured.
    - **Every entry that names the gate counts, live or dead,** and so does an entry in a file this launch did not read. Either can only lower the bound. That is a stated residual, and it never causes a pass.
  - **`gate_bounded <budget> <run dir> <command...>`** starts the watchdog, then runs the command in the foreground. **A run dir that is not an absolute path blocks** before anything starts: the child `cd`s to the git root before it writes `end`, and the parent and the watchdog never do, so a relative one would put `end` where the parent never looks.
    - **The child.** It is launched as `sh -c 'echo $PPID >"$1/ppid" && echo $$ >"$1/pid" || exit 125; shift; exec "$@"' _ "$run" "$@"`. So its pid is on disk before any gate code runs, and the pid is the child's own, because `exec` keeps it. **A child that cannot write both files never runs:** it exits 125, leaves no `end`, and the gate blocks; with `;` in place of `||`, a failed write ran the command with nothing the watchdog could kill. `ppid` is the shell that forked it, which is what the watchdog compares, so `gate_bounded` works from a subshell too, where `$$` names the gate and not the child's parent.
    - **Its output.** The child's stdout goes to `<run dir>/verdict` and its stderr to `<run dir>/err`. The call sits inside `{ …; } 2>/dev/null`, and its status is captured inside the braces. Without that, bash-as-sh prints `Terminated: 15` for a killed child onto the gate's own stderr, which is Claude Code's block reason.
    - **Nothing but `gate_pass` or a block writes to the child's stdout.** Each validator writes to its own file (the quality gate's Child bullet). So `verdict` holds one line or nothing.
  - **The watchdog** is a background subshell with its descriptors on `/dev/null`:
    1. **It ignores HUP, INT, QUIT, TERM, USR2 and ALRM before it forks anything**, and USR1 too until its sleep is running. A validator's group-wide send therefore cannot end it.
    2. **It starts `(trap '' USR1; exec sleep "$budget") &`**, so the sleep is born ignoring every signal above. Started with USR1 merely trapped, a USR1 landing before the subshell's own `trap` killed the sleep under bash 3.2 (probed).
    3. **Then it traps USR1 to a no-op**, which only interrupts its `wait`, and writes `<run dir>/armed`. Then it loops: check `<run dir>/done`, then `wait` on the sleep. If `done` exists, it KILLs the sleep, reaps it, and exits. Otherwise it waits again while the sleep is alive. When the sleep has ended, it fires. Checking before each `wait`, and not only after, keeps a `done` and USR1 that land before the first `wait` from being lost; what is left of that window is two builtins wide and costs latency only, never the verdict.
    4. **Disarming needs `done`, a file only the gate writes.** USR1 only makes the watchdog look, so a validator's `kill -s USR1 0` does nothing to it.
    5. **On firing,** it ignores USR1, checks `done` one last time, and writes `<run dir>/fired`.
    6. **The kill.** It reads the child's pid from `<run dir>/pid`, polling for up to 1 s if the file is not there yet, and its parent from `<run dir>/ppid`. With neither, the child never ran (it refuses to), so there is nothing to kill and no `nowalk` is written. Then it takes a `ps -A -o pid= -o ppid=` snapshot on a line of its own: never a pipeline, whose status would be awk's. The walk is rooted at the child, not at the gate, so the watchdog is never in it and needs no pid of its own.
       - **The child is signalled only while the snapshot lists it with the parent `ppid` names.** A child the gate has already reaped is not walked, so a reused pid is never signalled.
       - It STOPs the child, then walks and STOPs its descendants, until the set stops growing, at most five times.
       - **A walk has failed** when `ps` exits non-zero, prints nothing, or does not list the child while `kill -0` still reaches it. The set is then the child alone, and the watchdog writes `<run dir>/nowalk`.
       - It sends TERM to the set, then CONT, then polls `kill -0` once a second for up to 2 s, stopping early when nothing is left alive. Whole seconds, so a `sleep` without fractions changes nothing.
       - **Before KILL**, it STOPs whatever in the saved set is still alive, walks again from each of those pids, adds what it finds, and repeats until the set stops growing (at most five times). Then it KILLs the union. The walk is rooted at the saved pids, not at the gate, so a descendant already reparented to pid 1 is still covered. A worker a TERM-catching loop forked during the grace is found from that loop's pid.
  - **The gate, around the child:**
    1. **After starting the watchdog, it waits for `armed`** before the child starts: a hundred `sleep 0.01` polls, or two whole-second polls where `sleep` rejects a fraction. The watchdog writes `armed` within milliseconds, so a first poll of 0.1 s cost every gate run most of that 0.1 s: measured at T3 and T4 as about 185 ms of the parent's overhead, and 20 s of `scripts/test-gates.sh`. If `armed` never appears, it STOPs the watchdog, which is its own unreaped child, so the pid is safe, KILLs the watchdog's children from a snapshot (its sleep, which ignores every catchable signal and would otherwise live out the budget), then KILLs the watchdog, reaps it, and blocks (AC5).
    2. **After the child returns, on every path, the signal traps' included:** if `fired` does not exist, it writes `done`, sends USR1 to the watchdog's pid, and reaps it. If `fired` exists, it reaps the watchdog, which is finishing its kill. Both use `{ wait "$wd"; } 2>/dev/null`, looped while `kill -0 "$wd"` still reaches it, because a trapped signal returns `wait` early. No ending leaves a watchdog alive.
    3. It reports the child's status.
  - **`gate_replay <run dir> <status>`**, the status being the one `gate_bounded` returned, judges what the child left, and only when `<run dir>/end` exists. In the child, `gate_pass` and `_gate_block_exit` write `end` after stdout and before they exit. So a verdict torn by a kill is never judged, whatever its bytes.
    - `verdict` exactly `{}` with status 0 is a pass: it replays `err` to stderr and calls `gate_pass`.
    - `verdict` one line beginning `{"decision":"continue","reason":"` and ending `"}`, with the status the channel gives a block, is a block. It replays both files and exits through the harness test `gate_block` uses, which moves into a shared `_gate_block_exit`.
    - Anything else returns 1, as does a `signalled` file or a missing status, which a gate under `set -u` must not abort on. A recognised verdict wins even when `fired` exists, because the child reached it within the budget plus a moment.
  - **Every new function goes on its gate's predates check**, and on the anchor check's (`assets/check-steering-anchors.sh:89`), because a library cut off after `gate_block` passes the bootstrap guard (#198).
- **Both gates take the same shape.** The bootstrap guard and the predates checks run as today. Then `if [ "${1-}" = --bounded ]; then shift; <the existing body, plus progress lines>; fi`, and the parent path follows:
  1. **The run dir:** `mktemp -d "${TMPDIR:-/tmp}/gate-sdd-run.XXXXXX"`, then the same template under `$(git rev-parse --git-path gate-sdd)`. If both fail, the gate blocks, naming both (AC5). Today a failed `mktemp` costs only the fingerprint skip. An inherited sandbox `TMPDIR` that does not exist would otherwise block every turn.
  2. **The EXIT trap** removes `run`'s known files (`v.*` among them) and then the directory, whatever else holds. Unlinking a file a leftover background child still holds open is harmless. A directory it cannot remove is left in `TMPDIR` or the git dir, never in the work tree. This replaces `quality-gate.sh:145`'s guarded trap, which skipped removal whenever `qg_tmp` was empty and left `.out` in the project's root.
  3. **The traps for HUP, INT, QUIT, TERM, USR1, USR2 and ALRM** write `run/signalled` with the signal's name, and return. POSIX runs them only once the foreground child has returned, so they cannot kill the child's tree. The child got the same group-wide signal and ends through its own traps. The parent then runs step 2 of "around the child" and judges. A descendant that ignored a stray group signal and outlived the child survives the gate. That is a stated residual, and the verdict is still a block.
  4. **Before writing any verdict, the parent sets all seven signals to ignored**, so exactly one JSON object reaches stdout. A stray TERM during the replay used to be able to append a second.
  5. The budget is computed, then `gate_bounded "$budget" "$run" sh "$DIR/<gate>.sh" --bounded "$run" …`.
  6. **Judging:** with `signalled`, the signalled block, naming the signal. Otherwise `gate_replay`. Failing that, when `fired` exists, the timeout block. Failing that, the no-verdict block, with `err`'s tail. On the harness's own TERM that block is discarded, which costs nothing. On a stray signal it is the correct outcome.

  - **The child checks its run dir.** It blocks unless `${1-}` is a directory whose `pid` file holds its own `$$`. So a hook entry that wrote `--bounded` by hand blocks. It is neither an unbounded body nor an `set -u` abort with empty stdout, which would be a pass.
  - **The child's own traps** may still `exit 1xx`, because its parent judges that ending (AC5).
- **Quality gate** (`hooks/quality-gate.sh`):
  - **Parent:**
    - The budget is `gate_validator_budget`'s value, or 170 when the line is malformed. In that case the sentence goes to the child as `--budget-error <file>`, so the line blocks only when the validators are about to run (AC7). On return 3, the parent hands nothing over.
    - That value is then bounded by `gate_hook_timeout quality-gate.sh "$_gate_qg_ceiling"` over the list `gate_hook_files "$DIR"` printed before the `cd`, minus the margin. The list is split on newlines only, so a path with a space stays one argument. Return 2, or a bound that is not positive, blocks at once (AC9).
    - The source of the budget (default, line, or file) goes into the timeout block.
  - **Child:** today's body, with three changes.
    - After the skip, a `--budget-error` blocks before the record is removed.
    - **Validator n runs as `( eval "$cmd" ) >"$run/v.$n" 2>&1`** instead of `out=$(eval "$cmd" 2>&1)` (`:203`).
      - It is still a subshell, so an `exit`, a `cd` or an assignment stays inside it, as under `$(...)` today.
      - It runs in the foreground with the hook's stdin and pathname expansion (case 203).
      - Its output goes to a file, not a pipe, so a leftover background child that holds the descriptor no longer holds the gate. A pipe made `$(...)` wait for EOF: 3 s for `sleep 3`, measured.
      - A failure's tail is `tail` of `v.<n>`, with today's line count (case 16).
    - The loop appends `start <n> <cmd>` before validator n, then `ok <n>` or `fail <n>`, to `run/progress`. The index, not the command, ties a line to its file, because two validators may share a command.
  - **The timeout block** (AC1, AC2) is built by the parent, after the watchdog has finished its kill, from three sources:
    - `progress`: the last `start` with no matching end is the cut-off command, and its tail is `tail` of its `v.<n>`, whatever it wrote before it died;
    - the `- Validators:` line, split by the same function the child uses, for the commands that never started;
    - the `v.<n>` of each `fail <n>`.

    **The remedy depends on where the bound came from:**
    - from the line or the default, below the maximum: raise `- Validator budget:`, naming its maximum;
    - from a hook file: that file's `timeout`, the plugin's shipped value, and "re-run `init`";
    - **at the maximum, or for a validator that alone ran past it:** the gate cannot hold this suite. The block names the honest options: a faster suite, or moving the slow validator off the `- Validators:` line to CI, with the reason in `tech.md`. That is how this repository treats `check-version-bump.py`.
  - **The record:** on any ending that is not a replayed verdict, the parent removes the pass record (`git rev-parse --git-path gate-sdd/quality-pass`) before it blocks (AC3). That covers a child cut off just after writing it. A removal that fails is named in the block. The two blocks `gate_bounded` raises itself, a relative run dir and a watchdog that never wrote `armed`, keep the record: no child ran, so the record still describes the source, and AC3 is about runs that were cut off.
  - **What set the budget:** a hook file whose bound is equal to or lower than the line's value, or the default's, is named as the source, and the remedy is its `"timeout"`. A tie is today's normal state (a 180 s `"timeout"` against the 170 s default), and naming the line there would send the user to raise a value the file caps anyway.
  - **The header** (`:17-19`) and the comment at `:187-190` say that the deadline is part of the guarantee.
- **Review gate** (`hooks/review-gate.sh`):
  - **Parent:** the budget is `_gate_rg_budget`, bounded the same way by `gate_hook_timeout review-gate.sh "$_gate_rg_ceiling"` minus the margin. No environment variable can change it. The tests set it through a copied-gate fixture's own hook file.
  - **Child:** today's body. It writes:
    - `phase current` before `check_current_branch` and `phase scan` before `scan_other_branches`;
    - the listed refs to `run/refs`;
    - `checked <slug>` and `found <slug> — <sentence>` as the scan goes.
  - **The timeout block** (AC6) names one of two states:
    - "still checking the current branch";
    - for the scan: the branches found so far with their sentences, and the branches not checked (`refs` minus `checked`).

    **The remedy depends on the cause:**
    - when a hook file set the bound: that file's `timeout`, the 120 the plugin ships, and "re-run `init`". A project still rendered at 30 is bounded to 20 s, and fewer branches is the wrong advice for it;
    - in the scan: fewer live branches. Merge, review or delete them;
    - in either phase: `git commit-graph write --reachable`, because the issue's replay measured the history walk dominating.
- **Ceilings** (AC8):
  - The six `Stop` timeouts become 600 and 120: `.claude-plugin/hooks.json:6,11`, `hooks/templates/antigravity.hooks.json:27,32` and `.claude/settings.json:14,19`.
  - `scripts/check-manifests.py` reads `_gate_qg_ceiling` and `_gate_rg_ceiling` from `hooks/gate-lib.sh` with anchored regexes, and fails when either is missing. It reads each file's `Stop` timeouts, keyed by gate script name, in both shapes, the way `scripts_in` pairs the gates (`:288-296`), and fails on any difference.
  - `manifest_repo` (`scripts/test-gates.sh:7213`) gains `.claude/settings.json`. A missing file fails, because this is a check on this repository, wherever `.specs/` is present; a release payload, which has none, passes without it. A file that is valid JSON but not an object fails, as the plugin's file and the template already do.
  - The anchor check also reads `.claude/settings.json` in this repository, but with AC9's rule (budget against timeout). Two checks over one file, for two different questions.
- **Anchor check** (AC10, `assets/check-steering-anchors.sh`):
  - `ANCHORS` gains `.steering/tech.md|Validator budget`, in T1 beside the function, so case 30 stays green.
  - Its existing loop already fails a loosely matched key with an empty value, which agrees with AC7's empty-is-malformed.
  - It then calls `gate_validator_budget`, and `gate_hook_timeout` for both gates over AC10's file set: `git ls-files -z` for the three names at any depth (so a path git would quote is still read; only one holding a newline is a residual), plus the root's three names, tracked or not. It fails on return 2 or 3. It fails when an explicit line exceeds the file's bound minus the margin. Where the library came from (`GATE_SDD_HOOKS`, a copy or the plugin) does not change the files it reads.
  - **The header's "does NOT judge whether a value is any good"** becomes: it judges whether the value can be honoured by the hook that reads it. That is the question it already asks, whether the reader can see the line, taken one step further. `hooks/gate-lib.sh:359-360`, which quotes the header, follows it.
- **Steering line wiring** (AC13):
  - `init`'s tech.md template (`skills/init/SKILL.md:49-56`) describes `- Validator budget: <seconds>` as optional, to be omitted unless the suite needs more than 170 s, with the `- Target:` bullet's "omit if no view" wording. A `check-skill-contracts.py` pin pins that sentence.
  - `init`'s Antigravity bullet (`:71`) says the rendered timeouts are the hook's ceiling, and the budget lives in steering.
  - `init`'s anchor-check bullet (`:63`) says what the check now verifies.
  - `CONTRIBUTING.md:43` lists the line. `docs/DESIGN.md:17` and `:30` count it ("seven" becomes "eight"), and the Seams table gains a row: budget against timeout, guarded by `check-manifests.py` and the anchor check.
  - The key lists at `assets/check-document-set.py:189-190` and `scripts/test-gates.sh:5082` stay as they are. They list the keys `gate_steering_value` reads, and this line has its own parser.
  - This repository writes no line: 70 s against 170 s needs none, and the absent path is the one most projects take. T3 records two times for the `- Validators:` line in the spec: one alone, and one beside a second concurrent run, because parallel sessions share this checkout. If either is over 120 s, the line is written at twice the slower time, capped at 590, and the reason given.
    - **Measured at T3, 2026-10-17** (macOS, the T3 tree, every command exiting 0): 92.6 s alone, and 104.4 s for each of two runs started together. Both are under 120 s, so this repository writes no line. `scripts/test-gates.sh` is 91.6 s of the 92.6, up from 71 s before T3: about 5 s is T3's own cases, and the rest is every quality-gate case paying for the parent, about 185 ms a run, most of it `gate_bounded`'s first 0.1 s wait for `armed`.
    - **Re-measured at T4, 2026-10-17:** T4 put the review gate behind the same parent, and the suite reached 110–117 s, the whole line about 121 s alone, past the 120 s rule; the T3 conclusion above no longer held. After the poll change the line is measured again in T5, once the shipped timeouts are 600/120, since a line written above 170 while `.claude/settings.json` still gives the quality gate 180 would fail AC10's anchor check. T5 writes `- Validator budget:` by the rule above if either time is still over 120 s, and records both times here either way.
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
  - **`docs/fidelity.md`, on both:**
    - A suite always over its budget blocks every turn until the line is raised. Above the maximum it cannot be raised, and the block says so.
    - Claude Code stops honouring that block after 8 continuations in a row with no tool call (`CLAUDE_CODE_STOP_HOOK_BLOCK_CAP`). A model that makes tool calls between them resets the count, so the cap does not bound the loop. Antigravity's cap is 10, and whether it resets is unverified.
    - The residuals of AC4, AC5 and AC9, each in one line.
    - busybox `ps`, `ash` and `awk` are unverified. Only the macOS tools and CI's ubuntu tools run the cases.
    - A cut-off tail can carry control bytes, which #302 owns.
- **Release notes** (quoted by the PR body):
  - **Claude Code:** the new ceilings arrive by plugin update.
  - **Every project:** re-copy `check-steering-anchors.sh` for AC10.
  - **Antigravity:** re-run `init`, which re-renders `.agents/hooks.json` at 600/120 and re-copies the gates. A project that re-copies only `hooks/` keeps 180/30. Its gates then bound themselves to 170 s and 20 s (AC9), which blocks, never passes.
  - **Stand-down projects:** the same bound applies through their `.claude/settings.json`.
  - **Every pass record is invalidated once**, because `gate-lib.sh` is in the fingerprint.
  - **A suite between 170 s and 180 s goes from passing to blocking** until the project writes `- Validator budget:`. The note gives the line to write.
- **Bump:** minor, 0.33.0, as a step of `implement` after the review. The change alters when both gates block and adds a machine-read line.
- Affected files: `hooks/gate-lib.sh`, `hooks/quality-gate.sh`, `hooks/review-gate.sh`, `.claude-plugin/hooks.json`, `hooks/templates/antigravity.hooks.json`, `hooks/templates/README.md`, `.claude/settings.json`, `assets/check-steering-anchors.sh`, `scripts/check-manifests.py`, `scripts/check-skill-contracts.py`, `scripts/test-gates.sh`, `skills/init/SKILL.md`, `README.md`, `README.ja.md`, `AGENTS.md`, `CONTRIBUTING.md`, `docs/CONTRACT.md`, `docs/DESIGN.md`, `docs/fidelity.md`, `docs/verified.md`, `docs/BACKLOG.md` (#304 to row 1's `Why here`, the two out-of-scope findings), and both manifests for the bump.
- **Blast radius:**
  - **A validator's leftover background child no longer holds the gate open.** It held the `$(...)` pipe before. Now it holds its own `v.<n>`, which the gate neither waits on nor judges. Nothing kills it when the validator exits in time, which is the same as on Claude Code once a hook exits. When the budget fires, the walk kills it.
  - **One extra `sh` per gate per turn end**, plus the watchdog. The time stays well inside the margin.
  - **A slow review gate can hold a turn end for up to 110 s** where the harness killed it at 30 s. That time is spent reaching a verdict.
  - **Turn-end stdout and stderr are replayed after the child exits** instead of streamed. Neither harness shows a `Stop` hook's output before it exits.
- **Why this cannot recur:**
  - A verdict reaches the harness only as a replay the gate recognised, or as a block the gate wrote. The child's exit, a killed child, a stray signal and the deadline all end in one of those two.
  - The verdict channel carries the verdict alone, and is judged only once the child marked it complete.
  - Disarming needs a file only the gate writes, not a signal anyone in the group can send.
  - The deadline is a `sleep`, not a clock, and it is checked against every timeout the gate can see: `check-manifests.py` for the plugin's files, AC9 at run time and the anchor check in CI for the project's own.
  - A temporary directory, watchdog or library function that is missing blocks.
  - AC12's cases assert elapsed time, so removing the deadline goes red even though the suite never reproduces the harness's kill.

## 3. Tasks (TDD-ordered)
> One task is one complete Red-Green-Refactor cycle, so one green commit. No task is sequenced after the review.
- [x] T1: budget and hook-timeout readers. Cases in the shared-library section after `:2312`:
  - `gate_validator_budget` for absent, `1`, `590`, `591`, `0`, `010`, `-5`, `abc`, `12s`, `300\r`, tab-only, empty and space-only, and an unreadable `tech.md` returning 3 (AC7);
  - `gate_hook_files` for each L2 layout (launched at the root, below it with `sub/.claude/` and with `sub/.agents/`, and no `CLAUDE_PROJECT_DIR`), for no git root, and for a symlinked `.agents/hooks`. One case checks that its Claude Code half and `plugin-gate.sh:133-143` give the same set (AC9);
  - `gate_hook_timeout` for nothing named (ceiling, source `ceiling`), `.agents/hooks.json` at 180/30, two files with the lower one winning, every spelling in case 221's `pd_spellings`, `code-review-gate.sh` not naming the review gate, minified JSON, `timeout` before `command`, a duplicate `timeout` key (the smaller wins), `//` and `/* */` comments, a `{` or `}` inside a command string, `\"` escapes, a missing `timeout`, a timeout of 10 (bound not positive), an unparseable file, an unreadable file (under `note_skip`'s root guard), a fast check holding `{}` ahead of the `Stop` entries, and a 1 MB minified file parsed in under 1 s (AC9);
  - the derived constants (AC8's library half).

  Red: the functions do not exist. Green: the constants, the three functions, and the `ANCHORS` row. Case 30 stays green.
- [x] T2: `gate_bounded` and `gate_replay`, driven by a small script under `$TMP` that sources the library. First the AC12 session helper, defined before every case that uses it. Cases:
  - a 20 s command at budget 2: `fired` is written and the elapsed time is ≤ 7;
  - a fast command at budget 20: status passed through, no `fired`, elapsed ≤ 1 (mutation: a foreground `sleep`, whose trap waits out the budget);
  - a command that exits 143 by itself: no `fired`;
  - a grandchild that ignores TERM, dead once the function returns;
  - a TERM-catching loop that forks a fresh `sleep` on each TERM: nothing it created is alive once the function returns (mutation: KILL the saved set without the re-walk);
  - in the session helper, a `kill 0` and a `kill -s USR1 0` from inside the command: each leaves the watchdog armed, so a 20 s command still fires at the budget (mutation: disarm on USR1 alone);
  - `ps` shims on `PATH` that exit 1, that exit 0 and print nothing, and that print a table without the child: in each, the child is killed, `nowalk` is written, and elapsed ≤ budget + 5 (mutations: judge by the pipeline's status; detect by `command -v ps`);
  - a watchdog that never writes `armed` blocks;
  - no watchdog or `sleep` from the run is alive after any case, the signal cases included;
  - `gate_replay` for `{}`, a block line, a torn line, a complete line with no `end`, empty output, status 1 with `{}`, a `signalled` file, and no status under `set -u`;
  - `gate_bounded` called from a subshell still cuts off a 20 s command at budget 2; a child that cannot write its `pid` never runs; a relative run dir blocks; a watchdog stuck before `armed` leaves no sleep behind.

  Each case names its mutation; those not named above are: kill the root only; decide by status; skip the KILL step; let TERM disarm the watchdog. Red: the functions do not exist. Green: both functions and `_gate_block_exit`.
- [x] T3: quality gate, cases 287 and up (T1 took 259–269, T2 270–286) after `:2310` (`qgp_repo`, `qgp_runs`, the second `run_qg`):
  - a 20 s validator after a fast one at budget 3, which prints a line before it sleeps: that line is in the block (mutation: read the tail from the verdict file);
  - a 20 s validator after a failing one at budget 3;
  - one validator alone at budget 2, on the Claude Code channel (stderr begins with the gate's own sentence) and on the Antigravity channel (parsed JSON);
  - the not-run list;
  - no pass record afterwards, and the next run runs;
  - a passing validator that prints to stdout and stderr: the run passes, and replays `{}` on the Antigravity channel (mutation: validators write to the child's stdout);
  - a validator that runs `(sleep 20; echo late) &` and exits 0: a pass in under 5 s at budget 3 (mutation: keep the `$(...)` capture);
  - a validator's `cd` does not reach the next validator;
  - a copied gate under `.agents/hooks/` with no budget line and `"timeout": 13`, which blocks at 3 s and names the file (the no-line path);
  - a stand-down copy under `sub/.claude/hooks/`, launched with `CLAUDE_PROJECT_DIR=sub`, whose `sub/.claude/settings.json` sets 13, with a root `settings.json` at 600: it blocks at 3 s and names `sub/.claude/settings.json` (mutation: read the root's files only);
  - a malformed line that blocks only when the validators run;
  - in the session helper, a validator running `kill 0`, and one running `kill -s USR1 0`: each blocks, naming the signal;
  - a TERM sent to the gate's pid alone during a 20 s validator: a block within budget + 5;
  - `TMPDIR` set to a directory that does not exist: the run dir falls back to the git dir and the gate still decides (mutation: block on the first `mktemp`). Both unwritable: a block naming both;
  - a hand-written `--bounded` with no run dir blocks;
  - no file left in the work tree, with no `- Source globs:` line (mutation: the run dir falls back to `.`).

  The timing cases run concurrently (AC12). Cases 16, 17, 159, 203 and 239–258 stay green. Then the parent and child split. Record the `- Validators:` line's two measured times in the spec (Steering line wiring).
- [x] T4: review gate:
  - a copied-gate fixture whose own hook file has review `"timeout": 13`;
  - a `git` shim on `PATH` that sleeps 20 s in `rev-parse --verify` for one branch, and one that sleeps in the current branch's `merge-base`;
  - each blocks within budget + 5 and names what it was checking, the branches not checked and the ones found;
  - the remedy for the copied-gate fixture names its hook file's `timeout` and the shipped 120, not fewer branches;
  - the unbounded default prints 110 through the derivation case in T1.

  Then the review gate's parent and child split.
- [ ] T5: manifest and anchor checks:
  - check-manifests' section, after `:7236`: a mismatched timeout in each of the three files, a missing `.claude/settings.json`, and a missing constant each fail (AC8);
  - the anchor section, after `anchor_repo` at `:3111`, with fixtures under `git init`, since AC10 reads tracked files:
    - a malformed line fails;
    - an explicit line above an `.agents/hooks.json` bound fails, and still fails with `GATE_SDD_HOOKS` pointing at a plugin checkout (mutation: take the file set from the library's directory);
    - a line above a `sub/.claude/settings.json` bound fails;
    - an unparseable hook file fails;
    - a library without the new functions fails with the "predates" diagnosis;
    - a stand-down `.claude/settings.json` at 600/120 with a line of 300 passes (mutation: compare against the default, not the file);
    - no hook file passes (mutation: fail when no hook file exists) (AC10).

  Then the six timeouts, `check-manifests.py`'s reader and comparison, and the anchor check's additions with its header.
- [ ] T6: the `check-skill-contracts.py` pin for the template sentence, red until `skills/init/SKILL.md` carries it. Then the `init` bullets, every statement listed under Docs and Steering line wiring, and `docs/BACKLOG.md`: #304 moves from row 1's `Item` cell to its `Why here`, which gains the #320 citation and the scan-cost finding, and the `SessionStart` contradiction goes to the claim-drifts row.
