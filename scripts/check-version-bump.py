#!/usr/bin/env python3
"""Fail when a shipped file changed without the plugin version moving.

`claude plugin update` compares version strings, not commit shas. A change to a shipped
file that leaves the version alone is therefore unreachable: the updater tells the user
"already at the latest version" and keeps serving the old content, so the fix appears to
have been released and has not been. Nothing about that state is visible from either
side — it took a byte-for-byte diff of the marketplace checkout against the install cache
to notice six such commits, one of which was a real bug fix.

CONTRIBUTING.md has always described this hazard and called it "a habit rather than a
check". This is the check.

  ./scripts/check-version-bump.py                 compare against origin/main
  ./scripts/check-version-bump.py <base-ref>      compare against something else

Only paths that end up in a consumer's install count. Editing docs/, evals/, scripts/,
CI, or the READMEs does not require a release, and a guard that demanded one for those
would fire on most PRs — which is how a guard gets deleted.
"""

import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

#: What a consumer actually receives. Kept as prefixes so a new skill or rulebook is
#: covered on the day it is added rather than the day someone remembers this file.
SHIPPED = ("skills/", "agents/", "hooks/", "assets/", "plugin.json", ".claude-plugin/plugin.json")

#: Changing these does not change what is installed.
EXEMPT = (".claude-plugin/marketplace.json",)


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()


def version_at(ref: str | None) -> str | None:
    """The Antigravity manifest's version at `ref`, or in the working tree if None."""
    try:
        raw = (ROOT / "plugin.json").read_text() if ref is None else git("show", f"{ref}:plugin.json")
    except subprocess.CalledProcessError:
        return None
    try:
        return json.loads(raw).get("version")
    except json.JSONDecodeError:
        return None


base = sys.argv[1] if len(sys.argv) > 1 else "origin/main"

try:
    git("rev-parse", "--verify", base)
except subprocess.CalledProcessError:
    print(f"check-version-bump: base ref {base!r} not found — skipping", file=sys.stderr)
    sys.exit(0)

changed = [p for p in git("diff", "--name-only", f"{base}...HEAD").splitlines() if p]
shipped = [
    p for p in changed if p not in EXEMPT and any(p == s or p.startswith(s) for s in SHIPPED)
]

if not shipped:
    print("check-version-bump: no shipped file changed")
    sys.exit(0)

before, after = version_at(base), version_at(None)

if after is None:
    print("check-version-bump FAILED: plugin.json has no readable version", file=sys.stderr)
    sys.exit(1)

if before == after:
    print("check-version-bump FAILED", file=sys.stderr)
    print(f"  {len(shipped)} shipped file(s) changed, but the version is still {after!r}:", file=sys.stderr)
    for p in shipped[:20]:
        print(f"      {p}", file=sys.stderr)
    if len(shipped) > 20:
        print(f"      ... and {len(shipped) - 20} more", file=sys.stderr)
    print(
        "\n  Consumers would never receive this. `claude plugin update` compares versions,\n"
        "  reports 'already at the latest version', and keeps serving the old content.\n"
        "  Bump `version` in BOTH plugin.json and .claude-plugin/plugin.json.\n"
        "\n  A `#non-breaking` change still needs a bump: semver describes compatibility,\n"
        "  not reachability, and an unreachable fix is not a fix.",
        file=sys.stderr,
    )
    sys.exit(1)

print(f"check-version-bump: {len(shipped)} shipped file(s) changed, version {before} -> {after}")
