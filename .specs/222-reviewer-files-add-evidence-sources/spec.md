# Spec: The contract's Bash policy forbids any evidence source a reviewer file adds, and every reviewer file adds one
- Slug: 222-reviewer-files-add-evidence-sources   Issue: 222   Type: bug   Status: approved
- Author: m0m0i   Date: 2026-10-01

## 1. Requirements (WHAT / WHY)

- Reproduction: #222's **Reproduction**, steps 1–4.
- Expected: #222's **Expected** — one rule, which a reviewer reading its own file and its contract can follow literally.
- Actual: #222's **Actual**. All five reviewer files this repository ships or runs add a source the contract's line 22 forbids, and four of them do it as an instruction their own allow-list does not permit.
- Impact: #222's **Scope of impact**. The contradiction is in the reviewer layer, not in a gate. No gate fails open, so this is not a BLOCKER under `gates never fail open`. It is a contract every reviewer is told to obey and cannot.
- **Root cause:** the Bash policy was written as a closed list of general purposes. Since then, additions have been made in the places they were needed: a lock check in each rulebook section, `claude plugin validate` on the dogfood list, and a project's evidence sources downstream. Nobody went back to the sentence that closes the list. Line 3 says a reviewer file adds "what is specific to its stack" and frames that as grounding and checks, never as evidence sources. `scripts/check-reviewer-allow-list.py` deliberately chose "containment, not equality" for extra allow-list entries, and the contract never learned that either. Every document that touched the question was right for its own case, and the one sentence that generalises them was never written.
- Acceptance criteria:
  - [ ] **AC1:** WHEN a reviewer reads its contract's `## Bash policy`, THE contract SHALL let a reviewer file add an evidence source beyond the four general purposes, on four conditions (named as a command form, read-only, scoped, explained). It SHALL still send to a finding, not a run, both a command the file does not list and a listed one that fails a condition. Evidence: the contract rows of the grep table in section 2.
  - [ ] **AC2:** THE contract's line 3 SHALL name project-specific evidence sources among what a reviewer file adds, and point to the Bash policy rather than restate it. Evidence: its grep-table rows.
  - [ ] **AC3:** `.claude/agents/_shared/reviewer-contract.md` SHALL be byte-identical to `agents/_shared/reviewer-contract.md`, and `./scripts/check-receipt-schema.py` SHALL print its merge-base line.
  - [ ] **AC4:** The `## Bash policy` sections of `agents/ts-reviewer.md`, `agents/python-reviewer.md`, `agents/dart-flutter-reviewer.md` and `agents/_template/reviewer.md` SHALL each name `shasum -a 256` with its reason. In `.claude/agents/gate-sdd-reviewer.md`, every entry outside the four purposes and the `- Validators:` line SHALL carry its reason. `./scripts/check-reviewer-allow-list.py` SHALL print its merge-base line.
  - [ ] **AC5:** THE allow-list sentence in `README.md` and the one in `README.ja.md` SHALL both state that a reviewer file may add a source with its reason, and SHALL make the same claim as each other (C-3).
  - [ ] **AC6:** THE text this diff adds to the contract SHALL name no path that exists only in this repository. Evidence: the contract's word-level diff (`git diff --word-diff=porcelain`) adds no backticked path except `.git/`. Word level, because the clock paragraph's line is rewritten for one phrase, and a line diff would re-add the existing mention of `scripts/check-receipt-schema.py`. This is #188's class, and #188 owns the sentence already there.
  - [ ] **AC7:** At the tip, every validator on `.steering/tech.md`'s `- Validators:` line SHALL exit 0. Every validator other than `check-readme-claims.py` SHALL print its merge-base summary line, and `check-readme-claims.py`'s line SHALL differ only in the version the bump moves. `test-gates.sh` SHALL report 169 passed, 0 failed, 0 skipped, the same as at the merge-base.
  - [ ] **AC8:** Row 17's Item cell in `docs/BACKLOG.md` SHALL name **#222**, and `./scripts/check-backlog-tracker.py` SHALL exit 0 on the pull request, where CI runs it.
  - [ ] **AC9:** THE grep table SHALL show every old string at 1 and every new one at 0 at the merge-base, and the reverse at the tip. It is this bug's regression test, recorded in T1's commit body before any edit.
