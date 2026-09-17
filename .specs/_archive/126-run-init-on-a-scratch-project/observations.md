# Observations — 126-run-init-on-a-scratch-project

Plugin **0.7.0**, `skills/` identical to the installed copy. Run 2026-09-12T09:26:53Z.

## T1 — baseline of THIS repository, captured before anything ran

The invariant is that this repository is unchanged. "Nothing broke" is an assertion unless
the before-state exists, so it is recorded here first.

_Fenced with four backticks, not three: `check-markdown-fences`'s own output contains a
three-backtick run, which closes a three-backtick fence early. The block was complete in
git and truncated in every renderer — a record that is right in the file and wrong on the
screen, which is the half a reader sees._

````
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
````

## T1 — the scratch project, built before `init` saw it

A git repository in a temp directory, TypeScript, deleted in T4. Eight files — `tests/` held exactly one, `ledger.test.mjs`; the count is named literally because T4 deletes the only thing that could confirm it:

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

**A second, independent cause sits behind it, and the run did not see it.** `check-document-set.py` fails at `docs.is_dir()` before reaching its `TEMPLATES = ("feature.md", "bug.md", "chore.md")` check — and on this target `bug.md` does not exist either, because step 3's merge bullet said to add only the *missing* types and `bug` was not missing. So **fixing #127 alone would not turn proof 1 green** on any project that already had a differently-named bug template. Two bullets in the same step disagree on a literal filename. Filed as **#130** after review caught what this record had attributed wholly to #127 — the fail-fast hid it, and I read the first cause as the only one.

**That is CAP-4's falsifier — "a user's first turn blocked by a failure that predates them" — produced by the harness rather than by the project.** It is #81's shape with a different file, and it arrived with #110. The gap is inside step 3: the opening promises the mandatory set, the bullets never create it, and #110 then added a validator that requires it.

Note the timing, because it matters for how it is found: the gate stays **silent** until a source file changes, since `quality-gate.sh` runs the `- Validators:` line only when a `- Source globs:` path moved. So the failure lies dormant through the whole install and fires on the user's first real edit.

**Proof 4 — the observation `1.0.0` waits on. Confirmed.** Attempted rather than read: the three paths the installed reviewer names, tried in written order from the project root.

```
misses  _shared/reviewer-contract.md
OPENS   .claude/agents/_shared/reviewer-contract.md
misses  .agents/_shared/reviewer-contract.md
-> opened with NO hand-edit; first line: '# Reviewer contract'
```

The relative form misses — which is exactly what #82's round 1 discovered and why the concrete paths were added. The Claude Code path opens. `.agents/…` misses because this is a Claude Code install, which is what "open whichever your project has" is for. **#82's Claude Code half works on a real install** — the `.agents/` destination it also added remains unopened by anything.

### Not exercised, named rather than omitted (C-9)

- **The reviewer was not spawned.** Proof 4's "is it spawnable" half needs a session restart in the target project; this run verified that its contract **opens**, which is the part #82 changed and the part `1.0.0` waits on. Spawnability was verified on #76 and is unchanged by this branch.
- **#84 could not fire.** It needs a project whose `docs/CONTRACT.md` cites rule ids; a clean install has no `CONTRACT.md` at all. **Not reproduced — for a reason that says nothing about whether it is fixed.**
- **#81 could not be reproduced.** Its check is `ruff` under a common config, and `ruff` is not installed here. Not observed either way.
- **Antigravity, entirely.** `.agents/` placement, which labelled path a reviewer picks there, and the invocation contract `docs/fidelity.md` calls "partial — untested".
- **The cold interview**, by this spec's own clarification.

### A procedural mistake of mine, recorded because it nearly cost the run

Testing proof 3, I created a spec branch, `git add -A`, committed — which swept **the entire `init` output** onto that branch — then checked out `main` and deleted the branch. All of it vanished. Recovered from the dangling commit via `git reflog`.

