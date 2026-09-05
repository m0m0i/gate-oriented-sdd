# ADR-6: This repository's own instance runs the hooks from source and leaves its reviewer unpinned
- Status: accepted
- Date: 2026-08-24 — recorded 2026-09-05; #17

## Context
Running the harness on the repository that ships it is the only way to find the integration defects it exists to find. An ordinary install copies `hooks/*.sh` into `.claude/hooks/` and pins its reviewer's rulebook; here a copy would test a stale version of the enforcement, and at the time a lock under `.claude/agents/` would have made `check-locks.py` discover that directory instead of `agents/` and verify nothing (#16).

## Decision
`.claude/settings.json` points at the repository's own `hooks/*.sh`, and `.claude/agents/gate-sdd-reviewer/` has no `rules-lock.json`.

## Consequences
- The repository tests its live enforcement, and every dogfood session is a run against the shipped scripts.
- Both deviations look like mistakes, so each needs a paragraph explaining itself in `AGENTS.md`, `.steering/`, and the reviewer file, and those paragraphs go stale: #16 is closed and `check-locks.py` now discovers both directories, so the live reason the lock is absent is #19, which cannot create one.
- The dogfood reviewer cites rules that were never pinned, which is what the lock exists to prevent.
- Revisit when #19 ships a bootstrap: pin the rulebook and delete the paragraphs.

## Alternatives considered
- **Copy the hooks like every other install** — drift between the copy and the source, and the repository tests the wrong thing.
- **Write the lock by hand** — defeats the guard's one safety property, that `--update` only rewrites hashes a human already chose to trust.
