# Spec: The fast check speaks each harness's protocol, and switching it off leaves the gates on

- Slug: 324-antigravity-fast-check-speaks-json   Issue: 324, with 330   Type: bug   Status: done
- Author: m0m0i (Claude Code)   Date: 2026-10-26

One spec for two issues, by the maintainer's decision at the twenty-sixth refinement: both are `hooks/templates/antigravity.hooks.json`, and #324's failure is what makes #330's edit likely. The pull request closes both. #324's triage asked to fold in the Claude Code template's fast check only if the spec rewrote both templates; `clarify` chose to, so it is the third subsection.

## 1. Requirements (WHAT / WHY)

### #324: the fast check's output breaks Antigravity's hook parser

- **Reproduction:**
  1. Render the template as `init` does (`skills/init/SKILL.md:72`), with a fast check that prints, for example `.venv/bin/ruff check .`.
  2. Run the rendered `PostToolUse` command with `.agents/` as cwd, as Antigravity does.
  3. Stdout carries `All checks passed!` or the diagnostics, not a JSON object. The matcher is `".*"` (`hooks/templates/antigravity.hooks.json:13`), so this happens after every tool call, reads included.
- **Expected:** stdout is exactly `{}`. Antigravity's hooks page says `PostToolUse` "Returns an empty JSON object `{}`". A13 (`docs/verified.md:505`) observed that stdout must be `{}`, and that the event is observe-only. The fast check runs only after a tool that writes a file. The Claude Code template already matches `Write|Edit` (`hooks/templates/claude-code.settings.json:13`).
- **Actual:** Antigravity fails to parse the hook's stdout on every tool call. In the field report, an agent cleared the error by replacing `.venv/bin/ruff` with a script that prints `{}` and exits 0. The project's quality gate then passed lint errors, because `quality-gate.sh` correctly trusted a validator made to lie, until the project's CI caught them.
- **Impact:** every Antigravity or dual-target install whose fast check writes to stdout, on every tool call. Triaged MEDIUM, high end, on 2026-10-21. No gate exits 0 because of the template, but the visible error pushes an agent into changing the toolchain the gates trust.
- **Root cause:** the template renders `cd … && {{FAST_CHECK}}` with the check's stdout as the hook's stdout. Antigravity reads hook stdout as the hook's JSON result. The `PostToolUse` entry was ported from the Claude Code template, where stdout on this event is ignored, and its matcher was widened to `".*"` with no Antigravity tool names to narrow it to. Nothing checks it:
  - `scripts/test-gates.sh`'s Antigravity `PostToolUse` case (section "Antigravity hook command execution", case 3) asserts only the working directory;
  - `scripts/check-manifests.py:265-274` checks only the entry's shape.

### #330: one `enabled` key switches off the fast check and both gates

- **Reproduction:**
  1. In a project `init` rendered, set `"enabled": false` in `.agents/hooks.json`'s `gate-sdd` group. Antigravity's hooks page documents this as the way to "disable the hook without removing it", and an agent quieting #324's noise has exactly that reason.
  2. Run `./assets/check-steering-anchors.sh`.
- **Expected:**
  - Switching off the fast check does not switch off the gates.
  - A project whose gates are switched off fails a check that says so. A missing `gate-lib.sh` already does: `assets/check-steering-anchors.sh:73-84`, "a guard that cannot do its job must not report success", #16.
- **Actual:**
  - The fast check, the steering digest and both `Stop` gates share one group and its one `enabled` key (`hooks/templates/antigravity.hooks.json:2-3`). With it false, no gate runs and nothing says so.
  - The anchor check reads `.agents/hooks.json` for `timeout`s only.
  - `scripts/check-manifests.py:259` and `:267` skip the key. They read only the template, never a project's file.
- **Impact:** every Antigravity or dual-target project. It needs a deliberate edit. The anchor's rule makes it BLOCKER-shaped once made, a gate that silently stops checking. #324 is what makes the edit likely.
- **Root cause:** the template puts every hook in one group named after the plugin, the shape the plugin-name envelope suggested. Antigravity's `enabled` belongs to a group, not to an entry; the hooks page shows `enabled` beside a group's events and several named groups in one file. So the noisy, harmless check and the two gates got one switch, and no reader of a project's hook file looks at it.

