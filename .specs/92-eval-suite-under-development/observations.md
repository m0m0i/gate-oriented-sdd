# Observations — #92

## T1 — red, taken from `main`

    README.md:152:**v0.4.3 — pre-release.** A reference implementation with a tested-against version matrix, not a supported
    README.ja.md:153:**v0.4.3、pre-release です。** 検証済みバージョンの一覧を添えた reference implementation であって、サポート付きのプロダクトではありません。[eval スイート](
    docs/layout.md:98:├── evals/                         ← authored, not yet run
    .steering/structure.md:15:| `evals/` | authored, unrun | no |
    evals/README.md:14:## Status: authored, not yet run
    AGENTS.md:62:- `evals/` is authored but unrun — `claude plugin eval` is early access. Do not wire it into CI as a passin

- "under development" / 開発中 on main: 0 0 0 0 0 0

## T2 — after

- old phrasings, one per file: 0 0 1 1 1 0
- under development / 開発中, one per file: 2 2 1 1 2 1
- the run fact, kept:
    .steering/structure.md:15:| `evals/` | under development — authored, unrun | no |
    README.md:152:**v0.4.3 — pre-release.** A reference implementation with a tested-against version matrix, not a
    README.ja.md:153:**v0.4.3、pre-release です。** 検証済みバージョンの一覧を添えた reference implementation であって、サポート付きのプロダクトではありません
    docs/layout.md:98:├── evals/                         ← under development: authored, not yet run
    evals/README.md:14:## Status: under development — authored, not yet run
    AGENTS.md:62:- `evals/` is under development — authored but unrun, because `claude plugin eval` is early acces
- diff paths: .specs/92-eval-suite-under-development/observations.md .specs/92-eval-suite-under-development/spec.md .steering/structure.md AGENTS.md README.ja.md README.md docs/layout.md evals/README.md 
- anchors: check-steering-anchors: 5 of 5 anchor(s) resolved, none unreadable

### Validators, after the last write, stopping on failure

- `./scripts/check-leakage.sh` → exit 0 — `check-leakage: clean`
- `./scripts/check-manifests.py` → exit 0 — `check-manifests: both manifests agree`
- `./scripts/check-markdown-fences.py` → exit 0 — `check-markdown-fences: 10 ```markdown fence(s), no hand-wrapped prose`
- `./scripts/check-receipt-schema.py` → exit 0 — `check-receipt-schema: 7 field(s) agree across 3 copies`
- `./scripts/check-skill-contracts.py` → exit 0 — `check-skill-contracts: 9 skill contract(s) present`
- `./scripts/check-templates.py` → exit 0 — `check-templates: 10 task line(s) across 3 template(s), no split red steps`
- `./assets/check-steering-anchors.sh` → exit 0 — `check-steering-anchors: 5 of 5 anchor(s) resolved, none unreadable`
- `./assets/check-locks.py` → exit 0 — `check-locks: 6 pinned file(s) match their locks in .claude/agents, agents`
- `./scripts/test-gates.sh` → exit 0 — `test-gates: 54 passed, 0 failed`

### Refactor under green

AC1's grep still matched the three lines that kept "not yet run" or "unrun" after the new phrase, while AC2 keeps the fact. The fact is now carried as "no case has run" in `layout.md`, `structure.md`, `evals/README.md` and `AGENTS.md`, so AC1's grep returns nothing and every file still says it. Old phrasings per file after this: 0 0 0 0 0 0.
