# Spec: init arms the document-set gate red on a fresh install
- Slug: 127-init-arms-the-document-set-gate-red   Issue: 127   Type: bug   Status: archived
- Author: Claude Opus 5   Date: 2026-09-13   Archived: 2026-09-17

## 1. Requirements (WHAT / WHY)

- Reproduction: run `init` at 0.7.0 against a project with no `docs/` directory, then run
  `./scripts/check-document-set.py`. Observed 2026-09-12 on #126 against a scratch TypeScript
  project.
- Expected: `init` step 4's first proof — *"Every gating validator runs clean on the current
  tree, and `quality-gate.sh` exits 0"* — passes. Step 3 opens with *"Scaffold the mandatory
  set"*, and the mandatory set is five documents.
- Actual: `init` writes `- Mode: minimum` and `- Docs: docs/`, copies
  `assets/check-document-set.py` into the project, adds it to `- Validators:` — and creates
  neither `docs/` nor `PRD.md`, `DESIGN.md`, `BACKLOG.md`, which that checker requires in both
  modes (`assets/check-document-set.py:32`, `:131`). The checker exits 1 at `:128`.
- Impact: every first install. It is CAP-4's falsifier stated literally — *a user's first turn
  blocked by a failure that predates them* — and `.steering/product.md` names that as the
  moment the gate is switched off and never switched back on. It is also **dormant**:
  `quality-gate.sh` runs the `- Validators:` line only when a `- Source globs:` path changed
  and a document is never source, so the install looks clean and the failure fires on the
  user's first real edit, when the cause is furthest from mind.
- **Root cause:** `check-document-set.py` asks two questions through one exit code. *"Is the
  harness installed correctly?"* — directories, issue templates, steering — is an install-time
  invariant that `init` can and must make true. *"Has this project authored its inception
  documents?"* is a fact about the project's maturity that `init` cannot make true without
  writing the user's thinking for them. #110 added the second question to a checker `init` arms
  at install time, and nothing distinguishes *not yet authored* from *authored and then lost*.
  The `- Mode:` line was built to separate a deliberate omission from an abandonment; it has no
  value for the state every project passes through first.
- Acceptance criteria:
  - [x] **AC1:** WHEN `init` completes on a project with no inception documents THEN
        `check-document-set.py`, as `init` step 3 placed it on the `- Validators:` line, exits 0
        on the resulting tree. **Narrowed at review round 4**, from "every validator it placed"
        — step 3 also arms `assets/check-steering-anchors.sh` (`skills/init/SKILL.md:56`), and
        the fixture neither installs nor runs it. The wider claim was true of the intent and
        false of the evidence, and a criterion is the artifact that outlives the branch, so the
        code comment saying so was not enough. The unexercised axis is recorded in Design.
  - [x] **AC2:** the regression test fails before the fix and passes after.
  - [x] **AC3:** WHEN the document set is genuinely incomplete in a state that claims the
        documents exist THEN `check-document-set.py` still exits non-zero — the fix narrows
        what is claimed, and narrows it in a declared state, never by tolerating absence in the
        states that exist today.
  - [x] **AC4:** the state in which documents are not required is **self-terminating**: it
        stops passing once the project starts building against documents it never wrote, so it
        cannot become a permanent switch-off.
  - [x] **AC5:** whatever `init` writes, no inception document contains a `TODO` placeholder —
        `skills/init/SKILL.md` step 3's closing rule, and its reason (an unpopulated document
        teaches that documents are noise) applies past `.steering/`.
  - [x] **AC6:** `init`'s own text no longer promises what it does not do: step 3's *"Scaffold
        the mandatory set"* and its bullet list agree about the inception documents.
  - [x] **AC7:** every reader of `- Mode:` has a defined reading for the new value. A declared
        state that one reader understands and another falls through is the drift the line was
        added to prevent.
- Out of scope:
  - **#130** — `init`'s merge bullet and `TEMPLATES` disagree on a literal filename. It is the
    *second* independent cause of the same red gate, on the template axis rather than the
    document axis, and #127 masks it because `:128` fails before `:134` is reached. Fixing this
    spec does not turn step 4's first proof green on a project that already had
    `bug_report.md`; that is #130's to close, and this spec must not claim it.
  - **#83** — the three READMEs step 3 lists and the plugin ships no source for.
  - **#128** — the missing label→type translation.

### Clarifications
- 2026-09-13 — **Does `init` create the three inception documents, or does the checker stop
  requiring them in a state that says so?** **Answered: a third declared state,
  `- Mode: bootstrap`** — harness installed, inception documents not yet authored. Rejected:
  *`init` runs `prd`/`design-doc`/`backlog`* (green with genuine content, but it turns install
  into a multi-hour interview, against `init`'s own *"treat a greenfield repo as the special
  case"* and the week-two abandonment its step 3 warns about); *placeholder documents* (the
  `TODO` step 3 forbids, one directory over — AC5); *leave the checker off `- Validators:`
  until the documents exist* (the gate switched off at install and never switched back on,
  which is what `.steering/product.md` names as the failure). The chosen route keeps the
  declaration-plus-verification shape #110 was built on: the new state is **declared**, not
  inferred from an empty `docs/`, for the same reason `minimum` is.
