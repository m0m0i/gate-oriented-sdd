#!/usr/bin/env python3
"""Fail when the two copies of the Receipt block disagree about its fields.

The reviewer emits the Receipt block; `implement` copies it verbatim into
`.specs/<slug>/.review-receipt`; `review-gate.sh` reads that file. The schema therefore
exists in three documents at once — `agents/_shared/reviewer-contract.md` defines it,
`skills/implement/SKILL.md` reproduces it, and `.claude/agents/_shared/` mirrors the first for
this repo's own reviewer — and nothing has ever checked that they agree.

A field added to one and not the other is invisible: the reviewer emits it, the author
copying the other block drops it, and the receipt is silently poorer than the schema
claims. That is the same argument `check-manifests.py` makes about the two plugin
manifests, applied to the other pair of documents this repo keeps in lockstep.

Field ORDER is compared too, not just membership. The block is copied by a reader working
top to bottom, so a reordered copy is a copy that will drift.
"""

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

#: Where the schema is written down. Both must agree, and neither is more authoritative —
#: a disagreement is a bug wherever it came from.
SOURCES = (
    "agents/_shared/reviewer-contract.md",
    "skills/implement/SKILL.md",
    # This repo runs the harness on itself, so its own reviewer reads a COPY of the contract
    # and that copy is what actually governs a review here. It was missed on the first pass:
    # the guard reported agreement across the two it knew about while the third — the one
    # doing the reviewing — still described a six-field receipt.
    ".claude/agents/_shared/reviewer-contract.md",
)

#: Membership rule, so the next maintainer has a basis for adding to this: the fields
#: `hooks/review-gate.sh` mechanically reads (`sed -n 's/^verdict=//p'` and
#: `s/^reviewed_sha=//p'`), plus the one #9 exists to add. Nothing else belongs here.
#:
#: This is NOT a fourth copy of the schema. A copy must agree in full and drifts silently
#: both ways; this is a deliberate subset that can only drift lax, which fails safe.
#: Fields the schema must still contain, not merely agree about. Equality alone is satisfied
#: by every copy dropping the same field, which is exactly how this guard could have been
#: green while the field #9 exists to add was deleted from all of them.
REQUIRED = ("reviewed_sha", "verdict", "reviewed_by")

FIELD = re.compile(r"^\s*([a-z_]+)=")


def bash_policy(path: pathlib.Path) -> str | None:
    """The text of a reviewer's `## Bash policy` section, or None if it has no such section.

    Scoped to the section rather than searched for across the whole file, because the rest of
    a reviewer names commands it is describing rather than permitting — a rulebook row, a
    validator table, an example of a finding. Matching those would let a reviewer pass while
    its allow-list still forbade the command, which is the fail-open direction and the one
    this repository is named for avoiding.

    Ends at the next `## ` heading. Deliberately not at the next blank line: the section is a
    bullet list with prose around it, and every reviewer file separates the two with one.
    """
    lines = path.read_text().splitlines()
    body: list[str] = []
    inside = False
    for line in lines:
        if line.startswith("## "):
            if inside:
                break
            inside = line.strip().lower() == "## bash policy"
            continue
        if inside:
            body.append(line)
    return "\n".join(body) if inside or body else None


def fields(path: pathlib.Path) -> list[str]:
    """The receipt field names, in order, from the block that defines `reviewed_sha`.

    Located by anchor rather than by line number so that editing the prose around it does
    not silently change what this checks.
    """
    names: list[str] = []
    started = False
    for line in path.read_text().splitlines():
        m = FIELD.match(line)
        if m and not started and m.group(1) == "reviewed_sha":
            # First block only. A second `reviewed_sha=` further down is prose about the
            # schema, not another definition of it.
            started, names = True, [m.group(1)]
            continue
        if not started:
            continue
        if line.strip().startswith("```"):
            break  # the fence closed: the block is over
        if m:
            names.append(m.group(1))
        # Anything else inside the fence — a blank line, a comment — is skipped rather than
        # treated as the end. Breaking on the first gap let a cosmetic blank line silently
        # narrow what was compared, and the guard still exited 0.
    return names


