#!/bin/sh
# check-leakage.sh — refuse to let private context reach a public repo.
#
# This harness was extracted from a private polyrepo. The extraction is meant to
# be clean-room: read the private file, close it, write the generic one. This
# script is the backstop for when that discipline slips — which it does most
# easily in the places that look harmless, like an example in a rulebook or a
# path in a doc comment.
#
# It runs in CI and is safe to run locally: ./scripts/check-leakage.sh
# Exit 0 = clean. Exit 1 = something private is in the tree.
set -u

ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT" || exit 1

# This script necessarily contains every pattern it looks for, so it excludes
# itself. Nothing else may be excluded — an allowlist here is how a guard rots.
SELF="scripts/check-leakage.sh"

# Tier 1 — identifiers that are unambiguously private. Any hit is a failure.
PRIVATE='perk[-_ ]?patrol|4thFebs|perkpatrol'

# Tier 2 — the private cross-reference id scheme. Bare words like "ADR" are fine
# and appear legitimately in this repo's own prose; it is the *numbered* forms
# that carry meaning from the private docs hub.
IDS='\bNS-[0-9]|\bCAP-[a-z]|\bCON-[a-z]|\bADR-[0-9]{4}'

# Tier 3 — domain nouns from the private product. These can appear innocently in
# a generic example, so they are reported as warnings for a human to judge.
DOMAIN='card_rules|cardType|benefits[-_]digger|amex|chase_sapphire|venture_x'

# Decided once and read twice: which lister runs, and whether a leading `"` can only be git's
# doing. In a non-git tree nothing quotes, so a file genuinely named `"quoted".md` must not be
# mistaken for one git could not represent. Review round 2.
if git rev-parse --git-dir >/dev/null 2>&1; then IN_GIT=1; else IN_GIT=0; fi

files() {
  if [ "$IN_GIT" -eq 1 ]; then
    # --others so a file that is written but not yet staged is still checked.
    # Plain `git ls-files` sees only tracked files, which means a fresh repo, or
    # a new file before `git add`, scans nothing and reports clean — the worst
    # possible failure mode for a guard.
    # `core.quotePath` defaults to TRUE, and it renders any byte above 0x80 as a C-quoted
    # literal — `"caf\303\251.md"` — which is not a path anything here can open. The
    # readability check below then calls a readable file unreadable, and this script is the
    # FIRST entry on the `- Validators:` line, so that is every turn stopped on a wrong
    # diagnosis. A guard with a wrong diagnosis gets removed. #39 review round 1.
    git -c core.quotePath=false ls-files --cached --others --exclude-standard
  else
    find . -type f -not -path './.git/*' | sed 's|^\./||'
  fi | grep -v "^${SELF}$"
}

# The work-set, read ONCE. Three scans over three separately computed lists could disagree
# with each other and with the count below, and the count is only worth printing if it is the
# count of what was actually handed to grep — which is why the scans below run over `scanlist`,
# the entries that survived classification, rather than over `list`. Those drifted apart for
# one round: `absent` entries stayed in the list grep was given while leaving the count.
list=$(files)

