# .specs/

One directory per issue, named `<issue-number>-<kebab-title>` — the same string as the branch and the spec, so an issue, a branch, a spec, and a PR are always one unit of work.

Each holds `spec.md` and, once a review has run, `.review-receipt`.

`Status:` moves `draft` → `approved` → `done` → `archived`, and one skill owns each edge, so the status always says something true about who touched it last. A spec is not implementable until you have agreed it and the status reads `approved` — the spec is the first commit on the issue's branch, not a pull request of its own.

The review gate reads this directory. A spec whose slug does not begin with an issue number blocks the turn: work that never had an issue entered through the side door.

Shipped specs move to `_archive/` in a sweep run on request — `archive` is not a step in the per-issue flow. `done` is where delivery ends, so a merged spec still sitting here is finished work awaiting bookkeeping rather than a loose end, and the review gate never sees it. The gate reads the specs each branch carries, which are the one named for the branch and the ones the branch adds against the default branch. It reads the current branch's from the working tree, and each other local branch's from that branch's own tree until the branch has shipped. It never globs this directory.