found = {}
for rel in SOURCES:
    path = ROOT / rel
    if not path.is_file():
        print(f"check-receipt-schema: {rel} is missing", file=sys.stderr)
        sys.exit(1)
    names = fields(path)
    if not names:
        print(f"check-receipt-schema: no receipt block found in {rel}", file=sys.stderr)
        sys.exit(1)
    found[rel] = names

#: The `.claude/` contract is a MIRROR of the shipped one, not an independent document —
#: this repo runs the harness on itself, so its reviewer reads a copy. Field agreement is not
#: enough: the severity ladder, the definition of CLEAN, and the rules of engagement are every
#: bit as load-bearing as the field names, and none of them are checked by comparing fields.
#: Demonstrated rather than assumed — redefining CLEAN in the mirror as "zero BLOCKER" instead
#: of "zero BLOCKER and zero HIGH" passed every validator, which would let this repo's own
#: reviewer emit CLEAN with HIGH findings outstanding and the gate would clear the turn.
MIRRORS = (
    ("agents/_shared/reviewer-contract.md", ".claude/agents/_shared/reviewer-contract.md"),
)

for _src, _dst in MIRRORS:
    # Every mirror must also be a SOURCE. That is what makes the skip below unreachable: the
    # SOURCES loop hard-exits on a missing file before this runs. Stated rather than left as
    # an ordering accident, because this repo has twice shipped a guard whose safety rested on
    # something no comment named.
    if _dst not in SOURCES:
        print(f"check-receipt-schema: {_dst} is a mirror but not a SOURCE, so a missing "
              "file would be skipped rather than caught — see #16.", file=sys.stderr)
        sys.exit(1)
    a, b = ROOT / _src, ROOT / _dst
    if not b.is_file():
        continue  # unreachable today; a mirror that does not exist cannot have drifted
    if a.read_bytes() != b.read_bytes():
        print("check-receipt-schema FAILED — a mirrored contract has drifted", file=sys.stderr)
        print(f"  {_dst} differs from {_src}", file=sys.stderr)
        print("  The mirror is regenerated by copying, not by editing. Run:", file=sys.stderr)
        print(f"      cp {_src} {_dst}", file=sys.stderr)
        sys.exit(1)

if len(SOURCES) < 2:
    print(
        "check-receipt-schema: SOURCES lists fewer than two copies, so there is nothing to "
        "compare. A guard with an empty work-set must not report success — see #16.",
        file=sys.stderr,
    )
    sys.exit(1)

first, *rest = SOURCES
if any(found[r] != found[first] for r in rest):
    print("check-receipt-schema FAILED — the receipt schema differs between its copies", file=sys.stderr)
    for rel in SOURCES:
        print(f"  {rel}:", file=sys.stderr)
        print(f"    {found[rel]}", file=sys.stderr)
    # Union, not the first two. With three sources a drift confined to the third — the
    # hand-mirrored copy, and so the likeliest — left this empty and printed "different
    # order", sending the reader after a reordering that does not exist.
    every = set().union(*(set(v) for v in found.values()))
    shared = set.intersection(*(set(v) for v in found.values()))
    only = every - shared
    if only:
        print(f"  fields present in one copy and not the other: {sorted(only)}", file=sys.stderr)
    else:
        print("  same fields, different order — the block is copied top to bottom", file=sys.stderr)
    sys.exit(1)

absent = [f for f in REQUIRED if f not in found[first]]
if absent:
    print("check-receipt-schema FAILED — the agreed schema is missing required field(s)", file=sys.stderr)
    print(f"  missing: {absent}", file=sys.stderr)
    print(f"  agreed:  {found[first]}", file=sys.stderr)
    print("  The copies agreeing is not enough. Every copy dropping the same field agrees too.", file=sys.stderr)
    sys.exit(1)

# --- A required field must have a producer on every reviewer's allow-list -----------------
#
# #105. The Receipt block and the Bash policy live in the same document but were written
# against different questions: `reviewed_at` was specified as something the record must
# CONTAIN, with no pass asking what a reviewer is permitted to RUN to fill it. No allow-list
# named a clock, and the contract also says to raise a finding rather than run an off-list
# command — so every reviewer resolved a contradiction on its own, three ways in one week.
#
# The rule is a pairing, in both directions. A field the contract requires must have a
# command on every allow-list; a command demanded of every allow-list must be required by the
# contract. Checking only the first leaves the guard demanding a clock the day `reviewed_at`
# leaves the schema, and a guard that outlives its reason is one that gets switched off.

