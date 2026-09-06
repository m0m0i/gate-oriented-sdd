# Observations — #92

## T1 — red, taken from `main`

    README.md:152:**v0.4.3 — pre-release.** A reference implementation with a tested-against version matrix, not a supported
    README.ja.md:153:**v0.4.3、pre-release です。** 検証済みバージョンの一覧を添えた reference implementation であって、サポート付きのプロダクトではありません。[eval スイート](
    docs/layout.md:98:├── evals/                         ← authored, not yet run
    .steering/structure.md:15:| `evals/` | authored, unrun | no |
    evals/README.md:14:## Status: authored, not yet run
    AGENTS.md:62:- `evals/` is authored but unrun — `claude plugin eval` is early access. Do not wire it into CI as a passin

- "under development" / 開発中 on main: 0 0 0 0 0 0

## T2 — after

- old phrasings, one per file: 0 0 1 1 1 0
- under development / 開発中, one per file: 2 2 1 1 2 1
- the run fact, kept:
    .steering/structure.md:15:| `evals/` | under development — authored, unrun | no |
    README.md:152:**v0.4.3 — pre-release.** A reference implementation with a tested-against version matrix, not a
    README.ja.md:153:**v0.4.3、pre-release です。** 検証済みバージョンの一覧を添えた reference implementation であって、サポート付きのプロダクトではありません
    docs/layout.md:98:├── evals/                         ← under development: authored, not yet run
    evals/README.md:14:## Status: under development — authored, not yet run
    AGENTS.md:62:- `evals/` is under development — authored but unrun, because `claude plugin eval` is early acces
- diff paths: .specs/92-eval-suite-under-development/observations.md .specs/92-eval-suite-under-development/spec.md .steering/structure.md AGENTS.md README.ja.md README.md docs/layout.md evals/README.md 
- anchors: check-steering-anchors: 5 of 5 anchor(s) resolved, none unreadable

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

### Second commit — AC1 was red under T2's first commit

AC1's grep still matched the three lines that kept "not yet run" or "unrun" after the new phrase, while AC2 keeps the fact. The fact is now carried as "no case has run" in `layout.md`, `structure.md`, `evals/README.md` and `AGENTS.md`, so AC1's grep returns nothing and every file still says it. Old phrasings per file after this: 0 0 0 0 0 0.

## The run behind the date

The READMEs' sentence moves from 2026-09-05 to 2026-09-06 because the command was run again on 2026-09-06, in the session that produced this branch, before the wording change was asked for:

    $ claude --version
    2.1.263 (Claude Code)
    $ claude plugin eval . --case 'review-gate*' --runs 1 --max-cost-usd 3 --allow-tools Bash --no-publish --json <scratch>/eval-smoke-2.json
    `plugin eval` is currently in early access
    $ echo $?
    1

No results directory, no JSON, no cost. Two things changed since 2026-09-05: the CLI is 2.1.263, and the gated invocation exits **1** where it exited 0. That is why the sentence now says "exits without running a case" rather than "exits 0", and why the clause about refusing to read that exit code as a pass was dropped: at exit 1 there is no exit code that could be read as one. The refusal that remains — a green suite that never ran is the unverified assertion this harness exists to prevent — is the one that still has an object. Recorded here as deliberate; the reviewer's MEDIUM was right that it had been silent.

## Consequences to existing documents

- `docs/NORTH_STAR.md:37` quoted the old `evals/README.md` heading verbatim; `docs/DESIGN.md:19` restated "Authored and unrun". Both would have been false after the rename. AC3 was widened in its own commit and both lines now carry the new label with the run fact. `docs/BACKLOG.md`'s Unshaped item describes the block, not the label, and stays; `docs/verified.md`'s observations are dated and stay.

**Review triage.** HIGH — the re-date had no run on the branch: the run is above. MEDIUM — no consequences section, two lines made false: widened and fixed. MEDIUM — "exits 0" and the refusal clause dropped silently: recorded as deliberate, with the reason. LOW — `evals/README.md:31` pointed at the label rather than the fact: now quotes "no case has run". INFO ×3 accepted: this is the edit `NORTH_STAR.md` calls the most tempting, and the fact is kept in every file; the second commit's heading now says AC1 was red under the first; `Status: done` before review is `implement`'s own order.

**The other half of the dated clause.** `claude plugin eval --help` on 2026-09-06, CLI 2.1.263: exit 0, first line `Usage: claude plugin eval [options] [command] [target]`. So both observations in the READMEs' sentence — the help renders, the invocation prints "in early access" and exits without running — were made on the date the sentence gives. LOW accepted by adding this line; the READMEs are unchanged.