The run is about a skill that writes many untracked files into a repository that already has commits. **Committing "everything" mid-run binds that output to whatever branch happens to be checked out.** #82's session lost two case rewrites to `git checkout` on the same day; this is the same lesson from the other end — in a working tree full of uncommitted work, every git command that moves HEAD is destructive by default.

## T4 — re-verification, what was filed, and the discard

**AC1 — the invariant holds. 11/11 validators identical** to the baseline captured before anything ran, compared by name rather than by eye.

_The first comparison reported 2/3 and looked like a real difference._ It was not: my extraction regex read the baseline block up to the first three-backtick run, and `check-markdown-fences`'s own output **contains** one. So the record was complete in git and truncated in the renderer, and my comparison read the truncation. The fence is now four backticks and the reason is recorded where it happened.

That is the same shape #124 was filed for, arriving in a document rather than a case. _Review pushed back on an earlier wording here — "the fourth time in two days" — as a claim about this repository's history that the diff cannot support. It is withdrawn: the instances are enumerated in #124 itself, which is where a reader can count them._

| Criterion | Result |
| :-- | :-- |
| AC1 | 11/11 validators identical; `test-gates` 76 before and after — **9/11 independently re-run at review**, the other two outside the reviewer's allow-list (#131) |
| AC2 | diff is `docs/verified.md` + this spec directory. `check-version-bump`: **no shipped file changed** — so no version bump, as the spec said |
| AC3 | `check-leakage: clean`, run by hand; **zero** occurrences of the scratch project's name in either committed file |
| AC4 | every step recorded above, with "Not exercised" naming what could not be |
| AC5 | proof 4 — attempted from the project root, stated as observed |
| AC6 | #83 confirmed, #84 not reproduced, #81 not observed; #127/#128/#129 filed, #130/#131 after review |
| AC7 | the `docs/verified.md` section, with the synthetic limitation above its table |
| AC8 | no shipped file modified in response to any finding |

### Filed, not fixed

| # | What |
| :-- | :-- |
| **#127** | `init` installs `check-document-set.py` and never creates the documents it requires — the gate is armed **red** by the harness's own file, dormant until the first source edit. CAP-4's falsifier. |
| **#128** | the template merge leaves `spec` with no way to read an issue's type — no label mapping is recorded, and the kept template's shape is not the one `spec`'s bug template draws on |
| **#129** | step 2 asks the operator to confirm a branch convention `review-gate.sh` will reject, and says nothing about what to do with a conflicting answer |
| **#130** | `check-document-set.py` requires a literal `bug.md` that step 3's merge bullet tells the installer not to create — the second cause of proof 1, filed after review found it |
| **#131** | this reviewer's allow-list has drifted from the `- Validators:` line, so two of eleven validators could not be independently re-run |

### Confirmed, not reproduced, and not observed — kept distinct on purpose

- **#83 — confirmed.** No source ships for the three READMEs.
- **#84 — not reproduced**, because a clean install has no `CONTRACT.md` for it to fire on. That says nothing about whether it is fixed, and the distinction matters: a run that reports "did not fire" as "passed" is the failure this repository keeps finding one level up.
- **#81 — not observed.** Its check is `ruff`; it is not installed here.

### The scratch project is deleted

`rm -rf` on its temp root, verified gone. Nothing was pushed anywhere. It existed in version control only inside itself.

## What this run was worth

