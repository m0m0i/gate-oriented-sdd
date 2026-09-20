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
    # The existence test passing and the read failing is object-store corruption, which the
    # working-tree branch above distinguishes and this one used to flatten into "empty file"
    # — and an empty spec counts zero tasks, which is silence.
    git show "$1:$2" 2>/dev/null || return 2
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

# Has this branch's WORK reached the base — whatever merge style put it there?
#
# The skip beside this one asks `git merge-base --is-ancestor`, which answers whether a COMMIT
# was joined into the base's history. That is a different question, and the two coincide only
# under a merge commit or a fast-forward. A squash merge writes a new commit carrying the
# branch's result with no parent link back to it, so the tip is not an ancestor and never will
# be: the ancestry test is not failing intermittently, it is being asked something that can no
# longer be true. In a squash-merging repository the skip therefore never fired at all, and
# every shipped but undeleted spec branch stayed in the scan permanently. #182.
#
# Two steps, cheap first, and every unresolvable input leaves the skip unfired:
#
#   1. the base's tree carries this slug's spec, under .specs/ or .specs/_archive/
#   2. the branch holds nothing beyond what shipped
#
# Both locations count and neither alone does: `_archive/` is timely only after a sweep that
# `archive` runs on request, and `.specs/` is what that sweep empties.
#
# Step 1 alone is a fail-open, and it is the one this had to avoid — merge, then carry on
# committing to the same branch, and the slug is in the base while the branch holds work nobody
# reviewed. A slug reaching the base is a fact about the SPEC, not about the branch, and
# reading the first as the second is #26's defect returning through the door built to close
# its side effects. Case 134.
#
# Step 2's anchor is the FIRST commit on the base carrying the slug — the squash commit, since
# a spec is its branch's first commit and reaches the base only when the branch does. First
# rather than last, so `archive`'s later `git mv` into `_archive/` cannot drag the anchor
# forward onto work the branch never had. The comparison is scoped to the branch's OWN
# footprint rather than to all of `- Source globs:`, and that scoping is what makes it survive
# a base that moves: the anchor carries the branch's content at exactly those paths, while
# whatever else landed between the branch's fork and its squash is at other paths. Compared
# against the base's tip instead, the skip would stop firing the moment anyone touched one of
# those files again — the same permanent block wearing a new mechanism.
#
# The intersection is done in awk rather than by handing the footprint back to git as
# pathspecs. Word-splitting a path list splits a path containing a space into two pathspecs
# that match nothing, and a pathspec matching nothing makes `git diff` print nothing, which
# reads here as "shipped". That is a fail-open produced by quoting, which is #1's whole family.
gate_work_reached_base() {  # <slug> <tip sha> <base sha>
  _wslug=$1; _wtip=$2; _wbase=$3
  [ -n "$_wslug" ] && [ -n "$_wtip" ] && [ -n "$_wbase" ] || return 1

  _wlive=".specs/$_wslug/spec.md"
  _warch=".specs/_archive/$_wslug/spec.md"
  git cat-file -e "$_wbase:$_wlive" 2>/dev/null \
    || git cat-file -e "$_wbase:$_warch" 2>/dev/null \
    || return 1

  _wanchor=$(git rev-list --reverse "$_wbase" -- "$_wlive" "$_warch" 2>/dev/null | head -1)
  [ -n "$_wanchor" ] || return 1

  _wfork=$(git merge-base "$_wbase" "$_wtip" 2>/dev/null) || return 1
  [ -n "$_wfork" ] || return 1

  _wglobs=$(gate_steering_value .steering/tech.md 'Source globs')
  [ -n "$_wglobs" ] || _wglobs='*'
  _wglobs=$(printf '%s' "$_wglobs" | tr -d "\"'")

  # Exit status, never emptiness. `- Source globs:` is consumer-authored and nothing validates
  # it — `check-steering-anchors.sh` says in its own header that it does not judge whether a
  # value is any good — so a pathspec git rejects (`:(globs)` for `:(glob)`, a typo echoing the
  # key's own name) makes this exit 128 having printed nothing. Nothing is also what a branch
  # with no footprint prints, and reading the two as one silenced the gate on both call sites
  # with no diagnostic anywhere. Review round 1's BLOCKER, case 140. A git that could not
  # answer leaves the skip unfired, which is the same direction as every other guard here.
  # What did this branch touch? Two readings, and they are COMPLEMENTS rather than rivals —
  # each is blind to a shape the other catches, and "absent from the footprint" is read below
  # as "nothing to review", so a blind spot here is a silenced gate.
  #
  #   git log   the branch's own commits. Sees a path changed and then changed back — add a
  #             file, ship it, delete it on the branch — which a tree comparison cannot,
  #             because fork and tip agree at a path neither of them has. Round 3, case 142.
  #             Blind to a merge commit, for which --name-only prints no diff at all.
  #   git diff  the net tree comparison. Sees content that exists ONLY in a merge commit — a
  #             conflict fixup, or a hand edit between `git merge --no-commit` and the commit
  #             — because it does not care how the trees came to differ. Round 4, case 143.
  #
  # So: the union. It can only grow, and a larger footprint intersects more below, so the skip
  # fires LESS — widening is the safe way to be wrong here. Neither term widens the scoping the
  # design turns on, because _wfork is the merge base: whatever the base carried before this
  # branch forked is common to both sides and appears in neither term.
  set -f
  _wlog=$(git log --format= --name-only "$_wfork".."$_wtip" -- $_wglobs 2>/dev/null) || { set +f; return 1; }
  _wnet=$(git diff --name-only "$_wfork" "$_wtip" -- $_wglobs 2>/dev/null) || { set +f; return 1; }
  set +f

  # Folded here rather than piped above, for two reasons. A pipeline's status is its LAST
  # command's, so `git log ... | sort -u` hands back sort's success and undoes the exit-status
  # reads two lines up — case 140 went red on exactly that regression. And `git log
  # --name-only` separates each commit's paths with a BLANK line, which is the sentinel the
  # intersection below splits its two lists on; left in, the first commit boundary would be
  # read as the end of the footprint.
  #
  # `|| return 1` for the same reason every other step here has it, and it was missing for one
  # round: an awk that exits non-zero prints nothing, and nothing is what a branch with no
  # footprint prints — so the empty-footprint return below read "awk could not tell me" as
  # "the branch touched nothing". UNPINNED, and said out loud rather than implied: no
  # consumer-authored value reaches this line, so the trigger is awk itself failing and no
  # cheap fixture produces it. The anchor diff's guard is unpinned for its own reason, which
  # case 140 records.
  #
  # `NF` and not `length($0)`: it is what guarantees _wfoot holds no blank-equivalent line,
  # which is what makes the sentinel below safe. The cost is a corner — a path named entirely
  # of spaces is dropped from the footprint, which narrows it, in the one place this function
  # argues that only widening is safe. Fixing it means giving the two lists a separator git
  # cannot emit; changing NF alone reintroduces case 139's truncation.
  _wfoot=$(printf '%s\n%s\n' "$_wlog" "$_wnet" | awk 'NF && !seen[$0]++') || return 1

  # Answered, and the answer is that the branch carries no reviewable source of its own. Step 1
  # already established the work is in the base. Distinct from the line above on purpose: "git
  # could not tell me" and "git told me nothing changed" must not collapse into one return.
  [ -n "$_wfoot" ] || return 0

  set -f
  _wnow=$(git diff --name-only "$_wanchor" "$_wtip" -- $_wglobs 2>/dev/null) || { set +f; return 1; }
  set +f

  # Both lists go in on STDIN, separated by a blank line, because `awk -v foot="$list"` cannot
  # carry one: a -v assignment takes no newline, and BSD awk warns `newline in string` and
  # truncates at the first path. Truncated, the intersection sees one file and a branch that
  # carried on in any other reads as shipped — a fail-open produced by quoting, which is #1's
  # family, and the warning lands on the stderr a Stop hook hands to the user. A blank line is
  # a safe separator because `git diff --name-only` never emits an empty path. Case 139.
  # `|| return 1` for the same reason the two git calls above have it, and it was missing here
  # for two rounds: an awk that exits non-zero prints nothing, and nothing is what an empty
  # intersection prints. `$(a | b)` carries b's status in POSIX sh, so this is one token.
  _wleft=$(printf '%s\n\n%s\n' "$_wfoot" "$_wnow" | awk '
    !split_seen && NF == 0 { split_seen = 1; next }
    !split_seen { foot[$0] = 1; next }
    NF > 0 && $0 in foot { print }
  ') || return 1
  [ -z "$_wleft" ]
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
