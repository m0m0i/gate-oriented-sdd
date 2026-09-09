# Observations — #102

## T1 — red

    AGENTS.md:62:- `evals/` is under development — authored, no case has run, because `claude plugin eval` is early access. 
    docs/layout.md:98:├── evals/                         ← under development: authored, no case has run
    evals/README.md:14:## Status: under development — authored, no case has run
    evals/README.md:16:`claude plugin eval` is in early access and was not enabled on the account these were written on, so 
    evals/README.md:18:They are deliberately **not** wired into CI as a passing gate. Claiming a green eval suite that has n
    evals/README.md:31:Replace this section with the versions tested against, the date, and the observed deltas. Until then 
    .claude/agents/gate-sdd-reviewer.md:51:- `evals/` is authored but has never been run. Never treat it as passing evidence
    docs/DESIGN.md:19:| `evals/` | none yet | `evals/` | no capability. Under development — authored, no case has run; kept 
    docs/BACKLOG.md:43:- **Running the eval suite** — four cases authored, never executed. As of 2026-09-05 `claude plugin e
    docs/NORTH_STAR.md:37:The live instance: `evals/` holds four authored cases that have never executed, because `claude pl
    .steering/structure.md:15:| `evals/` | under development — authored, no case has run | no |
    scripts/check-skill-contracts.py:10:and `evals/` has never been run. A presence check is the weaker claim, and stating t
    docs/verified.md:14:| Antigravity CLI (`agy`) | 1.1.17 — verified 2026-08-21, not re-run since |
    docs/verified.md:15:| Antigravity IDE | 2.3.1 — verified 2026-08-21, not re-run since |
    docs/verified.md:115:| Did running the chain falsify anything already written down? | **yes, two things.** `docs/BACKLOG
    docs/verified.md:202:**Run on 2026-09-05, gate-sdd 0.4.2, Claude Code 2.1.252**, inside a local clone of a real, unrelat

- hits: evals/README.md:4 .claude/agents/gate-sdd-reviewer.md:1 AGENTS.md:1 docs/layout.md:1 .steering/structure.md:1 docs/NORTH_STAR.md:1 docs/DESIGN.md:1 docs/BACKLOG.md:1 scripts/check-skill-contracts.py:1 docs/verified.md:4

## T2 — after

- old phrasings per file: evals/README.md:0 .claude/agents/gate-sdd-reviewer.md:0 docs/layout.md:0 .steering/structure.md:0 docs/NORTH_STAR.md:0 AGENTS.md:0 docs/DESIGN.md:0 docs/BACKLOG.md:0 docs/verified.md:2 scripts/check-skill-contracts.py:0
- unverified/under development per file: evals/README.md:5 AGENTS.md:1 .claude/agents/gate-sdd-reviewer.md:1 .steering/structure.md:1 docs/DESIGN.md:1 docs/NORTH_STAR.md:2 scripts/check-skill-contracts.py:1 docs/verified.md:0 docs/layout.md:1 docs/BACKLOG.md:1
- NORTH_STAR quotes the live evals heading: yes; verified.md preamble no longer says the rows 'say so'
- diff paths: .claude/agents/gate-sdd-reviewer.md .specs/102-unverified-is-the-word/observations.md .specs/102-unverified-is-the-word/spec.md .steering/structure.md AGENTS.md docs/BACKLOG.md docs/DESIGN.md docs/NORTH_STAR.md docs/layout.md docs/verified.md evals/README.md scripts/check-skill-contracts.py 

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

**AC1, the two lines that stay.** `docs/verified.md:115` quotes `docs/BACKLOG.md`'s old preamble — "`epics` has never run…" — as the thing #55 found false, and `:202` says `init` was the last skill in the queue that had never run, dated 2026-09-05. Both are observation rows; rewording them would rewrite what was recorded. AC1 was amended ahead of this commit to say so, and the T2 commit was re-made behind the amendment so the tick reads as an independent check.

**AC2 for `docs/verified.md`** is met by its lines 5 and 7 — the rows carry the date they were verified, and the preamble says so — not by the word; the count of `0` above is the word count, not the outcome.

**Review triage.** CLEAN on the first pass. LOW ×2 — the spec said "thirteen" where no count of the diff yields it, and the record showed `verified.md: 0` under a ticked AC2 without saying why: both fixed here, after the review, in the record only.
