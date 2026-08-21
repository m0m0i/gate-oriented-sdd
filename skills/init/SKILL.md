---
name: init
description: Set up this SDD harness in a project — detect the toolchain, interview for what cannot be inferred, and write .steering, .specs, .work_logs, a project-specific reviewer, and the hooks. Use once per project, or to migrate a project that already has parts of the harness.
---

# init — Install the harness into a project

Runs **inside** the target project. It interviews the repository first and the user second, because most of what varies is discoverable and asking about it wastes the one resource the user actually spends: attention.

Migration is the common case. **Treat a greenfield repo as the special case, not the default.**

## Step 1 — Detect, don't ask

Read before asking anything:

| Signal | Tells you |
| :-- | :-- |
| lockfiles, `package.json`, `pyproject.toml`, `pubspec.yaml`, `go.mod`, `Cargo.toml`, `Gemfile` | language and package manager |
| scripts/tasks in those files, CI workflow files | the real validator commands — the ones that already pass |
| existing test directories and naming | the test runner and where tests live |
| `git log --format=%s -50` | the commit convention actually in use, not the one in CONTRIBUTING |
| `git remote -v`, existing PR templates | the tracker and default branch |
| existing `.claude/`, `.agents/`, `CLAUDE.md`, `AGENTS.md`, `.specs/` | what is already installed, and what you must not overwrite |

**Run each candidate validator before adopting it.** A command copied from a README that fails on a clean checkout will make the quality gate block every turn from day one, and the user will disable the gate rather than debug it. If a validator fails on a clean tree, say so and ask whether to fix it, omit it, or record it as known-failing.

## Step 2 — Ask only what is left

At most five questions, highest consequence first, each with a recommended answer:

1. **What quality property does this project own?** Correctness, latency, safety, accessibility, cost — the one a defect would most damage. This anchors every severity in the reviewer, so it is the question worth spending the most on. There is no good default; ask.
2. **Is there a source of truth above this repo** — a design hub, an ADR set, a shared contract — and how are its documents referenced?
3. **Which validators are gating** (block a turn) versus advisory (report only)?
4. **Confirm the detected commit convention and branch naming.**
5. **Anything the reviewer must never flag** — a deliberate deviation it would otherwise read as a violation.

## Step 3 — Write

- **`.steering/product.md`** — what this project is, who uses it, what it deliberately is not, and a `- Owns: <quality property>` line the reviewer and the digest both read.
- **`.steering/tech.md`** — the stack, and the exact commands, with these machine-read lines:
  ```
  - Validators: <the gating commands, comma-separated>
  - Reviewer: <reviewer name>
  - Source globs: <globs that count as reviewable source, e.g. '*.ts' '*.py'>
  ```
  The gates parse these, so a project changes its enforcement by editing steering rather than by editing hooks.
- **`.steering/structure.md`** — where code belongs, and where tests mirror it.
- **`.specs/README.md`**, **`.specs/_archive/README.md`**, **`.work_logs/README.md`** — each stating its contract.
- **The reviewer** — from the closest reference implementation (`ts-reviewer`, `python-reviewer`, `dart-flutter-reviewer`), or from `agents/_template/` for an unrecognised stack. Copy `_shared/reviewer-contract.md` next to it. Re-pin with `check-locks.py --update` after any edit.
- **The hooks** — render `hooks/templates/` for whichever harnesses the project uses, and copy `gate-lib.sh`, `review-gate.sh`, and `steering-digest.sh` into the project's hooks directory.
- **`AGENTS.md`**, with `CLAUDE.md` pointing at it, so one file is canonical.

**Populate every file. Never leave a `TODO` in a steering file.** An unpopulated steering file is worse than none: it teaches the agent that steering files are noise, and that lesson generalises to the ones you did fill in.

## Step 4 — Prove it works before declaring success

Do not report completion on files written. Verify:

1. Every gating validator runs clean on the current tree.
2. `review-gate.sh` exits silently on the current branch — if it fires immediately, the scoping is wrong and the user's first experience of the harness is a false block.
3. The quality gate actually blocks when it should: make a trivial violation, confirm it fires, revert it.
4. Report what you verified, and anything you could not.

## Rules

- **Never overwrite an existing `.steering/`, `.specs/`, or `AGENTS.md` without showing a diff and getting agreement.** Merge into what is there.
- The directory names `.specs/`, `.steering/`, and `.work_logs/` are fixed. They are not configurable, because every skill body references them literally, and that is precisely what lets one copy of a skill serve every project without templating.
- If the project already has a harness from an earlier version, diff and upgrade rather than reinstalling.
- **Stop before adding configuration for its own sake.** If you find yourself designing a file that describes how to describe a language, the harness has drifted from its purpose: three concrete reviewers people copy beat one abstraction people configure.
