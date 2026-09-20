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

# Read one machine-read value out of a steering file.
#
# THE definition of how a steering anchor is read. Five call sites across the three hooks
# used to carry this expression by hand, and a sixth — the anchor check in assets/ — needs
# to ask the same question the gates ask. A copy that can disagree with its subject is the
# defect #14 and #23 are about; this exists so there is nothing to disagree with.
#
# Exact by design. `- **Owns: ...**` does not match, and that is correct: the consumer would
# not match it either, so a checker using this function sees precisely what a gate sees.
gate_steering_value() {  # <file> <key>
  sed -n "s/^ *- *$2: *//p" "$1" 2>/dev/null | head -1
}

# Emit a spec's Tasks section ONLY — section 3, up to the next heading.
#
# The scoping is the load-bearing part. Acceptance criteria are checkboxes too, and on a
# shipped spec they are commonly left unticked; counting those as open work would make the
# gate fire forever on every finished spec, which is how a gate earns being switched off.
# Both counters below scope through here so they can never disagree about what a task is.
#
# Text in rather than a path, because since #26 the same reading has to serve two sources: a
# file in the working tree, and a blob on a branch nobody is standing on. The file wrappers
# below keep every existing caller unchanged.
_gate_tasks_section_text() {
  printf '%s\n' "$1" | awk '/^#+ *3\./ {f=1; next} /^#+ /{f=0} f'
}

# Count UNTICKED checkboxes: how much work is left.
gate_open_tasks_text() {
  _gate_tasks_section_text "$1" | grep -c '^ *- \[ \]'
}

# Count ALL checkboxes in a spec's Tasks section, ticked or not.
#
# gate_open_tasks returning 0 is ambiguous, and the two meanings are opposites: "every task
# is done" and "no task was ever written". Reading the second as the first blocks a spec that
# is still being drafted, which is the state `spec` step 3 tells the author to create. A
# caller needs both counts to tell them apart.
gate_total_tasks_text() {
  _gate_tasks_section_text "$1" | grep -c '^ *- \[[ xX]\]'
}

# The file forms, kept because a project's own scripts may source this library and ask about a
# spec on disk; the private section wrapper went with #26, having lost its last caller.
# An unreadable or absent file yields empty text and therefore zero, which is
# the reading `review-gate.sh` already depends on and which #8 and its AC7 pinned: zero total
# means "nothing authored", and telling that apart from "cannot be read" is the CALLER's job,
# done before it counts anything.
gate_open_tasks()     { gate_open_tasks_text     "$(cat -- "$1" 2>/dev/null)"; }
gate_total_tasks()    { gate_total_tasks_text    "$(cat -- "$1" 2>/dev/null)"; }

# Read a file from the working tree, or from a branch's own tree when <ref> is given.
#
# Absence returns 1 and unreadability returns 2, so the two stay distinguishable: the gate
# says different things about a receipt nobody wrote and a receipt it could not open, and
# collapsing them would make "I could not check" indistinguishable from "I checked".
_gate_read() {  # <ref, empty for the working tree> <path>
  if [ -z "$1" ]; then
    [ -f "$2" ] || return 1
    [ -r "$2" ] || return 2
    cat -- "$2"
  else
    git cat-file -e "$1:$2" 2>/dev/null || return 1
    git show "$1:$2" 2>/dev/null
  fi
}

