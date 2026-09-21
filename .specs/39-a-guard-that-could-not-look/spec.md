# Spec: A guard that could not look does not report that it looked
- Slug: 39-a-guard-that-could-not-look   Issue: 39   Type: bug   Status: done
- Author: m0m0i   Date: 2026-09-21

## 1. Requirements (WHAT / WHY)

- Reproduction: the sharpest of four, and the only one inside a gate.

  ```sh
  chmod 000 .steering/tech.md
  sh hooks/quality-gate.sh; echo $?     # -> {}  0
  ```

  The other three, each reachable the same way:

  ```sh
  mv hooks/templates/antigravity.hooks.json /tmp/ && ./scripts/check-manifests.py
  #   -> check-manifests: both manifests agree            (comparison never ran)
  ./scripts/check-leakage.sh
  #   -> check-leakage: clean                             (no count of what was read)
  chmod 000 .steering/tech.md && ./assets/check-steering-anchors.sh
  #   -> the same unreadable-file block, six times        (once per anchor row)
  chmod 000 .steering && ./assets/check-steering-anchors.sh
  #   -> no steering files found — nothing was checked    (it could not reach them)
  ```

- Expected: a check that could not read its subject says so and fails. `.steering/product.md` carries `- Owns: gates never fail open`, and grades this exact shape: *"one that makes a gate silently stop checking is a BLOCKER."*
- Actual: all four report success, in the sentence they print for a real pass, on the same exit code.
- Impact: AC1 is the one that matters — `quality-gate.sh` is the bottom row of the harness's table and the only row `.steering/tech.md` calls a guarantee. On an unreadable `tech.md` it exits 0 having run no validator, and the failure is indistinguishable from a clean turn, so it survives as long as it takes to matter. The other three are guards this repository runs on itself; `AGENTS.md` names `check-leakage.sh` the one that matters most, and it is the one with no count.
- **Root cause:** `hooks/gate-lib.sh` carries two readers with opposite contracts. `_gate_read` returns 1 for absent and 2 for unreadable — added during #26's review for exactly this reason, and its own comment says collapsing them "would make 'I could not check' indistinguishable from 'I checked'". `gate_steering_value` predates it, is `sed ... 2>/dev/null | head -1`, and returns the empty string for both. Every caller inherits a state it cannot recover, and then each re-derives *nothing found* as *nothing wrong* in its own words: `quality-gate.sh` reaches `[ -n "$validators" ] || gate_pass`; `assets/check-steering-anchors.sh` recovers the distinction by hand with its own `[ ! -r ]` test, which proves it is recoverable and that the library is the wrong place to have lost it. The two repo-local guards are the same class by a different mechanism: `scripts/check-manifests.py:68` gates the whole hook-template comparison on `is_file() and is_file()` and falls through to the success line, and `scripts/check-leakage.sh` prints `clean` with nothing to distinguish a scanned tree from an empty `files()`, over three scans whose `2>/dev/null` also discards every per-file read error.
- Acceptance criteria:
  - [x] **AC1:** WHEN `.steering/tech.md` exists and cannot be read THE quality gate SHALL block the turn naming that file, rather than exiting 0.
  - [x] **AC2:** WHEN a steering file is absent, and WHEN it exists and cannot be read, THE reader in `hooks/gate-lib.sh` SHALL report those as distinct states to its caller.
  - [x] **AC3:** WHEN either hook template is absent or unreadable THE `check-manifests.py` SHALL exit non-zero, and SHALL NOT print `check-manifests: both manifests agree`.
  - [x] **AC4:** WHEN `check-leakage.sh` finds no hit THE SYSTEM SHALL report how many files it scanned, and SHALL exit non-zero when that count is zero.
  - [x] **AC5:** WHEN a file in `check-leakage.sh`'s work-set is **present** and cannot be read, or cannot be handed to `grep` as a path, THE SYSTEM SHALL exit non-zero naming that file, rather than scanning around it. WHEN an entry in the work-set has no working-tree file THE SYSTEM SHALL report it as a count, not a failure. _Narrowed in review round 2 — see Clarifications Q5._
  - [x] **AC6:** WHEN a steering file exists and cannot be read THE `check-steering-anchors.sh` SHALL report it once per file, not once per anchor row.
  - [x] **AC7:** WHEN `.steering/` exists and cannot be traversed THE `check-steering-anchors.sh` SHALL NOT report `no steering files found — nothing was checked`.
  - [x] **AC8:** each of AC1 and AC3–AC7 has a case in `scripts/test-gates.sh` that fails before its fix and passes after; where `chmod 000` is ineffective the case self-disables through `note_skip`, never `report … ok`.
