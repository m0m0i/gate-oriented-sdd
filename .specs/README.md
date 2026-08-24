# .specs/

One directory per issue, named `<issue-number>-<kebab-title>` — the same string as the branch and
the spec, so an issue, a branch, a spec, and a PR are always one unit of work.

Each holds `spec.md` and, once a review has run, `.review-receipt`.

`Status:` moves `draft` → `approved` → `done` → `archived`, and one skill owns each edge, so the
status always says something true about who touched it last. A spec is not implementable until its
own PR has merged and the status reads `approved`.

The review gate reads this directory. A spec whose slug does not begin with an issue number blocks
the turn: work that never had an issue entered through the side door.

Shipped specs move to `_archive/`.
