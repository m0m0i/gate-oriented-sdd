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

## T2 — `backlog`

Run through the Skill tool. **One pause, the whole order, accepted as drafted with zero changes.** Three calls were put to the author explicitly — row 1 above #26, five pairs as single rows, the two rows without an issue — and all three came back as recommended. As in #55: that cannot be told apart from the drafts being right, and this run does not claim otherwise.

**AC1 verified.** 19 bold issue ids in the table, no duplicates, equal to `gh issue list --state open` minus #58. Rows without an issue: 1 (the `sprint` and `init` runs) and 13 (re-run `epics`); those are what `sprint` takes from. The parser reads bold `**#n**` only — two Item cells cite #55 and #56 in prose as sources, and a bare-`#n` parser counted them as items. On `main`'s file the bold-only parser yields T1's twelve rows.

**AC2 verified.** `#` runs 1…14; no empty `Why here`.

**AC3 verified.** No priority or tier heading or column; one table.

**AC4 verified, with a note.** `Epic` column present; cells are `EPIC-1`…`EPIC-4`, each a heading in `EPICS.md`, or `—`. The seven issues filed after `epics` ran: #57, #58, #68, #69, #70, #71, #72. Five sit in `—` rows. **#69 sits in row 5 under `EPIC-2` beside #19, and #72 in row 2 under `EPIC-4` beside #48 and #47** — grouped by the work they belong to rather than by the epic that lists them, because the alternative was a row per issue, which the skill red-flags. Recorded so the `epics` re-run (row 13) knows where they went.

**AC5 verified.** The preamble names every inception document, that `epics` has run, and the inversion — still true of twelve of fourteen rows.

**AC7 — what step 1 did with no walking skeleton.** *"Start from the walking skeleton — it is always first."* `EPICS.md` says none is one and hands ordering to this file, naming EPIC-1 to lead. The grooming put the test-queue runs first instead, by the author's decision, and EPIC-1's row says it was displaced. So the rule bound nothing, and the skill has no instruction for what leads when nothing is a skeleton — the same greenfield assumption #55 recorded in `epics`. **"Next up" and "Not ready":** the rules say *"Every 'Next up' row states why now"* and the red flags say *"Nothing is in 'Not ready'"*; the template defines neither section. This file has neither; the nearest are a per-row `Why here` and the Unshaped queue. A consumer following the template cannot trip either red flag.

### Seams that did not join

- **The template's `Blocks` column uses `#3, #7` for row references.** In a repository whose items are issues that reads as issue numbers. Written as `row 2`, `rows 5, 7` instead.
- **Step 6 hands to `sprint`, and row 1 is the `sprint` run.** The backlog's first item is the act of consuming the backlog. Not wrong, but a sign the test queue and the product plan are the same list here.
- **"A backlog item is not an issue"** is true of two rows. The other twelve are issues or pairs of issues, which the red flags call decomposed too early. The preamble says so; the grooming did not undo it, because the issues exist and un-filing them is not `backlog`'s to do.
- **`Rough size` for a row that is one existing issue** mostly restates that fact. The column earns its place only on rows 1, 2, 4 and 8.

### Not exercised

- A grooming that reorders against the author's stated preference. Every call was accepted.
- `backlog` on a project with a walking skeleton to start from, or with epics that are not already partly built.

## T3 — statements this run falsified, or checked

| Where | Statement | Status | Belongs to |
| :-- | :-- | :-- | :-- |
| `docs/EPICS.md:4` | *"nothing cites these ids"* | false — the `Epic` column cites `EPIC-1`…`EPIC-4`. In prose, with no check, so *no mechanical consumer* stays true | row 13's `epics` re-run, which owns that status line; `EPICS.md` is must-not-change here |
| `docs/verified.md:114` | *"Nothing cites a capability or epic id"* | false for both halves now — `DESIGN.md` cites capabilities, `BACKLOG.md` cites epics | T4's section supersedes it; the row stays, append-only |
| `docs/verified.md:155` | the citation half is *"half false"* | wholly false now | same |
| `docs/verified.md:115`, `:122` | `BACKLOG.md`'s preamble is false; #58 records it | true until this branch merges | nothing — historical record |
| `README.md:56-58`, `README.ja.md:73-75` | `backlog` creates nothing; one item usually becomes several issues | still true — no issue created; rows 1, 2, 4 and 8 are multi-issue | nothing |
| `docs/layout.md:16` | *"product backlog, ordered, coarse"* | truer than before — five rows group issues; twelve of fourteen are still issue-shaped | nothing |
| `skills/backlog/SKILL.md:41` | #61's LOW: this sentence would re-introduce hand-wrapped prose at the next grooming | did not fire — no prose line in the new file is broken at a column | nothing; recorded because the LOW predicted it |

## T5 — re-verification

`baseline.sh` re-run unchanged at the final tree.

**AC6 verified.** Nine validators at exit 0 with the same lines as T1; `test-gates.sh` 54/0. Open issues 20, the same twenty numbers as T1 — the skill created none. `git diff --name-only main` is confined to `docs/BACKLOG.md`, `docs/verified.md`, and `.specs/58-regroom-the-backlog/`. Checksums: every file in the baseline list unchanged except `BACKLOG.md` and `verified.md`.

**Filed after the run, by the operator, so the open count moved 20 → 21 after AC6 was recorded:** #74 — `backlog` names a walking skeleton that may not exist, two sections its template does not define, and a `Blocks` form that collides with issue numbers (AC7's three observations). Not filed: `EPICS.md:4` belongs to row 13's `epics` re-run, which `sprint` will make an issue.
