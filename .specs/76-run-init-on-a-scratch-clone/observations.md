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

## T2 — `init`, steps 1–4

Run through the Skill tool, plugin 0.4.2, Claude Code 2.1.252; every action performed by absolute path inside the clone.

### Step 1 — detect

**AC2 verified.** Detection read `pyproject.toml` (six `[tool.*]` sections; `ruff` at line length 100 with rules E, F, I, UP, B, SIM, RUF and E501 ignored under `tests/`; `mypy`; `pytest` with strict markers and config), one CI workflow (whose `run:` lines are the real commands), 14 test files under `tests/` with a `conftest.py` of builders, 50 commit subjects (38 prefixed: feat 14, docs 12, fix 5, test 3, refactor 2, perf 1, chore 1), four issue templates already present with labels `bug`, `enhancement`, `task`, a tracker with 14 labels including three project phases, and — under "what is already installed" — an `AGENTS.md` that still points at the stripped `.steering/` files, at `.claude/hooks/`, and at a `docs/CONTRACT.md` that survives and cites fifteen `MEAS-`/`PRV-`/`ADK-` rule ids whose rulebook was stripped with `.claude/agents/`. So detection did not meet a blank project; it met the shadow of the earlier install, which is what clarification 1 chose.

Every candidate validator was run on the clean clone before adoption:

| Command | Exit | Last line |
| :-- | :-- | :-- |
| `uv run ruff check` | 0 | All checks passed! |
| `uv run ruff format --check` | 0 | 52 files already formatted |
| `uv run mypy` | 0 | Success: no issues found in 43 source files |
| `uv run pytest` | 0 | 393 passed, 106 warnings in 6.28s |
| `uv lock --check` (CI only) | 0 | Resolved 78 packages |

All four adopted. T1's prediction that the tests would need a git-ignored `.env` was wrong: the suite is offline by design. The known-failing path was therefore **not exercised** at step 1 — it was exercised at step 4 instead, by a file the skill installed.

### Step 2 — ask

