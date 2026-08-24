# Spec: check-locks.py reports success when it verified nothing
- Slug: 16-lock-guard-reports-nothing-as-success   Issue: 16   Type: bug   Status: approved
- Author: m0m0i   Date: 2026-08-24

## 1. Requirements (WHAT / WHY)

- Reproduction: in a clean checkout, `./assets/check-locks.py` reports `6 pinned file(s) match
  their locks`. Create a project-local reviewer the way `init` does — `.claude/agents/<r>/` with a
  `rules-lock.json` — and it reports `0 pinned file(s) match their locks`, exit 0. Append a rule to
  `agents/ts-reviewer/rules/types-and-style.md` and it still reports `0`, exit 0. CI is green while
  a shipped rulebook has drifted.

- Expected: two things, both violated.
  1. Adding a project-local reviewer does not stop the repository's own rulebooks being checked.
  2. Verifying zero files is not success. A guard that checked nothing must not be indistinguishable
     from one that checked everything and found no drift.

- Actual: three unrelated states emit the identical line and the identical exit code:

  | State | Output | Exit |
  | :-- | :-- | :-- |
  | a lock exists under `.claude/agents/` that pins nothing | `0 pinned file(s)` | 0 |
  | …and a shipped rulebook has since been corrupted | `0 pinned file(s)` | 0 |
  | a repository with no lock files at all | `0 pinned file(s)` | 0 |

- Impact: this repository, on the guard protecting one of the two mechanisms `AGENTS.md` names as
  the reason the repo exists — the rulebook hash-pinned to its sources. Six pinned files stop being
  verified with no symptom beyond a number nobody diffs. It also lands on any consumer project
  keeping reviewers in more than one candidate location, but the harness repo is the case that is
  certain rather than hypothetical: it is triggered by installing the harness into itself, which is
  what #17 does. That PR ships a deliberately **unpinned** rulebook, explained in three places, as
  the workaround.

- **Root cause:** two independent defects that compound, and either alone would be survivable.

  `_reviewers_dir()` returns the **first** candidate directory that holds a lock and stops. Its
  docstring reasons correctly that the reviewer directory differs between the harness repo
  (`agents/`) and a project (`.claude/agents/`), then encodes "pick whichever" — which silently
  assumes the two can never coexist. In this repository they must.

  The zero-count then hides the switch. `checked` reaching 0 is reported through the success path,
  so no output, exit code, or CI signal distinguishes "scanned a directory with nothing in it" from
  "scanned everything and found no drift". This is the half that turned a wrong directory into an
  invisible one.

- Acceptance criteria:
  - [x] **AC1:** every candidate reviewer directory SHALL be scanned, not the first one that matches.
  - [x] **AC2:** WHEN lock files exist but zero pinned files were verified THE SYSTEM SHALL fail.
  - [x] **AC3:** the output SHALL name which directories were scanned and how many locks were found,
        so a count of zero is never ambiguous to a reader.
  - [x] **AC4:** WHEN a shipped rulebook has drifted THE SYSTEM SHALL fail regardless of what other
        reviewer directories exist.
  - [x] **AC5:** `--update` SHALL re-pin only the lock whose file drifted, and SHALL NOT rewrite a
        lock in a different reviewer directory.
  - [x] **AC6:** the regression test fails before the fix and passes after.
  - [x] **AC9:** WHEN a reviewer directory exists but cannot be read THE SYSTEM SHALL fail.
        *Added during the reviewer pass.* AC3 asked the report to name the directories it
        scanned, and implementing it created this: `Path.glob` swallows a permission error and
        yields nothing, so an unreadable reviewer contributed no locks while still being named
        as scanned. The report asserted coverage it did not have — AC3 made the failure worse
        rather than better, which the spec did not anticipate.
  - [x] **AC7:** WHEN no lock files exist in any candidate directory THE SYSTEM SHALL exit 0 with
        wording that cannot be read as a successful verification.
  - [x] **AC8:** every AC above SHALL be pinned by a case in the deterministic suite.

- Out of scope: **teaching `--update` to create a lock that does not exist** — filed as #19. It is
  what stops this repo's own reviewer being pinned, but it is a new capability with its own design
  questions (vendored or derived? what sources does a generated lock cite? `--update` or a separate
  `--init`?), and answering them here would turn a small fix to a lying guard into a feature.
  Also out of scope: the error message's `./scripts/check-locks.py --update` hint, which is correct in a
  project and wrong in the harness repo where the script lives at `assets/`. Adjacent, one line,
  and it will be fixed here only if it falls inside the diff anyway — otherwise its own issue.

