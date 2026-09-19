# Spec: Expose plugin rules under rules/ for Antigravity plugin loader
- Slug: 145-expose-plugin-rules-under-rules-for-antigravity   Issue: 145   Type: feature   Status: approved
- Author: Hiroyuki   Date: 2026-09-19

## 1. Requirements (WHAT / WHY)

### User story
As an Antigravity plugin user installing `gate-sdd` (globally or locally in `<workspace>/.agents/plugins/gate-sdd`),
I want the harness's core rules and invariants automatically discovered and loaded under `rules/AGENTS.md`,
So that the agent automatically adheres to Gate-SDD rules without manual rule copying or configuration.

### Acceptance Criteria
- [ ] **AC1:** WHEN the plugin is inspected or loaded by Antigravity THE SYSTEM SHALL provide `rules/AGENTS.md` linked or mirrored to the canonical `AGENTS.md` at repository root, with byte-identical content.
- [ ] **AC2:** WHEN `scripts/check-manifests.py` runs THE SYSTEM SHALL verify that `rules/AGENTS.md` exists and is byte-identical to repository root `AGENTS.md`, failing closed with exit code 1 if `rules/AGENTS.md` is missing, unreadable, or drifted from `AGENTS.md`.
- [ ] **AC3:** WHEN `scripts/test-gates.sh` runs THE SYSTEM SHALL test `scripts/check-manifests.py` against a fixture repository, verifying that missing `rules/AGENTS.md`, drifted `rules/AGENTS.md`, and missing `AGENTS.md` fail closed (exit 1), and valid matching `rules/AGENTS.md` passes (exit 0).
- [ ] **AC4:** WHEN `scripts/check-version-bump.py` evaluates shipped files THE SYSTEM SHALL include `"rules/"` in `SHIPPED` so modifications to plugin rules require a version bump.
- [ ] **AC5:** WHEN `.steering/tech.md` defines `- Source globs:` THE SYSTEM SHALL include `:(glob)rules/**/*.md` so rule modifications trigger gate checks.
- [ ] **AC6:** WHEN documentation (`AGENTS.md`, `docs/fidelity.md`) describes the dual-target layout THE SYSTEM SHALL document the `rules/` discovery seam for Antigravity alongside root `AGENTS.md`.

### Out of scope
- PreInvocation steering digest hook (#144).
- `init` harness detection (#146).

### Clarifications
2026-09-19, from `clarify`:

- **C1 — Symlink vs Mirrored Copy:**
  `rules/AGENTS.md` should be a relative symbolic link `rules/AGENTS.md -> ../AGENTS.md`. This maintains a single source of truth in git and local edits, adhering to `AGENTS.md`'s invariant: "one copy read by both... drift between the two targets is not possible". `scripts/check-manifests.py` reads file content using `read_text()`, so it works transparently whether `rules/AGENTS.md` is a symlink or a regular file, and strictly checks content equality to catch any broken symlink or content drift.
- **C2 — Guard Check in `scripts/check-manifests.py`:**
  `check-manifests.py` checks both files (`rules/AGENTS.md` and `AGENTS.md`). If `rules/AGENTS.md` is missing or is a broken link (`not is_file()`), it reports `missing: rules/AGENTS.md`. If `AGENTS.md` is missing, it reports `missing: AGENTS.md`. If their contents differ (`read_text() != read_text()`), it reports `rules/AGENTS.md has drifted from AGENTS.md; they must be identical`. Any `OSError` is caught and reported.
- **C3 — Test Coverage in `scripts/test-gates.sh`:**
  `scripts/test-gates.sh` creates a fixture directory testing `scripts/check-manifests.py`:
  1. Passing case: `rules/AGENTS.md` symlinked/matching `AGENTS.md` exits 0.
  2. Missing `rules/AGENTS.md`: exits 1 with error mentioning `missing: rules/AGENTS.md`.
  3. Drift: `rules/AGENTS.md` containing drifted content exits 1 with error mentioning `drifted`.
  4. Missing `AGENTS.md`: exits 1 with error mentioning `missing: AGENTS.md`.
- **C4 — Shipped path and version bump:**
  `rules/` is a plugin-shipped path. Adding `"rules/"` to `SHIPPED` in `scripts/check-version-bump.py` and `:(glob)rules/**/*.md` to `- Source globs:` in `.steering/tech.md`. This change adds a new feature (`feat(plugin)`), requiring a minor version bump from `0.10.1` to `0.11.0` in `plugin.json` and `.claude-plugin/plugin.json`, to be performed post-review as a step of `implement`.
- **C5 — Check-contract-path inclusion:**
  `scripts/check-contract-path.py` includes `AGENTS.md` in `SUFFIX`. Since `rules/AGENTS.md` is linked to `AGENTS.md`, adding `"rules/AGENTS.md"` to `SUFFIX` ensures both paths are verified against the reviewer contract canonical path rule.

## 2. Design (HOW)

### Key technical decisions
- **Symlink at `rules/AGENTS.md`**:
  `rules/AGENTS.md` points to `../AGENTS.md`. Antigravity's plugin loader automatically discovers files under `rules/` (`rules/AGENTS.md` or `rules/*.md`) and merges them into the active rule set.
- **Fail-closed Guard in `scripts/check-manifests.py`**:
  Ensures that `rules/AGENTS.md` cannot be accidentally removed or drifted from `AGENTS.md`.
- **Automated Verification in `scripts/test-gates.sh`**:
  Adds fixture-based tests confirming `check-manifests.py` exits 1 on missing `rules/AGENTS.md`, missing `AGENTS.md`, or drifted content.
- **Shipped Path Registration**:
  Registers `"rules/"` in `scripts/check-version-bump.py` and `:(glob)rules/**/*.md` in `.steering/tech.md`.

### Affected files
- `rules/AGENTS.md` (new, shipped)
- `scripts/check-manifests.py` (validator)
- `scripts/check-version-bump.py` (validator)
- `scripts/check-contract-path.py` (validator)
- `.steering/tech.md` (steering)
- `AGENTS.md` (documentation/layout)
- `docs/fidelity.md` (documentation/ledger)
- `scripts/test-gates.sh` (guard test suite)

### Blast radius
- Antigravity plugin loader: automatically discovers and merges `rules/AGENTS.md`.
- Claude Code: unaffected (Claude Code reads `AGENTS.md` at root).
- CI / guards: all existing guards remain green; new guard checks ensure `rules/AGENTS.md` cannot drift or be removed.

## 3. Tasks (TDD-ordered)
> One task is one complete Red-Green-Refactor cycle, so one green commit. No task is sequenced after the review.

- [x] T1: failing test in `scripts/test-gates.sh` asserting `check-manifests.py` fails closed when `rules/AGENTS.md` is missing or drifted — then the implementation in `scripts/check-manifests.py` and creating `rules/AGENTS.md` that passes it
- [x] T2: failing test in `scripts/test-gates.sh` for `rules/` in `check-version-bump.py` — then the implementation updating `check-version-bump.py`, `check-contract-path.py`, `tech.md`, `AGENTS.md`, and `docs/fidelity.md` that passes it
- [x] T3: refactor and verify all validators and `test-gates.sh` pass cleanly
