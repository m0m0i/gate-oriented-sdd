# Spec: Enforce the document cascade with a reconciliation line and a guard

- Slug: 166-document-cascade-reconciliation   Issue: 166   Type: feature   Status: done
- Author: Hiroyuki Momoi   Date: 2026-10-12

## 1. Requirements (WHAT / WHY)

- User story: As a developer, maintainer, or planner using the SDD harness, I want downstream inception documents (`DESIGN.md`, `BACKLOG.md`, `ROADMAP.md`, `CONTRACT.md`) to carry a declared `- Reconciled against PRD: <sha>` line and an automated turn-end validator to enforce that each document has been reconciled against the latest commit modifying `PRD.md`, so that changes to requirements cannot silently orphan downstream architecture, roadmap, or backlog plans without someone explicitly verifying and re-stamping the cascade.
- Serves: **CAP-6** (LV-4) — Planning that terminates in something the harness reads. Sits at the mechanical terminus of the planning chain (`prd` -> `design-doc` / `roadmap` / `backlog` / `contract`), unblocked by #164 and #165.
- Why the current design fails:
  1. The document set defines a stated cascade (`PRD.md` changes, and design, roadmap, backlog, and contract follow), but nothing mechanically verifies or enforces it.
  2. In this repository's own history (between the fourth and fifth refinements), twenty-four issues closed and eighteen were filed while `docs/BACKLOG.md` never moved, and the fifth refinement went stale in the two days between authoring and merging.
  3. Without an automated check, downstream documents drift quietly. A human discovers stale plans only during manual grooming or when implementation runs into contradictions.
  4. The repository's proven idiom is declaration plus verification (e.g. `rules-lock.json` against rule sources, declared `- Validators:` lines, declared `- Mode:`). Enforcing the cascade requires the same idiom: an explicit declaration on each downstream document, mechanically checked on turn ends.
- Acceptance criteria:
  - [x] **AC1:** WHEN a downstream document is written THE SYSTEM SHALL carry `- Reconciled against PRD: <sha>` on one physical line, where `<sha>` is the full 40-character hexadecimal git commit SHA of `PRD.md`, read using the same extraction pattern as `gate_steering_read` (`^ *- *Reconciled against PRD: *([0-9a-fA-F]{40})`).
  - [x] **AC2:** WHEN the PRD's last-modifying commit is newer than or differs from a document's recorded sha THE SYSTEM SHALL fail and name both the document, its recorded sha, and the current PRD commit sha it has not been reconciled against.
  - [x] **AC3:** WHEN `- Mode:` is `minimum` THE SYSTEM SHALL require the line on `DESIGN.md` and `BACKLOG.md`; `full` adds `ROADMAP.md` and `CONTRACT.md`. `NORTH_STAR.md` is upstream of the PRD and carries no line.
  - [x] **AC4:** WHEN the guard cannot establish the PRD's history (e.g. unresolvable git repository, detached/unborn HEAD with no PRD commit, or uncommitted modifications to `PRD.md`) THE SYSTEM SHALL fail rather than report success — it must never exit 0 having checked nothing.
  - [x] **AC5:** WHEN `- Mode:` is `bootstrap` THE SYSTEM SHALL pass without requiring the line, since inception documents are not authored yet.
  - [x] **AC6:** The guard SHALL be implemented as a standalone script `assets/check-document-cascade.py`, named on `.steering/tech.md`'s `- Validators:` line, and therefore covered by the reviewer's allow-list in `.claude/agents/gate-sdd-reviewer.md`.
  - [x] **AC7:** A missing or malformed line (missing SHA, invalid SHA, or non-hex SHA) SHALL be a failure, never a default. An absent declaration cannot read as reconciled.
  - [x] **AC8:** Inception skills (`design-doc`, `roadmap`, `backlog`, `contract`) templates and instructions SHALL mandate the `- Reconciled against PRD: <sha>` line in their preambles, and instruct how to populate/re-stamp it from `git log -n 1 --format=%H -- <docs>/PRD.md`. `skills/prd/SKILL.md` SHALL note that modifying `PRD.md` invalidates downstream reconciliation.
  - [x] **AC9:** Existing downstream inception documents in `docs/` (`DESIGN.md`, `ROADMAP.md`, `BACKLOG.md`, `CONTRACT.md`) SHALL be stamped with the latest modifying commit SHA of `docs/PRD.md` (`99e15913803d5e882a1cfc2e2713c6a6d1b081cd`), passing `assets/check-document-cascade.py`.
  - [x] **AC10:** Automated test cases in `scripts/test-gates.sh` (Case 225) SHALL verify `bootstrap` pass, `minimum` and `full` enforcement, missing line, uncommitted PRD, stale SHA failure, clean match, and red-capability under named mutation.
