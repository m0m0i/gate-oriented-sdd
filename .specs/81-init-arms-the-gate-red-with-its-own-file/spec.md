# Spec: init arms the gate red with its own file
- Slug: 81-init-arms-the-gate-red-with-its-own-file   Issue: 81   Type: bug   Status: done
- Author: m0m0i   Date: 2026-09-25

## 1. Requirements (WHAT / WHY)

- Reproduction: run `init` against a Python project whose `- Validators:` line runs `ruff check` and
  `ruff format --check`, with a common configuration — line length 100, rules `E,F,I,UP,B,SIM,RUF`.
  `init` copies four files from `assets/` into the project's `scripts/` and names two of them on that
  same `- Validators:` line. The next turn ends red on files the user did not write. Observed
  2026-09-05 on #76 against a scratch clone of a real consumer whose tree was green before `init` ran
  (`.specs/_archive/76-run-init-on-a-scratch-clone/observations.md`, step 4).

- Expected: the files `init` installs pass the validators `init` adopts. Step 4.1 of `init` already
  requires this — the gate is meant to arm on a green tree.

- Actual: `init` arms the gate red with its own file. Re-measured 2026-09-25 with
  `ruff --isolated --line-length 100 --select E,F,I,UP,B,SIM,RUF`:

  | File | `ruff check` | `ruff format` |
  | :-- | :-- | :-- |
  | `assets/check-locks.py` | `I001` (l.25), `E501` (l.118, l.123), `UP017` (l.123, `target-version` ≥ py311 only) | reformats |
  | `assets/check-document-set.py` | `E501` (l.359) | reformats |
  | `assets/check-steering-anchors.sh` | clean under `shellcheck -s sh` | — |
  | `assets/check-unreviewed-work.sh` | clean under `shellcheck -s sh` | — |

- Impact: every consumer whose Python lint configuration selects `E` or `I` and runs `ruff format
  --check`, on their first turn after `init` — which is CAP-4's falsifier stated literally, produced
  by the harness rather than by the project. A consumer who reports completion on files written,
  which step 4's first sentence exists to prevent, ships it. The cost is paid at the worst possible
  moment: the user's first turn, before any trust exists.

- **Root cause:** not that these two files are dirty — that is the symptom. `assets/` is the only
  shipped path whose contents are **copied into a consumer's tree and then named on that consumer's
  `- Validators:` line**, so their cleanliness is judged by a toolchain this repository never runs.
  CI here runs thirteen guards and no linter or formatter on any path, so the property that decides
  whether a consumer's first turn is green is unobserved by construction and drifts freely. The
  evidence that this is the mechanism rather than an accident: `assets/check-document-set.py` was
  added on 2026-09-19, two weeks *after* #81 was filed against exactly this class, and arrived with
  its own `E501`. Fixing the two files without closing the observation gap buys one green install and
  the next file reopens it.

- Acceptance criteria:
  - [ ] **AC1:** WHEN `ruff check --isolated --line-length 100 --select E,F,I,UP,B,SIM,RUF` and
        `ruff format --check --isolated --line-length 100` are run over `assets/` THEN both exit 0.
  - [ ] **AC2:** WHEN `shellcheck -s sh` is run over every `*.sh` file under `assets/` THEN it exits 0.
  - [ ] **AC3:** CI fails when any file under `assets/` stops satisfying AC1 or AC2, on pull requests
        and on pushes to `main`, and the failure is reported separately from the guard job so that
        "a lint drift" and "a guard caught a defect" are distinguishable in the checks list.
  - [ ] **AC4:** the CI lint job fails when run against this branch's merge-base tree and passes
        against its tip — demonstrated by running it against both, with the output recorded in the
        pull request body, not asserted.
  - [ ] **AC5:** `assets/check-locks.py` and `assets/check-document-set.py` are behaviourally
        unchanged: same exit status and same stdout on this repository before and after, the
        `generatedAt` string `check-locks.py --update` writes is byte-identical in form, and
        `scripts/test-gates.sh` stays at 163 passed / 0 failed / 0 skipped.
  - [ ] **AC6:** the fix raises no Python floor: AC1 holds at `--target-version` py39, py310, py311
        and py313, so no consumer's interpreter is excluded by it.
  - [ ] **AC7:** `docs/CONTRACT.md`'s G-5 cell and its copy in
        `.claude/agents/gate-sdd-reviewer/rules/gates-and-guards.md` no longer claim there is no
        toolchain to run `shellcheck` with, since AC2 ships one. *Amended at T3: the rulebook's G-5
        carries no such note — the claim lived in `docs/CONTRACT.md` alone — so the rulebook is
        unchanged and this criterion is one cell.*

