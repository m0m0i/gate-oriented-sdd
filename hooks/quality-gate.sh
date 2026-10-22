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
#
# The deadline is part of the guarantee, not a cost to keep down (#304). Neither harness turns
# a Stop hook it timed out into a block: Claude Code discards a block written after its TERM,
# and Antigravity's KILL cannot be caught, so a suite that outran the hook's timeout ended the
# turn as a pass. So the gate runs its own body as a child, under a watchdog started first, and
# blocks at a budget of its own, ahead of the timeout: 170 s unless `- Validator budget:` in
# .steering/tech.md says otherwise, and never past what any hook file that runs it allows.
set -u

_gate_name='Quality gate'
# --- bootstrap guard: byte-identical in every hook that blocks through gate-lib.sh ------
#
# The one thing a gate must always be able to do is speak, and until #194 its ability to
# speak was loaded from the file whose absence it had to report. `.` on a file that is not
# there aborts the shell AT the source line below, before gate_block and gate_pass exist:
# stdout stays empty, so Antigravity ends the turn with no sign anything happened, and Claude
# Code reads whatever status the shell chose — 1 under bash 3.2, 2 under dash — neither of
# them a decision this gate made. An empty or truncated copy does not abort at all, and
# leaves every later call answered by `command not found`, which is 127 and keeps going.
#
# So the block is written out by hand, above the source line. That copy is the #14/#23 shape
# gate-lib.sh exists to prevent, and it is contained rather than avoided: everything between
# these two markers is identical byte for byte in every hook that blocks through the library,
# the hook's own name is lifted into $_gate_name above the region so that it can be, and the
# bootstrap-drift case in scripts/test-gates.sh goes red when the copies drift from each
# other or from gate_block.
#
# Nothing is interpolated into the messages. _gate_json_escape lives in the library too, so a
# path spliced in here would be a path nobody escaped — and the cases that trigger these
# messages parse the stdout they produce rather than grepping it.
DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
_gate_bootstrap_block() {             # gate_block, for the one state that cannot call it
  printf '{"decision":"continue","reason":"%s"}\n' "$1"
  printf '%s\n' "$1" >&2
  if [ -n "${ANTIGRAVITY_CONVERSATION_ID:-}" ] || [ -n "${ANTIGRAVITY_AGENT:-}" ]; then
    exit 0
  fi
  exit 2
}
if [ ! -r "$DIR/gate-lib.sh" ]; then
  # Absent and unreadable send you to different places — re-copy the hooks, or fix a mode —
  # so they are not fused into one sentence. #39, one file along.
  if [ -e "$DIR/gate-lib.sh" ]; then
    _gate_bootstrap_block "$_gate_name: gate-lib.sh is beside this hook and cannot be read, so this gate cannot load the plumbing it blocks through. Fix that file's permissions and run again rather than treating this turn as a pass."
  else
    _gate_bootstrap_block "$_gate_name: gate-lib.sh is missing from this hook's own directory, so this gate cannot load the plumbing it blocks through. Re-copy the plugin's hooks/ into this project and run again rather than treating this turn as a pass."
  fi
fi
. "$DIR/gate-lib.sh"
command -v gate_block >/dev/null 2>&1 || _gate_bootstrap_block "$_gate_name: gate-lib.sh loaded and defines no gate_block, so it is not the library this gate blocks through — an empty or truncated copy. Re-copy the plugin's hooks/ into this project and run again rather than treating this turn as a pass."
# --- end bootstrap guard ----------------------------------------------------------------

# The validator list is read through gate_steering_read. If this hooks/ directory is a mix of
# versions the function is undefined — and `set -u` does not catch an undefined FUNCTION, so
# the read yields empty, the "no validators configured" branch below fires, and the gate exits
# 0 having run nothing. That is a fail-open created by the migration to a shared reader, so the
# migration has to carry the check. The asset guards itself this way; the gate is the half that
# matters more, because its failure is silent.
command -v gate_steering_read >/dev/null 2>&1 || gate_block "Quality gate: gate-lib.sh predates the shared steering reader, so this gate cannot read its validator list. Re-copy the plugin's hooks/ into this project and run again rather than treating this as a pass."

# The deadline came with five more (#304), so a gate-lib.sh copied before them is a library older
# than this gate. Unguarded, a missing gate_hook_files reads as no hook file and the bound as the
# ceiling, and a missing gate_bounded or gate_replay is `command not found` with nothing on stdout,
# which a harness reads as a pass. Case 293.
for _qg_fn in gate_validator_budget gate_hook_files gate_hook_timeout gate_bounded gate_replay; do
  command -v "$_qg_fn" >/dev/null 2>&1 || gate_block "Quality gate: gate-lib.sh predates $_qg_fn, which this gate holds itself to a deadline through, so it cannot finish ahead of the harness's timeout. Re-copy the plugin's hooks/ into this project and run again rather than treating this turn as a pass."
done

