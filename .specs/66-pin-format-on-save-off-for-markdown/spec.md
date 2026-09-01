# Spec: Pin format-on-save off for Markdown in the workspace
- Slug: 66-pin-format-on-save-off-for-markdown   Issue: 66   Type: chore   Status: draft
- Author: m0m0i   Date: 2026-09-01

## 1. Requirements (WHAT / WHY)

- What changes: add `.vscode/settings.json` containing a `[markdown]` block that sets `editor.formatOnSave` to `false`, committed so it applies to every clone. Both Claude Code's VS Code extension and Antigravity read workspace settings from that path.
- **What must NOT change:** the rendered output and the bytes of every existing file; the eight validators at their current values, with `test-gates.sh` at 54 passed / 0 failed; `check-markdown-fences.py` still reporting 10 fences and no hand-wrapped prose. This adds an editor setting and edits no content. Nothing shipped moves — `.vscode/` is in neither `Source globs` nor `check-version-bump.py`'s `SHIPPED`, so no version bump is required and none is made.
- Why now: it already cost a review round on #64, and the damage was not cosmetic. A formatter wrote a stale buffer over `.specs/64-.../spec.md` between two commits, flipping `Status: done` back to `approved`, unticking six acceptance criteria and T5, and destroying four uncommitted edits. `hooks/review-gate.sh` passes silently when a spec has any open task, so the branch was one step from a pull request with the review gate never firing — on a branch about gates that fail open. It happened twice, because the first time it was reverted by hand and no guard was put in place.
- Acceptance criteria:
  - [ ] **AC1:** WHEN the repository is opened in an editor that reads workspace settings THE SYSTEM SHALL have `editor.formatOnSave` false for the `[markdown]` language, stated in a tracked `.vscode/settings.json`.
  - [ ] **AC2:** the file parses as the JSON-with-comments an editor will accept, and contains no key other than the Markdown scope — verified by parsing it, not by reading it.
  - [ ] **AC3:** every tracked file other than the new one and this spec is byte-identical to `main`, and the eight validators hold their values with `test-gates.sh` at 54 passed / 0 failed.
- Out of scope: changing the user's own Antigravity settings, which are theirs to edit; a `.prettierignore`, rejected because it only works if the formatter is Prettier while disabling `formatOnSave` for the language is formatter-agnostic; and any second opinion about how Markdown should be written, which is `CONTRIBUTING.md`'s and `check-markdown-fences.py`'s job.

### Clarifications

None needed — the requirement is one setting, and the alternative considered is recorded on #66 with its reason.

## 2. Design (HOW)

- Approach: one new file, no edits to existing ones.

```jsonc
{
  // Prettier-on-save reverted a spec twice during #64 — see .work_logs/2026-08-31.md.
  "[markdown]": {
    "editor.formatOnSave": false
  }
}
```

Scoped to the `[markdown]` language rather than set globally, so the setting suppresses formatting of this repo's documents without taking a position on anyone's TypeScript. `editor.formatOnSave` is the trigger every formatter hangs off, so disabling it for the language is formatter-agnostic — which matters, because the diagnosis identified Prettier from its signature and from `editor.defaultFormatter`, not by watching it run.

- **The limitation, stated rather than left to be discovered:** this cannot be tested by `test-gates.sh`. The failure lives in an editor, outside anything the harness executes, so the guard is a committed setting and not a case. The repo has no way to assert that a formatter did not run. AC2 is therefore about the file being well-formed and minimal — the most a test here can honestly claim.
- Affected files: `.vscode/settings.json` (new). Nothing else.
- Rollback: delete the file.

## 3. Tasks (TDD-ordered)
> One task is one complete Red-Green-Refactor cycle, so one green commit.
- [ ] T1: a check that the settings file exists, parses, and carries only the Markdown scope — failing first because the file does not exist — then the file that satisfies it
- [ ] T2: confirm the invariant — every other tracked file byte-identical to `main`, validators at their values, `test-gates.sh` 54/0
