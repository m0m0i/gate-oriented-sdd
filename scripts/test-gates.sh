#!/bin/sh
# test-gates.sh — deterministic tests for the review gate.
#
# The claim this repo makes is that its review gate is enforced rather than
# advisory. That claim is testable without a model and without cost, so it is
# tested here rather than asserted in a README.
#
# Builds throwaway git repositories, drives review-gate.sh through every path,
# and asserts on exit code and on BOTH blocking channels.
set -u

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
pass=0; fail=0

report() { # report <name> <ok|no> <detail>
  if [ "$2" = ok ]; then pass=$((pass+1)); printf '  ok   %s\n' "$1"
  else fail=$((fail+1)); printf '  FAIL %s — %s\n' "$1" "$3" >&2; fi
}

# A repo with the harness installed and one spec branch.
#
# Source lives one directory down, in src/, and the glob defaults to the quoted form the
# init skill documents. Both are deliberate. An earlier fixture put its only source file
# at the repository root and wrote the glob bare, which meant the staleness case passed
# because the shell expanded `*.txt` into exactly the changed file — the gate could have
# been doing nothing and the test would not have known.
#
# $1 = repo name, $2 = open tasks (0 or 1), $3 = the Source globs value (optional)
make_repo() {
  r="$TMP/$1"; mkdir -p "$r/hooks" "$r/.steering" "$r/.specs/9-feature" "$r/src"
  cp "$ROOT/hooks/gate-lib.sh" "$ROOT/hooks/review-gate.sh" "$r/hooks/"
  globs=${3:-}
  [ -n "$globs" ] || globs="'*.txt'"
  printf -- '- Reviewer: test-reviewer\n- Source globs: %s\n' "$globs" > "$r/.steering/tech.md"
  if [ "$2" = 0 ]; then box='- [x]'; else box='- [ ]'; fi
  cat > "$r/.specs/9-feature/spec.md" <<EOF
# Spec: feature
- Slug: 9-feature   Status: approved

## 1. Requirements
- [ ] **AC1:** an acceptance criterion, deliberately left unticked.

## 3. Tasks (TDD-ordered)
$box T1: do the thing
EOF
  ( cd "$r" && git init -q -b main && git config user.email t@t && git config user.name t \
    && echo one > src/main.txt && git add -A && git commit -qm init \
    && git checkout -q -b 9-feature && echo two >> src/main.txt && git commit -qam work ) >/dev/null 2>&1
  echo "$r"
}

run_gate() { ( cd "$1" && sh hooks/review-gate.sh 2>"$TMP/err" ; echo "exit=$?" ) }

# 1. Tasks still open -> silent (mid-implementation)
r=$(make_repo open 1); out=$(run_gate "$r")
case "$out" in *"exit=0"*) report "open tasks stay silent" ok ;;
                        *) report "open tasks stay silent" no "$out" ;; esac

# 2. All ticked, no receipt -> blocks, on BOTH channels
r=$(make_repo noreceipt 0); out=$(run_gate "$r"); err=$(cat "$TMP/err")
case "$out" in *"exit=2"*) c1=ok ;; *) c1=no ;; esac
case "$out" in *'"decision":"continue"'*) c2=ok ;; *) c2=no ;; esac
case "$err" in *receipt*) c3=ok ;; *) c3=no ;; esac
[ "$c1$c2$c3" = "okokok" ] && report "missing receipt blocks on both channels" ok \
  || report "missing receipt blocks on both channels" no "exit=$c1 json=$c2 stderr=$c3"

# 3. Unticked ACs must NOT be read as open tasks (case 2 proves it: its ACs are
#    unticked and it still reached the receipt check rather than staying silent).
case "$out" in *"exit=2"*) report "unticked acceptance criteria are ignored" ok ;;
                        *) report "unticked acceptance criteria are ignored" no "gate went silent" ;; esac

# 4. BLOCKED receipt -> blocks
r=$(make_repo blocked 0)
printf 'reviewed_sha=%s\nverdict=BLOCKED\n' "$(cd "$r" && git rev-parse HEAD)" > "$r/.specs/9-feature/.review-receipt"
out=$(run_gate "$r")
case "$out" in *"exit=2"*) report "BLOCKED verdict blocks" ok ;;
                        *) report "BLOCKED verdict blocks" no "$out" ;; esac

# 5. CLEAN receipt at HEAD -> silent
r=$(make_repo clean 0)
printf 'reviewed_sha=%s\nverdict=CLEAN\n' "$(cd "$r" && git rev-parse HEAD)" > "$r/.specs/9-feature/.review-receipt"
out=$(run_gate "$r")
case "$out" in *"exit=0"*) report "CLEAN receipt at HEAD passes" ok ;;
                        *) report "CLEAN receipt at HEAD passes" no "$out" ;; esac

