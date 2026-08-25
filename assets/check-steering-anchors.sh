#!/bin/sh
# check-steering-anchors.sh — fail when a steering line is written in a form its reader cannot parse.
#
# Steering carries a handful of machine-read lines. Each is read by a hook with an exact
# expression, and a value that misses that expression produces nothing and no complaint. The
# file goes on looking right — more right, if the miss was caused by emphasising the line.
#
# This repository wrote `- **Owns: gates never fail open.**` and lost the quality property
# every reviewer severity is judged against for a week, in a digest that silently omitted it
# rather than reporting a problem (#34).
#
# It asks its subject's own question, by calling the same function the hooks call, so it
# cannot drift from what a gate would see. It does NOT judge whether a value is any good —
# that would be a steering linter, and every rule in one is a new way to false-block.
set -u

# Absent is legitimate; present-but-unparseable is not. A project may have no `Docs` line at
# all, and saying so would fire on a configuration the harness supports.
#
#   no loose match, no value   -> absent, silent
#   loose match, no value      -> FAIL: written in a form the reader cannot see
#   loose match, value         -> fine
ANCHORS="
.steering/product.md|Owns
.steering/tech.md|Validators
.steering/tech.md|Reviewer
.steering/tech.md|Source globs
.steering/tech.md|Docs
"

# gate-lib.sh is `hooks/` in the harness repo and `.claude/hooks/` in a project. Finding it is
# the problem that produced #16, so this FAILS when it cannot — a guard that skips because it
# could not locate its own dependency is the bug this script exists to prevent.
lib=""
for d in hooks .claude/hooks .agents/hooks; do
  [ -f "$d/gate-lib.sh" ] && { lib="$d/gate-lib.sh"; break; }
done
if [ -z "$lib" ]; then
  echo "check-steering-anchors: cannot find gate-lib.sh in hooks/, .claude/hooks/ or .agents/hooks/." >&2
  echo "  Without it this check cannot ask the question the gates ask, and a guard that cannot" >&2
  echo "  do its job must not report success. See #16." >&2
  exit 1
fi
# shellcheck source=/dev/null
. "$lib"

failed=""
checked=0
old_ifs=$IFS
IFS='
'
for row in $ANCHORS; do
  IFS=$old_ifs
  [ -n "$row" ] || continue
  file=${row%%|*}
  key=${row#*|}
  [ -f "$file" ] || { IFS='
'; continue; }
  value=$(gate_steering_value "$file" "$key")
  if [ -z "$value" ] && grep -qi -- "$key *:" "$file" 2>/dev/null; then
    failed="${failed}
  $file: '$key' is present but written in a form its reader cannot parse.
      found:  $(grep -i -m1 -- "$key *:" "$file" | sed 's/^ *//')
      The reader is: sed -n 's/^ *- *$key: *//p'  — so the line must begin with '- $key:',
      with no emphasis markers or other characters before the key."
  fi
  checked=$((checked + 1))
  IFS='
'
done
IFS=$old_ifs

if [ -n "$failed" ]; then
  echo "check-steering-anchors FAILED$failed" >&2
  exit 1
fi

echo "check-steering-anchors: $checked anchor(s) checked, all readable"
