# ADR-8: The Claude Code gates ship from the plugin; the reviewers do not
- Status: accepted
- Date: 2026-10-07; #256, split from #245

## Context
`init` copied `gate-lib.sh`, `quality-gate.sh`, `review-gate.sh` and `steering-digest.sh` into every project's `.claude/hooks/`, and nothing refreshed the copies. #245 measured four repositories of one consumer at 90 to 359 lines behind the plugin's `review-gate.sh`; the sixteenth refinement re-measured them at 130 to 377; #254 (0.22.1) was one more fix that reached nobody. The gate is the part of the harness that most needs to be current, and it was the only part that was not.

The copy existed for one reason, written in `hooks/templates/README.md`: on Antigravity a plugin-shipped hook runs with the plugin directory as cwd. That reason never held on Claude Code, and V1 (`docs/verified.md`) confirmed it: a plugin-shipped `Stop` or `SessionStart` hook runs with the project as cwd and `CLAUDE_PLUGIN_ROOT` set.

ADR-7 had just taken the reviewers the other way, out of what the plugin registers and into what `init` copies.

## Decision
On Claude Code the gates run from the plugin. `.claude-plugin/hooks.json`, named by the manifest's `"hooks"` field, runs `hooks/plugin-gate.sh` on `Stop` and `SessionStart`, and the wrapper execs the gate beside itself. It is silent in a project without `.steering/`, and it stands down only on evidence that the project runs its own copy: the project's settings naming the gate under the gate's event, and the named file on disk. `init` copies no gate script on Claude Code; it writes the marketplace declaration with `autoUpdate` and the enabled plugin, and migrates an older install by removing the copies and their entries. The two shipped checks that source the library find it by `GATE_SDD_HOOKS`, then a copy, then `$CLAUDE_PLUGIN_ROOT/hooks`, and a Claude Code project's CI checks the plugin out.

On Antigravity nothing changes: the gates are copied, and a fix arrives by running `init` again.

## Why the two layers ship differently
A reviewer is adapted per project and pinned there; the project owns its text, and the lock (ADR-2) exists so that a plugin update cannot change it under the project. A gate is the opposite in every respect: identical in every project, configured through `.steering/tech.md` rather than by editing, and most dangerous when stale, because a stale gate is indistinguishable from a working one until it matters. One layer is the project's; the other is the plugin's. Shipping them the same way would be wrong for one of them whichever way was chosen.

## Consequences
- A gate fix reaches a Claude Code project at its next session after the plugin updates, with no pull request in the project.
- A project that has not been migrated keeps its copies and the plugin stands down, so it is no worse off than before and no better until `init` runs.
- A Claude Code project has no `gate-lib.sh`; its CI and any by-hand run of the two checks need `GATE_SDD_HOOKS`, and the checks say so.
- A clone where the plugin is not installed or not enabled runs no `Stop` gate at all, and nothing in the project says so: a contributor who declines the `enabledPlugins` prompt, a machine where the marketplace clone fails, or a headless session without the plugin has a settings file with no `Stop` entry and no plugin behind it. Before this decision the copied gates ran in every trusted clone. The backstop is CI: `check-unreviewed-work.sh` for the review half, and the project's own validators for the quality half; `init` already asks for both.
- The stand-down reads text, not JSON by event, and needs the entry and the file it names: the shipped pre-0.23.0 entry exits 0 by its own guard once the copy is gone, so an entry alone would have silenced both in a half-migrated project. A settings file whose `Stop` command names an existing copy without running it still silences both; nothing writes that, and the alternative was parsing JSON in POSIX `sh`.
- Antigravity projects still drift. `docs/fidelity.md` says so; this is the second real gap after compaction re-injection.
- This repository keeps running its hooks from source (ADR-6). Its `.claude/settings.json` is the stand-down evidence, so the installed plugin's gates are silent here.
- 2026-10-08: a by-hand run of the two checks inside a Claude Code session no longer needs `GATE_SDD_HOOKS`. The plugin's `SessionStart` hook writes `GATE_SDD_PLUGIN_ROOT` into the session's env file, and the checks read it after any copy (ADR-9, #264). A terminal outside a session still sets `GATE_SDD_HOOKS`, and so does CI.
- 2026-10-08: the stand-down reads what the launch ran (#262). The Decision's "the named file on disk" now means on disk where the entry's own shell finds it. A relative or absolute path qualifies, and so does a path through `$CLAUDE_PROJECT_DIR`, the form Claude Code's hooks documentation asks for, resolved to the value the plugin's hook and the project's were measured to share. An entry that reaches the copy any other way is not evidence, and both gate sets run until `init` migrates the project. The settings read are the ones the launch read. Below the git root, that is the launch directory's two files and the root's `settings.local.json`, not the root's `settings.json`. A relative path resolves from the directory the hook started in. #263 measured a plugin's hook starting where the Bash tool had last `cd`ed, and that the project's hook starts there too is inferred (`docs/verified.md`). Before this, a launch below the root could stand the plugin down on a root entry that never ran, and no gate ran. On that inference, so could a turn that ended in a subdirectory.
- 2026-10-09: a session the Claude desktop app starts runs no plugin auto-update pass. The app sets `DISABLE_AUTOUPDATER=1`, which turns the pass off unless `FORCE_AUTOUPDATE_PLUGINS=1` is also set, so on a machine used only through the app the first consequence above waits for a by-hand update (#265, `docs/verified.md`). The remedy is #274.

## Alternatives considered
- **Keep copying, and have the digest report the lag** — the copy still drifts, and CI's unreviewed-work check keeps running yesterday's fail-open fixes.
- **Keep `gate-lib.sh` copied for the checks, ship only the three gates** — the same drift, in the file that holds the fixes.
- **Guard in the JSON commands rather than a wrapper** — a guard in a JSON string is one nobody tests; `scripts/test-gates.sh` runs the wrapper against the real gates.
- **Stand down on the copied file's presence** — a half-migrated project, with the file and no entry, would run no gate at all, under `- Owns: gates never fail open` (backlog row 1).
- **A version floor in `.steering/tech.md`** — a fallback #245 kept for the case where pinning proved unsafe; V3 showed a project-scope pin is ignored rather than harmful, so nothing needs the floor yet.