# 6. Docs-only commit after review -> still silent (worklog and Status flips land
#    after the reviewer runs; re-triggering there would fire on a correct flow)
r=$(make_repo docsonly 0)
printf 'reviewed_sha=%s\nverdict=CLEAN\n' "$(cd "$r" && git rev-parse HEAD)" > "$r/.specs/9-feature/.review-receipt"
( cd "$r" && echo note > NOTES.md && git add -A && git commit -qm docs ) >/dev/null 2>&1
out=$(run_gate "$r")
case "$out" in *"exit=0"*) report "docs-only commit after review passes" ok ;;
                        *) report "docs-only commit after review passes" no "$out" ;; esac

# 7. Source commit after review -> blocks as stale
r=$(make_repo stale 0)
printf 'reviewed_sha=%s\nverdict=CLEAN\n' "$(cd "$r" && git rev-parse HEAD)" > "$r/.specs/9-feature/.review-receipt"
( cd "$r" && echo three >> src/main.txt && git commit -qam more ) >/dev/null 2>&1
out=$(run_gate "$r")
case "$out" in *"exit=2"*) report "source commit after review blocks as stale" ok ;;
                        *) report "source commit after review blocks as stale" no "$out" ;; esac

# 8. Merged branch -> silent (else every historical branch trips on install)
r=$(make_repo merged 0)
( cd "$r" && git checkout -q main && git merge -q 9-feature && git checkout -q 9-feature \
  && git update-ref refs/remotes/origin/main refs/heads/main ) >/dev/null 2>&1
out=$(run_gate "$r")
case "$out" in *"exit=0"*) report "merged branch stays silent" ok ;;
                        *) report "merged branch stays silent" no "$out" ;; esac

# 9. Not a spec branch -> silent
r=$(make_repo nospec 0); ( cd "$r" && git checkout -q -b unrelated ) >/dev/null 2>&1
out=$(run_gate "$r")
case "$out" in *"exit=0"*) report "non-spec branch stays silent" ok ;;
                        *) report "non-spec branch stays silent" no "$out" ;; esac

# 10. Spec on a branch with no issue number -> blocks ("no issue, no spec")
r=$(make_repo noissue 0)
( cd "$r" && git checkout -q -b add-retries && mv .specs/9-feature .specs/add-retries ) >/dev/null 2>&1
out=$(run_gate "$r"); err=$(cat "$TMP/err")
case "$out$err" in *"exit=2"*"No issue, no spec"*) report "spec without an issue number blocks" ok ;;
                 *) report "spec without an issue number blocks" no "$out" ;; esac

# 11-13. The same staleness check must hold however the glob line is spelled. Each of
#    these used to fail OPEN: a quoted value reached git with its quotes and matched
#    nothing, and a bare value was expanded by the shell against the repo root, which in
#    a src/ layout also matches nothing. A gate that silently stops checking is worse
#    than one that was never installed, so all three spellings are pinned.
for spelling in "'*.txt'" '*.txt' ':(glob)**/*.txt'; do
  name=$(printf '%s' "$spelling" | tr -d ' ')
  r=$(make_repo "globs$(echo "$name" | tr -cd 'a-z')" 0 "$spelling")
  printf 'reviewed_sha=%s\nverdict=CLEAN\n' "$(cd "$r" && git rev-parse HEAD)" > "$r/.specs/9-feature/.review-receipt"
  ( cd "$r" && echo four >> src/main.txt && git commit -qam more ) >/dev/null 2>&1
  out=$(run_gate "$r")
  case "$out" in *"exit=2"*) report "stale source blocks with globs written as $spelling" ok ;;
                          *) report "stale source blocks with globs written as $spelling" no "$out — gate failed open" ;; esac
done

# 14. And it must still stay silent when nothing reviewable moved, or the fix above has
#     simply turned the gate into one that always fires.
r=$(make_repo globsquiet 0)
printf 'reviewed_sha=%s\nverdict=CLEAN\n' "$(cd "$r" && git rev-parse HEAD)" > "$r/.specs/9-feature/.review-receipt"
( cd "$r" && echo note > NOTES.md && git add -A && git commit -qm docs ) >/dev/null 2>&1
out=$(run_gate "$r")
case "$out" in *"exit=0"*) report "quoted globs do not cause a false block" ok ;;
                        *) report "quoted globs do not cause a false block" no "$out" ;; esac

printf '\ntest-gates: %d passed, %d failed\n' "$pass" "$fail"
[ "$fail" -eq 0 ] || exit 1
