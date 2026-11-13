#!/bin/sh
# check-leakage.sh — refuse to let private context reach a public repo.
#
# This harness was extracted from a private polyrepo. The extraction is meant to
# be clean-room: read the private file, close it, write the generic one. This
# script is the backstop for when that discipline slips — which it does most
# easily in the places that look harmless, like an example in a rulebook or a
# path in a doc comment.
#
# It runs in CI and is safe to run locally: ./scripts/check-leakage.sh
# Exit 0 = clean. Exit 1 = something private is in the tree, or the guard could not look.
set -u

# --public-only is the one argument: the public tier alone, for a pull request from a fork, which
# has no private patterns to be given. Any other argument is refused, and is not printed (#357).
PUBLIC_ONLY=0
case "$#:${1-}" in
  0:) ;;
  1:--public-only) PUBLIC_ONLY=1 ;;
  *)
    echo "check-leakage FAILED — it was given an argument it does not take, so it looked at nothing." >&2
    echo "  The only argument is --public-only, which runs the public tier alone and is not a" >&2
    echo "  pass for private context. The argument is withheld: this report can reach a public log." >&2
    exit 1 ;;
esac

ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT" || exit 1

# Nothing is excluded, this script included: an allowlist here is how a guard rots, and its own
# text is scanned so that a private word written back into it is caught (#357).

# The public tier — the numbered forms of the private cross-reference id scheme. It names
# nothing, so it stays here and fails on every run; a bare word like "ADR" is this repo's own.
IDS='\bNS-[0-9]|\bCAP-[a-z]|\bCON-[a-z]|\bADR-[0-9]{4}'

# The private patterns live in a file outside the repository, because every word written here
# is published. $GATE_SDD_LEAKAGE_PATTERNS names the file, else it is the default path (#357).
PATTERNS=${GATE_SDD_LEAKAGE_PATTERNS:-${XDG_CONFIG_HOME:-${HOME-}/.config}/gate-sdd/leakage-patterns}

# A list that is missing or unusable is not a pass. The report names the fault and the file,
# never a pattern: it reaches a public CI log (#357).
pattern_fault() {  # $1 = the fault
  echo "check-leakage FAILED — the private patterns were not loaded: $1" >&2
  echo "  Looked in: $PATTERNS" >&2
  echo "" >&2
  echo "  That is \$GATE_SDD_LEAKAGE_PATTERNS, else \${XDG_CONFIG_HOME:-\$HOME/.config}/gate-sdd/leakage-patterns." >&2
  echo "  The file holds one extended regular expression per line, each under [fail]," >&2
  echo "  [fail ignore-case] or [warn ignore-case], and at least one of them fails. Blank lines" >&2
  echo "  and lines starting with # are dropped, and a line that ends in a space or a tab is" >&2
  echo "  refused. CONTRIBUTING.md says what to write in it without private context. A run with" >&2
  echo "  no list is not a pass." >&2
  exit 1
}

# Every tier is a file of expressions in this directory. It holds private text, so it goes on
# every exit (#357).
TIERS=$(mktemp -d 2>/dev/null) || TIERS=""
if [ -z "$TIERS" ] || [ ! -d "$TIERS" ]; then
  echo "check-leakage FAILED — mktemp -d made no directory to write the tiers into." >&2
  exit 1
fi
trap 'rm -rf "$TIERS"' EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

