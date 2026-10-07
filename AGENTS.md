# AGENTS.md

Cross-tool context for agents working on **this** repo. `.claude/CLAUDE.md` imports it so there is one canonical file.

## What this repo is

A spec-driven development harness, packaged as a plugin that installs into **both** Claude Code and Google Antigravity from **one** directory.

The contribution is not the directory scaffold — anyone can make folders. It is two ideas:

1. **The reviewer's rulebook lives inside the agent's own directory**, so it never enters a normal session's context, and it is hash-pinned to its sources.
2. **Each rule sits at the layer matching how much it can be talked out of** — deterministic checks in hooks, judgment in a subagent, process in a skill.

A refactor that loads the rulebook into normal sessions, or turns an enforced gate back into prose, has removed the reason this repo exists.

## Dual-target layout

**The repository root is the plugin** — simultaneously a Claude Code plugin, a Claude Code marketplace, and an Antigravity plugin. None of the formats collide, so nothing is nested and nothing is duplicated:

| Artifact | Claude Code | Antigravity |
| :-- | :-- | :-- |
| Manifest | `.claude-plugin/plugin.json` | `plugin.json` |
| Hooks | the gates ship from `.claude-plugin/hooks.json`, which runs `hooks/plugin-gate.sh`; `hooks/templates/claude-code.settings.json`, rendered into the project by `init`, carries the marketplace declaration and the fast check only (#256, ADR-8) | `hooks/templates/antigravity.hooks.json`, rendered the same way (plugin-name envelope, `enabled` flag), with the gates copied beside it |
| Skills | `skills/<name>/SKILL.md` | same path, same format |
| Reviewers | `reviewers/<name>.md`, copied by `init` into `.claude/agents/` | the same file, copied into `.agents/agents/` |
| Rules | `AGENTS.md` | `rules/AGENTS.md` (symlinked, auto-discovered by plugin loader) |
| Distribution | `.claude-plugin/marketplace.json`, git-native | `agy plugin install <local path>` |

Keeping the plugin at the root rather than nesting it under `plugins/<name>/` means the clone directory *is* the installable unit: `agy plugin install ./gate-oriented-sdd` takes the repository itself, and the Claude Code marketplace entry points at `"./"`. One directory, two install paths, nothing duplicated between them.

Skills, reviewers, and rules are **one copy read by both** (rules symlinked at `rules/AGENTS.md`). There is no sync step and no templating engine, so drift between the two targets is not possible — only the hook files and the two manifests differ, and `scripts/check-manifests.py` verifies they agree. The plugin's own `.claude-plugin/hooks.json` is the one hook file neither harness's template renders: it is what Claude Code runs, at a path Antigravity's loader does not read, and the guard refuses a `hooks/hooks.json` or a root `hooks.json` for that reason.

## Known fidelity gap

Antigravity has five hook events: `PreToolUse`, `PostToolUse`, `PreInvocation`, `PostInvocation`, `Stop`. Both blocking gates port — `Stop` blocks on both sides, via exit code 2 on Claude Code and `{"decision": "continue"}` on Antigravity.

**Antigravity has no `SessionStart`.** Steering digest delivery ports via `PreInvocation` turn 1 step injection (`hooks/steering-digest-antigravity.sh`), paired with `SessionStart` in `scripts/check-manifests.py`. Context re-injection after mid-session compaction remains the one unhooked path on Antigravity. Keep [`docs/fidelity.md`](./docs/fidelity.md) honest about this. A fidelity table a reader can trust is worth more than a claim of parity.

## Working on this repo

Run these before every commit. The `- Validators:` line in `.steering/tech.md` is the authority on which commands gate a turn, and `.github/workflows/ci.yml` on what CI runs — this block is a contributor's short list, not a third definition of the set:

```bash
./scripts/check-leakage.sh          # no private context
./scripts/check-manifests.py        # both manifests agree; hook shapes correct
./scripts/check-markdown-fences.py  # no ```markdown fence hand-wraps the Markdown it quotes
./scripts/check-receipt-schema.py   # the receipt schema agrees across its copies
./scripts/check-skill-contracts.py  # skills still carry their load-bearing instructions
./scripts/check-templates.py        # no spec template splits a red step from its green step,
                                    # and no live spec sequences a task after the review
./assets/check-steering-anchors.sh  # steering's machine-read lines still parse
./assets/check-locks.py             # rulebooks match their locks (--update to re-pin)
./assets/check-document-set.py      # the installed document set matches the declared mode
./scripts/check-contract-path.py    # every statement of the contract's path agrees
./scripts/check-readme-claims.py    # the README's Status claims match what they describe
./scripts/check-reviewer-allow-list.py  # the reviewer's allow-list covers the Validators line
./scripts/test-gates.sh             # the gates still behave
./scripts/check-version-bump.py     # shipped changes carry a version bump (PR-only in CI)
./scripts/check-backlog-tracker.py  # the ordered list agrees with the tracker (PR-only in CI)
```

- `check-leakage.sh` matters most. This harness was extracted from a private polyrepo; the extraction is clean-room. If the guard fires, **rewrite the file — do not scrub it in place.** Scrubbing leaves the shape, and the shape is where the private structure lives.
- Run `./scripts/check-manifests.py` after touching any manifest or hook file.
- Validate with `claude plugin validate . --strict`.
- Develop against a live install with `claude --plugin-dir .`, then `/reload-plugins` to pick up edits without restarting.
- Plugin skills are namespaced: `gate-sdd:spec`, not `/spec`.
- **The plugin ships no agents, and has no `agents/` directory.** Claude Code registers every Markdown file under a plugin's `agents/`, at any depth, and Antigravity's loader processes it too, so the rulebooks, `_shared/reviewer-contract.md` and the template all registered as agents while they lived there (#235, ADR-7). The reviewers are in `reviewers/`, which neither harness scans: a reviewer is something `init` copies into a project, and it names a contract and rules that exist only there. `scripts/check-manifests.py` fails if `agents/` or a root `CLAUDE.md` comes back.
- `reviewers/*/rules/*.md` and `reviewers/_shared/reviewer-contract.md` carry no frontmatter. **Do not add any.** In a project's `.claude/agents/`, a file with frontmatter registers as an agent. `scripts/check-manifests.py` checks this, and checks that each reviewer's frontmatter `name` is its filename.
- `reviewers/_template/reviewer.md` quotes its frontmatter placeholders on purpose: bare `{{...}}` is a flow mapping in YAML, so an unquoted placeholder parses as an object and fails validation before substitution ever happens.
- `evals/` is under development — authored, unverified, because `claude plugin eval` is early access. Do not wire it into CI as a passing gate until it runs green.

## This repo runs its own harness

`.steering/`, `.specs/`, `.work_logs/`, and `.claude/` are this repository dogfooding the plugin it ships. None of it is shipped — consumers get `skills/`, `reviewers/`, `hooks/`, and `assets/`.

Two things are deliberately unlike a normal install, and both would look like mistakes:

- **The hooks are not copied.** `.claude/settings.json` points at the repository's own `hooks/*.sh`. Every other project copies them, because a gate must run with the project as its working directory — here the project *is* the source, so a copy would only create drift, and a drifted copy means this repo tests a stale version of its own enforcement.
- **`.claude/agents/gate-sdd-reviewer/` has no `rules-lock.json`.** `assets/check-locks.py --update` can refresh a lock but cannot create one (#19). The rulebook stays unpinned until #19 ships a bootstrap, and `docs/decisions/ADR-6` records why.

The project reviewer is `gate-sdd-reviewer` and is unrelated to the three reference reviewers in `reviewers/`, which are the product. Its anchor is **gates never fail open**.

## Status

Pre-release. Treat this as a reference implementation with a tested-against version matrix, not a supported product.