#: Every reviewer whose allow-list this repository controls. The three shipped ones are the
#: product, `_template` is what an unrecognised stack starts from, and the `.claude/` one is
#: what actually reviews this repository — the copy missed on this guard's first pass, which
#: is the whole reason that omission is called out in SOURCES above.
REVIEWERS = (
    "agents/ts-reviewer.md",
    "agents/python-reviewer.md",
    "agents/dart-flutter-reviewer.md",
    "agents/_template/reviewer.md",
    ".claude/agents/gate-sdd-reviewer.md",
)

#: The work-set, stated in full so it can never be silently empty — the failure #16 and #39
#: are both about. Every field in the agreed schema appears here exactly once, and the
#: `None` entries are a claim, not a gap: those values are known to the reviewer from its own
#: run or from a command already on every list. A field added to the contract with no entry
#: here fails the completeness check below rather than reaching a reviewer that cannot
#: produce it.
PRODUCERS = {
    "reviewed_sha": None,   # `git rev-parse HEAD`, on every allow-list already
    "reviewer": None,       # its own name
    "verdict": None,        # its own findings
    "blockers": None,       # its own findings
    "high": None,           # its own findings
    "reviewed_at": ("date -u", "names no clock", "date -u +%Y-%m-%dT%H:%M:%SZ"),
    "reviewed_by": None,    # whether it was spawned, which only it knows
}

# Completeness before correctness. An unknown field is a field nobody asked the producer
# question about, which is exactly how #105 arrived.
unmapped = [f for f in found[first] if f not in PRODUCERS]
if unmapped:
    print("check-receipt-schema FAILED — a receipt field has no entry in PRODUCERS", file=sys.stderr)
    print(f"  unmapped: {unmapped}", file=sys.stderr)
    print("  Say how a reviewer obtains it. `None` means it is known from the reviewer's own", file=sys.stderr)
    print("  run or from a command already on every allow-list — a claim, not a shrug.", file=sys.stderr)
    sys.exit(1)

#: Only the fields the agreed schema actually requires are demanded of the reviewers, so the
#: pairing releases as well as binds.
_demanded = {f: PRODUCERS[f] for f in found[first] if PRODUCERS[f] is not None}

if _demanded:
    _failures = []
    for _rel in REVIEWERS:
        _path = ROOT / _rel
        if not _path.is_file():
            # Not a skip. `scripts/` is this repository's own guard set and never ships, so a
            # reviewer named here and absent from disk is a rename nobody finished, not an
            # optional component.
            print(f"check-receipt-schema FAILED — {_rel} is listed in REVIEWERS but is missing", file=sys.stderr)
            sys.exit(1)
        _policy = bash_policy(_path)
        if _policy is None:
            print(f"check-receipt-schema FAILED — {_rel} has no '## Bash policy' section", file=sys.stderr)
            print("  The allow-list is what keeps a read-only reviewer read-only. A reviewer", file=sys.stderr)
            print("  without one is not a narrower reviewer; it is an unscoped one.", file=sys.stderr)
            sys.exit(1)
        for _field, (_needle, _reason, _fix) in _demanded.items():
            if _needle not in _policy:
                _failures.append((_rel, _field, _reason, _fix))
    if _failures:
        print("check-receipt-schema FAILED — a reviewer cannot produce a field the contract requires", file=sys.stderr)
        for _rel, _field, _reason, _fix in _failures:
            print(f"  {_rel}: the contract requires {_field} but this reviewer's Bash policy {_reason}", file=sys.stderr)
            print(f"    add to its allow-list: {_fix}", file=sys.stderr)
        print("  A field required by the contract and forbidden by the allow-list is not a", file=sys.stderr)
        print("  strict reviewer. It is one that has been taught the allow-list is negotiable.", file=sys.stderr)
        sys.exit(1)

print(f"check-receipt-schema: {len(found[first])} field(s) agree across {len(SOURCES)} copies, "
      f"and {len(REVIEWERS)} reviewer(s) can produce the {len(_demanded)} needing a command")