### #324's rider: Claude Code's fast check never reaches the model

- **Reproduction:**
  1. Render `hooks/templates/claude-code.settings.json` with a fast check that fails, for example `ruff check .` on a file with a lint error.
  2. Edit a file in a Claude Code session.
- **Expected:** the diagnostics reach the model after the edit. `docs/fidelity.md`'s "Per-edit feedback" row says Claude Code's is "`PostToolUse`, exit 2 to stderr". Claude Code's hooks page says a `PostToolUse` hook exiting 2 "Shows stderr to Claude; the tool already ran". It says "Exit code 1 without valid JSON output is a non-blocking error", and "Claude never sees stderr from a hook that exits 0".
- **Actual:** the template renders `{{FAST_CHECK}}` bare (`hooks/templates/claude-code.settings.json:15`). A linter exits 1, with its diagnostics on stdout. Claude Code writes stdout on this event to the debug log, and treats exit 1 as a non-blocking error. The model sees nothing, and the user sees at most a one-line notice.
- **Impact:** every Claude Code project with a fast check, on every edit. Nothing fails open: the quality gate still runs the `- Validators:` line at turn end. But the per-edit feedback the fidelity table claims does not exist.
- **Root cause:** the template passes the fast check's own exit code and stdout through as the hook's. Claude Code gives the model a hook's stderr only on exit 2, and linters exit 1 with their output on stdout.

### Acceptance criteria

- [ ] **AC1:** WHEN the rendered Antigravity `PostToolUse` command runs a fast check that prints to stdout and exits non-zero THE SYSTEM SHALL print exactly `{}` on stdout and exit 0, with the fast check's output on stderr. The same holds when the fast check is a compound command, or calls `exit`.
- [ ] **AC2:** WHEN Antigravity runs a tool that does not write a file THE SYSTEM SHALL run no fast check. The template's `PostToolUse` matcher is `write_file|edit_file|write_to_file|replace_file_content|multi_replace_file_content`. These are the write tools Antigravity CLI 1.4.7 calls (`write_file`, `edit_file`) and the ones its hooks page names (C6).
- [ ] **AC3:** WHEN `scripts/check-manifests.py` runs over an Antigravity template whose `PostToolUse` command lacks the envelope of AC1, or whose matcher is not the one in AC2, THE SYSTEM SHALL fail and name the entry.
- [ ] **AC4:** WHEN a project sets `"enabled": false` on the fast check THE SYSTEM SHALL keep both `Stop` gates and the steering digest running. The fast check is a named group of its own, `gate-sdd-fast-check`, in the rendered file. `gate-sdd` keeps the digest and both gates (C1).
- [ ] **AC5:** WHEN `check-steering-anchors.sh` runs in a project whose `.agents/hooks.json` turns off a group that runs `quality-gate.sh` or `review-gate.sh`, or runs only one of the two gates, THE SYSTEM SHALL fail and name the file and what is off (C4).
- [ ] **AC6:** WHEN this ships, these say what the code does:
  - `docs/fidelity.md`'s "Per-edit feedback" row, for both harnesses;
  - `docs/verified.md`'s A13;
  - `skills/init/SKILL.md:72`, on the stdout rule and the groups;
  - `hooks/templates/README.md`;
  - `AGENTS.md`'s layout table ("plugin-name envelope, `enabled` flag").
  - the "Per-edit fast feedback" row in `README.md` and `README.ja.md`, whose Antigravity cell said "full" for an event whose output reaches no model.
  That includes a sentence saying the quality pass's fingerprint does not cover the toolchain, so a pass recorded under a shimmed linter can outlive the shim.