# One file per section, named for it, with each pattern's line number beside it in `<section>.at`.
load_private() {
  [ -e "$PATTERNS" ] || pattern_fault "no such file"
  { [ -f "$PATTERNS" ] && [ -r "$PATTERNS" ]; } || pattern_fault "the file cannot be read"

  # A CR before the newline is part of no pattern: left in, the pattern matches nothing.
  tr -d '\r' 2>/dev/null < "$PATTERNS" > "$TIERS/list" || pattern_fault "the file cannot be read"

  # A blank line is dropped because an empty expression matches every line.
  # A space or a tab that ends a line is part of its expression, and after a section header it
  # makes the header an expression of the section above, so the line is a fault (#357).
  tab=$(printf '\t')
  section=""
  at=0
  orphans=""
  trailing=""
  while IFS= read -r line || [ -n "$line" ]; do
    at=$((at + 1))
    case "$line" in
      '#'*) continue ;;
      '[fail]'|'[fail ignore-case]'|'[warn ignore-case]')
        section=${line#?}; section=${section%?}; continue ;;
      *[![:space:]]*' '|*[![:space:]]*"$tab") trailing="$trailing $at"; continue ;;
      *[![:space:]]*) ;;
      *) continue ;;
    esac
    if [ -z "$section" ]; then
      orphans="$orphans $at"
      continue
    fi
    # A pattern that is not written is a pattern not run, which must not read as a pass (#357).
    { printf '%s\n' "$line" >> "$TIERS/$section" && printf '%s\n' "$at" >> "$TIERS/$section.at"; } \
      || pattern_fault "a pattern could not be written to the temporary directory the tiers are read from"
  done < "$TIERS/list"

  [ -z "$trailing" ] || pattern_fault "line(s)$trailing end in a space or a tab"
  [ -z "$orphans" ] || pattern_fault "line(s)$orphans hold a pattern outside any section"

  # An expression grep cannot compile makes every scan exit above 1 into a discarded stderr, which
  # reads as no hit. Each section is compiled against empty input before any file is scanned.
  for section in 'fail' 'fail ignore-case' 'warn ignore-case'; do
    [ -s "$TIERS/$section" ] || continue
    case "$section" in *ignore-case) fold=-i ;; *) fold="" ;; esac
    # shellcheck disable=SC2086  # $fold is one option or nothing
    grep -E $fold -f "$TIERS/$section" </dev/null >/dev/null 2>&1
    [ "$?" -gt 1 ] || continue
    invalid=""
    while IFS= read -r line <&3 && IFS= read -r at <&4; do
      # shellcheck disable=SC2086
      grep -E $fold -e "$line" </dev/null >/dev/null 2>&1
      [ "$?" -le 1 ] || invalid="$invalid $at"
    done 3< "$TIERS/$section" 4< "$TIERS/$section.at"
    pattern_fault "invalid expression in [$section], line(s)$invalid"
  done

  { [ -s "$TIERS/fail" ] || [ -s "$TIERS/fail ignore-case" ]; } || pattern_fault "it holds no fail pattern"
}

# A run that leaves the private patterns out says so before it scans, whatever it then finds,
# and never says they were loaded: read as a pass, it clears a tree nothing private was looked
# for in (#357).
if [ "$PUBLIC_ONLY" -eq 1 ]; then
  echo "check-leakage: PRIVATE PATTERNS NOT RUN (--public-only): not a pass for private context" >&2
else
  load_private
fi

# Every tier is a file of expressions over the same work-set: the private file's three sections,
# and the public tier, which fails as [fail] does. A tier with no file is a tier not run, which
# is every private one under --public-only (#357).
if ! printf '%s\n' "$IDS" > "$TIERS/public"; then
  echo "check-leakage FAILED — the public tier could not be written beside the private patterns." >&2
  exit 1
fi
TIER_ORDER='fail
fail ignore-case
public
warn ignore-case'

# Decided once and read twice: which lister runs, and whether a leading `"` can only be git's
# doing. In a non-git tree nothing quotes, so a file genuinely named `"quoted".md` must not be
# mistaken for one git could not represent. Review round 2.
if git rev-parse --git-dir >/dev/null 2>&1; then IN_GIT=1; else IN_GIT=0; fi

files() {
  if [ "$IN_GIT" -eq 1 ]; then
    # --others so a file that is written but not yet staged is still checked.
    # Plain `git ls-files` sees only tracked files, which means a fresh repo, or
    # a new file before `git add`, scans nothing and reports clean — the worst
    # possible failure mode for a guard.
    # `core.quotePath` defaults to TRUE, and it renders any byte above 0x80 as a C-quoted
    # literal — `"caf\303\251.md"` — which is not a path anything here can open. The
    # readability check below then calls a readable file unreadable, and this script is the
    # FIRST entry on the `- Validators:` line, so that is every turn stopped on a wrong
    # diagnosis. A guard with a wrong diagnosis gets removed. #39 review round 1.
    git -c core.quotePath=false ls-files --cached --others --exclude-standard
  else
    find . -type f -not -path './.git/*' | sed 's|^\./||'
  fi
}

