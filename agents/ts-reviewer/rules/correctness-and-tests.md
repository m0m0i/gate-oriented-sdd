# Rulebook: correctness, async, and tests — `COR-*`, `TST-*`

Scope: all TypeScript in the diff, plus any test it adds or changes. Load whenever the diff contains logic, not only when it contains tests.

Severities here assume the project's quality anchor from `.steering/product.md`. Where that anchor is correctness or trust, `COR-001` and `COR-005` are Blockers; where it is responsiveness, `COR-004` rises. Say which anchor you applied when it decides a severity.

## COR-001 — Errors are handled at the boundary, not swallowed
**Severity: BLOCKER**

A `catch` that logs and continues, or returns a default, converts a failure into a silent wrong answer — the most expensive defect class there is, because nothing reports it.

Check: every `catch`. It must rethrow, return an explicit error value the caller has to handle, or carry a comment naming the recovered condition **and** a test exercising it.

## COR-002 — `catch (e)` narrows before use
**Severity: HIGH**

`e` is `unknown`. Reading `e.message` without narrowing is `COR-001` plus `TS-002`.

## COR-003 — Every promise is awaited or explicitly detached
**Severity: BLOCKER**

A floating promise loses both its result and its rejection. Deliberate fire-and-forget carries `void` and a comment naming why.

## COR-004 — No `await` in a loop over independent work
**Severity: MEDIUM**

Sequential awaits over independent items is a latency bug. Use `Promise.all` or `Promise.allSettled`, and say which and why — `allSettled` when partial success is meaningful, `all` when it is not.

## COR-005 — External input is parsed, not asserted
**Severity: BLOCKER**

Anything crossing a process boundary — file contents, HTTP responses, environment variables, CLI arguments, model output — is validated where it enters. `JSON.parse(...) as Config` is a lie the type system believes for the rest of the program.

## COR-006 — Exhaustive switches assert `never`
**Severity: HIGH**

A `switch` over a union gets a `default` assigning the scrutinee to `never`, so adding a member becomes a compile error rather than a runtime fallthrough.

## COR-007 — No silent numeric coercion
**Severity: HIGH**

`Number(x)` on unvalidated input yields `NaN`, which compares false against everything and propagates silently. Check the result or use a parser.

## COR-008 — Resources are released on every path
**Severity: HIGH**

File handles, timers, watchers, connections, and browser contexts opened in a `try` are released in `finally` or a disposal scope — including when the body throws.

---

## TST-001 — Test order matches the spec's task order
**Severity: HIGH**

`implement` walks tasks Red → Green → Refactor. A task whose commit contains implementation with no preceding failing test is a process violation, and it is visible in the log.

Check: `git log --oneline <base>...HEAD` against the Tasks list. Report task numbers showing Green without Red.

## TST-002 — Every acceptance criterion maps to a test
**Severity: HIGH**

For each numbered `AC` in the spec's Requirements, there is a test whose name or assertion demonstrably covers it. Report uncovered criteria **by id** — this is what the Spec conformance block is for.

## TST-003 — Error paths are tested, not only happy paths
**Severity: HIGH**

Every branch `COR-001` through `COR-008` protects has a test reaching it. An untested `catch` is an untested claim.

## TST-004 — Tests assert behaviour, not implementation
**Severity: MEDIUM**

A test asserting a private call count breaks on refactor and blocks the Refactor phase by design.

## TST-005 — No conditional logic in tests
**Severity: MEDIUM**

An `if` in a test means the test does not know what it is asserting. Split it.

## TST-006 — Fixtures are deterministic
**Severity: HIGH**

No real clock, no real network, no unseeded randomness, no dependence on filesystem ordering. A flaky test is indistinguishable from a real defect, and it trains people to re-run instead of investigate.
