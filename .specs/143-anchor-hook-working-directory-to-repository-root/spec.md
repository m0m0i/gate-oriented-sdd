# Spec: Anchor hook working directory to repository root in antigravity.hooks.json
- Slug: 143-anchor-hook-working-directory-to-repository-root   Issue: 143   Type: bug   Status: draft
- Author: Hiroyuki   Date: 2026-09-19

## 1. Requirements (WHAT / WHY)
- Reproduction: Install the harness into an Antigravity project (`init`), creating `<project>/.agents/hooks.json` and `<project>/.agents/hooks/`. In `<project>`, introduce an unreviewed spec or a failing validator. Run an agent turn ending in `Stop` or `PostToolUse`.
- Expected: On turn end, `quality-gate.sh` blocks if a validator fails; `review-gate.sh` blocks if an unreviewed completed spec is present; `{{FAST_CHECK}}` runs project tests on tool use.
- Actual: In Antigravity, hooks are executed with `cwd` set to the directory containing `hooks.json` (`<project>/.agents/`). When evaluating `[ -f {{HOOKS_DIR}}/quality-gate.sh ]`, `{{HOOKS_DIR}}` resolves to `.agents/hooks`, so the test checks `.agents/.agents/hooks/quality-gate.sh`. This path does not exist, so `|| exit 0` executes immediately. Both gates are bypassed completely and silently exit 0. Furthermore, `quality-gate.sh` itself assumes the repository root when testing `[ -f .steering/tech.md ] || gate_pass`, and `{{FAST_CHECK}}` executes inside `.agents/` rather than the project root.
- Impact: Every project using `gate-oriented-sdd` under Antigravity. Both gates fail open on every turn, violating the repository's primary anchor (`- Owns: gates never fail open`). The failure is completely silent — the user sees clean turns while the harness is entirely inoperative.
- **Root cause:** Antigravity executes hook command strings with `cwd` set to the directory of the hook file (`<project>/.agents/`), while `antigravity.hooks.json` commands and hook scripts assume the repository root as working directory.
- Acceptance criteria:
  - [ ] **AC1:** WHEN Antigravity executes `PostToolUse` or `Stop` hooks with working directory set to `<project>/.agents/` THE SYSTEM SHALL anchor execution to the repository root before evaluating hook paths or commands, so that `quality-gate.sh`, `review-gate.sh`, and `{{FAST_CHECK}}` execute with the repository root as their working directory.
  - [ ] **AC2:** WHEN `quality-gate.sh` or `review-gate.sh` is invoked from any working directory within a git repository (such as `.agents/` or a subfolder) THE SYSTEM SHALL ensure its working directory is the repository root so relative paths (`.steering/tech.md`, `.specs/`) resolve correctly.
  - [ ] **AC3:** WHEN `scripts/test-gates.sh` tests Antigravity hook execution THE SYSTEM SHALL invoke the hook command with `cwd` set to `.agents/` and verify that failing validators and unreviewed specs block the turn as expected.
  - [ ] **AC4:** the regression test fails before the fix and passes after.
- Out of scope: PreInvocation steering digest hook (#144); rule auto-loading under `rules/` (#145); `init` harness detection (#146).

### Clarifications
2026-09-19, from `clarify`:

- **C1 — Shell precedence in `antigravity.hooks.json`:**
  Why semicolon `;` rather than `&& ... || exit 0`?
  In POSIX `sh`, `cmd1 && cmd2 || exit 0` triggers `exit 0` if `cmd2` exits non-zero (such as exit 2 when a gate blocks). Chaining with `;` separates the missing-file fallback from script execution:
  `cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"; [ -f {{HOOKS_DIR}}/quality-gate.sh ] || exit 0; sh {{HOOKS_DIR}}/quality-gate.sh`
  If the hook script is missing, `[ -f ... ] || exit 0` exits 0. If it exists, `sh ...` executes and its exit code (2 for block, 0 for pass) and stdout JSON are preserved.
- **C2 — In-script directory anchoring:**
  `quality-gate.sh` and `review-gate.sh` assume `cwd` is the repository root when reading `.steering/` or `.specs/`. If invoked directly from a subdirectory without the wrapper `cd`, they would see missing paths and exit 0. Sourcing `gate-lib.sh` anchors `cd "$(git rev-parse --show-toplevel 2>/dev/null)" || gate_pass` to prevent silent bypasses.
- **C3 — PostToolUse command:**
  `{{FAST_CHECK}}` runs with `cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" && {{FAST_CHECK}}` so project test runners execute in the repo root where project manifests (`package.json`, `pyproject.toml`, etc.) live.
- **C4 — Version bump:**
  This change modifies `hooks/templates/antigravity.hooks.json` and `hooks/*.sh`, which are shipped files. A patch version bump (to `0.10.1`) is owed in both `plugin.json` and `.claude-plugin/plugin.json`, landing after the review receipt as a step of `implement`.

## 2. Design (HOW)
- Fix approach, and why this rather than the narrower or wider fix:
  A dual-layer fix:
  1. In `hooks/templates/antigravity.hooks.json`, anchor `cwd` in every hook command before evaluating `{{HOOKS_DIR}}` or running `{{FAST_CHECK}}`.
  2. Inside `hooks/quality-gate.sh` and `hooks/review-gate.sh`, defensively anchor `cwd` to `$(git rev-parse --show-toplevel)` after sourcing `gate-lib.sh`.
  This guarantees that whether invoked via Antigravity's hook runner (where `cwd` is `.agents/`) or directly in a subshell, gates execute with repository root as `cwd`.
- Affected files:
  - `hooks/templates/antigravity.hooks.json` (shipped)
  - `hooks/quality-gate.sh` (shipped)
  - `hooks/review-gate.sh` (shipped)
  - `scripts/test-gates.sh` (guard test suite)
- **Blast radius:** All projects running on Antigravity where hooks were previously silently bypassed. On Claude Code, hooks already run with project root as `cwd`, so adding directory anchoring is transparent and non-breaking.
- Why this cannot recur: `scripts/test-gates.sh` will explicitly execute Antigravity hook command strings with `cwd` set to `.agents/`, failing if any gate bypasses or fails open.

## 3. Tasks (TDD-ordered)
> One task is one complete Red-Green-Refactor cycle, so one green commit. No task is sequenced after the review.
- [ ] T1: regression test in `scripts/test-gates.sh` invoking hook commands from `.agents/` working directory — then the fix anchoring commands in `hooks/templates/antigravity.hooks.json`
- [ ] T2: test that reproduces fail-open when gates are invoked from a subdirectory — then the fix anchoring to repository root inside `hooks/quality-gate.sh` and `hooks/review-gate.sh`
- [ ] T3: refactor test helpers and verify suite passes
