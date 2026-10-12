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

The reviewer directory differs between the harness repo (`reviewers/`) and a project using it
(`.claude/agents/`), so it is discovered rather than hardcoded — otherwise every install
has to hand-edit the copy, which is exactly the kind of divergence that never gets
re-applied on the next re-vendor. Every candidate is scanned rather than the first that
matches: a repository that installs this harness into itself has both at once.

Verifying nothing is not success. A run that hashed no files exits non-zero when locks
exist, because a guard that did not run must not be indistinguishable from one that ran and
found everything in order.

A lock proves the rulebook is the text that was agreed; it cannot prove it is the rulebook the
project's contract cites. So this also checks that every Judgment row of `<docs>/CONTRACT.md`
names a rule the reviewer `- Reviewer:` names defines (#84): `init` once put a reference
rulebook over a project whose contract cited fifteen ids it did not carry, and the lock half
reported the reference lock matching the reference rules — true, and beside the point. It
checks ids only. Whether a row's severity and wording agree with its rule is still the
reviewer's to read.
"""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent


#: Every place a repository may keep reviewers. `reviewers/` is the harness repo's own; the
#: other two are where `init` puts a project's. They are not alternatives — a repository
#: that dogfoods the harness has both at once.
CANDIDATE_DIRS = (".claude/agents", ".agents/agents", "reviewers")


def _reviewer_dirs(root: pathlib.Path) -> list[pathlib.Path]:
    """Every reviewer directory that exists, not the first one that does.

    This used to return a single directory — whichever held a lock first — which quietly
    assumed the candidates could never coexist. They must: installing this harness into its
    own repository creates `.claude/agents/` beside the shipped `reviewers/`, and the old rule
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
                    f"{reviewer.name}: derived/{name} source {src.get('id')!r} is pinned by "
                    "neither a version (pinnedBy) nor a date (checkedOn)"
                )

    if dirty:
        lock["generatedAt"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        lock_path.write_text(json.dumps(lock, indent=2) + "\n")
        print(f"re-pinned {lock_path.relative_to(ROOT)}")


def _steering_value(text: str, key: str) -> str:
    """The first value for `key`, read with the expression `check-document-set.py` uses."""
    for line in text.split("\n"):
        if m := re.match(rf"^ *- *{key}: *(.*)$", line):
            return m.group(1)
    return ""


def _cell(text: str) -> str:
    return text.strip().strip("*`").strip()


def _judgment_ids(contract: str) -> list[str]:
    """The id of every row whose Tier is Judgment, in any table with `id` and `Tier` columns.

    Columns are found by the header rather than by position, so a contract that reorders or
    adds columns is still read; a table without both headers is not a Rules table and is
    skipped.
    """
    ids: list[str] = []
    cols: tuple[int, int] | None = None
    for line in contract.splitlines():
        if not line.strip().startswith("|"):
            cols = None
            continue
        cells = [_cell(c) for c in line.strip().strip("|").split("|")]
        names = [c.lower() for c in cells]
        if "id" in names and "tier" in names:
            cols = (names.index("id"), names.index("tier"))
        elif cols and len(cells) > max(cols) and cells[cols[1]].lower() == "judgment":
            ids.append(cells[cols[0]])
    return ids


def _defines(rulebook: str, rule_id: str) -> bool:
    """True when a heading or a bolded list item OPENS with the id.

    Both shipped shapes — `## PY-001 — ...` and `- **G-1 — ...**` — and nothing looser. A
    mention in prose ("unlike G-3") is not a rule, and `G-10` is not `G-1`; matching either
    would let a rulebook pass on ids it never wrote, which is the stripped path of #84.
    """
    head = r"^[ \t]*(?:#{1,6}[ \t]+|[-*][ \t]+\*\*)"
    return re.search(head + re.escape(rule_id) + r"(?![\w-])", rulebook, re.M) is not None


def _read(path: pathlib.Path) -> str | None:
    try:
        return path.read_text()
    except OSError as exc:
        errors.append(
            f"{path.relative_to(ROOT)} exists but cannot be read ({exc.strerror}), so the "
            "contract was not checked against the rulebook. Fix it rather than treating this "
            "as a pass."
        )
        return None


contract_note = ""
_steering = ROOT / ".steering" / "tech.md"
_tech = (_read(_steering) or "") if _steering.is_file() else ""
_docs = _steering_value(_tech, "Docs").strip() or "docs/"
if "://" in _docs:
    # A URL is not a directory. Failing would leave a multi-repo project no way to keep this
    # guard, whose lock half still applies to it; passing silently would read as having looked.
    contract_note = f"contract not checked: `- Docs: {_docs}` names another repository"
elif (_contract_path := ROOT / _docs / "CONTRACT.md").is_file() and (
    _contract := _read(_contract_path)
) is not None:
    _contract_rel = _contract_path.relative_to(ROOT)
    _ids = _judgment_ids(_contract)
    _reviewer = _steering_value(_tech, "Reviewer").strip()
    if not _ids:
        contract_note = f"{_contract_rel} cites no Judgment rule id"
    elif not _reviewer:
        errors.append(
            f"{_contract_rel} cites Judgment rule(s) {', '.join(_ids)}, but .steering/tech.md "
            "has no `- Reviewer:` line naming the reviewer whose rulebook must define them."
        )
    else:
        _rule_dirs = [r for d in AGENT_DIRS if (r := d / _reviewer / "rules").is_dir()]
        if not _rule_dirs:
            _where = ", ".join(str(d.relative_to(ROOT)) for d in AGENT_DIRS)
            errors.append(
                f"{_contract_rel} cites Judgment rule(s) {', '.join(_ids)} of reviewer "
                f"`{_reviewer}`, but there is no rulebook for it: no `{_reviewer}/rules/` in "
                f"{_where or 'any reviewer directory'}.\n"
                f"      Those rows have no enforcer. Restore the project's rulebook from git "
                f"history, or run `contract` to compile them into the reviewer installed."
            )
        _defined_in: list[str] = []
        for _rules in _rule_dirs:
            _rel = _rules.relative_to(ROOT)
            if not os.access(_rules, os.R_OK | os.X_OK):
                errors.append(f"{_rel} exists but cannot be read, so the contract was not checked.")
                continue
            _texts = [_read(p) for p in sorted(_rules.iterdir()) if p.suffix == ".md"]
            if None in _texts:
                continue
            _book = "\n".join(t for t in _texts if t is not None)
            if _missing := [i for i in _ids if not _defines(_book, i)]:
                errors.append(
                    f"{_rel}: {_contract_rel} cites Judgment rule(s) this rulebook does not "
                    f"define: {', '.join(_missing)}\n"
                    f"      Those rows have no enforcer. Restore the project's rulebook "
                    f"(git log -- {_rel}), or run `contract` to compile them into it."
                )
            else:
                _defined_in.append(str(_rel))
        if _defined_in and len(_defined_in) == len(_rule_dirs):
            contract_note = (
                f"{_contract_rel} cites {len(_ids)} Judgment rule id(s), each defined in "
                f"{', '.join(_defined_in)}"
            )

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
if contract_note:
    print(f"check-locks: {contract_note}")

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
