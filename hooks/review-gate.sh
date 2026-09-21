#!/bin/sh
# review-gate.sh — the harness's one enforced rule.
#
# Everything else here is guidance a model can decline. This is the rule that
# holds: finished work cannot sit in this repository without a fresh, clean review.
#
# It asks that about the REPOSITORY, not about where HEAD happens to point, and not about
# which files happen to be checked out. Those are three questions, and the gate has had to be
# taught each of them in turn. Until #26 only the first was asked: on a branch with no spec the
# gate exited 0 and printed nothing, so `git checkout main` turned the one enforced rule off
# and left no trace — a skipped review and a clean repository produced identical silence. #26
# left the third behind, one branch wide: the branch you stand on was read from the working
# tree and then skipped by name in the scan, so the same silence was still available by
# emptying the tree instead of moving HEAD. #177 closed it, and check_current_branch carries
# the reasoning.
#
# It is still deliberately narrow. A gate that fires on ordinary turns is a gate people
# disable, and a disabled gate protects nothing — so this is silent on every case that is not
# the one it exists for. What it is not is narrow in a way the author chooses per turn.
set -u

DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
. "$DIR/gate-lib.sh"

git rev-parse --git-dir >/dev/null 2>&1 || gate_pass
if repo_root=$(git rev-parse --show-toplevel 2>/dev/null); then
  cd "$repo_root"
fi
branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null) || gate_pass

reviewer=$(gate_steering_value .steering/tech.md Reviewer)
[ -n "$reviewer" ] || reviewer="the reviewer named in .steering/tech.md"

# Already-merged work has nothing left to review. What that buys is narrower than this comment
# used to claim, and the difference matters to anyone changing the skip: it said every
# historical feature branch would trip the gate on install, and that case cannot occur. A
# branch with no spec of its own is already silent whatever the merge style, and by two
# different routes: the current-branch path returns before reaching any of this, when the spec
# is in neither the working tree nor the branch's own tree, while the scan consults ancestry
# first and then gets an empty state back from gate_spec_review_state. Cases 83 and 148 pin the
# first — 148 is the one that reads both trees, since #177 — and case 144 the second. Cases 1-7 were cited
# for the second and do not reach it — their only other ref is main, which IS an ancestor of
# itself, so the scan skips it before asking. The branch that needs this skip is one that
# shipped WITH a spec and was not deleted — which, in a squash-merging repository, is every
# branch anyone has merged. #182 measured that and corrected the sentence.
#
# The candidate list is longer since #26 widened the scan, because an unresolvable base costs
# far more than it used to. It used to mean one false block, while you stood on your own
# merged branch; now it means the merged check never fires for ANY branch, so every shipped
# but undeleted spec branch blocks every turn from everywhere. `master` is the common case
# that was missing, and a repository with no remote at all has no origin/* to fall back on.
#
# Both skip sites below ask two questions of this base, not one: was the COMMIT joined into its
# history, and did the WORK reach it. The second exists because a squash merge answers no to
# the first forever — #182, and gate_work_reached_base carries the reasoning.
base=$(git rev-parse --verify -q origin/HEAD 2>/dev/null \
     || git rev-parse --verify -q origin/main 2>/dev/null \
     || git rev-parse --verify -q origin/master 2>/dev/null \
     || git rev-parse --verify -q main 2>/dev/null \
     || git rev-parse --verify -q master 2>/dev/null) || base=""

