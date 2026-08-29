# Observations — the inception run

Recorded as each skill ran, per task. `docs/verified.md` is written from this file in T5.
The rule for this file: a seam that did not join, and a seam that was **not exercised**, are
both recorded. Only successes would make it useless.

## T2 — `northstar`

**AC2 verified.** `- Owns:` byte-identical to baseline
(`3f52ee31…`), `.steering/product.md` byte-identical as a whole (`635a65f2…`),
`check-steering-anchors.sh` resolving 5 of 5.

**AC3 verified.** `docs/NORTH_STAR.md` written, 5 levers, each carrying an `LV-` id.

### The seam I set out to observe was not exercised, and that is the result

AC2 was written to observe *"whether the skill preserves, merges, or clobbers an existing
`Owns:` value."* It did none of those, because **step 5's derivation produced the value that was
already there.** Law 1 of the drafted north star is "a gate fails closed", and the property
derived from it is "gates never fail open" — the existing line, word for word.

So `.steering/product.md` was never written to, and the collision path **remains unobserved.**
The honest reading is that this run tested that `northstar` does not gratuitously rewrite an
anchor it agrees with, which is a much weaker claim than AC2 was reaching for. A project whose
existing `Owns:` disagrees with the derivation is still a path nobody has watched, and it is the
path where #34's cost is actually paid.

That is a candidate contract for #54 and a candidate case for a throwaway run, not a result.

### The protocol weakened the test, and it is worth saying how

`northstar`'s last rule is explicit: *"Do not write this from the code. It is a product decision;
ask the user, and record their answer rather than a plausible one."*

Clarification 2 of the spec chose propose-then-correct: drafts derived from `README.md`,
`.steering/product.md`, and `docs/BACKLOG.md`, put to the author for correction. **Both product
decisions — the metric and the non-negotiable — came back confirmed exactly as drafted.**

Two readings, and this run cannot distinguish them: the drafts were right because the repository
genuinely encodes these decisions already, or a plausible answer was accepted because it was
presented first with a recommendation. That is precisely the failure the rule names. It does not
invalidate the document; it means the *interview* is still unobserved, as clarification 2 already
recorded, and the propose-then-correct path has now demonstrated the specific way it can go
quiet.

### Smaller notes

- Step 6 says "update `.steering/product.md` with the `- Owns:` line". With the derived value
  identical, no write was made. The skill gives no instruction for that case; treating "update"
  as a no-op when the value already matches is an inference, not something the text says.
- The template asks for one page. The result is 85 lines, which is a page only generously. Every
  section earns its place, but "one page" as written is not a limit anything checks.
