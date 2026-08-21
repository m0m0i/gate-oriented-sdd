# Rulebook: correctness and tests — `COR-*`, `TST-*`

Scope: all Dart in the diff, plus tests it adds or changes.

Severities assume the project's quality anchor from `.steering/product.md`. Say which anchor you applied when it decides a severity.

## COR-001 — Errors surface, they do not vanish
**Severity: BLOCKER**

A `catch` that logs and continues turns a failure into a silent wrong screen. It must rethrow, surface to the user, or carry a comment naming the recovered condition **and** a test exercising it.

## COR-002 — Every future is awaited or explicitly detached
**Severity: BLOCKER**

A dropped future loses its result and its error. `unawaited(...)` plus a comment is the deliberate form.

## COR-003 — Disposal is complete
**Severity: HIGH**

Controllers, streams, subscriptions, timers, and focus nodes created in a state object are disposed. A leaked subscription fires against a dead widget and throws where the user cannot see it.

## COR-004 — No state mutation after dispose
**Severity: HIGH**

Async work completing after teardown must check mounted state before touching anything. This is the most common crash in an otherwise passing app.

## COR-005 — External input is parsed, not asserted
**Severity: BLOCKER**

JSON from a network call is `dynamic`. Deserialization is total and null-tolerant, and field names match the contract the other side actually sends.

## COR-006 — Layout has bounded constraints
**Severity: MEDIUM**

Unbounded height inside a scrollable, or an unconstrained flex child, throws at runtime on a screen size nobody tested. Read the constraints, not just the widget tree.

---

## TST-001 — Test order matches the spec's task order
**Severity: HIGH**

Report task numbers whose commits show implementation with no preceding failing test.

## TST-002 — Every acceptance criterion maps to a test
**Severity: HIGH**

Report uncovered criteria **by id** in the Spec conformance block.

## TST-003 — Error and empty states are tested
**Severity: HIGH**

Loading, empty, and error states are the ones users hit and tests skip.

## TST-004 — Widget tests are hermetic
**Severity: HIGH**

No real network, no real clock, no real platform channels. Fakes over mocks; mocks only where a fake is genuinely impractical.

## TST-005 — Tests assert what the user observes
**Severity: MEDIUM**

Asserting a private method was called breaks on refactor and blocks the Refactor phase by design.
