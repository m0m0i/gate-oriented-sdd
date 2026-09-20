# Spec: Isolate runtime plugin payload from repo-internal tooling on plugin installation
- Slug: 140-isolate-runtime-plugin-payload   Issue: 140   Type: feature   Status: approved
- Author: Hiroyuki   Date: 2026-09-20

## 1. Requirements (WHAT / WHY)

### User story
As an Antigravity or Claude Code plugin consumer,
I want a clean standalone distribution artifact containing only the runtime plugin payload,
so that installing the plugin into my workspace does not unpack repository-internal development assets (`.specs/`, `.steering/`, `scripts/`, `evals/`, `docs/`, `.work_logs/`).

### Serves
CAP-4 (Installation into a repository that already has opinions) and CAP-5 (Fixes that reach the people running it).

### Acceptance criteria
- [ ] **AC1:** WHEN the release packaging tool (`scripts/package-release.py`) executes THE SYSTEM SHALL generate a standalone zip archive (`dist/gate-sdd.zip`) containing strictly the runtime payload (`plugin.json`, `.claude-plugin/`, `skills/`, `agents/`, `hooks/`, `rules/`, `assets/`, `AGENTS.md`, `README.md`, `README.ja.md`, `LICENSE`), preserving file permissions and symbolic links.
- [ ] **AC2:** WHEN the release packaging tool generates `dist/gate-sdd.zip` THE SYSTEM SHALL exclude repository-internal assets (`.specs/`, `.steering/`, `.work_logs/`, `scripts/`, `evals/`, `docs/`, `.github/`, `.vscode/`, `.git*`, `__pycache__`, `.DS_Store`).
- [ ] **AC3:** WHEN `dist/gate-sdd.zip` is extracted into a target directory THE SYSTEM SHALL pass `scripts/check-manifests.py` verifying both manifests agree and `rules/AGENTS.md` resolves identically to `AGENTS.md`.
- [ ] **AC4:** WHEN a tag matching `gate-sdd--v*` or `v*` is pushed (or `workflow_dispatch` triggered) THE SYSTEM SHALL run `.github/workflows/release.yml` to package `dist/gate-sdd.zip`, verify its manifest integrity, and attach it to the GitHub Release.
- [ ] **AC5:** WHEN documentation (`docs/fidelity.md`, `docs/layout.md`) is consulted THE SYSTEM SHALL describe the release distribution artifact, explain what direct `git clone` or local path installs unpack vs the release artifact, and record why Option 1 (`.gitattributes export-ignore`) and Option 2 (`plugins/gate-sdd/`) were rejected.
- [ ] **AC6:** WHEN `scripts/test-gates.sh` runs THE SYSTEM SHALL verify `scripts/package-release.py` against a fixture and current repository, verifying runtime files are present, internal dev assets are excluded, and missing runtime files fail closed with non-zero exit code.

### Out of scope
- Restructuring the repository root into `plugins/gate-sdd/` (Option 2 — rejected because the repo root IS the plugin, per `docs/layout.md`).
- Relying on `.gitattributes export-ignore` as the distribution solution (Option 1 — rejected because marketplace installs clone, so exclusions never apply).
- Modifying how raw `git clone` operates (git clones the whole repository commit history and files).

### Clarifications
2026-09-20, from `clarify`:

- **C1 — Inclusion of `assets/` and `AGENTS.md` in runtime payload:**
  The runtime payload must include `assets/` and `AGENTS.md` in addition to `plugin.json`, `.claude-plugin/`, `skills/`, `agents/`, `hooks/`, `rules/`, `README.md`, `README.ja.md`, `LICENSE`. `assets/` is required by `skills/init/SKILL.md` to copy issue templates, `check-steering-anchors.sh`, `check-document-set.py`, and `check-locks.py`. `AGENTS.md` is required because `rules/AGENTS.md` is a symlink pointing to `../AGENTS.md` and Claude Code reads `AGENTS.md` at root.
- **C2 — Packaging script `scripts/package-release.py`:**
  Rather than relying solely on inline shell in GitHub Actions, implement `scripts/package-release.py` (Python 3 stdlib only, no third-party dependencies). This enables deterministic testing in `scripts/test-gates.sh`, ensuring symlinks and exclusion rules are rigorously verified before CI runs.
