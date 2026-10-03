# Spec: an unborn branch turns the review gate off
- Slug: 228-an-unborn-branch-turns-the-gate-off   Issue: 228   Type: bug   Status: approved
- Author: m0m0i   Date: 2026-10-03

## 1. Requirements (WHAT / WHY)

- Reproduction: in a healthy repository where another branch holds a finished spec with no
  receipt (a state the gate blocks from every branch, case 76), run `git checkout --orphan scratch`,
  then `sh hooks/review-gate.sh`. It prints `{}` and exits 0, under macOS `sh` (bash 3.2) and under
  `dash`. After the orphan's first commit the same gate blocks, naming the other branch. Measured at
  `6b5047e`; the issue's measurements were at `6dca392`, and `hooks/` has not changed between them.

- Expected: the repository-wide scan runs whatever HEAD is. That is #26's whole subject — moving HEAD
  does not clear the gate — and case 77 already pins it for a detached HEAD, whose comment calls that
  "the same hole one step quieter". An unborn branch is one more step.

- Actual: `hooks/review-gate.sh:68`, `branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null) || gate_pass`,
  exits 128 on an unborn branch, and the gate passes before `check_current_branch` or
  `scan_other_branches` runs. A spec sitting finished in an unborn branch's own working tree is silent
  for the same reason.

- Impact: no damage is needed, only an ordinary command. `git checkout --orphan` is the documented way
  to start a `gh-pages` branch, among other uses. The window lasts until the orphan's first commit,
  and a turn can end inside it. Under `- Owns: gates never fail open` a gate that silently stops
  checking is a BLOCKER. The same line also passes when the ref store is damaged, which is the state
  #178's measured reproduction actually reaches.

