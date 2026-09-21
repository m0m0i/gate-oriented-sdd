# Spec: A missing spec file silences the one branch nobody else reads
- Slug: 177-a-missing-spec-file-silences-one-branch   Issue: 177   Type: bug   Status: done
- Author: m0m0i   Date: 2026-09-21

## 1. Requirements (WHAT / WHY)

- Reproduction: on a spec branch whose tasks are all ticked, whose `spec.md` is committed, and
  which has no receipt, `sh hooks/review-gate.sh` exits 2. Delete `.specs/<slug>/spec.md` from
  the **working tree only** — do not commit the deletion — and it exits 0 and prints nothing. A
  sparse checkout excluding `.specs/`, or a partial worktree, reaches the same state with
  nobody deleting anything.
- Expected: the gate blocks. The branch holds finished work with no usable review, and the spec
  that says so is in the branch's own tree. #26's AC1 is that the question is asked on **every**
  branch, and `- Owns: gates never fail open` is what ranks a silent gate as a defect rather
  than a rough edge.
- Actual: silence, by two routes that are each correct alone. `hooks/review-gate.sh:49` returns
  0 when `.specs/$branch/spec.md` is not a file **on disk**, because the current-branch path
  reads the working tree on purpose so an uncommitted spec edit counts. `hooks/review-gate.sh:109`
  then skips that same ref by name in the repository-wide scan, because the current-branch path
  is supposed to have answered for it.
- Impact: the author still chooses what the gate looks at — #26's sentence, narrowed from every
  branch to one, and reached by changing the working tree rather than `HEAD`. Narrower than #26
  in two ways, which is why this is row 1 rather than an emergency: it needs the spec to be
  absent from the working tree while committed on the branch, and `assets/check-unreviewed-work.sh`
  still catches it on the pull request, because that reads the head commit's tree. What is lost
  is the fast local signal, not the guarantee. Every *other* branch in the same repository is
  read from its own tree and reported.
- **Root cause:** the two readers partition the branches between them — the current branch is
  the working tree's to answer, every other branch is the ref scan's — and the partition is
  asserted by a name comparison that nothing revokes. `[ -f "$spec" ]` at :49 is made to do two
  different jobs at once: decide **which tree to read** (the working tree, so uncommitted edits
  count) and decide **whether this is a spec branch at all** (nothing to gate). When the first
  job answers "not here", the second is read off the same test as "nothing to gate", the path
  returns 0, and the scan has already been told by name that this branch is spoken for. So the
  one branch that is read from the working tree is also the one branch nobody reads from its own
  tree, and the gap between the two readings is exactly one branch wide.
- Acceptance criteria:
  - [ ] **AC1:** WHEN the current branch's `.specs/<branch>/spec.md` is absent from the working
        tree, present in that branch's own committed tree, has no unticked task, and has no
        usable review, THE SYSTEM SHALL block the turn on both channels — exit 2 with the
        message on stderr, and `{"decision":"continue"}` on stdout.
  - [ ] **AC2:** the regression test fails before the fix and passes after, and its red
        capability is recorded in the case as a named mutation, per the convention
        `scripts/test-gates.sh` already follows.
  - [ ] **AC3:** WHEN the current branch has no `spec.md` in **either** tree THE SYSTEM SHALL
        stay silent. Cases 83 and 144 are the two shapes — a swept `.specs/` directory whose
        branch is gone, and an ordinary branch that never had a spec — and neither may start
        blocking on litter.
  - [ ] **AC4:** WHEN `.specs/<branch>/spec.md` is present in the working tree THE SYSTEM SHALL
        read that copy and not the committed one, in **both** directions: a working-tree copy
        with an open task stays silent though the committed copy is all ticked, and a
        working-tree copy that is all ticked blocks though the committed copy has an open task.
        #26 chose the working-tree read deliberately; the fix adds a fallback to it, not a
        replacement for it.
  - [ ] **AC5:** THE SYSTEM SHALL report the current branch at most once, and whatever text
        reports it SHALL be true of it — a report reached through this path may not describe
        the branch as one other than the one this turn is on.
  - [ ] **AC6:** WHEN the branch's work has already reached the base — by merge commit,
        fast-forward, or squash — THE SYSTEM SHALL stay silent through the new path too, so a
        shipped-but-undeleted branch whose working tree lacks the spec does not block every turn.
  - [ ] **AC7:** WHEN the gate blocks on a spec it read from the committed tree, the message
        SHALL say that the file is not in the working tree and name the tree it was read from.
        A message about a file the reader cannot see reads as the gate hallucinating, and a gate
        that looks broken is a gate switched off (CAP-7).
  - [ ] **AC8:** WHEN the spec was read from the committed tree, the receipt SHALL be read from
        the same tree: a committed CLEAN receipt keeps the branch silent, and a receipt written
        into the working tree alone does not clear the block until it is committed.
  - [ ] **AC9:** `./scripts/test-gates.sh` passes whole, with no case removed or weakened.
