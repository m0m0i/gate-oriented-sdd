# Spec: Align README and README.ja.md with Antigravity parity and release packaging
- Slug: 157-align-readme-with-antigravity-parity   Issue: 157   Type: chore   Status: draft
- Author: Antigravity   Date: 2026-09-20

## 1. Requirements (WHAT / WHY)
- What changes:
  Update `README.md` and `README.ja.md` in lockstep to reflect the completed Antigravity parity track (#143, #144, #145, #146, #147) and release payload isolation (#140):
  1. **Install Section**: Document both installation options for Google Antigravity:
     - Standalone release zip (`gate-sdd.zip`) from GitHub Releases (recommended: isolates runtime payload and excludes repo-internal development tooling).
     - Direct `git clone` and local path installation (`agy plugin install ./gate-oriented-sdd`).
  2. **Context Isolation & Pointers ("Two things worth stealing")**: Update rulebook location description from `not in CLAUDE.md` to `not in AGENTS.md (or CLAUDE.md / GEMINI.md)` in both languages.
  3. **Fidelity Table**: Add the `Rules discovery` row from `docs/fidelity.md` (`root AGENTS.md` vs `rules/AGENTS.md`) and keep English and Japanese tables identical in structure.
  4. **`init` Skill Description**: Clarify that `init` detects the active harness (Claude Code, Antigravity, or both) and configures the corresponding rule pointers (`CLAUDE.md` / `GEMINI.md`) and agent directory structures.
- **What must NOT change:**
  - `scripts/check-readme-claims.py` constraints:
    - Dynamic version badge must remain untouched (`https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2Fm0m0i%2Fgate-oriented-sdd%2Fmain%2Fplugin.json&query=%24.version&prefix=v&label=gate-sdd&color=blue`).
    - No static version literals (e.g. `**v0.14.0**` or `**vX.Y.Z**`).
    - No gate or guard behaviour counts (e.g. numbers in close proximity to gates/guards).
    - Exact inline receipt counts must be preserved in both languages (`from a spawned reviewer on all but three` in English, `3件を除いて` and `その3件は inline` in Japanese).
  - All 12 project validators, `scripts/test-gates.sh`, `quality-gate.sh`, and `review-gate.sh` must remain 100% green.
  - Markdown fence formatting must obey `scripts/check-markdown-fences.py`.
- Why now:
  Following the merge of #140 and #146, the documentation in `README.md` and `README.ja.md` remained partially dated and Claude Code-centric. Users following the README instructions to install on Antigravity were directed solely to `git clone` (which brings internal repo files), unaware of the clean `gate-sdd.zip` distribution artifact, and readers looking at the fidelity table lacked information on rules discovery.
- Acceptance criteria:
  - [ ] **AC1:** `README.md` and `README.ja.md` SHALL describe both the standalone release archive (`gate-sdd.zip`) and direct `git clone` installation methods for Antigravity.
  - [ ] **AC2:** `README.md` and `README.ja.md` SHALL update the context isolation explanation to refer to `AGENTS.md` (or `CLAUDE.md` / `GEMINI.md`) instead of `CLAUDE.md` alone.
  - [ ] **AC3:** `README.md` and `README.ja.md` SHALL include `Rules discovery` in the fidelity table (`root AGENTS.md` vs `rules/AGENTS.md`), matching `docs/fidelity.md`.
  - [ ] **AC4:** `README.md` and `README.ja.md` SHALL note in the `init` description that `init` detects the active harness to configure appropriate rule pointers and agent directories.
  - [ ] **AC5:** `scripts/check-readme-claims.py` and all 12 repository validators SHALL pass with exit code 0.
- Out of scope:
  - Bumping version or modifying `plugin.json` during spec authoring (manifest bumps occur during post-receipt implement steps for shipped changes).
  - Changing runtime hook or plugin logic.

### Clarifications
None needed — requirements were unambiguous and follow directly from previous parity issues (#140, #145, #146) and `docs/fidelity.md`.

## 2. Design (HOW)
- Approach:
  Update `README.md` and `README.ja.md` in lockstep:
  1. In `## The idea` ("Two things worth stealing"):
     - Adjust text to note rules sit in `agents/<reviewer>/rules/`, not in `AGENTS.md` (or `CLAUDE.md` / `GEMINI.md`) and not in session context.
  2. In `## The minimum set` / `## The skills`:
     - In the description of `init`, mention that `init` inspects markers to detect the active harness (Claude Code, Antigravity, or both) and writes the appropriate rule pointer (`CLAUDE.md`, `GEMINI.md`) and reviewer contracts.
  3. In `## Install`:
     - Under `Google Antigravity`, present two clear options:
       - Option 1 (recommended): Download and extract `gate-sdd.zip` from GitHub Releases (`agy plugin install /path/to/extracted/gate-sdd`).
       - Option 2: Direct clone (`git clone ... && agy plugin install ./gate-oriented-sdd`).
  4. In `## Fidelity between the two harnesses`:
     - Insert a row for `Rules discovery`:
       Claude Code: `root AGENTS.md (canonical context)`
       Antigravity: `rules/AGENTS.md (auto-discovered and merged by plugin loader)`
- Affected files:
  - `README.md`
  - `README.ja.md`
- **Coverage gap:**
  Behavior is guarded by `scripts/check-readme-claims.py`, `scripts/check-markdown-fences.py`, `scripts/check-manifests.py`, and `scripts/test-gates.sh`. Baseline runs confirm these checks are currently green.
- Rollback:
  Revert `git checkout main -- README.md README.ja.md`.

## 3. Tasks (TDD-ordered)
- [ ] T1: verify baseline guards pass (`scripts/check-readme-claims.py`, `scripts/check-markdown-fences.py`, `scripts/test-gates.sh`)
- [ ] T2: update `README.md` with Antigravity release archive and clone install options, updated rulebook pointer phrasing, `Rules discovery` fidelity row, and `init` harness detection note
- [ ] T3: update `README.ja.md` in lockstep with matching Japanese translations
- [ ] T4: confirm `scripts/check-readme-claims.py`, `scripts/check-markdown-fences.py`, and `scripts/test-gates.sh` pass cleanly
