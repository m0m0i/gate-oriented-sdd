# Spec: Each reviewer's lock note names the reviewer it grounds

- Slug: 47-lock-notes-name-their-reviewer Issue: 47 Type: bug Status: done
- Author: m0m0i Date: 2026-09-05

## 1. Requirements (WHAT / WHY)

- Reproduction: `grep -o '"note": "Grounding for [a-z-]*' agents/*/rules-lock.json` gives `ts-reviewer` three times — for `python-reviewer` and `dart-flutter-reviewer` too.
- Expected: each lock's `note` names the reviewer it grounds; the rest of the note — vendored versus derived, and why live documentation is not hashed — is identical across the three by design.
- Actual: two notes were copied from the TypeScript lock and the name was never changed. `check-locks.py` does not read `note`, so nothing noticed.
- **Root cause:** the locks were authored by copying, and the one field that differs per reviewer is free text no guard inspects.
- Acceptance criteria:
  - [x] **AC1:** The grep gives `python-reviewer`, `ts-reviewer`, `dart-flutter-reviewer`, each once, in its own lock.
  - [x] **AC2:** `check-locks.py` still reports 6 pinned files matching; the `vendored`, `derived`, `policy` and `version` fields of all three locks are byte-identical to `main`'s — only `note` changes.
  - [x] **AC3:** Both manifests move 0.4.2 → 0.4.3 and agree; `check-version-bump.py` against `main` passes; every other `- Validators:` command at exit 0 after the last write.
  - [x] **AC4:** `git diff --name-only main` is confined to the two locks, the two manifests, and this directory.
- Out of scope: a guard that reads `note` (`rules-lock.json` notes are prose; #23's family); the `generatedAt` field, left as it is because nothing regenerated the lock.

### Clarifications

None needed — requirements were unambiguous.

## 2. Design (HOW)

- **Approach.** T1 records the grep red. T2 edits the one substring in two files with a JSON-preserving replacement, bumps both manifests, and re-runs the guards. A version bump is a release: after merge, `claude plugin tag` creates `gate-sdd--v0.4.3` and the tag is pushed, which is the half #68 says nothing enforces.
- **Affected files.** `agents/python-reviewer/rules-lock.json`, `agents/dart-flutter-reviewer/rules-lock.json`, `plugin.json`, `.claude-plugin/plugin.json`, this directory.
- **Coverage gap.** Nothing reads `note`; the grep is the test.
- **Rollback.** `git revert`; the tag, if made, is deleted with it.

## 3. Tasks (TDD-ordered)

> One task is one complete Red-Green-Refactor cycle, so one green commit.

- [x] T1: record the grep red and the locks' checksums.
- [x] T2: fix the two notes, bump both manifests, assert AC1–AC4 with the validators run last.
