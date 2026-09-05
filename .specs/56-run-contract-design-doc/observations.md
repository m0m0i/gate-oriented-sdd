# Observations — contract and design-doc

Recorded as each task ran. `docs/verified.md` is written from this file in T5. A seam that did not join and a seam that was **not exercised** are both recorded; only successes would make this file useless.

## T1 — baseline

Captured by one script, re-run unchanged in T6. Everything below is its verbatim output. Two things it already corrects in the issue: the suite is at 54, not 52, and the dogfood reviewer has no lock, so the 6 pinned files are all under `agents/`.

- HEAD: 95626c9 on 56-run-contract-design-doc
- Claude Code 2.1.252, gate-sdd 0.4.2

### Validators (each command on the `- Validators:` line, last output line and exit code)

- `./scripts/check-leakage.sh` → exit 0 — `check-leakage: clean`
- `./scripts/check-manifests.py` → exit 0 — `check-manifests: both manifests agree`
- `./scripts/check-markdown-fences.py` → exit 0 — `check-markdown-fences: 10 ```markdown fence(s), no hand-wrapped prose`
- `./scripts/check-receipt-schema.py` → exit 0 — `check-receipt-schema: 7 field(s) agree across 3 copies`
- `./scripts/check-skill-contracts.py` → exit 0 — `check-skill-contracts: 9 skill contract(s) present`
- `./scripts/check-templates.py` → exit 0 — `check-templates: 10 task line(s) across 3 template(s), no split red steps`
- `./assets/check-steering-anchors.sh` → exit 0 — `check-steering-anchors: 5 of 5 anchor(s) resolved, none unreadable`
- `./assets/check-locks.py` → exit 0 — `check-locks: 6 pinned file(s) match their locks in .claude/agents, agents`
- `./scripts/test-gates.sh` → exit 0 — `test-gates: 54 passed, 0 failed`

### Anchors and locks

- `./assets/check-steering-anchors.sh`: check-steering-anchors: 5 of 5 anchor(s) resolved, none unreadable
- `./assets/check-locks.py`: check-locks: 6 pinned file(s) match their locks in .claude/agents, agents
- Dogfood lock present: no

### Checksums (sha256, first 12)

- `.steering/product.md` 7151a38e2ddb
- `.steering/tech.md` c36dd681de5d
- `.steering/structure.md` d1f46d77e302
- `CONTRIBUTING.md` 98c828d5351d
- `docs/NORTH_STAR.md` 4b9d822c9697
- `docs/PRD.md` 164bd25d5321
- `docs/EPICS.md` dab97c5c1bc6
- `docs/BACKLOG.md` dbf96d207391
- `.claude/agents/gate-sdd-reviewer.md` a5031b32a758
- `.claude/agents/_shared/reviewer-contract.md` 9b766d8747a9
- `.claude/agents/gate-sdd-reviewer/rules/claims-and-prose.md` b30421ddfd85
- `.claude/agents/gate-sdd-reviewer/rules/gates-and-guards.md` fab2a934cffa
- `agents/dart-flutter-reviewer/rules-lock.json` 7540f9cb7d16
- `agents/python-reviewer/rules-lock.json` 8901b1fd3bab
- `agents/ts-reviewer/rules-lock.json` 2d89dc559f41

### Anchor lines, verbatim

    - Owns: gates never fail open
    - Validators: ./scripts/check-leakage.sh, ./scripts/check-manifests.py, ./scripts/check-markdown-fences.py, ./scripts/check-receipt-schema.py, ./scripts/check-skill-contracts.py, ./scripts/check-templates.py, ./assets/check-steering-anchors.sh, ./assets/check-locks.py, ./scripts/test-gates.sh
    - Reviewer: gate-sdd-reviewer
    - Source globs: :(glob)skills/**/*.md :(glob)agents/**/*.md :(glob)hooks/**/*.sh :(glob)assets/**/*.py :(glob)assets/**/*.sh :(glob)assets/**/*.md :(glob)scripts/**/*.py :(glob)scripts/**/*.sh
    - Docs: docs/

### Rule ids and severities

Command: `grep -hE '^- \*\*[GC]-[0-9]+' .claude/agents/gate-sdd-reviewer/rules/*.md | sed -E 's/^- \*\*([GC]-[0-9]+).*(BLOCKER|HIGH|MEDIUM|LOW|INFO)[^A-Z]*$/\1 \2/'`

    C-1 HIGH
    C-2 MEDIUM
    C-3 MEDIUM
    C-4 HIGH
    C-5 HIGH
    C-6 HIGH
    C-7 BLOCKER
    G-1 BLOCKER
    G-2 BLOCKER
    G-3 BLOCKER
    G-4 HIGH
    G-5 HIGH
    G-6 HIGH
    G-7 MEDIUM
    G-8 HIGH
    G-9 HIGH

- Count: 16

### ADR state

- `ls docs/decisions/`: ls: docs/decisions/: No such file or directory
- `git branch -r | grep -c ADR-`: 0
- `git ls-tree -r --name-only origin/main | grep -c ADR-`: 0
- `grep -c ADR` in files the reviewer reads: gate-sdd-reviewer.md=0 reviewer-contract.md=0 rules=0

### structure.md headings and table rows

    # Structure — gate-oriented-sdd
    | Path | Holds | Shipped to consumers |
    | :-- | :-- | :-- |
    | `skills/<name>/SKILL.md` | one skill each, read by both harnesses | yes |
    | `agents/<name>.md` + `agents/<name>/rules/` | reviewers and their hash-pinned rulebooks | yes |
    | `agents/_shared/`, `agents/_template/` | the reviewer contract, and the starting point for an unrecognised stack | yes |
    | `hooks/*.sh` | the gates; `hooks/templates/` renders into projects | yes |
    | `assets/` | files copied into projects — issue templates, `check-locks.py` | yes |
    | `scripts/` | this repo's own guards, run by CI | no |
    | `docs/` | fidelity, layout, verified behaviour | no |
    | `evals/` | authored, unrun | no |
    ## Where the harness's own instance lives
