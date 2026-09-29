# Spec: a case under each deliberate word-split, then its suppression
- Slug: 207-a-case-under-each-word-split   Issue: 207   Type: chore   Status: approved
- Author: m0m0i   Date: 2026-09-29

## 1. Requirements (WHAT / WHY)

- What changes: five `shellcheck` findings in the shipped hooks are suppressed at their line, with
  the reason beside the directive — the four `SC2086`s in `hooks/gate-lib.sh` (l.218, 306, 307,
  340: `$_globs` in the review gate's freshness check, `$_wglobs` three times in the
  unreviewed-work skip) and the `SC2046` at `hooks/quality-gate.sh:106`, the quality gate's own
  `set -- $(…)`, which is the same deliberate word-split one hook over and which #207 does not
  count. Before any directive lands, `scripts/test-gates.sh` gains a case per line that goes red
  when that line's expansion is quoted. The three places that give "four deliberate `SC2086`s" as
  the reason `hooks/` is read rather than linted are corrected to the reason that is true after
  this change.

- **What must NOT change:** the five command lines are byte-identical — the directive is the
  comment above, never a quote on the line. A `- Source globs:` line of several `:(glob)` patterns
  still reaches git as one pathspec per pattern in all five readers. Every case in
  `scripts/test-gates.sh` keeps passing. The `lint` job's steps are unchanged, so its subject stays
  `assets/`.

- Why now: G-4 says every gate behaviour has a case that can fail, and these five lines have none.
  Measured on 2026-09-27 (`.work_logs/2026-09-27.md`) and again on 2026-09-29: with all four
  `gate-lib.sh` expansions quoted, `test-gates.sh` stays at 163 passed / 0 failed / 0 skipped,
  because every fixture's `- Source globs:` line holds one glob. On a line of several — this
  repository's own has nine — the quoted form hands git one pattern that matches nothing,
  `gate-lib.sh:220` returns empty, and `review-gate.sh` reads no `stale=` as fresh: the gate passes
  silently, the direction `- Owns:` forbids. The guard sweep (backlog row 2; #195, #198 and #199
  name this file) is about to edit it, and the sweep's own witness, #182, is fixes that introduced
  fail-opens. **Narrowed from the issue on 2026-09-29.** Under the pinned
  `shellcheck-py==0.11.0.1`, `shellcheck -s sh hooks/*.sh` reports fifteen findings, not the four
  the issue counts: the five above, plus `SC1007` ×4 (the `CDPATH= cd` idiom), `SC1091` ×3 (the
  sourced library is not followed) and `SC2164` ×3 (`cd "$repo_root"` with nothing after it) in
  the four entry hooks. The `SC2164`s are the sweep's own class — a gate that carries on in the
  wrong directory has checked nothing — so `hooks/*.sh` cannot join the `lint` step until the
  sweep has decided them. The backlog's falsifier for row 1 fired on that count; the user chose to
  keep the case and the five suppressions here and defer the step.

- Acceptance criteria:
  - [ ] **AC1:** `scripts/test-gates.sh` holds, for each of the five lines, a case whose fixture's
        `- Source globs:` line carries two or more `:(glob)` patterns and whose changed path
        matches only a later one, and that case fails when that line's expansion alone is quoted,
        every other hook line as shipped. Demonstrated by quoting each line one at a time in a
        scratch clone and recording on this spec which cases went red and that the rest stayed
        green.
  - [ ] **AC2:** the cases of AC1 pass on the unmodified hooks before any directive is added, and
        pass unchanged after — the baseline, then the change.
  - [ ] **AC3:** WHEN `shellcheck -s sh --include=SC2086,SC2046 hooks/*.sh` is run under
        `shellcheck-py==0.11.0.1` THEN it exits 0 and reports nothing, where at the branch's
        merge-base it reports exactly those five findings; both outputs are recorded on this spec.
  - [ ] **AC4:** each directive sits on its own line immediately above the command it covers,
        names one code, and carries the reason; `git diff main` on the five hook lines is empty.
  - [ ] **AC5:** `scripts/test-gates.sh` reports 0 failed and 0 skipped, and its passed count has
        risen by exactly the number of cases AC1 added.
  - [ ] **AC6:** `.steering/tech.md`'s lint section, `docs/CONTRACT.md`'s G-5 cell, and the
        `lint` job's shellcheck comment in `.github/workflows/ci.yml` no longer name the four
        `SC2086`s as the reason `hooks/` is unlinted, and the comment no longer says
        `gate-lib.sh` is "never copied anywhere" — `skills/init/SKILL.md` copies all five hooks
        into every project. The remaining reason is stated once, in `tech.md`, and the other two
        cite it.