# The commands on the `- Validators:` line in $validators, one per line, trimmed, the empty ones
# dropped. Comma-separated, because a validator is a whole command and commands contain spaces.
# The child runs them in this order and numbers them from 1, and the parent's timeout block counts
# them the same way, so the two cannot disagree about which one was cut off or never started.
# Inside `set -f`, so a command is never matched against file names on its way to `eval`.
qg_split() {
  _qs_ifs=$IFS
  IFS=,
  set -f
  for _qs_c in $validators; do
    _qs_c=$(printf '%s' "$_qs_c" | sed -e 's/^ *//' -e 's/ *$//')
    [ -z "$_qs_c" ] || printf '%s\n' "$_qs_c"
  done
  set +f
  IFS=$_qs_ifs
}
qg_nl='
'

# The order of runs in this worktree (#331). One record per worktree, written by whichever run
# FINISHED last, let a run that started before a later one failed record its pass after that
# failure, and the next turn end skipped a red tree: two sessions in one checkout, or Antigravity
# running these gates in a reviewer subagent's turn while the parent's ends (#329). The token
# beside the record names the latest run to start or fail here, by the id below; a pass records
# its writer's id as the record's second line, and is honoured only while the token still names
# it. A run never waits for another — a wait would count against #304's deadline — and a run that
# dies partway leaves a token that withholds a pass, never one that grants it.
#
# Both halves write the token: the child when a run starts or a validator fails, the parent on
# every block it builds. Written through a temp file and `mv` in the record's own directory, so a
# reader never sees half a value, and only over nothing or a regular file: `mv` onto a directory,
# or a link to one, moves the file into it and reports success. qg_tnew names the temp file while
# it exists, for each half's EXIT trap; qg_tfail names the step that failed, for the message.
qg_token_write() {  # <value> — status 0 only if the token now holds it
  qg_tfail=""
  [ -n "$qg_token" ] || { qg_tfail="there is no work tree to hold it"; return 1; }
  if [ -e "$qg_token" ] && [ ! -f "$qg_token" ]; then qg_tfail="it is not a regular file"; return 1; fi
  mkdir -p "${qg_token%/*}" 2>/dev/null || { qg_tfail="its directory could not be made"; return 1; }
  qg_tnew=$(mktemp "${qg_token%/*}/quality-run.XXXXXX" 2>/dev/null) || { qg_tnew=""; qg_tfail="no temp file could be made beside it"; return 1; }
  if ! printf '%s\n' "$1" > "$qg_tnew"; then
    qg_tfail="the temp file beside it could not be written"
  elif ! mv -f "$qg_tnew" "$qg_token"; then
    qg_tfail="the temp file could not be moved into place"
  else
    qg_tnew=""; return 0
  fi
  rm -f "$qg_tnew"; qg_tnew=""; return 1
}
# A token that could not be written is removed if it is a regular file, so it names no run at all
# and every skip runs. Anything else at that path already makes every skip run (step 4 reads only a
# regular file), and is left alone. Status 1 only if a token a skip would read may still be there:
# a directory this user cannot search hides one as well as it hides none.
qg_token_drop() {
  if [ -f "$qg_token" ]; then
    rm -f "$qg_token" 2>/dev/null
    [ ! -f "$qg_token" ]; return
  fi
  if [ -e "$qg_token" ] || [ -L "$qg_token" ]; then return 0; fi
  [ ! -e "${qg_token%/*}" ] || [ -x "${qg_token%/*}" ]
}
# A failure, for the parent's block and the child's failed validators: written, or else dropped.
# Status 1 only if neither took, when the token may still name a run that started before this
# failure and the block must say so (qg_unordered); a later failure that takes clears it.
qg_token_fail() {  # <value>
  qg_unordered=""
  qg_token_write "$1" || qg_token_drop || {
    qg_unordered="

This failure could not be recorded at $qg_token, because $qg_tfail, and what is there could not be removed, so a pass recorded by a run that started before it, already or later, may still be skipped on at the next turn end. Remove it by hand."
    return 1
  }
}