- [ ] **AC7:** each regression case fails on `main` for the stated reason and passes after the fix.
- [ ] **AC8:** WHEN the rendered Claude Code `PostToolUse` command runs a fast check that fails THE SYSTEM SHALL exit 2 with the fast check's output, stdout and stderr both, on stderr. WHEN the fast check passes it SHALL exit 0. A compound fast check, or one that calls `exit`, behaves the same. `scripts/check-manifests.py` fails a Claude Code template whose `PostToolUse` command lacks that envelope.
- [ ] **AC9:** WHEN this ships THE SYSTEM SHALL have a recorded run on Antigravity CLI 1.4.7 in `docs/verified.md` (C2). It records whether:
  - a rendered file with the two named groups loads, and both gates still block;
  - `"enabled": false` on `gate-sdd-fast-check` leaves the gates firing;
  - the narrowed matcher runs the fast check after an edit and not after a read;
  - the wrapped command's `{}` raises no parse error.
  If the two-group file does not load, the spec stops, and AC4's mechanism goes back to the maintainer before anything ships.

### Out of scope

- **#302:** control bytes in `gate_block`'s JSON. It shares the stdout rule, not a file, and it is row 1's next spec.
- **Existing installs.** They get the new template by re-running `init`, which #343 defines and measures.
- **The fast check's output reaching the model on Antigravity.** `PostToolUse` is observe-only there (A13). The output goes to stderr and nowhere a model reads, and this spec does not claim otherwise.
- **A project's hand edit that puts the fast check back on stdout.** AC5 guards the gates, not the fast check's envelope.

### Clarifications

Asked and answered on 2026-10-26.

- **C1: how switching off the fast check stops switching off the gates.** Answer: **a group of its own.** The fast check moves to a named group, `gate-sdd-fast-check`, with its own `enabled`. `gate-sdd` keeps the digest and both `Stop` gates. Antigravity's hooks page shows several named groups in one file, each with an `enabled`. The alternative was one group and AC5's guard alone. It was not taken because quieting the fast check would still have turned the gates off, and the guard would only have said so afterwards. AC4 amended.
- **C2: probing the local Antigravity CLI 1.4.7 during implement.** Answer: **yes**, in a scratch trusted folder made with `mktemp -d`, recorded in `docs/verified.md`. The two-group file is the measurement that matters. If Antigravity rejected a file with two groups, the whole file would be invalid and every gate off. AC9 added.
- **C3: fold in the Claude Code template's bare fast check.** Answer: **fold it in.** It is a behaviour change on Claude Code: a failing fast check's output now reaches the model after every edit, as `docs/fidelity.md` already claims. The third subsection and AC8 added. The Claude Code matcher stays `Write|Edit`. Widening it to `NotebookEdit` is not asked for.
- **C4, decided here, not asked: which hook files AC5 judges.** Every `.agents/hooks.json` the anchor check already reads for `timeout`s (`assets/check-steering-anchors.sh:200-245`). A file that runs either gate must run both, and no group running one may be turned off. A file that runs neither passes. The anchor check cannot tell an Antigravity install whose `gate-sdd` group was deleted from a project that never installed for Antigravity, and failing the second would be a false block on every Claude Code project with Antigravity hooks of its own. That is a stated residual, like deleting the file itself.
- **C5, decided here, not asked: the steering digest stays in `gate-sdd`.** It is the gates' context, and a group of its own would add a third switch for nothing anyone asked to turn off.
- **C6, from T1's probe, asked and answered on 2026-10-26: AC2's matcher.** On Antigravity CLI 1.4.7 the file tools are `read_file`, `write_file` and `edit_file`, and there is no multi-edit tool. The hooks page's `write_to_file`, `replace_file_content` and `multi_replace_file_content` matched nothing, so the matcher AC2 first named would never have run the fast check. Answer: **both sets of names.** R5 measured that matcher: the fast check ran after `write_file` and `edit_file`, and not after `read_file`. The documented names stay in case a later CLI uses them. AC2 and the Design's template amended.

## 2. Design (HOW)

### Fix approach

**The two templates.** Each wraps the fast check in a subshell, so a compound check or one that calls `exit` ends only the subshell. Each sends both of its streams to stderr, and then answers in its own harness's protocol:

