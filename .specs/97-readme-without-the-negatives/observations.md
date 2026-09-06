# Observations — #97

## T1 — red

- README.md negatives: 3
- README.ja.md negatives: 3
- "What is verified" paragraph checksums: en 3f400370f08f, ja 713762c5828a

## T2 — after

- negatives: en 0, ja 0
- "What is verified" checksums unchanged: en 3f400370f08f, ja 713762c5828a
- pointer to verified.md present in both; matrix dates 2026-09-05 and 2026-08-21 kept in both
- diff paths: .specs/97-readme-without-the-negatives/observations.md .specs/97-readme-without-the-negatives/spec.md README.ja.md README.md 

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

## Consequences to existing documents

- `docs/NORTH_STAR.md:37`, the worked example under the non-negotiable, said the README's status line repeats `evals/README.md`'s run fact. After this branch it does not; the clause now says what the status line says — under development, early access. AC3 was widened in its own commit to allow the one clause. Nothing else describes the README's status line: `docs/verified.md`, `evals/README.md`, `AGENTS.md` and `.steering/structure.md` describe `evals/` itself and keep their run facts.

**AC2, C-3.** Read pair by pair after the fix: the version sentence, the eval sentence, the matrix line, the pointer — each carries the same claims, dates and references in both languages.

**Review triage.** MEDIUM — no consequences section and one sentence made false: the section above, and the clause fixed under the amended AC3. LOW — the pointer named "Still to verify" while two of the removed items live elsewhere in `verified.md`: softened to the file and the issues, both languages. INFO: none.
