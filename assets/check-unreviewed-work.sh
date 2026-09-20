#!/bin/sh
# check-unreviewed-work.sh — fail a pull request that carries finished, unreviewed work.
#
# The turn-end review gate is a fast local signal, and it has two limits a guarantee cannot
# have: a hook can be switched off, and until #26 it asked only about the branch HEAD pointed
# at, so `git checkout main` silenced it. This asks the same question where neither move is
# available. A pull request has no working tree to step out of: its head branch and head
# commit come from the event, not from wherever the checkout happens to be standing.
#
# Usage:  check-unreviewed-work.sh [<branch> [<commit>]]
#
#   In CI, pass both, from the pull-request event — `actions/checkout` leaves a pull request
#   on a detached merge ref, so a checker reading HEAD would be asking about a commit that
#   exists nowhere else. With no arguments it asks about the current branch, which is what is
#   wanted when a person runs it by hand.
#
# Deliberately NOT a turn-end validator. `quality-gate.sh` runs the `- Validators:` line on
# every turn a source path changed, and the review gate already asks this question there, in
# a message written for the person whose turn it is. Running it twice per turn would buy
# nothing and would put a second, differently worded block in the same place.
set -u

if root=$(git rev-parse --show-toplevel 2>/dev/null); then
  cd "$root" || exit 1
else
  echo "check-unreviewed-work: not inside a git repository, so there is no pull request to check." >&2
  exit 1
fi

# gate-lib.sh is `hooks/` in the harness repo and `.claude/hooks/` in a project. Finding it is
# the problem that produced #16, so this FAILS when it cannot — a guard that skips because it
# could not locate its own dependency is the bug this script exists to prevent.
lib=""
for d in hooks .claude/hooks .agents/hooks; do
  [ -f "$d/gate-lib.sh" ] && { lib="$d/gate-lib.sh"; break; }
done
if [ -z "$lib" ]; then
  echo "check-unreviewed-work: cannot find gate-lib.sh in hooks/, .claude/hooks/ or .agents/hooks/." >&2
  echo "  Without it this check cannot ask the question the gate asks, and a guard that cannot" >&2
  echo "  do its job must not report success. See #16." >&2
  exit 1
fi
# shellcheck source=/dev/null
. "$lib"

# Finding the file is not the same as finding the question. Every project installed before
# #26 has a gate-lib.sh without it, and without this the state comes back empty and the
# pull request passes — the exact fail-open this check exists to close.
if ! command -v gate_spec_review_state >/dev/null 2>&1; then
  echo "check-unreviewed-work: $lib has no gate_spec_review_state — it predates the shared question (#26)." >&2
  echo "  Re-copy the plugin's hooks/gate-lib.sh over it and run this again." >&2
  exit 1
fi

branch=${1:-$(git rev-parse --abbrev-ref HEAD 2>/dev/null)}
if [ -z "$branch" ] || [ "$branch" = HEAD ]; then
  echo "check-unreviewed-work: no branch name available — pass the pull request's head branch as the first argument." >&2
  exit 1
fi

sha=${2:-}
if [ -z "$sha" ]; then
  sha=$(git rev-parse --verify -q "$branch^{commit}" 2>/dev/null) || sha=""
fi
if [ -z "$sha" ]; then
  echo "check-unreviewed-work: cannot resolve a commit for '$branch'." >&2
  exit 1
fi

spec=".specs/$branch/spec.md"
short=$(git rev-parse --short "$sha" 2>/dev/null || printf '%s' "$sha")

# Asked separately from the state below, and only to choose the wording. "Nothing to check"
# and "checked, and clean" must not share a sentence: that is #16's shape, and a guard that
# reports a success it did not earn is what #39 is open about.
if ! git cat-file -e "$sha:$spec" 2>/dev/null; then
  echo "check-unreviewed-work: branch '$branch' carries no spec at $spec in $short — no review to demand, and nothing else examined."
  exit 0
fi

state=$(gate_spec_review_state ".specs/$branch" "$sha" "$sha")

if [ -z "$state" ]; then
  echo "check-unreviewed-work: $spec at $short holds no finished, unreviewed work."
  exit 0
fi

reviewer=$(gate_steering_value .steering/tech.md Reviewer)
[ -n "$reviewer" ] || reviewer="the reviewer named in .steering/tech.md"

echo "check-unreviewed-work FAILED" >&2
echo "  $branch — $(gate_review_state_sentence "$state")" >&2
echo "" >&2
echo "  This pull request carries finished work that no review covers. The turn-end gate can be" >&2
echo "  switched off and HEAD can be moved; a pull request can do neither. Run $reviewer against" >&2
echo "  $short, write its Receipt block to .specs/$branch/.review-receipt, and push that commit." >&2
exit 1