- Out of scope — adjacent, and every one of them is already filed or is recorded here as a deliberate deferral:
  - **The `report` third state**, #39's own lead item. Superseded: `note_skip()` and a printed `skipped` count landed with #127 across thirteen sites, and the two cases that called `report … ok` on a skip path no longer do.
  - **`test-gates.sh` case 14's behaviour under root.** See Clarifications Q3 — the case is correct as written and the backlog cell is not.
  - **`test-gates.sh` case 30's drift detector** — counting `gate_steering_value` call sites against extracted rows. Detector integrity, not subject readability.
  - **`test-gates.sh` case 35** — its literal three-directory work-set (G-8) and its structurally unexercisable `rc -eq 2` branch. #39's own comment calls the fix a refactor rather than a bug fix: the case has to take its work-set as a parameter first.
  - **`. "$DIR/gate-lib.sh"` on a missing file**, which aborts the shell with no `{"decision":"continue"}` on stdout — silently advisory on Antigravity. Filed as #194; see Clarifications Q2.
  - **`hooks/steering-digest.sh`'s double blank line**, #39's last loose end.
  - **Red-capable cases for `check-receipt-schema.py` and `check-skill-contracts.py`.**
  - **#178, #176, #191 and #179** — the rest of backlog row 1. Same row, separate branches.

### Clarifications

Asked and answered 2026-09-21.