- **C3 — Rejection of Alternative Options:**
  - *Option 1 (`.gitattributes export-ignore`)*: Rejected because marketplace installs clone the repository, so export-ignore rules never apply to the common install path.
  - *Option 2 (`plugins/gate-sdd/` subfolder layout)*: Rejected because it violates `docs/layout.md` ("the repo root IS the plugin") and breaks the dual-manifest arrangement, moving both manifests, marketplace.json, guard paths, and downstream pinned copies in one disruptive change.
- **C4 — Plain documentation of direct git clone vs release artifact:**
  `docs/fidelity.md` and `docs/layout.md` will explicitly document that a direct `git clone` or local path install will unpack the entire repository including internal tooling (safe via progressive disclosure), whereas the `gate-sdd.zip` release distribution artifact provides an isolated payload containing only runtime components.

## 2. Design (HOW)

### Key technical decisions
- **Deterministic packager (`scripts/package-release.py`)**:
  - Uses Python `zipfile` module.
  - Copies required runtime paths: `plugin.json`, `.claude-plugin/`, `skills/`, `agents/`, `hooks/`, `rules/`, `assets/`, `AGENTS.md`, `README.md`, `README.ja.md`, `LICENSE`.
  - Preserves Unix file permissions (executable bits on hook scripts) and symbolic links (`rules/AGENTS.md`).
  - Strict validation: fails closed (exit code 1) if any expected runtime file or directory is missing.
  - Excludes unwanted files: `__pycache__`, `.DS_Store`, and ignores internal directories (`.specs/`, `.steering/`, `scripts/`, `evals/`, `docs/`, `.work_logs/`, `.github/`, `.vscode/`, `.git/`).
- **Release workflow (`.github/workflows/release.yml`)**:
  - Triggers on tag pushes (`gate-sdd--v*`, `v*`) and `workflow_dispatch`.
  - Packages `dist/gate-sdd.zip` via `python3 scripts/package-release.py dist/gate-sdd.zip`.
  - Extracts to a temporary directory and validates manifest parity via `scripts/check-manifests.py`.
  - Uploads `gate-sdd.zip` to the GitHub Release via `softprops/action-gh-release@v2`.
- **Automated test suite (`scripts/test-gates.sh`)**:
  - Adds Case 76 testing `package-release.py`:
    - Tests execution against repository: creates zip, verifies table of contents contains runtime files and strictly omits `.specs/`, `.steering/`, `scripts/`, `evals/`, etc.
    - Tests extracted archive against `check-manifests.py`.
    - Tests fail-closed behavior when a required runtime component is missing.
- **Documentation updates**:
  - Updates `docs/layout.md` to document the release distribution artifact.
  - Updates `docs/fidelity.md` under distribution to clarify `gate-sdd.zip` consumption vs direct git clone / local path installation, and notes the rejected options.

### Affected files
- `scripts/package-release.py` (new, repo packaging tool)
- `.github/workflows/release.yml` (new, CI workflow)
- `scripts/test-gates.sh` (modified, guard test suite Case 76)
- `docs/fidelity.md` (modified, documentation)
- `docs/layout.md` (modified, documentation)

### Blast radius
- Downstream projects installing via release artifact `gate-sdd.zip` receive a clean directory with only runtime components.
- Existing git clone installs continue to function identically (no changes to repository root layout or manifests).
- CI: adds new workflow triggered only on tags and manual dispatch.

## 3. Tasks (TDD-ordered)
> One task is one complete Red-Green-Refactor cycle, so one green commit. No task is sequenced after the review.

- [x] T1: failing test in `scripts/test-gates.sh` asserting `scripts/package-release.py` packages runtime files, preserves symlinks, and strictly excludes internal dev assets — then implement `scripts/package-release.py` to make the test pass
- [ ] T2: add release workflow `.github/workflows/release.yml` with tag and workflow_dispatch triggers, and verify syntax and packaging step
- [ ] T3: update `docs/fidelity.md` and `docs/layout.md` documenting the release artifact, consumption methods, and rejected alternatives
- [ ] T4: refactor and verify all 12 repository validators and `scripts/test-gates.sh` pass cleanly
