#!/bin/sh
# install-git-hooks.sh — installs the leak hooks for this clone and every worktree of it (#360).
#
# It writes scripts/git-hooks/shim.sh under each hook's name into the clone's common hooks
# directory, and beside them a snapshot of the guard and the hook scripts, which a worktree
# whose branch holds no hooks runs. Run again, it brings both up to date. It refuses to
# replace a hook it did not write, to install over a newer shim, and to install where
# core.hooksPath sends git elsewhere.
set -u

ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT" || exit 1

# The hooks installed. Each is scripts/git-hooks/<name>.sh.
NAMES="commit-msg pre-commit pre-push"

refuse() {
  echo "install-git-hooks FAILED — $1" >&2
  echo "  Nothing was installed or changed." >&2
  exit 1
}
version() {  # $1 = a shim. Prints its number, or nothing when it is not a shim.
  sed -n 's/^# gate-sdd-shim \([0-9][0-9]*\)$/\1/p' "$1" 2>/dev/null | sed -n 1p
}

common=$(git rev-parse --git-common-dir 2>/dev/null) || refuse "this is not a git repository."
! git config --get core.hooksPath >/dev/null 2>&1 \
  || refuse "core.hooksPath is set, so git would not run a hook installed here. Unset it: git config --unset core.hooksPath"

new=$(version scripts/git-hooks/shim.sh)
[ -n "$new" ] || refuse "scripts/git-hooks/shim.sh holds no version line."
[ -f scripts/check-leakage.sh ] || refuse "scripts/check-leakage.sh is missing from this checkout."
for name in $NAMES; do
  [ -f "scripts/git-hooks/$name.sh" ] || refuse "scripts/git-hooks/$name.sh is missing from this checkout."
done

hooks="$common/hooks"
for name in $NAMES; do
  [ -e "$hooks/$name" ] || continue
  old=$(version "$hooks/$name")
  [ -n "$old" ] || refuse "$hooks/$name is a hook this installer did not write. Move it away first."
  [ "$old" -le "$new" ] \
    || refuse "$hooks/$name is shim version $old and this checkout's is $new. Install from a checkout that holds the newer one."
done

mkdir -p "$hooks" || refuse "$hooks could not be made."
rm -rf "$hooks/gate-sdd.new"
mkdir -p "$hooks/gate-sdd.new/scripts/git-hooks" \
  && cp scripts/check-leakage.sh "$hooks/gate-sdd.new/scripts/" \
  || refuse "the snapshot could not be written under $hooks."
for name in $NAMES; do
  cp "scripts/git-hooks/$name.sh" "$hooks/gate-sdd.new/scripts/git-hooks/" \
    || refuse "the snapshot could not be written under $hooks."
done
for name in $NAMES; do
  cp scripts/git-hooks/shim.sh "$hooks/$name.new" && chmod +x "$hooks/$name.new" \
    && mv -f "$hooks/$name.new" "$hooks/$name" \
    || { echo "install-git-hooks FAILED — $hooks/$name could not be written. Run it again." >&2; exit 1; }
done
rm -rf "$hooks/gate-sdd"
mv "$hooks/gate-sdd.new" "$hooks/gate-sdd" \
  || { echo "install-git-hooks FAILED — the snapshot could not be put in place. Run it again." >&2; exit 1; }

echo "install-git-hooks: $NAMES installed in $hooks (shim version $new), with a snapshot in $hooks/gate-sdd"
