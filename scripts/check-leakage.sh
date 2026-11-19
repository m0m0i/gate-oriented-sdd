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
# Exit 0 = clean. Exit 1 = something private is in what it was given, or the guard could not look.
set -u

# With no mode it scans the working tree. --text scans standard input instead, --refs a list of
# ref names on it, --staged what the next commit changes, and --commits the commits the
# revisions after it name: revisions, --not and --all, as git rev-list takes them (#360).
# --public-only runs the public tier alone, for a pull request from a fork, which has no private
# patterns to be given. Any other argument is refused, and is not printed (#357).
# --no-hook-check skips the working-tree scan's check that this clone's hooks are installed,
# for CI, which has no clone to commit from (#360).
PUBLIC_ONLY=0
HOOK_CHECK=1
MODE=tree
refuse_arguments() {
  echo "check-leakage FAILED — it was given an argument it does not take, so it looked at nothing." >&2
  echo "  It takes --public-only, which runs the public tier alone and is not a pass for private" >&2
  echo "  context, --no-hook-check, which CI gives it because it has no clone to commit from, and" >&2
  echo "  one mode at most: --text, --refs, --staged, or --commits and the revisions" >&2
  echo "  to scan. The argument is withheld: this report can reach a public log." >&2
  exit 1
}
while [ "$#" -gt 0 ]; do
  case "$1" in
    --public-only) [ "$PUBLIC_ONLY" -eq 0 ] || refuse_arguments; PUBLIC_ONLY=1 ;;
    --no-hook-check) [ "$HOOK_CHECK" -eq 1 ] || refuse_arguments; HOOK_CHECK=0 ;;
    --text|--refs|--staged) [ "$MODE" = tree ] || refuse_arguments; MODE=${1#--} ;;
    --commits)
      [ "$MODE" = tree ] || refuse_arguments
      MODE=commits; shift
      [ "$#" -gt 0 ] || refuse_arguments
      for revision in "$@"; do
        case "$revision" in --not|--all) ;; ''|-*) refuse_arguments ;; esac
      done
      break ;;
    *) refuse_arguments ;;
  esac
  shift
done

# Only the working-tree scan reads the checkout this script sits in, so it drops what git sets
# for a hook, which names the repository the hook ran in (#360).
if [ "$MODE" = tree ]; then
  unset GIT_DIR GIT_INDEX_FILE GIT_WORK_TREE GIT_PREFIX GIT_COMMON_DIR
  ROOT=$(cd "$(dirname "$0")/.." && pwd)
  cd "$ROOT" || exit 1
fi

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

fail=0
warned=0

# What a clean run says of the private patterns, after what it scanned (#357).
loaded() {
  if [ "$PUBLIC_ONLY" -eq 1 ]; then printf 'private patterns not run'; else printf 'private patterns loaded'; fi
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
  [ -z "${named-}" ] \
    || echo "A path number is the line of this command's output that holds the path: $LISTING" >&2
}

# An input the guard could not read is not an input it read and found clean (#360).
input_fault() {  # $1 = the fault
  echo "check-leakage FAILED — $1, so nothing was scanned." >&2
  exit 1
}

# Tries every tier against a file of lines, as text in this locale and again as bytes, and
# reports each tier that hits by the numbers of its lines. $1 = the file, $2 = what the numbers
# count. Sets fail and warned, and leaves every number that hit in $hit_at (#360).
scan_lines() {
  hit_at=""
  while IFS= read -r tier; do
    [ -s "$TIERS/$tier" ] || continue
    case "$tier" in *ignore-case) fold=-i ;; *) fold="" ;; esac
    case "$tier" in warn*) kind=WARNING ;; *) kind=LEAK ;; esac
    # shellcheck disable=SC2086  # $fold is one option or nothing
    at=$(
      { grep -anE $fold -f "$TIERS/$tier" -- "$1" 2>/dev/null
        LC_ALL=C grep -anE $fold -f "$TIERS/$tier" -- "$1" 2>/dev/null
      } | LC_ALL=C sed -n 's/^\([0-9][0-9]*\):.*/\1/p' | LC_ALL=C sort -n -u | tr '\n' ' ')
    at=${at% }
    [ -n "$at" ] || continue
    echo "$kind [$tier] $2: $at" >&2
    hit_at="$hit_at $at"
    case "$kind" in LEAK) fail=1 ;; *) warned=1 ;; esac
  done <<EOF
