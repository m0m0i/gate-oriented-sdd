# What to check on Antigravity — 2026-10-11

The run sheet for the Antigravity findings in [`2026-10-11-deep-review.md`](./2026-10-11-deep-review.md). The review established most of these by reading the agy and IDE binaries and by headless `agy` runs under a throwaway `HOME`; **none was observed in an interactive session**, which is what this sheet is for. Each check says what the review expects, so a different result is a finding rather than noise. Results go to `docs/verified.md` (method, versions, outcome — including "not exercised") and, where a row changes, `docs/fidelity.md`.

## Setup

1. Record versions: `agy --version` and the IDE's About box. The review saw CLI 1.3.3 and IDE 2.17.0; the ledger still says 1.2.16 and 2.3.1.
2. A scratch git repository with `init` run in Antigravity mode, so `.agents/hooks.json` and `.agents/hooks/` exist. **Trust the folder** — workspace hooks load only in a trusted folder, and an untrusted one silently loads none (`verified.md`, "Antigravity hooks").
3. A probe that records what a hook receives. Save as `.agents/hooks/probe.sh` and add it as an extra entry under the event being checked:

   ```sh
   #!/bin/sh
   # Usage: sh .agents/hooks/probe.sh <event>  — appends the event, cwd, exit-relevant env and stdin to /tmp/agy-probe.log
   { printf '=== %s %s cwd=%s conv=%s\n' "$1" "$(date +%T)" "$(pwd)" "${ANTIGRAVITY_CONVERSATION_ID:-unset}"; cat; printf '\n'; } >>/tmp/agy-probe.log
   printf '{}\n'
   ```

4. Know where agy logs. Grep its log directory for `loaded N named hooks` (the hooks file loaded), `failed to call custom stop hook` (a hook counted as failed) and `jsonhook__gate-sdd`.

## Checks

| # | Check | How | Review expects | Closes or feeds |
| :-- | :-- | :-- | :-- | :-- |
| A1 | **Does a gate block at all?** | On branch `9-probe`, add `.specs/9-probe/spec.md` with every task ticked and no `.review-receipt`; end a turn. | The turn ends. agy logs `failed to call custom stop hook … exit status 2`, and the model never sees the reason. | Deep review §1.2; `fidelity.md` "verified — both block" |
| A2 | **Does exit 0 plus JSON block?** | Same fixture, with `\|\| true` appended to both Stop commands in `.agents/hooks.json`. | The agent re-enters the loop and acts on the reason. Confirm which `decision` values are honoured: `continue`, and whether `block` is too. | The fix: exit 0 under Antigravity, keyed on `ANTIGRAVITY_CONVERSATION_ID` or a template variable; G-3's wording |
| A3 | Is `ANTIGRAVITY_CONVERSATION_ID` set in a hook's environment? | The probe's `conv=` field on a Stop entry. | Set. | Whether the gate can detect the harness itself |
| A4 | **The Stop continuation cap** | A Stop hook that always prints `{"decision":"continue","reason":"probe"}` and exits 0; count the continuations before the turn ends. | 10 by default (`max_stop_hook_continuations`); after that the turn ends as a pass. Find where the setting lives. | `fidelity.md` row for the cap; why the review gate must stay clearable in far fewer turns |
| A5 | **A Stop hook that outlives its timeout** | A Stop entry `sleep 40; printf '{"decision":"continue","reason":"late"}'` with `"timeout": 30`. | Killed, result discarded, turn ends — a fail-open. | Deep review §1.7; an in-gate deadline |
| A6 | **When the steering digest arrives** | Probe on `PreInvocation`; start a new conversation; read `invocationNum` on the first call. Ask the model on its first turn whether it has a `## Repo facts` block. | The first call carries `invocationNum: 0`, and the digest arrives on the second call (the script waits for `== 1`). | `steering-digest-antigravity.sh`; the "verified — both deliver digest" cell |
| A7 | Does `initialNumSteps` fall at a compaction? | Same probe through a long conversation until it compacts. | Unverified. If it falls, the documented compaction gap closes through `PreInvocation` state keyed by `conversationId`. | `fidelity.md` "The one real gap" |
| A8 | **Does the installed reviewer register?** | `agy agents` in the fixture, with `.agents/agents/<name>.md` as `init` writes it (`tools: Read, Grep, Glob, Bash`), then a copy with a YAML list (`tools: [Read, Grep, Glob, Bash]`). | The string form is dropped silently; the list form registers. Then check which tool names grant anything — Antigravity's are `view_file`, `grep_search`, `run_command`, not Claude Code's. | `verified.md` Still to verify: the subagent contract and `.agents/agents/` |
| A9 | Can the registered reviewer read its contract and rules? | Invoke it on the fixture and watch which paths it opens. | Unknown. The shipped reviewers name their rulebook and lock by relative paths that resolve to nothing from the project root. | The reviewer file's paths |
| A10 | **Does the plugin's `rules/AGENTS.md` reach a consumer session?** | Install the plugin, open an unrelated project, ask the model what rules it has loaded, or look for this repository's contributor text. | Yes, as an always-on rule: `AGENTS.md` is exempt from the rules frontmatter requirement, so this repository's contributor guide is in every consumer's session. | `fidelity.md` "Rules discovery"; #240; split the two audiences |
| A11 | Where `agy plugin install` puts a plugin | Install from a local path; look under `~/.gemini/config/plugins/` and `~/.gemini/antigravity-cli/plugins/`. | Unknown. | `verified.md` Still to verify |
| A12 | Does a **plugin-shipped** `hooks.json` fire, with what cwd and stdin? | A throwaway plugin whose `hooks.json` runs the probe on Stop and PreInvocation. | It fires, with the plugin directory as cwd and `workspacePaths` on stdin. | Whether the Antigravity gates could ship from the plugin and stop being copied (ADR-8's Antigravity half) |
| A13 | The fast check after every tool call | Time a few tool calls with and without the `PostToolUse` entry; check its stdout is only `{}`. | Synchronous on every tool call, observe-only, and it shares one `enabled` switch with both gates. | Drop or narrow the entry |
| A14 | A block reason with control characters | After A2's fix, make the failing validator print a tab or a colour code. | The JSON is invalid, so the block is lost: `_gate_json_escape` escapes only `\`, `"` and newline. | `gate-lib.sh` escaping; a case that parses every block's JSON |

Only on a Windows machine: agy runs hook commands with `cmd /c`, so the POSIX commands `init` renders cannot run there. Record it as not exercised otherwise.

## When the sheet is done

- Every row gets an outcome in `docs/verified.md`, under the versions from setup step 1: observed, not reproduced, or not exercised.
- `docs/fidelity.md` stops saying "verified" for any cell A1, A6 or A10 contradicts.
- A1 and A2 together decide the first fix; nothing else here matters while no gate blocks.
