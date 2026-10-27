#!/bin/sh
# review-gate.sh — the harness's one enforced rule.
#
# Everything else here is guidance a model can decline. This is the rule that
# holds: finished work cannot sit in this repository without a fresh, clean review.
#
# It asks that about the REPOSITORY, not about where HEAD happens to point, and not about
# whether the spec happens to be checked out. Those are three questions, and the gate has had
# to be taught each of them in turn. Only the third's ABSENCE half is closed: which tree a
# spec that IS checked out is read from is still the working tree's call, deliberately, and
# check_current_branch says why. Until #26 only the first was asked: on a branch with no spec the
# gate exited 0 and printed nothing, so `git checkout main` turned the one enforced rule off
# and left no trace — a skipped review and a clean repository produced identical silence. #26
# left the third behind, one branch wide: the branch you stand on was read from the working
# tree and then skipped by name in the scan, so the same silence was still available by
# emptying the tree instead of moving HEAD. #177 closed it, and check_current_branch carries
# the reasoning.
#
# It is still deliberately narrow. A gate that fires on ordinary turns is a gate people
# disable, and a disabled gate protects nothing — so this is silent on every case that is not
# the one it exists for. What it is not is narrow in a way the author chooses per turn.
#
# Nor is it a rule that holds only while the check is quick (#304). Neither harness turns a Stop
# hook it timed out into a block: Claude Code discards a block written after its TERM, and
# Antigravity's KILL cannot be caught, so a scan that outran the hook's timeout ended the turn as a
# pass. So the gate runs its own body as a child, under a watchdog started first, and blocks at a
# budget of its own, ahead of the timeout: the hook's ceiling less a margin, never past what any
# hook file that runs it allows. quality-gate.sh has the same shape, and gate_bounded the mechanism.
set -u

_gate_name='Review gate'
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
# messages parse the stdout they produce rather than grepping it. Each ends, as gate_block's
# do, with the library's _gate_addressee paragraph, written out here for the same reason (#329).
DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
_gate_bootstrap_block() {             # gate_block, for the one state that cannot call it
  _gate_addressee='This block is for the session doing the work. A reviewer that receives it ends its turn: it writes nothing, fixes nothing, starts nothing and waits for nothing.'
  printf '{"decision":"continue","reason":"%s\\n\\n%s"}\n' "$1" "$_gate_addressee"
  printf '%s\n\n%s\n' "$1" "$_gate_addressee" >&2
  case "${GATE_SDD_HARNESS:-}" in antigravity) exit 0 ;; claude-code) exit 2 ;; esac
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

git rev-parse --git-dir >/dev/null 2>&1 || gate_pass

# The first two readers below came with #233 and the third with #191, so a gate-lib.sh copied
# before them is a library older than this gate. Unguarded, a missing gate_head_branch exits 127
# and reaches the naming line's damage arm, which sends the person to repair a healthy
# repository; a missing gate_ref_commit empties the base without a word; and a missing
# gate_tree_names is not called at all while the spec is in the working tree, so the gate goes
# on over a library whose scan still reads an object git cannot get as no spec.
# quality-gate.sh guards its reader the same way. Case 190.
for _gate_fn in gate_head_branch gate_ref_commit gate_tree_names; do
  command -v "$_gate_fn" >/dev/null 2>&1 || gate_block "Review gate: gate-lib.sh predates $_gate_fn, which this gate reads branches through, so it cannot say which branches hold finished work. Re-copy the plugin's hooks/ into this project and run again rather than treating this turn as a pass."
done

# The deadline came with four more (#304), checked the same way and for the same reason: a missing
# gate_hook_files reads as no hook file and the bound as the ceiling, and a missing gate_bounded or
# gate_replay is `command not found` with nothing on stdout, which a harness reads as a pass.
# quality-gate.sh carries the same check with its budget reader added. Case 314.
for _gate_fn in gate_hook_files gate_hook_timeout gate_bounded gate_replay; do
  command -v "$_gate_fn" >/dev/null 2>&1 || gate_block "Review gate: gate-lib.sh predates $_gate_fn, which this gate holds itself to a deadline through, so it cannot finish ahead of the harness's timeout. Re-copy the plugin's hooks/ into this project and run again rather than treating this turn as a pass."
done

