# Spec: a strippable assert guards the path that keeps check-receipt-schema from checking nothing
- Slug: 28-strippable-assert-guards-receipt-schema   Issue: 28   Type: bug   Status: archived
- Author: m0m0i   Date: 2026-08-25   Archived: 2026-08-26

## 1. Requirements (WHAT / WHY)

- Reproduction: remove `.claude/agents/_shared/reviewer-contract.md` from `SOURCES` in `scripts/check-receipt-schema.py`, delete the mirror file it names, then run the guard through an interpreter with assertions off:

  ```
  $ python3 -O ./scripts/check-receipt-schema.py
  check-receipt-schema: 7 field(s) agree across 2 copies
  $ echo $?
  0
  ```

  `PYTHONOPTIMIZE=1` in the environment produces the same result without any flag, and it reaches the `#!/usr/bin/env python3` shebang too, so no caller has to opt in for this to happen.

- Expected: the guard fails, on stderr, naming the mirror that is not a `SOURCE` — because the comparison it exists to make was skipped.

- Actual: it prints its success line and exits 0. The `assert` on line 106 is the only thing that makes `continue` on line 109 unreachable; with assertions stripped, a mirror the `SOURCES` loop never checked for existence is silently skipped, and the run reports success having compared the mirrored contract against nothing.

- Impact: this repository, on the guard that keeps this repo's *own* reviewer contract in lockstep with the shipped one. Field agreement is not the whole of what that mirror carries — the severity ladder and the definition of CLEAN are in it, and a drifted mirror is a reviewer that can emit CLEAN with HIGH findings outstanding. That is `- Owns: gates never fail open` at one remove.

  **Why it is not HIGH.** Nothing in the repository invokes with `-O` and nothing sets `PYTHONOPTIMIZE`; CI runs the script through its shebang, so the path is not reachable today. It is a fail-safe that one environment variable removes, not a live fail-open. It was raised as a MEDIUM in the fourth review of #9 and carried here rather than fixed on that branch.

- **Root cause:** the invariant and the safety property are the same property, and the invariant is written in a form the interpreter is allowed to delete.

  `assert` is a *developer* invariant — a statement about internal consistency that a release build may reasonably drop. What this one actually holds up is the precondition that makes a `continue` unreachable, and if it stops holding the guard exits 0 having compared nothing. Expressing a safety check in the one Python construct that is conditionally compiled out puts the guard's correctness under the control of an environment variable that no caller in this repo sets and any caller anywhere could.

  Secondarily, it is the only `assert` in the repository: eleven `sys.exit(1)` call sites across five guard scripts, and zero asserts in `scripts/`, `assets/`, or `hooks/`. One incidental deviation from a pattern established well past the point where convention decides.

- Acceptance criteria:
  - [x] **AC1:** WHEN a `MIRRORS` destination is not listed in `SOURCES` THE SYSTEM SHALL print a diagnostic naming that path to stderr and exit 1, rather than proceeding.
  - [x] **AC2:** AC1 SHALL hold when the script is run as `python3 -O`, and when `PYTHONOPTIMIZE` is set in the environment with no flag passed.
  - [x] **AC3:** the invariant SHALL be expressed in the idiom the other five guards use — `print(..., file=sys.stderr)` then `sys.exit(1)` — leaving zero `assert` statements in `scripts/`, `assets/`, and `hooks/`.
  - [x] **AC4:** the comment above the check SHALL survive verbatim. It says the thing the code cannot: why the skip below is unreachable, and that this repo has twice shipped a guard whose safety rested on something no comment named.
  - [x] **AC5:** on a clean checkout the guard SHALL keep its current success output and exit 0, identically under `python3` and under `python3 -O`.
  - [x] **AC6:** the regression test SHALL be a case in `scripts/test-gates.sh` that fails before the fix and passes after, and it SHALL drive the script under `-O` — a case that only runs the default interpreter cannot fail on this bug.

- Out of scope:
  - **Auditing the other five guards for the same shape.** #39 is already open for "six guards can report success having checked nothing"; the sweep belongs there, with this as a worked example.
  - **Refusing to run under `PYTHONOPTIMIZE` at all.** A global refusal is a different, wider decision about how these scripts are invoked, and it would not fix this defect — it would only make one way of reaching it noisy.
  - Any change to what the guard compares, to `SOURCES`, `MIRRORS`, or `REQUIRED`.

### Clarifications
_2026-08-25._

- **Q: keep the `continue`-on-missing-mirror and make it unreachable, or delete the unreachable branch so there is no invariant left to protect?** A: keep it — the reviewer's verbatim fix. Deleting the branch trades one duplicated check (the `SOURCES` loop already hard-exits on a missing file) for the loss of the comment that explains *why* the skip is safe, and that comment is the part the issue singles out as worth keeping. The belt-and-braces variant — both the membership check and a hard failure on a missing mirror — was rejected for the same reason: it makes the surviving comment describe a skip that no longer exists, so the file would gain a check and lose an explanation.

