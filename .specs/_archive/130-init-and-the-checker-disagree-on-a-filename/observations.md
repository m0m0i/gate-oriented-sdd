# Observations — 130-init-and-the-checker-disagree-on-a-filename

Four reviewer rounds, no BLOCKER and no HIGH at any point. What makes this spec worth reading back
is that **every MEDIUM after round 1 was damage the fix did to the bullet it was fixing** — the
same defect class as #130 itself, reproduced three times by the person who had just written it
down.

## Round 1 — CLEAN, 3 MEDIUM

**Copy-then-absorb.** The bullet opened *"copy `feature.md`, `bug.md`, `chore.md`…"* and narrowed
to *"If templates already exist…"* three sentences later. Executed in reading order, the plugin's
`bug.md` lands first, `bug_report.md` stops looking like a type with no template, and the rename
has an occupied destination — **#130 reproduced, with `check-document-set.py` green**. The ordering
had been harmless while the merge rule was additive; a rename made the destination contendable, so
the order became load-bearing in the same diff that introduced it.

**The consent rule did not reach the rename.** Step 3's Rules line named `.steering/`, `.specs/`
and `AGENTS.md`, and its verb was *overwrite*. Neither reaches `.github/ISSUE_TEMPLATE/`, and
neither reaches a rename. So the safeguard for the one genuinely destructive act `init` now
performs lived in a single unpinned sentence — while the pin sat on the destructive half. The
reviewer was also right that the spec's Clarification **overstated the licence**: it claimed step
3's rules "already say" this. They did not. That Clarification is left unrewritten, because it is
the record of what was argued at the time; the safeguard no longer depends on it.

**The bump landed as a task.** `.steering/tech.md:21` already settles this — a version bump is a
*step* of `implement`, not a task, which is #113 — and two consecutive specs broke it (#127's T4,
this spec's T3). `check-templates.py` catches deferral *phrasing*, not a task that simply is the
bump. Left as it landed and filed as **#136**, framed as *either* extend the check *or* revisit
#113, because **C-6** pulls the other way and adding a check to a rule nobody has reconciled is how
a guard ends up certifying a decision that was never made.

## Round 2 — CLEAN, 4 MEDIUM, all mine

The reorder that fixed round 1 broke four things:

- **`bug.md` fell out of the copy list.** Naming only `feature.md` and `chore.md` left the fresh
  install — the majority path — reaching `bug.md` through *"any other still-absent type"*.
- **"Adapt labels to the ones this project already uses" was stranded.** It had been a modifier on
  the copy clause; the reorder made it a standalone imperative at the top of the bullet, governing
  the absorbed template too and contradicting *"keeping its labels exactly as they are"* four
  sentences later. A model following it rewrites `labels: defect, needs-triage` to the plugin's —
  the precise loss AC4 forbids, invisible to every check.
- **`config.yml` against the rule just widened.** It lives in `.github/ISSUE_TEMPLATE/`, so the new
  Rules line covered it while the bullet still copied it unconditionally over a project's own,
  `contact_links:` and all.
- **The pin covered the rename but not the order** — and the order is the half that closes AC5.
  Swapping it back left the needle intact and every check green.

## Round 3 — CLEAN, 2 LOW, "ship it"

**A rename onto itself.** *"for each of the three types the project already has a template for"*
was unconditional on whether the file was already canonical, so a project holding `feature.md` and
`bug_report.md` got `git mv feature.md feature.md` — `fatal: destination exists`, mid-install.
Re-running `init` is the documented upgrade path, so this is the case a user hits **second**. Taken
despite the ship-it, because an abort is not a wording nit.

## Round 4 — APPROVE, nothing at LOW or above

The reviewer verified mechanically that the new qualifier sits outside the pinned needle, traced
all three inputs again, and confirmed the degenerate re-run — all three already canonical — now
issues no `git mv` and copies nothing. **`init` is idempotent on templates, which it was not two
commits earlier.**

## What this spec should be remembered for

The fix was right at round 1 and correct at round 4. Everything between was **the fix damaging its
own artifact**, in exactly the way the bug it closed had damaged that artifact originally: two
instructions in one bullet, disagreeing, with nothing reading both.

The reorder is the sharpest instance. Moving a sentence is the cheapest-looking edit in prose, and
it silently re-scoped a modifier onto a clause that contradicts it. Nothing mechanical could see
that, and nothing mechanical can see it now — which is the honest limit of what this spec bought.

The pin is the partial answer. It holds the rename **and** the order after round 2 widened it, and
the widening was mutation-tested rather than asserted: swapping the order back with the rename left
intact reddens the suite. What the pin cannot hold is the whole bullet, and the docstring's cap
says it should not try.

## What review never saw, and what remains uncovered

- **Three validators were never run against this tree**, in all four rounds — including
  `assets/check-document-set.py`, the file this branch changes. Their logic is exercised by
  `test-gates.sh` against fixtures, which is not the same. That is **#131**, unchanged and unfixed,
  and it has now been true for two consecutive specs about that same file.
- **AC2's red is partial.** `says-remedy` and the contracts mutation fail before the fix; the other
  six assertions in case 70 pass against `main` too, because the checker's verdict logic never
  moved. The case comment says so; the reviewer recorded it rather than letting the receipt imply
  wider coverage.
- **The self-rename qualifier is itself unpinned.** Deleting it leaves the needle intact and the
  re-run path aborting again. Recorded as a known gap rather than an assumed cover — widening the
  needle again would force a fixture change and reopen the pin's argument against a docstring that
  says to keep the list short, and the failure is a loud `fatal:` rather than a gate exiting 0.
- **AC5 has no mechanical enforcement at all.** "One template per type" is prose, held by a presence
  pin, and a presence pin asserts a sentence is *written*, not *followed*. Only an eval closes that,
  and `evals/` cannot yet.
- **`.steering/structure.md`'s stale count** was fixed here, outside scope and labelled as such —
  but nothing stops the next one. `check-readme-claims.py` guards that claim class across two files
  and the claim lives in more. Filed as **#137**.