# The work-set, read ONCE. Three scans over three separately computed lists could disagree
# with each other and with the count below, and the count is only worth printing if it is the
# count of what was actually handed to grep — which is why the scans below run over `scanlist`,
# the entries that survived classification, rather than over `list`. Those drifted apart for
# one round: `absent` entries stayed in the list grep was given while leaving the count.
list=$(files)

scanned=0
absent=0
scanlist=""
unreadable=""
unscannable=""
while IFS= read -r f; do
  [ -n "$f" ] || continue
  # FIRST, before any filesystem test. git C-quotes a path holding `"`, a backslash or a
  # control character whatever core.quotePath says, and `ls-files -z` -- the only way to get
  # those verbatim -- has no portable reader in POSIX sh. The quoted form is not a path, so
  # `[ -e ]` is false for it and the ancestor walk below has nothing to blame: put after them,
  # this arm became unreachable and such a file was counted as absent on exit 0. It was added
  # in review round 1, dead from round 2, and no case exercised it until round 4 -- deleting
  # it outright left the suite green. In a non-git tree `find` does not quote, so a leading
  # quote there is a real filename and this must not fire; a path holding a newline splits
  # there instead and is counted twice, recorded rather than fixed because the fix is the NUL
  # reader this shell does not have.
  if [ "$IN_GIT" -eq 1 ]; then
    case "$f" in
      '"'*) unscannable="${unscannable}
  $f"; continue ;;
    esac
  fi
  # `--cached` lists INDEX entries and filters on neither existence nor `skip-worktree`, so a
  # tracked path that is not on disk arrives here: an unstaged `rm`, a sparse checkout, a
  # partial worktree. `[ -r ]` is false for every one of them, and this guard blocked the turn
  # saying "could not be read … fix the permissions" about a file that is not there — absent
  # and unreadable fused, which is this issue's own subject reached one level down inside its
  # own fix. Counted rather than skipped in silence: "I scanned round three index entries" is
  # exactly the thing that must not hide inside `clean`. AC5, narrowed in review round 2.
  if [ ! -e "$f" ]; then
    # Absent, or UNREACHABLE — and `[ -e ]` cannot tell you which. stat() returns EACCES
    # through any prefix with no search permission, and `test` collapses that into false, so
    # the arm above counted a file that IS in the working tree as one that is not: a planted
    # hit under a mode-000 directory went from caught to `clean`, on exit 0, in the clean-room
    # backstop. Introduced by the fix for the defect above it, which is this issue's own
    # subject a third time. Review round 3.
    #
    # Walk UP to the first ancestor that can be stat'd at all. Testing only the immediate
    # parent is not enough: under a mode-000 `a/`, `[ -d a/b ]` cannot be answered either, so
    # `a/b/c.md` would fall through to "absent" by the same mechanism one level deeper. A path
    # with no directory part has no ancestor to blame and is simply gone.
    _d=$f; _blocked=0
    while [ "${_d%/*}" != "$_d" ]; do
      _d=${_d%/*}
      if [ -d "$_d" ]; then
        [ -x "$_d" ] || _blocked=1
        break
      fi
    done
    if [ "$_blocked" -eq 1 ]; then
      unreadable="${unreadable}
  $f"
    else
      absent=$((absent + 1))
    fi
    continue
  fi
  scanned=$((scanned + 1))
  scanlist="${scanlist}${f}
"
  [ -r "$f" ] || unreadable="${unreadable}
  $f"
done <<EOF
$list
EOF

if [ "$IN_GIT" -eq 1 ]; then
  LISTING="git ls-files --cached --others --exclude-standard"
else
  LISTING="find . -type f -not -path './.git/*'"
fi

fail=0
warned=0

# The report reaches a public CI log, so it holds a tier and a location and never the text that
# matched or the pattern. A path that matches is itself that text: it is named by its position
# in the listing: here, in the refusals below, and wherever a hit inside the file is reported.
# So every path is tried before anything is refused (#357).
#
# Each tier is tried against the listing as text in this locale, and again as bytes. In a UTF-8
# locale a name that is not UTF-8 is matched by no expression under BSD grep, and under GNU
# grep without -a it is matched and a sentence on stderr stands in for it. Both read as no hit (#357).
named=""
while IFS= read -r tier; do
  [ -s "$TIERS/$tier" ] || continue
  case "$tier" in *ignore-case) fold=-i ;; *) fold="" ;; esac
  case "$tier" in warn*) kind=WARNING ;; *) kind=LEAK ;; esac
  # shellcheck disable=SC2086  # $fold is one option or nothing
  hits=$(
    { printf '%s\n' "$list" | grep -anE $fold -f "$TIERS/$tier" 2>/dev/null
      printf '%s\n' "$list" | LC_ALL=C grep -anE $fold -f "$TIERS/$tier" 2>/dev/null
    } | LC_ALL=C sort -t: -k1,1n -u
  )
  [ -n "$hits" ] || continue
  named="$named$(printf '%s\n' "$hits" | LC_ALL=C sed 's/^[0-9]*://')
"
  at=$(printf '%s\n' "$hits" | LC_ALL=C sed 's/:.*//' | tr '\n' ' ')
  echo "$kind [$tier] path number(s) in the listing: ${at% }" >&2
  case "$kind" in LEAK) fail=1 ;; *) warned=1 ;; esac
