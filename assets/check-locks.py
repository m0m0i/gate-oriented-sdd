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
re-applied on the next re-vendor. Every candidate is scanned rather than the first that
matches: a repository that installs this harness into itself has both at once.

Verifying nothing is not success. A run that hashed no files exits non-zero when locks
exist, because a guard that did not run must not be indistinguishable from one that ran and
found everything in order.
"""
import datetime
import hashlib
import os
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

# Walked explicitly rather than globbed, because a directory that exists and cannot be
# read must be an error rather than an empty contribution. `Path.glob` swallows the
# permission error and yields nothing, so an unreadable reviewer would otherwise be
# counted as scanned — and since the report names the directories it scanned, it would
# actively claim coverage it does not have. Both levels matter: the candidate root, and
# each reviewer inside it.
lock_paths: list[pathlib.Path] = []
for _dir in AGENT_DIRS:
    if not os.access(_dir, os.R_OK | os.X_OK):
        errors.append(
            f"{_dir.relative_to(ROOT)} exists but cannot be read, so its rulebooks were not "
            "verified. Fix the directory's permissions rather than treating this as a pass."
        )
        continue
    for _sub in sorted(_dir.iterdir()):
        if not _sub.is_dir():
            continue
        if not os.access(_sub, os.R_OK | os.X_OK):
            errors.append(
                f"{_sub.relative_to(ROOT)} exists but cannot be read, so its rulebook was not "
                "verified. Fix the directory's permissions rather than treating this as a pass."
            )
            continue
        if (_lock := _sub / "rules-lock.json").is_file():
            lock_paths.append(_lock)

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

# Three outcomes, not two. "Verified nothing" and "found no drift" used to share this line
# and this exit code, which is what let a wrong reviewer directory go unnoticed: the guard
# kept reporting success while hashing nothing at all. Naming the directories scanned in
# every branch is what makes a count of zero legible without reading this file.
scanned = ", ".join(str(d.relative_to(ROOT)) for d in AGENT_DIRS) or "no reviewer directory"

if not lock_paths:
    # Legitimate: a project may install this guard before its first reviewer exists. Failing
    # would hand it a red build it could only fix by deleting the guard.
    print(f"check-locks: no rulebooks are pinned in {scanned} — nothing to verify")
    sys.exit(0)

if checked == 0:
    print("lock check FAILED", file=sys.stderr)
    print(
        f"  {len(lock_paths)} lock file(s) found in {scanned}, but they verified no files.\n"
        "      A lock that pins nothing is not a lock that passed — it is a guard that did\n"
        "      not run. Check that each lock's 'vendored'/'derived' entries name paths that\n"
        "      exist.",
        file=sys.stderr,
    )
    sys.exit(1)

print(f"check-locks: {checked} pinned file(s) match their locks in {scanned}")
