# Observations — #78

## T1 — baseline

- anchors: check-steering-anchors: 5 of 5 anchor(s) resolved, none unreadable
- grep hits: 3
    .steering/product.md:27:`LV-*` are the levers in `docs/NORTH_STAR.md`. **Nothing cites these ids yet** — no spec is required to name a capab
    docs/PRD.md:6:Nothing cites the capability ids below yet. That is recorded deliberately rather than left to be discovered — see `docs/verifi
    docs/EPICS.md:4:- Status: draft — nothing cites these ids; see `docs/verified.md`.
- `.steering/product.md` 7151a38e2ddb
- `docs/PRD.md` 164bd25d5321
- `docs/EPICS.md` dab97c5c1bc6
- `docs/verified.md` 282e993f1481
- `.steering/tech.md` 60fe179aa311
- anchor lines saved for AC2

## T2 — the restatement

**AC1 verified.** The grep returns nothing; each restated sentence names the citing document and keeps "no check" and "nothing consumes them mechanically".

**AC2 verified.** Anchors 5 of 5; the five anchor lines byte-identical to T1's copy.

**AC3 verified.** One line changed in each of the three files; nothing else in the diff but this directory; `docs/verified.md` at its baseline checksum; nine validators at exit 0, `test-gates.sh` 54/0.
