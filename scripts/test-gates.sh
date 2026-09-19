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

# A half that could not run is not a half that passed.
#
# Several cases below self-disable when the environment cannot produce the state they need —
# `chmod 000` under root is the live one, and skipping beats a case that silently cannot fail.
# But those branches then set their variable to `ok`, the aggregate matches, and `report` prints
# the same line it prints for a real pass: G-1 one layer out, in the suite that exists to
# enforce G-1. Under root — any container-based CI step — four halves of case 69 stop testing
# anything and the output is identical. So the skip is spoken, and the count is printed at the
# end beside the passes.
#
# THIRTEEN sites. The first cut converted ten and said seven; the recount that caught that said
# twelve and nine, in the paragraph whose subject is not counting. Two of the three the first
# cut missed were worse than any half: they called `report ... ok` on the skip path,
# manufacturing a pass and incrementing the counter. Those two are whole cases and now report
# nothing at all, which is why the summary says `skipped` rather than `half-case(s) skipped`.
#
# How to get thirteen, since two recounts did not: count the GUARDS, not the `chmod 000` lines.
# There are twelve of those and ELEVEN guards among them, because case 14 (the unguarded
# `chmod 000` at :209) has no self-disabling branch — under root it goes red rather than
# skipping, which is the safe direction and deliberately left alone; do not "fix" that
# asymmetry. The last two guards are not permission-based at all: `bootstrap/symlinked-slug`
# and `bootstrap/dangling-symlink` self-disable when `ln -s` fails. 11 + 2 = 13.
skipped=0
note_skip() { skipped=$((skipped+1)); printf '  skip %s — %s\n' "$1" "$2"; }

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
  note_skip "locks/unreadable-reviewer-dir" "permissions not enforced here (running as root?)"
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
# THREE older uses of that glob remain, at :372, :384 and :436. They are safe, but not for the
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

# 29b. `- Target:` joins the anchors, because it is read with the same exact expression.
#
# #141 AC10. The table is hand-maintained, so a new machine-read line that is not added to it
# is unguarded: `- **Target: full**` yields nothing, `check-document-set.py` sees no target and
# falls back to the generic wording, and the operator's answer is silently discarded. That is
# #34 exactly, reached through the line added to prevent a different silent discard.
r=$(anchor_repo anc-tgt-bold '- Owns: x')
printf -- '- **Target: full**\n' >> "$r/.steering/tech.md"
out=$(run_anchors "$r"); err=$(cat "$TMP/aerr" 2>/dev/null)
[ "$out" = "1" ] && c1=ok || c1=no
case "$err" in *"Target"*) c2=ok ;; *) c2=no ;; esac
case "$err" in *"tech.md"*) c3=ok ;; *) c3=no ;; esac

# Correctly written passes — otherwise "bolded fails" is satisfiable by a row that rejects the
# key outright, and every project writing the line properly would be blocked by it.
r=$(anchor_repo anc-tgt-ok '- Owns: x')
printf -- '- Target: full\n' >> "$r/.steering/tech.md"
out=$(run_anchors "$r"); [ "$out" = "0" ] && c4=ok || c4=no

# Absent stays legitimate. The line is optional by design — it is meaningless outside the
# bootstrap window — and a guard that demanded it would fire on every settled project.
r=$(anchor_repo anc-tgt-absent '- Owns: x')
out=$(run_anchors "$r"); [ "$out" = "0" ] && c5=ok || c5=no

[ "$c1$c2$c3$c4$c5" = "okokokokok" ] \
  && report "a bolded Target fails the anchor guard, a plain one passes, an absent one is silent" ok \
  || report "a bolded Target fails the anchor guard, a plain one passes, an absent one is silent" no \
     "bold-red=$c1 names-key=$c2 names-file=$c3 plain-green=$c4 absent-green=$c5"

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
  note_skip "anchors/unreadable-product-md" "permissions not enforced here (running as root?)"
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
  # The five reviewers, because #105 made the guard read them too: a field the contract
  # requires has to have a command on every reviewer's allow-list that can produce it. They
  # are copied for EVERY receipt fixture, not only the cases below, so that case 34's control
  # keeps exercising the whole guard rather than an early exit on a missing reviewer.
  mkdir -p "$r/agents/_template" "$r/.claude/agents"
  for rv in ts-reviewer python-reviewer dart-flutter-reviewer; do
    cp "$ROOT/agents/$rv.md" "$r/agents/"
  done
  cp "$ROOT/agents/_template/reviewer.md" "$r/agents/_template/"
  cp "$ROOT/.claude/agents/gate-sdd-reviewer.md" "$r/.claude/agents/"
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
  # "Traceback", which no crash can satisfy. That pairing is this file's own rule at :506-509.
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
# file records at :664-668, so the comment named the failure mode while the check did not
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
  note_skip "templates/unreadable-templates-md" "permissions not enforced here (running as root?)"
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
new = t.replace('r"|<"                      # a template placeholder', 'r"|<<<NEVER>>>"          # a template placeholder')
if new == t:
    raise SystemExit("sabotage matched nothing; this case would run an unmodified guard")
p.write_text(new)
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
new = t.replace(
    "if c and (tag in MARKDOWN_TAGS or c.group(3).lower() in MARKDOWN_TAGS):",
    "if c and tag in MARKDOWN_TAGS:")
if new == t:
    raise SystemExit("sabotage matched nothing; this case would run an unmodified guard")
p.write_text(new)
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
  note_skip "fences/unreadable-doc" "permissions not enforced here (running as root?)"
else
  out=$(run_fences "$r"); err=$(cat "$TMP/ferr")
  chmod 644 "$r/doc.md" 2>/dev/null
  [ "$out" = "1" ] && c11=ok || c11=no
  case "$err" in *"cannot be read"*) c12=ok ;; *) c12=no ;; esac
fi

[ "$c1$c2$c3$c4$c5$c6$c7$c8$c9$c10$c11$c12$c13$c14$c15" = "okokokokokokokokokokokokokokok" ] && report "an empty work-set, an unclassifiable fence and a broken self-test all fail" ok \
  || report "an empty work-set, an unclassifiable fence and a broken self-test all fail" no \
     "empty-exit=$c1 empty-msg=$c2 nested-exit=$c3 nested-msg=$c4 unclosed-exit=$c5 unclosed-msg=$c6 selftest-exit=$c7 selftest-msg=$c8 quoted-exit=$c9 quoted-msg=$c10 unreadable-exit=$c11 unreadable-msg=$c12 invariant-exit=$c13 invariant-msg=$c14 invariant-not-selftest=$c15"


# 43. A reviewer that cannot produce a field the contract requires must fail.
#
# #105. `reviewed_at` is the only receipt field whose value comes from outside both the diff
# and the reviewer's own run, and no allow-list named a clock — so the contract required a
# field every reviewer was simultaneously forbidden to produce. Each one resolved that on its
# own: `date` run off-list and disclosed, a time taken from context, a placeholder.
#
# The check is a PAIRING, so both halves are pinned here. A guard that only looked for the
# clock would go green the day `reviewed_at` left the contract, still demanding a command
# nothing needed; one that only read the contract would never have caught this.
r=$(receipt_repo receipt-clock)

# Control first, as case 34 does and for the same reason: without it a case that fails because
# the fixture is broken reads as a caught bug. The unmutated tree is the FIXED tree, so this
# also pins that all five reviewers really do carry the clock.
ctl=$( cd "$r" && python3 scripts/check-receipt-schema.py 2>/dev/null; echo "exit=$?" )
case "$ctl" in *"exit=0"*) c1=ok ;; *) c1=no ;; esac

# Strip the clock from ONE reviewer, the way the tree looked before this fix. python3 rather
# than sed -i, which is not portable, and it exits non-zero when its needle is gone so that a
# reworded allow-list cannot no-op the mutation and leave this case green against a guard that
# was never tested.
python3 - "$r" <<'PYEOF'
import pathlib, sys
p = pathlib.Path(sys.argv[1], "agents", "python-reviewer.md")
src = p.read_text()
kept = [ln for ln in src.splitlines(keepends=True) if "date -u" not in ln]
if len(kept) == len(src.splitlines(keepends=True)):
    sys.exit(3)
p.write_text("".join(kept))
PYEOF
built=$?

if [ "$built" -ne 0 ]; then
  report "a reviewer that cannot produce a required receipt field fails" no \
    "fixture could not be built: the clock line this case removes was not found"
else
  out=$( cd "$r" && python3 scripts/check-receipt-schema.py >/dev/null 2>"$TMP/cerr"; printf '%s' "$?" )
  cerr=$(cat "$TMP/cerr" 2>/dev/null)
  [ "$out" = "1" ] && c2=ok || c2=no
  # Exit 1 is also what a traceback returns, so the code alone is not the check — this file's
  # rule at :506-509. The path is required because a finding that does not say WHICH reviewer
  # is unactionable across five of them, and the phrase unique to this branch is required
  # because two sibling branches of the same guard also exit 1 naming a path.
  case "$cerr" in *Traceback*) c3=no ;; *) c3=ok ;; esac
  case "$cerr" in *"agents/python-reviewer.md"*) c4=ok ;; *) c4=no ;; esac
  case "$cerr" in *"names no clock"*) c5=ok ;; *) c5=no ;; esac
  [ "$c1$c2$c3$c4$c5" = "okokokokok" ] \
    && report "a reviewer that cannot produce a required receipt field fails" ok \
    || report "a reviewer that cannot produce a required receipt field fails" no \
       "control=$c1 exit=$c2 no-traceback=$c3 names-file=$c4 names-reason=$c5"
fi

# 44. The other half of the pairing: no requirement, no demand.
#
# A required field and its producer are one fact. Dropping `reviewed_at` from the contract
# must stop the guard asking for a clock, or the check becomes a rule of its own that outlives
# the reason it exists — which is how a guard earns the reputation that gets it switched off.
r=$(receipt_repo receipt-clock-unrequired)
python3 - "$r" <<'PYEOF'
import pathlib, sys
paths = [
    ("agents", "_shared", "reviewer-contract.md"),
    (".claude", "agents", "_shared", "reviewer-contract.md"),
    ("skills", "implement", "SKILL.md"),
]
for parts in paths:
    p = pathlib.Path(sys.argv[1], *parts)
    src = p.read_text()
    kept = [ln for ln in src.splitlines(keepends=True) if not ln.lstrip().startswith("reviewed_at=")]
    if len(kept) == len(src.splitlines(keepends=True)):
        sys.exit(3)
    p.write_text("".join(kept))
# and the clock goes too, so the tree is consistent: nothing requires it, nothing offers it.
for rv in ("agents/ts-reviewer.md", "agents/python-reviewer.md", "agents/dart-flutter-reviewer.md",
           "agents/_template/reviewer.md", ".claude/agents/gate-sdd-reviewer.md"):
    p = pathlib.Path(sys.argv[1], rv)
    p.write_text("".join(ln for ln in p.read_text().splitlines(keepends=True) if "date -u" not in ln))
PYEOF
built=$?
if [ "$built" -ne 0 ]; then
  report "a contract that stops requiring the field stops demanding the clock" no \
    "fixture could not be built: the reviewed_at line this case removes was not found"
else
  out=$( cd "$r" && python3 scripts/check-receipt-schema.py >/dev/null 2>"$TMP/uerr"; printf '%s' "$?" )
  [ "$out" = "0" ] && c1=ok || c1=no
  [ "$c1" = "ok" ] \
    && report "a contract that stops requiring the field stops demanding the clock" ok \
    || report "a contract that stops requiring the field stops demanding the clock" no \
       "exit=$out stderr=$(cat "$TMP/uerr" 2>/dev/null | head -2 | tr '\n' ' ')"
fi


# 45. The clock check survives having assertions stripped.
#
# #28 is why this is behavioural rather than left to case 35. That case greps for `assert` at
# statement position, which is a check on the SHAPE of the source and can be walked around —
# `if __debug__:` is not an assert and is deleted by exactly the same flag. #105's check is
# the newest safety check in this guard and therefore the one most likely to be written that
# way by someone who did not read #28, so it is pinned by running it stripped.
r=$(receipt_repo receipt-clock-stripped)
python3 - "$r" <<'PYEOF'
import pathlib, sys
p = pathlib.Path(sys.argv[1], "agents", "dart-flutter-reviewer.md")
src = p.read_text()
kept = [ln for ln in src.splitlines(keepends=True) if "date -u" not in ln]
if len(kept) == len(src.splitlines(keepends=True)):
    sys.exit(3)
p.write_text("".join(kept))
PYEOF
built=$?

if [ "$built" -ne 0 ]; then
  report "the clock check still fires with assertions stripped" no \
    "fixture could not be built: the clock line this case removes was not found"
else
  # Same pairing of requirements as case 34, and for the same reason: exit 1 is also what a
  # traceback returns, so the code alone cannot tell a working check from a crashing one.
  clock_fails() { # clock_fails <exit-code> <stderr-file> -> ok|no
    [ "$1" = "1" ] || { echo no; return; }
    serr=$(cat "$2" 2>/dev/null)
    case "$serr" in *Traceback*) echo no; return ;; esac
    case "$serr" in *"agents/dart-flutter-reviewer.md"*) : ;; *) echo no; return ;; esac
    case "$serr" in *"names no clock"*) echo ok ;; *) echo no ;; esac
  }
  out=$( cd "$r" && python3 -O scripts/check-receipt-schema.py >/dev/null 2>"$TMP/serr"; printf '%s' "$?" )
  c1=$(clock_fails "$out" "$TMP/serr")
  # No flag, through the shebang — how PYTHONOPTIMIZE arrives without any caller choosing it.
  out2=$( cd "$r" && PYTHONOPTIMIZE=1 ./scripts/check-receipt-schema.py >/dev/null 2>"$TMP/serr2"; printf '%s' "$?" )
  c2=$(clock_fails "$out2" "$TMP/serr2")
  [ "$c1$c2" = "okok" ] \
    && report "the clock check still fires with assertions stripped" ok \
    || report "the clock check still fires with assertions stripped" no "minus-O=$c1 PYTHONOPTIMIZE=$c2"
fi


# 46, 47, 48. The three hard-exit branches of the #105 pairing check.
#
# Cases 43-45 pin the branch that COLLECTS failures. These pin the three that exit on the
# spot, and they are here because a guard's fail-closed paths are exactly the ones nobody
# exercises by accident — case 7 passed for three releases while the gate did nothing.
#
# 48 carries the most weight of the three. The spec's claim that this is a class fix rather
# than an instance fix rests entirely on it: a field added to the contract with no producer
# entry must fail HERE, rather than reaching a reviewer that cannot produce it, which is the
# omission #105 itself was.
clock_branch_fails() { # clock_branch_fails <exit> <stderr-file> <needle> -> ok|no
  [ "$1" = "1" ] || { echo no; return; }
  serr=$(cat "$2" 2>/dev/null)
  case "$serr" in *Traceback*) echo no; return ;; esac
  case "$serr" in *"$3"*) echo ok ;; *) echo no ;; esac
}

# 46. A reviewer named in REVIEWERS but absent from disk.
# Not a skip: scripts/ never ships, so this only ever runs where all five exist. A named
# reviewer that is not there is a rename nobody finished.
r=$(receipt_repo receipt-reviewer-gone)
rm -f "$r/agents/ts-reviewer.md"
out=$( cd "$r" && python3 scripts/check-receipt-schema.py >/dev/null 2>"$TMP/gerr"; printf '%s' "$?" )
c1=$(clock_branch_fails "$out" "$TMP/gerr" "is listed in REVIEWERS but is missing")
c2=$(clock_branch_fails "$out" "$TMP/gerr" "agents/ts-reviewer.md")
[ "$c1$c2" = "okok" ] && report "a reviewer listed but missing from disk fails" ok \
  || report "a reviewer listed but missing from disk fails" no "reason=$c1 names-file=$c2"

# 47. A reviewer whose Bash policy section has been renamed out from under the guard.
# The section match is exact after strip().lower(), so a renamed heading is indistinguishable
# from an absent one — and both must fail closed. A reviewer with no allow-list is not a
# narrower reviewer, it is an unscoped one.
r=$(receipt_repo receipt-policy-renamed)
python3 - "$r" <<'PYEOF'
import pathlib, sys
p = pathlib.Path(sys.argv[1], "agents", "python-reviewer.md")
src = p.read_text()
if "## Bash policy\n" not in src:
    sys.exit(3)
p.write_text(src.replace("## Bash policy\n", "## Bash policy notes\n", 1))
PYEOF
if [ $? -ne 0 ]; then
  report "a reviewer whose Bash policy heading was renamed fails" no \
    "fixture could not be built: the heading this case renames was not found"
else
  out=$( cd "$r" && python3 scripts/check-receipt-schema.py >/dev/null 2>"$TMP/herr"; printf '%s' "$?" )
  c1=$(clock_branch_fails "$out" "$TMP/herr" "has no '## Bash policy' section")
  c2=$(clock_branch_fails "$out" "$TMP/herr" "agents/python-reviewer.md")
  [ "$c1$c2" = "okok" ] && report "a reviewer whose Bash policy heading was renamed fails" ok \
    || report "a reviewer whose Bash policy heading was renamed fails" no "reason=$c1 names-file=$c2"
fi

# 48. A receipt field with no entry in PRODUCERS.
# The completeness half of the pairing, and the one the "cannot recur" claim rests on. The
# field is added to all three schema copies at once, because a field added to one copy alone
# is caught by the older drift check and would never reach this branch.
r=$(receipt_repo receipt-field-unmapped)
python3 - "$r" <<'PYEOF'
import pathlib, sys
for parts in (("agents", "_shared", "reviewer-contract.md"),
              (".claude", "agents", "_shared", "reviewer-contract.md"),
              ("skills", "implement", "SKILL.md")):
    p = pathlib.Path(sys.argv[1], *parts)
    src = p.read_text()
    needle = "reviewed_by=subagent|inline\n"
    if needle not in src:
        sys.exit(3)
    p.write_text(src.replace(needle, needle + "reviewed_model=<the model that reviewed>\n", 1))
PYEOF
if [ $? -ne 0 ]; then
  report "a receipt field with no producer entry fails" no \
    "fixture could not be built: the reviewed_by line this case appends after was not found"
else
  out=$( cd "$r" && python3 scripts/check-receipt-schema.py >/dev/null 2>"$TMP/uerr3"; printf '%s' "$?" )
  c1=$(clock_branch_fails "$out" "$TMP/uerr3" "has no entry in PRODUCERS")
  c2=$(clock_branch_fails "$out" "$TMP/uerr3" "reviewed_model")
  [ "$c1$c2" = "okok" ] && report "a receipt field with no producer entry fails" ok \
    || report "a receipt field with no producer entry fails" no "reason=$c1 names-field=$c2"
fi


# 49. An emptied REVIEWERS must fail rather than report success.
#
# #16's shape, in the work-set #105 added. This file already guards its other hard-coded
# work-set — `if len(SOURCES) < 2` at check-receipt-schema.py, with a comment citing #16 —
# and the new tuple arrived without the equivalent. Emptying it makes the loop run zero times,
# leaves the failure list empty, and prints a success line naming zero reviewers.
#
# The success line is checked as well as the exit code, because "0 reviewer(s) can produce"
# is the sentence a reader would have skimmed past. A guard is allowed to check nothing only
# when it says so loudly enough that nobody mistakes it for a pass.
r=$(receipt_repo receipt-no-reviewers)
python3 - "$r" <<'PYEOF'
import pathlib, re, sys
p = pathlib.Path(sys.argv[1], "scripts", "check-receipt-schema.py")
src = p.read_text()
new, n = re.subn(r"REVIEWERS = \(\n(?:    \"[^\"]+\",\n)+\)", "REVIEWERS = ()", src, count=1)
if n != 1:
    sys.exit(3)
p.write_text(new)
PYEOF
if [ $? -ne 0 ]; then
  report "an emptied REVIEWERS must not report success" no \
    "fixture could not be built: the REVIEWERS tuple this case empties was not found"