if [ "${1-}" != --bounded ]; then
  # --- the parent: the budget, the watchdog, the verdict (#304) --------------------------
  #
  # quality-gate.sh's parent, one gate along, and its comments carry the reasoning. The parent
  # checks nothing. It works out the budget, runs this same script as its child through
  # gate_bounded, and judges what the child left in the run dir: a pass or a block the child
  # printed and gate_replay recognised, or a block this parent builds. Every other ending — a
  # cut-off, a signal, a status or stdout that means neither — is the second.

  # A signal to the parent is recorded and returns (AC5). POSIX runs the trap only once the
  # foreground child has returned, so it cannot cut the child's tree short.
  run=""; rg_sig=""
  rg_caught() {  # <signal>
    rg_sig="${rg_sig:+$rg_sig, }SIG$1"
    [ -z "$run" ] || { printf '%s\n' "$1" >> "$run/signalled"; } 2>/dev/null
  }
  for _rg_s in HUP INT QUIT TERM USR1 USR2 ALRM; do
    # shellcheck disable=SC2064  # the signal's name is fixed when the trap is set, on purpose
    trap "rg_caught $_rg_s" "$_rg_s"
  done

  # The files the child and the watchdog leave, removed by name, and then the directory.
  trap '[ -z "$run" ] || { rm -f "$run/ppid" "$run/pid" "$run/verdict" "$run/err" "$run/end" "$run/armed" "$run/fired" "$run/nowalk" "$run/done" "$run/signalled" "$run/progress" "$run/refs"; rmdir "$run"; } 2>/dev/null' EXIT

  # Every block the parent builds ignores the seven signals first, so exactly one verdict reaches
  # stdout. This gate keeps no pass record, so there is none to remove.
  rg_block() {  # <message>
    trap '' HUP INT QUIT TERM USR1 USR2 ALRM
    gate_block "$1"
  }

  # Listed before anything could move the working directory, because CLAUDE_PROJECT_DIR and the
  # working directory are the launch's (gate_hook_files). The parent never cds; the child does.
  rg_files=$(gate_hook_files "$DIR")

  # Under TMPDIR, or under the git directory when TMPDIR cannot hold one, and always absolute:
  # quality-gate.sh's qg_mkrun says why.
  rg_mkrun() {  # <directory> — a fresh run dir under it, as an absolute path, in $run
    _mr=$(mktemp -d "$1/gate-sdd-run.XXXXXX" 2>/dev/null) || return 1
    run=$(CDPATH= cd -- "$_mr" 2>/dev/null && pwd -P) && return 0
    rmdir -- "$_mr" 2>/dev/null; run=""; return 1
  }
  rg_gitdir=$(git rev-parse --git-path gate-sdd 2>/dev/null) || rg_gitdir=""
  if ! rg_mkrun "${TMPDIR:-/tmp}" && ! { [ -n "$rg_gitdir" ] && mkdir -p "$rg_gitdir" 2>/dev/null && rg_mkrun "$rg_gitdir"; }; then
    rg_block "Review gate: this gate could not make the directory its check runs in, under TMPDIR (${TMPDIR:-/tmp}) or under the git directory (${rg_gitdir:-none, outside a git repository}), so the check had no deadline it could be held to and was not run. A check the harness kills at its timeout ends the turn as a pass, so this blocks instead. Point TMPDIR at a writable directory, or unset it."
  fi

  # The budget is fixed: the hook's ceiling less the margin, which no environment variable or
  # steering line moves. Only a hook file that runs this gate can lower it, by the shortest
  # "timeout" it gives the gate, less the same margin (AC9); a file that cannot be read or parsed,
  # or an entry that names this gate with no "timeout", blocks at once. Split on newlines alone, so
  # a path holding a space stays one argument.
  rg_budget=$_gate_rg_budget
  rg_src="its own ceiling of $_gate_rg_ceiling s, less the $_gate_margin s it keeps back to write its verdict"
  _rg_ifs=$IFS; IFS='
