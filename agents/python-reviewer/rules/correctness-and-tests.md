# Rulebook: correctness and tests — `COR-*`, `TST-*`

Scope: all Python in the diff, plus tests it adds or changes.

Severities assume the project's quality anchor from `.steering/product.md`. Say which anchor you applied when it decides a severity.

## COR-001 — Errors are handled at the boundary, not swallowed
**Severity: BLOCKER**

An `except` that logs and continues, or returns a default, turns a failure into a silent wrong answer. It must re-raise, return an explicit error the caller must handle, or carry a comment naming the recovered condition **and** a test exercising it.

## COR-002 — External input is parsed, not assumed
**Severity: BLOCKER**

Anything crossing a process boundary — files, HTTP responses, environment variables, CLI arguments, model output — is validated where it enters. A `dict` from `json.loads` is not the shape your annotation claims.

## COR-003 — Resources are closed on every path
**Severity: HIGH**

Files, sockets, subprocesses, and locks use a context manager or `finally`. "It gets collected eventually" is not a release strategy under load.

## COR-004 — No silent numeric or encoding coercion
**Severity: HIGH**

`int(x)` on unvalidated input raises; `float(x)` can produce `nan`, which compares false against everything. Text decoded without an explicit encoding is a latent platform bug.

## COR-005 — Concurrency has an ownership story
**Severity: HIGH**

Shared mutable state across threads, tasks, or processes needs a lock, a queue, or immutability — named explicitly. Blocking calls inside async functions stall the event loop and are a defect even when tests pass.

## COR-006 — No unbounded work
**Severity: MEDIUM**

Unpaginated queries, unbounded retries, and unbounded caches are fine in development and fail in production. A limit, a timeout, or a documented reason.

---

## TST-001 — Test order matches the spec's task order
**Severity: HIGH**

A task whose commit shows implementation with no preceding failing test is a process violation, visible in `git log --oneline <base>...HEAD`. Report the task numbers.

## TST-002 — Every acceptance criterion maps to a test
**Severity: HIGH**

Report uncovered criteria **by id** in the Spec conformance block.

## TST-003 — Error paths are tested
**Severity: HIGH**

Every branch `COR-001` through `COR-005` protects has a test reaching it. An untested `except` is an untested claim.

## TST-004 — Tests are deterministic and offline
**Severity: HIGH**

No real clock, no real network, no unseeded randomness, no dependence on filesystem or dict ordering. Mock at the boundary, not three layers in.

## TST-005 — Assertions are specific
**Severity: MEDIUM**

`assert result` passes for `True`, `1`, `"error"`, and a non-empty list of failures. Assert the value you mean.
