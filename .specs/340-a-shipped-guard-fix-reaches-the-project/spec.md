# Spec: a guard fix the plugin ships reaches every project by update

- Slug: 340-a-shipped-guard-fix-reaches-the-project   Issue: 340   Type: bug   Status: draft
- Author: m0m0i (Claude Code)   Date: 2026-11-01
- **Depends on #309**, by the maintainer's decision (C5): it ships first, so that the document checks this spec arms in every project have a state a project installed before `- Mode:` can declare.

Backlog row 1's third issue, after #324 with #330, #302 and #329. It decides how a project runs the guards `init` copies today, and what an existing install's copies become. #343, the row's last issue, re-runs `init` on Antigravity and follows this spec's answer (#343's AC5).

## 1. Requirements (WHAT / WHY)

- **Reproduction:**
  1. Run `init` on a Claude Code project. Step 3 copies `assets/check-steering-anchors.sh`, `assets/check-document-set.py` and `assets/check-document-cascade.py` into the project's `scripts/` and puts them on the `- Validators:` line (`skills/init/SKILL.md:64`, `:67`, `:68`). It copies `assets/check-unreviewed-work.sh` into `scripts/` for CI (`:69`), and `assets/check-locks.py` into `scripts/` and `reviewers/_shared/reviewer-contract.md` into the agents directory (`:70`).
  2. Ship a change to one of those files in a new plugin version. 0.39.0 is one: #329 added a section to the reviewer contract, and its release notes tell a Claude Code project to re-run `init` to get it.
  3. Update the plugin in the project, start a new session, and end a turn that changes source.