'
  set -f
  # shellcheck disable=SC2086  # one hook file per line
  set -- $rg_files
  set +f
  IFS=$_rg_ifs
  rg_ht=$(gate_hook_timeout review-gate.sh "$_gate_rg_ceiling" "$@") \
    || rg_block "Review gate: $rg_ht, so this gate cannot tell how long it has before the harness's timeout, and it checked nothing. A check the harness kills at its timeout ends the turn as a pass, so this blocks instead."
  rg_t=${rg_ht%% *}; rg_tsrc=${rg_ht#* }
  case "$rg_t" in
    ''|*[!0-9]*) rg_block "Review gate: the hook-timeout reader answered '$rg_ht', which is no number of seconds, so this gate cannot tell how long it has. Re-copy the plugin's hooks/ into this project and run again rather than treating this turn as a pass." ;;
  esac
  rg_bound=$((rg_t - _gate_margin))
  [ "$rg_bound" -gt 0 ] || rg_block "Review gate: $rg_tsrc gives this gate a \"timeout\" of $rg_t s, which leaves nothing once it keeps $_gate_margin s back to write its verdict, so it checked nothing. Raise that \"timeout\"."
  # A file that binds the budget at the gate's own is named as its source, as quality-gate.sh
  # names one that ties its line: a "timeout" equal to the ceiling is the shipped state. The
  # ceiling the reader answers when no file names this gate is no file, and is never named as one.
  if [ "$rg_tsrc" != ceiling ] && [ "$rg_bound" -le "$rg_budget" ]; then
    rg_budget=$rg_bound
    rg_src="the \"timeout\" of $rg_t s that $rg_tsrc gives this gate, less the $_gate_margin s it keeps back to write its verdict"
  fi

  gate_bounded "$rg_budget" "$run" sh "$DIR/review-gate.sh" --bounded "$run"; rg_rc=$?

  # The child's progress: `phase current <branch>` before it checks the branch this turn is on,
  # `phase scan` before the other branches, and `checked <slug>` and `found <slug> — <sentence>` as
  # the scan goes; `refs` holds every branch it listed. Each of these prints nothing when the file
  # is not there.
  rg_phase() { awk '$1 == "phase" { p = $2 } END { print p }' "$run/progress" 2>/dev/null; }
  rg_current() { awk '$1 == "phase" && $2 == "current" { b = $3 } END { print b }' "$run/progress" 2>/dev/null; }
  # The listed branches the child had not checked when it stopped, in the order it lists them,
  # never the branch this turn is on: the refs, minus every `checked`, minus the current branch.
  rg_unchecked() {
    { cat "$run/progress" 2>/dev/null; echo '--- refs'; cat "$run/refs" 2>/dev/null; } | awk '
      $0 == "--- refs" { r = 1; next }
      !r && $1 == "checked" { c[$2] = 1; next }
      !r && $1 == "phase" && $2 == "current" { b = $3; next }
      r && $0 != "" { s = $0; sub(/^refs\/heads\//, "", s); if (!(s in c) && s != b) print s }'
  }

  # The timeout block (AC6), built once the watchdog has finished its kill: where the check was —
  # the current branch, or the scan and the branch it had reached — the unreviewed work it had
  # already found, and each branch it did not check. Then, where the watchdog could not walk the
  # child's tree, that only the child was killed (AC4); and a remedy that follows from what set the
  # budget and where the time went.
  rg_timeout_block() {
    _tb_phase=$(rg_phase)
    _tb_left=$(rg_unchecked)
    printf "Review gate: its check did not finish within this gate's budget of %s s, set by %s, so this turn is blocked rather than passed. A gate the harness kills at its timeout ends the turn as a pass, so this gate keeps a deadline of its own and blocks at it." "$rg_budget" "$rg_src"
    if [ "$_tb_phase" = scan ]; then
      if [ -n "$_tb_left" ]; then
        printf ' It had checked the branch this turn is on and was scanning the others: it was checking %s at the deadline.' "$(printf '%s\n' "$_tb_left" | head -1)"
      else
        printf ' It had checked every branch, and was cut off before it reached a verdict.'
      fi
    else
      _tb_cur=$(rg_current)
      printf ' It was still checking the current branch%s.' "${_tb_cur:+, $_tb_cur}"
    fi
    _tb_found=$(sed -n 's/^found /  /p' "$run/progress" 2>/dev/null)
    [ -z "$_tb_found" ] || printf '\n\nUnreviewed work it had already found, on branches other than the one this turn is on:\n%s' "$_tb_found"
    if [ ! -e "$run/refs" ]; then
      printf '\n\nIt had not yet listed the other branches, so it checked none of them.'
    elif [ -n "$_tb_left" ]; then
      printf '\n\nBranches it did not check:\n%s' "$(printf '%s\n' "$_tb_left" | sed 's/^/  /')"
    fi
    printf '%s' "$rg_nw"
    printf '\n\n'
    if [ "$rg_budget" -ge "$_gate_rg_budget" ]; then
      printf "%s s is the most this gate can hold: the hook's ceiling of %s s, less the %s s it keeps back to write this block." "$_gate_rg_budget" "$_gate_rg_ceiling" "$_gate_margin"
      [ "$_tb_phase" != scan ] || printf ' Fewer live branches make the scan shorter: merge, review or delete the ones that are done.'
    else
      printf "To give it more time, raise that \"timeout\" in %s to the %s s the plugin ships, or re-run init, which renders it. The budget is then %s s." "$rg_tsrc" "$_gate_rg_ceiling" "$_gate_rg_budget"
    fi
    printf ' Running git commit-graph write --reachable speeds up the history walk that takes most of this check'"'"'s time.'
  }

  # Judged with the seven signals ignored: a signal first, which no replay outranks; then the
  # child's own verdict, if it marked one complete; then the deadline; and anything else is a
  # check that ended without a verdict.
  trap '' HUP INT QUIT TERM USR1 USR2 ALRM
  rg_nw=""; [ ! -e "$run/nowalk" ] || rg_nw="

This host's process listing did not show the check's process tree, so only the check itself was killed, and a command it started may still be running."
  if [ -n "$rg_sig" ]; then
    if [ "$(rg_phase)" = scan ]; then rg_w=' It was scanning the branches other than the one this turn is on.'
    else rg_c=$(rg_current); rg_w=" It was checking the current branch${rg_c:+, $rg_c}."; fi
    rg_block "Review gate: this gate received $rg_sig before it reached a verdict, so this turn is blocked rather than passed.$rg_w A command that runs 'kill 0', or ends with the common trap 'kill 0' EXIT, sends its signal to the whole process group, this gate included. If the harness sent it at its timeout this block is discarded, which costs nothing; if it repeats, look for a git wrapper on PATH, or anything else this gate runs, that signals its process group.$rg_nw"
  fi
  gate_replay "$run" "$rg_rc"
  [ ! -e "$run/fired" ] || rg_block "$(rg_timeout_block)"
  rg_e=""; [ ! -s "$run/err" ] || rg_e="

Its last output:
$(tail -20 "$run/err")"
  rg_block "Review gate: its check ended without a verdict (status $rg_rc), so this turn is blocked rather than passed: an ending with no pass and no block reads to the harness as a pass.$rg_e"
fi

# --- the child: the body, under the parent's deadline -------------------------------------
#
# Run only as `review-gate.sh --bounded <run dir>`, by the parent above, and checked as
# quality-gate.sh's child checks itself: a hook entry that wrote --bounded by hand gets a block,
# never a body with no deadline. Only then is _gate_child_run set, which has gate_pass and
# gate_block mark the verdict complete.
shift
if [ ! -d "${1-}" ] || [ "$(cat -- "$1/pid" 2>/dev/null)" != "$$" ]; then
  gate_block "Review gate: this gate was started with --bounded and without a run directory of its own, so it has no deadline it can be held to, and it checked nothing. --bounded is for the gate's own use; a hook runs the gate with no arguments."
fi
run=$1; shift
_gate_child_run=$run
# One progress line for the parent's timeout block. printf, never `:`, whose failed redirection
# would exit this shell (gate_bounded); a line that cannot be written only leaves the block vaguer.
rg_mark() { { printf '%s\n' "$1" >> "$run/progress"; } 2>/dev/null; }

if repo_root=$(git rev-parse --show-toplevel 2>/dev/null); then
  cd "$repo_root"
fi

# Which branch HEAD is on, asked of the symbolic ref rather than of a commit, because an unborn
# branch — `git checkout --orphan`, or any fresh `git init` — has a name and no commit yet. This
# line used to be `git rev-parse --abbrev-ref HEAD … || gate_pass`, from the first commit, when the
# gate asked only about the branch you stood on and no commit meant no spec. #26 made it ask about
# the repository and turned every exit inside check_current_branch into a return, so that the scan
# always runs; this line sits in front of both and kept its pass, so an unborn branch turned the one
# enforced rule off until its first commit. #228. Nothing in front of the scan may pass.
#
# gate_head_branch asks `symbolic-ref -q HEAD`, which answers by exit status, three ways, where
# `rev-parse` gave two:
#
#   0    a branch, born or unborn: its own name, the full ref with `refs/heads/` stripped. Never
#        git's short form, which is `heads/<name>` whenever a tag or a remote's HEAD shares the
#        name, and which hid that branch from both checks below until #233 (cases 176–178)
#   1    a detached HEAD: the literal `HEAD`, which both checks below already handle (case 77)
#   128  a ref store git cannot read — damage, and a gate that cannot name the branch it stands on
#        cannot say what it checked (case 174)
branch=$(gate_head_branch); rc=$?
case "$rc" in
  0) : ;;
  1) branch=HEAD ;;
  *) gate_block "Review gate: git could not say which branch HEAD is on (git symbolic-ref exited $rc), so this gate cannot tell which spec is yours or which branches hold finished work. That is a ref store git cannot read: run git status to see it, and repair the repository rather than treating this turn as a pass." ;;
