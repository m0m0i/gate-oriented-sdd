# Hook templates

`init` renders these into the target project. Since 0.23.0 the two files do different jobs, because the two harnesses get their gates differently (#256, ADR-8):

- **`antigravity.hooks.json`** is rendered into `.agents/hooks.json`, and the gates are copied beside it into `.agents/hooks/`. They are copies for one concrete reason: **a gate has to run with the project as its working directory**, and on Antigravity a plugin-shipped hook runs with *the directory containing `hooks.json`* as cwd, which for a plugin is the plugin directory, where `.specs/` and `.steering/` do not exist. A gate fix reaches an Antigravity project by running `init` again.
- **`claude-code.settings.json`** is rendered into `.claude/settings.json`, and carries **no gate**. On Claude Code a plugin hook runs with the project as cwd (verified, `docs/verified.md`), so the gates ship from the plugin's own `.claude-plugin/hooks.json`, which runs `hooks/plugin-gate.sh` on `Stop` and `SessionStart`. What the template carries is the project's half: the marketplace declaration with `"autoUpdate": true`, the enabled plugin, and the per-language `PostToolUse` fast check, which really is per-project. A gate fix reaches a Claude Code project by plugin update.

`init` copies `gate-lib.sh`, `quality-gate.sh`, `review-gate.sh`, `steering-digest.sh` and `steering-digest-antigravity.sh` into an Antigravity project's hooks directory, and into nothing on Claude Code, and substitutes:

| Placeholder | Becomes | In |
| :-- | :-- | :-- |
| `{{HOOKS_DIR}}` | where the scripts were installed (`.agents/hooks`) | the Antigravity template |
| `{{FAST_CHECK}}` | the per-edit check for this project's language | both |

The blocking quality gate is **not** a placeholder. It ships as `quality-gate.sh` and reads its commands from the `- Validators:` line in `.steering/tech.md`, so the project configures enforcement by editing steering rather than by having `init` bake a command into a settings file. It used to be `{{QUALITY_GATE}}`, which meant every `init` invented the most important hook in the harness — and an invented one usually loses the dual-channel blocking that `gate-lib.sh` exists to provide.

The plugin's own `.claude-plugin/hooks.json` is not a template and is never rendered. `scripts/check-manifests.py` holds it: the manifest must name it, its commands must name scripts the plugin ships, and its events plus the Claude Code template's must pair with the Antigravity template's. It also refuses a `hooks/hooks.json` or a root `hooks.json`, because both are places Antigravity reads, and Claude Code's nested `Stop` shape in a file Antigravity parses invalidates Antigravity's whole file.

## Schema warning

The Antigravity template and the plugin's Claude Code hooks file are **not** the same shape, and Antigravity's own shape is not internally consistent — this is verified behaviour, see `docs/verified.md`:

- Antigravity **tool** events (`PreToolUse`, `PostToolUse`) take the nested `{matcher, hooks: [...]}` form.
- Antigravity **non-tool** events (`Stop`, `PreInvocation`, `PostInvocation`) take a flat `{type, command, timeout}`.

Mixing them up invalidates the *entire file* with `invalid hook "<name>": command hook must specify 'command'`, which reads like a missing field rather than a wrong shape. `scripts/check-manifests.py` checks these templates agree on which events they cover so the mistake cannot ship.

Antigravity has no `SessionStart`; it delivers the steering digest via `PreInvocation` with turn 1 step injection (`hooks/steering-digest-antigravity.sh`). `scripts/check-manifests.py` enforces that `SessionStart` on Claude Code pairs with `PreInvocation` on Antigravity.

