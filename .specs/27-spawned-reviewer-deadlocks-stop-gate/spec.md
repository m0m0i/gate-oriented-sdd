# Spec: a spawned reviewer deadlocks the Stop gate into an unbreakable loop

- Slug: 27-spawned-reviewer-deadlocks-stop-gate Issue: 27 Type: bug Status: approved
- Author: m0m0i Date: 2026-08-25

## 1. Requirements (WHAT / WHY)

- Reproduction: on a branch whose spec has every task ticked and no `.review-receipt`, follow
  `skills/implement/SKILL.md` step 2 — _"Invoke the reviewer subagent named in `.steering/tech.md`"_.
  The reviewer runs asynchronously and takes minutes. Attempt to end the turn:

  ```
  Review gate: every task in .specs/<slug>/spec.md is ticked, but no reviewer receipt
  exists. Run gate-sdd-reviewer on the branch diff, then write its Receipt block to ...
  ```

  It repeats on every subsequent attempt until the reviewer returns.

- Expected: the workflow `implement` prescribes can be followed without the gate firing on it.

- Actual: an unbreakable loop. Observed cost: roughly twenty-five turns in one session before the
  user interrupted, and the only exit found was `git checkout main` — which is #26.

- Impact: every `implement` that uses a spawned reviewer, which is the path the harness recommends
  and the one #9 changed `init` to guarantee is available. **The harness deadlocks on the path it
  tells you to use and works fine on the fallback it calls second-best.** Both gates ship enabled,
  so a new project reaches this on its first reviewed spec.

- **Root cause:** `review-gate.sh` fires on `Stop` and therefore assumes the review completes
  _inside_ the turn. That assumption held for the whole of this repo's history by accident — every
  prior review was inline, run synchronously by the author of the diff. The first genuinely spawned
  review broke it within seconds.

  **Corrected after review — the first version of this root cause was wrong, and the fix that grew
  out of it was wrong with it.** It claimed "an agent has no wait primitive". That is false. A turn
  ends when the agent emits a final message with no tool call; it stays open across tool calls. So
  waiting is available: keep issuing read-only calls until the result lands and emit nothing final
  before it does. A turn that has not ended cannot trip a gate that fires on turn end.

  What actually happened is narrower and more embarrassing. During the deadlock the pattern was
  *check the agent, then say "Holding."* — and that second half is a final message. Each one ended
  the turn and re-armed the gate. Twenty-five turns were spent re-arming a trap by announcing that
  I was waiting instead of waiting.

  So the defect is that **nothing said how to wait.** `implement` told the author to invoke a
  reviewer and said nothing about what to do while it ran, and the gate's message named an action
  the author had no reason to believe was available.
  Writing a receipt to escape is what `implement` forbids most explicitly; un-ticking a finished
  task is the same lie wearing bookkeeping.

- Acceptance criteria:
  - [x] **AC1:** following `implement` step 2 as written SHALL NOT produce a turn that cannot end.
  - [x] **AC2:** WHEN the gate blocks for a missing receipt, its message SHALL NOT instruct the
        author to start a review that may already be running — the instruction must be actionable.
  - [x] **AC3:** no change SHALL introduce a state in which the gate stops blocking while a spec has
        ticked tasks and no CLEAN receipt. A quieter gate is a fail-open, and this is the only
        enforced rule in the harness.
  - [x] **AC4:** the gate SHALL gain no new state. No counter, no marker, no file written by
        either the author or the gate to record that a review is in flight. Recorded as a criterion
        because it was the rejected alternative, and because any such marker is a line someone can
        write to make the only enforced rule go quiet.
  - [x] **AC5:** the spec SHALL declare which criteria are presence assertions rather than
        behavioural ones. **Declared: AC1 is presence-only** — it is a sentence in a skill, checked
        by `check-skill-contracts.py` asserting the sentence exists. Nothing here can check that a
        model obeys it; only an eval could, and `evals/` has never run. AC2 and AC3 are behavioural and
        testable in `scripts/test-gates.sh`. **AC4 is inspected, not tested** — no case asserts the
        gate creates no files; it is verified by reading the diff, which is one string literal
        inside an existing branch.

- Out of scope: **#26.** The `git checkout` escape is the symptom this drove the author into three
  times, and the backlog deliberately orders it _after_ this — closing the escape while the
  deadlock stands would leave a stuck turn with no exit at all.

### Clarifications

- **Q: the plugin cannot break the loop without failing open. What should ship?**
  A: a prose mandate plus a truthful message. `implement` step 2 mandates a _synchronous_
  invocation, so the gate's assumption becomes true by construction rather than by luck. Nothing
  about the gate's blocking behaviour changes, which makes AC3 safe by construction rather than by
  care.
- **Q: should the gate detect the stuck state and report it?**
  A: no — rejected, and pinned as AC4. It would not break the loop, only narrate it, and it buys
  that narration with gate-owned state in `.specs/` that can drift, be deleted, or be mistaken for
  something the author maintains. A counter is a poor trade for a message.