esac

reviewer=$(gate_steering_value .steering/tech.md Reviewer)
[ -n "$reviewer" ] || reviewer="the reviewer named in .steering/tech.md"

# Already-merged work has nothing left to review. What that buys is narrower than this comment
# used to claim, and the difference matters to anyone changing the skip: it said every
# historical feature branch would trip the gate on install, and that case cannot occur. A
# branch with no spec of its own is already silent whatever the merge style, and by two
# different routes: the current-branch path returns before reaching any of this, when the spec
# is in neither the working tree nor the branch's own tree, while the scan consults ancestry
# first and then gets an empty state back from gate_spec_review_state. Cases 83 and 148 pin the
# first — 148 is the one that reads both trees, since #177 — and case 144 the second. Cases 1-7 were cited
# for the second and do not reach it — their only other ref is main, which IS an ancestor of
# itself, so the scan skips it before asking. The branch that needs this skip is one that
# shipped WITH a spec and was not deleted — which, in a squash-merging repository, is every
# branch anyone has merged. #182 measured that and corrected the sentence.
#
# Both skip sites below ask two questions of this base, not one: was the COMMIT joined into its
# history, and did the WORK reach it. The second exists because a squash merge answers no to
# the first forever — #182, and gate_work_reached_base carries the reasoning. The candidates,
# and why each is a full refname, are gate_default_bases'. The skip measures against the first;
# the specs a branch adds are measured against all of them (gate_branch_specs says why).
base=$(gate_default_base) || base=""
bases=$(gate_default_bases) || bases=""

