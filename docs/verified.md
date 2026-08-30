# Verified behaviour

Both target harnesses move fast, so nothing in this repo is designed against documentation alone. Every row below was produced by running the thing on a real install. Re-verify when the version column moves.

Last **updated**: 2026-08-30 — this field records the most recent addition, not a re-run of
every row. Each section carries its own provenance; the Antigravity rows below still date from
2026-08-21 and have not been re-checked.

**The version table below was not re-run for the 2026-08-30 addition.** The inception-chain
section exercised skills, which are Markdown read by the harness rather than an integration with
it, so it produced no evidence about the Claude Code or Antigravity versions named here. It
records its own provenance instead: gate-sdd 0.4.0, this repository. Re-dating the table on the
strength of a run that did not test it is the failure this file exists to prevent — see #48,
which asks that question directly and still needs an answer from a run that does.

## Versions tested against

| Component | Version |
| :-- | :-- |
| Claude Code | 2.1.238 |
| Antigravity CLI (`agy`) | 1.1.17 |
| Antigravity IDE | 2.3.1 |
| Platform | macOS (darwin, arm64) |

## Claude Code subagent invocation

**Subagent invocation is asynchronous, and a turn can still wait for it.** Claude Code 2.1.238.

**The provenance of these rows differs and that matters.** Rows 1 and 2 were observed while
implementing #27. Row 3 was *not* — it was written into this file as observed before it had been
done, which is the exact failure this document exists to prevent, caught in review. It was
confirmed afterwards, on 2026-08-25: a turn held open across twelve read-only tool calls while a
spawned reviewer ran, emitting no final message until its result arrived, and the `Stop` gate did
not fire. The reviewer confirmed the same from its side. **Row 4 was observed in that same run** — completion
arrived as an unrequested notification, and the running-agent listing was polled repeatedly while
waiting. It is called out separately because it was added in the same commit as this paragraph and
the paragraph did not originally mention it, which is the omission this accounting exists to stop.

| Question | Observed |
| :-- | :-- |
| Does spawning a reviewer return immediately? | **yes** — it returns an id and notifies on completion |
| Is there a blocking/synchronous invocation? | **no** — none is offered |
| Can a turn stay open until the result lands? | **yes** — a turn ends on a final message with no tool call, so continuing to issue read-only calls keeps it open |
| How does the caller learn it finished? | completion arrives as a notification without being asked for; the agent listing reports `running` until then, so it can also be polled |

The third row is the one that matters, and it was asserted false in #27's first draft before being
checked. `review-gate.sh` fires on `Stop`; a turn that has not ended does not reach it. So a spawned
review *can* be waited for without tripping the gate — the mistake that produced the twenty-five
turn loop was emitting a short "still waiting" message between checks, each of which ended the turn
and re-armed the gate.

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

## The inception chain — northstar, prd, epics

**Run on 2026-08-29/30, gate-sdd 0.4.0, against this repository.** Not a cold start: the harness was
already installed, `.steering/` populated, and 16 issues already open. That shapes what these rows
can claim — `init` was not run, the cold interview was not exercised, and the `- Docs:` path was
left at its default rather than probed. Those belong on a throwaway repo and are still unobserved.

Every row below was produced by running the skill and reading the result. Where a row says a seam
was **not exercised**, that is the observation — it is recorded because the run set out to test it
and could not, and a table showing only what worked would be the failure this file exists to
prevent.

Full working record: `.specs/55-run-northstar-prd-epics/observations.md`. Spec: #55.

| Question | Observed |
| :-- | :-- |
| Does `northstar` write a parseable `- Owns:` line? | **not exercised** — step 5 derived the value already present, so nothing was written. The collision path is unobserved. |
| Does `northstar` preserve an existing `Owns:` it disagrees with? | **unknown.** It agreed. This run shows only that it does not gratuitously rewrite an anchor it accepts. |
| Does an id prefix chosen in `northstar` survive downstream? | **partly.** `LV-` reached `PRD.md` intact. It never reaches `EPICS.md`, which cites capabilities, not levers — so the question does not arise there. |
| Does the harness impose an id vocabulary? | **yes, for epics.** `northstar` says "the harness does not impose a vocabulary; pick one and keep it", and the `epics` template hardcodes `EPIC-<n>`. The chosen prefix governs levers and capabilities; epic ids are the template's. |
| Does `prd` check that every lever is served? | **no.** It checks the forward direction only — that each capability names a real lever. The first draft left `LV-2` served by nothing and passed. |
| Does `epics` check that every capability has an epic? | **no.** Same asymmetry. The first draft left CAP-3 and CAP-4 served by nothing while their work sat in three epics under other `Serves:` lines. |
| Does `prd` say what to do when `.steering/product.md` already has content? | **no.** Step 7 says "summarise into". The additive merge here — 19 insertions, 0 deletions, `Owns:` intact — came from the operator. Replacing the file would be equally compliant with the text. |
| Same question for `northstar` step 6? | **no**, identically. Two skills write that file; neither states a merge rule. |
| Can `epics` describe a product that already ships? | **no.** Rule 6, its red flag, and the `Walking skeleton: yes \| no` field all assume greenfield. This system's skeleton shipped weeks ago and the skill offers no way to say so. |
| Do `PRD.md` and `EPICS.md` have a mechanical consumer here? | **no.** Nothing cites a capability or epic id, and no check requires one to exist. Both carry `Status: draft` saying so. See #22. |
| Did the gates and guards survive the run? | **yes.** Eight validators at exit 0 and `test-gates.sh` at 52/0, before and after; `- Owns:` byte-identical; `check-steering-anchors.sh` at 5 of 5 throughout. |

### What this run does not support

**The interviews are untested.** The spec chose propose-then-correct: drafts derived from the
repository, put to the author for correction. Across three skills, **all four product decisions
came back confirmed exactly as drafted.** That cannot distinguish "the drafts were right because
the repository already encodes these decisions" from "a plausible answer was accepted because it
arrived first with a recommendation" — which is precisely what `northstar`'s own last rule warns
about: *"ask the user, and record their answer rather than a plausible one."*

So: this run tests the skills' mechanics and the seams between them. It says nothing about whether
they elicit good product decisions from someone who does not already have the answers.

## Still to verify

- [ ] Workspace-local `.agents/hooks.json` after explicitly trusting the folder.
- [ ] Whether plugin-shipped `hooks.json` fires identically to the global one.
- [ ] `PreInvocation` step injection as the `SessionStart` substitute, including a once-per-session guard.
- [ ] Whether `agy plugin install` targets `~/.gemini/config/plugins/` (where the IDE's plugins live) or `~/.gemini/antigravity-cli/plugins/` (what the CLI docs describe).
- [ ] Antigravity subagent invocation contract, for the reviewer.
- [ ] `northstar` meeting an `Owns:` line it disagrees with — the collision path #55 could not reach.
- [ ] The cold interview: `northstar`, `prd`, `epics` answered by someone without the repository's context.
- [ ] `init` on a greenfield repo, including detection and the five-question interview.
- [ ] Whether a non-default `- Docs:` path reaches every inception skill, or any of them hardcode `docs/`.
