# Spec: One path for the reviewer contract
- Slug: 82-one-path-for-the-reviewer-contract   Issue: 82   Type: bug   Status: approved
- Author: m0m0i   Date: 2026-09-12

## 1. Requirements (WHAT / WHY)
- Reproduction: install this harness into a project, take the reviewer from the closest reference implementation, and read its first instruction. `agents/python-reviewer.md:10` — and both siblings — says **"Read `agents/_shared/reviewer-contract.md` first."** In an installed project that path does not exist: `agents/` is the *plugin's* directory, and the install has `.claude/agents/` (Claude Code) or `.agents/` (Antigravity).
- Expected: one placement, named identically by the shipped reviewers, the template, `init`, and `docs/layout.md`, so an installed reviewer's first instruction resolves.
- Actual: **four distinct forms across shipped files, plus one non-form** — the issue says three, and enumerating them is the first task.

  | Where | What it says | Resolves in an install? |
  | :-- | :-- | :-- |
  | `agents/{ts,python,dart-flutter}-reviewer.md:10` | `agents/_shared/reviewer-contract.md` | **no** — plugin-relative |
  | `agents/_template/reviewer.md` | `_shared/reviewer-contract.md` | **yes** — reviewer-relative |
  | `docs/layout.md:43` | `.claude/agents/reviewer-contract.md` | flat, no `_shared/` |
  | `scripts/check-receipt-schema.py:34,128` | `.claude/agents/_shared/reviewer-contract.md` | matches the dogfood |
  | `skills/init/SKILL.md:60` | "copy `_shared/reviewer-contract.md` **next to it**" | names no path at all |

  This repository's own install is `.claude/agents/_shared/reviewer-contract.md`, so the schema guard and the dogfood agree with each other and with nothing else.
- Impact: **the reviewer stops.** `agents/_shared/reviewer-contract.md:5` instructs a reviewer that cannot find the contract to "say so and stop — reviewing without a shared severity scale" is worse than not reviewing. So a consumer who copies a shipped reviewer without hand-editing that line gets a reviewer that declines to review. That falsifies **CAP-1, "review that cannot be declined"**, at install time and silently — the failure is indistinguishable from a careful reviewer being careful. Observed 2026-09-05 on #76 against a scratch clone of a real consumer (`.specs/_archive/76-run-init-on-a-scratch-clone/observations.md:58`), where the run fixed it by hand and recorded that it had.
- **Root cause:** the shipped reviewer names its sibling by a path relative to the **plugin root**, and `init` copies that file into a **project root** where no such directory exists. Nothing rewrites the line at copy time, and nothing checks it afterwards. The template escaped the bug by naming the contract relative to the reviewer itself — not by design, as far as the record shows, but that is the form that works. The three reference reviewers are the ones consumers actually copy.
- **Two corrections to the issue, verified before encoding them:**
  - **No lock re-pin is needed.** The issue says the fix requires "a re-pin of any lock that hashes the reviewer files". The locks do not hash the reviewer files: `agents/*/rules-lock.json` carries `derived: [types-and-style, correctness-and-tests]`, and `check-locks.py` reports **6 pinned files** — three reviewers × two rulebooks. Editing `agents/ts-reviewer.md:10` changes nothing any lock covers.
  - **The proposed placement hardcodes one harness.** The issue says *"Pick one: `.claude/agents/_shared/reviewer-contract.md`"*. That is Claude Code's directory. Antigravity installs to `.agents/` (`docs/layout.md:49`), and `docs/fidelity.md:8` records the subagent contract as *"partial — invocation contract differs, untested"*. A single absolute path written into a file that ships to both harnesses is wrong for one of them by construction. Resolving this is the clarification this spec must settle before any Design.