# The branch you are standing on, with the messages written in the second person because you
# are the person who can act on them. Every exit from here is a `return`, never a pass: the
# repository-wide pass below must run whatever this one concludes, or each of its early
# returns is another way to be standing somewhere the gate does not look.
check_current_branch() {
  spec=".specs/$branch/spec.md"

  # Which tree answers for this branch, and why there are two of them.
  #
  # The working tree is read first, deliberately: a spec edited and not yet committed is the
  # state its author is in for most of the spec's life, and #26 chose to count it.
  #
  # What that USED to mean is that an absent file ended the question — and the scan below skips
  # this ref BY NAME, on the understanding that this path has answered for it. So the one branch
  # read from the working tree was the one branch nobody read from its own tree, and a spec
  # committed on the branch but missing from the tree in front of you was silent on both paths
  # while every other branch in the same repository was read from its tree and reported. Nobody
  # has to delete anything for that: a sparse checkout excluding `.specs/`, or a partial
  # worktree, is the same state. #177 — and it is #26's own sentence, the author choosing what
  # the gate looks at, narrowed to one branch and reached through the tree rather than HEAD.
  #
  # The fix is not a second place to look so much as one question asked once: both readers now
  # decline on "is there a spec for this branch at all" rather than on two different tests of
  # it. A spec is its branch's FIRST commit, so the branch's own tree is where it lives whenever
  # the working tree does not have it.
  tree=''                             # empty — gate_spec_review_state reads the working tree
  note=''
  if [ ! -f "$spec" ]; then
    # Under a detached HEAD `branch` is the literal `HEAD`, so this asks for
    # `HEAD:.specs/HEAD/spec.md`, gets nothing, and returns — case 77 is unchanged and the scan
    # goes on reporting the real branches. A repository with no commits returns here too.
    git cat-file -e "HEAD:$spec" 2>/dev/null || return 0   # in neither tree — nothing to gate
    tree=HEAD
    # Appended to every block below. The remedy names a file the author cannot see, so the
    # message has to say why it is not there and which tree the answer came from; without it the
    # block reads as the gate inventing a file, and a gate that looks broken is a gate switched
    # off. Empty on every path that existed before this change, and appended with no separator,
    # so those messages are unchanged character for character.
    note=" ($spec is not in your working tree, so the gate read it — and the receipt — from this branch's own tree at HEAD. A sparse checkout, a partial worktree, or a deletion nobody committed produces that, and it means a receipt written into the working tree alone does not clear this until it is committed.)"
  fi

  # No issue, no spec. The slug is <issue-number>-<kebab-title>, so a spec directory
  # without a numeric prefix is work that never had an issue — unplanned work that
  # entered through the side door and bypassed whatever decided the sprint. This is
  # checkable without touching the network, so it is checked.
  #
  # Current-branch only, on purpose: it is a rule about the spec you are authoring now, and
  # asking it of every directory in .specs/ would fire forever on anything predating it.
  #
  # Asked of the working-tree read ONLY, which is the same sentence applied rather than an
  # exception carved out of it: a spec that is not in your working tree is not one you are
  # authoring now. It also matters where this sits — before the merged-work skip — so widening
  # it to the fallback would block on branches that shipped long ago, which is the false block
  # that skip exists to prevent.
  if [ -z "$tree" ]; then
    case "$branch" in
      [0-9]*) : ;;
      *) gate_block "No issue, no spec: the branch '$branch' has a spec at $spec but its slug does not start with an issue number. The slug is <issue>-<kebab-title>, and the issue is what recorded that this work was chosen. Create the issue and rename the branch and spec directory to match, or say explicitly that this is acknowledged unplanned work." ;;
    esac
  fi

  receipt=".specs/$branch/.review-receipt"
  head=$(git rev-parse HEAD 2>/dev/null || echo '')

  # Two arms, because there are two ways work reaches the base and only one of them leaves a
  # parent link. Ancestry is kept and asked first: it is exact when it fires, costs one call,
  # and is the whole of the merge-commit and fast-forward case on the path those projects
  # already take. The second arm is #182 — see gate_work_reached_base.
  if [ -n "$base" ] && { git merge-base --is-ancestor HEAD "$base" 2>/dev/null \
       || gate_work_reached_base "$branch" "$head" "$base"; }; then
    return 0
  fi

  # Two ways there is nothing to review, indistinguishable in a count of unticked boxes alone
  # — which is why that count used to block a spec still being drafted while telling its
  # author that every task was ticked:
  #
  #   no checkboxes at all   the Tasks section is a placeholder; nothing has been written yet
  #   some still unticked    implementation is in progress
  #
  # Neither is the moment to demand a review. Both are an empty state below.
  state=$(gate_spec_review_state ".specs/$branch" "$head" "$tree")
  case "$state" in
    '')
      return 0 ;;
    unreadable)
      # A spec that exists but cannot be read is NOT the same as a spec with nothing in it,
      # and the difference is invisible downstream: both task counters come back 0 for a file
      # they cannot open, and a zero total is read as "nothing authored, stay silent". Fail
      # closed — an unreadable spec is a broken working tree, not an empty one.
      gate_block "Review gate: $spec exists but cannot be read, so the gate cannot tell whether this branch has been reviewed. Fix the file's permissions and re-run rather than treating this as a pass.$note" ;;
    no-receipt)
      gate_block "Review gate: every task in $spec is ticked, but no reviewer receipt exists. Run $reviewer on the branch diff, then write its Receipt block to $receipt. If $reviewer is already running, wait for it and write the receipt from its result — do not start a second one.$note" ;;
    receipt-unreadable)
      gate_block "Review gate: $receipt exists but cannot be read, so the gate cannot tell whether this branch has been reviewed. Fix the file's permissions and re-run rather than treating this as a pass.$note" ;;
    verdict=*)
      gate_block "Review gate: the recorded review verdict is '${state#verdict=}', not CLEAN. Address every BLOCKER and HIGH finding, re-run $reviewer, and update $receipt.$note" ;;
    unresolved-sha=*)
      gate_block "Review gate: $receipt records reviewed_sha '${state#unresolved-sha=}', which cannot be resolved in this repository, so the gate cannot tell whether the review covers the code that is here now. Re-run $reviewer and rewrite $receipt rather than treating an uncheckable receipt as a pass.$note" ;;
    stale=*)
      rest=${state#stale=}
      gate_block "Review gate: source changed since the recorded review (${rest%% *}): ${rest#* }. Re-run $reviewer and update $receipt before opening the PR.$note" ;;
  esac
}

