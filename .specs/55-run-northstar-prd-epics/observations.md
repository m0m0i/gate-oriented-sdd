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

### Every author pause so far has returned the draft unchanged

Clarification 2's protocol has run **twice** as of T3 — T2 carrying the metric and the
non-negotiable, T3 carrying CAP-6's falsifier and the third user — and all four answers confirmed
the draft exactly. *(Corrected on review: this section originally read "three of three", counting
four items as three pauses. T4 later added a third pause carrying one question. Final tally: three
pauses, five questions, all five accepted as recommended.)* T2 recorded that
this cannot distinguish "the drafts were right" from "a plausible answer was accepted because it
came first". Three for three does not resolve that; it raises how much of this run rests on it.

Stated plainly: **this run tests the skills' mechanics and their seams. It does not test their
interviews.** Anything claimed about whether these skills elicit good product decisions from a
user is unsupported by this run.

## T4 — `epics`

**AC5 verified**, as amended. Four epics, four `Demo:` sentences, every `- Serves:` id resolving
verbatim in `docs/PRD.md`, and an explicit recorded reason no epic is the walking skeleton.

### `epics` has no vocabulary for a product that already ships

Step 6: *"Say which epic is the walking skeleton — the thinnest end-to-end path through the whole
system. It goes first, always, because it is the only thing that discovers integration problems
while they are still cheap."* Red flag: *"No epic is the walking skeleton. Then integration risk
is being deferred."* Field: `Walking skeleton: yes | no`.

Every one of those assumes greenfield. This system's thinnest end-to-end path was the first spec
carried through `implement`, the reviewer and a merged PR; it discovered exactly the integration
problems it exists to discover — #1, #2, #8 — weeks ago. Nothing remaining is a skeleton.

The skill offers no way to say that. A mature project running it is pushed toward marking some
epic `yes` to satisfy a defined field with a meaning that does not apply, and **no rule, red flag,
or template line warns against it.** This is the first finding of this run that is structural
rather than a missing sentence, and it applies to every consumer past their first release — which
is every consumer, eventually.

Recorded in `EPICS.md` under its own heading rather than by designation. AC5 was amended to accept
that; see clarification 5.

### The forward-only citation check, second instance

T3 found `prd` checks that every capability names a real lever, and nothing checks that every
lever is served. `epics` has the identical asymmetry: step 3 says *"Give each an id and name the
capability it serves"*, and nothing asks whether every capability has an epic.

Run in reverse, the first draft left **CAP-3 and CAP-4 served by nothing** — while their remaining
work sat in three of the four epics under other `Serves:` lines. #25 is independence work, #19 is
what makes a rulebook pinnable, #22 is the completeness of what `init` leaves behind. The epics
were right; their citations were incomplete, and neither the skill nor AC5 would have noticed.

After completing the `Serves:` lines, the same reverse check:

```
CAP-1 served by 3 epic lines
CAP-2 served by 1
CAP-3 served by 2      <-- 0 in the first draft
CAP-4 served by 1      <-- 0 in the first draft
CAP-5 served by 1
CAP-6 served by 1
CAP-7 served by 2
```

*Recorded on review:* the pre-fix drafts do not exist on the branch. Each was corrected inside its
own task commit, so `git show 94a91f8:docs/PRD.md` already contains CAP-7 and
`git show d5445dd:docs/EPICS.md` already contains the completed `Serves:` lines. These count
tables are the artifact; the drafts are not reproducible, and a reader who was not present is
taking the operator's word for what they contained.

**Two skills, same defect, found the same way.** That makes it one issue rather than two
observations: *every citation seam in the inception chain is checked forward and never backward.*
`northstar` → `prd` → `epics` all pass while a lever or a capability quietly serves nothing, and
the document set reads as complete. It is also a candidate contract for #54 on both skills, with
this run as the incident.

### Smaller notes

- The template's `- Serves: <capability id>` is singular. Every epic here serves two or three, and
  nothing says whether that is allowed. Writing multiple ids is an inference, like T3's merge.
- Epic contents came from the tracker, not from a backlog: `docs/BACKLOG.md` already orders **12**
  of the 16. Six — #47, #48, #49, #54, #55, #56 — are in no backlog row, and two of the backlog's
  rows, #10 and #28, are in no epic. Step 5 says to list issues "at the granularity `spec` consumes", and here they
  already existed at that granularity — the inversion `BACKLOG.md` names in its own preamble.
  `epics` assumes it runs before issues exist, and gives no instruction for the case where they do.

## T6 — baseline re-verified

**AC1 verified.** All eight validators exit 0; `test-gates.sh` at 52 passed, 0 failed — identical
to T1.
**AC2 verified.** `- Owns:` sha256 `3f52ee31…`, matching the baseline exactly.
**AC8 verified, as amended.** `docs/BACKLOG.md` (`d72253ff…`), `.steering/tech.md` (`5e544055…`)
and `.steering/structure.md` (`061e0ff7…`) all byte-identical. The diff against `main` touches
`docs/`, `.specs/55-run-northstar-prd-epics/`, and `.steering/product.md` — nothing else, and no
shipped path.

Nothing in the run degraded a gate or a guard, which was the thing most worth being sure of and
the thing that could not have been asserted without T1's capture.


## Recorded on review — two consequences the run created and did not name

The reviewer found both. Neither is a defect in a skill; both are things this run did to the
repository that AC7 required it to record and it did not.

### `docs/BACKLOG.md`'s preamble is now false by construction

It still reads: *"There are still no epics. `epics` has never run, and `docs/` holds none of the
inception documents except this one — see #22."* All three clauses were true at `main`. All three
are false at this tip.

The file was correctly **not** edited — "What must NOT change" forbids it, AC8 confines the diff,
and "a defect found mid-run gets an issue, not a fix" is the right handling. But the run's
deliverable is the record, and a document this run falsified is exactly what the record is for.
Re-grooming is `backlog`'s job on its own branch. Same shape as #23.

### The `CAP-` prefix collides with `check-leakage.sh`'s tier-2 pattern

`scripts/check-leakage.sh:27` is:

```
IDS='\bNS-[0-9]|\bCAP-[a-z]|\bCON-[a-z]|\bADR-[0-9]{4}'
```

and its own comment at `:24-26` says *"it is the **numbered** forms that carry meaning from the
private docs hub."* `CAP-` is guarded only in its lowercase form, so `CAP-1` passes — which is why
the guard is green today. This branch has now made `CAP-1`…`CAP-7` the repository's permanent
public id vocabulary across four files. Correcting the pattern to `CAP-[0-9]`, the fix the comment
asks for, would immediately fail on this repo's own documents; and `:18` forbids the only other
exit — *"Nothing else may be excluded — an allowlist here is how a guard rots."*

The run took deliberate care over `LV-`, choosing it because it appeared nowhere in the repository
and verifying that in `baseline.md`. It applied none of that care to `CAP-`, and `CAP-` is the one
that appears in a guard.

Both need follow-up issues. Neither is fixable on this branch without breaching AC8.