- 2026-09-13 — **What stops `bootstrap` becoming permanent?** **Answered: the first spec.**
  `bootstrap` stops passing once `.specs/` holds any spec, because a PRD starts being cited the
  moment a spec exists. The grace period therefore lasts exactly until the harness is genuinely
  in use, and the failure arrives while the user is inside the flow rather than on their first
  turn — which is the whole distinction CAP-4 draws. Rejected: *the first **merged** spec* (a
  longer runway, but the first spec would then be authored against documents that do not exist,
  which is precisely the citation it cannot make); *a loud line and nothing else* (honest
  output, but a project can sit in it for a year and nothing ever escalates — a switch-off with
  a note, which AC4 exists to forbid).
- 2026-09-13 — **Version bump.** **Answered: 0.8.0, minor.** Precedent: #110's `- Mode:` line
  → 0.6.0 (minor, new capability), against #109's prose → 0.5.1 (patch). This adds a value to a
  machine-read line and changes what `init` writes, so the flow moves and the flow argument
  wins. Rejected: *1.0.0* — #82 shipped, so the reviewer-contract relocation that was holding
  the major is done, but this spec changes the installed interface in the same breath as
  declaring it frozen; let the third mode value settle first.
- Not asked, because the reasoning settles them: **the state's name** is `bootstrap`, not
  `pending` or `new` — it names what the project is doing (standing the harness up) rather than
  a status of the check. It appears nowhere in the plugin today, so it carries no prior
  meaning to collide with — checked, rather than assumed.
  **Whether `bootstrap` is a `- Mode:` value or its own machine-read line** — a value, because
  the existing line already answers "which document set did this project sign up for" and
  "none yet" is an answer to that question; a second line would let the two disagree.
  **Backward compatibility** — adding an enum value breaks no project already on
  `minimum`/`full`, which is why this is not a major.

## 2. Design (HOW)

- **Fix approach, and why this rather than the narrower or wider fix.** Split the one exit code
  in two along the seam the root cause names, and declare which half is being claimed.
  `bootstrap` asserts the install-time invariant — `.specs/`, `.work_logs/`, the three issue
  templates, a readable `- Mode:` line — and asserts nothing about the inception documents,
  saying so in its own success line rather than in the shared one (G-1: not finding a problem
  and not having looked must not share an outcome). `minimum` and `full` are **untouched**;
  every case that fails today still fails (AC3).

  The narrower fix — have `init` create `docs/` and stop there — leaves the three documents
  missing and the gate red, so it fixes nothing. The wider fix — make the checker tolerant of
  absent documents generally — deletes #110.

- **Self-termination (AC4).** In `bootstrap` only, the checker fails when `.specs/` holds any
  spec: a directory containing `spec.md`, under `.specs/` or `.specs/_archive/`. Three
  outcomes, not two — if `.specs/` cannot be *read*, that is neither "no spec" nor "a spec" and
  it fails with its own message. `os.scandir`, not `Path.glob`, which swallows `OSError` and
  would report an unreadable directory as an empty one; that is the #115 lesson and G-1 again.

- **Where `docs/` fits.** `bootstrap` does not require `docs/` to exist, because nothing has
  been written into it. The URL check stays ahead of it in all three modes: a `- Docs:` naming
  another repository is still its own outcome, not a directory that happens to be absent.

- **Affected files:**

  | File | Change |
  | :-- | :-- |
  | `assets/check-document-set.py` | `bootstrap` added to `MODES`; the document set and the `docs/` directory required only under `minimum`/`full`; the self-termination scan; its own success line (AC1, AC3, AC4) |
  | `skills/init/SKILL.md` | step 3's opening sentence and its `- Mode:` paragraph, the `- Mode:` grammar at `:49`, the document-set bullet, and the upgrade rule at `:81` which today knows only `minimum`→`full` (AC5, AC6) |
  | `skills/spec/SKILL.md` | step 1's mode branch reads `full` and not-`full`; a declared `bootstrap` must have a defined reading rather than falling through prose that never names it (AC7) |
  | `scripts/check-skill-contracts.py` | `:75` pins the literal `` `- Mode: minimum` or `- Mode: full` on one physical line `` — the pin is part of the guard (G-8), so it moves with the sentence |
  | `scripts/test-gates.sh` | a standalone `init_tree` fixture modelling step 3's output — deliberately **not** derived from `docset_repo`, which would make it a model of the other fixture instead; the bootstrap cases |
  | `README.md`, `README.ja.md` | the mode vocabulary at `:106` / `:73`, and the `## Status` version. The JA is a mirror, claims identical (C-3) |
  | `plugin.json`, `.claude-plugin/plugin.json` | 0.8.0 (C-6) |