# Has every spec in <specs> reached the base, by the work and not the commit? Every, not any: a
# branch carrying one shipped spec and one unshipped one is not shipped, and a skip that fires
# less is the safe way to be wrong (#182, #316's clarifications). Each spec is asked by its slug,
# which is what names it in the base's tree.
every_spec_reached_base() {  # <tip sha> <specs, one per line>
  while IFS= read -r _ed; do
    [ -n "$_ed" ] || continue
    gate_work_reached_base "$(gate_spec_slug "$_ed")" "$1" "$base" || return 1
  done <<EOF
$2
EOF
  return 0
}

# One message for the current branch's block. check_current_branch ends in a single gate_block
# holding every one, so a branch carrying two specs is told about both (#316, the spec's Q2).
add_block() {
  if [ -z "$blocks" ]; then blocks=$1; else blocks="$blocks

$1"; fi
}

# The branch you are standing on, with the messages written in the second person because you
# are the person who can act on them. Every exit from here is a `return`, never a pass: the
# repository-wide pass below must run whatever this one concludes, or each of its early
# returns is another way to be standing somewhere the gate does not look.
check_current_branch() {
  blocks=''
  # Empty on an unborn branch, which has no commit. `git rev-parse HEAD` there prints its argument
  # before failing, so the `|| echo ''` this line used to carry appended to the literal `HEAD`
  # rather than replacing it, and that word would have reached every reader below as a tip. #228.
  head=$(git rev-parse --verify -q HEAD 2>/dev/null) || head=''

  # Which specs are yours. This used to be one path, `.specs/$branch/spec.md`, and a branch not
  # named for its spec — `feature/12-x`, a typo, a spec archived on its own branch — asked for a
  # path that did not exist and passed (#316). gate_branch_specs reads the name match and the
  # specs this branch adds against the base.
  #
  # The adds are asked only where there is a branch with a commit of its own to ask about. Under a
  # detached HEAD `branch` is the literal `HEAD`, and case 77's scan goes on reporting the real
  # branches; an unborn branch has no commit to diff. In both the name match alone is today's
  # reading, unchanged. A HEAD already in a base — the base branch itself, or a branch with no
  # commit beyond it — derives nothing either, which the library decides from the merge base.
  ancestor=''
  if [ -n "$base" ] && [ -n "$head" ] && git merge-base --is-ancestor HEAD "$base" 2>/dev/null; then
    ancestor=1
  fi
  sbases=$bases
  { [ "$branch" != HEAD ] && [ -n "$head" ]; } || sbases=''
  specs=$(gate_branch_specs "$sbases" '' "$branch"); listed=$?
  [ "$listed" -eq 0 ] || add_block "Review gate: git could not list the specs this branch adds against the base it is measured from, so the gate cannot tell whether any of them hold finished work nobody reviewed. A damaged object store, or a partial clone that cannot reach its remote, produces that. Check the repository with git fsck, or reconnect and run git fetch, and re-run rather than treating this as a pass."

  # No issue, no spec. The slug is <issue-number>-<kebab-title>, so a spec directory
  # without a numeric prefix is work that never had an issue — unplanned work that
  # entered through the side door and bypassed whatever decided the sprint. This is
  # checkable without touching the network, so it is checked.
  #
  # It judges the spec's slug, not the branch's name (#316 AC7): a branch with an issue number
  # carrying a directory without one is the unplanned work, and `feature/12-x` carrying
  # `.specs/12-x/` is not. The slug is the directory under `.specs/` with `_archive/` stripped,
  # never its last component, which for the slashed slug `12-feat/sub` (case 179) is `sub`.
  #
  # Current-branch only, on purpose: it is a rule about the spec you are authoring now, and
  # asking it of every directory in .specs/ would fire forever on anything predating it.
  #
  # Asked of working-tree specs ONLY, which is the same sentence applied rather than an
  # exception carved out of it: a spec that is not in your working tree is not one you are
  # authoring now. It also matters where this sits — before the merged-work skip — so widening
  # it to the fallback would block on branches that shipped long ago, which is the false block
  # that skip exists to prevent.
  while IFS= read -r dir; do
    [ -n "$dir" ] && [ -f "$dir/spec.md" ] || continue
    sslug=$(gate_spec_slug "$dir")
    case "$sslug" in
      [0-9]*) : ;;
      *) add_block "No issue, no spec: the branch '$branch' carries a spec at $dir/spec.md whose slug, '$sslug', does not start with an issue number. The slug is <issue>-<kebab-title>, and the issue is what recorded that this work was chosen. Create the issue and rename the branch and spec directory to match, or say explicitly that this is acknowledged unplanned work." ;;
    esac
  done <<EOF
