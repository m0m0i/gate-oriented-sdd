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
    a, b = ROOT / _src, ROOT / _dst
    if not b.is_file():
        continue  # a consumer project has no mirror; only this repo does
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

print(f"check-receipt-schema: {len(found[first])} field(s) agree across {len(SOURCES)} copies")
