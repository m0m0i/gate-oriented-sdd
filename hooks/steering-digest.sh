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

steer() { sed -n "s/^ *- *$1: *//p" .steering/tech.md 2>/dev/null | head -1; }

echo "## Repo facts"
[ -f .steering/product.md ] && echo "- Persistent context is in .steering/product.md, .steering/tech.md, .steering/structure.md."

owns=$(sed -n 's/^ *- *Owns: *//p' .steering/product.md 2>/dev/null | head -1)
[ -n "$owns" ] && echo "- This project owns $owns."

v=$(steer Validators);  [ -n "$v" ] && echo "- Validators: $v"
r=$(steer Reviewer);    [ -n "$r" ] && echo "- The reviewer for this repo is $r."

echo "- The flow is spec -> clarify -> implement -> reviewer -> worklog -> archive. One issue = one spec = one branch = one PR."
echo "- Live specs are .specs/<slug>/spec.md; shipped ones are under .specs/_archive/."
echo "- A Stop hook enforces the quality gate and the freshness of the review receipt."

branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo '')
spec=".specs/$branch/spec.md"
if [ -n "$branch" ] && [ -f "$spec" ]; then
  status=$(sed -n 's/.*Status: *\([A-Za-z]*\).*/\1/p' "$spec" | head -1)
  open=$(awk '/^#+ *3\./{f=1;next} /^#+ /{f=0} f' "$spec" | grep -c '^ *- \[ \]')
  echo "- The active branch $branch has spec $spec (Status: $status, $open task(s) still open)."
elif [ -n "$branch" ]; then
  echo "- The active branch $branch has no spec directory under .specs/."
fi
