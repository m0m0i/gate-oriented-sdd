# Spec: the normalisation-asymmetry fail-open has no rule id
- Slug: 45-g9-normalisation-asymmetry   Issue: 45   Type: bug   Status: done
- Author: m0m0i   Date: 2026-08-28

## 1. Requirements (WHAT / WHY)

- Reproduction: during #10's review (PR #44), a fix for one fail-open in `scripts/check-templates.py`
  introduced another. Prose-stripping was applied to both the accusing and the clearing pattern, and
  two purely red task lines began clearing:

  ```
  - [ ] T1: write the `failing test` for <behavior>          -> cleared
  - [ ] T1: add the failing/regression test for <behavior>   -> cleared
  ```

  Both were flagged correctly *before* the fix. The reviewer had to derive the principle from first
  principles mid-review, because no rule id covers it. Grep the rulebook for it and there is nothing:

  ```
  $ grep -n "normalis\|strip\|canonicalis" .claude/agents/gate-sdd-reviewer/rules/gates-and-guards.md
  (no output)
  ```

- Expected: a class of fail-open that has already bitten this repo is citable by a rule id, so the
  next reviewer recognises it instead of re-deriving it.

- Actual: it exists in exactly two places, neither of which a reviewer reads — a comment in
  `scripts/check-templates.py` beside the regex it constrains, and §4 of an archived spec.

- Impact: every guard that canonicalises input before matching, which is every guard the moment one
  of them grows a normalisation step. `check-templates.py` is the only current instance, so the
  live blast radius is one file — but the defect it produced was invisible to a full ablation
  suite and was caught only because a reviewer read the diff adversarially.

- **Root cause:** `G-1` already covers the *symptom* — "a guard must not exit 0 on a path where it
  could not do its job" — but names no mechanism, so it is only recognisable after the fact. The
  G-series has eight rules about guard shape and none about input handling. Normalisation is the
  first transformation any guard grows, and the direction of its danger is counter-intuitive:
  stripping feels like it makes a check *stricter*, and on the clearing side it does. On the
  accusing side it does the opposite, silently.

- **Two of the issue's premises are wrong, and both change scope.** Recorded here rather than
  discovered during implementation:

  1. **`gates-and-guards.md` exists only for this repo's own reviewer**, at
     `.claude/agents/gate-sdd-reviewer/rules/`. The issue says to add `G-9` "for the three shipped
     reviewers plus the template". Those reviewers have no G-series at all — they carry
     `correctness-and-tests.md` (`COR-*`, `TST-*`) and `types-and-style.md`, and the template carries
     `starter.md` with `{{PREFIX}}-*` placeholders. There is no file to add `G-9` to there.
  2. **The file that needs the rule is deliberately unpinned**, so no re-pin is required.
     `.claude/agents/gate-sdd-reviewer/` contains only `rules/` — no `rules-lock.json` — and
     `AGENTS.md`:74-77 explains that adding one makes `check-locks.py` stop verifying the six
     shipped rulebooks. That is #16's residue, waiting on #19. **The reviewer's stated reason for
     carrying this off #10's branch — that the rulebook is hash-pinned and a re-pin has no business
     in a bug fix — was therefore false.** The work was still worth separating, but not for that
     reason, and the record should not keep a wrong justification.

- Acceptance criteria:
  - [x] **AC1:** `G-9` SHALL exist in `.claude/agents/gate-sdd-reviewer/rules/gates-and-guards.md`,
        citable by id, stating the asymmetry as a property rather than as an anecdote.
  - [x] **AC2:** `G-9` SHALL carry an observable check — concrete enough that two reviewers would
        flag the same lines — matching the format the surrounding G-rules use.
  - [x] **AC3:** every guard in `scripts/`, `assets/` and `hooks/` SHALL be audited for the shape,
        and the result recorded in the spec: which guards normalise input at all, and for each, on
        which side.
  - [x] **AC4:** WHEN the audit finds a live instance THE SYSTEM SHALL have it either fixed with a
        failing case first, or filed as its own issue with the reasoning — never left implicit.
  - [x] **AC5:** `./assets/check-locks.py` SHALL still report six pinned files across both reviewer
        directories, so this change does not disturb #16's standing workaround.

