# Epics

- Covers the capabilities in `docs/PRD.md`. The per-epic `- Serves:` lines below carry the citations; this line deliberately carries none, so a mechanical reader is not handed an elision to resolve.
- Status: draft — nothing cites these ids; see `docs/verified.md`.

Cut from the **remaining** work. Every capability in the PRD is already partly built, so these are not the epics that produced the product — they are what is left before each capability stops having a live falsifier. Where an epic closes a falsifier, the entry says which.

## Walking skeleton

**Already shipped, and no epic below is one.**

The thinnest end-to-end path through this system was the first spec carried through `implement`, the reviewer, and a merged pull request. It discovered the integration problems it exists to discover — that is what #1, #2, and #8 are — and it did so weeks ago. Nothing remaining is a skeleton: every epic below modifies a system that already runs end to end.

Recorded rather than designated, because marking one of these `yes` would mean using the field for "goes first" while the skill defines it as "discovers integration risk". Those are different claims, and only one of them is true here. See `docs/verified.md`.

If ordering is the question, it is `docs/BACKLOG.md`'s job, and EPIC-1 leads it.

## EPIC-1 — The gate cannot be stepped around

- Serves: CAP-1, CAP-7, CAP-3 — #25 is independence work, not only bypass work
- Demo: "Here are the four ways a change reached `main` without a fresh independent review. Watch each one fail."
- Walking skeleton: no
- Issues:
  - #26 — the review gate is silenced by `git checkout`, the one deliberate bypass
  - #36 — enforce at `git push` / `gh pr create` rather than at turn end
  - #25 — refuse a CLEAN verdict on a self-review
  - #35 — a review by ref records the working tree's sha, not the reviewed commit
- Depends on: nothing
- Not included: making the gate stricter about *what* it reviews. This epic is about the review being unavoidable, not about its contents. Widening the rulebook is CAP-3's work and belongs with `contract`.
- Closes the falsifier on: CAP-1, which is live — #26 records four bypasses in one week.

## EPIC-2 — No guard reports success it did not earn

- Serves: CAP-1, CAP-3 — #19 is what makes a rulebook pinnable at all
- Demo: "Here is a guard with nothing to check. It fails, and says it checked nothing."
- Walking skeleton: no
- Issues:
  - #39 — six guards can report success having checked nothing, and the suite cannot say "skipped"
  - #19 — `check-locks.py --update` cannot create a lock, so a new rulebook can never be pinned
- Depends on: nothing
- Not included: adding guards. This is about the ones that exist reporting honestly; a new check that fails open would be this epic's own falsifier.

## EPIC-3 — The shipped-path definition has one home

- Serves: CAP-2, CAP-5
- Demo: "Add a new reviewable file type in one place. Both gates and the version guard see it, and no second list needed editing."
- Walking skeleton: no
- Issues:
  - #14 — `Source globs` duplicates the shipped-path definition by hand, and the copy fails open
  - #18 — the review gate is unsatisfiable without a `Source globs` line
  - #49 — the reviewer's Bash allow-list names six validators; the `Validators:` line names eight
- Depends on: EPIC-2 — #18's fix is a fail-closed path, and #39 decides how a guard reports having nothing to check.
- Not included: making `.steering/tech.md` a general configuration format. Two consumers agreeing on one line is the goal; a schema for the file is the failure mode `init` warns about.

## EPIC-4 — Every claim the harness makes about itself is checked

- Serves: CAP-6, CAP-4 — #22 is the completeness of what `init` leaves behind
- Demo: "Change a number in a README. CI fails and names the file that disagrees."
- Walking skeleton: no
- Issues:
  - #55 — run `northstar`, `prd`, `epics` on this repo and record what was observed
  - #56 — run `contract` and `design-doc` against a live rulebook and structure.md
  - #54 — nine of thirteen skills carry no check at all
  - #22 — the mandatory document set is declared but never verified
  - #23 — rule C-2 enumerates the files that state a fact, so it goes stale
  - #48 — both READMEs claim a version six releases behind
  - #47 — all three `rules-lock.json` notes say "Grounding for ts-reviewer"
- Depends on: nothing, but #55 and #56 come first within it — they produce the observations the rest is specced from.
- Not included: verifying claims about *consumers*. This epic covers what the harness asserts about itself. Whether an installed project's documents are complete is #22's opt-out question and may not be checkable from here at all.
- Closes the falsifier on: CAP-6, which is live — two inception skills produce documents nothing reads, and this run is the evidence.
