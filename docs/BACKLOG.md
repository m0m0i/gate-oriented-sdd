# Product backlog

- Last groomed: 2026-08-25 (second grooming — see **What changed** below)
- Ordered, not prioritized. Position reflects value, risk, cost, and dependency together.
  There is no separate priority field, and adding one would contradict this.

## A note on how this list was built

`backlog` expects to read epics and hand shaped items to `sprint`, which then creates the
issues. That is not what happened. Every item below already exists as a tracker issue, filed
as it was discovered while using the harness on itself, so this document imposes an order on
work that was already committed. The inversion is worth naming rather than hiding: it means
the tracker was the plan for a week.

The `Rough size` column therefore estimates how many issues each item will *turn out* to
need, which for several is more than the one that already exists.

There are still no epics. `epics` has never run, and `docs/` holds none of the inception
documents except this one — see #22, itself on this list.

## What changed at this grooming

- **#27 shipped and is closed.** It was item 1. Its fix — teaching `implement` how to wait —
  is what makes the top of this list movable at all.
- **Three issues arrived** while #27 was in flight: #34, #35, #36, all found by doing the work
  rather than by looking for work.
- **#26 moves to the top and its reason changed.** It was second because it was "the only
  escape from #27". That rationale died twice over: the premise behind it was retracted, and
  #27 is now closed. It leads on its own merits instead.
- **#34 goes above it.** Reasoning in the table.

| # | Item | Blocks | Rough size | Why here |
| :-- | :-- | :-- | :-- | :-- |
| 1 | **#34** — nothing checks that steering's machine-read anchors parse; this repo's `Owns` line never has | — | ~1 issue | Above #2 because it is **already happening and requires nobody to do anything wrong.** The quality anchor every reviewer severity is judged against has never loaded into the digest, since bolding the line defeated the `sed`. It only stayed invisible here because `init` wrote the anchor into the reviewer file too; a project without that duplication has a reviewer working from taste. The general fix guards the four other lines the gates read — `Validators`, `Reviewer`, `Source globs`, `Docs` — so it protects the inputs of everything below it. |
| 2 | **#26** — the gate is silenced by `git checkout` | #25 | ~1–2 issues | The only *deliberate* bypass of the only enforced rule, and silent: a skipped review and a clean repo produce identical output. Below #1 because it takes an act — someone must type the command — whereas #1 fails on its own. Its old reason for being second ("the only escape from #27") is retracted and #27 is closed, so it now leads on merit. Used four times in one session, disclosed each time, which is the evidence for how reachable it is. |
| 3 | **#36** — enforce at `git push` / `gh pr create` rather than at turn end | — | ~1 issue, or 0 | **Adjacent to #2 on purpose: it may be #2's answer rather than a separate item.** It enforces the promise the harness actually makes — "no PR without a clean review" — and cannot loop, since it fires at a boundary crossed deliberately. Whoever specs #26 must decide whether to adopt it, fold it in, or reject it in writing. Ordering it separately keeps that decision visible instead of buried. |
| 4 | **#35** — a review conducted by ref produces a `reviewed_sha` of the working tree | — | ~1 issue | Can clear the gate on a review of *different code*, which is the fail-open direction on the enforced rule. It sits at 4 rather than 2 because **#27 shipping made it rarer**: reviewing by ref existed because the deadlock forced a parked working tree, and that reason is gone. A real hazard whose likelihood the previous item just reduced. |
| 5 | **#25** — the gate should refuse CLEAN on a self-review | — | ~1 issue | Independence is what the judgment layer is sold on, and the gate still clears `reviewed_by=inline`. Its prerequisite shipped with #9. Below #2 because enforcing independence through a gate that can be stepped around enforces nothing — the order between these two is the one real dependency in the top half. |
| 6 | **#19** — `--update` cannot create a lock, so a new rulebook can never be pinned | — | ~1 issue | `AGENTS.md` names the hash-pinned rulebook as one of the two ideas this repo exists for, and the dogfooded instance ships **unpinned** with a three-place explanation. A core claim is false in the reference implementation. Above #7 because it is a broken promise rather than a latent hazard. |
| 7 | **#28** — a strippable `assert` guards the path that keeps a check from checking nothing | — | ~1 issue | Five lines, replacement supplied verbatim by the reviewer that found it. Unreachable today — nothing runs with `-O` — which is the only reason it is not higher, because the shape is #16's exactly. Cheap enough that it should not be allowed to age. |
| 8 | **#14** — `Source globs` duplicates the shipped-path definition by hand | #18 | ~2 issues | A decision before it is a change: how many places define "what is shipped", and which is authoritative. It also answers two questions with opposite right answers for the manifests. Above #9 because whatever is decided here determines what #9's fix should look like. |
| 9 | **#18** — the review gate is unsatisfiable without a `Source globs` line | — | ~1 issue | The fallback is `globs='*'`, so committing the receipt invalidates the receipt, forever. Real impact on any partial install, and it fails *closed* — a loud failure can wait behind the decision that shapes its fix. |
| 10 | **#23** — rule C-2 enumerates the files that state a fact, so it goes stale | — | ~1–2 issues | Bitten repeatedly, most recently three times inside #27's own review rounds. Below #9 because it damages credibility rather than behaviour: no gate fails open, a number is merely untrue. |
| 11 | **#10** — "one task, one commit" contradicts the quality gate | — | ~1 issue | A spec is written and merged, so it is the cheapest here to start. Eleventh anyway because the decision was made a week ago and every spec since folds red and green into one task — documentation catching up to practice. |
| 12 | **#22** — the mandatory document set is declared but never verified | — | ~2–3 issues | Widest blast radius on the list: it would run in every project the harness installs into, including ones mid-setup, and a guard that fires on a considered choice gets deleted. Its central question — what the opt-out is — is unanswered. Last because it needs a decision this repo has not made, not because it is unimportant. |

