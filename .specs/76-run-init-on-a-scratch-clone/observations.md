# Observations — init on a scratch clone

Recorded as each task ran. `docs/verified.md`'s section is written from this file in T3. The target is described by toolchain, counts and behaviour only; no identifier from it appears here, by AC7's rule.

## T1 — the clone, and what was stripped

**The target.** A real, unrelated Python project of the maintainer's, and the plugin's first consumer. Python 3.12, `uv` with a lockfile, `ruff`, `mypy` and `pytest` configured in `pyproject.toml` (six `[tool.*]` sections), a `src/` layout, 14 test files, one CI workflow, 38 of the last 50 commit subjects carrying a conventional prefix. Cloned locally from the working checkout, default branch `main`, into this session's scratch directory. Nothing is pushed; the clone is discarded in T4.

**Removed — harness state, per clarification 1**, 19 files plus one key:

| Removed | Rule |
| :-- | :-- |
| `.steering/` (3 files), `.specs/` (a README and its archive README, plus 3 spec directories), `.work_logs/` (a README and 2 entries) | the harness's own state; `init` writes these |
| `.claude/agents/` (a Python reviewer and its `reviewer-contract.md` beside it, in the pre-`_shared/` layout) and `.claude/hooks/` (the four gate scripts) | harness state; the reviewer and hooks `init` installs |
| the `hooks` key of `.claude/settings.json` — the only key the file had, so the file is now `{}` | harness wiring; the file itself is the project's and stays |
| `scripts/check-locks.py` | the copy `init` installs so a project can re-pin its rulebook |

**Kept — the project's own, which `init` must merge into**, per clarification 1: `AGENTS.md` (six harness mentions, from the earlier install) and `CLAUDE.md`; `.github/ISSUE_TEMPLATE/` with the four files; every `[tool.*]` section; the CI workflow; the tests. The earlier install's `check-steering-anchors.sh` was not present under `scripts/`, so that copy was never made — a first observation about the earlier install, recorded and not acted on.

**State entering T2.** The clone is on `main` with 20 uncommitted deletions and `uv sync` completed at exit 0, so the candidate validators can run. `.env` is git-ignored and absent from the clone; tests that need it will fail on the clean tree, which is the path `init` step 1 says to surface rather than adopt.
