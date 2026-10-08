# Spec: the stand-down reads an entry that names the copy through `$CLAUDE_PROJECT_DIR`, and every statement of it says when it holds
- Slug: 262-the-stand-down-reads-the-project-dir-form   Issue: 262   Type: bug   Status: approved
- Author: m0m0i   Date: 2026-10-08

## 1. Requirements (WHAT / WHY)

- Reproduction: the issue's. A repository with `.steering/tech.md` and a copy at `.claude/hooks/quality-gate.sh`, whose `.claude/settings.json` runs that copy under `Stop` as `sh "${CLAUDE_PROJECT_DIR:-.}"/.claude/hooks/quality-gate.sh`; run `hooks/plugin-gate.sh quality-gate.sh` from the root as `.claude-plugin/hooks.json` does, then again with the entry `init` wrote, `sh .claude/hooks/quality-gate.sh`. Re-read at `37f86b7` by running case (2)'s extraction, `grep -oE "[^\"' ]*quality-gate\.sh"`, over each spelling an entry can use:

  | Entry names the copy as | Word case (2) tests with `[ -f ]` |
  | :-- | :-- |
  | `sh .claude/hooks/quality-gate.sh` | `.claude/hooks/quality-gate.sh` |
  | `sh \"${CLAUDE_PROJECT_DIR:-.}\"/.claude/hooks/quality-gate.sh` | `/.claude/hooks/quality-gate.sh` |
  | `\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/quality-gate.sh` | `/.claude/hooks/quality-gate.sh` |
  | `sh \"$CLAUDE_PROJECT_DIR/.claude/hooks/quality-gate.sh\"` | `$CLAUDE_PROJECT_DIR/.claude/hooks/quality-gate.sh` |
  | `sh ${CLAUDE_PROJECT_DIR}/.claude/hooks/quality-gate.sh` | `${CLAUDE_PROJECT_DIR}/.claude/hooks/quality-gate.sh` |

- Expected: `skills/init/SKILL.md` step 3, migration step 1: "While those entries remain, the plugin's gates stand down and the project keeps running its stale copies". It is stated without a condition, so it should hold for every entry that runs a copy. The form the issue reproduces is the one Claude Code's hooks documentation asks for: "In shell form, wrap each placeholder in double quotes".

- Actual: with the plain entry the wrapper exits 0 silently; with the variable entry it runs the plugin's gate beside the project's copy, `{}` and exit 0 on a clean tree. Both sets of gates run on every turn: two block messages for one failure, and the validators twice within the quality gate's timeout.

- Impact: a project that rewrote its entries into the `$CLAUDE_PROJECT_DIR` form before migrating, which is what a Claude Code user is told to write. Projects `init` wrote are unaffected: the 0.22.0 template substituted `{{HOOKS_DIR}}` with the plain `.claude/hooks`. The cost is noise and doubled turn-end time, not a fail-open, since the plugin's gate still runs. It is also the stand-down #261's candidate fallback would rely on, and #261 is parked under `## Open, not planned` (cloud sessions are out of scope since 2026-10-07).

