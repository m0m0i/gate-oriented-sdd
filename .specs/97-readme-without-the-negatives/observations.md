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