$specs
EOF

  # Two arms, because there are two ways work reaches the base and only one of them leaves a
  # parent link. Ancestry is kept and asked first: it is exact when it fires, costs one call,
  # and is the whole of the merge-commit and fast-forward case on the path those projects
  # already take. The second arm is #182 — see gate_work_reached_base — asked of every spec the
  # branch carries, by its slug, since #316.
  if [ -n "$base" ] && [ -n "$specs" ] && { [ -n "$ancestor" ] || every_spec_reached_base "$head" "$specs"; }; then
    specs=''
  fi

  while IFS= read -r dir; do
    [ -n "$dir" ] || continue
    check_spec_here "$dir"
  done <<EOF
$specs
EOF
  [ -z "$blocks" ] || gate_block "$blocks"
}

# One spec the current branch carries, in <dir>. Every finding is an add_block and a return.
check_spec_here() {  # <spec dir>
  spec="$1/spec.md"
  receipt="$1/.review-receipt"

  # Which tree answers for this spec, and why there are two of them.
  #
  # The working tree is read first, deliberately: a spec edited and not yet committed is the
  # state its author is in for most of the spec's life, and #26 chose to count it.
  #
  # What that USED to mean is that an absent file ended the question — and the scan below skips
  # this ref BY NAME, on the understanding that this path has answered for it. So the one branch
  # read from the working tree was the one branch nobody read from its own tree, and a spec
  # committed on the branch but missing from the tree in front of you was silent on both paths
  # while every other branch in the same repository was read from its tree and reported. Nobody
  # has to delete anything for that: a sparse checkout excluding `.specs/`, or a partial
  # worktree, is the same state. #177 — and it is #26's own sentence, the author choosing what
  # the gate looks at, narrowed to one branch and reached through the tree rather than HEAD.
  #
  # Whether there is a spec at all is gate_branch_specs' question, asked once: it lists a spec
  # that is in neither tree only when it could not read HEAD's (#191, cases 197 and 198), and an
  # unborn branch only from its working tree (cases 171 and 172). A spec is its branch's FIRST
  # commit, so the branch's own tree is where it lives whenever the working tree does not have it.
  tree=''                             # empty — gate_spec_review_state reads the working tree
  note=''
  cause=''
  if [ ! -f "$spec" ]; then
    [ -n "$head" ] || return 0
    tree=HEAD
    # Appended to every block below. The remedy names a file the author cannot see, so the
    # message has to say why it is not there and which tree the answer came from; without it the
    # block reads as the gate inventing a file, and a gate that looks broken is a gate switched
    # off. Empty on every path that existed before this change, and appended with no separator,
    # so those messages are unchanged character for character.
    note=" ($spec is not in your working tree, so the gate read it from this branch's own tree at HEAD. A sparse checkout, a partial worktree, or a deletion nobody committed produces that. The receipt is read from there too, so one written into the working tree alone does not clear this until it is committed.)"
    # The two unreadable states are the exception: on this path they get a sentence of their
    # own, ending in this. Read from a tree, "cannot be read" is never a file mode. It is an
    # object git could not get, and the working-tree sentences tell you to fix a permission,
    # which is advice about a file that is not the subject. This used to be a correction
    # appended after that advice, written when only damage could reach it and no fixture did.
    # A blobless clone with no network reaches it now (#191), and someone in that state has
    # nothing to repair, so the first remedy named is the one for them.
    cause=" Git cannot get an object that tree needs: a partial clone that cannot reach its remote, or a damaged object store. Reconnect and run git fetch, or check the repository with git fsck, and re-run rather than treating this as a pass."
  fi

  # Two ways there is nothing to review, indistinguishable in a count of unticked boxes alone
  # — which is why that count used to block a spec still being drafted while telling its
  # author that every task was ticked:
  #
  #   no checkboxes at all   the Tasks section is a placeholder; nothing has been written yet
  #   some still unticked    implementation is in progress
  #
  # Neither is the moment to demand a review. Both are an empty state below.
  state=$(gate_spec_review_state "$1" "$head" "$tree")

  # An unborn branch has no commit, so a receipt in its working tree cannot describe code on it:
  # whatever reviewed_sha names is another branch's. Only the empty state needs saying so — every
  # other receipt state already blocks — and it is empty here because the staleness diff compares
  # the receipt against a HEAD that does not exist and reads git's refusal as "nothing changed",
  # which is #232's line. Asked here rather than as a library state because only this reader can
  # stand on an unborn branch: the scan reads refs, which have tips, and CI reads a pull request's
  # head. Case 175.
  if [ -z "$head" ] && [ -z "$state" ] && [ -f "$receipt" ] \
       && [ "$(gate_total_tasks "$spec")" -gt 0 ] 2>/dev/null \
       && [ "$(gate_open_tasks "$spec")" -eq 0 ] 2>/dev/null; then
    add_block "Review gate: every task in $spec is ticked and $receipt records a review, but this branch has no commits yet, so that review cannot describe any code on it. Commit the work, run $reviewer on the branch diff, and rewrite $receipt."
    return 0
  fi

  case "$state" in
    '')
      return 0 ;;
    unreadable)
      # A spec that exists but cannot be read is NOT the same as a spec with nothing in it,
      # and the difference is invisible downstream: both task counters come back 0 for a file
      # they cannot open, and a zero total is read as "nothing authored, stay silent". Fail
      # closed — an unreadable spec is a broken working tree, not an empty one.
      if [ -n "$tree" ]; then
        add_block "Review gate: $spec cannot be read from this branch's own tree at HEAD, so the gate cannot tell whether this branch has been reviewed.$cause$note"
      else
        add_block "Review gate: $spec exists but cannot be read, so the gate cannot tell whether this branch has been reviewed. Fix the file's permissions and re-run rather than treating this as a pass."
      fi ;;
    no-receipt)
      add_block "Review gate: every task in $spec is ticked, but no reviewer receipt exists. Run $reviewer on the branch diff, then write its Receipt block to $receipt. If $reviewer is already running, wait for it and write the receipt from its result — do not start a second one.$note" ;;
    receipt-unreadable)
      if [ -n "$tree" ]; then
        add_block "Review gate: $receipt cannot be read from this branch's own tree at HEAD, so the gate cannot tell whether this branch has been reviewed.$cause$note"
      else
        add_block "Review gate: $receipt exists but cannot be read, so the gate cannot tell whether this branch has been reviewed. Fix the file's permissions and re-run rather than treating this as a pass."
      fi ;;
    verdict=*)
      add_block "Review gate: the recorded review verdict is '${state#verdict=}', not CLEAN. Address every BLOCKER and HIGH finding, re-run $reviewer, and update $receipt.$note" ;;
    unresolved-sha=*)
      add_block "Review gate: $receipt records reviewed_sha '${state#unresolved-sha=}', which cannot be resolved in this repository, so the gate cannot tell whether the review covers the code that is here now. Re-run $reviewer and rewrite $receipt rather than treating an uncheckable receipt as a pass.$note" ;;
    stale=*)
      rest=${state#stale=}
      add_block "Review gate: source changed since the recorded review (${rest%% *}): ${rest#* }. Re-run $reviewer and update $receipt before opening the PR.$note" ;;
  esac
}

