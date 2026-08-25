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

# Finding the file is not the same as finding the reader. `init` copies this asset into
# projects whose gate-lib.sh may predate the shared reader, and then every anchor comes back
# empty and every correctly written line is reported unparseable — failing closed, which is
# right, with a diagnosis that is wrong, which sends the author to edit steering that is fine.
if ! command -v gate_steering_value >/dev/null 2>&1; then
  echo "check-steering-anchors: $lib has no gate_steering_value — it predates the shared reader." >&2
  echo "  Re-copy the plugin's hooks/gate-lib.sh over it and run this again." >&2
  exit 1
fi

failed=""
resolved=0
present=0
old_ifs=$IFS
IFS='
'
for row in $ANCHORS; do
  [ -n "$row" ] || continue
  file=${row%%|*}
  key=${row#*|}
  [ -f "$file" ] || continue
  value=$(gate_steering_value "$file" "$key")
  # Anchored to the start of a line, modulo leading punctuation. Deliberately looser than the
  # reader — it must still see `- **Owns:` and `  * Owns :` — but not so loose that ordinary
  # prose trips it. Unanchored, `Docs *:` matched the word "docs:" inside this repo's own
  # commit-convention paragraph, so deleting a legitimately optional `- Docs:` line would have
  # failed the guard while pointing at prose.
  if [ -z "$value" ] && grep -qi -- "^[^A-Za-z]*$key *:" "$file" 2>/dev/null; then
    failed="${failed}
  $file: '$key' is present but written in a form its reader cannot parse.
      found:  $(grep -i -- "^[^A-Za-z]*$key *:" "$file" | head -1 | sed 's/^ *//')
      The reader is: sed -n 's/^ *- *$key: *//p'  — so the line must begin with '- $key:',
      with no emphasis markers or other characters before the key."
  fi
  # Count what RESOLVED, not what had a file. Counting files meant a tech.md holding only
  # `- Validators:` still printed "5 anchor(s) checked, all readable" having read one — the
  # same room case 28 locks the other door to, and the likelier state in a real project.
  [ -n "$value" ] && resolved=$((resolved + 1))
  present=$((present + 1))
done
IFS=$old_ifs

if [ -n "$failed" ]; then
  echo "check-steering-anchors FAILED$failed" >&2
  exit 1
fi

if [ "$present" -eq 0 ]; then
  # "Checked nothing" and "found nothing wrong" must not share a sentence. Legitimate — the
  # guard may be installed before init writes steering — but #16 was exactly this wording on
  # exactly this exit code, and AC7 closed the neighbouring door while leaving this one open.
  echo "check-steering-anchors: no steering files found — nothing was checked"
  exit 0
fi

echo "check-steering-anchors: $resolved of $present anchor(s) resolved, none unreadable"
