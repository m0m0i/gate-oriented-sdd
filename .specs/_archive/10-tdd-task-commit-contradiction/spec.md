# Spec: the TDD task/commit rule contradicts the quality gate
- Slug: 10-tdd-task-commit-contradiction   Issue: 10   Type: bug   Status: archived
- Author: m0m0i   Date: 2026-08-23   Archived: 2026-08-26

## 1. Requirements (WHAT / WHY)
- Reproduction: author a spec from the feature or bug template. Both split the pair across tasks — `T1: write the failing test for ...` / `T2: implement ... to make it pass`. Apply `implement`'s rule *"One task, one commit. No batching, no half-tasks."* literally, and end the turn after T1. `quality-gate.sh` runs the `Validators:` line and blocks, because the tests fail.
- Expected: the prescribed workflow can be followed literally without tripping the harness's own gate.
- Actual: it cannot. The only way forward is to ignore "one task, one commit", with no sanction and no guidance saying so.
- Impact: every TDD pair in every feature and bug spec, so several times per implementation. The chore template is unaffected — its T1/T2 are green by construction. Sharper since `quality-gate.sh` shipped in 0.2.3: before it, nothing ran the tests on turn end and the contradiction was theoretical. A rule that must be quietly broken to make progress erodes the rules next to it.
- **Root cause:** the two documents disagree about what a *task* is. `implement`'s loop is defined per task as Red → Green → Refactor → tick → one commit, which makes a task a **complete** cycle. The feature and bug templates split Red and Green into separate tasks, which makes a task **half** a cycle. Applying the loop to `T1: write the failing test` asks for a failing test for the writing of a failing test. The gate collision is a symptom of that disagreement, not its cause — and note `quality-gate.sh` never inspects commits, so a red *commit* is not what blocks; a turn that *ends* red is.
- Acceptance criteria:
  - [x] **AC1:** following the templates and `implement`'s rules literally SHALL NOT produce a turn that ends with failing validators.
  - [x] **AC2:** `implement` SHALL state the resolution explicitly, rather than leaving each user to rediscover it.
  - [x] **AC3:** the feature and bug templates and `implement`'s loop SHALL agree on what one task is.
  - [x] **AC4:** a check SHALL fail when a shipped task template contains a task that is only a red step, so the split cannot quietly return.
  - [x] **AC5:** the regression test fails before the fix and passes after.
  - [x] **AC6:** every behaviour of `check-templates.py` SHALL be pinned by cases in `scripts/test-gates.sh`: that it flags a split feature or bug `T1`, that it does NOT flag the chore template, and that it FAILS rather than passes when `templates.md` is missing or unreadable. *Added 2026-08-26.* `.steering/structure.md` makes that file the project's whole notion of test coverage, and a new guard with no case there is #39's family — the shape this repo has now shipped four times, twice inside #28's own review.
  - [x] **AC7:** `check-templates.py` SHALL appear on `.steering/tech.md`'s `- Validators:` line as well as in CI, and every place that states how many validators there are SHALL agree with the new count. *Added 2026-08-26.* The quality gate executes that line at turn end; a guard absent from it runs only in CI, which is the half of the enforcement this repo does not control. `AGENTS.md`:40 currently reads "Run all eight before every commit — CI runs the same eight".
  - [x] **AC8:** `skills/spec/SKILL.md`'s "The first task is always" table SHALL agree with the folded templates. *Added 2026-08-26.* It is a third statement of the thing AC3 is about, and once the templates fold it becomes the outlier — "a failing test for the new behavior" is no longer what the first task is.
- Out of scope: the chore template, which does not have a red step; #8 and #9. Also out of scope: rewriting the six specs already carrying a hand-written `> Folded red-and-green per #10` note. They are correct as written and four of them are archived; the templates are copied at authoring time, so nothing reads them again.

### Clarifications
- **Q: the templates and `implement`'s loop disagree on what a task is — which gives way?** A: the templates. `implement`'s loop already defines a task as a complete Red-Green-Refactor cycle, so the templates are the outlier and the loop needs no edit. Folding the pair makes one task genuinely one green commit. Accepted cost: the Red step stops being its own line in the written plan.
- **Q: redefine the rule instead (a red/green pair is one commit, tasks stay split)?** A: rejected. It is what the issue preferred, but it requires rewording "no half-tasks" — since `T1` is exactly half a task — and restructuring the per-task loop to permit a task that is part of a cycle. More edits, to the document that is currently correct.
- **Q: loosen the quality gate to tolerate test-only commits?** A: rejected. It makes the gate's behaviour depend on classifying a diff, and a misclassification fails open — the failure 0.2.1 was spent fixing.
- **Q: prose-only, or a mechanical check?** A: a check. AC4.

