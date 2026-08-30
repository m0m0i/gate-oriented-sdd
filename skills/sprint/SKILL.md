---
name: sprint
description: Decompose the top of the product backlog into typed tracker issues for this iteration — each sized as one issue, one branch, one spec, one PR. Use at the start of an iteration. This is where a plan becomes committed work.
---

# sprint — Turn ordered plan into issues someone can pick up

The moment planning becomes commitment. Everything before this is a document that changes for free; an issue is a promise, and it is where a person's name goes.

**One backlog item usually becomes several issues.** That decomposition is the work this skill does — not selection, which the backlog already settled by ordering. An item and an issue are different sizes, and pretending otherwise is how a plan looks precise while being wrong.

Its output is **typed tracker issues**, because `spec <issue>` is where delivery starts. The type is not decoration: `spec` reads it to choose the shape of the spec it writes.

## Where it goes

Into the **tracker**, not into a file. This skill writes no document: the issues it creates are the record, and a parallel markdown copy of them would be a second source of truth that drifts from the first.

If the iteration is worth a retrospective, that belongs in `.work_logs/` via `worklog`, which is already the append-only record of what happened.

## Steps

1. Read the product backlog and the epics. **Take from the top.** The order already encodes value, risk, cost, and dependency; an iteration assembled by picking interesting items from further down silently overrides a decision someone already made. If the top item is genuinely wrong to start now, that is not a reason to skip it — it is a reason to re-groom. Go and change the order in `backlog`, with the reasoning recorded, then come back and take from the top. Reordering by selection leaves the document saying one thing while the team does another.
2. **Decompose each item into issues.** Split until each one is genuinely *one branch's worth of work* — one spec, one PR, one review. The usual seams:
   - the change itself
   - test coverage the change turns out to need but that does not exist yet
   - a migration, rename, or dependency bump the change forces
   These are different issue *types*, which is the point: they get differently shaped specs.
3. **Type each issue as you create it** — `feature`, `bug`, or `chore` — from the matching template in `.github/ISSUE_TEMPLATE/`, with the matching label. The type is decided here, at decomposition, not earlier: one backlog item routinely yields a feature and a chore, so it never had a single type to inherit.
4. **Create the issues for this iteration only.** Everything else stays in the backlog, where it costs nothing. An issue nobody will touch for two months is noise in every future search, and it ages into a decision nobody remembers making.
5. **Say what is deliberately left out**, and why. This is what stops the same argument recurring mid-iteration.
6. Optionally group them with the tracker's native container — a GitHub milestone, a Linear cycle, a Jira sprint — if you want a due date and a progress view. It is a grouping label, nothing more: no spec, no branch, no PR hangs off it.

## Rules

- **One issue = one spec = one branch = one PR.** If an issue cannot be closed by a single PR, it is more than one issue. This is the invariant the whole flow rests on, and the first exception is how it stops being one.
- **Every issue is typed.** An untyped issue makes `spec` guess, and it guesses feature — the wrong shape for a bug and for a chore.
- **Take from the top.** Skipping down the list is re-ordering without recording it, and the backlog stops describing what actually happens.
- **Decompose here, not in the backlog.** Ordering coarse items is cheap and revisable; decomposing early freezes guesses into the plan.
- **Issues for this iteration only.**
- **Unplanned work is visible.** A bug found mid-iteration that must be fixed now gets its own issue and is named as unplanned when the iteration is reviewed. Silently absorbing it is how an iteration appears to have gone well while the plan quietly stops meaning anything.
- Group with a milestone if it helps, but nothing in the flow depends on it.

## Red flags

- Every issue is a feature. Real iterations carry bugs and chores; one that carries none is either a very new project or deferring both.
- An issue's title matches a backlog item's exactly. Then no decomposition happened, and the missing test coverage and the forced migration are hiding inside a single PR that will be too large to review.
- An issue that cannot be sized. That is a spike — make it a chore whose deliverable is an answer, not an implementation.
- The iteration's issues come from positions 1, 4, and 9. Either the order is wrong and should be fixed, or it is being ignored — and both are worth saying out loud.
- Issues created for the next three iterations. Only the current one is a commitment; the rest is a plan wearing a tracker's clothes.
