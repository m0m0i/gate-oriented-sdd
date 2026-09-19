# Spec: Support steering digest on Antigravity via PreInvocation hook
- Slug: 144-support-steering-digest-on-antigravity   Issue: 144   Type: feature   Status: approved
- Author: Hiroyuki   Date: 2026-09-19

## 1. Requirements (WHAT / WHY)

### User story
As an Antigravity plugin user running `gate-sdd`,  
I want the steering digest (`## Repo facts`, quality anchor, and invariants) injected into the agent session on turn 1 via the `PreInvocation` hook,  
So that Antigravity sessions start with the same quality anchors, persistent context pointers, and workflow rules as Claude Code sessions without re-injecting and wasting tokens on subsequent turns.

### Serves
CAP-2 (Enforcement the project defines, not the hook) and CAP-4 (Installation into a repository that already has opinions) across dual targets without fidelity loss.

### Acceptance criteria
- [ ] **AC1:** WHEN Antigravity invokes `PreInvocation` on turn 1 (`stdin` has `{"invocationNum": 1}`), THE SYSTEM SHALL emit valid JSON on stdout `{"injectSteps": [{"ephemeralMessage": "<steering digest content>"}]}` containing the output of `hooks/steering-digest.sh`, and exit with code 0.
- [ ] **AC2:** WHEN Antigravity invokes `PreInvocation` on subsequent turns (`invocationNum > 1`) or without `invocationNum == 1`, THE SYSTEM SHALL emit `{}` on stdout and exit with code 0.
- [ ] **AC3:** WHEN `stdin` is empty, malformed JSON, or missing `invocationNum`, THE SYSTEM SHALL fail closed by emitting `{}` on stdout and exit with code 0, never emitting malformed JSON or unhandled errors.
- [ ] **AC4:** WHEN `.steering/` directory is missing or empty, THE SYSTEM SHALL emit valid JSON containing the fallback digest output from `hooks/steering-digest.sh` on turn 1, and `{}` on subsequent turns, with exit code 0.
- [ ] **AC5:** WHEN invoked from a subdirectory (such as `.agents/`), THE SYSTEM SHALL anchor to the git repository root so that `.steering/` and git status resolve correctly.
- [ ] **AC6:** WHEN `scripts/check-manifests.py` validates hook templates, THE SYSTEM SHALL verify that `hooks/templates/antigravity.hooks.json` registers `PreInvocation` in flat `{type, command}` form, and that Claude Code's `SessionStart` pairs with Antigravity's `PreInvocation` for steering digest injection, failing closed if either is missing or misformed.
- [ ] **AC7:** WHEN `scripts/test-gates.sh` runs, THE SYSTEM SHALL include test cases verifying:
  1. `invocationNum == 1` emits valid JSON with `injectSteps` and `ephemeralMessage` containing the digest and exits 0.
  2. `invocationNum > 1` (e.g. 2) emits `{}` and exits 0.
  3. Missing / empty / malformed stdin emits `{}` and exits 0.
  4. Invocation from a subdirectory resolves repository root facts.
  5. Missing `.steering/` emits valid JSON digest and exits 0.
  6. `check-manifests.py` catches missing or misconfigured `PreInvocation` in `antigravity.hooks.json`.
- [ ] **AC8:** WHEN `docs/fidelity.md` and `AGENTS.md` describe the harness fidelity, THE SYSTEM SHALL document that the steering digest gap is closed on Antigravity via `PreInvocation` step injection on turn 1 (`invocationNum == 1`).

### Out of scope
- Re-injecting steering digest after context truncation or compaction mid-session on Antigravity (Antigravity currently has no compaction lifecycle hook event).
- Changing Claude Code `SessionStart` behavior.

### Clarifications
2026-09-19, from `clarify`:

- **C1 — Script separation**:
  `hooks/steering-digest.sh` remains the canonical plain-text digest generator. `hooks/steering-digest-antigravity.sh` handles Antigravity stdin/stdout JSON protocol and delegates to `steering-digest.sh`.