if [ "${1-}" != --bounded ]; then
  # --- the parent: the budget, the watchdog, the verdict (#304) --------------------------
  #
  # The parent runs no validator. It works out the budget, runs this same script as its child
  # through gate_bounded, and judges what the child left in the run dir. A verdict reaches the
  # harness one of two ways: a pass or a block the child printed and gate_replay recognised, or a
  # block this parent builds. Every other ending — a cut-off, a signal, a status or stdout that
  # means neither — is the second.

  # A signal to the parent, from the harness or from a validator's group-wide `kill 0`, is
  # recorded and returns (AC5). POSIX runs the trap only once the foreground child has returned,
  # so it cannot cut the child's tree short: the child got the same group-wide signal and ends
  # through its own traps, or the watchdog ends it. The parent then judges, and a signal is a block.
  run=""; qg_sig=""; qg_token=""; qg_tnew=""; qg_tfail=""; qg_unordered=""
  qg_caught() {  # <signal>
    qg_sig="${qg_sig:+$qg_sig, }SIG$1"
    [ -z "$run" ] || { echo "$1" >> "$run/signalled"; } 2>/dev/null
  }
  for _qg_s in HUP INT QUIT TERM USR1 USR2 ALRM; do
    # shellcheck disable=SC2064  # the signal's name is fixed when the trap is set, on purpose
    trap "qg_caught $_qg_s" "$_qg_s"
  done

  # The run dir holds what the child and the watchdog leave (gate_bounded). The EXIT trap removes
  # the files it knows by name and then the directory, whatever else is going on: unlinking a file
  # a validator's leftover background child still holds is harmless, and a directory that cannot
  # be removed stays where it was made, never in the work tree. That replaces a trap that removed
  # nothing whenever its temp name was empty, and left `.out` in the project's root.
  trap '[ -z "$run" ] || { rm -f "$run"/v.* "$run"/fp.* "$run/ppid" "$run/pid" "$run/verdict" "$run/err" "$run/end" "$run/armed" "$run/fired" "$run/nowalk" "$run/done" "$run/signalled" "$run/progress" "$run/budget-error"; rmdir "$run"; } 2>/dev/null; [ -z "$qg_tnew" ] || rm -f "$qg_tnew"' EXIT

  # Every block the parent builds writes a failure to the token and then removes the last pass
  # record. The write (#331) ends the pass of every run that started before this block, still
  # going or already recorded: a child cut off or signalled before any validator failed never
  # reached its own failure write, and no run's id ends in `.failed`. The removal (AC3) covers a
  # child cut off just after it wrote a record, which the next turn end would otherwise skip on;
  # one that fails is named. The seven signals are ignored before anything is written, so exactly
  # one verdict reaches stdout.
  qg_block() {  # <message>
    trap '' HUP INT QUIT TERM USR1 USR2 ALRM
    _qb_m=$1
    if [ "$(git rev-parse --is-inside-work-tree 2>/dev/null)" = true ] \
       && _qb_r=$(git rev-parse --git-path gate-sdd/quality-pass 2>/dev/null); then
      qg_token=${_qb_r%/*}/quality-run
      qg_token_fail "${run##*/}.$$.failed" || _qb_m="$_qb_m$qg_unordered"
    else
      _qb_r=""
    fi
    if [ -n "$_qb_r" ] && [ -e "$_qb_r" ] && ! rm -f "$_qb_r" 2>/dev/null; then
      _qb_m="$_qb_m

The last pass record at $_qb_r could not be removed, so the next turn end may skip the validators on it. Remove it by hand."
    fi
    gate_block "$_qb_m"
  }

  # Listed before the `cd` below, because CLAUDE_PROJECT_DIR and the working directory are the
  # launch's (gate_hook_files).
  qg_files=$(gate_hook_files "$DIR")

  # Under TMPDIR, or under the git directory when TMPDIR cannot hold one: an inherited sandbox
  # TMPDIR that does not exist would otherwise block every turn. Never the work tree, where a
  # validator that asks git for untracked files would find it, and always absolute: the child
  # cds to the git root, and a relative path would then name a directory the parent never reads.
  qg_mkrun() {  # <directory> — a fresh run dir under it, as an absolute path, in $run
    _mr=$(mktemp -d "$1/gate-sdd-run.XXXXXX" 2>/dev/null) || return 1
    run=$(CDPATH= cd -- "$_mr" 2>/dev/null && pwd -P) && return 0
    rmdir -- "$_mr" 2>/dev/null; run=""; return 1
  }
  qg_gitdir=$(git rev-parse --git-path gate-sdd 2>/dev/null) || qg_gitdir=""
  if ! qg_mkrun "${TMPDIR:-/tmp}" && ! { [ -n "$qg_gitdir" ] && mkdir -p "$qg_gitdir" 2>/dev/null && qg_mkrun "$qg_gitdir"; }; then
    qg_block "Quality gate: this gate could not make the directory its check runs in, under TMPDIR (${TMPDIR:-/tmp}) or under the git directory (${qg_gitdir:-none, outside a git repository}), so the check had no deadline it could be held to and the validators did not run. A check the harness kills at its timeout ends the turn as a pass, so this blocks instead. Point TMPDIR at a writable directory, or unset it."
  fi

  # Anchored to the repository root, as the child is below, so .steering/ resolves.
  if repo_root=$(git rev-parse --show-toplevel 2>/dev/null); then
    cd "$repo_root"
  fi

  # The budget: the `- Validator budget:` line, or the library's default. A malformed line is
  # handed to the child, which blocks on it only when the validators are about to run, so a turn
  # the source skip passes is not blocked by it (AC7). An unreadable tech.md hands nothing over,
  # because the child already blocks on that file.
  qg_budget=$(gate_validator_budget .steering/tech.md); qg_vb=$?
  qg_from=line; qg_src="the '- Validator budget:' line in .steering/tech.md"; qg_berr=""
  case "$qg_vb" in
    0) ;;
    1) qg_from=default; qg_src="the default, as .steering/tech.md has no '- Validator budget:' line" ;;
    2) { printf '%s\n' "$qg_budget" > "$run/budget-error"; } 2>/dev/null \
         || qg_block "Quality gate: $qg_budget, and this gate could not hand that to its check through $run. Fix the line and run again."
       qg_berr=yes; qg_budget=$_gate_qg_default; qg_from=default; qg_src="the default, as the '- Validator budget:' line is malformed" ;;
    *) qg_budget=$_gate_qg_default; qg_from=default; qg_src="the default" ;;
  esac

  # Never past what a hook file that runs this gate allows: the shortest "timeout" any of them
  # gives it, less the margin the gate keeps back to write its block (AC9). A file that cannot be
  # read or parsed, or an entry that names this gate with no "timeout", blocks at once. Split on
  # newlines alone, so a path holding a space stays one argument.
  _qg_ifs=$IFS; IFS=$qg_nl
  set -f
  # shellcheck disable=SC2086  # one hook file per line
  set -- $qg_files
  set +f
  IFS=$_qg_ifs
  qg_ht=$(gate_hook_timeout quality-gate.sh "$_gate_qg_ceiling" "$@") \
    || qg_block "Quality gate: $qg_ht, so this gate cannot tell how long it has before the harness's timeout, and its validators did not run. A check the harness kills at its timeout ends the turn as a pass, so this blocks instead."
  qg_t=${qg_ht%% *}; qg_tsrc=${qg_ht#* }
  case "$qg_t" in
    ''|*[!0-9]*) qg_block "Quality gate: the hook-timeout reader answered '$qg_ht', which is no number of seconds, so this gate cannot tell how long it has. Re-copy the plugin's hooks/ into this project and run again rather than treating this turn as a pass." ;;
  esac
  qg_bound=$((qg_t - _gate_margin))
  [ "$qg_bound" -gt 0 ] || qg_block "Quality gate: $qg_tsrc gives this gate a \"timeout\" of $qg_t s, which leaves nothing once it keeps $_gate_margin s back to write its verdict, so its validators did not run. Raise that \"timeout\"."
  # The ceiling the reader answers when no file names this gate is no file, and is never named as
  # one; a file that ties the budget is, since raising the line would not move it.
  if [ "$qg_tsrc" != ceiling ] && [ "$qg_bound" -le "$qg_budget" ]; then
    qg_budget=$qg_bound; qg_from=file
    qg_src="the \"timeout\" of $qg_t s that $qg_tsrc gives this gate, less the $_gate_margin s it keeps back to write its verdict"
  fi

  # The child is this script with --bounded and the run dir. The hook's stdin and the working
  # directory pass to it, and through it to the validators.
  if [ -n "$qg_berr" ]; then
    gate_bounded "$qg_budget" "$run" sh "$DIR/quality-gate.sh" --bounded "$run" --budget-error "$run/budget-error"; qg_rc=$?
  else
    gate_bounded "$qg_budget" "$run" sh "$DIR/quality-gate.sh" --bounded "$run"; qg_rc=$?
  fi

  # The validator a cut-off or a signal caught running: `progress` holds `start <n> <command>`
  # before validator n and `ok <n>` or `fail <n>` after it, so it is the last start with no end.
  qg_open() { awk '$1 == "start" { s = $2 } ($1 == "ok" || $1 == "fail") && $2 == s { s = "" } END { print s }' "$run/progress" 2>/dev/null; }

  # The timeout block (AC1, AC2), built once the watchdog has finished its kill, from what the
  # child recorded: the validator it cut off with the tail of its v.<n>, whatever it wrote before
  # it died; each one that failed before that, with its tail as an ordinary failure has it; and
  # each one after the last start, which never ran. Then, where the watchdog could not walk the
  # child's tree, that only the child was killed (AC4); and a remedy that follows from what set
  # the budget.
  qg_timeout_block() {
    validators=$(gate_steering_value .steering/tech.md Validators)
    _tb_cut=$(qg_open)
    _tb_last=$(awk '$1 == "start" { n = $2 } END { print n + 0 }' "$run/progress" 2>/dev/null) || _tb_last=0
    printf "Quality gate: the validators did not finish within this gate's budget of %s s, set by %s, so this turn is blocked rather than passed. A gate the harness kills at its timeout ends the turn as a pass, so this gate keeps a deadline of its own and blocks at it." "$qg_budget" "$qg_src"
    if [ "${_tb_last:-0}" -eq 0 ]; then
      printf ' It was cut off before its first validator started.'
    elif [ -z "$_tb_cut" ]; then
      printf ' Every validator it started had finished, and it was cut off before it reached a verdict.'
    fi
    _tb_n=0; _tb_body=""
    while IFS= read -r _tb_c; do
      [ -n "$_tb_c" ] || continue
      _tb_n=$((_tb_n + 1))
      if [ "$_tb_n" = "$_tb_cut" ]; then
        _tb_body="$_tb_body
--- $_tb_c (cut off at the deadline)"
      elif [ "$_tb_n" -gt "${_tb_last:-0}" ]; then
        _tb_body="$_tb_body
--- $_tb_c (did not run)"; continue
      elif grep -qx "fail $_tb_n" "$run/progress" 2>/dev/null; then
        _tb_body="$_tb_body
--- $_tb_c"
      else
        continue
      fi
      _tb_t=$(tail -20 "$run/v.$_tb_n" 2>/dev/null)
      [ -z "$_tb_t" ] || _tb_body="$_tb_body
$_tb_t"
    done <<EOF
$(qg_split)
EOF
    [ -z "$_tb_body" ] || printf '\n%s' "$_tb_body"
    printf '%s' "$qg_nw"
    printf '\n\n'
    if [ "$qg_budget" -ge "$_gate_qg_max" ]; then
      printf "%s s is the most this gate can hold: the hook's ceiling of %s s, less the %s s it keeps back to write this block. No budget holds this suite. Make it faster, or move the slow validator off the '- Validators:' line to CI and give the reason in .steering/tech.md." "$_gate_qg_max" "$_gate_qg_ceiling" "$_gate_margin"
    elif [ "$qg_from" = file ]; then
      printf "To give it more time, raise that \"timeout\" in %s to the %s s the plugin ships, or re-run init, which renders it. The budget is then %s s, or what '- Validator budget:' in .steering/tech.md says, up to %s." "$qg_tsrc" "$_gate_qg_ceiling" "$_gate_qg_default" "$_gate_qg_max"
    else
      printf "To give it more time, write '- Validator budget: <seconds>' in .steering/tech.md, a whole number up to %s, or make the suite faster. A validator that alone needs more than %s s belongs in CI rather than on the '- Validators:' line." "$_gate_qg_max" "$_gate_qg_max"
    fi
  }

  # Judged with the seven signals ignored: a signal first, which no replay outranks; then the
  # child's own verdict, if it marked one complete; then the deadline; and anything else is a
  # check that ended without a verdict. On the harness's own TERM the block is discarded, which
  # costs nothing; on a stray signal it is the right answer.
  trap '' HUP INT QUIT TERM USR1 USR2 ALRM
  qg_nw=""; [ ! -e "$run/nowalk" ] || qg_nw="

