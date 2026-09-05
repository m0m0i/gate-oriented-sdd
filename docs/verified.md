# Verified behaviour

Both target harnesses move fast, so nothing in this repo is designed against documentation alone. Every row below was produced by running the thing on a real install. Re-verify when the version column moves.

Last **updated**: 2026-08-30 — this field records the most recent addition, not a re-run of every row. Each section carries its own provenance; the Antigravity rows below still date from 2026-08-21 and have not been re-checked.

**The version table below was not re-run for the 2026-08-30 addition.** The inception-chain section exercised skills, which are Markdown read by the harness rather than an integration with it, so it produced no evidence about the Claude Code or Antigravity versions named here. It records its own provenance instead: gate-sdd 0.4.0, this repository. Re-dating the table on the strength of a run that did not test it is the failure this file exists to prevent — see #48, which asks that question directly and still needs an answer from a run that does.

## Versions tested against

| Component | Version |
| :-- | :-- |
| Claude Code | 2.1.238 |
| Antigravity CLI (`agy`) | 1.1.17 |
| Antigravity IDE | 2.3.1 |
| Platform | macOS (darwin, arm64) |

## Claude Code subagent invocation

**Subagent invocation is asynchronous, and a turn can still wait for it.** Claude Code 2.1.238.

**The provenance of these rows differs and that matters.** Rows 1 and 2 were observed while implementing #27. Row 3 was *not* — it was written into this file as observed before it had been done, which is the exact failure this document exists to prevent, caught in review. It was confirmed afterwards, on 2026-08-25: a turn held open across twelve read-only tool calls while a spawned reviewer ran, emitting no final message until its result arrived, and the `Stop` gate did not fire. The reviewer confirmed the same from its side. **Row 4 was observed in that same run** — completion arrived as an unrequested notification, and the running-agent listing was polled repeatedly while waiting. It is called out separately because it was added in the same commit as this paragraph and the paragraph did not originally mention it, which is the omission this accounting exists to stop.

| Question | Observed |
| :-- | :-- |
| Does spawning a reviewer return immediately? | **yes** — it returns an id and notifies on completion |
| Is there a blocking/synchronous invocation? | **no** — none is offered |
| Can a turn stay open until the result lands? | **yes** — a turn ends on a final message with no tool call, so continuing to issue read-only calls keeps it open |
| How does the caller learn it finished? | completion arrives as a notification without being asked for; the agent listing reports `running` until then, so it can also be polled |

The third row is the one that matters, and it was asserted false in #27's first draft before being checked. `review-gate.sh` fires on `Stop`; a turn that has not ended does not reach it. So a spawned review *can* be waited for without tripping the gate — the mistake that produced the twenty-five turn loop was emitting a short "still waiting" message between checks, each of which ended the turn and re-armed the gate.

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

**Run on 2026-08-29/30, gate-sdd 0.4.0, against this repository.** Not a cold start: the harness was already installed, `.steering/` populated, and 16 issues already open. That shapes what these rows can claim — `init` was not run, the cold interview was not exercised, and the `- Docs:` path was left at its default rather than probed. Those belong on a throwaway repo and are still unobserved.

Every row below was produced by running the skill and reading the result. Where a row says a seam was **not exercised**, that is the observation — it is recorded because the run set out to test it and could not, and a table showing only what worked would be the failure this file exists to prevent.

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
| Can `epics` describe a product that already ships? | **no.** Step 6, its red flag, and the `Walking skeleton: yes \| no` field all assume greenfield. This system's skeleton shipped weeks ago and the skill offers no way to say so. |
| Do `PRD.md` and `EPICS.md` have a mechanical consumer here? | **no.** Nothing cites a capability or epic id, and no check requires one to exist. Both carry `Status: draft` saying so. See #22. |
| Did running the chain falsify anything already written down? | **yes, two things.** `docs/BACKLOG.md`'s preamble ("`epics` has never run… `docs/` holds none of the inception documents") is false at this tip — #58. And `CAP-1`…`CAP-7` collide with `check-leakage.sh`'s tier-2 pattern, which guards `CAP-[a-z]` while its comment says the numbered forms are the ones that matter — #57. |
| Did the gates and guards survive the run? | **yes.** Eight validators at exit 0 and `test-gates.sh` at 52/0, before and after; `- Owns:` byte-identical; `check-steering-anchors.sh` at 5 of 5 throughout. |

### Two consequences the run created and did not notice

Both were found by the reviewer, not by the run. That is worth recording as plainly as the findings themselves: the section above argues that citation seams are only ever checked forward, and this section is the same defect in the run's own record — AC7 required "any seam that did not join" and the run recorded only the seams it went looking for.

- **#58** — `docs/BACKLOG.md`'s preamble is now false by construction. The file was correctly not edited; the run's job was to say so, and it did not.
- **#57** — the `CAP-` ids this run established collide with `check-leakage.sh`'s tier-2 pattern. The run took deliberate care choosing `LV-` because it appeared nowhere in the repository, and applied none of that care to `CAP-`, which appears in a guard.

### What this run does not support

