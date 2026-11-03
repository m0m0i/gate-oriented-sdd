# Spec: a project that adopted the harness before `- Mode:` can declare a mode that passes

- Slug: 309-a-project-adopted-before-mode-can-declare-one   Issue: 309   Type: bug   Status: approved
- Author: m0m0i (Claude Code)   Date: 2026-11-03
- **Ships before #340**, by the maintainer's decision at #340's C5: #340 runs both document checks in every project at turn end, and a project with no readable `- Mode:` line then blocks on a plugin update alone. This spec gives that project a state it can declare truthfully.

Backlog row 12's last issue, moved ahead of row 1's #340 by that decision.

## 1. Requirements (WHAT / WHY)

- **Reproduction** (the issue's table, re-measured on `b0a71bd` in a scratch fixture):
  1. A git repository whose `.steering/tech.md` has no `- Mode:` line, whose `.specs/` holds five specs with `spec.md`, whose `docs/` holds only `CONTRACT.md`, and which has the three canonical issue templates and `.work_logs/`.
  2. Run `assets/check-document-set.py` and `assets/check-document-cascade.py` from the repository root, once with no line and once with each mode.
  3. No line: both exit 1, "carries no readable `- Mode:` line". `bootstrap`: the set check exits 1, "5 spec(s) already exist"; the cascade check defers with exit 0. `minimum` and `full`: both exit 1 on documents that do not exist. Moving the specs into `.specs/_archive/` changes nothing, because the expiry scan reads `_archive/` too (`assets/check-document-set.py:303-341`).
- **Expected:**
  - CAP-4 says every project runs under the same gates "whatever state it was in before", and its falsifier is "a first turn blocked by a failure that predates the install" (`docs/PRD.md:42`, `:44`). A project adopted before 0.6.0 is in a state the harness should be able to describe.
  - The remediation text is part of the guard (`assets/check-document-set.py:166-168`, #127): a refusal names a value that passes for the project reading it.
  - `init`'s upgrade path names that state before step 4 arms the check (`skills/init/SKILL.md:90`, step 4.1).
- **Actual:**
  - **No mode is true for this project until it writes `PRD.md`, `DESIGN.md` and `BACKLOG.md`.** An absent line is refused on purpose (`:161-174`), `bootstrap` expires at the first spec (`:335-341`), and `minimum` and `full` claim documents that do not exist (`:244-263`).
  - **The absent-line refusal advises `bootstrap`** "if the inception documents are not written yet" (`:171-172`), which is true of this project and fails one run later: the self-contradiction `:166-168` says #127 ended. The cascade check's refusal names no remedy beyond the three values (`assets/check-document-cascade.py:49-54`).
  - **Under `minimum` or `full`, the missing-documents failure names paths only** (`:265-279`). `DOC_OWNER` names the skill that writes each document, and only the `bootstrap` branch uses it.
  - **`init` has no rule for this project.** Its Mode rule covers "a project that already carries a `- Mode:` line" (`skills/init/SKILL.md:101`). Step 3 knows two cases, "this step has just written one on a fresh install, and an upgrade carried one in" (`:46`), so a project with no line and shipped specs takes the fresh-install branch and is given `bootstrap`, which fails at once. Step 4.1 then cannot pass without three documents that step 3 forbids `init` to write.
  - **`spec` treats the absent line as `full` and says so on every spec** (`skills/spec/SKILL.md:12`), in a project that has never run `sprint`, against that step's own "a rule that fires on every single spec is one the user learns to skip".
- **Impact:**
  - Every project installed before 0.6.0 that kept using the harness. The maintainer's real, unrelated project is one, measured the same way on a scratch copy.
  - Today such a project can keep the check off its `- Validators:` line, which #127 rejected as the gate switched off and never switched back on (`.specs/_archive/127-*/spec.md`, Clarifications). After #340 it cannot: #340's AC2 runs the check whatever the line says, and AC5 blocks on the absent line. Each turn end blocks until the session writes three inception documents and commits and stamps them for the cascade check, inside a Stop loop.
  - A project installed after 0.8.0 that declared `bootstrap`, wrote specs and never wrote the documents is blocked by the same expiry, but its message already names a remedy that works. It is not this issue's population (C4).
- **Root cause:**
  - **`bootstrap` measures "nothing specified yet" as "no spec on disk".** #127 ended the window at the first spec because "a PRD starts being cited the moment a spec exists" (its C2). For a project that installs the harness and then writes specs, the two are the same. For a project whose specs predate the declaration, they are not: those specs were written before any PRD could be cited, and the window can never open.
  - **The absent-line refusal looks at neither `.specs/` nor `docs/`.** It returns at `:161-174`, before the spec scan and before `- Docs:` is read, so it gives a fresh install, a project with shipped specs and a project with written documents the same advice.
  - **`init`'s rules key on the line existing.** The upgrade rule starts from "already carries a `- Mode:` line", and step 3's routing treats "no line" as "fresh install". Nothing in either covers a project that is not a first install and has no line, which every pre-0.6.0 project is.
- **Acceptance criteria.** The **adoption line** is `- Specs before bootstrap:`, a comma-separated list of spec directory names on one physical line, in `.steering/tech.md`. An **adopted project** has no `- Mode:` line, at least one spec in `.specs/` or `.specs/_archive/`, and not all of `PRD.md`, `DESIGN.md` and `BACKLOG.md` under its local `- Docs:` directory.
  - [ ] **AC1:** WHEN an adopted project declares `- Mode: bootstrap` with an adoption line naming exactly the specs on disk THE set check SHALL pass, and the cascade check SHALL defer as it does for any `bootstrap`.
  - [ ] **AC2:** WHILE an adoption line is present THE window SHALL end at the first spec it does not name, as #127's window ends at the first spec:
    - a spec in `.specs/` or `_archive/` the line does not name fails, counted the moment its `spec.md` is written, committed or not;
    - a name that matches no spec directory on disk, compared exactly against the directory's own name, fails, naming the causes: deleted, renamed, misspelt or not yet written;
    - a name with a spec in both `.specs/` and `_archive/` fails, naming both paths, since one of them is new;
    - archiving a named spec keeps it named;
    - an empty entry, or one holding `/` or equal to `.` or `..`, fails and names the entry;
    - every failure above is reported together in one run, and none prints the unlisted names as text to append;
    - the check reads the filesystem only, needs no git, keeps the three outcomes (found, unreadable, none), and fails closed on every read error.
  - [ ] **AC3:** WHEN `- Mode:` is absent or unreadable both document checks SHALL still exit 1, and the set check SHALL name the declaration that settles the Mode question for this tree. The cascade check points at the set check's message rather than restating it.
    - no spec on disk, or no `.specs/` at all: `bootstrap`, as today;
    - an adopted project: `bootstrap` with the adoption line written out for the specs present, or the documents and `minimum` or `full`;
    - the three documents present: `minimum`, or `full` after the opt-in three;
    - specs on disk whose names cannot be written on the line (holding a comma or a newline, or edge whitespace): the documents only, naming those directories;
    - a `.specs/` that cannot be read: fail closed, saying the declaration cannot be named;
    - a remote `- Docs:` value: today's text, since the remote refusal follows whatever mode is declared.
  - [ ] **AC4:** THE documents remedy SHALL name a set each mode accepts, wherever it is printed: `minimum` after `PRD.md`, `DESIGN.md` and `BACKLOG.md`, `full` after those and the opt-in three, each with the skill that writes it. This covers the expired-`bootstrap` message with no `- Target:` (`:295`), whose "declare `minimum` or `full`" fails one run later for `full`, and the `minimum` and `full` missing-items failure (`:265-279`), which names paths only.
  - [ ] **AC5:** THE set check SHALL read the adoption line only under `bootstrap`, as it reads `- Target:`, so a spent one in a `minimum` or `full` project changes no verdict. Absent, or present with an empty value, it changes nothing for any install. The anchor check holds its form in every mode, as for `- Target:`: written so the reader cannot see it, it fails. It is listed wherever the machine-read lines are listed.
  - [ ] **AC6:** WHEN `init` runs on a project with no `- Mode:` line THE skill SHALL route it by what is on disk: no spec, a fresh install as today; the three documents present, `minimum` or `full` by the existing upgrade route; an adopted project, `bootstrap` with the adoption line naming the specs on disk. For an adopted project it first brings the project's copies of the two document checks up to the plugin's, then says the window ends at the next spec, asks for `- Target:`, and arms the check on the green tree that results.
  - [ ] **AC7:** WHEN `spec` reads no `- Mode:` line THE skill SHALL name the declaration the set check names for this tree, and say in the same breath that this spec ends a `bootstrap` window, as it says for `bootstrap` today.
  - [ ] **AC8:** the regression cases that fail before the fix fail for the reproduction's reason: the reproduction's tree with an exact adoption line, failing on "5 spec(s) already exist", and each malformed or unknown-name line on a tree with no spec, which today passes because the line is unread. The remaining cases are controls on fail-closed behaviour that already holds. A matrix case takes every absent-`Mode` refusal across specs (none, live, archived, untracked) and documents (absent, present), parses the `- Mode:` and adoption lines out of the message, applies them, and re-runs the set check, which passes. The documents remedies are checked by their text.
  - [ ] **AC9:** THE documents that list the machine-read lines or describe `bootstrap`'s expiry SHALL name the adoption line, the version SHALL move by a minor at `implement`'s step 5, and `docs/BACKLOG.md` SHALL record #309 ahead of #340 in row 1.
- **Out of scope:**
  - #340's runner, the digest, the remote-Docs refusal's "Remove this checker from `- Validators:`" text and the docstring's "No hook reads the mode" (`:25-27`), which #340 rewrites.
  - Template filenames from before 0.9.0, which keep the check red whatever `- Mode:` says. `init` step 3 already absorbs them, and the checker's own note names that.
  - #338, a squash merge that leaves the PRD stamp red, which the "write the documents" remedy inherits.
  - **Enforcing that an adoption line is never extended.** A filesystem check cannot tell an appended name, or a deleted and rewritten line, from the original declaration. Both show in the `tech.md` diff, and the success line prints the count the line grandfathers. C4 records the choice.

### Clarifications

- 2026-11-03 — **How does a project with shipped specs and no inception documents get a mode it can declare truthfully?** **Answered: a mid-life `bootstrap`**, declared with a line naming the specs that predate it (AC1). It is true for an adopted project in the sense it is true for a new one: the documents are owed, and nothing has been specified against them since the declaration. The documents are deferred, not waived: the next spec ends the window, so the block arrives inside the flow at the step that cites them, not at the first turn end after an update. Rejected: *prose and messages only, so the remedy is writing the three documents* (truthful, but after #340 the blocked session writes, commits and stamps three inception documents inside a Stop loop, and `init` step 3 forbids `init` to write them).
- 2026-11-03 — **What anchors the window?** **Answered: the names of the specs present**, not a commit or a count (AC2). It needs no git, so it survives a squash merge and a shallow CI checkout, and a name with no spec on disk fails, so it cannot pre-authorise one. Rejected: *`- Since: <sha>`*, measured failing closed in a depth-1 clone (rc 128) and, written on the upgrade branch, no ancestor of `main` after a squash merge (#338's shape); *a count*, which deleting an old spec would silently make room under.
- 2026-11-03 — **Is a project that declared `bootstrap`, then wrote specs without the documents, offered the same line?** First answered yes. **Superseded by C4.**
- 2026-11-03 — **Where is the adoption line offered?** **Answered: only where no `- Mode:` line exists**: the set check's absent-`Mode` refusal (AC3) and `init`'s routing (AC6). An expired `bootstrap` keeps today's documents remedy, so #127's C2 still holds for every fresh install: its first spec forces the documents. The checker accepts a hand-written line from any project; the harness just never suggests one after `bootstrap` was declared. The spec's critique found that C3 as first answered reached every fresh install's first spec, and that "offer once" cannot be enforced without history. Rejected: *keep the offer on expiry* (it supersedes #127's C2 for every install); *a git-backed CI check that the line never grows* (closes the residual, but brings back the git dependency C2 avoided and needs `fetch-depth: 0`).

## 2. Design (HOW)

- **Fix approach, and why this rather than the narrower or wider fix.** The narrower fix is the messages alone: truthful, and after #340 a Stop loop that ends only when three inception documents exist (C1). The wider one is a new mode, which #127 and #148 argued against: a second name for "documents owed" would let two values disagree about the same state. This keeps one mode and changes only what its expiry counts from, and only for a project that declares where its window starts.

- **The adoption line.** `- Specs before bootstrap: <name>, <name>, …` in `.steering/tech.md`, on one physical line.
  - Read with `steering_value(text, "Specs before bootstrap")` and stripped, as `Target` and `Docs` are. No hook reads it. The anchor check's shell reader judges only presence and readability, and a whitespace-only value is empty to both readers.
  - An empty value after the strip is tested first and is the same as no line. Otherwise the value is split on commas and each entry stripped, and AC2's entry rules apply.
  - Read only when `- Mode:` is `bootstrap`, at the point `Target` is read (`:212`).

- **`assets/check-document-set.py`.**
  - **The spec scan becomes a function** returning, for each directory name, the paths holding its `spec.md` in `.specs/` and `_archive/`. Its fail-closed handling is unchanged: `os.scandir` and `os.stat`, unreadable entries refused, and `_archive/` scanned as an entry of `.specs/` (`:303-331`). Names are `entry.name`, compared as strings, never through `Path.exists()`, which is case-insensitive on macOS.
  - **The absent-`Mode` branch** (`:161-174`) still exits 1 and still says "A mode is declared, never assumed". Before refusing it computes the advice of AC3. It reads `- Docs:` as the later code does. With a remote value it keeps today's text. Otherwise it checks whether the three documents exist and runs the scan, where a missing `.specs/` counts as no spec. It reads no `- Target:`. The written-out remedy is `- Mode: bootstrap` and `- Specs before bootstrap: ` followed by the sorted names joined by `, `. A name that would not survive the split is listed as unwritable instead.
  - **Under `bootstrap`** (`:283-353`), with the install invariant checked first as today:
    - **no adoption line:** today's verdicts and text, with AC4's documents remedy where no `- Target:` is set. No adoption line is offered;
    - **an adoption line:** the entry, unknown-name, both-places and unlisted-spec failures of AC2, gathered and reported in one message. The unlisted-spec part keeps today's documents remedy and names the specs, but not as text to append;
    - **pass:** today's success line, plus the count the line grandfathers and that the next spec ends the window, so a mid-life window reads differently from a fresh one in every log that prints it.
  - **Under `minimum` and `full`** the missing-items failure appends ` (via <skill>)` to each document `DOC_OWNER` names (AC4).
  - The docstring's `bootstrap` paragraph (`:9-17`) gains the adoption in one sentence. The paragraph about being copied into `scripts/` (`:25-27`) is #340's.

- **`assets/check-document-cascade.py`.** The absent-`Mode` refusal (`:48-54`) adds one sentence: `check-document-set.py` names the declaration that settles this for this tree. Under `bootstrap` it defers as today and does not read the adoption line, since expiry is the set check's question and a second reader of it could disagree with the first.

- **`assets/check-steering-anchors.sh`.** One `ANCHORS` row, `.steering/tech.md|Specs before bootstrap`. The loose match (`:185`) already accepts a key with spaces, as `Source globs` shows.

- **`skills/init/SKILL.md`.**
  - **Step 3's Mode paragraph (`:46`).** Where the project carried no `- Mode:` line when the step began, look in `.specs/` and `.specs/_archive/` for a directory holding `spec.md`, and in `- Docs:` for the three documents. Route as AC6 says.
    - For an adopted project, first compare the project's `scripts/check-document-set.py` and `scripts/check-document-cascade.py` with the plugin's and copy what differs, with the diff shown, as the pre-0.23.0 migration does (`:75`). A copy from before this fix cannot read the line, and step 4.1 would fail on it.
    - Then write `- Mode: bootstrap` and the adoption line, and say the window ends at the next spec the line does not name and why. Ask the `- Target:` question as for a fresh install.
  - **Sentences this makes false:** "this step has just written one on a fresh install, and an upgrade carried one in" names the adopted case too, and "`bootstrap` expires at the first spec: once `.specs/` holds one" becomes "at the first spec the declaration did not name".
  - **The template (`:55-57`)** gains the line, "read only while Mode is bootstrap; written only for a project adopted with specs already on disk".
  - **Rules (`:100-101`).** Beside the Mode rule, a rule for a project with no line and specs on disk: it is an adoption, neither a fresh install nor an upgrade of a declared mode. `:100` still governs the rest of the install.
  - **Pins.** The `check-skill-contracts.py` entries on the upgrade sentence and the Mode literal must still match, and the edits keep their text. **No new pin:** what enforces this is the checker and its cases, and `init`'s prose is review's to defend. The cap of forty-one asks for an argument this does not have.

- **`skills/spec/SKILL.md:12`.** The absent-line branch keeps treating the project as `full` and saying so. It adds what the set check names for this tree and, in the same sentence, that this spec ends a `bootstrap` window, so the documents come before it (AC7). It runs no command, since the path to the check differs by harness and, after #340, by release.

- **Documents (AC9).**
  - `docs/DESIGN.md:17` ("eight machine-read lines" becomes nine) and `:30`.
  - `CONTRIBUTING.md:43`, worded so it does not say a gate reads the new line.
  - `README.md:108`, and `README.ja.md:77` and `:79`, each one sentence on an adopted project, the same claim, with the "block at the first spec" clause kept true.
  - The comments of test cases 69 and 71 where they state the expiry rule.
  - Version 0.40.0 in both manifests at `implement`'s step 5, after the receipt: a new machine-read line and a change to `init`'s flow are minor by #110's, #127's and #141's precedent.
  - `docs/BACKLOG.md`: row 1's Item cell gains **#309** ahead of **#340**, and "**#340 first now.**" becomes "#309 first, then #340, by the maintainer's decision at #340's C5". Row 12 loses #309 and its sentence. `check-backlog-tracker.py` stays green on this PR. As with #329, merging the PR that closes an Item-cell issue needs a discharge PR after it.

- **Antigravity.** The logic is the same. Until #340, the checks sit in `scripts/` on both harnesses and reach a project when `init`'s adoption route compares them (AC6), or by the README's loop by hand (`README.md:226-235`). A project with a declared mode gets them the way it gets any guard fix today.

- **What #340 inherits.** #340 rebases on this, and its anchor-check branch and its rewrite of `init`'s document-check bullets (`:67-68`) meet this spec's edits beside them. **#340 needs one amendment, in its own commit when it starts:** its fingerprint bullet (its Design, "The fingerprint") hashes `- Docs:` only. Its AC1 asks that a pass not outlive a change to a steering value a check reads, so the bullet gains `- Mode:`, `- Target:` and the adoption line. `.specs/` stays outside the fingerprint, as documents are today: a turn that only writes a spec can still skip at turn end, and CI is where that window closes.

- **Affected files.** `assets/check-document-set.py`, `assets/check-document-cascade.py`, `assets/check-steering-anchors.sh`, `skills/init/SKILL.md`, `skills/spec/SKILL.md`, `scripts/test-gates.sh`, `docs/DESIGN.md`, `CONTRIBUTING.md`, `README.md`, `README.ja.md`, `docs/BACKLOG.md`, `.claude-plugin/plugin.json`, `plugin.json`.

- **Blast radius.**
  - A project with no `- Mode:` line: the same exit 1, with advice that now depends on `.specs/` and `docs/`. Case 57 asserts only `*Mode*` and exit 1, so it holds.
  - A project at `bootstrap` with no adoption line: the same verdicts. Case 69's `*"already exist"*7-a-thing*` holds, since the expiry message keeps that text. Only the no-`Target` remedy wording changes (AC4).
  - `minimum` and `full`: the same verdicts, with ` (via <skill>)` in the missing-items failure. No case asserts that line's exact text.
  - The cascade check: one added sentence on a path that exits 1 either way.
  - This repository runs `full` and never reaches the new branches.

- **Why this cannot recur.** AC8's matrix: every absent-`Mode` refusal has its named declaration parsed out and applied, and the set check run again. Advice that fails one run later fails that case, which is the self-contradiction #127 ended and this issue found again.

## 3. Tasks (TDD-ordered)

> One task is one complete Red-Green-Refactor cycle, so one green commit. No task is sequenced after the review.

- [x] **T1 (AC1, AC2, AC5's set-check half, AC8's red cases):** cases after `docset_repo` in `scripts/test-gates.sh`, with AC8's red-first cases and the AC2 controls. Then the scan function and the `bootstrap` branch.
- [ ] **T2 (AC3, AC4, AC8's matrix):** cases for each absent-`Mode` refusal and each documents remedy, and the matrix. Then the absent-`Mode` branch, AC4's wording in both places, and the cascade sentence.
- [ ] **T3 (AC5's anchor half):** a case that a bolded `- Specs before bootstrap:` fails the anchor check in `bootstrap` and in `minimum`, and an absent one is silent. Then the `ANCHORS` row.
- [ ] **T4 (AC6, AC7):** `init` step 3, its template and its Rules, and `spec` step 1. `check-skill-contracts.py` and the test-gates mutation cases stay green.
- [ ] **T5 (AC9):** the documents and the backlog edit. The version bump is not a task.
