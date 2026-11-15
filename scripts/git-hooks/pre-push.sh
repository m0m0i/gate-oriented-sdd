#!/bin/sh
# pre-push — refuses a push that would publish what the leakage guard fails on (#360).
#
# $2 is the URL git is pushing to, and standard input holds one line for each ref:
# `<local ref> <local id> <remote ref> <remote id>`. Three things are scanned: the names being
# published; the name and the message of every annotated tag pushed, and a blob a tag points
# at; and every commit the destination does not hold. What it holds is what `git ls-remote` on
# that URL lists, never the remote-tracking refs: those are what this clone remembers, and
# they hide commits when a remote's push URL differs from its fetch URL or its history was
# rewritten since the last fetch. A deletion publishes nothing. The guard is the one beside
# this script.
guard="$(dirname "$0")/../check-leakage.sh"
url=${2-}

g() { git --no-replace-objects "$@"; }
refuse() {  # $1 = why the hook could not look
  echo "gate-sdd pre-push hook FAILED — $1, so nothing was scanned." >&2
  echo "The push is refused." >&2
  exit 1
}

work=$(mktemp -d 2>/dev/null) || work=""
{ [ -n "$work" ] && [ -d "$work" ]; } || refuse "mktemp -d made no directory to work in"
trap 'rm -rf "$work"' EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM
# What was read and could not be written down was not scanned, so every write is checked, and
# "nothing to push" is decided by the lines read, not by what reached a file.
unwritten() { refuse "the hook's temporary directory could not be written"; }
for part in names text commits; do
  printf '' > "$work/$part" || unwritten
done

published=0
while read -r local_ref local_id remote_ref remote_id; do
  [ -n "$local_id" ] || continue
  case "$local_id" in *[!0]*) ;; *) continue ;; esac
  published=$((published + 1))
  printf '%s\n' "$remote_ref" >> "$work/names" || unwritten
  id=$local_id
  while :; do
    kind=$(g cat-file -t "$id" 2>/dev/null) || refuse "an object being pushed could not be read"
    case "$kind" in
      commit) printf '%s\n' "$id" >> "$work/commits" || unwritten; break ;;
      tag)
        g cat-file tag "$id" > "$work/tag" 2>/dev/null || refuse "a tag being pushed could not be read"
        # The header ends at the first empty line. Its `tag` line is the name the object
        # carries, whatever ref it is pushed under; its tagger is not scanned.
        sed -n '1,/^$/s/^tag //p' "$work/tag" >> "$work/text" || unwritten
        sed '1,/^$/d' "$work/tag" >> "$work/text" || unwritten
        # A message need not end in a newline, and the next text must start a line of its own.
        echo >> "$work/text" || unwritten
        id=$(sed -n 's/^object //p' "$work/tag" | sed -n 1p)
        [ -n "$id" ] || refuse "a tag being pushed names no object" ;;
      blob)
        g cat-file blob "$id" >> "$work/text" 2>/dev/null || refuse "a blob a tag points at could not be read"
        # A blob need not end in a newline, and the next text must start a line of its own.
        echo >> "$work/text" || unwritten
        break ;;
      *) refuse "a tag being pushed points at a tree, which the guard has no way to scan" ;;
    esac
  done
done

[ "$published" -gt 0 ] || exit 0
[ -s "$work/names" ] || unwritten

refused=0
sh "$guard" --refs < "$work/names" > /dev/null || refused=1
if [ -s "$work/text" ]; then
  sh "$guard" --text < "$work/text" > /dev/null || refused=1
fi
if [ -s "$work/commits" ]; then
  g ls-remote "$url" > "$work/remote" 2>/dev/null \
    || refuse "the destination could not be asked what it holds"
  # Of what it lists, the commits and tags this clone holds are what a push need not send.
  sed 's/[^0-9a-f].*//' "$work/remote" | g cat-file --batch-check > "$work/held" 2>/dev/null \
    || refuse "the destination's ids could not be looked up in this clone"
  held=$(sed -n -e 's/^\([0-9a-f]*\) commit .*/\1/p' -e 's/^\([0-9a-f]*\) tag .*/\1/p' "$work/held" | sort -u)
  # shellcheck disable=SC2046,SC2086  # each id is one word
  sh "$guard" --commits $(cat "$work/commits") --not $held > /dev/null || refused=1
fi

[ "$refused" -eq 0 ] && exit 0
echo "" >&2
echo "The push is refused: what it would publish did not pass scripts/check-leakage.sh." >&2
exit 1