else
  out=$( cd "$r" && python3 scripts/check-receipt-schema.py >"$TMP/nout" 2>"$TMP/nerr"; printf '%s' "$?" )
  [ "$out" = "1" ] && c1=ok || c1=no
  case "$(cat "$TMP/nerr" 2>/dev/null)" in *Traceback*) c2=no ;; *) c2=ok ;; esac
  case "$(cat "$TMP/nerr" 2>/dev/null)" in *"below its floor"*) c3=ok ;; *) c3=no ;; esac
  # The success line must not have been printed at all.
  case "$(cat "$TMP/nout" 2>/dev/null)" in *"reviewer(s) can produce"*) c4=no ;; *) c4=ok ;; esac
  [ "$c1$c2$c3$c4" = "okokokok" ] && report "an emptied REVIEWERS must not report success" ok \
    || report "an emptied REVIEWERS must not report success" no \
       "exit=$c1 no-traceback=$c2 says-empty=$c3 no-success-line=$c4"
fi


# 50. A producer LEAVING an allow-list must fail, not only a field arriving without one.
#
# The other half of #105's recurrence claim. Case 48 catches a new field with no producer;
# nothing caught an existing field's producer being deleted from a reviewer, which is #105's
# own mechanism running the other way. `reviewed_sha` is the second field with a command
# behind it, so it is the one that shows the gap.
r=$(receipt_repo receipt-sha-producer-gone)
python3 - "$r" <<'PYEOF'
import pathlib, sys
p = pathlib.Path(sys.argv[1], "agents", "ts-reviewer.md")
src = p.read_text()
# The precondition is the replacement TARGET, not a substring of it. Checking only
# "git rev-parse HEAD" would still pass if the bullet were reordered, leaving the replace a
# no-op and this case failing through the wrong diagnosis — cases 47-49 all check the exact
# string they mutate, and 50 was the odd one out.
target = "`git log --oneline <base>...HEAD`, `git rev-parse HEAD`"
if target not in src:
    sys.exit(3)
p.write_text(src.replace(target, "`git log --oneline <base>...HEAD`", 1))
PYEOF
if [ $? -ne 0 ]; then
  report "a producer deleted from an allow-list fails" no \
    "fixture could not be built: the git rev-parse bullet this case removes was not found"
else
  out=$( cd "$r" && python3 scripts/check-receipt-schema.py >/dev/null 2>"$TMP/perr"; printf '%s' "$?" )
  c1=$(clock_branch_fails "$out" "$TMP/perr" "agents/ts-reviewer.md")
  c2=$(clock_branch_fails "$out" "$TMP/perr" "reviewed_sha")
  [ "$c1$c2" = "okok" ] && report "a producer deleted from an allow-list fails" ok \
    || report "a producer deleted from an allow-list fails" no "names-file=$c1 names-field=$c2"
fi


# --- guards: check-templates.py's live-spec scan -----------------------------------
#
# #113. review-gate.sh arms on zero open tasks, which stands in for "implementation is
# finished". A task deliberately sequenced after the review holds one box unticked for the
# whole review window, so the gate stays silent during exactly the stretch it exists to
# cover — and .steering/tech.md used to tell authors to write one. The fix is definitional:
# no task is sequenced after the review. This is the half that checks a live spec obeys it.
#
# The hard part is not catching #105's T5. It is catching it WITHOUT flagging the spec that
# introduces the guard, whose own tasks necessarily describe deferral while not being
# deferred. The distinction is positional: a task announces its schedule in its DIRECTIVE,
# the text before its first clause break. What follows describes the work, not its timing.

specs_repo() {
  r="$TMP/$1"; mkdir -p "$r/scripts" "$r/skills/spec" "$r/.specs"
  cp "$ROOT/scripts/check-templates.py" "$r/scripts/"
  chmod +x "$r/scripts/check-templates.py"
  # A valid templates.md, so any failure below comes from the spec scan and not from the
  # check this guard already performed.
  write_templates "$r" "- [ ] T1: failing test for <behavior> — then the implementation that makes it pass"
  echo "$r"
}

# $1 = repo, $2 = directory under .specs (may be nested, e.g. _archive/105-x), $3 = a task
# line, $4 = a second task line (optional).
write_spec() {
  d="$1/.specs/$2"; mkdir -p "$d"
  { printf '# Spec: x\n- Slug: %s   Status: approved\n\n## 1. Requirements\n' "$2"
    printf -- '- [ ] **AC1:** an acceptance criterion, deliberately left unticked.\n\n'
    printf '## 3. Tasks (TDD-ordered)\n%s\n' "$3"
    [ $# -lt 4 ] || printf '%s\n' "$4"
  } > "$d/spec.md"
}

# 51. A deferred task fails in every phrasing this project writes; a task that merely
# DESCRIBES deferral passes.
#
# The control runs first, as in case 36: "flags the thing we broke" is not evidence unless
# "passes the thing we did not" stands beside it.
#
# The pre-fix red, argued rather than assumed: before check-templates.py grew a second
# subject it read only skills/spec/templates.md, so every fixture below exited 0 with the
# deferred task sitting in .specs/ unexamined. The accusing halves of this case therefore
# failed for the stated reason and not for a setup error.
#
# Four accusing fixtures, not one, because the SEPARATOR and the POSITION both varied in
# review and each variation escaped:
#   T5: **after ...** — bump      the id ends in a colon, deferral in the directive
#   T5 — after ..., bump          the id ends in a DASH, which the prefix used to leave
#                                 behind, collapsing the directive to the bare id "T5"
#   **T5** — after ..., bump      the same, with the id bolded
#   T5: bump ... — after ...      the mirror: deferral in the TAIL, not the directive
# The last two are not contrived. #105's real T5 is the first form, and the mirror is a coin
# flip away from it in phrasing.
#
# The third fixture is this spec's own T1 and T3, verbatim. They are the adversarial case
# and no invented line is a substitute — both contain a deferral phrase, both are ordinary
# pre-review tasks, and a guard that flags them would have been tuned until its own spec
# passed, which is the failure this case exists to make impossible.
r=$(specs_repo spec-clean)
write_spec "$r" "9-feature" "- [ ] T1: failing test for the thing — then the implementation that passes it"
out=$(run_templates "$r")
[ "$out" = "0" ] && c0=ok || c0=no

# $1 = fixture name, $2 = the offending task line. Echoes ok when the guard failed.
deferred_fails() {
  rr=$(specs_repo "$1")
  write_spec "$rr" "9-feature" "- [ ] T1: failing test for the thing — then the implementation that passes it" "$2"
  [ "$(run_templates "$rr")" = "1" ] && echo ok || echo no
}

r=$(specs_repo spec-deferred)
write_spec "$r" "9-feature" "- [ ] T1: failing test for the thing — then the implementation that passes it" \
  "- [x] T5: **after the reviewer gate is CLEAN** — bump both manifests to 0.4.4."
out=$(run_templates "$r"); err=$(cat "$TMP/terr")
[ "$out" = "1" ] && c1=ok || c1=no
case "$err" in *".specs/9-feature/spec.md"*) c2=ok ;; *) c2=no ;; esac
case "$err" in *"after the reviewer gate is CLEAN"*) c3=ok ;; *) c3=no ;; esac

c5=$(deferred_fails spec-dash-id "- [ ] T5 — after the reviewer gate is CLEAN, bump both manifests.")
c6=$(deferred_fails spec-bold-id "- [ ] **T5** — after the review, bump both manifests.")
c7=$(deferred_fails spec-mirror "- [x] T5: bump both manifests to 0.4.4 — after the reviewer gate is CLEAN")

r=$(specs_repo spec-describes)
write_spec "$r" "113-post-review-task-disarms-the-gate" \
  "- [ ] T1: cases in \`scripts/test-gates.sh\` — a live spec whose Tasks section names post-review work fails \`check-templates.py\` with the spec named; a clean spec passes. (AC4, AC5)" \
  "- [ ] T3: the definition — \`skills/spec/templates.md\` states that no task is sequenced after the review. (AC1)"
out=$(run_templates "$r"); derr=$(cat "$TMP/terr")
[ "$out" = "0" ] && c4=ok || c4=no

[ "$c0$c1$c2$c3$c4$c5$c6$c7" = "okokokokokokokok" ] && report "a deferred task fails in every phrasing, a task describing deferral passes" ok \
  || report "a deferred task fails in every phrasing, a task describing deferral passes" no \
     "clean-passes=$c0 deferred-fails=$c1 names-spec=$c2 names-line=$c3 describing-passes=$c4 dash-id=$c5 bold-id=$c6 mirror=$c7 [$derr]"

# 52. The scan's boundaries: archived specs are records, and an absent or unwritten spec is
# not a defect.
#
# .specs/_archive/ holds #105 itself, whose T5 is precisely the forbidden shape. Rewriting a
# record to satisfy a guard added afterwards destroys its value as evidence — the #102
# precedent. A repository with no .specs/ at all, and a spec whose Tasks section has not been
# written yet, are both states `spec` tells an author to create: flagging them is #8.
r=$(specs_repo spec-archive)
write_spec "$r" "_archive/105-a-clock" "- [x] T5: **after the reviewer gate is CLEAN** — bump both manifests to 0.4.4."
out=$(run_templates "$r")
[ "$out" = "0" ] && c1=ok || c1=no

# ...and one directly at .specs/_archive/spec.md, which the enumeration DOES reach. The case
# above alone cannot fail if the `_archive` name check is deleted — its fixture sits a level
# below what iterdir() inspects, so the exemption would still look tested while being gone.
# An exemption nothing can mutation-test is an exemption that is not really pinned (G-8).
r=$(specs_repo spec-archive-direct)
write_spec "$r" "_archive" "- [x] T5: **after the reviewer gate is CLEAN** — bump both manifests to 0.4.4."
out=$(run_templates "$r")
[ "$out" = "0" ] && c1b=ok || c1b=no

r=$(specs_repo spec-none)
rmdir "$r/.specs"                  # ABSENT, not merely empty — specs_repo creates it, and a
                                   # fixture that leaves it in place never reaches the branch
                                   # this case claims to cover. The two states happen to agree
                                   # today, which is exactly why the case must build the right
                                   # one rather than the one that passes.
out=$(run_templates "$r")
[ "$out" = "0" ] && c2=ok || c2=no

r=$(specs_repo spec-empty)
mkdir -p "$r/.specs/9-feature"
printf '# Spec: x\n\n## 1. Requirements\n- [ ] **AC1:** x.\n\n## 3. Tasks (TDD-ordered)\n' > "$r/.specs/9-feature/spec.md"
out=$(run_templates "$r")
[ "$out" = "0" ] && c3=ok || c3=no

[ "$c1$c1b$c2$c3" = "okokokok" ] && report "archived specs, a missing .specs and an unwritten Tasks section are not failures" ok \
  || report "archived specs, a missing .specs and an unwritten Tasks section are not failures" no \
     "archive-skipped=$c1 archive-direct=$c1b no-specs=$c2 no-tasks=$c3"

# 53. A spec that exists and cannot be read must fail, not pass.
#
# The same third state as cases 32 and 37. A spec the guard never opened contributes no task
# lines, and an empty contribution is indistinguishable from a compliant one — so silence
# here would be the guard reporting success about a file it could not read.
r=$(specs_repo spec-unreadable)
write_spec "$r" "9-feature" "- [ ] T1: failing test for the thing — then the implementation that passes it"
chmod 000 "$r/.specs/9-feature/spec.md" 2>/dev/null
if cat "$r/.specs/9-feature/spec.md" >/dev/null 2>&1; then
  chmod 644 "$r/.specs/9-feature/spec.md" 2>/dev/null
  c1=ok; c2=ok
  note_skip "templates/unreadable-spec-file" "chmod does not deny access here (running as root?)"
else
  out=$(run_templates "$r"); err=$(cat "$TMP/terr")
  chmod 644 "$r/.specs/9-feature/spec.md" 2>/dev/null
  [ "$out" = "1" ] && c1=ok || c1=no
  case "$err" in *"cannot be read"*) c2=ok ;; *) c2=no ;; esac
fi
[ "$c1$c2" = "okok" ] && report "a spec that cannot be read fails rather than passing" ok \
  || report "a spec that cannot be read fails rather than passing" no "exit=$c1 msg=$c2"


# --- guards: scripts/check-skill-contracts.py --------------------------------------
#
# #113. The other half of the same fix. check-templates.py above catches a spec that defers
# a task; this catches the instruction that tells authors not to being edited out of the
# shipped skill. They fail in opposite directions, and only this one reaches consumers —
# scripts/ is not shipped, skills/ is.
#
# The guard had no case here at all before this, which is the guard-shaped hole #16 and #35
# are both about: .steering/structure.md makes this file the project's whole notion of test
# coverage, so a guard nothing exercises is a guard that can stop working unnoticed.

# The real skills/ tree, so the control asserts every needle in CONTRACTS is genuinely
# present rather than asserting it against a fixture built to satisfy it.
contracts_repo() {
  r="$TMP/$1"; mkdir -p "$r/scripts"
  cp "$ROOT/scripts/check-skill-contracts.py" "$r/scripts/"
  chmod +x "$r/scripts/check-skill-contracts.py"
  cp -R "$ROOT/skills" "$r/skills"
  echo "$r"
}

run_contracts() { ( cd "$1" && python3 scripts/check-skill-contracts.py >/dev/null 2>"$TMP/cerr"; printf '%s' "$?" ) }

# 54. implement stripped of the post-receipt version bump must fail.
#
# The mutation REMOVES the sentence if it is there and is a no-op if it is not, deliberately.
# A fixture builder that aborted on a missing target would have reported this case red for a
# setup error on the turn before the step was written, and a red that comes from the fixture
# proves nothing about the guard. Written this way, the pre-fix red is the real one: implement
# carries no bump step, and check-skill-contracts.py does not care.
r=$(contracts_repo contracts-control)
out=$(run_contracts "$r")
[ "$out" = "0" ] && c0=ok || c0=no

r=$(contracts_repo contracts-stripped)
python3 - "$r" <<'PYEOF'
import pathlib, sys
p = pathlib.Path(sys.argv[1], "skills", "implement", "SKILL.md")
needle = "The version bump lands here, after the receipt — never as a task"
src = p.read_text()
p.write_text(src.replace(needle, "Bump the version at some point"))
PYEOF
out=$(run_contracts "$r"); err=$(cat "$TMP/cerr")
[ "$out" = "1" ] && c1=ok || c1=no
case "$err" in *"skills/implement/SKILL.md"*) c2=ok ;; *) c2=no ;; esac
case "$err" in *"never as a task"*) c3=ok ;; *) c3=no ;; esac

[ "$c0$c1$c2$c3" = "okokokok" ] && report "implement stripped of the post-receipt version bump fails" ok \
  || report "implement stripped of the post-receipt version bump fails" no \
     "control=$c0 stripped-exit=$c1 names-file=$c2 names-needle=$c3"


# 55. A .specs/ or a spec directory that cannot be READ must fail, not scan nothing.
#
# Case 53 covers the unreadable spec FILE. One level up is a different state and it failed
# open: `is_dir()` succeeds on a directory the process cannot read, because stat needs only
# the parent's execute bit, and `Path.glob` swallows the OSError from scandir. Both yield
# zero entries, which is indistinguishable from a repository with nothing to check — so the
# guard printed an affirmative line about specs it never enumerated. That is #16 exactly, in
# the half of the state space the first cut of this scan did not cover.
r=$(specs_repo spec-dir-unreadable)
write_spec "$r" "9-feature" "- [x] T5: **after the reviewer gate is CLEAN** — bump both manifests."
chmod 000 "$r/.specs/9-feature" 2>/dev/null
if ls "$r/.specs/9-feature" >/dev/null 2>&1; then
  chmod 755 "$r/.specs/9-feature" 2>/dev/null
  c1=ok; c2=ok
  note_skip "templates/unreadable-spec-dir" "permissions not enforced here (running as root?)"
else
  out=$(run_templates "$r"); err=$(cat "$TMP/terr")
  chmod 755 "$r/.specs/9-feature" 2>/dev/null
  [ "$out" = "1" ] && c1=ok || c1=no
  case "$err" in *"cannot be read"*) c2=ok ;; *) c2=no ;; esac
fi

r=$(specs_repo spec-root-unreadable)
write_spec "$r" "9-feature" "- [ ] T1: failing test for the thing — then the implementation that passes it"
chmod 000 "$r/.specs" 2>/dev/null
if ls "$r/.specs" >/dev/null 2>&1; then
  chmod 755 "$r/.specs" 2>/dev/null
  c3=ok; c4=ok
  note_skip "templates/unreadable-specs-root" "permissions not enforced here (running as root?)"
else
  out=$(run_templates "$r"); err=$(cat "$TMP/terr")
  chmod 755 "$r/.specs" 2>/dev/null
  [ "$out" = "1" ] && c3=ok || c3=no
  case "$err" in *"cannot be read"*) c4=ok ;; *) c4=no ;; esac
fi

[ "$c1$c2$c3$c4" = "okokokok" ] && report "an unreadable spec directory or .specs fails rather than scanning nothing" ok \
  || report "an unreadable spec directory or .specs fails rather than scanning nothing" no \
     "slug-exit=$c1 slug-msg=$c2 root-exit=$c3 root-msg=$c4"


# --- guards: assets/check-document-set.py -------------------------------------------
#
# #110. `init` chose between a minimum and a full document set and recorded nothing, so the
# harness could not tell "minimum, deliberately" from "full, half-abandoned". The mode is now
# DECLARED in .steering/tech.md and VERIFIED against the filesystem here. The declaration is
# the point: derivation from which files exist cannot distinguish deliberate omission from
# abandonment, which is the whole feature.
#
# The checker is a guard a project OWNS — copied into its scripts/ and named on its
# `- Validators:` line, like check-steering-anchors.sh and check-locks.py — so no hook
# branches on the mode. A gate that branched on mode would be a switch that turns enforcement
# down, which is why AC5 forbids it and why nothing below drives a hook.

# $1 = name, $2 = the `- Mode:` value (empty writes no line at all), $3 = Docs value (optional)
docset_repo() {
  # $2 is read with ${2-} rather than $2: the suite runs under `set -u`, and an unbound $2
  # aborts the subshell, which returns an EMPTY path. Every later `rm "$r/..."` then operates
  # on "/..." and the assertions read whatever the previous case left behind. That is a
  # fixture failure wearing a guard failure's clothes — it cost one red run here, and one of
  # the assertions passed SPURIOUSLY while it lasted, on an error file that was empty because
  # nothing had run at all.
  m=${2-}
  r="$TMP/$1"; mkdir -p "$r/scripts" "$r/.steering" "$r/.github/ISSUE_TEMPLATE" "$r/.specs" "$r/.work_logs"
  cp "$ROOT/assets/check-document-set.py" "$r/scripts/"
  chmod +x "$r/scripts/check-document-set.py"
  d=${3:-docs/}
  # A URL is not a path. Seeding it would build a real tree at `$r/https:/example.invalid/docs`,
  # and case 58 would then survive only because add_full_docs is not called for it — red for
  # the right verdict and the wrong reason, one "for symmetry" edit away from going green on a
  # checker that reads a URL as a directory. G-4: a fixture must be able to fail for the reason
  # it claims to test.
  case "$d" in
    *://*) : ;;
    *) mkdir -p "$r/$d" 2>/dev/null || true
       for f in PRD DESIGN BACKLOG; do printf 'x\n' > "$r/$d/$f.md"; done ;;
  esac
  {
    printf '# Tech\n\n'
    printf -- '- Validators: ./scripts/check-document-set.py\n'
    printf -- '- Reviewer: some-reviewer\n'
    printf -- '- Docs: %s\n' "$d"
    [ -n "$m" ] && printf -- '- Mode: %s\n' "$m"
  } > "$r/.steering/tech.md"
  for t in feature bug chore; do printf 'x\n' > "$r/.github/ISSUE_TEMPLATE/$t.md"; done
  echo "$r"
}
add_full_docs() { for f in NORTH_STAR EPICS CONTRACT; do printf 'x\n' > "$1/docs/$f.md"; done; }
run_docset() { ( cd "$1" && python3 scripts/check-document-set.py >/dev/null 2>"$TMP/derr"; printf '%s' "$?" ) }

