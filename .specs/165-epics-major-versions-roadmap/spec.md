# Spec: Redefine an epic as a major version, rename EPICS.md to ROADMAP.md, and rename skill to roadmap

- Slug: 165-epics-major-versions-roadmap   Issue: 165   Type: feature   Status: done
- Author: Hiroyuki Momoi   Date: 2026-10-11

## 1. Requirements (WHAT / WHY)

- User story: As a project maintainer, planner, or teammate, I want `roadmap` (formerly `epics`) to define major versions as content commitments (themes, demos, and capabilities completed) in `<docs>/ROADMAP.md` formatted as `<major.minor>-<name>` without specifying issue lists, walking skeleton flags, or backlog rows, so that the roadmap and backlog stop competing for granularity, version membership is derived from sequence in `BACKLOG.md`, and planning documents terminate in something verifiable without redundant maintenance.
- Serves: **CAP-6** (LV-4) — planning that terminates in something the harness reads. Sits at the center of the sequential planning chain (`roadmap` -> `backlog` -> `sprint`), following #164 and unblocking #166.
- Why the current design fails:
  1. `epics` currently defines an epic as an outcome-cut chunk of work that lists specific issues and names a walking skeleton. This creates granularity overlap with the backlog, forcing two documents to compete for sequence and issue tracking.
  2. Because issue lists were embedded in `EPICS.md`, backlog refinement or issue creation caused `EPICS.md` to go stale or require parallel manual updates.
  3. The `Walking skeleton: yes | no` field is permanently `no` on any project past its initial week, forcing projects (including this repository) to author awkward disclaimers explaining why no remaining epic is a skeleton (#74). 1.0 is the skeleton by definition.
  4. `EPICS.md` holding major versions is a misnomer; a document named `EPICS.md` attracts backlog-level items rather than release-level milestone commitments.
  5. Inception skills must terminate in something the harness uses. Redefining epics as major versions provides a mechanical terminus: versions map to release milestones, and `Completes:` cites PRD capabilities that can be cross-checked.
- Acceptance criteria:
  - [x] **AC1:** WHEN the skill defines a major version THE SYSTEM SHALL define it as a content commitment with a demo, not a date or calendar phase.
  - [x] **AC2:** The skill SHALL be renamed to `roadmap` (`skills/roadmap/SKILL.md`), and WHEN the document is authored THE SYSTEM SHALL write `<docs>/ROADMAP.md`.
  - [x] **AC3:** `assets/check-document-set.py` SHALL name `ROADMAP.md` in `FULL_ONLY_DOCS` and map it to `roadmap` in `DOC_OWNER`.
  - [x] **AC4:** The `Walking skeleton` field SHALL be removed from the skill instructions and template. 1.0 is the skeleton by definition.
  - [x] **AC5:** WHEN a version entry is written THE SYSTEM SHALL NOT list issues and SHALL NOT name a backlog row; membership is derived in `BACKLOG.md` via position against `## Lines`.
  - [x] **AC6:** WHEN a version entry is written THE SYSTEM SHALL carry a `Completes:` field citing PRD capability ids.
  - [x] **AC7:** Version entry headers in `ROADMAP.md` SHALL use the `## <major.minor>-<name>` format (e.g., `## 1.0-baseline-harness`).
  - [x] **AC8:** The template in `skills/roadmap/SKILL.md` SHALL carry its own definitions in its preamble, so a reader of `ROADMAP.md` alone knows that issue and row membership are derived in `BACKLOG.md` rather than written here.
  - [x] **AC9:** `README.md` and `README.ja.md` SHALL agree across the flow diagram, the skills table, and the minimum-set opt-in table, replacing `epics` with `roadmap` and removing stale references to `EPICS.md` and any outdated justification citing #22.
  - [x] **AC10:** `skills/init/SKILL.md`'s opt-in three description SHALL name `roadmap` / `ROADMAP.md` rather than `epics` / `EPICS.md`.
  - [x] **AC11:** `skills/backlog/SKILL.md` and `docs/layout.md` SHALL reference `roadmap` and `ROADMAP.md` rather than `epics` and `EPICS.md`.
  - [x] **AC12:** `docs/EPICS.md` SHALL be rewritten and replaced by `docs/ROADMAP.md` defining major versions (content commitments, demos, completed capabilities) conforming to the new template, passing `assets/check-document-set.py`.
  - [x] **AC13:** Automated test cases in `scripts/test-gates.sh` SHALL verify the updated docset checks for `ROADMAP.md` and `roadmap`, template invariants in `skills/roadmap/SKILL.md` (major version definition, `Completes:` field, absence of `Walking skeleton` and issue lists), and red-capability under named mutation.
- Out of scope:
  - The backlog's `## Lines` section and `Serves` column (handled by #164).
  - The `- Reconciled against PRD:` line and its cascade enforcement guard (deferred to #166).
  - Dates, quarters, or calendar phases on versions (versions are strictly content commitments).

### Clarifications

Three questions, resolved before design (2026-10-11):
1. **Should existing `docs/EPICS.md` content be migrated or rewritten?** — *Answered: Rewrite `docs/ROADMAP.md` around major versions.* Its four entries were cut by outcome rather than version. Rewriting them honestly as major version commitments (e.g. 1.0 baseline harness, 2.0 dual-target parity and mechanical gates) matches the new template with `Completes:` lines and no issue lists or walking skeleton disclaimers.
2. **Should the skill command and directory remain `epics` or be renamed to `roadmap`?** — *Answered: Rename the skill to `roadmap` (`skills/roadmap/SKILL.md`).* Changing the command name from `epics` to `roadmap` across the plugin, manifests, docset checker, and documentation aligns the skill name with the document and avoids holding a skill name that misdescribes its output.
3. **What header format should version entries follow in `ROADMAP.md`?** — *Answered: `## <major.minor>-<name>` (e.g., `## 1.0-baseline-harness`).*

## 2. Design (HOW)

- Approach and key decisions:
  1. **Rename skill to `skills/roadmap/SKILL.md`.** Move `skills/epics/SKILL.md` to `skills/roadmap/SKILL.md`. Update skill frontmatter `name: roadmap`, description, title, steps, template, rules, and red flags. The skill authors `<docs>/ROADMAP.md`.
  2. **Major versions as content commitments with demos and completed capabilities.** Each version section is formatted as `## <major.minor>-<name>`. Entries carry:
     - `- Completes: <capability ids>` (e.g., `CAP-1, CAP-2`)
     - `- Demo: "<the sentence you would say while showing it>"`
     - `- Depends on: <earlier version, or nothing>`
     - `- Not included: <scope boundary>`
  3. **No issue lists and no walking skeleton field.** Version membership is derived in `BACKLOG.md` via position relative to lines in `## Lines`. 1.0 is the skeleton by definition; subsequent versions do not carry the field.
  4. **Preamble definitions.** The template preamble in `skills/roadmap/SKILL.md` explicitly defines that version entries are major milestones and content commitments, not dates, and that issue and row membership are derived from `BACKLOG.md`.
  5. **Docset checker and init alignment.** In `assets/check-document-set.py`, update `FULL_ONLY_DOCS` to `("NORTH_STAR.md", "ROADMAP.md", "CONTRACT.md")` and `DOC_OWNER` to map `"ROADMAP.md": "roadmap"`. Update `skills/init/SKILL.md` to describe `roadmap` as the opt-in skill authoring `ROADMAP.md`.
  6. **Cross-skill and documentation references.**
     - In `skills/backlog/SKILL.md`: Update step 1 to read the roadmap (`ROADMAP.md`), noting `1.0` is the skeleton by definition, and updating the minimum mode note (`ROADMAP.md is absent`).
     - In `README.md` and `README.ja.md`: Update flow diagrams (`design-doc ──▶ roadmap ──▶ backlog`), skills tables (`roadmap` authors `ROADMAP.md`), and opt-in tables.
     - In `docs/layout.md`: Update `docs/EPICS.md` to `docs/ROADMAP.md` authored by `roadmap`.
  7. **Rewrite `docs/EPICS.md` as `docs/ROADMAP.md`.** Delete `docs/EPICS.md` and create `docs/ROADMAP.md` defining major milestones (1.0 baseline harness, 2.0 dual-target parity and mechanical gates) with `Completes:` referencing PRD capabilities.
  8. **Test coverage in `scripts/test-gates.sh`.** Update existing docset test assertions from `EPICS.md (via epics)` to `ROADMAP.md (via roadmap)`. Add Case 224 verifying `roadmap` skill template invariants (`ROADMAP.md`, `Completes:`, no `Walking skeleton`, no issue lists) and red-capability under named mutation.

- Affected modules and files, per `.steering/structure.md`:
  - `skills/roadmap/SKILL.md` (renamed from `skills/epics/SKILL.md`) — shipped. (AC1, AC2, AC4, AC5, AC6, AC7, AC8)
  - `assets/check-document-set.py` — shipped. (AC3)
  - `skills/init/SKILL.md` — shipped. (AC10)
  - `skills/backlog/SKILL.md` — shipped. (AC11)
  - `docs/ROADMAP.md` (replaces `docs/EPICS.md`) — not shipped. (AC12)
  - `docs/layout.md` — not shipped. (AC11)
  - `README.md` and `README.ja.md` — not shipped. (AC9)
  - `scripts/test-gates.sh` — not shipped. Test updates and Case 224. (AC13)
  - `plugin.json` and `.claude-plugin/plugin.json` — shipped. Version bump (implement step after review).
  - `.work_logs/2026-10-11.md` — not shipped. Work log entry (implement step after review).

- Contract changes, and who else consumes them:
  - `assets/check-document-set.py` is copied into consumer repositories by `init` and run on their `- Validators:` line. Updating `FULL_ONLY_DOCS` and `DOC_OWNER` changes what `- Mode: full` requires.
  - Consumers running `full` mode require `ROADMAP.md` instead of `EPICS.md`.
  - Skill name `epics` changes to `roadmap`; users invoke `roadmap` instead of `epics`.

- Risks and trade-offs:
  - **Breaking change on skill command name:** Renaming `epics` to `roadmap` is a user-facing command change. Since the repository is pre-release (and in dual-target plugin layout, skills are auto-discovered), renaming now prevents carrying a legacy skill name that disagrees with its output document.
  - **Docset checker compatibility for existing full-mode clones:** Existing repos with `docs/EPICS.md` under full mode would fail `check-document-set.py` until renamed to `docs/ROADMAP.md`. Handled via documentation and release notes.

## 3. Tasks (TDD-ordered)

> One task is one complete Red-Green-Refactor cycle, so one green commit. No task is sequenced after the review.

- [x] T1: failing test in `scripts/test-gates.sh` (Case 224 asserting roadmap skill template invariants, and docset test updates) — then the implementation updating `assets/check-document-set.py`, renaming `skills/epics/SKILL.md` to `skills/roadmap/SKILL.md` with major version definitions, and updating `skills/init/SKILL.md` and `skills/backlog/SKILL.md`
- [x] T2: rewrite `docs/EPICS.md` to `docs/ROADMAP.md` conforming to the new template, and update `README.md`, `README.ja.md`, and `docs/layout.md` — then verify all 13 gating validators pass cleanly
- [x] T3: refactor and verification pass across all validators, with named mutation proving red-capability of Case 224 in `scripts/test-gates.sh`
