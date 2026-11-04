# Spec: a re-run of `init` upgrades an existing Antigravity install without losing the project's edits

- Slug: 343-a-re-run-of-init-upgrades-an-existing-install   Issue: 343   Type: feature   Status: approved
- Author: m0m0i (Claude Code)   Date: 2026-11-04

Backlog row 1's last issue, after #340 shipped as #353 in 0.41.0. On Antigravity a plugin-shipped hook runs with the plugin directory as its working directory (A12), so `init` renders `.agents/hooks.json` and copies eleven files into `.agents/hooks/` (`skills/init/SKILL.md:77`). That line names a re-run of `init` as the only way a fix to any of them reaches an existing install. This spec defines that re-run and measures it.

## 1. Requirements (WHAT / WHY)

- **User story:** As the maintainer of a project that an earlier gate-sdd version installed for Antigravity, I want a re-run of `init` to bring every copy and the hooks file up to the plugin's current text while keeping what my project changed in them. Then a fix the plugin ships reaches my project without my working out which differences are mine.
- **Serves:** CAP-4, the install path, and CAP-5 / LV-5, a shipped fix reaches the projects running the harness. On Antigravity CAP-5 stays unmet in the sense ADR-10 records, because a fix still needs a re-run. This spec makes that re-run one that is defined and has been run.
- **Today**, citing main at 4b91cef:
  - **The re-run is undefined.** `skills/init/SKILL.md:114` says only "diff and upgrade rather than reinstalling". `:77` says the set is "refreshed together by a re-run", with no compare step and no ask.
  - **The diff-first Rule misses the hooks.** `:112` covers `.steering/`, `.specs/`, `.work_logs/`, `AGENTS.md` and `.github/ISSUE_TEMPLATE/`, not `.agents/hooks.json` or `.agents/hooks/`.
  - **A stale copy and an edited one look the same.** The only compare-and-ask in `init` is #340's guard migration, which compares a `scripts/` copy with the current plugin only (`:89`). The reviewer contract is copied "if it differs" with no ask (`:75`, `:80`).
  - **The records say it was never run.** `README.md:203`, `:230` and `docs/verified.md:641` say the upgrade path is not run or not verified. `README.md:218` says the plugin refresh on Antigravity, an uninstall and an install, has not been run either.
  - **Nothing records what an install holds.** No copy records the version that wrote it (`hooks/harness-checks.sh:41-45`). Tags miss shipped states: there are 35 tags for 71 version bumps, and some untagged bumps carry texts that no tag holds.
  - **The template changed shape six times since v0.2.3.**
    - #143 added the `cd` anchor, and #144 the turn-0 digest.
    - #304 changed the `Stop` timeouts from 180/30 to 600/120.
    - #324 and #330 moved the fast check out of the one `gate-sdd` group, from under matcher `.*`, into a group of its own under the write-tool matcher, inside `( … ) 1>&2; echo '{}'`.
    - #302 added `GATE_SDD_HARNESS=antigravity` to both `Stop` commands.

    The gate commands are byte-identical from v0.21.0 to v0.37.0. So a gate command cannot tell those renders apart.