# 56. Both modes verified in both directions, and the mandatory set checked under BOTH.
#
# The control runs first and in both modes: a checker that failed on every input would satisfy
# the accusing halves on its own. The minimum-mode control is the one with no dogfooding in
# this repository — every document the full set names exists here — so it is the half most
# likely to be wrong and is asserted explicitly rather than inferred from the full-mode pass.
r=$(docset_repo ds-full-ok full); add_full_docs "$r"
out=$(run_docset "$r"); [ "$out" = "0" ] && c0=ok || c0=no

r=$(docset_repo ds-min-ok minimum)                       # the three optional documents absent
out=$(run_docset "$r"); [ "$out" = "0" ] && c1=ok || c1=no

# full mode, one required document missing: must fail AND name it.
r=$(docset_repo ds-full-gap full); add_full_docs "$r"; rm "$r/docs/CONTRACT.md"
out=$(run_docset "$r"); err=$(cat "$TMP/derr")
[ "$out" = "1" ] && c2=ok || c2=no
case "$err" in *CONTRACT.md*) c3=ok ;; *) c3=no ;; esac

# minimum mode must NOT report the optional three as missing...
r=$(docset_repo ds-min-quiet minimum)
out=$(run_docset "$r"); err=$(cat "$TMP/derr")
case "$err" in *CONTRACT.md*|*EPICS.md*|*NORTH_STAR.md*) c4=no ;; *) c4=ok ;; esac

# ...but it must still verify the MANDATORY set. A mode that checks nothing is not a mode.
r=$(docset_repo ds-min-gap minimum); rm "$r/docs/BACKLOG.md"
out=$(run_docset "$r"); err=$(cat "$TMP/derr")
[ "$out" = "1" ] && c5=ok || c5=no
case "$err" in *BACKLOG.md*) c6=ok ;; *) c6=no ;; esac

# An optional document PRESENT under minimum is not an error: clarify settled that a
# minimum-mode project may run `contract` at any point without changing mode.
r=$(docset_repo ds-min-extra minimum); printf 'x\n' > "$r/docs/CONTRACT.md"
out=$(run_docset "$r"); [ "$out" = "0" ] && c7=ok || c7=no

# The issue templates are part of the set in both modes.
r=$(docset_repo ds-tpl-gap full); add_full_docs "$r"; rm "$r/.github/ISSUE_TEMPLATE/bug.md"
out=$(run_docset "$r"); err=$(cat "$TMP/derr")
[ "$out" = "1" ] && c8=ok || c8=no
case "$err" in *bug.md*) c9=ok ;; *) c9=no ;; esac

[ "$c0$c1$c2$c3$c4$c5$c6$c7$c8$c9" = "okokokokokokokokokok" ] \
  && report "both modes verify their own set, in both directions" ok \
  || report "both modes verify their own set, in both directions" no \
     "full-ok=$c0 min-ok=$c1 full-gap-exit=$c2 names-doc=$c3 min-quiet=$c4 min-gap-exit=$c5 names-doc=$c6 min-extra-ok=$c7 tpl-exit=$c8 tpl-names=$c9"

# 57. No mode, an unknown mode, and an unreadable tech.md are a THIRD outcome, never a default.
#
# This is #16 at the newest layer. A checker that reads "no `- Mode:` line" as "minimum"
# reports success having verified the smaller set — indistinguishable from a project that
# chose minimum — and the declaration it exists to enforce is then optional in practice.
# Reachable with no adversarial input at all: any project installed before this feature has
# no line.
r=$(docset_repo ds-nomode "")                    # no `- Mode:` line written
out=$(run_docset "$r"); err=$(cat "$TMP/derr")
[ "$out" = "1" ] && c1=ok || c1=no
case "$err" in *Mode*) c2=ok ;; *) c2=no ;; esac

r=$(docset_repo ds-badmode velocity)             # a value that is neither minimum nor full
out=$(run_docset "$r"); err=$(cat "$TMP/derr")
[ "$out" = "1" ] && c3=ok || c3=no
case "$err" in *velocity*) c4=ok ;; *) c4=no ;; esac

r=$(docset_repo ds-notech full); rm "$r/.steering/tech.md"
out=$(run_docset "$r"); err=$(cat "$TMP/derr")
[ "$out" = "1" ] && c5=ok || c5=no

r=$(docset_repo ds-unreadable full); add_full_docs "$r"
chmod 000 "$r/.steering/tech.md" 2>/dev/null
if cat "$r/.steering/tech.md" >/dev/null 2>&1; then
  chmod 644 "$r/.steering/tech.md" 2>/dev/null
  c6=ok; c7=ok
  note_skip "docset/unreadable-tech-md" "permissions not enforced here (running as root?)"
else
  out=$(run_docset "$r"); err=$(cat "$TMP/derr")
  chmod 644 "$r/.steering/tech.md" 2>/dev/null
  [ "$out" = "1" ] && c6=ok || c6=no
  case "$err" in *"cannot be read"*) c7=ok ;; *) c7=no ;; esac
fi

# A `- Mode:` line the reader cannot parse is the #34 shape: bolded, it yields nothing and
# the file looks right. It must fail as "no mode", not pass on a default.
r=$(docset_repo ds-bolded "")
printf -- '- **Mode: full**\n' >> "$r/.steering/tech.md"
out=$(run_docset "$r"); [ "$out" = "1" ] && c8=ok || c8=no

[ "$c1$c2$c3$c4$c5$c6$c7$c8" = "okokokokokokokok" ] \
  && report "an absent, unknown or unreadable mode fails rather than defaulting" ok \
  || report "an absent, unknown or unreadable mode fails rather than defaulting" no \
     "nomode-exit=$c1 nomode-msg=$c2 bad-exit=$c3 bad-names=$c4 notech=$c5 unreadable-exit=$c6 unreadable-msg=$c7 bolded=$c8"

# 58. Documents in another repository cannot be verified here, and must say so rather than pass.
#
# `- Docs:` may hold "the path/URL of a shared documentation repo in a multi-repo product",
# per init. A URL is not a directory, so every document would read as absent — which would be
# a false RED — and treating it as "nothing to check" would be a false GREEN. Neither is
# acceptable, so it is a named outcome and init does not put this checker on the Validators
# line of a project configured that way.
r=$(docset_repo ds-remote full "https://example.invalid/docs")
out=$(run_docset "$r"); err=$(cat "$TMP/derr")
[ "$out" = "1" ] && c1=ok || c1=no
case "$err" in *"cannot be verified"*) c2=ok ;; *) c2=no ;; esac
case "$err" in *"not found"*) c3=no ;; *) c3=ok ;; esac     # must NOT read as absent documents

[ "$c1$c2$c3" = "okokok" ] && report "a remote Docs value is named, not read as absent documents" ok \
  || report "a remote Docs value is named, not read as absent documents" no \
     "exit=$c1 says-unverifiable=$c2 not-reported-as-missing=$c3"


# 60. Trailing whitespace: strict on `Mode`, tolerant on `Docs`, and each says why.
#
# This case exists because the parity fix that produced it was, for one round, an INTENTION.
# `steering_value` dropped `.strip()` so it would return exactly what `sed -n "s/^ *- *KEY: *//p"`
# returns — the Python had been the more PERMISSIVE of the two, accepting a value the hooks
# would not match, which is #34 inverted and the direction that passes silently. Nothing
# asserted it. Restoring `.strip()` reintroduced the divergence with all 71 cases green, so a
# later "tidy up this odd return" commit would have undone it unopposed. G-4: no case, not
# shipped.
#
# The two halves are deliberately asymmetric, and the asymmetry is the thing under test.
# `Mode` is read by a shell consumer, so parity is the stricter behaviour and wins. `Docs` is
# not — gate_steering_value is called for Validators, Source globs, Owns and Reviewer, and the
# anchors guard reads Docs only to test it non-empty — so there is no reader to be stricter
# than, and `Path("docs/ ")` would fail on a directory named " " with the cause invisible in
# rendered Markdown. A single rule applied to both would be wrong at one end or the other.
r=$(docset_repo ds-ws-mode ""); add_full_docs "$r"
printf -- '- Mode: full \n' >> "$r/.steering/tech.md"      # one trailing space
out=$(run_docset "$r"); err=$(cat "$TMP/derr")
[ "$out" = "1" ] && c1=ok || c1=no
case "$err" in *whitespace*) c2=ok ;; *) c2=no ;; esac
# exit 1 alone cannot tell the parity fix from the pre-existing "not a mode" branch, so the
# message is asserted too — and asserted NOT to be the unactionable one.
case "$err" in *"is not a mode"*) c3=no ;; *) c3=ok ;; esac

# The mirror: `Docs` with a trailing space must still PASS. Strict here would fire on an
# ordinary steering file and is how a gate gets switched off.
r=$(docset_repo ds-ws-docs full); add_full_docs "$r"
# The assertion below expects a PASS, so a no-op mutation would satisfy it by leaving an
# ordinary repo — silent green. The needle matches byte-for-byte only because docset_repo
# writes `- Docs: %s\n`, so the edit reports whether it applied AND the shell checks it: a
# `raise` alone is not enough, because the shell does not inspect a heredoc python's exit
# status. Found by mutating docset_repo's format string and watching this case stay green.
#
# Not an `assert`: this suite's own guard forbids expressing a safety check that way, since
# `python -O` strips them — #28, found in a guard protecting the receipt schema.
if python3 - "$r" <<'PYEOF'
import pathlib, sys
p = pathlib.Path(sys.argv[1], ".steering", "tech.md")
src = p.read_text()
out = src.replace("- Docs: docs/\n", "- Docs: docs/ \n")
if out == src:
    raise SystemExit("fixture no-op: the `- Docs:` needle no longer matches docset_repo's format")
p.write_text(out)
PYEOF
then cf1=ok; else cf1=no; fi
out=$(run_docset "$r")
{ [ "$out" = "0" ] && [ "$cf1" = ok ]; } && c4=ok || c4=no

# A whitespace-ONLY `- Docs:` is the third state, and it was a fail-open for one round. With
# the strip outside the `or`, a tab is truthy, survives the default, and is then emptied —
# and `pathlib.Path("")` is `.`, a directory that always exists. The guard then verified the
# set at the repository ROOT and, on a project keeping its documents there, exited 0 with a
# success line naming no directory. The anchors guard cannot catch it either: a tab is not
# empty, so it reports `Docs` resolved about the same line.
#
# The fixture puts the documents where a real project puts them, so a run against `.` finds
# nothing and the exit code separates the two behaviours.
r=$(docset_repo ds-docs-blank full); add_full_docs "$r"
if python3 - "$r" <<'PYEOF'
import pathlib, sys
p = pathlib.Path(sys.argv[1], ".steering", "tech.md")
src = p.read_text()
out = src.replace("- Docs: docs/\n", "- Docs: \t\n")
if out == src:
    raise SystemExit("fixture no-op: the `- Docs:` needle no longer matches docset_repo's format")
p.write_text(out)
PYEOF
then cf2=ok; else cf2=no; fi
out=$(run_docset "$r"); err=$(cat "$TMP/derr")
# Must fall back to docs/ exactly as an absent line does, and therefore PASS on this tree —
# never verify `.` and never report the documents missing from a directory nobody configured.
{ [ "$out" = "0" ] && [ "$cf2" = ok ]; } && c5=ok || c5=no
case "$err" in *PRD.md*) c6=no ;; *) c6=ok ;; esac

[ "$c1$c2$c3$c4$c5$c6" = "okokokokokok" ] && report "trailing whitespace is strict on Mode, tolerant on Docs, and blank Docs never means the repo root" ok \
  || report "trailing whitespace is strict on Mode, tolerant on Docs, and blank Docs never means the repo root" no \
     "mode-exit=$c1 mode-names-whitespace=$c2 mode-not-generic=$c3 docs-tolerant=$c4 blank-falls-back=$c5 not-root-scanned=$c6"

# 68. The tree `init` step 3 actually produces must pass the document-set checker step 3 arms.
#
# #127. `init` writes `- Mode:` and `- Docs: docs/`, copies this checker into the project and
# adds it to `- Validators:` — and creates no `docs/` and none of PRD/DESIGN/BACKLOG, which the
# checker required in BOTH modes. So every first install armed its own gate red. CAP-4's
# falsifier stated literally, and DORMANT: quality-gate.sh runs the Validators line only when a
# `- Source globs:` path changed, and a document is never source, so it fired on the user's
# first real edit with the cause a day behind them.
#
# The fixture is built from what step 3 writes rather than by deleting from docset_repo, and
# that is the point of it: it is a model of the installer's output, so it goes red again the
# next time THIS checker's requirements outgrow what step 3 creates. Deriving it by `rm` would
# make it a model of the OTHER fixture instead.
#
# Scoped to one validator, and the scope is stated because the claim is otherwise larger than
# the case: step 3 also arms check-steering-anchors.sh, which this fixture neither installs nor
# runs. Extending it to the whole armed set is worth doing and is not done here.
init_tree() {
  r="$TMP/$1"; mkdir -p "$r/scripts" "$r/.steering" "$r/.github/ISSUE_TEMPLATE" "$r/.specs" "$r/.work_logs"
  cp "$ROOT/assets/check-document-set.py" "$r/scripts/"
  chmod +x "$r/scripts/check-document-set.py"
  {
    printf '# Tech\n\n'
    printf -- '- Validators: ./scripts/check-document-set.py\n'
    printf -- '- Reviewer: some-reviewer\n'
    printf -- '- Docs: docs/\n'
    printf -- '- Mode: %s\n' "${2-}"
  } > "$r/.steering/tech.md"
  for t in feature bug chore; do printf 'x\n' > "$r/.github/ISSUE_TEMPLATE/$t.md"; done
  # Deliberately NOT created: docs/, PRD.md, DESIGN.md, BACKLOG.md. Step 3 writes none of them.
  echo "$r"
}

r=$(init_tree ds-boot-install bootstrap)
out=$(run_docset "$r"); err=$(cat "$TMP/derr")
[ "$out" = "0" ] && c1=ok || c1=no

# The same tree under the two modes that CLAIM the documents must still fail — this is the
# half that keeps the fix a narrowing rather than a hole. Without it, "bootstrap passes" is
# satisfiable by a checker that stopped looking at documents altogether.
r=$(init_tree ds-boot-min-red minimum)
out=$(run_docset "$r"); [ "$out" = "1" ] && c2=ok || c2=no
r=$(init_tree ds-boot-full-red full)
out=$(run_docset "$r"); [ "$out" = "1" ] && c3=ok || c3=no

# bootstrap asserts the INSTALL-time invariant and must still fail on it. A missing issue
# template is step 3's own output going absent, which is a different fact from an unwritten
# PRD and must not be waved through with it.
r=$(init_tree ds-boot-tpl bootstrap); rm "$r/.github/ISSUE_TEMPLATE/chore.md"
out=$(run_docset "$r"); err=$(cat "$TMP/derr")
[ "$out" = "1" ] && c4=ok || c4=no
case "$err" in *chore.md*) c5=ok ;; *) c5=no ;; esac

r=$(init_tree ds-boot-dirs bootstrap); rmdir "$r/.work_logs"
out=$(run_docset "$r"); [ "$out" = "1" ] && c6=ok || c6=no

# Its success line must not be the other modes' success line. G-1: "the documents are present"
# and "the documents were not looked at" cannot share an outcome, and exit 0 is already shared,
# so the words are the only place the difference can live.
r=$(init_tree ds-boot-says bootstrap)
sout=$( cd "$r" && python3 scripts/check-document-set.py 2>/dev/null )
case "$sout" in *bootstrap*) c7=ok ;; *) c7=no ;; esac
case "$sout" in *PRD.md*) c8=ok ;; *) c8=no ;; esac
# ...and it must not claim a count of documents it never checked.
case "$sout" in *"document(s), "*) c9=no ;; *) c9=ok ;; esac

# A remote `- Docs:` is still its own outcome under bootstrap. The URL branch sits ahead of the
# document set in all three modes: a value that is not a path is a misconfiguration whatever
# the mode, and reading it as "nothing to check yet" would be the false GREEN case 58 exists
# to forbid, reachable again through the new value.
r=$(init_tree ds-boot-remote bootstrap)
if python3 - "$r" <<'PYEOF'
import pathlib, sys
p = pathlib.Path(sys.argv[1], ".steering", "tech.md")
src = p.read_text()
out = src.replace("- Docs: docs/\n", "- Docs: https://example.invalid/docs\n")
if out == src:
    raise SystemExit("fixture no-op: the `- Docs:` needle no longer matches init_tree's format")
p.write_text(out)
PYEOF
then cf1=ok; else cf1=no; fi
out=$(run_docset "$r"); err=$(cat "$TMP/derr")
{ [ "$out" = "1" ] && [ "$cf1" = ok ]; } && c10=ok || c10=no
case "$err" in *"cannot be verified"*) c11=ok ;; *) c11=no ;; esac

[ "$c1$c2$c3$c4$c5$c6$c7$c8$c9$c10$c11" = "okokokokokokokokokokok" ] \
  && report "the tree init step 3 produces passes check-document-set, and bootstrap narrows nothing else" ok \
  || report "the tree init step 3 produces passes check-document-set, and bootstrap narrows nothing else" no \
     "install-green=$c1 min-still-red=$c2 full-still-red=$c3 tpl-red=$c4 names-tpl=$c5 dirs-red=$c6 says-bootstrap=$c7 names-owed=$c8 no-false-count=$c9 remote-red=$c10 remote-msg=$c11"

# 69. `bootstrap` stops passing once the project starts building against documents it never
#     wrote — otherwise it is a gate switched off with a note attached.
#
# #127's AC4. The grace period ends at the FIRST SPEC, because a spec is where a capability id
# gets cited and a spec is the first moment the harness is genuinely in use. That puts the
# failure inside the flow, with the cause one command behind the user, rather than on their
# first turn, which is the distinction CAP-4 actually draws — it is not "never block", it is
# "never block on a failure that predates them".
spec_in() { mkdir -p "$1"; printf '# Spec\n' > "$1/spec.md"; }

# Control FIRST: the directories init creates, empty, plus the README it will hold. A checker
# that failed on any `.specs/` at all would satisfy every accusing half below on its own.
r=$(init_tree ds-boot-nospec bootstrap); printf 'x\n' > "$r/.specs/README.md"; mkdir -p "$r/.specs/_archive"
out=$(run_docset "$r"); [ "$out" = "0" ] && c1=ok || c1=no

r=$(init_tree ds-boot-spec bootstrap); spec_in "$r/.specs/7-a-thing"
out=$(run_docset "$r"); err=$(cat "$TMP/derr")
[ "$out" = "1" ] && c2=ok || c2=no
case "$err" in *7-a-thing*) c3=ok ;; *) c3=no ;; esac
# The message has to carry the way OUT, not just the verdict. A user who reaches this has a
# spec in hand and three unwritten documents; "bootstrap is no longer valid" tells them
# nothing they can act on.
case "$err" in *minimum*) c4=ok ;; *) c4=no ;; esac

# An archived spec counts. A project that shipped work and then swept it has still been built
# against documents that do not exist, and reading only the live directory would hand it a
# fresh grace period for tidying up.
r=$(init_tree ds-boot-arch bootstrap); spec_in "$r/.specs/_archive/7-a-thing"
out=$(run_docset "$r"); [ "$out" = "1" ] && c5=ok || c5=no

# A directory under `.specs/` with no spec.md is not a spec. `_archive/` itself is one of
# these, and so is anything a session left behind.
r=$(init_tree ds-boot-bare bootstrap); mkdir -p "$r/.specs/7-a-thing"
out=$(run_docset "$r"); [ "$out" = "0" ] && c6=ok || c6=no

# THIRD OUTCOME. An unreadable `.specs/` is neither "no spec" nor "a spec", and the difference
# is invisible in the exit code unless it is made visible: `Path.glob` swallows OSError and
# would report an unreadable directory as an empty one — reporting the grace period intact
# because it could not look. G-1, and the #115 lesson in the same shape.
r=$(init_tree ds-boot-unreadable bootstrap); spec_in "$r/.specs/7-a-thing"
chmod 000 "$r/.specs" 2>/dev/null
if ( cd "$r" && ls .specs >/dev/null 2>&1 ); then
  chmod 755 "$r/.specs" 2>/dev/null
  c7=ok; c8=ok
  note_skip "bootstrap/unreadable-.specs" "permissions not enforced here (running as root?)"
