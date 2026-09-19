# Fidelity ledger

What each harness actually supports, and what this harness does about the difference. Rows are marked **verified** only where the behaviour was observed on a real install — see [`verified.md`](./verified.md) for method and versions.

| Capability | Claude Code | Antigravity | Status |
| :-- | :-- | :-- | :-- |
| Skill format and discovery | `skills/<n>/SKILL.md` | identical path and format | verified |
| Subagent definition | `agents/<n>.md` | `agents/` in plugin layout | handled — explicit invocation routes in `skills/implement/SKILL.md` |
| Plugin manifest | `.claude-plugin/plugin.json` | `plugin.json` | verified — both present, no collision |
| Marketplace / git install | yes | no — local path only | verified from docs |
| Quality gate blocks a turn | `Stop`, exit 2 | `Stop`, `{"decision":"continue"}` | **verified — both block** |
| Review-receipt gate | `Stop` | `Stop` | verified via the same mechanism |
| Per-edit feedback | `PostToolUse`, exit 2 to stderr | `PostToolUse`, observe-only | verified — both fire |
| Deny a tool call outright | `PreToolUse` | `PreToolUse`, `decision: deny` | not exercised by this harness |
| Rules discovery | root `AGENTS.md` (read as canonical context) | `rules/AGENTS.md` (auto-discovered and merged by plugin loader) | verified — symlinked, kept in sync by `check-manifests.py` |
| Steering digest | `SessionStart` | `PreInvocation` (turn 1 step injection) | verified — both deliver digest |
| Context re-injection after compaction | `SessionStart` | **no event** | **gap** |

## The one real gap

Antigravity has five hook events — `PreToolUse`, `PostToolUse`, `PreInvocation`, `PostInvocation`, `Stop` — and none of them is `SessionStart`. Initial steering digest injection is solved via `PreInvocation` with turn 1 filtering, but context re-injection after mid-session compaction has no trigger on Antigravity.

On Claude Code, `SessionStart` re-fires on session resume and context compaction, keeping steering invariants in prompt context. On Antigravity, `PreInvocation` inspects `stdin` for `invocationNum == 1` to deliver the digest on the first turn without re-injecting on subsequent turns; if the session compacts mid-stream, the digest is not re-injected until a new session begins.

## Divergences that are handled, not gaps

**Blocking signal.** Claude Code blocks with exit code 2 and speaks through stderr; Antigravity blocks with JSON on stdout and speaks through the `reason` field. `hooks/gate-lib.sh` emits both from one script, so each harness reads its own channel and the two cannot disagree.

**Hook schema.** Antigravity's schema is mixed: tool events take the nested `{matcher, hooks: [...]}` form, non-tool events take a flat `{type, command, timeout}`. Getting it wrong invalidates the entire file with an error that reads like a missing field. `scripts/check-manifests.py` enforces the shapes so the mistake cannot ship.

**Working directory.** A gate must run with the project as cwd. Claude Code plugin hooks already do; on Antigravity, a plugin-shipped hook gets the plugin directory instead. `init` therefore installs project-local hooks for both, which is also what the gate needs anyway, since validators differ per project.

**Steering digest.** Claude Code delivers the steering digest on `SessionStart`. Antigravity delivers it via `PreInvocation` turn 1 step injection (`hooks/steering-digest-antigravity.sh`), emitting `{"injectSteps": [{"ephemeralMessage": "..."}]}` on turn 1 and `{}` thereafter. `scripts/check-manifests.py` verifies both hook templates declare their respective steering hook.

**Reviewer subagent invocation.** Claude Code auto-discovers subagent definitions from `.claude/agents/<name>.md` and invokes them directly by name. Antigravity does not auto-discover arbitrary agent files on disk; instead, an agent can dynamically register the reviewer from its file via `define_subagent` (with write tools disabled) or delegate to a `self` subagent via `invoke_subagent` for context isolation. Both paths run outside this session's context, preserving reviewer independence, and record `reviewed_by=subagent`. If neither subagent route is available, the agent falls back to inline execution and records `reviewed_by=inline`.

**Harness detection and rule pointers.** `init` inspects filesystem markers (`.claude/` or `CLAUDE.md` for Claude Code; `.agents/` or `GEMINI.md` for Antigravity) and runtime environment signals (`CLAUDE_CODE`, `ANTIGRAVITY`, or agent tool availability). If signals are ambiguous or neither is detected, `init` prompts `"Which harness(es) should this project configure? [1] Claude Code, [2] Antigravity, [3] Both"`. Canonical rules always reside in `AGENTS.md`, and `init` generates pointer files (`CLAUDE.md` for Claude Code, `GEMINI.md` for Antigravity, or both). For Antigravity projects, reviewer contracts and agents sit under `.agents/agents/` (e.g. `.agents/agents/_shared/reviewer-contract.md`) to align with `check-locks.py` candidate directories.