- Out of scope:
  - **#119**: whether `git grep` joins the dogfood reviewer's list. This change gives #119 a third resolution and does not choose it.
  - **#185**: whether a reviewer may run mutations. The read-only condition decides nothing for it, because a mutation run writes and #185's design question is where.
  - **#188**: the existing sentence naming `scripts/check-receipt-schema.py`. It stays word for word.
  - **A guard pinning the new clause.** See the coverage gap in section 2.
  - **The downstream project's own reviewer file**, which conforms once its copy of the contract is refreshed.
  - **`skills/init/SKILL.md`.** It copies the contract verbatim and builds the reviewer from a reference file or `_template`, so both changes reach a new install without a word changing there.

### Clarifications

Asked and answered 2026-10-01, when #222 was filed.

- **Q1: file #222 as acknowledged unplanned work?** In `- Mode: full`, an issue created outside `sprint` is the maintainer's call (`spec` step 1). **A: filed as drafted.** The maintainer's task statement for this branch is the reason it is taken ahead of rows 1–16.
- **Q2: contract only, or the plugin's own reviewer files too?** **A: the reviewer files too** (AC4). After this change, a reviewer told by its own file to run `shasum` and told by its contract not to would be facing a contradiction the fix made sharper.

Decided here, as the author's calls rather than the maintainer's:

- **The read-only condition is "writes nothing the validators do not already write", not "touches nothing in the tree".** The contract's first section already says a reviewer never creates a file. A narrower condition would let a temporary directory through, and that would quietly decide #185.
- **Scoped means narrow enough that its reach can be read off the entry.** That is why "named" asks for a command form and not a tool. `gh api` as a GET, or `curl -sI` against a host a claim names, can be audited from the allow-list. `gh` or `curl` cannot.
- **Patch: 0.21.3 → 0.21.4.** #105 changed this same section to add the clock and shipped as 0.4.4. The prescribed flow does not move. #217 is also bumping to 0.21.4, so whichever merges second re-bumps.
- **#222 goes on row 17**, next to #119, because both are about what a reviewer's shell may run. The form follows #219 on row 19. No other row moves, and nothing is written under `## What changed at this refinement`.

## 2. Design (HOW)

- **Fix approach.** In the Bash policy, the closing sentence becomes a paragraph that permits additions on four conditions, followed by the existing "say so as a finding" sentence, now covering both ways a command can be out of scope. The next paragraph's "the clock is on that list" becomes "among the four general purposes", because a second list now sits between it and the one it meant. Line 3 gains "and its project" and a pointer to the Bash policy. Then the mirror is overwritten with `cp`, which is the remedy the receipt-schema guard itself prints.
  - **Narrower fix, rejected:** a fifth general purpose. Projects would still be forbidden their own sources, which is the downstream report, and every reviewer would get a source only some of them need.
  - **Wider fix, rejected:** dropping the list for "read-only commands". That loses the property the list exists for: a reviewer's reach can be read off its file.
- **Affected files:**
  - `agents/_shared/reviewer-contract.md` and its mirror `.claude/agents/_shared/reviewer-contract.md` (AC1–AC3, AC6).
  - Four shipped reviewer files: one bullet each in `## Bash policy` (AC4).
  - `.claude/agents/gate-sdd-reviewer.md`: a reason on `check-version-bump.py` and on `claude plugin validate . --strict` (AC4). `check-backlog-tracker.py` already carries one.
  - `README.md:132` and `README.ja.md:133` (AC5).
  - `docs/BACKLOG.md` row 17 (AC8).
  - The manifests, at the bump step.
