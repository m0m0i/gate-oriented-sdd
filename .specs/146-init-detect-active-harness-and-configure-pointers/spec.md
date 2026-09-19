# Spec: Detect active harness and configure rule pointers and contracts accordingly
- Slug: 146-init-detect-active-harness-and-configure-pointers   Issue: 146   Type: feature   Status: approved
- Author: Hiroyuki   Date: 2026-09-19

## 1. Requirements (WHAT / WHY)

### User story
As an agent or operator running `init` in a project,
I want `init` to automatically detect the active agent harness (Claude Code, Antigravity, or both) from filesystem markers and runtime environment signals (or confirm via an interview if ambiguous),
So that the appropriate canonical rule pointers (`CLAUDE.md`, `GEMINI.md`, or both pointing to `AGENTS.md`), reviewer contract placement (`.claude/agents/_shared/` vs `.agents/agents/_shared/`), and hooks (`.claude/settings.json` vs `.agents/hooks.json`) are configured without manual intervention or platform clutter.

### Serves
Dual-target parity: automated harness detection, proper rule pointer generation, and consistent reviewer contract placement across Claude Code and Google Antigravity (#146).

### Acceptance criteria
- [ ] **AC1 (Step 1 Detection)**: WHEN `init` runs in Step 1 THE SYSTEM SHALL inspect:
  (a) Filesystem markers: `.claude/` or `CLAUDE.md` -> Claude Code targeted; `.agents/` or `GEMINI.md` -> Antigravity targeted. If both present -> Dual-target project.
  (b) Runtime environment signals: environment variables (`CLAUDE_CODE`, `ANTIGRAVITY`) or agent tool availability.
  If signals are unambiguous, proceed with the detected target harness(es) without asking.
- [ ] **AC2 (Step 2 Interview)**: WHEN target harness signals are ambiguous or neither harness is detected THE SYSTEM SHALL prompt the operator:
  `"Which harness(es) should this project configure? [1] Claude Code, [2] Antigravity, [3] Both"`
- [ ] **AC3 (Step 3 Rule Pointers)**: WHEN scaffolding rule files THE SYSTEM SHALL always create canonical `AGENTS.md` and configure pointers:
  - Claude Code: create `CLAUDE.md` referencing `AGENTS.md`.
  - Antigravity: create `GEMINI.md` referencing `AGENTS.md`.
  - Dual: create both pointer files.
- [ ] **AC4 (Step 3 Reviewers & Hooks)**: WHEN scaffolding reviewers and hooks THE SYSTEM SHALL configure the directory matching the chosen harness(es):
  - Claude Code: `.claude/settings.json`, `.claude/hooks/`, and `.claude/agents/_shared/reviewer-contract.md`.
  - Antigravity: `.agents/hooks.json`, `.agents/hooks/`, and `.agents/agents/_shared/reviewer-contract.md` (aligning with `check-locks.py` candidate directory `.agents/agents`).
- [ ] **AC5 (Contract Pinning)**: WHEN `scripts/check-skill-contracts.py` runs THE SYSTEM SHALL verify that `skills/init/SKILL.md` contains the harness interview question and the pointer instruction, failing closed if either is missing, with the total contract count moved from 21 to 23 and justified in the docstring.
- [ ] **AC6 (Guard Tests)**: WHEN `scripts/test-gates.sh` runs THE SYSTEM SHALL include guard tests confirming `scripts/check-skill-contracts.py` fails if `skills/init/SKILL.md` is stripped of the harness interview question or pointer instructions.
- [ ] **AC7 (Documentation)**: WHEN `docs/fidelity.md` and `docs/layout.md` are inspected THE SYSTEM SHALL document the active harness detection logic, `CLAUDE.md`/`GEMINI.md` rule pointers, and `.agents/agents/_shared/reviewer-contract.md` structure.

### Out of scope
- Automatic platform installation or CLI bootstrapping outside the repository.
- Changes to the underlying reviewer rulebook format.

### Clarifications
2026-09-19:
- **C1 — Ambiguity in Antigravity Reviewer Directory**: `skills/init/SKILL.md` previously instructed copying the reviewer contract to `.agents/_shared/reviewer-contract.md`. However, `assets/check-locks.py` searches `CANDIDATE_DIRS = (".claude/agents", ".agents/agents", "agents")`, and `skills/implement/SKILL.md` references `.agents/agents/<name>.md`. In Antigravity projects, subagents live in `.agents/agents/`, so the reviewer contract must live in `.agents/agents/_shared/reviewer-contract.md` to be "beside this file".
- **C2 — Load-Bearing Contract Pinning in `scripts/check-skill-contracts.py`**:
  Two contracts are added to bring the total to 23:
  1. Entry #22 pins `"Which harness(es) should this project configure? [1] Claude Code, [2] Antigravity, [3] Both"`: If detection is ambiguous or neither is detected, `init` must interview the operator rather than silently defaulting to Claude Code.
  2. Entry #23 pins `"CLAUDE.md for Claude Code, GEMINI.md for Antigravity, or both"`: The harness pointer must match the active target so canonical `AGENTS.md` is reachable.
  Both entries meet the bar for inclusion because omitting either reads as harmless concision in code review while breaking Antigravity context loading or defaulting to Claude Code.

## 2. Design (HOW)

### Approach and key decisions
- **Update `skills/init/SKILL.md`**:
  - In *Step 1 — Detect, don't ask*: Add explicit filesystem marker checks (`.claude/` or `CLAUDE.md` for Claude Code, `.agents/` or `GEMINI.md` for Antigravity) and runtime environment checks (`CLAUDE_CODE`, `ANTIGRAVITY`, or agent tool availability).
  - In *Step 2 — Ask only what is left*: If signals are ambiguous or neither is detected, confirm target harness(es) via `"Which harness(es) should this project configure? [1] Claude Code, [2] Antigravity, [3] Both"`.
  - In *Step 3 — Write*:
    - Pointers: Always create canonical `AGENTS.md`. Create `CLAUDE.md` for Claude Code, `GEMINI.md` for Antigravity, or both for dual-target projects.
    - Reviewers: Scaffolding into `.claude/agents/_shared/reviewer-contract.md` for Claude Code and `.agents/agents/_shared/reviewer-contract.md` for Antigravity.
    - Hooks: Scaffold `.claude/settings.json` and/or `.agents/hooks.json` based on the chosen harness(es).
- **Update `scripts/check-skill-contracts.py`**:
  - Update docstring count to 23 with explicit rationale.
  - Add two tuples in `CONTRACTS` targeting `skills/init/SKILL.md`:
    - `"Which harness(es) should this project configure? [1] Claude Code, [2] Antigravity, [3] Both"`
    - `"CLAUDE.md for Claude Code, GEMINI.md for Antigravity, or both"`
- **Update `scripts/test-gates.sh`**:
  - Add a test case (case 75) asserting that `scripts/check-skill-contracts.py` fails when either of the new `skills/init/SKILL.md` contract needles is stripped, naming the file and needle.
- **Update `docs/fidelity.md` and `docs/layout.md`**:
  - Add documentation covering harness detection, `CLAUDE.md`/`GEMINI.md` pointers, and `.agents/agents/_shared/reviewer-contract.md`.

### Affected modules and files, per .steering/structure.md
- `skills/init/SKILL.md` (shipped skill)
- `scripts/check-skill-contracts.py` (validator)
- `scripts/test-gates.sh` (test suite)
- `docs/fidelity.md` (documentation)
- `docs/layout.md` (documentation)
- `.specs/146-init-detect-active-harness-and-configure-pointers/spec.md` (this spec)

### Contract changes, and who else consumes them
Adds contracts #22 and #23 to `scripts/check-skill-contracts.py`. Verified by CI and turn-end validators.

### Risks and trade-offs
- Risk: Divergence in `check-contract-path.py` if `.agents/agents/` path format is rejected.
  Mitigation: `skills/init/SKILL.md` is in `SUFFIX` in `scripts/check-contract-path.py`, which validates using `.endswith(CANONICAL)`. Since `.agents/agents/_shared/reviewer-contract.md` ends with `_shared/reviewer-contract.md`, it passes without issue.

## 3. Tasks (TDD-ordered)
> One task is one complete Red-Green-Refactor cycle, so one green commit. No task is sequenced after the review.

- [x] T1: add guard test in `scripts/test-gates.sh` and contracts #22 & #23 in `scripts/check-skill-contracts.py` asserting `init` harness interview question and pointer instructions exist — verify red (stripped test fails, control passes) — then implement Step 1 detection, Step 2 interview, and Step 3 scaffolding in `skills/init/SKILL.md` to pass green
- [x] T2: update `docs/fidelity.md` and `docs/layout.md` to document active harness detection, `CLAUDE.md`/`GEMINI.md` pointers, and `.agents/agents/_shared/reviewer-contract.md` layout, and verify all validators pass
- [ ] T3: refactor and run full validator suite (`quality-gate.sh` and `test-gates.sh`), confirming clean baseline