$TIER_ORDER
EOF
}

# --text and --refs: standard input, whole. A terminal is refused: a run that waits on a
# keyboard has scanned nothing. A ref name is the text, so --refs reports a position (#360).
if [ "$MODE" = text ] || [ "$MODE" = refs ]; then
  case "$MODE" in
    text) what="input line(s)"; unit="line(s) of text"; none="the text held nothing" ;;
    *) what="ref number(s) in the list"; unit="ref name(s)"; none="the list held no ref name" ;;
  esac
  [ ! -t 0 ] || input_fault "standard input is a terminal and --$MODE reads what to scan from it"
  cat > "$TIERS/in.read" 2>/dev/null || input_fault "standard input could not be read"
  # A branch or tag is scanned as its name: with `refs/heads/` or `refs/tags/` left on, an
  # expression anchored at the start matches none. Any other ref is scanned whole.
  case "$MODE" in
    refs) LC_ALL=C sed -e 's|^refs/heads/||' -e 's|^refs/tags/||' "$TIERS/in.read" > "$TIERS/in.lines" ;;
    *) cat "$TIERS/in.read" > "$TIERS/in.lines" ;;
  esac
  [ -f "$TIERS/in.lines" ] || input_fault "what was read could not be written to the temporary directory"
  scan_lines "$TIERS/in.lines" "$what"
  closing
  [ "$fail" -eq 0 ] || exit 1
  count=$(grep -c '' "$TIERS/in.lines")
  if [ "$count" -eq 0 ]; then
    echo "check-leakage: clean — $none, $(loaded)"
  else
    echo "check-leakage: clean — $count $unit scanned, $(loaded)"
  fi
  exit 0
fi

# Every git call of a mode goes through here, so nothing the caller's configuration holds
# changes what is read: a replace ref shows another object, and a quoted path is not a path (#360).
g() { git --no-replace-objects -c core.quotePath=false "$@"; }
# What every diff of a mode is given: a colour, an external diff, a textconv filter and
# diff.relative each change or drop the lines a scan reads. A deletion publishes nothing (#360).
DIFF="--no-color --no-ext-diff --no-textconv --no-relative --no-renames --diff-filter=d"

# Tries every tier against the files of a directory, which are named by number, and reports
# each file that hits by its label and the numbers of its lines. $1 = the directory, $2 = a file
# whose line N is the label of file N. Sets fail and warned (#360).
scan_blobs() {
  while IFS= read -r tier; do
    [ -s "$TIERS/$tier" ] || continue
    case "$tier" in *ignore-case) fold=-i ;; *) fold="" ;; esac
    case "$tier" in warn*) kind=WARNING ;; *) kind=LEAK ;; esac
    [ -d "$1" ] || input_fault "the temporary directory lost the content it was to scan"
    # shellcheck disable=SC2086  # $fold is one option or nothing
    hits=$(
      cd "$1" || exit
      { ls | xargs grep -lE $fold -f "$TIERS/$tier" -- 2>/dev/null
        ls | LC_ALL=C xargs grep -lE $fold -f "$TIERS/$tier" -- 2>/dev/null
      } | LC_ALL=C sort -n -u | while IFS= read -r n; do
        [ -n "$n" ] || continue
        lines=$(
          { grep -anE $fold -f "$TIERS/$tier" -- "$n" 2>/dev/null
            LC_ALL=C grep -anE $fold -f "$TIERS/$tier" -- "$n" 2>/dev/null
          } | LC_ALL=C sed -n 's/^\([0-9][0-9]*\):.*/\1/p' | LC_ALL=C sort -n -u | tr '\n' ' ')
        printf '%s\n' "$kind [$tier] $(sed -n "${n}p" "$2") line(s): ${lines% }"
      done
    )
    [ -n "$hits" ] || continue
    printf '%s\n' "$hits" >&2
    case "$kind" in LEAK) fail=1 ;; *) warned=1 ;; esac
  done <<EOF
$TIER_ORDER
EOF
}