- **Root cause:** `hooks/plugin-gate.sh` case (2), lines 113–119. The stand-down tests each word the settings text holds that ends in the gate's name, literally, from the repository root. A word is a run of characters other than `"`, `'` and a space. So a JSON-escaped quote ends a word, and `\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/x` yields `/.claude/hooks/x`, a path at the filesystem root that only happens not to exist. A word that keeps the variable is tested under the variable's own name. Neither resolves to the file the entry runs, so the evidence is never found. The wrapper's comment chooses this on purpose, "which is the noisy direction". Two things make it a bug anyway. The documented form makes the noise the normal case for anyone following Claude Code's docs. And every statement of the stand-down leaves the condition out: `init`, ADR-8, `docs/fidelity.md` and `docs/layout.md`. `hooks/templates/README.md`, which the issue also names, states no stand-down. Both READMEs already carry the condition, citing #262.

- Measured on 2026-10-08 on Claude Code 2.1.293, headless (`claude -p --tools "" --strict-mcp-config --setting-sources project,local --plugin-dir`). The fixture was a scratch plugin and project, each `Stop` hook logging `CLAUDE_PROJECT_DIR` and its cwd:
  - **The plugin's hook and the project's see one value.** Both see `CLAUDE_PROJECT_DIR` set to the launch directory, and both run with that directory as cwd.
  - **A launch below the git root reads three of the four files.** Launched from `sub/` of a git repository, Claude Code read `sub/.claude/settings.json`, `sub/.claude/settings.local.json` and the root's `.claude/settings.local.json`. It did **not** read the root's `.claude/settings.json`. Every hook ran with `sub/` as both cwd and `CLAUDE_PROJECT_DIR`. The control, launched from the root, fired the root's `settings.json` hook. The settings documentation says the shared file is read "from the session's primary working directory". That the local file is read at the root is measured, not documented.
  - **So case (2) can stand down for a hook that never ran.** It reads the git root's two files, and resolves a relative path from the root. In a launch below the root it stands down on a root `settings.json` entry Claude Code never ran. Then no gate runs, when the plugin is enabled at user scope and the root's `settings.json` runs copies of the gates. That root is an unmigrated project, or this repository, whose entries run its source (Clarifications, Q2).

- Acceptance criteria:
  - [ ] **AC1:** WHEN the project's settings name a copy of the gate under its event through `$CLAUDE_PROJECT_DIR`, and the file exists where the variable puts it, THE plugin's gate SHALL stand down. This covers each spelling in the reproduction table, quoted around the variable, quoted around the whole path, or unquoted.
  - [ ] **AC2:** WHEN such an entry names a file that is not on disk where the variable puts it, or the variable cannot be resolved, THE plugin's gate SHALL run. #256's rule stays: the entry and the file together are the evidence.
  - [ ] **AC3:** WHEN an entry reaches the copy through any other variable, THE plugin's gate SHALL run, as today.
  - [ ] **AC4:** WHEN the settings name a file whose name ends in the gate's name without being it (`code-review-gate.sh`), THE plugin's gate SHALL run. This is #256's round-3 MEDIUM.
  - [ ] **AC5:** WHEN a word holds a glob character, THE wrapper SHALL test it as written, never as the shell's expansion of it. The split is the one case 204's matcher does not reach (#256 round 4).
  - [ ] **AC6:** WHEN the `SessionStart` append to `CLAUDE_ENV_FILE` fails, THE wrapper SHALL print nothing on stderr, and still exit 0 with the digest on stdout. This is #263's LOW.
  - [ ] **AC7:** each statement of the stand-down states its condition: `skills/init/SKILL.md` migration step 1, ADR-8 as a dated consequence, `docs/fidelity.md`, `docs/layout.md`, both READMEs' row for pre-0.23.0 copies, and the wrapper's own comment (2). Each also says what a project gets before it migrates when its entries reach the copy some other way: both sets run.
  - [ ] **AC8:** `init`'s dual-target sentence agrees with migration step 3, whose `GATE_SDD_HOOKS` is read before `.agents/hooks/`. This is #263's LOW.
  - [ ] **AC9:** every existing stand-down case keeps its verdict: 207 (a)–(g), 208, and case 220's (g). The new cases for AC1, AC4, AC5, AC6 and AC10 go red against `37f86b7`'s `hooks/` and green after. Those for AC2 and AC3 are pins, green before and after.
  - [ ] **AC10:** WHEN `CLAUDE_PROJECT_DIR` is set, THE wrapper SHALL take the stand-down's evidence from the files that launch reads: `.claude/settings.json` and `.claude/settings.local.json` under `$CLAUDE_PROJECT_DIR`, and the git root's `.claude/settings.local.json`. It SHALL resolve a relative path from the directory the hook started in, which is where the entry's own shell resolves it. A session launched below the root therefore never stands the plugin down on the root's `settings.json`. WHEN `CLAUDE_PROJECT_DIR` is unset, THE wrapper SHALL read the git root's two files, as today. `docs/verified.md` records the measurements above.

- Out of scope:
  - #265, the auto-update observation, next in row 1 and its own spec.
  - #261, the cloud-session fallback, parked.
  - The "unset" diagnosis in the two copied checks naming one cause (#263's LOW). It goes with the next change to the checks, not to the wrapper.
  - `scripts/check-manifests.py`'s per-command wrapper requirement (#256's round-3 LOW). It goes with the next change to that guard.

### Clarifications

Asked and answered 2026-10-08.

- **Q1. #262 offers two halves: the gate, which would resolve `$CLAUDE_PROJECT_DIR`, and the prose, which would state the condition. Which does this spec take?** Both. The documented entry form stands the plugin down. The fixes the record reserved for the wrapper's next change come with it. Every statement of the stand-down names the condition that remains. → AC1–AC9.
- **Q2. The wrapper reads `.claude/settings.json` at the git root, while Claude Code reads it from the launch directory. With the plugin enabled at user scope and a session launched from a subdirectory, unmigrated root entries would make the wrapper stand down for hooks that never ran, so no gate runs. Fold it in, or file it?** Fold it in. The stand-down reads the settings Claude Code read, and falls back to the git root when `CLAUDE_PROJECT_DIR` is unset. The launch from a git subdirectory was measured after this answer, and before the design (the second bullet of the measurements). It found the root's `settings.local.json` read too, which AC10 includes. → AC10.
- **Not asked, because the record answers it:**
  - The wrapper's reserved fixes, AC4 to AC6 and AC8. The 2026-10-07 work log gives the basename filter, `set -f` and the `$CLAUDE_PROJECT_DIR` prefix to the next change to `hooks/plugin-gate.sh`. #263's §4 sends the env-file stderr line and `init`'s dual-target sentence to this spec.
  - Which value the variable resolves to. The one in the wrapper's own environment: the measurement above shows the plugin's hook and the project's hook get the same value. The issue's `.` (the git root) differs from it exactly in a subdirectory launch, which is Q2's case.
  - An unquoted spelling. It is recognised only where the value holds no character the shell would split or expand. Elsewhere the entry would break for the project too, so standing down on it would be the fail-open. That is the gate's own bias, not a choice for the user.
  - The version bump: a patch, as for #254. Shipped `hooks/` and a skill's prose change, and the flow does not move.

## 2. Design (HOW)

- **Fix approach.** Case (2) of `hooks/plugin-gate.sh` asks two questions that Claude Code's own run already answers. Which files did this launch read? Does a command in them run an existing copy of this gate under this event? The case changes in four places, and the statements follow.
  1. **The files (AC10).** The wrapper records its start directory, `_start=$(pwd)`, before it anchors to the git root. With `CLAUDE_PROJECT_DIR` set, the evidence is that directory's `.claude/settings.json` and `.claude/settings.local.json`, plus the root's `.claude/settings.local.json`. A launch at the root reads the local file twice, which costs one grep. With the variable unset, the evidence is the root's two files, as today. The `"command"` grep and the event-key grep are unchanged.
  2. **The words (AC1–AC3).** The extraction admits a JSON-escaped quote inside a word: `([^"' \\]|\\")*<gate>`, in place of `[^"' ]*<gate>`. A word that starts with `\"` is quoted, and every `\"` is then dropped. Then three prefixes are recognised: `$CLAUDE_PROJECT_DIR/`, `${CLAUDE_PROJECT_DIR}/` and `${CLAUDE_PROJECT_DIR:-.}/`. Such a prefix is replaced by the variable's value, and only when the value is non-empty. For an unquoted word the value must also hold no whitespace and none of `*`, `?` or `[`. Any other word holding a `$` is skipped (AC3). An absolute word stays as it is; a relative word is prefixed with `_start`.
  3. **The name and the split (AC4, AC5).** Every resolved word now holds a `/`. It counts only when its last component is the gate's name, `case "$_w" in */"$gate")`. The block runs between a whole-line `set -f` and a whole-line `set +f`, so each word is tested as written. A closed region is the form case 204 reads.
  4. **The env-file append (AC6).** `{ printf … >> "$CLAUDE_ENV_FILE"; } 2>/dev/null || :`. The shell reports a failed redirection before the command's own `2>/dev/null` applies, and a group's redirection covers it.
  5. **The statements (AC7, AC8).** Each document that states the stand-down gets one condition, stated once. The stand-down holds for an entry in the files that launch reads, naming the copy by a relative or absolute path or through `$CLAUDE_PROJECT_DIR`, with the copy on disk. An entry that reaches the copy any other way does not stand the plugin down, and both run until `init` migrates the project. The places:
     - `init`'s migration step 1, and its dual-target sentence, which also says that in CI step 3's `GATE_SDD_HOOKS` is read first.
     - ADR-8, as a dated consequence. Its accepted Decision stays as written.
     - `docs/fidelity.md` and `docs/layout.md`, kept to a clause that points at ADR-8.
     - Both READMEs' row. It loses the #262 caveat, and its evidence cites the new cases by their reports.
     - `docs/verified.md`, which records the measurements.
     - The wrapper's comment (2), which T1–T3 rewrite together with the code.

- **Rejected, and why:**
  - **`.` for the variable, as the issue proposes.** It equals the value only when the session was launched at the git root. Below the root, `.` names the root's copy while the entry runs the subdirectory's. That is AC10's fail-open in a new spelling.
  - **Let the shell expand the command (`eval`).** That runs text from a settings file inside a gate. And a command holds more than the path: `eval` of `[ -f … ] || exit 0; sh …` would exit the wrapper.
  - **Parse the JSON.** ADR-8 rejected this for POSIX `sh`, and it would not help: the fault is in reading the command string, not in finding it.
  - **Resolve every variable from the wrapper's environment.** An entry's shell can set its own (`D=…; sh "$D"/…`), and a plugin's hook carries `CLAUDE_PLUGIN_ROOT` where the project's hook does not, so a match would be a guess. `CLAUDE_PROJECT_DIR` is the variable Claude Code documents for this, and the one measured equal in both hooks.
  - **Resolve a relative word from `$CLAUDE_PROJECT_DIR` instead of `_start`.** The two were equal in every measured launch. `_start` is also where the project's hook was spawned, so it stays right if hooks ever run from a session cwd that has moved, which was not measured.
  - **Read only `$CLAUDE_PROJECT_DIR`'s two files**, as Q2 was put. That misses the root's `settings.local.json`, which the measurement found read below the root. The miss would run both gates: the safe direction, but a known miss.

- **Affected files:** `hooks/plugin-gate.sh`; `scripts/test-gates.sh`; `scripts/check-skill-contracts.py`; `skills/init/SKILL.md`; ADR-8's dated line; `docs/fidelity.md`; `docs/layout.md`; `docs/verified.md`; `README.md` and `README.ja.md`; both manifests at the bump.

- **Blast radius:**
  - **The suite inherits `CLAUDE_PROJECT_DIR` when the quality gate runs it.** The gate is a `Stop` hook, so the variable names this repository, and every wrapper case would read this repository's settings. It joins the top-level `unset`. `run_pg` and case 220's runner set it to the fixture's project, which is what Claude Code did in every measured launch. The unset fallback gets halves of its own.
  - **This repository.** Its entries are relative (`hooks/quality-gate.sh`) and resolve from `_start`. Launched at the root, the plugin stands down as today. Launched below it, Claude Code does not run the root's `settings.json`, and the plugin's gates now run where nothing ran before.
  - **A worktree session, like the one this spec was written in.** The hooks documentation says `CLAUDE_PROJECT_DIR` "stays put" at the session's start, so the wrapper reads the settings that session loaded. It resolves `hooks/…` from the directory the hook was spawned in, as the entry does. Consistent by construction, but not measured.
  - **Projects `init` wrote, and migrated ones,** have no such entries, so nothing changes for them. An unmigrated project with `init`'s entry form, launched at the root, is unchanged as well.
  - **Cases 205–209 and 220 keep their verdicts** (AC9). 207's report keeps its name, because both READMEs cite it.
  - **The digest** runs through the same case, so AC1 holds for `SessionStart` entries too, and one half pins it.
  - **`.steering/tech.md`'s lint paragraph** counts the wrapper's `cd`s, and this design adds none: `_start` is `$(pwd)`.

- **Why this cannot recur:**
  - **The resolution.** The cases name each spelling, each launch and each kind of non-evidence, so a resolution that drops one goes red. AC5's half covers the wrapper's own split, which case 204's matcher does not reach (#256, round 4).
  - **The statements.** `check-skill-contracts.py` pins `init`'s condition, the statement a migrating user follows. **Not closed:** the other statements can lose the condition again, and nothing reads them.

- **Limits, recorded rather than fixed:**
  - **The root's local file is measured, not documented.** If Claude Code stops reading the root's `settings.local.json` below the root, the wrapper reads one file more than the launch does. A relative or `$CLAUDE_PROJECT_DIR` entry there resolves below the root and finds nothing. Only an absolute path to an existing copy could stand the plugin down wrongly, and nothing writes that.
  - **User and managed settings are not read**, as today. An entry there that runs a copy leaves both gates running.
  - **A command that names an existing copy without running it still stands the plugin down.** This is ADR-8's accepted residue, and it now applies to the variable spellings too.

- **Open question for `implement`:** none. The Japanese README row is a draft for the maintainer's reading, as usual.

## 3. Tasks (TDD-ordered)
> One task is one complete Red-Green-Refactor cycle, so one green commit. No task is sequenced after the review.
- [ ] T1: case 207 gains (h) and (i). In (h), an existing `.claude/hooks/code-review-gate.sh` is run under `Stop`, and the review gate runs. In (i), `sh \".claude/hook?/quality-gate.sh\"` is run with the real copy on disk, and the quality gate runs. Both are red against `37f86b7`, which stands down. Then the basename filter and `set -f` across the block → green. AC4, AC5.
- [ ] T2: the suite pins `CLAUDE_PROJECT_DIR`, as Blast radius says. Case 221 covers the variable spellings:
  - each of the reproduction's four variable spellings, with the copy → stand down;
  - the same spellings without the copy → runs;
  - unquoted, with a project path holding a space → runs;
  - `$OTHER/.claude/hooks/…` with the copy → runs;
  - a variable spelling with `CLAUDE_PROJECT_DIR` unset → runs;
  - the digest under `SessionStart` in the documented spelling → stands down.

  The standing-down halves are red against `37f86b7`. Then the extraction and the resolution → green. AC1–AC3, AC9.
- [ ] T3: case 222 is a launch below the root, with `CLAUDE_PROJECT_DIR` and the start directory at `project/sub`:
  - the root's `settings.json` entry with the root's copy → runs, red against `37f86b7`;
  - the root's `settings.local.json` naming `\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/quality-gate.sh`, with the copy under `sub/` → stands down;
  - the same entry with the copy only at the root → runs;
  - a relative entry in the root's local file, with the copy only at the root → runs;
  - `sub/`'s own `settings.json` entry, with the copy under `sub/` → stands down.

  Then the evidence files and `_start` → green. AC10, AC9.
- [ ] T4: case 220 gains a half: `CLAUDE_ENV_FILE` under a directory that does not exist → exit 0, the digest on stdout, nothing on stderr. Red against `37f86b7`, which prints the shell's own error. Then the group redirect → green. AC6.
- [ ] T5: a `check-skill-contracts.py` entry for `init`'s condition, red against the current text. Then the statements Design item 5 lists. `check-readme-claims.py`, `check-markdown-fences.py` and `check-leakage.sh` are the check → green. AC7, AC8, and AC10's record.
