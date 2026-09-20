# Spec: The reviewer's allow-list and the Validators line
- Slug: 131-reviewer-allow-list-drifts-from-the-validators-line   Issue: 131   Type: bug   Status: approved
- Author: m0m0i, Antigravity   Date: 2026-09-20

## 1. Requirements (WHAT / WHY)

- Reproduction: compare `.steering/tech.md`'s `- Validators:` line (twelve entries) against
  `.claude/agents/gate-sdd-reviewer.md`'s `## Bash policy` allow-list (nine, plus the CI-only
  `check-version-bump.py`). Three are absent: `./assets/check-document-set.py` (added by #110),
  `./scripts/check-contract-path.py` (#82), `./scripts/check-readme-claims.py` (#115).
- Expected: `agents/_shared/reviewer-contract.md:18` sanctions "running the project's own
  validators, **as named in `.steering/tech.md`**". The allow-list is meant to *be* that line, so a
  validator on the line is a validator the reviewer may run.
- Actual: the reviewer does the correct thing with an off-list command — it declines and records the
  result as *unknown rather than as agreeing* — so a branch's validator claims stop being
  independently verifiable, silently. Observed on #126: the record claimed eleven green, the
  reviewer could confirm nine.

  A second instance, found while clarifying: the dogfood reviewer carries **no category-3 line at
  all**. `agents/_shared/reviewer-contract.md:19` sanctions "checking an installed version before
  claiming an API is wrong"; the other four reviewers each show it, and this one shows nothing.
  #118 was filed believing "all five files currently list all four categories" and therefore that
  it was closing a class with no instance. It has one.
- Impact: every review on this repository since #110. It widens by one each time a spec adds a
  validator — two when #131 was filed, three today — and the direction of failure is the one
  `.steering/product.md` calls a BLOCKER shape: a gate that *silently stops checking*. Nothing
  fires, and the receipt still reads CLEAN.
- **Root cause:** the four shipped reviewers delegate — `agents/ts-reviewer.md:…` and its two
  siblings say *"the validators named in `.steering/tech.md`"* and hold no copy. The dogfood
  reviewer alone **enumerates** the line by hand, and `agents/_template/reviewer.md` teaches that
  shape via `{{VALIDATOR_LIST}}`, so `init` generates an enumerated copy into every new project.
  A hand-maintained copy of a machine-read line drifts the moment the line moves, and no guard
  compares them — `check-receipt-schema.py` pairs receipt *fields* with commands (#105) and stops
  there. This is C-2's class and #14's class: a definition with two homes, where the copy fails
  open.
- Acceptance criteria:
  - [ ] **AC1:** WHEN `.steering/tech.md`'s `- Validators:` line names a validator absent from
        `.claude/agents/gate-sdd-reviewer.md`'s Bash policy THE SYSTEM SHALL fail and name both the
        absent validator and the file.
  - [ ] **AC2:** WHEN the reviewer is asked to run any validator on the `- Validators:` line THE
        SYSTEM SHALL sanction it, for all twelve current entries.
  - [ ] **AC3:** WHEN a reviewer file shows neither evidence of one of the four categories
        `reviewer-contract.md`'s Bash policy sanctions nor a declared N/A for it THE SYSTEM SHALL
        fail and name the file and the category. The corpus is the five files
        `check-receipt-schema.py` already pins as `REVIEWERS`. *(#118)*
  - [ ] **AC4:** WHEN a category is inapplicable to a project THE SYSTEM SHALL accept a declared
        N/A that states its reason, and SHALL reject a bare or unreasoned one. The dogfood
        reviewer declares category 3 N/A because `.steering/tech.md` records that this project has
        no package manager, no build, and no dependency file.
  - [ ] **AC5:** AC3 SHALL match each category across the spellings the shipped reviewers already
        use — `agents/ts-reviewer.md` and `agents/python-reviewer.md` spell category 3 "the package
        manager's list command", `agents/dart-flutter-reviewer.md` "the SDK version command" — so
        the check reads the category, not one stack's wording.
  - [ ] **AC6:** no reviewer's allow-list gains a command it does not have today. The check proves a
        reviewer *shows* what the contract already permits; it is not a route to granting.
        *(#118's "What must NOT change")*
  - [ ] **AC7:** `./scripts/check-version-bump.py` remains sanctioned for the dogfood reviewer while
        remaining off the `- Validators:` line, per `.steering/tech.md`'s stated reason.
  - [ ] **AC8:** the new guard is itself named on `.steering/tech.md`'s `- Validators:` line and on
        the dogfood reviewer's allow-list, and therefore passes its own AC1.
  - [ ] **AC9:** the regression fails before the fix and passes after, and the control case runs
        first. Every new branch survives `python3 -O` (#28).
  - [ ] **AC10:** `plugin.json` and `.claude-plugin/plugin.json` SHALL be incremented in lockstep by a
        patch version (`0.14.0` -> `0.14.1`), and verified by `scripts/check-manifests.py` and
        `scripts/check-version-bump.py main`.
  - [ ] **AC11:** `README.md` and `README.ja.md` SHALL be updated in lockstep to describe the
        reviewer's bounded Bash policy allow-list and drift prevention, passing
        `scripts/check-readme-claims.py` and `scripts/check-markdown-fences.py`.
- Out of scope:
  - **#137** — widening `check-readme-claims.py`'s corpus. Adjacent (both are a guard whose reach
    is narrower than its rule) and separately filed.
  - **#116** — `docs/CONTRACT.md`'s rule ids addressed but unchecked. Same family, own issue.
  - Whether `init` should append to a generated allow-list when it appends to `- Validators:`
    (#131's third design question). It touches no reviewer today; changing that is `init` behaviour
    and a second spec.

### Clarifications

**2026-09-14**

1. **Q: The dogfood reviewer enumerates the Validators line; the three shipped reviewers point at it
   instead. Is the fix a guard, or a deletion?**
   A: **Enumerate and guard it** — AC1. A delegating allow-list is *self-widening*: whatever lands
   on the `- Validators:` line is sanctioned with no second pair of eyes, which is the mechanism
   AC6 exists to forbid and the direction `.steering/product.md` calls the owned failure. The two
   shapes fail in opposite directions, and the choice is which failure the project prefers:
   enumeration fails **closed** — the reviewer verifies less than it should, silently, which is
   this bug — and delegation fails **open**. Enumeration is the lesser, and the guard removes its
   only drawback.

   Rejected: *delete the copy*. It is the remedy `scripts/check-readme-claims.py`'s docstring argues
   for — make the claim unnecessary rather than checkable — and the argument does not reach here.
   That reasoning applies to a **claim**, which costs nothing to drop. An allow-list is a
   **permission**, where the delegated form grants more than the enumerated one.

   Not in question: the three shipped reviewers keep delegating. They ship into projects that have
   no `.steering/tech.md` yet, so they have nothing to enumerate at install time. Their shape is
   forced, not chosen, and AC5 exists because of it.

2. **Q: Where does the check live — a new validator, or an extension of `check-receipt-schema.py`?**
   A: **A new `scripts/check-reviewer-allow-list.py`** — AC8. #118 suggested the extension, and
   `check-receipt-schema.py` already owns the `REVIEWERS` corpus, so it is the least new code. It
   is also #117's exact shape: that issue is open *because* `check-templates.py` grew a second
   subject with a different lifetime, and repeating it in the same week it was filed would be
   adding a known defect knowingly. The receipt schema and the Bash policy are two subjects; the
   first is about what a reviewer must *produce*, the second about what it may *run*.

   The recursion is deliberate rather than incidental: a new validator must be added to the
   `- Validators:` line **and** to the dogfood allow-list, so it fails its own AC1 until it is
   wired into both. The guard's first subject is itself.

3. **Q: The dogfood reviewer has no category-3 line. `.steering/tech.md` says this project has no
   package manager and no build. What should the category check do about it?**
   A: **A declared N/A that states its reason** — AC4. The category is genuinely inapplicable; the
   fix is for the file to say so rather than to stay silent, because silence is indistinguishable
   from the drift AC3 is looking for.

   Rejected: *grant it a version-check line*, which would make the check a route to granting a
   command — AC6 — and grant one this project has no use for. Also rejected: *drop category 3*,
   which retires the question instead of answering it; #105 is the incident where an unasked
   question of exactly this shape cost a week.

   The N/A is an opt-out, and opt-outs fail open, so AC4 requires a reason and rejects a bare one.
   That is the narrowest form that still lets an honest project pass.

**2026-09-20**

4. **Q: Should this change increment the patch version and update the README?**
   A: **Yes** — AC10 and AC11. Per user instruction, bump the patch version from `0.14.0` to `0.14.1`
   in lockstep across `plugin.json` and `.claude-plugin/plugin.json`, and update `README.md` and
   `README.ja.md` in lockstep to document that the reviewer's Bash policy allow-list is bounded by
   `- Validators:` and protected from silent drift.

## 2. Design (HOW)

### Fix approach, and why this rather than the narrower or wider fix

A new `scripts/check-reviewer-allow-list.py`, whose subject is the **`## Bash policy` block** of a
reviewer file. It enforces two rules over that one block:

- **Coverage** (AC1, AC2, AC7) — every validator on `.steering/tech.md`'s `- Validators:` line
  appears in the dogfood reviewer's enumerated list. Containment, not equality; see the limit below.
- **Categories** (AC3, AC4, AC5) — each of the four categories
  `agents/_shared/reviewer-contract.md`'s Bash policy sanctions is either shown or declared N/A with
  a reason, across all five files in `check-receipt-schema.py`'s `REVIEWERS`.

*Narrower* would be correcting the three absent validators and leaving the comparison to review.
That is how the drift started: #110 and #82 each passed a review that did not make the comparison,
because nothing asked anyone to.

*Wider* would be granting the dogfood reviewer a category-3 command, or converting the shipped
reviewers to enumerate. Both are ruled out in the Clarifications.

**Why two rules share one guard, having just used #117 to refuse extending `check-receipt-schema.py`.**
The line is the *subject*, not the file. Both rules read one section — the Bash policy — and both
change when it changes, so they share a lifetime. `check-receipt-schema.py`'s subject is the
**Receipt** block: what a reviewer must *produce*, not what it may *run*. `scripts/check-contract-path.py`
already set this precedent verbatim, and its docstring gives the same reason.

### The limit, stated rather than discovered

Coverage is **containment**, so the guard catches the allow-list falling *behind* the line and not
the allow-list running *ahead* of it. Equality is unavailable: the dogfood list legitimately carries
`git`, `date`, `claude plugin validate . --strict` and — per AC7 — `check-version-bump.py`, which
`.steering/tech.md` keeps off the line for a stated reason.

This is the honest asymmetry: erosion is an **absence in one file caused by an edit to another**,
invisible in the diff that causes it, and that is the direction now guarded. Widening is an
**addition, in the diff, in the file being reviewed** — the shape review actually catches. The guard
covers the half review cannot see.

### Affected files

| File | Change |
| :-- | :-- |
| `scripts/check-reviewer-allow-list.py` | New. Both rules. |
| `scripts/test-gates.sh` | New cases: control first, then one per failure mode, plus the `python3 -O` branch. |
| `.claude/agents/gate-sdd-reviewer.md` | The three absent validators added; category 3 declared N/A with its reason; the new guard added (AC8). |
| `.steering/tech.md` | The new guard on the `- Validators:` line (AC8). |
| `.github/workflows/ci.yml` | The new guard as a CI step. |
| `plugin.json` | Patch version bump (`0.14.0` -> `0.14.1`) (AC10). |
| `.claude-plugin/plugin.json` | Patch version bump in lockstep (AC10). |
| `README.md` | Document reviewer allow-list bounded policy and drift guard (AC11). |
| `README.ja.md` | Mirror README changes in Japanese in lockstep (AC11). |

**Shipped file changes & version bump:** `plugin.json` and `.claude-plugin/plugin.json` are bumped (`0.14.0` -> `0.14.1`), which `check-version-bump.py` validates against `main` (AC10).

### Blast radius

- **`hooks/quality-gate.sh` runs the Validators line dynamically** (`gate_steering_value ... Validators`),
  so the moment AC8 lands the new guard runs at every turn end. If it is red then, it blocks the
  branch that is adding it — #81's shape, *"init arms the gate red with its own file"*. This
  constrains task order rather than the design: the allow-list is correct **before** the guard
  reaches the line, and the two edits that make AC8 true are one atomic task.
- **`check-receipt-schema.py` is untouched.** It keeps `REVIEWERS`; the new guard imports nothing
  and re-declares its own corpus, because a cross-script import would couple two lifetimes that the
  #117 argument above says to keep apart.
- **The three shipped reviewers and `_template/reviewer.md` are read, not written.** AC6 is
  satisfied by construction: no allow-list gains a command.

### Why this cannot recur

The guard is on the `- Validators:` line it polices, so it runs at every turn end and in CI, and it
fails until it is itself on the allow-list (AC8). The next validator added to that line reddens the
gate for the branch that adds it, in that branch's own turn — the one moment someone is positioned
to fix it. The class closes because the guard's first subject is itself.

## 3. Tasks (TDD-ordered)

> One task is one complete Red-Green-Refactor cycle, so one green commit.

- [ ] **T1:** Coverage rule — cases for AC1, AC2, AC7 (control first, then a validator absent from
      the allow-list, then the sanctioned extra proving containment rather than equality), failing
      for the right reason; then `scripts/check-reviewer-allow-list.py` implementing it, and the
      three absent validators added to the dogfood allow-list.
- [ ] **T2:** Category rule — cases for AC3, AC4, AC5 (a dropped category fails and is named; each
      of the three category-3 spellings passes; a bare N/A fails and a reasoned one passes); then
      the rule, and the dogfood reviewer's category-3 N/A declaration with its reason.
- [ ] **T3:** AC8 — the guard onto `.steering/tech.md`'s `- Validators:` line, onto the dogfood
      allow-list, and into `.github/workflows/ci.yml`. One task because the first edit reddens the
      turn-end gate until the second lands.
- [ ] **T4:** Verification, README updates, and patch version bump (AC9, AC10, AC11) — extend the
      `python3 -O` case to both new branches (#28), confirm AC6 by diffing every reviewer's Bash
      policy for added commands, update `README.md` and `README.ja.md` in lockstep, and bump
      `plugin.json` and `.claude-plugin/plugin.json` patch version (`0.14.0` -> `0.14.1`).
