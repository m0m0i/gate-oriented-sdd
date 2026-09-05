# Spec: The README Status section describes a repository that no longer exists

- Slug: 48-readme-status Issue: 48 Type: bug Status: done
- Author: m0m0i Date: 2026-09-05

## 1. Requirements (WHAT / WHY)

- Reproduction: `grep -n "v0\.2\.3" README.md README.ja.md` matches once in each while `plugin.json` says 0.4.2; `README.md:158` says the skills have never been executed end to end and no reviewer has yet reviewed a real diff; `README.ja.md:159` renders the second claim as "has not yet reviewed every diff"; `README.md:154` and `docs/verified.md:13` give Claude Code 2.1.238 while this session's runs were under 2.1.252; `docs/layout.md:93` lists four files under `docs/` where there are eleven and a directory.
- Expected: every claim in the section that sells the project's honesty is true at HEAD, and the Japanese README says the same thing as the English one (C-3).
- Actual: the section was written at 0.2.3 and every sentence in it aged. The skills have each run at least once (#55, #56, #58, #77, #76; `docs/verified.md`), the reviewer has reviewed every pull request since #17 as a subagent, and `claude plugin eval` now exists on the account and exits 0 without running.
- **Root cause:** `check-version-bump.py` exempts the READMEs by design (its docstring), nothing compares a README claim against anything, and the Status section states facts in prose that only a run can refresh. #23's shape on four more facts.
- Acceptance criteria:
  - [x] **AC1:** Both READMEs' Status sections carry the version `plugin.json` carries, demonstrated by grep.
  - [x] **AC2:** The "what is not verified" sentence in both READMEs states only what `docs/verified.md` does not support — the interviews' independence, the eval suite, `init`'s greenfield and upgrade paths, the Antigravity rows since 2026-08-21 — and the "what is verified" sentence gains the skill runs and the reviewer's receipts; the Japanese section says the same as the English (C-3), and the mistranslation is gone.
  - [x] **AC3:** The matrix reads Claude Code 2.1.252 dated 2026-09-05 and keeps Antigravity CLI 1.1.17 and IDE 2.3.1 as last verified 2026-08-21 and not re-run since, in both READMEs and in `docs/verified.md`'s table — clarification 1.
  - [x] **AC4:** `docs/layout.md`'s harness-repository picture lists what `docs/` holds at HEAD.
  - [x] **AC5:** The eval sentence states the observed behaviour — the command exists, prints "in early access", exits 0 without running a case — and still refuses to read that as a pass.
  - [x] **AC6:** `git diff --name-only main` is confined to `README.md`, `README.ja.md`, `docs/layout.md`, `docs/verified.md` and this directory; every `- Validators:` command at exit 0, run after the last write; `check-version-bump.py` reports no shipped file changed.
- Out of scope: a guard comparing the READMEs' version to the manifests, which #48 raises and says may belong with #23; any README section other than Status; `docs/fidelity.md`.

### Clarifications

Resolved 2026-09-05.

1. **Re-run the matrix, or re-date it?** Re-date Claude Code to 2.1.252, observed in this session's runs, and keep the two Antigravity rows at the versions and date they were verified, saying they were not re-run. Re-running the Antigravity CLI at the installed 1.1.18 was rejected for this branch: only the CLI row could be re-run from here and the IDE row would still carry its old date. Leaving the matrix untouched was rejected because the Claude Code row would then understate what was run today.

## 2. Design (HOW)

- **Approach.** T1 is the regression test in the only form prose admits — greps that match the false claims today and must match nothing after — plus checksums. T2 rewrites the two Status sections as mirrors of each other, the matrix line in three places, the layout picture's `docs/` line, and the eval sentence.
- **Affected files.** `README.md`, `README.ja.md`, `docs/layout.md`, `docs/verified.md`, this directory.
- **Coverage gap.** Nothing checks a prose claim; T1's greps are the test and they are recorded red before the change.
- **Rollback.** `git revert`.

## 3. Tasks (TDD-ordered)

> One task is one complete Red-Green-Refactor cycle, so one green commit.

- [x] T1: record the greps red — the stale version, the two false claims, the mistranslation, the old Claude Code version, the stale `docs/` line — and the checksums.
- [x] T2: rewrite; confirm the greps clear and AC1–AC6 hold with the validators run after the last write.
