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

  *Wider, rejected:* a mechanical check that G-series ids are unique and that cross-references
  inside the rulebook resolve. It is buildable and it would be green on arrival, so it would be
  ceremony rather than a test — and `check-skill-contracts.py`'s own docstring makes the argument
  against it: "a check that grows to police every sentence becomes an obstacle to editing prose, and
  prose that cannot be edited rots." Nine rules do not need an index.

- **There is no failing test for AC1 and AC2, and that is not a skipped step.** The deliverable is a
  rule for the judgment layer — a subagent that reads prose — and the harness's whole design is that
  judgment rules live in a rulebook precisely because they cannot be made deterministic. The
  property `G-9` describes *is* already pinned mechanically, by case 39 in `scripts/test-gates.sh`
  (`backticked-red`, `slashed-red`), added in #10 when the defect was fixed. This spec adds the
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
  one instance that existed is fixed and pinned by case 39. What changes is that the next reviewer
  cites an id instead of deriving the principle mid-review, which is what happened on #44 and cost a
  round.

### The audit (AC3)
Recorded here rather than in a commit message, because it is the part a future reader needs.

Every guard in `scripts/`, `assets/` and `hooks/`, and what it normalises:

| Guard | Normalises | Side | Verdict |
| :-- | :-- | :-- | :-- |
| `check-templates.py` | `CODE_OR_PATH.sub` | **clearing only** | correct — the fixed instance, pinned by case 39 |
| `check-templates.py` | `line.strip()` at collection | **accusing** | safe, see below |
| `check-skill-contracts.py` | `flat()` on both operands | one comparison | legitimate — the carve-out |
| `check-receipt-schema.py` | `line.strip()` for fence detection | structural | safe — `FIELD` matches the raw line |
| `check-leakage.sh` | `sed 's\|^\./\|\|'`; `sed 's/^/  /'` | work-set; display | safe — the three accusing greps read raw file content |
| `check-steering-anchors.sh` | `sed 's/^ *//'` | display, inside the error text | safe — the accusing `grep` reads the raw file |
| `check-version-bump.py` | `.stdout.strip()` | subprocess hygiene | not a matching normalisation |
| `review-gate.sh` | `tr -d "\"'"`; `tr '\n' ' '` | input to `git`; display | safe — no pattern pair; this is #1's fix |
| `quality-gate.sh` | `tr -d '\042\047'` | input to `git` | safe — same |
| `check-manifests.py`, `check-locks.py`, `steering-digest.sh`, `gate-lib.sh` | none | — | — |

**One live instance, already fixed** (`check-templates.py`'s `CODE_OR_PATH`, corrected in #10 and
pinned by case 39's `backticked-red` and `slashed-red`). **No new instance found**, so AC4 has
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
> T2 — see the Design note above; the property is already pinned by case 39 from #10.

- [x] T1: audit every guard in `scripts/`, `assets/` and `hooks/` for normalisation applied before
      matching, and record the per-guard result in the section above — which normalise at all, and
      for each, on which side *(AC3, AC4)*
- [x] T2: write `G-9` in the dogfood rulebook, with its observable check and the `flat()` carve-out
      *(AC1, AC2)*
- [x] T3: confirm `check-locks.py` still reports six pinned files across both reviewer directories,
      that no `rules-lock.json` appeared under `.claude/agents/`, and that all nine validators pass
      *(AC5)*