Three new defects from the run — one of them (#127) shipped **this morning** by #110 and reachable on the very first install — and a fourth, #130, that the *review of this record* found hiding behind #127's fail-fast. None of the four was visible from reading the skill. Against that: **#82's Claude Code half confirmed working on a real install** — the `.agents/` destination it also added stays unopened by anything — which is the observation `1.0.0` was waiting on and which no amount of reasoning could have produced.

Both halves argue the same thing. The harness's own claim is that a gate beats a request; this run is the same claim applied to verification — **executing the skill beats reading it**, and the gap between them is where four of today's defects were living.

## Review round 1 — CLEAN, 0 blockers, 0 HIGH, 4 MEDIUM, 3 LOW

Reviewed at `f1c2402`. Every finding was about **the record**, which is correct — the run is gone and the record is the artifact.

**The reviewer could only re-run 9 of the 11 validators.** `./assets/check-document-set.py` and `./scripts/check-contract-path.py` are on the `- Validators:` line and absent from its allow-list, so it recorded them as **unknown rather than as agreeing** — the same discipline this record is being judged by, applied to itself. Filed as **#131**. AC1's "11/11" is therefore 9/11 independently confirmed, and that is now stated rather than implied.

**And the issue numbers are the author's claim, not a verified one.** The reviewer could not confirm that #127-#131 exist: that needs `gh`, which is outside its allow-list, and no committed file here references them. AC6 only requires the numbers to appear in the record, so this is not a conformance gap — it is the one "could not observe" from the review that this record had not inherited, in the document whose whole subject is inheriting exactly those.

### The findings, and what they changed

- **A second cause of proof 1, hidden behind the first.** The record blamed #127 entirely. `check-document-set.py` also requires a literal `bug.md`, which step 3's merge bullet tells the installer *not* to create — and the `docs.is_dir()` fail-fast hides it. **Fixing #127 alone would not turn proof 1 green.** Filed as #130. This is the finding worth the round: a run that stops at the first red reports one cause, and the record inherited that.
- **`docs/verified.md`'s own "Last updated" field** said 2026-09-05 while the diff added a 2026-09-12 section — the honesty ledger, stale by the definition stated in its own sentence.
- **The section named the plugin version and not Claude Code's**, so the new row was covered by no version line, in a file whose preamble says "re-verify when the version column moves".
- **The `1.0.0` row's subject was an actor that never acted.** "Does a shipped reviewer open its contract" — no reviewer was spawned; the operator resolved the paths. The claim is sound and the grammar overstated it. Reworded to what was performed.
- **"Detect every signal — yes"** read as *all were found*, where four of seven had nothing to detect. Now says so, including that the package manager was *inferred* rather than proved.
- The scratch project's file count and the T4 criterion table, both tightened.

### One claim withdrawn

The record said this was "the fourth time in two days" that a record or fixture produced a result reading as a finding. Review pushed back: that is a claim about the repository's history, not verifiable from the diff, and C-1 is what it exists for. Withdrawn and replaced with a pointer to #124, which enumerates the instances.

**A reviewer correcting an author's self-criticism is worth recording.** The instinct that a confession is automatically safe is wrong — an unverifiable claim is unverifiable in either direction, and this one was flattering in its own way: it made a pattern sound better-established than the evidence in front of the reviewer.

## Review round 2 — APPROVE, 0 blockers, 0 HIGH, 0 MEDIUM, 3 LOW

Reviewed at `fd43af8`. All four round-1 MEDIUMs and three LOWs closed. The reviewer re-derived the
two-causes paragraph independently and confirmed it does not oversell — naming the three clauses
that keep it honest, of which the load-bearing one is *"on any project that already had a
differently-named bug template"*: on a greenfield target `init` copies `bug.md` and cause B never
arises, so dropping that qualifier would have been the overstatement.

All three LOWs fixed:

- **The `1.0.0` row said "confirms #82 on a real install", unqualified** — in the one row a release
  decision gets quoted from, sixteen lines above the entry recording that `.agents/` has never
  been opened. _(The review said eighteen without counting and this record inherited it verbatim — a reviewer's unchecked number becoming a record's unchecked number one commit later, which the reviewer then caught against itself.)_ Now "**#82's Claude Code half**", with the gap named in the row itself. The general
  point is worth keeping: a qualifier that lives elsewhere in the document does not travel with the
  sentence that gets quoted.
- **The record had not inherited the review's second "could not observe"** — that the reviewer
  cannot confirm #127–#131 exist, because `gh` is outside its allow-list. Now stated: the numbers
  are the author's claim. In a document about inheriting exactly those, missing one was the right
  thing to be caught on.
- **The two ledgers a reader scans had not caught up with round 2** — AC1 asserted 11/11 where the
  9/11 qualification sat 37 lines below, the Filed table listed three of five issues, and the AC
  rows had landed out of order. All three fixed at the ledger rather than in prose.

### What two rounds of reviewing a *record* were worth

Neither round found an **observation that was false**. Both found things wrong with what the run
**claimed** — and one, #130, with how far it looked: a run that stops at the first red sees one cause,
which is a coverage defect in the method rather than in the writing. Between them: a second cause masked by a fail-fast, a stale ledger field, a version row covering no
version, a grammatical subject that never acted, a count that read as found-all, an unverifiable
aside, and a qualifier that would not have travelled with the sentence it qualified.

That is the argument for reviewing verification records at all. The run is gone; the record is the
only thing that will ever be read again, and every one of those defects would have survived into it
unchallenged.

## Review round 3 — CLEAN, 0 blockers, 0 HIGH, 1 MEDIUM, 3 LOW

Reviewed at `6029756`. **The MEDIUM is the rule this record had just written, on its third
instance, in this file.**

Round 2 recorded: *a qualifier that lives elsewhere in the document does not travel with the
sentence that gets quoted.* Round 3 found the unqualified `#82` claim **still standing at `:191`**,
under the heading *What this run was worth* — the passage a release note lifts. I had reported
fixing it "where the claim is also made"; there were two places and I fixed one.

Worth stating plainly, because it is the more useful half: **writing the rule down did not make me
apply it.** I recorded the principle and then failed to enumerate the instances it governed — which
is what a guard does and a paragraph does not. The claim is now qualified in all three places, and
enumerated rather than trusted.

### The three LOWs

- **"Neither round found anything wrong with the run" was false by this file's own account.** #130
  is a coverage defect in the run's *method* — a run that stops at the first red sees one cause —
  and the summary erased the half reflecting on the run while keeping the half reflecting on the
  writing. In the section where that asymmetry is hardest for the author to see, which is why I
  asked the reviewer to look there.
- **"Three new defects" no longer agreed with the record's own five-issue ledger.** `verified.md`
  had it right; the observations' closing section had not caught up. Three is true of *what the run
  produced*; four is true of *what this record produced*, which is what the heading promises.
- **"Eighteen lines above" was sixteen** — and the number was the reviewer's, written without
  counting in round 2 and inherited here verbatim. It caught it against itself. A reviewer's
  unchecked count becomes a record's unchecked count one commit later, and the neighbouring "37
  lines below" being correct is what made the wrong one look checked.

### Three rounds on a record, and the shape of what they found

Round 1: a second cause masked by a fail-fast, and four overstatements. Round 2: where the
corrections landed. Round 3: the one place a correction had not landed, plus two counts and a
false dichotomy.

**Every round found something, and all but two of the findings were in the summary rather than the
observations.** The exceptions were the fixture file count, in `## T1`, and the two-causes
paragraph in step 4 — which is #130, round 1's largest finding. A **third correction** also landed
in step 4, proof 4's `#82` qualifier, from a finding filed against `docs/verified.md`; that is why
*two findings* and *three corrections* both appear in this file and both are right. The
step-by-step record was **amended in two of the three passes**, not untouched.

_An earlier wording claimed it had survived all three untouched, and review disproved it from the
commit hunks. It was false in the direction that flatters the run, and it certified a half of the
document review had never cleared — "no finding was filed" read as "it was sound", which is the
collapse this record refuses one level up every time it keeps #84 at **not reproduced**._

What kept failing is still, mostly, the part that tells a reader what it meant — the part that gets
quoted, and the only part most readers will see.

## Review round 4 — CLEAN, 0 blockers, 0 HIGH, 1 MEDIUM, 1 LOW

Reviewed at `76b232a`. I asked the reviewer to check the one sentence it was better placed to check
than I was — a claim about its own three reports. **It was false, and false in the direction that
flatters the run.**

The claim: *every round found it in the summary rather than in the observations*, and *the
step-by-step record has survived three passes untouched*. Disproved from the commit hunks: `fd43af8`
amended `## T1` and `### Step 4 — prove`, and `6029756` amended `### Step 4` again — three
corrections inside the observations half, one of them the two-causes paragraph that became #130 and
that I had myself called round 1's largest finding.

**Why it was worth a MEDIUM rather than a shrug**, in the reviewer's framing and now recorded here:
the sentence certified a half of the document that review had never cleared. *"No finding was filed
against the observations"* and *"the observations were sound"* are different statements, and
collapsing them is the same move this record refuses one level up every time it keeps #84 at **not
reproduced** rather than passed. It was also the file's closing sentence — which, by this branch's
own evidence, is the most-quoted position in it.

The LOW was a fragment — "Both halves of them:" — left by patching a sentence in place rather than
rewriting it, in the paragraph whose subject is that the summary is the part people read.

### Four rounds, and the one thing I would carry to the next record

Round 4 found the same failure as round 3, one level more abstract: **a general claim asserted
instead of enumerated.** Round 3 was a qualifier I stated as a rule and did not apply to its three
instances. Round 4 was a summary I asserted about three reports without checking them against the
three diffs sitting in the same branch.

Both were cheap to check and neither was checked, because a sentence *about* evidence reads as
evidence. The rule that would have caught both: **when a record generalises over a set, enumerate
the set in the record.** Three instances of the `#82` claim; three rounds of findings. Both lists
were short, both were available, and neither was written down until review demanded it.

### A correction to the round-4 entry above, and the fifth instance of the same thing

The commit that added the round-4 section **claimed both fixes and made neither.** The script
applied the first replacement, asserted on the second, threw before `write_text`, and I committed
the appended narrative without re-reading the file. So for one commit this record described
correcting a false sentence that was still sitting nine lines above the description.

Both are applied now and verified by grep, each replacement independent so one failure cannot
silently discard the other.

**That is the fifth instance of the shape #124 tracks, and the third recorded on this branch**, and
it is the sharpest because the
artifact was a claim about itself: a step that did not run, whose failure was not checked, followed
by a report that assumed it had. #124 was filed for four of these; this one belongs in it too, and
it extends the rule — *"a case must assert why it went red"* has a sibling: **a report must be
written from the artifact, not from the intent.** Every prior instance was a check that could not
fail; this was a narrative that could not be false, because nothing compared it to the file.

The mechanical fix is the one already learned twice today and not yet generalised: **bind the exit
status, and re-read the artifact.** The diagnosis matters and an earlier wording here had it
backwards: `&&` is exactly what *would* have stopped the commit — an uncaught `AssertionError` exits
1, and `python3 … && git commit` never reaches the commit. What I actually used was a
**newline-separated sequence**, where every command runs regardless of the last one's status, and
the `AssertionError` scrolled past on stderr. Verified both ways rather than reasoned about.

## Review round 5 — CLEAN, 0 blockers, 0 HIGH, 2 MEDIUM, 1 LOW

Reviewed at `08eb58b`. The reviewer verified the previous round's confession **from the artifact
rather than from my message** — `git show cb3a159 --stat` is 34 insertions and 0 deletions, a pure
append, so the account was exact. It also re-counted "nine lines above the description" against the
old blob and found it reconciles. That is the behaviour the round-4 entry asked for, applied to the
entry itself.

Three findings: **two in text I adopted rather than derived, and one — the shell diagnosis — in text I
reasoned rather than ran.**

- **"The exceptions both landed in step 4" was wrong** — the fixture file count is at `:31`, inside
  `## T1`. The wording was the reviewer's own suggested fix from round 4, taken verbatim. It also
  conflated two counts: *two findings* were filed against observation lines, while *three
  corrections* landed there, the third being proof 4's `#82` qualifier from a finding filed against
  `docs/verified.md`. Both numbers appear in this file; neither was wrong; nothing bridged them.
- **"The fifth instance on this branch" reattached a scope the record had already withdrawn.**
  #124's four were "in two days", and one of them happened in #82's session — a different branch.
  On *this* branch the enumerable instances are three. The round-1 withdrawal had moved that count
  into #124 precisely because it could not be scoped here, and the round-4 entry quietly moved it
  back.
- **The shell diagnosis was backwards.** I wrote that `&&` does not stop a later `git commit`. It is
  exactly what does — an uncaught `AssertionError` exits 1 and the chain halts. What I actually used
  was a newline-separated sequence. Verified both ways in a shell rather than reasoned about, and
  the prescription that follows it was right all along; only the explanation pointed a future reader
  away from the form that would have saved them.

### The pattern under two of the three, which is the reviewer's and belongs in #124

**Text adopted from elsewhere does not inherit the checking that the text around it got.** The
central claim of the round-4 section — that `cb3a159` applied neither fix — was derived, checked and
true. Its two peripheral claims were copied: one from the reviewer's round-4 report, one from the
arithmetic of a withdrawn sentence. Both were wrong.

The reviewer's own framing, recorded because it implicates it as much as me: its uncounted
"eighteen" and its mislocated "both landed in step 4" **both entered this record because it wrote
them in a report and I trusted the report over the file.** A review is not a source; it is a claim
about a source, and it needs re-deriving exactly as much as anything else does.

**The third had a different lesson and folding it in would have lost it.** The shell sentence failed
because a claim about a tool's behaviour was asserted from memory where one command would have tested
it — the same failure as asserting a count, and the less flattering of the two, since copying someone
else's wording is a gentler story than asserting how `&&` behaves without running it.

That is the third form of one thing on this branch — after *a qualifier does not travel with the
sentence that gets quoted* and *writing the rule down did not make me apply it*. All three are the
same failure at different distances: **the check that was not performed because something nearby had
been.**

## Review round 6 — CLEAN, 0 blockers, 0 HIGH, 1 MEDIUM, 1 LOW

What changed, and nothing else. The reviewer's advice was to record the fixes without a new thesis,
on the evidence that a thesis had failed in each of the last three rounds and a list in none.

- **`:371`** — "all three were in text I adopted rather than derived" was false for one of the
  three. The shell diagnosis was new text in `08eb58b`, not adopted; `:382` already attributed it
  correctly and `:392` already narrowed the set to two, so the section contradicted itself twelve
  lines apart. Now: two adopted, one reasoned-rather-than-run.
- **`:390`** — the heading's scope narrowed to match.
- **New sentence after `:392`** — the third finding's own lesson, which folding it into the
  adopted-text thesis had erased: a claim about a tool's behaviour is testable in one command, and
  asserting it instead is the same failure as asserting a count. Recorded as the less flattering of
  the two, because copying someone else's wording is a gentler story than asserting how `&&` behaves
  without running it.
- **`:348`** — re-wrapped from 130 columns to 99.

One fact noticed while re-wrapping and not acted on: this file mixes hard-wrapped prose (the review
sections, ~100 columns) with unwrapped paragraphs (the T1–T4 observations, some over 400). #61 made
unwrapped the convention for this repository. `check-markdown-fences.py` passes either way, since it
polices `​```markdown` fences rather than prose. Left as it is — consistency here is worth less than
another round.

**Stopping here** on the reviewer's recommendation: rounds 1–2 found defects in what the run
recorded; rounds 3–6 found defects only in sections about the reviews, each created by the round
before it. The observations half has been stable since `6029756` and the `docs/verified.md` section
since round 3 — the parts that will actually be read again are done.