- Out of scope:
  - **Pinning the dogfood rulebook** — that is #19, and doing it here reintroduces #16.
  - **Fixing #47** (all three `rules-lock.json` notes say "Grounding for ts-reviewer"), which is in
    files adjacent to this work and will be tempting to tidy. It is its own issue.

### Clarifications
_2026-08-28._

- **Q: where does the rule land, given the G-series exists only for this repo's own reviewer?**
  A: the dogfood reviewer only — `.claude/agents/gate-sdd-reviewer/rules/gates-and-guards.md`, and
  nowhere else. The three shipped reviewers review application code in a language; guard-writing is
  this repo's own domain, and their rulebooks have no guard rules to extend. Adding an equivalent
  `COR-*` rule to each was rejected: those rulebooks *are* hash-pinned, so it would need the re-pin
  the issue wrongly assumed was needed here, and it turns a one-file prose fix into four files plus
  three locks. `agents/_template/rules/starter.md` was also rejected — it is placeholder scaffolding
  (`{{PREFIX}}-001`), and a concrete rule sits oddly among stubs a copier is meant to replace.

- **Q: `check-skill-contracts.py`'s `flat()` collapses whitespace on both the needle and the file
  text, which makes matching easier — the lenient direction for a presence check. Instance or not?**
  A: not an instance, and `G-9` must say so. It is one comparison with both operands canonicalised,
  which is legitimate; the defect is a guard with *two* patterns, one accusing and one clearing,
  where the normalisation is applied to the accusing side. Without the carve-out the rule condemns
  correct code, and a rule that fires on correct code is a rule reviewers learn to skip. Fixing
  `flat()` was rejected outright: the normalisation is what stops the guard false-failing on
  rewrapped prose, and a guard that false-fails is a guard someone deletes.

## 2. Design (HOW)

- **Fix approach.** One rule appended to one file, and an audit recorded in this spec. `G-9` follows
  the format of `G-1` through `G-8` — a bolded id, the property stated first, then why, then the
  observable check — and carries the carve-out from the second clarification, because the rule was
  derived from a case that has a legitimate near-neighbour in this very repository.

  *Wider, rejected — on cost, and the first version of this paragraph rejected it on a false
  premise.* A mechanical check on the rulebook's citations was rejected here as "green on arrival".
  That was true only of the scope named — ids unique, cross-references *inside* the file resolving —
  and that is the scope guaranteed to find nothing. The scope that would have found something is
  resolving citations *outward*: `case N` against `test-gates.sh`, `#N` against the tracker, file
  paths against the tree. It would have gone red on this very branch, on a `case 39` that resolves
  to two different cases depending on whether you count source comments or printed output. So the
  conclusion stands but the ground for it does not: the reason not to build it is that nine rules do
  not need an index and `check-skill-contracts.py`'s docstring argues against policing prose — not
  that nothing was broken. Something was, and the fix was to stop citing ordinals at all.

- **There is no failing test for AC1 and AC2, and that is not a skipped step.** The deliverable is a
  rule for the judgment layer — a subagent that reads prose — and the harness's whole design is that
  judgment rules live in a rulebook precisely because they cannot be made deterministic. The
  property `G-9` describes *is* already pinned mechanically, by the `backticked-red` and
  `slashed-red` assertions in `scripts/test-gates.sh`, added in #10 when the defect was fixed. This
  spec adds the
  name, not the enforcement. Stated here because a bug spec with no red step otherwise reads as a
  corner cut, and because `G-4` — "every new gate behaviour needs a case" — correctly does not apply:
  no gate behaviour changes.

- **Affected files:** `.claude/agents/gate-sdd-reviewer/rules/gates-and-guards.md`, and this spec.
  Nothing shipped, so **no version bump** — `.claude/` is not in `check-version-bump.py`'s `SHIPPED`
  tuple, and `.steering/structure.md` marks it as this repo's own instance rather than product.

- **Blast radius:** the file is read by `gate-sdd-reviewer` on demand, only when a diff touches
  `hooks/` or anything that gates or guards. A wrong rule here costs review noise on future
  branches, not a broken build. It is deliberately **unpinned** — `.claude/agents/gate-sdd-reviewer/`
  has no `rules-lock.json` and must not gain one until #19, so `AC5` exists to confirm
  `check-locks.py` still reports six pinned files across both directories after this lands.

