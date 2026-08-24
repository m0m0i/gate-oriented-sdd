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

# Emit a spec's Tasks section ONLY — section 3, up to the next heading.
#
# The scoping is the load-bearing part. Acceptance criteria are checkboxes too, and on a
# shipped spec they are commonly left unticked; counting those as open work would make the
# gate fire forever on every finished spec, which is how a gate earns being switched off.
# Both counters below scope through here so they can never disagree about what a task is.
_gate_tasks_section() {
  awk '/^#+ *3\./ {f=1; next} /^#+ /{f=0} f' "$1" 2>/dev/null
}

# Count UNTICKED checkboxes: how much work is left.
gate_open_tasks() {
  _gate_tasks_section "$1" | grep -c '^ *- \[ \]'
}

# Count ALL checkboxes in a spec's Tasks section, ticked or not.
#
# gate_open_tasks returning 0 is ambiguous, and the two meanings are opposites: "every task
# is done" and "no task was ever written". Reading the second as the first blocks a spec that
# is still being drafted, which is the state `spec` step 3 tells the author to create. A
# caller needs both counts to tell them apart.
gate_total_tasks() {
  _gate_tasks_section "$1" | grep -c '^ *- \[[ xX]\]'
}
