#!/bin/sh
# test-gates.sh — deterministic tests for the gates and guards.
#
# The claim this repo makes is that its review gate is enforced rather than
# advisory. That claim is testable without a model and without cost, so it is
# tested here rather than asserted in a README.
#
# Builds throwaway git repositories, drives review-gate.sh and quality-gate.sh
# through every path, and asserts on exit code and on BOTH blocking channels.
#
# It also covers assets/check-locks.py. That is a guard rather than a gate — it fails a
# build instead of ending a turn — but it shares the property the gates are tested for:
# it can exit 0 having verified nothing, which is indistinguishable from working. A
# second suite was considered and rejected; one file, one CI step, one place to look.
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

# 11. Tasks section authored but empty -> silent.
#
# This is the exact state `spec` step 3 prescribes: draft Requirements, stop, run clarify.
# Zero UNTICKED boxes used to read as "implementation finished", so a spec nobody had started
# blocked the turn — and said every task was ticked when the spec had none. See #8.
r=$(make_repo drafting 0)
cat > "$r/.specs/9-feature/spec.md" <<'SPEC'
# Spec: feature
- Slug: 9-feature   Status: draft

## 1. Requirements
- [ ] **AC1:** an acceptance criterion, deliberately left unticked.

## 3. Tasks (TDD-ordered)
<not written yet>
SPEC
( cd "$r" && git add -A && git commit -qm "spec: draft requirements only" ) >/dev/null 2>&1
out=$(run_gate "$r")
case "$out" in *"exit=0"*) report "spec with no tasks authored stays silent" ok ;;
                        *) report "spec with no tasks authored stays silent" no "$out" ;; esac

# 12. No Tasks section at all -> silent. Same reasoning as 11, different shape: a spec can be
# mid-authoring with the heading not yet written, and the awk extractor yields nothing at all
# rather than a section with no boxes. Both must reach the same verdict.
r=$(make_repo nosection 0)
cat > "$r/.specs/9-feature/spec.md" <<'SPEC'
# Spec: feature
- Slug: 9-feature   Status: draft

## 1. Requirements
- [ ] **AC1:** an acceptance criterion.
SPEC
( cd "$r" && git add -A && git commit -qm "spec: requirements only" ) >/dev/null 2>&1
out=$(run_gate "$r")
case "$out" in *"exit=0"*) report "spec with no Tasks section stays silent" ok ;;
                        *) report "spec with no Tasks section stays silent" no "$out" ;; esac

# 13. A spec with at least one TICKED box and none unticked must still block. This is the
# boundary the fix must not have moved: "all done" and "none written" now differ, and only
# the second is silent. Without this case, gate_total_tasks could return 0 unconditionally
# and every case above would still pass.
r=$(make_repo allticked 0)
out=$(run_gate "$r"); err=$(cat "$TMP/err")
case "$out$err" in *"exit=2"*"no reviewer receipt exists"*) report "all tasks ticked still blocks" ok ;;
                 *) report "all tasks ticked still blocks" no "$out" ;; esac

# 14. A spec that exists but cannot be READ must block, not pass.
#
# Both task counters return 0 for a file they cannot open, and since #8 a zero total means
# "nothing authored, stay silent". That is the right reading for an empty section and the
# wrong one for an unreadable file: the gate would exit 0 exactly when it could not do its
# job. Fail closed instead.
r=$(make_repo unreadable 0)
chmod 000 "$r/.specs/9-feature/spec.md"
out=$(run_gate "$r"); err=$(cat "$TMP/err")
chmod 644 "$r/.specs/9-feature/spec.md"
case "$out$err" in *"exit=2"*"cannot be read"*) report "unreadable spec blocks rather than failing open" ok ;;
                 *) report "unreadable spec blocks rather than failing open" no "$out" ;; esac

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

# --- quality-gate.sh -------------------------------------------------------------
#
# It reads its commands from the `- Validators:` line rather than carrying them, so the
# thing worth testing is that the line is honoured: a failing command must block, a
# passing one must not, and a project with no such line must not be gated on nothing.

qg_repo() { # qg_repo <name> <validators line, or empty to omit it>
  r="$TMP/$1"; mkdir -p "$r/hooks" "$r/.steering"
  cp "$ROOT/hooks/gate-lib.sh" "$ROOT/hooks/quality-gate.sh" "$r/hooks/"
  if [ -n "$2" ]; then printf -- '- Validators: %s\n' "$2" > "$r/.steering/tech.md"
  else printf -- '- Reviewer: test-reviewer\n' > "$r/.steering/tech.md"; fi
  echo "$r"
}
run_qg() { ( cd "$1" && sh hooks/quality-gate.sh 2>"$TMP/err" ; echo "exit=$?" ) }

# 15. A passing validator -> silent
r=$(qg_repo qgpass "true"); out=$(run_qg "$r")
case "$out" in *"exit=0"*) report "passing validator stays silent" ok ;;
                        *) report "passing validator stays silent" no "$out" ;; esac

# 16. A failing validator -> blocks, on BOTH channels, naming the command
r=$(qg_repo qgfail "true, sh -c 'echo boom >&2; exit 1'"); out=$(run_qg "$r"); err=$(cat "$TMP/err")
case "$out" in *"exit=2"*) c1=ok ;; *) c1=no ;; esac
case "$out" in *'"decision":"continue"'*) c2=ok ;; *) c2=no ;; esac
case "$err" in *boom*) c3=ok ;; *) c3=no ;; esac
[ "$c1$c2$c3" = "okokok" ] && report "failing validator blocks on both channels" ok \
  || report "failing validator blocks on both channels" no "exit=$c1 json=$c2 stderr=$c3"

# 17. Every validator runs. Stopping at the first failure would report one problem per
#     turn and make a broken tree take as many turns to fix as it has broken validators.
r=$(qg_repo qgboth "sh -c 'echo alpha >&2; exit 1', sh -c 'echo omega >&2; exit 1'")
out=$(run_qg "$r"); err=$(cat "$TMP/err")
case "$err" in *alpha*) c1=ok ;; *) c1=no ;; esac
case "$err" in *omega*) c2=ok ;; *) c2=no ;; esac
[ "$c1$c2" = "okok" ] && report "a failure does not stop later validators running" ok \
  || report "a failure does not stop later validators running" no "first=$c1 second=$c2"

# 18. No Validators line -> silent. A project that has not declared its validators is not
#     one whose turns should be blocked by a gate with nothing to run.
r=$(qg_repo qgnone ""); out=$(run_qg "$r")
case "$out" in *"exit=0"*) report "absent Validators line stays silent" ok ;;
                        *) report "absent Validators line stays silent" no "$out" ;; esac

# --- quality gate: only pays when something matching Source globs changed ---------------
qg_repo() { # $1 = name
  r="$TMP/$1"; mkdir -p "$r/hooks" "$r/.steering"
  cp "$ROOT/hooks/gate-lib.sh" "$ROOT/hooks/quality-gate.sh" "$r/hooks/"
  printf -- '- Validators: sh -c "echo RAN >&2; exit 1"\n- Source globs: *.txt\n' > "$r/.steering/tech.md"
  ( cd "$r" && git init -q -b main && git config user.email t@t && git config user.name t \
    && echo one > src.txt && echo doc > NOTES.md && git add -A && git commit -qm init ) >/dev/null 2>&1
  echo "$r"
}
run_qg() { ( cd "$1" && sh hooks/quality-gate.sh 2>"$TMP/qerr"; echo "exit=$?" ) }

r=$(qg_repo qg-clean); out=$(run_qg "$r")
case "$out" in *"exit=0"*) report "quality gate silent when nothing changed" ok ;;
                        *) report "quality gate silent when nothing changed" no "$out" ;; esac

r=$(qg_repo qg-docs); echo more >> "$r/NOTES.md"; out=$(run_qg "$r")
case "$out" in *"exit=0"*) report "quality gate silent on a docs-only change" ok ;;
                        *) report "quality gate silent on a docs-only change" no "$out" ;; esac

r=$(qg_repo qg-src); echo more >> "$r/src.txt"; out=$(run_qg "$r"); err=$(cat "$TMP/qerr")
case "$out" in *"exit=2"*) c1=ok ;; *) c1=no ;; esac
case "$err" in *"Quality gate"*) c2=ok ;; *) c2=no ;; esac
[ "$c1$c2" = "okok" ] && report "quality gate fires on a source change" ok \
  || report "quality gate fires on a source change" no "exit=$c1 msg=$c2"