- **Why this cannot recur:** it can, and the honest claim is narrower. `G-9` does not prevent the
  defect; it makes it *nameable* in review, which is the layer this repo assigns to judgment. The
  one instance that existed is fixed, and pinned by the `backticked-red` and `slashed-red`
  assertions. What changes is that the next reviewer cites an id instead of deriving the principle
  mid-review, which is what happened on #44 and cost a
  round.

### The audit (AC3)
Recorded here rather than in a commit message, because it is the part a future reader needs.

Every guard in `scripts/`, `assets/` and `hooks/`, and what it normalises:

| Guard | Normalises | Side | Verdict |
| :-- | :-- | :-- | :-- |
| `check-templates.py` | `CODE_OR_PATH.sub` | **clearing only** | correct — the fixed instance, pinned by the `backticked-red` / `slashed-red` assertions |
| `check-templates.py` | `line.strip()` at collection | **accusing** | safe, see below |
| `check-skill-contracts.py` | `flat()` on both operands | one comparison | legitimate — the carve-out |
| `check-receipt-schema.py` | `line.strip()` for fence detection | structural | safe — `FIELD` matches the raw line |
| `check-leakage.sh` | `sed 's\|^\./\|\|'`; `sed 's/^/  /'` | work-set; display | safe — the three accusing greps read raw file content |
| `check-steering-anchors.sh` | `sed 's/^ *//'` | display, inside the error text | safe — the accusing `grep` reads the raw file |
| `check-version-bump.py` | `.stdout.strip()` | subprocess hygiene | not a matching normalisation |
| `review-gate.sh` | `tr -d "\"'"`; `tr '\n' ' '` | input to `git`; display | safe — no pattern pair; this is #1's fix |
| `quality-gate.sh` | `tr -d '\042\047'` | input to `git` | safe — same |
| `quality-gate.sh` | `sed -e 's/^ *//' -e 's/ *$//'` on each validator command | feeds an emptiness test | safe — a whitespace-only entry is not a validator |
| `gate-lib.sh` | `sed -n "s/^ *- *$2: *//p"`; the JSON escaper | extraction; display | safe — no pattern pair |
| `steering-digest.sh` | `sed -n 's/.*Status: *\([A-Za-z]*\).*/\1/p'` | extraction | safe — no pattern pair |
| `check-manifests.py`, `check-locks.py` | none | — | — |

*Three rows above were missing from the first version of this table and were added on review.* All
three are safe and the conclusion is unchanged, but a reader applying `G-9`'s Check literally — it
names `sed` — would have hit three lines the table said were not there. Their category is also what
forced `G-9`'s Check to grow a third outcome: most shell normalisation feeds an *extraction* or an
*emptiness test*, and the rule originally had no verdict for that, which is why this table needed
five ad-hoc categories the rule never defined.

**One live instance, already fixed** — `check-templates.py`'s `CODE_OR_PATH`, corrected in #10 and
pinned by the `backticked-red` and `slashed-red` assertions. **No new instance found**, so AC4 has
nothing to fix or file.

**The audit's one real finding is a normalisation on the accusing side that is nonetheless safe.**
`check-templates.py` stores `line.strip()` at collection, and `RED` then matches that stripped
string. By the naive reading of this rule that is exactly the defect. It is not, and the reason is
the thing `G-9` has to say precisely: `.strip()` removes only *leading and trailing* whitespace, and
an accusing cue lives in the interior of a line. A normalisation on the accusing side is safe when
it provably cannot remove an accusing cue — and unsafe as soon as it removes interior content, which
is what `CODE_OR_PATH` does and why it had to move. Without that distinction the rule would condemn
a `.strip()` in every guard in the repository, and a rule that fires on correct code is a rule
reviewers learn to skip.

## 3. Tasks (TDD-ordered)
> One task is one complete Red-Green-Refactor cycle, so one green commit. No red step exists for
> T2 — see the Design note above; the property is already pinned by the `backticked-red` and
> `slashed-red` assertions, from #10.

- [x] T1: audit every guard in `scripts/`, `assets/` and `hooks/` for normalisation applied before
      matching, and record the per-guard result in the section above — which normalise at all, and
      for each, on which side *(AC3, AC4)*
