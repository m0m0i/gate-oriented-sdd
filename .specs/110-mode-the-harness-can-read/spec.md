# Spec: The installed document set, as a mode the harness reads
- Slug: 110-mode-the-harness-can-read   Issue: 110   Type: feature   Status: approved
- Author: m0m0i   Date: 2026-09-11

## 1. Requirements (WHAT / WHY)
- User story: As a developer installing this harness into a project, I want to choose between a minimum and a full document set and have that choice **recorded where the harness reads it**, so that a later check can tell a deliberate omission from a hole, and so that I can upgrade without anything having to guess my intent from which files happen to exist.
- Serves: **CAP-4** (installation into a repository that already has opinions) and **CAP-7** (a gate people leave switched on). `init` step 3 already makes this choice — "Scaffold the mandatory set; offer the rest" — and records nothing, so the harness cannot distinguish *"minimum, deliberately"* from *"full, half-abandoned"*. That is the exact distinction #22 needs before it can verify the document set at all, and the one #84 runs into when `init` installs a reference rulebook over a `CONTRACT.md` citing rules the project does not carry.
- The motivating case is **product lifecycle, not project size**. Before product-market fit the inception documents churn and pivots are normal; after it the PRD stabilises, epics become version goals and the backlog becomes feature sets, which is when the full set earns its cost.
- **Two modes, differing by exactly three skills.** Everything else is in both, `archive` included (#109).

  | Skill | `minimum` | `full` | Why it is the one that moves |
  | :-- | :-: | :-: | :-- |
  | `northstar` | — | yes | `init`'s step-2 interview already produces the `- Owns:` anchor by another route |
  | `epics` | — | yes | nothing consumes it mechanically yet (#22) |
  | `contract` | — | yes | evidence-triggered rather than scale-triggered — see AC7 |

- **Declared, then verified — not derived.** The mode is *almost* derivable from which files exist, and a line restating that would be a fact stated twice. But derivation cannot tell deliberate omission from abandonment, which is the whole point. So the line declares intent, a checker verifies the filesystem against it, and disagreement fails closed — the same shape as `rules-lock.json` against its rulebook, and as `- Validators:` being declared and then run.
- **Corrections to the issue's own arithmetic, carried in before they are encoded.** #110 was written before #109 landed and repeats the defect #109 removed: it states "minimum is 10 skills and 6 documents; full is 13 and 9". Both document counts are one too many — the three issue templates are counted once inside the total and again as the three. Verified against the merged README: **minimum is 10 skills, 5 documents and 3 issue templates; full is 13 skills, 8 documents and 3 issue templates.** The three the full set adds are `docs/NORTH_STAR.md`, `docs/EPICS.md` and `docs/CONTRACT.md`. This spec encodes the corrected numbers, and encoding the issue's would have made a machine-readable set whose first act was to assert a false count.
- Acceptance criteria:
  - [ ] **AC1:** WHEN `init` writes `.steering/tech.md` THE SYSTEM SHALL emit a `- Mode:` line on ONE physical line, in the same machine-read family as `- Validators:`, `- Reviewer:`, `- Source globs:` and `- Docs:`, readable by `gate_steering_value` with no change to that function.
  - [ ] **AC2:** WHEN the mode is `full` AND a document that mode requires is absent THE SYSTEM SHALL fail the check, naming the absent document.
  - [ ] **AC3:** WHEN the mode is `minimum` THE SYSTEM SHALL NOT report any of the three optional documents as missing.
  - [ ] **AC4:** WHEN the `- Mode:` line is absent, unreadable, or holds a value that is neither `minimum` nor `full` THE SYSTEM SHALL fail the check rather than assume a mode. Three outcomes, not two — a checker that reads "no mode" as "minimum" reports success having verified nothing, which is #16.
  - [ ] **AC5:** No file under `hooks/` branches on the mode. Mode-dependent blocking reaches the gates ONLY through the `- Validators:` line: `init` writes the document-set checker into it, and the checker reads the mode. This preserves `README.md`'s stated design that enforcement is a property of the project rather than of the hook — a gate that branches on mode is a switch that turns enforcement down.
  - [ ] **AC6:** A hook states only facts true under the project's mode. No mode-dependent fact exists in `hooks/steering-digest.sh` once `archive` is in both modes, so no reader is added now; this is a constraint on what may be added later, and the spec records it as such rather than as work.
  - [ ] **AC7:** `skills/spec/SKILL.md` step 1's "unplanned work entering through the side door" wording reads the mode, so it does not fire on every spec in a project that does not run `sprint` as a batch.
  - [ ] **AC8:** The documentation states `contract`'s trigger as **evidence** rather than scale — "when recurring review findings reveal an unwritten rule" — and says plainly that a `minimum`-mode project may run it at any point without changing mode.
  - [ ] **AC9:** WHEN `init` is re-run against a project already carrying a `- Mode:` line THE SYSTEM SHALL offer the upgrade rather than reinstalling, per its existing "diff and upgrade rather than reinstalling" rule.
  - [ ] **AC10:** Both READMEs state that **nothing about enforcement differs between the modes** — same gates, same reviewer, same receipt, same TDD loop. What differs is how much planning is written before the first spec.
  - [ ] **AC11:** `git diff --name-only main` contains **no path under `hooks/`**, and the 67 existing `scripts/test-gates.sh` cases pass unchanged. New cases are added only for the document-set checker. _Amended at `clarify`, ahead of any Design. The issue states this as "test-gates.sh gains no case and stays at 62 paths", which cannot hold once the checker lands here (the answer to the scope question): guards are tested in that suite — cases 52-55 are `check-templates` — so forbidding new cases would forbid testing the checker and contradict AC12. The intent was to pin **gate** behaviour, and that is what an untouched `hooks/` asserts directly rather than by proxy. 62 was also stale: #113 took the suite to 67._
  - [ ] **AC12:** The regression tests fail before the fix and pass after — specifically, the document-set checker is red on a tree whose `- Mode:` disagrees with its filesystem, and green when they agree, demonstrated in both directions for both modes.
  - [ ] **AC13:** THE SYSTEM SHALL carry a version bump in both manifests — `skills/` and `assets/` are shipped paths — performed as the step of `implement` after the receipt, not as a task (#113). **The size is `1.0.0`**, on the author's recorded word that a major is reserved for the minimum/full install switch, which this is. Flagged for confirmation at approval rather than assumed: `.steering/product.md` still says "not a supported product, pre-release", and #81-#84 are open, so a 1.0.0 may be premature even though the trigger has arrived.
- Out of scope: a third tier. Auto-detecting product-market fit, which is not observable to a harness — detect the symptom instead (`sprint` run with no `BACKLOG.md`), left to a follow-up. A separate `upgrade-sdd-mode` skill: this is `init`'s existing upgrade path, and it may be aliased for discoverability but must not become a fourteenth skill. Any change to gate behaviour, by AC5. Closing **#22** as a duplicate or reworking it, which is a tracker decision this spec does not take — see the open question.
- **Dependencies, stated rather than assumed.** The issue names **#81, #82, #83 and #84** — "all of this lands on `init`, and it should land on a healthy one" — and **all four are open**. #109 is closed as of today, which was the other precondition. This spec does not block on the four: it changes `init`'s *output* (a new line, a checker in `- Validators:`) rather than the defects those issues describe, and none of them touches the `- Mode:` line or the document-set check. Recorded as a known risk rather than a silent assumption — if any of the four changes `init`'s step 3 structurally, this spec's AC1 and AC9 land on a moved target.

### Clarifications

- 2026-09-11 — **Does the document-set checker land in this spec, or only the `- Mode:` line?** The issue's ACs demand a checker while its title asks only for a recorded mode. **Answered: the checker lands here.** A mode nothing verifies is a fact declared once and checked never, which is the failure this repository keeps hitting — and it is the whole distinction the line exists to make. Consequence, stated because it enlarges the spec: **#22** ("the mandatory document set is declared but never verified") is satisfied by this work and becomes a close rather than a dependency. Serving AC2, AC3, AC4, AC12.
- 2026-09-11 — **Does `minimum` mode run `contract`?** Deferred to `clarify` by the issue itself. **Answered: absent from minimum, runnable at any time without changing mode.** `contract`'s own step 1 asks for the last fifty commits and any review comments, and its red flags name "copying a style guide wholesale" — so run early it produces a *worse* rulebook rather than an absent one, and the reference rulebook already covers language-level correctness for the three supported stacks. The rejected alternative (a tiny starter contract in minimum) was argued from the reviewer being this product's core claim; it loses because a contract compiled from no evidence is the thing `contract` warns against. Serving AC8, and the three-skill difference in section 1.
- 2026-09-11 — **In `minimum` mode, how does an issue get created?** **Answered: ad-hoc creation from the backlog is the sanctioned path, stated as such.** `spec` step 1 currently calls it "unplanned work entering through the side door, bypassing the sprint", which in a project that never runs `sprint` as a batch fires on every single spec and trains the user to ignore the one rule the step exists to enforce. The rule survives — the issue is still created explicitly and out loud — and only the accusation is scoped to `full`. Serving AC7.
- Not asked, because the reasoning settles them: **mode value names** are `minimum`/`full`, matching the vocabulary both READMEs already use, because `velocity`/`stability` implies enforcement differs and AC10 exists to deny exactly that. **Whether a minimum-mode project has "earned" its contract** is left to its own issue, as the tracker item says.

## 2. Design (HOW)

**Approach: declare in `.steering/`, verify from `- Validators:`, and keep `hooks/` out of it entirely.**

`- Mode: minimum|full` joins the machine-read family in `.steering/tech.md`. `gate_steering_value` is a generic `sed -n "s/^ *- *$2: *//p" | head -1`, so it reads the new key with **no change to that function** — AC1 costs one line in `init`'s output, not a code change.

The checker is `assets/check-document-set.py`, copied by `init` into the project's `scripts/` and appended to its `- Validators:` line. That is the established shape for a check a project must own: `assets/check-steering-anchors.sh` and `assets/check-locks.py` both work exactly this way, and `init` already has the step that copies them. It is why mode-dependent blocking never reaches a hook — `quality-gate.sh` runs whatever `- Validators:` names and knows nothing about modes, which preserves the property that enforcement is the project's rather than the hook's.

**Three outcomes, not two.** Agree → 0. Disagree → non-zero naming the absent (or unexpected) document. Mode absent, unreadable, or not one of the two values → non-zero saying *that*. A checker that reads "no mode" as "minimum" reports success having verified nothing, which is #16 and is the defect this repository has now hit at four distinct layers. AC4 exists to make that a tested behaviour rather than an intention.

**Why declared rather than derived:** the mode is *almost* computable from which files exist, and a derived value would need no line at all. But derivation cannot distinguish "no `CONTRACT.md`, deliberately" from "no `CONTRACT.md`, abandoned halfway" — and that distinction is the entire feature. Declaration plus verification is the same shape as `rules-lock.json` against its rulebook.

**Affected files:**

| Path | Change |
| :-- | :-- |
| `assets/check-document-set.py` | **new** — reads `- Mode:`, verifies the document set, three outcomes |
| `skills/init/SKILL.md` | writes `- Mode:`, copies the checker, appends it to `- Validators:`; the re-run path offers an upgrade (AC9) |
| `skills/spec/SKILL.md` | step 1's side-door wording scoped to `full` (AC7) |
| `skills/contract/SKILL.md` | trigger stated as evidence, and that minimum may run it any time (AC8) |
| `README.md`, `README.ja.md` | the two modes, and that **nothing about enforcement differs** (AC10) |
| `.steering/tech.md` | this repo's own `- Mode: full`, and the checker on its `- Validators:` line — dogfooding, and the first thing that would catch a wrong checker |
| `scripts/test-gates.sh` | cases for the checker only; no gate case changes (AC11) |
| `plugin.json`, `.claude-plugin/plugin.json` | the version bump, as the step after the receipt |

**Risks and trade-offs:**

- **The four open `init` bugs (#81–#84).** This spec changes `init`'s *output*, not the defects they describe, and none of them touches the `- Mode:` line or the document-set check — so they are recorded as a risk rather than a blocker. If any of them restructures step 3, AC1 and AC9 land on a moved target and this spec needs re-reading, not rewriting.
- **This repo is `full`, so `minimum` gets no dogfooding here.** Every document the full set names exists in this repository, which means the `minimum` path is exercised only by the checker's own test cases. That is a real gap and the reason AC12 demands both directions for both modes explicitly, rather than trusting a green run.
- **One more file on every project's `- Validators:` line** is one more thing running on every turn. The checker reads one line and stats at most eight paths, so the cost is negligible — but the count of turn-end commands is itself a thing users switch off, and #54 is the standing argument about guard proliferation.

## 3. Tasks (TDD-ordered)
> One task is one complete Red-Green-Refactor cycle, so one green commit.

- [x] T1: cases for `assets/check-document-set.py` covering all three outcomes in both modes and both directions — red first — then the checker that makes them pass (AC2, AC3, AC4, AC12).
- [x] T2: cases for `init`'s contract — the `- Mode:` line written, the checker copied and appended to `- Validators:`, the re-run offering an upgrade — then the `skills/init/SKILL.md` changes (AC1, AC9).
- [ ] T3: `skills/spec/SKILL.md` step 1 scoped to `full`, and `skills/contract/SKILL.md`'s evidence trigger, each pinned by a `check-skill-contracts.py` entry (AC7, AC8).
- [ ] T4: both READMEs — the two modes and the equal-enforcement statement — and this repo's own `- Mode: full` plus the checker on its `- Validators:` line; assert AC10, AC11 and the full validator set green.