This host's process listing did not show the check's process tree, so only the check itself was killed, and a validator's own children may still be running."
  if [ -n "$qg_sig" ]; then
    validators=$(gate_steering_value .steering/tech.md Validators)
    qg_c=$(qg_open); [ -z "$qg_c" ] || qg_c=$(qg_split | sed -n "${qg_c}p")
    qg_block "Quality gate: this gate received $qg_sig before it reached a verdict, so this turn is blocked rather than passed.${qg_c:+ It was running: $qg_c.} A validator that runs 'kill 0', or ends with the common trap 'kill 0' EXIT, sends its signal to the whole process group, this gate included. If the harness sent it at its timeout this block is discarded, which costs nothing; if it repeats, look for a validator that signals its process group.$qg_nw"
  fi
  gate_replay "$run" "$qg_rc"
  [ ! -e "$run/fired" ] || qg_block "$(qg_timeout_block)"
  qg_e=""; [ ! -s "$run/err" ] || qg_e="

Its last output:
$(tail -20 "$run/err")"
  qg_block "Quality gate: its check ended without a verdict (status $qg_rc), so this turn is blocked rather than passed: an ending with no pass and no block reads to the harness as a pass.$qg_e"
fi

# --- the child: the body, under the parent's deadline -------------------------------------
#
# Run only as `quality-gate.sh --bounded <run dir>`, by the parent above. It blocks unless the run
# dir is a directory whose `pid` holds this shell's own pid, which gate_bounded's launcher wrote
# before any of this ran: a hook entry that wrote --bounded by hand gets a block, never an
# unbounded body, and never a `set -u` abort with nothing on stdout, which a harness reads as a
# pass. Only then is _gate_child_run set, which has gate_pass and gate_block mark the verdict
# complete. Its own traps may still exit 1xx, because the parent judges that ending.
shift
if [ ! -d "${1-}" ] || [ "$(cat -- "$1/pid" 2>/dev/null)" != "$$" ]; then
  gate_block "Quality gate: this gate was started with --bounded and without a run directory of its own, so it has no deadline it can be held to, and its validators did not run. --bounded is for the gate's own use; a hook runs the gate with no arguments."