# --staged: each path the next commit adds or changes, and its content as the index holds it.
# No git command feeds a pipe: each writes a file, and its status is read first (#360).
if [ "$MODE" = staged ]; then
  g rev-parse --git-dir >/dev/null 2>&1 \
    || input_fault "this is not a git repository and --staged reads its index"
  # shellcheck disable=SC2086  # $DIFF is a list of options
  g diff --cached --raw --no-abbrev $DIFF > "$TIERS/in.raw" 2>/dev/null \
    || input_fault "git could not list what is staged"
  tab=$(printf '\t')
  sed "s/^[^$tab]*$tab//" "$TIERS/in.raw" > "$TIERS/in.paths"
  LISTING="git diff --cached --name-only --no-renames --diff-filter=d"

  quoted=$(grep -n '^"' "$TIERS/in.paths" | sed 's/:.*//' | tr '\n' ' ')
  [ -z "$quoted" ] || input_fault "git quotes staged path number(s) ${quoted% }, which hold a quote, a backslash or a control character and cannot be read by name. Rename them"

  # A path that matches is the text, so a hit inside it is reported against its number.
  scan_lines "$TIERS/in.paths" "staged path number(s) in the listing"
  named=$hit_at

  mkdir "$TIERS/in.blobs" || input_fault "the temporary directory could not hold the staged content"
  empty=""
  n=0
  while IFS= read -r meta <&3 && IFS= read -r path <&4; do
    n=$((n + 1))
    case " $named " in
      *" $n "*) printf 'staged path number %s in the listing,\n' "$n" ;;
      *) printf '%s\n' "$path" ;;
    esac >> "$TIERS/in.labels"
    # $meta is `:<old mode> <new mode> <old id> <new id> <status>`.
    set -f; set -- $meta; set +f
    [ "$2" != 160000 ] || continue
    g cat-file blob "$4" > "$TIERS/in.blobs/$n" 2>/dev/null && continue
    # A path added with intent to add is listed with the empty blob, which no object holds.
    [ -n "$empty" ] || empty=$(g hash-object -t blob /dev/null 2>/dev/null)
    [ "$4" = "$empty" ] && { : > "$TIERS/in.blobs/$n"; continue; }
    input_fault "the staged content of $(sed -n "${n}p" "$TIERS/in.labels" | sed 's/,$//') could not be read"
  done 3< "$TIERS/in.raw" 4< "$TIERS/in.paths"

  [ "$n" -eq 0 ] || scan_blobs "$TIERS/in.blobs" "$TIERS/in.labels"
  closing
  [ "$fail" -eq 0 ] || exit 1
  if [ "$n" -eq 0 ]; then
    echo "check-leakage: clean — nothing is staged, $(loaded)"
  else
    echo "check-leakage: clean — $n staged path(s) scanned, $(loaded)"
  fi
  exit 0
fi

# --commits: the verdict comes from three files over every commit at once: the messages, the
# paths, and the added lines of the patches. Only when a tier hits are the commits that hold a
# hit read again, one by one, for a location, and a hit that read cannot place still fails (#360).
if [ "$MODE" = commits ]; then
  g rev-parse --git-dir >/dev/null 2>&1 \
    || input_fault "this is not a git repository and --commits reads its history"
  [ "$(g rev-parse --is-shallow-repository 2>/dev/null)" = false ] \
    || input_fault "this repository is shallow, and commits it does not hold cannot be scanned"
  # `--` ends the revisions: a word after them is not a path that limits the commits read.
  g rev-list "$@" -- > "$TIERS/in.ids" 2>/dev/null \
    || input_fault "git could not resolve the revisions it was given"
  count=$(grep -c '' "$TIERS/in.ids")
  # With no revision on its standard input, git log reads HEAD.
  if [ "$count" -eq 0 ]; then
    echo "check-leakage: clean — the revisions name no commit, $(loaded)"
    exit 0
  fi

  LOG="--no-walk --diff-merges=separate --root"
  # shellcheck disable=SC2086  # $LOG and $DIFF are lists of options
  { g log --no-walk --stdin --format=%B < "$TIERS/in.ids" > "$TIERS/in.messages" 2>/dev/null \
    && g log --stdin $LOG --format= --name-only $DIFF < "$TIERS/in.ids" > "$TIERS/in.paths" 2>/dev/null \
    && g log --stdin $LOG --format= -p -U0 --text $DIFF < "$TIERS/in.ids" > "$TIERS/in.patch" 2>/dev/null
  } || input_fault "git could not read the commits it was given"
  # An added line is scanned as the line it is: with the patch's `+` left on, an expression
  # anchored at a line's start matches none. A `+++ b/<path>` header keeps two of its three.
  LC_ALL=C sed -n 's/^+//p' "$TIERS/in.patch" > "$TIERS/in.added"
  [ -f "$TIERS/in.added" ] || input_fault "the added lines of the commits could not be written to the temporary directory"
  ! grep -q '^"' "$TIERS/in.paths" \
    || input_fault "git quotes a path of these commits, which holds a quote, a backslash or a control character and cannot be read by name"

  hit_tiers=""
  while IFS= read -r tier; do
    [ -s "$TIERS/$tier" ] || continue
    case "$tier" in *ignore-case) fold=-i ;; *) fold="" ;; esac
    for part in messages paths added; do
      # shellcheck disable=SC2086  # $fold is one option or nothing
      if grep -aqE $fold -f "$TIERS/$tier" -- "$TIERS/in.$part" 2>/dev/null \
        || LC_ALL=C grep -aqE $fold -f "$TIERS/$tier" -- "$TIERS/in.$part" 2>/dev/null; then
        hit_tiers="$hit_tiers
