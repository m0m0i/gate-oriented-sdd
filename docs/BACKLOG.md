# Product backlog

- Last groomed: 2026-08-25 (third grooming — see **What changed** below)
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

- **#34 shipped and is closed.** It was item 1. Four review rounds; three HIGH findings, one of
  which was #14's recorded hazard firing live on that branch.
- **#39 arrived**, collecting six guards that can report success having checked nothing — the
  residue of #34's review rounds plus pre-existing instances nobody had gathered.
- **#26 is unchanged at the top of the remaining work, and has been through two branches
  without being started.** It was used four times this week as the only way out of a stuck
  turn. Now that #27 has shipped the instruction that removes the need for it, closing the
  bypass is safe — which was the stated condition.
- **#28 is promoted to second** for a reason that is not severity: it is the small,
  self-contained one, and it is the task chosen for the fresh-session test.

| # | Item | Blocks | Rough size | Why here |
| :-- | :-- | :-- | :-- | :-- |
| 1 | **#26** — the gate is silenced by `git checkout` | #25 | ~1–2 issues | The only deliberate bypass of the only enforced rule, and silent: a skipped review and a clean repo produce identical output. Its stated precondition is now met — #27 shipped the instruction that removes the reason to reach for it, and it was still reached for four times this week while that instruction did not exist. It has led this list through two branches without being started, which is itself an argument for taking it before something else displaces it again. |
| 2 | **#28** — a strippable `assert` guards the path that keeps a check from checking nothing | — | ~1 issue | Second **not on severity** — it is unreachable today, since nothing runs with `-O`. It is here because it is small, self-contained, has its replacement supplied verbatim, and is the task chosen to test whether a cold session can carry `spec` → `implement` → reviewer without help. A first task should be one where a failure is legible as a harness problem rather than a hard problem. |
| 3 | **#39** — six guards can report success having checked nothing | — | ~2–3 issues | The generalisation of #16, #34 and half of this week's review findings, now that they are gathered in one place. Its first item — `report` has no `skip` state, so `45 passed` can mean 44 verified plus one skipped — probably retires the whole family. Above #4 because it includes a regression #34 shipped: routing the quality gate's read through the shared function suppressed the only signal that an unreadable `tech.md` was being read as an absent one. |
| 4 | **#36** — enforce at `git push` / `gh pr create` rather than at turn end | — | ~1 issue, or 0 | Still adjacent to #26 and still possibly its answer rather than a separate item. Whoever specs #26 must adopt, fold, or reject it in writing. Below #3 now because #39 contains a live regression and this does not. |
| 5 | **#35** — a review by ref produces a `reviewed_sha` of the working tree | — | ~1 issue | Can clear the gate on a review of *different code* — the fail-open direction. It stays mid-list because #27 removed the reason to review by ref at all: the parked working tree existed to escape the deadlock, and the deadlock is gone. A real hazard whose likelihood two shipped items have now reduced. |
| 6 | **#25** — the gate should refuse CLEAN on a self-review | — | ~1 issue | Its prerequisite shipped with #9, and the reviewer is now genuinely independent — so this is the difference between independence being available and being required. Below #1 because enforcing independence through a gate that can be stepped around enforces nothing. |
| 7 | **#19** — `--update` cannot create a lock, so a new rulebook can never be pinned | — | ~1 issue | `AGENTS.md` names the hash-pinned rulebook as one of the two ideas this repo exists for, and the dogfooded instance still ships **unpinned**. A core claim false in the reference implementation. |
| 8 | **#14** — `Source globs` duplicates the shipped-path definition by hand | #18 | ~2 issues | **Promoted in evidence, not in position.** #34's review caught this firing for real: a new `.sh` under `assets/` was invisible to both gates while `check-version-bump.py`'s prefix list counted it. It is no longer hypothetical. Still below the fail-opens above it, but the next person who argues it is theoretical has a counter-example. |
| 9 | **#18** — the review gate is unsatisfiable without a `Source globs` line | — | ~1 issue | Fails *closed*, so a loud failure can wait behind the decision at #8 that shapes its fix. |
| 10 | **#23** — rule C-2 enumerates the files that state a fact | — | ~1–2 issues | Bitten four more times this week, all inside review rounds. Damages credibility rather than behaviour: no gate fails open, a number is merely untrue. |
| 11 | **#10** — "one task, one commit" contradicts the quality gate | — | ~1 issue | A spec is written and merged. Eleventh because practice adopted the decision a week ago — every spec since folds red and green into one task. Documentation catching up. |
| 12 | **#22** — the mandatory document set is declared but never verified | — | ~2–3 issues | Widest blast radius: it would run in every project the harness installs into, including ones mid-setup. Its central question — what the opt-out is — is still unanswered. |

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

- **The fresh-session test failing at #27's wait instruction.** #27's AC1 is presence-checked
  only; a cold agent that reads "keep the turn open" and still says "Holding." means the fix
  did not work, and #36 — enforcing at the push boundary instead of turn end — stops being
  fourth.
- **#36 turning out to be the right fix for #26.** Then they are one item and everything below
  shifts up.
- **Anyone other than the author using this.** Every item was found by dogfooding, which finds
  what the author's own habits reach. A second user would reorder this within a day — which is
  precisely what the fresh-session test is for.

### Triggers that have already fired

- **2026-08-25 — "#34's fix revealing other unparsed anchors."** Fired sideways. No other
  anchor was unparsed, but the fix revealed that the new guard itself was outside `Source
  globs` — the *shipped-path* definition drifting rather than the *anchor* one. #14 moved in
  evidence rather than in position; see its row.

- **2026-08-25 — "#27 turning out to be a harness limitation rather than a plugin bug."**
  Fired, and the order held. #27's spec conceded that a blocking `Stop` hook cannot coexist
  with an async subagent; the review of that spec then established the concession was wrong.
  A turn *can* wait by staying open (`docs/verified.md`), so #27 was a plugin bug after all
  and was fixed as one. The trigger's own consequence — that `git checkout` is the only escape
  — was retracted with it; it is the only *bypass*, never the only *exit*.
