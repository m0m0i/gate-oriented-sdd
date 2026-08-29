---
name: archive
description: Sweep shipped specs out of .specs/ into .specs/_archive/ and set Status archived, so a session globbing .specs/ sees only live work. Use on request, when .specs/ has accumulated enough finished work to be noise — not after every merge.
---

# archive — Retire shipped specs

`.specs/` grows monotonically, and every stale spec is context a future session pays for and may act on. Archiving is how the directory keeps meaning what it claims: **`.specs/` is live work.**

**This is a sweep you run when you choose, not the step that follows a merge.** One shipped spec is a `git mv`, and a branch, a review and a merge to carry it is more process than the change contains — a flow with that step in it spends a second pull request per issue on a diff nobody reads. Nothing mechanical is waiting either: the review gate reads `.specs/<current branch>/spec.md`, so a shipped spec still sitting in `.specs/` cannot block a turn or stale a receipt. What it costs is **context, per session rather than per spec**, which is why the right trigger is a directory that has grown noisy rather than a merge that has just happened.

There is one direction in which this is not symmetric, and it is worth knowing before you sweep: archiving the spec of the branch you are **on** moves `.specs/<branch>/spec.md` out from under the review gate, which passes on any branch it finds no spec for. That silences the gate for that branch entirely, receipt freshness included. Sweeping from its own branch, as below, is what keeps it out of reach.

## Steps

1. Determine the targets — a named slug, or with `--swept`, every spec whose `Status` is `done` **and** whose PR has merged. Check the tracker when in doubt; do not archive work that merely looks finished.
2. For each target:
   - Move it with **`git mv .specs/<slug> .specs/_archive/<slug>`** — never copy-then-delete; history has to follow the file.
   - Set front matter `Status: archived` and append `Archived: <YYYY-MM-DD>`.
3. **Leave the slug and directory name exactly as they are.** Work logs, PR bodies, and any docs hub resolve these by slug; a rename quietly breaks every one of them.
4. Report what moved and what you deliberately left live.

## Rules

- Archive is a **move, not a delete**. An archived spec stays readable, greppable, and citable.
- Never archive a spec with unticked tasks or `Status: draft`/`approved` without saying plainly that it is unfinished work — even if asked to.
- One sweep per session at most. This is bookkeeping; it should never become the session's work.
- **A sweep is its own small commit, on its own branch.** Batched, that is one pull request for several specs rather than one per spec — and if the repository allows committing to the default branch directly, it does not need a pull request at all.
- `done` is where the delivery chain ends. `archived` is bookkeeping applied afterwards, so a spec that is merged but not yet swept is finished work, not a loose end.
