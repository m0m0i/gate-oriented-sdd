# Observations — #48

## T1 — the greps, red

- `v0\.2\.3`: 2 hit(s)
- `never been executed`: 1 hit(s)
- `no reviewer has yet`: 1 hit(s)
- `2\.1\.238`: 4 hit(s)
- `すべての diff`: 1 hit(s)
- `verified.md, fidelity.md, skill-anatomy.md, layout.md$`: 1 hit(s)

- `README.md` 7bb1395ea4f8
- `README.ja.md` 9e59e36abed1
- `docs/layout.md` dac8738b1dcf
- `docs/verified.md` 282e993f1481

## T2 — the rewrite

Both Status sections rewritten as mirrors; the matrix line in both READMEs and in `verified.md`'s table per clarification 1; `layout.md`'s `docs/` line; the eval sentence stating the exit-0 no-op. Every T1 grep returns nothing; `2.1.238` survives at `verified.md:13` and `:20`, both as provenance. Validators run after the last write with a loop that stops on the first failure — below.
===== validators, after the last write, stopping on failure

- `./scripts/check-leakage.sh` → exit 0 — `check-leakage: clean`
- `./scripts/check-manifests.py` → exit 0 — `check-manifests: both manifests agree`
- `./scripts/check-markdown-fences.py` → exit 0 — `check-markdown-fences: 10 ```markdown fence(s), no hand-wrapped prose`
- `./scripts/check-receipt-schema.py` → exit 0 — `check-receipt-schema: 7 field(s) agree across 3 copies`
- `./scripts/check-skill-contracts.py` → exit 0 — `check-skill-contracts: 9 skill contract(s) present`
- `./scripts/check-templates.py` → exit 0 — `check-templates: 10 task line(s) across 3 template(s), no split red steps`
- `./assets/check-steering-anchors.sh` → exit 0 — `check-steering-anchors: 5 of 5 anchor(s) resolved, none unreadable`
- `./assets/check-locks.py` → exit 0 — `check-locks: 6 pinned file(s) match their locks in .claude/agents, agents`
- `./scripts/test-gates.sh` → exit 0 — `test-gates: 54 passed, 0 failed`
- `./scripts/check-version-bump.py <main>` → check-version-bump: no shipped file changed

### Per criterion, at the review-fix commit

- **AC1:** `v0.4.2` in both READMEs; `plugin.json` 0.4.2.
- **AC2:** both "what is verified" sentences name all thirteen skills, `archive` as four sweeps, and claim a receipt on every spec since #17 with two inline, which is what `.specs/**/.review-receipt` says; the Japanese mirrors the English clause for clause; "すべての diff" gone.
- **AC3:** Claude Code 2.1.252 (2026-09-05) and the two Antigravity rows as last verified 2026-08-21, in both READMEs and `verified.md`'s table; the table's preamble at `:7` rewritten to agree with it.
- **AC4:** `layout.md`'s `docs/` line lists the ten files and `decisions/`.
- **AC5:** the eval sentence states the exit-0 no-op in both languages.
- **AC6:** diff confined to the four files and this directory; the validator output above.

**Review triage.** HIGH — the reviewer claim: two receipts say `inline` and eleven docs PRs have none; premise and AC2 amended alone, then both READMEs fixed. MEDIUM ×2 — `verified.md:7` contradicted the table cell and still said #48 needed an answer: rewritten; this record asserted validator output it did not contain: pasted, with a row per AC. LOW ×3 — `2.1.238` at two dated places; `archive` named; "ten". INFO accepted: AC5's observation is recorded in the work log and #56's record, not in `verified.md`.
