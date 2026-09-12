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
| `.github/ISSUE_TEMPLATE/`, existing labels | the issue taxonomy already in use — adopt it rather than imposing one |
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

**Scaffold the mandatory set; offer the rest.** Count the two in their own units and they do not collide. **Ten of the thirteen skills** are in a minimum install — `init`, `prd`, `design-doc`, `backlog`, `sprint`, `spec`, `clarify`, `implement`, `worklog`, `archive` — and between them they produce **five documents** (`PRD`, design doc, backlog, spec, work log) and **three issue templates**. Five of those ten produce no document at all, which is why counting documents never finds them: `init` installs the harness, `sprint` produces issues, `clarify` a section inside a spec, `implement` code and a receipt, `archive` a `git mv` and a `Status` flip. The remaining three are opt-in, each for its own reason — `northstar`, because step 2's interview already produces the `- Owns:` anchor by another route; `epics`, because nothing consumes it mechanically; `contract`, because running it before there are commits and review findings to compile produces a *worse* rulebook rather than an absent one. Creating every document a large project would want, in a project that needed five, is how a harness gets abandoned in week two, so name the opt-in three and let the user choose rather than creating them by default. **Record the choice**: write `- Mode: minimum` or `- Mode: full` on one physical line in `.steering/tech.md`. It is declared rather than worked out later from which files happen to exist, because that derivation cannot tell a deliberate omission from an abandoned install — and that distinction is the only reason the line exists. What that choice governs is which documents are created and which skills are in the flow — never whether a skill can be run. Every skill ships with the plugin and is always available.

- **`.steering/product.md`** — what this project is, who uses it, what it deliberately is not, and a `- Owns: <quality property>` line the reviewer and the digest both read.
- **`.steering/tech.md`** — the stack, and the exact commands, with these machine-read lines:
  ```
  - Validators: <the gating commands, comma-separated>
  - Reviewer: <reviewer name>
  - Source globs: <git pathspecs for reviewable source, space separated, e.g. :(glob)**/*.ts :(glob)**/*.py>
  - Docs: <where inception documents live — `docs/` by default, or the path/URL of a shared documentation repo in a multi-repo product>
  - Mode: <minimum|full — which document set this project signed up for>
  ```
  The gates parse these, so a project changes its enforcement by editing steering rather than by editing hooks. Two consequences worth stating, because both fail silently:

  - **Each value must stay on one physical line.** The gates read them with `sed ... | head -1`, so a wrapped value is truncated at the first newline and the rest is lost without complaint.
  - **`Source globs` is a git pathspec, and `:(glob)` earns its place.** The value is interpolated unquoted, so a bare `*.py` is expanded by the shell against the repository root before git ever sees it — which in a `src/` layout matches nothing. `:(glob)` matches no file on disk, so the shell leaves the word alone and git receives the pattern intact.
