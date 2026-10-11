# Spec: Gates fail open on exit code 2 and unescaped control characters in Antigravity
- Slug: 282-antigravity-gate-fail-open   Issue: 282   Type: bug   Status: approved
- Author: Hiroyuki Momoi   Date: 2026-10-11

## 1. Requirements (WHAT / WHY)

- Reproduction: three distinct fail-open defects on Antigravity:
  1. **Non-zero exit fails open on Stop hook:** In an Antigravity workspace with `.agents/hooks.json` running `quality-gate.sh` or `review-gate.sh` on `Stop`, trigger a gate block (e.g. on a spec branch, tick all tasks with no `.review-receipt`). End a turn in `agy -p`. `gate_block` prints JSON on stdout and exits 2. `agy` logs `failed to call custom stop hook ... exit status 2`, discards hook stdout, and terminates the turn successfully (`status: SUCCESS`).
  2. **Unescaped control characters break JSON unmarshaling:** In an Antigravity workspace where a gate exits 0, if a failing validator or diff emits a horizontal tab (`\t`) or carriage return (`\r`), `_gate_json_escape` leaves it unescaped. `agy` fails to parse hook stdout with `protojson: proto: syntax error: invalid character '\t' in string`, discards the hook result, and ends the turn (fails open).
  3. **Steering digest skips initial turn:** On the first model invocation of a session, Antigravity sends `{"invocationNum": 0}` to `PreInvocation`. `hooks/steering-digest-antigravity.sh` checks `data.get("invocationNum") != 1` and exits with `{}`, delivering no digest on turn 0.

- Expected:
  - When `gate_block` blocks under Antigravity, it SHALL emit `{"decision":"continue","reason":"..."}` on stdout and exit 0, causing `agy` to block turn termination and pass the reason to the model.
  - When `gate_block` blocks under Claude Code, it SHALL emit the JSON on stdout, the message on stderr, and exit 2, preserving Claude Code's blocking protocol.
  - `_gate_json_escape` SHALL escape tabs (`\t`), carriage returns (`\r`), newlines (`\n`), backslashes (`\\`), and double quotes (`\"`) so that hook output is valid RFC 8259 JSON acceptable to `protojson`.
  - `hooks/steering-digest-antigravity.sh` SHALL deliver the steering digest on turn 0 (`invocationNum == 0`) and emit `{}` on all subsequent turns (`invocationNum > 0`).

- Actual:
  - `gate_block` unconditionally exits 2, failing open on Antigravity across 100% of sessions.
  - `_gate_json_escape` only escapes `\` and `"`, leaving tabs unescaped and failing open on any validator output containing tabs.
  - `steering-digest-antigravity.sh` checks for `invocationNum == 1`, skipping turn 0.

- Impact:
  - Every Antigravity session. Currently no gate blocks on Antigravity, completely disarming SDD enforcement (CAP-1, CAP-2) and violating the repository anchor `- Owns: gates never fail open` (`.steering/product.md`).

- **Root cause:**
  - `hooks/gate-lib.sh:28`: `gate_block` unconditionally exits 2. The author assumed Antigravity would inspect stdout regardless of exit code; in reality `agy` treats any non-zero exit code as an execution failure and discards stdout.
  - `hooks/gate-lib.sh:20`: `_gate_json_escape` uses `sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' | awk 'BEGIN{ORS=""} {print sep $0; sep="\\n"}'`, which does not escape `\t`, `\r`, or other control characters.
  - `hooks/steering-digest-antigravity.sh:35`: checks `data.get("invocationNum") != 1` based on an assumed 1-indexed turn counter, whereas Antigravity's `invocationNum` is 0-indexed and starts at 0.

- Acceptance criteria:
  - [ ] **AC1:** WHEN `gate_block` is called in an Antigravity environment (`ANTIGRAVITY_CONVERSATION_ID` or `ANTIGRAVITY_AGENT` is non-empty), THE SYSTEM SHALL emit `{"decision":"continue","reason":"..."}` on stdout and exit 0.
  - [ ] **AC2:** WHEN `gate_block` is called in an environment without Antigravity variables (Claude Code), THE SYSTEM SHALL emit the JSON on stdout, the message on stderr, and exit 2.
  - [ ] **AC3:** WHEN `gate_block` is given a reason string containing horizontal tabs, carriage returns, newlines, double quotes, or backslashes, THE SYSTEM SHALL output strictly valid JSON whose unmarshaled `reason` matches the input message.
  - [ ] **AC4:** WHEN `hooks/steering-digest-antigravity.sh` receives `{"invocationNum": 0}`, THE SYSTEM SHALL execute `steering-digest.sh` and emit `{"injectSteps": [{"ephemeralMessage": "<digest>"}]}` on stdout; and for `{"invocationNum": N}` where N > 0, it SHALL emit `{}` and exit 0.
  - [ ] **AC5:** Regression tests for AC1, AC2, AC3, and AC4 in `scripts/test-gates.sh` fail before the fix and pass after.

