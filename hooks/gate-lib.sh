#!/bin/sh
# gate-lib.sh — shared plumbing for this harness's gates.
#
# The two target harnesses signal "do not end this turn" differently:
#
#   Claude Code   exit code 2, message on stderr
#   Antigravity   {"decision":"continue","reason":"..."} on stdout, exit 0
#
# Rather than maintain two scripts, a gate emits BOTH. Each harness reads the
# channel it understands and ignores the other, so one script is authoritative
# and the two can never drift apart.
#
# Usage:  . "$(dirname "$0")/gate-lib.sh"
#         gate_block "message the model needs to read"
#         gate_pass

# JSON string escaping, enough for the messages gates actually produce
# (backslashes, quotes, newlines). Gate messages are ours, not user input.
_gate_json_escape() {
  printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' | awk 'BEGIN{ORS=""} {print sep $0; sep="\\n"}'
}

# Block the turn. Speaks to both harnesses, then exits non-zero for Claude Code.
gate_block() {
  _msg=$1
  printf '{"decision":"continue","reason":"%s"}\n' "$(_gate_json_escape "$_msg")"
  printf '%s\n' "$_msg" >&2
  exit 2
}

# Allow the turn to end. Antigravity expects a JSON object; Claude Code expects
# exit 0 and ignores stdout here.
gate_pass() {
  printf '{}\n'
  exit 0
}

# Count unticked checkboxes in a spec's Tasks section ONLY.
#
# Acceptance criteria are checkboxes too, and on a shipped spec they are commonly
# left unticked — reading those as open work would make the gate fire forever on
# every finished spec, which is precisely how a gate earns being switched off.
gate_open_tasks() {
  awk '/^#+ *3\./ {f=1; next} /^#+ /{f=0} f' "$1" 2>/dev/null | grep -c '^ *- \[ \]'
}
