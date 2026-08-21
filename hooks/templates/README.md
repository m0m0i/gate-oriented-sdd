# Hook templates

`init` renders these into the target project. They are templates rather than live plugin hooks for one concrete reason: **a gate has to run with the project as its working directory.**

On Claude Code a plugin hook already runs with the project as cwd, so a plugin-level hook would work. On Antigravity the working directory is set to *the directory containing `hooks.json`* — for a plugin-shipped hook that is the plugin directory, where `.specs/` and `.steering/` do not exist. Installing project-local copies makes both harnesses behave identically, and it is what the gate needs anyway, since validators differ per project.

`init` copies `gate-lib.sh`, `review-gate.sh`, and `steering-digest.sh` into the project's hooks directory and substitutes:

| Placeholder | Becomes |
| :-- | :-- |
| `{{HOOKS_DIR}}` | where the scripts were installed (`.claude/hooks` or `.agents/hooks`) |
| `{{FAST_CHECK}}` | the per-edit check for this project's language |
| `{{QUALITY_GATE}}` | the blocking format/lint/type gate for this project |

## Schema warning

The two files are **not** the same shape, and Antigravity's own shape is not internally consistent — this is verified behaviour, see `docs/verified.md`:

- Antigravity **tool** events (`PreToolUse`, `PostToolUse`) take the nested `{matcher, hooks: [...]}` form.
- Antigravity **non-tool** events (`Stop`, `PreInvocation`, `PostInvocation`) take a flat `{type, command, timeout}`.

Mixing them up invalidates the *entire file* with `invalid hook "<name>": command hook must specify 'command'`, which reads like a missing field rather than a wrong shape. `scripts/check-manifests.py` checks these templates agree on which events they cover so the mistake cannot ship.

There is no `SessionStart` on Antigravity. The steering digest is Claude Code only; `PreInvocation` is the candidate substitute and needs a once-per-session guard before it is worth shipping.
