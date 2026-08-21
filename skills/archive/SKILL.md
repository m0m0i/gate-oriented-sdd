---
name: archive
description: Move shipped specs to .specs/_archive/ and set Status archived, so a session globbing .specs/ sees only live work. Use after a spec's PR merges, or to sweep accumulated done specs.
---

# archive — Retire shipped specs

`.specs/` grows monotonically, and every stale spec is context a future session pays for and may act on. Archiving is how the directory keeps meaning what it claims: **`.specs/` is live work.**

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