- **`.steering/structure.md`** — where code belongs, and where tests mirror it.
- **The anchor check** — copy `assets/check-steering-anchors.sh` to the project's `scripts/` directory and add it to the `- Validators:` line. The machine-read lines above are read with exact expressions, and a value written in a form the reader cannot see produces nothing and no complaint: the file looks right, the gate runs on a default, and nobody finds out. This harness lost its own quality anchor that way for a week by writing `- **Owns: ...**` instead of `- Owns: ...`.
- **`.specs/README.md`**, **`.specs/_archive/README.md`**, **`.work_logs/README.md`** — each stating its contract.
- **`.github/ISSUE_TEMPLATE/`** — copy `feature.md`, `bug.md`, `chore.md`, and `config.yml` from the plugin's `assets/issue-templates/`, adapting labels to the ones this project already uses. The issue is the entry point to the whole flow: `backlog` creates typed issues, `spec` reads the type to choose its shape, and one issue becomes one spec, one branch, one PR. Leaving the entry point undefined leaves a hole in the middle of the process. `config.yml` sets `blank_issues_enabled: false` on purpose — an untyped issue makes `spec` guess, and it guesses feature, which is the wrong shape for a bug and for a chore. If the project has a reason to allow blank issues, say so and change it deliberately. If templates already exist, **merge rather than replace**: keep their wording and their labels, and add only the missing types. An existing template encodes decisions the team already made.
- **The document-set check** — copy `assets/check-document-set.py` to the project's `scripts/` directory and add it to the `- Validators:` line. This is the only route by which the mode reaches a gate: `quality-gate.sh` runs whatever that line names and knows nothing about modes, which is what keeps enforcement a property of the project rather than of the hook. A gate that branched on mode would be a switch that turns enforcement down. **Add it to the project's CI as well, beside its other validators** — the turn-end gate runs the `- Validators:` line only when a path matching `- Source globs:` changed, and a document is never source, so this is the one check that gate structurally cannot reach. **Skip it when `- Docs:` names another repository** — the documents cannot be verified from here, and the checker says so and exits non-zero rather than passing on a set it never read.
- **The reviewer** — from the closest reference implementation (`ts-reviewer`, `python-reviewer`, `dart-flutter-reviewer`), or from `agents/_template/` for an unrecognised stack. Copy the contract to `_shared/reviewer-contract.md` **inside the agents directory you are installing into** — `.claude/agents/_shared/reviewer-contract.md` for Claude Code, `.agents/_shared/reviewer-contract.md` for Antigravity. The reviewer names the relative form — which says where the file lives — **and** the concrete path for each harness, which is what it can actually open: a reviewer reads its own instruction with the project root as its working directory, so the relative form alone resolves to nothing. **Keep the concrete path for the harness this project uses; never leave only the relative form.** Trimming the other is optional, and leaving both is harmless. Then copy the plugin's `assets/check-locks.py` into the project's own scripts directory — the project has to be able to re-pin its rulebook, and telling it to run a script it was never given is how the lock quietly stops being checked. Then re-pin with `check-locks.py --update` after any edit, and add it to the project's CI beside its other validators.
- **The hooks** — render `hooks/templates/` for whichever harnesses the project uses, and copy `gate-lib.sh`, `quality-gate.sh`, `review-gate.sh`, and `steering-digest.sh` into the project's hooks directory. Only `{{FAST_CHECK}}` and `{{HOOKS_DIR}}` are substituted; the blocking quality gate ships as a script and reads the `- Validators:` line, so do not inline the validator commands into the settings file.
- **`AGENTS.md`**, with `CLAUDE.md` pointing at it, so one file is canonical.

**Populate every file. Never leave a `TODO` in a steering file.** An unpopulated steering file is worse than none: it teaches the agent that steering files are noise, and that lesson generalises to the ones you did fill in.

## Step 4 — Prove it works before declaring success

Do not report completion on files written. Verify:

1. Every gating validator runs clean on the current tree, and `quality-gate.sh` exits 0. Arm the gate on a green tree — otherwise the user's first turn is blocked by a failure that predates them, and their first act is to disable it.
2. `review-gate.sh` exits silently on the current branch — if it fires immediately, the scoping is wrong and the user's first experience of the harness is a false block.
3. Both gates actually block when they should: introduce a trivial lint violation, confirm `quality-gate.sh` fires, revert it.
4. **The reviewer is spawnable.** You just wrote it into the project's agents directory, and a subagent registered mid-session is usually not available until the harness restarts. Check whether it can actually be invoked — if it cannot, **say so and tell the user to restart before their first `implement`.** This is not tidiness. `implement` step 2 falls back to running the reviewer's procedure inline when it is not spawnable, which means the author of the diff reviews their own work. That fallback exists for good reasons and it still finds real defects, but it is not the independence the judgment layer is sold on — and on a fresh install it is not the exception, it is guaranteed. A restart costs seconds; a project whose every early review was a self-review does not find that out until someone reads the receipts.
5. Report what you verified, and anything you could not.

## Rules

- **Never overwrite an existing `.steering/`, `.specs/`, or `AGENTS.md` without showing a diff and getting agreement.** Merge into what is there.
- The directory names `.specs/`, `.steering/`, and `.work_logs/` are fixed. They are not configurable, because every skill body references them literally, and that is precisely what lets one copy of a skill serve every project without templating.
- If the project already has a harness from an earlier version, diff and upgrade rather than reinstalling.
- **A project that already carries a `- Mode:` line is an upgrade, never a fresh install.** Read the line first: offer to move `minimum` to `full` — creating only the documents the full set adds — and change nothing else. Re-running the scaffold over a project that already chose would recreate documents its author deliberately declined, which is the failure the mode was recorded to prevent.
- **Stop before adding configuration for its own sake.** If you find yourself designing a file that describes how to describe a language, the harness has drifted from its purpose: three concrete reviewers people copy beat one abstraction people configure.
