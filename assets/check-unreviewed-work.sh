#!/bin/sh
# check-unreviewed-work.sh — fail a pull request that carries finished, unreviewed work.
#
# The turn-end review gate is a fast local signal, and it has two limits a guarantee cannot
# have: a hook can be switched off, and until #26 it asked only about the branch HEAD pointed
# at, so `git checkout main` silenced it. This asks the same question where neither move is
# available. A pull request has no working tree to step out of: its head branch and head
# commit come from the event, not from wherever the checkout happens to be standing.
#
# Usage:  check-unreviewed-work.sh [<branch> [<commit> [<base commit>]]]
#
#   In CI, pass all three, from the pull-request event — `actions/checkout` leaves a pull request
#   on a detached merge ref, so a checker reading HEAD would be asking about a commit that
#   exists nowhere else. The base is the event's `pull_request.base.sha`: the head's specs are
#   the ones it adds against its merge base with that commit (#316). Without it the check uses
#   the gates' own candidate list, so a two-argument workflow keeps working. With no arguments
#   it asks about the current branch, which is what is wanted when a person runs it by hand.
#
# Deliberately NOT a turn-end validator. `quality-gate.sh` runs the `- Validators:` line
# whenever the source has changed since it last passed, and the review gate already asks this question there, in
# a message written for the person whose turn it is. Running it twice per turn would buy
# nothing and would put a second, differently worded block in the same place.
set -u

if root=$(git rev-parse --show-toplevel 2>/dev/null); then
  cd "$root" || exit 1
else
  echo "check-unreviewed-work: not inside a git repository, so there is no pull request to check." >&2
  exit 1
fi

# gate-lib.sh is `hooks/` in the harness repo, `.agents/hooks/` in an Antigravity project, and
# `.claude/hooks/` in a Claude Code project installed before 0.23.0. Since #256 a Claude Code
# project has no copy: its gates run from the plugin, and this check finds the library the way
# each place it runs can say where the plugin is. GATE_SDD_HOOKS is the explicit answer, for CI
# (where `init` has the workflow check the plugin out) and for a terminal outside any Claude
# Code session, and it is read first. $CLAUDE_PLUGIN_ROOT/hooks is what the plugin's own gate
# puts in every validator's environment at turn end. $GATE_SDD_PLUGIN_ROOT/hooks is what the
# plugin's SessionStart hook writes into the session's env file, so the session's own shell —
# `implement`'s loop, a reviewer — has it, where Claude Code documents CLAUDE_PLUGIN_ROOT as
# absent (#264). Each of those two is set in exactly one of the two places, so they cannot
# disagree. Both are read LAST, after the three directories: this repository's sessions carry
# the installed plugin's root too, and a dogfood run must read hooks/ from source rather than
# from an installed copy. Finding the library is the problem that produced #16, so this FAILS
# when it cannot — a guard that skips because it could not locate its own dependency is the bug
# this script exists to prevent — and the failure names every place it looked.
lib=""
if [ -n "${GATE_SDD_HOOKS:-}" ]; then
  # Set and wrong is not the same as unset: a workflow whose checkout path and this variable
  # disagree must not fall through to whatever copy is beside this script while saying it
  # reads the plugin. It fails here, naming the path.
  if [ -f "$GATE_SDD_HOOKS/gate-lib.sh" ]; then
    lib="$GATE_SDD_HOOKS/gate-lib.sh"
  else
    echo "check-unreviewed-work: GATE_SDD_HOOKS is set to '$GATE_SDD_HOOKS' and there is no gate-lib.sh there." >&2
    echo "  Point it at a checkout of the plugin's hooks/ directory, or unset it to search the project." >&2
    exit 1
  fi
fi
if [ -z "$lib" ]; then
  for d in hooks .claude/hooks .agents/hooks; do
    [ -f "$d/gate-lib.sh" ] && { lib="$d/gate-lib.sh"; break; }
  done
