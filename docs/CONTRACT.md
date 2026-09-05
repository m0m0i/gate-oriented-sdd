# Development contract

- Applies to: everything this repository ships — `skills/`, `agents/`, `hooks/`, `assets/`, the two manifests — and the guards under `scripts/` that CI runs against them. `.steering/`, `.specs/`, `.work_logs/` and `.claude/` are the dogfood instance and hold to the same rules.
- Quality anchor: **gates never fail open**, the `- Owns:` line in `.steering/product.md`. A defect that lets a gate exit 0 when it should have blocked is at least HIGH; one that makes a gate silently stop checking is a BLOCKER.

This document was compiled **from** the reviewer's rulebook at `.claude/agents/gate-sdd-reviewer/rules/`, not the reverse: the rulebook was hand-authored one rule per incident, and this contract indexes it and states the tiers around it. Where `CONTRIBUTING.md` already states a rule, this document links to it rather than restating it.

## Language and tooling

POSIX `sh` for hooks, Python 3 standard library for guards, Markdown for everything a model reads. No package manager, no dependency file, no build: the repository root is the installable plugin (`AGENTS.md`).

| | Command |
| :-- | :-- |
| test | `./scripts/test-gates.sh` |
| lint | the commands on the `- Validators:` line of `.steering/tech.md`, run by the quality gate on turn end and by CI |
| validate | `claude plugin validate . --strict` (CI) |
| release check | `./scripts/check-version-bump.py <base>` (CI, pull requests only) |

## Style

There is no formatter. `.vscode/settings.json` pins format-on-save off for Markdown because Prettier reverted a spec twice (#66). What a formatter would own is stated once instead:

- Markdown is not hand-wrapped — `CONTRIBUTING.md`, "Markdown is not hand-wrapped".
- Hooks are POSIX `sh`: `#!/bin/sh`, `set -u`, no bashisms (`G-5`).
- Guards are `#!/usr/bin/env python3` with a module docstring saying what the guard proves and why, paths from a `ROOT` derived from `__file__`, and no `assert` for a check that must survive `-O`.
- Machine-read steering lines stay on one physical line (`G-7`).

Naming, file placement and module boundaries are `.steering/structure.md`'s.

## Testing

Tests are `scripts/test-gates.sh`. Each case builds a throwaway repository and runs the real hook or guard against it, with no model in the loop and nothing mocked. Every new gate behaviour needs a case (`G-4`), and a case is shown to fail by reverting the fix before it ships.

"Done" for a spec branch is every task ticked, every validator green, the reviewer's verdict CLEAN, and a receipt at `.specs/<slug>/.review-receipt` naming the reviewed commit. The review gate refuses to end the turn otherwise.

## Review

Blocks a merge: a BLOCKER or HIGH finding; a failing validator; a missing, stale or non-CLEAN receipt on a finished spec branch; a shipped-path change without a version bump. Advisory: MEDIUM, LOW and INFO, each fixed or recorded with a reason in the work log entry the branch ships with. The severity ladder and the rules of engagement are `.claude/agents/_shared/reviewer-contract.md`; the bar a rule meets before entering the rulebook is `CONTRIBUTING.md`, "The bar for a rule".

## Rules

The rulebook is the source for every Judgment row and holds each rule's rationale and check; this table is its index, and nothing checks that the two agree — the lock pins the rulebook, not this file (#23's shape).

| id | Rule | Tier | Severity | Enforced by |
| :-- | :-- | :-- | :-- | :-- |
| M-1 | No private context in the tree | Mechanical | — | `check-leakage.sh` |
| M-2 | Both manifests agree and the hook shapes are right | Mechanical | — | `check-manifests.py`, also after every Write/Edit via `PostToolUse` |
| M-3 | A ` ```markdown ` fence does not hand-wrap what it quotes | Mechanical | — | `check-markdown-fences.py` |
| M-4 | The receipt schema agrees across its copies | Mechanical | — | `check-receipt-schema.py` |
| M-5 | Skills keep their load-bearing sentences | Mechanical | — | `check-skill-contracts.py` |
| M-6 | No spec template splits a red step from its green step | Mechanical | — | `check-templates.py` |
| M-7 | Steering's machine-read lines parse | Mechanical | — | `check-steering-anchors.sh` |
| M-8 | Shipped rulebooks match their locks | Mechanical | — | `check-locks.py` |
| M-9 | The gates behave, on every path the suite pins | Mechanical | — | `test-gates.sh` |
| M-10 | Guards do not rely on `assert` | Mechanical | — | the `test-gates.sh` case that runs them under `python3 -O` |
| M-11 | A shipped-path change carries a version bump | Mechanical | — | `check-version-bump.py`, CI on pull requests only; `C-6` flags it earlier |
| M-12 | Both plugin manifests validate | Mechanical | — | `claude plugin validate --strict`, CI |
| M-13 | A finished spec branch cannot end a turn without a fresh CLEAN receipt | Mechanical | — | `hooks/review-gate.sh` |
| M-14 | A spec branch's slug carries its issue number | Mechanical | — | `hooks/review-gate.sh` |
| G-1 | A guard never exits 0 where it could not do its job | Judgment | BLOCKER | rulebook |
| G-2 | A value interpolated into `git` reaches it intact | Judgment | BLOCKER | rulebook |
| G-3 | A blocking gate speaks both channels | Judgment | BLOCKER | rulebook |
| G-4 | Every new gate behaviour has a case that can fail | Judgment | HIGH | rulebook |
| G-5 | Hooks are POSIX `sh` | Judgment | HIGH | rulebook — lintable by `shellcheck -s sh`, not done: no toolchain to install it with |
| G-6 | A gate stays narrow | Judgment | HIGH | rulebook |
| G-7 | Machine-read steering values stay on one line | Judgment | MEDIUM | rulebook |
| G-8 | A guard's exemption list is part of the guard | Judgment | HIGH | rulebook |
| G-9 | Normalisation belongs on the clearing side | Judgment | HIGH | rulebook |
| C-1 | A claim of verification names what was run | Judgment | HIGH | rulebook |
| C-2 | A count in prose matches what it counts | Judgment | MEDIUM | rulebook |
| C-3 | The Japanese README is a translation | Judgment | MEDIUM | rulebook |
| C-4 | A skill terminates in something the harness reads | Judgment | HIGH | rulebook |
| C-5 | Instructions never describe a file the project was not given | Judgment | HIGH | rulebook |
| C-6 | A shipped-path change carries a version bump | Judgment | HIGH | rulebook, ahead of M-11 |
| C-7 | No frontmatter on `agents/*/rules/*.md` | Judgment | BLOCKER | rulebook |
| C-8 | A spec amendment lands in its own commit ahead of the artifact it judges | Judgment | MEDIUM | rulebook, added by this contract |
| C-9 | A verification record names what it set out to observe and could not | Judgment | MEDIUM | rulebook, added by this contract |
| N-1 | Markdown outside fences is not hand-wrapped | Narrative | — | nothing — #61's detector cannot reach zero, so the reviewer reads for it |
| N-2 | Commit subjects carry a conventional prefix | Narrative | — | nothing — and `main`'s squash-merge subjects do not consistently follow it |
| N-3 | A leakage hit is rewritten, not scrubbed in place | Narrative | — | nothing — `AGENTS.md` |
| N-4 | Six to ten rules per rulebook file; a skill past about a hundred lines moves reference material out | Narrative | — | nothing — `CONTRIBUTING.md`, `docs/skill-anatomy.md` |
| N-5 | Advisory findings are fixed or recorded with a reason | Narrative | — | `implement` step 3 — a skill, which is a layer this table has no tier for |