fi
run=$1; shift
_gate_child_run=$run
qg_budget_error=""
if [ "${1-}" = --budget-error ]; then
  qg_budget_error=$(cat -- "${2-}" 2>/dev/null)
  [ -n "$qg_budget_error" ] || qg_budget_error="the '- Validator budget:' line in .steering/tech.md is malformed, and why could not be read from ${2-}"
fi

# Anchor to the repository root so relative paths (.steering/, .specs/) resolve
# correctly regardless of the working directory the hook was invoked from.
if repo_root=$(git rev-parse --show-toplevel 2>/dev/null); then
  cd "$repo_root"
fi

# Absent and unreadable are opposite answers, and this gate gave them the same one. `[ -f ]`
# passes for a mode-000 file, the read came back empty, and the "no validators configured"
# branch below exited 0 having verified nothing — .steering/product.md's own BLOCKER shape,
# in the gate .steering/tech.md calls the one guarantee. #39.
#
# Absent still passes, and that is not the same judgment made twice: a project that has not
# declared its validators is not one whose turns should be blocked, which is what the case
# beside this one pins. A project that declared them in a file nobody can open is.
validators=$(gate_steering_read .steering/tech.md Validators); rc=$?
[ "$rc" -eq 1 ] && gate_pass
[ "$rc" -eq 2 ] && gate_block "Quality gate: .steering/tech.md exists and cannot be read, so this gate cannot find out which validators it is supposed to run. Fix the file's permissions rather than treating this as a pass — a gate that could not look is not a gate that found nothing."
[ -n "$validators" ] || gate_pass

