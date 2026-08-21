# Verified behaviour

Both target harnesses move fast, so nothing in this repo is designed against documentation alone. Every row below was produced by running the thing on a real install. Re-verify when the version column moves.

Last verified: **2026-08-21**.

## Versions tested against

| Component | Version |
| :-- | :-- |
| Claude Code | 2.1.238 |
| Antigravity CLI (`agy`) | 1.1.17 |
| Antigravity IDE | 2.3.1 |
| Platform | macOS (darwin, arm64) |

## Antigravity hooks

**Where `hooks.json` is read from.** Three locations, all confirmed by the CLI's own loader log (`hooks_manager.go: loaded N named hooks from N hooks.json file(s)`):

| Location | Scope | Confirmed |
| :-- | :-- | :-- |
| `~/.gemini/config/hooks.json` | global, shared between TUI and backend | **yes** — loaded and fired |
| `<workspace>/.agents/hooks.json` | workspace | path is correct, but **did not load** in a scratch directory. The CLI changelog notes workspace hooks load *after trusting a folder*, so an untrusted directory silently loads zero files |
| `<plugin>/hooks.json` | plugin-shipped | documented, and observed in an installed first-party plugin |

The `.agents/` vs `.agent/` question is settled: it is **`.agents/`**.

**The schema is mixed, and this is the trap.** Tool events and non-tool events take *different shapes*, and one malformed entry invalidates the entire file with `invalid hook "<name>": command hook must specify 'command'` — which reads like a missing field rather than a wrong shape.

```jsonc
{
  "<hook-set-name>": {
    "enabled": true,

    // Tool events: NESTED. The matcher is a regex over tool names.
    "PreToolUse":  [ { "matcher": ".*",
                       "hooks": [ { "type": "command", "command": "…", "timeout": 10 } ] } ],
    "PostToolUse": [ { "matcher": ".*",
                       "hooks": [ { "type": "command", "command": "…", "timeout": 10 } ] } ],

    // Non-tool events: FLAT. These ignore matchers, and giving them a nested
    // form is what produces the misleading parse error above.
    "Stop":           [ { "type": "command", "command": "…", "timeout": 10 } ],
    "PreInvocation":  [ { "type": "command", "command": "…", "timeout": 10 } ],
    "PostInvocation": [ { "type": "command", "command": "…", "timeout": 10 } ]
  }
}
```

**Which events fire.** All five confirmed firing with the correct shape, in `agy -p` print mode:

| Event | Fires | Can block |
| :-- | :-- | :-- |
| `PreToolUse` | yes (nested form, tool actually invoked) | yes — JSON `decision`: allow / deny / ask |
| `PostToolUse` | yes (nested form) | no — observe-only |
| `PreInvocation` | yes | no — can inject steps |
| `PostInvocation` | yes | no — step injection, termination control |
| `Stop` | yes | **yes** |

**`Stop` genuinely blocks — tested, not assumed.** A `Stop` hook printing `{"decision": "continue", "reason": "…"}` on stdout made the agent re-enter the loop and act on the reason after it had already produced its final answer. That is the mechanism this harness's review gate depends on, and it works.

The reason text reaches the model, so a gate message on Antigravity carries the same information as stderr does on Claude Code.

> A hook that continues unconditionally will spin the agent forever. The probe used a one-shot sentinel, and production gates must be equally certain to stop asking — this repo's gates are silent unless a spec branch is finished and unreviewed, which is a condition the model can actually clear.

**Known-issue status.** A [public report](https://discuss.ai.google.dev/t/stop-and-posttooluse-hooks-in-agents-hooks-json-never-fire-antigravity-ide-1-107-0-windows/178288) says `Stop` and `PostToolUse` in `.agents/hooks.json` never fire. On the versions above that is **not reproducible via the global path** — both fire. The CLI changelog carries a fix reading *"lets `Stop` hooks run at all instead of sitting unreachable behind the built-ins"*, so the report predates the fix. Workspace-local `.agents/hooks.json` remains unconfirmed here, pending a trusted-folder test.

## Blocking signal differs between harnesses

| | Claude Code | Antigravity |
| :-- | :-- | :-- |
| Block a turn ending | exit code `2` | stdout `{"decision": "continue", "reason": "…"}` |
| Message to the model | stderr | the `reason` field |
| Non-blocking pass | exit `0` | `{}` |

One gate script can serve both: emit the JSON on stdout **and** exit 2. Each harness reads the channel it cares about and ignores the other.

## Still to verify

- [ ] Workspace-local `.agents/hooks.json` after explicitly trusting the folder.
- [ ] Whether plugin-shipped `hooks.json` fires identically to the global one.
- [ ] `PreInvocation` step injection as the `SessionStart` substitute, including a once-per-session guard.
- [ ] Whether `agy plugin install` targets `~/.gemini/config/plugins/` (where the IDE's plugins live) or `~/.gemini/antigravity-cli/plugins/` (what the CLI docs describe).
- [ ] Antigravity subagent invocation contract, for the reviewer.