# Every other branch. This is the half #26 was missing, and the reason it reads branches
# rather than globbing `.specs/` is that the spec is its branch's FIRST commit: from anywhere
# else, the directory does not exist in the working tree at all. A scan of `.specs/` would
# therefore find nothing and report it as cleanliness — the same silence, one layer deeper.
scan_other_branches() {
  found=''
  # Full refnames, and the slug stripped by hand; gate_head_branch says why. `ref` is what git
  # reads, exactly, since for-each-ref has listed it (rg_refs, below); `slug` is what a person
  # reads, and the name match gate_branch_specs keeps (#316). Each branch is marked `checked` in the progress file
  # once it has been answered for, whichever way, which is how a cut-off names the ones it did not
  # reach (#304).
  for ref in $rg_refs; do
    slug=${ref#refs/heads/}
    scan_branch
    rg_mark "checked $slug"
  done

  [ -n "$found" ] || return 0

  # Held in a variable rather than expanded inline. `${base:-TEXT}` substitutes the VALUE of
  # base whenever base is set and non-null — and line 41 always sets it — so the inline form
  # appended the base sha to every block instead of a note to none of them.
  nobase=''
  [ -n "$base" ] || nobase='

(This repository has no resolvable default branch — origin/HEAD, origin/main, origin/master, main and master are all missing — so the gate cannot tell which of these branches have already shipped, and is naming them all.)'

  # "a branch you are not standing on" would be false under a detached HEAD, which is a path
  # this deliberately blocks (case 77): the naming line's arm 1 sets the literal `HEAD`, which no
  # branch can be named, so the branch you are detached at is reported like any other.
  gate_block "Review gate: this repository holds finished work that nobody has reviewed, on a branch other than the one this turn is on:
$found

The gate asks what this repository contains, not which branch HEAD points at, so moving HEAD does not clear this and neither does a detached checkout. For each branch above: run $reviewer against it and write the receipt, merge it, or delete the branch if the work is abandoned.$nobase"
}

# One branch of the scan, `ref` and `slug`; every return is that branch answered for. No branch
# can be named `HEAD` (git refuses), so under a detached HEAD the skip below never fires.
#
# `slug` is the branch's name, and since #316 it is only the name match: the specs are the ones
# gate_branch_specs lists, judged one at a time. A spec at `.specs/<branch>/` is reported as it
# always was; any other carries its path, because the branch's name no longer says which spec it is.
scan_branch() {
  [ "$slug" = "$branch" ] && return 0
  tip=$(git rev-parse --verify -q "$ref^{commit}" 2>/dev/null) || return 0
  # Ancestry first: exact when it fires, one call, and ahead of the listing's diff.
  if [ -n "$base" ] && git merge-base --is-ancestor "$tip" "$base" 2>/dev/null; then
    return 0                          # shipped — case 8's reasoning, one branch over
  fi
  specs=$(gate_branch_specs "$bases" "$tip" "$slug"); listed=$?
  [ "$listed" -eq 0 ] || scan_found "git could not list the specs it adds, so the gate cannot tell whether it holds finished work nobody reviewed: a damaged object store, or a partial clone that cannot reach its remote"
  [ -n "$specs" ] || return 0
  # Shipped by the work rather than the commit, asked of every spec the branch carries (#182).
  if [ -n "$base" ] && every_spec_reached_base "$tip" "$specs"; then
    return 0
  fi
  while IFS= read -r dir; do
    [ -n "$dir" ] || continue
    state=$(gate_spec_review_state "$dir" "$tip" "$ref")
    [ -n "$state" ] || continue
    sentence=$(gate_review_state_sentence "$state")
    if [ "${dir#.specs/}" = "$slug" ]; then
      scan_found "$sentence"
    else
      scan_found "$dir/spec.md: $sentence"
    fi
  done <<EOF
$specs
EOF
}

# One line of the scan's block, for the branch in `slug`. It joins `found`, and is marked `found`
# in the progress file with its sentence, so a cut-off still names the work the scan had already
# found (#304).
scan_found() {  # <what this branch holds>
  found="$found
  $slug — $1"
  rg_mark "found $slug — $1"
}

# The branches the scan reads, listed once and before the current branch is checked, so that a
# cut-off there can still name every branch it did not reach. Unquoted where the scan reads them:
# git refuses a branch name holding a space or a glob character. Then a phase line ahead of each
# half, which is what the parent's timeout block says the check was doing (#304).
rg_refs=$(git for-each-ref --format='%(refname)' refs/heads/ 2>/dev/null)
{ printf '%s\n' "$rg_refs" > "$run/refs"; } 2>/dev/null
rg_mark "phase current $branch"
check_current_branch
rg_mark "phase scan"
scan_other_branches
gate_pass