# Skip when the source has not changed since the validators last passed.
#
# Without a skip the gate pays full price on every turn end, including the many that touch
# only docs, specs, or the work log. That is how a gate earns the reputation that gets it
# switched off — and the comment above about keeping it fast is worth nothing if the script
# itself ignores it.
#
# The question is "has the source changed since the last pass?", not "is any source
# uncommitted?". Until #297 the skip asked the second, with `git status`, and `implement`
# commits every task — so a red task committed during the turn ended it with `{}` and no
# validator run, and stayed invisible to every turn end after it. The answer is a fingerprint
# of the source's CONTENT (below), compared with a record written only when every validator
# passed, and honoured only while no other run has started or failed in this worktree since
# (#331, below). Committing content that already passed does not change it; anything else does.
#
# `Source globs` is the same line the review gate reads to decide what counts as reviewable
# source, so a project states "what is code here" once and both gates obey it. When the line
# is absent, outside a work tree, with no record yet, or when any step below fails, the gate
# runs: for a guarantee, failing toward MORE checking is the right direction.

# The fingerprint of the source the pathspecs match, in $fp; on any failure $fp is empty and
# $qg_step names what failed. Its scratch files are fp.* in the run dir, which the parent removes.
# Built in a COPY of the index so the real one is never touched,
# and every git call is checked on its own — never through a pipeline, whose status would be
# its last command's, which is how `| grep -q .` read git's 128 on a rejected pathspec as
# "nothing changed".
#
#   - `cp -p`, not `cp`: git decides an entry is racily clean by comparing it with the index
#     FILE's mtime, and a copy stamped "now" lets a same-size edit made in the same second as
#     the last index write match on stat alone and keep its old blob id — a red tree passing.
#   - `ls-files -c -o --exclude-standard` lists tracked and untracked-not-ignored files whatever
#     `status.showUntrackedFiles` says, and `update-index --add --remove --info-only` re-hashes
#     them into the copy without writing an object.
#   - Hashed in with the listing: a format tag; the Validators and Source globs lines, so adding
#     a validator runs it; the plugin-root variables, so a pass in one of #264's two
#     environments is not trusted by the other; and this gate's own files, so an upgrade by
#     re-copy runs once.
#   - GIT_INDEX_FILE prefixes git itself only. On a shell function, macOS sh keeps the
#     assignment and exports it to every validator after it.
qg_fingerprint() {  # <pathspec>...
  fp=""
  qg_tmp="$run/fp"
  qg_idx=$(git rev-parse --git-path index) || { qg_step="git rev-parse --git-path index"; return 1; }
  if [ -f "$qg_idx" ]; then
    cp -p "$qg_idx" "$qg_tmp.idx" || { qg_step="copying the index"; return 1; }
  fi
  git ls-files -z -c -o --exclude-standard -- "$@" > "$qg_tmp.list" || { qg_step="git ls-files"; return 1; }
  GIT_INDEX_FILE="$qg_tmp.idx" git update-index -z --add --remove --info-only --stdin < "$qg_tmp.list" \
    || { qg_step="git update-index"; return 1; }
  { printf 'gate-sdd quality-pass 1\n%s\n%s\n%s\n%s\n' "$validators" "$globs" "${CLAUDE_PLUGIN_ROOT-}" "${GATE_SDD_PLUGIN_ROOT-}" \
    && git hash-object --no-filters -- "$DIR/quality-gate.sh" "$DIR/gate-lib.sh" \
    && GIT_INDEX_FILE="$qg_tmp.idx" git ls-files -s -- "$@"; } > "$qg_tmp.fp" || { qg_step="listing the source"; return 1; }
  fp=$(git hash-object --stdin < "$qg_tmp.fp") || { fp=""; qg_step="git hash-object"; return 1; }
}

trap 'exit 129' HUP; trap 'exit 130' INT; trap 'exit 143' TERM
# A temp file the child made and did not move into place is removed however it ends; the parent
# removes the run dir, but these live in the git directory, beside the files they replace. Both
# are emptied first, so a value inherited from the environment never names a file to remove.
qg_tnew=""; qg_new=""; qg_tfail=""; qg_unordered=""; qg_unrec=""
trap '[ -z "${qg_tnew-}" ] || rm -f "$qg_tnew"; [ -z "${qg_new-}" ] || rm -f "$qg_new"' EXIT