else
  out=$(run_docset "$r"); err=$(cat "$TMP/derr")
  chmod 755 "$r/.specs" 2>/dev/null
  [ "$out" = "1" ] && c7=ok || c7=no
  case "$err" in *"cannot be read"*) c8=ok ;; *) c8=no ;; esac
fi

# The SAME third outcome one level in. `Path.is_file()` delegates to `os.path.isfile`, which
# swallows every OSError including PermissionError — so a slug directory the process cannot
# traverse reads as "no spec.md here", and the grace period is reported intact because the
# checker could not look. The outer scandir being guarded does not cover this: found in review,
# and it is the file's own docstring promise delivered for the outer directory only. It was
# also interpreter-dependent, which means it was not a verdict.
r=$(init_tree ds-boot-slug-unreadable bootstrap); spec_in "$r/.specs/7-a-thing"
chmod 000 "$r/.specs/7-a-thing" 2>/dev/null
if ( cd "$r" && cat .specs/7-a-thing/spec.md >/dev/null 2>&1 ); then
  chmod 755 "$r/.specs/7-a-thing" 2>/dev/null
  c10=ok; c11=ok
  note_skip "bootstrap/unreadable-slug" "permissions not enforced here (running as root?)"
else
  out=$(run_docset "$r"); err=$(cat "$TMP/derr")
  chmod 755 "$r/.specs/7-a-thing" 2>/dev/null
  [ "$out" = "1" ] && c10=ok || c10=no
  case "$err" in *7-a-thing*) c11=ok ;; *) c11=no ;; esac
fi

# A FOURTH outcome the function admitted to having three of: a symlinked slug directory was
# neither found nor unreadable, because `follow_symlinks=False` skipped it before the stat.
# The entry landed in no list, the caller saw no specs, and the grace period was reported
# intact with a spec on disk — the fail-open direction, reached by a definition of "spec
# directory" narrower than the design's. Found in review of the fix for the permission case.
r=$(init_tree ds-boot-symlink bootstrap); spec_in "$TMP/ds-boot-symlink-elsewhere/7-a-thing"
ln -s "$TMP/ds-boot-symlink-elsewhere/7-a-thing" "$r/.specs/7-a-thing" 2>/dev/null
if [ -L "$r/.specs/7-a-thing" ]; then
  out=$(run_docset "$r"); err=$(cat "$TMP/derr")
  [ "$out" = "1" ] && c12=ok || c12=no
  # The MESSAGE, not just the exit code. `*7-a-thing*` alone is satisfied by the unreadable
  # branch as well, which would pin "not green" rather than the outcome following symlinks
  # exists to produce — the link was resolved and the spec behind it counted.
  case "$err" in *"already exist"*7-a-thing*) c13=ok ;; *) c13=no ;; esac
else
  c12=ok; c13=ok
  note_skip "bootstrap/symlinked-slug" "symlink creation unavailable on this filesystem"
fi

# The green control for that widening. G-6: a condition that widens when a gate fires needs a
# case proving it does not fire on a correct repo. A dangling link holds no spec, and `is_dir()`
# answers a definite ENOENT rather than an unknown — so it must stay silent, not join the
# `unreadable` list that a loop or a permission wall belongs in.
r=$(init_tree ds-boot-dangling bootstrap)
ln -s "$TMP/ds-boot-dangling-nowhere" "$r/.specs/7-dangling" 2>/dev/null
# `-L` alone is true of ANY symlink, so a future fixture creating that target would turn this
# into "a symlinked directory holding no spec.md" — still green, for a different reason, and
# nothing would say so. The target's absence is the precondition, so it is asserted.
if [ -L "$r/.specs/7-dangling" ] && [ ! -e "$r/.specs/7-dangling" ]; then
  out=$(run_docset "$r"); [ "$out" = "0" ] && c14=ok || c14=no
else
  c14=ok
  note_skip "bootstrap/dangling-symlink" "symlink creation unavailable on this filesystem"
fi

# ...and the scan is `bootstrap`-only. In minimum and full a spec is the ordinary state of a
# working project, and failing on one would fire on every repository that uses this harness.
r=$(docset_repo ds-min-spec minimum); spec_in "$r/.specs/7-a-thing"
out=$(run_docset "$r"); [ "$out" = "0" ] && c9=ok || c9=no

[ "$c1$c2$c3$c4$c5$c6$c7$c8$c9$c10$c11$c12$c13$c14" = "okokokokokokokokokokokokokok" ] \
  && report "bootstrap expires at the first spec, and cannot expire quietly" ok \
  || report "bootstrap expires at the first spec, and cannot expire quietly" no \
     "empty-ok=$c1 spec-red=$c2 names-spec=$c3 says-way-out=$c4 archived-red=$c5 bare-dir-ok=$c6 unreadable-red=$c7 unreadable-msg=$c8 minimum-unaffected=$c9 slug-unreadable-red=$c10 names-slug=$c11 symlink-red=$c12 names-symlink=$c13 dangling-stays-green=$c14"

# 71. `- Target:` names what the chosen document set owes, in the bootstrap window only.
#
# #141. `- Mode:` records what is TRUE now; it cannot record what the operator signed up for,
# because `- Mode: full` on day one is a claim about documents that do not exist — the claim
# the checker exists to refuse. So the bootstrap block named three documents to an operator
# who may have chosen six, and the set they owed first became visible at the moment it blocked
# them. `- Target:` carries the choice through that window.
#
# It changes MESSAGES ONLY. `wanted` is still built from `- Mode:` alone, which is what keeps a
# mistyped target unable to let a document go unchecked — a target on the pass/fail path would
# be a second mode, and a wrong one would fail open.
target_in() { printf -- '- Target: %s\n' "$2" >> "$1/.steering/tech.md"; }

# Control FIRST, and it is the whole no-regression half: with no `- Target:` line the message
# must be byte-for-byte what it is today. Every accusing half below is satisfiable by a
# checker that simply prints all six documents always.
r=$(init_tree ds-tgt-absent bootstrap); spec_in "$r/.specs/7-a-thing"
out=$(run_docset "$r"); base_err=$(cat "$TMP/derr")
[ "$out" = "1" ] && c1=ok || c1=no
case "$base_err" in *NORTH_STAR.md*) c2=no ;; *) c2=ok ;; esac
case "$base_err" in *PRD.md*) c3=ok ;; *) c3=no ;; esac

# `- Target: full` and a spec: the block must now name the three the full set adds, and still
# name the three it never stopped owing.
r=$(init_tree ds-tgt-full bootstrap); target_in "$r" full; spec_in "$r/.specs/7-a-thing"
out=$(run_docset "$r"); err=$(cat "$TMP/derr")
[ "$out" = "1" ] && c4=ok || c4=no
case "$err" in *NORTH_STAR.md*) c5=ok ;; *) c5=no ;; esac
case "$err" in *EPICS.md*) c6=ok ;; *) c6=no ;; esac
case "$err" in *CONTRACT.md*) c7=ok ;; *) c7=no ;; esac
case "$err" in *PRD.md*) c8=ok ;; *) c8=no ;; esac

# `- Target: minimum` is not the same message as no target at all — it is a choice that was
# made, and it must not silently produce the "you have not chosen" wording. It owes three
# documents, and must NOT name the opt-in three.
r=$(init_tree ds-tgt-min bootstrap); target_in "$r" minimum; spec_in "$r/.specs/7-a-thing"
out=$(run_docset "$r"); err=$(cat "$TMP/derr")
[ "$out" = "1" ] && c9=ok || c9=no
case "$err" in *NORTH_STAR.md*|*EPICS.md*) c10=no ;; *) c10=ok ;; esac
case "$err" in *PRD.md*) c11=ok ;; *) c11=no ;; esac

# The target must not rescue a bootstrap project that has NOT started: no spec, still green.
# Without this, "names six documents" is satisfiable by a checker that blocks on the target.
r=$(init_tree ds-tgt-nospec bootstrap); target_in "$r" full
out=$(run_docset "$r"); [ "$out" = "0" ] && c12=ok || c12=no

[ "$c1$c2$c3$c4$c5$c6$c7$c8$c9$c10$c11$c12" = "okokokokokokokokokokokok" ] \
  && report "a bootstrap block names the target's documents, and no target keeps today's wording" ok \
  || report "a bootstrap block names the target's documents, and no target keeps today's wording" no \
     "absent-red=$c1 absent-quiet-on-optional=$c2 absent-names-mandatory=$c3 full-red=$c4 names-northstar=$c5 names-epics=$c6 names-contract=$c7 full-names-mandatory=$c8 min-red=$c9 min-quiet-on-optional=$c10 min-names-mandatory=$c11 no-spec-stays-green=$c12"

# 72. A `- Target:` that cannot be honoured is loud; an absent one is not; a spent one is unread.
#
# #141 AC4/AC5/AC9. Three states that all look like "no usable target" from inside the code and
# must not share an outcome. ABSENT is a supported configuration — every project installed
# before the line existed is in it — so it falls back to today's wording. PRESENT-BUT-WRONG is
# a declaration that cannot be honoured, and swallowing it would hide the typo for the whole
# and only window the line is read in. SPENT (mode no longer `bootstrap`) must not be read at
# all, or an upgraded project carrying a stale target goes red for a line nothing should be
# consulting.

# Wrong value, and the value itself must appear — "not a target" without the offending text is
# a diagnosis on a one-line file the reader has to go hunting through anyway.
r=$(init_tree ds-tgt-bogus bootstrap); target_in "$r" ful
out=$(run_docset "$r"); err=$(cat "$TMP/derr")
[ "$out" = "1" ] && c1=ok || c1=no
case "$err" in *ful*) c2=ok ;; *) c2=no ;; esac

# Trailing whitespace is TOLERATED here, and the asymmetry with `- Mode:` is the point: Mode is
# byte-compared against what gate_steering_value hands the shell, and Target has no shell
# reader to be stricter than. Strict here would reject a line that reads correctly to a human.
r=$(init_tree ds-tgt-ws bootstrap)
printf -- '- Target: full \n' >> "$r/.steering/tech.md"
out=$(run_docset "$r"); [ "$out" = "0" ] && c3=ok || c3=no
# ...and it must be honoured, not merely not-rejected. Without this the strip could be a
# silent discard and the case would still pass.
spec_in "$r/.specs/7-a-thing"
out=$(run_docset "$r"); err=$(cat "$TMP/derr")
case "$err" in *NORTH_STAR.md*) c4=ok ;; *) c4=no ;; esac

# An EMPTY value is the absent case, not the wrong-value case. `- Target:` with nothing after
# it is a line someone started and did not finish; failing on it would block an install over
# punctuation, and CAP-4 is the falsifier.
r=$(init_tree ds-tgt-empty bootstrap); spec_in "$r/.specs/7-a-thing"
printf -- '- Target: \n' >> "$r/.steering/tech.md"
out=$(run_docset "$r"); err=$(cat "$TMP/derr")
[ "$out" = "1" ] && c5=ok || c5=no
case "$err" in *NORTH_STAR.md*) c6=no ;; *) c6=ok ;; esac
case "$err" in *"minimum"*) c7=ok ;; *) c7=no ;; esac

# SPENT. A settled mode makes the target history, and a project that declared `minimum` after
# targeting `full` changed its mind — a decision, not a disagreement to police.
r=$(docset_repo ds-tgt-spent minimum); target_in "$r" full
out=$(run_docset "$r"); [ "$out" = "0" ] && c8=ok || c8=no

# The strongest half: even an UNPARSEABLE target is unread once the mode is settled. If the
# validation ran before the mode check, this would be red — and every project that upgraded
# past bootstrap with a typo in a line nothing reads would be blocked by it.
r=$(docset_repo ds-tgt-spent-bogus full); add_full_docs "$r"; target_in "$r" nonsense
out=$(run_docset "$r"); [ "$out" = "0" ] && c9=ok || c9=no

[ "$c1$c2$c3$c4$c5$c6$c7$c8$c9" = "okokokokokokokokok" ] \
  && report "an unhonourable target is named, an absent one falls back, and a spent one is never read" ok \
  || report "an unhonourable target is named, an absent one falls back, and a spent one is never read" no \
     "bogus-red=$c1 names-value=$c2 ws-green=$c3 ws-honoured=$c4 empty-red=$c5 empty-quiet-on-optional=$c6 empty-offers-both=$c7 spent-unread=$c8 spent-bogus-unread=$c9"

# 73. The bootstrap ADVISORY line names the target's set too, not just the failure.
#
# #141 AC8. The failure at the first spec was only half the ambush. The advisory line is what
# an operator sees on every green turn between install and that spec — so a `full` project
# being told "3 document(s) not yet authored" for a week is the surprise arriving later rather
# than never. The two outputs must agree about what is owed.
#
# G-1 still binds: the counts of templates and directories are in THEIR OWN units and must not
# absorb the document count, which is the conflation #109 introduced and the checker's own
# comment warns against reintroducing one layer down.
sout_docset() { ( cd "$1" && python3 scripts/check-document-set.py 2>/dev/null ) }

# Control: no target, and the line is what it is today.
r=$(init_tree ds-adv-absent bootstrap)
s=$(sout_docset "$r")
case "$s" in *"3 document(s)"*) c1=ok ;; *) c1=no ;; esac
case "$s" in *NORTH_STAR.md*) c2=no ;; *) c2=ok ;; esac

# `- Target: full`: six owed, each named with the skill that writes it.
r=$(init_tree ds-adv-full bootstrap); target_in "$r" full
s=$(sout_docset "$r")
case "$s" in *"6 document(s)"*) c3=ok ;; *) c3=no ;; esac
case "$s" in *"NORTH_STAR.md (via northstar)"*) c4=ok ;; *) c4=no ;; esac
case "$s" in *"EPICS.md (via epics)"*) c5=ok ;; *) c5=no ;; esac
case "$s" in *"CONTRACT.md (via contract)"*) c6=ok ;; *) c6=no ;; esac
case "$s" in *"PRD.md (via prd)"*) c7=ok ;; *) c7=no ;; esac
# The counts that are not documents must survive the change unconflated.
case "$s" in *"3 issue template(s)"*) c8=ok ;; *) c8=no ;; esac
case "$s" in *"2 directory(ies)"*) c9=ok ;; *) c9=no ;; esac
# A choice already made is not offered back.
# Single-quoted inside the pattern: a bare backtick in an unquoted `case` glob is command
# substitution, which ran and left the assertion comparing against a mangled string. That is a
# fixture failure wearing a guard failure's clothes — #124's genre, caught here by the stray
# `-: command not found` on stderr rather than by the red itself.
case "$s" in *'`- Mode: full`'*) c10=ok ;; *) c10=no ;; esac

# `- Target: minimum` owes three and must not list the opt-in three.
r=$(init_tree ds-adv-min bootstrap); target_in "$r" minimum
s=$(sout_docset "$r")
case "$s" in *"3 document(s)"*) c11=ok ;; *) c11=no ;; esac
case "$s" in *NORTH_STAR.md*|*EPICS.md*) c12=no ;; *) c12=ok ;; esac

[ "$c1$c2$c3$c4$c5$c6$c7$c8$c9$c10$c11$c12" = "okokokokokokokokokokokok" ] \
  && report "the bootstrap advisory line names the target's set, in units that stay separate" ok \
  || report "the bootstrap advisory line names the target's set, in units that stay separate" no \
     "absent-three=$c1 absent-quiet=$c2 full-six=$c3 names-northstar=$c4 names-epics=$c5 names-contract=$c6 names-prd=$c7 templates-own-unit=$c8 dirs-own-unit=$c9 names-one-mode=$c10 min-three=$c11 min-quiet=$c12"

# 70. A project that already had a bug template under its own name must pass after init.
#
# #130. Two bullets of step 3 disagreed: the merge rule said "add only the missing types", so a
# project with `bug_report.md` never got `bug.md` — and the checker requires that literal name.
# Following the instruction correctly produced a red gate. #127 masked it entirely, because the
# `- Docs:` check failed before the template check was reached.
#
# The fix is on init's side: absorb the project's template into the canonical filename. So what
# this case pins is that the CHECKER is indifferent to everything except the name — the body and
# labels below are the project's own, not the plugin's, and they must not matter.
docset_repo_tpl() {
  r=$(docset_repo "$1" "${2:-minimum}")
  rm -f "$r/.github/ISSUE_TEMPLATE/bug.md"
  echo "$r"
}

# Absorbed: the team's wording and labels, at the canonical name. Green.
r=$(docset_repo_tpl ds-tpl-absorbed)
printf -- '---\nname: Bug Report\nabout: Something is broken\nlabels: defect, needs-triage\n---\n\n## What happened\n' \
  > "$r/.github/ISSUE_TEMPLATE/bug.md"
out=$(run_docset "$r"); [ "$out" = "0" ] && c1=ok || c1=no

# Not absorbed: the shape the old instruction produced. Red, and it must still NAME the path —
# the fix narrows nothing about the verdict.
r=$(docset_repo_tpl ds-tpl-kept)
printf 'x\n' > "$r/.github/ISSUE_TEMPLATE/bug_report.md"
out=$(run_docset "$r"); err=$(cat "$TMP/derr")
[ "$out" = "1" ] && c2=ok || c2=no
case "$err" in *"ISSUE_TEMPLATE/bug.md"*) c3=ok ;; *) c3=no ;; esac
# ...and it must say what to DO. A project in this state believes it HAS a bug template, so a
# message naming only the absent path reads as a false accusation and gets the guard switched
# off. The remediation text is part of the guard — #127's round-2 lesson, one file over.
case "$err" in *"renames an existing template"*) c4=ok ;; *) c4=no ;; esac

# A type with no template at all is the control for that message: still red, still named, and
# the remedy is as true for it as for the renamed case (AC3).
r=$(docset_repo_tpl ds-tpl-absent)
out=$(run_docset "$r"); err=$(cat "$TMP/derr")
[ "$out" = "1" ] && c5=ok || c5=no
case "$err" in *"ISSUE_TEMPLATE/bug.md"*) c6=ok ;; *) c6=no ;; esac

# The control that keeps the above honest: the unmodified fixture, all three canonical names,
# must stay green. Without it a checker that failed on every template set would satisfy c2-c6.
r=$(docset_repo ds-tpl-control minimum)
out=$(run_docset "$r"); [ "$out" = "0" ] && c7=ok || c7=no

[ "$c1$c2$c3$c4$c5$c6$c7" = "okokokokokokok" ] \
  && report "an absorbed template passes, a kept one fails and says what to do" ok \
  || report "an absorbed template passes, a kept one fails and says what to do" no \
     "absorbed-green=$c1 kept-red=$c2 names-path=$c3 says-remedy=$c4 absent-red=$c5 absent-names=$c6 control-green=$c7"

# 59. init stripped of the document-set wiring must fail.
#
# Out of numeric order on purpose: 60 is grouped with the other docset cases above,
# because it shares their fixture family, while this one uses contracts_repo. The suite's
# source comments and its output order have already diverged (G-9); this is the third
# instance and it is deliberate rather than drift.
#
# Two entries, and the second is the load-bearing one: copying the checker onto the
# `- Validators:` line is the ONLY route by which the mode reaches a gate. Delete that
# sentence and the mode becomes a comment — declared on every install, checked on none — and
# the deletion is invisible in review, because what it removes is a check that says nothing
# rather than a behaviour anyone sees. That is the argument check-skill-contracts.py's own
# docstring demands of a new entry.
#
# The control runs first: a guard that failed on every input would satisfy the accusing half
# on its own. Both mutations are no-ops if their target is already absent, deliberately — a
# fixture that aborted would report a setup error as a guard failure.
r=$(contracts_repo contracts-mode-control)
out=$(run_contracts "$r")
[ "$out" = "0" ] && c0=ok || c0=no

r=$(contracts_repo contracts-nomode)
python3 - "$r" <<'PYEOF'
import pathlib, sys
p = pathlib.Path(sys.argv[1], "skills", "init", "SKILL.md")
needle = "`- Mode: bootstrap`, `- Mode: minimum` or `- Mode: full` on one physical line"
p.write_text(p.read_text().replace(needle, "a mode line somewhere"))
PYEOF
out=$(run_contracts "$r"); err=$(cat "$TMP/cerr")
[ "$out" = "1" ] && c1=ok || c1=no
case "$err" in *"skills/init/SKILL.md"*) c2=ok ;; *) c2=no ;; esac