- Out of scope:
  - **`scripts/`** — 106 findings across 11 files under the same configuration. Never shipped, never
    copied into a consumer's tree, so it cannot arm anyone's gate red. Fixing it here would multiply
    the diff by an order of magnitude for none of the defect. Worth its own issue; not this one.
  - **`hooks/*.sh`** — four `SC2086` findings in `hooks/gate-lib.sh` (l.218, 306, 307, 340) that are
    **deliberate and load-bearing**: `$_globs` is interpolated unquoted because `:(glob)` pathspecs
    must word-split, which `.steering/tech.md` records as the fix for #1. Quoting them would pass one
    argument where git expects several and take the gate with it. Recorded here so that the next
    person to point `shellcheck` at this repository does not "fix" them; if `hooks/` is ever linted,
    those four need suppressing with the reason, which is a separate issue.
  - **Whether `init` should run the adopted validators after step 3** before declaring the gate
    armed. Step 4.1 already says it; making it checkable is the sentence #54 would pin, and #54 is
    its own backlog row.

### Clarifications

Recorded 2026-09-26. Four questions asked, four answered; the fourth was reopened by a measurement
taken while writing the Design, and the reopening is recorded rather than smoothed over.

1. **Which ruff configuration does the guard pin?** — *The observed config:* `--line-length 100
   --select E,F,I,UP,B,SIM,RUF`. It is the configuration that actually reddened a real consumer in
   #76, and it is a superset of ruff's defaults, so clean under it implies clean under anything
   narrower. Accepted cost: a future ruff that adds rules to these families can redden `main`, which
   is what Q3's pin answers.
2. **How is `UP017` handled, given `datetime.UTC` is 3.11+ and this repository declares no minimum
   Python?** — *Answered twice.* First answer was `# noqa: UP017`. That answer was then **withdrawn
   on evidence**: with `RUF` selected, an unused `noqa` trips `RUF100`, so the pragma is clean at
   py311+ and red at py39/py310 — the same defect as #81 wearing a different rule id, relocated
   rather than removed. Final answer: **drop the construct**. `time.strftime("%Y-%m-%dT%H:%M:%SZ",
   time.gmtime())` produces a byte-identical string, passes at py39/py310/py311/py313, is already
   `ruff format` clean, needs no pragma, and leaves nothing for `UP017` to flag. Recorded at length
   because the first option set was the flaw, not the first answer.
3. **Are the tool versions pinned in CI?** — *Pinned:* `ruff==0.16.9`, `shellcheck-py==0.11.0.1`,
   bumped deliberately. An unpinned linter reddens `main` on a day nobody touched the repository,
   and a gate that fails for a reason its operator did not cause is a gate they switch off, which is
   CAP-7 exactly. Accepted cost: the pin drifts from what a consumer installing today gets, and
   somebody has to move it.
4. **Is G-5's stated reason reworded here or filed?** — *Answered by the repository, not asked.*
   G-5's "no toolchain to install it with" note lives in `docs/CONTRACT.md` and in
   `.claude/agents/gate-sdd-reviewer/rules/`, which ADR-6 records as this repository's own
   deliberately unpinned rulebook. No shipped rulebook carries G-5, so no re-pin is triggered and
   the blast radius is two prose cells — a call to make, not a question to spend. Reworded here,
   as AC7.

## 2. Design (HOW)

- Fix approach, and why this rather than the narrower or wider fix:

  **Narrower** would be editing the two files and stopping, which is what the issue's own Fix section
  leads with. Rejected by the root cause: the defect is the absence of observation, and
  `check-document-set.py` already demonstrated that the next file reopens it. **Wider** would be
  linting every path in the repository, which is 106 findings in `scripts/` plus four deliberate
  suppressions in `hooks/`, and buys nothing for the consumer because neither path is copied into
  their tree. The fix is therefore scoped to exactly the shipped-and-copied set — `assets/` — and
  pairs the two edits with the CI job that keeps them true.

  The guard is **CI-only and deliberately not on the `- Validators:` line.** `ruff` and `shellcheck`
  are absent from the author's machine and `.steering/tech.md` opens with "no package manager and no
  build", so a `- Validators:` entry would fail on the developing machine rather than in CI — and a
  turn-end gate that cannot run locally is #195's shape, a validator that reports on a toolchain it
  never found. Same conclusion as `check-version-bump.py` and `check-unreviewed-work.sh`, reached for
  a third distinct reason, so it is written down beside theirs in `.steering/tech.md`.

  It is also **a separate `lint` job rather than steps appended to `guard`**, which is AC3: a red
  check named "Assets are clean under a consumer's linter" says what drifted, where a fourteenth step
  inside "Guards, locks, and gate behaviour" says only that something did.

  `--isolated` is load-bearing. There is no `pyproject.toml` in this repository today, so ruff would
  fall back to its defaults plus these flags either way — but a `pyproject.toml` added later would be
  picked up silently and could widen or narrow what the guard asserts without anyone editing the
  guard. That is a configuration reaching into a gate from outside, which is the family this
  repository exists to refuse.

  `--target-version` is deliberately **not** pinned to one value. `UP017` was the only
  target-version-sensitive finding in the tree and the Q2 answer removes it, so the guard is
  version-independent by construction — and AC6 asserts that rather than assuming it, by running the
  check at both ends of the plausible range. Pinning a single value would narrow the claim to one
  interpreter for no gain.