fp=""; qg_step=""; qg_record=""; qg_token=""; qg_stale=""
# The record is per worktree — git keeps a name it does not know under the worktree's own git
# directory — never tracked, and relative, which is safe because the gate is at the toplevel. It
# is resolved whatever the globs line says, because the removal below must happen on every run:
# a turn that failed with the line absent once left an older pass behind (#297's review, case 257).
qg_tree=""
if [ "$(git rev-parse --is-inside-work-tree 2>/dev/null)" = true ]; then
  qg_tree=yes
  qg_record=$(git rev-parse --git-path gate-sdd/quality-pass) || { qg_record=""; qg_step="git rev-parse --git-path"; }
fi
[ -z "$qg_record" ] || qg_token=${qg_record%/*}/quality-run
globs=$(gate_steering_value .steering/tech.md 'Source globs')
if [ -n "$globs" ] && [ -n "$qg_tree" ]; then
  # Unquoted on purpose: the line holds several space-separated globs and each has to reach
  # git as its own pathspec. Quotes inside a variable are NOT removed on expansion, so a
  # line written '*.py' would hand git a literal quote and match nothing — the same
  # fail-open this script's sibling was fixed for, which is why they are stripped first.
  #
  # Unquoted also means pathname expansion, and that is the second half of #1: the shell
  # matched a bare `*.py` against the repository root before git saw it, so a flat project
  # with one unchanged `.py` at the root handed git that file's name, git found it clean, and
  # the gate passed having run nothing for every change below the root (#254). The library's
  # three copies of this split sit inside `set -f`, and so does this one now. The two lines
  # are whole lines of their own, because case 204 recognises the region by them, and
  # expansion is back on before the validator loop, where an `ls *.log` has to work.
  set -f
  # shellcheck disable=SC2046  # deliberate word-split: one pathspec per glob (#1); quoted, case 164 goes red
  set -- $(printf '%s' "$globs" | tr -d '\042\047')   # \042 = " and \047 = ', stripped so git sees bare globs
  set +f
  if [ -n "$qg_record" ] && qg_fingerprint "$@"; then
    if [ -e "$qg_record" ] && ! [ -r "$qg_record" ]; then
      qg_step="reading $qg_record"
    elif [ -r "$qg_record" ]; then
      # A matching source counts only while the record's writer is still the latest run to start
      # or fail here (#331). Read once and split here: two reads could pair one record's
      # fingerprint with the writer of the record a concurrent run moved in between them. A record
      # with no writer, which an older gate wrote, and a missing token run the validators; a token
      # that is not a regular file, or cannot be read, is a failed step and is named as one.
      if ! qg_rec=$(cat -- "$qg_record" 2>/dev/null); then
        qg_step="reading $qg_record"
      elif [ "${qg_rec%%"$qg_nl"*}" = "$fp" ]; then
        case $qg_rec in
          *"$qg_nl"*) qg_writer=${qg_rec#*"$qg_nl"}; qg_writer=${qg_writer%%"$qg_nl"*} ;;
          *) qg_writer="" ;;
        esac
        if [ -z "$qg_writer" ]; then
          qg_stale="the record names no run that wrote it, as one an older gate wrote does not"
        elif [ ! -e "$qg_token" ] && [ ! -L "$qg_token" ]; then
          qg_stale="no run is recorded as the latest to start or fail in this worktree"
        elif [ ! -f "$qg_token" ] || ! qg_latest=$(cat -- "$qg_token" 2>/dev/null); then
          qg_step="reading $qg_token"
        elif [ "$qg_latest" = "$qg_writer" ]; then
          gate_pass
        else
          qg_stale="another run has started or failed in this worktree since that pass was recorded"
        fi
      fi
    fi
  fi
fi
# A malformed `- Validator budget:` line blocks here, where the validators are about to run, and
# not before the skip: a turn the skip passes is not blocked by it (AC7). The record is kept, as
# the line changes nothing the last pass verified.
[ -z "$qg_budget_error" ] || gate_block "Quality gate: $qg_budget_error. The validators did not run. Fix the line, or remove it to take the default of $_gate_qg_default s."
# Q2 of #297's spec: a step that failed runs the validators and says so, whatever they find — a
# project paying for a full run on every turn should be able to find out why.
[ -z "$qg_step" ] || printf 'Quality gate: could not tell whether source changed since the validators last passed (%s failed), so they ran.\n' "$qg_step" >&2
[ -z "$qg_stale" ] || printf 'Quality gate: the source matches the last pass, but %s, so the validators ran.\n' "$qg_stale" >&2
# This run starts here, before the record is removed (#331): from now on no run that started
# before it can record a pass or be skipped on; only this run, or one that starts after it, can.
# A start that cannot be written leaves this run unable to record its own pass, which costs the
# next turn end a run, and is removed. One that cannot be removed either may still name a run that
# started earlier, whose pass is then skipped on: the same residual as a record that cannot be
# removed, below, and named the same way.
qg_id="${run##*/}.$$"; qg_why=""
if ! qg_token_write "$qg_id"; then
  qg_id=""; qg_why="this run's start could not be recorded at ${qg_token:-a token outside any work tree}, because $qg_tfail"
  qg_token_drop || printf 'Quality gate: %s, and what is there could not be removed, so a pass an earlier run records may still be skipped on. Remove it by hand.\n' "$qg_why" >&2
