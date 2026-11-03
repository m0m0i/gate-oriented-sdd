#!/bin/sh
# harness-checks.sh — the harness's own checks, run from the tree this file sits in (#340).
#
# The harness checks are the guards that check the harness's own files: the steering anchors,
# the reviewer's locks, the document set and the document cascade. They were copies in each
# project's scripts/, named on its `- Validators:` line, so a fix the plugin shipped reached no
# project that updated, which CAP-5 and LV-5 say must not happen. The quality gate now runs this
# file from its own directory, before the line's commands, so a check and the gate that runs it
# always come from one tree, and the line holds only the project's own commands.
#
# Its tree is read from a marker, never from which files happen to exist. With
# `../.claude-plugin/plugin.json` beside its directory, the checks are in `../assets/`: the
# plugin, the release zip and this repository. Otherwise they sit flat beside it, which is
# Antigravity's `.agents/hooks/`, where `init` copies them with the gates.
#
# Each check runs with GATE_SDD_HOOKS naming this tree's hooks directory, so a check that sources
# gate-lib.sh reads this tree's copy: neither an exported GATE_SDD_HOOKS nor a dual-target
# project's `.agents/hooks/` can pair a new check with an old library.
#
# It fails closed. A missing check, or one that cannot be run, is a failure that names its path,
# never the `[ -f x ] || exit 0` the hooks template uses for an optional command. It writes
# nothing, never passes `--update`, and reads no variable or flag that skips a check. The one
# skip is a remote `- Docs:` value, the condition `init` has always used to leave the document
# checks uninstalled; it is printed.
#
# `--files` prints the files it would run, one per line, this file first, and runs nothing: the
# quality gate hashes them into its fingerprint, so a fix to any of them runs once.
set -u

hc_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd) || {
  printf 'harness-checks: cannot resolve the directory of %s, so no harness check ran.\n' "$0" >&2
  exit 1
}
if [ -f "$hc_dir/../.claude-plugin/plugin.json" ]; then
  hc_tree=$(CDPATH='' cd -- "$hc_dir/.." && pwd) || {
    printf 'harness-checks: cannot resolve the tree above %s, so no harness check ran.\n' "$hc_dir" >&2
    exit 1
  }
  hc_checks=$hc_tree/assets
  hc_version=$(sed -n 's/^ *"version": *"\([^"]*\)".*/\1/p' "$hc_tree/.claude-plugin/plugin.json" 2>/dev/null | head -1)
else
  hc_tree=$hc_dir
  hc_checks=$hc_dir
  hc_version=""
fi

# The order is fixed: the anchors first, because every other check reads a steering line, then
# the locks, then the two document checks.
hc_names='check-steering-anchors.sh
check-locks.py
check-document-set.py
check-document-cascade.py'

if [ "${1-}" = --files ]; then
  printf '%s\n' "$hc_dir/harness-checks.sh"
  printf '%s\n' "$hc_names" | while IFS= read -r hc_n; do printf '%s\n' "$hc_checks/$hc_n"; done
  exit 0
fi

# The project is the git toplevel of the working directory, as the quality gate's is. Outside a
# repository the checks run where they were started, and each one decides what that means.
if hc_top=$(git rev-parse --show-toplevel 2>/dev/null); then
  cd "$hc_top" || {
    printf 'harness-checks: cannot enter %s, so no harness check ran.\n' "$hc_top" >&2
    exit 1
  }
fi

printf 'harness-checks: from %s%s\n' "$hc_tree" "${hc_version:+ (gate-sdd $hc_version)}"

# Read as gate-lib.sh's gate_steering_value reads a steering line, and only to test it for `://`.
hc_docs=$(sed -n 's/^ *- *Docs: *//p' .steering/tech.md 2>/dev/null | head -1)
hc_failed=""
hc_ran=0
hc_nl='
'
hc_ifs=$IFS
IFS=$hc_nl
set -f
for hc_n in $hc_names; do
  set +f
  IFS=$hc_ifs
  hc_path=$hc_checks/$hc_n
  case "$hc_n" in
    check-document-set.py|check-document-cascade.py)
      case "$hc_docs" in
        *://*)
          printf -- '--- %s: not applicable, because - Docs: names another repository (%s)\n' "$hc_n" "$hc_docs"
          continue ;;
      esac ;;
  esac
  printf -- '--- %s\n' "$hc_n"
  hc_ran=$((hc_ran + 1))
  if [ ! -f "$hc_path" ]; then
    printf 'harness-checks: %s is missing, so it did not run, and that is a failure rather than a pass.\n' "$hc_path"
    hc_failed="$hc_failed $hc_n"
    continue
  fi
  case "$hc_n" in
    *.py) GATE_SDD_HOOKS=$hc_dir python3 "$hc_path" 2>&1 ;;
    *) GATE_SDD_HOOKS=$hc_dir sh "$hc_path" 2>&1 ;;
  esac || hc_failed="$hc_failed $hc_n"
done
set +f
IFS=$hc_ifs

# The verdict is the last line on purpose: a block shows a command's last 20 lines, and the
# names of the checks that failed must survive that cut whatever the checks printed.
if [ -n "$hc_failed" ]; then
  printf 'harness-checks: failed:%s (from %s)\n' "$hc_failed" "$hc_tree"
  exit 1
fi
printf 'harness-checks: %s check(s) passed, from %s\n' "$hc_ran" "$hc_tree"
