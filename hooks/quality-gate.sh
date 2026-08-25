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

# The validator list is read through gate_steering_value. If this hooks/ directory is a mix of
# versions the function is undefined — and `set -u` does not catch an undefined FUNCTION, so
# the read yields empty, the "no validators configured" branch below fires, and the gate exits
# 0 having run nothing. That is a fail-open created by the migration to a shared reader, so the
# migration has to carry the check. The asset guards itself this way; the gate is the half that
# matters more, because its failure is silent.
command -v gate_steering_value >/dev/null 2>&1 || gate_block "Quality gate: gate-lib.sh predates the shared steering reader, so this gate cannot read its validator list. Re-copy the plugin's hooks/ into this project and run again rather than treating this as a pass."

[ -f .steering/tech.md ] || gate_pass

validators=$(gate_steering_value .steering/tech.md Validators)
[ -n "$validators" ] || gate_pass

# Skip when nothing this gate is about has changed.
#
# Without this the gate pays full price on every turn end, including the many that touch
# only docs, specs, or the work log. That is how a gate earns the reputation that gets it
# switched off — and the comment above about keeping it fast is worth nothing if the script
# itself ignores it.
#
# `Source globs` is the same line the review gate reads to decide what counts as reviewable
# source, so a project states "what is code here" once and both gates obey it. When the line
# is absent the gate runs: for a guarantee, failing toward MORE checking is the right
# direction.
globs=$(gate_steering_value .steering/tech.md 'Source globs')
if [ -n "$globs" ] && git rev-parse --git-dir >/dev/null 2>&1; then
  # Unquoted on purpose: the line holds several space-separated globs and each has to reach
  # git as its own pathspec. Quotes inside a variable are NOT removed on expansion, so a
  # line written '*.py' would hand git a literal quote and match nothing — the same
  # fail-open this script's sibling was fixed for, which is why they are stripped first.
  set -- $(printf '%s' "$globs" | tr -d '\042\047')   # \042 = " and \047 = ', stripped so git sees bare globs
  git status --porcelain -- "$@" 2>/dev/null | grep -q . || gate_pass
fi

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