r=$(contracts_repo contracts-nowiring)
python3 - "$r" <<'PYEOF'
import pathlib, sys
p = pathlib.Path(sys.argv[1], "skills", "init", "SKILL.md")
needle = "copy `assets/check-document-set.py` to the project's `scripts/` directory and add it to the `- Validators:` line"
p.write_text(p.read_text().replace(needle, "install the document-set checker"))
PYEOF
out=$(run_contracts "$r"); err=$(cat "$TMP/cerr")
[ "$out" = "1" ] && c3=ok || c3=no
case "$err" in *"Validators"*) c4=ok ;; *) c4=no ;; esac

# The third clause of #110's T2, which had prose and no pin until review found it. The
# upgrade bullet is what stops a re-run from recreating documents the author deliberately
# declined — the feature undoing itself — and it read as ordinary advice, so its deletion
# would have looked like trimming.
r=$(contracts_repo contracts-noupgrade)
python3 - "$r" <<'PYEOF'
import pathlib, sys
p = pathlib.Path(sys.argv[1], "skills", "init", "SKILL.md")
needle = "A project that already carries a `- Mode:` line is an upgrade, never a fresh install"
p.write_text(p.read_text().replace(needle, "Re-running init is fine"))
PYEOF
out=$(run_contracts "$r"); err=$(cat "$TMP/cerr")
[ "$out" = "1" ] && c5=ok || c5=no
case "$err" in *upgrade*) c6=ok ;; *) c6=no ;; esac

# #82's half: the contract-path guard checks that init NAMES the canonical path, and cannot
# check that init says WHERE to put it. That sentence is the only statement of the destination,
# and its absence is what produced four placements for one file.
r=$(contracts_repo contracts-nodest)
python3 - "$r" <<'PYEOF'
import pathlib, sys
p = pathlib.Path(sys.argv[1], "skills", "init", "SKILL.md")
needle = "inside the agents directory you are installing into"
p.write_text(p.read_text().replace(needle, "next to it"))
PYEOF
out=$(run_contracts "$r"); err=$(cat "$TMP/cerr")
[ "$out" = "1" ] && c7=ok || c7=no
case "$err" in *"agents directory"*) c8=ok ;; *) c8=no ;; esac

# #127's pin, the seventeenth. `spec` step 1 branches on `full` versus not-`full` and has an
# explicit rule for the line being ABSENT; a value it does not recognise falls through both,
# silently, so the model picks a reading and the user never learns a choice was made. Deleting
# the clause reads as removing a redundant case — `bootstrap` is "obviously" minimum-like — and
# what it removes is the only sentence that makes that obviousness written down.
r=$(contracts_repo contracts-nobootstrap)
python3 - "$r" <<'PYEOF'
import pathlib, sys
p = pathlib.Path(sys.argv[1], "skills", "spec", "SKILL.md")
needle = "A project still in `bootstrap` has neither, so read it as `minimum` here"
p.write_text(p.read_text().replace(needle, "Read the mode and use your judgement"))
PYEOF
out=$(run_contracts "$r"); err=$(cat "$TMP/cerr")
[ "$out" = "1" ] && c9=ok || c9=no
case "$err" in *"skills/spec/SKILL.md"*) c10=ok ;; *) c10=no ;; esac
# The needle too: that file carries two pins now, and the file name alone is satisfied by the
# OTHER one firing. check-skill-contracts.py's own docstring records this ambiguity as a
# shipped defect, and case 54 asserts both halves for the same reason.
case "$err" in *"has neither, so read it as"*) c11=ok ;; *) c11=no ;; esac

# #130's pin, the eighteenth. The sentence it replaced read as considerate — keep what the team
# wrote, add only what is missing — and this one reads as destructive, because it renames their
# file. Restoring the kinder wording undoes the fix while looking like a softened overreach, and
# every check here stays green: the damage lands only in installs that had templates of their
# own, which is to say never in this repository.
r=$(contracts_repo contracts-nomerge)
python3 - "$r" <<'PYEOF'
import pathlib, sys
p = pathlib.Path(sys.argv[1], "skills", "init", "SKILL.md")
needle = "and do it first: for each of the three types the project already has a template for, `git mv` each existing template to the canonical filename for its type"
src = p.read_text()
if needle not in src:
    raise SystemExit("fixture no-op: the absorb instruction is not where this expects it")
p.write_text(src.replace(needle, "keep their wording and add only the missing types"))
PYEOF
out=$(run_contracts "$r"); err=$(cat "$TMP/cerr")
[ "$out" = "1" ] && c12=ok || c12=no
case "$err" in *"skills/init/SKILL.md"*) c13=ok ;; *) c13=no ;; esac
case "$err" in *"canonical filename for its type"*) c14=ok ;; *) c14=no ;; esac

[ "$c0$c1$c2$c3$c4$c5$c6$c7$c8$c9$c10$c11$c12$c13$c14" = "okokokokokokokokokokokokokokok" ] && report "init stripped of the mode line, its wiring, its upgrade path or its destination — or spec of its bootstrap reading — fails" ok \
  || report "init stripped of the mode line, its wiring, its upgrade path or its destination — or spec of its bootstrap reading — fails" no \
     "control=$c0 nomode-exit=$c1 names-file=$c2 nowiring-exit=$c3 names-validators=$c4 noupgrade-exit=$c5 names-upgrade=$c6 nodest-exit=$c7 names-dest=$c8 nobootstrap-exit=$c9 names-spec-skill=$c10 names-needle=$c11 nomerge-exit=$c12 names-init=$c13 names-merge-needle=$c14"


# 74. init stripped of the TARGET question or its destination must fail. #141's pins, the
#     nineteenth and twentieth.
#
# #141 AC7. The question is the whole feature: the checker can read `- Target:` perfectly and
# still never see one, because nothing but this sentence causes the line to be written. Its
# deletion is the deletion that review cannot defend — asking one fewer question reads as
# respecting the operator's attention, and step 2's own five-question budget argues for it,
# while what it removes is the only producer of a value three guards now consume.
r=$(contracts_repo contracts-notarget)
python3 - "$r" <<'PYEOF'
import pathlib, sys
p = pathlib.Path(sys.argv[1], "skills", "init", "SKILL.md")
needle = "ask which document set the project is signing up for and record the answer as `- Target: minimum` or `- Target: full`"
src = p.read_text()
if needle not in src:
    raise SystemExit("fixture no-op: the target question is not where this expects it")
p.write_text(src.replace(needle, "record the mode"))
PYEOF
out=$(run_contracts "$r"); err=$(cat "$TMP/cerr")
[ "$out" = "1" ] && c1=ok || c1=no
case "$err" in *"skills/init/SKILL.md"*) c2=ok ;; *) c2=no ;; esac
case "$err" in *Target*) c3=ok ;; *) c3=no ;; esac

# The control, again first: unmutated init must pass, or the accusing half above is satisfied
# by a guard that fails on everything.
r=$(contracts_repo contracts-target-control)
out=$(run_contracts "$r"); [ "$out" = "0" ] && c4=ok || c4=no

# AC7 is a conjunction — question, DESTINATION, wiring — and the needle above pins only the
# first. Delete the fenced-block line and every validator stays green while `init` is left to
# infer where the answer goes; a `- Target:` written into the wrong file resolves to nothing
# and is discarded in silence, which is the failure the line was added to close. Found in
# review, in the same shape the `- Mode:` entry still carries.
r=$(contracts_repo contracts-notarget-dest)
python3 - "$r" <<'PYEOF'
import pathlib, sys
p = pathlib.Path(sys.argv[1], "skills", "init", "SKILL.md")
needle = "- Target: <minimum|full — the set the operator chose, read only while Mode is bootstrap"
src = p.read_text()
if needle not in src:
    raise SystemExit("fixture no-op: the Target line is not in the machine-read block")
p.write_text(src.replace(needle, "- Target: <the chosen set"))
PYEOF
out=$(run_contracts "$r"); err=$(cat "$TMP/cerr")
[ "$out" = "1" ] && c5=ok || c5=no
# The NEEDLE, not the word "Target": this file carries two Target pins now, and the looser cue
# is satisfied by the other one firing. Same reason case 54 asserts both halves.
case "$err" in *"read only while Mode is bootstrap"*) c6=ok ;; *) c6=no ;; esac

[ "$c1$c2$c3$c4$c5$c6" = "okokokokokok" ] \
  && report "init stripped of the target question or its destination fails, naming the file and the key" ok \
  || report "init stripped of the target question or its destination fails, naming the file and the key" no \
     "notarget-exit=$c1 names-file=$c2 names-key=$c3 control=$c4 nodest-exit=$c5 nodest-names-key=$c6"


# --- shipped reviewers: the contract path they name -----------------------------------
#
# #82. A reference reviewer's FIRST instruction is "Read the reviewer contract first", and the
# contract it points at tells a reviewer that cannot find it to say so and stop. So a path that
# does not resolve does not degrade the review — it ends it, and the failure is
# indistinguishable from a careful reviewer being careful. CAP-1, falsified at install time.
#
# Resolution is judged FROM THE PROJECT ROOT, and that is the whole of this case. A reviewer
# reads its own instruction as a tool-using agent whose working directory is the project root,
# not the directory its own file sits in. Judging from the agents directory is what let the
# first cut of this branch pass a reviewer naming `_shared/reviewer-contract.md` alone — a path
# that resolves from neither root, and whose obvious guess (`agents/_shared/`) lands on the
# plugin's copy rather than the install's.

# $1 = repo name, $2 = the agents directory. Echoes the PROJECT ROOT.
install_reviewers() {
  r="$TMP/$1"; a="$r/$2"
  mkdir -p "$a/_shared"
  cp "$ROOT/agents/_shared/reviewer-contract.md" "$a/_shared/"
  cp "$ROOT/agents/ts-reviewer.md" "$ROOT/agents/python-reviewer.md" \
     "$ROOT/agents/dart-flutter-reviewer.md" "$a/"
  cp "$ROOT/agents/_template/reviewer.md" "$a/tpl-reviewer.md"
  echo "$r"
}

# $1 = project root, $2 = agents dir. Names every reviewer none of whose stated paths resolves
# from the project root. Prints nothing when every one of them can be opened.
unresolved() {
  python3 - "$1" "$2" <<'PYEOF'
import pathlib, re, sys
root, adir = pathlib.Path(sys.argv[1]), sys.argv[2]
for f in sorted((root / adir).glob("*reviewer.md")):
    stated = re.findall(r"[\w./-]*reviewer-contract\.md", f.read_text())
    if not stated:
        print(f"{f.name}: names no contract path"); continue
    if not any((root / s).exists() for s in stated):
        print(f"{f.name}: none of {sorted(set(stated))} resolves from the project root")
PYEOF
}

# 61. Every shipped reviewer resolves from the project root in both layouts, and a broken one
# is named.
#
# The template is the control and runs first: "the others are broken" is not evidence unless
# "the one that is right passes" sits beside it. The fifth copy is the accusing half, added
# after review observed that a passing-only case cannot distinguish "looked and found nothing"
# from "could not look" — G-4.
r=$(install_reviewers rv-claude ".claude/agents")
out=$(unresolved "$r" ".claude/agents")
case "$out" in *tpl-reviewer*) c0=no ;; *) c0=ok ;; esac
[ -z "$out" ] && c1=ok || c1=no

r=$(install_reviewers rv-antigravity ".agents")
out2=$(unresolved "$r" ".agents")
[ -z "$out2" ] && c2=ok || c2=no

r=$(install_reviewers rv-broken ".claude/agents")
printf 'x\n\nRead `agents/_shared/reviewer-contract.md` first.\n' > "$r/.claude/agents/bad-reviewer.md"
out3=$(unresolved "$r" ".claude/agents")
case "$out3" in *bad-reviewer*) c3=ok ;; *) c3=no ;; esac
case "$out3" in *ts-reviewer*|*tpl-reviewer*) c4=no ;; *) c4=ok ;; esac   # and ONLY that one

grep -q 'say so and stop' "$ROOT/agents/_shared/reviewer-contract.md" && c5=ok || c5=no

# The contract must be named in the FIRST instruction, not buried in a footnote. The rewrite of
# this case dropped the `Read \`…\`` anchor the old regex had, so position went unguarded — the
# third thing neither condition covered, and it moved in the wrong direction.
c6=ok
for f in "$ROOT"/agents/ts-reviewer.md "$ROOT"/agents/python-reviewer.md \
         "$ROOT"/agents/dart-flutter-reviewer.md "$ROOT"/agents/_template/reviewer.md; do
  grep -q '^\*\*Read the reviewer contract first\*\*.*_shared/reviewer-contract\.md' "$f" || c6=no
done

[ "$c0$c1$c2$c3$c4$c5$c6" = "okokokokokokok" ] && report "every shipped reviewer resolves from the project root, and a broken one is named" ok \
  || report "every shipped reviewer resolves from the project root, and a broken one is named" no \
     "template-control=$c0 claude=$c1 antigravity=$c2 accuses-broken=$c3 only-broken=$c4 stop-rule-intact=$c5 first-instruction=$c6 [$out|$out3]"


# --- guards: scripts/check-contract-path.py -------------------------------------------
#
# One fact — where the reviewer contract lives — was written in many places and nothing
# compared them, so it drifted into four forms and survived months of review. It surfaced only
# when `init` was run against a real project (#76). A fix that corrects them and leaves the
# comparison to review re-opens on the next edit, which is how it drifted in the first place.
#
# A NEW guard rather than an extension of check-receipt-schema.py: that one already has a
# subject, and #117 records what happens when a guard acquires a second with a different
# lifetime.

# $1 = name. A repo holding every file the guard compares, all in agreement.
cpath_repo() {
  r="$TMP/$1"
  mkdir -p "$r/scripts" "$r/agents/_shared" "$r/agents/_template" "$r/skills/init" "$r/docs" "$r/.claude/agents" "$r/rules"
  cp "$ROOT/scripts/check-contract-path.py" "$r/scripts/"
  chmod +x "$r/scripts/check-contract-path.py"
  rv='x\n\nRead `_shared/reviewer-contract.md`, beside this file: `.claude/agents/_shared/reviewer-contract.md` under Claude Code, `.agents/_shared/reviewer-contract.md` under Antigravity.\n'
  for f in ts python dart-flutter; do printf "$rv" > "$r/agents/$f-reviewer.md"; done
  printf "$rv" > "$r/agents/_template/reviewer.md"
  printf 'x\n' > "$r/agents/_shared/reviewer-contract.md"
  printf 'Read `.claude/agents/_shared/reviewer-contract.md` first.\n' > "$r/.claude/agents/gate-sdd-reviewer.md"
  printf 'copy `_shared/reviewer-contract.md` to it\n' > "$r/skills/init/SKILL.md"
  printf '  |-- _shared/reviewer-contract.md\n' > "$r/docs/layout.md"
  printf '"agents/_shared/reviewer-contract.md",\n' > "$r/scripts/check-receipt-schema.py"
  printf '`.claude/agents/_shared/reviewer-contract.md`\n' > "$r/docs/CONTRACT.md"
  printf '`_shared/reviewer-contract.md`\n' > "$r/AGENTS.md"
  ln -s ../AGENTS.md "$r/rules/AGENTS.md" 2>/dev/null || cp "$r/AGENTS.md" "$r/rules/AGENTS.md"
  echo "$r"
}
# stdout is CAPTURED, not discarded: case 64 asserts the success line does NOT print, and
# grepping stderr for a string that only ever reaches stdout is an assertion that cannot fail.
# Case 49 captures stdout for exactly this reason; this helper did not, and the mutation table
# in observations.md credited it with a catch it never made.
run_cpath() { ( cd "$1" && python3 scripts/check-contract-path.py >"$TMP/cpout" 2>"$TMP/cperr"; printf '%s' "$?" ) }

# 62. Agreement passes; ANY single file disagreeing fails and is named; a reviewer naming only
# the relative form fails for its own reason.
r=$(cpath_repo cp-control)
out=$(run_cpath "$r"); [ "$out" = "0" ] && c0=ok || c0=no

r=$(cpath_repo cp-reviewer)
printf 'Read `agents/_shared/reviewer-contract.md` first.\n' > "$r/agents/ts-reviewer.md"
out=$(run_cpath "$r"); err=$(cat "$TMP/cperr")
[ "$out" = "1" ] && c1=ok || c1=no
case "$err" in *ts-reviewer.md*) c2=ok ;; *) c2=no ;; esac

r=$(cpath_repo cp-template)
printf 'Read `../_shared/reviewer-contract.md` first.\n' > "$r/agents/_template/reviewer.md"
out=$(run_cpath "$r"); [ "$out" = "1" ] && c3=ok || c3=no

# The real defect's shape: a document drawing the flat sibling instead of the _shared/ form.
r=$(cpath_repo cp-layout)
printf '  |-- reviewer-contract.md\n' > "$r/docs/layout.md"
out=$(run_cpath "$r"); err=$(cat "$TMP/cperr")
[ "$out" = "1" ] && c4=ok || c4=no
case "$err" in *layout.md*) c5=ok ;; *) c5=no ;; esac

r=$(cpath_repo cp-sibling)
printf '".claude/agents/reviewer-contract.md",\n' > "$r/scripts/check-receipt-schema.py"
out=$(run_cpath "$r"); [ "$out" = "1" ] && c6=ok || c6=no

# A reviewer naming ONLY the relative form. This is what this branch's first cut shipped, and
# it failed its own review: a reviewer's working directory is the PROJECT ROOT, so that path
# resolves to nothing.
r=$(cpath_repo cp-relative-only)
printf 'Read `_shared/reviewer-contract.md` first.\n' > "$r/agents/ts-reviewer.md"
out=$(run_cpath "$r"); err=$(cat "$TMP/cperr")
[ "$out" = "1" ] && c7=ok || c7=no
case "$err" in *"does not name"*) c8=ok ;; *) c8=no ;; esac

# The ALLOWED check on its own. Every mutant above that removes it is ALSO caught by the
# concrete-path check, so without this sub-case that rule could be deleted with the suite
# green — a guard half that cannot fail. Here the reviewer names a valid concrete form AND a
# junk one, so the concrete check is satisfied and only ALLOWED can object.
r=$(cpath_repo cp-extra-form)
printf 'Read `.claude/agents/_shared/reviewer-contract.md`, or `vendor/reviewer-contract.md`.\n' > "$r/agents/ts-reviewer.md"
out=$(run_cpath "$r"); err=$(cat "$TMP/cperr")
[ "$out" = "1" ] && c9=ok || c9=no
case "$err" in *vendor*) c10=ok ;; *) c10=no ;; esac

# A SHIPPED reviewer naming only one destination. It satisfies ALLOWED and satisfies "at least
# one concrete form", so before the SHIPPED/INSTALLED split it passed — handing every
# Antigravity consumer a reviewer that cannot open its contract. That is #82's own shape
# narrowed to one harness, and two-harness correctness is why the issue's fix was overruled.
r=$(cpath_repo cp-one-harness)
printf 'Read `_shared/reviewer-contract.md`, at `.claude/agents/_shared/reviewer-contract.md`.\n' > "$r/agents/ts-reviewer.md"
out=$(run_cpath "$r"); err=$(cat "$TMP/cperr")
[ "$out" = "1" ] && c11=ok || c11=no
# The specific sentence, not the bare path: the failure epilogue enumerates CONCRETE on EVERY
# failure, so grepping for `.agents/_shared` alone was satisfied by the epilogue regardless of
# which problem fired — and saying WHICH destination is missing is the entire value of the
# SHIPPED rule. Second time on this branch that an assertion read the wrong text.
case "$err" in *"is shipped to both harnesses and does not name .agents/_shared"*) c12=ok ;; *) c12=no ;; esac

# …while the INSTALLED reviewer naming exactly one is correct and must stay green.
r=$(cpath_repo cp-install-one)
out=$(run_cpath "$r"); [ "$out" = "0" ] && c13=ok || c13=no

