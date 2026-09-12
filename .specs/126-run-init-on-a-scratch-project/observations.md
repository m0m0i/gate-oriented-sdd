# Observations — 126-run-init-on-a-scratch-project

Plugin **0.7.0**, `skills/` identical to the installed copy. Run 2026-09-12T09:26:53Z.

## T1 — baseline of THIS repository, captured before anything ran

The invariant is that this repository is unchanged. "Nothing broke" is an assertion unless
the before-state exists, so it is recorded here first.

```
./scripts/check-leakage.sh         check-leakage: clean
./scripts/check-manifests.py       check-manifests: both manifests agree
./scripts/check-markdown-fences.py check-markdown-fences: 10 ```markdown fence(s), no hand-wrapped prose
./scripts/check-receipt-schema.py  check-receipt-schema: 7 field(s) agree across 3 copies, and 5 reviewer(s) can produce the 2 needing a command
./scripts/check-skill-contracts.py check-skill-contracts: 16 skill contract(s) present
./scripts/check-templates.py       check-templates: 10 task line(s) across 3 template(s), no split red steps; 5 live spec(s), no task sequenced after the review
./assets/check-steering-anchors.sh check-steering-anchors: 6 of 6 anchor(s) resolved, none unreadable
./assets/check-locks.py            check-locks: 6 pinned file(s) match their locks in .claude/agents, agents
./assets/check-document-set.py     check-document-set: mode `full` at `docs/` — 6 document(s), 3 issue template(s) and 2 directory(ies) present
./scripts/check-contract-path.py   check-contract-path: 10 source(s) agree on `_shared/reviewer-contract.md`
./scripts/test-gates.sh            test-gates: 76 passed, 0 failed
```

## T1 — the scratch project, built before `init` saw it

A git repository in a temp directory, TypeScript, deleted in T4. Eight files:

| Path | Why it is there |
| :-- | :-- |
| `package.json` | three scripts — `lint`, `typecheck`, `test` — so step 1 has real commands to run |
| `tools/lint.mjs`, `tools/typecheck.mjs` | stand-ins for eslint/tsc that genuinely exit non-zero on a violation |
| `src/ledger.ts`, `tests/*.test.mjs` | a `src/` layout with a passing test |
| `.github/ISSUE_TEMPLATE/bug_report.md` | **an existing template with its own labels** — `init` must merge, not replace |
| `CONTRIBUTING.md` | **an existing commit convention** — `type(scope): subject`, and a branch convention that is *not* the harness's `<issue>-<kebab-title>` |
| `.gitignore` | ordinary |

**The validators discriminate**, verified before the run rather than assumed — a candidate that cannot fail tells step 1 nothing:

```
clean tree:        lint: clean | typecheck: no errors | tests pass
with a violation:  lint exit=1 (var, >100 cols) | typecheck exit=1 (explicit any)
```

**One fixture defect, mine, fixed before `init` ran:** `node --test tests/` threw `MODULE_NOT_FOUND` on Node 24 — it wants a glob, not a directory. Recorded because the project had to be green before step 4 could arm a gate on it, and because a broken fixture is the failure this repository keeps meeting; here it was loud rather than silent, which is the good direction.

**The two deliberate collisions** are the issue template and the commit convention. `init` claims to merge into both. Nothing else in this project was chosen to be awkward — which is the CAP-4 weakness this spec already names: its opinions are mine.
