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

## T2 — `contract`

Run through the Skill tool, plugin 0.4.2, Claude Code 2.1.252. **Zero questions were put to the author.** Every step is derivation from the repository, so the interview `northstar` has does not exist here; the only decisions were the three clarifications, taken before the run.

**AC2 verified.** 37 rows in `docs/CONTRACT.md`, 37 tiered, 37 with an `Enforced by`; 18 of 18 Judgment ids grep-match `.claude/agents/gate-sdd-reviewer/rules/`. Tiers: 14 Mechanical, 18 Judgment (16 existing, 2 new), 5 Narrative.

**AC3 verified.** The 16 baseline ids are present at their baseline severities; the extracted list differs from T1's only by the two additions. `check-locks.py` at 6 matching, every `agents/*/rules-lock.json` byte-identical.

**AC5: merged, by appending.** `claims-and-prose.md` +3/−0 lines, nothing renumbered or reworded. But see the first observation below: the skill's text did not ask for that.

**AC4: the re-pin.** Command `./assets/check-locks.py --update`, run after the rulebook edit. Output, entire: `check-locks: 6 pinned file(s) match their locks in .claude/agents, agents`. Exit 0. No `rules-lock.json` created under `.claude/agents/gate-sdd-reviewer/`; the three shipped locks byte-identical before and after. #19 live, and worse than #19 describes: #19 says `--update` "prints nothing and exits 0" for a reviewer with no lock, and since #16 it prints a success line that **names `.claude/agents`** among the directories it verified, while zero of the six pinned files are there and the rulebook just edited in it was never hashed. The line reads as the dogfood rulebook being verified. A consumer following "then re-pin the lock" gets a green message and an unpinned rulebook.

**AC11 verified.** `tech.md` +4/−0, a section stating the contract was compiled from the rulebook. Step 6's literal instruction — *"Record in `.steering/tech.md` where the contract lives and that the rulebook is generated from it"* — would have written the reverse of what happened into the file both gates read. Anchors 5 of 5, all five lines byte-identical.

### Seams that did not join

- **Step 1 does not name the reviewer's existing rulebook.** It lists `tech.md`, linter and formatter config, the code, the last fifty commits, and review comments. Nothing says to read the rulebook step 4 will write into. Read it anyway, because a destination you write to without reading is a regeneration; a literal follower would produce a fresh `PFX-001` table and "add" it beside sixteen rules it never saw. The merge this run recorded came from the operator, not the skill — the same shape as #55's `product.md` merge.
- **The first thing step 1 names does not exist here.** No linter, no formatter, no config. `.vscode/settings.json` exists to switch a formatter *off* (#66). The skill's tier table assumes a Mechanical tier lives in "linter, formatter, type checker config"; here it lives in nine validators, a CI workflow, a `PostToolUse` hook and a test case. Tiered as Mechanical anyway, with the real enforcer named. Step 5 ("move the Mechanical tier into config") had nothing to move.
- **The template's id format is `PFX-001`; the rulebook's is `G-1`.** No rule says which wins on meeting an existing series. Kept the existing form and continued its numbering (`C-8`, `C-9`). The template's id column also forces ids onto Mechanical and Narrative rows that nothing will ever cite — `M-1`…`M-14`, `N-1`…`N-5` here — a second vocabulary beside the one receipts use, which is the `LV-`/`CAP-`/`EPIC-` observation from #55 again.
- **Three tiers cannot express this repo's third layer.** `AGENTS.md` places rules at hooks, the reviewer, or a skill. "Advisory findings are fixed or recorded with a reason" is enforced by `implement` step 3, and the only tier for it is Narrative, whose definition is "nothing enforces it". Row `N-5` says so.
- **The contract's table restates the rulebook and nothing checks they agree.** The lock pins the rulebook, not `CONTRACT.md`. Every Judgment row's short form can drift from the rule it indexes — #23's shape, created by the template's own design. Said in the table's preamble; not fixed.
- **`G-5` is lintable and sits in Judgment.** `shellcheck -s sh` would make it Mechanical. Not done because the project has no toolchain to install it with; recorded on the row rather than moved to Narrative, which the skill's red flags call choosing not to enforce while appearing to.
- **`tech.md`'s commit convention is not what `main` shows.** "Conventional commits — `feat:`, `fix:`, `docs:`, `chore:`" against a first-parent log where every subject is a squash-merged PR title and 36 of the last 50 carry a prefix. Row `N-2` states it as Narrative and says it is not consistently followed, which is what step 2 asks for over aspiration.
- **The rulebook's severity-word convention is unwritten, and the baseline's extraction depends on it.** The first draft of `C-8` put its rationale after `MEDIUM` and mentioned `HIGH` in it; AC3's command read the last severity word and reported `C-8 HIGH`. Every existing rule ends on its severity word. Reordered to match before commit. A format nothing states, that a check silently assumes — recorded here rather than left for the next author to discover the same way.

### Not exercised

- `--update` on a reviewer that **has** a lock and a changed rulebook. The shipped rulebooks were not touched, so the rewrite path ran against unchanged files and left them byte-identical — a useful observation, but not the re-pin path.
- What `contract` does on a second run, against a `CONTRACT.md` that already exists. The skill has no vocabulary for that either.
