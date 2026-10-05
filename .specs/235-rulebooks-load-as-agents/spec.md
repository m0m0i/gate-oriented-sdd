# Spec: the plugin registers its reviewers' rulebooks, contract and template as agents, and CLAUDE.md sits at the plugin root
- Slug: 235-rulebooks-load-as-agents   Issue: 235   Type: bug   Status: approved
- Author: m0m0i   Date: 2026-10-05

## 1. Requirements (WHAT / WHY)

- Reproduction: the issue's, measured again on 2026-10-05 at `322e6cf` with Claude Code 2.1.289, which is also npm's latest.
  - `claude plugin validate . --strict` fails with the issue's nine warnings. Run here at `dbf51df` with the manifest's `agents` key set (Clarifications, Q1); the issue's run at `022372b` is the one without it.
  - `agy plugin validate .` (Antigravity CLI 1.2.16) reports `agents : 8 processed` for a plugin with three reviewers.
  - A headless session with `--plugin-dir .` (the installed copy disabled, hooks off) reports twelve `gate-sdd:` entries in the `agents` list of its `init` message: the three reviewers, the six rulebooks, `_shared:reviewer-contract`, `_template:rules:starter` and `_template:{{REVIEWER_NAME}}`.

- Expected: a session that loads the plugin gets no agent the plugin cannot stand behind, and strict validation passes on the current CLI. `README.md:35` says the rulebooks and the contract "are not registered components at all".

- Actual: nine of the twelve are reference files and a template. Each puts a description into every session, and invoking one runs a rulebook with no instructions.

- Impact: every install, in every session. CI is held at 2.1.288 by a pin that can only move with this issue, so the required validation job checks against a CLI that goes stale.