- Out of scope:
  - Verifying that a human actually re-read the upstream document (the line records that someone stamped it; that is the honest limit).
  - Capability-coverage check across `ROADMAP.md` and `BACKLOG.md` (deferred to a separate issue).
  - Reconciliation against anything other than `PRD.md`.
  - Checking documents in `bootstrap` mode.

### Clarifications

Four questions, resolved before design (2026-10-12):
1. **What format should the reconciliation identifier take in `- Reconciled against PRD: <sha>`?** — *Answered: Full 40-character git commit SHA (exact, deterministic, aligns with `rules-lock.json` sha-pinning pattern).*
2. **Where should the cascade enforcement guard be implemented and named?** — *Answered: A standalone Python script `assets/check-document-cascade.py` added to `.steering/tech.md`'s `- Validators:` line (the 14th validator).*
3. **How should the reconciliation line be initialized on downstream documents?** — *Answered: Authored and updated by inception skills (`design-doc`, `roadmap`, `backlog`, `contract`) using `git log -n 1 --format=%H -- <docs>/PRD.md`; `init` writes no placeholder documents.*
4. **How should the guard handle uncommitted working-tree modifications to `PRD.md`?** — *Answered: Fail if `PRD.md` has uncommitted working tree changes, requiring `PRD.md` to be committed before downstream reconciliation can be valid.*

## 2. Design (HOW)

- Approach and key decisions:
  1. **Standalone Python validator `assets/check-document-cascade.py`.** Standard library only (`os`, `sys`, `pathlib`, `subprocess`, `re`). Follows the architecture of `assets/check-document-set.py` and `assets/check-locks.py`. Copied into projects by `init` and run on the project's `- Validators:` line.
  2. **Strict mode and doc directory resolution.** Read `- Mode:` and `- Docs:` from `.steering/tech.md` using the exact `gate_steering_read` regex pattern. Fail closed if `- Mode:` is missing, empty, or unrecognised.
  3. **Bootstrap mode bypass.** In `bootstrap` mode, print diagnostic (`check-document-cascade: mode bootstrap — inception documents not yet authored; cascade verification deferred`) and exit 0.
  4. **PRD working tree and history verification.**
     - Ensure `<docs>/PRD.md` exists and is tracked.
     - Execute `git status --porcelain -- <docs>/PRD.md`. If output is non-empty, fail: `PRD.md has uncommitted working tree changes; commit PRD.md before reconciling downstream documents`.
     - Execute `git log -n 1 --format=%H -- <docs>/PRD.md`. If git fails or output is not a 40-character hex string, fail closed: `cannot determine PRD.md commit history`.
  5. **Required document set based on mode.**
     - Under `minimum`: `["DESIGN.md", "BACKLOG.md"]`.
     - Under `full`: `["DESIGN.md", "BACKLOG.md", "ROADMAP.md", "CONTRACT.md"]`.
     - `NORTH_STAR.md` is upstream of `PRD.md` and is never checked.
  6. **Reconciliation line validation.**
     - For each required document in `<docs>`:
       - If document does not exist, record failure: `missing required document <doc>`.
       - Read physical lines matching `^ *- *Reconciled against PRD: *(.*)`.
       - If line is absent, record failure: `<doc> missing '- Reconciled against PRD:' line`.
       - Extract SHA. If value does not match `^[0-9a-fA-F]{40}$`, record failure: `<doc> invalid SHA '<val>'`.
       - If recorded SHA != PRD commit SHA, record failure: `<doc> reconciled against <recorded_sha>, but PRD.md is at <prd_sha>`.
  7. **Inception skills updates.**
     - `skills/design-doc/SKILL.md`: update template preamble and authoring step to include `- Reconciled against PRD: <sha>` fetched via `git log -n 1 --format=%H -- <docs>/PRD.md`.
     - `skills/roadmap/SKILL.md`: update template preamble and authoring step to include `- Reconciled against PRD: <sha>`.
     - `skills/backlog/SKILL.md`: update template preamble and authoring step to include `- Reconciled against PRD: <sha>`.
     - `skills/contract/SKILL.md`: update template preamble and authoring step to include `- Reconciled against PRD: <sha>`.
     - `skills/prd/SKILL.md`: update steps to note that modifications to `PRD.md` advance its commit SHA and require re-stamping downstream documents.
     - `skills/init/SKILL.md`: instruct copying `assets/check-document-cascade.py` to `scripts/` and adding to `- Validators:`.
  8. **Wiring in repository.**
     - Add `./assets/check-document-cascade.py` to `.steering/tech.md`'s `- Validators:` line (validator #14).
     - Add `./assets/check-document-cascade.py` to `.claude/agents/gate-sdd-reviewer.md`'s Bash policy allow-list.
     - Stamp `docs/DESIGN.md`, `docs/ROADMAP.md`, `docs/BACKLOG.md`, `docs/CONTRACT.md` with `- Reconciled against PRD: 99e15913803d5e882a1cfc2e2713c6a6d1b081cd`.
     - Update `AGENTS.md` contributor short list of validators.
  9. **Automated test coverage in `scripts/test-gates.sh`.** Case 225 covering all failure modes (missing line, uncommitted PRD, stale SHA, bootstrap pass, minimum/full sets) and verifying red-capability under named mutation.