- **Root cause:** line 68 asks `git rev-parse`, which answers by resolving HEAD to a commit. An unborn
  branch has no commit, so the question fails, and `|| gate_pass` reads the failure as a reason to stop
  before anything is checked. The line is older than the scan: it dates from the first commit
  (`fc4b7f2`), when the gate asked only about the branch you stood on and every early exit was a pass,
  which was then correct — no commit, no spec. #26 made the gate ask about the repository, and rewrote
  every exit inside `check_current_branch` as a `return` so that the scan always runs ("Every exit from
  here is a `return`, never a pass"). Line 68 sits in front of both functions and kept its pass. The
  comment at `:130–132` says a repository with no commits "returns here too", inside
  `check_current_branch`; it never gets there.

- Acceptance criteria:
  - [ ] **AC1:** WHEN HEAD is an unborn branch and another branch holds finished work with no usable
    review, THE review gate SHALL block on both channels and name that branch, with the message it
    gives from a born branch.
  - [ ] **AC2:** WHEN the repository has no commits and no other branch (a fresh `git init`), THE review
    gate SHALL print `{}` and exit 0.
  - [ ] **AC3:** WHEN HEAD is detached, THE review gate SHALL behave as it does today: case 77 stays
    green, and the current-branch question is still asked of the literal `HEAD`.
  - [ ] **AC4:** WHEN HEAD is an unborn branch whose working tree holds a finished spec for that branch
    and no receipt, THE review gate SHALL block with the message it gives a born branch in that state.
  - [ ] **AC5:** WHEN HEAD is an unborn branch whose working tree holds a finished spec for that branch
    and a receipt, THE review gate SHALL block and say that the branch has no commit for the review to
    describe.
  - [ ] **AC6:** WHEN git cannot say which branch HEAD is on (`git symbolic-ref` exits 128, as under
    #178's two ref faults), THE review gate SHALL block on both channels and say so.
  - [ ] **AC7:** each new case in `scripts/test-gates.sh` fails against `6b5047e`'s `hooks/` (or, for
    AC5, against the tree before its own task) and passes after the fix, and every existing case keeps
    its verdict.

- Out of scope:
  - #178's other two sites, `review-gate.sh:219` (`for-each-ref` drops a broken ref and exits 0) and
    `:221` (`|| continue` on an unresolvable tip). Line 68 moves here (Q2); those two stay #178's.
  - `review-gate.sh:64`, `git rev-parse --git-dir || gate_pass`. Outside a repository the pass is
    correct, and a `.git` too damaged to be recognised is not this issue.
  - #232, found while drafting this: `gate_spec_review_state`'s stale diff (`hooks/gate-lib.sh:219`)
    discards git's exit status, so a `- Source globs:` value git rejects lets a stale receipt pass.
    AC5's path reaches the same line from an unborn HEAD; this spec closes its own path in
    `review-gate.sh` and leaves the line to #232.
  - #176's default arm. No state is added to the `case` here, which is what keeps the two apart.

### Clarifications

Asked and answered 2026-10-03.

- **Q1. On an unborn branch, does the gate also check that branch's own working tree, as it does for any
  other branch?** Yes. #26 counts a spec that is not yet committed ("the state its author is in for most
  of the spec's life"), and an unborn branch is a branch with nothing committed. A receipt there cannot
  describe any code, so it blocks too, handled in `review-gate.sh` with no new library state. → AC4, AC5.
- **Q2. When git cannot say what HEAD is, does this fix make line 68 block, or leave the pass for #178?**
  This fix blocks. The line is being rewritten, and keeping `|| gate_pass` in it would write a fresh
  fail-open on purpose. #228 owns all of line 68; #178 keeps `:219` and `:221`, and its triage comment
  gets a pointer. → AC6.
- **Not a requirement, decided at the same time:** the stale-diff finding is filed as #232 and placed in
  row 1 from this branch, the way #219 and #222 were placed by their own pull requests, so this branch's
  tracker check stays green.

## 2. Design (HOW)

- **Fix approach.** Ask which branch HEAD is on, not which commit it resolves to.
  1. Line 68 becomes `git symbolic-ref -q --short HEAD`, read by exit status. Measured at `6b5047e`, its
     three statuses are the three states, where `rev-parse --abbrev-ref` gives two:

     | HEAD | `symbolic-ref -q --short` | `rev-parse --abbrev-ref` | Gate today |
     | :-- | :-- | :-- | :-- |
     | a born branch | 0, its name | 0, its name | runs |
     | unborn (orphan, fresh `git init`) | **0, its name** | 128 | passes at `:68` |
     | detached, including at a missing object | 1 | 0, `HEAD` | runs; case 77 |
     | ref store damaged (#178's mode-000 `refs/heads`, garbage `packed-refs`) | **128** | 128 | passes at `:68` |

     So: 0 keeps the name; 1 sets `branch=HEAD`, the literal both functions already handle for a
     detached HEAD; anything else is `gate_block`, naming git's status and sending the reader to the
     repository rather than to a permission. For a born branch the two commands print the same name:
     measured for a plain name, a name shadowed by a tag (both print `heads/12-x`), a slashed name, and a
     linked worktree.
  2. `check_current_branch`'s `head` becomes `git rev-parse --verify -q HEAD`. Today an unborn branch
     sets it to the literal `HEAD` — `rev-parse` echoes its argument before failing, and `|| echo ''`
     appends to that rather than replacing it — which would reach `gate_spec_review_state` as a tip. With
     `--verify -q` it is empty; a born branch gets the same sha as before.
  3. In `check_current_branch`, after the state: WHEN `head` is empty, the state is empty, the receipt
     exists, and the spec's tasks are all ticked, block with AC5's message. Only that combination needs
     it: every other receipt state already blocks, and the empty state is reached here because the
     staleness diff compares against a HEAD that does not exist, which is #232's line read the same way.
     It lives in `review-gate.sh` rather than as a library state because only the current-branch reader
     can stand on an unborn branch — the scan reads refs, which have tips, and CI reads a pull request's
     head — and a new state would need arms that #176 is about.
  4. Comments. Line 68 says what the three answers are and carries #26's rule to the line in front of
     both functions: nothing before the scan may pass. The comment at `:130–132` ("A repository with no
     commits returns here too") becomes true, and says so with the unborn branch beside it.
  - **Narrower,** keeping `rev-parse` and testing for an unborn HEAD on failure: needs a second command to
    tell unborn from damaged, which is what `symbolic-ref` already answers. **Wider,** rethinking how the
    gate picks its subject: #26's ground, and not what is broken.

- **Affected files:** `hooks/review-gate.sh`; `scripts/test-gates.sh`; `docs/BACKLOG.md` (row 1 places
  #232, and #178's description loses `:68`). `hooks/` ships, so `implement`'s version step bumps the
  patch.

- **Blast radius:**
  - Line 68 runs at every turn end in every install. Born branches see the same name (measured above);
    detached HEADs the same literal. Unborn branches now reach both functions; a fresh `git init` still
    passes, because it has no spec and no refs. A damaged ref store now blocks, which is the change; the
    risk is a healthy repository where `symbolic-ref` exits 128, and none of the measured states does.
  - The `head` change touches only unborn branches. `gate_work_reached_base` already returns 1 on an
    empty tip (its first guard), so the merged-work skip stays unfired there, which is the safe direction.
  - `check-unreviewed-work.sh` takes the head from the pull-request event and never names HEAD;
    `quality-gate.sh` and the steering digests do not read the branch. None of them changes.

- **Why this cannot recur:** a case for each of `symbolic-ref`'s three answers (unborn, detached, damaged)
  and for the fresh-install door, so any return to a commit-based question goes red. And line 68's
  comment states #26's rule where #26 did not write it: an early exit in front of the scan is another
  place to stand where the gate does not look.

## 3. Tasks (TDD-ordered)
> One task is one complete Red-Green-Refactor cycle, so one green commit. No task is sequenced after the review.
- [x] T1: cases for AC1, AC2, AC4 and AC6 (AC1, AC4 and AC6 red against `6b5047e`'s `hooks/`; AC2 green
  before and after, as the fresh-install pin). AC6's fixture is the garbage `packed-refs` line, which
  needs no file mode and so no root skip. Then line 68 as Design 1 → green, with case 77 (AC3) unchanged.
- [x] T2: a case for AC5 — an unborn branch, a finished spec and a CLEAN receipt naming `main`'s commit
  in its working tree — red after T1. Then `head` via `--verify -q` and the guard (Design 2 and 3) → green.
- [ ] T3: the comments (Design 4), and `docs/BACKLOG.md`: #232 into row 1's `Item`, #178's description
  down to `:219` and `:221`. Full suite green, and `check-backlog-tracker.py` clean.