## Unshaped

Items that cannot be ordered yet because nobody knows what they are. This is a queue to
empty, not a tier — anything sitting here is undecided work, and it does not get built while
it stays here.

- **The inception documents** — `PRD.md`, `DESIGN.md`, `NORTH_STAR.md`, `EPICS.md`,
  `CONTRACT.md`. `init` calls three of them mandatory and this repo has one: this file. Every
  one of their *mechanical* outputs already exists — and #34 is the discovery that one of
  them, the `Owns` anchor, has never actually been read. **Blocked on:** a decision, not
  information. #34 may change the answer, since it makes the case that these outputs are load
  bearing rather than ceremonial.
- **Running the eval suite** — four suites authored, never executed, because
  `claude plugin eval` is early access and was not enabled on this account. **Blocked on:**
  access. Until then nobody knows whether the suites are green, red, or malformed. This
  matters more after #27, whose central acceptance criterion is presence-checked only and
  which an eval is the only thing that could really verify.
- **Antigravity has no `SessionStart`** — the steering digest has no equivalent, and
  `PreInvocation` is the candidate substitute but needs a once-per-session guard.
  **Blocked on:** whether the guard is achievable at all, which nobody has tried.

## What would change this order

- **#36 turning out to be the right fix for #26.** Then they are one item, not two, and
  everything below shifts up one.
- **#34's fix revealing other unparsed anchors.** If `Validators` or `Source globs` is also
  silently absent in some project shape, the gates below it have been running on defaults and
  several items change meaning.
- **Anyone other than the author using this.** Every item on this list was found by
  dogfooding, which finds what the author's own habits reach. A second user would reorder it
  within a day, and that is an argument for shipping before polishing.

### Triggers that have already fired

- **2026-08-25 — "#27 turning out to be a harness limitation rather than a plugin bug."**
  Fired, and the order held. #27's spec conceded that a blocking `Stop` hook cannot coexist
  with an async subagent; the review of that spec then established the concession was wrong.
  A turn *can* wait by staying open (`docs/verified.md`), so #27 was a plugin bug after all
  and was fixed as one. The trigger's own consequence — that `git checkout` is the only escape
  — was retracted with it; it is the only *bypass*, never the only *exit*.
