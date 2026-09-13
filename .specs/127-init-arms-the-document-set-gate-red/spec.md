# Spec: init arms the document-set gate red on a fresh install
- Slug: 127-init-arms-the-document-set-gate-red   Issue: 127   Type: bug   Status: draft
- Author: Claude Opus 5   Date: 2026-09-13

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
  - [ ] **AC1:** WHEN `init` completes on a project with no inception documents THEN every
        validator it placed on the `- Validators:` line exits 0 on the resulting tree,
        `check-document-set.py` included.
  - [ ] **AC2:** the regression test fails before the fix and passes after.
  - [ ] **AC3:** WHEN the document set is genuinely incomplete in a state that claims the
        documents exist THEN `check-document-set.py` still exits non-zero — the fix narrows
        what is claimed, and narrows it in a declared state, never by tolerating absence in the
        states that exist today.
  - [ ] **AC4:** the state in which documents are not required is **self-terminating**: it
        stops passing once the project starts building against documents it never wrote, so it
        cannot become a permanent switch-off.
  - [ ] **AC5:** whatever `init` writes, no inception document contains a `TODO` placeholder —
        `skills/init/SKILL.md` step 3's closing rule, and its reason (an unpopulated document
        teaches that documents are noise) applies past `.steering/`.
  - [ ] **AC6:** `init`'s own text no longer promises what it does not do: step 3's *"Scaffold
        the mandatory set"* and its bullet list agree about the inception documents.
  - [ ] **AC7:** every reader of `- Mode:` has a defined reading for the new value. A declared
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
  | `scripts/test-gates.sh` | `docset_repo` gains a no-documents variant; the bootstrap cases |
  | `README.md`, `README.ja.md` | the mode vocabulary at `:106` / `:73`, and the `## Status` version. The JA is a mirror, claims identical (C-3) |
  | `plugin.json`, `.claude-plugin/plugin.json` | 0.8.0 (C-6) |

- **Blast radius.** Three readers consume `- Mode:`: this checker, `skills/spec/SKILL.md`'s
  step 1, and `skills/contract/SKILL.md`'s "installed in `minimum` mode" sentence. The last is
  an example rather than a branch and stays correct. Nothing in `hooks/` reads the mode, by
  #110's AC5, so no gate branches on it and none can be weakened by a new value. Projects
  already on `minimum` or `full` are unaffected — no existing tree changes verdict.

- **Why this cannot recur.** The class is *`init` arms a validator whose precondition `init`
  does not establish*, and it survived #110's review because nothing runs the checker against
  the tree `init` actually produces. The regression test is exactly that tree: a fixture built
  to hold what step 3 creates and nothing else, asserted green. It fails today for the reason
  the issue names, and it fails again the next time a validator's requirements outgrow what
  step 3 writes. `check-skill-contracts.py`'s pin covers the second half — the vocabulary in
  `init`'s prose and the vocabulary in `MODES` cannot drift apart silently.

## 3. Tasks (TDD-ordered)
> One task is one complete Red-Green-Refactor cycle, so one green commit. No task is sequenced after the review.
- [ ] T1: a fixture holding exactly what `init` step 3 creates — no `docs/`, no inception
      documents — asserted to exit 0, plus `bootstrap` rejected-when-documents-claimed and the
      `minimum`/`full` controls still failing; then `bootstrap` in `assets/check-document-set.py`
      (AC1, AC2, AC3).
- [ ] T2: self-termination — a spec under `.specs/`, a spec under `.specs/_archive/`, and an
      unreadable `.specs/` as three distinct outcomes; then the scan (AC4).
- [ ] T3: `skills/init/SKILL.md` — step 3's promise, the `- Mode:` grammar, the document-set
      bullet and the upgrade rule — and `skills/spec/SKILL.md`'s mode branch, each pinned by its
      `check-skill-contracts.py` entry (AC5, AC6, AC7).
- [ ] T4: both READMEs' mode vocabulary and `## Status` version, the two manifests at 0.8.0;
      assert the full validator set green.
