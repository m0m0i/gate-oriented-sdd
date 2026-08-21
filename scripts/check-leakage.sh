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

fail=0

hits=$(files | xargs grep -HniE "$PRIVATE" 2>/dev/null)
if [ -n "$hits" ]; then
  echo "LEAK (private identifier):" >&2
  echo "$hits" | sed 's/^/  /' >&2
  fail=1
fi

hits=$(files | xargs grep -HnE "$IDS" 2>/dev/null)
if [ -n "$hits" ]; then
  echo "LEAK (private cross-reference id):" >&2
  echo "$hits" | sed 's/^/  /' >&2
  fail=1
fi

hits=$(files | xargs grep -HniE "$DOMAIN" 2>/dev/null)
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

echo "check-leakage: clean"
exit 0
