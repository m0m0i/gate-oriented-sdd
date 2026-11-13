# Spec: a validator the hook's PATH cannot find blocks with a message that says so
- Slug: 355-a-validator-the-hook-path-cannot-find-says-so   Issue: 355   Type: bug   Status: approved
- Author: m0m0i   Date: 2026-11-08

## 1. Requirements (WHAT / WHY)
- Reproduction: a project whose `- Validators:` line names a bare command that a user-space version manager puts on the shell's `PATH`, such as `npm --prefix web run lint` with `npm` from nvm or mise. The quality gate runs at turn end under a hook whose `PATH` does not hold that directory, which is the case for a host started by launchd rather than from a terminal. #355 quotes the block from a consumer's Antigravity session: each `npm` validator printed `npm: command not found`, and the gate blocked. In `scripts/test-gates.sh` terms, a Validators entry naming a command that is on no `PATH` reproduces it on `main` at `3e477ff`. The gate blocks, with no line saying the command was not found on the hook's `PATH`, no `PATH`, and the remedy "fix the failure rather than working around the gate" (`hooks/quality-gate.sh:654`).
- Expected:
  - The gate still blocks. A validator that did not run has not passed (`- Owns: gates never fail open`, `.steering/product.md`; G-1).
  - The block says why: the command the hook could not find, the `PATH` it ran with, and that the fix is the host's environment. No agent can change that, so the block gives a remedy a person can apply.
  - Today the message tells the agent to fix the failure. #324's issue records an agent doing exactly that, when its visible failure was not one it could fix: it swapped in an always-pass validator.
- Actual:
  - Every turn end blocks with the same message.
  - The message points the agent at a failure in the project's code, which is not where the failure is.
  - The agent cannot end the session's loop, and nothing in the block tells the person what to change.
- Impact:
  - **Who hits it:** every project with a bare toolchain command on its `- Validators:` line (`npm`, `pnpm`, `npx`, `uv`, `cargo`, `go`, a bare `ruff`), on any host whose hooks get a narrower `PATH` than the session's shell. Commands named by a path from the git root (`./scripts/x`, `.venv/bin/ruff`) are not exposed: the gate `cd`s to the root first (`hooks/quality-gate.sh:404-406`). The four harness checks are not exposed either. They pass under `PATH=/usr/bin:/bin` with macOS's `/usr/bin/python3` 3.9.6 (measured 2026-11-08).
  - **Where:**
    - **Claude Code:** a hook inherits the session's environment (code.claude.com/docs/en/hooks: "A hook process inherits the parent environment"), and `docs/verified.md` P4 measured a `Stop` hook's `PATH` lacking what the Bash tool's had.
    - **Antigravity:** the hooks page says nothing about a hook's environment. On this Mac on 2026-11-08, process inspection found two different environments:
      - the launchd-started App (2.29.0) and the `remote-control` CLI daemon have `PATH=/usr/bin:/bin:/usr/sbin:/sbin`;
      - the App's language server gets the login shell's environment, through a `$SHELL -ilc env` that falls back silently to the minimal one.
      Which of these #355's session ran under is unknown.
  - **It hides until the first edit.** `init` runs the validators and the gate by hand in the session's own shell (`skills/init/SKILL.md:104`). That run records a pass, and `PATH` is not in the fingerprint (`hooks/quality-gate.sh:466-469`). So the hook skips on that record, and the 127 first shows at a turn end after an unrelated edit.
  - **What it costs:** every turn end of the session, until a person restarts the host with the right environment. The message also steers the agent at the project's toolchain, which is how #324's swap happened.
