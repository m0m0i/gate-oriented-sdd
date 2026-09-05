# ADR-1: The repository root is the plugin
- Status: accepted
- Date: 2026-08-21 — recorded 2026-09-05

## Context
One clone has to be installable as a Claude Code plugin, a Claude Code marketplace, and an Antigravity plugin. The three formats put their manifests at different paths and share the `skills/` and `agents/` layout, so they can coexist in one directory or be nested one level down.

## Decision
The repository root is the plugin. Nothing is nested; the marketplace entry points at `./`, and `agy plugin install` takes the clone itself.

## Consequences
- One directory, two install paths, no sync step; drift between the two targets is impossible because there is one copy.
- The repository can never host a second plugin, and every top-level file is shipped-adjacent, which is why `check-leakage.sh` exists and runs first.
- Two manifests state the same name and version and must agree; `check-manifests.py` is the cost of not nesting.
- Revisit if a second plugin or a monorepo is ever needed.

## Alternatives considered
- **`plugins/<name>/` nesting** — the marketplace-native layout. Rejected because `agy plugin install` would then take a subdirectory and the clone stops being the installable unit.