- Affected modules and files, per `.steering/structure.md`:
  - `assets/check-document-cascade.py` — shipped. New validator script. (AC1–AC7)
  - `skills/design-doc/SKILL.md` — shipped. (AC8)
  - `skills/roadmap/SKILL.md` — shipped. (AC8)
  - `skills/backlog/SKILL.md` — shipped. (AC8)
  - `skills/contract/SKILL.md` — shipped. (AC8)
  - `skills/prd/SKILL.md` — shipped. (AC8)
  - `skills/init/SKILL.md` — shipped. (AC8)
  - `.steering/tech.md` — not shipped. Adds 14th validator. (AC6)
  - `.claude/agents/gate-sdd-reviewer.md` — not shipped. Allow-list addition. (AC6)
  - `docs/DESIGN.md` — not shipped. Stamped with PRD SHA. (AC9)
  - `docs/ROADMAP.md` — not shipped. Stamped with PRD SHA. (AC9)
  - `docs/BACKLOG.md` — not shipped. Stamped with PRD SHA. (AC9)
  - `docs/CONTRACT.md` — not shipped. Stamped with PRD SHA. (AC9)
  - `AGENTS.md` — not shipped. Short-list update. (AC6)
  - `scripts/check-skill-contracts.py` — not shipped. Pin new init instruction if applicable. (AC8)
  - `scripts/test-gates.sh` — not shipped. Automated Case 225. (AC10)
  - `plugin.json` and `.claude-plugin/plugin.json` — shipped. Version bump (implement step after review).
  - `.work_logs/2026-10-12.md` — not shipped. Work log entry (implement step after review).

- Contract changes, and who else consumes them:
  - `assets/check-document-cascade.py` is copied into consumer repositories by `init` and added to their `- Validators:` line.
  - Consumers running in `minimum` mode must carry `- Reconciled against PRD: <sha>` on `DESIGN.md` and `BACKLOG.md`.
  - Consumers running in `full` mode must additionally carry it on `ROADMAP.md` and `CONTRACT.md`.
  - Updating `PRD.md` now causes `- Validators:` to fail on downstream documents until explicitly reconciled and re-stamped.

- Risks and trade-offs:
  - **Friction on PRD edits:** When `PRD.md` is updated, 2 to 4 downstream documents will fail the cascade check until their reconciliation lines are re-stamped. This is deliberate: this is the mechanical friction needed to prevent the fifth grooming failure mode (unnoticed downstream drift).
  - **Commit-before-stamp sequence:** Because the SHA must come from a committed `PRD.md`, authoring PRD and downstream documents in a single uncommitted pass requires committing `PRD.md` first, or stamping after commit. Handled cleanly in skill instructions.

## 3. Tasks (TDD-ordered)

> One task is one complete Red-Green-Refactor cycle, so one green commit. No task is sequenced after the review.

- [x] T1: failing test in `scripts/test-gates.sh` (Case 225 asserting cascade check behavior: bootstrap mode pass, minimum/full mode enforcement, missing line, uncommitted PRD, stale SHA failure, clean match) — then the implementation of `assets/check-document-cascade.py` making it pass
- [x] T2: update inception skills (`design-doc`, `roadmap`, `backlog`, `contract`, `prd`, `init`), stamp repository's `docs/` documents (`DESIGN.md`, `ROADMAP.md`, `BACKLOG.md`, `CONTRACT.md`) with PRD commit `99e15913803d5e882a1cfc2e2713c6a6d1b081cd`, add `./assets/check-document-cascade.py` to `.steering/tech.md` `- Validators:`, `.claude/agents/gate-sdd-reviewer.md`, and `AGENTS.md`, and verify all 14 gating validators pass cleanly
- [x] T3: refactor and verification pass across all validators, with named mutation proving red-capability of Case 225 in `scripts/test-gates.sh`
