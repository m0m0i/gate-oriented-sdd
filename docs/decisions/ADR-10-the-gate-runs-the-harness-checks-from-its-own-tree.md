# ADR-10: The gate runs the harness checks from its own tree
- Status: accepted
- Date: 2026-11-03; #340

## Context
ADR-8 took the Claude Code gates out of projects and left the guards in them. `init` still copied `check-steering-anchors.sh`, `check-locks.py`, `check-document-set.py` and `check-document-cascade.py`, the harness checks, into each project's `scripts/` and named them on its `- Validators:` line, with `check-unreviewed-work.sh` beside them for CI. A fix the plugin shipped to one of them reached no project that updated, which CAP-5 and LV-5 say must not happen, and nothing but the README's by-hand comparison command reported a copy as stale. #263 is what one cost: a stale anchor check blocked every turn that changed source until it was re-copied.

ADR-9 rejected the two ways out. "Ship the checks from the plugin" failed because the line is one line both harnesses' gates run, and a plugin path resolves nowhere in a dual-target project or a terminal. "The digest prints the path" failed because exporting it is a rule in the layer that can be talked out of it, repeated on every command. Both rejections assumed the checks had to be reached through the line. So did #110 AC5, which says mode-dependent blocking reaches the gates "ONLY through the `- Validators:` line".

`check-locks.py` was tied to being a copy as well: it took its root from its own location, so run from the plugin's `assets/` it would have verified the plugin's rulebooks and passed without reading the project's.

## Decision
The quality gate runs the harness checks itself, from the tree it was loaded from, before the line's commands. `hooks/harness-checks.sh`, the runner, is shipped beside the gates. It reads its layout from a marker, `../.claude-plugin/plugin.json`, which puts the checks in `../assets/`; without it they sit flat beside it. It runs each with `GATE_SDD_HOOKS` set to its own hooks directory, so a check and its library come from one tree, fails closed on a missing check, writes nothing and never passes `--update`. The line holds only the project's own commands. The fingerprint hashes the runner, the four checks and the steering values they branch on, so a fix to any of them runs once.

On Claude Code nothing is copied into a project for the guards. On Antigravity `init` copies the runner, the four checks and `check-unreviewed-work.sh` flat into `.agents/hooks/` with the gates, one set a re-run refreshes, and the anchor check fails a `.agents/hooks/quality-gate.sh` with no runner beside it.

`check-locks.py` takes its root from the git toplevel of the working directory and fails closed outside a repository.

The reviewer contract stays a copy in the project, because a reviewer opens a concrete path (`scripts/check-contract-path.py`, A9). It is the one exception, and the Claude Code digest reports a copy that differs from the one its tree ships.

This supersedes two of ADR-9's rejected alternatives, "Ship the checks from the plugin" and "The digest prints the path…", and ADR-9's consequence "A copied check can still fall behind the plugin". Their reasons no longer hold:
- The gate, not the line, runs the checks, from its own directory. No variable and no plugin path appears on the line, and each harness's gate runs the checks of the tree it came from.
- The digest prints a command, not a path to export. On Claude Code it reads the `GATE_SDD_PLUGIN_ROOT` that ADR-9's env file already sets, and its `:?` names the remedy when that is unset instead of running nothing. Nothing is repeated on each command, and the turn-end verdict does not depend on a by-hand run.

#110 AC5's "only through the `- Validators:` line" now has the gate's runner beside it: the document-set check reaches the gate through the runner. No hook branches on the mode. The fingerprint hashes `- Mode:` as an input, and the runner's one branch is on `- Docs:` naming another repository.

## Consequences
- CAP-2's done-when says `quality-gate.sh` "carries no validator commands of its own and runs the `- Validators:` line". It now carries the harness checks, which check the harness's own files, and the line still holds every command the project enforces, so the done-when reads as "no project validator commands of its own". `docs/PRD.md` is not edited here: a PRD change re-stamps every downstream document, and the capability itself is unchanged.
- Every Claude Code project's turn end runs the four checks from the plugin once an update lands, with no pull request in the project. A project that left one off its line now runs it, and it can block with a named remedy.
- An empty or absent `- Validators:` line no longer passes: the runner still runs. A project with no `.steering/tech.md` still passes.
- The runner counts against `- Validator budget:`, and the deadline block names it when it is the command cut short.
- A project's CI with the plugin checkout at `ref: main` runs a check fix with the next run. A checkout pinned to a release tag runs that tag's checks until the workflow moves it.
- On Antigravity CAP-5 stays unmet for the guards as for the gates: both arrive by re-running `init`. `docs/fidelity.md` says so.
- A project not yet migrated runs its old copies on the line beside the gate's checks until `init` re-runs. A stale copy can only add a block, and the digest says the line still names one.
- After an update, a by-hand run in a session that started before it can read a stale `GATE_SDD_PLUGIN_ROOT` naming an old cache version, whose directory stays on disk; 0.38.0 was named with 0.39.0 installed (`docs/verified.md`, #340's U4). The runner prints the tree and version it ran from, so the run shows it. The turn-end verdict is unaffected.
- This repository runs the checks from source through `hooks/harness-checks.sh` (ADR-6). Its line no longer names them, its reviewer's allow-list names the runner, and its CI keeps its separate steps.

## Alternatives considered
A design panel attacked four mechanisms against every place the line runs; #340's C1 records the ranking.
- **A dispatcher copied once into the project** — its root lookup is itself a copy on every entry's path, and its by-hand route reads a root that can be stale.
- **A variable chain on the line** — no one variable names the plugin at turn end, in the session's shell, in CI and on Antigravity, so it had no answer for Antigravity and its by-hand route reads a root that can be stale.
- **The gate runs the guards (chosen)** — the checks come from the tree the gate was loaded from, so a gate and its checks cannot disagree about version.
- **Keep the copies and add a staleness detector** — it keeps the copying CAP-5 rules out, and a blocking detector would block every project on every release.