- **Acceptance criteria:**
  - [ ] **AC1:** WHEN `init` runs on a project with an Antigravity install that an earlier version made THE SYSTEM SHALL:
    - replace each file of the copy set whose text is one the plugin shipped and differs from the current one;
    - copy each file that is missing;
    - name each file it replaced or added.
  - [ ] **AC2:** WHEN `init` re-renders `.agents/hooks.json` over an existing one THE SYSTEM SHALL identify the template that wrote the file by its whole structure.
    - It SHALL take the current template's own values: the gate and digest commands, the `timeout`s, the groups and event shapes, and the `GATE_SDD_HARNESS` marker.
    - It SHALL keep the values the project chose: the fast check command, a matcher that differs from the identified template's, the fast-check group's `enabled` where that group existed, and every group and entry the template does not carry.
    - It SHALL show the result as a diff and get agreement before writing it.
  - [ ] **AC3:** WHEN a file of the copy set, a pre-0.41.0 guard in `scripts/`, or a reviewer contract copy holds a text the plugin never shipped THE SYSTEM SHALL treat it as the project's edit. It SHALL show the diff against the current text and ask before replacing it, never overwriting it silently. On either harness this includes the contract copy, wherever `init` put one.
  - [ ] **AC4:** WHEN `init` re-runs on an install that is already current THE SYSTEM SHALL change no file and say that nothing needed upgrading. A hooks file whose difference is whitespace or key order alone is current.
  - [ ] **AC5:** WHEN `init` re-runs THE SYSTEM SHALL:
    - remove a pre-0.41.0 install's `scripts/` guards only through #340's migration (`skills/init/SKILL.md:87-95`), whose step 2 now asks only about the guards classified as edited;
    - never overwrite the reviewer or its rulebook (`:75`);
    - leave `.steering/`, `.specs/`, `.work_logs/`, `AGENTS.md` and `.github/ISSUE_TEMPLATE/` to the diff-first Rule (`:112`), and `GEMINI.md` to the rules bullet (`:96`).
  - [ ] **AC6:** WHEN the re-render cannot place a value THE SYSTEM SHALL say which value it could not place and why, show the proposed file, and take the answer through a flag. It SHALL never guess, never write a file that switches a gate off, and never write a placeholder. The values it cannot place are:
    - a pre-0.37.0 `gate-sdd` group with `enabled` false, which switched the gates and the fast check off together;
    - a v0.37.0-or-later `gate-sdd` group with `enabled` false;
    - a fast check that does not fit the identified template's envelope;
    - a template-owned group, event or entry the project deleted;
    - a gate or digest command the project edited;
    - two templates that fit equally, or none that fits;
    - a file that is not JSON.
  - [ ] **AC7:** WHEN the project keeps an edited copy THE SYSTEM SHALL judge the whole set, not each file alone. A kept quality gate that does not run the harness checks SHALL be a question that names the checks it would stop running. While such a gate stays, #340's migration SHALL take no harness check off the `- Validators:` line. The copies and the hooks file SHALL be written together: a run that would refresh the gates while leaving an older hooks file writes nothing and says why.
  - [ ] **AC8:** WHEN `init` installs Antigravity into a project with no install THE SYSTEM SHALL copy the set and render the hooks file through the same script, so the copy set has one machine-read statement and one renderer. WHEN the script finds no install and was not asked to make one THE SYSTEM SHALL exit with a code distinct from both a refusal and a pass. It SHALL never create an Antigravity install in a project that has none unless asked.
  - [ ] **AC9:** WHEN this ships THE SYSTEM SHALL have two recorded runs in `docs/verified.md`, each in a real `agy` session in a trusted folder. Each SHALL record which files changed and which edit survived, and SHALL show the re-rendered gates blocking a seeded failure in a later turn.
    - **The fixture:** installed as `init` at `gate-sdd--v0.36.0` writes it, with a hand edit to the fast check, then re-run after the plugin is refreshed by an `agy plugin uninstall` and `install`, which is also recorded.
    - **A real consumer** that the maintainer names (C6), where nothing is pushed without the maintainer's go.

    `README.md:203`, `:218`, `:230` and `:249`, their Japanese counterparts, and `docs/verified.md:641` then say what was run.
  - [ ] **AC10:** WHEN the script is given more than one `--project` THE SYSTEM SHALL report on each in turn and write nothing. Its last line SHALL name every project that is behind, and every project it refused. It SHALL exit 3 if any project has changes or questions pending, 1 if any was refused, and 0 only when every project is current. `--write` SHALL take exactly one project.