r=$(qg_repo qg-quoted)
printf -- '- Validators: sh -c "exit 1"\n- Source globs: %s\n' "'*.txt'" > "$r/.steering/tech.md"
echo more >> "$r/src.txt"; out=$(run_qg "$r")
case "$out" in *"exit=2"*) report "quoted globs still match (no fail-open)" ok ;;
                        *) report "quoted globs still match (no fail-open)" no "$out" ;; esac


# --- guards: assets/check-locks.py -------------------------------------------------
#
# The lock guard answers "has a rulebook drifted from what was agreed". It can also answer
# nothing at all — no reviewer directory scanned, no file hashed — and until #16 it reported
# that through the same success path. These fixtures build real reviewer directories so the
# difference between "checked and clean" and "checked nothing" is observable.

_sha() {
  if command -v shasum >/dev/null 2>&1; then shasum -a 256 "$1" | cut -d' ' -f1
  else sha256sum "$1" | cut -d' ' -f1; fi
}

# $1 = reviewer directory, $2 = rule path relative to it. Pins $2 at its current contents.
write_lock() {
  cat > "$1/rules-lock.json" <<EOF
{
  "version": 1,
  "vendored": {},
  "derived": {
    "r": {
      "path": "$2",
      "computedHash": "$(_sha "$1/$2")",
      "sources": [ { "id": "s", "kind": "first-party", "checkedOn": "2026-01-01" } ]
    }
  }
}
EOF
}

# $1 = repo name. A repo holding one SHIPPED reviewer under agents/, correctly pinned.
lock_repo() {
  r="$TMP/$1"; mkdir -p "$r/assets" "$r/agents/shipped/rules"
  cp "$ROOT/assets/check-locks.py" "$r/assets/"
  printf '# rules\n- **S-1** a shipped rule.\n' > "$r/agents/shipped/rules/s.md"
  write_lock "$r/agents/shipped" rules/s.md
  echo "$r"
}

# $1 = repo, $2 = reviewer name. Adds a correctly pinned reviewer under .claude/agents/.
add_project_reviewer() {
  d="$1/.claude/agents/$2"; mkdir -p "$d/rules"
  printf '# rules\n- **P-1** a project rule.\n' > "$d/rules/p.md"
  write_lock "$d" rules/p.md
}

run_locks() { ( cd "$1" && python3 assets/check-locks.py 2>"$TMP/lerr"; echo "exit=$?" ) }

# 15. A project-local reviewer must not stop the shipped rulebooks being verified.
#
# _reviewers_dir returned the FIRST candidate holding a lock and stopped, so creating
# .claude/agents/<r>/rules-lock.json took agents/ out of scope entirely — silently. The
# second half of this case is the one that matters: a clean exit proves nothing unless a
# real drift in the directory that was dropped still fails.
r=$(lock_repo lk-union); add_project_reviewer "$r" proj
out=$(run_locks "$r")
case "$out" in *"exit=0"*) c1=ok ;; *) c1=no ;; esac
printf '\n- **FAKE-1** an unpinned rule nobody agreed to.\n' >> "$r/agents/shipped/rules/s.md"
out2=$(run_locks "$r")
case "$out2" in *"exit=1"*) c2=ok ;; *) c2=no ;; esac
[ "$c1$c2" = "okok" ] && report "a project reviewer does not hide the shipped rulebooks" ok \
  || report "a project reviewer does not hide the shipped rulebooks" no "clean=$c1 drift-caught=$c2"

# 16. Locks exist but pinned zero verifiable files -> FAIL.
#
# The state that made #16 invisible. A lock with empty vendored/derived hashes nothing, so
# `checked` stayed 0 and 0 was reported through the success path — identical output to a
# run that verified everything and found no drift.
r=$(lock_repo lk-empty)
printf '{"version":1,"vendored":{},"derived":{}}\n' > "$r/agents/shipped/rules-lock.json"
out=$(run_locks "$r"); err=$(cat "$TMP/lerr")
case "$out" in *"exit=1"*) c1=ok ;; *) c1=no ;; esac
case "$err" in *"verified no files"*) c2=ok ;; *) c2=no ;; esac
[ "$c1$c2" = "okok" ] && report "locks that pin nothing fail rather than pass" ok \
  || report "locks that pin nothing fail rather than pass" no "exit=$c1 msg=$c2 [$err]"

# 17. No locks anywhere -> pass, but not with the wording of a real verification.
#
# Legitimate: a project may install the guard before its first reviewer exists. Failing here
# would hand it a red build it could only fix by deleting the guard, which is how a guard
# gets deleted. The requirement is that its message cannot be mistaken for having checked.
r=$(lock_repo lk-none); rm -f "$r/agents/shipped/rules-lock.json"
out=$(run_locks "$r")
case "$out" in *"exit=0"*) c1=ok ;; *) c1=no ;; esac
case "$out" in *"no rulebooks are pinned"*) c2=ok ;; *) c2=no ;; esac
case "$out" in *"match their locks"*) c3=no ;; *) c3=ok ;; esac
[ "$c1$c2$c3" = "okokok" ] && report "no locks anywhere passes with distinct wording" ok \
  || report "no locks anywhere passes with distinct wording" no "exit=$c1 distinct=$c2 not-success-wording=$c3"

# 18. --update must re-pin ONLY the lock whose file drifted.
#
# The blast radius of scanning several directories instead of one. --update rewrites lock
# files in place, so a union that re-pinned every lock it walked past would silently accept
# drift in reviewers nobody touched — turning "re-pin after a deliberate edit" into "accept
# whatever is on disk", which is the guard agreeing with anything it is shown.
r=$(lock_repo lk-update); add_project_reviewer "$r" proj
before=$(_sha "$r/.claude/agents/proj/rules-lock.json")
printf '\n- **S-2** a deliberate new rule.\n' >> "$r/agents/shipped/rules/s.md"
( cd "$r" && python3 assets/check-locks.py --update >/dev/null 2>&1 )
after=$(_sha "$r/.claude/agents/proj/rules-lock.json")
out=$(run_locks "$r")
[ "$before" = "$after" ] && c1=ok || c1=no          # untouched reviewer's lock is byte-identical
case "$out" in *"exit=0"*) c2=ok ;; *) c2=no ;; esac # the edited one was re-pinned
[ "$c1$c2" = "okok" ] && report "--update re-pins only the lock that drifted" ok \
  || report "--update re-pins only the lock that drifted" no "untouched=$c1 repinned=$c2"

# 19. A reviewer directory that exists but cannot be READ must fail, not be skipped.
#
# Path.glob swallows the permission error and yields nothing, so an unreadable directory
# contributed zero locks while still being named in the "scanned" list — the report actively
# claiming coverage it did not have. Naming the directories (case 16/17) made this worse
# rather than better, which is why it is pinned separately.
#
# Skipped when the chmod does not actually deny access (running as root, or a filesystem
# without POSIX permissions). A case that cannot fail is worse than no case.
r=$(lock_repo lk-unreadable); add_project_reviewer "$r" proj
chmod 000 "$r/agents/shipped" 2>/dev/null
if cat "$r/agents/shipped/rules-lock.json" >/dev/null 2>&1; then
  chmod 755 "$r/agents/shipped" 2>/dev/null
  report "unreadable reviewer directory fails rather than being skipped" ok
else
  out=$(run_locks "$r"); err=$(cat "$TMP/lerr")
  chmod 755 "$r/agents/shipped" 2>/dev/null
  case "$out" in *"exit=1"*) c1=ok ;; *) c1=no ;; esac
  case "$err" in *"cannot be read"*) c2=ok ;; *) c2=no ;; esac
  [ "$c1$c2" = "okok" ] && report "unreadable reviewer directory fails rather than being skipped" ok \
    || report "unreadable reviewer directory fails rather than being skipped" no "exit=$c1 msg=$c2"
fi

# 20. A legacy receipt with no reviewed_by must still clear the gate.
#
# AC2 of #9. The field is new, and every receipt written before it existed lacks it. The
# gate must not start blocking those — but equally it must not read their silence as
# independence, which is why the field is recorded rather than inferred. Today the gate
# ignores the field entirely; this case exists so that stays deliberate rather than
# accidental when the gate is eventually taught to read it (#25).
r=$(make_repo legacy-receipt 0)
( cd "$r" && printf 'reviewed_sha=%s\nreviewer=test-reviewer\nverdict=CLEAN\nblockers=0\nhigh=0\nreviewed_at=2026-01-01T00:00:00Z\n' "$(git rev-parse HEAD)" > .specs/9-feature/.review-receipt ) >/dev/null 2>&1
out=$(run_gate "$r")
case "$out" in *"exit=0"*) report "a receipt without reviewed_by still clears the gate" ok ;;
                        *) report "a receipt without reviewed_by still clears the gate" no "$out" ;; esac

