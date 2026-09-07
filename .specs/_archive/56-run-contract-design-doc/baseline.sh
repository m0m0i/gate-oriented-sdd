#!/bin/sh
# Baseline / re-verification capture for #56. Prints a Markdown record.
echo "- HEAD: $(git rev-parse --short HEAD) on $(git branch --show-current)"
echo "- Claude Code $(claude --version 2>/dev/null | cut -d' ' -f1), gate-sdd $(python3 -c "import json;print(json.load(open('plugin.json'))['version'])")"
echo
echo "### Validators (each command on the \`- Validators:\` line, last output line and exit code)"
echo
line=$(sed -n 's/^- Validators: *//p' .steering/tech.md | head -1)
echo "$line" | tr ',' '\n' | sed 's/^ *//' | while read -r cmd; do
  [ -z "$cmd" ] && continue
  out=$($cmd 2>&1); rc=$?
  last=$(printf '%s\n' "$out" | grep -v '^$' | tail -1)
  echo "- \`$cmd\` → exit $rc — \`$last\`"
done
echo
echo "### Anchors and locks"
echo
echo "- \`./assets/check-steering-anchors.sh\`: $(./assets/check-steering-anchors.sh 2>&1 | tail -1)"
echo "- \`./assets/check-locks.py\`: $(./assets/check-locks.py 2>&1 | tail -1)"
echo "- Dogfood lock present: $( [ -f .claude/agents/gate-sdd-reviewer/rules-lock.json ] && echo yes || echo no )"
echo
echo "### Checksums (sha256, first 12)"
echo
for f in .steering/product.md .steering/tech.md .steering/structure.md CONTRIBUTING.md docs/NORTH_STAR.md docs/PRD.md docs/EPICS.md docs/BACKLOG.md .claude/agents/gate-sdd-reviewer.md .claude/agents/_shared/reviewer-contract.md .claude/agents/gate-sdd-reviewer/rules/*.md agents/*/rules-lock.json; do
  echo "- \`$f\` $(shasum -a 256 "$f" | cut -c1-12)"
done
echo
echo "### Anchor lines, verbatim"
echo
grep -h '^- Owns:' .steering/product.md | sed 's/^/    /'
grep -hE '^- (Validators|Reviewer|Source globs|Docs):' .steering/tech.md | sed 's/^/    /'
echo
echo "### Rule ids and severities"
echo
printf '%s\n' "Command: \`grep -hE '^- \*\*[GC]-[0-9]+' .claude/agents/gate-sdd-reviewer/rules/*.md | sed -E 's/^- \*\*([GC]-[0-9]+).*(BLOCKER|HIGH|MEDIUM|LOW|INFO)[^A-Z]*\$/\1 \2/'\`"
echo
grep -hE '^- \*\*[GC]-[0-9]+' .claude/agents/gate-sdd-reviewer/rules/*.md | sed -E 's/^- \*\*([GC]-[0-9]+).*(BLOCKER|HIGH|MEDIUM|LOW|INFO)[^A-Z]*$/\1 \2/' | sed 's/^/    /'
echo
echo "- Count: $(grep -hE '^- \*\*[GC]-[0-9]+' .claude/agents/gate-sdd-reviewer/rules/*.md | wc -l | tr -d ' ')"
echo
echo "### ADR state"
echo
echo "- \`ls docs/decisions/\`: $(ls docs/decisions/ 2>&1 | head -1)"
echo "- \`git branch -r | grep -c ADR-\`: $(git branch -r | grep -c 'ADR-')"
echo "- \`git ls-tree -r --name-only origin/main | grep -c ADR-\`: $(git ls-tree -r --name-only origin/main 2>/dev/null | grep -c 'ADR-')"
echo "- \`grep -c ADR\` in files the reviewer reads: gate-sdd-reviewer.md=$(grep -c 'ADR' .claude/agents/gate-sdd-reviewer.md) reviewer-contract.md=$(grep -c 'ADR' .claude/agents/_shared/reviewer-contract.md) rules=$(cat .claude/agents/gate-sdd-reviewer/rules/*.md | grep -c 'ADR')"
echo
echo "### structure.md headings and table rows"
echo
grep -E '^#|^\|' .steering/structure.md | sed 's/^/    /'
