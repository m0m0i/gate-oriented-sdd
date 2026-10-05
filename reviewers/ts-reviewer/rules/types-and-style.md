# Rulebook: types and style — `TS-*`

Scope: `**/*.ts`, `**/*.tsx`. Load when the diff touches TypeScript sources.

The linter and the compiler already enforce the mechanical subset of this. **Do not report what they catch.** These rules are for what a formatter and a type checker cannot see: intent, contract shape, and names that are syntactically fine and semantically wrong.

## TS-001 — Every export is a deliberate contract
**Severity: HIGH**

A symbol exported only because a test needed it is a contract you did not mean to sign, and it will be imported by someone else within a month.

Check: for each newly exported symbol, is it named in the spec's Design, or re-exported from the package entry point? If neither, it is internal — tests can import from the module path.

## TS-002 — No `any`, and no `unknown` that never narrows
**Severity: HIGH**

`any` disables checking. `unknown` is correct only when the value is narrowed before use; `unknown` cast straight to a concrete type with `as` is `any` wearing a hat.

Check: every `as` on an `unknown` value. Demand a type guard or a schema parse.

## TS-003 — A non-null assertion needs a proven invariant
**Severity: HIGH**

`!` asserts the type system is wrong. It is acceptable only where the invariant is proven on the immediately preceding lines, or documented in a comment naming why it holds.

## TS-004 — Names carry unit and shape
**Severity: LOW**

`timeout` is ambiguous; `timeoutMs` is not. `users` is ambiguous when it is a `Map`; `usersById` is not. Booleans read as predicates: `isValid`, `hasExpired`, `shouldRetry`.

## TS-005 — No default exports in library code
**Severity: MEDIUM**

Named exports are greppable and refactorable; default exports rename themselves at every import site. Entry-point scripts are the exception.

## TS-006 — `readonly` on inputs that are not mutated
**Severity: LOW**

A parameter the function does not mutate takes `readonly T[]` or `Readonly<T>`. That is a documented contract, not decoration.

## TS-007 — No barrel that re-exports everything
**Severity: MEDIUM**

An index re-exporting `*` from every module makes the public surface unreviewable and defeats `TS-001`.

## TS-008 — Discriminated unions over optional-field soup
**Severity: MEDIUM**

A type where three fields are optional and only certain combinations are legal is a union that has not been written yet. The compiler can enforce a union; it cannot enforce a comment.
