# Tech — gate-oriented-sdd

Shell (POSIX `sh`), Python 3 (stdlib only, no dependency file anywhere), and Markdown. There is no
package manager and no build. The repository root *is* the installable plugin.

Machine-read lines. Each must stay on ONE physical line — the gates read them with
`sed ... | head -1`, so a wrapped value is truncated at the first newline without complaint.

- Validators: ./scripts/check-leakage.sh, ./scripts/check-manifests.py, ./scripts/check-receipt-schema.py, ./scripts/check-skill-contracts.py, ./assets/check-steering-anchors.sh, ./assets/check-locks.py, ./scripts/test-gates.sh
- Reviewer: gate-sdd-reviewer
- Source globs: :(glob)skills/**/*.md :(glob)agents/**/*.md :(glob)hooks/**/*.sh :(glob)assets/**/*.py :(glob)assets/**/*.sh :(glob)assets/**/*.md :(glob)scripts/**/*.py :(glob)scripts/**/*.sh
- Docs: docs/

## Why `check-version-bump.py` is not on the Validators line

`./scripts/check-version-bump.py` is CI-only, on pull requests. It is deliberately **not** a
turn-end validator: mid-implementation a shipped file is routinely edited before the version moves,
so running it on every turn would block normal work and teach the user to switch the gate off. CI
runs it once, against the PR base, which is the moment the question is actually meaningful.

## Why `Source globs` excludes the manifests, and what that costs

Since 0.2.4 this one line answers **two different questions**: the review gate asks "what re-stales
a receipt?" and the quality gate asks "what should trigger the validators?". Those have different
right answers for the manifests, and the line can only give one.

A version bump lands *after* the review, in the same family as the work-log entry and the
`Status: done` flip, so including `plugin.json` here would re-stale a receipt on every single spec
and force a second review of a one-character change. Excluded, therefore.

**The cost is explicit:** a commit touching only a manifest does not run the validators locally, so
`check-manifests.py` will not catch a version disagreement on that turn. CI runs it on every pull
request, which is the backstop. This is a reasoned trade — local speed against a check that is
duplicated in CI — not an oversight, and it is recorded on #14.

Also on #14: this line duplicates by hand the definition `scripts/check-version-bump.py` holds in
its `SHIPPED` tuple, and nothing detects them disagreeing.

`:(glob)` is load-bearing. The value is interpolated unquoted, so a bare `*.py` would be expanded
by the shell against the repository root before git ever saw it. `:(glob)` matches no file on disk,
so the shell leaves the word alone. This is #1, and it failed silently for three releases.

## Commit and branch convention

Conventional commits — `feat:`, `fix:`, `docs:`, `chore:` — subject in the imperative, body
explaining why over what. Branches are `<issue-number>-<kebab-title>`, which is also the spec
directory name; the review gate blocks a spec branch whose slug has no issue number.

## Gates

Both hooks run from the repository's own `hooks/` directory rather than from a copy under
`.claude/`. This repo is the source of those scripts, and a second copy would drift — which would
mean the repo tests a stale version of its own enforcement. It is the one project where pointing at
the source is correct; every other install copies.
