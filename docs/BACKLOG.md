# Product backlog

- Last groomed: 2026-09-05 (fourth grooming — see **What changed** below)
- Ordered, not prioritized. Position reflects value, risk, cost, and dependency together. There is no separate priority field, and adding one would contradict this.

## A note on how this list was built

`backlog` expects to read epics and hand shaped items to `sprint`, which then creates the issues. For the first three groomings that is not what happened: every item already existed as a tracker issue, filed as it was discovered while using the harness on itself, and this document imposed an order on work that was already committed. That inversion is still true of most rows and is worth naming rather than hiding — the tracker was the plan for a week.

This grooming is the first with epics to read (`docs/EPICS.md`, from #55) and the first to carry rows that are not issues yet. Those rows are marked, and `sprint` decomposes them. The `Rough size` column estimates how many issues an item will turn out to need, which for several is more than the one that already exists.

## What changed at this grooming

- **Every inception document now exists.** `NORTH_STAR.md`, `PRD.md`, `EPICS.md` (#55), `CONTRACT.md`, `DESIGN.md` and six ADRs (#56). The "inception documents" item leaves Unshaped; the decision it was blocked on was taken by running the skills.
- **Shipped and closed since the last grooming:** #10, #28 (the fresh-session task), #34, #45, #49 (with #64), #52, #55, #56, #59, #61, #62, #64, #66.
- **Arrived:** #47, #48, #54 before the runs; #57, #58 from #55; #68 from #62; #69, #70, #71, #72 from #56. Seven of them postdate `epics` and belong to no epic, so their `Epic` cell is `—`; homing them is row 13.
- **#58 is this grooming**, in flight, and is not ordered.
- **The `Epic` column is new**, from the template; earlier groomings had no epics to cite.
- **#26 is displaced from first a third time, and this time by decision.** The skills were untested and the runs are finding a defect a day; the user chose to finish the test queue first. Its row says so.
- **#26 and #36 are one row.** Three groomings said whoever specs one must adopt, fold, or reject the other; a row that holds both makes that the first task rather than a note.

| # | Item | Epic | Blocks | Rough size | Why here |
| :-- | :-- | :-- | :-- | :-- | :-- |
| 1 | The remaining test-queue runs: `sprint` on this list, then `init` on a scratch clone of a real, unrelated project — *no issue yet* | — | row 2 | ~2 issues | In flight by decision, and the two runs most likely to change this list: `sprint` is the first thing that will ever read it, and `init` on a real toolchain is CAP-4's live test. Each run so far has filed three or four defects; the ones these find go above everything below. |
| 2 | The READMEs and steering say things that are false — **#48**, **#72**, **#47**, and the rows #56's reread found | EPIC-4 | — | ~3 issues | Waits on row 1 because it states what the runs proved. Above the gate work because the Status section is the sentence that sells the project's honesty, and it currently claims no reviewer has reviewed a real diff. |
| 3 | The gate is one command from off — **#26**, with **#36** as its candidate fix | EPIC-1 | row 6 | ~1–2 issues | The product's live falsifier, and displaced from first a third time — this time by decision: the runs above are cheap and finding defects daily. Whoever specs #26 adopts, folds, or rejects #36 in writing; that is why they are one row. |
| 4 | Guards that report success they did not earn — **#39** | EPIC-2 | rows 5, 7 | ~2–3 issues | Decides how a guard says "I checked nothing", which rows 5 and 7 both need before they can be specced. Above 5 for that reason alone. |
| 5 | A new rulebook can be pinned, and `--update` says what it did — **#19**, **#69** | EPIC-2 | — | ~2 issues | The reference implementation's own reviewer is unpinned (ADR-6), and every `contract` run tells consumers to run a command that prints success over an unpinned rulebook. A core claim false at home. Below 4 because its message half is 4's family. |
| 6 | The receipt says what was reviewed and by whom — **#35**, **#25** | EPIC-1 | — | ~2 issues | #35 can clear the gate on a review of different code, the fail-open direction; #25 makes independence required rather than available. Below 3 because a gate that can be stepped around enforces neither. |
| 7 | The shipped-path definition has one home — **#14**, **#18** | EPIC-3 | — | ~2 issues | #14 has fired for real once, on #34's branch. Below 4 because #18's fix is a fail-closed path whose shape 4 decides. |
| 8 | The skills have no vocabulary for a project that already has state — **#70**, **#71**, and the `northstar`/`prd`/`epics` equivalents #55 recorded without filing | — | row 9 | ~3 issues | Every consumer hits this on its second run. Cheap prose fixes with a version bump; above 9 because 9 pins skill sentences and should pin the corrected ones. |
| 9 | Nine skills carry no check — **#54** | EPIC-4 | — | ~1–2 issues | Now has the incident it was waiting for: `contract`'s re-pin sentence, observed in #56. After 8 so the needles pin text 8 has already changed. |
| 10 | Facts stated twice drift — **#23**, and `CONTRACT.md`'s index of the rulebook, which nothing compares | EPIC-4 | — | ~1–2 issues | Damages credibility, not behaviour, and every review round finds one. The `CONTRACT.md` half arrived with #56 and has no issue. |
| 11 | `check-leakage`'s `CAP-` pattern guards a form the repository does not use — **#57** | — | — | ~1 issue | An accusing pattern that misses the live form is the fail-open shape (G-9), but the identifiers it guards are not the ones now in the tree. Low likelihood, small fix, and its own issue says the obvious correction breaks CI. |
| 12 | Nothing proves a tag followed a bump — **#68** | — | — | ~1 issue | Happened once, to 0.4.0. Same family as 10; below it because the bump half is enforced and a consumer notices an untagged version within a day. |
| 13 | Re-run `epics` to home the issues filed since it ran — *no issue yet* | — | — | ~1 issue | Seven rows above carry `—`. Cheap, and it makes the next grooming's `Epic` column complete; below everything with a falsifier. |
| 14 | The mandatory document set is declared but never verified — **#22** | EPIC-4 | — | ~2–3 issues | Widest blast radius: it runs in every installed project. Last because its opt-out question is still unanswered — and, now that every document exists here, answerable by observation rather than argument. |

## Unshaped

Items that cannot be ordered yet because nobody knows what they are. This is a queue to empty, not a tier — anything sitting here is undecided work, and it does not get built while it stays here.

- **Running the eval suite** — four cases authored, never executed. As of 2026-09-05 `claude plugin eval` renders its full help and then any invocation prints "in early access" and exits 0, running nothing. **Blocked on:** access. It matters more with every skill run, since the harness's own claims about skill behaviour are presence-checked only.
- **Antigravity has no `SessionStart`** — the steering digest has no equivalent, and `PreInvocation` is the candidate substitute but needs a once-per-session guard. **Blocked on:** whether the guard is achievable at all, which nobody has tried.

## What would change this order

- **`sprint` finding nothing to decompose at the top.** Rows 1 and 13 are the only ones that are not already issues. If `sprint`'s run shows the top of this list is a tracker query rather than a plan, the inversion has not been undone and rows should be coarser.
- **`init` blocking a first turn on the scratch clone.** That is CAP-4's falsifier, and it would move whatever it finds to row 1.
- **#36 turning out to be the right fix for #26.** Then row 3 is one issue and the pair stays one row.
- **Anyone other than the author using this.** Every item was found by dogfooding, which finds what the author's own habits reach.

### Triggers that have already fired

- **2026-08-25 — "#34's fix revealing other unparsed anchors."** Fired sideways. No other anchor was unparsed, but the fix revealed that the new guard itself was outside `Source globs` — the *shipped-path* definition drifting rather than the *anchor* one. #14 moved in evidence rather than in position; see its row.

- **2026-08-25 — "#27 turning out to be a harness limitation rather than a plugin bug."** Fired, and the order held. #27's spec conceded that a blocking `Stop` hook cannot coexist with an async subagent; the review of that spec then established the concession was wrong. A turn *can* wait by staying open (`docs/verified.md`), so #27 was a plugin bug after all and was fixed as one. The trigger's own consequence — that `git checkout` is the only escape — was retracted with it; it is the only *bypass*, never the only *exit*.

- **2026-09-05 — "The inception documents" leaving Unshaped.** It was blocked on a decision, not information. The decision was to run the skills and record what they did (#55, #56), and every document now exists. What it found is rows 5, 8 and 10.