- **Q1 — `gate_steering_value` collapses absent and unreadable into the empty string. Change the contract, add a sibling, or leave each caller to test `-r`?**
  **A: add a sibling reader in `gate-lib.sh` that returns 1 absent / 2 unreadable, matching `_gate_read`; `gate_steering_value` keeps its signature as a thin wrapper, and only the callers that must distinguish opt in.** One definition, so there is nothing for a second site to disagree with (#14, #23), and `review-gate.sh`, `steering-digest.sh`, `gate_spec_review_state` and `gate_work_reached_base` keep their current read path byte for byte — which matters, because #182 found five fail-opens in the last of those and this branch should not reopen it.
- **Q2 — is the `. "$DIR/gate-lib.sh"`-on-a-missing-file fail-open in this spec?**
  **A: no. File it as its own issue.** It is the library-absent axis rather than the subject-unreadable one, and its fix shape differs from every criterion here: it needs a guard *before* the source line, in both gates, with no library available to speak through. #39 records that `assets/check-locks.py` already handles the condition (its AC7, case 25) and the gates do not, which is the asymmetry worth closing — separately.
- **Q3 — `test-gates.sh` case 14 goes red under root instead of skipping. `scripts/test-gates.sh:44-48` says that is deliberate and says not to fix it; `docs/BACKLOG.md` row 1 calls it "one more instance" of this issue.**
  **A: the code comment is right and the backlog cell is wrong.** A loud failure under root is the safe direction, and converting it would trade that for a quiet skip. T5 corrects the cell rather than the case.
- **Q4 — `check-leakage.sh`'s three scans run through `xargs grep … 2>/dev/null`, so a file it cannot read is silently not scanned. Fold that in with AC4's count?**
  **A: yes — AC5.** Same guard, same axis, and a count of files scanned still cannot tell you that three of them were never read. `AGENTS.md` calls this the guard that matters most.

- **Q5 — review round 2 narrowed AC5, and the finding was this issue's own subject one level down.**
  AC5 originally said "a file in the work-set cannot be read". `files()` reads `git ls-files --cached`, which lists
  **index entries** and filters on neither existence nor `skip-worktree` — so a tracked path that is not on disk (an
  unstaged `rm`, a sparse checkout, a partial worktree) reached `[ -r "$f" ]`, which is false for a file that is not
  there, and the guard blocked the turn saying *"could not be read … fix the permissions"* about it. `check-leakage.sh`
  is the first entry on `- Validators:`, so that is every turn, on a wrong diagnosis. **The criterion licensed it**:
  absent and unreadable are different states, which is the whole of this spec, and AC5 had fused them in the one place
  the spec did not look. Amended rather than worked around, per C-8 — an absent entry is counted and reported, never
  failed, because "I scanned round three index entries" is exactly what must not hide inside `clean`. **C-8 was broken doing it**, and is recorded rather than rebased away: the amendment landed in `6605fd3` together with `scripts/check-leakage.sh` and `scripts/test-gates.sh`, the artifacts AC5 and AC8 name, so AC5's tick is not independent evidence. That commit's message claimed the opposite; `7d56992` corrects it.

## 2. Design (HOW)

- **Fix approach, and why this rather than the narrower or wider fix.** One new reader in `hooks/gate-lib.sh` — `gate_steering_read <file> <key>`, returning 1 for an absent file and 2 for a present one it cannot read, with `gate_steering_value` reimplemented over it so the two can never diverge. Two callers opt in. The narrower fix is a `[ -r ]` test in `quality-gate.sh`, which leaves the library still unable to state the difference and adds a third hand-rolled copy of it; the wider fix changes `gate_steering_value`'s own contract and rewrites six read sites, two of them inside `gate_work_reached_base`, which #182 left stable eight days ago at the cost of seven review rounds. The three non-gate guards are independent one-file fixes on the same axis and are not routed through the library — `check-manifests.py` is Python, and `check-leakage.sh` reads a work-set rather than an anchor.
- **Affected files:**
  - `hooks/gate-lib.sh` — the new reader (AC2). **Shipped.**
  - `hooks/quality-gate.sh` — opts in; unreadable `tech.md` becomes `gate_block` (AC1). **Shipped.**
  - `assets/check-steering-anchors.sh` — opts in, replacing its hand-rolled `[ ! -r ]`; the unreadable-file report collapses to once per file; an unreachable `.steering/` stops being reported as "not found" (AC6, AC7). **Shipped.**
  - `scripts/check-manifests.py` — the `is_file() and is_file()` guard becomes an error (AC3). Repo-local.
  - `scripts/check-leakage.sh` — a scanned count, a zero-count failure, and a read failure (AC4, AC5). Repo-local.
  - `scripts/test-gates.sh` — six cases (AC8). Repo-local.
  - `docs/BACKLOG.md` — row 1's case-14 sentence corrected; the Q2 issue recorded under `## Open, not planned` so `check-backlog-tracker.py` does not redden this branch's own pull request. Not shipped.
  - `plugin.json`, `.claude-plugin/plugin.json` — `hooks/` and `assets/` are on `- Source globs:`, so `check-version-bump.py` requires a bump off 0.19.0. A gate that now blocks where it passed is a behaviour change, so minor: **0.20.0**. This lands as a **step of `implement`**, after the review, never as a task (#113).
- **Blast radius:** `gate_steering_value` has six call sites — `quality-gate.sh`, `review-gate.sh`, `steering-digest.sh`, `gate_spec_review_state`, `gate_work_reached_base`, and `check-steering-anchors.sh`. Reimplementing it over the new reader touches all six by construction, so the criterion that protects them is that its stdout stays identical for both existing states: a value when there is one, empty when there is not. The one behavioural widening is deliberate and is AC1 — a project whose `tech.md` is present and unreadable now has every turn blocked, where before it had none. That is G-6 in the direction the anchor names, and `[ -f .steering/tech.md ] || gate_pass` still passes a project with no steering file at all, which the harness supports. AC7 changes a message rather than an exit code; `check-steering-anchors.sh` is on the `- Validators:` line, so a wrong widening there blocks every turn in every install.
- **Why this cannot recur:** the distinction becomes a property of the library rather than of each caller. A new site reading a steering anchor gets absent-versus-unreadable from `gate_steering_read` without knowing it needed to ask, which is the same argument that put `gate_steering_value` in `gate-lib.sh` in the first place (#14, #23) — the guard here is that there is one definition to be wrong in, not six. What this does **not** give is a check that a guard never prints success on a path where it read nothing; that would need the work-set parameterisation #39 records against case 35, and is named out of scope above.

## 4. Accepted, not fixed

Findings the reviewer raised below HIGH and this branch did not act on, each with the reason. Recorded here rather
than dropped, so none of them is a silent deferral.

- **`scripts/check-manifests.py:40` — `if cc and agy:` is a truthiness test.** A `plugin.json` holding `null` or `{}`
  skips every manifest comparison with nothing recorded, and the guard prints `both manifests agree` on exit 0. It is
  the same lesson AC3's fix writes down one block below, and it is pre-existing and outside AC3, which is scoped to
  the two hook templates. Left because widening it is a second guard's worth of decision about what an empty manifest
  means, not a line.
- **`scripts/check-leakage.sh` — a directory that cannot be searched and holds no *tracked* file never enters the
  work-set.** `git ls-files --others` cannot traverse it; the `find` branch skips it with a stderr line nothing reads.
  AC4 and AC5 are both framed over the work-set, so this sits outside them by construction, and it is unchanged from
  `main`. It is the same family as #194 and #195 — a guard that cannot see what it cannot reach.
- **`scripts/check-leakage.sh` — a work-set entry that is a directory in the working tree** (a submodule gitlink, or a
  tracked file replaced by a directory) passes `[ -e ]` and `[ -r ]`, is counted, and is then skipped by `grep` with
  "Is a directory" into the discarded stderr. Counted-but-not-read, the same class as the dash and spaced paths.
  Not live here — this repository has no submodules — and pre-existing.
- **A path holding a newline, in a non-git tree.** `find` does not quote it, so it splits across the line-delimited
  list and is counted twice. The fix is a NUL-safe reader, which POSIX `sh` has no portable form of; the git branch
  catches its own case through `unscannable`. Stated in the code at the classification loop.
- **`hooks/quality-gate.sh` — an unreachable `.steering/` reads as absent and the gate passes.** Filed as #195 and
  recorded in `docs/BACKLOG.md` under `## Open, not planned`, beside #194. Unchanged from `main`, and AC7 scopes the
  directory case to `assets/check-steering-anchors.sh` deliberately.

**Review rounds: four.** Three of them found a defect this branch's own previous fix had introduced, all four in
`scripts/check-leakage.sh` — the quotePath block came out of T4's fix, the `--cached` block out of that one's, and the
dead `unscannable` arm out of the one after. That is #182's pattern repeating in a second file, and it is the sharpest
evidence #39 has: the guards that report success they did not earn are written, repeatedly, by people trying not to
write them. Recorded here because the issue is the argument for the rule, and this branch is now a witness to it.

## 3. Tasks (TDD-ordered)

> One task is one complete Red-Green-Refactor cycle, so one green commit. No task is sequenced after the review.

- [x] T1: case that `quality-gate.sh` exits 0 with `{}` on a present-but-unreadable `.steering/tech.md` — then `gate_steering_read` in `hooks/gate-lib.sh`, `gate_steering_value` reimplemented over it, and `quality-gate.sh` opting in. (AC1, AC2, AC8)
- [x] T2: cases that `check-steering-anchors.sh` repeats its unreadable-file block once per anchor row, and calls an unreachable `.steering/` "no steering files found" — then the asset opting in to `gate_steering_read`, reporting once per file, and separating unreachable from absent. (AC6, AC7, AC8)
- [x] T3: case that `check-manifests.py` prints `both manifests agree` with a hook template moved away — then the fix. (AC3, AC8)
- [x] T4: cases that `check-leakage.sh` prints `clean` over an empty work-set and over a file it cannot read — then the scanned count, the zero-count failure, and the read failure. (AC4, AC5, AC8)
- [x] T5: correct `docs/BACKLOG.md` row 1's case-14 sentence per Q3, file the Q2 issue, and record it under `## Open, not planned`.