scanned=0
absent=0
scanlist=""
unreadable=""
unscannable=""
while IFS= read -r f; do
  [ -n "$f" ] || continue
  # `--cached` lists INDEX entries and filters on neither existence nor `skip-worktree`, so a
  # tracked path that is not on disk arrives here: an unstaged `rm`, a sparse checkout, a
  # partial worktree. `[ -r ]` is false for every one of them, and this guard blocked the turn
  # saying "could not be read … fix the permissions" about a file that is not there — absent
  # and unreadable fused, which is this issue's own subject reached one level down inside its
  # own fix. Counted rather than skipped in silence: "I scanned round three index entries" is
  # exactly the thing that must not hide inside `clean`. AC5, narrowed in review round 2.
  if [ ! -e "$f" ]; then
    # Absent, or UNREACHABLE — and `[ -e ]` cannot tell you which. stat() returns EACCES
    # through any prefix with no search permission, and `test` collapses that into false, so
    # the arm above counted a file that IS in the working tree as one that is not: a planted
    # hit under a mode-000 directory went from caught to `clean`, on exit 0, in the clean-room
    # backstop. Introduced by the fix for the defect above it, which is this issue's own
    # subject a third time. Review round 3.
    #
    # Walk UP to the first ancestor that can be stat'd at all. Testing only the immediate
    # parent is not enough: under a mode-000 `a/`, `[ -d a/b ]` cannot be answered either, so
    # `a/b/c.md` would fall through to "absent" by the same mechanism one level deeper. A path
    # with no directory part has no ancestor to blame and is simply gone.
    _d=$f; _blocked=0
    while [ "${_d%/*}" != "$_d" ]; do
      _d=${_d%/*}
      if [ -d "$_d" ]; then
        [ -x "$_d" ] || _blocked=1
        break
      fi
    done
    if [ "$_blocked" -eq 1 ]; then
      unreadable="${unreadable}
  $f"
    else
      absent=$((absent + 1))
    fi
    continue
  fi
  scanned=$((scanned + 1))
  scanlist="${scanlist}${f}
"
  # git C-quotes a path holding `"`, a backslash or a control character whatever
  # core.quotePath says, and `ls-files -z`, the only way to get those verbatim, has no
  # portable reader in POSIX sh. Such a path genuinely cannot be scanned here, so it is named
  # as exactly that rather than as a permissions problem it is not. In a non-git tree `find`
  # does not quote, so a path holding a newline splits there and is counted twice — recorded
  # rather than fixed, because the fix is the NUL reader this shell does not have.
  if [ "$IN_GIT" -eq 1 ]; then
    case "$f" in
      '"'*) unscannable="${unscannable}
  $f"; continue ;;
    esac
  fi
  [ -r "$f" ] || unreadable="${unreadable}
  $f"
done <<EOF
$list
EOF

# Zero files is not a clean tree. files()'s own comment calls a scan of nothing "the worst
# possible failure mode for a guard" and then does not check for it: a fresh clone, a broken
# `git ls-files`, or an SELF exclusion that grew all end here, and until now they all printed
# `check-leakage: clean` on exit 0. AGENTS.md calls this the guard that matters most. #39.
if [ "$scanned" -eq 0 ]; then
  if [ "$absent" -gt 0 ]; then
    # It was not empty, and saying so would send the reader to `git ls-files` and to SELF,
    # neither of which is the cause. A fully sparse checkout lands here. AC5's second clause.
    echo "check-leakage FAILED — the work-set held $absent index entr(ies) and no working-tree" >&2
    echo "  file for any of them, so nothing was scanned. A checkout this partial cannot be" >&2
    echo "  cleared by this guard; check it out fully rather than treating this as a pass." >&2
  else
    echo "check-leakage FAILED — the work-set is empty, so nothing was scanned." >&2
    echo "  'found nothing' and 'looked at nothing' must not share an exit code. Check that" >&2
    echo "  git ls-files works here, and that SELF still excludes only this script." >&2
  fi
  exit 1
fi

# A file this guard was handed and could not open is not a file it read and found clean.
# `xargs grep … 2>/dev/null` discarded "Permission denied" along with the noise it was there
# for, so the scan went round such a file in silence, on the same exit code and in the same
# sentence. Checked once here rather than three times below, so the three scans keep their
# stderr discard: after this, what they could still print is noise.
if [ -n "$unscannable" ]; then
  echo "check-leakage FAILED — in the work-set and cannot be handed to grep as a path:$unscannable" >&2
  echo "" >&2
  echo "  git C-quoted these because they hold a quote, a backslash or a control character." >&2
  echo "  Rename them. This guard is the clean-room backstop and must not skip a file quietly." >&2
  exit 1
fi

if [ -n "$unreadable" ]; then
  echo "check-leakage FAILED — in the work-set and could not be read:$unreadable" >&2
  echo "" >&2
  echo "  Fix the permissions rather than treating this as a pass. A file that was not read" >&2
  echo "  is not a file that came back clean, and this guard is the clean-room backstop." >&2
  exit 1
fi

# NUL-delimited into xargs. Split on whitespace, `docs/my file.md` reaches grep as two
# pathspecs that match nothing — and grep finding nothing in a file it was never handed is
# indistinguishable from a clean file, so a real private identifier in a path with a space
# passed this guard silently while the count above said it had been read. That is the empty
# work-set one layer in, and it was a fail-open before this branch as well. #39 review round 1.
# `--` closes the class the NUL delimiter opened only half of: a path beginning with `-` is
# not C-quoted by git, so it passes every test above, is counted, and then reaches grep as an
# OPTION — a valid one silently changing the scan, an invalid one exiting 2 into the discarded
# stderr. Either way never read, while the count says it was. Review round 2.
scan() { printf '%s\n' "$scanlist" | tr '\n' '\0' | xargs -0 grep "$@" -- 2>/dev/null; }

fail=0

hits=$(scan -HniE "$PRIVATE")
if [ -n "$hits" ]; then
  echo "LEAK (private identifier):" >&2
  echo "$hits" | sed 's/^/  /' >&2
  fail=1
fi

hits=$(scan -HnE "$IDS")
if [ -n "$hits" ]; then
  echo "LEAK (private cross-reference id):" >&2
  echo "$hits" | sed 's/^/  /' >&2
  fail=1
fi

hits=$(scan -HniE "$DOMAIN")
if [ -n "$hits" ]; then
  echo "WARNING (private domain noun — confirm this is a generic example):" >&2
  echo "$hits" | sed 's/^/  /' >&2
fi

if [ "$fail" -ne 0 ]; then
  echo "" >&2
  echo "Clean-room rule: do not scrub these in place. Scrubbing leaves the shape," >&2
  echo "and the shape is where the private structure lives. Rewrite the file." >&2
  exit 1
fi

note=""
[ "$absent" -gt 0 ] && note=", $absent index entr(ies) not in the working tree"
echo "check-leakage: clean — $scanned file(s) scanned$note"
exit 0