# 21. A receipt carrying reviewed_by=inline clears the gate too, for now.
#
# Recorded, not gated — the clarification on #9 was "record now, gate later", because
# refusing CLEAN on a self-review before init guarantees a spawnable reviewer would block
# every new project's first implement. This case pins the CURRENT contract so that changing
# it is a deliberate act with a failing test, not a quiet tightening.
r=$(make_repo inline-receipt 0)
( cd "$r" && printf 'reviewed_sha=%s\nreviewer=test-reviewer\nverdict=CLEAN\nblockers=0\nhigh=0\nreviewed_at=2026-01-01T00:00:00Z\nreviewed_by=inline\n' "$(git rev-parse HEAD)" > .specs/9-feature/.review-receipt ) >/dev/null 2>&1
out=$(run_gate "$r")
case "$out" in *"exit=0"*) report "reviewed_by=inline is recorded, not gated (see #25)" ok ;;
                        *) report "reviewed_by=inline is recorded, not gated (see #25)" no "$out" ;; esac

# 22. The missing-receipt message must name waiting as a valid action.
#
# #27. The gate fires on Stop, so it can fire while a spawned reviewer is still reading —
# and it then told the author to run a reviewer that was already running. That is advice
# which cannot be taken by an author who does not know how to wait. A turn stays open across
# tool calls, so waiting is possible — the failure was emitting a final message between checks,
# each of which ended the turn and re-armed the gate. This message does not fix that; it stops
# the message misleading about what to do while the reviewer runs.
r=$(make_repo waiting-msg 0)
out=$(run_gate "$r"); err=$(cat "$TMP/err")
case "$out" in *"exit=2"*) c1=ok ;; *) c1=no ;; esac
case "$err" in *"already running"*) c2=ok ;; *) c2=no ;; esac
case "$err" in *"no reviewer receipt exists"*) c3=ok ;; *) c3=no ;; esac
[ "$c1$c2$c3" = "okokok" ] && report "missing-receipt message names waiting as valid" ok \
  || report "missing-receipt message names waiting as valid" no "blocks=$c1 waiting=$c2 kept-substring=$c3"

# --- guards: assets/check-steering-anchors.sh --------------------------------------
#
# Steering carries five machine-read lines. Each is read by a hook with a `sed` whose
# anchor is exact, and a value that fails that anchor produces nothing and no complaint —
# the file still looks right to a human. This repo's own `- Owns:` line was bolded and
# therefore unreadable for a week (#34). These fixtures pin the difference between a line
# that is ABSENT, which is legitimate, and one that is PRESENT and unparseable, which is not.

# $1 = repo name, $2 = the literal Owns line to write (or empty to omit it)
anchor_repo() {
  r="$TMP/$1"; mkdir -p "$r/.steering" "$r/hooks" "$r/assets"
  cp "$ROOT/hooks/gate-lib.sh" "$r/hooks/"
  cp "$ROOT/assets/check-steering-anchors.sh" "$r/assets/"
  printf -- '- Validators: true\n- Reviewer: r\n- Source globs: :(glob)**/*.txt\n- Docs: docs/\n' > "$r/.steering/tech.md"
  printf '# Product\n\n' > "$r/.steering/product.md"
  [ -n "$2" ] && printf '%s\n' "$2" >> "$r/.steering/product.md"
  echo "$r"
}
# Prints the bare exit code, NOT "exit=$?". A case glob of *"exit=1"* also matches
# "exit=127" — what sh returns for a missing script — so the first draft of case 23 reported
# ok while the script did not exist.
#
# THREE older uses of that glob remain, at :347, :359 and :411. They are safe, but not for the
# reason first written here: "the subject always exists" does not hold, since a python3 that
# is missing (127) or that dies on a traceback (1) both satisfy the glob. What saves them is
# that each is corroborated by an assertion a crash cannot satisfy — a stderr substring, or a
# paired *"exit=0"* test. Copy the glob into a case with no corroborator and it breaks again.
# stdout is discarded as well as captured stderr: the success line would otherwise be
# concatenated with the exit code, so `out` read "…all readable0" and every equality test
# failed. Case 23 hid it, because a failing run prints nothing to stdout.
run_anchors() { ( cd "$1" && sh assets/check-steering-anchors.sh >/dev/null 2>"$TMP/aerr"; printf '%s' "$?" ) }

# 23. A bolded anchor is present and unparseable -> fail, naming anchor and file.
r=$(anchor_repo anc-bold '- **Owns: gates never fail open.**')
out=$(run_anchors "$r"); err=$(cat "$TMP/aerr" 2>/dev/null)
[ "$out" = "1" ] && c1=ok || c1=no
case "$err" in *"Owns"*) c2=ok ;; *) c2=no ;; esac
case "$err" in *"product.md"*) c3=ok ;; *) c3=no ;; esac
[ "$c1$c2$c3" = "okokok" ] && report "a bolded steering anchor fails, naming anchor and file" ok \
  || report "a bolded steering anchor fails, naming anchor and file" no "exit=$c1 anchor=$c2 file=$c3"

# 24. A correctly written anchor passes, and an absent optional one does not fail.
#
# Absence is legitimate — a project may have no `Docs` line at all — so failing on it would
# fire on a configuration the harness supports, which is how a guard earns being deleted.
r=$(anchor_repo anc-ok '- Owns: gates never fail open.')
out=$(run_anchors "$r")
[ "$out" = "0" ] && c1=ok || c1=no
r=$(anchor_repo anc-absent '')          # no Owns line at all
out=$(run_anchors "$r")
[ "$out" = "0" ] && c2=ok || c2=no
[ "$c1$c2" = "okok" ] && report "a readable anchor passes and an absent one is not a failure" ok \
  || report "a readable anchor passes and an absent one is not a failure" no "readable=$c1 absent=$c2"

# 25. The check must FAIL, not skip, when it cannot find gate-lib.sh.
#
# AC7, and the reason it is a criterion: locating gate-lib.sh is the problem that produced
# #16, and this script ships into every project. A guard that reports success because it
# could not find its own dependency is the exact bug it exists to prevent.
r=$(anchor_repo anc-nolib '- **Owns: bolded.**')
rm -f "$r/hooks/gate-lib.sh"
out=$(run_anchors "$r"); err=$(cat "$TMP/aerr" 2>/dev/null)
[ "$out" = "1" ] && c1=ok || c1=no
case "$err" in *"cannot find gate-lib.sh"*) c2=ok ;; *) c2=no ;; esac
[ "$c1$c2" = "okok" ] && report "missing gate-lib.sh fails rather than skipping" ok \
  || report "missing gate-lib.sh fails rather than skipping" no "exit=$c1 msg=$c2"

# 26. The digest emits the quality anchor, and emits nothing on stderr.
#
# There was no case for steering-digest.sh at all, which is why migrating its reader to
# gate_steering_value broke it invisibly: the file did not source gate-lib.sh, so the call
# was to an undefined function and the anchor silently vanished — the exact failure #34 is
# about, reintroduced by #34's own fix. The case-list diff could not catch it because the
# suite had nothing to say about this hook.
r=$(anchor_repo dg-anchor '- Owns: gates never fail open')
cp "$ROOT/hooks/steering-digest.sh" "$r/hooks/"
( cd "$r" && sh hooks/steering-digest.sh >"$TMP/dgout" 2>"$TMP/dgerr" )
case "$(cat "$TMP/dgout")" in *"owns gates never fail open"*) c1=ok ;; *) c1=no ;; esac
[ -s "$TMP/dgerr" ] && c2=no || c2=ok
[ "$c1$c2" = "okok" ] && report "the digest emits the quality anchor, with clean stderr" ok \
  || report "the digest emits the quality anchor, with clean stderr" no "anchor=$c1 clean-stderr=$c2"

# 27. An absent optional anchor must stay silent even when the file mentions the key in prose.
#
# The loose match has to be sloppier than the reader — it must still see `- **Owns:` — but not
# so sloppy that ordinary prose trips it. Unanchored, `Docs *:` matched "docs:" inside this
# repo's own commit-convention paragraph, so deleting a legitimately optional `- Docs:` line
# would have failed the guard while pointing at prose. There was no case for that.
r=$(anchor_repo anc-prose '- Owns: gates never fail open')
printf -- '- Validators: true\n- Reviewer: r\n\nConventional commits — `feat:`, `docs:`, `chore:` — imperative.\n' > "$r/.steering/tech.md"
out=$(run_anchors "$r")
[ "$out" = "0" ] && report "prose containing an anchor key does not false-block" ok \
  || report "prose containing an anchor key does not false-block" no "exit=$out"

