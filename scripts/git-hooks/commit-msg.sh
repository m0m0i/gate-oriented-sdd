#!/bin/sh
# commit-msg — refuses a commit whose message the leakage guard fails on (#360).
#
# $1 is the message file as git hands it. With an editor it also holds comment lines and, under
# -v, the diff: more than the commit will hold, never less. The guard is the one beside this
# script, so a hook and a guard of different versions never run together.
guard="$(dirname "$0")/../check-leakage.sh"
sh "$guard" --text < "$1" > /dev/null && exit 0
echo "" >&2
echo "The commit is refused: its message did not pass scripts/check-leakage.sh --text." >&2
exit 1