$tier"
        break
      fi
    done
  done <<EOF
$TIER_ORDER
EOF

  if [ -n "$hit_tiers" ]; then
    LISTING="git log --no-walk --format= --name-only --diff-merges=separate --root --no-renames --diff-filter=d <commit>"
    tab=$(printf '\t')
    any_named=""

    # Which commits to read again: one more pass with each commit's id on a line of its own
    # before its message and patch, and the commits whose lines a tier that hit matches. A
    # line that only looks like an id line can misplace a hit, never clear one: the verdict
    # is already made, and a tier this read places nowhere is reported against the set.
    # shellcheck disable=SC2086
    g log --stdin $LOG --format='@@@ %H%n%B' -p -U0 --text $DIFF < "$TIERS/in.ids" > "$TIERS/in.marked.patch" 2>/dev/null \
      || : > "$TIERS/in.marked.patch"
    # Without the `+`, as the first read took the added lines. Line numbers are unchanged.
    LC_ALL=C sed 's/^+//' "$TIERS/in.marked.patch" > "$TIERS/in.marked"
    : > "$TIERS/in.hitlines"
    while IFS= read -r tier; do
      [ -n "$tier" ] || continue
      case "$tier" in *ignore-case) fold=-i ;; *) fold="" ;; esac
      # shellcheck disable=SC2086
      { grep -anE $fold -f "$TIERS/$tier" -- "$TIERS/in.marked" 2>/dev/null
        LC_ALL=C grep -anE $fold -f "$TIERS/$tier" -- "$TIERS/in.marked" 2>/dev/null
      } | LC_ALL=C sed -n 's/^\([0-9][0-9]*\):.*/\1/p' >> "$TIERS/in.hitlines"
    done <<EOF
