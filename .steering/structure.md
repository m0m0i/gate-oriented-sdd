# Structure — gate-oriented-sdd

The repository root is simultaneously a Claude Code plugin, a Claude Code marketplace, and an
Antigravity plugin. Nothing is nested and nothing is duplicated, because the three formats do not
collide.

| Path | Holds | Shipped to consumers |
| :-- | :-- | :-- |
| `skills/<name>/SKILL.md` | one skill each, read by both harnesses | yes |
| `agents/<name>.md` + `agents/<name>/rules/` | reviewers and their hash-pinned rulebooks | yes |
| `agents/_shared/`, `agents/_template/` | the reviewer contract, and the starting point for an unrecognised stack | yes |
| `hooks/*.sh` | the gates; `hooks/templates/` renders into projects | yes |
| `assets/` | files copied into projects — issue templates, `check-locks.py` | yes |
| `scripts/` | this repo's own guards, run by CI | no |
| `docs/` | fidelity, layout, verified behaviour | no |
| `evals/` | authored, unrun | no |

**Tests live in `scripts/test-gates.sh`**, not beside the code. There is no test framework: the
gates are shell, so their tests are shell, and each case builds a throwaway git repository in a
temp directory. A new gate behaviour needs a new case there — that is the project's whole notion of
test coverage, and 31 paths are currently pinned.

`agents/*/rules/*.md` deliberately carry **no frontmatter**. They are reference material the
reviewer loads on demand, not agents; giving them frontmatter risks registering them as subagents.

## Where the harness's own instance lives

`.steering/`, `.specs/`, `.work_logs/`, and `.claude/` are this repo dogfooding itself. They are not
shipped. `.claude/agents/gate-sdd-reviewer/` is the project's own reviewer and is unrelated to the
three reference reviewers in `agents/`, which are the product.
