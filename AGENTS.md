# AGENTS.md

Cross-tool context for agents working on **this** repo. `CLAUDE.md` points here so there is one canonical file.

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
| Hooks | `hooks/hooks.json` | `hooks.json` (plugin-name envelope, `enabled` flag) |
| Skills | `skills/<name>/SKILL.md` | same path, same format |
| Subagents | `agents/<name>.md` | `agents/` |
| Distribution | `.claude-plugin/marketplace.json`, git-native | `agy plugin install <local path>` |

Keeping the plugin at the root rather than nesting it under `plugins/<name>/` means the clone directory *is* the installable unit: `agy plugin install ./gate-oriented-sdd` takes the repository itself, and the Claude Code marketplace entry points at `"./"`. One directory, two install paths, nothing duplicated between them.

Skills and agents are **one copy read by both**. There is no sync step and no templating engine, so drift between the two targets is not possible — only the two hook files and the two manifests differ, and `scripts/check-manifests.py` verifies they agree.

## Known fidelity gap

Antigravity has five hook events: `PreToolUse`, `PostToolUse`, `PreInvocation`, `PostInvocation`, `Stop`. Both blocking gates port — `Stop` blocks on both sides, via exit code 2 on Claude Code and `{"decision": "continue"}` on Antigravity.

**Antigravity has no `SessionStart`.** The steering digest has no direct equivalent; `PreInvocation` step injection is the candidate workaround and needs a once-per-session guard. Keep [`docs/fidelity.md`](./docs/fidelity.md) honest about this. A fidelity table a reader can trust is worth more than a claim of parity.

## Working on this repo

Run all four before every commit — CI runs the same four:

```bash
./scripts/check-leakage.sh      # no private context
./scripts/check-manifests.py    # both manifests agree; hook shapes correct
./scripts/check-locks.py        # rulebooks match their locks (--update to re-pin)
./scripts/test-gates.sh         # the review gate still behaves, 9 paths
```

- `check-leakage.sh` matters most. This harness was extracted from a private polyrepo; the extraction is clean-room. If the guard fires, **rewrite the file — do not scrub it in place.** Scrubbing leaves the shape, and the shape is where the private structure lives.
- Run `./scripts/check-manifests.py` after touching any manifest or hook file.
- Validate with `claude plugin validate . --strict`.
- Develop against a live install with `claude --plugin-dir .`, then `/reload-plugins` to pick up edits without restarting.
- Plugin skills are namespaced: `gate-sdd:spec`, not `/spec`.
- `claude plugin tag` warns that `agents/*/rules/*.md` have no frontmatter. **Expected — do not add any.** Those are reference material, not agents; giving them frontmatter risks registering them as subagents, which is the phantom-component bug that `_shared/reviewer-contract.md` was moved out of `agents/` to avoid. `claude plugin details` confirms only three agents are registered.
- `agents/_template/reviewer.md` quotes its frontmatter placeholders on purpose: bare `{{...}}` is a flow mapping in YAML, so an unquoted placeholder parses as an object and fails validation before substitution ever happens.
- `evals/` is authored but unrun — `claude plugin eval` is early access. Do not wire it into CI as a passing gate until it has actually run.

## Status

Pre-release. Treat this as a reference implementation with a tested-against version matrix, not a supported product.
