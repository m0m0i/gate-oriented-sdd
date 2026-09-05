# ADR-5: The version-bump check runs in CI on pull requests only, not at turn end
- Status: accepted
- Date: 2026-08-22 — recorded 2026-09-05; #6, reasoning in `.steering/tech.md`

## Context
A change to a shipped path that does not move the version reaches nobody (#3). Mid-implementation, shipped files are routinely edited before the version moves, so a check that fires on every turn would block ordinary work.

## Decision
`check-version-bump.py` runs in CI against the pull request base, and is not on the `- Validators:` line.

## Consequences
- No false blocks on ordinary turns, which is what keeps the gate switched on (CAP-7).
- Nothing local catches an unbumped change; the reviewer's C-6 is the earlier warning, and it is advisory.
- The READMEs are exempt, so the version they state drifts from the manifests (#48).
- Revisit if unbumped changes reach `main` through a path that is not a pull request.

## Alternatives considered
- **A turn-end validator** — blocks the normal mid-implementation state and teaches switching the gate off.
- **A `pre-push` hook** — outside both harnesses' hook models, and installed per clone rather than per project.