done <<EOF
$TIER_ORDER
EOF

# A name is compared as bytes, so one that is not text in this locale is still found (#357).
shown() {  # $1 = a path, $2 = what follows a position. Prints the path, or its position in the
           # listing when the path itself matched.
  if printf '%s' "$named" | LC_ALL=C grep -aFxq -e "$1"; then
    printf 'path number %s in the listing%s' \
      "$(printf '%s\n' "$list" | LC_ALL=C grep -anFx -e "$1" | LC_ALL=C sed -n '1s/:.*//p')" "${2-}"
  else
    printf '%s' "$1"
  fi
}

entries() {  # $1 = the entries a refusal names, one to a line. Prints each as `shown` gives it.
  printf '%s\n' "$1" | while IFS= read -r entry; do
    entry=${entry#  }
    [ -n "$entry" ] || continue
    printf '\n  %s' "$(shown "$entry")"
  done
}

# A report that holds a LEAK or a WARNING ends with this, whichever exit it leaves by (#357).
closing() {
  [ "$fail" -ne 0 ] || [ "$warned" -ne 0 ] || return 0
  echo "" >&2
  if [ "$fail" -ne 0 ]; then
    echo "Clean-room rule: do not scrub these in place. Scrubbing leaves the shape," >&2
    echo "and the shape is where the private structure lives. Rewrite the file." >&2
  else
    echo "A warning does not fail the guard. Confirm that each one is a generic example." >&2
  fi
  echo "The matched text is withheld on purpose, because this report is public wherever CI" >&2
  echo "prints it. Open the location to see what matched." >&2
  [ -z "$named" ] \
    || echo "A path number is the line of this command's output that holds the path: $LISTING" >&2
}

# A file this guard was handed and could not open is not a file it read and found clean.
# `xargs grep … 2>/dev/null` discarded "Permission denied" along with the noise it was there
# for, so the scan went round such a file in silence, on the same exit code and in the same
# sentence. Checked once here rather than three times below, so the three scans keep their
# stderr discard: after this, what they could still print is noise.
if [ -n "$unscannable" ]; then
  echo "check-leakage FAILED — in the work-set and cannot be handed to grep as a path:$(entries "$unscannable")" >&2
  echo "" >&2
  echo "  git C-quoted these because they hold a quote, a backslash or a control character." >&2
  echo "  Rename them. This guard is the clean-room backstop and must not skip a file quietly." >&2
  closing
  exit 1
fi

if [ -n "$unreadable" ]; then
  echo "check-leakage FAILED — in the work-set and could not be read:$(entries "$unreadable")" >&2
  echo "" >&2
  echo "  Fix the permissions rather than treating this as a pass. A file that was not read" >&2
  echo "  is not a file that came back clean, and this guard is the clean-room backstop." >&2
  closing
  exit 1
fi

# Zero files is not a clean tree. files()'s own comment calls a scan of nothing "the worst
# possible failure mode for a guard" and then does not check for it: a fresh clone, a broken
# `git ls-files`, or an exclusion that grew all end here, and until now they all printed
# `check-leakage: clean` on exit 0. AGENTS.md calls this the guard that matters most. #39.
if [ "$scanned" -eq 0 ]; then
  if [ "$absent" -gt 0 ]; then
    # It was not empty, and saying so would send the reader to `git ls-files`, which is not
    # the cause. A fully sparse checkout lands here. AC5's second clause.
    echo "check-leakage FAILED — the work-set held $absent index entr(ies) and no working-tree" >&2
    echo "  file for any of them, so nothing was scanned. A checkout this partial cannot be" >&2
    echo "  cleared by this guard; check it out fully rather than treating this as a pass." >&2
  else
    echo "check-leakage FAILED — the work-set is empty, so nothing was scanned." >&2
    echo "  'found nothing' and 'looked at nothing' must not share an exit code. Check that" >&2
    echo "  git ls-files works here: the listing holds this script at the least." >&2
  fi
  closing
  exit 1
fi

# Reads paths one to a line. NUL-delimited into xargs, so a path holding a space reaches grep as
# one argument, and `--`, so a path beginning with `-` is not read as an option. Either one
# unread is a silent pass (#39).
scan() { tr '\n' '\0' | xargs -0 grep "$@" -- 2>/dev/null; }

# A file holding a line this locale cannot read whole is scanned again as bytes: BSD grep in a
# UTF-8 locale matches nothing after a byte that is not UTF-8, which reads as no hit. Only those
# files get the second pass, which keeps the run time (#357).
undecoded=$(printf '%s' "$scanlist" | scan -lvxE --null -e '.*' | tr '\0' '\n')

# One batched pass per tier finds the files that hit, and only those are read again for their
# line numbers, as text and as bytes. The inner loop ends a pipeline, so its lines come back
# through a command substitution and the verdict is set from them (#357).
while IFS= read -r tier; do
  [ -s "$TIERS/$tier" ] || continue
  case "$tier" in *ignore-case) fold=-i ;; *) fold="" ;; esac
  case "$tier" in warn*) kind=WARNING ;; *) kind=LEAK ;; esac
  # shellcheck disable=SC2086
  hits=$(
    { printf '%s' "$scanlist" | scan -lE $fold --null -f "$TIERS/$tier"
      [ -z "$undecoded" ] \
        || printf '%s\n' "$undecoded" | ( LC_ALL=C; export LC_ALL; scan -lE $fold --null -f "$TIERS/$tier" )
    } | tr '\0' '\n' | LC_ALL=C sort -u | while IFS= read -r f; do
      [ -n "$f" ] || continue
      # -a, so a file grep calls binary still gives its line numbers and not a sentence.
      lines=$(
        { grep -anE $fold -f "$TIERS/$tier" -- "$f" 2>/dev/null
          LC_ALL=C grep -anE $fold -f "$TIERS/$tier" -- "$f" 2>/dev/null
        } | LC_ALL=C sed -n 's/^\([0-9][0-9]*\):.*/\1/p' | LC_ALL=C sort -n -u | tr '\n' ' ')
      lines=${lines% }
      printf '%s\n' "$kind [$tier] $(shown "$f" ,) line(s): ${lines:-not found on the second read}"
    done
  )
  [ -n "$hits" ] || continue
  printf '%s\n' "$hits" >&2
  case "$kind" in LEAK) fail=1 ;; *) warned=1 ;; esac
done <<EOF
$TIER_ORDER
EOF

closing
[ "$fail" -eq 0 ] || exit 1

note=""
[ "$absent" -gt 0 ] && note=", $absent index entr(ies) not in the working tree"
if [ "$PUBLIC_ONLY" -eq 1 ]; then
  echo "check-leakage: public tier clean — $scanned file(s) scanned$note, private patterns not run"
else
  echo "check-leakage: clean — $scanned file(s) scanned$note, private patterns loaded"
fi
exit 0
