# Spec: Run northstar, prd, and epics on this repo and record what was observed

- Slug: 55-run-northstar-prd-epics Issue: 55 Type: chore Status: approved
- Author: m0m0i Date: 2026-08-29

## 1. Requirements (WHAT / WHY)

- What changes: run `northstar`, then `prd`, then `epics` against this repository, in that
  order, keeping `docs/NORTH_STAR.md`, `docs/PRD.md`, and `docs/EPICS.md`, plus a section in
  `docs/verified.md` recording what was **observed** at each handoff. The documents are the
  by-product; the observations are the deliverable.

- **What must NOT change:**
  - `- Owns: gates never fail open` in `.steering/product.md`, verbatim. `northstar` step 6
    writes that line and it is already there, so this run observes whether the skill preserves,
    merges, or clobbers an existing value. It is the anchor every reviewer severity is judged
    against; see #34 for what its absence costs.
  - Every gate and guard. `./scripts/test-gates.sh` at 52/0 and all eight `- Validators:`
    commands exiting 0, before and after.
  - `docs/BACKLOG.md`, byte-identical. `backlog` is not in this issue, and re-grooming a
    curated ordering is a deliberate act rather than a side effect of a verification run.
  - `.steering/tech.md` and `.steering/structure.md`, byte-identical. `.steering/product.md`
    is **no longer** on this list as a whole file — see clarification 4 — but its `- Owns:`
    line still is, and that is the constraint AC2 enforces.
  - Every shipped path: `skills/`, `agents/`, `hooks/`, `assets/`. This spec authors documents
    and records observations. A defect found mid-run gets an issue, not a fix — a fixed chain
    is no longer the shipped chain, and the run stops describing what a consumer would get.

- Why now: three open issues are waiting on evidence only a real run produces. #54 requires each
  new skill contract to cite the consumer that breaks and the failure it reproduces, and
  `northstar`, `prd`, `epics` are three of its nine uncovered skills — specced from prose alone
  it would invent needles, which its own AC2 forbids. #48 cannot be closed honestly until the
  version matrix has been re-run. #22's evidence section says this repo has none of the
  mandatory documents, and that is still true.

- Acceptance criteria:
  - [ ] **AC1:** THE SYSTEM SHALL behave identically for every gate and guard — `test-gates.sh`
        reporting 52 passed / 0 failed and all eight validators exiting 0 — demonstrated by running
        both before the first skill and after the last, with both results recorded.
  - [ ] **AC2:** WHEN `northstar` completes THE SYSTEM SHALL still carry `- Owns: gates never
fail open` verbatim in `.steering/product.md`, and `./assets/check-steering-anchors.sh`
        SHALL resolve 5 of 5 anchors with none unreadable.
  - [ ] **AC3:** WHEN `northstar` completes THE SYSTEM SHALL have written `docs/NORTH_STAR.md`
        in which every lever carries a stable id.
  - [ ] **AC4:** WHEN `prd` completes THE SYSTEM SHALL have written `docs/PRD.md` carrying
        `Status: draft`, in which every capability names a lever id that appears verbatim in
        `docs/NORTH_STAR.md`, demonstrated by grep with the matched count recorded — not by reading.
  - [ ] **AC4b:** THE SYSTEM SHALL record in `docs/verified.md` that no mechanical consumer of
        `PRD.md` or `EPICS.md` exists in this repo today, and that nothing is required to cite the
        capability ids. `.steering/product.md` says this project is not a document generator; a run
        that produces two documents nothing consumes must say so rather than let the gap pass as
        normal. This is #22's argument, restated from observation.
  - [ ] **AC5:** WHEN `epics` completes THE SYSTEM SHALL have written `docs/EPICS.md` in which
        every `- Serves:` id appears verbatim in `docs/PRD.md`, every epic carries a `Demo:`
        sentence, and **either** exactly one epic is `Walking skeleton: yes` **or**
        `docs/EPICS.md` records an explicit reason none applies. _Amended 2026-08-30 — see
        clarification 5._
  - [ ] **AC6:** WHEN an id prefix is chosen at `northstar` step 2 THE SYSTEM SHALL be observed
        to either carry it through `prd` and `epics` or not, and the answer recorded either way.
        The prefix SHALL be one that could not be guessed from the domain, so that a match cannot
        be coincidence.
  - [ ] **AC7:** WHEN the run completes THE SYSTEM SHALL have a `docs/verified.md` section
        recording, per handoff, what was observed — **including any seam that did not join.** A run
        reporting only successes has not been recorded honestly; that file's own account of the row
        written before it was observed is the standard.
  - [ ] **AC8:** WHEN the run completes `git diff --stat main` SHALL show changes confined to
        `docs/`, `.specs/55-run-northstar-prd-epics/`, and `.steering/product.md`, with
        `docs/BACKLOG.md` unchanged. _Amended 2026-08-29 — see clarification 4._

