# Observations — sprint

Notes taken as the skill ran on 2026-09-05, verbatim, with the tracker state before and after. `docs/verified.md`'s section is written from these in T2.

## sprint run — 2026-09-05, gate-sdd 0.4.2, Claude Code 2.1.252 (notes for #77)

- Tracker before: 20 open (14 18 19 22 23 25 26 35 36 39 47 48 54 57 68 69 70 71 72 74). After: 23 — #76, #77, #78 created. Milestone #1 "Iteration 1 — the test queue" with #76 #77 #78 #48 #72 #47.
- Entry: sprint has no issue and the spec skill says no issue, no spec. The user chose to run sprint directly, as the skill's own model (issues come from sprint). Iteration = rows 1 and 2, by the user; row 13 left out because taking it skips rows 3–12.
- Step 1, take from the top: row 1 IS the sprint run (and the init run). Sprint decomposed its own row: "record this run" (#77) + "init on a scratch clone" (#76). Self-reference; the skill has no sentence for it, and nothing broke.
- Step 2, decomposition: row 1 (~2 issues) → 2 new. Row 2 (~3 issues) → 3 existing (#48, #72, #47) re-scoped by comment + 1 new (#78). Row 2's existing issues were already one-PR sized, so "decomposition" there was scoping, not splitting. The red flag "title matches the backlog item" did not fire because the rows were coarse.
- Step 3, types: all three chores → label `task`. The label vocabulary (task/enhancement/bug) differs from the type vocabulary (chore/feature/bug); the mapping lives only in each template's `labels:` line, and the spec skill reads the label and has mapped task→chore by convention on #55/#56/#58 without any sentence stating it.
- Templates: `.github/ISSUE_TEMPLATE/*.md` exist here. `gh issue create` cannot apply a template's body non-interactively together with `--body-file`; the shape was reproduced by hand from chore.md (headings verbatim, trailing italic line). A consumer running sprint from a CLI does the same or gets an untemplated body.
- Red flag inverted: "every issue is a feature" → every issue is a chore, because the iteration is observation work. Not a defect; recorded.
- Step 5, left out: row 13 (epics re-run — skipping down the list); the README-version guard #48 raises (belongs with #23, row 10); rows 3–12. Row 3 (#26) displaced again, by the grooming's decision, not by selection here.
- Step 6, milestone: GitHub has no sprint container; a milestone created via the API, with a description saying it is a grouping label only. `gh issue edit --milestone` works per issue; no bulk form.
- Not exercised: a backlog item that decomposes into different types (feature + chore); "take from the top" against an author who wants a lower row; unplanned-work labelling mid-iteration.
- Consequence: docs/BACKLOG.md row 1 now says "no issue yet" for work that has issues #76 and #77, and row 2 omits #78. The next grooming corrects both; the backlog is not edited by sprint (it writes no file), so the file is stale by construction the moment sprint runs — the same shape as #58's preamble after #55. Candidate issue for the backlog/sprint seam.

## T3 — after the record

AC3: the diff is confined to `docs/verified.md` and this directory; nine validators at exit 0, `test-gates.sh` 54/0. AC4: filed #79 — `sprint` makes the backlog stale the moment it runs, and neither skill says who corrects it. Open issues now 24.
