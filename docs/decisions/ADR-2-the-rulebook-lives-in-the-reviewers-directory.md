# ADR-2: The rulebook lives in the reviewer's directory, hash-pinned, and never in session context
- Status: accepted
- Date: 2026-08-21 — recorded 2026-09-05

## Context
Review rules written into `CLAUDE.md` or `AGENTS.md` are read by every session, cost context on every turn, and can be argued out of by the model reading them. A rule that is cited in a finding needs an id and a text that cannot drift unnoticed.

## Decision
Rules live in `agents/<name>/rules/*.md`, loaded on demand by the reviewer and by nothing else, and are pinned by `agents/<name>/rules-lock.json`, which `check-locks.py` verifies and fails closed on.

## Consequences
- Findings cite ids; a normal session never sees the rules; an edited rule is detected.
- A reviewer with no lock cannot get one from `--update` (#19), so a new reviewer starts unpinned, and this repository's own reviewer still is (ADR-6).
- The rule files must carry no frontmatter or they register as phantom agents (C-7), which every tool that validates plugins warns about.
- Revisit if either harness gains rule loading of its own, or if on-demand loading proves unreliable in practice.

## Alternatives considered
- **Rules in `CLAUDE.md` / `AGENTS.md`** — read every session, unpinned, and the reason this repository exists is that they were skipped.
- **Rules in the reviewer agent's body** — loaded whole on every review and unpinned; the same drift with more context spent.