- [x] T2: write `G-9` in the dogfood rulebook, with its observable check and the `flat()` carve-out
      *(AC1, AC2)*
- [x] T3: confirm `check-locks.py` still reports six pinned files across both reviewer directories,
      that no `rules-lock.json` appeared under `.claude/agents/`, and that all nine validators pass
      *(AC5)*

## 4. Review triage

`gate-sdd-reviewer`, first pass at `2acf6ba`: **BLOCKED** — 0 BLOCKER, 2 HIGH, 2 MEDIUM, 1 LOW,
3 INFO. All five findings fixed; the INFOs are answered below.

- **HIGH — "stripping before the clearing pattern can only make the guard louder" is false for a
  substitution, and the counter-example is in the file G-9 cites as its own worked example.** Fixed.
  `CODE_OR_PATH.sub(" ", line)` *inserts*, so it can assemble a clearing cue that was not in the
  input — which `check-templates.py` documents on its own clearing side and accepts with an
  argument. G-9 as written told the next reviewer the clearing side was risk-free, so the one
  residual hole this repo knows about was the one the rule instructed them not to look for. The rule
  now rests the direction claim on "can only **delete**", and says a clearing-side substitution
  needs its own argument rather than inheriting the rule's blessing.

- **HIGH — the whitespace carve-out was granted categorically on a premise about this repo's current
  cues.** Fixed. "Cues live in a line's interior" is false for any accuser whose cue is indentation
  or trailing whitespace — and `G-7` names wrapped machine-read lines as a real failure with no
  mechanical check yet, so this repo is one plausible guard away from that class. Under the original
  wording a reviewer would have cited G-9 to *clear* a `.strip()` that destroyed the cue, which is
  `G-8`'s shape: an exemption certifying what it is not checking. Now conditioned on the accusing
  pattern's cues being unable to occur at a line's edges.

- **MEDIUM — `case 39` does not resolve.** Fixed, and the finding needs one correction. The reviewer
  said case 39 "never denoted this case"; it does — `scripts/test-gates.sh`:957 carries a literal
  `# 39.` comment above it. What is true, and is the part that matters, is that the file has **two
  numbering schemes that have diverged by twelve**: the source comments say 39, the printed output
  makes it the 51st, and the suite prints no numbers at all, so a reader cannot resolve the
  citation from the output they are looking at. An ordinal was the wrong handle regardless of which
  scheme is "right". All six sites now cite the greppable assertion names, and
  `scripts/check-templates.py`'s own pre-existing `case 32` was fixed with them rather than left as
  a known-drifted citation beside six corrected ones.

- **MEDIUM — the `flat()` carve-out gave the wrong reason, and the wrong reason generalises.**
  Fixed. "No second pattern to be asymmetric against" is true and irrelevant: a presence check
  accuses by *non-match*, so canonicalising the haystack is the lenient direction — which the
  clarification named and the rule then dropped. As written it pre-authorised any single-comparison
  guard with both operands canonicalised, including one whose equivalence class is far too coarse.
  Restated as the equivalence-class test: the class must be one the property does not distinguish.

- **LOW — the audit table missed three normalisations and recorded two files as "none".** Fixed:
  `quality-gate.sh`'s per-command trim, `gate-lib.sh`'s extraction and JSON escaper, and
  `steering-digest.sh`'s status extraction. All three are safe and the conclusion is unchanged, but
  a reader applying the Check literally would have hit three lines the table denied. Their category
  is also what forced the Check to grow a third outcome — most shell normalisation feeds an
  extraction or an emptiness test, and the rule had no verdict for that, which is why the table
  needed five ad-hoc categories the rule never defined.

- **INFO — was the no-failing-test reasoning self-serving?** Partly, and the reviewer was right
  about which part. The rejected checker was scoped to "ids unique, cross-references *inside* the
  file resolve", which is the scope guaranteed to find nothing; the scope that resolves citations
  *outward* would have gone red on this very branch, on `case 39`. The conclusion stands — nine
  rules do not need an index — but the ground for it was rewritten to cost rather than to the claim
  that nothing was broken, because something was.

