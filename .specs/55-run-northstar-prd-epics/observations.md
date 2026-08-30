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

## T3 — `prd`

**AC4 verified.** Every lever id cited in `docs/PRD.md` resolves verbatim in
`docs/NORTH_STAR.md`: LV-1, LV-2, LV-3, LV-4, LV-5, five of five.
**AC4b verified.** `PRD.md` carries `Status: draft` and states in its own header that nothing
cites the capability ids; the `.steering/product.md` summary repeats it.

### AC4 as written would have passed over a real gap

The criterion asks one direction — every capability names a lever that exists. Run that way it
passed on the first draft. Run in **reverse**, which the spec never required, it did not:

```
LV-1 served by 2 capability lines
LV-2 served by 0        <-- the first draft
LV-3 served by 1
LV-4 served by 3
LV-5 served by 1
```

`LV-2` is gate narrowness, which `NORTH_STAR.md` calls one of "the pair that actually decides the
number", and no capability served it. `prd`'s rules cover the forward direction — *"Every
capability cites a lever. If none fits, either the lever list is incomplete or the capability does
not belong."* — and say nothing about a lever no capability serves. Nothing in the skill, and
nothing in this spec, would have caught it.

Fixed by adding CAP-7. The finding is not the missing capability, which is authoring; it is that
**the check only runs one way**, in the skill and in AC4 alike.

### Step 7 wrote to a hand-authored file with no instruction for the case

`prd` step 7: *"Register the ids wherever this project tracks them, and summarise into
`.steering/product.md`."* That file is hand-authored — "Who uses it", "What it deliberately is
not", "The claim that has to stay true" — and step 7 says nothing about what to do when content is
already present.

The result was additive: 19 insertions, 0 deletions, all three sections kept, `- Owns:`
byte-identical, anchors 5 of 5. **But that came from the operator, not the skill.** A session that
read "summarise into" as "write the summary to" and replaced the file would have been equally
compliant with the text, and would have destroyed the `Owns:` anchor and its rationale in the same
move — #34's cost, arriving through a skill instead of through a parser.

Paired with T2's note on `northstar` step 6, this is one finding on two skills: **both write to
`.steering/product.md`, and neither states a merge rule.** Unlike T2's null result this one is
backed by an actual write, which makes it the stronger candidate of the two for #54.

### Three of three author pauses returned the draft unchanged

Clarification 2's protocol has now run three times — the metric, the non-negotiable, CAP-6's
falsifier, and the third user — and every answer confirmed the draft exactly. T2 recorded that
this cannot distinguish "the drafts were right" from "a plausible answer was accepted because it
came first". Three for three does not resolve that; it raises how much of this run rests on it.

Stated plainly: **this run tests the skills' mechanics and their seams. It does not test their
interviews.** Anything claimed about whether these skills elicit good product decisions from a
user is unsupported by this run.