- **C2 — Parsing and Escaping via Python 3**:
  `hooks/steering-digest-antigravity.sh` executes Python 3 stdlib to parse JSON and serialize `{"injectSteps": [{"ephemeralMessage": ...}]}`. Any exception defaults safely to `{}` and exits 0.
- **C3 — Defense in depth cwd anchoring**:
  Both the command in `antigravity.hooks.json` (`cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"; ...`) and `hooks/steering-digest-antigravity.sh` anchor to the repository root.
- **C4 — Manifest check pairing**:
  `scripts/check-manifests.py` pairs Claude Code `SessionStart` with Antigravity `PreInvocation` and checks that neither template drops its steering digest hook.
- **C5 — Version bump**:
  Post-review during `implement`, version moves from `0.11.0` to `0.12.0` in `plugin.json` and `.claude-plugin/plugin.json`.

## 2. Design (HOW)

### Key technical decisions
- **Dedicated Adapter Script (`hooks/steering-digest-antigravity.sh`)**:
  Separates JSON protocol handling from plain-text digest generation. `hooks/steering-digest.sh` remains testable and runnable directly in the terminal without stdin overhead.
- **Fail-Closed JSON Handling via Python 3**:
  `hooks/steering-digest-antigravity.sh` invokes `python3 -c ...` to parse `stdin`. If `invocationNum == 1`, it executes `hooks/steering-digest.sh` via subprocess, escapes and wraps stdout into `json.dumps({"injectSteps": [{"ephemeralMessage": digest}]})`. If `invocationNum != 1` or if stdin cannot be parsed, it emits `{}` and exits 0.
- **Hook Template Registration**:
  In `hooks/templates/antigravity.hooks.json`, register `PreInvocation` as a non-tool hook (flat schema with `type: "command"`, `command`, `timeout: 15`).
- **Strict Manifest Verification**:
  In `scripts/check-manifests.py`, ensure `SessionStart` in `claude-code.settings.json` corresponds to `PreInvocation` in `antigravity.hooks.json`. Missing either hook or failing to use flat format in Antigravity fails closed.
- **Documentation Alignment**:
  Update `docs/fidelity.md` and `AGENTS.md` to reflect that the `SessionStart` steering digest gap is closed via `PreInvocation` on turn 1.

### Affected modules and files
- `hooks/steering-digest-antigravity.sh` (new, shipped)
- `hooks/templates/antigravity.hooks.json` (modified, shipped template)
- `scripts/check-manifests.py` (modified, validator)
- `scripts/test-gates.sh` (modified, test suite)
- `docs/fidelity.md` (modified, documentation)
- `AGENTS.md` (modified, canonical context)
- `skills/init/SKILL.md` (modified, skill)

### Contract changes, and who else consumes them
Antigravity plugin installations will now execute `PreInvocation` on turn 1 to receive the steering digest. No breaking changes to existing contracts or Claude Code configuration.

### Risks and trade-offs
- Antigravity `PreInvocation` runs before every invocation. Checking `invocationNum == 1` and exiting with `{}` in <10ms for turns > 1 ensures minimal overhead during interactive sessions.
- In the absence of a session compaction hook on Antigravity, re-injection after context truncation remains limited to session start (`invocationNum == 1`), which is accurately documented in `docs/fidelity.md`.

## 3. Tasks (TDD-ordered)

> One task is one complete Red-Green-Refactor cycle, so one green commit. No task is sequenced after the review.

- [x] T1: failing test for Antigravity steering digest script in `scripts/test-gates.sh` — then implementation in `hooks/steering-digest-antigravity.sh`
- [x] T2: failing test for `check-manifests.py` verifying `PreInvocation` in `antigravity.hooks.json` — then implementation in `hooks/templates/antigravity.hooks.json` and `scripts/check-manifests.py`
- [x] T3: update documentation (`docs/fidelity.md`, `AGENTS.md`), skill (`skills/init/SKILL.md`), and verify all validators pass cleanly