- Out of scope:
  - Context re-injection after compaction on Antigravity (no hook event exists; documented in `docs/fidelity.md`).
  - Antigravity IDE (discontinued; removed from target matrix).
  - Uncommitted source change skip in `hooks/quality-gate.sh` (tracked separately).
  - Plugin-shipped hooks layout migration (ADR-8 / A12).

### Clarifications

Asked and answered 2026-10-11:
- **Q1 — How should `gate_block` and `_gate_bootstrap_block` detect Antigravity to exit 0 while preserving Claude Code's exit 2?**
  **A: Check `[ -n "${ANTIGRAVITY_CONVERSATION_ID:-}" ] || [ -n "${ANTIGRAVITY_AGENT:-}" ]` in both `gate_block` and `_gate_bootstrap_block`.** In Antigravity CLI and agents, both variables are present in hook environments. If either is set, exit 0. If neither is set, retain exit 2 for Claude Code.
- **Q2 — What character set should `_gate_json_escape` handle to prevent protojson unmarshal errors?**
  **A: Escape backslash (`\\`), double-quote (`\"`), newline (`\n`), tab (`\t`), and carriage return (`\r`).** Handled in POSIX `awk` with `gsub`, producing valid RFC 8259 JSON without spawning extra subprocesses.
- **Q3 — Should `steering-digest-antigravity.sh` trigger strictly on `invocationNum == 0`?**
  **A: Yes, check `data.get("invocationNum") == 0`.** Antigravity sends 0 on the initial invocation. Subsequent continuation turns send N > 0 and receive `{}` with exit 0.

## 2. Design (HOW)

- Fix approach, and why this rather than the narrower or wider fix:
  - **Exit code under Antigravity:** Rather than wrapping commands in template JSON with `|| true` (which would mask genuine crashes and fail open), `gate_block` in `hooks/gate-lib.sh` and `_gate_bootstrap_block` in `hooks/quality-gate.sh` and `hooks/review-gate.sh` detect Antigravity via `[ -n "${ANTIGRAVITY_CONVERSATION_ID:-}" ] || [ -n "${ANTIGRAVITY_AGENT:-}" ]`. If set, they exit 0. If absent, they exit 2. This keeps the bootstrap guards byte-identical and preserves parity.
  - **Control character escaping:** Replace the `sed | awk` pipeline in `_gate_json_escape` with a unified POSIX `awk` script that escapes `\\`, `\"`, `\r`, `\t`, and joins newlines as `\n`. This handles multi-line compiler errors, test failure diffs with tabs, and CRLF outputs cleanly.
  - **Steering digest turn 0:** Update `hooks/steering-digest-antigravity.sh` line 35 to inspect `data.get("invocationNum") != 0`, triggering execution on `invocationNum == 0`.
- Affected files:
  - `hooks/gate-lib.sh` — `gate_block` exit code switch and `_gate_json_escape` escaping.
  - `hooks/quality-gate.sh` — `_gate_bootstrap_block` exit code switch matching `gate_block`.
  - `hooks/review-gate.sh` — `_gate_bootstrap_block` exit code switch matching `gate_block`.
  - `hooks/steering-digest-antigravity.sh` — turn 0 filter (`invocationNum == 0`).
  - `scripts/test-gates.sh` — regression test cases for Antigravity exit 0, Claude Code exit 2, tab/CR escaping, bootstrap guard parity, and digest turn 0.
  - `docs/fidelity.md` — update Antigravity blocking gate status to verified/fixed.
- **Blast radius:**
  - `gate_block` is called whenever any validator fails or review is missing. In Claude Code sessions, `ANTIGRAVITY_*` is unset, so exit 2 is preserved with zero change in behavior.
  - In Antigravity sessions, `gate_block` previously exited 2 (discarded by `agy`); exiting 0 with JSON `{"decision":"continue","reason":"..."}` enables turn-blocking as intended.
  - The bootstrap region in `quality-gate.sh` and `review-gate.sh` is byte-compared in `scripts/test-gates.sh` case 201; both files and the extracted library function must stay in sync.
- Why this cannot recur:
  - `scripts/test-gates.sh` tests both channels (exit 0 under `ANTIGRAVITY_AGENT=1`, exit 2 under clean env), unmarshals the JSON through Python `json.loads` to prove validity, and verifies that the bootstrap guard matches `gate_block` under both harness environments.

## 3. Tasks (TDD-ordered)

> One task is one complete Red-Green-Refactor cycle, so one green commit. No task is sequenced after the review.

- [x] T1: regression tests for Antigravity exit 0, Claude Code exit 2, and control character escaping (tabs and carriage returns) — then the fix in `hooks/gate-lib.sh` and bootstrap guards in `hooks/quality-gate.sh` and `hooks/review-gate.sh`
- [ ] T2: regression test for `steering-digest-antigravity.sh` turn-0 delivery vs turn-1 suppression — then the fix in `hooks/steering-digest-antigravity.sh`
- [ ] T3: test coverage for dual-target bootstrap guard parity across both harnesses — then docs and fidelity alignment
