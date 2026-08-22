#!/bin/sh
# review-gate.sh — the harness's one enforced rule.
#
# Everything else here is guidance a model can decline. This is the rule that
# holds: a finished spec branch cannot end a turn without a fresh, clean review.
#
# It is deliberately narrow. A gate that fires on ordinary turns is a gate people
# disable, and a disabled gate protects nothing — so this exits silently on every
# case that is not the one it exists for.
set -u

DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
. "$DIR/gate-lib.sh"

git rev-parse --git-dir >/dev/null 2>&1 || gate_pass
branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null) || gate_pass

spec=".specs/$branch/spec.md"
[ -f "$spec" ] || gate_pass          # not a spec branch — nothing to gate

# No issue, no spec. The slug is <issue-number>-<kebab-title>, so a spec directory
# without a numeric prefix is work that never had an issue — unplanned work that
# entered through the side door and bypassed whatever decided the sprint. This is
# checkable without touching the network, so it is checked.
case "$branch" in
  [0-9]*) : ;;
  *) gate_block "No issue, no spec: the branch '$branch' has a spec at $spec but its slug does not start with an issue number. The slug is <issue>-<kebab-title>, and the issue is what recorded that this work was chosen. Create the issue and rename the branch and spec directory to match, or say explicitly that this is acknowledged unplanned work." ;;
esac

# Already-merged work has nothing left to review. Without this, every historical
# feature branch trips the gate the moment the harness is installed.
base=$(git rev-parse --verify -q origin/HEAD 2>/dev/null \
     || git rev-parse --verify -q origin/main 2>/dev/null \
     || git rev-parse --verify -q main 2>/dev/null) || base=""
if [ -n "$base" ] && git merge-base --is-ancestor HEAD "$base" 2>/dev/null; then
  gate_pass
fi

# Tasks still open means implementation is in progress, which is not the moment
# to demand a review.
[ "$(gate_open_tasks "$spec")" -gt 0 ] 2>/dev/null && gate_pass

receipt=".specs/$branch/.review-receipt"
reviewer=$(sed -n 's/^ *- *Reviewer: *//p' .steering/tech.md 2>/dev/null | head -1)
[ -n "$reviewer" ] || reviewer="the reviewer named in .steering/tech.md"

if [ ! -f "$receipt" ]; then
  gate_block "Review gate: every task in $spec is ticked, but no reviewer receipt exists. Run $reviewer on the branch diff, then write its Receipt block to $receipt."
fi

verdict=$(sed -n 's/^verdict=//p' "$receipt" | head -1)
if [ "$verdict" != "CLEAN" ]; then
  gate_block "Review gate: the recorded review verdict is '${verdict:-missing}', not CLEAN. Address every BLOCKER and HIGH finding, re-run $reviewer, and update $receipt."
fi

sha=$(sed -n 's/^reviewed_sha=//p' "$receipt" | head -1)
head=$(git rev-parse HEAD 2>/dev/null || echo '')
[ "$sha" = "$head" ] && gate_pass

# HEAD moved after the review. That is expected and fine when the trailing
# commits are the work log and the spec's own Status flip. It is not fine when
# reviewable source moved, because then the receipt describes code that no longer
# exists. Source globs come from .steering/tech.md so this stays language-neutral.
globs=$(sed -n 's/^ *- *Source globs: *//p' .steering/tech.md 2>/dev/null | head -1)
[ -n "$globs" ] || globs='*'

# Two ways this used to fail OPEN, both the shell's doing rather than git's, and both
# silent — which is the worst direction for a gate to fail in.
#
#   '*.py'   quotes inside a variable are not removed on expansion, so git received the
#            literal pathspec '*.py' and matched nothing
#   *.py     the shell expanded it against the repository root before git saw it, so a
#            src/-layout project matched nothing and a flat one matched only top level
#
# Strip the quotes, then disable globbing across the word split so the pattern reaches
# git intact. Word splitting is still wanted here: several globs are separated by spaces.
globs=$(printf '%s' "$globs" | tr -d "\"'")
set -f
changed=$(git diff --name-only "$sha"..HEAD -- $globs 2>/dev/null)
set +f

[ -z "$changed" ] && gate_pass

gate_block "Review gate: source changed since the recorded review ($sha): $(echo "$changed" | tr '\n' ' '). Re-run $reviewer and update $receipt before opening the PR."