$hit_tiers
EOF
    LC_ALL=C awk '
      NR == FNR { hit[$1] = 1; next }
      /^@@@ [0-9a-f]+$/ { id = $2 }
      (FNR in hit) && id != "" && !seen[id]++ { print id }
    ' "$TIERS/in.hitlines" "$TIERS/in.marked" > "$TIERS/in.suspects"

    {
      while IFS= read -r id; do
        short=$(printf '%s' "$id" | cut -c1-7)
        if g log --no-walk --format=%B "$id" > "$TIERS/in.message" 2>/dev/null; then
          scan_lines "$TIERS/in.message" "commit $short, message line(s)"
        fi
        # shellcheck disable=SC2086
        g log $LOG --format= --raw --no-abbrev $DIFF "$id" > "$TIERS/in.raw" 2>/dev/null || continue
        sed "s/^[^$tab]*$tab//" "$TIERS/in.raw" > "$TIERS/in.listing"
        scan_lines "$TIERS/in.listing" "commit $short, path number(s) in its listing"
        named=$hit_at
        [ -z "$named" ] || any_named=1
        rm -rf "$TIERS/in.blobs" "$TIERS/in.labels"
        mkdir "$TIERS/in.blobs" || continue
        n=0
        while IFS= read -r meta <&3 && IFS= read -r path <&4; do
          n=$((n + 1))
          case " $named " in
            *" $n "*) printf 'commit %s, path number %s in its listing,\n' "$short" "$n" ;;
            *) printf 'commit %s, %s\n' "$short" "$path" ;;
          esac >> "$TIERS/in.labels"
          set -f; set -- $meta; set +f
          [ "$2" != 160000 ] || continue
          g cat-file blob "$4" > "$TIERS/in.blobs/$n" 2>/dev/null || rm -f "$TIERS/in.blobs/$n"
        done 3< "$TIERS/in.raw" 4< "$TIERS/in.listing"
        [ "$n" -eq 0 ] || scan_blobs "$TIERS/in.blobs" "$TIERS/in.labels"
      done < "$TIERS/in.suspects"
    } 2> "$TIERS/in.report"
    named=$any_named

    # A tier the first read found fails whatever the second read placed, and one it placed
    # nowhere is reported against the set.
    while IFS= read -r tier; do
      [ -n "$tier" ] || continue
      case "$tier" in warn*) kind=WARNING; warned=1 ;; *) kind=LEAK; fail=1 ;; esac
      grep -Fq -e "$kind [$tier] " "$TIERS/in.report" \
        || echo "$kind [$tier] in the commits scanned, at a place the second read did not find" >> "$TIERS/in.report"
    done <<EOF
$hit_tiers
EOF
    awk '!seen[$0]++' "$TIERS/in.report" >&2
  fi

  closing
  [ "$fail" -eq 0 ] || exit 1
  echo "check-leakage: clean — $count commit(s) scanned, $(loaded)"
  exit 0
fi

# Decided once and read twice: which lister runs, and whether a leading `"` can only be git's
# doing. In a non-git tree nothing quotes, so a file genuinely named `"quoted".md` must not be
# mistaken for one git could not represent. Review round 2.
if git rev-parse --git-dir >/dev/null 2>&1; then IN_GIT=1; else IN_GIT=0; fi

