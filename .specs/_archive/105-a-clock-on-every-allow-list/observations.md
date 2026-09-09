# Observations — #105

## T1 — before

The five allow-lists, against the seven fields the Receipt block requires:

    agents/ts-reviewer.md              git diff, git diff --stat, git log --oneline, git rev-parse HEAD
    agents/python-reviewer.md          same four
    agents/dart-flutter-reviewer.md    same four
    agents/_template/reviewer.md       same four, plus {{VALIDATOR_LIST}}
    .claude/agents/gate-sdd-reviewer.md  same four, plus the ten named validators

No clock on any of the five. `git log --oneline` prints no date, so the issue's second
proposal — `reviewed_at` as the HEAD commit time, "already on every allow-list" — needed a new
command on all five lists as well, at the same cost as the clock and with the field no longer
recording when the review ran. That is the finding that decided the Clarifications.

`reviewed_sha` was the only other field with a command behind it, and `git rev-parse HEAD` was
on all five. The remaining five fields come from the reviewer's own run.

## T4 — the count claim, twice

The first enumeration searched `.steering/`, both READMEs, `AGENTS.md` and `docs/` by hand and
reached five places. `CONTRIBUTING.md:21` was the sixth, found by the reviewer, and it states
the count twice — as a total and as the number of the next test. The re-enumeration is
`git grep` across all tracked files, which found no seventh and which is what should have been
run first. The number moved twice: 54 → 57 after T1 and T3, then → 62 after the review round
added cases 46-50.

Records left alone, having been checked rather than assumed: `docs/verified.md` :151, :176,
:195, :219; the `.work_logs/` mentions; and the `observations.md` validator line in all eleven
spec directories that carry one, two live and nine archived.

### Validators, at the reviewed tip

- `./scripts/check-leakage.sh` → exit 0 — `check-leakage: clean`
- `./scripts/check-manifests.py` → exit 0 — `check-manifests: both manifests agree`
- `./scripts/check-markdown-fences.py` → exit 0 — `check-markdown-fences: 10 ```markdown fence(s), no hand-wrapped prose`
- `./scripts/check-receipt-schema.py` → exit 0 — `check-receipt-schema: 7 field(s) agree across 3 copies, and 5 reviewer(s) can produce the 2 needing a command`
- `./scripts/check-skill-contracts.py` → exit 0 — `check-skill-contracts: 9 skill contract(s) present`
- `./scripts/check-templates.py` → exit 0 — `check-templates: 10 task line(s) across 3 template(s), no split red steps`
- `./assets/check-steering-anchors.sh` → exit 0 — `check-steering-anchors: 5 of 5 anchor(s) resolved, none unreadable`
- `./assets/check-locks.py` → exit 0 — `check-locks: 6 pinned file(s) match their locks in .claude/agents, agents`
- `./scripts/test-gates.sh` → exit 0 — `test-gates: 62 passed, 0 failed`

**No lock re-pin was needed.** The spec predicted this and `check-locks.py` confirms it: the
three `rules-lock.json` files pin `rules/*.md` only, and no lock hashes a reviewer file or the
contract. The issue's "re-pin any lock that hashes the reviewer files" was conditional and the
condition does not hold.

**Each new case shown to discriminate, not assumed to.** Neutering the missing-file branch to
`continue` leaves 46 red and 47/48 green; the same for 47; emptying the completeness check
leaves only 48 red; removing the floor makes 49 exit 0 with the success line it checks for;
dropping `reviewed_sha` from `PRODUCERS` makes only 50 fail. For 45, replacing the whole failure
branch with an `assert` — #28's actual shape — takes both invocations red, while an `assert`
merely added alongside working code leaves 45 green and is caught by 43's no-traceback
requirement instead. The two cases cover different halves.

**Review triage — five rounds, one reviewer, context kept.**

1. BLOCKED, 2 HIGH. `CONTRIBUTING.md` as a sixth count claim; three hard-exit branches with no
   case. Both taken. 3 MEDIUM also taken: no emptiness guard on `REVIEWERS`; `reviewed_by`
   filed as "known from its own run" where the contract says the opposite twelve lines under
   the Receipt block; `reviewed_sha` asserted in a comment where it could be enforced — taking
   the third closed the "a producer LEAVING an allow-list" gap and is what case 50 pins.
2. CLEAN, 5 LOW, all taken. Case 49 caught its own message changing under LOW-3 and was updated
   with it, which is the case doing what it was written for.
3. CLEAN, 1 MEDIUM, 1 LOW, both taken. The MEDIUM was the round's best finding: the `None`
   bucket offered three justifications and the middle one — "comes from a command already on
   every list" — has no members and must never have any, because that is the reasoning
   `reviewed_sha` carried. The guidance a maintainer reads at the moment of classifying a new
   field would have reproduced #105 past the guard built to prevent it.
4. CLEAN, 1 LOW, taken. "verbatim" was not, and "until it became the root cause of #105"
   resolved most naturally to `reviewed_sha`, which the spec contradicts. Rewritten
   prospectively in the reviewer's own words.
5. APPROVE, no findings at any severity. Receipt at `5efca3a`.

**Recorded, not acted on.** The partition "known to the reviewer from its own run" reads
narrowly against a hypothetical field the reviewer would obtain by *reading* rather than
generating; such a field is correctly `None` either way and the completeness check still forces
an entry and a comment. Left on the reviewer's own advice not to touch the sentence for that
alone.

**The reviewer disclosed an off-list command in round two**, `git grep`, run because its
rulebook's C-2 requires grepping for every other statement of a changed count while its
allow-list names no search command. That is this issue's own defect a second time, one level up
— in the rulebook rather than the receipt — and outside what the new guard can see, since a
rulebook is prose and offers no pairing for a guard to hold. Filed rather than fixed here.

**The first receipt in this repository produced by a reviewer that had a clock.**
`reviewed_at=2026-09-09T09:32:21Z`, from the command this branch put on its allow-list.