# 28. No steering at all -> pass, but NOT in the wording of a run that checked something.
#
# #16's exact shape, in the guard whose own AC7 exists because of #16. Exit 0 is right — the
# guard may be installed before init writes steering — but a success-shaped sentence
# is a sentence that cannot be told apart from a real verification.
r=$(anchor_repo anc-nosteering ''); rm -rf "$r/.steering"
out=$(run_anchors "$r")
o=$( cd "$r" && sh assets/check-steering-anchors.sh 2>/dev/null )
[ "$out" = "0" ] && c1=ok || c1=no
case "$o" in *"nothing was checked"*) c2=ok ;; *) c2=no ;; esac
case "$o" in *"anchor(s) resolved"*) c3=no ;; *) c3=ok ;; esac   # the wording the success path uses TODAY
[ "$c1$c2$c3" = "okokok" ] && report "no steering passes with wording distinct from a real check" ok \
  || report "no steering passes with wording distinct from a real check" no "exit=$c1 distinct=$c2 not-success-wording=$c3"

# 29. A gate-lib.sh that predates the shared reader must fail with the RIGHT diagnosis.
#
# init copies this asset into projects whose gate-lib.sh may be older. Without this the script
# fails closed — correct — while reporting every correctly written anchor as unparseable, which
# sends the author to edit steering that is fine. A guard with a wrong diagnosis gets removed.
r=$(anchor_repo anc-stalelib '- Owns: x')
python3 - "$r" <<'PYEOF'
import pathlib, sys
src = pathlib.Path(sys.argv[1], "hooks", "gate-lib.sh").read_text()  # the fixture's own copy, not cwd's
i = src.index("# Read one machine-read value out of a steering file.")
j = src.index("\n}\n", src.index("gate_steering_value()")) + 3
pathlib.Path(sys.argv[1], "hooks", "gate-lib.sh").write_text(src[:i] + src[j:])
PYEOF
out=$(run_anchors "$r"); err=$(cat "$TMP/aerr" 2>/dev/null)
[ "$out" = "1" ] && c1=ok || c1=no
case "$err" in *"predates the shared reader"*) c2=ok ;; *) c2=no ;; esac
[ "$c1$c2" = "okok" ] && report "a stale gate-lib.sh fails with the right diagnosis" ok \
  || report "a stale gate-lib.sh fails with the right diagnosis" no "exit=$c1 msg=$c2"