- **Q: is "zero asserts in `scripts/`, `assets/`, `hooks/`" pinned mechanically, or done once?** A: pinned, as a case in `scripts/test-gates.sh`. The issue's own argument is that a guard's safety must not rest on a condition nobody checks; an unpinned convention is that condition again, one level up. A statement-position match (`^[[:space:]]*assert[[:space:]]`) is required — an unanchored `assert` matches "asserts the" in `check-skill-contracts.py` and "asserted in a README" in the suite's own header, so a loose pattern would arrive permanently red.

- **Not asked, because the repo answers it:** whether this needs a version bump. `SHIPPED` in `scripts/check-version-bump.py` is `skills/ agents/ hooks/ assets/ plugin.json .claude-plugin/plugin.json`. Both files this spec touches are under `scripts/`, which `.steering/structure.md` also marks as not shipped. No bump.

## 2. Design (HOW)

- **Fix approach.** Replace line 106 with the file's own idiom, leaving the comment above it untouched:

  ```python
  for _src, _dst in MIRRORS:
      # Every mirror must also be a SOURCE. ... (comment unchanged, verbatim)
      if _dst not in SOURCES:
          print(f"check-receipt-schema: {_dst} is a mirror but not a SOURCE, so a missing "
                "file would be skipped rather than caught — see #16.", file=sys.stderr)
          sys.exit(1)
  ```

  Five lines, in one guard, replacing a check the interpreter may delete with the same check expressed the way the other five guards express theirs. Nothing else in the file moves.

- **How the regression case reaches the bug.** `SOURCES` and `MIRRORS` are module constants, so the only way to violate the invariant is to edit them — which is exactly what the reviewer did by hand. The case therefore builds a throwaway tree under `$TMP`:

  | Path in the fixture | Content |
  | :-- | :-- |
  | `scripts/check-receipt-schema.py` | a copy of the real script, executable |
  | `agents/_shared/reviewer-contract.md` | copied from `$ROOT`, so the surviving copies agree |
  | `skills/implement/SKILL.md` | copied from `$ROOT` |
  | `.claude/agents/_shared/reviewer-contract.md` | **absent** — this is the mirror that vanishes |

  `ROOT` is derived from `__file__`, so the copy resolves against the fixture and not this repository. A `python3` heredoc then deletes the `.claude/...` line from `SOURCES` — the same mutation idiom cases 29, 31 and 33 already use, and portable in a way `sed -i` is not.

  Three assertions, in this order:

  1. **Control, before mutation:** the untouched copy under `python3 -O` exits 0 and prints its success line. This is AC5, and it is what makes the next two mean something — without it a case that fails for any reason at all reads as a caught bug.
  2. `python3 -O <copy>` after the mutation: exit 1, stderr naming `.claude/agents/_shared/reviewer-contract.md`.
  3. `PYTHONOPTIMIZE=1 <copy>` invoked through its shebang, no flag: same. This is the half that matters — it is how the bug arrives without anyone choosing it.

  **The fixture must fail loudly if it cannot be built.** If the `SOURCES` line is ever reworded, the mutation silently no-ops and the case reports ok having tested a script that was never broken. The heredoc exits non-zero when its needle is absent, and the case reports failure with "fixture could not be built" rather than success. That is case 30's lesson applied on arrival rather than after a round of review.

- **The convention pin** is a separate case: `grep -rnE '^[[:space:]]*assert[[:space:]]'` over `$ROOT/scripts`, `$ROOT/assets`, `$ROOT/hooks`, failing with the offending lines quoted. It is anchored to statement position for the reason recorded in the clarifications.

- **Affected files:** `scripts/check-receipt-schema.py`, `scripts/test-gates.sh`. No manifest change and no version bump — neither path is shipped.

- **Blast radius:** small and loud in the one direction it can go wrong. CI runs this guard on every pull request; the new branch is unreachable in a correct checkout, so an error in it can only turn CI red visibly, never green silently. The regression case operates on a copy under `$TMP` that the suite's existing `trap` removes, so it cannot leave the repository mutated even if it fails part-way. Consumer projects do not ship this script and see no change at all.

- **Why this cannot recur:** because AC3 is pinned rather than remembered. The next safety check written as an `assert` in a guard directory fails the suite on the commit that introduces it, which is the difference between a convention and a rule.

## 3. Tasks (TDD-ordered)
> Folded red-and-green per #10: one task is one complete Red-Green-Refactor cycle, so one green commit.

- [x] T1: failing case — the mutated copy exits 0 with its success line under `python3 -O` and under `PYTHONOPTIMIZE=1` through the shebang, with the unmutated control exiting 0 — then replace the `assert` with the print-and-exit idiom, leaving the comment verbatim. *(AC1, AC2, AC4, AC5, AC6)*
- [x] T2: failing case — no statement-position `assert` in `scripts/`, `assets/`, `hooks/`. Its red state is demonstrated against T1's parent commit, since the same edit cures both. *(AC3)* *Both cases were in fact written red together and the one edit turned both green; T2 is still its own commit, and its redness at `9344b79` was confirmed by running its grep against that revision rather than inferred.*
- [x] T3: run all eight validators, and diff the case list against `main` to confirm no pre-existing case changed verdict.

## 4. Review triage