[ "$c0$c1$c2$c3$c4$c5$c6$c7$c8$c9$c10$c11$c12$c13" = "okokokokokokokokokokokokokok" ] && report "one contract placement, any file disagreeing is named, and a shipped reviewer must name both harnesses" ok \
  || report "one contract placement, any file disagreeing is named, and a shipped reviewer must name both harnesses" no \
     "control=$c0 reviewer-exit=$c1 names=$c2 template=$c3 layout-exit=$c4 names=$c5 sibling=$c6 relative-only=$c7 names-reason=$c8 extra-form=$c9 names-junk=$c10 one-harness=$c11 names-missing=$c12 install-one-ok=$c13"

# 63. A statement the guard cannot find or read is a THIRD outcome, never agreement.
r=$(cpath_repo cp-missing); rm "$r/docs/layout.md"
out=$(run_cpath "$r"); err=$(cat "$TMP/cperr")
[ "$out" = "1" ] && c1=ok || c1=no
case "$err" in *layout.md*) c2=ok ;; *) c2=no ;; esac

r=$(cpath_repo cp-silent); printf 'no mention here at all\n' > "$r/docs/layout.md"
out=$(run_cpath "$r"); err=$(cat "$TMP/cperr")
[ "$out" = "1" ] && c3=ok || c3=no
case "$err" in *"names no"*) c4=ok ;; *) c4=no ;; esac

r=$(cpath_repo cp-unreadable)
chmod 000 "$r/docs/layout.md" 2>/dev/null
if cat "$r/docs/layout.md" >/dev/null 2>&1; then
  chmod 644 "$r/docs/layout.md" 2>/dev/null
  c5=ok; c6=ok
  note_skip "contract-path/unreadable" "permissions not enforced here (running as root?)"
else
  out=$(run_cpath "$r"); err=$(cat "$TMP/cperr")
  chmod 644 "$r/docs/layout.md" 2>/dev/null
  [ "$out" = "1" ] && c5=ok || c5=no
  case "$err" in *"cannot be read"*) c6=ok ;; *) c6=no ;; esac
fi

[ "$c1$c2$c3$c4$c5$c6" = "okokokokokok" ] && report "a statement the contract guard cannot find or read fails, never agrees" ok \
  || report "a statement the contract guard cannot find or read fails, never agrees" no \
     "missing-exit=$c1 names=$c2 silent-exit=$c3 silent-msg=$c4 unreadable-exit=$c5 unreadable-msg=$c6"

# 64. An empty or shrunken work-set must fail, not print "0 source(s) agree".
#
# Case 49 pins this for check-receipt-schema.py's two tuples, and its comment says the new
# tuple there "arrived without the equivalent". This guard arrived the same way one release
# later, and review caught it: emptying SHIPPED leaves the three shipped reviewers uncompared
# while `3 source(s) agree` prints at exit 0 — the exact defect #82 exists for, passing.
#
# The mutation edits the COPY in the fixture, so it tests the shipped floor rather than a
# reimplementation of it.
shrink_cpath() {  # $1 = repo, $2 = the tuple to empty
  # Scans to the BALANCED closing paren rather than to a `)` at line start. The first cut used
  # `^NAME = \(.*?^\)`, which works for a multi-line tuple and silently runs past a ONE-LINE
  # one — it swallowed `EXACT = SHIPPED + INSTALLED` and the guard then died of NameError,
  # exiting 1 for the wrong reason and turning this case green while the floor it tests was
  # deleted. Third instance on this branch of a fixture failure wearing a guard failure's
  # clothes, so the result is now parsed before it is used.
  python3 - "$1" "$2" <<'PYEOF'
import ast, pathlib, re, sys
name = sys.argv[2]
p = pathlib.Path(sys.argv[1], "scripts", "check-contract-path.py")
src = p.read_text()
m = re.search(rf"^{name} = \(", src, flags=re.M)
if not m:
    raise SystemExit(f"fixture no-op: {name} tuple not found")
i, depth = m.end() - 1, 0
while i < len(src):
    if src[i] == "(":
        depth += 1
    elif src[i] == ")":
        depth -= 1
        if depth == 0:
            break
    i += 1
else:
    raise SystemExit(f"fixture broken: {name} tuple never closes")
out = src[: m.start()] + f"{name} = ()" + src[i + 1 :]
try:
    ast.parse(out)
except SyntaxError as exc:
    raise SystemExit(f"fixture broken: shrinking {name} produced unparseable source ({exc})")
p.write_text(out)
PYEOF
}

r=$(cpath_repo cp-empty-shipped)
if shrink_cpath "$r" SHIPPED; then cf=ok; else cf=no; fi
out=$(run_cpath "$r"); err=$(cat "$TMP/cperr")
{ [ "$out" = "1" ] && [ "$cf" = ok ]; } && c1=ok || c1=no
case "$err" in *floor*) c2=ok ;; *) c2=no ;; esac
sout=$(cat "$TMP/cpout")
case "$sout" in *"source(s) agree"*) c3=no ;; *) c3=ok ;; esac   # the success line must NOT print

r=$(cpath_repo cp-empty-suffix)
if shrink_cpath "$r" SUFFIX; then cf2=ok; else cf2=no; fi
out=$(run_cpath "$r"); err=$(cat "$TMP/cperr")
# The REASON, not just the exit code: a guard that dies during import also exits 1, and the
# floor these exist to test would be gone while the case read green. #124's own pattern, and
# two of its instances were in the commit that filed it.
{ [ "$out" = "1" ] && [ "$cf2" = ok ]; } && c4=ok || c4=no
case "$err" in *Traceback*) c4=no ;; esac
case "$err" in *floor*) : ;; *) c4=no ;; esac

# The INSTALLED clause was pinned by nothing: delete it and the suite stayed green, after which
# emptying INSTALLED drops this repository's own reviewer out of the comparison and prints
# "9 source(s) agree" at exit 0 — the dogfood file leaving the guard silently, which is the very
# reason it was added.
r=$(cpath_repo cp-empty-installed)
if shrink_cpath "$r" INSTALLED; then cf3=ok; else cf3=no; fi
out=$(run_cpath "$r"); err=$(cat "$TMP/cperr")
{ [ "$out" = "1" ] && [ "$cf3" = ok ]; } && c5=ok || c5=no
case "$err" in *Traceback*) c5=no ;; esac
case "$err" in *floor*) : ;; *) c5=no ;; esac

# A duplicate satisfies a floor that counts entries while displacing the name it replaced.
r=$(cpath_repo cp-dupe)
python3 - "$r" <<'PYEOF'
import pathlib, sys
p = pathlib.Path(sys.argv[1], "scripts", "check-contract-path.py")
src = p.read_text()
out = src.replace('"agents/python-reviewer.md",', '"agents/ts-reviewer.md",')
if out == src:
    raise SystemExit("fixture no-op: python-reviewer entry not found")
p.write_text(out)
PYEOF
out=$(run_cpath "$r"); err=$(cat "$TMP/cperr")
[ "$out" = "1" ] && c6=ok || c6=no
case "$err" in *duplicate*) c7=ok ;; *) c7=no ;; esac

# An entry moved to the tuple with the weaker obligation — a one-line diff that reads as tidying
# and hands back round 2's HIGH.
r=$(cpath_repo cp-misgrouped)
python3 - "$r" <<'PYEOF'
import pathlib, sys
p = pathlib.Path(sys.argv[1], "scripts", "check-contract-path.py")
src = p.read_text()
out = src.replace('INSTALLED = (".claude/agents/gate-sdd-reviewer.md",)',
                  'INSTALLED = (".claude/agents/gate-sdd-reviewer.md", "agents/ts-reviewer.md")')
if out == src:
    raise SystemExit("fixture no-op: INSTALLED tuple not found")
p.write_text(out)
PYEOF
out=$(run_cpath "$r"); err=$(cat "$TMP/cperr")
[ "$out" = "1" ] && c8=ok || c8=no
case "$err" in *"only an install may name one destination"*) c9=ok ;; *) c9=no ;; esac

# A non-reviewer padding SHIPPED to hold the floor while a real reviewer leaves it. Floors and
# distinctness both pass; only the prefix clause can object. This is the mutation demonstrated
# in round 3 — pad the tuple, move the reviewer — and it was caught by nothing.
r=$(cpath_repo cp-misgrouped-shipped)
python3 - "$r" <<'PYEOF'
import pathlib, sys
p = pathlib.Path(sys.argv[1], "scripts", "check-contract-path.py")
src = p.read_text()
out = src.replace('"agents/ts-reviewer.md",', '"docs/layout.md",')
if out == src:
    raise SystemExit("fixture no-op: ts-reviewer entry not found")
p.write_text(out)
PYEOF
out=$(run_cpath "$r"); err=$(cat "$TMP/cperr")
[ "$out" = "1" ] && c10=ok || c10=no
case "$err" in *"does not live under"*) c11=ok ;; *) c11=no ;; esac

# And a reviewer demoted into SUFFIX, where only the canonical suffix is required — the rule
# under which `agents/_shared/reviewer-contract.md`, the original defect, passes.
r=$(cpath_repo cp-reviewer-in-suffix)
if python3 - "$r" <<'PYEOF'
import pathlib, sys
p = pathlib.Path(sys.argv[1], "scripts", "check-contract-path.py")
src = p.read_text()
needle = '    "docs/CONTRACT.md",'
out = src.replace(needle, needle + '\n    "agents/ts-reviewer.md",')
if out == src:
    raise SystemExit("fixture no-op: docs/CONTRACT.md entry not found")
p.write_text(out)
PYEOF
then cf4=ok; else cf4=no; fi
out=$(run_cpath "$r"); err=$(cat "$TMP/cperr")
{ [ "$out" = "1" ] && [ "$cf4" = ok ]; } && c12b=ok || c12b=no
case "$err" in *"sits in SUFFIX"*) c13b=ok ;; *) c13b=no ;; esac

[ "$c1$c2$c3$c4$c5$c6$c7$c8$c9$c10$c11$c12b$c13b" = "okokokokokokokokokokokokok" ] && report "an empty, duplicated or misgrouped contract-path work-set fails rather than agreeing" ok \
  || report "an empty, duplicated or misgrouped contract-path work-set fails rather than agreeing" no \
     "shipped-exit=$c1 says-floor=$c2 no-success-line=$c3 suffix-exit=$c4 installed-exit=$c5 dupe-exit=$c6 says-dupe=$c7 misgrouped-exit=$c8 says-group=$c9 pad-shipped=$c10 says-prefix=$c11 reviewer-in-suffix=$c12b says-suffix=$c13b"


# --- guards: scripts/check-readme-claims.py -------------------------------------------
#
# #115. Three claims in the README's Status section were false at once, by three different
# mechanisms. The version is the instructive one: it survived three releases AND an edit to the
# same file, because nothing tied it to the manifest bump — check-manifests.py verifies the two
# manifests against each other and knows nothing about the README.
#
# The guard deliberately does NOT check a count of gate behaviours. That number's only source is
# running test-gates.sh, already the slowest validator, so it was removed from the README instead
# — and the guard fails if it comes back, because a check that only verifies what is present
# cannot notice a removed claim returning.

# $1 = name. A repo whose README agrees with its sources.
readme_repo() {
  r="$TMP/$1"; mkdir -p "$r/scripts" "$r/.specs/9-feature" "$r/.specs/_archive/8-old"
  cp "$ROOT/scripts/check-readme-claims.py" "$r/scripts/"
  chmod +x "$r/scripts/check-readme-claims.py"
  printf '{\n  "version": "1.2.3"\n}\n' > "$r/plugin.json"
  printf 'reviewed_by=subagent\n' > "$r/.specs/9-feature/.review-receipt"
  printf 'reviewed_by=inline\n' > "$r/.specs/_archive/8-old/.review-receipt"
  # Heredocs, not printf: the badge URL is full of `%` escapes and printf would eat them, which
  # is a fixture quietly writing a DIFFERENT badge than the one under test. #141 shipped a `case`
  # glob with the same class of bug — unquoted backticks — and it cost a red run to find.
  cat > "$r/README.md" <<'RMEOF'
# fixture

[![gate-sdd](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2Fm0m0i%2Fgate-oriented-sdd%2Fmain%2Fplugin.json&query=%24.version&prefix=v&label=gate-sdd&color=blue)](./plugin.json)

## Status

**Pre-release.**

the gates and guards behaviours, tested deterministically; and a receipt on every spec from a spawned reviewer on all but one, which were reviewed inline.

Tested against: Antigravity CLI 1.1.17, Antigravity IDE 2.3.1.
RMEOF
  cat > "$r/README.ja.md" <<'RMEOF'
# fixture

[![gate-sdd](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2Fm0m0i%2Fgate-oriented-sdd%2Fmain%2Fplugin.json&query=%24.version&prefix=v&label=gate-sdd&color=blue)](./plugin.json)

## Status

**Pre-release です。**

ゲートとガードの挙動。1件を除いてサブエージェントとして起動した reviewer によるレビューです。
RMEOF
  echo "$r"
}
run_readme() { ( cd "$1" && python3 scripts/check-readme-claims.py >/dev/null 2>"$TMP/rmerr"; printf '%s' "$?" ) }

# 65. Each of the three claims, in each language, and the control first.
r=$(readme_repo rm-control)
out=$(run_readme "$r"); [ "$out" = "0" ] && c0=ok || c0=no

# #133. The version is no longer a claim the README makes, so there is no mismatch to detect.
# There is a BADGE, and the guard's job is now that the badge is still the thing that makes a
# mismatch impossible. Removing it must fail: a README carrying neither a version nor a badge
# tells the reader nothing, and a guard that shrugged at that would have stopped covering this
# claim while still exiting 0.
r=$(readme_repo rm-nobadge)
python3 - "$r" <<'PYEOF'
import pathlib, sys
p = pathlib.Path(sys.argv[1], "README.md"); src = p.read_text()
out = "\n".join(l for l in src.split("\n") if "img.shields.io" not in l)
if out == src: raise SystemExit("fixture no-op: no badge line to remove")
p.write_text(out)
PYEOF
[ "$?" = 0 ] && cf1=ok || cf1=no
out=$(run_readme "$r"); err=$(cat "$TMP/rmerr")
{ [ "$out" = "1" ] && [ "$cf1" = ok ]; } && c1=ok || c1=no
case "$err" in *"no badge labelled \`gate-sdd\`"*) c2=ok ;; *) c2=no ;; esac

# The removed number coming back — the half a presence-only check cannot see.
r=$(readme_repo rm-count)
python3 - "$r" <<'PYEOF'
import pathlib, sys
p = pathlib.Path(sys.argv[1], "README.md"); src = p.read_text()
out = src.replace("the gates and guards behaviours", "the gates and guards' 99 behaviours")
if out == src: raise SystemExit("fixture no-op: behaviours phrase not found")
p.write_text(out)
PYEOF
[ "$?" = 0 ] && cf2=ok || cf2=no
out=$(run_readme "$r"); err=$(cat "$TMP/rmerr")
{ [ "$out" = "1" ] && [ "$cf2" = ok ]; } && c3=ok || c3=no
case "$err" in *"removed on purpose"*) c4=ok ;; *) c4=no ;; esac

# The receipt count, in each language independently.
r=$(readme_repo rm-receipts-en)
printf 'reviewed_by=inline\n' > "$r/.specs/9-feature/.review-receipt"   # now 2 inline, README says one
out=$(run_readme "$r"); err=$(cat "$TMP/rmerr")
[ "$out" = "1" ] && c5=ok || c5=no
case "$err" in *"2 of 2 say reviewed_by=inline"*) c6=ok ;; *) c6=no ;; esac

r=$(readme_repo rm-receipts-ja)
python3 - "$r" <<'PYEOF'
import pathlib, sys
p = pathlib.Path(sys.argv[1], "README.ja.md"); src = p.read_text()
out = src.replace("1件を除いて", "5件を除いて")
if out == src: raise SystemExit("fixture no-op: JA receipt phrase not found")
p.write_text(out)
PYEOF
[ "$?" = 0 ] && cf3=ok || cf3=no
out=$(run_readme "$r"); err=$(cat "$TMP/rmerr")
{ [ "$out" = "1" ] && [ "$cf3" = ok ]; } && c7=ok || c7=no
# The receipt-count message specifically: README.ja.md appears in this guard's output for a
# missing file, a missing version, a version mismatch and a behaviour count too, so the filename
# alone cannot tell this assertion from any of those. Every sibling here pins its own text.
case "$err" in *"but 1 of 2 say reviewed_by=inline"*) c8=ok ;; *) c8=no ;; esac

[ "$c0$c1$c2$c3$c4$c5$c6$c7$c8" = "okokokokokokokokok" ] && report "each README Status claim disagreeing with its source is named" ok \
  || report "each README Status claim disagreeing with its source is named" no \
     "control=$c0 nobadge-exit=$c1 names-label=$c2 count-exit=$c3 says-removed=$c4 receipts-en=$c5 names-count=$c6 receipts-ja=$c7 names-file=$c8"

# 65b. A STATIC badge is the drift returning, and must not be reported as a missing one.
#
# #133 AC3. This is the deletion review cannot defend: a static badge renders faster, has no
# third-party JSON fetch, and looks like a simplification — while what it restores is exactly
# the hand-edited number this issue removed. Reported as its own cause, because "carries no
# version badge" sends the next author to add the badge they can already see.
r=$(readme_repo rm-staticbadge)
python3 - "$r" <<'PYEOF'
import pathlib, sys
import re
root = sys.argv[1]
# An EMPTY root is not "the current directory" — it is a fixture that never got built, and
# every path below then resolves against the repository itself. This case rewrote the real
# README.md exactly that way once. Refuse rather than edit something nobody meant to edit.
if not root:
    raise SystemExit("fixture no-op: empty repo path — readme_repo did not run")
p = pathlib.Path(root, "README.md"); src = p.read_text()
out = re.sub(r"https://img\.shields\.io/[^\s)\]]+",
             "https://img.shields.io/badge/gate--sdd-v1.2.3-blue", src)
if out == src: raise SystemExit("fixture no-op: no shields badge to replace")
p.write_text(out)
PYEOF
[ "$?" = 0 ] && cf5=ok || cf5=no
out=$(run_readme "$r"); err=$(cat "$TMP/rmerr")
{ [ "$out" = "1" ] && [ "$cf5" = ok ]; } && s1=ok || s1=no
case "$err" in *static*) s2=ok ;; *) s2=no ;; esac
# It must NOT be diagnosed as absence — that is the wrong remedy for a badge that is present.
case "$err" in *"no badge labelled"*) s3=no ;; *) s3=ok ;; esac

# A non-version shields badge alongside the real one is fine. Without this, "a static badge
# fails" is satisfiable by a guard that rejects every badge but one, and a licence or CI badge
# added later would go red for no reason — LV-2, a gate firing on an ordinary edit.
r=$(readme_repo rm-otherbadge)
python3 - "$r" <<'PYEOF'
import pathlib, sys
root = sys.argv[1]
if not root:
    raise SystemExit("fixture no-op: empty repo path — readme_repo did not run")
p = pathlib.Path(root, "README.md"); src = p.read_text()
extra = "[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)\n"
out = src.replace("## Status", extra + "\n## Status")
if out == src: raise SystemExit("fixture no-op: no Status heading")
p.write_text(out)
PYEOF
[ "$?" = 0 ] && cf6=ok || cf6=no
out=$(run_readme "$r")
{ [ "$out" = "0" ] && [ "$cf6" = ok ]; } && s4=ok || s4=no

[ "$s1$s2$s3$s4" = "okokokok" ] \
  && report "a static version badge fails as a substitution, and an unrelated badge does not" ok \
  || report "a static version badge fails as a substitution, and an unrelated badge does not" no \
     "static-red=$s1 says-static=$s2 not-called-absent=$s3 other-badge-green=$s4"

# 65b-ii. shields' OTHER static form — the label as a query parameter, unescaped.
#
# Found in review, as a regression the label tie introduced. `/static/v1?label=gate-sdd&
# message=v1.2.3` spells the label plainly, where `/badge/gate--sdd-v1.2.3-blue` escapes the
# hyphen. This is the likelier substitution of the two: the badge already in the README
# carries `label=` as a query parameter, so an author editing that URL reaches this form
# first. Matching only the escaped spelling gave it the right verdict with the wrong remedy.
# Inlined rather than using `mutate_badge`: that helper is defined in case 65c, BELOW this
# point, and a call to an undefined function yields an empty `$r` whose fixture edits land on
# the repository itself. That happened once on this branch already.
r=$(readme_repo rm-static-query)
python3 - "$r" <<'PYEOF'
import pathlib, re, sys
root = sys.argv[1]
if not root:
    raise SystemExit("fixture no-op: empty repo path — readme_repo did not run")
