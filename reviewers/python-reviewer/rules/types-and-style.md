# Rulebook: types and style — `PY-*`

Scope: `**/*.py`. The formatter and linter enforce the mechanical subset. **Do not report what they catch.**

## PY-001 — Public surface is deliberate
**Severity: HIGH**

A name is public unless it is underscore-prefixed, and a module's public names are a contract. A helper made public only because a test imported it is a contract nobody meant to sign.

## PY-002 — Type hints on every public signature
**Severity: HIGH**

Parameters and returns of public functions, methods, and dataclasses are annotated. An unannotated public signature defeats the type checker for every caller, not just for itself.

## PY-003 — No bare `except`, and no `except Exception` without re-raise
**Severity: HIGH**

Catching everything catches `KeyboardInterrupt` and the bug you have not found yet. Catch the specific exception, or re-raise after handling.

## PY-004 — No mutable default arguments
**Severity: HIGH**

`def f(x=[])` shares one list across every call. Use `None` and construct inside.

## PY-005 — Names say what, not how
**Severity: LOW**

`user_dict` names the container; `users_by_id` names the meaning. Units belong in the name: `timeout_s`, not `timeout`.

## PY-006 — No import-time side effects
**Severity: HIGH**

Module-level work — opening connections, reading configuration, constructing clients — makes the module untestable and its import order significant. Initialize lazily.

## PY-007 — Prefer explicit over clever
**Severity: LOW**

A nested comprehension that needs a comment to be read should be a loop. Comprehensions are for clarity, not for proving it fits on one line.

## PY-008 — Dataclasses and enums over tuples and strings
**Severity: MEDIUM**

A tuple returned from a function is positional trivia at every call site. A string used as a mode flag is a typo waiting to be a runtime error.
