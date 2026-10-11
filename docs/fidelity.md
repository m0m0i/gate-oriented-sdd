# Fidelity ledger

What each harness actually supports, and what this harness does about the difference. Rows are marked **verified** only where the behaviour was observed on a real install — see [`verified.md`](./verified.md) for method and versions.

| Capability | Claude Code | Antigravity | Status |
| :-- | :-- | :-- | :-- |
| Skill format and discovery | `skills/<n>/SKILL.md` | identical path and format | verified |
| Reviewer definition | `reviewers/<n>.md`, copied by `init` to `.claude/agents/<n>.md` | the same file, copied to `.agents/agents/<n>.md` | handled — the plugin registers no agent on either harness (#235); explicit invocation routes in `skills/implement/SKILL.md` |
| Plugin manifest | `.claude-plugin/plugin.json` | `plugin.json` | verified — both present, no collision |
| Marketplace / git install | yes | no — local path only | verified from docs |
| Quality gate blocks a turn | `Stop`, exit 2 | `Stop`, `{"decision":"continue"}` with exit 0 | verified on Claude Code; verified on Antigravity under exit 0 (#282) |
| Review-receipt gate | `Stop` | `Stop` | same mechanism; verified on both harnesses (#282) |
| Gate delivery | from the plugin: `.claude-plugin/hooks.json` runs `hooks/plugin-gate.sh`, and a fix arrives by plugin update, whose pass a session the Claude desktop app starts runs only with the `env` line `init` writes (#274) | copied into `.agents/hooks/` by `init`, and a fix arrives by running `init` again | **verified on Claude Code** (V1, V2 in `verified.md`; the pass with the line, F2 and F3); on Antigravity plugin-shipped hooks run with cwd in the plugin directory (A12) |
| Per-edit feedback | `PostToolUse`, exit 2 to stderr | `PostToolUse`, observe-only | verified — both fire (A13) |
| Deny a tool call outright | `PreToolUse` | `PreToolUse`, `decision: deny` | not exercised by this harness |
| Rules discovery | root `AGENTS.md` (read as canonical context) | `rules/AGENTS.md` (auto-discovered and merged by plugin loader) | **leakage gap** — plugin-shipped `rules/AGENTS.md` leaks into every project on the machine (A10) |
| Steering digest | `SessionStart` | `PreInvocation` (turn 0 step injection) | verified on Claude Code; turn 0 delivered on Antigravity (#282) |
| Context re-injection after compaction | `SessionStart` | **no event** | **gap** |

## The one real gap

Antigravity has five hook events — `PreToolUse`, `PostToolUse`, `PreInvocation`, `PostInvocation`, `Stop` — and none of them is `SessionStart`. Initial steering digest injection is solved via `PreInvocation` with turn 0 filtering, but context re-injection after mid-session compaction has no trigger on Antigravity.

On Claude Code, `SessionStart` re-fires on session resume and context compaction, keeping steering invariants in prompt context. On Antigravity, `PreInvocation` inspects `stdin` for `invocationNum == 0` to deliver the digest on the initial turn without re-injecting on subsequent turns; if the session compacts mid-stream, the digest is not re-injected until a new session begins.

## Divergences that are handled, not gaps

**Blocking signal.** Claude Code blocks with exit code 2 and speaks through stderr; Antigravity blocks only when a `Stop` hook exits 0 with `{"decision": "continue", "reason": "…"}` (or `"block"`) on stdout. `hooks/gate-lib.sh` and the bootstrap guard detect Antigravity via `ANTIGRAVITY_CONVERSATION_ID` or `ANTIGRAVITY_AGENT` and exit 0 (fixing the exit 2 fail-open defect from 1.3.3; #282). Furthermore, `_gate_json_escape` escapes backslashes, quotes, newlines, tabs, and carriage returns to prevent `protojson` unmarshal errors (#282).

**Hook schema.** Antigravity's schema is mixed: tool events take the nested `{matcher, hooks: [...]}` form, non-tool events take a flat `{type, command, timeout}`. Getting it wrong invalidates the entire file with an error that reads like a missing field. `scripts/check-manifests.py` enforces the shapes so the mistake cannot ship.

**Working directory.** A gate must run with the project as cwd. A Claude Code plugin hook does, with `CLAUDE_PLUGIN_ROOT` naming the plugin (verified, V1), so since 0.23.0 the Claude Code gates ship from the plugin's `.claude-plugin/hooks.json` and `init` copies nothing there; `hooks/plugin-gate.sh` keeps them silent in a project without `.steering/` and stands them down where a project still runs its own copy through an entry the wrapper can resolve, and otherwise lets both run (#256, #262, ADR-8). On Antigravity a plugin-shipped hook gets the plugin directory instead (verified on 1.3.3, A12; `workspacePaths` arrives on stdin), so `init` still installs project-local copies into `.agents/hooks/`, and a fix reaches an Antigravity project only by running `init` again. The per-project difference was never in the copy: validators come from `.steering/tech.md`.

**Steering digest.** Claude Code delivers the steering digest on `SessionStart`. On Antigravity, `PreInvocation` stdin provides `invocationNum`, which starts at 0 on turn 0 (verified on 1.3.3, A6). `hooks/steering-digest-antigravity.sh` checks `data.get("invocationNum") != 0` to deliver the digest on initial turn 0 and exit 0 with `{}` on subsequent continuation turns (#282).

**Reviewer subagent invocation.** Claude Code auto-discovers subagent definitions from `.claude/agents/<name>.md` and invokes them directly by name. On Antigravity CLI 1.3.3, `agy agents` lists only global/plugin agents; workspace `.agents/agents/*.md` is not registered as standalone agents, and Claude Code tool names (`Read, Grep, Glob, Bash`) do not map to Antigravity tools (A8). Furthermore, reviewer prompt relative paths like `rules/types-and-style.md` do not resolve from project root (A9). `implement` does not rely on Antigravity discovering a project's agent files; instead, an agent can dynamically register the reviewer from its file via `define_subagent` (with write tools disabled) or delegate to a `self` subagent via `invoke_subagent` for context isolation. Both paths run outside this session's context, preserving reviewer independence, and record `reviewed_by=subagent`. If neither subagent route is available, the agent falls back to inline execution and records `reviewed_by=inline`. A plugin's own `agents/` directory is a different matter, and both harnesses read it: Claude Code registers every Markdown file under it at any depth, and `agy plugin validate` 1.2.16 reported eight files processed there for this plugin's three reviewers. That is why the plugin has no such directory since #235 ([`verified.md`](./verified.md)).

**Harness detection and rule pointers.** `init` inspects filesystem markers (`.claude/` or `CLAUDE.md` for Claude Code; `.agents/` or `GEMINI.md` for Antigravity) and runtime environment signals (`CLAUDE_CODE`, `ANTIGRAVITY`, or agent tool availability). If signals are ambiguous or neither is detected, `init` prompts `"Which harness(es) should this project configure? [1] Claude Code, [2] Antigravity, [3] Both"`. Canonical rules always reside in `AGENTS.md`, and `init` generates pointer files (`CLAUDE.md` for Claude Code, `GEMINI.md` for Antigravity, or both). For Antigravity projects, reviewer contracts and agents sit under `.agents/agents/` (e.g. `.agents/agents/_shared/reviewer-contract.md`) to align with `check-locks.py` candidate directories.

**Release distribution and payload isolation.** Direct `git clone` or local path installation unpacks the full repository including development assets (`.specs/`, `.steering/`, `scripts/`, `evals/`, `docs/`, `.work_logs/`). While harness runtimes safely ignore these extra folders via progressive disclosure, downstream consumers wanting an isolated runtime payload can consume the CI release artifact (`gate-sdd.zip`) generated on tag releases via `.github/workflows/release.yml` and `scripts/package-release.py`. Alternative approaches like `.gitattributes export-ignore` (ignored by git clone) and subdirectory nesting (`plugins/gate-sdd/`, which breaks the root-as-plugin invariant) were evaluated and rejected (see `docs/layout.md` and Issue #140).


