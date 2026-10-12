# Spec: init does not say how CLAUDE.md points at AGENTS.md, and a prose pointer keeps AGENTS.md out of a Claude Code session
- Slug: 239-claude-md-imports-agents-md   Issue: 239   Type: bug   Status: done
- Author: m0m0i   Date: 2026-10-12

## 1. Requirements (WHAT / WHY)
- Reproduction: run `init` for Claude Code. Step 3's `AGENTS.md` bullet says *"Point to it with CLAUDE.md for Claude Code"* and nothing about the form, so the natural result is one line of prose linking `AGENTS.md`. Start a session there under the default **Project instructions** value.
- Expected: the project's `AGENTS.md` is in context at session start — what `docs/fidelity.md`'s Rules discovery row and both READMEs claim.
- Actual: under `claude-md-or-agents-md` a `CLAUDE.md` suppresses native `AGENTS.md` reading, and a prose pointer loads it only if Claude decides to open it. Measured on this repository's own prose `CLAUDE.md` on 2026-10-04 (#239's table): `NOT-IN-CONTEXT` under the default and under `claude-md`.
- Impact: every Claude Code install `init` writes a pointer into. `AGENTS.md` is the canonical context file; a session that never reads it runs without the project's rules, and nothing reports it.
- **Root cause:** #146 added harness-specific pointers and said *point*, not *how*, a day after Claude Code 2.1.277 began reading `AGENTS.md` natively only when no `CLAUDE.md` exists. The fidelity row's "verified" covered the Antigravity symlink (#145) and was read as covering Claude Code too.
- Acceptance criteria:
  - [ ] **AC1:** `init` step 3's `AGENTS.md` bullet says that on Claude Code `CLAUDE.md` imports it with a line reading `@AGENTS.md`, that a prose pointer is not enough and why, and that an existing `CLAUDE.md` gets the line added after a diff; #146's pinned phrase stays.
  - [ ] **AC2:** `scripts/check-skill-contracts.py` pins the import instruction, failing before the edit.
  - [ ] **AC3:** a probe in a scratch project — `AGENTS.md` stating facts nothing else states — shows the form `init` now writes (a root `CLAUDE.md` with `@AGENTS.md`) answering them at session start under the default, and a prose pointer not; recorded in `docs/verified.md`.
  - [ ] **AC4:** the Claude Code cell of the Rules discovery row in `docs/fidelity.md`, `README.md` and `README.ja.md`, and `docs/layout.md`'s two `AGENTS.md`/`CLAUDE.md` lines, say the project's `AGENTS.md` reaches a session through that import and cite AC3's run; none claims the plugin's own `AGENTS.md` reaches a Claude Code session.
  - [ ] **AC5:** every command on the `- Validators:` line exits 0.
- Out of scope: the form of `GEMINI.md` (whether Antigravity expands an import is unmeasured; the fidelity row says so); dropping `CLAUDE.md` for native reading (it needs a Claude Code floor above the READMEs' tested-against line); the Antigravity leakage gap (A10).

### Clarifications
None needed — the issue's open questions are answered by the repo: the row's Claude Code cell can only mean the consumer's `AGENTS.md`, since Claude Code never reads a plugin's install directory; the import is the form #237 measured here and works under every **Project instructions** value but `managed-only`, while a symlink replaces a file the project may already own and dropping `CLAUDE.md` needs a newer floor; extending the sentence keeps #146's pin.

## 2. Design (HOW)
- Fix approach: one sentence in `init` naming the import and the reason, pinned; a measured probe of the consumer form; the four claim sites reworded to what was measured. Narrower — prose only — leaves the fidelity row claiming an unmeasured form. Wider — a guard that a consumer's `CLAUDE.md` carries the import — would block projects whose user sets `claude-md-and-agents-md` and needs no import.
- Affected files: `skills/init/SKILL.md`, `scripts/check-skill-contracts.py`, `docs/fidelity.md`, `docs/layout.md`, `docs/verified.md`, `README.md`, `README.ja.md`, `docs/BACKLOG.md` row 1.
- **Blast radius:** `check-readme-claims.py` reads both READMEs; the row change must keep the two in step (C-3). #146's pin and `test-gates.sh`'s fixture for it are unchanged because the pinned phrase stays.
- Why this cannot recur: the pin keeps the form in `init`; the fidelity cell now cites a run of the form rather than a run of a different file.
- Version: minor, 0.30.0 → 0.31.0 — `init` writes a different file. A step after the receipt.

## 3. Tasks (TDD-ordered)
> One task is one complete Red-Green-Refactor cycle, so one green commit. No task is sequenced after the review.
- [x] T1: the pin, run red, then `init` step 3's sentence — green (AC1, AC2)
- [x] T2: the probe recorded in `docs/verified.md`, then the fidelity row, both READMEs, `docs/layout.md` and backlog row 1; every validator green (AC3, AC4, AC5)