# Every other branch. This is the half #26 was missing, and the reason it reads branches
# rather than globbing `.specs/` is that the spec is its branch's FIRST commit: from anywhere
# else, the directory does not exist in the working tree at all. A scan of `.specs/` would
# therefore find nothing and report it as cleanliness — the same silence, one layer deeper.
scan_other_branches() {
  found=''
  for ref in $(git for-each-ref --format='%(refname:short)' refs/heads/ 2>/dev/null); do
    [ "$ref" = "$branch" ] && continue
    tip=$(git rev-parse --verify -q "$ref^{commit}" 2>/dev/null) || continue
    if [ -n "$base" ] && { git merge-base --is-ancestor "$tip" "$base" 2>/dev/null \
         || gate_work_reached_base "$ref" "$tip" "$base"; }; then
      continue                        # shipped — case 8's reasoning, one branch over
    fi
    state=$(gate_spec_review_state ".specs/$ref" "$tip" "$ref")
    [ -n "$state" ] || continue
    found="$found
  $ref — $(gate_review_state_sentence "$state")"
  done

  [ -n "$found" ] || return 0

  # Held in a variable rather than expanded inline. `${base:-TEXT}` substitutes the VALUE of
  # base whenever base is set and non-null — and line 41 always sets it — so the inline form
  # appended the base sha to every block instead of a note to none of them.
  nobase=''
  [ -n "$base" ] || nobase='

(This repository has no resolvable default branch — origin/HEAD, origin/main, origin/master, main and master are all missing — so the gate cannot tell which of these branches have already shipped, and is naming them all.)'

  # "a branch you are not standing on" would be false under a detached HEAD, which is a path
  # this deliberately blocks (case 77): `git rev-parse --abbrev-ref HEAD` yields the literal
  # `HEAD`, so the branch you are detached at is reported like any other.
  gate_block "Review gate: this repository holds finished work that nobody has reviewed, on a branch other than the one this turn is on:
$found

The gate asks what this repository contains, not which branch HEAD points at, so moving HEAD does not clear this and neither does a detached checkout. For each branch above: run $reviewer against it and write the receipt, merge it, or delete the branch if the work is abandoned.$nobase"
}

check_current_branch
scan_other_branches
gate_pass
