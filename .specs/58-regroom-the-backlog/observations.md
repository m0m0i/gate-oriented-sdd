# Observations — backlog

Recorded as each task ran; `docs/verified.md` rows are written from this file in T4. Seams that did not join and seams not exercised are both recorded.

## T1 — baseline

Captured by `baseline.sh`, re-run unchanged in T5. Verbatim:

- HEAD: 3fa1bab on 58-regroom-the-backlog
- Claude Code 2.1.252, gate-sdd 0.4.2

### Validators

- `./scripts/check-leakage.sh` → exit 0 — `check-leakage: clean`
- `./scripts/check-manifests.py` → exit 0 — `check-manifests: both manifests agree`
- `./scripts/check-markdown-fences.py` → exit 0 — `check-markdown-fences: 10 ```markdown fence(s), no hand-wrapped prose`
- `./scripts/check-receipt-schema.py` → exit 0 — `check-receipt-schema: 7 field(s) agree across 3 copies`
- `./scripts/check-skill-contracts.py` → exit 0 — `check-skill-contracts: 9 skill contract(s) present`
- `./scripts/check-templates.py` → exit 0 — `check-templates: 10 task line(s) across 3 template(s), no split red steps`
- `./assets/check-steering-anchors.sh` → exit 0 — `check-steering-anchors: 5 of 5 anchor(s) resolved, none unreadable`
- `./assets/check-locks.py` → exit 0 — `check-locks: 6 pinned file(s) match their locks in .claude/agents, agents`
- `./scripts/test-gates.sh` → exit 0 — `test-gates: 54 passed, 0 failed`

### Open issues (`gh issue list --state open`)

- count: 20
- numbers: 14 18 19 22 23 25 26 35 36 39 47 48 54 57 58 68 69 70 71 72 

### BACKLOG.md table

- rows: 12
    1 #26
    2 #28
    3 #39
    4 #36
    5 #35
    6 #25
    7 #19
    8 #14
    9 #18
    10 #23
    11 #10
    12 #22
- closed but tabled: #10 #28 
- open but untabled: #47 #48 #54 #57 #58 #68 #69 #70 #71 #72 
- Epic column present: no

### Checksums (sha256, first 12)

- `docs/EPICS.md` dab97c5c1bc6
- `docs/PRD.md` 164bd25d5321
- `docs/NORTH_STAR.md` 4b9d822c9697
- `.steering/product.md` 7151a38e2ddb
- `.steering/tech.md` 60fe179aa311
- `.steering/structure.md` d3d25014a85e
- `docs/verified.md` 3ac9e03dbac5
- `docs/BACKLOG.md` dbf96d207391

### 'nothing cites' statements

    docs/EPICS.md:4:- Status: draft — nothing cites these ids; see `docs/verified.md`.
    docs/verified.md:114:| Do `PRD.md` and `EPICS.md` have a mechanical consumer here? | **no.** Nothing cites a capability or epic id, and no c
    docs/verified.md:149:| Did either skill create a second id vocabulary? | **one did.** `contract`'s table forced `M-`/`N-` ids on Mechanical 
    docs/verified.md:155:The row above reading *"Nothing cites a capability or epic id"* is half false after this run: `DESIGN.md` cites the cap
    .steering/product.md:27:`LV-*` are the levers in `docs/NORTH_STAR.md`. **Nothing cites these ids yet** — no spec is required to name a capab
    docs/PRD.md:6:Nothing cites the capability ids below yet. That is recorded deliberately rather than left to be discovered — see `docs/verifi