- **Root cause:**
  - The gate runs each validator as `( eval "$cmd" ) > "$run/v.$n" 2>&1` (`hooks/quality-gate.sh:604`), in whatever environment the host started the hook with. That is correct, because the gate must not guess a toolchain.
  - It then treats every non-zero status the same. It keeps no status, so a 127 (the shell's status for a command it could not find) and a lint error look alike. Each becomes `--- <cmd>` plus the last 20 lines of output, under one header aimed at the agent (`:620-622`, `:654`).
  - The shell's own "not found" text is in that tail, but it differs between shells (bash says `npm: command not found`, dash says `eval: npm: not found`). It names neither the `PATH` searched nor who can change it.
  - The same is true of the parent's timeout block, which re-reads each failed validator's tail (`:336-344`).
- Acceptance criteria:
  - [ ] **AC1:** WHEN a validator exits 127 and its first word, read by text alone (Design step 2), is a bare name that `command -v` does not resolve under the gate's own `PATH`, THE SYSTEM SHALL block as for any failed validator, and:
    - name that word as a command the hook's `PATH` does not hold;
    - print that `PATH` once;
    - say that this is the environment the host started the hook with, which no agent can change from inside the session;
    - give the remedies a person can apply, worded for the harness the gate runs under (Design step 4).
    This holds on both harnesses and both channels (the JSON `reason` and stderr), in the child's block and in the parent's timeout block. When every failed validator is AC1's case, the child's header replaces "fix the failure rather than working around the gate" (Design step 5). The timeout block keeps its own header and remedy.
  - [ ] **AC2:** WHEN a validator exits 127 and AC1's condition does not hold, THE SYSTEM SHALL block and say only what is known. AC1 fails to hold when the first word resolves, holds a `/`, follows a `PATH=` assignment, or cannot be read from the text. The block says that 127 is the shell's status for a command it could not find, which may be the one the validator names or one it runs. It prints the `PATH` (Q1), and says the command may be missing from that `PATH` or may be one the project or its checkout should provide. It does not say that no agent can change the cause.
  - [ ] **AC3:** WHEN any failed validator is not AC1's case, THE SYSTEM SHALL keep the child's header byte for byte as on `main`. The only additions are each 127's appended line and the one paragraph after the failures. WHEN no failed validator exits 127, THE SYSTEM SHALL produce `main`'s block, byte for byte, in the child and in the timeout block.
  - [ ] **AC4:** a 127 stays an ordinary failure:
    - it is `fail <n>` in `progress`, as on `main`;
    - the start token records it (`:612`);
    - the pass record is removed (`:613`), and no pass is recorded;
    - the next turn end runs the validators again.
    Nothing about a 127 makes any turn end pass that would block on `main`.
  - [ ] **AC5:** the text this change adds names no file, setting, variable or command through which an agent could make the gate pass. That text is the appended lines, the paragraph and the replaced header clause. It must not name a `PATH=` prefix in a hook file, a `git config` key, a file in the home directory, or an edit to `- Validators:`. The remedies it names are ones a person applies to the host. The text `main` already prints is outside this criterion and unchanged under AC3.
  - [ ] **AC6:** the block is valid JSON whatever bytes the `PATH` holds, as #302 requires of every block. That covers a tab, a quote, a backslash, a `%`, a well-formed multibyte character, and a lone byte that is not UTF-8.
    - In the `reason`, the `PATH` round-trips exactly, except that each byte that is not well-formed UTF-8 reads as one U+FFFD.
    - stderr carries the `PATH`'s raw bytes.
  - [ ] **AC7:** `init`'s Step 4 says its by-hand run used the session's own `PATH`, which a hook need not have. It also says the first turn end after an edit is the first run under the hook's `PATH`, because the by-hand pass is recorded (Q2).
    - **It warns, and blocks nothing,** when a bare first word resolves in the session's shell but not in a fresh `sh` under the system directories, `PATH=/usr/bin:/bin:/usr/sbin:/sbin`.
    - **That test catches three cases:** a tool from a user-space version manager under `$HOME`, Homebrew's `/opt/homebrew/bin` or `/usr/local/bin`, and a name that exists only as an alias or function of the session's shell.
    - **The warning** names the remedies AC1 gives, and goes in the report.
    - **The READMEs:** `README.md`'s and `README.ja.md`'s `init` sentence state the limit.
    - **A pin:** one in `scripts/check-skill-contracts.py` holds the instruction.
  - [ ] **AC8:** `docs/fidelity.md` and `docs/verified.md` say what each harness gives a hook's `PATH`, and mark each claim as documented, measured, or not exercised. The 2026-11-08 process inspection is recorded as what it is: process inspection, not a hook run.
  - [ ] **AC9:** the tests are `scripts/test-gates.sh` cases for AC1–AC6, placed after the fixtures they use. Each case for something new fails on `main`.
  - [ ] **AC10:** a real run on Antigravity CLI, in a local fixture pushed nowhere (Q3).
    - **Setup:** `agy` is started headless by absolute path, under `env PATH=/usr/bin:/bin:/usr/sbin:/sbin` (not `env -i`, which drops `HOME` and the login). The fixture has two validators: `npm --version`, and a command that is on no `PATH` at all.
    - **On `main`'s gate:** the absent command's block is today's.
    - **On this branch's gate:** it is AC1's.
    - **Recorded from inside the hook:** the hook's `PATH`, and whether `npm` resolved in it. That shows whether `agy` hands its hooks the `PATH` it was launched with or the login shell's.
    - **Where it goes:** `docs/verified.md`.
- Out of scope:
  - **Adding directories to the gate's `PATH`, by a built-in list or a person-owned file** (the maintainer's call on #355). Reasons:
    - the list has no end;
    - a guessed toolchain can differ from the project's and CI's;
    - an agent can write some of those directories;
    - a sourced file would let the gate be switched off from outside the repo.
    The block names remedies instead. `init`'s comparison with the system directories (AC7) is advisory and changes no `PATH`.
  - **The fast check.** It also inherits the hook's `PATH`, but never blocks (`hooks/templates/antigravity.hooks.json`).
  - **Windows.** The gates are POSIX `sh`.
  - **Parsing the shell's "not found" text,** which differs by shell.
  - **A remedy for the Antigravity App.** Its hook environment is not exercised here, so the block offers it none, and `docs/verified.md` says so.

### Clarifications
Asked and answered 2026-11-08.

- **Q1 — which 127s does the block explain?** **A:** every one, in two wordings (AC1, AC2). The `PATH` is printed for any 127, and "not on the hook's `PATH`" is said only when the first word fails `command -v`. A 127 from inside a validator is the same host fault one level down, and the definite wording would be wrong there. Examples are an `env node` shebang, or an npm script calling `npx`. A wrong reading changes only the text, since the turn blocks either way.
- **Q2 — what does `init` do, given it cannot see a hook's `PATH`?** **A:** a note and an advisory warning (AC7), which blocks nothing. "Note only" and "nothing" were the alternatives. The answer named "resolves under `$HOME`" as the trigger. The critique below widened it to "resolves in the session but not under the system directories", which catches Homebrew and session aliases too, and it stays advisory.
- **Q3 — a real run?** **A:** yes, on a real `agy` with a reduced `PATH`, recorded in `docs/verified.md` (AC10), as #343's T6 was.

Decided rather than asked, as design calls:
- **How the first word is found:** by text alone, with no `eval` (Design step 2).
- **The remedies the block names:** only ones documented or measured, worded per harness (Design step 4).
- **The anchor check stays out.** A `command -v` failure there would duplicate the gate's diagnosis. It would also false-block a CI job that runs it before `npm ci` or `uv sync` (`assets/check-steering-anchors.sh:12-18`).

**Revised 2026-11-08, before approval, from a four-lens spec review.** The lenses were fail-open, portability, tests and records, and an independent skeptic re-checked each finding. 34 of 41 survived, and every one is taken.
- **The HIGH.** The draft gave every 127, AC2's included, the header swap and "no agent can change it". Those are false for a fixable failure in the project or its checkout: a missing `node_modules`, a script calling a misspelled name, a deleted validator file. Both now belong to AC1 alone (AC1, AC2, AC3).
- **The MEDIUMs:**
  - the mixed block and the timeout block's header (AC1, AC3);
  - AC2's condition and wording, which claimed a resolution the gate never checked;
  - `FOO=1 <missing>`, which is AC1's case, not AC2's;
  - the timeout block finding a 127 by its tail's text, now by a `progress` line;
  - AC6's lone invalid byte, which #302 turns into U+FFFD;
  - AC5's scope, now only the added text;
  - remedies that were documented for neither host, now worded per harness;
  - the fidelity row's claim for Claude Code;
  - the pin's required argument and its count;
  - `init`'s trigger, which missed Homebrew;
  - AC10's reproduction on `main`, now with a command on no `PATH`.
- **The LOWs:**
  - glob, redirection and tilde words;
  - a line glued onto output with no trailing newline;
  - `assets/shipped-texts.json`, rebuilt in every task that edits the gate;
  - the insertion point in `init`;
  - T5's AC reference.

## 2. Design (HOW)
- **Fix approach.** The gate keeps the status of each validator. A 127 gets one more line, and the block gets one paragraph. Nothing else in a block changes.
  1. **Keep the status.**
     - The child's loop (`hooks/quality-gate.sh:604`) becomes `( eval "$cmd" ) > "$run/v.$n" 2>&1 && qg_rc=0 || qg_rc=$?`.
     - The probe runs outside that subshell, never inside `eval "$cmd; …"`. A trailing `# comment` on an entry would comment out a probe written inside it, and the runner's own command carries one (`:122`).
     - On a 127, the child writes `127 <n> bare` (AC1) or `127 <n> other` (AC2) to `progress`, before `fail <n>`. `fail <n>` itself is unchanged, and `qg_open` (`:308`), `_tb_last` (`:319`) and the timeout block's `grep -qx "fail $_tb_n"` (`:336`) ignore the new line type. The exit trap's cleanup list does not change either.
  2. **Classify a 127, by text alone (`qg_first_word`).**
     - Under `set -f` with the default `IFS`, split the command into words.
     - Skip leading assignments. A word is one only when it matches `[A-Za-z_][A-Za-z0-9_]*=*`. An assignment whose name is exactly `PATH` makes the first word unknown.
     - A word holding a quote, `$`, a backtick, `(`, `{`, `\`, `;`, `&`, `|`, `<`, `>`, `*`, `?` or `[`, or starting with `~`, is unknown. The gate evals under `set +f` (`:598`), so a glob or a tilde can expand to a name the probe never checked, and a redirection is not a command.
     - A word holding a `/` is never called "not on the `PATH`".
     - Otherwise the word is bare, and `command -v "$w" >/dev/null 2>&1` is asked under the gate's own `PATH`. dash returns 127 for a missing name and bash 1, so the test is for non-zero, never for `= 1`.
     - A bare word that does not resolve is AC1's case. Everything else is AC2's.
  3. **Append, never insert.** The line goes into `v.$n` after the command's own output. When `v.$n` is non-empty and its last byte is not a newline, a newline is written first.
     - AC1: `gate-sdd: exit 127: '<word>' is not on the PATH this hook runs with.`
     - AC2: `gate-sdd: exit 127, the shell's status for a command it could not find: the one this validator names, or one it runs, such as an 'env' shebang's interpreter or a script's tool.`
     As the last line of `v.$n`, it survives `tail -20` and reaches the child's block (`:622`) and the timeout block (`:342`). The `--- <cmd>` header stays next to the tail's first line, as case 295 requires.
  4. **The paragraph, once per block (`qg_path_note`).** The child knows the classes from step 1. The timeout block reads them only from `progress`'s `127 <n>` lines, for validators it prints as `fail` (never the cut-off one), and never from a tail's text. The paragraph goes after the failures and before `$qg_unordered$qg_unrec`, and holds:
     - the `PATH` the hook ran with, printed as a `%s` argument and escaped by `gate_block` (#302) (AC6);
     - with any AC1 case: that this is the environment the host started the hook with, which no agent can change from inside the session;
     - with AC2 cases only: that the command not found may be missing from this `PATH`, or may be one the project or its checkout should provide;
     - the host remedies, worded by `_gate_block_status` (`hooks/gate-lib.sh:114`):
       - **Claude Code:** start `claude` from a terminal whose shell has the tool on its `PATH`. A hook inherits the session's environment, per the hooks page. For the desktop app, put the tool's directory on the login shell's `PATH`, then quit and reopen the app, per the desktop page's "Session not finding installed tools".
       - **Antigravity:** start `agy` from such a terminal (AC10).
     It names nothing else (AC5).
  5. **The header.** Only when every failed validator is AC1's case does the child's clause "fix the failure rather than working around the gate" become "none of these could be started on the hook's PATH, which no agent can change; the paragraph below says what a person can". In every other block the header is `main`'s, byte for byte (AC3). The timeout block's header and remedies do not change.
  6. **What does not move:**
     - the token write on a failure (`:612`);
     - the record's removal (`:613`);
     - the pass write (`:629-647`), which a 127 never reaches;
     - the exit path (AC4).
- **Why not narrower:** appending the shell's text, or the `PATH` alone, leaves the remedy aimed at the agent. That is the half of #355 that steers the agent at the toolchain.
- **Why not wider:**
  - A `PATH` source of any kind is out of scope (§1).
  - The anchor check stays out (Clarifications).
  - A probe of each `&&`, `;` or `|` segment would still be a guess, and AC2's wording is true for all of them.
- **`init` (AC7).** The sentence goes in Step 4 item 1 (`skills/init/SKILL.md:104`). It follows the sentence ending "…because the record does not hold the budget line." and precedes "On Claude Code the plugin's `SessionStart` hook sets `GATE_SDD_PLUGIN_ROOT`". That position is outside the span `scripts/check-skill-contracts.py:149-163` matches verbatim, and it keeps "the same two reads" next to the timing it refers to. The sentence says:
  - the by-hand run and the recorded pass used the session's own `PATH`;
  - for each bare first word, compare `command -v` in that shell with `env PATH=/usr/bin:/bin:/usr/sbin:/sbin sh -c 'command -v "$1"' sh <word>`, testing for non-zero;
  - a word that resolves only in the session is reported as a warning naming AC1's remedies.
  Item 5 (`:108`) reports it. `README.md:180` and `README.ja.md:188` gain the limit.
  - **The pin is the forty-third,** and the docstring moves with it: "Forty-two today. A forty-third" becomes "Forty-three today. A forty-fourth", and "#355 the forty-third" joins the history. Its argument for why review cannot defend the sentence: the sentence reads as an optional caveat about the by-hand run, so a review that trims it reads the cut as concision. Deleting it leaves every install passing `init`, and the cost appears later, as #355's misreported 127 at a turn end.
- **Docs (AC8):**
  - **`docs/fidelity.md` gains a row, "A hook's `PATH`":**
    - **Claude Code:**
      - documented, not measured: a hook inherits the session's environment (hooks page);
      - measured (P4): an entry only the Bash tool receives, the plugin's `bin/`, does not reach a `Stop` hook;
      - not exercised: a desktop-started session's hook.
    - **Antigravity:**
      - undocumented;
      - the 2026-11-08 process inspection;
      - AC10's run;
      - not exercised: the App.
  - **`docs/verified.md` gains a section** with AC10's run and what it does not support.
  - **`hooks/quality-gate.sh`'s comment at `:466-469`** says that `PATH` is not hashed either, and why: a pass recorded under one `PATH` stands under another until the source changes.
- **Affected files:**
  - `hooks/quality-gate.sh`;
  - `scripts/test-gates.sh`;
  - `assets/shipped-texts.json`;
  - `skills/init/SKILL.md`, `scripts/check-skill-contracts.py`;
  - `README.md`, `README.ja.md`;
  - `docs/fidelity.md`, `docs/verified.md`;
  - the work log;
  - both manifests, after the receipt.
  Every commit that edits `hooks/quality-gate.sh` rebuilds `assets/shipped-texts.json` with `scripts/build-shipped-texts.py` in the same commit, or case 417 goes red. `hooks/gate-lib.sh` does not change.
- **Blast radius:**
  - Every failed validator now has its status read. A block with no 127 is `main`'s byte for byte (AC3), and so are the needles of cases 16, 17, 295 and 403.
  - Antigravity installs get the change by a re-run of `init` (#343), and Claude Code installs by a plugin update. gate-lib does not change, so an old `quality-gate.sh` beside a new library is unaffected.
  - The fast check and the review gate run no validator through this path.
- **Why this cannot recur:**
  - The status is kept, so a command the hook could not start is no longer reported as a failure of the project's code.
  - Cases pin both wordings, the unchanged blocks, and AC5's absence of any agent lever.
  - AC10 records what Antigravity actually gives a hook, so the next diagnosis starts from a measurement.

## 3. Tasks (TDD-ordered)
> One task is one complete Red-Green-Refactor cycle, so one green commit. No task is sequenced after the review. Each case names the Design rule it exercises rather than restating the classification.
- [ ] **T1:** the child's block (AC1–AC5). Cases from 421, after `t3_repo`, `t3_qg` and `adr_check`, on both harnesses and both channels. The rows:
  - AC1's case: alone, and after an assignment that is not `PATH` (`FOO=1 <missing>`; the step 2 skip). Every failure is AC1's, so the header is swapped.
  - AC2's case:
    - `sh -c <missing>` (the word resolves);
    - a script on `PATH` whose `#!/usr/bin/env` names a missing interpreter;
    - `./lint.sh` calling a missing name, and `./missing.sh` (both `/`);
    - `PATH=/x <missing>` (the `PATH=` rule);
    - `>o <missing>` and `a-b=c <missing>` (the unknown and assignment rules).
    Each asserts `main`'s header, the line, the `PATH`, and no "no agent can change" sentence.
  - Mixed blocks: an exit 1 beside an AC1 127, and an AC1 127 beside an AC2 127. `main`'s header, the lines, and one paragraph.
  - An exit 1 alone: the block is `main`'s byte for byte.
  - `sh -c 'printf x; exit 127'`: the line stands on its own line.
  - AC4: a seeded pass, then a 127 run. No pass is written, and the next turn end runs the validators again.
  - AC5: with the paragraph cut out by its opening words, and the printed `PATH` value removed, the added text holds none of `hooks.json`, `settings.json`, `git config`, `tech.md`, `Validators`, `~/`, `export` or `launchctl`. The paragraph's presence makes this red on `main`.
  - The per-harness remedy wording, one row each.
  Then the fix, Design steps 1–6, the comment at `:466-469`, and the table rebuilt.
- [ ] **T2:** the timeout block and AC6. The rows:
  - an AC1 127, followed by a validator cut off at a 3 s budget: the timeout block carries the line and the paragraph, and keeps its own header;
  - a validator that prints the AC1 line itself and exits 1, followed by the cut-off: no paragraph, and the block is `main`'s;
  - AC6, in both blocks: (a) a `PATH` entry holding a tab, `'`, `"`, `\`, `%s` and `é` (C3 A9), where the decoded `reason` holds the `PATH` exactly and stderr the raw bytes; (b) one holding a lone `\377`, built with `printf`, never typed, where the `reason` has U+FFFD at that place and stderr the raw byte. Both are checked as strict UTF-8, against the suite's `gbs_expect` decoder.
  Red first, then the timeout block's half, and the table rebuilt.
- [ ] **T3:** AC7. `init`'s sentence, item 5's report, the forty-third pin with its docstring, and both READMEs. Red: the pin fails before the sentence exists.
- [ ] **T4:** AC10, the real run on `agy`, in a fixture under `~/agent-work-dir/`.
  - **No install:** `agy plugin install` changes the machine-wide plugin set (A10), and the installed v0.41.0 stays as it is. The hooks file and the gates are copied into the fixture's `.agents/` by hand, in `init`'s layout: first `main`'s, then this branch's.
  - **The run:** headless, `--sandbox --mode accept-edits`, a trusted folder.
  - **Recorded from inside the hook:** a validator that writes the hook's `PATH` and `command -v npm` to a file.
  - **Nothing is pushed.**
- [ ] **T5:** the records for AC8 and AC10: `docs/fidelity.md`'s row, and `docs/verified.md`'s section from T4.
