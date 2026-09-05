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

**AC3 — verified at the review-fix commit, not at T2.** One line changed in each of the three files; nothing else in the diff but this directory; `docs/verified.md` at its baseline checksum. At T2 the leakage guard was red and the loop did not stop; the nine validators were at exit 0 only after the reviewer's BLOCKER was fixed, with a loop that stops on failure.

**A guard fired on this branch's own spec.** `check-leakage.sh` flagged `spec.md:8` for a placeholder of the form the tier-2 pattern matches — the capability prefix, a hyphen, one lowercase letter — which #57 says is the wrong form to guard. Rewritten as "every capability id"; the T2 commit had landed with the guard red because the validator loop printed exit codes without stopping on them, which is the second time today a post-write guard was not honoured by hand (#73). Noted on #57 as a live instance. **Then the same token was written into this paragraph after the guard had run, and committed** — the reviewer's BLOCKER. The loop now stops on the first non-zero exit and runs after the last write.

**Review triage.** BLOCKER — the leak token in this file's own record of the leak: rewritten, and the guard run after the last write. HIGH — `product.md:27` claimed `DESIGN.md` was the only citer while `EPICS.md`'s Serves lines cite every capability; it now names both and keeps "nothing consumes them mechanically". INFO accepted: `verified.md:114` stays, corrected by its later sections.
