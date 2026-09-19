#!/bin/sh
# steering-digest-antigravity.sh — PreInvocation hook for Google Antigravity.
#
# Antigravity does not have a SessionStart hook event. Instead, it fires
# PreInvocation before every model invocation and pipes session metadata
# over stdin as JSON, including {"invocationNum": N}.
#
# On turn 1 (invocationNum == 1), this hook executes steering-digest.sh,
# packages its output into Antigravity's step injection schema:
#   {"injectSteps": [{"ephemeralMessage": "<digest>"}]}
#
# On all subsequent turns (invocationNum > 1) or on unexpected/malformed
# input, it emits {} and exits 0 so normal turns proceed with zero overhead.

set -u

DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

# Anchor to repository root so relative paths (.steering/, .specs/) resolve
# correctly regardless of the working directory the hook was invoked from.
if repo_root=$(git rev-parse --show-toplevel 2>/dev/null); then
  cd "$repo_root"
fi

if command -v python3 >/dev/null 2>&1; then
  exec python3 -c '
import json, os, subprocess, sys

try:
    raw = sys.stdin.read()
    data = json.loads(raw) if raw.strip() else {}
except Exception:
    data = {}

if not isinstance(data, dict) or data.get("invocationNum") != 1:
    print("{}")
    sys.exit(0)

digest_script = sys.argv[1]
msg = ""
if os.path.isfile(digest_script):
    try:
        res = subprocess.run(["sh", digest_script], capture_output=True, text=True)
        msg = res.stdout
    except Exception:
        pass

if not msg:
    print("{}")
    sys.exit(0)

print(json.dumps({"injectSteps": [{"ephemeralMessage": msg}]}))
' "$DIR/steering-digest.sh"
fi

# Fallback if python3 is unavailable
printf '{}\n'
exit 0
