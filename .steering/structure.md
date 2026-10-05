# Structure — gate-oriented-sdd

The repository root is simultaneously a Claude Code plugin, a Claude Code marketplace, and an Antigravity plugin. Nothing is nested and nothing is duplicated, because the three formats do not collide.

| Path | Holds | Shipped to consumers |
| :-- | :-- | :-- |
| `skills/<name>/SKILL.md` | one skill each, read by both harnesses | yes |
| `reviewers/<name>.md` + `reviewers/<name>/rules/` | reference reviewers and their hash-pinned rulebooks, copied into a project by `init` and registered by neither harness | yes |
| `reviewers/_shared/`, `reviewers/_template/` | the reviewer contract, and the starting point for an unrecognised stack | yes |
| `hooks/*.sh` | the gates; `hooks/templates/` renders into projects | yes |
| `assets/` | files copied into projects — issue templates, `check-locks.py` | yes |
| `scripts/` | this repo's own guards, run by CI | no |
| `docs/` | the inception documents — north star, PRD, epics, backlog, contract, design — and fidelity, layout, verified behaviour | no |
| `docs/decisions/ADR-<n>-<slug>.md` | one contested decision each, append-only | no |
| `evals/` | under development — authored, unverified | no |

The seams between these — what crosses each, who produces and consumes it, and which guard makes a disagreement loud — are `docs/DESIGN.md`. The decisions behind the layout, with the alternatives they rejected, are `docs/decisions/`.

**Tests live in `scripts/test-gates.sh`**, not beside the code. There is no test framework: the gates are shell, so their tests are shell, and each case builds a throwaway git repository in a temp directory. A new gate behaviour needs a new case there — that is the project's whole notion of test coverage. The count is the suite's — run it rather than trusting a number here, which is what #115 settled for the same claim in both READMEs.

There is no `agents/` directory, on purpose: Claude Code registers every Markdown file under a plugin's `agents/` and Antigravity's loader processes the directory, and this plugin ships no agents (#235, ADR-7). `reviewers/*/rules/*.md` and the contract deliberately carry **no frontmatter**. They are reference material the reviewer loads on demand, and with frontmatter they register as agents in the project they are copied into. `scripts/check-manifests.py` holds both.

## Where the harness's own instance lives

`.steering/`, `.specs/`, `.work_logs/`, and `.claude/` are this repo dogfooding itself. They are not shipped. `.claude/agents/gate-sdd-reviewer/` is the project's own reviewer and is unrelated to the three reference reviewers in `reviewers/`, which are the product. The two ways this instance deviates from an ordinary install — hooks run from source, reviewer unpinned — are ADR-6.
