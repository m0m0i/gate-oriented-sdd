#!/usr/bin/env python3
"""Verify every reviewer's rules-lock.json against the files it pins.

A rulebook that has drifted from its lock is worse than an unpinned one: the
reviewer keeps citing rule ids as though they were the reviewed, agreed text
while the text underneath has changed. This makes that state a build failure.

  ./assets/check-locks.py            verify   (CI)
  ./assets/check-locks.py --update   re-pin   (after deliberately editing a rulebook)

It lives in assets/ because it is one of the few files a project needs a COPY of rather
than a reference to: `init` copies it in so the project can re-pin its own rulebook. That
also puts it on a shipped path, so a fix to it cannot go out unreachable.

The reviewer directory differs between the harness repo (`agents/`) and a project using it
(`.claude/agents/`), so it is discovered rather than hardcoded — otherwise every install
has to hand-edit the copy, which is exactly the kind of divergence that never gets
re-applied on the next re-vendor.
"""
import datetime
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


#: Every place a repository may keep reviewers. `agents/` is the harness repo's own; the
#: other two are where `init` puts a project's. They are not alternatives — a repository
#: that dogfoods the harness has both at once.
CANDIDATE_DIRS = (".claude/agents", ".agents/agents", "agents")


def _reviewer_dirs(root: pathlib.Path) -> list[pathlib.Path]:
    """Every reviewer directory that exists, not the first one that does.

    This used to return a single directory — whichever held a lock first — which quietly
    assumed the candidates could never coexist. They must: installing this harness into its
    own repository creates `.claude/agents/` beside the shipped `agents/`, and the old rule
    then took all six shipped rulebooks out of scope while still exiting 0.
    """
    return [d for c in CANDIDATE_DIRS if (d := root / c).is_dir()]


AGENT_DIRS = _reviewer_dirs(ROOT)
update = "--update" in sys.argv
errors: list[str] = []
checked = 0

lock_paths = sorted(p for d in AGENT_DIRS for p in d.glob("*/rules-lock.json"))

for lock_path in lock_paths:
    reviewer = lock_path.parent
    lock = json.loads(lock_path.read_text())
    dirty = False

    for kind in ("vendored", "derived"):
        for name, meta in (lock.get(kind) or {}).items():
            rel = meta.get("path") or meta.get("skillPath")
            if not rel:
                errors.append(f"{lock_path.name}: {kind}/{name} has no path")
                continue
            target = reviewer / rel
            if not target.is_file():
                errors.append(f"{reviewer.name}: {kind}/{name} pins a missing file: {rel}")
                continue
            actual = hashlib.sha256(target.read_bytes()).hexdigest()
            checked += 1
            if actual != meta.get("computedHash"):
                if update:
                    meta["computedHash"] = actual
                    dirty = True
                else:
                    errors.append(
                        f"{reviewer.name}: {rel} has drifted from its lock\n"
                        f"      locked {meta.get('computedHash')}\n"
                        f"      actual {actual}\n"
                        f"      If the edit was deliberate: ./scripts/check-locks.py --update"
                    )

    # A derived rule cites sources; without them "first-party grounding" is a claim
    # rather than something a reader can check.
    for name, meta in (lock.get("derived") or {}).items():
        for src in meta.get("sources", []):
            if not src.get("pinnedBy") and not src.get("checkedOn"):
                errors.append(
                    f"{reviewer.name}: derived/{name} source {src.get('id')!r} is pinned by neither "
                    "a version (pinnedBy) nor a date (checkedOn)"
                )

    if dirty:
        lock["generatedAt"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        lock_path.write_text(json.dumps(lock, indent=2) + "\n")
        print(f"re-pinned {lock_path.relative_to(ROOT)}")

if errors:
    print("lock check FAILED", file=sys.stderr)
    for e in errors:
        print(f"  {e}", file=sys.stderr)
    sys.exit(1)
print(f"check-locks: {checked} pinned file(s) match their locks")