- Acceptance criteria:
  - [ ] **AC1:** WHEN a reviewer shipped in `agents/` is copied into an installed project THE SYSTEM SHALL name the reviewer contract by a path that resolves there, under both harness layouts.
  - [ ] **AC2:** The three reference reviewers, `agents/_template/reviewer.md`, `skills/init/SKILL.md`, `docs/layout.md` and `scripts/check-receipt-schema.py` all state the same placement; `init` names the exact path rather than "next to it".
  - [ ] **AC3:** WHEN any of those files states a different placement from the others THE SYSTEM SHALL fail a validator naming the disagreeing file. The defect is that one fact is written in five places and nothing compares them — a fix that leaves the comparison to review re-opens it on the next edit.
  - [ ] **AC4:** WHEN a reviewer's stated contract path does not exist THE SYSTEM SHALL still behave as `agents/_shared/reviewer-contract.md:5` prescribes — say so and stop. This is not relaxed; AC1 removes the cause rather than the symptom.
  - [ ] **AC5:** `.claude/agents/` — this repository's own install — continues to resolve, and `scripts/check-receipt-schema.py`'s mirror pairing keeps working against whatever placement is chosen.
  - [ ] **AC6:** the regression tests fail before the fix and pass after, in both directions: a reviewer whose path resolves, and one whose path does not.
  - [ ] **AC7:** THE SYSTEM SHALL carry a version bump in both manifests — `agents/` and `skills/` are shipped paths — as the step of `implement` after the receipt, not as a task (#113). **The size is the open question this branch finally answers:** `1.0.0` has been reserved for the minimum/full switch *and* a settled installed interface, and this issue is the second condition. Proposed in Clarifications, not assumed here.
- Out of scope: #81, #83, #84 — the other three open `init` defects, each its own issue. Whether Antigravity's subagent invocation contract works at all, which `docs/fidelity.md` records as untested and which this spec does not resolve. The `_template` reviewer's own correctness beyond this one line. Any change to what the contract *says*, as opposed to where it lives.

### Clarifications

- 2026-09-12 — **Absolute or relative?** The issue says *"Pick one: `.claude/agents/_shared/reviewer-contract.md`"*, which is Claude Code's directory, while these reviewers ship to Antigravity too (`.agents/`, `docs/layout.md:49`). **Answered: relative to the reviewer — `_shared/reviewer-contract.md`.** One string is then correct under both layouts, and `agents/_template/reviewer.md` already says exactly that, making it the only file in the repository that is right today. The issue's own proposal is therefore **overruled**, and the reason is recorded rather than left to a reader to rediscover: an absolute path in a file that ships to two harnesses is wrong for one of them by construction, and `docs/fidelity.md:8` already calls that contract "partial — untested" rather than broken. Documents still draw the concrete tree, because a diagram cannot draw a relative path. Rejected: dropping `_shared/` for a flat sibling, which matches what `docs/layout.md` draws today but would move this repository's own file and rewrite `check-receipt-schema.py`'s mirror pairs for no gain. Serving AC1, AC2.
- 2026-09-12 — **Build the comparison, or fix the five and stop?** **Answered: build it.** The defect *is* one fact written in five places with nothing comparing them, and a fix that leaves the comparison to review re-opens on the next edit — which is how it reached five. Review did not catch this the first time: the drift was invisible for months and surfaced only when `init` was run against a real project (#76). #54's standing argument against growing the guard count is acknowledged and loses here, on the same reasoning #110 used for the document set. Serving AC3.
- 2026-09-12 — **Does `1.0.0` ship on this branch?** `1.0.0` has been reserved for the minimum/full switch **and** a settled installed interface; #110 delivered the first and this delivers the second. **Answered: decide after the review, not now** — the bump is the post-receipt step regardless, and whether the interface is genuinely settled is better judged against the finished diff than predicted against an unwritten one. AC7 is written to record the question rather than pre-empt it. Serving AC7.
- Not asked, because the repository answers it: whether a lock re-pin is needed (no — the locks hash `rules/*.md`, not the reviewer files), and whether `agents/_shared/reviewer-contract.md` itself moves (it does not; only the sentences naming it change).

## 2. Design (HOW)

**Fix approach: make the three reference reviewers say what the template already says, then make everything else agree, then compare them mechanically.**

The contract file does not move. `agents/_shared/reviewer-contract.md` stays where it is in the plugin, and an install keeps it at `<agents dir>/_shared/reviewer-contract.md`. What changes is the **sentence** in the files that name it — from a plugin-relative path that cannot resolve in a project, to a reviewer-relative one that resolves in both.

Why not the narrower fix — editing only the three reviewers: `init` would still say "next to it", `docs/layout.md` would still draw the flat form, and the next person to install would still have three answers to one question. Why not the wider one — moving the contract or dropping `_shared/`: that relocates this repository's own file and rewrites the schema guard's mirror pairs, and the clarification settled against it.

**Affected files:**

| Path | Change |
| :-- | :-- |
| `agents/{ts,python,dart-flutter}-reviewer.md:10` | `agents/_shared/…` → `_shared/reviewer-contract.md` |
| `agents/_template/reviewer.md` | unchanged — it is already correct, and the case pins that |
| `skills/init/SKILL.md:60` | names the exact relative path instead of "next to it", and the concrete tree it lands in |
| `docs/layout.md:43` | draws `_shared/reviewer-contract.md`, not the flat sibling |
| `scripts/check-contract-path.py` | **new** — compares every statement of the placement |
| `.steering/tech.md`, `.github/workflows/ci.yml` | the new guard on the `- Validators:` line and in CI |

**Blast radius:** `scripts/check-receipt-schema.py` reads `.claude/agents/_shared/reviewer-contract.md` as the dogfood mirror of `agents/_shared/reviewer-contract.md`; neither file moves, so its pairing is untouched — asserted in T3 rather than assumed. `assets/check-locks.py` hashes `rules/*.md` only, so no lock re-pins. No hook reads any of this. The three reviewers are shipped paths, so a version bump is owed.

**Why this cannot recur — and why a guard rather than review.** The new check is in `scripts/` because it verifies the **plugin's internal agreement**, not an installed project's state, and it is a **new file rather than an extension of `check-receipt-schema.py`**: that guard already has one subject, and #117 records what happens when a guard acquires a second with a different lifetime. It reads the placement from each of the five statements and fails naming any that differs, with the third outcome this repository now insists on — a statement it cannot find or read is neither agreement nor disagreement, and must fail rather than compare four of five and report success.

## 3. Tasks (TDD-ordered)
> One task is one complete Red-Green-Refactor cycle, so one green commit.

- [x] T1: a case that fails because a shipped reviewer, copied into an installed agents directory, names a contract path that does not resolve there — and passes for `_template`, which already resolves — then the three reference reviewers (AC1, AC4, AC6).
- [x] T2: cases for `scripts/check-contract-path.py` covering agreement, each single disagreement, and an unreadable statement — then the guard, then `skills/init/SKILL.md` and `docs/layout.md` brought into agreement, which is what turns it green (AC2, AC3).
- [x] T3: the guard onto `- Validators:` and into CI; assert the blast radius — `check-receipt-schema.py`'s mirror pairing still passes, this repository's own `.claude/agents/` still resolves, and the full validator set is green (AC5).
