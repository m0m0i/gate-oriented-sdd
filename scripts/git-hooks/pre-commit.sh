#!/bin/sh
# pre-commit — refuses a commit whose staged paths or staged content the leakage guard fails
# on (#360).
#
# git names the index of this commit in GIT_INDEX_FILE, a partial commit's included, and the
# guard reads that one. The guard is the one beside this script.
guard="$(dirname "$0")/../check-leakage.sh"
sh "$guard" --staged > /dev/null && exit 0
echo "" >&2
echo "The commit is refused: what it stages did not pass scripts/check-leakage.sh --staged." >&2
exit 1
