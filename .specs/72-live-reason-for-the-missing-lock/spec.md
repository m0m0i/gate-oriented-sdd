# Spec: Give the live reason the dogfood reviewer has no lock, and name the hook files that exist

- Slug: 72-live-reason-for-the-missing-lock Issue: 72 Type: chore Status: approved
- Author: m0m0i Date: 2026-09-05

## 1. Requirements (WHAT / WHY)

- What changes: the two paragraphs that explain why `.claude/agents/gate-sdd-reviewer/` has no `rules-lock.json` — `.claude/agents/gate-sdd-reviewer.md:43` and `AGENTS.md:71` — give the reason that is true now: `check-locks.py --update` cannot create a lock (#19), #16 is closed and the guard discovers both directories, and ADR-6 records the deviation. `AGENTS.md:23`'s Hooks row names the two template files that exist instead of two that do not.

- **What must NOT change:**
  - The decision itself: the rulebook stays unpinned until #19 ships a bootstrap; nothing here creates a lock.
  - Every other line of both files; `.steering/` untouched; every `- Validators:` command at exit 0.
  - No shipped path: `.claude/` and `AGENTS.md` are not shipped, so no version bump, and `check-version-bump.py` says so.

- Why now: #56's reread found both paragraphs citing a closed issue as a live reason, and its reviewer found the hook paths; sprint put this in the iteration (row 2, milestone 1). A reader who follows the stated reason today finds it false in one command.

- Acceptance criteria:
  - [ ] **AC1:** `grep -n "That is #16" .claude/agents/gate-sdd-reviewer.md AGENTS.md` returns nothing; both paragraphs name #19 as the reason, say #16 is closed, and point at ADR-6.
  - [ ] **AC2:** `AGENTS.md`'s Hooks row names `hooks/templates/claude-code.settings.json` and `hooks/templates/antigravity.hooks.json`, the files `check-manifests.py` reads; `grep -c "hooks/hooks.json" AGENTS.md` is 0.
  - [ ] **AC3:** `git diff --name-only main` is confined to the two files and this directory; validators at exit 0 after the last write; `check-version-bump.py` reports no shipped file changed.

- Out of scope: creating the lock (#19); `docs/layout.md`'s placement of the reviewer contract (#82).

### Clarifications

None needed — requirements were unambiguous.

## 2. Design (HOW)

- **Approach.** T1 records the greps red; T2 rewrites three lines and re-runs them.
- **Affected files.** `.claude/agents/gate-sdd-reviewer.md`, `AGENTS.md`, this directory.
- **Coverage gap.** None; the greps are the test.
- **Rollback.** `git revert`.

## 3. Tasks (TDD-ordered)

> One task is one complete Red-Green-Refactor cycle, so one green commit.

- [ ] T1: record the greps red.
- [ ] T2: rewrite; assert AC1–AC3 with the validators run last.