- **Q: close it as a harness constraint instead?**
  A: no. It is true that a blocking `Stop` hook cannot coexist with an async subagent, but that is
  an argument for not spawning async — not for leaving the recommended path broken and documenting
  the wreck.
- **Q: how far should the message go — should it name the `git checkout` escape as forbidden?**
  A: no. Naming it advertises #26 to every reader who had not thought of it, at the moment they are
  most tempted. The message names _waiting_ as the valid action and stops there.

### The uncomfortable part, stated before Design exists

The plugin ships prose and shell. It cannot change how a harness spawns subagents. Of the four
candidate fixes below, two actually break the loop, and the one adopted here is the one this repo
can least verify:

| Candidate | Breaks the loop? | Testable? |
| :-- | :-- | :-- |
| `implement` mandates a **synchronous** invocation, and says how to wait | yes | presence only, like #9's AC3 |
| the gate detects repeated blocks and says so | no — it narrates, and buys that with gate-owned state | yes |
| the message stops giving unactionable advice | no, but it stops misleading | yes |
| **move the check off `Stop`** — block on `PreToolUse` for `git push` / `gh pr create` | yes, and it cannot loop: it fires at a boundary crossed deliberately, not on every reply | yes |

The fourth was missed on the first pass and is not obviously worse. It enforces the promise the
harness actually makes — `implement` says *"Do not open a PR before the reviewer pass is clean"*,
and `README.md` sells a receipt rather than a turn-end trap — while adding no state and never
passing on unreviewed code. It is **not** adopted here: `Stop` is strictly stricter, and a
`PreToolUse` gate sits nearer to #26's shape. Recorded so the decision is one someone can argue
with rather than one nobody knows was made. Worth its own issue.

One rejection in the first draft proved too much and is withdrawn: *"any in-flight marker is
author-forgeable"*. Every input this gate reads is author-forgeable — the receipt is a file the
author writes, the ticks are checkboxes the author types. Forgeability is not the threat model;
visible, deliberate, diffable lying is. The sound half of that rejection stands on its own: a gate
that **passes** while a review is in flight is a fail-open.

Anything that makes the gate _pass_ while a review is "in flight" is a fail-open, and any marker
the author writes to signal that is the fabricated receipt one step further back. So the real fix
is on the caller, and the caller is prose.

## 2. Design (HOW)

- Fix approach, and why this rather than the narrower or wider fix:
  Two edits, in different layers, doing different jobs.

  **`skills/implement/SKILL.md` step 2** gains the mandate: invoke the reviewer and wait for its
  result within the same turn; do not spawn it and continue. The reason travels with the rule,
  because a rule whose reason is elsewhere gets optimised away — nothing useful can happen during a
  review anyway, since touching the files under review is precisely what must not happen while it
  reads them.

  **`hooks/review-gate.sh`'s missing-receipt message** stops giving advice that cannot be taken. It
  keeps the instruction and adds that if a reviewer is already running, waiting for it is the
  correct action rather than starting another.

  _Narrower, rejected:_ the message alone. It makes the loop honest and leaves it a loop.

  _Wider, rejected:_ anything that lets the gate pass while a review is "in flight". Every version
  of that is a fail-open, and every marker signalling it is a line the author can write — the
  fabricated receipt one step further back. AC4 pins this shut.

- Affected files: `skills/implement/SKILL.md`, `hooks/review-gate.sh`,
  `scripts/check-skill-contracts.py`, `scripts/test-gates.sh`, and both manifests for the bump.

- **Blast radius:** the message text is asserted by an existing case —
  `scripts/test-gates.sh:174` matches `"no reviewer receipt exists"`. That substring must survive
  the rewording or the case breaks, and it breaking would be the _good_ outcome; the bad one is
  rewording around it so the case passes while asserting something no longer central. T3 checks the
  full case list against `origin/main` rather than trusting the totals. `check-skill-contracts.py`
  gains a fourth needle, and its `len(CONTRACTS) < 2` floor is unaffected.

- Why this cannot recur: it cannot, fully, and saying otherwise would be the overclaim this repo
  exists to prevent. The mandate is prose; a model can ignore it and the presence check cannot tell.
  What changes is that the async path stops being the _recommended_ one, so reaching the deadlock
  requires going against a written instruction rather than following one.

## 3. Tasks (TDD-ordered)

> Folded red-and-green per #10: one task is one complete Red-Green-Refactor cycle.

- [x] T1: failing case in `test-gates.sh` — the missing-receipt message names waiting as a valid
      action when a review may be in flight — then the `review-gate.sh` reword that makes it pass,
      keeping `no reviewer receipt exists` intact so case 13 still asserts what it always did
- [x] T2: failing needle in `check-skill-contracts.py` for the synchronous mandate — then the
      `implement` step 2 rewording. **AC5 applies: presence, not adherence.**
- [x] T3: blast radius — diff the full case list against `origin/main`'s hooks and confirm no
      pre-existing case changed verdict, and that AC4 holds by inspection: no file is created,
      written, or read that was not before
- [x] T4: refactor
