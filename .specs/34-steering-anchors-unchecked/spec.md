# Spec: nothing checks that steering's machine-read anchors parse
- Slug: 34-steering-anchors-unchecked   Issue: 34   Type: bug   Status: done
- Author: m0m0i   Date: 2026-08-25

## 1. Requirements (WHAT / WHY)

- Reproduction: in this repository, at `main`:

  ```
  $ grep -n 'Owns' .steering/product.md
  6:- **Owns: gates never fail open.**

  $ sed -n 's/^ *- *Owns: *//p' .steering/product.md
                        # nothing
  ```

  `hooks/steering-digest.sh:19` reads it with exactly that sed. The `**` defeats the anchor.

- Expected: a machine-read steering line either resolves, or something says it does not.

- Actual: it fails silently, and the failure is invisible from both ends. The file looks *more*
  correct for the bolding — a human reads `- **Owns: ...**` as emphasis on the most important line
  in the document. The consumer reads nothing and carries on.

- Impact: the quality property is the anchor every reviewer severity is judged against —
  `northstar` calls it *"the question worth spending the most on"*, and `agents/_template/reviewer.md`
  interpolates it as `{{QUALITY_ANCHOR}}`. Every session start since #17 has emitted a digest one
  line short, and nobody noticed for a week.

  **The redundancy is what hid it.** `init` also writes the anchor verbatim into the project's
  reviewer file, so the reviewer had it from a second source while the digest silently lacked it. A
  project without that duplication gets a reviewer working from taste, which is the exact failure
  `northstar` exists to prevent.

  Current state of the five anchors in this repo:

  | Anchor | File | Read by | Parses |
  | :-- | :-- | :-- | :-- |
  | `Owns` | `product.md` | `steering-digest.sh` | **no** |
  | `Validators` | `tech.md` | `quality-gate.sh` | yes |
  | `Reviewer` | `tech.md` | `review-gate.sh` | yes |
  | `Source globs` | `tech.md` | `review-gate.sh`, `quality-gate.sh` | yes |
  | `Docs` | `tech.md` | skills only — no hook | yes |

- **Root cause:** two faults, and only the second is worth fixing.

  The local fault is one author bolding one line. The product fault is that **nothing validates
  that steering's machine-read lines parse.** `init` step 4 verifies the gates fire and the
  validators run; it never checks that the values those gates read are readable.
  `skills/init/SKILL.md` already warns that a wrapped value is silently truncated — so this class
  of failure is known, documented, and unchecked.

  It is the same shape as #1 (a quoted glob matching nothing), the `str.replace` no-op found in
  #9's review, and a `"Bash(gh pr merge:*"` permission rule missing its closing paren: **a value
  that looks right to a human and matches nothing.**

- Acceptance criteria:
  - [x] **AC1:** WHEN a steering anchor is present in a form its consumer cannot parse THE SYSTEM
        SHALL fail and name the anchor and the file.
  - [x] **AC2:** WHEN an optional anchor is absent entirely THE SYSTEM SHALL NOT fail. Absence and
        unparseability are different states and only the second is a defect.
  - [x] **AC3:** this repository's own `- Owns:` line SHALL parse.
  - [x] **AC4:** the check SHALL derive what it reads from the same expression its consumer uses,
        not a lookalike — a second definition that can disagree is #14 and #23 again.
  - [x] **AC5:** the regression test fails before the fix and passes after.
  - [x] **AC6:** the check SHALL be a shipped asset that `init` copies into a project and adds to
        its `- Validators:` line, so it runs in every project rather than only in this one.
  - [x] **AC7:** WHEN the check cannot locate the shared reader it SHALL fail, not skip. A guard
        that silently checks nothing is #16, and this one would be shipping into projects.

- Out of scope: the wrapped-value truncation `init` warns about (`sed ... | head -1` silently drops
  everything after the first newline). It is the same family and a strictly harder problem — a
  wrapped value *parses*, it is just incomplete — and folding it in would turn a small guard into a
  steering-file linter. Worth its own issue if this one lands well.

### Clarifications

- **Q: where does the check run?**
  A: a shipped asset in `assets/`, copied by `init` into the project and added to its
  `- Validators:` line — the same shape as `check-locks.py`. It then catches a broken anchor on
  the turn it is written, in every project, rather than protecting only this repository.
  A hook-side warning inside `steering-digest.sh` was rejected: the digest runs on `SessionStart`,
  which **Antigravity does not have**, so consumers on that harness would get nothing. Fixing this
  only in this repo's CI was rejected as fixing the instance rather than the class.
