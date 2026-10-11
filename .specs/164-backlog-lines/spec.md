# Spec: Derive backlog version membership from lines instead of an Epic column

- Slug: 164-backlog-lines   Issue: 164   Type: feature   Status: done
- Author: Hiroyuki Momoi   Date: 2026-10-11

## 1. Requirements (WHAT / WHY)

- User story: As someone reading, refining, or consuming `<docs>/BACKLOG.md`, I want version and milestone membership to be derived from position against lines naming row numbers instead of an `Epic` column written on each row, and I want clear rules for leading items when no walking skeleton exists, so that version membership cannot contradict the total order, columns do not rot into unpopulated cells, and `sprint` can take shaped work from above the ready line without reordering.
- Serves: **CAP-6** (LV-4) — planning that terminates in something the harness reads. Sits at the head of the sequential planning chain (`epics` -> `backlog` -> `sprint`). Closes #74.
- Why the current design fails:
  1. An `Epic` column on every row states membership per item rather than by sequence. In practice, epics are coarse outcomes, and most items do not map 1:1 to an epic; in this repository's own backlog, 10 of 18 rows had `—` in the `Epic` column before the column was removed by decision on 2026-09-20.
  2. Stating membership per row enables a contradiction between the total order and version grouping: an item lower in the list can claim an earlier version than an item above it.
  3. When `docs/EPICS.md` records no walking skeleton (e.g. skeleton already shipped, or a project in `minimum` mode without `EPICS.md`), Step 1 and Rule 1 of `backlog` bind to nothing and offer no instruction on what leads (#74 bullet 1).
  4. The `Blocks` column example in the template (`#3, #7`) collides with tracker issue numbers (#74 bullet 3).
  5. In a `minimum`-mode project, `EPICS.md` is not installed, but Step 1 instructs to read epics.
- Acceptance criteria:
  - [ ] **AC1:** WHEN the template at `skills/backlog/SKILL.md` is rendered THE SYSTEM SHALL provide a `## Lines` section carrying one ready line and zero or more version lines, each naming a row number.
  - [ ] **AC2:** WHEN a backlog row is written THE SYSTEM SHALL NOT carry a version or epic identifier on the row; membership is derived from position against the lines. The table header SHALL have 5 columns: `| # | Item | Blocks | Rough size | Why here |`.
  - [ ] **AC3:** WHEN the `Blocks` column is written THE SYSTEM SHALL use the `row N` / `rows N, M` form rather than `#N`, so it cannot be read as an issue number (#74).
  - [ ] **AC4:** WHEN `- Mode:` is `minimum` THE SYSTEM SHALL instruct step 1 to read PRD capabilities directly and draw only the ready line, rather than referencing a document that mode does not install.
  - [ ] **AC5:** The template SHALL carry its own definitions in the preamble — ordered-not-prioritized, and membership-is-derived — so a reader of `BACKLOG.md` alone can interpret it without reading the skill.
  - [ ] **AC6:** WHEN `docs/EPICS.md` records no walking skeleton (or the skeleton has already shipped), Step 1 and the first rule in `skills/backlog/SKILL.md` SHALL instruct what leads: the epic or item closing the live falsifier, or the lead item the author names (#74).
  - [ ] **AC7:** Refinement SHALL be defined as a gradient where the top of the list (above the ready line) is shaped and sized for `sprint` to decompose while the bottom is coarse; `backlog` maintains the ready line during refinement, and `sprint` takes items strictly from above the ready line without moving the line, preserving `sprint`'s invariant ("One edit per row, naming the issues that row became; leave the order, the `Why here` reasoning, and every other row untouched", `skills/sprint/SKILL.md:33`).
  - [ ] **AC8:** The `Epic` column SHALL NOT be replaced by a `Serves` column; membership reasoning and capability linkages stay in `Why here`, avoiding another column that goes blank across rows.
  - [ ] **AC9:** `docs/BACKLOG.md` SHALL receive the `## Lines` section with a ready line and version lines, and its preamble updated, demonstrated to parse cleanly without drift under `./scripts/check-backlog-tracker.py`.
  - [ ] **AC10:** A test case in `scripts/test-gates.sh` (Case 223) SHALL assert the backlog lines format and template invariants (ready line and version lines in `## Lines`, 5-column table with no `Epic` column, `row N` in `Blocks`, derived membership preamble bullet, no-skeleton guidance, and `minimum` mode instruction), verifying both positive matches and red-capable failure under named mutation.
- Out of scope:
  - Redefining an epic as a major version and renaming `EPICS.md` to `ROADMAP.md` (#165, ordered row 2 in the backlog; builds on this spec).
  - The `- Reconciled against PRD:` line and its cascade enforcement guard (#166, ordered row 3).
  - `sprint` writing issue numbers back onto rows it took (#79, already shipped).
  - Re-ordering or re-prioritizing existing rows in `docs/BACKLOG.md` (this change migrates structure, it does not re-groom).
  - Version bump (minor bump 0.25.1 -> 0.26.0 is a post-review step of `implement`, per #113 / templates.md).

### Clarifications

Four questions, resolved before design (2026-10-11):
1. **Should `Serves` be a column or live in `Why here`?** — *Answered: Live in `Why here`.* A dedicated column repeats the exact failure mode of `Epic` — blank or em-dash cells on more than half the rows. `Why here` already holds value, risk, cost, dependency, and capability linkages. Rejected: **`Serves` column** (creates another column that rots and goes blank).
2. **Who maintains the ready line, and does `sprint` move it?** — *Answered: `backlog` maintains the ready line during refinement.* `sprint` takes items from above the ready line from the top without moving the line, preserving `sprint`'s invariant: "One edit per row, naming the issues that row became; leave the order, the `Why here` reasoning, and every other row untouched" (`skills/sprint/SKILL.md:33`). Moving the line inside `sprint` would turn `sprint` into a second author of backlog boundaries. Rejected: **`sprint` moves the ready line** (violates `sprint`'s single-cell edit invariant).
3. **What leads when no walking skeleton exists?** — *Answered: The epic or item closing the live falsifier, or the lead item the author names.* (#74 bullet 1). Step 1 and Rule 1 state this explicitly. Rejected: **silence on no-skeleton** (leaves Step 1 binding to nothing on brownfield projects).
4. **Status of "Next up" and "Not ready"?** — *Answered: Already closed by #174 AC5.* #164's original AC6 is superseded and dropped as a no-op, as documented in #174's spec and backlog notes.

## 2. Design (HOW)

- Approach and key decisions:
  1. **Line markers in `## Lines` as markdown bullets (never a table).** `## Lines` is placed immediately before the ordered table. Each line specifies a boundary: `- **Ready line:** row <n> — work above this line is shaped and ready for sprint to decompose; work below is coarse.` and `- **<Version> line:** row <n> — items up to row <n> complete <version or outcome>.` Like `## Discharged since last refinement`, lines MUST be markdown bullets, never table rows (`| <digits> |`), so `scripts/check-backlog-tracker.py` does not parse them as backlog rows.
  2. **5-column table with no `Epic` column.** The table header is `| # | Item | Blocks | Rough size | Why here |`. Membership is derived from position relative to the lines in `## Lines`, never written on a row.
  3. **`Blocks` format is `row N` / `rows N, M`.** In the template and instructions, `Blocks` examples use `row 3, row 7` rather than `#3, #7`, ensuring positions cannot be confused with issue numbers.
  4. **Sizing gradient and Ready line ownership.** Refinement is defined as a gradient: items above the ready line are shaped and sized for `sprint` decomposition; items below are coarse. `backlog` draws the ready line. `sprint` consumes rows strictly from above the ready line without moving it.
  5. **Brownfield / no-skeleton guidance and `minimum` mode.** Step 1 and Rule 1 instruct what leads when no walking skeleton exists (epic or item closing the live falsifier, or lead item named by author). In `minimum` mode, Step 1 instructs to read PRD capabilities directly and draw only the ready line (as `EPICS.md` is not installed).
  6. **Preamble definitions.** The template carries its own definitions in the preamble (`Ordered, not prioritized...` and `Version and release membership are derived from position against the lines in ## Lines, never written on a row.`), ensuring `BACKLOG.md` is self-interpreting without the skill.
  7. **Migration of `docs/BACKLOG.md`.** Preamble disclaimer updated to reflect shipped lines; `## Lines` added with ready line (row 3, covering the planning chain #164–#166) and 0.26.0 line (row 3); verified clean by running `./scripts/check-backlog-tracker.py`.
  8. **Automated test in `scripts/test-gates.sh`.** Case 223 verifies template structure, 5-column layout, line markers, no-skeleton instruction, and `minimum` mode guidance, with red-capability verified under named mutation.

- Affected modules and files, per `.steering/structure.md`:
  - `skills/backlog/SKILL.md` — shipped. Steps 1 & 5, template fence, rules, and red flags. (AC1–AC8)
  - `skills/sprint/SKILL.md` — shipped. Step 1 reference to ready line. (AC7)
  - `docs/BACKLOG.md` — not shipped. Preamble update and `## Lines` section. (AC9)
  - `scripts/test-gates.sh` — not shipped. Test case 223. (AC10)
  - `plugin.json` and `.claude-plugin/plugin.json` — shipped. Version bump 0.25.1 -> 0.26.0 (implement step after review).
  - `.work_logs/2026-10-11.md` — not shipped. Work log entry (implement step after review).

- Contract changes, and who else consumes them:
  - `skills/backlog/SKILL.md` template is consumed by every project running the skill, and by `scripts/check-backlog-tracker.py`.
  - `scripts/check-backlog-tracker.py` is unaffected: it matches `Item` column by name, table rows by `ROW` (`^\s{0,3}\|\s*(\d+)\s*\|`), and ignores markdown bullets in `## Lines`.
  - `skills/sprint/SKILL.md` reads `docs/BACKLOG.md` at step 1; taking from above the ready line clarifies what "top" means without changing `sprint`'s bounded-edit contract (step 6).
  - `scripts/check-skill-contracts.py` is unaffected: `skills/sprint/SKILL.md` retains its pinned sentence "creates no parallel record" (`:317`), and `skills/backlog/SKILL.md` has no pinned entry.

- Risks and trade-offs:
  - **Ready line without mechanical enforcement:** The ready line is a planning boundary rather than a mechanical gate. `scripts/check-backlog-tracker.py` does not fail if unshaped work is above the ready line, but `backlog`'s red flags explicitly warn against this ("The ready line is placed below unshaped or unsized items").
  - **Positional renumbering of lines:** When rows are inserted or discharged, lines naming row numbers must be shifted along with row numbers and `Blocks` references. This is the existing positional trade-off of `BACKLOG.md` and cannot be avoided until stable row IDs exist (noted in deep review §4).
  - **Migration of `docs/BACKLOG.md`:** Editing `docs/BACKLOG.md` runs against `scripts/check-backlog-tracker.py` in CI; task T2 ensures it passes cleanly with 0 drift.

## 3. Tasks (TDD-ordered)

> One task is one complete Red-Green-Refactor cycle, so one green commit. No task is sequenced after the review.

- [x] T1: failing test in `scripts/test-gates.sh` (Case 223) asserting backlog lines format, template invariants, and skill instructions — then the implementation in `skills/backlog/SKILL.md` and `skills/sprint/SKILL.md` that makes it pass
- [x] T2: migrate `docs/BACKLOG.md` to add `## Lines` with ready line and version lines, and update preamble — then verify `./scripts/check-backlog-tracker.py` passes cleanly
- [x] T3: refactor and verification pass across all validators, with named mutation proving red-capability of Case 223