- **A seventeenth `check-skill-contracts.py` entry, argued** — its docstring caps the list at
  sixteen and requires the argument to be made here, because a check that grows to police every
  sentence makes prose uneditable, which rots worse than the drift it prevents. The entry is
  `skills/spec/SKILL.md`'s reading of `bootstrap`. What review cannot defend: step 1 branches on
  `full` versus not-`full` and has an explicit rule for the line being **absent** — a value it
  does not recognise falls through both, and falls through *silently*, so the model picks a
  reading and the user never learns a choice was made. Deleting the clause reads as removing a
  redundant case, since `bootstrap` is "obviously" minimum-like; what it removes is the only
  sentence that makes that obviousness written down. The existing sixteenth entry — the
  `- Mode:` needle — is **updated, not added**: this spec changes the literal it pins, and a
  pin left behind its sentence is a guard that passes on the absence it exists to catch (G-8).

- **Blast radius.** Three readers consume `- Mode:`: this checker, `skills/spec/SKILL.md`'s
  step 1, and `skills/contract/SKILL.md`'s "installed in `minimum` mode" sentence. The last is
  an example rather than a branch and stays correct. Nothing in `hooks/` reads the mode, by
  #110's AC5, so no gate branches on it and none can be weakened by a new value. Projects
  already on `minimum` or `full` are unaffected — no existing tree changes verdict.

- **What the review rounds settled**, recorded here rather than left in commit messages:
  - **Three outcomes at *both* levels.** The per-entry test is `os.stat`, deliberately not
    `Path.is_file()`, which delegates to `os.path.isfile` and swallows every `OSError`: the
    docstring's promise honoured for the outer directory and broken one level in, and
    interpreter-dependent besides, which is not a verdict at all.
  - **"Spec directory" follows symlinks.** `entry.is_dir()` over `follow_symlinks=False`,
    because the narrower reading produced a *fourth* outcome — an entry in neither list — in
    the fail-open direction. A dangling link is a definite ENOENT and stays green; a loop is an
    `OSError` and is `unreadable`.
  - **`ARCHIVE.is_dir()`'s swallow is safe by an invariant that lives in another function.**
    `_archive` is itself an entry of `.specs`, already classified with error-visible stats.
    Skipping it by name in that loop — the natural way to stop it being listed twice — would
    activate the swallow with nothing left to catch it.
  - **The remediation text is part of the guard.** The absent-`- Mode:` message offers all
    three values; naming only the two document sets sent a project with no documents to declare
    one it had not written, which is this issue's own defect spoken by the checker that closes
    it.
  - **`DOC_OWNER`** names the skill that writes each owed document, in both the success line
    and the expiry message — three documents owed without saying what writes them leaves the
    user to search the skill list.
  - **A skipped half-assertion is not a passed one.** `test-gates.sh` gained `note_skip`, and
    the summary now counts skips beside passes. **Thirteen** sites self-disable; the first
    cut converted ten of them and claimed seven, and two of the three it missed called `report`
    directly on the skip path — manufacturing a pass, in the environment the mechanism exists
    for. The recount that caught that then wrote down twelve and nine, in the paragraph whose
    subject is not counting; this is the third statement of the number and the first that was
    derived rather than recalled.

- **Armed but unexercised.** `init` step 3 arms two validators and this spec's fixture proves
  one. `check-steering-anchors.sh` needs a `.steering/product.md` with an `- Owns:` line, which
  `init_tree` does not write; extending the fixture to the whole armed set is worth doing and is
  not done here. That gap is the shape of this very issue one axis over, and it is stated rather
  than closed.

- **Why this cannot recur.** The class is *`init` arms a validator whose precondition `init`
  does not establish*, and it survived #110's review because nothing runs the checker against
  the tree `init` actually produces. The regression test is exactly that tree: a fixture
  holding the part of step 3's output this checker reads, asserted green. It fails today for
  the reason the issue names, and it fails again the next time a validator's requirements outgrow what
  step 3 writes. `check-skill-contracts.py`'s pin covers the second half — the vocabulary in
  `init`'s prose and the vocabulary in `MODES` cannot drift apart silently.

## 3. Tasks (TDD-ordered)
> One task is one complete Red-Green-Refactor cycle, so one green commit. No task is sequenced after the review.
- [x] T1: a fixture holding exactly what `init` step 3 creates — no `docs/`, no inception
      documents — asserted to exit 0, plus `bootstrap` rejected-when-documents-claimed and the
      `minimum`/`full` controls still failing; then `bootstrap` in `assets/check-document-set.py`
      (AC1, AC2, AC3).
- [x] T2: self-termination — a spec under `.specs/`, a spec under `.specs/_archive/`, and an
      unreadable `.specs/` as three distinct outcomes; then the scan (AC4).
- [x] T3: `skills/init/SKILL.md` — step 3's promise, the `- Mode:` grammar and the upgrade rule
      — and `skills/spec/SKILL.md`'s mode branch; the `- Mode:` pin moved to its new literal and
      the seventeenth pin added on the argument above (AC5, AC6, AC7).
- [x] T4: both READMEs' mode vocabulary and `## Status` version, the two manifests at 0.8.0;
      assert the full validator set green.