- **Q: which anchors are mandatory?**
  A: none. Fail only on **present-but-unparseable** — a line that loosely contains the key and a
  colon, where the consumer's own expression returns nothing. That is exactly the bolded-`Owns`
  case.

  **Corrected after review.** This first claimed it "cannot fire on a project that simply has no
  `Docs` line". It could: the loose match was unanchored, so `Docs *:` matched the word `docs:`
  inside this repo's own commit-convention paragraph. The match is now anchored to the start of a
  line modulo punctuation, and case 27 pins it — an absent anchor plus prose containing its key. Accepted weakness, recorded
  rather than hidden: a project that never wrote `- Owns:` at all still gets a reviewer working
  from taste, and this check will not say so. Making absence a failure is #22's unresolved
  question — what the opt-out is — arriving early and undecided.
- **Q: how does the check avoid becoming a second definition of how anchors are read?**
  A: extract the reader. `gate_steering_value <file> <key>` goes in `hooks/gate-lib.sh`, all five
  existing call sites use it, and the check sources the same library. One expression, six callers.
  The alternative — a documented copy — is knowingly adding a third instance of #14 and #23.

## 2. Design (HOW)

- Fix approach, and why this rather than the narrower or wider fix:
  **`gate_steering_value <file> <key>`** in `hooks/gate-lib.sh`, replacing five hand-copied `sed`
  expressions. That is the whole reason the check can be trusted: it does not restate how an anchor
  is read, it calls the same code the gates call.

  **`assets/check-steering-anchors.sh`** sources `gate-lib.sh`, walks a table of
  `(file, key)` pairs, and for each asks two questions:

  | loose match (`grep -i "key.*:"`) | `gate_steering_value` | verdict |
  | :-- | :-- | :-- |
  | no | empty | absent — silent, this is legitimate |
  | **yes** | **empty** | **present but unparseable — fail, naming anchor and file** |
  | yes | non-empty | fine |

  Shell rather than Python, unlike its neighbours in `assets/`, precisely so it can source
  `gate-lib.sh`. A Python check would have to re-implement the expression, which is the thing AC4
  forbids.

  *Narrower, rejected:* fix this repo's `Owns` line and stop. It repairs one instance of a class
  the repo has now hit four times.

  *Wider, rejected:* validating that values are *correct* rather than *parseable* — that
  `Validators` name real commands, that `Source globs` match files. That is a steering linter, and
  every rule in it is a new way to false-block.

- Affected files: `hooks/gate-lib.sh`, `hooks/review-gate.sh`, `hooks/quality-gate.sh`,
  `hooks/steering-digest.sh`, `assets/check-steering-anchors.sh` (new), `skills/init/SKILL.md`,
  `scripts/check-skill-contracts.py`, `scripts/test-gates.sh`, `.steering/product.md`,
  **`.steering/tech.md`** (Validators, the `Source globs` fix below, and a stale heading), and
  both manifests. `.steering/tech.md` was omitted from the first draft of this list.

- **Blast radius: this is the risky part and it is bigger than the fix.** Migrating five call sites
  touches **every gate at once** — the review gate, the quality gate, and the digest. All 34 gate
  cases must still pass, and T3 diffs the full case list against `origin/main` rather than trusting
  the totals.

  Two specific hazards:

  1. `review-gate.sh` suppresses sed stderr with `2>/dev/null`; `quality-gate.sh` does not. A
     shared reader normalises them. That is safe only because `quality-gate.sh` already returns
     early when `.steering/tech.md` is absent — verify that, do not assume it.
  2. **Locating `gate-lib.sh` is the same problem that produced #16.** It is `hooks/` here and
     `.claude/hooks/` in a project. The check must search both and **fail if it finds neither** —
     AC7. A guard that skips when it cannot find its own dependency is the bug this spec exists to
     prevent, shipped into every project.

- Why this cannot recur: the class is "a value that looks right and matches nothing", and this
  closes it for the five anchors by making the reader shared and the failure loud. It does not
  close the class generally — a wrapped value still truncates silently, which is Out of scope and
  named there.

## 3. Tasks (TDD-ordered)
> Folded red-and-green per #10: one task is one complete Red-Green-Refactor cycle.

- [x] T1: failing case — a fixture whose `- **Owns: …**` is bolded exactly as this repo's was makes
      the check fail naming the anchor and the file — then `gate_steering_value` and the check that
      uses it
- [x] T2: failing cases for the two states that must **not** fail — an absent optional anchor, and
      a correctly written one — then whatever narrowing makes them pass
- [x] T3: failing case — the check cannot locate `gate-lib.sh` and **fails rather than skipping**
      (AC7) — then the discovery that searches `hooks/` and `.claude/hooks/`
- [x] T4: migrate all five hook call sites to `gate_steering_value`, and diff the full case list
      against `origin/main` to confirm no pre-existing case changed verdict
- [x] T5: fix this repo's own `- Owns:` line, and confirm the digest now emits the quality property
      it has been silently omitting since #17
- [x] T6: `init` copies the check and adds it to the project's `- Validators:` line, pinned by
      `check-skill-contracts.py`. **Presence assertion, not adherence** — the same limit as #9's AC3
- [x] T7: refactor
