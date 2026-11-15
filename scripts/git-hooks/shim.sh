#!/bin/sh
# gate-sdd-shim 1
#
# Installed by scripts/install-git-hooks.sh under each hook's name in the clone's common hooks
# directory, which every worktree shares. It runs the
# hook script of that name from the worktree git called it in, and the installed snapshot's
# copy when that worktree's branch holds none. It reads no other checkout's working tree, and
# it refuses when neither copy exists: a hook that is absent is silent (#360).
#
# The number on the second line is what check-leakage.sh compares with the installed copy.
# Raise it with any change to this file.
name=${0##*/}
top=$(git rev-parse --show-toplevel 2>/dev/null) || top=""
hook="$top/scripts/git-hooks/$name.sh"
if [ -z "$top" ] || [ ! -f "$hook" ]; then
  hook="$(dirname "$0")/gate-sdd/scripts/git-hooks/$name.sh"
fi
if [ ! -f "$hook" ]; then
  echo "gate-sdd $name hook FAILED — it found no hook script to run, so nothing was scanned." >&2
  echo "  Looked in: $top/scripts/git-hooks and $(dirname "$0")/gate-sdd/scripts/git-hooks" >&2
  echo "  Run scripts/install-git-hooks.sh from a checkout that holds scripts/git-hooks." >&2
  exit 1
fi
exec sh "$hook" "$@"