- Out of scope: `hooks/*.sh` in the `lint` step — the follow-up, filed after merge; the ten
  findings outside these five lines (`SC1007` and `SC1091` are spelling and tooling, `SC2164` is
  row 2's); `hooks/templates/`, which holds two JSON files and a README and nothing `shellcheck`
  reads, so the issue's question about it is moot; `docs/BACKLOG.md` row 1, which now overshoots
  this spec and is the next grooming's to reconcile.

### Clarifications
2026-09-29, three questions, each answered with the recommended option.

- **Q1 — one case per line, or fewer?** Recommended and taken: five new cases, each a multi-glob
  copy of the sibling that already exercises its path, so AC1 holds line by line. Rejected:
  changing `make_repo`'s default `- Source globs:` line, which would pin the split across the
  suite but re-derive the meaning of a hundred fixtures in a diff nobody could read; and two cases
  only, under which quoting l.306 or l.307 alone stays green because the other half of the union
  still catches the carry-on.
- **Q2 — correct the three "four deliberate `SC2086`s" statements here or in the follow-up?**
  Recommended and taken: here, as AC6. The reason they give is false the moment T2 lands, and
  `main` should not carry a false reason between two issues.
- **Q3 — how is the narrowing recorded on the tracker?** Recommended and taken: one comment on
  #207 when the pull request opens — the fifteen-finding measurement, the narrowing, this spec,
  and the follow-up to be filed after merge. The issue's body and title stay as filed.

## 2. Design (HOW)

- Approach, in the order the tasks land: the cases first, on the hooks as shipped, so the
  baseline is observed rather than asserted; then one line quoted at a time in a scratch clone, so
  each directive's reason can name the case that goes red; then the five directives; then the
  three statements. Nothing in `.github/workflows/ci.yml` outside a comment moves.

- The five cases, numbered on from 159. Each takes its shape from a sibling that already drives
  the path and differs from it in one way: a `- Source globs:` line of two `:(glob)` patterns,
  `:(glob)docs/*.md :(glob)src/*.txt` (root-level `:(glob)*.txt` for the quality gate, whose
  fixture keeps its files at the root), where the path the fixture changes matches only the
  second. Quoted, the whole line is one pathspec whose pattern is `docs/*.md :(glob)src/*.txt`,
  and git matches nothing. Each case also carries a control — a docs-only change under the same
  line stays silent — because `gate-lib.sh:215` falls back to `*` when the line reads empty and
  `quality-gate.sh` runs every validator when it does, and under either fallback the blocking half
  passes for the wrong reason.

  | Case | Pins | Sibling | Shape | Expected red when that line alone is quoted |
  | :-- | :-- | :-- | :-- | :-- |
  | 160 | `gate-lib.sh:218`, `$_globs` | 7 | CLEAN receipt at HEAD, a `NOTES.md` commit stays silent, then a commit to `src/main.txt` blocks as stale and names the file | 218 |
  | 161 | `gate-lib.sh:340`, `_wnow` | 134 | squash-merge `12-parked`, carry on in `src/main.txt`: blocks standing on it and from `main`, naming it | 340 |
  | 162 | `gate-lib.sh:306`, `_wlog` | 142 | add `src/a.txt`, squash-merge, `git rm` it on the branch: blocks | 306; also 340 |
  | 163 | `gate-lib.sh:307`, `_wnet` | 143 | a fixup to `src/b.txt` inside a merge commit: blocks | 307; also 340 |
  | 164 | `quality-gate.sh:106`, `set --` | the `qg-src` case | a dirty `NOTES.md` stays silent; a dirty `src.txt` blocks and the validator's `RAN` reaches stderr | 106 |

  Why 306 and 307 need shapes of their own: `_wlog` and `_wnet` are complements by design
  (`gate-lib.sh:289-304`), so quoting either alone leaves the other to catch case 161's carry-on.
  A revert is visible only to the log and a merge-commit fixup only to the diff, which is what
  cases 142 and 143 already show; a multi-glob copy of each is what makes one quote on 306 or on
  307 observable. The last column is the prediction; the mutation record below is the measurement.

- The directives. One line above each command, one code, and a reason that points rather than
  re-explains — the comments at `gate-lib.sh:204-213` and `quality-gate.sh:102-105` already carry
  the mechanism:

  ```sh
  # shellcheck disable=SC2086  # $_globs word-splits on purpose, one :(glob) pathspec per argument (#1); quote it and case 160 goes red
  ```

  Verified with the pinned tool on 2026-09-29: `shellcheck-py==0.11.0.1` accepts a trailing
  `# reason` after `disable=` and suppresses the finding.

- The three statements (AC6). `.steering/tech.md`'s "Why the `lint` job is not on the Validators
  line" carries the reason once: `hooks/` is copied by `init` into every project; its five
  deliberate word-splits are suppressed at the line and pinned by cases 160-164; ten findings
  remain in the four entry hooks — `SC1007` ×4, `SC1091` ×3, `SC2164` ×3 — and the `SC2164`s are
  row 2's class, so the step takes `hooks/*.sh` in the follow-up. `docs/CONTRACT.md`'s G-5 cell and
  the step's comment in `ci.yml` cite that section in one clause each.

- Affected files: `scripts/test-gates.sh` (five cases), `hooks/gate-lib.sh` (four comment lines),
  `hooks/quality-gate.sh` (one comment line), `.steering/tech.md`, `docs/CONTRACT.md`,
  `.github/workflows/ci.yml` (comment only), this spec. `plugin.json` and
  `.claude-plugin/plugin.json` move by a patch as a step of `implement` after the receipt, not as a
  task — `.steering/tech.md` says why, and `scripts/check-templates.py` fails a spec that writes
  it as one.

- **Coverage gap:** the five lines themselves; T1 is that gap closed. `hooks/templates/` holds
  `antigravity.hooks.json`, `claude-code.settings.json` and a `README.md` — nothing `shellcheck -s
  sh` can read — so the issue's question about linting it has no subject. Recorded; nothing to do.

- Rollback: revert the squash commit. Comment lines and test cases only; no gate logic moves, and
  the version bump goes with it.

### Mutation record
Measured 2026-09-29 in T1, on the hooks as shipped at `eca84d6` with cases 160-164 present. Each
row is one clone of the branch with that line alone quoted; the suite is 168 passed / 0 failed /
0 skipped unmutated (163 at the merge-base, AC2 and AC5).

| Quoted | Cases red | Suite |
| :-- | :-- | :-- |
| `gate-lib.sh:218`, `$_globs` | 160 | 167 / 1 / 0 |
| `gate-lib.sh:306`, `_wlog` | 162 | 167 / 1 / 0 |
| `gate-lib.sh:307`, `_wnet` | 163 | 167 / 1 / 0 |
| `gate-lib.sh:340`, `_wnow` | 160, 161, 162, 163 | 164 / 4 / 0 |
| `quality-gate.sh:106`, `set --` | 164 | 167 / 1 / 0 |
| `306` and `307` together | 160, 161, 162, 163 | 164 / 4 / 0 |
| all four `gate-lib.sh` lines | 160, 161, 162, 163 | 164 / 4 / 0 |

Every existing case stayed green in every row, so a quote on any of the five lines is now caught
by a case that names it and by nothing else. One row corrects the prediction above: the table
said 160 goes red under 218 only, and it also goes red under 340, the pair, and all four. That is
not the freshness check: `make_repo` commits its spec on `main` at init, so on the current-branch
path the skip runs before the freshness check (case 133's route), and a skip that returns 0 —
empty `_wnow`, or an empty footprint — silences the branch before `$_globs` is ever expanded.
Case 160 is red there because the same fail-open reaches it from the other side, which is
consistent with case 134's blast-radius note. 306 alone and 307 alone each red exactly one case,
as predicted: the pair are complements, and only the revert and the merge-commit fixup are visible
to one of them alone.

`shellcheck -s sh --include=SC2086,SC2046 hooks/*.sh` at the merge-base and at the tip (AC3):
filled by T2.

## 3. Tasks (TDD-ordered)
- [x] T1: cases 160-164 in `scripts/test-gates.sh`, each with its control; run the suite on the
      hooks as shipped and record the count (AC2, AC5); then quote each of the five lines alone
      in a scratch clone and fill the mutation record (AC1). Ends green on the shipped hooks.
- [ ] T2: the five directives (AC4); `shellcheck -s sh --include=SC2086,SC2046 hooks/*.sh` before
      and after, both recorded (AC3); the suite rerun (AC2, AC5).
- [ ] T3: the three statements (AC6).
