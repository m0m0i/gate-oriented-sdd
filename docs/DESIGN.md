# Design

- Serves: the capabilities in `docs/PRD.md`. The directory pictures are `docs/layout.md` and are not repeated here.
- Status: accepted — this describes what ships at 0.4.2, not a proposal.

Three layers, chosen by how much each can be talked out of (`AGENTS.md`): deterministic checks in hooks, judgment in a subagent, process in skills. The design worth recording is the seams between them, because every integration failure this repository has filed lived at one.

## Components

| Component | Layer | Lives in | Serves |
| :-- | :-- | :-- | :-- |
| Gates — `gate-lib.sh`, `quality-gate.sh`, `review-gate.sh`, `steering-digest.sh` | deterministic | `hooks/` | CAP-1, CAP-2, CAP-7 |
| Guards — the validators on the `- Validators:` line, and `check-version-bump.py` | deterministic, at turn end and in CI | `scripts/`, `assets/` | CAP-5, CAP-7, and the gates' own correctness |
| Reviewer — agent file, rulebook, lock, shared contract | judgment | `agents/<name>.md`, `agents/<name>/`, `agents/_shared/` | CAP-3 |
| Skills — one copy read by both harnesses | process | `skills/` | CAP-4, CAP-6 |
| Steering — three files, five machine-read lines | bridge | `.steering/` in a project | every capability; it is what the layers agree through |
| Manifests and hook wiring — two of each | packaging | `.claude-plugin/plugin.json`, `plugin.json`, `hooks/templates/claude-code.settings.json`, `hooks/templates/antigravity.hooks.json` | CAP-5 |
| Tracker — issues typed feature, bug, chore | external | the project's tracker, via templates `init` installs | CAP-6 |
| `evals/` | none yet | `evals/` | no capability. Authored and unrun; kept because CAP-1's claim needs it to run one day |

The PRD's third user, the reference-implementation reader, is served by `README*` and `docs/`. No component exists for them, as the PRD says.

## Seams

What crosses, who produces it, who consumes it, and what happens when they disagree. The last column is the guard that makes disagreement loud; where it says *none*, disagreement is silent, and that is a listed risk.

| Seam | Crosses | Producer → consumer | On disagreement | Guard |
| :-- | :-- | :-- | :-- | :-- |
| Steering lines | `- Owns:`, `- Validators:`, `- Reviewer:`, `- Source globs:`, `- Docs:`, one physical line each | `init`, `northstar`, `contract` → `quality-gate.sh`, `review-gate.sh`, `steering-digest.sh`, the reviewer, the inception skills | a wrapped value is truncated at the first newline; an absent anchor is not a failure, an unreadable one is (#34) | `check-steering-anchors.sh` |
| Receipt | the Receipt block's fields | reviewer → `implement` copies verbatim → `review-gate.sh` reads | the gate blocks on a missing, non-CLEAN or stale `reviewed_sha`; an absent `reviewed_by` means not independent | `check-receipt-schema.py` keeps the copies of the schema agreeing |
| Rulebook and lock | `rules/*.md` and the hashes in `rules-lock.json` | `contract`, `init`, a human → `check-locks.py`; the reviewer loads rules on demand | drift fails closed since #16; a reviewer with no lock is invisible to `--update` (#19) | `check-locks.py` |
| Slug | `<issue-number>-<kebab-title>` | tracker → branch, `.specs/<slug>/`, PR | a spec directory without an issue number blocks the turn | `review-gate.sh` |
| Issue type | `feature`, `bug`, `chore` | issue template or label → `spec` chooses the section-1 shape | a wrong type produces a spec that tests the wrong thing | none — `clarify` and the reviewer |
| Spec | Requirements, Design, TDD-ordered Tasks | `spec` → `implement` executes, the reviewer reviews against | a task split red from green cannot be committed under the quality gate (#10) | `check-templates.py` |
| Dual target | two manifests, two hook files, one body of skills and agents | this repository → Claude Code and Antigravity | a name or version disagreement installs two identities; a gate that speaks one channel is advisory on the other (G-3) | `check-manifests.py`; `test-gates.sh` asserts both channels |
| Load-bearing sentences | a sentence in a skill that a hook or another skill depends on | skill author → the consumer the contract names | the consumer breaks silently while the sentence reads as editable prose | `check-skill-contracts.py` (#54 for the skills it does not cover) |
| Version | `version` in both manifests | a shipped-path change → `claude plugin update` | an unbumped fix reaches nobody and reports success (#3) | `check-version-bump.py`, CI on pull requests |
| Inception hand-offs | `NORTH_STAR.md` → `PRD.md` → `EPICS.md` → `BACKLOG.md` → issues; `contract` → rulebook; `design-doc` → `structure.md` | each skill → the next, and the harness | citations are checked forward only, and `PRD.md` and `EPICS.md` have no mechanical consumer (#22) | none — recorded in `docs/verified.md` |

## Where tests live

`scripts/test-gates.sh` is the only test file. Each case builds a throwaway repository and runs the real hook or guard against it, with no model in the loop. There is no mirror tree: the code is shell and Python in four directories, and the tests are cases in one file named by the behaviour each pins. A new gate behaviour needs a new case, and a case that cannot fail is not one (G-4).

## Risks, and what would change course

- **The gate is enforced against the model and negotiable by the human.** `git checkout` silences it (#26), and CAP-1's falsifier is live. Course changes if the escape keeps being used after the false blocks it hides behind are fixed: enforcement moves to `git push` or `gh pr create` (#36).
- **Independence is asserted by a field.** `reviewed_by=subagent` is written by the author of the diff. Course changes if receipts are predominantly `inline` on a fresh install, which #25 predicts: the gate refuses CLEAN on an `inline` review once `init` guarantees a spawnable reviewer.
- **Two inception documents have no consumer.** If nothing comes to read `PRD.md` and `EPICS.md`, CAP-6 is narrower than stated and the product's own boundary puts the skills that produce them out of scope (#22).
- **Facts stated twice drift silently.** `Source globs` duplicates `check-version-bump.py`'s `SHIPPED` tuple (#14); `C-2` enumerates count sites (#23); `CONTRACT.md` indexes the rulebook with no check. Course changes when a drift causes a wrong finding: a single source each derives from, or a guard that compares them.
- **A new reviewer cannot be pinned.** `--update` creates no lock (#19), and this repository's own reviewer is the standing example (ADR-6). Course changes if a consumer ships an unpinned rulebook without knowing; the fix is a bootstrap mode visibly distinct from re-pinning.