- **Antigravity**, in a group of its own (C1). The `gate-sdd` group keeps `enabled`, `PreInvocation` and both `Stop` entries, unchanged:

  ```json
  "gate-sdd-fast-check": {
    "enabled": true,
    "PostToolUse": [
      {
        "matcher": "write_file|edit_file|write_to_file|replace_file_content|multi_replace_file_content",
        "hooks": [
          {
            "type": "command",
            "command": "cd \"$(git rev-parse --show-toplevel 2>/dev/null || pwd)\" && ( {{FAST_CHECK}} ) 1>&2; echo '{}'",
            "timeout": 60
          }
        ]
      }
    ]
  }
  ```

  `echo '{}'` follows `;`, so it runs whether the `cd` or the check fails, and the hook exits 0. Antigravity reads nothing from a `PostToolUse` exit code (A13).
- **Claude Code**: `( {{FAST_CHECK}} ) 1>&2 || exit 2`. Exit 2 is the only code whose stderr Claude Code gives the model on this event. A passing check exits 0, and its stderr is never shown. The matcher stays `Write|Edit` (C3).

Not taken: routing the fast check through `gate-lib.sh`. The triage rejected it because block and pass mean nothing on an event that cannot block, and the fast check is not a gate.

**`scripts/check-manifests.py`** reads the Antigravity template as groups rather than as one envelope named after the plugin:

- Events and entry shapes are read across every group. The gate pairing still compares the plugin's `Stop` and the `gate-sdd` group's.
- New rules (AC3, AC8):
  - the template holds exactly the groups `gate-sdd` and `gate-sdd-fast-check`, each with `"enabled": true`;
  - `PostToolUse` is only in `gate-sdd-fast-check`, which holds nothing else;
  - its matcher is AC2's;
  - its command is the cwd prefix followed by `( {{FAST_CHECK}} ) 1>&2; echo '{}'`;
  - the Claude Code template's `PostToolUse` command is exactly `( {{FAST_CHECK}} ) 1>&2 || exit 2`.
- Each failure names the template and the entry, like the existing shape errors.

**`gate_hook_switches <file>`** in `hooks/gate-lib.sh` (AC5, C4) reads one hook file and prints a line for each thing that is off:

- a group whose `enabled` is present and not literally `true`, while a command in it names `quality-gate.sh` or `review-gate.sh`;
- a file where enabled groups run one of the two gates and not the other.

It reuses `gate_hook_timeout`'s byte-level JSON walk, the same tokenizer and the same command-name match. It tracks the group a value sits in, at depth 1, and the group's `enabled`, at depth 2. It returns 0 when nothing is off, 1 when something is, and 2 when the file is unreadable or does not parse. It prints the reason in every case. `enabled` read fail-closed: `false`, `"false"`, `0` and `null` all count as off. Only an absent key or `true` counts as on, so a value whose meaning to Antigravity is unknown is never read as a running gate.

**`assets/check-steering-anchors.sh`** calls it for each `.agents/hooks.json` in the set it already reads for `timeout`s, and adds each line to `failed`, naming the file. It adds the function to the library guard loop at `:102`, so an old `gate-lib.sh` fails with the guard's remedy and not with exit 127. #323's review found that gap for the review gate.

**Docs (AC6).**
- `docs/fidelity.md` "Per-edit feedback": Claude Code exit 2 to stderr, now true; Antigravity observe-only, in a group of its own, `{}` on stdout.
- `docs/verified.md` A13 gains a line pointing at AC9's run.
- `skills/init/SKILL.md:72` states the stdout rule and the two groups, and that only `gate-sdd-fast-check` may be switched off.
- `hooks/templates/README.md` describes the groups.
- `AGENTS.md`'s table reads "plugin-named groups, each with its `enabled` flag".
- The fingerprint sentence goes beside `qg_fingerprint` in `hooks/quality-gate.sh`, the one place that defines what the fingerprint covers.

**The probe (AC9, C2)** runs first, before any code, on a hand-rendered file in a `mktemp -d` project trusted in Antigravity CLI 1.4.7. It checks the two groups loading, both gates blocking, `enabled: false` on the fast-check group only, the matcher (an edit against a read), and `{}` raising no parse error in `agy.log`. If the two-group file does not load, implementation stops there.

### Affected files

