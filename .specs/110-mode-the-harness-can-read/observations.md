# Observations — 110-mode-the-harness-can-read

## Review round 1 — BLOCKED, 0 blockers, 1 HIGH, 6 MEDIUM, 4 LOW

Reviewed at `fa74d43`. The checker itself survived: the reviewer traced every early exit and
could not find a path to the success line that verifies nothing, which was AC4's whole claim.
The HIGH is about something else entirely — **where the checker runs**, not what it does.

### HIGH — the validator's trigger does not overlap its subject

`hooks/quality-gate.sh:49-58` runs the `- Validators:` line **only when a path matching
`- Source globs:` changed**, and `gate_pass`es otherwise. A document is never source: one line
points at documents, the other at code, so the two sets are **disjoint by construction** — not
by oversight, and not only here. Every consumer inherits it.

So the checker ran on exactly the turns where nothing it checks could have changed, and was
absent on the turns where something did. The coverage window, inverted. And it was invisible,
because every run was green.

Demonstrated rather than reasoned about, before fixing:

```
$ rm docs/CONTRACT.md
$ ./assets/check-document-set.py
check-document-set: mode is `full` and 1 required item(s) are not found: docs/CONTRACT.md   (exit 1)
$ sh hooks/quality-gate.sh
(exit 0)
```

The turn ends **green** on a full-mode project that just lost a required document. It was also
the only one of the ten validators with no step in `.github/workflows/ci.yml`, so CI missed it
too — the two gaps compounding rather than covering for each other.

Fixed on both halves: a CI step, and the sentence `init` already carries for `check-locks.py`
("add it to the project's CI beside its other validators") now on the document-set bullet, with
the reason stated so a reader knows why this one cannot rely on the turn-end gate.

### The six MEDIUMs

- **"on every turn" was false in both READMEs.** The sentence that would have stopped anyone
  looking for the HIGH. C-3 was satisfied, which only meant both languages were wrong the same
  way. Now: whenever the quality gate runs, **and in CI, which is where it actually bites**.
- **`check-skill-contracts.py`'s docstring said "Ten today."** while the table held fourteen.
  C-2, in the guard whose own output prints the real number.
- **Four new entries, no argument for any of them.** That guard's docstring requires the
  argument be made *in the spec that proposes it*, and #54 is the standing case against growth.
  Two were genuinely weak on the incumbent standard — ordinary prose whose deletion is visible
  in a diff. The argument is now written per entry and tabulated in the spec's Design; the two
  weaker ones are kept because their deletions read as *tightening* (`spec`) and as *imprecision*
  (`contract`), which are the two shapes review waves through.
- **`- Mode:` joined the machine-read family but not `ANCHORS`.** Not a fail-open — the checker
  catches the bolded form and a case pins it — but the diagnosis landed in the wrong guard, and
  a project may declare the mode without installing the checker at all (multi-repo installs skip
  it), leaving the new anchor checked by nothing. Added.
- **`steering_value()` was not the byte-for-byte copy its own comment claimed.** `sed` does not
  trim what follows a value; the Python called `.strip()`. The divergence was in the
  **permissive** direction — accepting a value a shell consumer would not match — which is #34
  inverted and the direction that passes silently. `.strip()` removed, parity restored, and the
  trailing-whitespace case now fails with a sentence naming the real cause instead of a
  confusing one.
- **T2 promised three cases and delivered two.** The re-run upgrade path — the thing that stops
  `init` recreating documents the author declined — had prose and no pin. Now a fifth entry and
  an extended case 59.

### The four LOWs

- The success line counted issue templates as documents: `9 document(s)` for 6 documents and 3
  templates. **The exact conflation this spec corrected in the issue**, reintroduced one layer
  down in the checker's own output. Now counted in their own units.
- The remote-`Docs` fixture built a real directory tree at `$r/https:/example.invalid/docs`, so
  case 58 discriminated partly by accident — it survived only because `add_full_docs` is not
  called for it. One "for symmetry" edit from going green on a checker that reads a URL as a
  directory. The fixture now skips seeding when the value contains `://`. G-4.
- `spec`'s new mode read gave two outcomes where the checker insists on three: nothing covered
  an absent line, which is every project installed before this feature. Now treats an absent
  line as `full` **and says so**, rather than defaulting in silence — the harness had just
  spent a checker insisting this value is never defaulted.
