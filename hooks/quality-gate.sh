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

# Anchor to the repository root so relative paths (.steering/, .specs/) resolve
# correctly regardless of the working directory the hook was invoked from.
if repo_root=$(git rev-parse --show-toplevel 2>/dev/null); then
  cd "$repo_root"
fi

# The validator list is read through gate_steering_read. If this hooks/ directory is a mix of
# versions the function is undefined — and `set -u` does not catch an undefined FUNCTION, so
# the read yields empty, the "no validators configured" branch below fires, and the gate exits
# 0 having run nothing. That is a fail-open created by the migration to a shared reader, so the
# migration has to carry the check. The asset guards itself this way; the gate is the half that
# matters more, because its failure is silent.
command -v gate_steering_read >/dev/null 2>&1 || gate_block "Quality gate: gate-lib.sh predates the shared steering reader, so this gate cannot read its validator list. Re-copy the plugin's hooks/ into this project and run again rather than treating this as a pass."

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
# passed. Committing content that already passed does not change it; anything else does.
#
# `Source globs` is the same line the review gate reads to decide what counts as reviewable
# source, so a project states "what is code here" once and both gates obey it. When the line
# is absent, outside a work tree, with no record yet, or when any step below fails, the gate
# runs: for a guarantee, failing toward MORE checking is the right direction.

# The fingerprint of the source the pathspecs match, in $fp; on any failure $fp is empty and
# $qg_step names what failed. Built in a COPY of the index so the real one is never touched,
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
  qg_tmp=$(mktemp "${TMPDIR:-/tmp}/gate-sdd-qg.XXXXXX") || { qg_step="mktemp"; return 1; }
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
qg_tmp=""
trap '[ -z "$qg_tmp" ] || rm -f "$qg_tmp" "$qg_tmp.idx" "$qg_tmp.idx.lock" "$qg_tmp.list" "$qg_tmp.fp"' EXIT
trap 'exit 129' HUP; trap 'exit 130' INT; trap 'exit 143' TERM

fp=""; qg_step=""; qg_record=""
globs=$(gate_steering_value .steering/tech.md 'Source globs')
if [ -n "$globs" ] && [ "$(git rev-parse --is-inside-work-tree 2>/dev/null)" = true ]; then
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
  # The record is per worktree — git keeps a name it does not know under the worktree's own git
  # directory — never tracked, and relative, which is safe because the gate is at the toplevel.
  if ! qg_record=$(git rev-parse --git-path gate-sdd/quality-pass); then
    qg_record=""; qg_step="git rev-parse --git-path"
  elif qg_fingerprint "$@"; then
    if [ -e "$qg_record" ] && ! [ -r "$qg_record" ]; then
      qg_step="reading $qg_record"
    elif [ -r "$qg_record" ] && [ "$(cat "$qg_record")" = "$fp" ]; then
      gate_pass
    fi
  fi
  # Q2 of #297's spec: a step that failed runs the validators and says so, whatever they find —
  # a project paying for a full run on every turn should be able to find out why.
  [ -z "$qg_step" ] || printf 'Quality gate: could not tell whether source changed since the validators last passed (%s failed), so they ran.\n' "$qg_step" >&2
  # The validators are about to run, so the last pass stops counting until they pass again. Kept
  # through a failure, the record matched source put back to a state that passed EARLIER, and the
  # gate skipped a tree still red from an input outside the globs (case 248). A run cut off by
  # the hook timeout leaves no pass behind either.
  if [ -n "$qg_record" ] && [ -e "$qg_record" ] && ! rm -f "$qg_record"; then
    printf 'Quality gate: could not remove the last pass record at %s; the validators run anyway.\n' "$qg_record" >&2
  fi
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

# Record the pass — the fingerprint taken BEFORE the first validator ran, so an edit made during
# the run is not recorded as passed — through a temp file and `mv` in the same directory, so a
# reader never sees half a value. A record that cannot be written costs the next turn a run,
# never a pass, and says so.
if [ -z "$failed" ] && [ -n "$fp" ] && [ -n "$qg_record" ]; then
  if ! { mkdir -p "${qg_record%/*}" && qg_new=$(mktemp "${qg_record%/*}/quality-pass.XXXXXX") \
         && printf '%s\n' "$fp" > "$qg_new" && mv -f "$qg_new" "$qg_record"; }; then
    [ -z "${qg_new-}" ] || rm -f "$qg_new"
    printf 'Quality gate: the validators passed, and the pass could not be recorded at %s, so the next turn end runs them again.\n' "$qg_record" >&2
  fi
fi

[ -z "$failed" ] && gate_pass

gate_block "Quality gate: a gating validator failed. These are the commands on the '- Validators:' line in .steering/tech.md, and they gate CI too — fix the failure rather than working around the gate.
$failed"