fi
[ -z "$lib" ] && [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -f "$CLAUDE_PLUGIN_ROOT/hooks/gate-lib.sh" ] && lib="$CLAUDE_PLUGIN_ROOT/hooks/gate-lib.sh"
[ -z "$lib" ] && [ -n "${GATE_SDD_PLUGIN_ROOT:-}" ] && [ -f "$GATE_SDD_PLUGIN_ROOT/hooks/gate-lib.sh" ] && lib="$GATE_SDD_PLUGIN_ROOT/hooks/gate-lib.sh"
if [ -z "$lib" ]; then
  echo "check-unreviewed-work: cannot find gate-lib.sh in \$GATE_SDD_HOOKS, hooks/, .claude/hooks/, .agents/hooks/, \$CLAUDE_PLUGIN_ROOT/hooks/ or \$GATE_SDD_PLUGIN_ROOT/hooks/." >&2
  # A variable that is set and names no library is reported by value: after a plugin update
  # removes the cache directory a session's env file still names, this is the line that says so.
  [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && echo "  CLAUDE_PLUGIN_ROOT is '$CLAUDE_PLUGIN_ROOT', and there is no hooks/gate-lib.sh under it." >&2
  [ -n "${GATE_SDD_PLUGIN_ROOT:-}" ] && echo "  GATE_SDD_PLUGIN_ROOT is '$GATE_SDD_PLUGIN_ROOT', and there is no hooks/gate-lib.sh under it." >&2
  echo "  In a Claude Code session the plugin's SessionStart hook sets GATE_SDD_PLUGIN_ROOT. Unset there, the" >&2
  echo "  plugin was not enabled when the session started: enable it and start a new session." >&2
  echo "  From a terminal outside a Claude Code session, or in CI, set GATE_SDD_HOOKS to a checkout of the" >&2
  echo "  plugin's hooks/ directory, which is what CI does." >&2
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

# The same for the reader #191 added. Against a library older than it, `gate_tree_names` below
# is a command not found, and 127 is not the status this script reads as "no spec": a branch
# with none would go on to "holds no finished, unreviewed work", a sentence that claims a
# check. #233's two readers have no guard here because both sit on by-hand paths. This one is
# on the path CI takes. Case 200.
if ! command -v gate_tree_names >/dev/null 2>&1; then
  echo "check-unreviewed-work: $lib has no gate_tree_names — it predates the reader that tells a spec that is not there from one git cannot get (#191)." >&2
  echo "  Re-copy the plugin's hooks/gate-lib.sh over it and run this again." >&2
  exit 1
fi

# The same for the lister #316 added, and for the same reason: against a library older than it,
# `gate_branch_specs` below is a command not found, the list comes back empty, and a head carrying
# a spec not named for it goes on to "carries no spec", a sentence that claims a check. Case 358.
if ! command -v gate_branch_specs >/dev/null 2>&1; then
  echo "check-unreviewed-work: $lib has no gate_branch_specs — it predates the lister that finds a branch's specs from what it adds rather than from its name (#316)." >&2
  echo "  Re-copy the plugin's hooks/gate-lib.sh over it and run this again." >&2
  exit 1
fi

# By hand only, both of them: CI passes the branch and the commit from the event. Each goes
# through the library's full-refname readers, because a short name is ambiguous whenever a tag
# shares it, and git then lengthens the branch to `heads/<name>` or resolves the tag in its
# place — either way this said "carries no spec" about a branch that carries one. #233. Against
# a library older than those readers each comes back empty, which reaches the exit-1 messages
# below. No guard is added for them: both calls sit on paths CI never takes, and both already
# fail closed there.
branch=${1:-$(gate_head_branch 2>/dev/null)}
if [ -z "$branch" ] || [ "$branch" = HEAD ]; then
  echo "check-unreviewed-work: no branch name available — pass the pull request's head branch as the first argument." >&2
  exit 1
fi

sha=${2:-}
if [ -z "$sha" ]; then
  sha=$(gate_ref_commit "refs/heads/$branch" 2>/dev/null) || sha=""
fi
if [ -z "$sha" ]; then
  echo "check-unreviewed-work: cannot resolve a commit for '$branch'." >&2
  exit 1
fi

# The commit came from the event, so it is an assertion about a repository this process has
# not checked. Verify it before asking anything about it. A commit that is not in this clone
# used to read as "that commit has no such file", which passed every pull request while
# printing a success sentence. Since #191 it would read as a spec that cannot be read, which
# fails, and names the wrong cause. The live trigger is the default `actions/checkout` — on a
# pull_request event with fetch-depth 1, only the merge commit is fetched and the head commit
# is absent.
if ! git rev-parse --verify -q "$sha^{commit}" >/dev/null 2>&1; then
  echo "check-unreviewed-work: cannot resolve commit '$sha' in this clone, so nothing about it was checked." >&2
  echo "  A shallow checkout hides it: check out with fetch-depth: 0. A force-push after the" >&2
  echo "  run started does too, in which case re-run against the new head." >&2
  exit 1
fi

# The base, from the event when it is passed, and verified like the head: a base this clone cannot
# see would otherwise fall back to a reading the event did not ask for. Case 356. Without it, every
# candidate in the gates' own list that resolves.
#
# With no base at all this fails. The gate keeps the name match alone there, which is what every
# reader did before #316, but a pull request always has a base, and a check that says the head
# adds no spec, having never asked, claims a check it did not make: #16's shape. A two-argument
# workflow in a repository whose default branch is neither `main` nor `master`, checked out with no
# `origin/HEAD`, is that state, and the remedy is the third argument. Case 364.
base=${3:-}
if [ -n "$base" ]; then
  if ! git rev-parse --verify -q "$base^{commit}" >/dev/null 2>&1; then
    echo "check-unreviewed-work: cannot resolve base commit '$base' in this clone, so the specs this head adds cannot be told." >&2
    echo "  A shallow checkout hides it: check out with fetch-depth: 0." >&2
    exit 1
  fi
  bases=$(git rev-parse --verify -q "$base^{commit}")
else
  bases=$(gate_default_bases 2>/dev/null) || bases=""
fi
if [ -z "$bases" ]; then
  echo "check-unreviewed-work: no base to measure '$branch' against, so the specs it adds cannot be told and nothing was checked." >&2
  echo "  Pass the pull request's base commit as the third argument: on GitHub Actions," >&2
  echo "  \"\${{ github.event.pull_request.base.sha }}\". By hand, pass the commit the branch will merge into." >&2
  exit 1
fi

short=$(git rev-parse --short "$sha" 2>/dev/null || printf '%s' "$sha")

# Which specs the head carries: the name match, and every spec it adds against its merge base with
# the base. This read `.specs/<head branch>/spec.md` alone, so a head named any other way — a
# prefix, a typo, a spec archived on its own branch — "carried no spec" and passed (#316). A tree
# that names a spec git cannot get stays listed, and the library says the spec cannot be read
# (#191, case 199).
#
# A listing git could not make fails the check, and what the name match found is judged all the
# same, so a tree git cannot read still says that its spec cannot be read (case 199).
specs=$(gate_branch_specs "$bases" "$sha" "$branch"); listed=$?
failed=''
receipts=''
[ "$listed" -eq 0 ] || failed="
  $branch — git could not list the specs it adds at $short: a shallow checkout, a damaged object store, or a partial clone that cannot reach its remote. Check out with fetch-depth: 0, or run git fsck, and re-run."

# "Nothing to check" and "checked, and clean" must not share a sentence: that is #16's shape, and
# a guard that reports a success it did not earn is what #39 is open about.
if [ "$listed" -eq 0 ] && [ -z "$specs" ]; then
  echo "check-unreviewed-work: branch '$branch' carries no spec in $short — none named for it, and none it adds — so there is no review to demand, and nothing else was examined."
  exit 0
fi

while IFS= read -r dir; do
  [ -n "$dir" ] || continue
  state=$(gate_spec_review_state "$dir" "$sha" "$sha")
  [ -n "$state" ] || continue
  if [ "${dir#.specs/}" = "$branch" ]; then
    failed="$failed
  $branch — $(gate_review_state_sentence "$state")"
  else
    failed="$failed
  $branch — $dir/spec.md: $(gate_review_state_sentence "$state")"
  fi
  receipts="$receipts${receipts:+, }$dir/.review-receipt"
done <<EOF
$specs
EOF

if [ -z "$failed" ]; then
  echo "check-unreviewed-work: $(printf '%s' "$specs" | tr '\n' ' ' | sed 's/ $//') at $short holds no finished, unreviewed work."
  exit 0
fi

reviewer=$(gate_steering_value .steering/tech.md Reviewer)
[ -n "$reviewer" ] || reviewer="the reviewer named in .steering/tech.md"

echo "check-unreviewed-work FAILED" >&2
printf '%s\n' "$failed" | sed '1d' >&2
[ -n "$receipts" ] || exit 1          # only the listing failed, and its line says what to do
echo "" >&2
echo "  This pull request carries finished work that no review covers. The turn-end gate can be" >&2
echo "  switched off and HEAD can be moved; a pull request can do neither. Run $reviewer against" >&2
echo "  $short, write its Receipt block to $receipts, and push that commit." >&2
exit 1