# THE question this harness enforces: does this spec hold finished work with no usable review?
#
# One definition, three callers — `review-gate.sh` asks it about the branch you are standing
# on and about every other branch, and `check-unreviewed-work.sh` asks it about a pull
# request's head. Before #26 the receipt logic lived inline in the gate, so the only way to
# ask it anywhere else was to copy it, and a copy that can disagree with its subject is the
# defect class of #14 and #23.
#
# Prints a state, empty when there is nothing to demand. Callers compose their own messages,
# because a gate blocking your turn, a gate naming someone else's branch, and a CI step
# failing a pull request have to say different things about the same fact.
#
#   (empty)             no spec, no tasks authored, tasks still open, or reviewed and current
#   unreadable          the spec file is there and cannot be read
#   no-receipt          finished, and no receipt was ever written
#   receipt-unreadable  finished, and the receipt is there and cannot be read
#   verdict=<v>         finished, with a receipt that does not say CLEAN
#   unresolved-sha=<v>  finished and CLEAN, and <v> is absent or not a commit here
#   stale=<sha> <files> finished and CLEAN, but reviewable source moved since <sha>
gate_spec_review_state() {  # <spec dir> <tip sha> [<ref, empty for the working tree>]
  _dir=$1; _tip=$2; _ref=${3:-}

  _spec=$(_gate_read "$_ref" "$_dir/spec.md"); _rc=$?
  [ "$_rc" -eq 1 ] && return 0
  [ "$_rc" -eq 2 ] && { printf 'unreadable'; return 0; }

  [ "$(gate_total_tasks_text "$_spec")" -eq 0 ] 2>/dev/null && return 0
  [ "$(gate_open_tasks_text "$_spec")" -gt 0 ] 2>/dev/null && return 0

  _receipt=$(_gate_read "$_ref" "$_dir/.review-receipt"); _rc=$?
  [ "$_rc" -eq 1 ] && { printf 'no-receipt'; return 0; }
  [ "$_rc" -eq 2 ] && { printf 'receipt-unreadable'; return 0; }

  _verdict=$(printf '%s\n' "$_receipt" | sed -n 's/^verdict=//p' | head -1)
  [ "$_verdict" = CLEAN ] || { printf 'verdict=%s' "${_verdict:-missing}"; return 0; }

  _sha=$(printf '%s\n' "$_receipt" | sed -n 's/^reviewed_sha=//p' | head -1)
  [ "$_sha" = "$_tip" ] && return 0

  # A receipt whose sha this repository cannot resolve is worse than a stale one: nothing can
  # be compared, so returning "nothing changed" asserts a comparison that never happened.
  # Two shapes reach here, and the first is the sharper — `git diff ..<tip>` resolves an
  # omitted left side to HEAD, so a receipt recording no commit at all used to read as current
  # on the branch it was written on, and in CI compared two unrelated commits.
  #
  # This is the one new way to block, so its no-false-block argument is the line above: a
  # receipt written at the tip returns before ever reaching it. What does reach it is an
  # orphaned sha after a post-review rebase, which SHOULD block — the receipt describes
  # commits that no longer exist.
  if [ -z "$_sha" ] || ! git rev-parse --verify -q "$_sha^{commit}" >/dev/null 2>&1; then
    printf 'unresolved-sha=%s' "${_sha:-missing}"
    return 0
  fi

  # HEAD moved after the review. That is expected and fine when the trailing commits are the
  # work log and the spec's own Status flip. It is not fine when reviewable source moved,
  # because then the receipt describes code that no longer exists. Source globs come from
  # .steering/tech.md so this stays language-neutral.
  #
  # Two ways this used to fail OPEN, both the shell's doing rather than git's, and both
  # silent — which is the worst direction for a gate to fail in.
  #
  #   '*.py'   quotes inside a variable are not removed on expansion, so git received the
  #            literal pathspec '*.py' and matched nothing
  #   *.py     the shell expanded it against the repository root before git saw it, so a
  #            src/-layout project matched nothing and a flat one matched only top level
  #
  # Strip the quotes, then disable globbing across the word split so the pattern reaches git
  # intact. Word splitting is still wanted here: several globs are separated by spaces.
  _globs=$(gate_steering_value .steering/tech.md 'Source globs')
  [ -n "$_globs" ] || _globs='*'
  _globs=$(printf '%s' "$_globs" | tr -d "\"'")
  set -f
  _changed=$(git diff --name-only "$_sha".."$_tip" -- $_globs 2>/dev/null)
  set +f
  [ -z "$_changed" ] && return 0
  printf 'stale=%s %s' "$_sha" "$(echo "$_changed" | tr '\n' ' ')"
}

# One state, one sentence — for callers naming a branch that is not the one in hand, where
# the tailored second person of the gate's own messages would be wrong.
gate_review_state_sentence() {  # <state from gate_spec_review_state>
  case "$1" in
    unreadable)         printf 'its spec exists and cannot be read' ;;
    no-receipt)         printf 'every task is ticked and no reviewer receipt exists' ;;
    receipt-unreadable) printf 'its receipt exists and cannot be read' ;;
    verdict=*)          printf "the recorded review verdict is '%s', not CLEAN" "${1#verdict=}" ;;
    unresolved-sha=*)   printf "its receipt records reviewed_sha '%s', which cannot be resolved here" "${1#unresolved-sha=}" ;;
    stale=*)            _r=${1#stale=}; printf 'source changed since the review at %s: %s' "${_r%% *}" "${_r#* }" ;;
    *)                  printf 'it holds finished work with no usable review' ;;
  esac
}