# 30. ANCHORS must not fall behind the hooks it mirrors.
#
# G-8: a guard's list is part of the guard, and "N of M anchor(s) resolved" reads the
# same whether the hooks have five anchors or six. Deriving the table would be worse; detecting
# drift is not. Every call site passes literal arguments, so they can be compared.
declared=$(sed -n 's/^\.steering\/[a-z]*\.md|//p' "$ROOT/assets/check-steering-anchors.sh" | sort -u)
# The `s/"\$1"//` clause that used to be here could never match — grep's [A-Za-z ] class
# excludes the quote — so it read as though the steer() wrapper were handled while the wrapper
# was silently dropped instead. The wrapper is gone; every call site is literal.
used=$(grep -ho "gate_steering_value [^ ]* '\?[A-Za-z ]*'\?" "$ROOT"/hooks/*.sh \
       | sed "s/.*gate_steering_value [^ ]* //; s/'//g" | grep -v '^$' | sort -u)
# The relation is containment, not equality. ANCHORS may legitimately hold more than the hooks
# read — `Docs` is consumed by skills and no hook touches it — and that is not drift. Drift is
# a hook reading an anchor the table does not cover, which is the direction that makes
# the success line certify something unchecked. Asserting equality here failed on `Docs` and
# would have taught the next person to delete it.
# `|| true` only, and no fallback. The first version had `|| comm -23 <(...) <(...)` as a
# defensive alternative; process substitution is not POSIX, and under `sh` it made the whole
# substitution yield nothing — so the case could not fail, and a mutation adding an uncovered
# anchor still reported ok. An untested fallback disabled the test it was guarding.
missing=$(echo "$used" | grep -vxF "$declared" || true)
# An empty `used` makes the comparison vacuous: `echo "" | grep -vxF` emits nothing, `missing`
# is empty, and the case reports ok having compared nothing. Any reformatting of the call sites
# — a variable key, a line break, a rename — would turn this detector off silently rather than
# red. That is the same shape as the untested fallback removed from this case last round.
if [ -z "$used" ]; then
  report "every anchor a hook reads is covered by the ANCHORS table" no "call-site extraction matched nothing"
elif [ -z "$missing" ]; then report "every anchor a hook reads is covered by the ANCHORS table" ok
else report "every anchor a hook reads is covered by the ANCHORS table" no "uncovered: $(echo "$missing" | tr '\n' ',')"; fi

# 31. A gate-lib.sh predating the shared reader must BLOCK the quality gate, not pass it.
#
# The migration to gate_steering_value created this: `set -u` does not catch an undefined
# FUNCTION, so a stale library made the validator read return empty, the "nothing configured"
# branch fire, and the gate exit 0 having run nothing. A fail-open introduced by the change
# that centralised the reader — and the asset already guarded itself against the same skew,
# which made the gate the unguarded half and the one whose failure is silent.
r=$(qg_repo qg-stalelib)
python3 - "$r" <<'PYEOF'
import pathlib, sys
src = pathlib.Path(sys.argv[1], "hooks", "gate-lib.sh").read_text()
i = src.index("# Read one machine-read value out of a steering file.")
j = src.index("\n}\n", src.index("gate_steering_value()")) + 3
pathlib.Path(sys.argv[1], "hooks", "gate-lib.sh").write_text(src[:i] + src[j:])
PYEOF
echo more >> "$r/src.txt"
out=$(run_qg "$r"); err=$(cat "$TMP/qerr")
case "$out" in *"exit=2"*) c1=ok ;; *) c1=no ;; esac
case "$err" in *"predates the shared steering reader"*) c2=ok ;; *) c2=no ;; esac
[ "$c1$c2" = "okok" ] && report "a stale gate-lib blocks the quality gate rather than passing it" ok \
  || report "a stale gate-lib blocks the quality gate rather than passing it" no "exit=$c1 msg=$c2"

# 32. A steering file that exists but cannot be READ must fail, not read as "anchor absent".
#
# `[ -f ]` tests existence. For a mode-000 file gate_steering_value returns empty (its own
# 2>/dev/null eats the sed error) and the loose grep exits 2 — an ERROR, which `&&` cannot
# distinguish from a non-match — so the anchor was classified absent and the run went on to
# claim "none unreadable" about a file it could not read. Third state, same exit code, same
# sentence, in the guard that exists to keep those apart.
#
# Skipped where chmod does not actually deny access (root, or a filesystem without POSIX
# permissions). A case that cannot fail is worse than no case.
r=$(anchor_repo anc-unreadable '- Owns: x')
chmod 000 "$r/.steering/product.md" 2>/dev/null
if cat "$r/.steering/product.md" >/dev/null 2>&1; then
  chmod 644 "$r/.steering/product.md" 2>/dev/null
  report "an unreadable steering file fails rather than reading as absent" ok
else
  out=$(run_anchors "$r"); err=$(cat "$TMP/aerr" 2>/dev/null)
  chmod 644 "$r/.steering/product.md" 2>/dev/null
  [ "$out" = "1" ] && c1=ok || c1=no
  case "$err" in *"cannot be read"*) c2=ok ;; *) c2=no ;; esac
  [ "$c1$c2" = "okok" ] && report "an unreadable steering file fails rather than reading as absent" ok \
    || report "an unreadable steering file fails rather than reading as absent" no "exit=$c1 msg=$c2"
fi

# 33. A stale gate-lib.sh must degrade the digest visibly, not silently.
#
# The digest has no blocking channel, so it cannot be made loud — but omitting Owns,
# Validators and Reviewer while printing "not found" to stderr is #34's symptom reintroduced
# by #34's fix. A visible line in the digest is the right register for a hook that cannot block.
r=$(anchor_repo dg-stalelib '- Owns: x')
cp "$ROOT/hooks/steering-digest.sh" "$r/hooks/"
python3 - "$r" <<'PYEOF'
import pathlib, sys
src = pathlib.Path(sys.argv[1], "hooks", "gate-lib.sh").read_text()
i = src.index("# Read one machine-read value out of a steering file.")
j = src.index("\n}\n", src.index("gate_steering_value()")) + 3
pathlib.Path(sys.argv[1], "hooks", "gate-lib.sh").write_text(src[:i] + src[j:])
PYEOF
( cd "$r" && sh hooks/steering-digest.sh >"$TMP/dgout" 2>"$TMP/dgerr" )
case "$(cat "$TMP/dgout")" in *"degraded"*) c1=ok ;; *) c1=no ;; esac
[ -s "$TMP/dgerr" ] && c2=no || c2=ok
[ "$c1$c2" = "okok" ] && report "a stale gate-lib degrades the digest visibly, not silently" ok \
  || report "a stale gate-lib degrades the digest visibly, not silently" no "visible=$c1 clean-stderr=$c2"

# --- guards: scripts/check-receipt-schema.py ---------------------------------------
#
# #28. The invariant that makes the mirror-skip unreachable — every MIRRORS destination is
# also a SOURCE, so the SOURCES loop hard-exits on a missing file before the skip can run —
# was written as an `assert`. `python3 -O` deletes it, and so does PYTHONOPTIMIZE=1 in the
# environment, which reaches an `env python3` shebang without any caller opting in. With it
# gone the guard skips a mirror it never checked for and prints its success line. That is
# #16's shape, in the guard added by the spec whose sibling fixed #16.

# A tree the guard resolves against instead of this repository: ROOT comes from __file__,
# so a copy of the script under $TMP compares the copies sitting next to it.
receipt_repo() {
  r="$TMP/$1"; mkdir -p "$r/scripts" "$r/agents/_shared" "$r/skills/implement"
  cp "$ROOT/scripts/check-receipt-schema.py" "$r/scripts/"
  chmod +x "$r/scripts/check-receipt-schema.py"   # the PYTHONOPTIMIZE case runs the shebang
  cp "$ROOT/agents/_shared/reviewer-contract.md" "$r/agents/_shared/"
  cp "$ROOT/skills/implement/SKILL.md" "$r/skills/implement/"
  # The mirror starts PRESENT. It has to: it is a SOURCE, and the SOURCES loop hard-exits on a
  # missing file, so a fixture built without it fails before reaching the branch under test —
  # which is what the control below is there to catch. Case 34 removes it and its SOURCES entry
  # together, which is the pair of edits that makes the skip reachable.
  mkdir -p "$r/.claude/agents/_shared"
  cp "$ROOT/.claude/agents/_shared/reviewer-contract.md" "$r/.claude/agents/_shared/"
  echo "$r"
}

# 34. A mirror that is not a SOURCE must fail, with assertions stripped.
r=$(receipt_repo receipt-mirror)

# The control runs FIRST, and it is not decoration: without it a case that fails for any
# reason at all — a bad copy, a python3 that is not there — reads as a caught bug. It is
# also AC5: the untouched guard behaves identically under -O.
ctl=$( cd "$r" && python3 -O scripts/check-receipt-schema.py 2>/dev/null; echo "exit=$?" )
case "$ctl" in *"field(s) agree"*"exit=0"*) c0=ok ;; *) c0=no ;; esac

# Break the invariant the way the reviewer broke it by hand. python3 rather than `sed -i`,
# which is not portable, and it EXITS NON-ZERO when its needle is gone — a reworded SOURCES
# entry would otherwise no-op the mutation and leave this case reporting ok having run a
# script that was never broken.
python3 - "$r" <<'PYEOF'
import pathlib, sys
p = pathlib.Path(sys.argv[1], "scripts", "check-receipt-schema.py")
src = p.read_text()
needle = '    ".claude/agents/_shared/reviewer-contract.md",\n'
if needle not in src:
    sys.exit(3)
p.write_text(src.replace(needle, "", 1))
pathlib.Path(sys.argv[1], ".claude", "agents", "_shared", "reviewer-contract.md").unlink()
PYEOF
built=$?

if [ "$built" -ne 0 ]; then
  report "a mirror that is not a SOURCE fails even with assertions stripped" no \
    "fixture could not be built: the SOURCES entry this case removes was not found"
else
  # Both invocations are checked the same way, and exit code alone is not the check. Exit 1 is
  # also what a traceback returns — including the AssertionError this fix removes — so a bare
  # `= "1"` would read ok against the UNFIXED script on any interpreter where PYTHONOPTIMIZE
  # did not really strip assertions. Each half therefore needs a diagnostic naming the path
  # (which is AC1, and what AC2 asks to hold under both invocations) and an absence of
  # "Traceback", which no crash can satisfy. That pairing is this file's own rule at :481-484.
  stripped_fails() { # stripped_fails <exit-code> <stderr-file> -> ok|no
    [ "$1" = "1" ] || { echo no; return; }
    serr=$(cat "$2" 2>/dev/null)
    case "$serr" in *Traceback*) echo no; return ;; esac
    # AC1 asks for the path, so the path is required. It is not SUFFICIENT: the SOURCES loop's
    # own "is missing" message at check-receipt-schema.py:82 names the same path and also exits
    # 1 with no traceback, so the path alone is satisfied by a sibling branch of the same guard.
    # That branch cannot fire while the fixture drops the SOURCES entry and the mirror as one
    # act — but then the discrimination rests on the fixture builder rather than on the
    # assertion, and a later loosening of the fixture would turn this green against the unfixed
    # script. Require the phrase unique to the branch under test as well.
    case "$serr" in *".claude/agents/_shared/reviewer-contract.md"*) : ;; *) echo no; return ;; esac
    case "$serr" in *"is a mirror but not a SOURCE"*) echo ok ;; *) echo no ;; esac
  }
  out=$( cd "$r" && python3 -O scripts/check-receipt-schema.py >/dev/null 2>"$TMP/rerr"; printf '%s' "$?" )
  c1=$(stripped_fails "$out" "$TMP/rerr")
  # No flag, through the shebang — how this arrives without any caller choosing it.
  out2=$( cd "$r" && PYTHONOPTIMIZE=1 ./scripts/check-receipt-schema.py >/dev/null 2>"$TMP/rerr2"; printf '%s' "$?" )
  c2=$(stripped_fails "$out2" "$TMP/rerr2")
  [ "$c0$c1$c2" = "okokok" ] \
    && report "a mirror that is not a SOURCE fails even with assertions stripped" ok \
    || report "a mirror that is not a SOURCE fails even with assertions stripped" no \
       "control=$c0 minus-O=$c1 PYTHONOPTIMIZE=$c2"
fi

# 35. No guard expresses a safety check as an assert.
#
# #28 generalised, and pinned rather than remembered because the convention had already been
# deviated from once. `assert` is the one Python statement the interpreter is allowed to
# delete, so a safety check written as one is a check an environment variable removes.
#
# Anchored to statement position on purpose: an unanchored `assert` matches "asserts the" in
# check-skill-contracts.py and "asserted in a README" in this file's own header, so the loose
# pattern would arrive permanently red and be deleted rather than obeyed.
# The work-set is corroborated PER DIRECTORY. Counting the union — which the first draft of
# this case did — cannot detect one of the three vanishing: `find` keeps going on the surviving
# operands, any one directory alone holds well over three files, and its non-zero status is
# never read. `grep -rnE` then exits 2 on the missing operand, and a trailing `|| true`
# flattens that into the same silence as "no matches". That is precisely the confusion this
# file records at :640-644, so the comment named the failure mode while the check did not
# reach it — the guard-shaped hole this whole spec is about, in the case pinning it.
missing_dirs=
for d in scripts assets hooks; do
  [ -d "$ROOT/$d" ] || missing_dirs="$missing_dirs $d"
done
if [ -n "$missing_dirs" ]; then
  report "no guard expresses a safety check as an assert" no "work-set incomplete:$missing_dirs"
else
  hits=$(grep -rnE '^[[:space:]]*assert[[:space:]]' "$ROOT/scripts" "$ROOT/assets" "$ROOT/hooks")
  rc=$?   # 0 matched, 1 no match, 2 ERROR. Only 1 is a pass; 2 must not read as silence.
  if [ "$rc" -eq 2 ]; then
    report "no guard expresses a safety check as an assert" no "grep could not read its work-set"
  elif [ "$rc" -eq 1 ]; then
    report "no guard expresses a safety check as an assert" ok
  else
    report "no guard expresses a safety check as an assert" no "$(echo "$hits" | tr '\n' ' ')"
  fi
fi

# --- guards: scripts/check-templates.py --------------------------------------------
#
# #10. The feature and bug templates split a TDD pair across two tasks while implement's
# loop defines a task as a complete Red-Green-Refactor cycle, so following both literally
# ends a turn red and quality-gate.sh blocks it. check-templates.py fails when a task names
# a red step with no green step to answer it. These cases pin the guard itself: it ships as
# a new validator, and .steering/structure.md makes this file the project's whole notion of
# test coverage, so a guard with no case here is a guard nothing checks.

# A tree the guard resolves against instead of this repository. $1 = name, and the caller
# writes templates.md afterwards, so each case controls exactly the line under test.
templates_repo() {
  r="$TMP/$1"; mkdir -p "$r/scripts" "$r/skills/spec"
  cp "$ROOT/scripts/check-templates.py" "$r/scripts/"
  chmod +x "$r/scripts/check-templates.py"
  echo "$r"
}

# $1 = repo dir, $2 = the Feature block's T1 line, $3 = the Bug block's T1 line (optional,
# defaults to the folded form). BOTH are parameters: an earlier version varied only Feature,
# and the consequence was that no fixture anywhere contained a split line outside that
# section — so narrowing the guard to scan Feature alone deleted half its work-set with the
# whole suite still green. Isolation is worth having, but not at the price of a work-set no
# case ever exercises. python3 rather than a shell heredoc: the fixture contains fenced code
# blocks, and escaping backticks through sh is how a fixture quietly stops being the shape it
# claims to be.
write_templates() {
  python3 - "$1" "$2" "${3:-- [ ] T1: regression test that fails for the right reason — then the fix for the root cause}" <<'PYEOF'
import pathlib, sys
root, t1, bug = sys.argv[1], sys.argv[2], sys.argv[3]
doc = f"""# Spec templates by issue type

## Feature

```markdown
## 3. Tasks (TDD-ordered)
{t1}
- [ ] T2: refactor ...
```

## Bug

```markdown
## 3. Tasks (TDD-ordered)
{bug}
- [ ] T2: refactor
```

## Chore

```markdown
## 3. Tasks (TDD-ordered)
- [ ] T1: add tests covering the behavior that must be preserved but is untested
- [ ] T2: confirm they pass BEFORE the change — this is the baseline
- [ ] T3: make the change
```
"""
pathlib.Path(root, "skills", "spec", "templates.md").write_text(doc)
PYEOF
}

run_templates() { ( cd "$1" && python3 scripts/check-templates.py >/dev/null 2>"$TMP/terr"; printf '%s' "$?" ) }

# 36. A split red step fails; a folded one passes; the chore block is never flagged.
#
# The control runs FIRST. A guard that failed on every input would satisfy the split half of
# this case on its own, and "flags the thing we broke" is not evidence unless "passes the
# thing we did not" is established beside it. The chore assertion is the other half of the
# same argument: chore's T1 adds tests with no red step, and flagging it would mean the guard
# had learned "mentions tests" rather than "names a red step with nothing to answer it".
r=$(templates_repo tpl-split)
write_templates "$r" "- [ ] T1: failing test for <behavior> — then the implementation that makes it pass"
out=$(run_templates "$r")
[ "$out" = "0" ] && c0=ok || c0=no

write_templates "$r" "- [ ] T1: write the failing test for ..."
out=$(run_templates "$r"); err=$(cat "$TMP/terr")
[ "$out" = "1" ] && c1=ok || c1=no
case "$err" in *"write the failing test for"*) c2=ok ;; *) c2=no ;; esac
case "$err" in *"add tests covering the behavior"*) c3=no ;; *) c3=ok ;; esac   # chore must NOT appear

# The Bug section, with Feature folded. Without this nothing pins that the guard looks
# outside Feature at all, and a guard narrowed to one section passes the whole suite.
write_templates "$r" "- [ ] T1: failing test for <behavior> — then the implementation that makes it pass" \
                     "- [ ] T1: write the regression test — confirm it fails, and fails for the right reason"
out=$(run_templates "$r"); berr=$(cat "$TMP/terr")
[ "$out" = "1" ] && c4=ok || c4=no
case "$berr" in *"write the regression test"*) c5=ok ;; *) c5=no ;; esac
case "$berr" in *"(Bug)"*) c6=ok ;; *) c6=no ;; esac

[ "$c0$c1$c2$c3$c4$c5$c6" = "okokokokokokok" ] && report "a split red step fails in either section, a folded one passes, chore is untouched" ok \
  || report "a split red step fails in either section, a folded one passes, chore is untouched" no \
     "folded-passes=$c0 feature-fails=$c1 names-line=$c2 chore-not-flagged=$c3 bug-fails=$c4 names-bug-line=$c5 names-section=$c6"

# 37. A templates.md the guard cannot read must fail, not pass.
#
# The guard's whole job is to compare something. Existence is not readability — case 32
# established that as a real third state — and a guard that reports success about a file it
# never opened is the shape this repo has shipped four times.
r=$(templates_repo tpl-missing)          # no templates.md written at all
out=$(run_templates "$r"); err=$(cat "$TMP/terr")
[ "$out" = "1" ] && c1=ok || c1=no
case "$err" in *"is missing"*) c2=ok ;; *) c2=no ;; esac

r=$(templates_repo tpl-unreadable)
write_templates "$r" "- [ ] T1: failing test for X — then the implementation that makes it pass"
chmod 000 "$r/skills/spec/templates.md" 2>/dev/null
# Skipped where chmod does not actually deny access (root, or a filesystem without POSIX
# permissions). A case that cannot fail is worse than no case.
if cat "$r/skills/spec/templates.md" >/dev/null 2>&1; then
  chmod 644 "$r/skills/spec/templates.md" 2>/dev/null
  c3=ok; c4=ok
else
  out2=$(run_templates "$r"); err2=$(cat "$TMP/terr")
  chmod 644 "$r/skills/spec/templates.md" 2>/dev/null
  [ "$out2" = "1" ] && c3=ok || c3=no
  case "$err2" in *"cannot be read"*) c4=ok ;; *) c4=no ;; esac
fi
[ "$c1$c2$c3$c4" = "okokokok" ] && report "a templates.md that cannot be read fails rather than passing" ok \
  || report "a templates.md that cannot be read fails rather than passing" no \
     "missing-exit=$c1 missing-msg=$c2 unreadable-exit=$c3 unreadable-msg=$c4"

# 38. An empty work-set must fail, and a vanished section must not read as "nothing to check".
#
# Both are #16 in this guard. Zero task lines compared is not zero disagreements found, and a
# template section whose Tasks block was deleted is a section the guard stopped covering — in
# neither case may the success line be reachable.
r=$(templates_repo tpl-empty)
python3 - "$r" <<'PYEOF'
import pathlib, sys
# Three sections, every Tasks heading present, and not one task line under any of them.
doc = "# t\n\n## Feature\n\n## 3. Tasks (TDD-ordered)\n\n## Bug\n\n## 3. Tasks (TDD-ordered)\n\n## Chore\n\n## 3. Tasks (TDD-ordered)\n"
pathlib.Path(sys.argv[1], "skills", "spec", "templates.md").write_text(doc)
PYEOF
out=$(run_templates "$r"); err=$(cat "$TMP/terr")
[ "$out" = "1" ] && c1=ok || c1=no
case "$err" in *"nothing"*) c2=ok ;; *) c2=no ;; esac

r=$(templates_repo tpl-nosection)
python3 - "$r" <<'PYEOF'
import pathlib, sys
# Bug's Tasks block has been deleted entirely. Feature and Chore are intact and folded, so
# the guard could compare two of three and report success on what it did look at.
doc = ("# t\n\n## Feature\n\n## 3. Tasks (TDD-ordered)\n"
       "- [ ] T1: failing test for X — then the implementation that makes it pass\n\n"
       "## Bug\n\nprose only, no Tasks block\n\n"
       "## Chore\n\n## 3. Tasks (TDD-ordered)\n- [ ] T1: add tests for preserved behavior\n")
pathlib.Path(sys.argv[1], "skills", "spec", "templates.md").write_text(doc)
PYEOF
out2=$(run_templates "$r"); err2=$(cat "$TMP/terr")
[ "$out2" = "1" ] && c3=ok || c3=no
case "$err2" in *"Bug"*) c4=ok ;; *) c4=no ;; esac
[ "$c1$c2$c3$c4" = "okokokok" ] && report "an empty work-set and a vanished section both fail" ok \
  || report "an empty work-set and a vanished section both fail" no \
     "empty-exit=$c1 empty-msg=$c2 section-exit=$c3 names-section=$c4"

# 39. One section contributing nothing must fail, and ordinary markdown drift must not hide a split.
#
# The emptiness checks were asymmetric: the section check asserted only that a `## 3. Tasks`
# heading had produced a KEY, which `setdefault` creates whether or not a task line parsed
# under it, and the zero-total check was GLOBAL. So one section could contribute an empty
# work-set while the other two kept the total non-zero, and the success line was reachable
# with the split still in the file. Reaching it needed nothing adversarial — bolding a task
# id, or an em dash instead of a colon, is ordinary drift in the file this guard watches.
r=$(templates_repo tpl-drift)

# Feature's Tasks heading is present and its only task line is bolded. Under the old
# TASK_LINE it parsed as nothing at all; the section still had a key, the global total was
# non-zero from Bug and Chore, and the guard printed its success line.
write_templates "$r" "- [ ] **T1:** write the failing test for <behavior>"
out=$(run_templates "$r"); err=$(cat "$TMP/terr")
[ "$out" = "1" ] && c1=ok || c1=no
case "$err" in *"write the failing test"*) c2=ok ;; *) c2=no ;; esac

# An em dash instead of the colon, and a numbered id instead of T1. Same shape, two more of
# the three forms the review demonstrated.
write_templates "$r" "- [ ] T1 — write the failing test for <behavior>"
out=$(run_templates "$r")
[ "$out" = "1" ] && c3=ok || c3=no
write_templates "$r" "- [ ] 1. write the failing test for <behavior>"
out=$(run_templates "$r")
[ "$out" = "1" ] && c4=ok || c4=no

# And a section that genuinely contributes no task lines, while the others do — the case the
# global total cannot see.
r=$(templates_repo tpl-onesection)
python3 - "$r" <<'PYEOF'
import pathlib, sys
doc = ("# t\n\n## Feature\n\n## 3. Tasks (TDD-ordered)\n\n"          # heading, no task lines
       "## Bug\n\n## 3. Tasks (TDD-ordered)\n"
       "- [ ] T1: regression test that fails for the right reason — then the fix\n\n"
       "## Chore\n\n## 3. Tasks (TDD-ordered)\n- [ ] T1: add tests for preserved behavior\n")
pathlib.Path(sys.argv[1], "skills", "spec", "templates.md").write_text(doc)
PYEOF
out=$(run_templates "$r"); err2=$(cat "$TMP/terr")
[ "$out" = "1" ] && c5=ok || c5=no
case "$err2" in *"Feature"*) c6=ok ;; *) c6=no ;; esac

# A purely red task line that merely CITES implement's file path must still be flagged. The
# green cue was a bare `implement`, which matches the substring inside `skills/implement/` —
# and the folded templates now reference that loop in a blockquote right above the task lines,
# so moving the reference onto a task line was one edit away from disarming this guard.
r=$(templates_repo tpl-cite)
write_templates "$r" "- [ ] T1: add a failing test, per skills/implement/SKILL.md"
out=$(run_templates "$r")
[ "$out" = "1" ] && c7=ok || c7=no

# Markup on the RED phrase itself must not hide the split. Stripping code spans and paths is
# what stops a path citation reading as green — but normalisation is not symmetric: stripping
# before the CLEARING pattern can only make the guard louder, while stripping before the
# ACCUSING one can only make it quieter. Applied to both, it traded a wide hole for two narrow
# ones. The second form needs no code span at all: `failing/regression test` is an ordinary way
# to write a task line for a template serving both a feature and a bug.
r=$(templates_repo tpl-redmarkup)
write_templates "$r" '- [ ] T1: write the `failing test` for <behavior>'
out=$(run_templates "$r")
[ "$out" = "1" ] && c8=ok || c8=no
write_templates "$r" "- [ ] T1: add the failing/regression test for <behavior>"
out=$(run_templates "$r")
[ "$out" = "1" ] && c9=ok || c9=no

[ "$c1$c2$c3$c4$c5$c6$c7$c8$c9" = "okokokokokokokokok" ] && report "markup on either side cannot hide a split" ok \
  || report "markup on either side cannot hide a split" no \
     "bold=$c1 names-line=$c2 emdash=$c3 numbered=$c4 empty-section=$c5 names-section=$c6 path-citation=$c7 backticked-red=$c8 slashed-red=$c9"

# --- hooks/steering-digest.sh: the flow it announces ---------------------------------
#
# 40. The digest names the per-issue chain, and keeps archive out of it.
#
# Every cold session reads this line, which makes it the one description of the flow that is
# guaranteed to be acted on rather than merely read. #30 folded the spec's own pull request
# away and this line went on announcing it until a human happened to notice — prose drifting
# where no case could see it, in the one hook whose whole job is to state facts.
#
# The negative half cannot stand alone: a digest that printed nothing at all would satisfy
# "no archive in the chain". Two positive assertions and a clean stderr corroborate it, so a
# run that checked nothing cannot report ok. See #16 for why that is written down.
r=$(anchor_repo dg-flow '- Owns: gates never fail open')
cp "$ROOT/hooks/steering-digest.sh" "$r/hooks/"
( cd "$r" && sh hooks/steering-digest.sh >"$TMP/dgout" 2>"$TMP/dgerr" )
flow=$(grep -F 'The flow is' "$TMP/dgout")
sweep=$(grep -F 'Archiving' "$TMP/dgout")
case "$flow" in *"spec -> clarify -> implement -> reviewer -> worklog"*) c1=ok ;; *) c1=no ;; esac
case "$flow" in *archive*) c2=no ;; *) c2=ok ;; esac
case "$sweep" in *"on request"*) c3=ok ;; *) c3=no ;; esac
[ -s "$TMP/dgerr" ] && c4=no || c4=ok
[ "$c1$c2$c3$c4" = "okokokok" ] && report "the digest names the chain and keeps archive out of it" ok \
  || report "the digest names the chain and keeps archive out of it" no \
     "chain=$c1 no-archive=$c2 sweep-on-request=$c3 clean-stderr=$c4"

# --- guards: scripts/check-markdown-fences.py ---------------------------------------
#
# #64. The no-hand-wrap convention carved out "fenced code", which states the exemption by
# DELIMITER when the property that decides it is CONTENT — so the skills that generate this
# repo's own documents kept emitting the wrapping the convention had just removed, and the
# rule read correctly put it back. The guard keys on the language tag instead. These cases
# pin it, because .steering/structure.md makes this file the project's whole notion of test
# coverage and a guard with no case here is a guard nothing checks.
#
# Unlike check-templates.py this guard finds its work-set with `git ls-files`, so a fixture
# has to be a real repository with the file committed — a loose file on disk is invisible to
# it, and a fixture the guard cannot see would pass every case by finding nothing.

# $1 = name. Returns a git repo with the guard installed and one Markdown file, whose content
# the caller writes next.
fences_repo() {
  r="$TMP/$1"; mkdir -p "$r/scripts"
  cp "$ROOT/scripts/check-markdown-fences.py" "$r/scripts/"
  chmod +x "$r/scripts/check-markdown-fences.py"
  ( cd "$r" && git init -q -b main && git config user.email t@t && git config user.name t ) >/dev/null 2>&1
  echo "$r"
}

# python3, not a shell heredoc: every fixture here is made of backticks, and escaping those
# through sh is how a fixture quietly stops being the shape it claims to be.
write_fenced() {
  python3 - "$1" "$2" <<'PYEOF'
import pathlib, sys
pathlib.Path(sys.argv[1], "doc.md").write_text(sys.argv[2])
PYEOF
  ( cd "$1" && git add -A ) >/dev/null 2>&1
}

run_fences() { ( cd "$1" && python3 scripts/check-markdown-fences.py >/dev/null 2>"$TMP/ferr"; printf '%s' "$?" ) }

# 41. A wrapped ```markdown fence fails, a clean one passes, and the language tag is what
# decides — an untagged fence holding the very same wrapped prose stays exempt.
#
# The reported name says "markdown-tagged" rather than showing the fence: `report` takes a
# double-quoted string, so a backtick in one is command substitution, and the first version of
# this case ran `markdown` as a command and failed on a label while every assertion passed.
#
# The control runs FIRST. A guard that failed on every input satisfies the accusing half of
# this case by itself, and "flags the thing we broke" is not evidence until "passes the thing
# we did not" stands beside it.
#
# The sibling-placeholder assertion is the other half of the same argument, and it is the one
# that separates this guard from the transform it replaces: skills/contract/SKILL.md:47-48 is
# two separate instructions, one per line, and .specs/61-.../unwrap.py folds them into one.
# A guard that asked "would the transform join this?" would false-accuse a shipped file. If
# that assertion ever goes green-by-deletion, the guard has learned "looks like prose".
r=$(fences_repo mdf-basic)
write_fenced "$r" '```markdown
- Ordered, not prioritized. Position reflects value, risk, cost, and dependency together.
```
'
out=$(run_fences "$r"); [ "$out" = "0" ] && c0=ok || c0=no

write_fenced "$r" '```markdown
- Ordered, not prioritized. Position reflects value, risk, cost, and dependency
  together. There is no separate priority field.
```
'
out=$(run_fences "$r"); err=$(cat "$TMP/ferr")
[ "$out" = "1" ] && c1=ok || c1=no
case "$err" in *"doc.md"*) c2=ok ;; *) c2=no ;; esac
case "$err" in *":3"*) c3=ok ;; *) c3=no ;; esac   # the continuation line, not the fence

# The same wrapped prose, untagged. This is implement's receipt block and the reviewer
# contract's [SEVERITY] format: a line break there is meaningful, and unwrapping one would
# destroy a format. A tagged fence must be needed for the guard to look at all.
write_fenced "$r" '```
- Ordered, not prioritized. Position reflects value, risk, cost, and dependency
  together. There is no separate priority field.
```

```markdown
- a clean item
```
'
out=$(run_fences "$r"); [ "$out" = "0" ] && c4=ok || c4=no

# Two sibling placeholder lines: NOT a hand wrap, and the counter-example #64 was filed
# without. Both open a template slot, so neither is a continuation.
write_fenced "$r" '```markdown
## Style
<what the formatter owns — say "the formatter decides" rather than restating it>
<what it does not own: naming, file organisation, module boundaries>
```
'
out=$(run_fences "$r"); [ "$out" = "0" ] && c5=ok || c5=no

[ "$c0$c1$c2$c3$c4$c5" = "okokokokokok" ] && report "a wrapped markdown-tagged fence fails, a clean one passes, an untagged one is exempt" ok \
  || report "a wrapped markdown-tagged fence fails, a clean one passes, an untagged one is exempt" no \
     "clean-passes=$c0 wrapped-fails=$c1 names-file=$c2 names-line=$c3 untagged-exempt=$c4 siblings-not-accused=$c5"

# 42. An empty work-set must fail, and a fence the guard cannot classify must fail rather
# than be guessed at.
#
# Both are #16 in this guard. Zero fences read is not zero defects found — that is the exact
# sentence #61's own verifier shipped, exiting 0 on a ref that did not resolve after having
# compared nothing. And a nested or unclosed fence makes a body's structure a guess; a guard
# that guesses is a guard that fails open on the input it guessed wrong about.
r=$(fences_repo mdf-closed)
write_fenced "$r" '# A document with no markdown-tagged fence at all

```python
x = 1
```
'
out=$(run_fences "$r"); err=$(cat "$TMP/ferr")
[ "$out" = "1" ] && c1=ok || c1=no
case "$err" in *"read nothing"*) c2=ok ;; *) c2=no ;; esac

write_fenced "$r" '```markdown
- an item
```python
x = 1
```
```
'
out=$(run_fences "$r"); err=$(cat "$TMP/ferr")
[ "$out" = "1" ] && c3=ok || c3=no
case "$err" in *"cannot be determined"*) c4=ok ;; *) c4=no ;; esac

write_fenced "$r" '```markdown
- an item that never closes its fence
'
out=$(run_fences "$r"); err=$(cat "$TMP/ferr")
[ "$out" = "1" ] && c5=ok || c5=no
case "$err" in *"never closed"*) c6=ok ;; *) c6=no ;; esac

# The self-test must be able to FAIL, or it is decoration. Break the rule that makes a
# placeholder line open a slot, and the sibling-placeholder fixture must start false-accusing.
r=$(fences_repo mdf-selftest)
write_fenced "$r" '```markdown
- a clean item
```
'
python3 - "$r" <<'PYEOF'
import pathlib, sys
p = pathlib.Path(sys.argv[1], "scripts", "check-markdown-fences.py")
t = p.read_text()
p.write_text(t.replace('r"|<"                      # a template placeholder', 'r"|<<<NEVER>>>"          # a template placeholder'))
PYEOF
out=$(run_fences "$r"); err=$(cat "$TMP/ferr")
[ "$out" = "1" ] && c7=ok || c7=no
case "$err" in *"SELFTEST FAILED"*) c8=ok ;; *) c8=no ;; esac

# A markdown fence quoted inside a LONGER untagged fence. Four backticks is the canonical
# CommonMark way to quote a fence, so this is the shape documentation naturally takes. The
# first version skipped it in silence: the inner line failed the close test (3 >= 4 is false)
# and failed the raise test (the OUTER tag was not markdown), so it was appended to the body
# as inert text and the fence was never scanned. A clean fence sits alongside it deliberately
# — the empty-work-set guard cannot catch this, because the other fence keeps the count above
# zero. The doctrine was being applied asymmetrically: refuse to guess when it can see in,
# guess "skip" when it cannot.
#
# Its OWN repo, and a diagnosis-specific assertion. The first version of this reused $r from
# the sabotaged-self-test fixture above, so the guard exited 1 for the wrong reason and a
# `*markdown*` stderr match was satisfied by the string "check-markdown-fences SELFTEST
# FAILED". It reported ok against a guard that still had the hole.
r=$(fences_repo mdf-quoted)
write_fenced "$r" '````
```markdown
- Ordered, not prioritized. Position reflects value
  together. There is no separate priority field.
```
````

```markdown
- a clean item
```
'
out=$(run_fences "$r"); err=$(cat "$TMP/ferr")
[ "$out" = "1" ] && c9=ok || c9=no
case "$err" in *"one of the two is Markdown-tagged"*) c10=ok ;; *) c10=no ;; esac

# ...and the SAME fixture, against a guard whose nested-fence rule has been reverted to the
# holed version that only looked at the outer fence's tag. The scan-coverage invariant is a
# backstop for exactly this: a nesting shape the parse rules do not recognise. Every shape
# reachable today trips a parse rule first, so the invariant has no natural fixture — sabotage
# is the only way to reach it, and an unreachable backstop is one nobody knows is broken.
# The self-test still passes under this sabotage (its nested fixture has a Markdown-tagged
# OUTER fence), so a failure here is the invariant firing and not the self-test.
r2=$(fences_repo mdf-invariant)
write_fenced "$r2" '````
```markdown
- Ordered, not prioritized. Position reflects value
  together. There is no separate priority field.
```
````

```markdown
- a clean item
```
'
python3 - "$r2" <<'PYEOF'
import pathlib, sys
p = pathlib.Path(sys.argv[1], "scripts", "check-markdown-fences.py")
t = p.read_text()
p.write_text(t.replace(
    "if c and (tag in MARKDOWN_TAGS or c.group(3).lower() in MARKDOWN_TAGS):",
    "if c and tag in MARKDOWN_TAGS:"))
PYEOF
out=$(run_fences "$r2"); err=$(cat "$TMP/ferr")
[ "$out" = "1" ] && c13=ok || c13=no
case "$err" in *"quoted inside another fence"*) c14=ok ;; *) c14=no ;; esac
case "$err" in *"SELFTEST FAILED"*) c15=no ;; *) c15=ok ;; esac   # must be the invariant, not the self-test

# A file that exists but cannot be read. Existence is not readability, and the spec's Design
# promises this as one of three fail-closed ways. The suite already pins the same path for
# check-templates.py, the reviewer directory, and a steering file.
r=$(fences_repo mdf-unreadable)
write_fenced "$r" '```markdown
- a clean item
```
'
chmod 000 "$r/doc.md" 2>/dev/null
# Skipped where chmod does not actually deny access (root, or a filesystem without POSIX
# permissions). A case that cannot fail is worse than no case.
if cat "$r/doc.md" >/dev/null 2>&1; then
  chmod 644 "$r/doc.md" 2>/dev/null
  c11=ok; c12=ok
else
  out=$(run_fences "$r"); err=$(cat "$TMP/ferr")
  chmod 644 "$r/doc.md" 2>/dev/null
  [ "$out" = "1" ] && c11=ok || c11=no
  case "$err" in *"cannot be read"*) c12=ok ;; *) c12=no ;; esac
fi

[ "$c1$c2$c3$c4$c5$c6$c7$c8$c9$c10$c11$c12$c13$c14$c15" = "okokokokokokokokokokokokokokok" ] && report "an empty work-set, an unclassifiable fence and a broken self-test all fail" ok \
  || report "an empty work-set, an unclassifiable fence and a broken self-test all fail" no \
     "empty-exit=$c1 empty-msg=$c2 nested-exit=$c3 nested-msg=$c4 unclosed-exit=$c5 unclosed-msg=$c6 selftest-exit=$c7 selftest-msg=$c8 quoted-exit=$c9 quoted-msg=$c10 unreadable-exit=$c11 unreadable-msg=$c12 invariant-exit=$c13 invariant-msg=$c14 invariant-not-selftest=$c15"


printf '\ntest-gates: %d passed, %d failed\n' "$pass" "$fail"
[ "$fail" -eq 0 ] || exit 1
