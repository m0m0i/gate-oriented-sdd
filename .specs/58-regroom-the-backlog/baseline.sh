#!/bin/sh
# Baseline / re-verification capture for #58. Prints a Markdown record.
echo "- HEAD: $(git rev-parse --short HEAD) on $(git branch --show-current)"
echo "- Claude Code $(claude --version 2>/dev/null | cut -d' ' -f1), gate-sdd $(python3 -c "import json;print(json.load(open('plugin.json'))['version'])")"
echo
echo "### Validators"
echo
sed -n 's/^- Validators: *//p' .steering/tech.md | head -1 | tr ',' '\n' | sed 's/^ *//' | while read -r cmd; do
  [ -z "$cmd" ] && continue
  out=$($cmd 2>&1); rc=$?
  echo "- \`$cmd\` → exit $rc — \`$(printf '%s\n' "$out" | grep -v '^$' | tail -1)\`"
done
echo
echo "### Open issues (\`gh issue list --state open\`)"
echo
open=$(gh issue list --state open --limit 100 --json number -q '.[].number' | sort -n | tr '\n' ' ')
echo "- count: $(echo $open | wc -w | tr -d ' ')"
echo "- numbers: $open"
echo
echo "### BACKLOG.md table"
echo
rows=$(grep -E '^\| [0-9]+ \|' docs/BACKLOG.md | awk -F'|' '{ n=$2; gsub(/ /,"",n); item=$3; out=""; while (match(item, /#[0-9]+/)) { out=out " " substr(item, RSTART, RLENGTH); item=substr(item, RSTART+RLENGTH) } if (out=="") out=" (no issue)"; print n out }')
echo "- rows: $(printf '%s\n' "$rows" | wc -l | tr -d ' ')"
printf '%s\n' "$rows" | sed 's/^/    /'
tabled=$(printf '%s\n' "$rows" | grep -oE '#[0-9]+' | tr -d '#' | sort -n)
echo "- closed but tabled: $(for n in $tabled; do echo " $open " | grep -q " $n " || printf '#%s ' "$n"; done)"
echo "- open but untabled: $(for n in $open; do printf '%s\n' "$tabled" | grep -qx "$n" || printf '#%s ' "$n"; done)"
echo "- Epic column present: $(grep -q '^| # | Item | Epic |' docs/BACKLOG.md && echo yes || echo no)"
echo
echo "### Checksums (sha256, first 12)"
echo
for f in docs/EPICS.md docs/PRD.md docs/NORTH_STAR.md .steering/product.md .steering/tech.md .steering/structure.md docs/verified.md docs/BACKLOG.md; do
  echo "- \`$f\` $(shasum -a 256 "$f" | cut -c1-12)"
done
echo
echo "### 'nothing cites' statements"
echo
grep -n -i "nothing cites" docs/EPICS.md docs/verified.md .steering/product.md docs/PRD.md | cut -c1-140 | sed 's/^/    /'