**AC3 verified.** Five questions, each with the recommendation detection produced, all five **answered as recommended**: measurement integrity as the owned property (from the project's own `AGENTS.md`); no source of truth above the repository, `Docs: docs/`; all four toolchain commands gating, `uv lock --check` CI-only; the detected conventions confirmed (Conventional Commits with a `Refs:` footer, `feat/<kebab>` feature branches, `<issue>-<kebab>` spec branches); and three things the reviewer must never flag (E501 under `tests/`, warnings on a green run, an unexercised billed path). Step 3's separate offer of the optional set was taken up for `northstar`. As in every run so far: accepted-as-recommended cannot be told from right, and the recommendations were derived from the project's own kept files, so this was not a cold interview.

### Step 3 — write

**AC4 verified.** Written: `.steering/product.md`, `tech.md`, `structure.md` (five machine-read lines; `check-steering-anchors.sh` in the clone at 5 of 5), `.specs/README.md`, `.specs/_archive/README.md`, `.work_logs/README.md`, `.claude/settings.json` (the template rendered with `{{FAST_CHECK}}` = the two ruff commands and `{{HOOKS_DIR}}` = `.claude/hooks`, merged into the `{}` the strip left), `.claude/hooks/` (four scripts), `.claude/agents/python-reviewer.md` with `_shared/reviewer-contract.md` beside it and the reference rulebook and lock, `scripts/check-steering-anchors.sh`, `scripts/check-locks.py`. Merged into rather than replaced: the issue templates (all four byte-identical to the plugin's assets, so the merge was a no-op), `AGENTS.md` (already canonical with `CLAUDE.md` pointing at it, and pointing at the files just recreated — no diff needed, none shown). Re-pin: `./scripts/check-locks.py --update` in the clone printed `2 pinned file(s) match their locks in .claude/agents`, exit 0 — the copied lock matched the copied rules, so the rewrite path ran on unchanged files again.

### Step 4 — prove

**AC5 verified, after two rounds.** On the tree the skill had just armed, `quality-gate.sh` exited **2**: `ruff format --check` named one file, `scripts/check-locks.py`, the copy `init` installed from `assets/`. The project's earlier copy of the same script, differing by 106 lines, was format-clean. Fixing per the author's answer (format the copy) left `ruff check` red on the same file — I001 import order, UP017 `datetime.UTC`, E501 at 101 columns — and a second fix cleared it. Then: quality gate exit 0 on the clean tree; `review-gate.sh` exit 0 with `{}` on `main`; a probe file with an unused import made the fast check exit 1 and the quality gate exit 2 with `F401` in the message and the Antigravity JSON line on stdout; the revert returned both to 0. **Step 4.4:** the reviewer written into the clone is not registered in this session — no subagent by that name exists here — so a first `implement` in the clone would run the reviewer inline until a restart, as the skill says to tell the user.

**AC6 — what did not join.**

- **`init` armed the gate red with its own file.** `assets/check-locks.py` at 0.4.2 fails `ruff format --check` and `ruff check` under a common configuration — line length 100, isort, pyupgrade — and this repository's CI never runs ruff on `assets/`. That is CAP-4's falsifier, produced by the harness rather than by the project, and step 4.1 caught it only because the operator ran the gate rather than reporting on files written. A consumer who trusted step 3 would have their first turn blocked by the harness's own script.
- **The stripped path cannot restore a project-compiled rulebook.** `docs/CONTRACT.md` cites fifteen ids; the reference `python-reviewer` rulebook carries none of them. `init` has no step that reads an existing `CONTRACT.md` and compiles its Judgment rows, so after this install the contract points at rules the reviewer does not have. The upgrade path — out of scope here — is the one that would have kept them.
- **The reviewer contract's path is wrong in every installed layout.** The shipped `python-reviewer.md` says *"Read `agents/_shared/reviewer-contract.md` first"*. In a project that path does not exist; the skill says to copy the contract "next to" the reviewer, the earlier install put it at `.claude/agents/reviewer-contract.md`, `docs/layout.md` draws it there, and this run put it under `.claude/agents/_shared/` and edited the reviewer's line to match. Three placements, one sentence, and a reviewer that cannot find its contract is told by that contract to stop.
- **`AGENTS.md` describes the pre-#30 flow** — *"(review the spec PR)"* and `archive` as a step — and the skill's rule not to overwrite `AGENTS.md` without a diff means the stripped path leaves it; only the upgrade path could correct it, and nothing in the skill says to.
- **Step 3 has no source for the three READMEs.** `.specs/README.md`, `.specs/_archive/README.md` and `.work_logs/README.md` are "each stating its contract", with no template in the plugin; they were copied from this repository's own dogfood files, which a consumer does not have.
- **The skill declared nothing.** Step 4.5 says report what was verified; the operator did. A model following the text could report completion after step 3, which is the sentence *"Do not report completion on files written"* exists to prevent — and on this run, doing so would have shipped a red gate.

### Not exercised

- The known-failing path at step 1, and the omit and record-as-known-failing answers at step 4.
- Templates that differ from the plugin's, and an `AGENTS.md` that needs a diff shown.
- A cold interview: every recommendation came from files the project already had.

## T2, continued — `northstar` in the clone, the opt-in taken at step 3

Run through the Skill tool. Four questions to the author — the metric, the levers (multi-select), the laws' order, the non-negotiable — each with a draft derived from the project's kept `AGENTS.md`; **all four answered as drafted**, every lever selected. `docs/NORTH_STAR.md` written in the clone: one page, four levers with `LV-` ids (the project had no lever vocabulary; `LV-` chosen as in #55), three laws ordered with the worked example, a non-negotiable that costs something, and an `Owns` section.

**Step 6, the collision path — not exercised, for the same reason as #55.** The derivation from the laws produced *measurement integrity*, the value `init` had written into `.steering/product.md` minutes earlier from the interview's first answer. Equal, so nothing was written and `product.md` is byte-identical before and after. The path where `northstar` disagrees with an existing `Owns:` line is still unobserved, and this run shows why it is hard to reach: both values come from the same author in the same session, and the skill has no instruction for the case anyway.

Not exercised: `northstar` on a project whose `product.md` has no `Owns:` line at all — `init` always writes one first, so on this skill order the write-back at step 6 can only ever agree, disagree, or be redundant; it is never the first write.