**The interviews are untested.** The spec chose propose-then-correct: drafts derived from the repository, put to the author for correction. Counting every point at which the run stopped and put a question to the author, there were **four pauses carrying six questions** — four product decisions (the metric, the non-negotiable, CAP-6's falsifier, the third user) and two spec amendments (AC8, AC5). **All six were accepted as recommended.** That cannot distinguish "the drafts were right because the repository already encodes these decisions" from "a plausible answer was accepted because it arrived first with a recommendation" — which is precisely what `northstar`'s own last rule warns about: *"ask the user, and record their answer rather than a plausible one."*

So: this run tests the skills' mechanics and the seams between them. It says nothing about whether they elicit good product decisions from someone who does not already have the answers.

## The inception chain, second half — contract, design-doc

**Run on 2026-09-05, gate-sdd 0.4.2, Claude Code 2.1.252, against this repository.** Second half of the run above, same protocol, and the same shaping fact: not a cold start. What this half could test that the first could not is each skill meeting state it did not write — a hand-authored rulebook of sixteen rules, and a live `structure.md`. Neither skill put a single question to the author; both are derivation from the repository, so the interview caveat below is not weakened by this run, it is simply absent from it.

Full working record: `.specs/56-run-contract-design-doc/observations.md`. Spec: #56.

| Question | Observed |
| :-- | :-- |
| Does `contract` read the rulebook it will write into? | **not by instruction.** Step 1 lists `tech.md`, linter and formatter config, the code, the last fifty commits and review comments; the existing rulebook is not on the list. It was read anyway, and the result was a merge by appending — but the merge came from the operator, as `northstar`'s `product.md` merge did above. |
| What does step 4 do to a rulebook it did not author? | **appended two rules, changed nothing.** All sixteen ids at their severities, `+3/−0` lines. The two new rules continued the existing `C-` series; the template's `PFX-001` form was not adopted and the skill gives no rule for which wins. |
| What does "re-pin the lock" do on a reviewer with no lock? | **prints success and exits 0.** `./assets/check-locks.py --update`, run after the rulebook edit: `check-locks: 6 pinned file(s) match their locks in .claude/agents, agents`, exit 0, no lock created, the edited rulebook never hashed. #19 live — and since #16 the message names `.claude/agents` as a directory it verified, which it did not. A consumer following the step gets a green line and an unpinned rulebook. |
| Would step 6's sentence have been true? | **no.** *"Record… that the rulebook is generated from"* the contract. Here the contract was compiled from the rulebook. Written the true way round, deviation recorded; this was decided before the run (spec clarification 2), not during it. |
| Does the tier table fit a project with no linter? | **partly.** The Mechanical tier's stated home is "linter, formatter, type checker config"; here it is nine validators, CI, a `PostToolUse` hook and a test case. Tiered as Mechanical with the real enforcer named. Step 5 had nothing to move. |
| Can three tiers express this repo's third layer? | **no.** Process enforced by a skill has no tier but Narrative, whose definition is "nothing enforces it". |
| Does the contract's table create a fact stated twice? | **yes.** Every Judgment row indexes a rulebook rule; the lock pins the rulebook, not `CONTRACT.md`, and nothing compares them. |
| Does `design-doc` say what to do with a `structure.md` that exists? | **no.** Step 5 says "write". It was reconciled, `+5/−2`, and the reconciliation found the `docs/` row had been false since #55 through two runs and a review. |
| Does the reviewer's reconciliation clause escalate to an ADR? | **no.** `grep ADR` is 0 across the reviewer file, the shared contract and the rulebook. The clause says "a written decision". The reviewer can now reach `docs/decisions/` through `structure.md`, which its load order reads first; whether it does is unobserved. |
| Does the ADR template fit a decision recorded after it was taken? | **no.** One `Date:` field; every ADR here carries two. Greenfield does not have this problem, as with `epics`' walking skeleton. |
| Did either skill create a second id vocabulary? | **one did.** `contract`'s table forced `M-`/`N-` ids on Mechanical and Narrative rows nothing cites. `design-doc`'s seam ids are conditional on multi-repo and were not created. |
| Did running the chain falsify anything already written down? | **yes, and found five things already false.** `DESIGN.md` cites every capability id, so `product.md` and `PRD.md` no longer truly say nothing does; and the reread found both READMEs claiming no reviewer has reviewed a real diff, the Japanese README mistranslating that line, two files citing closed #16 as the reason the dogfood lock is absent, and `layout.md`'s picture of `docs/`. Table with owners: `observations.md`, T4. |
| Did the gates and guards survive the run? | **yes.** Nine validators at exit 0 and `test-gates.sh` at 54/0 before and after; all five anchor lines byte-identical; the three shipped locks byte-identical; nothing under a shipped path changed, so no version bump. |

### What the first half's record gets wrong now

The row above reading *"Nothing cites a capability or epic id"* is half false after this run: `DESIGN.md` cites the capabilities in prose. *No mechanical consumer* is still the true statement, for both.

### What this run does not support

Neither skill paused. `contract` derives everything from the repository, and `design-doc`'s one open judgment — which decisions were contested — was made by the operator and is corrected at pull-request review, not in an interview. So this half says nothing about eliciting decisions, and the caveat above stands unchanged.

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
- [ ] `--update` on a reviewer that has a lock and a changed rulebook — the shipped rulebooks were untouched, so only the unchanged path ran.
- [ ] `contract` and `design-doc` on a second run, against a `CONTRACT.md` and a `structure.md` that already exist and disagree with the repository.
- [ ] Whether a reviewer reaches `docs/decisions/` through `structure.md` when its rulebook and the repository conflict.