- Out of scope:
  - `contract` and `design-doc` — #56. They write state the gates already read, which is a
    different blast radius and a separate review.
  - `backlog`, `sprint`, and `init`. `init` is a migration here rather than a cold start, so it
    cannot exercise detection or the interview; `sprint` would create real issues in a tracker
    that already has fifteen open; `backlog` would clobber a curated document.
  - Probe P1 from the run sheet — a non-default `- Docs:` path. `Docs: docs/` is live in this
    repo and changing it to probe a default would be vandalism. It belongs on a throwaway.
  - Fixing anything the run finds, and building the guard #22 asks for.

### Clarifications

Resolved 2026-08-29.

1. **Q: `.steering/product.md` says this project is not a document generator — every skill must
   terminate in something the harness mechanically uses. `northstar` terminates in `- Owns:`,
   which already exists, but `prd` and `epics` would terminate in documents nothing consumes.
   What status do the three documents get?**
   **A: Keep them, marked provisional.** `PRD.md` carries `Status: draft` and nothing is required
   to cite its capability ids yet; `verified.md` records plainly that no mechanical consumer
   exists (AC4b). Discarding them would destroy the artifacts AC4 and AC5 are checked against;
   marking them agreed would make a product commitment a side effect of a verification run.

2. **Q: The skills ask for genuine product judgment — the metric, the non-negotiable, the
   capability boundary. Who answers?**
   **A: Proposed from the repo, corrected by the author at each of the three skill boundaries.**
   Drafts come from `README.md`, `.steering/product.md`, `docs/BACKLOG.md` and the issue history;
   the author accepts or corrects before the next skill runs. This mirrors `init` step 2, which
   asks with a recommended answer attached.
   _Recorded limitation:_ this run therefore does **not** test the cold interview. A consumer
   with no repo context gets a different experience, and that variant is still unobserved — it
   belongs with `init` on a throwaway repo.

3. **Q: If `northstar` step 5 derives an `Owns:` line different from "gates never fail open",
   what happens?**
   **A: Record it as a finding and keep the existing line.** `Owns:` is cited in merged review
   receipts and `.steering/product.md` carries a paragraph of rationale for the current value.
   Changing it would turn a verification run into a steering change with a far wider blast
   radius. AC2 stands as written.

4. **Q: `prd` step 7 says "register the ids … and summarise into `.steering/product.md`", which
   AC8 as originally written forbids. Amend, or scope the step out?**
   **A: Amend AC8 to permit `.steering/product.md`, and run step 7 as written.** Raised at the
   start of T3, before `prd` ran.
   The conflict is a scoping error in #55 itself, not in the skill: this issue was split from #56
   on the premise that #55 touches no state the gates read, and `prd` step 7 does. The split
   missed it.
   Amending rather than skipping, for a reason beyond fidelity: `.steering/product.md` is
   hand-authored today — "Who uses it", "What it deliberately is not", "The claim that has to stay
   true" — so a PRD summary must either merge with that prose or replace it. **That is the same
   preserve-merge-clobber seam T2 set out to observe and could not**, because `northstar`'s
   derivation agreed with the existing `Owns:` value. Step 7 is a second chance at it on a
   different file, and skipping it would leave two of this run's three skills with an unexercised
   seam.
   Guarded by: AC2 is unchanged, so `- Owns:` must stay byte-identical;
   `check-steering-anchors.sh` must still resolve 5 of 5; and T1 recorded the file's checksum, so
   the before-state is recoverable.

