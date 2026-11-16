#!/bin/sh
# install-gh-hook.sh — install the gh guard (#361) for every Claude Code session on this machine.
#
#   scripts/install-gh-hook.sh [--python <interpreter>]
#
# Writes the hook, its compiled module and the leakage guard into a new versioned directory under
# ${XDG_DATA_HOME:-$HOME/.local/share}/gate-sdd/gh-hook/, then points `current` at it in one
# rename, so no Bash call finds it half-installed and a failed install leaves the old version
# running. It prints the PreToolUse entry to add to ~/.claude/settings.json and says whether the
# file holds it. It never writes that file (#361 AC7): registering the hook is the maintainer's.
set -u

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SRC="$ROOT/scripts/claude-hooks"
FILES="gh_guard.py gh_guard_lib.py"

fail() {
  echo "install-gh-hook FAILED — $1" >&2
  exit 1
}

PY=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --python) [ "$#" -ge 2 ] || fail "--python needs the interpreter's absolute path."
              PY=$2; shift 2 ;;
    *) fail "it was given an argument it does not take. It takes --python <interpreter>." ;;
  esac
done
[ -n "${HOME:-}" ] || fail "HOME is not set, so it cannot tell where to install."
DATA=${XDG_DATA_HOME:-$HOME/.local/share}/gate-sdd/gh-hook

# The interpreter, named by its real path. On macOS /usr/bin/python3 is a shim that a project's
# DEVELOPER_DIR reroutes and that fails while an Xcode licence is unaccepted, so the default is
# the file xcrun resolves (#361). A version manager's shim is refused: it chooses at run time.
if [ -z "$PY" ]; then
  if [ "$(uname -s)" = Darwin ]; then
    PY=$(/usr/bin/xcrun -f python3 2>/dev/null) \
      || fail "xcrun could not find python3. Install the Command Line Tools, or give --python."
  else
    PY=$(command -v python3 2>/dev/null) || fail "there is no python3 on PATH. Give --python."
  fi
