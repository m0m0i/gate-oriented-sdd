#!/usr/bin/env python3
"""Fail when the two copies of the Receipt block disagree about its fields.

The reviewer emits the Receipt block; `implement` copies it verbatim into
`.specs/<slug>/.review-receipt`; `review-gate.sh` reads that file. The schema therefore
exists in two documents at once — `agents/_shared/reviewer-contract.md` defines it and
`skills/implement/SKILL.md` reproduces it — and nothing has ever checked that they agree.

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
)

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
        if m:
            if m.group(1) == "reviewed_sha":
                started, names = True, [m.group(1)]
                continue
            if started:
                names.append(m.group(1))
        elif started:
            break  # the block ended; take the first one only
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

first, *rest = SOURCES
if any(found[r] != found[first] for r in rest):
    print("check-receipt-schema FAILED — the receipt schema differs between its copies", file=sys.stderr)
    for rel in SOURCES:
        print(f"  {rel}:", file=sys.stderr)
        print(f"    {found[rel]}", file=sys.stderr)
    only = set(found[first]) ^ set(found[rest[0]])
    if only:
        print(f"  fields present in one copy and not the other: {sorted(only)}", file=sys.stderr)
    else:
        print("  same fields, different order — the block is copied top to bottom", file=sys.stderr)
    sys.exit(1)

print(f"check-receipt-schema: {len(found[first])} field(s) agree across {len(SOURCES)} copies")
