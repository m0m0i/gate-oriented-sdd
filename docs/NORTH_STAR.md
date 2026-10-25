# North star

- Status: updated on 2026-10-25

## What this is for

**You design; agents build.** gate-sdd splits design work into pieces you can think through in a short slot, and the gate makes sure agents build nothing outside them. You stop being the blocker, but you never stop being the one who decides.

It is for building a real application with professional practice: every change traces to a decision, is reviewed and tested, nothing changes by accident, decisions are written down, and another engineer could take the project over from its documents alone. It keeps the old order — make it work, make it right, make it fast — and goes through it as quickly as possible.

## The metric

**Re-entry time: the minutes from opening a project after time away until the engineer can answer three questions — what was done last, what is in progress and where it stopped, and what is next and why.**

The engineer this serves has many duties and no three-hour focus block. Work happens in short slots, and every slot starts by reloading context. When re-entry takes minutes, a free half hour is enough to decide the next piece; when it takes an hour, the engineer is the blocker again.

Measured two ways: a scheduled re-entry check, in which a fresh agent session answers the three questions on each project and a checker grades the answers; and, now and then, one line in the project's work log — days away, minutes — when the engineer comes back after at least a day. An answer only counts if it is right — asking the agent is allowed, and is the point, but a wrong "what is next" is worse than a slow one. Baseline, 2026-10-19: a fresh agent session on four projects, 1 to 15 days away, answered "what was done last" correctly 3 of 4 times and "what is next" correctly 0 of 4 times, twice misleadingly.

**Guardrail — plan adherence:** the share of merged pull requests whose change traces through the whole chain (PR → spec → issue → backlog item or triage record → PRD capability, plus a roadmap milestone under `full` for work created after `full` was turned on) with a review receipt at the PR's head. Re-entry time must not improve by cutting the chain.

## Levers

- **LV-1 Pieces one engineer can hold** — one issue, one spec, one branch, one pull request, each small enough to understand without reading the code. The engineer writes the deciding sentences; agents draft, build and review.
- **LV-2 Plan adherence** — every change to source traces to the plan, and the gate refuses one that does not. Source includes dependency manifests and lockfiles: a dependency bump has an issue and a spec whose impact research decides its tests. Code without a spec is blocked.
- **LV-3 Where you stopped** — asked where things stand, a session answers right at the lowest latency and token cost, from state the harness keeps: behind or ahead of origin, the newest work log with each open next step and its real state, the active pull request, the backlog's top row for this repository, and open issues the backlog has not placed. This is the lever that moves the metric directly.
- **LV-4 Strict about what, cheap about when** — fast checks at turn end; the full chain check when the pull request is created; the same check again in CI. A gate that fires every turn on guesses gets switched off, so the counterweight to LV-2 is false blocks per real block.
- **LV-5 Field signal first** — a bug from real use is triaged before any new spec starts, then fixed by severity; a gate that passes when it should block, or lost work, goes first. A fix reaches the projects running the harness without anyone copying files.

LV-1 comes first: if a piece is too big to hold, the rest enforces a plan nobody understands. LV-2 and LV-3 move the number. LV-4 keeps LV-2 switched on, and LV-5 is how it quietly gets worse.

## Quality laws, in priority order

1. **A gate fails closed.** When it cannot tell, it blocks and records why. The only way past a block that is not the work's fault is a visible override with a written reason, approved by the engineer, and CI checks again. A check that passes having verified nothing is indistinguishable from one that worked.
2. **A gate stays welcome by being cheap about when, never lenient about what.** It runs where the question is meaningful and is silent elsewhere, but it never stops checking a change.
3. **A claim is reproducible.** Anything the harness says about itself is tested, or labelled unverified in the same sentence.

When two conflict, the higher one wins, and law 2 is satisfied by scoping a check, never by softening it. The chain check would block ordinary mid-implementation turns, so law 2 moves it to pull-request creation and CI, where it still fails closed. The counter-example is the old rule that kept the gates silent on work with no spec: narrowness bought by softening, and 24 of 31 unreviewed merges in the 2026-10-11 field review were exactly that work.

## Non-negotiable

**The agent never decides what to build; the engineer controls it.**

An agent drafts plans, proposes the order and builds, but the sentences that decide what gets built — the north star, a capability, a backlog position, a spec's scope — are the engineer's. The live instance is this document: the first north star was proposed by an agent on 2026-08-29 and stayed a draft "pending the author's correction" for 51 days, while everything below it was built on top. Accepting a well-written draft is always faster, and a week with no free hour makes it tempting every time.

What it costs: work waits for the engineer's sentence, even when an agent could have written a plausible one in seconds.

## Owns

**Gates never fail open** — law 1, as in `.steering/product.md`. A change to source that reaches a merge with no spec, or with a review of a different commit, is a fail-open too, not a scope choice.

This repository and not a project using it, because this repository *is* the enforcement: a project inherits whatever this one gets wrong. A defect that lets a gate pass when it should have blocked is at least HIGH; one that makes a gate silently stop checking is a BLOCKER.