- `hooks/templates/antigravity.hooks.json`, `hooks/templates/claude-code.settings.json`
- `hooks/gate-lib.sh` (`gate_hook_switches`), `hooks/quality-gate.sh` (comment only)
- `assets/check-steering-anchors.sh`
- `scripts/check-manifests.py`
- `scripts/test-gates.sh`: cases 377 onward; `agy_get_cmd` finds an event in whichever group holds it
- `docs/fidelity.md`, `docs/verified.md`, `skills/init/SKILL.md`, `hooks/templates/README.md`, `AGENTS.md`
- `plugin.json`, `.claude-plugin/plugin.json`: 0.37.0, after the receipt. Minor: a behaviour change in both rendered templates and a new failure in a copied guard.

### Blast radius

- **Readers of a project's `.agents/hooks.json`.** `gate_hook_timeout`, in both gates and in the anchor check, finds a gate's entry by the script its command names, at any depth. A second group changes nothing for it, and the fast check's 60 s `timeout` names no gate, so it lowers no gate's deadline. Case 377's file also goes through `gate_hook_timeout` to show this.
- **Installed projects.** They keep their one-group file until `init` re-runs (#343). The anchor check's new rule passes that file, `enabled` true with both gates, so the upgrade is not forced by a false block.
- **Claude Code sessions.** A failing fast check now reaches the model after every `Write` or `Edit`. That is the per-edit feedback the fidelity table claims. Mid-change, an edit that leaves a type error is told about it, which is the fast check's purpose. The quality gate is untouched.
- **`test-gates.sh` fixtures** that write their own `{"gate-sdd": …}` files are unaffected: AC5's rule passes a group that runs both gates.
- **The quality gate's fingerprint** hashes `gate-lib.sh`, so the new function forces one validator run in every project after the update. That fails closed.

### Why this cannot recur

- `test-gates.sh` runs each rendered `PostToolUse` command as its harness would, with a fast check that prints and fails. It asserts the bytes on stdout and the exit code, not the command's text.
- `check-manifests.py` pins the envelopes, the matcher and the groups in both templates.
- The anchor check reads a project's switches, so a gate switched off with an `enabled` key no longer passes every check.

## 3. Tasks (TDD-ordered)

> One task is one complete Red-Green-Refactor cycle, so one green commit. No task is sequenced after the review.

- [x] T1: **Probe (AC9).** On Antigravity CLI 1.4.7, in a trusted `mktemp -d` project, load a hand-rendered two-group file and record each AC9 item in `docs/verified.md`. Stop if the file does not load.
- [x] T2: **Antigravity envelope, matcher and group (AC1, AC2, AC4).**
  - Red: case 377 renders the template with a fast check that prints and exits 1, runs the `PostToolUse` command from `.agents/`, and expects stdout `{}` and exit 0. It fails on `main` because stdout carries the check's output. Case 378 does the same with `exit 3` inside a compound check.
  - Green: change the template.
  - In the same commit, so that it stays green: `agy_get_cmd` and the existing working-directory case read the new group, and `check-manifests.py` reads events and shapes across groups.
- [x] T3: **`check-manifests.py` pins the Antigravity template (AC3).**
  - Red: cases 379 to 382 mutate a copy of the template: the matcher widened to `.*`, the envelope dropped, `PostToolUse` moved back into `gate-sdd`, and `enabled` false on a group. Each expects exit 1 and an error naming the entry.
  - Green: the rules.
- [x] T4: **The Claude Code envelope (AC8).**
  - Red: case 383 runs the rendered Claude Code command with a fast check that prints and exits 1, expecting exit 2, the output on stderr and an empty stdout. A passing check exits 0. Case 384 mutates the template back to a bare check and expects `check-manifests.py` to fail.
  - Green: change the template and add the rule.
- [x] T5: **The anchor check reads the switches (AC5).**
  - Red: cases 385 to 390, each a project file:
    - `enabled: false` on `gate-sdd`: fails;
    - `"enabled": "false"`: fails;
    - `review-gate.sh` removed: fails;
    - `enabled: false` on `gate-sdd-fast-check` only: passes;
    - a file running neither gate: passes;
    - an old `gate-lib.sh` without the function: fails with the guard's remedy.
  - Green: `gate_hook_switches` and the anchor check's call and guard.
- [x] T6: **Docs (AC6).** The docs listed in Design and the fingerprint comment. Every validator passes.

The 0.37.0 bump is not a task. It lands after the receipt, as `implement` step 5 says (#113).