fi
case "$PY" in /*) ;; *) fail "the interpreter must be named by an absolute path." ;; esac
real=$PY
hops=0
while [ -L "$real" ]; do
  hops=$((hops + 1)); [ "$hops" -le 40 ] || fail "the interpreter's path is a loop of links."
  link=$(readlink "$real") || fail "a link on the interpreter's path cannot be read."
  case "$link" in /*) real=$link ;; *) real=$(dirname "$real")/$link ;; esac
done
dir=$(CDPATH= cd -P -- "$(dirname -- "$real")" 2>/dev/null && pwd) \
  || fail "the interpreter's directory does not exist."
PY=$dir/$(basename -- "$real")
[ -f "$PY" ] && [ -x "$PY" ] || fail "the interpreter is not an executable file: $PY"
case "$PY" in */shims/*) fail "the interpreter is a version manager's shim: $PY. Give the interpreter it runs." ;; esac
[ "$(head -c 2 "$PY")" != '#!' ] || fail "the interpreter is a script, which is a shim: $PY."
if [ "$(uname -s)" = Darwin ]; then
  case "$PY" in /usr/bin/*) fail "the interpreter is under /usr/bin, where macOS keeps xcrun's shims: $PY." ;; esac
fi
env -i PATH=/usr/bin:/bin "$PY" -I -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' \
  2>/dev/null || fail "the interpreter is older than Python 3.9, or does not run: $PY"

# The version, and the refusal to go back.
version_of() { sed -n 's/^GH_GUARD_VERSION = \([0-9][0-9]*\)$/\1/p' "$1" 2>/dev/null; }
NEW=$(version_of "$SRC/gh_guard_lib.py")
[ -n "$NEW" ] || fail "scripts/claude-hooks/gh_guard_lib.py holds no GH_GUARD_VERSION line."
for f in $FILES; do [ -f "$SRC/$f" ] || fail "scripts/claude-hooks/$f is missing."; done
[ -f "$ROOT/scripts/check-leakage.sh" ] || fail "scripts/check-leakage.sh is missing."
if [ -e "$DATA/current/gh_guard_lib.py" ]; then
  OLD=$(version_of "$DATA/current/gh_guard_lib.py")
  [ -n "$OLD" ] || fail "the installed hook holds no version line, so it cannot tell which is newer. Remove $DATA/current to reinstall."
  [ "$OLD" -le "$NEW" ] || fail "the installed hook is version $OLD, newer than this checkout's $NEW."
fi

# A directory named by the version and a hash of what it holds and the interpreter that runs it.
HASH=$( { printf '%s\n' "$PY"; for f in $FILES; do cat "$SRC/$f"; done; cat "$ROOT/scripts/check-leakage.sh"; } \
  | env -i PATH=/usr/bin:/bin "$PY" -I -c 'import hashlib, sys; print(hashlib.sha256(sys.stdin.buffer.read()).hexdigest()[:12])') \
  || fail "the interpreter could not hash the hook's files."
NAME=v$NEW-$HASH
mkdir -p "$DATA" || fail "it could not make $DATA."

if [ ! -d "$DATA/$NAME" ]; then
  work=$(mktemp -d "$DATA/.install.XXXXXX") || fail "it could not make a directory to work in under $DATA."
  cleanup() {
    for f in $FILES check-leakage.sh; do rm -f "$work/$f"; done
    rm -f "$work"/__pycache__/*.pyc
    rmdir "$work/__pycache__" "$work" 2>/dev/null
  }
  for f in $FILES; do cp "$SRC/$f" "$work/$f" || { cleanup; fail "it could not copy $f."; }; done
  cp "$ROOT/scripts/check-leakage.sh" "$work/check-leakage.sh" || { cleanup; fail "it could not copy check-leakage.sh."; }
  chmod 644 "$work"/*.py "$work/check-leakage.sh"
  env -i PATH=/usr/bin:/bin "$PY" -I -c 'import py_compile, sys; py_compile.compile(sys.argv[1], doraise=True)' \
    "$work/gh_guard_lib.py" 2>/dev/null || { cleanup; fail "gh_guard_lib.py did not compile under $PY."; }
  # The copy must decide before it is installed: a command without gh passes in silence, and
  # one whose gh it cannot account for blocks.
  probe() {
    printf '{"tool_input":{"command":"%s"}}' "$1" \
      | env -i PATH=/usr/bin:/bin HOME="$HOME" "$PY" -I "$work/gh_guard.py" >"$work/.out" 2>/dev/null
    code=$?; out=$(cat "$work/.out"); rm -f "$work/.out"; [ "$code:$out" = "$2" ]
  }
  probe 'ls' '0:' || { cleanup; fail "the copy did not pass a command without gh."; }
  probe '${:-gh} issue list' '2:' || { cleanup; fail "the copy did not block a gh it cannot account for."; }
  mv "$work" "$DATA/$NAME" || { cleanup; fail "it could not move the copy into place."; }
fi
for f in $FILES; do
  cmp -s "$SRC/$f" "$DATA/$NAME/$f" || fail "$DATA/$NAME/$f differs from this checkout's. Remove $DATA/$NAME to reinstall."
done

# One rename points `current` at the new directory.
rm -f "$DATA/.current.new"
ln -s "$NAME" "$DATA/.current.new" || fail "it could not make the new link."
env -i PATH=/usr/bin:/bin "$PY" -I -c 'import os, sys; os.replace(sys.argv[1], sys.argv[2])' \
  "$DATA/.current.new" "$DATA/current" 2>/dev/null \
  || fail "it could not point $DATA/current at $NAME. If current is a directory, move it away."

SETTINGS=${CLAUDE_CONFIG_DIR:-$HOME/.claude}/settings.json
env -i PATH=/usr/bin:/bin "$PY" -I - "$PY" "$DATA/current/gh_guard.py" "$SETTINGS" "$NAME" <<'PY'
import json, sys
py, hook, settings, name = sys.argv[1:5]
handler = {"type": "command", "command": py, "args": ["-I", hook], "timeout": 30,
           "onFailure": "block"}
entry = {"matcher": "Bash|mcp__terminal__run_in_terminal", "hooks": [handler]}
print("install-gh-hook: installed " + name + ".")
print("Register it with this entry under hooks.PreToolUse in " + settings + ":")
print(json.dumps(entry, indent=2))
try:
    with open(settings) as f:
        data = json.load(f)
except FileNotFoundError:
    data = None
except (OSError, ValueError):
    print("install-gh-hook: " + settings + " cannot be read as JSON, so it cannot tell whether it"
          " holds the entry.")
    sys.exit(0)
groups = ((data or {}).get("hooks") or {}).get("PreToolUse") or [] if isinstance(data, dict) else []
held = any(isinstance(g, dict) and g.get("matcher") == entry["matcher"] and handler in (g.get("hooks") or [])
           for g in groups)
print("install-gh-hook: " + settings + (" holds the entry." if held else " does not hold the entry yet."))
PY
