#!/bin/sh
# steering-digest.sh — restate the repo's facts when context has been lost.
#
# A digest, deliberately, and not a dump of .steering/. This harness's claim is
# that reference material stays out of a normal session's context until it is
# needed; re-injecting three steering files on every startup, resume, clear and
# compact would spend the most context exactly where the design saves it.
#
# Everything printed is a factual statement. Imperative out-of-band text reads as
# an injected instruction and gets surfaced to the user instead of used as
# context, so this describes the repo rather than telling anyone what to do.
set -u

DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
. "$DIR/gate-lib.sh"

# No blocking channel here, so a skewed hooks/ cannot be made loud — but it must not be
# silent either. Without this, a stale library omits Owns, Validators and Reviewer and prints
# "not found" to stderr, which is #34's exact symptom reintroduced by #34's fix. The branch
# line below reads through gate_head_branch, so a library predating that is the same skew. #233.
# And through gate_branch_specs, which #316 added, for the same reason.
command -v gate_steering_value >/dev/null 2>&1 && command -v gate_head_branch >/dev/null 2>&1 \
  && command -v gate_branch_specs >/dev/null 2>&1 || {
  echo "## Repo facts"
  echo "- (steering digest degraded: hooks/gate-lib.sh predates the shared reader — re-copy the plugin's hooks/)"
  exit 0
}


echo "## Repo facts"
[ -f .steering/product.md ] && echo "- Persistent context is in .steering/product.md, .steering/tech.md, .steering/structure.md."

owns=$(gate_steering_value .steering/product.md Owns)
[ -n "$owns" ] && echo "- This project owns $owns."

v=$(gate_steering_value .steering/tech.md Validators);  [ -n "$v" ] && echo "- Validators: $v"
r=$(gate_steering_value .steering/tech.md Reviewer);    [ -n "$r" ] && echo "- The reviewer for this repo is $r."

echo "- The flow is spec -> clarify -> implement -> reviewer -> worklog. One issue = one spec = one branch = one PR, and that PR is the last step."
echo "- Live specs are .specs/<slug>/spec.md; shipped ones are under .specs/_archive/."
echo "- Archiving a shipped spec into .specs/_archive/ is a sweep run on request, not a step in that flow."
echo "- A Stop hook enforces the quality gate and the freshness of the review receipt."

# The harness checks (#340). The quality gate runs them from its own tree, before the line, and a
# by-hand run needs a command for the tree this digest ran from. Inside the project, the path is the
# command: hooks/ in the harness repository, .agents/hooks/ on Antigravity. From the plugin, through
# plugin-gate.sh, the session's shell reaches it only through GATE_SDD_PLUGIN_ROOT, and the `:?`
# says what to do when that is unset rather than running nothing. Facts only, as every line here.
# Both physical, since git's toplevel is: a link on the way (macOS's /var) would read as outside.
dg_top=$(git rev-parse --show-toplevel 2>/dev/null) || dg_top=$(pwd -P)
dg_dir=$(CDPATH='' cd -- "$DIR" && pwd -P) || dg_dir=$DIR
case "$dg_dir/" in
  "$dg_top"/*) dg_cmd="sh ${dg_dir#"$dg_top"/}/harness-checks.sh" ;;
  *) dg_cmd='sh "${GATE_SDD_PLUGIN_ROOT:?is unset; start a new Claude Code session}/hooks/harness-checks.sh"' ;;
esac
echo "- Harness checks: the quality gate runs them first at turn end; by hand, beside the Validators line, \`$dg_cmd\` runs them."
# A tree that ships the reviewer contract (the plugin, or this repository) is one a project's copy
# can fall behind. Antigravity's copy set and its contract come from the same init run, so there is
# nothing newer to compare against there.
if [ -f "$DIR/../.claude-plugin/plugin.json" ] && [ -f .claude/agents/_shared/reviewer-contract.md ] \
  && [ -f "$DIR/../reviewers/_shared/reviewer-contract.md" ] \
  && ! cmp -s .claude/agents/_shared/reviewer-contract.md "$DIR/../reviewers/_shared/reviewer-contract.md"; then
  dg_ver=$(sed -n 's/.*"version": *"\([^"]*\)".*/\1/p' "$DIR/../.claude-plugin/plugin.json" | head -1)
  echo "- The project's .claude/agents/_shared/reviewer-contract.md differs from the one gate-sdd ${dg_ver:-this version} ships; init copies the shipped one over it when re-run."
fi
dg_named=""
for dg_n in check-steering-anchors.sh check-locks.py check-document-set.py check-document-cascade.py; do
  case "$v" in *"$dg_n"*) dg_named="${dg_named:+$dg_named, }$dg_n" ;; esac
done
[ -z "$dg_named" ] || echo "- The Validators line still names $dg_named, which the quality gate runs itself, so a copy there runs a second time and a stale one can only add a block; init's migration takes them off the line."

# By its own name, never git's short form, which lengthens to `heads/<name>` when a tag shares
# it — and then this line denied a spec that exists. Status 1 is a detached HEAD, printed as the
# literal `HEAD` as it always was; an unborn branch is named, where `rev-parse` used to print
# `HEAD` for it too. #233.
branch=$(gate_head_branch); [ $? -eq 1 ] && branch=HEAD
[ -n "$branch" ] || exit 0

# Which specs are the branch's: the ones the review gate judges, through gate_branch_specs, so this
# line cannot say "no spec" about a branch the gate blocks on. It used to read `.specs/<branch>/`
# alone, and told a session on `feature/12-x` that it had no spec while the gate blocked on
# `.specs/12-x/` (#316). The adds are asked under check_current_branch's rules in review-gate.sh,
# which says why: not under a detached HEAD or on an unborn branch, and the library derives nothing
# for a HEAD already in a base. Read from the working tree only, as this line always has been. A
# listing git could not make is said, rather than read as "no spec": this has no channel to block
# on, but a "none" it never established is a false fact at the start of a session.
head=$(git rev-parse --verify -q HEAD 2>/dev/null) || head=''
bases=$(gate_default_bases 2>/dev/null) || bases=''
{ [ "$branch" != HEAD ] && [ -n "$head" ]; } || bases=''
specs=$(gate_branch_specs "$bases" '' "$branch" 2>/dev/null); listed=$?
named=''
while IFS= read -r dir; do
  spec="$dir/spec.md"
  [ -n "$dir" ] && [ -f "$spec" ] || continue
  status=$(sed -n 's/.*Status: *\([A-Za-z]*\).*/\1/p' "$spec" | head -1)
  open=$(awk '/^#+ *3\./{f=1;next} /^#+ /{f=0} f' "$spec" | grep -c '^ *- \[ \]')
  echo "- The active branch $branch has spec $spec (Status: $status, $open task(s) still open)."
  named=1
done <<EOF
$specs
EOF
if [ "$listed" -ne 0 ]; then
  echo "- The specs the active branch $branch adds could not be listed: git could not read what it needed."
elif [ -z "$named" ]; then
  echo "- The active branch $branch has no spec directory under .specs/."
fi
