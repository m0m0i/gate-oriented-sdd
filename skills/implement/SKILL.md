---
name: implement
description: Execute an approved .specs/<slug>/spec.md through the TDD Red-Green-Refactor loop, then pass the mandatory reviewer gate before any PR. Use after a spec has been reviewed and approved.
---

# implement — Build a spec, task by task

## Preconditions

- A spec exists at `.specs/<slug>/spec.md`. If `<slug>` is omitted, list the live specs and ask which one.
- Its `Status` is `approved`. If it is `draft`, say so and ask before starting — implementing an unreviewed spec is how a misread requirement becomes a merged branch. If it is `done` or `archived`, this is a resume or a mistake; establish which.
- The branch is `<slug>`. Offer to create it from the default branch.
- `.steering/tech.md` names this project's validators and its reviewer. **Read it now; never assume commands.**

## The loop

For each task in the spec's Tasks list, in order:

1. **Red** — write the failing test the task names. Run it. Confirm it fails **for the stated reason**, not for a setup error. A test that fails because of a typo has proved nothing.
2. **Green** — the smallest implementation that passes. Run the tests.
3. **Refactor** — clean up under green tests. Re-run the validators.
4. Tick the task, then make one commit scoped to that task, in this project's commit convention (see `.steering/tech.md`).

## Review gate — mandatory

When every task is committed and the validators pass:

1. Run the full validator set from `.steering/tech.md`. Set the spec `Status: done`.
2. **Invoke the reviewer subagent** named in `.steering/tech.md`, asking it to review the branch diff against the default branch, and against `.specs/<slug>/spec.md`.
   **Invoke it and wait for its result in the same turn. Do not spawn it and carry on.** The review gate runs on turn end, so it assumes the review finished inside the turn.
   **If your harness returns from the invocation immediately and notifies you later, waiting means keeping the turn open** — keep issuing read-only calls until the result arrives, and emit no final message before it does. Completion normally arrives as a notification without being asked for; if your harness lists running agents, that listing can be polled instead. A turn that has not ended cannot trip a gate that fires on turn end. Announcing that you are waiting *is* ending the turn, and it re-arms the gate every time — that mistake cost twenty-five turns in the repository this harness was built in.
   Nothing useful can happen during a review anyway, because touching the files it is reading is exactly what must not happen. If the reviewer genuinely cannot be invoked at all — not registered, added mid-session and needing a restart, or the harness has no subagents — run its procedure yourself from its agent file and record `reviewed_by=inline`.
3. Address every **BLOCKER** and **HIGH** through the TDD loop: a failing test, then the fix. Re-run the reviewer until none remain. Triage MEDIUM/LOW/INFO explicitly — fixed, or recorded with a reason.
4. **Write the receipt.** The reviewer is read-only, so you record its result at `.specs/<slug>/.review-receipt`, copying its Receipt block verbatim:

   ```
   reviewed_sha=<git rev-parse HEAD at review time>
   reviewer=<reviewer name>
   verdict=CLEAN|BLOCKED
   blockers=<n>
   high=<n>
   reviewed_at=<YYYY-MM-DDTHH:MM:SSZ>
   reviewed_by=subagent|inline
   ```

   `reviewed_by` records **how** the review was obtained, not who ran it. `subagent` means
   the reviewer ran as its own agent, outside this session's context, which is the
   independence the whole layer exists to provide. `inline` means step 2's fallback was
   taken and the author of the diff ran the reviewer's procedure themselves — still useful,
   since it finds real defects, but not independent, and a reader of the receipt cannot tell
   the difference unless you write it down. **Never record `subagent` for a review you ran
   inline.** It is the same lie as a receipt for a review that did not happen, one step
   quieter.

   The review gate reads this file and refuses to end a turn when a spec whose tasks are all ticked has no receipt, a non-CLEAN one, or one whose `reviewed_sha` predates a later source change.

   **Never write a receipt for a review that did not run.** The gate catches omission and staleness; a fabricated receipt defeats the only mechanical check in the flow, and it defeats it silently.
5. Run `worklog`, then summarize the diff and propose the PR, closing its issue.

## Rules

- **Never write implementation code before its failing test exists.**
- One task, one commit. No batching, no half-tasks.
- **If a task proves the spec wrong, stop.** Amend `.specs/<slug>/spec.md`, say what changed and why, and get agreement before resuming. Do not code around a spec you no longer believe.
- Match the surrounding code. `.steering/structure.md` says where code belongs.
- Do not open a PR before the reviewer pass is clean of BLOCKER/HIGH.
- Commits landing **after** the review — the work-log entry, the `Status: done` flip — do not invalidate the receipt; the gate only re-triggers when reviewable source changes. Fixing a finding *is* source: re-review, and rewrite the receipt.
