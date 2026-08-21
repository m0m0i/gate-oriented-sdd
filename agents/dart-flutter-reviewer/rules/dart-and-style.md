# Rulebook: Dart and style — `DART-*`

Scope: `**/*.dart`. The formatter and analyzer enforce the mechanical subset. **Do not report what they catch** — cite the analyzer's own diagnostic name when reporting something it found.

## DART-001 — Sound null safety, no gratuitous `!`
**Severity: HIGH**

`!` asserts the analyzer is wrong. Acceptable only where the invariant is proven immediately above, or documented. `late` without a guaranteed initialization path is the same defect with a different spelling.

## DART-002 — `const` wherever the constructor allows it
**Severity: MEDIUM**

A non-`const` widget that could be `const` rebuilds its subtree for nothing. In a list or an animation that is a visible performance defect, not a style preference.

## DART-003 — Immutable models with value equality
**Severity: HIGH**

Domain models are immutable and implement equality, or comparisons silently compare identity — which is why a rebuilt list "changes" when nothing did.

## DART-004 — Names carry unit and shape
**Severity: LOW**

`duration` is ambiguous; `timeoutMs` or a `Duration` is not. Booleans read as predicates.

## DART-005 — No business logic in widgets
**Severity: HIGH**

A widget builds UI. Data fetching, persistence, and decision logic belong behind the project's declared layering. A `build` method that awaits IO is a defect regardless of framework.

## DART-006 — Pattern matching and exhaustive switches
**Severity: MEDIUM**

A `switch` over a sealed type without a `default` becomes a compile error when a case is added. A chain of `if (x is A)` does not.

## DART-007 — Logging through the SDK's logger, not `print`
**Severity: LOW**

`print` bypasses log levels and developer tooling, and ships to production output.
