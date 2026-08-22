#!/bin/sh
# quality-gate.sh — the deterministic half of the enforcement layer.
#
# The bottom row of this harness's table is the only one that is a guarantee: format,
# lint, types, and tests, on turn end, not skippable. This is the script that holds it.
#
# The commands are NOT hardcoded. They come from the `- Validators:` line in
# .steering/tech.md, which is what lets one copy of this script serve every project the
# harness is installed into — and what makes a project change its enforcement by editing
# steering rather than by editing a hook. That line already exists and is already read by
# steering-digest.sh; before this script, nothing acted on it.
#
# Like review-gate.sh, this speaks both harnesses' blocking channels through gate-lib.sh.
# An inline `npm test` in settings.json would serve Claude Code and leave Antigravity
# silently advisory, which is the failure CONTRIBUTING.md names for a change to hooks/.
#
# Keep it fast. A gate that costs a minute per turn is a gate that gets switched off, and
# a switched-off gate protects nothing. If the suite is slow, the honest fix is a faster
# suite or a narrower validator list — not a demotion to advisory.
set -u

DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
. "$DIR/gate-lib.sh"

[ -f .steering/tech.md ] || gate_pass

validators=$(sed -n 's/^ *- *Validators: *//p' .steering/tech.md | head -1)
[ -n "$validators" ] || gate_pass

failed=""
# Comma-separated, because a validator is a whole command and commands contain spaces.
old_ifs=$IFS
IFS=,
for cmd in $validators; do
  IFS=$old_ifs
  cmd=$(printf '%s' "$cmd" | sed -e 's/^ *//' -e 's/ *$//')
  [ -n "$cmd" ] || continue
  if ! out=$(eval "$cmd" 2>&1); then
    # Only the tail. The model needs to know which validator failed and roughly why; a
    # full test-runner dump in a hook message buries that in its own output.
    failed="${failed}
--- $cmd
$(printf '%s' "$out" | tail -20)"
  fi
  IFS=,
done
IFS=$old_ifs

[ -z "$failed" ] && gate_pass

gate_block "Quality gate: a gating validator failed. These are the commands on the '- Validators:' line in .steering/tech.md, and they gate CI too — fix the failure rather than working around the gate.
$failed"
