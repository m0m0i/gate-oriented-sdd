# ADR-4: The spec is the first commit on the issue's branch, not a pull request of its own
- Status: accepted
- Date: 2026-08-25 — recorded 2026-09-05; #30

## Context
Until #30 a spec was reviewed and merged in its own pull request, then implemented in a second. A merge sat between agreeing and building, which is a real checkpoint, and it doubled the pull requests for every issue.

## Decision
One issue is one branch, one spec, one pull request. The spec is the first commit on that branch, so the diff reads spec first and then the code that satisfies it.

## Consequences
- Half the pull requests, and a reader sees what was agreed before any code existed.
- Nothing mechanical marks `approved`; it is a status a person writes, and a spec flipped without review looks identical to one that was reviewed.
- A contentious spec has to be pushed and discussed on the branch rather than merged first.
- Revisit if `approved` is found being set without the spec having been read.

## Alternatives considered
- **A spec pull request** — the prior practice; a checkpoint bought with a second review and merge per issue.
- **The spec in the issue body** — no diff to review and no status to flip; the tracker becomes the spec store.