## 2. Design (HOW)
- Fix approach, and why this rather than the narrower or wider fix: Four edits and one new guard. The **feature** and **bug** templates fold their red and green tasks into one — `T1: failing test for X, then the implementation that passes it`. The **chore** template is untouched: its T1/T2 are green by construction, so it has no red step to strand. `implement/SKILL.md` states the resolution outright — a task is a full cycle, one task is one green commit, and a turn must not end with failing validators — because this is precisely the kind of thing every user otherwise rediscovers alone.

  `skills/spec/SKILL.md`'s "The first task is always" table is reconciled with the fold — the fourth edit, added on review, because it says the same thing a third time and would be left contradicting the templates it describes.

  A new `scripts/check-templates.py` fails when a Tasks block in `skills/spec/templates.md` contains a task line that names a failing or regression test without also naming the implementation that answers it. Wired into CI **and onto `.steering/tech.md`'s `- Validators:` line**, so it fails the turn as well as the build — a guard in CI only is enforced by the half of this harness that cannot end a turn.

  *Narrower, rejected:* edit the templates and say nothing in `implement`. The templates would be consistent and the contradiction would survive in any spec already written from the old ones, with nothing telling the author how to execute it.

  *Wider, rejected:* changing `quality-gate.sh` — see the third clarification.