- **Blast radius:** two guards read the `## Bash policy` section.
  - `check-receipt-schema.py` looks for the clock and `git rev-parse HEAD` needles, which nothing here removes, and compares the mirror byte for byte.
  - `check-reviewer-allow-list.py` matches the four categories and the `- Validators:` spans. A new bullet can only add matches, and none of the new text says "n/a", so the N/A branch is unreached.
  - `check-contract-path.py` reads the reviewers' contract-path line. #217 is rewriting that line, ten lines above any hunk here.
  - Every installed project gets the new contract on its next copy. Until then, its old contract still forbids what its reviewer file adds, which is today's state and no worse.
- **The grep table** (AC9). Each row is run as `grep -c` on the named file, and on both contract copies for the contract rows. "before" is the merge-base and "after" is the tip:

  | File | String | Before | After |
  | :-- | :-- | :-- | :-- |
  | both contract copies | `Anything else is out of scope. If you believe` | 1 | 0 |
  | both contract copies | `A reviewer file may also add an evidence source` | 0 | 1 |
  | both contract copies | `a listed one that fails any of the four conditions` | 0 | 1 |
  | both contract copies | `specific to its stack — the sources` | 1 | 0 |
  | both contract copies | `specific to its stack and its project` | 0 | 1 |
  | both contract copies | `The clock is on that list` | 1 | 0 |
  | four shipped reviewer files, `## Bash policy` section only | `shasum -a 256` | 0 | 1 |
  | `.claude/agents/gate-sdd-reviewer.md` | `` `claude plugin validate . --strict` — `` | 0 | 1 |
  | `README.md` | `strictly bounded to evidence-gathering commands (` | 1 | 0 |
  | `README.md` | `plus any source a reviewer file names with its reason` | 0 | 1 |
  | `README.ja.md` | `証拠収集コマンド（` | 1 | 0 |
  | `README.ja.md` | `理由を添えて名指しした情報源` | 0 | 1 |

  The section-only row reads the section with the same `bash_policy()` both guards use, because `ts-reviewer.md` and `_template` already mention `shasum` in their rulebook sections. Counting the whole file would show 1 before the fix and prove nothing.
- **Why this cannot recur.** It partly can, and the gap is recorded here rather than closed:
  - **What this change closes:** the contradiction. Once the contract names the permission and its conditions, a reviewer file that adds a source either meets them or is a finding. The reviewer applies the conditions when it reads its own list.
  - **The coverage gap:** no guard pins the clause. A guard can tell whether an entry is listed. It cannot tell whether an entry is read-only, scoped or explained, because all three are judgments, and judgments sit in the reviewer layer, which is this repo's second idea. A presence pin would defend the sentence's existence, but `check-skill-contracts.py`'s subject is skills, and its list is at the twenty-five its header caps without an argued exception. The argument for this sentence is weaker than for those twenty-five: deleting it would make every lock-carrying reviewer's own allow-list a finding on its next run, which review would see.
- Rollback: revert the branch's commits. A project that already copied the new contract keeps a contract more permissive than the plugin's until it re-copies. No gate reads the text, so the only cost is prose.

## 3. Tasks (TDD-ordered)
> One task is one complete Red-Green-Refactor cycle, so one green commit. No task is sequenced after the review.
- [x] T1: record the grep table's "before" column and the validators' merge-base lines in the commit body, then place #222 on row 17. The tracker check is the failing test: it has been red on `main` since #222 was filed. AC8, and AC9's before half.
- [ ] T2: amend the contract, then `cp` it over the mirror, in one commit. Editing only the shipped copy is the red step, and `check-receipt-schema.py` must fail naming the mirror before the copy turns it green. AC1–AC3, AC6.
- [ ] T3: the four shipped reviewer files and the dogfood reviewer. Run the section-only `shasum` count at 0 first. AC4.
- [ ] T4: both READMEs in one commit, so no commit on the branch leaves the pair disagreeing. AC5, AC7, and AC9's after half.
