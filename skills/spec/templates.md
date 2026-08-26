# Spec templates by issue type

Read only the one matching the issue's type. A bug pushed through feature-shaped
scaffolding produces acceptance criteria that are fiction, because there is no
user story — there is a thing that is broken.

All three share the same front matter and the same TDD-ordered Tasks section.
What differs is section 1, which is where the type actually matters.

**One task is one complete Red-Green-Refactor cycle**, so a task ends green and is one
commit. The red and green halves are deliberately not separate tasks: `quality-gate.sh` runs
the project's validators on turn end, so a task that is only the red half cannot be committed
without ending the turn red. `scripts/check-templates.py` fails if that split returns. See #10.

---

## Feature

```markdown
# Spec: <title>
- Slug: <slug>   Issue: <n>   Type: feature   Status: draft
- Author: <you>   Date: <YYYY-MM-DD>

## 1. Requirements (WHAT / WHY)
- User story: As a <role>, I want <goal>, so that <benefit>.
- Serves: <the lever or capability this moves>
- Acceptance criteria:
  - [ ] **AC1:** WHEN <event> THE SYSTEM SHALL <observable behavior>.
- Out of scope: ...

### Clarifications
<from `clarify`, or "None needed">

## 2. Design (HOW)
- Approach and key decisions:
- Affected modules and files, per .steering/structure.md:
- Contract changes, and who else consumes them:
- Risks and trade-offs:

## 3. Tasks (TDD-ordered)
> One task is one complete Red-Green-Refactor cycle, so one green commit.
- [ ] T1: failing test for <behavior> — then the implementation that makes it pass
- [ ] T2: refactor ...
```

---

## Bug

The first task is always a test that reproduces the bug. If you cannot write
that test, you do not yet understand the bug well enough to fix it — and a fix
without it will be reverted by the next person who touches the file.

```markdown
# Spec: <title>
- Slug: <slug>   Issue: <n>   Type: bug   Status: draft
- Author: <you>   Date: <YYYY-MM-DD>

## 1. Requirements (WHAT / WHY)
- Reproduction: <the shortest sequence that shows it>
- Expected: <what should happen, and what says so>
- Actual: <what happens instead>
- Impact: <who hits this, how often, what it costs — this is what justified the priority>
- **Root cause:** <the actual mechanism, once found. Not "a null check was missing"
  but why the value was null on a path nobody expected.>
- Acceptance criteria:
  - [ ] **AC1:** WHEN <the reproduction> THE SYSTEM SHALL <the correct behavior>.
  - [ ] **AC2:** the regression test fails before the fix and passes after.
- Out of scope: <adjacent bugs found while investigating — file them, do not fix them here>

### Clarifications
<from `clarify`, or "None needed">

## 2. Design (HOW)
- Fix approach, and why this rather than the narrower or wider fix:
- Affected files:
- **Blast radius:** <what else uses this code path and could change behavior>
- Why this cannot recur: <the guard, type, or test that makes the class of bug
  impossible rather than just this instance fixed>

## 3. Tasks (TDD-ordered)
> One task is one complete Red-Green-Refactor cycle, so one green commit.
- [ ] T1: regression test that fails for the right reason — then the fix for the root cause
- [ ] T2: check the blast radius — tests for the other callers
- [ ] T3: refactor
```

---

## Chore

The controlling line is **what must not change.** A chore is defined by its
invariant; without one stated, a refactor and a rewrite are the same diff and
the reviewer has no way to tell them apart.

```markdown
# Spec: <title>
- Slug: <slug>   Issue: <n>   Type: chore   Status: draft
- Author: <you>   Date: <YYYY-MM-DD>

## 1. Requirements (WHAT / WHY)
- What changes: <the mechanical description>
- **What must NOT change:** <the observable behavior this work preserves>
- Why now: <what it unblocks, or the cost of deferring>
- Acceptance criteria:
  - [ ] **AC1:** THE SYSTEM SHALL behave identically for <the preserved behavior>,
    demonstrated by <the tests that already cover it>.
  - [ ] **AC2:** <the mechanical outcome — the dependency is on version X, the
    module no longer imports Y>.
- Out of scope: <the tempting adjacent cleanup>

### Clarifications
<from `clarify`, or "None needed">

## 2. Design (HOW)
- Approach, and the order of operations if it must land in steps:
- Affected files:
- **Coverage gap:** <behavior that must be preserved but has no test today.
  Those tests are written FIRST, before the change — otherwise "nothing broke"
  is an assertion, not an observation.>
- Rollback: <how to undo this>

## 3. Tasks (TDD-ordered)
- [ ] T1: add tests covering the behavior that must be preserved but is untested
- [ ] T2: confirm they pass BEFORE the change — this is the baseline
- [ ] T3: make the change
- [ ] T4: confirm the same tests still pass
- [ ] T5: refactor
```
