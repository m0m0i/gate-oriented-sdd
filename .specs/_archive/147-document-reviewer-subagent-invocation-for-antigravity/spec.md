# Spec: Document reviewer subagent invocation semantics for Antigravity
- Slug: 147-document-reviewer-subagent-invocation-for-antigravity   Issue: 147   Type: feature   Status: archived   Archived: 2026-09-20
- Author: Hiroyuki   Date: 2026-09-19

## 1. Requirements (WHAT / WHY)

### User story
As an agent or developer running `implement` under Google Antigravity,
I want explicit instructions in `skills/implement/SKILL.md` on how to invoke an independent reviewer subagent via Antigravity's dynamic registration (`define_subagent`) or context isolation delegation (`self`),
So that the reviewer runs outside this session's context with genuine independence, and `reviewed_by=subagent` can be recorded honestly instead of defaulting to an inline review.

### Serves
Dual-target parity: reviewer independence under Google Antigravity (CAP-4 / fidelity between Claude Code and Antigravity).

### Acceptance criteria
- [ ] **AC1:** WHEN an agent executes `skills/implement/SKILL.md` Step 2 under Google Antigravity THE SYSTEM SHALL provide explicit reviewer invocation guidance:
  (a) dynamically register the reviewer using `define_subagent` from its agent file (e.g. `.claude/agents/<name>.md` or `.agents/agents/<name>.md`) with read-only tools and call `invoke_subagent`, OR
  (b) spawn a `self` subagent via `invoke_subagent` passing reviewer instructions, contract, and branch diff in the prompt.
- [ ] **AC2:** WHEN an independent reviewer is invoked via either Antigravity method (dynamic registration or `self` subagent delegation) THE SYSTEM SHALL direct the agent to record `reviewed_by=subagent` in `.specs/<slug>/.review-receipt`, because the reviewer ran outside the calling session's context.
- [ ] **AC3:** WHEN neither subagent invocation route is supported or possible THE SYSTEM SHALL direct the agent to execute the reviewer procedure inline in the current session and record `reviewed_by=inline` in `.specs/<slug>/.review-receipt`.
- [ ] **AC4:** WHEN `scripts/check-skill-contracts.py` runs THE SYSTEM SHALL verify that `skills/implement/SKILL.md` contains the Antigravity reviewer invocation instruction, failing closed if it has been edited away.
- [ ] **AC5:** WHEN `scripts/test-gates.sh` runs THE SYSTEM SHALL include a guard test confirming `scripts/check-skill-contracts.py` fails when the Antigravity reviewer subagent invocation contract is missing from `skills/implement/SKILL.md`.
- [ ] **AC6:** WHEN `docs/fidelity.md` is inspected THE SYSTEM SHALL document the reviewer subagent invocation divergence and semantics between Claude Code (file auto-discovery) and Google Antigravity (dynamic registration or `self` delegation).

### Out of scope
- Automatic harness detection in `init` (#146).
- Platform-level subagent discovery changes in Google Antigravity.

### Clarifications
2026-09-19, from `clarify`:
- **C1 — Reviewer Independence and `reviewed_by=subagent`**: Both dynamic registration via `define_subagent` + `invoke_subagent` and delegating to a `self` subagent via `invoke_subagent` run in a separate subagent conversation context, providing reviewer independence outside the calling session. Both record `reviewed_by=subagent`. `reviewed_by=inline` is reserved strictly for when the author executes the review procedure within the calling session.
- **C2 — Read-Only Tool Policy**: When dynamically registering a reviewer via `define_subagent`, write tools should not be enabled (`enable_write_tools=false`), keeping the subagent read-only in compliance with the reviewer contract.
- **C3 — Load-Bearing Contract Needle**: `scripts/check-skill-contracts.py` will pin `"register it dynamically via define_subagent or delegate to a self subagent"`. This ensures future edits cannot silently discard the Antigravity reviewer invocation paths, moving the contract count from 20 to 21 with explicit rationale.

## 2. Design (HOW)

### Approach and key decisions
- **Explicit Antigravity Invocation Flow in `skills/implement/SKILL.md` Step 2**:
  Update Step 2 of `skills/implement/SKILL.md` with structured instructions:
  1. *Claude Code*: Subagents are auto-discovered from `.claude/agents/<name>.md`.
  2. *Antigravity*: Subagents are not auto-discovered from markdown files. The agent should either:
     - Register the reviewer dynamically via `define_subagent` using the prompt and rules from the reviewer agent file (with read-only tools), then call `invoke_subagent`; OR
     - Delegate to a `self` subagent via `invoke_subagent`, passing the reviewer instructions, contract, and diff.
  3. *Waiting and Turn Lifecycle*: Retain the existing critical instructions ("waiting means keeping the turn open", emit no final message before result lands).
  4. *Fallback*: If neither subagent path is supported or possible, execute the reviewer procedure inline and record `reviewed_by=inline`.
  5. *Receipt Semantics*: Clarify that both Antigravity subagent paths record `reviewed_by=subagent`.
- **Contract Enforcement in `scripts/check-skill-contracts.py`**:
  Add entry #21 to `CONTRACTS` in `scripts/check-skill-contracts.py`, pinning the needle `"register it dynamically via define_subagent or delegate to a self subagent"`. Update the count comment to 21 with justification.
- **Guard Test in `scripts/test-gates.sh`**:
  Add a test case in `scripts/test-gates.sh` asserting that `scripts/check-skill-contracts.py` fails if `skills/implement/SKILL.md` is stripped of the Antigravity reviewer invocation needle.
- **Fidelity Documentation in `docs/fidelity.md`**:
  Update row 8 to reflect that reviewer subagent invocation semantics are defined (dynamic registration / `self` delegation) and add a subsection under "Divergences that are handled, not gaps".

### Affected modules and files, per .steering/structure.md
- `skills/implement/SKILL.md` (shipped skill)
- `scripts/check-skill-contracts.py` (validator)
- `scripts/test-gates.sh` (test suite)
- `docs/fidelity.md` (documentation)
- `.specs/147-document-reviewer-subagent-invocation-for-antigravity/spec.md` (this spec)

### Contract changes, and who else consumes them
Adds contract #21 in `scripts/check-skill-contracts.py`. Verified by CI and turn-end validators.

### Risks and trade-offs
- Risk: Bloating `skills/implement/SKILL.md`.
  Mitigation: Keep the prose compact, directly stating the two Antigravity paths without redundant fluff, while preserving all existing load-bearing sentences.

## 3. Tasks (TDD-ordered)
> One task is one complete Red-Green-Refactor cycle, so one green commit. No task is sequenced after the review.

- [x] T1: add failing test in `scripts/test-gates.sh` and contract #21 in `scripts/check-skill-contracts.py` asserting Antigravity reviewer invocation instruction exists — verify red — then implement the documentation in `skills/implement/SKILL.md` to pass green
- [x] T2: update `docs/fidelity.md` to document the reviewer subagent invocation semantics for Antigravity, and verify all validators pass
- [x] T3: refactor and run full validator suite (`quality-gate.sh` and `test-gates.sh`), confirming clean baseline
