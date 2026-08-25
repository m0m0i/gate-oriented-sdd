# Product backlog

- Last groomed: 2026-08-25
- Ordered, not prioritized. Position reflects value, risk, cost, and dependency together.
  There is no separate priority field, and adding one would contradict this.

## A note on how this list was built

`backlog` expects to read epics and hand shaped items to `sprint`, which then creates the
issues. That is not what happened here. Every item below **already exists as a tracker
issue**, filed as it was discovered while using the harness on itself, and this document is
being written afterwards to impose an order on work that was already committed.

That inversion is worth naming rather than hiding. It means the tracker has been the plan
for a week, which is the state this skill exists to prevent — and it is also why "which one
next?" has twice been answered from judgment rather than from a record. This document is the
record. The `Rough size` column is therefore doing unusual work: it estimates how many
issues each item will *turn out* to need, which for several is more than the one that
already exists.

There are no epics. `epics` has never run and `docs/` holds none of the inception
documents — see #22, which is itself on this list.

| # | Item | Blocks | Rough size | Why here |
| :-- | :-- | :-- | :-- | :-- |
| 1 | **#27** — a spawned reviewer deadlocks the Stop gate into an unbreakable loop | #26, #25 | ~1 issue | The harness cannot be used the way it tells you to use it. `implement` says invoke the reviewer subagent; doing so produced a turn that could not end, because nothing said how to wait for it. This cost 25 turns in one session. Everything below assumes the recommended path works. |
| 2 | **#26** — the gate is silenced by `git checkout` | #25 | ~1–2 issues | The only enforced rule is one command from off, and silently: a skipped review and a clean repo produce identical output. It goes second **and cannot go first** — today it is the only escape from #27, so closing it while the deadlock stands would leave no way out of a stuck turn. Fixing them in this order is the whole reason to write an order down. |
| 3 | **#25** — the gate should refuse CLEAN on a self-review | — | ~1 issue | Independence is what the judgment layer is sold on, and the gate still clears `reviewed_by=inline`. Its prerequisite shipped with #9 (`init` verifies the reviewer is spawnable). Above #4 because it closes the last gap in the claim the repo leads with; below #2 because enforcing independence through a gate that can be stepped around enforces nothing. |
| 4 | **#19** — `--update` cannot create a lock, so a new rulebook can never be pinned | — | ~1 issue | `AGENTS.md` names the hash-pinned rulebook as one of the two ideas this repo exists for, and the dogfooded instance ships **unpinned** with a three-place explanation of why. A core claim is false in the reference implementation. Above #5 because it is a broken promise rather than a latent hazard. |
| 5 | **#28** — a strippable `assert` guards the path that keeps a check from checking nothing | — | ~1 issue | Five lines, and the reviewer supplied the replacement verbatim. Unreachable today — nothing runs with `-O` — which is the only reason it is not higher, because the shape is #16's exactly: a guard exiting 0 having compared nothing. Cheap enough that it should not be allowed to age. |
| 6 | **#14** — `Source globs` duplicates the shipped-path definition by hand | #18 | ~2 issues | A decision before it is a change: how many places get to define "what is shipped", and which is authoritative. It also now answers two questions at once (what re-stales a receipt, what triggers validators) which want opposite answers for the manifests. Above #7 because whatever is decided here determines what #7's fix should even look like. |
| 7 | **#18** — the review gate is unsatisfiable without a `Source globs` line | — | ~1 issue | The fallback is `globs='*'`, so `.specs/` counts as source and committing the receipt invalidates the receipt, forever. Real user impact on any partial install, and it fails *closed*, which is why it sits below #6 despite being the more concrete bug — a loud failure can wait behind the decision that shapes its fix. |
| 8 | **#23** — rule C-2 enumerates the files that state a fact, so it goes stale | — | ~1–2 issues | The gate count was wrong in three files, then five, and `.steering/structure.md` sat wrong through two releases because C-2 predates it. Recurring and self-inflicted. Below #7 because it damages credibility rather than behaviour: no gate fails open, a number is merely untrue. |
| 9 | **#10** — "one task, one commit" contradicts the quality gate | — | ~1 issue | A spec is already written and merged, so it is the cheapest item here to start. It is ninth anyway because the decision was made and adopted a week ago — every spec written since folds red and green into one task — so this is documentation catching up to practice, not a change in behaviour. |
| 10 | **#22** — the mandatory document set is declared but never verified | — | ~2–3 issues | The widest blast radius of anything on this list: it would run in every project the harness installs into, including ones mid-setup, and a guard that fires on a considered choice gets deleted. Its central question — what the opt-out is — is unanswered, and answering it badly is worse than the gap. Last because it needs a decision this repo has not made, not because it is unimportant. |

## Unshaped

Items that cannot be ordered yet because nobody knows what they are. This is a queue to
empty, not a tier — anything sitting here is undecided work, and it does not get built while
it stays here.

- **The inception documents** — `PRD.md`, `DESIGN.md`, `NORTH_STAR.md`, `EPICS.md`,
  `CONTRACT.md`. `init` calls three of them mandatory and this repo has none. Every one of
  their *mechanical* outputs already exists (`- Owns:`, `.steering/structure.md`, the
  reviewer's `G-*`/`C-*` rulebook), so what is undecided is whether the prose is worth
  writing at all, or whether `README.md` and `AGENTS.md` genuinely do the job. **Blocked on:**
  a decision, not information. Note this backlog is the one member of that set now written.
- **Running the eval suite** — four suites authored, never executed, because
  `claude plugin eval` is early access and was not enabled on the account this was built on.
  **Blocked on:** access. Until then nobody knows whether the suites are green, red, or
  malformed, so no work behind them can be sized.
- **Antigravity has no `SessionStart`** — the steering digest has no equivalent, and
  `PreInvocation` is the candidate substitute but needs a once-per-session guard.
  `docs/fidelity.md` records this honestly as a real gap. **Blocked on:** whether the guard
  is achievable at all, which nobody has tried.

## What would change this order

- **FIRED, 2026-08-25, and the order held.** #27's spec conceded that a blocking `Stop` hook
  cannot coexist with an async subagent — the trigger below, verbatim. The order did not change,
  because the review of that spec then established the concession was wrong: a turn *can* wait for
  an async subagent by staying open, so the coexistence is fine and #27 is a plugin bug after all
  (`docs/verified.md`). #26 stays second on its original reasoning — it remains the only escape
  when a turn does get stuck.
- **#27 turning out to be a harness limitation rather than a plugin bug.** If a blocking
  `Stop` hook simply cannot coexist with an async subagent, then #26 stops being second —
  the escape it describes becomes load-bearing and closing it would be wrong.
- **Anyone other than the author using this.** Nine of the ten items were found by
  dogfooding, which finds what the author's own habits reach. A second user would reorder
  this list within a day, and that is an argument for shipping before polishing.