fi
# The validators are about to run, so the last pass stops counting until they pass again —
# whatever the globs line says. Kept through a failure, the record matched source put back to a
# state that passed EARLIER, and the gate skipped a tree still red from an input outside the
# globs (cases 248, 257). A run cut off at the deadline leaves no pass behind either: the parent
# removes the record before it blocks, in case the child wrote one just before it was killed.
if [ -n "$qg_record" ] && [ -e "$qg_record" ] && ! rm -f "$qg_record"; then
  printf 'Quality gate: could not remove the last pass record at %s; the validators run anyway.\n' "$qg_record" >&2
fi

failed=""
# Each validator runs in a subshell of its own, so an `exit`, a `cd` or an assignment stays inside
# it, in the foreground with the hook's stdin and pathname expansion (case 203). Its output goes to
# v.<n> in the run dir, never to this shell's stdout, which carries the verdict alone and nothing
# else; and to a file rather than a `$(...)` pipe, which a validator's leftover background child
# held open until it exited, holding the gate with it. `progress` records each one's start and end
# by its number, not its command, since two validators may share one: that is what the parent's
# timeout block reads when the deadline cuts this run short.
n=0
cmds=$(qg_split)
old_ifs=$IFS
IFS=$qg_nl
set -f
for cmd in $cmds; do
  set +f
  IFS=$old_ifs
  n=$((n + 1))
  printf 'start %s %s\n' "$n" "$cmd" >> "$run/progress"
  if ( eval "$cmd" ) > "$run/v.$n" 2>&1; then
    printf 'ok %s\n' "$n" >> "$run/progress"
  else
    printf 'fail %s\n' "$n" >> "$run/progress"
    # Every failure is an ordering event, written before the next validator starts (#331): a run
    # that started before this failure, earlier or later than this run, can no longer record a
    # pass, or be skipped on one it already recorded, and a cut-off or a signal from here on
    # cannot undo that. Not only the first: a run can start between two failures.
    qg_token_fail "${run##*/}.$$.failed" || :
    if [ -n "$qg_record" ] && [ -e "$qg_record" ] && ! rm -f "$qg_record" 2>/dev/null; then
      qg_unrec="

The last pass record at $qg_record could not be removed, so the next turn end may skip the validators on it. Remove it by hand."
    fi
    # Only the tail. The model needs to know which validator failed and roughly why; a
    # full test-runner dump in a hook message buries that in its own output.
    failed="${failed}
--- $cmd
$(tail -20 "$run/v.$n")"
  fi
done
set +f
IFS=$old_ifs

# Record the pass — the fingerprint taken BEFORE the first validator ran, so an edit made during
# the run is not recorded as passed — through a temp file and `mv` in the same directory, so a
# reader never sees half a value. A record that cannot be written costs the next turn a run,
# never a pass, and says so. Only a run the token still names writes one (#331): any other is
# older than a start or a failure since, and a stale pass written over a newer one would cost a
# run. Correctness does not rest on this read, because the skip asks the token too.
if [ -z "$failed" ] && [ -n "$fp" ] && [ -n "$qg_record" ]; then
  if [ -z "$qg_why" ]; then
    if [ ! -f "$qg_token" ] || ! qg_latest=$(cat -- "$qg_token" 2>/dev/null); then
      qg_why="reading $qg_token failed"
    elif [ "$qg_latest" != "$qg_id" ]; then
      qg_why="another run started or failed in this worktree after this one began"
    fi
  fi
  if [ -n "$qg_why" ]; then
    printf 'Quality gate: the validators passed, and the pass could not be recorded at %s, because %s, so the next turn end runs them again.\n' "$qg_record" "$qg_why" >&2
  elif ! { mkdir -p "${qg_record%/*}" && qg_new=$(mktemp "${qg_record%/*}/quality-pass.XXXXXX") \
         && printf '%s\n%s\n' "$fp" "$qg_id" > "$qg_new" && mv -f "$qg_new" "$qg_record"; }; then
    [ -z "${qg_new-}" ] || rm -f "$qg_new"
    printf 'Quality gate: the validators passed, and the pass could not be recorded at %s, so the next turn end runs them again.\n' "$qg_record" >&2
  fi
  qg_new=""
fi

[ -z "$failed" ] && gate_pass

gate_block "Quality gate: a gating validator failed. These are the commands on the '- Validators:' line in .steering/tech.md, and they gate CI too — fix the failure rather than working around the gate.
$failed$qg_unordered$qg_unrec"