5. **Q: `epics` rule 6 requires a walking skeleton — "the thinnest end-to-end path through the
   whole system", which "goes first, always, because it is the only thing that discovers
   integration problems while they are still cheap." This system already runs end to end. AC5
   requires exactly one epic marked `yes`.**
   **A: Record it as already shipped and amend AC5** to accept an explicit recorded reason in
   place of a designation. Raised at the start of T4, before `epics` ran.
   Marking an epic `yes` that discovers no integration problems would fill a precisely defined
   field with a different meaning to satisfy a checkbox — the same failure #54's AC2 forbids one
   layer up, and the reason this run does not simply pass.
   The finding is structural rather than a missing sentence: **`epics` has no vocabulary for a
   product that already ships.** Its rule 6, its red flag "No epic is the walking skeleton", and
   its `Walking skeleton: yes | no` field all assume greenfield, and a mature project running the
   skill is pushed toward a false designation with nothing to warn it.

## 2. Design (HOW)

- **Approach.** Nothing here is code. The run is an experiment, and the design is the protocol
  that keeps it one: a recorded baseline, three skills executed in dependency order without
  intervention, a grep-verified assertion after each, and a re-verified baseline at the end.
  The documents are evidence; the `verified.md` section is the result.

- **Order of operations, and it must land in this order.** `prd` step 1 reads `northstar`, and
  `epics` step 1 reads the PRD. Running them out of order tests nothing, because each seam only
  exists if the upstream document was there first.

- **No intervention mid-run.** A defect found is recorded and the run continues. Fixing one
  changes what the next skill reads, and the run stops describing the chain a consumer gets.
  Anything found becomes an issue, filed after the run.

- **The id prefix.** `LV-` for levers, chosen because it appears nowhere in this repository —
  `grep -r 'LV-' .` returns nothing today, so any later match is causal rather than coincidence.
  This is AC6's mechanism.

- **Affected files.** `docs/NORTH_STAR.md`, `docs/PRD.md`, `docs/EPICS.md` (new);
  `docs/verified.md` (new section, existing content untouched);
  `.specs/55-run-northstar-prd-epics/spec.md`. Nothing else.

- **Coverage gap.** Real, and it is the reason T1 exists. The gates are covered by 52 cases and
  the guards by their own validators, but **nothing asserts that a documentation run left
  steering, the shipped paths, and `BACKLOG.md` alone.** That is precisely AC1, AC2 and AC8, and
  today it is an assertion rather than an observation. T1 turns it into one by capturing the
  baseline — suite counts, validator exit codes, the `Owns:` line, and a `BACKLOG.md` checksum —
  _before_ the first skill runs. Without that capture, "nothing broke" at the end is a claim with
  no before-value to compare against.
  It stays a manual protocol rather than a new script: `scripts/` is out of scope for this spec,
  and a guard for this belongs with #22, which is about exactly that question.

- **Rollback.** `git checkout main` and delete the branch. Every artifact is additive and
  confined to `docs/` and `.specs/`; nothing reads the three new documents, which is itself the
  observation AC4b records.

## 3. Tasks (TDD-ordered)

> One task is one complete Red-Green-Refactor cycle, so one green commit.

- [x] T1: capture the baseline and confirm it green — `./scripts/test-gates.sh`, all eight
      `- Validators:` commands, the `- Owns:` line, and a `sha256` of `docs/BACKLOG.md` — recorded
      verbatim into the branch. This is the before-value AC1, AC2 and AC8 are compared against,
      and without it they cannot be observed.
- [x] T2: run `northstar`; assert AC2 and AC3 — anchors resolve 5 of 5, `- Owns:` byte-identical,
      `docs/NORTH_STAR.md` written with `LV-` lever ids — and record what the skill did on finding
      an `Owns:` value already present.
- [x] T3: run `prd`; assert AC4 and AC4b — `docs/PRD.md` at `Status: draft`, every capability's
      lever id grep-matched in `NORTH_STAR.md` with the count recorded, and the absence of any
      mechanical consumer noted.
- [x] T4: run `epics`; assert AC5 — every `- Serves:` id grep-matched in `PRD.md`, every epic
      carrying a `Demo:`, exactly one `Walking skeleton: yes`.
- [x] T5: write the `docs/verified.md` section from the recorded observations, satisfying AC6 and
      AC7 — including every seam that did not join, and the `LV-` prefix outcome either way.
- [x] T6: re-run the baseline and assert AC1 and AC8 — suite and validators matching T1's
      recorded values, `BACKLOG.md` checksum unchanged, `git diff --stat main` confined to `docs/`
      and `.specs/55-run-northstar-prd-epics/`.
