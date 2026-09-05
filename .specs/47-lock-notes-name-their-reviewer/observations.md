# Observations — #47

## T1 — red

- python-reviewer        "note": "Grounding for ts-reviewer
- ts-reviewer            "note": "Grounding for ts-reviewer
- dart-flutter-reviewer  "note": "Grounding for ts-reviewer

- `agents/dart-flutter-reviewer/rules-lock.json` 7540f9cb7d16
- `agents/python-reviewer/rules-lock.json` 8901b1fd3bab
- `agents/ts-reviewer/rules-lock.json` 2d89dc559f41
- `plugin.json` 230cae789714
- `.claude-plugin/plugin.json` 0ea309ec4b13

## T2 — after

- python-reviewer        "note": "Grounding for python-reviewer
- ts-reviewer            "note": "Grounding for ts-reviewer
- dart-flutter-reviewer  "note": "Grounding for dart-flutter-reviewer
- manifests: "version": "0.4.3" "version": "0.4.3" 
- diff paths: .claude-plugin/plugin.json .specs/47-lock-notes-name-their-reviewer/observations.md .specs/47-lock-notes-name-their-reviewer/spec.md agents/dart-flutter-reviewer/rules-lock.json agents/python-reviewer/rules-lock.json plugin.json 

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
- `check-version-bump.py <main>` → exit 0 — `check-version-bump: no shipped file changed`
- `claude plugin validate . --strict` → exit 0 — `✔ Validation passed`

**Correction.** The `check-version-bump.py` line above ran before the T2 commit existed, so it compared `main` to the same tree and reported no shipped file changed. At the commit: exit 0 — `check-version-bump: 4 shipped file(s) changed, version 0.4.2 -> 0.4.3`.