- **Expected:** the project runs the shipped version. PRD CAP-5 says the user can "receive a shipped fix in every project by updating, without copying files" (`docs/PRD.md:49`), and LV-5 says the same (`docs/NORTH_STAR.md:27`). On Claude Code the gates already meet this, since #256 moved them into the plugin (ADR-8).
- **Actual:**
  - The gate runs the project's old copy. Nothing reports that it is stale: no guard compares itself with the plugin's (ADR-9's consequences say so: "A copied check can still fall behind the plugin. Nothing reports that except the README's comparison command").
  - The only route to the fix is a copy by hand. `README.md:226-235` lists the copies a plugin update does not reach and gives a diff loop. `init`'s pre-0.23.0 migration re-copies two of them and compares the rest (`skills/init/SKILL.md:75`). Nothing tells a project already past 0.23.0 to do either.
  - #263 is what a stale copy costs: a copy of the anchor check from before 0.23.0 blocked every turn that changed source until it was re-copied. That one failed closed; a stale copy that misses what a fix adds would pass instead.
- **Impact:**
  - Every Claude Code project, on every guard fix. The open fixes waiting on this include #308 and #338, both in `check-document-cascade.py`, and every fix to the anchor check, which every project's `- Validators:` line runs.
  - On Antigravity the same copies sit in `scripts/`, beside gates that reach a project only by re-running `init` (`skills/init/SKILL.md:72`).
  - Triaged MEDIUM on the issue. Nothing passes today that should block, but a fix that would make a guard block does not reach the project that needs it, so the copies are where a future fail-open would hide.
- **Root cause:**
  - **The guards were made project files when the gates were too.** `init` copies each one "to the project's `scripts/` directory", and two of them say they are the project's: `check-document-set.py` (`:25-27`) and `check-locks.py`, which "lives in assets/ because it is one of the few files a project needs a COPY of rather than a reference to" (`:10-12`). While the gates were copies as well, a copied guard cost nothing extra.
  - **#256 moved the gates and left the guards.** ADR-8 took the Claude Code gates out of projects. #263 and ADR-9 then taught the two shell guards to find the plugin's `gate-lib.sh` through `CLAUDE_PLUGIN_ROOT` at turn end, `GATE_SDD_PLUGIN_ROOT` in the session's shell and `GATE_SDD_HOOKS` in CI. ADR-9 rejected moving the guards themselves: "The `- Validators:` line is one line both harnesses' gates run, and a plugin path resolves nowhere in a dual-target project or a terminal" (ADR-9, Alternatives).
  - **No one variable names the plugin everywhere the line runs.** `CLAUDE_PLUGIN_ROOT` is set at a Claude Code turn end and not in the session's shell. `GATE_SDD_PLUGIN_ROOT` is set in the session's shell and not at turn end (`docs/verified.md`, P1 and P4). CI has only `GATE_SDD_HOOKS`, which names the plugin's `hooks/`. An Antigravity hook or shell has none. So the line names project paths, and a project path holds whatever `init` copied there last.
  - **`check-locks.py` is tied to being a copy.** It takes its root from its own location (`ROOT = pathlib.Path(__file__).resolve().parent.parent`, `:44`). Run from the plugin's `assets/`, it would verify the plugin's own rulebooks and pass without reading the project's: a pass about the wrong tree.
- **Acceptance criteria.** The **harness checks** are `check-steering-anchors.sh`, `check-locks.py`, `check-document-set.py` and `check-document-cascade.py`: the guards that check the harness's own files. **The runner** is the one command that runs them.
  - [ ] **AC1:** WHEN a plugin update changes a harness check THE SYSTEM SHALL run the changed check in a Claude Code project with no file in the project copied or edited: at turn end, by hand in the session's shell and in a subagent's, and in CI with the plugin checkout at `ref: main`. A CI checkout pinned to a tag runs that tag's checks until the workflow moves it, and the README and `docs/fidelity.md` say so. `check-unreviewed-work.sh` stays CI-only and runs there from the same checkout. A recorded pass does not outlive a change to the runner, to any check it runs, or to a steering value it reads.
  - [ ] **AC2:** WHEN `.steering/tech.md` is present and readable THE quality gate SHALL run the runner from its own tree, the one it was loaded from, before the project's `- Validators:` commands. It does so even when that line is empty or absent, and needs no variable at turn end. The runner and the validators are numbered together, so the timeout block and the signal block name the right one. The line holds only the project's own commands.
    - A missing harness check, or one that cannot be run, fails closed and names its path.
    - Each check reads the library of its own tree, never another copy.
    - No variable, flag or file present in a project makes the gate skip the runner.
    - The absent-`tech.md` pass stays. Because the runner runs on an empty line too, a `- Validators:` line the reader cannot see, such as `- **Validators: ...**`, now blocks through the anchor check, where today it passes having run nothing.
  - [ ] **AC3:** WHEN a harness check runs by hand THE SYSTEM SHALL offer one runner command for each place it can run:
    - the session's shell and a subagent's;
    - CI;
    - a terminal;
    - Antigravity;
    - this repository.

    The digest SHALL print the command for the tree it ran from. Where that command depends on a variable, it names the remedy when the variable is unset rather than running nothing. The runner says which tree it ran from, and ends with a line naming each check that failed. `implement`, the reviewer contract, the reference reviewers and the template reviewer say to run it beside the `- Validators:` line.
  - [ ] **AC4:** WHEN `check-locks.py` runs, from any location, THE SYSTEM SHALL verify the rulebooks of the repository the working directory is in, and fail closed outside one. `--update` SHALL write only that repository's locks. The gate and the runner never pass it. The re-pin command is named for each place, in the drift message, `init` and `contract`.
  - [ ] **AC5:** WHEN `- Docs:` names another repository THE SYSTEM SHALL report the two document checks as not applicable, the condition under which `init` installs neither today. WHEN `- Mode:` is missing THE SYSTEM SHALL block with the document-set check's remedy, never assume a mode. #309 ships first and makes that remedy one a project installed before `- Mode:` can follow (C5).
  - [ ] **AC6:** WHEN `init` installs an Antigravity project THE SYSTEM SHALL copy the runner, the harness checks and `check-unreviewed-work.sh` into `.agents/hooks/` with the gates, as one set that a re-run refreshes (C2). `docs/fidelity.md` says CAP-5 is unmet on Antigravity for the guards as for the gates. WHEN `.agents/hooks/quality-gate.sh` exists with no runner beside it THE anchor check SHALL fail, at a Claude Code turn end in a dual-target project and in CI. That is the one state where a turn end could run an old gate copy with no checks to run.
  - [ ] **AC7:** WHEN a Claude Code session starts THE digest SHALL print a one-line, non-blocking notice, worded as a fact:
    - if the project's `.claude/agents/_shared/reviewer-contract.md` differs from the copy in the tree the digest ran from, naming the command that refreshes it (C3);
    - if the line still names a copy of a harness check.
  - [ ] **AC8:** WHEN `init` meets an existing install THE SYSTEM SHALL, showing each change as a diff first:
    1. make sure every project-side gate copy carries a runner before any guard entry leaves the line. On Antigravity it refreshes the `.agents/hooks/` set. On Claude Code, the existing pre-0.23.0 migration deletes any `.claude/hooks/` copy, and no gate is ever written there.
    2. remove the guard copies in `scripts/`, asking first about any the project edited;
    3. drop each `- Validators:` entry that names a harness check, whatever its prefix, and list any entry it cannot match;
    4. point CI at the plugin checkout;
    5. propose the runner to every project reviewer whose allow-list names the validators, whether it copies the line or names it.

    WHEN `init` installs a project fresh THE SYSTEM SHALL copy no guard into `scripts/`.
  - [ ] **AC9:** every statement of where the guards live, or of what gates a turn, says what is true after this branch:
    - **A new ADR-10.** It supersedes ADR-9's two rejected alternatives, "ship the checks from the plugin" and "the digest prints the path", and ADR-9's drift consequence, and records that #110 AC5's "only through the `- Validators:` line" now has the gate's runner beside it.
    - **The READMEs.** `README.md` and `README.ja.md`, with identical claims.
    - **The repository's other documents.** `AGENTS.md`, `docs/fidelity.md`, `docs/DESIGN.md`, `docs/layout.md`, `.steering/structure.md`, `hooks/templates/README.md`, and the premise of `docs/CONTRACT.md` M-16.
    - **The gates and guards.** The gate's own header and block text, and the guards' docstrings and messages.
    - **CI's comments.** The comments in `.github/workflows/ci.yml` that state the line is the only authority. These are comments only; no job changes.
    - **This repository's own steering and reviewer.** Its `- Validators:` line, and its reviewer's allow-list, which `check-reviewer-allow-list.py` then requires to name the runner.
  - [ ] **AC10:** `docs/verified.md` records three runs, with the Claude Code version (C4):
    - **A two-version update.** A scratch project, installed from a local marketplace at one version and updated with a real `claude plugin update` to a scratch-local next version with one changed check. The gate, a by-hand run and a subagent all run the changed check.
    - **The stale root.** The stale `GATE_SDD_PLUGIN_ROOT` observed in this session: 0.38.0 named, 0.39.0 installed, the old directory still on disk.
    - **A real migration.** One real consumer project migrated by `init` as this branch states it, on a branch whose pull request's CI runs, with the plugin checkout pinned to this branch's head. The project is described by toolchain only.
  - [ ] **AC11:** T1's first case fails against `b0a71bd` for the reason in the reproduction: the line names a stale copy that passes, while the plugin's changed check would block. Every other new case fails against `b0a71bd` and passes after.
- **Out of scope:**
  - **The safe re-run.** Re-running `init` over `.agents/hooks/` and `.agents/hooks.json`, and telling a project's edit from an older version's text, are #343. AC8 fixes the order the guards move in, and #343 makes the re-run safe.
  - **#309 itself.** It is a prerequisite (C5), not part of this branch.
  - **The cascade fixes themselves**, #308 and #338.
  - **Cloud sessions**, where no plugin loads: #261, parked.
  - **Antigravity's plugin update**, which CLI 1.2.16 does not have (`docs/verified.md:322`).

### Clarifications

Asked and answered 2026-11-01. Before asking, two read-only workflows mapped the repository and attacked four candidate mechanisms against every place the line runs: a dispatcher copied once, a variable chain on the line, the gate running the guards, and copies with a staleness detector. The judge ranked them C > A > B > D. After the draft, three critics and their refuters found sixteen defects in its statement; each is folded in above, and C5 came from one of them.

- **C1. How does a Claude Code project run the harness's guards?** The gate runs them, from the tree it was loaded from, and the line keeps the project's own commands. The dispatcher kept its root lookup as a copy on every entry's path. The variable chain had no answer for Antigravity and, like the dispatcher's by-hand route, reads a root that can be stale. The detector enforces the copying CAP-5 rules out. → AC1–AC3, Design.
- **C2. What happens on Antigravity?** Its guards join the gate copies in `.agents/hooks/`, refreshed together by a re-run of `init`, and `docs/fidelity.md` says CAP-5 is unmet there. Baking the observed install path into the rendered hooks file was rejected: it was seen only on CLI 1.3.3, reaches no session shell, and the rendered file never updates. → AC6.
- **C3. What reports a stale contract copy?** A non-blocking notice in the Claude Code digest. A blocking check would block every project on every contract release, and CI's checkout of `main` would go red before the release ships. A stale contract is not a gate passing what it should block. → AC7.
- **C4. What proves it?** A scratch two-version run, plus one real consumer migration with a pull request whose CI runs, as #263 did. The maintainer names the project when T7 starts, and nothing is pushed there without the maintainer's go. → AC10.
- **C5. A project with no `- Mode:` line.** Once the gate runs the document checks everywhere, such a project, installed before 0.6.0, blocks, as the document-set check has always refused an absent line. #309 measured that no value passes there today, so #309 ships before this branch. Reporting the checks as not applicable was rejected: deleting the line would turn them off. → AC5.

## 2. Design (HOW)

- **Fix approach.** The harness's own guards become part of the gate, not of the line.
  - **The runner, `hooks/harness-checks.sh`.** It is shipped, and it lives in `hooks/` so that Antigravity's copy set takes it with the gates.
    - **Its tree.** It finds its tree from `$0`. With `../.claude-plugin/plugin.json` beside its directory, the checks are in `../assets/`: the plugin, the release zip and this repository. Otherwise they sit flat beside it, which is Antigravity's `.agents/hooks/`. The layout is read from that marker, never from which files happen to exist.
    - **How it runs them.** It moves to the git toplevel and runs each harness check in a fixed order, with `GATE_SDD_HOOKS` set to its own tree's hooks directory. So a check and its library always come from one tree. Neither an exported `GATE_SDD_HOOKS` nor a dual-target project's `.agents/hooks/` can pair a new check with an old library.
    - **Its verdict.** It runs every check and reports each one, then ends with a line naming each that failed, since a block shows only the last 20 lines. It exits non-zero if any failed, or if a check is missing or cannot be run. Unlike the hooks template's `[ -f x ] || exit 0`, it never treats a missing file as a pass.
    - **Its header.** It prints the tree it ran from and that tree's version where a manifest gives one, so a by-hand run under a stale root is visible.
    - **No writes.** It writes nothing, never passes `--update`, and reads no variable or flag that skips a check.
    - **Remote Docs.** With `- Docs:` holding `://`, it skips the two document checks and prints why (AC5). That is the condition `init` uses today to leave them uninstalled. The checks themselves keep failing on that value when run directly.
  - **`hooks/quality-gate.sh`.**
    - **One command list.** One function returns the commands: `sh "$DIR/harness-checks.sh"`, expanded inside `eval` so a path holding a space or a `$` is never re-read as code, then the split line. Three readers read that list: the child's loop (`:568`), the timeout block (`:331`) and the signal block (`:354`). So all three still number every command alike.
    - **The empty-line pass moves.** The pass at `:403` gives way to the runner. With the line empty or absent, the list holds the runner alone, and the absent-`tech.md` pass at `:401` stays.
    - **The fingerprint.** `qg_fingerprint` also hashes the runner, the four checks it resolves, and the `- Docs:` value the runner branches on. They are now the gate's own inputs, so the "toolchain not hashed" boundary keeps its meaning, and a fix in place, on a local marketplace, re-runs once.
  - **`assets/check-locks.py`.** ROOT becomes the git toplevel of the working directory. Outside a repository it fails closed, which removes the vacuous "nothing to verify" pass from anywhere but a repository. Its docstring drops "a COPY rather than a reference". Its drift message names the re-pin command for each place, and `init`'s reviewer bullet and `contract` give the same commands:
    - `python3 "${GATE_SDD_PLUGIN_ROOT:?…}/assets/check-locks.py" --update` in a Claude Code session;
    - `python3 .agents/hooks/check-locks.py --update` on Antigravity;
    - `./assets/check-locks.py --update` here.
  - **The anchor check gains one check (AC6).** It fails when `.agents/hooks/quality-gate.sh` exists with no `harness-checks.sh` beside it. A `.claude/hooks/` copy is out of its reach: when a settings entry runs it, `plugin-gate.sh` stands the plugin's gates down. That copy is the pre-0.23.0 migration's to delete (AC8).
  - **`hooks/steering-digest.sh`.** It prints a `Harness checks:` line, worded as a fact, with the runner command for the tree it ran from.
    - When the digest runs from a path inside the project, that path is the command: `sh hooks/harness-checks.sh` here, `sh .agents/hooks/harness-checks.sh` on Antigravity.
    - Run through `plugin-gate.sh`, the command is `sh "${GATE_SDD_PLUGIN_ROOT:?is unset; start a new Claude Code session}/hooks/harness-checks.sh"`.
    - It compares the contract copy with that same tree's `reviewers/_shared/reviewer-contract.md`, and the line with the harness checks' names, and prints a notice for each that differs (AC7).
    - Antigravity's contract and gates come from the same re-run, so there is nothing newer to compare against there.
  - **CI, as `init` prescribes it to a project.**
    - On Claude Code, `sh .gate-sdd/hooks/harness-checks.sh` runs with the existing checkout at `ref: main`, which keeps the document checks on document-only pull requests. The unreviewed-work check runs as `sh .gate-sdd/assets/check-unreviewed-work.sh <head ref> <head sha> <base sha>` with `GATE_SDD_HOOKS=.gate-sdd/hooks`.
    - On Antigravity, CI runs the `.agents/hooks/` copies.
    - In a terminal, the command is `sh "${GATE_SDD_HOOKS:?set it to a plugin checkout's hooks/}/harness-checks.sh"`.
    - This repository's `.github/workflows/ci.yml` changes no job.
  - **Text.** Every place that tells an agent which checks to run gets the same addition: "the validators named in `.steering/tech.md`, then the harness checks the digest names". That covers:
    - `implement` (`:13`, `:21`, `:28`);
    - the contract's evidence purpose (`:22`), with its mirror;
    - the three reference reviewers' allow-lists (`:18`);
    - the template, whose `{{VALIDATOR_LIST}}` gains the runner.
  - **`init`.** Step 3's four guard bullets become one: the gate runs the harness checks, and nothing is copied on Claude Code. The Antigravity hooks bullet adds the runner and the five guards to `.agents/hooks/`. Step 4 times the runner with the validators, since both count against `- Validator budget:`.
  - **The migration bullet** follows AC8's order. The dual-target note at `:79` is rewritten to match.
    - An entry is matched by its last path component, a harness check's filename, with any `./`, `sh`, `python3` or directory before it.
    - Until a project migrates, its old entries run beside the gate's checks. A stale copy can only add a block, never remove one, and the digest notice says so.
  - **The pins.** Each `check-skill-contracts.py` entry on a sentence this branch removes is retired with its replacement, and each new entry carries the argument the cap requires. The count moves to match.
  - **Why this rather than a narrower or wider fix.**
    - **Narrower:** a detector on the copies keeps the copying that CAP-5 forbids, and blocks every project on release day.
    - **Wider:** moving the reviewer contract into the plugin breaks the concrete path a reviewer opens (`scripts/check-contract-path.py`, A9). So the contract stays a copy, reported by AC7, and that is stated as the one exception.
- **Affected files:**
  - **Hooks:** `hooks/harness-checks.sh` (new), `hooks/quality-gate.sh`, `hooks/steering-digest.sh`, `hooks/templates/README.md`.
  - **Guards:** `assets/check-locks.py`, `assets/check-steering-anchors.sh`, and the docstrings of `assets/check-document-set.py` and `assets/check-document-cascade.py`.
  - **Skills and reviewers:** `skills/init/SKILL.md`, `skills/implement/SKILL.md`, `skills/contract/SKILL.md`, `reviewers/_shared/reviewer-contract.md` and `.claude/agents/_shared/reviewer-contract.md`, the three reference reviewers, `reviewers/_template/reviewer.md`.
  - **Checkers and tests:** `scripts/check-skill-contracts.py`, `scripts/check-reviewer-allow-list.py`, `scripts/test-gates.sh`, and `scripts/check-contract-path.py` if the digest's literal contract path joins its document set.
  - **This repository's own files:**
    - `.steering/tech.md`, whose line drops the four guards;
    - `.steering/structure.md`;
    - `.claude/agents/gate-sdd-reviewer.md`, whose allow-list gains `sh hooks/harness-checks.sh`;
    - `AGENTS.md`;
    - comments in `.github/workflows/ci.yml`.
  - **Documents:** `docs/decisions/ADR-10-*.md` (new), ADR-9 (a superseded note), `README.md`, `README.ja.md`, `docs/fidelity.md`, `docs/DESIGN.md`, `docs/layout.md`, `docs/CONTRACT.md`, `docs/verified.md`.
  - **Manifests:** the two version fields, after the receipt.
- **Blast radius:**
  - **Every project's turn end runs four more checks, once an update lands.** For a project `init` installed, that is today's set run from a fresh tree. For a project that left one off its line, it is new, and it can block with a named remedy. It never passes where the line alone would have blocked.
  - **The pinned no-validators case changes in one way.** A project with a `tech.md` and no validators declared now runs the runner, and blocks if a harness check fails. Today it passes having run nothing. An `init` interrupted between writing `.steering/` and arming the gate meets this too, which is the state step 4 exists to end.
  - **The validator budget now covers the runner.** A project whose suite sat near its budget can meet the deadline block sooner, and that block names the runner.
  - **`test-gates.sh` runs the gate in many fixtures.**
    - Each fixture that runs the validators now runs the runner from the fixture's hooks directory, which holds the flat layout.
    - Cases that do not test the checks place stub checks that exit 0 beside the fixture's runner. Nothing in the shipped gate skips it, and one case pins that a fixture missing a check blocks.
    - The cases that assert copies in `scripts/` are rewritten: case 219, the document-set fixtures and case 59's needle.
  - **Unmigrated projects run both** their old copies and the gate's checks until `init` re-runs.
  - **This repository** runs the checks from source through `hooks/harness-checks.sh`, as ADR-6 requires. Its digest names that path, and its CI keeps its separate steps.
- **Why this cannot recur:**
  - No harness check lives in a project on Claude Code, so there is no copy to fall behind. The fingerprint covers the checks, so a fix re-runs.
  - The anchor check fails the one state, an Antigravity gate copy with no runner, where a turn end could run no checks.
  - The contract, the one copy left, is compared at every session start.
  - Regression cases pin each of these:
    - a stale copy on the line no longer decides the verdict, because the plugin's check runs too;
    - a missing check blocks;
    - a check's library comes from its own tree;
    - an empty line still runs the runner;
    - `check-locks.py`, run from another directory, reads the project.

## 3. Tasks (TDD-ordered)

> One task is one complete Red-Green-Refactor cycle, so one green commit. No task is sequenced after the review.

- [ ] T1 (AC1, AC2, AC11): the cases AC11 names, then the runner, the gate's command list and the fingerprint. The cases cover:
  - a fixture plugin whose changed check blocks while the line's stale copy passes;
  - an empty and an absent line;
  - a missing check;
  - a check's library;
  - the timeout and signal blocks;
  - a re-run after a check or `- Docs:` changes;
  - a path with a space.
- [ ] T2 (AC4): cases for `check-locks.py` run from a plugin path against a project, from outside a repository, and with `--update`. Then the root and the messages.
- [ ] T3 (AC5, AC6): cases for remote Docs, a missing `- Mode:`, the flat Antigravity layout, and an Antigravity gate copy with no runner. Then those branches.
- [ ] T4 (AC3, AC7): cases for the digest's runner line from the plugin, from this repository and from `.agents/hooks/`, and for its two notices. Then the digest.
- [ ] T5 (AC1, AC3, AC8): `check-skill-contracts.py` entries for the load-bearing sentences, new and retired, failing against `b0a71bd`'s text, and a `check-reviewer-allow-list.py` case for the runner. Then the text in each of:
  - `init` and its CI instructions, `implement` and `contract`;
  - the contract and its mirror;
  - the reviewers and the template;
  - this repository's line and allow-list.
- [ ] T6 (AC9): ADR-10 and the documents AC9 lists, with `check-readme-claims` and the leakage check green.
- [ ] T7 (AC10): the three recorded runs in `docs/verified.md`, the real migration on the project the maintainer names.