- `add_full_docs`'s unexercised `${2:-docs}` was a near-miss default next to the `$2`-under-`set -u`
  trap that already bit once in this branch. Removed.

### What this round was actually about

Round 1 of #109 found the artifact correct and the evidence wrong. This round is the inverse and
more useful: **the artifact and its evidence were both right, and the wiring between the check
and the thing it checks was not.** A validator whose trigger cannot overlap its subject is a new
shape for this repository — not a fail-open in the guard, but a guard installed where it can
never fire on the change it exists to catch. Worth remembering as its own question: *when this
runs, could the thing it checks have just changed?*

## Review round 2 — BLOCKED, 0 blockers, 1 HIGH, 2 MEDIUM, 3 LOW

Reviewed at `0a1e6e8`. Round 1's HIGH and all ten lesser findings verified fixed. **The new HIGH
was introduced by round 1's own fix**, which is the second time on this branch's family that a
repair has carried its own defect in.

### HIGH — the parity fix was an intention, not a behaviour

Round 1's MEDIUM removed `.strip()` from `steering_value()` so it would return exactly what
`sed -n "s/^ *- *KEY: *//p"` returns. Nothing asserted it. **Restoring `.strip()` reintroduced
the divergence with all 71 cases green** — so a later "tidy up this odd return" commit would
have undone it unopposed, with every gate agreeing it was fine. G-4: no case, not shipped.

The suite number is what gave it away. `0a1e6e8` added a decision branch and extended an
existing case; it added no case, so the count stayed at 71 across a round that changed guard
behaviour.

Case 60 now pins it, and the mutation results are the argument for how it is written:

| Mutation | Caught by |
| :-- | :-- |
| restore `.strip()` — the exact regression | `mode-exit`, `mode-names-whitespace` |
| strip `Docs` the same way — over-correction | `docs-tolerant` |
| keep parity, drop the whitespace message | `mode-names-whitespace`, `mode-not-generic` |

The third is why the case asserts the **message** and not only the exit code: the reviewer's
point was that exit 1 alone cannot distinguish the parity fix from the pre-existing "not a
mode" branch, and mutant C proves it — exit is right, both message assertions red.

### MEDIUM — `Docs` did rely on the trim, and the parity argument does not reach it

The direction claim held for `Mode`, and the reviewer re-derived parity input by input. But
`docs_value` flows into `pathlib.Path`, and `Path("docs/ ")` is a directory named `" "` inside
`docs/` — so `- Docs: docs/ ` went from passing to failing with a message whose cause is
invisible in rendered Markdown. **And no shell consumer ever paths on `Docs`**:
`gate_steering_value` is called for Validators, Source globs, Owns and Reviewer, and the
anchors guard reads Docs only to test it non-empty. There is no reader there to be stricter
than, so the removal was a pure robustness regression at that caller.

`Docs` is stripped again, `Mode` is not, and the asymmetry now carries the reason at both the
code and the case. One rule applied to both would be wrong at one end or the other.

### The rest

- **"Fifteen today. An eleventh needs an argument…"** — the count moved and the ordinal did
  not, so the threshold read as five entries already breached. C-2, in the sentence that exists
  to impose a limit.
- **The docstring cited `report_whitespace`**, a function that does not exist; the behaviour is
  an inline branch. A comment naming a mechanism nothing can grep for.
- **`init`'s new clause was spliced as a fragment** — lowercase "and" after a full stop, in the
  one file whose sentences are the deliverable rather than a description of it.
- **The `contract` entry's argument did not support the entry.** It cited #109, whose failure
  was a sentence that *existed and was wrong* — which a presence check cannot catch. Corrected
  to the deletion case, which is the only case presence checks make: that sentence is the one
  place any document says a minimum-mode project may run the skill **at all**, so removing it
  leaves the skill reading complete while a model executing it there has no permission to point
  at. Worth recording as a general trap: **an argument for a guard must be an argument for the
  kind of failure that guard can detect**, and a plausible-sounding precedent about the wrong
  failure mode is harder to notice than no precedent at all.

### The pattern across both rounds

Round 1: the checker was right and its wiring was wrong. Round 2: the round-1 fixes were right
and two of them were unpinned or over-applied. Neither round found a defect in what the feature
*does* — both found defects in the connective tissue around it. That is the same lesson #109
recorded from the other side, and it is now twice-earned: **a fix is not finished when it is
correct; it is finished when reverting it turns something red.**
