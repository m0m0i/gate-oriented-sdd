# Spec: the gates find a branch's spec from what the branch carries, not from its name
- Slug: 316-gates-find-a-spec-only-by-branch-name   Issue: 316   Type: bug   Status: approved
- Author: m0m0i   Date: 2026-10-17

## 1. Requirements (WHAT / WHY)
- Reproduction: on a branch whose name is not the spec's slug, write a finished spec where `spec` writes it, `.specs/<n>-<slug>/spec.md`, with every task ticked. Change a source file, commit, and end the turn. Three ordinary shapes: branch `feature/12-x` with `.specs/12-x/spec.md`; a typo in the branch name; the spec archived to `.specs/_archive/12-x/` on its own branch.
- Expected: the review gate blocks, because the branch carries finished work nobody reviewed. The scan names the branch from any other branch, and CI fails its pull request. `- Owns: gates never fail open`.
- Actual: the turn ends, the scan passes, and CI passes, all with no review. CI prints "carries no spec … nothing else examined" and exits 0.
- Impact: any project whose branches carry a prefix reaches this, and `init` invites the operator to confirm their own branch convention (#129). So does a typo, or an archive made before merge. It is reached with nothing damaged, on the gate the harness exists to enforce. The deep review measured it (`docs/reviews/2026-10-11-deep-review.md` §1, item 5).
- **Root cause:** the flow names the spec directory and the branch alike by convention (`skills/spec/SKILL.md` step 1), and every reader uses the branch name as the spec's address. Nothing derives a spec from what the branch carries:
  - the current-branch check reads `.specs/$branch/spec.md` (`hooks/review-gate.sh:332`, `:434`);
  - the scan reads `.specs/$slug` with `slug` the branch name (`:521`);
  - CI reads `.specs/$branch/spec.md` (`assets/check-unreviewed-work.sh:138`, `:157`);
  - the shipped-branch skip, `gate_work_reached_base`, looks for the branch name's spec in the base (`hooks/gate-lib.sh:931-935`).

  When the convention is broken each reader asks for a path that does not exist. `_gate_read` answers "absent", and `gate_spec_review_state` reads absent as "no spec, nothing to demand". The silence is the designed answer to a question asked about the wrong path.
- Acceptance criteria:
  - [ ] **AC1:** WHEN the branch HEAD is on carries a spec the branch added, under a directory not named for the branch, finished and with no usable review, THE review gate SHALL block, naming that spec's directory and receipt path. This covers all three shapes in the reproduction, and a spec still only in the working tree, which #26 counts.
  - [ ] **AC2:** WHEN such a branch is not the one HEAD is on THE scan SHALL name it, from any other branch.
  - [ ] **AC3:** WHEN a pull request's head carries such a spec, `check-unreviewed-work.sh` SHALL exit 1, naming it.
  - [ ] **AC4:** All three readers SHALL take a branch's specs from one definition in `hooks/gate-lib.sh`: the spec files its diff against the base adds (Q1). Each SHALL also keep today's name match, so no reader checks fewer specs than it does now.
  - [ ] **AC5:** THE SYSTEM SHALL add no block on any of these:
    - a branch that moves or edits a spec the base already carries, such as an `archive` sweep or a typo fix in a shipped spec;
    - the base branch itself;
    - a branch whose specs all reached the base, whatever its name. The shipped skip (#182) uses the derived specs, so a squash-merged `feature/12-x` is skipped as shipped.
  - [ ] **AC6:** WHEN git cannot list a branch's specs THE SYSTEM SHALL fail closed: the gate blocks and CI exits 1, saying that it could not tell which specs the branch carries. A failed listing is never read as "no spec".
  - [ ] **AC7:** "No issue, no spec" (`hooks/review-gate.sh:408-413`) SHALL judge the spec's directory name, which is the slug, rather than the branch name.
  - [ ] **AC8:** the regression tests fail before the fix and pass after: one case per reproduction shape and per reader, plus AC5's no-block cases and AC6's failed listing.
  - [ ] **AC9:** every statement of how a gate finds a spec agrees with the code: the readers' comments, `docs/DESIGN.md`, `docs/fidelity.md`, and both READMEs where they say it.
- Out of scope:
  - #129, the `init` prose half: what `init` says about branch naming;
  - #298, the scan blocking on another worktree's branch while it is mid-review. It changes the same scan, and it stays its own spec;
  - #301, CI reading its globs and its own script from the pull request it judges;
  - the slug rule in `spec` and `implement` (Q3).

### Clarifications
Asked 2026-10-18. The maintainer took the recommended answer each time.

- **Q1: which spec files count as a branch's own, beyond the name match?** Every `spec.md` that the diff from the merge base to the tip adds, under `.specs/<d>/` or `.specs/_archive/<d>/`, with rename detection on. A spec the base already had and the branch moved is a rename, not an add, so an `archive` sweep adds no block. A spec the branch only edited is not counted either, so a typo fix in a shipped spec adds no block. Rejected: "added or edited", which pulls a shipped spec into any branch that touches it and reads its old receipt as stale; and "every spec the base tip lacks", which loses a merged-then-continued branch's spec (case 134) once the squash puts it in the base (AC4, AC5).
- **Q2: a diff carrying two or more specs?** Each is judged on its own, and the block names every one that holds finished work with no usable review. Rejected: blocking any branch with two specs, a new process rule with a false-block cost (AC1–AC3).
- **Q3: the slug rule in `spec` and `implement`?** It stays, and is out of scope. The gates stop depending on it, and #129 decides what a project with a forced branch prefix is told.

Decided without asking, because the repository answers them:
- **No resolvable base** (no `origin/HEAD`, `origin/main`, `origin/master`, `main` or `master`): the name match alone, which is today's behaviour. The scan already says it cannot tell what shipped there.
- **No common ancestor** (an orphan branch, such as `gh-pages`): `git merge-base` exits 1 having printed nothing, and the diff runs against the empty tree. Every other failure fails closed (AC6).
- **A detached HEAD or an unborn branch:** the current-branch check keeps the name match only. Case 77 (the scan still reports every real branch) and case 175 are unchanged, and a bisect over old commits is not blocked.
- **The current branch counts the working tree**, which #26 chose: tracked changes against the merge base, plus untracked `spec.md` files under `.specs/` that `.gitignore` does not exclude.
- **CI's base** is an optional third argument, the event's `pull_request.base.sha`. Without it, the check uses the same candidate list as the gate. That list moves from `review-gate.sh` into the library, so the three readers share it. An existing two-argument workflow keeps working.
- **The shipped skip:** a branch is skipped as shipped when its tip is an ancestor of the base, or when `gate_work_reached_base` holds for **every** slug it carries, derived or name-matched. Every, not any, because a skip that fires less is the safe way to be wrong (#182).

## 2. Design (HOW)
- **Fix approach: one library function that lists a branch's specs, read by all three readers.** Fixing the three lookups alone would leave the shipped skip asking for the branch name's spec in the base, so a squash-merged `feature/12-x` would stay in the scan forever: #182's permanent block, back for every branch not named for its slug. The narrower fix, adding `.specs/_archive/$branch` and a prefix strip, fixes two of the three reproduction shapes and none of the typos.
  - `gate_default_base` in `hooks/gate-lib.sh`: the candidate list now at `review-gate.sh:321-325`, moved unchanged.
  - `gate_branch_specs <base sha> <tip sha | empty for the working tree> <branch name>` prints one spec directory per line, such as `.specs/12-x` or `.specs/_archive/12-x`. Its status:
    - 0 when it read: the list is the union of the name match (`.specs/<branch>`, when that spec is in the tree read) and the directories whose `spec.md` the diff adds;
    - 2 when git could not tell. The caller blocks.
  - The diff is `git diff --no-ext-diff --no-color -M --name-only --diff-filter=A -z <merge base> <tip> -- .specs/`. `--name-only` rather than `--name-status`: the filter already says every entry is an add, and a list of paths alone cannot fall out of step the way status-and-path pairs can. It is limited to `.specs/`, so rename detection compares spec files only, and the cost is one small diff per branch.
  - For the working tree, three lists: the committed adds from the merge base to HEAD, the adds from the merge base to the working tree, and untracked `spec.md` files. The first is what #177 reads when the working tree lacks a committed spec, and the second is what #26 counts.
  - The current branch derives nothing when HEAD is an ancestor of the base, which is the base branch itself and any branch with no commit of its own. Both are skipped as shipped already, so derivation could only add the "No issue, no spec" check to them (AC5).
  - The merge base comes from `git merge-base <base> <tip>`, with exit 1 and no output read as the empty tree.
- **`hooks/review-gate.sh`**
  - `check_current_branch` loops over the listed specs. Per spec it keeps today's working-tree-then-own-tree choice (#177), the `note` and `cause` sentences, and the state messages, with `$spec` and `$receipt` naming the listed directory.
  - Several blocking specs become one `gate_block` holding each one's message.
  - "No issue, no spec" judges the slug: the directory under `.specs/`, with `_archive/` stripped. Not `${dir##*/}`, which reads `sub` for the slashed slug `12-feat/sub` that case 179 pins. For working-tree specs only, as today.
  - `scan_branch` keeps the ancestry check first, which is cheap and exact, then lists the branch's specs. It skips on none, or on `gate_work_reached_base` holding for every slug, and otherwise joins `found` with one line per spec holding finished, unreviewed work.
- **`assets/check-unreviewed-work.sh`**
  - Takes an optional third argument, the base sha, verified like the head sha. Without it, `gate_default_base`.
  - Lists the head's specs and fails naming each blocking one. "Carries no spec" prints only when the list is empty.
  - A library without `gate_branch_specs` exits 1 with a re-copy instruction, as the `gate_tree_names` guard does.
  - `.github/workflows/ci.yml` and `init` step 3's CI line pass `${{ github.event.pull_request.base.sha }}`.
- **`hooks/gate-lib.sh`'s `gate_work_reached_base`** is unchanged in shape. It already takes a slug, and its callers now pass each listed slug, with `_archive/` stripped, instead of the branch name.
- **Docs (AC9)**
  - `skills/archive/SKILL.md:12`, which describes the bug as how things work ("silences the gate for that branch entirely"), now says what happens: the gate follows the moved spec.
  - The `docs/DESIGN.md` "Unreviewed work" row.
  - The readers' comments that say a spec is found by the branch's name (`review-gate.sh:474-477`, `gate-lib.sh:724`).
  - Both READMEs and `docs/fidelity.md`, where they state it. A `git grep` at T4 settles which.
- **`hooks/steering-digest.sh`**, a fourth reader the design above missed and T4's recurrence case found. It builds `.specs/$branch/spec.md` to tell each new session which spec is active. On `feature/12-x` it says the branch has no spec directory, while the gate blocks on `.specs/12-x`. It lists the working tree's specs through `gate_branch_specs` under the current-branch check's rules, and names each one. Antigravity's digest runs this script, so it follows.
- **Affected files:** `hooks/gate-lib.sh`, `hooks/review-gate.sh`, `hooks/steering-digest.sh`, `assets/check-unreviewed-work.sh`, `.github/workflows/ci.yml`, `skills/init/SKILL.md`, `skills/archive/SKILL.md`, `scripts/test-gates.sh`, `docs/DESIGN.md`, and docs as T4 finds them.
- **Blast radius:**
  - Every message that named `.specs/<branch>/` now names the directory found, so the existing cases asserting those messages are re-read in T1.
  - The silence cases must stay silent: 77, 83, 144, 148, 171, 172, 175, and the #182 shipped-skip cases 134 and 139–143.
  - The scan gains one diff per branch that is not an ancestor of the base. That is a second cost beside the `rev-list` the backlog row records, and T2 measures it on the existing timing fixture.
  - A branch stacked on another unmerged spec branch carries that spec too, and is judged on it. The lower spec's receipt reads stale at the upper tip, so the upper branch blocks until it is rebased onto a base the lower spec has reached. The flow branches from the default branch (`implement`'s preconditions), so stacking is off the flow, and the block is the safe direction. Excluding specs the base carries would remove it, and would also silence a squash-merged `feature/12-x` that carried on, which is case 134's fail-open (Q1).
  - Antigravity projects copy `gate-lib.sh` beside the gates and re-copy all five together, so a mixed pair is the existing failure that the README's migration note covers. The copied CI check gets its own guard.
- **Why this cannot recur:**
  - No reader composes a spec path from a branch name except through `gate_branch_specs`. A `test-gates.sh` case reads the shipped shell for `.specs/$branch` or `.specs/$slug` outside that function, the shape check case 204 uses for globs, and goes red if one returns.
  - The regression cases drive each reproduction shape through each reader.
- **Version:** `hooks/`, `assets/` and `skills/` are shipped, so the bump lands after the review receipt. It is a minor version: the gates block on branches they passed, and the CI check takes a new argument.

## 3. Tasks (TDD-ordered)
> One task is one complete Red-Green-Refactor cycle, so one green commit. No task is sequenced after the review.
- [x] T1: AC1, AC6, AC7 on the current branch. Red: cases for the three reproduction shapes and a working-tree-only spec, each passing today. Also a `git diff` that fails, and a spec directory with no issue number on a branch that has one. Then the fix: `gate_default_base` and `gate_branch_specs` in the library, and `check_current_branch` looping over the list. Green, with the blast-radius silence cases unchanged.
- [x] T2: AC2, AC5 in the scan. Red: a `feature/12-x` branch named from `main`; two unreviewed specs on one branch, both named. Guard cases that must stay silent: a squash-merged `feature/12-x` skipped as shipped, an `archive` sweep branch, and a typo fix in a shipped spec. Then `scan_branch` and the per-slug shipped skip. Green, with the scan's added cost measured and recorded here.
  - Measured at T2 on a `git fast-import` fixture of 20,000 commits and 100 unmerged spec branches. The gate took 7.0 s before and 11.8 s after, two runs each, which is about 48 ms for each branch that is not an ancestor of the base. Per call: `git merge-base` 25 ms, the `.specs/` diff 10 ms, and the name match's `ls-tree` 7 ms. The merge base repeats the walk the ancestry check makes just before it, and folding the two into one call would save about half. That belongs with the batched history walk docs/BACKLOG.md row 1 records for `gate_work_reached_base`.
- [x] T3: AC3 and AC6 in CI. Red: the CI check on each reproduction shape, with and without the base argument, and on a library with no `gate_branch_specs`. Then `check-unreviewed-work.sh`, `ci.yml`, and `init` step 3's CI line. Green.
- [ ] T4: AC4's recurrence case (no `.specs/$branch` outside `gate_branch_specs`) and AC9's docs: `skills/archive/SKILL.md`, `docs/DESIGN.md`, the readers' comments, and whichever README and fidelity statements `git grep` finds. Full Validators line green.