- Out of scope:
  - **#176** — no default arm on `check_current_branch`'s `case`, so an unrecognised state
    reaches `gate_pass`. Backlog row 1 groups it here; this spec deliberately does not take it,
    so one issue stays one spec and one PR. It is a few lines in the same function and is the
    natural next thing to build — see the note on the `case` in Design.
  - **#178** — a failing `git for-each-ref` reads as "no other branches". Same file, groomed
    under row 2 with #39, which decides the vocabulary a guard uses to say it checked nothing.
  - Widening the **"No issue, no spec"** slug check to a spec that exists only in the committed
    tree. See the Design, which gates it deliberately rather than by omission.
  - `assets/check-unreviewed-work.sh`. It already reads the head commit's tree and already
    catches this; nothing here changes what it asks, and the Design keeps
    `gate_spec_review_state`'s signature so that stays true.

### Clarifications

Recorded 2026-09-21, before any Design existed.

- **Q: Must the block message say the spec is not in your working tree?** **A: yes, name the
  discrepancy.** Otherwise the author reads "every task in `.specs/<slug>/spec.md` is ticked"
  about a file they cannot see. Recorded as AC7. The cost anticipated when asking — teaching
  `gate_spec_review_state` to report which tree it read, across three callers — is not paid: the
  Design has the caller choose the tree, so the caller already knows and says so itself.
- **Q: In that state, where is the receipt read from?** **A: the same committed tree as the
  spec.** Reading the two halves of one question from two different trees is the exact shape of
  this bug. The consequence is accepted and stated: with `.specs/` absent from the working tree,
  a freshly written receipt does not clear the block until it is committed, which fails closed.
  Recorded as AC8.
- **Scope, decided before drafting:** this spec is #177 alone, though backlog row 1 groups
  #176 with it. One issue stays one spec, one branch and one PR.
- **Two questions were considered and dropped as details**, because both readings led to the
  same design: what happens under a detached `HEAD` (`branch` is the literal `HEAD`, so
  `.specs/HEAD/spec.md` is in neither tree and case 77 is untouched either way), and whether the
  fallback belongs in `gate_spec_review_state` rather than its caller (it does not — the
  pull-request check passes a ref precisely because it has no working tree to fall back to).

## 2. Design (HOW)

- **Fix approach, and why this rather than the narrower or wider fix.** `check_current_branch`
  stops treating "not on disk" as "nothing to gate". When `.specs/$branch/spec.md` is absent
  from the working tree it asks the branch's own tree — the spec is its branch's first commit,
  so that is where it lives whenever the working tree does not have it — and reads the spec and
  the receipt from `HEAD` by passing the ref `gate_spec_review_state` already accepts. When the
  file is in neither tree the path returns 0 exactly as it does today. The scan keeps skipping
  by name, unchanged.

  The narrower fix is the one the issue suggested and the backlog costed: stop skipping by name,
  and let the scan read the current ref from its own tree like any other branch. It was rejected
  on AC7. The scan reports in the third person, under a headline that says *"on a branch other
  than the one this turn is on"* — so that fix has to change the frozen sentence every user
  reads today, invert its meaning for one case, and still find somewhere third-person to say
  "this is not in **your** working tree". The remedy is second-person advice to the person
  standing on the branch, so it belongs in the second-person path. **This fires the trigger
  recorded in `docs/BACKLOG.md` — "#177 turning out to need the current-branch path rewritten
  rather than the scan's skip removed"** — and the honest report is that half of it fires: the
  fix is in the current-branch path rather than in the scan, so the trigger's premise holds,
  but neither of its two consequences does. Row 1 is not two issues, because #176 was split out
  above, and #26's frozen messages are not rewritten — every existing message is byte-identical
  when the spec is in the working tree, which is what the six appended `$note` expansions below
  are for. Whether that leaves the row above #81 is a grooming's call, not this spec's; it is
  named here so the ninth grooming does not have to re-find it.

  The wider fix — one dispatcher that reads every branch, current or not, from one predicate —
  is the right end state and is not this change. It rewrites both messages and both paths to
  close a defect that is one branch wide and already backstopped in CI.