p = pathlib.Path(root, "README.md"); src = p.read_text()
out = re.sub(r"https://img\.shields\.io/[^\s)\]]+",
             "https://img.shields.io/static/v1?label=gate-sdd&message=v1.2.3&color=blue", src)
if out == src:
    raise SystemExit("fixture no-op: no shields badge to replace")
p.write_text(out)
PYEOF
[ "$?" = 0 ] && cfi=ok || cfi=no
out=$(run_readme "$r"); err=$(cat "$TMP/rmerr")
{ [ "$out" = "1" ] && [ "$cfi" = ok ]; } && q1=ok || q1=no
# The guard's PHRASE, not the bare word: this fixture's own URL contains `/static/v1`, so
# `*static*` would stay green against a reworded message that quoted the badge and no longer
# said it. An assertion coupled to text it does not own is what cost rounds 2 and 3.
case "$err" in *"version badge is static"*) q2=ok ;; *) q2=no ;; esac
case "$err" in *"no badge labelled"*) q3=no ;; *) q3=ok ;; esac

[ "$q1$q2$q3" = "okokok" ] \
  && report "the query-parameter static form is named as a substitution, not as an absence" ok \
  || report "the query-parameter static form is named as a substitution, not as an absence" no \
     "red=$q1 says-static=$q2 not-called-absent=$q3"


# 65c. The dynamic badge must read THIS repository's manifest, and must survive reordering.
#
# #133 AC4. "Dynamic" alone is not the property that matters — a dynamic badge pointed at a
# fork, at another branch, or at `.claude-plugin/plugin.json` still renders a number, and a
# wrong number rendered confidently is worse than none. The guard therefore parses the URL.
#
# The green half is the one that keeps this from being a gate people switch off: query strings
# get reordered by editors and by hand, and a guard matching the whole URL literally would fail
# on a change that alters nothing. LV-2 — a gate that fires on an ordinary edit gets disabled.
mutate_badge() {   # $1 = repo, $2 = replacement URL
  python3 - "$1" "$2" <<'PYEOF'
import pathlib, re, sys
root, repl = sys.argv[1], sys.argv[2]
if not root:
    raise SystemExit("fixture no-op: empty repo path — readme_repo did not run")
p = pathlib.Path(root, "README.md"); src = p.read_text()
out = re.sub(r"https://img\.shields\.io/[^\s)\]]+", repl.replace("\\", "\\\\"), src)
if out == src:
    raise SystemExit("fixture no-op: no shields badge to replace")
p.write_text(out)
PYEOF
}

base="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2Fm0m0i%2Fgate-oriented-sdd%2Fmain%2Fplugin.json&query=%24.version&prefix=v&label=gate-sdd&color=blue"

# Another owner's manifest.
r=$(readme_repo rm-badge-fork)
mutate_badge "$r" "https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2Fsomeone-else%2Fgate-oriented-sdd%2Fmain%2Fplugin.json&query=%24.version&label=gate-sdd"
[ "$?" = 0 ] && cf7=ok || cf7=no
out=$(run_readme "$r"); err=$(cat "$TMP/rmerr")
{ [ "$out" = "1" ] && [ "$cf7" = ok ]; } && u1=ok || u1=no
case "$err" in *someone-else*) u2=ok ;; *) u2=no ;; esac

# The right repo, the wrong file — the near miss a human eye slides over.
r=$(readme_repo rm-badge-path)
mutate_badge "$r" "https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2Fm0m0i%2Fgate-oriented-sdd%2Fmain%2F.claude-plugin%2Fplugin.json&query=%24.version&label=gate-sdd"
[ "$?" = 0 ] && cf8=ok || cf8=no
out=$(run_readme "$r"); err=$(cat "$TMP/rmerr")
{ [ "$out" = "1" ] && [ "$cf8" = ok ]; } && u3=ok || u3=no
# The path, not just the exit code: if the label selection broke, this fixture would
# exit 1 through the ABSENCE branch and this half would stay green for the wrong cause.
case "$err" in *".claude-plugin"*) u3b=ok ;; *) u3b=no ;; esac

# Asking for the wrong FIELD renders someone else's value under a version label.
r=$(readme_repo rm-badge-query)
mutate_badge "$r" "https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2Fm0m0i%2Fgate-oriented-sdd%2Fmain%2Fplugin.json&query=%24.name&label=gate-sdd"
[ "$?" = 0 ] && cf9=ok || cf9=no
out=$(run_readme "$r"); err=$(cat "$TMP/rmerr")
{ [ "$out" = "1" ] && [ "$cf9" = ok ]; } && u4=ok || u4=no
case "$err" in *'asks for `$.name`'*) u4b=ok ;; *) u4b=no ;; esac

# GREEN: the same badge with its parameters in a different order must pass.
r=$(readme_repo rm-badge-reorder)
mutate_badge "$r" "https://img.shields.io/badge/dynamic/json?label=gate-sdd&color=blue&query=%24.version&prefix=v&url=https%3A%2F%2Fraw.githubusercontent.com%2Fm0m0i%2Fgate-oriented-sdd%2Fmain%2Fplugin.json"
[ "$?" = 0 ] && cfa=ok || cfa=no
out=$(run_readme "$r")
{ [ "$out" = "0" ] && [ "$cfa" = ok ]; } && u5=ok || u5=no

[ "$u1$u2$u3$u3b$u4$u4b$u5" = "okokokokokokok" ] \
  && report "a dynamic badge reading the wrong source fails, and reordering its parameters does not" ok \
  || report "a dynamic badge reading the wrong source fails, and reordering its parameters does not" no \
     "fork-red=$u1 names-owner=$u2 wrong-path-red=$u3 names-path=$u3b wrong-query-red=$u4 names-query=$u4b reorder-green=$u5"

# 65d. The literal coming back is the root cause returning, and must fail.
#
# #133 AC5. The badge removes the SECOND SOURCE; it does not stop anyone adding one. An editor
# who reads the badge as decoration writes the number back into the prose, the two can disagree
# again, and every check above still passes because the badge is untouched. This is the same
# hole #115 found in a presence-only check: a guard that verifies what is there cannot notice
# a removed claim coming back.
r=$(readme_repo rm-literal-back)
python3 - "$r" <<'PYEOF'
import pathlib, sys
root = sys.argv[1]
if not root:
    raise SystemExit("fixture no-op: empty repo path — readme_repo did not run")
p = pathlib.Path(root, "README.md"); src = p.read_text()
out = src.replace("**Pre-release.**", "**v1.2.3 — pre-release.**")
if out == src:
    raise SystemExit("fixture no-op: the Status line is not where this expects it")
p.write_text(out)
PYEOF
[ "$?" = 0 ] && cfb=ok || cfb=no
out=$(run_readme "$r"); err=$(cat "$TMP/rmerr")
{ [ "$out" = "1" ] && [ "$cfb" = ok ]; } && l1=ok || l1=no
case "$err" in *"states a version"*) l2=ok ;; *) l2=no ;; esac
# It fails even though the number happens to be RIGHT. Agreement today is not the property —
# two sources that can diverge tomorrow is the defect, and a check that only fired on a
# mismatch would wait for the drift it exists to prevent.
case "$err" in *"1.2.3"*) l3=ok ;; *) l3=no ;; esac

# The Japanese form differs after the number, so it needs its own case rather than an
# assumption that one pattern covers both.
r=$(readme_repo rm-literal-back-ja)
python3 - "$r" <<'PYEOF'
import pathlib, sys
root = sys.argv[1]
if not root:
    raise SystemExit("fixture no-op: empty repo path — readme_repo did not run")
p = pathlib.Path(root, "README.ja.md"); src = p.read_text()
out = src.replace("**Pre-release です。**", "**v1.2.3、pre-release です。**")
if out == src:
    raise SystemExit("fixture no-op: the JA Status line is not where this expects it")
p.write_text(out)
PYEOF
[ "$?" = 0 ] && cfc=ok || cfc=no
out=$(run_readme "$r"); err=$(cat "$TMP/rmerr")
{ [ "$out" = "1" ] && [ "$cfc" = ok ]; } && l4=ok || l4=no
case "$err" in *"README.ja.md: states a version"*) l5=ok ;; *) l5=no ;; esac

# The literal WITHOUT a trailing delimiter. The first cut of the prohibition required a space
# or a Japanese comma after the number, so `**v1.2.3**` walked straight through — the root
# cause returning in a slightly different costume. Dropping that requirement is a behaviour
# change, and a behaviour change with no case that reddens when it is reverted is a check that
# can stop checking in silence. G-4, found in review.
r=$(readme_repo rm-literal-bold)
python3 - "$r" <<'PYEOF'
import pathlib, sys
root = sys.argv[1]
if not root:
    raise SystemExit("fixture no-op: empty repo path — readme_repo did not run")
p = pathlib.Path(root, "README.md"); src = p.read_text()
out = src.replace("**Pre-release.**", "**v1.2.3**")
if out == src:
    raise SystemExit("fixture no-op: the Status line is not where this expects it")
p.write_text(out)
PYEOF
[ "$?" = 0 ] && cff=ok || cff=no
out=$(run_readme "$r"); err=$(cat "$TMP/rmerr")
{ [ "$out" = "1" ] && [ "$cff" = ok ]; } && l6=ok || l6=no
case "$err" in *"states a version"*) l7=ok ;; *) l7=no ;; esac

# ...and the other direction, which is why the pattern keeps its `**v` prefix. `readme_repo`
# now carries a `Tested against: … 1.1.17` line, and this fixture adds a bare number EQUAL to
# the manifest version — the hardest case for a broadened pattern, because the digits are
# exactly the ones the badge renders. Both must stay green: a version stated about something
# else is a different claim, and a prohibition that fired on them would be a gate people
# switch off. Distinct from `rm-control`, which carries only the first of the two.
r=$(readme_repo rm-bare-version)
python3 - "$r" <<'PYEOF'
import pathlib, sys
root = sys.argv[1]
if not root:
    raise SystemExit("fixture no-op: empty repo path — readme_repo did not run")
p = pathlib.Path(root, "README.md"); src = p.read_text()
out = src.replace("Tested against:", "Built from 1.2.3 of the compiler. Tested against:")
if out == src:
    raise SystemExit("fixture no-op: the tested-against line is not where this expects it")
p.write_text(out)
PYEOF
[ "$?" = 0 ] && cfg=ok || cfg=no
out=$(run_readme "$r")
{ [ "$out" = "0" ] && [ "$cfg" = ok ]; } && l8=ok || l8=no

[ "$l1$l2$l3$l4$l5$l6$l7$l8" = "okokokokokokokok" ] \
  && report "a version literal returning to either README fails, even when it happens to agree" ok \
  || report "a version literal returning to either README fails, even when it happens to agree" no \
     "en-red=$l1 says-states=$l2 names-value=$l3 ja-red=$l4 names-ja-file=$l5 bold-no-delimiter-red=$l6 says-states-bold=$l7 bare-number-green=$l8"

# 65e. A dynamic badge that is not the VERSION badge must not be judged as one.
#
# Found in review. The first cut selected every badge containing `/badge/dynamic/` and then
# required each to read plugin.json's `$.version` — so the subject was "any dynamic badge"
# while AC4's subject is "the version badge". C2 declined a wider badge row only for now, so
# the next badge is a live possibility, and a dynamic one measuring anything else would have
# gone red for an edit that broke nothing. G-6: a widening needs an argument AND a case in the
# direction it can fire wrongly. Case 65b's unrelated badge is STATIC, so it never covered this.
r=$(readme_repo rm-dynamic-other)
python3 - "$r" <<'PYEOF'
import pathlib, sys
root = sys.argv[1]
if not root:
    raise SystemExit("fixture no-op: empty repo path — readme_repo did not run")
p = pathlib.Path(root, "README.md"); src = p.read_text()
extra = ("[![docs](https://img.shields.io/badge/dynamic/json"
         "?url=https%3A%2F%2Fexample.invalid%2Fstats.json&query=%24.pages&label=docs)](./docs)\n")
out = src.replace("## Status", extra + "\n## Status")
if out == src:
    raise SystemExit("fixture no-op: no Status heading")
p.write_text(out)
PYEOF
[ "$?" = 0 ] && cfd=ok || cfd=no
out=$(run_readme "$r"); err=$(cat "$TMP/rmerr")
{ [ "$out" = "0" ] && [ "$cfd" = ok ]; } && d1=ok || d1=no
case "$err" in *example.invalid*) d2=no ;; *) d2=ok ;; esac

# ...and selecting by label must still FAIL CLOSED. Renaming the version badge's label leaves
# no version badge at all, which is the absence branch — not a silent pass because the
# selector matched nothing. This is the half that makes the narrowing safe.
r=$(readme_repo rm-badge-relabel)
python3 - "$r" <<'PYEOF'
import pathlib, sys
root = sys.argv[1]
if not root:
    raise SystemExit("fixture no-op: empty repo path — readme_repo did not run")
p = pathlib.Path(root, "README.md"); src = p.read_text()
out = src.replace("label=gate-sdd", "label=whatever")
if out == src:
    raise SystemExit("fixture no-op: the badge label is not where this expects it")
p.write_text(out)
PYEOF
[ "$?" = 0 ] && cfe=ok || cfe=no
out=$(run_readme "$r"); err=$(cat "$TMP/rmerr")
{ [ "$out" = "1" ] && [ "$cfe" = ok ]; } && d3=ok || d3=no
case "$err" in *"no badge labelled \`gate-sdd\`"*) d4=ok ;; *) d4=no ;; esac

[ "$d1$d2$d3$d4" = "okokokok" ] \
  && report "an unrelated dynamic badge passes, and relabelling the version badge fails closed" ok \
  || report "an unrelated dynamic badge passes, and relabelling the version badge fails closed" no \
     "other-dynamic-green=$d1 not-accused=$d2 relabel-red=$d3 says-absent=$d4"

# 65f. A foreign versioned badge is not this repo's version badge gone static.
#
# Found in review. `baked` selected any shields badge whose last segment carried a version, so
# a README that had genuinely LOST its version badge while carrying, say, `node-v18.0.0-green`
# was told the version badge had gone static — sending the author to fix a badge that was
# never the subject. The remedy matters more than the verdict here: both outcomes are exit 1,
# and only the message tells the reader what to do.
r=$(readme_repo rm-foreign-version-badge)
python3 - "$r" <<'PYEOF'
import pathlib, sys
root = sys.argv[1]
if not root:
    raise SystemExit("fixture no-op: empty repo path — readme_repo did not run")
p = pathlib.Path(root, "README.md"); src = p.read_text()
kept = [l for l in src.split("\n") if "img.shields.io" not in l]
if len(kept) == len(src.split("\n")):
    raise SystemExit("fixture no-op: no badge line to remove")
body = "\n".join(kept)
out = body.replace(
    "## Status",
    "[![node](https://img.shields.io/badge/node-v18.0.0-green)](https://nodejs.org)\n\n## Status",
)
# Checked, like every sibling: without this the fixture degenerates into rm-nobadge if the
# heading ever moves, and all four halves go green having tested nothing.
if out == body:
    raise SystemExit("fixture no-op: no Status heading to insert before")
p.write_text(out)
PYEOF
[ "$?" = 0 ] && cfh=ok || cfh=no
out=$(run_readme "$r"); err=$(cat "$TMP/rmerr")
{ [ "$out" = "1" ] && [ "$cfh" = ok ]; } && f1=ok || f1=no
# The ABSENCE remedy, because that is what is actually wrong: this README has no gate-sdd
# badge. Being told a badge it does not have went static is the wrong instruction.
case "$err" in *"no badge labelled"*) f2=ok ;; *) f2=no ;; esac
case "$err" in *static*) f3=no ;; *) f3=ok ;; esac
# ...and the node badge must not be named as though it were the subject.
case "$err" in *node*) f4=no ;; *) f4=ok ;; esac

[ "$f1$f2$f3$f4" = "okokokok" ] \
  && report "a foreign versioned badge is diagnosed as an absent version badge, not a static one" ok \
  || report "a foreign versioned badge is diagnosed as an absent version badge, not a static one" no \
     "red=$f1 says-absent=$f2 not-called-static=$f3 does-not-name-node=$f4"


# 66. A source the guard cannot read is a THIRD outcome, never agreement.
r=$(readme_repo rm-nomanifest); rm "$r/plugin.json"
out=$(run_readme "$r"); [ "$out" = "1" ] && c1=ok || c1=no

r=$(readme_repo rm-noreceipts); rm -rf "$r/.specs"
out=$(run_readme "$r"); err=$(cat "$TMP/rmerr")
[ "$out" = "1" ] && c2=ok || c2=no
case "$err" in *"no review receipts"*) c3=ok ;; *) c3=no ;; esac   # not "nothing to check"

r=$(readme_repo rm-nojp); rm "$r/README.ja.md"
out=$(run_readme "$r"); [ "$out" = "1" ] && c4=ok || c4=no

# A README that stops making the claim at all — the quiet half.
r=$(readme_repo rm-silent)
printf '## Status\n\n**v1.2.3 — pre-release.**\n\nnothing about receipts here.\n' > "$r/README.md"
out=$(run_readme "$r"); err=$(cat "$TMP/rmerr")
[ "$out" = "1" ] && c5=ok || c5=no
case "$err" in *"does not say how many"*) c6=ok ;; *) c6=no ;; esac

[ "$c1$c2$c3$c4$c5$c6" = "okokokokokok" ] && report "a README claim whose source is missing fails rather than agreeing" ok \
  || report "a README claim whose source is missing fails rather than agreeing" no \
     "nomanifest=$c1 noreceipts-exit=$c2 says-none=$c3 nojp=$c4 silent-exit=$c5 silent-msg=$c6"


# 67. The behaviour count in the phrasings that actually shipped, and the receipt field's third
# state.
#
# The first cut of BEHAVIOUR_COUNT was written around the one sentence the spec was looking at —
# `guards' 67 behaviours` in `## Status`. A section above it said `67 paths across the gates and
# guards`, and the Japanese said `ゲートとガードを合わせた67通り`; the pattern matched neither, so
# the guard printed "no behaviour count asserted" over two files that asserted one, wrong by
# eleven. A fixture using the phrasing a regex was built around cannot catch that class, so these
# use the phrasings that were missed.
r=$(readme_repo rm-count-before)
python3 - "$r" <<'PYEOF'
import pathlib, sys
p = pathlib.Path(sys.argv[1], "README.md"); src = p.read_text()
out = src.replace("the gates and guards behaviours", "67 paths across the gates and guards")
if out == src: raise SystemExit("fixture no-op: behaviours phrase not found")
p.write_text(out)
PYEOF
then_ok=$?; [ "$then_ok" = 0 ] && cf1=ok || cf1=no
out=$(run_readme "$r"); err=$(cat "$TMP/rmerr")
{ [ "$out" = "1" ] && [ "$cf1" = ok ]; } && c1=ok || c1=no
case "$err" in *"67 paths across the gates"*) c2=ok ;; *) c2=no ;; esac

r=$(readme_repo rm-count-ja)
python3 - "$r" <<'PYEOF'
import pathlib, sys
p = pathlib.Path(sys.argv[1], "README.ja.md"); src = p.read_text()
out = src.replace("ゲートとガードの挙動。", "ゲートとガードを合わせた67通りの経路。")
if out == src: raise SystemExit("fixture no-op: JA behaviour phrase not found")
p.write_text(out)
PYEOF
[ "$?" = 0 ] && cf2=ok || cf2=no
out=$(run_readme "$r"); err=$(cat "$TMP/rmerr")
{ [ "$out" = "1" ] && [ "$cf2" = ok ]; } && c3=ok || c3=no
case "$err" in *"67通り"*) c4=ok ;; *) c4=no ;; esac