# A hook that is absent is silent, so a clone whose hooks are not the ones this checkout would
# install fails here, where every turn end and every contributor's run passes. A shim newer
# than this checkout's passes: worktrees of one clone share the hooks and not the branch (#360).
hooks_fault() {  # $1 = what is wrong
  echo "check-leakage FAILED — the leak hooks of this clone are not installed as this checkout has them: $1." >&2
  echo "  Run: sh scripts/install-git-hooks.sh" >&2
  echo "" >&2
  echo "  They scan a commit's message and staged content, and what a push would publish, before" >&2
  echo "  git publishes it. Without them this scan of the working tree is the only one that runs." >&2
  exit 1
}
shim_version() {  # $1 = a file. Prints its shim number, or nothing when it is not a shim.
  sed -n 's/^# gate-sdd-shim \([0-9][0-9]*\)$/\1/p' "$1" 2>/dev/null | sed -n 1p
}
if [ "$IN_GIT" -eq 1 ] && [ "$HOOK_CHECK" -eq 1 ]; then
  [ -f scripts/git-hooks/shim.sh ] || hooks_fault "this checkout holds no scripts/git-hooks/shim.sh to compare them with"
  want=$(shim_version scripts/git-hooks/shim.sh)
  [ -n "$want" ] || hooks_fault "scripts/git-hooks/shim.sh holds no version line"
  # The key, not its value: set to nothing it still sends git elsewhere.
  ! git config --get core.hooksPath >/dev/null 2>&1 \
    || hooks_fault "core.hooksPath is set, so git runs none of them"
  common=$(git rev-parse --git-common-dir 2>/dev/null) || hooks_fault "git could not name the clone's common directory"
  checked=0
  for script in scripts/git-hooks/*.sh; do
    name=${script##*/}; name=${name%.sh}
    [ "$name" != shim ] || continue
    [ -f "$script" ] || continue
    checked=$((checked + 1))
    [ -f "$common/hooks/$name" ] || hooks_fault "$name is not installed"
    [ -x "$common/hooks/$name" ] || hooks_fault "$name is not executable"
    have=$(shim_version "$common/hooks/$name")
    [ -n "$have" ] || hooks_fault "$name is not the shim"
    [ "$have" -ge "$want" ] || hooks_fault "$name is shim version $have, older than this checkout's $want"
    [ "$have" -gt "$want" ] || cmp -s "$common/hooks/$name" scripts/git-hooks/shim.sh \
      || hooks_fault "$name differs from scripts/git-hooks/shim.sh at the same version"
  done
  [ "$checked" -gt 0 ] || hooks_fault "this checkout holds no hook script under scripts/git-hooks"
  hooks=""

  # The gh guard (#361 AC5): on a machine with Claude Code, the hook that scans what a session's
  # gh writes send must be registered as the installer prints it, and must work. The reference is
  # the default branch's copy, so a branch that edits the hook need not install its work in
  # progress; where the default branch has none, this checkout's.
  gh_fault() {  # $1 = the faults, one to a line, or a sentence
    echo "check-leakage FAILED — the gh guard is not registered as installed on this machine:" >&2
    printf '%s\n' "$1" | sed 's/^gate-sdd gh guard: not registered as installed: /  /' >&2
    echo "  Run: sh scripts/install-gh-hook.sh, and add the entry it prints to ~/.claude/settings.json." >&2
    echo "" >&2
    echo "  It scans what a Claude Code session's gh writes would send, in every project, before" >&2
    echo "  they run. CONTRIBUTING.md's \"The gh guard\" says how to install it and what passes it." >&2
    exit 1
  }
  if [ -n "${CLAUDE_CONFIG_DIR:-}" ]; then gh_config=$CLAUDE_CONFIG_DIR; else gh_config=${HOME:-}/.claude; fi
  if [ ! -d "$gh_config" ]; then
    hooks=", gh guard skipped: no Claude Code configuration on this machine"
  else
    # The reference is laid out as the installer lays out its copy: the three files side by side.
    gh_ref=$(git symbolic-ref -q --short refs/remotes/origin/HEAD 2>/dev/null) || gh_ref=""
    [ -z "$gh_ref" ] || git cat-file -e "$gh_ref:scripts/claude-hooks/gh_guard_lib.py" 2>/dev/null || gh_ref=""
    [ -n "$gh_ref" ] || [ -f scripts/claude-hooks/gh_guard.py ] \
      || gh_fault "  this checkout holds no scripts/claude-hooks/gh_guard.py to compare it with."
    gh_py=$(command -v python3 2>/dev/null) || gh_fault "  there is no python3 on PATH to run the check."
    gh_dir=$(mktemp -d "${TMPDIR:-/tmp}/gh-guard-ref.XXXXXX") || gh_fault "  no scratch directory for the reference."
    for f in claude-hooks/gh_guard.py claude-hooks/gh_guard_lib.py check-leakage.sh; do
      if [ -n "$gh_ref" ]; then git show "$gh_ref:scripts/$f" > "$gh_dir/${f#claude-hooks/}" 2>/dev/null
      else cp "scripts/$f" "$gh_dir/${f#claude-hooks/}" 2>/dev/null
      fi || { rm -rf "$gh_dir"; gh_fault "  ${gh_ref:+$gh_ref:}scripts/$f cannot be read."; }
    done
    gh_err=$("$gh_py" -I "$gh_dir/gh_guard.py" --check-registration "$ROOT" </dev/null 2>&1 >/dev/null)
    gh_rc=$?
    rm -rf "$gh_dir"
    case "$gh_rc" in
      0) case "$gh_err" in
           skipped:*) hooks=", gh guard skipped: no Claude Code configuration on this machine" ;;
           '') ;;
           *) gh_fault "  the check printed what it does not print on a pass." ;;
         esac ;;
      2) case "$gh_err" in
           'gate-sdd gh guard: not registered as installed: '*) gh_fault "$gh_err" ;;
           *) gh_fault "  the check could not run: $(printf '%s\n' "$gh_err" | sed -n 1p)" ;;
         esac ;;
      *) gh_fault "  the check exited $gh_rc." ;;
    esac
  fi
else
  # A run that did not look at the hooks says so, as one without the private patterns does.
  hooks=", hooks not checked"
fi

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
  echo "check-leakage: public tier clean — $scanned file(s) scanned$note, private patterns not run$hooks"
else
  echo "check-leakage: clean — $scanned file(s) scanned$note, private patterns loaded$hooks"
fi
exit 0