### Clarifications
- **Q: first-match or all candidate directories?**
  A: scan all and union them. The docstring's premise — "pick whichever actually holds a pinned
  rulebook" — is the defect, not the implementation of it. A union makes the harness repo and a
  consumer project behave identically with no flag, and coexistence stops being a special case
  rather than being handled as one. A `--dir` flag was rejected: a flag nobody passes is a flag
  that rots, and there is no current need to gate one directory separately.
- **Q: a repository with no locks anywhere — pass or fail?**
  A: pass, with distinct wording. It is legitimate: a project may install the guard before its
  first reviewer exists. Failing would give that project a red build it can only fix by deleting
  the guard, which is how a guard gets deleted. The requirement is that its message cannot be
  confused with a successful verification.
- **Q: is `--update` bootstrapping in scope?**
  A: no — #19.

## 2. Design (HOW)
- Fix approach, and why this rather than the narrower or wider fix:
  Two changes matching the two defects, plus a third outcome that only exists once they are
  separated.

  `_reviewers_dir() -> Path` becomes `_reviewer_dirs() -> list[Path]`, returning every candidate
  that exists, and the lock loop iterates the union. Each lock is read and rewritten at its own
  path, so a union cannot cross-contaminate `--update`.

  The terminal report gains a third branch, because there are three states and today there are two
  messages:

  | locks found | files verified | outcome |
  | :-- | :-- | :-- |
  | 0 | 0 | exit 0 — "no rulebooks are pinned in *dirs*" |
  | > 0 | 0 | **exit 1** — locks exist and none of them pinned anything verifiable |
  | > 0 | > 0 | exit 0 — "*n* pinned file(s) match their locks across *dirs*" |

  Naming the directories scanned in every branch is what makes a zero legible without reading the
  source, which is AC3 and is the cheapest half of the whole fix.

  *Narrower, rejected:* fix only `_reviewer_dirs` and leave the zero-count reporting alone. The
  directory bug becomes unreachable in this repo, and the guard still cannot distinguish "checked
  nothing" from "found no drift" for every other way that state can arise — an empty lock, a lock
  pinning a path that was renamed, a future candidate directory. The invisibility is the part that
  generalises.

  *Wider, rejected:* auditing every guard in `scripts/` for the same shape in this spec. It is the
  right instinct — #1 exited 0 with a pathspec matching no files, this exits 0 hashing no files —
  but a sweep is not one issue, one branch, one PR. Worth filing after this lands, with this fix
  as the worked example.
- Affected files: `assets/check-locks.py`, `scripts/test-gates.sh`, and both manifests for the
  version bump, since `assets/` is a shipped path.
- **Blast radius:** `--update` is the risk. It rewrites lock files in place, so it must keep
  touching exactly the lock whose hash drifted and no other — AC5 exists for this and is the case
  most worth writing first. CI runs this script on every PR, so a wrong strictness change turns
  every build red; the three-branch table above is deliberately conservative about which state
  fails. Consumer projects run their own copy, and one with a single reviewer directory sees no
  behaviour change at all.
- Why this cannot recur: the fix removes the shared exit path. "Verified nothing" and "found no
  drift" stop being expressible as the same output, so a future defect that empties the scan
  produces a failure rather than a silence.

### A note on where the tests go
The cases go in `scripts/test-gates.sh`, whose header is broadened from "the gates" to "the gates
and guards". A separate `scripts/test-locks.sh` was considered and rejected: it costs a second CI
step, a second entry in the five-command list in `AGENTS.md` and `CONTRIBUTING.md`, and a second
place to look — and this repo's stated preference is fewer moving parts. Renaming the file to match
was also rejected: it churns CI, `AGENTS.md`, `CONTRIBUTING.md`, and `README.md` for a filename.
**This is a judgment call and the reviewer should push back if the broadening reads as scope creep.**

## 3. Tasks (TDD-ordered)
> Folded red-and-green per #10: one task is one complete Red-Green-Refactor cycle, so one green commit.

- [x] T1: failing case — a lock under `.claude/agents/` must not stop `agents/` being verified, and
      a drifted shipped rulebook must still fail with both present — then `_reviewer_dirs` and the
      union loop that make it pass
- [x] T2: failing case — locks exist but zero pinned files verified exits 1 — then the third report
      branch
- [x] T3: failing case — no locks in any candidate directory exits 0 with wording distinct from a
      real verification — then that branch
- [x] T4: blast radius — `--update` re-pins only the drifted lock and leaves locks in other reviewer
      directories byte-identical
- [x] T5: refactor, and confirm no pre-existing case changed verdict by diffing the case list
