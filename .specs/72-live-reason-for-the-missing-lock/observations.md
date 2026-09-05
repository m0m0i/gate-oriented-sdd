# Observations — #72

## T1 — the greps, red

- `That is #16`: .claude/agents/gate-sdd-reviewer.md:1 AGENTS.md:1 
- `hooks/hooks.json` in AGENTS.md: 1
- `ADR-6` mentioned in either: AGENTS.md:0 .claude/agents/gate-sdd-reviewer.md:0 

## T2 — after

- `That is #16`: AGENTS.md:0 .claude/agents/gate-sdd-reviewer.md:0 
- `hooks/hooks.json` in AGENTS.md: 0
- `ADR-6` in either: AGENTS.md:1 .claude/agents/gate-sdd-reviewer.md:1 
- #19 named in both: AGENTS.md:1 .claude/agents/gate-sdd-reviewer.md:1 
- diff paths: .claude/agents/gate-sdd-reviewer.md .specs/72-live-reason-for-the-missing-lock/observations.md .specs/72-live-reason-for-the-missing-lock/spec.md AGENTS.md 

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
- `check-version-bump.py <main>` → check-version-bump: no shipped file changed
