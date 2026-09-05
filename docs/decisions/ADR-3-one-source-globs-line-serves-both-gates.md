# ADR-3: One `Source globs` line serves both gates, and it excludes the manifests
- Status: accepted
- Date: 2026-08-22 — recorded 2026-09-05; #4, refined in 0.2.4, cost recorded on #14

## Context
The review gate asks which paths re-stale a receipt. The quality gate asks which paths should trigger the validators. Those have different right answers for the manifests: a version bump lands after the review and must not re-stale it, but a manifest edit is exactly what `check-manifests.py` exists to check.

## Decision
One `- Source globs:` line in `.steering/tech.md` answers both, and the manifests are not on it.

## Consequences
- One place to edit, one anchor to guard, and no receipt is re-staled by the version bump that follows every review.
- A commit touching only a manifest runs no validators locally; CI is the backstop, and that is a duplication accepted on purpose.
- The line restates by hand the definition `check-version-bump.py` holds in `SHIPPED`, and nothing detects them disagreeing (#14).
- Revisit when a third path gives the two questions different answers, or when #14's duplication produces a wrong result.

## Alternatives considered
- **Two lines, one per gate** — the honest interface, at the cost of a second anchor that drifts from the first.
- **Deriving the globs from `check-version-bump.py`** — makes a shipped hook depend on a repository script that consumers do not receive (C-5).