- **Out of scope:**
  - A notice at session start saying a project's install is behind the plugin. On Antigravity that means the copied digest reading the installed plugin's directory, which has been observed only on CLI 1.3.3, and #340's C2 rejected relying on it. It is a follow-up after row 2's probe (C5).
  - A fix reaching an Antigravity project with no re-run: A12 rules it out while plugin hooks run from the plugin directory.
  - An `agy plugin update` command. CLI 1.2.16 has none (`docs/verified.md:322`), and row 2's probe re-checks that on a current CLI. AC9 records the uninstall-and-install refresh, but does not change it.
  - Claude Code's `.claude/settings.json` declaration and fast-check entry. The Claude Code pre-0.23.0 migration (`skills/init/SKILL.md:78-86`) and the Rule's Claude Code half stay as they are, except that the contract copy goes through AC3.
  - A project installed before `- Mode:` existed (#309, shipped), and `contract` against an existing rulebook (#70, row 12).

### Clarifications

2026-11-04, asked by `clarify` after a five-way mapping of `init`, the copy set's history, the guards, the records and the prior art. Each answer is the maintainer's.

- **C1. What compares the copies and re-renders the hooks file?** A shipped script that `init` runs, not skill prose.
  - The comparison and the JSON merge are deterministic work that a model can get wrong, and the layer rule (`AGENTS.md:12`) puts such work in a script.
  - `scripts/test-gates.sh:9886-9888` already records that `sed` corrupts a fast check holding `&`.
  - Prose only, as #340's migration and #320 did, was rejected.

  → AC1–AC8, Design.
- **C2. How does the re-run tell a text the plugin shipped from the project's edit?** From a shipped table of every text each copied file has had on `main`, across every commit and not only the tags, since tags miss shipped states. A check fails when a current text is missing from it. The reviewer contract is in the table too.
  - An install stamp was rejected: it helps only installs made after it ships, and no existing install has one.
  - Comparing with the current text only was rejected: every stale copy would become a question, and a stale copy would look like an edit.

  → AC1, AC3, Design.
- **C3. Which earlier installs does it upgrade?** Every render whose quality gate is a script: from v0.2.3, six template texts.
  - First answered as "from v0.21.0", on the premise that v0.21.0 was the first release to install into `.agents/`. The critique found that premise false: Antigravity installs have used `.agents/hooks.json` and `.agents/hooks/` since v0.2.3 (`gate-sdd--v0.10.0:hooks/templates/README.md:11`). Re-asked, the maintainer chose v0.2.3.
  - v0.2.0, which inlined the validator commands into the hooks file, has no field to map them to. It is AC6's question.

  → AC2, AC6.
- **C4. What proves it?** Three things:
  - cases in `scripts/test-gates.sh`;
  - one real `agy` re-run, on a fixture installed at v0.36.0 with a hand-edited fast check;
  - one real re-run on a real Antigravity consumer the maintainer names, as #340's M1 was. Nothing is pushed there without the maintainer's go.

  → AC9.
- **C5. What is in scope beyond the re-run?** Two things, the maintainer's choice:
  - A fresh install goes through the same script (AC8).
  - A batch report: one run after a plugin update lists every project that is behind (AC10).

  The maintainer asked whether the check could run once on every project when the plugin updates. Antigravity has no update event and runs each project's own copies, so an automatic check would need a notice in the copied digest. That rests on a plugin path seen only on CLI 1.3.3, so it is a follow-up. Writes stay per project, because the answers about edited files are per project. → AC8, AC10.
- **C6. Which real consumer?** The maintainer named one, a project whose real Antigravity install was made in 2026-09. That install has never been re-run, and its last commit holds:
  - the v0.2.3–v0.10.0 hooks shape: one group, matcher `.*`, `exit 0` as the fast check, and 180/30 timeouts;
  - four gate copies, and no turn-0 digest.

  That is the oldest shape C3 supports. The run is on a branch from that commit, so the maintainer may install the current plugin there in the meantime. The other consumers considered run Claude Code only and have no Antigravity install to upgrade. → AC9.

A four-lens critique of the first draft (fail-open, feasibility, repository rules, Antigravity in practice) with adversarial verifiers raised 47 findings, and 41 survived. This draft takes them all.
- **The HIGH.** Identifying the template by its gate commands, newest first, matched every v0.21.0 to v0.36.0 render to v0.37.0, because those commands are byte-identical. The template is now identified by its whole structure.
- **The rest** are in the Design below:
  - the builder's base ref;
  - target detection, and the no-install code;
  - the hooks file written with the copies;
  - kept edits judged as a set;
  - answer flags;
  - modes and symlinks;
  - fixtures without tags;
  - the Claude Code scope;
  - GEMINI.md's rule;
  - the copy set stated once;
  - AC9's observability and the plugin refresh.

## 2. Design (HOW)

- **Approach.** A stdlib Python script, `assets/upgrade-install.py`, and a shipped table, `assets/shipped-texts.json`. `init` runs the script from the plugin directory it installs from. It shows the report, asks the report's questions, and runs the script again with the answers to write. The script decides nothing a person must decide, and `init` computes nothing the script can.
- **The table** (C2, C3).
  - **`"copy_set"`** maps each file under `.agents/hooks/` to its source in the plugin: today the eleven files of `skills/init/SKILL.md:77`. It is the copy set's one machine-read statement. `init`, `hooks/templates/README.md` and both READMEs cite it or the script, and list no files.
  - **`"texts"`** maps each source path to the sha256 of every text that path has had. History follows a source across moves:
    - `agents/_shared/` to `reviewers/_shared/` (#235);
    - `scripts/check-locks.py` to `assets/` (v0.2.3).

    The keys cover the copy set's sources and `reviewers/_shared/reviewer-contract.md`. A pre-0.41.0 `scripts/<guard>` and a contract copy look up their source's texts.
  - **`"templates"`** holds, verbatim and keyed by sha256, every text `hooks/templates/antigravity.hooks.json` has had from the commit tagged `gate-sdd--v0.2.3` on: six today. The table names that commit by its sha, so the build needs no tag.
  - **No version per text** (amended in implement, T1). A text first enters the table on its branch, before its release has a version or a tag. A recorded version would therefore go stale at every bump and every release, and since the bump lands after the review, it would also re-stale the receipt. The report calls a `shipped` text "an earlier text of this plugin". The hand-kept keys (`copy_set`, the contract's copies, the source moves, the pre-0.41.0 guards, the template cut) are preserved by the builder, which derives only `texts` and `templates`.
  - **The history** is the first-parent chain of the merge-base of `HEAD` and the default branch's remote-tracking ref (`origin/main`). In CI that is the pull request's base. The working tree's current texts are added to it. A commit only a branch held is never in the table, so the table is the same at a branch's tip and at its merge.
  - **`scripts/build-shipped-texts.py`**, which is not shipped, writes the table. `--check` tests it as two sets: the history's texts ⊆ the table ⊆ the history's texts ∪ the working tree. So a table left behind by a moved `main` fails with "merge the default branch and rebuild", not with a byte diff.
  - **A case in `scripts/test-gates.sh`** runs `--check`, and checks everywhere that every current text is in the table. Where the history or the ref is missing, it runs the second check alone and reports a named skip for the first, never a pass. CI's guards job already checks out with `fetch-depth: 0`, so `ci.yml` does not change. So a change to a copied file cannot merge without the table naming its new text, just as a shipped change cannot merge without a bump.
  - **`assets/**/*.json` joins `- Source globs:`**, so a table change is reviewed source.
- **Targets and the install** (AC8).
  - **Antigravity** is a target when `.agents/hooks.json` or `.agents/hooks/` exists.
  - **Each contract copy** is classified in each of `.claude/agents/` and `.agents/agents/` that holds one.
  - **Nothing else is touched:** no `.claude/settings.json`, and nothing under `.agents/` in a project with no Antigravity install.
  - **With no target found,** the script exits 4, "no install", unless `--install` asks it to make an Antigravity install. `init`'s fresh Antigravity install uses `--install --fast-check <command>`.
  - **`init` always passes `--project <dir>`.** The project is that directory's git toplevel, and a run outside a repository, or inside the plugin's own tree, is a refusal.
- **Classifying the copies** (AC1, AC3, AC4). Each file is hashed and read as one of four states:
  - `current`: the hash is the current text's.
  - `shipped`: the hash is another text in the table. The plugin wrote it, so it is replaced.
  - `missing`: absent, so it is added.
  - `edited`: any other hash. The report shows a unified diff against the current text, and the file is replaced only when named with `--replace <path>`.

  Refusals:
  - An unreadable file, or a directory where a file should be, is a refusal that names the path.
  - A symlinked copy, or a symlinked `.agents/hooks/` directory, is a question that names the link's target, and nothing is written through it.
  - At start, the script hashes the plugin's own sources and refuses when one is not the table's current text, so a stale table in a plugin is never trusted.

  A pre-0.41.0 install's `scripts/` guards are classified the same way, reported, and never written (AC5).
- **The set is judged whole** (AC7).
  - A kept `edited` `quality-gate.sh` whose text does not run `harness-checks.sh` is a question that names the four checks it would stop running. The report tells `init` to keep the harness checks on the `- Validators:` line while it stays.
  - A kept `edited` `gate-lib.sh` beside replaced gates needs no rule here. The gates' own guards already block on a library older than the gate (`hooks/quality-gate.sh:85-93`), which fails closed, not open.
  - The report's verdict names every kept edit and the set as mixed.
- **Re-rendering `.agents/hooks.json`** (AC2, AC6).
  1. **Parse.** The project's file is parsed with `json`. A file that is not JSON is an unplaced value: the proposal is the current template rendered with a fast check of `true`, plus the question.
  2. **Identify the template by structure.** Each template text is parsed. Entries are aligned by what they run, never by position:
     - a `Stop` or `PreInvocation` entry by the script its command names: `quality-gate.sh`, `review-gate.sh` or `steering-digest-antigravity.sh`;
     - the fast check by being the template's `PostToolUse` entry.

     A template fits when every group, event and entry it carries is present. Within a fitting template:
     - a string holding `{{FAST_CHECK}}` is a pattern that captures the fast check, with `{{HOOKS_DIR}}` read as `.agents/hooks`;
     - every other value is a slot that is either equal or recorded as the project's.

     The fitting template with the fewest recorded values wins. A tie, or no fit, is unplaced. A case asserts that each of the six template texts, rendered, identifies itself.
  3. **Classify the differences.**
     - A gate or digest command that differs from the identified template's is an edited gate entry. It is asked about and written only with `--replace .agents/hooks.json`.
     - A fast check the pattern cannot capture is unplaced. The proposal wraps the project's whole command in the current envelope, and the question shows both.
     - An empty or whitespace-only capture becomes `true`, and the report says so.
     - A template-owned entry the project deleted is unplaced.
  4. **Propose.** The current template, substituted in the parsed structure and written with `json`, so a fast check holding `&` or a quote arrives escaped. It keeps:
     - the fast check;
     - a matcher that differs from the identified template's (so `.*` in a pre-0.37.0 file is that template's own value and becomes the write-tool list);
     - the fast-check group's `enabled` where the identified template had that group;
     - every project-only group and entry, verbatim.

     Gate and digest commands, `timeout`s, event shapes and the marker are the current template's.
  5. **Check before reporting or writing.** Every group whose commands name a gate or the digest is `enabled: true`, by the same rule as `gate_hook_switches` (`hooks/gate-lib.sh:537`). No string holds `{{`. A pre-0.37.0 one-group `enabled: false`, or a later `gate-sdd` `enabled: false`, is unplaced. Its proposal leaves the gates on and, for the first, the fast-check group off, and asks.
  6. **Already current** is decided on the parsed structure, so another whitespace or key order is current and nothing is written.
- **Interface.** `python3 <plugin>/assets/upgrade-install.py --project <dir>` reports and writes nothing.
  - **The report:**
    - each file's class, with its diff where it is `edited`;
    - the hooks-file proposal as a diff;
    - the unplaced values;
    - the questions;
    - a last-line verdict: `nothing to upgrade`, `N change(s) proposed, M question(s)`, `N edit(s) kept, set mixed`, `no install`, or a refusal.
  - **Batch** (AC10). `--project` may repeat in report mode. Each project's report is headed by its path, and the last line names the projects that are behind and the ones refused. The exit code is the worst of them: 1 over 3 over 4 over 0. `--write` with more than one `--project` is a refusal.
  - **Answers:**
    - `--replace <path>`, which may be repeated;
    - `--hooks-json`, to accept the hooks-file proposal;
    - `--fast-check <command>` and `--fast-check-enabled true|false`, applied in the parsed structure;
    - `--install`, for a fresh install.
  - **Writing.** `--write` applies the answered set as one unit. Copies are written only if the hooks file will be current after the run, meaning already current or accepted with `--hooks-json`. Otherwise nothing is written, exit 3, and the reason is named.
    - Each file is written by a rename from a temporary file in its own directory.
    - The temporary file gets the destination's mode, or the source's mode for a `missing` file.
    - A failure part-way exits 1, naming every file already written and the one that failed.
  - **Exit codes:**
    - 0: nothing to upgrade, or all applied;
    - 3: changes or questions pending;
    - 4: no install;
    - 1: a refusal.

    A refusal is never 0. `init` stops on 1, naming the path, and never falls through to a fresh install.
- **`init`'s prose.**
  - **The hooks bullet (`skills/init/SKILL.md:77`)** says how to run the script, ask its questions one at a time and write with the answers. It names the copy set only by citing the table.
  - **A fresh install** runs the script with `--install`.
  - **The Rule at `:114`** says a project with an Antigravity install is upgraded through the script. Its Claude Code half stays, except that the contract sentence at `:80` and the reviewer bullet's "copy it if it differs" (`:75`) go through the script's contract class.
  - **#340's migration step 2** asks only about guards the report calls `edited`. Step 3 keeps any entry the report says a kept gate still needs.
  - **One new pin** in `scripts/check-skill-contracts.py`, for the sentence that runs the script before copying anything. The count becomes 42. Its reason: a re-run that copies over an edited gate is the silent loss AC3 forbids, and removing the sentence would not stand out in review.
- **Records.**
  - **ADR-11** records C1 to C3, and the rejected stamp and current-only options.
  - **`docs/fidelity.md`'s gate-delivery and harness-check rows** say the re-run is defined, and measured after T6.
  - **Both READMEs:**
    - the by-hand loop (`README.md:218-228`) becomes the script run;
    - `:203`, `:218`, `:230` and `:249` say what was run;
    - the contract sentence at `:230` goes through the script.
  - **`docs/verified.md`** gets a new section with AC9's two runs, and `:641` is ticked or narrowed.
  - **`CONTRIBUTING.md` and `.steering/structure.md`** say a change to a copied file rebuilds the table.
- **Affected files:**
  - new: `assets/upgrade-install.py`, `assets/shipped-texts.json`, `scripts/build-shipped-texts.py`, `docs/decisions/ADR-11-*.md`;
  - changed: `skills/init/SKILL.md`, `scripts/test-gates.sh`, `scripts/check-skill-contracts.py`, `.steering/tech.md` (`- Source globs:`), `.steering/structure.md`, `README.md`, `README.ja.md`, `docs/fidelity.md`, `docs/verified.md`, `CONTRIBUTING.md`, `hooks/templates/README.md`.
- **Contract changes, and who consumes them.**
  - The script's flags, classes, verdicts and exit codes are read by `init` alone. The table is read by the script and written by the builder.
  - No gate, hook file or template changes, so an install that is never re-run behaves as before.
  - A new copied file now goes into the table's `copy_set` first.
- **Risks and trade-offs.**
  - **The table grows with each change to a copied file.** Today it holds 103 texts from 14 source paths over 185 first-parent commits, which is a few kilobytes of hashes, plus six templates. It only grows, as `main` does.
  - **A text only a feature branch held reads as `edited`** if a project installed from that branch. That costs a question, not a loss.
  - **Template identification is a structural fit over six shapes.** A tie or no fit is AC6's question, never a guess.
  - **`init` on Antigravity has to name its plugin directory.** It already copies from it, but no variable names it (#340's spec:27). T6's real runs measure this.
  - **The fresh install now goes through the script (AC8).** That widens this spec beyond a re-run: one renderer replaces the prose render that `sed` breaks, and the copy set is stated once. The cost is that a fresh install's prose changes too.

## 3. Tasks (TDD-ordered)

> One task is one complete Red-Green-Refactor cycle, so one green commit. No task is sequenced after the review.

- [x] T1 (C2, C3): a failing case for the table, which does not exist yet. Then `scripts/build-shipped-texts.py`, the generated `assets/shipped-texts.json` and the case. The case covers:
  - `--check` passes on the repository;
  - every current text of the copy set, the contract and the template is present;
  - a seeded change to a copied file without a rebuild fails;
  - a fixture branch that changes a copied file in two commits gives the same table at its tip and at a merge of it;
  - a missing history or ref reports a named skip, never a pass.
- [x] T2 (AC1, AC3, AC4, AC5, AC7, AC8, AC10): failing cases for the copies, then the script's targets, classes, set judgement and writing. The fixtures are built from `gate-sdd--v0.36.0`'s texts with `git show`, behind a reported skip when the tag is absent. The cases cover:
  - `shipped` replaced;
  - the runner and the checks added as `missing`;
  - an `edited` gate kept without `--replace` and replaced with it;
  - a kept edited quality gate reported with the checks it would stop running;
  - an unreadable copy refused;
  - a symlinked copy asked about and not written through;
  - modes kept;
  - a part-way failure exiting 1 with the files named;
  - the `scripts/` guards reported and never written;
  - a Claude Code-only project getting its contract line only, and nothing under `.agents/`;
  - no install exiting 4, and `--install` making one;
  - a batch of three projects (one current, one behind, one unreadable) naming the behind and the refused, exiting 1 and writing nothing; `--write` with two projects refused;
  - a stale table in the plugin refused;
  - a second run changing nothing.
- [x] T3 (AC2, AC4, AC6, AC7): failing cases for the hooks file, then identification, classification, the proposal and the checks. The fixtures are built from the table's own templates, which needs no git. The cases cover:
  - each of the six templates, rendered, identifying itself;
  - a v0.36.0 render with a fast check holding `&` and a quote, kept and escaped, with no `PostToolUse` left in `gate-sdd`;
  - its `.*` becoming the write-tool list;
  - a project matcher on a v0.38.0 render kept;
  - a project group, and a project `Stop` entry placed before the gates, kept;
  - the fast-check group's `enabled: false` kept;
  - a one-group `enabled: false` and a later `gate-sdd` `enabled: false` unplaced and unwritten, then written through `--fast-check-enabled`;
  - an edited gate command asked about;
  - an edited fast-check prefix unplaced;
  - a deleted template entry unplaced;
  - an empty capture becoming `true`;
  - a v0.2.0 render and a non-JSON file unplaced, then written through `--fast-check`;
  - copies pending with the hooks proposal declined, so nothing is written;
  - every written proposal passing `gate_hook_switches`, and none holding `{{`;
  - a whitespace-only difference reading as current.
- [x] T4 (AC1–AC8, the prose): failing pin and citation cases, then:
  - `init`'s hooks bullet and fresh install;
  - the Rule at `:114`, and the contract sentences at `:75` and `:80`;
  - #340's migration steps 2 and 3;
  - both READMEs' by-hand loop and contract sentence;
  - `hooks/templates/README.md`;
  - the new pin.

  A case fails when any of them lists the copy set's files instead of citing the table.
- [x] T5 (records): ADR-11, `docs/fidelity.md`, `CONTRIBUTING.md`, `.steering/structure.md`, and `.steering/tech.md`'s `- Source globs:`. Every validator stays green, and so do the pinned linters on `assets/`.
- [ ] T6 (AC9): the two real `agy` runs, recorded in `docs/verified.md`:
  - **The fixture,** in a trusted folder, installed as `init` at v0.36.0 writes it, with a hand-edited fast check. The plugin is refreshed by `agy plugin uninstall` and `install` to the branch head. Then `init` is re-run, and a later turn shows the gates blocking a seeded failure.
  - **The maintainer's consumer (C6),** on a branch from the commit that holds its install, with nothing pushed without the maintainer's go.

  Then `README.md:203`, `:218`, `:230` and `:249`, their Japanese counterparts, and `docs/verified.md:641` say what was run.