# A number near "gates" that is NOT a count of them must stay green, or the accuser fires on a
# correct file — the first widening did, eight times, on URLs and token counts.
r=$(readme_repo rm-count-noise)
python3 - "$r" <<'PYEOF'
import pathlib, sys
p = pathlib.Path(sys.argv[1], "README.md")
p.write_text(p.read_text() + "\nSee github.com/m0m0i/gate-oriented-sdd — the gate reports ~1,300 tokens always-on.\n")
PYEOF
out=$(run_readme "$r"); [ "$out" = "0" ] && c5=ok || c5=no

# reviewed_by is a three-way fact: absent is UNKNOWN, never spawned. Receipts predate the field.
r=$(readme_repo rm-receipt-unknown)
printf 'reviewed_sha=abc\nverdict=CLEAN\n' > "$r/.specs/9-feature/.review-receipt"
out=$(run_readme "$r"); err=$(cat "$TMP/rmerr")
[ "$out" = "1" ] && c6=ok || c6=no
case "$err" in *"Silence is not evidence"*) c7=ok ;; *) c7=no ;; esac

# The idiomatic Japanese form, which the flush-noun pattern could not see. Japanese rarely puts
# the noun against the digits — a counter or a particle sits between — so the ONE form the first
# cut caught was the one that happened to ship, and a rewrite in the most natural phrasing would
# have gone unnoticed under a guard printing "no behaviour count asserted".
r=$(readme_repo rm-count-ja-particle)
python3 - "$r" <<'PYEOF'
import pathlib, sys
p = pathlib.Path(sys.argv[1], "README.ja.md"); src = p.read_text()
out = src.replace("ゲートとガードの挙動。", "ゲートとガードを合わせて67の経路。")
if out == src: raise SystemExit("fixture no-op: JA behaviour phrase not found")
p.write_text(out)
PYEOF
[ "$?" = 0 ] && cf3=ok || cf3=no
out=$(run_readme "$r"); err=$(cat "$TMP/rmerr")
{ [ "$out" = "1" ] && [ "$cf3" = ok ]; } && c8=ok || c8=no
case "$err" in *"67の経路"*) c9=ok ;; *) c9=no ;; esac

# …and the no-false-block half, which the widening is only safe with. The real README.ja.md says
# 「4つのケースは書いてあり」 about the eval suite, and the English says "its four cases are
# authored" — both are counts near nothing to do with gates, and both must stay green. The
# widening that caught the six missed forms must not reach these.
r=$(readme_repo rm-count-ja-noise)
if python3 - "$r" <<'PYEOF'
import pathlib, sys
p = pathlib.Path(sys.argv[1], "README.ja.md")
p.write_text(p.read_text() + "\n[eval スイート](./evals/) は開発中です。4つのケースは書いてあります。\n")
q = pathlib.Path(sys.argv[1], "README.md")
q.write_text(q.read_text() + "\nThe eval suite is under development: its four cases are authored, and 2 of them are new.\n")
PYEOF
then cf4=ok; else cf4=no; fi
out=$(run_readme "$r")
{ [ "$out" = "0" ] && [ "$cf4" = ok ]; } && c10=ok || c10=no

# The Japanese receipt anchor. Dropping it to reach the echo matched any N件 in the file — a
# false red on an unrelated counter, and a fail-open if the receipt sentence is deleted while a
# stray one remains. Both directions pinned.
r=$(readme_repo rm-ja-unrelated-counter)
if python3 - "$r" <<'PYEOF'
import pathlib, sys
p = pathlib.Path(sys.argv[1], "README.ja.md")
p.write_text(p.read_text() + "\n未対応の issue が2件あります。\n")
PYEOF
then cf5=ok; else cf5=no; fi
out=$(run_readme "$r")
{ [ "$out" = "0" ] && [ "$cf5" = ok ]; } && c11=ok || c11=no

r=$(readme_repo rm-ja-silent)
if python3 - "$r" <<'PYEOF'
import pathlib, sys
p = pathlib.Path(sys.argv[1], "README.ja.md")
p.write_text("## Status\n\n**v1.2.3、pre-release です。**\n\nゲートとガードの挙動。未対応の issue が2件あります。\n")
PYEOF
then cf6=ok; else cf6=no; fi
out=$(run_readme "$r"); err=$(cat "$TMP/rmerr")
{ [ "$out" = "1" ] && [ "$cf6" = ok ]; } && c12=ok || c12=no
case "$err" in *"does not say how many"*) c13=ok ;; *) c13=no ;; esac

# The Japanese states the count twice. The anchored one carries the value; the echo must agree
# with it, and nothing pinned that until mutating the comparison produced zero failures.
r=$(readme_repo rm-ja-echo)
if python3 - "$r" <<'PYEOF'
import pathlib, sys
p = pathlib.Path(sys.argv[1], "README.ja.md")
src = p.read_text()
# This fixture APPENDS rather than substitutes, so `out != src` is guaranteed and an
# out-vs-src test cannot fail. The precondition is the guard: an earlier cut wrote
# `src.replace(x, x)` — the identity function — and reproduced the SHAPE of a no-op detector
# with the substance removed. #124's failure with the detector itself inert.
if "1件を除いて" not in src:
    raise SystemExit("fixture no-op: JA receipt sentence not found")
p.write_text(src + "その5件は inline でレビューしました。\n")
PYEOF
then cf7=ok; else cf7=no; fi
out=$(run_readme "$r"); err=$(cat "$TMP/rmerr")
{ [ "$out" = "1" ] && [ "$cf7" = ok ]; } && c14=ok || c14=no
case "$err" in *"states the receipt count twice and they disagree"*) c15=ok ;; *) c15=no ;; esac

[ "$c1$c2$c3$c4$c5$c6$c7$c8$c9$c10$c11$c12$c13$c14$c15" = "okokokokokokokokokokokokokokok" ] && report "a behaviour count in any phrasing fails, ordinary numbers do not, and an absent reviewed_by is unknown" ok \
  || report "a behaviour count in any phrasing fails, ordinary numbers do not, and an absent reviewed_by is unknown" no \
     "count-before-exit=$c1 quotes-it=$c2 count-ja-exit=$c3 quotes-ja=$c4 noise-stays-green=$c5 unknown-exit=$c6 says-silence=$c7 ja-particle-exit=$c8 quotes-particle=$c9 ja-eval-noise-green=$c10 ja-unrelated-green=$c11 ja-silent-exit=$c12 ja-silent-msg=$c13 ja-echo-exit=$c14 ja-echo-msg=$c15"


# --- Antigravity hook command execution ------------------------------------------
#
# #143. Antigravity executes hooks with cwd set to the directory containing hooks.json
# (<project>/.agents/). If commands in antigravity.hooks.json assume cwd is the repo root,
# `[ -f .agents/hooks/quality-gate.sh ]` checks .agents/.agents/hooks/quality-gate.sh,
# fails, and executes `|| exit 0`. Both gates silently pass on every turn, and
# {{FAST_CHECK}} runs inside .agents/.
#
# Any test verifying Antigravity hook execution MUST run the rendered command string
# with cwd set to .agents/, or it passes for the wrong reason.

agy_get_cmd() {
  # $1 = hooks.json, $2 = event, $3 = index
  python3 -c "
import json, sys
data = json.load(open(sys.argv[1]))
pkg = data.get('gate-sdd', {})
ev = pkg.get(sys.argv[2], [])
idx = int(sys.argv[3])
if sys.argv[2] == 'PostToolUse':
    print(ev[idx]['hooks'][0]['command'])
else:
    print(ev[idx]['command'])
" "$1" "$2" "$3"
}

antigravity_repo() {
  r="$TMP/$1"; mkdir -p "$r/.agents/hooks" "$r/.steering" "$r/.specs/9-feature" "$r/src"
  cp "$ROOT/hooks/gate-lib.sh" "$ROOT/hooks/quality-gate.sh" "$ROOT/hooks/review-gate.sh" "$r/.agents/hooks/"
  sed -e 's|{{HOOKS_DIR}}|.agents/hooks|g' -e 's|{{FAST_CHECK}}|pwd > fast_check.txt|g' \
    "$ROOT/hooks/templates/antigravity.hooks.json" > "$r/.agents/hooks.json"
  printf -- '- Reviewer: test-reviewer\n- Source globs: :(glob)**/*.txt\n' > "$r/.steering/tech.md"
  if [ "${2:-0}" = 0 ]; then box='- [x]'; else box='- [ ]'; fi
  cat > "$r/.specs/9-feature/spec.md" <<EOF
# Spec: feature
- Slug: 9-feature   Status: approved

## 3. Tasks (TDD-ordered)
$box T1: do the thing
EOF
  ( cd "$r" && git init -q -b main && git config user.email t@t && git config user.name t \
    && echo one > src/main.txt && git add -A && git commit -qm init \
    && git checkout -q -b 9-feature && echo two >> src/main.txt && git commit -qam work ) >/dev/null 2>&1
  echo "$r"
}

# 1. Quality gate blocks when a validator fails and cwd is .agents/
r=$(antigravity_repo agy-qg-fail 1)
echo '- Validators: false' >> "$r/.steering/tech.md"
( cd "$r" && git commit -qam "add failing validator" ) >/dev/null 2>&1
echo dirty >> "$r/src/main.txt"
cmd=$(agy_get_cmd "$r/.agents/hooks.json" Stop 0)
out=$( ( cd "$r/.agents" && sh -c "$cmd" 2>"$TMP/agy_qg_err"; echo "exit=$?" ) )
case "$out" in *"exit=2"*) c1=ok ;; *) c1=no ;; esac
case "$out" in *'"decision":"continue"'*) c2=ok ;; *) c2=no ;; esac

# 2. Review gate blocks when unreviewed spec is completed and cwd is .agents/
r=$(antigravity_repo agy-rv-fail 0)
cmd=$(agy_get_cmd "$r/.agents/hooks.json" Stop 1)
out=$( ( cd "$r/.agents" && sh -c "$cmd" 2>"$TMP/agy_rv_err"; echo "exit=$?" ) )
case "$out" in *"exit=2"*) c3=ok ;; *) c3=no ;; esac
case "$out" in *'"decision":"continue"'*) c4=ok ;; *) c4=no ;; esac

# 3. PostToolUse fast-check runs with cwd anchored to repo root
r=$(antigravity_repo agy-fast-check 1)
cmd=$(agy_get_cmd "$r/.agents/hooks.json" PostToolUse 0)
( cd "$r/.agents" && sh -c "$cmd" ) >/dev/null 2>&1
if [ -f "$r/fast_check.txt" ] && [ ! -f "$r/.agents/fast_check.txt" ]; then
  c5=ok
else
  c5=no
fi

# 4. Clean repo passes both gates when cwd is .agents/
r=$(antigravity_repo agy-clean 0)
echo '- Validators: true' >> "$r/.steering/tech.md"
head=$(git -C "$r" rev-parse HEAD)
printf 'verdict=CLEAN\nreviewed_sha=%s\nreviewed_by=inline\n' "$head" > "$r/.specs/9-feature/.review-receipt"
( cd "$r" && git add -A && git commit -qm "clean" ) >/dev/null 2>&1
cmd_qg=$(agy_get_cmd "$r/.agents/hooks.json" Stop 0)
cmd_rv=$(agy_get_cmd "$r/.agents/hooks.json" Stop 1)
out_qg=$( ( cd "$r/.agents" && sh -c "$cmd_qg"; echo "exit=$?" ) )
out_rv=$( ( cd "$r/.agents" && sh -c "$cmd_rv"; echo "exit=$?" ) )
case "$out_qg" in *"exit=0"*) c6=ok ;; *) c6=no ;; esac
case "$out_rv" in *"exit=0"*) c7=ok ;; *) c7=no ;; esac

[ "$c1$c2$c3$c4$c5$c6$c7" = "okokokokokokok" ] && report "Antigravity hooks execute from repo root when cwd is .agents/" ok \
  || report "Antigravity hooks execute from repo root when cwd is .agents/" no \
     "qg-exit=$c1 qg-json=$c2 rv-exit=$c3 rv-json=$c4 fast-check-root=$c5 clean-qg-exit=$c6 clean-rv-exit=$c7"


# --- Hooks invoked directly from a subdirectory (defense in depth) ----------------
#
# #143. If a gate script is invoked directly from a subdirectory (such as .agents/),
# relative references to .steering/ and .specs/ must still resolve against the
# git repository root rather than failing open.

# 1. Quality gate blocks when invoked directly from .agents/ with a failing validator
r=$(antigravity_repo agy-direct-qg 1)
echo '- Validators: false' >> "$r/.steering/tech.md"
( cd "$r" && git commit -qam "add failing validator" ) >/dev/null 2>&1
echo dirty >> "$r/src/main.txt"
out=$( ( cd "$r/.agents" && sh hooks/quality-gate.sh 2>"$TMP/agy_direct_qg_err"; echo "exit=$?" ) )
case "$out" in *"exit=2"*) c1=ok ;; *) c1=no ;; esac
case "$out" in *'"decision":"continue"'*) c2=ok ;; *) c2=no ;; esac

# 2. Review gate blocks when invoked directly from .agents/ without a receipt
r=$(antigravity_repo agy-direct-rv 0)
out=$( ( cd "$r/.agents" && sh hooks/review-gate.sh 2>"$TMP/agy_direct_rv_err"; echo "exit=$?" ) )
case "$out" in *"exit=2"*) c3=ok ;; *) c3=no ;; esac
case "$out" in *'"decision":"continue"'*) c4=ok ;; *) c4=no ;; esac

# 3. Clean repo passes both gates when invoked directly from .agents/
r=$(antigravity_repo agy-direct-clean 0)
echo '- Validators: true' >> "$r/.steering/tech.md"
head=$(git -C "$r" rev-parse HEAD)
printf 'verdict=CLEAN\nreviewed_sha=%s\nreviewed_by=inline\n' "$head" > "$r/.specs/9-feature/.review-receipt"
( cd "$r" && git add -A && git commit -qm "clean" ) >/dev/null 2>&1
out_qg=$( ( cd "$r/.agents" && sh hooks/quality-gate.sh; echo "exit=$?" ) )
out_rv=$( ( cd "$r/.agents" && sh hooks/review-gate.sh; echo "exit=$?" ) )
case "$out_qg" in *"exit=0"*) c5=ok ;; *) c5=no ;; esac
case "$out_rv" in *"exit=0"*) c6=ok ;; *) c6=no ;; esac

[ "$c1$c2$c3$c4$c5$c6" = "okokokokokok" ] && report "quality-gate.sh and review-gate.sh anchor to repo root when invoked from a subdirectory" ok \
  || report "quality-gate.sh and review-gate.sh anchor to repo root when invoked from a subdirectory" no \
     "qg-exit=$c1 qg-json=$c2 rv-exit=$c3 rv-json=$c4 clean-qg-exit=$c5 clean-rv-exit=$c6"


# --- guards: scripts/check-manifests.py ---------------------------------------
#
# #145. Antigravity plugin loader discovers rules at rules/ (rules/AGENTS.md).
# check-manifests.py ensures rules/AGENTS.md exists and matches root AGENTS.md.
# Missing rules/AGENTS.md, drifted rules/AGENTS.md, or missing AGENTS.md must fail closed.

manifest_repo() {
  r="$TMP/$1"; mkdir -p "$r/scripts" "$r/.claude-plugin" "$r/hooks/templates" "$r/rules"
  cp "$ROOT/scripts/check-manifests.py" "$r/scripts/"
  chmod +x "$r/scripts/check-manifests.py"
  cp "$ROOT/.claude-plugin/plugin.json" "$r/.claude-plugin/"
  cp "$ROOT/plugin.json" "$r/"
  cp "$ROOT/.claude-plugin/marketplace.json" "$r/.claude-plugin/"
  cp "$ROOT/hooks/templates/claude-code.settings.json" "$r/hooks/templates/"
  cp "$ROOT/hooks/templates/antigravity.hooks.json" "$r/hooks/templates/"
  printf '# AGENTS\n' > "$r/AGENTS.md"
  ln -s ../AGENTS.md "$r/rules/AGENTS.md" 2>/dev/null || cp "$r/AGENTS.md" "$r/rules/AGENTS.md"
  echo "$r"
}
run_manifest() { ( cd "$1" && python3 scripts/check-manifests.py >/dev/null 2>"$TMP/mferr"; printf '%s' "$?" ) }

r=$(manifest_repo mf-control)
out=$(run_manifest "$r"); [ "$out" = "0" ] && c0=ok || c0=no

r=$(manifest_repo mf-missing-rules)
rm -f "$r/rules/AGENTS.md"
out=$(run_manifest "$r"); err=$(cat "$TMP/mferr")
[ "$out" = "1" ] && c1=ok || c1=no
case "$err" in *"missing: rules/AGENTS.md"*) c2=ok ;; *) c2=no ;; esac

r=$(manifest_repo mf-drift)
rm -f "$r/rules/AGENTS.md"
printf '# DRIFTED\n' > "$r/rules/AGENTS.md"
out=$(run_manifest "$r"); err=$(cat "$TMP/mferr")
[ "$out" = "1" ] && c3=ok || c3=no
case "$err" in *"rules/AGENTS.md has drifted from AGENTS.md"*) c4=ok ;; *) c4=no ;; esac

r=$(manifest_repo mf-missing-root)
rm -f "$r/AGENTS.md"
out=$(run_manifest "$r"); err=$(cat "$TMP/mferr")
[ "$out" = "1" ] && c5=ok || c5=no
case "$err" in *"missing: AGENTS.md"*|*"missing: rules/AGENTS.md"*) c6=ok ;; *) c6=no ;; esac

[ "$c0$c1$c2$c3$c4$c5$c6" = "okokokokokokok" ] && report "check-manifests verifies rules/AGENTS.md matches AGENTS.md and fails closed" ok \
  || report "check-manifests verifies rules/AGENTS.md matches AGENTS.md and fails closed" no \
     "control=$c0 missing-rules-exit=$c1 missing-rules-err=$c2 drift-exit=$c3 drift-err=$c4 missing-root-exit=$c5 missing-root-err=$c6"


# --- guards: scripts/check-version-bump.py ------------------------------------
#
# #145. check-version-bump.py must include rules/ in SHIPPED so any change
# to plugin rules enforces a version bump.

vbump_repo() {
  r="$TMP/$1"; mkdir -p "$r/scripts" "$r/rules"
  cp "$ROOT/scripts/check-version-bump.py" "$r/scripts/"
  chmod +x "$r/scripts/check-version-bump.py"
  ( cd "$r" && git init -q && git config user.email "test@example.com" && git config user.name "test" )
  printf '{\n  "version": "1.0.0"\n}\n' > "$r/plugin.json"
  printf 'rules v1\n' > "$r/rules/AGENTS.md"
  ( cd "$r" && git add -A && git commit -qm "init" )
  printf 'rules v2\n' > "$r/rules/AGENTS.md"
  ( cd "$r" && git add -A && git commit -qm "change rules without bump" )
  echo "$r"
}
run_vbump() { ( cd "$1" && python3 scripts/check-version-bump.py HEAD~1 >/dev/null 2>"$TMP/vberr"; printf '%s' "$?" ) }

r=$(vbump_repo vb-rules)
out=$(run_vbump "$r"); err=$(cat "$TMP/vberr")
[ "$out" = "1" ] && c1=ok || c1=no
case "$err" in *"rules/AGENTS.md"*) c2=ok ;; *) c2=no ;; esac

( cd "$r" && git checkout -q HEAD~1 )
printf '{\n  "version": "1.1.0"\n}\n' > "$r/plugin.json"
printf 'rules v2\n' > "$r/rules/AGENTS.md"
( cd "$r" && git add -A && git commit -qm "change rules with bump" )
out=$(run_vbump "$r")
[ "$out" = "0" ] && c0=ok || c0=no

[ "$c0$c1$c2" = "okokok" ] && report "check-version-bump includes rules/ in SHIPPED" ok \
  || report "check-version-bump includes rules/ in SHIPPED" no \
     "bumped-exit=$c0 unbumped-exit=$c1 unbumped-err=$c2"


printf '\ntest-gates: %d passed, %d failed, %d skipped\n' "$pass" "$fail" "$skipped"
[ "$fail" -eq 0 ] || exit 1