- Affected files:
  - `assets/check-locks.py` — sort the import block (`I001`); replace `import datetime` with
    `import time`, since l.123 is `datetime`'s only use in the file; rewrite l.123 as
    `time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())`; wrap l.118 under 100 columns; apply
    `ruff format`.
  - `assets/check-document-set.py` — wrap l.359 under 100 columns; apply `ruff format` (two
    reflows: a blank line after the module docstring, and one call unwrapped onto a single line).
  - `.github/workflows/ci.yml` — a new `lint` job: pinned `ruff` and `shellcheck-py`, then
    `ruff check`, `ruff format --check`, and `shellcheck -s sh assets/*.sh`, each with the comment
    this file's steps all carry explaining what it caught and why it exists.
  - `.steering/tech.md` — a fourth "why this is not on the `- Validators:` line" section, beside the
    three that exist (the spec said third; the file already held three).
  - `docs/CONTRACT.md` (G-5's note) and
    `.claude/agents/gate-sdd-reviewer/rules/gates-and-guards.md` (its copy) — AC7.
  - `docs/verified.md` — record what is now checked mechanically and what still is not.

- **Blast radius:**
  - `assets/check-locks.py` is on the `- Validators:` line here and in every consumer's CI, and
    `--update` rewrites `generatedAt` in six lock files. The timestamp's *form* must not move: a
    changed format would re-pin every lock with a value the schema readers did not expect. Guarded by
    AC5, which compares the string form rather than trusting that two UTC clocks agree.
  - `assets/check-document-set.py` is one of the thirteen validators and runs on every turn end here.
    Its edits are a line wrap and a formatter reflow with no expression changed, so the risk is a
    mis-wrapped f-string changing a message the document-set tests read.
  - The `lint` job adds a required check to every pull request. If `ruff` or `shellcheck-py` cannot
    install, the job fails and blocks — fail-shut, which is the correct direction for this repository
    and is stated rather than discovered.
  - Nothing here touches `hooks/`, so no gate logic changes and `test-gates.sh` should not move.

- Why this cannot recur: the class is "a file copied into a consumer's tree is judged by a toolchain
  this repository never runs." The `lint` job runs that toolchain over the whole of `assets/` rather
  than over the two files named in the issue, so a file added to `assets/` tomorrow is covered on the
  day it lands — which is the specific way `check-document-set.py` escaped in September. What remains
  uncovered, and is recorded rather than implied: a consumer selecting rules outside
  `E,F,I,UP,B,SIM,RUF`, or a `ruff` newer than the pin, can still find something this guard does not.
  The guard narrows the window; it does not close it, and `docs/verified.md` says so.

## 3. Tasks (TDD-ordered)
> One task is one complete Red-Green-Refactor cycle, so one green commit. No task is sequenced after the review.

- [x] T1: the two files — record the four `ruff check` findings and the two `ruff format` diffs
      against the current tree as the red, then sort the imports, swap `datetime` for `time.gmtime`,
      wrap the three long lines and apply the formatter, until `ruff check`, `ruff format --check`
      and `shellcheck -s sh` are all clean over `assets/`. Ends green on AC1, AC2 and AC6, with AC5
      checked by running both scripts before and after and diffing their output.
- [x] T2: the `lint` job — add it to `.github/workflows/ci.yml` with both versions pinned, and prove
      it is not decorative by running the same three commands against the merge-base tree in a
      detached worktree (red on the four findings) and against the tip (green). Ends green on AC3
      and AC4 with the transcript captured for the pull request body.
- [x] T3: reconcile the prose the first two tasks made false — the third `- Validators:` exclusion in
      `.steering/tech.md`, G-5's note in `docs/CONTRACT.md` and its copy in the reviewer's rulebook
      (AC7), and `docs/verified.md`'s record of what is now mechanical and what is not. Ends green on
      the full thirteen-validator run plus `test-gates.sh`.

**After the review, as steps of `implement` rather than tasks:** the version bump — `assets/` is a
shipped path, and this is shipped-code content with no flow change, so 0.21.0 → **0.21.1** — then the
work-log entry and the `Status: done` flip.