`gate-sdd-reviewer`, first pass at `fd4e362`: **CLEAN** — 0 BLOCKER, 0 HIGH, 3 MEDIUM, 2 INFO. All three MEDIUMs were fixed rather than recorded, because each was cheap and each was correct.

- **MEDIUM — case 35 scanned two of the three directories it names and still reported ok.** Fixed. The work-set was corroborated by counting the *union* with `find`, and any one of those directories alone holds well over three files, so a vanished directory was undetectable; `grep` then exited 2 and the trailing `|| true` flattened that into "no matches". The comment above it named exactly this failure mode while the check did not reach it — the guard-shaped hole this spec is about, in the case pinning it. It is now corroborated per directory and reads grep's exit 2 as a failure rather than as silence. Verified by deleting `assets/` from a copy of the tree: the case now reports `work-set incomplete: assets` instead of `ok`.

- **MEDIUM — the `PYTHONOPTIMIZE=1` half had no corroborator a crash cannot satisfy.** Fixed. It asserted exit 1 alone, and exit 1 is also what a traceback returns — including the `AssertionError` this change removes — so on an interpreter where `PYTHONOPTIMIZE` did not really strip assertions it would have read ok against the *unfixed* script. Both invocations now go through one `stripped_fails` helper requiring exit 1, a diagnostic naming the path, and the absence of `Traceback`. That also closes the reviewer's AC2 gap: AC1's message requirement is now tested under both invocations, not just under `-O`.

- **MEDIUM — the case count was stale in four places.** Fixed: `45` → `47` at `README.md`:41,151 and `README.ja.md`:43,152, matching the precedent set by `8b559a9`.

- **INFO-1** (the reviewer ran `git checkout` to measure the baseline, outside its allow-list) and **INFO-2** (case 34's pre-fix redness was reasoned rather than observed, since #10's convention folds red and green into one commit) are both method notes rather than defects. INFO-2 was independently discharged afterwards by driving the case against `9344b79`'s copy of the guard: it fails `minus-O=no PYTHONOPTIMIZE=no` with `control=ok`, so it is red for the stated reason and not for a setup error.

The reviewer's one spec-accuracy finding — that "Why this cannot recur" overstated what case 35 guaranteed — is resolved in the code rather than by softening the sentence. The sentence is now true.

**Second pass at `78a9312`: CLEAN — 0 BLOCKER, 0 HIGH, 1 MEDIUM, 1 LOW, 5 INFO.** Both were fixed.

- **MEDIUM — the count sweep missed `CONTRIBUTING.md`:21.** Fixed: "45 paths are covered; a 46th behaviour needs a 46th test" → 47 and 48th. It was doubly wrong, and unlike the README lines it is an instruction a contributor acts on. `docs/BACKLOG.md`:38 was raised in the same finding as optional and is **deliberately left**: its "`45 passed` can mean 44 verified plus one skipped" is an illustration of #39's argument, and the pairing is what makes the point — renumbering it to 47 and 46 would not make it truer.

- **LOW — `stripped_fails` discriminated on a substring a sibling branch also prints.** Fixed. The `SOURCES` loop's own "is missing" message at `check-receipt-schema.py`:82 names the same path and exits 1 with no traceback, so the assertion's discrimination rested on the fixture builder removing the `SOURCES` entry and the mirror as one act, rather than on the assertion itself. It now additionally requires "is a mirror but not a SOURCE", the phrase unique to the branch under test. Demonstrated rather than assumed: a fixture loosened the way the finding describes produces `exit=1` and the path, which the old check accepted and the new one rejects.

- **INFO-1 to INFO-5** are confirmations and forward notes, not defects. INFO-4 — that case 35's `scripts assets hooks` list can fall behind a future fourth guard directory without going red — is real and is G-8's shape. It matches AC3's scope verbatim, so it is not a defect in this spec; it belongs to #39, where the same class of drift is already gathered. INFO-2 records that deleting a directory exercises the `missing_dirs` loop and not the `rc -eq 2` branch, whose live trigger is a present-but-unreadable directory — the state case 32 established as real. Both are recorded rather than fixed here.

**Third pass at `d2b2fa2`: APPROVE — CLEAN, no findings at any severity.** The count sweep is complete (`docs/BACKLOG.md`:38 confirmed as the one deliberate exclusion), and `stripped_fails` is self-discriminating: four conditions, each with its own early return, and the only `echo ok` is the last arm of the last `case`, so any unanticipated stderr fails closed. The reviewer confirmed that the guard's implicit string concatenation at `check-receipt-schema.py`:107-108 leaves the required phrase contiguous, and that rewording the message turns the case red rather than silently green.

Asked directly whether INFO-2 and INFO-4 belonged in this branch, the reviewer said no to both, and gave INFO-2 a structural reason worth keeping: case 35 scans `$ROOT` itself — that is what makes it a convention pin rather than a fixture test — so exercising its `rc -eq 2` branch would mean making part of the live repository unreadable during the suite run. Testing it properly needs the case to take its work-set as a parameter, which is a #39-shaped refactor rather than a #28-shaped one.

Receipt at `.review-receipt`, beside this file — written relative so it survives archiving.