- Affected files: `skills/spec/templates.md`, `skills/implement/SKILL.md`, `skills/spec/SKILL.md` (AC8), `scripts/check-templates.py` (new), `scripts/test-gates.sh` (AC6), `scripts/check-skill-contracts.py` (T3's presence check — see below), `.github/workflows/ci.yml`, `.steering/tech.md` and `AGENTS.md` (AC7), and both manifests.

  **Both manifests, because this one needs a version bump.** `skills/` is in `check-version-bump.py`'s `SHIPPED` tuple, so `plugin.json` and `.claude-plugin/plugin.json` must move or the PR fails CI. #28 did not need this and the contrast is easy to carry over wrongly: that spec touched only `scripts/`, which is not shipped.

  **T3's presence check has a home already, and it must be used rather than reinvented.** `scripts/check-skill-contracts.py` holds a `CONTRACTS` tuple of `(skill file, required substring, why it must stay)`, with two `skills/implement/SKILL.md` entries in it today. The paragraph AC2 asks for goes in there as a third. A second presence mechanism would be a second place to look and a second thing to keep in step, and this repo's stated preference is fewer moving parts.
- **Blast radius:** specs already written are unaffected — templates are copied at authoring time, not read at gate time — so existing in-flight specs keep their split tasks and keep needing the workaround. `implement`'s new paragraph is what serves them. The chore template's behaviour must not change, which the new check must not accidentally flag.
- Why this cannot recur: the split is the thing that failed, so the check is written against the split rather than against the current text. A future edit that re-separates red from green fails CI on the day it is made rather than on the day someone follows it — **and, per AC7, fails the turn it is made in**, because the guard is on the Validators line and not only in CI.

### Amendments — 2026-08-26

Reviewed before implementation, three days after drafting. Every premise still held: the templates still split at `templates.md`:36-37 and :77-78, the chore block at :119-123 still has no red step, `implement/SKILL.md`:63 still says "No batching, no half-tasks", and `check-templates.py` does not exist. The contradiction is also now demonstrated rather than argued — six specs, this one included, carry a hand-written `> Folded red-and-green per #10` note, which is the workaround the issue predicted, written out by hand every time.

Five things were added, none of which change the direction the clarifications chose:

1. **AC6 — the new guard was going to ship with no cases of its own.** T1 ran it against the live `templates.md`; the old T4 only confirmed the existing suite still passed. `.steering/structure.md` makes `test-gates.sh` the project's whole notion of test coverage, so that is a new guard nothing pins. It is #39's family, and #28's review found that exact shape twice in the cases written to pin #28 — a guard that cannot read its work-set must fail, not report success.
2. **AC7 — the Validators line was missing from Affected files.** Only CI was named, and CI is the half that does not end turns. A guard off that line is a guard this repo cannot enforce on itself.
3. **AC8 — `skills/spec/SKILL.md`'s table is a third statement of AC3's subject** and becomes the outlier once the templates fold. Decided in scope rather than left to be discovered mid-task.
4. **The presence check was homeless in the text** (old T2, now T3). `check-skill-contracts.py` already has the mechanism; naming it prevents a second one being built.
5. **The version bump.** `skills/` is shipped, so both manifests must move. Recorded because #28, the immediately preceding spec, correctly did *not* need one.

The task list was renumbered T1–T7 accordingly and each task now names the criteria it discharges.

## 3. Tasks (TDD-ordered)
> Folded red-and-green — this spec is the first written under its own decision.

- [x] T1: failing `check-templates.py` against the current `templates.md` — it must flag the feature and bug T1 lines and must NOT flag the chore template — then fold the two templates so it passes *(AC1, AC3, AC4, AC5)*
- [x] T2: failing cases in `scripts/test-gates.sh` for the guard's own three behaviours — flags a split `T1`, does not flag chore, and fails rather than passes on a missing or unreadable `templates.md` — then whatever the third one needs. The fixture copies the guard into a throwaway tree with its own `templates.md`, the way case 34 does, so the cases do not depend on the live file staying broken *(AC6)*
- [x] T3: state the resolution in `skills/implement/SKILL.md` — a task is a full Red-Green-Refactor cycle, one task is one green commit, a turn must not end red — and pin it as a third `skills/implement/SKILL.md` entry in `check-skill-contracts.py`'s `CONTRACTS` (**AC-limited: presence, not adherence**) *(AC2)*
- [x] T4: reconcile `skills/spec/SKILL.md`'s "The first task is always" table with the folded templates *(AC8)*
- [x] T5: wire `check-templates.py` into `.github/workflows/ci.yml` AND onto `.steering/tech.md`'s `- Validators:` line; update `AGENTS.md`'s "all eight" and any other count site; confirm it fails the build when the fold is reverted *(AC7)*
- [x] T6: blast radius — the chore template byte-identical, `test-gates.sh` green, and the case list diffed against `main` to confirm no pre-existing case changed verdict
- [x] T7: version bump in both manifests, then refactor

## 4. Review triage

`gate-sdd-reviewer`, first pass at `b92af1d`: **BLOCKED** — 0 BLOCKER, 2 HIGH, 2 MEDIUM, 3 INFO. All four findings fixed; the INFOs are confirmations or deferrals to #39.

- **HIGH — a section contributing nothing was skipped and the guard exited 0 with the split present.** Fixed, and it was two defects compounding. The section floor asserted only that each expected section had a *key* in `blocks` — which `setdefault` creates at the `## 3. Tasks` heading whether or not a line parsed under it — and the emptiness check was *global*, so one section could contribute nothing while the other two kept the total non-zero. Underneath it, `TASK_LINE` required `T\d+:`, so `- [ ] **T1:** …`, `- [ ] T1 — …` and `- [ ] 1. …` parsed as nothing at all. None of those is adversarial; bolding an id is ordinary drift in the file this guard watches. The floor is now per section, and **any** `- [ ] …` line inside a Tasks block is a task line. AC4 did not hold before this and does now.

- **HIGH — every fixture varied only the Feature section, so nothing pinned that the guard scans Bug at all.** Fixed. `write_templates` takes a Bug `T1` too, and case 36 asserts a split Bug line is flagged and its section named. The reviewer demonstrated this with a mutation the ablations could not see: narrowing the split loop to `section == "Feature"` deleted half the work-set with the whole suite still green. It now reddens case 36. The lesson is worth keeping: **an ablation removes a branch you wrote; it cannot find a work-set no fixture exercises.**

- **MEDIUM — `GREEN`'s bare `implement` matched inside a file path.** Fixed, but not the way the finding proposed. Word-bounding the alternatives does not work, because `/` is not a word character and `\bimplement\b` matches happily inside `skills/implement/SKILL.md`. Code spans and path-like tokens are now stripped before either pattern is applied, so the line is judged on its prose. `RED`'s narrowness was explicitly *not* flagged, correctly — the docstring declares it a short list and the Design section commits to a guard on prose staying narrow.

- **MEDIUM — `.steering/structure.md`:21 said "45 paths are currently pinned".** Fixed, along with the five other count sites, all now 51. It was already stale on `main` at 47, but T5 puts every count site in scope. `docs/BACKLOG.md`:38 remains the one deliberate exclusion.

- **INFO ×3, all accepted.** `EXPECTED_SECTIONS` is confirmed *not* a G-8 exemption list — it is a floor, not a filter, and the split loop iterates every section discovered, so a fourth section added tomorrow is scanned regardless. The reviewer's judgement was that the weakness was the floor's *depth*, which is the first HIGH. Case 37's `chmod`-ineffective branch reporting `ok` having asserted nothing is #39's first item verbatim, and `report` has no `skip` state to use instead — deferred, and noted as not making the case vacuous since the missing-file half runs unconditionally. `docs/BACKLOG.md`:38 confirmed as correctly excluded.

**Every fix was mutation-tested rather than trusted.** Reverting each one reddens exactly the case that covers it: scanning Feature only reddens case 36; the old `TASK_LINE` reddens case 39's three drift assertions; the old key-presence floor reddens **case 39 only**; dropping the prose stripping reddens case 39's path citation.

*Corrected in round two.* That third entry first read "cases 38 and 39", which was wrong, and wrong in the direction that flatters the work — it claimed a case covered something it does not. The mutation I actually ran disabled the whole per-section floor, which is more than the original floor was. Reconstructing `b92af1d`'s floor exactly — key presence plus a global `total == 0` — reddens case 39 alone. Case 38 stays green and correctly so: its two fixtures are an all-sections-empty file, caught by the global total, and a deleted Bug block, caught by key presence. The shape the old floor missed is the third one, which is case 39's.


**Second pass at `c553eaa`: BLOCKED — 0 BLOCKER, 1 HIGH, 1 LOW, 3 INFO.** Both fixed.

- **HIGH — the round-one MEDIUM fix introduced a new fail-open.** The prose stripping was applied to `RED` as well as `GREEN`, and normalisation is not symmetric: stripping before the *clearing* pattern can only make the guard louder, because a stripped green cue means the line gets flagged; stripping before the *accusing* pattern can only make it quieter, because a stripped red cue means the line is never examined. So `- [ ] T1: write the \`failing test\` for X` and `- [ ] T1: add the failing/regression test for X` both cleared — and the second needs no code span at all, since `failing/regression test` is an ordinary way to write a task line for a template serving both a feature and a bug. Both were correctly flagged before the round-one fix; it traded a wide hole for two narrow ones. The guard now accuses on the raw line and clears only on the stripped prose. All six of the reviewer's reproductions across both rounds are flagged, and the correctly folded line still passes.

- **LOW — §4 overstated a mutation result.** Corrected above, in place, with the reconstruction that establishes the right answer.

- **INFO** — the broadened `TASK_LINE` over-includes non-task checkbox lines, which can only produce a false *flag* and is therefore the fail-closed direction; `- [X]` with a capital X is unmatched and now fails closed via the per-section floor rather than passing silently. Recorded, not objected to. The count sweep was confirmed complete and consistent at 51 across six sites.

**The durable lesson from each round**, kept because the pattern is the point:
1. *An ablation removes a branch you wrote; it cannot find a work-set no fixture exercises.*
2. *Normalisation applied to both sides of a test is not symmetric — stripping before the accusing pattern can only make a guard quieter.*

**Third pass at `b2f83db`: APPROVE — CLEAN, nothing at any severity.** The reviewer answered the `\S*/\S*` breadth question with a proof rather than an absence of counterexamples: the substitution only removes characters and inserts one space, and a slash token is always consumed whole, so it can delete a green cue but never assemble one. The residual — a code span opened and closed *inside* a word, which can do both — was recommended for no action.

**Fourth pass at `4805394`: APPROVE — CLEAN.** Comment-only, and the reviewer verified that rather than accepting it: `git diff` adds eight lines all beginning `#:`, and the parsed AST is identical to the approved revision. The pass exists because `scripts/**/*.py` is in Source globs, so even a comment re-stales the receipt — the gate working as designed.

That fourth pass happened because the reviewer's "no action" was taken as advice rather than as a verdict. Its finding was that the boundary needs no *code* change, which is not the same as no change: a known boundary living only in a review transcript is not in the repo at all, which is the condition `.steering/product.md` argues against everywhere else. The reviewer agreed on re-reading. The boundary is now recorded beside the regex it constrains, with the reason for accepting it.

**Filed rather than fixed:** the reviewer's suggestion that lesson 2 — normalisation applied to both sides of a test is not symmetric — belongs in `agents/*/rules/gates-and-guards.md` as a `G-9`. Out of scope here: that rulebook is hash-pinned by `check-locks.py`, so adding a rule needs a re-pin that has no business in a bug fix for #10.

Receipt at `.review-receipt`, beside this file.
