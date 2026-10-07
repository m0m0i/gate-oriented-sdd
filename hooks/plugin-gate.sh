#!/bin/sh
# plugin-gate.sh — the gates as the plugin runs them on Claude Code (#256).
#
# .claude-plugin/hooks.json runs `sh "${CLAUDE_PLUGIN_ROOT}/hooks/plugin-gate.sh" <gate>` on
# Stop and SessionStart, so a fix to a gate reaches a project by plugin update rather than by
# re-running `init` and opening a pull request in every repository that copied it. The gate
# itself is unchanged and runs beside this file, with the project as cwd (verified: V1 in
# docs/verified.md). What this wrapper adds is the three decisions a plugin-shipped gate has to
# make that a copied one never did:
#
#   1. A project without .steering/ does not use the harness. A user-scope install reaches
#      every project on the machine, so the gate must be silent there — exit 0, no output.
#   2. A project that still runs its own copy of the same gate, from its .claude/settings.json,
#      would run the gate twice: Claude Code runs the plugin's hook AND the project's for the
#      same event (V2). So this stands down — but only on EVIDENCE that the copy runs: the
#      settings name the gate's file under the gate's event. The copied file alone is not
#      evidence; a project with the file and no entry runs this gate. Neither running is the
#      fail-open under `- Owns: gates never fail open`; both running costs a second validator
#      pass. The two mistakes are not symmetric, so the test is biased toward running.
#   3. A gate missing from the plugin is a broken install, and a broken install is loud. The
#      shape is the gates' own bootstrap guard: JSON on stdout for Antigravity, the sentence on
#      stderr for Claude Code, exit 2.
#
# A POSIX hook cannot parse JSON by event, so the evidence in (2) is text, and the text is
# held to two shapes rather than two words: the gate's filename on a `"command"` line, and the
# event as a KEY (`"Stop":`). The first draft asked only whether the file mentioned each
# anywhere, and Claude Code itself produces the counter-example: approving a by-hand run of
# the gate with "don't ask again" writes `"permissions": {"allow": ["Bash(sh
# .claude/hooks/quality-gate.sh:*)"]}` into settings.local.json, and a Stop hook for a
# notification is the documented example — together they read as the gate running under
# Stop, and the plugin's gate stood down for nothing (review round 1). What remains is a
# settings file with a `"command"` naming the gate and a `"Stop":` key that does not run it,
# which is contrived. Antigravity never runs this file; its gates are copied by `init`,
# because a plugin hook there runs with the plugin directory as cwd
# (hooks/templates/README.md).
set -u

DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
gate=${1:-}

_plugin_gate_block() {  # the bootstrap guard's shape; nothing interpolated is user-authored
  printf '{"decision":"continue","reason":"%s"}\n' "$1"
  printf '%s\n' "$1" >&2
  exit 2
}

# The gate decides the event, and the name is a closed list: a path from outside the plugin's
# hooks/ is not a gate this wrapper runs, whatever it is called.
case "$gate" in
  quality-gate.sh|review-gate.sh) event=Stop ;;
  steering-digest.sh) event=SessionStart ;;
  *) _plugin_gate_block "Plugin gate: '$gate' is not a gate this wrapper runs (quality-gate.sh, review-gate.sh or steering-digest.sh). The plugin's .claude-plugin/hooks.json names the wrong thing, so re-install the plugin rather than treating this turn as a pass." ;;
esac

gate_re=$(printf '%s' "$gate" | sed 's/\./\\./g')   # the name as a pattern: its dots literal

# Anchor to the repository root, as the gates do, so .steering/ and .claude/ resolve from
# wherever the hook was invoked.
if repo_root=$(git rev-parse --show-toplevel 2>/dev/null); then
  cd "$repo_root"
fi

# (1) Not a harness project: silent.
[ -d .steering ] || exit 0

# (2) The project runs its own copy of this gate under this event: stand down.
for f in .claude/settings.json .claude/settings.local.json; do
  [ -f "$f" ] || continue
  # Line layout is not assumed: a minified settings file is one line, and a line-wise test
  # read its permissions entry as its Stop command. The gate's name must sit INSIDE a
  # "command" string value — from the opening quote to the name with no unescaped quote
  # between — and the event must be a key.
  if grep -qE -- "\"command\" *: *\"([^\"\\\\]|\\\\.)*$gate_re" "$f" 2>/dev/null \
     && grep -qE -- "\"$event\" *:" "$f" 2>/dev/null; then
    exit 0
  fi
done

# (3) The gate runs from here, beside this file, with the project as cwd.
[ -f "$DIR/$gate" ] || _plugin_gate_block "Plugin gate: $gate is missing from the plugin's hooks/ directory beside plugin-gate.sh, so the gate cannot run. Re-install the plugin and run again rather than treating this turn as a pass."
exec sh "$DIR/$gate"
