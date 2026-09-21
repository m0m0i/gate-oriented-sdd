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

files() {
  if git rev-parse --git-dir >/dev/null 2>&1; then
    # --others so a file that is written but not yet staged is still checked.
    # Plain `git ls-files` sees only tracked files, which means a fresh repo, or
    # a new file before `git add`, scans nothing and reports clean — the worst
    # possible failure mode for a guard.
    git ls-files --cached --others --exclude-standard
  else
    find . -type f -not -path './.git/*' | sed 's|^\./||'
  fi | grep -v "^${SELF}$"
}

# The work-set, read ONCE. Three scans over three separately computed lists could disagree
# with each other and with the count below, and the count is only worth printing if it is the
# count of what was actually handed to grep.
list=$(files)

scanned=0
unreadable=""
while IFS= read -r f; do
  [ -n "$f" ] || continue
  scanned=$((scanned + 1))
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
  echo "check-leakage FAILED — the work-set is empty, so nothing was scanned." >&2
  echo "  'found nothing' and 'looked at nothing' must not share an exit code. Check that" >&2
  echo "  git ls-files works here, and that SELF still excludes only this script." >&2
  exit 1
fi

# A file this guard was handed and could not open is not a file it read and found clean.
# `xargs grep … 2>/dev/null` discarded "Permission denied" along with the noise it was there
# for, so the scan went round such a file in silence, on the same exit code and in the same
# sentence. Checked once here rather than three times below, so the three scans keep their
# stderr discard: after this, what they could still print is noise.
if [ -n "$unreadable" ]; then
  echo "check-leakage FAILED — in the work-set and could not be read:$unreadable" >&2
  echo "" >&2
  echo "  Fix the permissions rather than treating this as a pass. A file that was not read" >&2
  echo "  is not a file that came back clean, and this guard is the clean-room backstop." >&2
  exit 1
fi

fail=0

hits=$(printf '%s\n' "$list" | xargs grep -HniE "$PRIVATE" 2>/dev/null)
if [ -n "$hits" ]; then
  echo "LEAK (private identifier):" >&2
  echo "$hits" | sed 's/^/  /' >&2
  fail=1
fi

hits=$(printf '%s\n' "$list" | xargs grep -HnE "$IDS" 2>/dev/null)
if [ -n "$hits" ]; then
  echo "LEAK (private cross-reference id):" >&2
  echo "$hits" | sed 's/^/  /' >&2
  fail=1
fi

hits=$(printf '%s\n' "$list" | xargs grep -HniE "$DOMAIN" 2>/dev/null)
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

echo "check-leakage: clean — $scanned file(s) scanned"
exit 0
