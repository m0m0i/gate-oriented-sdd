# Observations — 126-run-init-on-a-scratch-project

Plugin **0.7.0**, `skills/` identical to the installed copy. Run 2026-09-12T09:26:53Z.

## T1 — baseline of THIS repository, captured before anything ran

The invariant is that this repository is unchanged. "Nothing broke" is an assertion unless
the before-state exists, so it is recorded here first.

```
./scripts/check-leakage.sh         check-leakage: clean
./scripts/check-manifests.py       check-manifests: both manifests agree
./scripts/check-markdown-fences.py check-markdown-fences: 10 ```markdown fence(s), no hand-wrapped prose
./scripts/check-receipt-schema.py  check-receipt-schema: 7 field(s) agree across 3 copies, and 5 reviewer(s) can produce the 2 needing a command
./scripts/check-skill-contracts.py check-skill-contracts: 16 skill contract(s) present
./scripts/check-templates.py       check-templates: 10 task line(s) across 3 template(s), no split red steps; 5 live spec(s), no task sequenced after the review
./assets/check-steering-anchors.sh check-steering-anchors: 6 of 6 anchor(s) resolved, none unreadable
./assets/check-locks.py            check-locks: 6 pinned file(s) match their locks in .claude/agents, agents
./assets/check-document-set.py     check-document-set: mode `full` at `docs/` — 6 document(s), 3 issue template(s) and 2 directory(ies) present
./scripts/check-contract-path.py   check-contract-path: 10 source(s) agree on `_shared/reviewer-contract.md`
./scripts/test-gates.sh            test-gates: 76 passed, 0 failed
```

## T1 — the scratch project, built before `init` saw it

A git repository in a temp directory, TypeScript, deleted in T4. Eight files:

| Path | Why it is there |
| :-- | :-- |
| `package.json` | three scripts — `lint`, `typecheck`, `test` — so step 1 has real commands to run |
| `tools/lint.mjs`, `tools/typecheck.mjs` | stand-ins for eslint/tsc that genuinely exit non-zero on a violation |
| `src/ledger.ts`, `tests/*.test.mjs` | a `src/` layout with a passing test |
| `.github/ISSUE_TEMPLATE/bug_report.md` | **an existing template with its own labels** — `init` must merge, not replace |
| `CONTRIBUTING.md` | **an existing commit convention** — `type(scope): subject`, and a branch convention that is *not* the harness's `<issue>-<kebab-title>` |
| `.gitignore` | ordinary |

**The validators discriminate**, verified before the run rather than assumed — a candidate that cannot fail tells step 1 nothing:

```
clean tree:        lint: clean | typecheck: no errors | tests pass
with a violation:  lint exit=1 (var, >100 cols) | typecheck exit=1 (explicit any)
```

**One fixture defect, mine, fixed before `init` ran:** `node --test tests/` threw `MODULE_NOT_FOUND` on Node 24 — it wants a glob, not a directory. Recorded because the project had to be green before step 4 could arm a gate on it, and because a broken fixture is the failure this repository keeps meeting; here it was loud rather than silent, which is the good direction.

**The two deliberate collisions** are the issue template and the commit convention. `init` claims to merge into both. Nothing else in this project was chosen to be awkward — which is the CAP-4 weakness this spec already names: its opinions are mine.

## T2 — `init`, steps 1–4

### Step 1 — detect

Every signal in the table was checked. What it found:

| Signal | Detected |
| :-- | :-- |
| manifests | `package.json` only — no lockfile, so the package manager is inferred rather than proved |
| scripts | `lint`, `typecheck`, `test`, with their real commands |
| CI workflows | **none** |
| test layout | `tests/`, `*.test.mjs` |
| commit convention | `type(scope): subject` — read from `git log`, matching `CONTRIBUTING.md` |
| issue templates | one, `bug_report.md`, labels `defect, needs-triage` |
| remote / default branch | **no remote**; branch `main` |
| already installed | nothing — a clean install |

**"Run each candidate validator before adopting it" was performed, not assumed.** All three passed on the clean tree and were adopted. This is the step #81 is about, and it behaved correctly *here* — see below for why that is not a refutation of #81.

**What step 1 could not detect, and correctly left for step 2:** the quality property, the reviewer name, the documentation location, the label mapping, and — because there is no remote — **the tracker**. The skill's table lists `git remote -v` as the signal for the tracker, so a repository without one has nothing to detect it from. That is not a defect; it is step 2's job.

### Step 2 — ask

Five questions, in the order the skill lists them. **Self-answered** — the operator built the target, so every answer was already known. Recorded per this spec's clarification: this exercises that the questions are asked, in what order, and that step 2 asks only what step 1 could not detect. **It is evidence for nothing about whether they are the right questions**, and `docs/verified.md`'s "cold interview" entry stays unverified.

| # | Question | Answered |
| :-- | :-- | :-- |
| 1 | Quality property owned | correctness — a ledger that sums wrong is the defect that matters |
| 2 | Source of truth above the repo | none; documents live in this repository |
| 3 | Gating vs advisory validators | all three gating |
| 4 | Confirm commit convention and branch naming | `type(scope): subject` confirmed; **branch naming conflicts** — the project uses `<initials>/<description>`, the harness requires `<issue>-<kebab-title>` |
| 5 | Anything the reviewer must never flag | `tools/*.mjs` are deliberately dependency-free stand-ins |

**Question 4 surfaced a real collision the skill has no instruction for.** The harness's review gate *requires* `<issue>-<kebab-title>` — `hooks/review-gate.sh` blocks a spec branch whose slug has no issue number — so "confirm the detected branch naming" cannot be satisfied when the project's convention is incompatible. The skill asks the question and says nothing about what to do with a conflicting answer. Filed below.

### Step 3 — write

Ten bullets, all executed. `.steering/` ×3, the two copied guards onto the `- Validators:` line, `.specs/` and `.work_logs/` READMEs, the issue templates, `ts-reviewer` with its rulebook and the contract, the four hooks, rendered settings, `AGENTS.md` + `CLAUDE.md`.

**Two things the skill told me to do that it cannot support, and one it did not tell me to do at all.**

- **#83 — confirmed at 0.7.0.** Step 3 lists `.specs/README.md`, `.specs/_archive/README.md` and `.work_logs/README.md`, "each stating its contract". `assets/` ships four issue templates and two scripts; `hooks/templates/` ships a README *about hook wiring*. **Nothing is a source for those three.** I wrote them from scratch; a consumer either invents them or leaves the directories contractless. _(My first check for this was wrong — `find -name README.md` matched `hooks/templates/README.md` and reported a source for all three. Re-checked by listing everything the plugin actually ships.)_
- **The merge instruction leaves `spec` without a type.** Step 3 says to merge into existing templates, "keep their wording and their labels, and add only the missing types". `bug` was **not** missing — the project had `bug_report.md`, labels `defect, needs-triage`. Following the instruction, I added only `feature` and `chore`. Consequences: nothing records that `defect` means `bug`, so `spec`'s "take the type from the label applied" has no mapping to apply; and the kept template's sections are *What happened / What should have happened*, where `spec`'s bug shape draws on *Reproduction / Expected / Actual / Root cause*. The instruction and the skill downstream of it want different things and nothing reconciles them.
- **Step 3 never creates the inception documents.** Its opening sentence is "**Scaffold the mandatory set**", and the mandatory set is five documents. **Not one of its ten bullets creates `docs/PRD.md`, `docs/DESIGN.md` or `docs/BACKLOG.md`.** See step 4.

### Step 4 — prove

Five proofs, run in order.

| # | Proof | Result |
| :-- | :-- | :-- |
| 1 | validators clean, `quality-gate.sh` exits 0 | **FAILED — see below** |
| 2 | `review-gate.sh` silent on the current branch | ok, exit 0, empty stderr |
| 3 | both gates block when they should | ok — `quality-gate` exit 2 naming the failing validator; `review-gate` exit 2 naming the project's own reviewer and receipt path, then exit 0 once a CLEAN receipt sits at HEAD |
| 4 | the reviewer is spawnable **and opens its contract** | **see below — the `1.0.0` observation** |
| 5 | report what was verified and what could not be | this record |

**Proof 1 failed, and it is `init`'s own doing.** `init` writes `- Mode: minimum` and `- Docs: docs/`, installs `check-document-set.py` onto the `- Validators:` line — and creates neither the `docs/` directory nor the three documents that checker requires in **both** modes:

```
$ ./scripts/check-document-set.py
check-document-set: `- Docs: docs/` does not name a directory that exists.   (exit 1)
$ <touch a source file>; sh .claude/hooks/quality-gate.sh
exit=2   Quality gate: a gating validator failed.
```

**That is CAP-4's falsifier — "a user's first turn blocked by a failure that predates them" — produced by the harness rather than by the project.** It is #81's shape with a different file, and it arrived with #110. The gap is inside step 3: the opening promises the mandatory set, the bullets never create it, and #110 then added a validator that requires it.

Note the timing, because it matters for how it is found: the gate stays **silent** until a source file changes, since `quality-gate.sh` runs the `- Validators:` line only when a `- Source globs:` path moved. So the failure lies dormant through the whole install and fires on the user's first real edit.

**Proof 4 — the observation `1.0.0` waits on. Confirmed.** Attempted rather than read: the three paths the installed reviewer names, tried in written order from the project root.

```
misses  _shared/reviewer-contract.md
OPENS   .claude/agents/_shared/reviewer-contract.md
misses  .agents/_shared/reviewer-contract.md
-> opened with NO hand-edit; first line: '# Reviewer contract'
```

The relative form misses — which is exactly what #82's round 1 discovered and why the concrete paths were added. The Claude Code path opens. `.agents/…` misses because this is a Claude Code install, which is what "open whichever your project has" is for. **#82's fix works on a real install.**

### Not exercised, named rather than omitted (C-9)

- **The reviewer was not spawned.** Proof 4's "is it spawnable" half needs a session restart in the target project; this run verified that its contract **opens**, which is the part #82 changed and the part `1.0.0` waits on. Spawnability was verified on #76 and is unchanged by this branch.
- **#84 could not fire.** It needs a project whose `docs/CONTRACT.md` cites rule ids; a clean install has no `CONTRACT.md` at all. **Not reproduced — for a reason that says nothing about whether it is fixed.**
- **#81 could not be reproduced.** Its check is `ruff` under a common config, and `ruff` is not installed here. Not observed either way.
- **Antigravity, entirely.** `.agents/` placement, which labelled path a reviewer picks there, and the invocation contract `docs/fidelity.md` calls "partial — untested".
- **The cold interview**, by this spec's own clarification.

### A procedural mistake of mine, recorded because it nearly cost the run

Testing proof 3, I created a spec branch, `git add -A`, committed — which swept **the entire `init` output** onto that branch — then checked out `main` and deleted the branch. All of it vanished. Recovered from the dangling commit via `git reflog`.

The run is about a skill that writes many untracked files into a repository that already has commits. **Committing "everything" mid-run binds that output to whatever branch happens to be checked out.** #82's session lost two case rewrites to `git checkout` on the same day; this is the same lesson from the other end — in a working tree full of uncommitted work, every git command that moves HEAD is destructive by default.
