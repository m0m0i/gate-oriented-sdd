# Observations — #95

## T1 — red

- README.md "none has run yet": 1
- README.ja.md 「まだ一度も走っていません」: 1

## T2 — after

- README.md "none has run yet": 0; "exits without running a case": 1
- README.ja.md 「まだ一度も走っていません」: 0; 「ケースは1つも実行されません」: 1
- numstat: 1 1 README.ja.md;1 1 README.md;
- diff paths: .specs/95-drop-redundant-clause/observations.md .specs/95-drop-redundant-clause/spec.md README.ja.md README.md 

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