- **Affected files:**
  - `hooks/review-gate.sh` — `check_current_branch` only. Three edits: the fallback read, the
    slug check gated to the working-tree read, and `$note` appended to the six `gate_block`
    messages. `$note` is empty on every path that exists today, and appended with no separator,
    so today's messages are unchanged character for character.
  - `scripts/test-gates.sh` — new cases, continuing the file's global numbering.
  - `docs/DESIGN.md` — the `Unreviewed work` row names the turn-end gate's two readers; it
    gains the fact that the first of them reads two trees.
  - `hooks/review-gate.sh`'s header comment — it states what the gate's domain is, and the
    domain is what changes.

- **The slug check is deliberately gated, not widened.** `case "$branch" in [0-9]*)` fires
  before the merged-work skip, so widening it to committed-only specs adds a path where a
  legacy branch blocks on install — the false block #26's comments argue hardest against. Its
  own comment says it is "a rule about the spec you are authoring now", and a spec that is not
  in your working tree is not one you are authoring now. So it runs when the working tree
  answered and not when the fallback did, which is the rule's own sentence applied rather than
  an exception carved for it.

- **Order inside the function is unchanged:** presence, then slug, then the merged-work skip,
  then the state. The fallback only changes what "presence" consults and which tree the state
  is read from, so AC6 holds for free — `gate_work_reached_base` reads git objects and never
  the working tree, and it still runs before any state is computed.

- **Blast radius:**
  - `gate_spec_review_state` keeps its signature and its six states. `check-unreviewed-work.sh`
    and `scan_other_branches` are untouched, and the three callers still ask one question.
  - The `case` in `check_current_branch` gains no arm, so **#176 is neither fixed nor worsened**
    here. Appending `$note` to six messages does put six edits in the block it will restructure;
    that is the whole of the overlap, and it is why #176 should follow this rather than precede
    it.
  - A detached `HEAD` yields the literal branch name `HEAD`, so the fallback asks
    `HEAD:.specs/HEAD/spec.md`, gets nothing, and returns 0 — case 77 is untouched.
  - A repository with no commits fails the fallback's existence test and returns 0.
  - The new block fires on a state nobody reaches today without an unusual working tree, so the
    false-block surface added is: a branch whose committed spec is finished and unreviewed, and
    whose author has arranged not to see it. That is the bug.

- **Why this cannot recur.** The two readers now decline on the same predicate. Before, the
  current-branch reader declined when the spec was absent **from the working tree** while the
  scan declined when it was absent **from the ref's tree**, and a branch could satisfy the first
  without satisfying the second — that difference *is* the defect, and no amount of care about
  the skip removes it while the two tests differ. After, both ask "is there a spec for this
  branch at all", and the current-branch reader answers it over both trees, so the partition
  has no gap left to fall into. The cases in T2 and T3 pin the four cells of
  {spec in working tree} × {spec in committed tree} on the current branch. **Three of the four
  go red under a named mutation and the fourth does not**, which is recorded in the case rather
  than glossed: with a spec in neither tree the silence is over-determined — every local
  mutation of the predicate still ends at `gate_spec_review_state` returning the empty state —
  so that case constrains the next change to this function (#176's default `*)` arm, and any
  refactor that gives "no spec at all" a state name) rather than this one. The other three go
  red on the cell an edit drifts into.

## 3. Tasks (TDD-ordered)

> One task is one complete Red-Green-Refactor cycle, so one green commit. No task is sequenced
> after the review.

- [x] T1: regression test that fails for the right reason — a current branch whose committed
      spec is finished and unreviewed while the working tree has no `spec.md` must block on both
      channels and say the file is not in the working tree — then the fix in
      `check_current_branch`: the fallback read from the branch's own tree, the slug check gated
      to the working-tree read, and `$note` on the six messages. Record the case's red capability
      as a named mutation. (AC1, AC2, AC7)
- [x] T2: the working tree still wins, pinned in both directions — a working-tree copy with an
      open task is silent though the committed copy is ticked, and a ticked working-tree copy
      blocks though the committed copy has an open task. These two cells and T1's are three of
      the four in the matrix the Design names. (AC4)
- [x] T3: the silences the fix may not take away — the fourth cell, a current branch with no
      spec in either tree, and a squash-merged branch whose working tree lacks the spec. (AC3, AC6)
- [x] T4: the receipt comes from the same tree as the spec — a committed CLEAN receipt keeps the
      branch silent, and one written only into the working tree does not clear the block. (AC8)
- [x] T5: refactor — the header comment of `hooks/review-gate.sh` states the domain it now
      covers, and `docs/DESIGN.md`'s `Unreviewed work` row records that the turn-end gate's
      first reader reads two trees. Run the full validator list. (AC9)