- **Root cause:** Claude Code registers every Markdown file under a plugin's `agents/`, at any depth, Antigravity's plugin loader processes the directory too, and this repository uses `agents/` for two different things. It is where the harness looks for plugin agents, and it is where `init` copies a reviewer and its rulebook *from*. Only the second use is real. A shipped reviewer names its contract at `.claude/agents/_shared/reviewer-contract.md` (#217) and its rules at `rules/…` beside itself, and both exist only in a project after `init` has copied them. So the three reviewers do not work as plugin agents either. After `init` they are duplicates of the project's own adapted, pinned reviewer, under names a model can pick in its place. The rulebooks registering is the visible part of that. `CLAUDE.md` is the same confusion one level up: the plugin root is also this repository's working tree, and the validator reads the root as plugin content.

- Acceptance criteria:
  - [ ] **AC1:** WHEN a Claude Code session loads the plugin, THE `agents` list of its `init` message SHALL hold no `gate-sdd:` entry.
  - [ ] **AC2:** `claude plugin validate . --strict` SHALL pass with no warning on the latest CLI, and CI SHALL install the CLI unpinned.
  - [ ] **AC3:** WHEN the plugin root holds an `agents/` directory or a `CLAUDE.md`, `scripts/check-manifests.py` SHALL fail and name it. The case fails before the fix and passes after.
  - [ ] **AC4:** WHEN a reviewer file under `reviewers/` lacks frontmatter with a `name` equal to its filename and a `description`, or a file under `reviewers/*/rules/` or `reviewers/_shared/` carries frontmatter, `scripts/check-manifests.py` SHALL fail and name the file.
  - [ ] **AC5:** WHEN a session starts in this repository under `claude-md-or-agents-md`, `AGENTS.md` SHALL be in its context with no tool call, as #237 measured it.
  - [ ] **AC6:** the tree `init` writes into a project (`.claude/agents/`, `.agents/agents/`) SHALL NOT change. `assets/check-locks.py` SHALL verify the same six shipped rulebooks at their new place and keep scanning both installed directories. Every guard that names a shipped reviewer path keeps its verdict on its existing cases.
  - [ ] **AC7:** no document or guard names a plugin path under `agents/`, except records of their time (`.specs/`, `.work_logs/`, `docs/BACKLOG.md`, and the dated sections of `docs/verified.md`). `docs/fidelity.md` stops saying Antigravity discovers no agent files, which the measurement above contradicts for a plugin. And `README.md`'s always-on figure and its "not registered components" sentence are re-measured and true, in both READMEs.

- Out of scope:
  - #239, the form of the pointer `init` writes for a consumer. AC5's measurement (`.claude/CLAUDE.md` with `@../AGENTS.md` loads) is evidence for it and is recorded in `docs/verified.md`, not acted on here.
  - #19, a lock for this repository's own reviewer.
  - #249 (Clarifications, Q4). The three guards that list the reviewers by filename keep their lists, renamed.
  - Migration for existing installs, by the user's decision (Clarifications). The installed tree does not move (AC6), so none is needed there.

### Clarifications

Asked and answered 2026-10-05.

- **Q1. The manifest's `agents` list stops the nine registering (twelve to three, measured) but the validator walks `agents/` whatever the manifest says, so all nine warnings stay. Allow-list them in CI, keep the pin, or move the files?** "I want to get this right, because it's still under development." Then, asked where the files should go: "the best way for this tool, you don't need to consider the migration, suggest the ideal way." → the Design below is that suggestion, and it goes further than the two locations offered: the reviewers move too (Root cause). Accepted 2026-10-05: "go ahead and proceed with 235".
- **Q2. Move `CLAUDE.md` to `.claude/CLAUDE.md`?** Yes. → AC5.
- **Q3. Does Antigravity compatibility hold?** Measured: `agy plugin validate` on the moved tree reports `skills : 13 processed` and `agents : skipped (not found)`, and passes. A missing `agents/` is an optional component, as `commands`, `mcpServers` and `hooks` already are.
- **Q4. Should the reviewers be decoupled from the workflow, as connectors?** The move is the first step and the only one taken here. The rest is #249, filed at the user's direction: guards that discover a reviewer instead of listing it, a pinnable reviewer for a stack with no reference one, and `init` reading a reviewer from any directory of this shape. ADR-7 records the direction.
- **Not asked, because measurement answers it:** a tree with `agents/` renamed to `reviewers/` and `CLAUDE.md` under `.claude/` passes strict validation on 2.1.289 with no warning, and a session loading it registers no `gate-sdd:` agent and all thirteen skills. A project's own `.claude/agents/<reviewer>/rules/*.md` and `_shared/reviewer-contract.md` do not register: this repository has both and a session here lists only `gate-sdd-reviewer`.

## 2. Design (HOW)

- **Fix approach.** The plugin ships no agents. `agents/` becomes `reviewers/`, moved whole, and nothing inside it changes shape:

  | Now | After |
  | :-- | :-- |
  | `agents/<name>.md` | `reviewers/<name>.md` |
  | `agents/<name>/rules/*.md`, `rules-lock.json` | `reviewers/<name>/…` |
  | `agents/_shared/reviewer-contract.md` | `reviewers/_shared/reviewer-contract.md` |
  | `agents/_template/` | `reviewers/_template/` |
  | `CLAUDE.md` | `.claude/CLAUDE.md`, importing `@../AGENTS.md` |

  - `reviewers/` has the shape of the directory `init` writes, so installing a reviewer is a copy of `<name>.md`, `<name>/` and `_shared/` with no path rewritten. The rulebook still lives in its reviewer's directory, in the source as in the install, which is ADR-2.
  - The top level then reads as the layers `AGENTS.md` names: `skills/` for process, `hooks/` for deterministic checks, `reviewers/` for judgment. Neither `hooks/` nor `reviewers/` is registered by the plugin. Both are rendered into the project by `init`, because a gate and a reviewer must both run against the project's own files.
  - **Narrower,** the manifest list this branch first held. It fixes the install and leaves CI pinned, the three unusable plugin agents registered, and `claude plugin details` reporting no agents. **Narrower still,** an allow-list around the validator, which is an enforced check turned into a parsed one. **Sideways,** `assets/reviewers/`. It needs no new shipped path, but it files the product's second idea under "files copied into projects" beside the issue templates, and `assets/` is the path CI lints as code a consumer runs.

- **Affected files:**
  - Moved: everything under `agents/`, and `CLAUDE.md`.
  - Guards: `scripts/check-manifests.py` (AC3, AC4), `assets/check-locks.py` (`CANDIDATE_DIRS`: `agents` becomes `reviewers`), `scripts/check-contract-path.py`, `scripts/check-receipt-schema.py`, `scripts/check-reviewer-allow-list.py`, `scripts/check-markdown-fences.py`, `scripts/check-version-bump.py` (`SHIPPED`), `scripts/package-release.py`, `scripts/test-gates.sh`.
  - Machine-read: `- Source globs:` in `.steering/tech.md`.
  - Shipped prose: `skills/init/SKILL.md`.
  - CI: `.github/workflows/ci.yml` loses the pin and its comment.
  - Documents: `AGENTS.md`, `.steering/structure.md`, both READMEs, `CONTRIBUTING.md`, `docs/layout.md`, `docs/DESIGN.md`, `docs/PRD.md`, `docs/CONTRACT.md`, `docs/fidelity.md`, `docs/verified.md` (a new dated section; older ones are records and stay), and a new `docs/decisions/ADR-7` for "the plugin ships no agents", which ADR-2 gains one line pointing to.
  - Dogfood: `.claude/agents/gate-sdd-reviewer.md` and its `rules/claims-and-prose.md`, where C-6 names the shipped paths and C-7 the rulebook path.
  - The manifest list and its case, uncommitted on this branch from 2026-10-04, are dropped. Shipped paths move, so `implement`'s version step bumps the minor.

- **Blast radius:**
  - **Anyone invoking `gate-sdd:<lang>-reviewer` directly** loses it. Root cause is why that is the fix and not a cost: the agent names a contract and rules that exist only after `init`.
  - **The validator no longer reads the reviewers' frontmatter**, because they are no longer agents. AC4 replaces that, and adds the half the validator never had: C-7, frontmatter on a rulebook, is judgment today and matters most in the installed directory, where a file with frontmatter does register.
  - **`assets/check-locks.py` is copied into projects.** A project's copy scans `.claude/agents` and `.agents/agents`, which do not change. It stops scanning a top-level `agents/` and starts scanning a top-level `reviewers/`, which only this repository has.
  - **Antigravity.** `rules/AGENTS.md`, its symlink, is untouched. `implement` registers a reviewer from the project's file with `define_subagent`, never from the plugin's `agents/`, so what the loader stops processing is the same nine non-agents and the same three reviewers that name a contract only `init` installs. What the Antigravity runtime did with the eight it processed was not measured.
  - **`README.md:35`'s figure** falls, since three reviewer descriptions leave every session. `claude plugin details` is the measurement.

- **Why this cannot recur:** AC3 makes "something under the plugin's `agents/`" a failing turn locally, where the validator is too slow to sit on the `- Validators:` line. AC2 puts the upstream validator, unpinned and strict, on every pull request, so the next thing it learns to see arrives as a red check with a cause.

## 3. Tasks (TDD-ordered)
> One task is one complete Red-Green-Refactor cycle, so one green commit. No task is sequenced after the review.
- [x] T1: cases for AC3 (an `agents/` directory, a root `CLAUDE.md`), red. Then the move in the table, `check-manifests.py`'s guard, and every guard, glob and fixture under Affected files that names a moved path → suite green (AC6).
- [x] T2: cases for AC4 (a reviewer with no frontmatter, one whose `name` is not its filename, a rulebook with frontmatter, the contract with frontmatter), red. Then the check → green.
- [x] T3: `skills/init/SKILL.md` and every document under Affected files, with ADR-7. Re-measure AC1, AC2, AC5 and `README.md:35`, and record them in `docs/verified.md` (AC7).
- [ ] T4: unpin CI.