- **INFO — both premise corrections were verified against the tree** by the reviewer independently.
  It also found the false justification still live at `.work_logs/2026-08-26.md`:66-68, pointing at
  a path that does not exist. Corrected at the worklog step rather than by rewriting a past entry,
  per that skill's rule that a corrected past is not an audit trail.

- **INFO — the reviewer's own Bash allow-list names six validators against the Validators line's
  eight**, so it cannot run `check-templates.py` or `check-steering-anchors.sh`. It disclosed this
  rather than reporting a complete-looking table. Filed as **#49** rather than fixed here: it is
  #14's shape in a different pair of documents, and the interesting half — deriving the allow-list
  from steering instead of restating it — is an escalation that needs its own argument, since it
  would make a reviewer's permitted commands a function of a file the branch under review can edit.

**Second pass at `267dc78`: APPROVE WITH NITS — CLEAN receipt, 0 BLOCKER, 0 HIGH, 1 MEDIUM,
2 LOW, 3 INFO.** All fixed.

- **MEDIUM — the Check's third verdict row read as a clean bill of health, and the reviewer raised
  it against a row it had asked for.** Fixed. "Not an instance" inherited the safety register of
  the two rows above it, while two of the four routes it names do reach a decision:
  `check-steering-anchors.sh` feeds an extraction into an emptiness test that is half its accusing
  condition (loosen it and you get #34), and `quality-gate.sh` and `review-gate.sh` strip quotes so
  `git` sees bare globs (get that wrong and you get #1). The verdict now hands off — *not an
  instance of G-9, but the value still reaches a decision, so check it against `G-1` and `G-2`.*

- **LOW — my citation replacement was applied mechanically and mangled three sentences.** Fixed by
  hand. Chained `.replace()` calls double-applied, leaving `assertions's backticked-red` in the
  sentence stating the audit's conclusion, a doubled citation in the Design note, and three prose
  lines over 125 columns. Worth recording rather than quietly repairing: the finding it was fixing
  was *about* citations being unreliable, and I introduced a worse one while fixing it.

- **LOW — "diverged by twelve" is a count in prose, inside the sentence explaining why counts make
  bad handles.** Fixed by dropping the number. The reviewer also found the source scheme is not
  injective: `# 14.` through `# 18.` are each used twice in `scripts/test-gates.sh`, so `case 15`
  through `case 18` are ambiguous *today*, and there are three counts in play — 44 numbered blocks,
  49 distinct case names, 51 printed results. The argument never needed the magnitude.

- **INFO — the rule assumed the accusing pattern accuses by matching.** Taken, three words: *whose
  match means the input is wrong*. For a presence check the accusation is the non-match, where a
  delete-only normalisation makes the accuser louder — the rule would have fired on something safe.
  Carve-out 2 already caught the one live case, so this was noise rather than a fail-open, but a
  rule that fires on correct code is one reviewers learn to skip.

- **INFO — the reviewer withdrew its own `case 39` evidence.** It had asserted "39 never denoted
  this case" from a count of `report` names without grepping for a source-side scheme. The
  conclusion survived; the evidence did not.

### On length, and where the audit table lives

`G-9` is 34 lines against 3–5 for every other rule. The reviewer's arrangement advice was taken in
full — the insertion caveat folded into the opening, the provenance cut to one line, the
illustrative counter-example dropped, the verdict table moved directly under the property — and that
is 6 lines, close to its own estimate of 8. Its accompanying target of "roughly twice a normal rule"
was not reachable and is not consistent with its own instruction that the three conditions *are* the
rule and must not be traded for brevity: the table alone is five lines and each condition is a
sentence that has already been wrong once. **Recorded as a deliberate miss rather than silently
approximated.** It is the only rule in the file whose misapplication is dangerous in both
directions, and the two-line version of it was wrong on two consecutive commits.

The audit table stays in this spec rather than moving to `docs/`. It is a dated snapshot of twelve
files that nothing checks, and a snapshot outliving its subject certifies what it is not checking —
`G-8`'s shape applied to a document. A second inventory in `docs/` would need hand-maintenance with
no guard. What moved instead is its one durable sentence, now the closing line of `G-9`: twelve
guards audited, one instance found and fixed, the rest extractions or display. The evidence stays
where evidence goes; the conclusion goes where the reviewer is already reading.
