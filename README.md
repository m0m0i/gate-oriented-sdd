# gate-oriented-sdd

[![gate-sdd](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2Fm0m0i%2Fgate-oriented-sdd%2Fmain%2Fplugin.json&query=%24.version&prefix=v&label=gate-sdd&color=blue)](./plugin.json)

*[日本語はこちら →](./README.ja.md)*

**Spec-driven development where the review gate is enforced by a hook, not requested by prose.**

One plugin directory, installing into both [Claude Code](https://claude.com/claude-code) and [Google Antigravity](https://antigravity.google/).

---

## The problem this solves

Most spec-driven setups are a folder convention plus instructions asking the model to follow them. That works until it doesn't. Instructions are advisory: late in a long session, on a task that is nearly finished, a model can simply not run the review step — and nothing notices, because the thing that was supposed to notice was also an instruction.

The result is a process that reports compliance it did not achieve. Which is worse than no process, because you stop checking.

## The idea

Sort every rule by **how much it can be talked out of**, and put it at the layer that matches.

| Layer | Mechanism | Can it be skipped? |
| :-- | :-- | :-- |
| **Process** | skills — `spec`, `clarify`, `implement`, `worklog`, `archive` | Yes. It is guidance, and that is appropriate. |
| **Judgment** | a read-only reviewer subagent with a hash-pinned rulebook | It can be skipped — so a receipt records whether it ran. |
| **Determinism** | `Stop` hook: format, lint, types, and receipt freshness — and, for the last of those, a pull-request check the hook's own weaknesses do not reach | **No.** |

The bottom row is the only one that is a guarantee, and it takes two places to be one. The `Stop` hook is the fast local half; a check on the pull request is the half with no working tree to step out of. Until #26 there was only the hook, and it asked whether you were *standing on* a finished spec branch rather than whether the repository *held* one — so `git checkout main` turned the only enforced rule off and left no trace. The design work is deciding what earns a place in this row — and keeping that list short enough that the gate stays welcome.

### Two things worth stealing even if you don't use this

**The rulebook lives inside the reviewer's directory.** A reviewer's rules sit in `<reviewer>/rules/` beside the reviewer — `reviewers/<reviewer>/rules/` in this plugin, `.claude/agents/<reviewer>/rules/` or `.agents/agents/<reviewer>/rules/` once `init` has installed it — not in `AGENTS.md` (or `CLAUDE.md` / `GEMINI.md`) and not in session context. A normal session never loads them; only the reviewer does, and only the files the diff calls for.

That is measurable rather than asserted. `claude plugin details gate-sdd` reports **~1,000 tokens always-on** for the entire harness — thirteen skills, and no agents. The three reviewers are about 2,100 tokens more, and the rulebooks and the reviewer contract another **~5,900 tokens**. They contribute **zero** to that always-on figure, because the plugin registers none of them: they are files `init` copies into a project. There, the one reviewer the project installed adds its description, about 100 tokens, and its rulebook is read only when it reviews.

The seven inception skills account for ~580 of that always-on total while firing perhaps once per project — a real cost against the same principle this section argues. It is small enough to accept today; if the inception set grows, it should split into a second plugin rather than quietly inflate every session. Reference material you pay for on every turn is reference material you will eventually delete.

**The rulebook is pinned, and pinned honestly.** `rules-lock.json` distinguishes **vendored** files — upstream text reproduced byte-for-byte, whose hash must match upstream — from **derived** files, which are rules written here that cite first-party sources. Upstream moving does not make a derived rule wrong; it makes it *unverified*, which is a different problem with a different fix. Hashing live documentation HTML was tried and rejected: it changes for navigation edits, and an alarm that fires for non-reasons gets switched off.

### Why the gate is narrow

A gate that fires on ordinary turns gets disabled, and a disabled gate protects nothing. So `review-gate.sh` is silent unless this repository holds a branch whose spec has every task ticked and no fresh clean review. It skips merged branches, mid-implementation turns, and the documentation commits that legitimately land *after* a review. What it does not skip is a branch you are not standing on: narrow is a property of the condition, not of where HEAD happens to point, and the difference is what #26 was. `quality-gate.sh` is the other half, and it carries no commands of its own — it runs the `- Validators:` line from `.steering/tech.md`, so enforcement is a property of the project rather than of the hook. The gates' and guards' behaviours are [tested deterministically](./scripts/test-gates.sh) with no model in the loop.

## The flow

**Inception — once per project:**

```
northstar ──▶ prd ──▶ design-doc ──▶ epics ──▶ backlog ──▶ sprint
   metric      capabilities  architecture   demos    ordered,    1 item :
                                                     coarse      N issues
        └───────────────▶ contract ◀───────────────┘
                    coding rules, compiled
                    into the reviewer's rulebook
```

`backlog` produces the **product backlog**: not a pile of known tasks, but the whole of what the product has to achieve, in one ordered list. **Ordered, not prioritized** — a position weighs value, risk, cost, and dependency together rather than flattening them into a label. The ordering is the entire value; a list of everything that must be built is an inventory, not a backlog.

It creates nothing. `sprint` decomposes the top of it into tracker issues — **one backlog item usually becomes several**, since the change, the test coverage it turns out to need, and the migration it forces are different issues with differently shaped specs. Ordering is cheap and reversible; an issue is a commitment, and that is why the two are separate steps.

**Delivery — once per issue:**

```
spec ──▶ clarify ──▶ implement ──▶ reviewer ──▶ worklog ──▶ one PR, closing the issue
         ≤5 questions  Red/Green/Refactor  receipt

archive ····· beside the chain, not a step in it: a sweep of shipped specs out of
              .specs/, run when the directory has grown noisy — not after every merge
```

The issue, the branch, the spec directory, and the PR all share one slug, and the PR closes the issue. The rule is **no issue, no spec**. `sprint` creates typed issues from templates; `spec` refuses to start without one rather than quietly creating it, because a spec written without an issue is something being built that nobody chose. The gate checks it mechanically: the slug is `<issue>-<title>`, so a spec directory without a numeric prefix blocks the turn. `spec` reads the type — `feature`, `bug`, or `chore` — and writes a differently shaped spec for each. A bug pushed through feature scaffolding produces a user story that does not exist and acceptance criteria that are fiction, so the type is not decoration: it decides what the first task is.

**The chain ends at one pull request.** The spec is that PR's first commit rather than a pull request of its own, the work-log entry is one of its last, and the merge is the end — there is no follow-up PR to open. `archive` sits beside the chain for that reason: a `git mv` does not earn a branch, a review and a merge of its own, and nothing mechanical waits on it. The review gate does now look past the branch you are standing on, so a shipped spec left in `.specs/` is within its view — it stays silent about one because the receipt is clean and the branch is merged, which is silence earned — or, where the branch has been deleted, because there is no branch left to read the spec from, which is not. Sweeping is therefore paid per noisy directory, not per merge.

Each inception skill has to terminate in something the harness mechanically uses, or it does not ship: `northstar` produces the quality anchor the reviewer reads for severity, `contract` compiles its enforceable rules into the rulebook, `backlog` orders the list from which `sprint` creates the typed tracker issues `spec` consumes, `design-doc` writes `.steering/structure.md` and the ADRs the reviewer escalates to. A document that ends in prose alone is one this repo has no business generating.

One issue = one spec = one branch = one PR. `clarify` is the phase most setups lack: the dominant failure of spec-driven development is not too little structure, it is a confident spec built on a misread requirement — and review cannot catch that, because the document reads the same either way.

## The minimum set

Thirteen skills is not thirteen required documents, and reading it that way is the fastest route to dismissing this as over-engineering. **Ten of the thirteen are in a minimum install**, and between them they produce **five documents and three issue templates**. Skills and documents are different units, and the two counts do not line up — which is exactly the confusion this section exists to prevent.

```text
skill:     prd   design-doc   backlog  sprint   spec implement worklog
            ↓        ↓           ↓        ↓      ↓      ↓        ↓
produces:  PRD → design doc → backlog → Issue → spec → code → worklog
                                          ↑         + receipt
                               issue templates: feature / bug / chore

also mandatory, off the chain: init, clarify, archive
```

The templates sit **inside** that chain rather than beside it: the Issue step is where the type is decided, and the type is what shapes the spec. Without them the chain still runs — it just produces feature-shaped specs for bugs, with a user story that does not exist and acceptance criteria that are fiction.

Five of the ten produce a document and five do not, which is why counting documents finds the wrong set. `sprint` and `implement` are on the chain even so, because an Issue and a receipt are steps in it without being documents. `init`, `clarify` and `archive` are on it nowhere — `init` installs the harness, `clarify` writes a section inside a spec, `archive` is a `git mv` and a `Status` flip — and all three are mandatory regardless. `archive` is not opt-in for being small: the phase with the least ceremony is the one that accumulates dead specs fastest.

Opt-in, and worth adding when the project justifies it — three skills, each for a different reason:

| Skill | Why it is opt-in |
| :-- | :-- |
| `northstar` | `init`'s interview already produces the `- Owns:` anchor by another route |
| `epics` | nothing consumes it mechanically **yet** — the gap is #166, not a decision |
| `contract` | run before there are commits and review findings to compile, it produces a *worse* rulebook rather than an absent one |

**Every skill is always available.** `init` detects the active harness (Claude Code, Google Antigravity, or both) and installs `.steering/`, `.specs/`, `.work_logs/`, the issue templates, the appropriate rule pointers (`CLAUDE.md` / `GEMINI.md`), the reviewer, and the hooks — never the skills themselves, which ship with the plugin, and on Claude Code not the gates either: the plugin ships them, and `init` writes only the settings that enable it, beside the per-language fast check. The choice above governs which documents get created and which skills are in the flow, never whether one can be run.

**The choice is recorded, not inferred.** `init` writes `- Mode: bootstrap`, `- Mode: minimum` or `- Mode: full` into `.steering/tech.md`, and a checker on the `- Validators:` line verifies the filesystem against it whenever the quality gate runs — and in CI, which is where it actually bites, because the gate runs that line only when source changed and a document is never source. Declared rather than worked out later from which files happen to exist, because that derivation cannot tell a deliberate omission from an abandoned install — and telling those two apart is the only reason the line exists. **A fresh install is `bootstrap`** — the harness is in place and the inception documents are not written yet, which is neither of the other two and used to be recorded as one of them, so every first install armed its own gate red (#127). It expires at the first spec, because that is where a document starts being cited: a state that never ended would be a switch-off with a note attached. **And the choice survives that window.** `init` also records `- Target: minimum` or `- Target: full` — what the operator signed up for, as distinct from what is true yet — and the checker names that target's documents, with the skill that writes each, both in the advisory line and in the block at the first spec. The target changes no verdict: what is required still comes from `- Mode:` alone, so a mistyped target can misdescribe what you owe and can never let a document go unchecked.

**Nothing about enforcement differs between the modes.** Same gates, same reviewer, same receipt, same TDD loop. What differs is how much planning is written before the first spec. The mode is also not a final choice: a `minimum` project runs `contract` the moment review findings start repeating, and `init` re-run against a project that already declared a mode offers the upgrade instead of reinstalling. It moves up, never down.

The middle of that chain is not this plugin's invention — it is **GitHub's**. Issues, branches, pull requests, closed by their PR. They work from pair-programming scale upward; a team of thirty is not the threshold.

## The skills

| Skill | Does | Ends in |
| :-- | :-- | :-- |
| `init` | sets the harness up in a project — detects the toolchain and active harness, asks only what it cannot infer | everything below, wired |
| `northstar` | the metric, its levers, the quality laws in order | the `Owns:` anchor the reviewer reads for severity |
| `prd` | users, capabilities with stable ids, the boundary | ids that specs cite |
| `design-doc` | architecture, its seams, the decisions worth recording | `.steering/structure.md` + ADRs |
| `epics` | capability-sized chunks that each end in a demo | grouped work |
| `backlog` | one ordered list — ordered, not prioritized | the order `sprint` takes from |
| `sprint` | decomposes the top into issues, 1 item : N issues | typed tracker issues |
| `contract` | coding rules, tiered by how they can be checked | the reviewer's rulebook |
| `spec` | one reviewable spec, shaped by the issue's type | the contract `implement` executes |
| `clarify` | ≤5 questions ranked by blast radius, before any design | ambiguity recorded in the spec |
| `implement` | TDD loop, then the mandatory reviewer pass | a receipt the gate checks |
| `worklog` | append-only session record | decisions with their reasons |
| `archive` | shipped specs out of `.specs/`, swept on request | `.specs/` means live work |

Plus three read-only reviewers — TypeScript, Python, Dart/Flutter — and a template for a stack none of them fit. They are reference implementations: `init` copies the closest one into the project, and the plugin registers none of them as an agent. Every reviewer's Bash policy allow-list is strictly bounded to read-only evidence gathering — diff/log, clock, installed version checks and the project's turn-end validators, plus any source a reviewer file names with its reason, such as the hash for its lock check — and a dedicated guard prevents silent drift between `.steering/tech.md`'s `- Validators:` line and the reviewer's allow-list.

## Layout

What the harness writes into a project, and where: [`docs/layout.md`](./docs/layout.md). `.specs/`, `.steering/`, and `.work_logs/` are fixed names; `docs/` is the one location that moves, so a multi-repo product can keep product-level truth in one shared place.

## Install

**Claude Code**

```bash
claude plugin marketplace add m0m0i/gate-oriented-sdd
claude plugin install gate-sdd@gate-oriented-sdd
```

Then run `init` in a project. On Claude Code it writes this declaration into the project's committed `.claude/settings.json`, beside the per-language fast check:

```json
{
  "extraKnownMarketplaces": {
    "gate-oriented-sdd": {
      "source": { "source": "github", "repo": "m0m0i/gate-oriented-sdd" },
      "autoUpdate": true
    }
  },
  "enabledPlugins": { "gate-sdd@gate-oriented-sdd": true }
}
```

That puts the harness in front of everyone who opens the repository. The gates run from the plugin, so a gate fix reaches the project by plugin update, with no pull request in it. `claude plugin install gate-sdd@gate-oriented-sdd --scope project` is not a substitute, because it writes only the `enabledPlugins` half (verified, M1 in [`docs/verified.md`](./docs/verified.md)).

**Google Antigravity** — install either from a standalone release archive or a clone:

*Option 1: Standalone release archive (recommended — excludes repo-internal tooling):*
Download and extract `gate-sdd.zip` from [GitHub Releases](https://github.com/m0m0i/gate-oriented-sdd/releases/latest), then:

```bash
agy plugin install /path/to/extracted/gate-sdd
```

*Option 2: Direct clone:*

```bash
git clone https://github.com/m0m0i/gate-oriented-sdd
agy plugin install ./gate-oriented-sdd
```

Then run `init` inside a project, as on Claude Code. On either harness it reads the repo before it asks you anything, runs each validator before adopting it, and verifies the gate is silent before declaring success.

### Keeping the gates current

Each claim below carries one of three marks. **Verified** names the run in [`docs/verified.md`](./docs/verified.md) or the case in [`scripts/test-gates.sh`](./scripts/test-gates.sh) that produced it. **Documented** names the Claude Code documentation it comes from, and means nothing here ran it. **Not run** means neither.

**Why `"autoUpdate": true` is required.** A third-party marketplace does not auto-update by default. Without it a project stays on whatever version each machine installed, and gate fixes stop arriving: the copy drift 0.23.0 removed, back in a quieter form. With it, an interactive session refreshes the marketplace after its first message, following a random delay of up to ten minutes, and updates the plugin on disk. The running session keeps what it loaded, and the new version loads at the next launch or on `/reload-plugins`. The plugin's manifest pins its version, so an update arrives per release, not per commit. The first of these that is set decides: `autoUpdate` on the marketplace's entry in a settings file, where the highest-precedence file's entry is used whole, so inside the project its own declaration decides; then the toggle under `/plugin` → **Marketplaces**; then the default, off. `DISABLE_UPDATES=1`, `DISABLE_AUTOUPDATER=1` and `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1` turn the pass off unless `FORCE_AUTOUPDATE_PLUGINS=1` is also set. Documented ([plugin loading](https://code.claude.com/docs/en/plugins/loading#when-auto-update-runs), [settings](https://code.claude.com/docs/en/settings-reference#extraknownmarketplaces)); no run here has waited for an update.

**What each kind of drift does.**

| Situation | What happens | Evidence |
| :-- | :-- | :-- |
| A teammate opens the repository for the first time and trusts the folder | The declared marketplace is cloned, and the plugin fetched because its marketplace entry is a relative path. If `/plugin` shows `Plugin "gate-sdd" is enabled in project settings but isn't installed here`, `claude plugin install gate-sdd@gate-oriented-sdd --scope project` once fixes it. | documented ([plugin loading](https://code.claude.com/docs/en/plugins/loading#enabled-in-project-settings-but-not-installed)); not run |
| The plugin enabled at user scope and at project scope, unpinned | One plugin id at one cache path, loaded once. | verified, V4 |
| The user scope declared by `marketplace add`, which writes no `autoUpdate`, and the project declaring it with `autoUpdate` | Inside the project the project's entry is used whole, so auto-update is on there, and the one install it updates is the one every project on the machine loads. | documented ([settings](https://code.claude.com/docs/en/settings-reference#extraknownmarketplaces)); verified, M1 and V4 |
| The project pins a `"ref"` on a machine that already knows the marketplace | The pin is ignored, and the shared clone does not move. | verified, V3 |
| The project pins a `"ref"` on a machine that does not know the marketplace yet | The pin is honoured and becomes the machine's registration, so every project on that machine is held at the tag, and a later unpinned declaration of the same name does not replace it. | verified, M2c, from `--settings`; the trust dialog in front of a project's own file not run |
| The same repository declared under a second marketplace name | A second plugin id. The harness does not deduplicate hooks (V2), and the stand-down reads only the project's settings, so both plugins' gates would run; whether two plugins of one name both load is undocumented. Do not. | not run |
| The project still holds pre-0.23.0 copies in `.claude/hooks/`, with the `Stop` entries that run them | The plugin's gates stand down and the copies run, stale, until `init` migrates the project. Copies with no entry do not stand them down. | verified, `test-gates.sh` cases 207 and 208; no live session yet |
| A clone whose folder is not trusted, or where the plugin is turned off in `.claude/settings.local.json` | No gate runs on turn end, and nothing says so. CI's validators and `check-unreviewed-work.sh` still run on the pull request. | documented ([settings](https://code.claude.com/docs/en/settings-reference#extraknownmarketplaces)); M2b saw an untrusted folder's declaration ignored |
| A cloud session — claude.ai/code, `claude --cloud`, a routine | A cloud session runs the repository's own settings hooks and installs none of the plugins it enables, so a migrated project runs no gate there (#260). | documented ([cloud environments](https://code.claude.com/docs/en/cloud-environments#what-carries-over-from-your-setup)); not run |
| Antigravity | Unchanged: `init` copies the gates into `.agents/hooks/`, and a fix arrives by refreshing the copies. | verified, the copies blocking (`docs/verified.md`, Antigravity hooks); a refresh by re-running `init` not run |

**Pinning.** Do not pin a project. `init` writes the declaration unpinned, and that is the recommendation as well as the default. A `"ref"` in the project's declaration does not hold the project: it holds a machine, and only a machine that met it first (the two pin rows above). One commit then holds some teammates and not others, and holds every other project on the machines it does hold. Not every release is tagged either, so a pin can name only a release with a `gate-sdd--v<version>` tag.

**Updating.**

- **Claude Code, before the next auto-update.** `claude plugin marketplace update gate-oriented-sdd`, then `claude plugin update gate-sdd@gate-oriented-sdd`, then a new session or `/reload-plugins`. Documented ([install](https://code.claude.com/docs/en/plugins/install#update-plugins-now)).
- **A Claude Code project installed before 0.23.0** still has the copies. This prints them, and nothing once the project is migrated:

  ```bash
  ls .claude/hooks/ 2>/dev/null; grep -nE '"(Stop|SessionStart)"' .claude/settings.json
  ```

  Run `init` again. It removes `gate-lib.sh`, `quality-gate.sh`, `review-gate.sh` and `steering-digest.sh` and their `Stop` and `SessionStart` entries, keeps the `PostToolUse` fast check, and writes the declaration, so it is the last pull request a gate fix needs in that project. Not yet run on a real project. **A project worked in cloud sessions keeps its gates there only while it keeps the copies (#260)**, so read that issue before migrating one.
- **Antigravity** has no update command: `agy plugin` at 1.2.16 lists none (verified, #257's section of `docs/verified.md`). Uninstall and install again from a fresh clone or release archive, which has not been run here, then refresh the copies by running `init` again or by hand. Copy the five together, because each gate blocks against a `gate-lib.sh` older than itself:

  ```bash
  P=/path/to/gate-oriented-sdd   # the clone or extracted archive you installed from
  for f in gate-lib.sh quality-gate.sh review-gate.sh steering-digest.sh steering-digest-antigravity.sh; do
    cp "$P/hooks/$f" .agents/hooks/
  done
  ```

- **What a plugin update does not reach, on either harness:** the copies `init` made in the project's scripts directory of `check-steering-anchors.sh`, `check-document-set.py`, `check-unreviewed-work.sh` and `check-locks.py`, the reviewer contract at `_shared/reviewer-contract.md`, and the reviewer and its rulebook. Compare the first two kinds with the plugin and copy what differs, or run `init` again, whose upgrade path is not yet verified. Never overwrite the reviewer: it was adapted to the project, so take what applies by hand and re-pin with `check-locks.py --update`. CI's checkout of the plugin moves only as far as the `ref` its workflow names.

  ```bash
  # P: as above on Antigravity; on Claude Code, the installPath of gate-sdd@gate-oriented-sdd
  # in ~/.claude/plugins/installed_plugins.json. Antigravity's contract is under .agents/agents/.
  for f in check-steering-anchors.sh check-document-set.py check-unreviewed-work.sh check-locks.py; do
    [ -f "scripts/$f" ] && diff -q "$P/assets/$f" "scripts/$f"
  done
  diff -q "$P/reviewers/_shared/reviewer-contract.md" .claude/agents/_shared/reviewer-contract.md
  ```

## Fidelity between the two harnesses

Every row was produced by running it. Method, versions, and open questions: [`docs/verified.md`](./docs/verified.md).

| Capability | Claude Code | Antigravity |
| :-- | :-- | :-- |
| Skills | full | full — same path, same format |
| Reviewer and rulebook | full — `init` copies them into `.claude/agents/`, and the reviewer is invoked by name | full — the same files, copied into `.agents/agents/`, and registered from the file with `define_subagent` |
| Rules discovery | root `AGENTS.md` (canonical context) | `rules/AGENTS.md` (auto-discovered and merged by plugin loader) |
| Quality gate on turn end | full — `Stop`, exit 2 | full — `Stop`, `{"decision":"continue"}` |
| Review-receipt gate | full | full |
| Gate delivery | from the plugin — `.claude-plugin/hooks.json` runs the gates, and a fix arrives by plugin update | copied into `.agents/hooks/` by `init`, and a fix arrives by running `init` again |
| Per-edit fast feedback | full — `PostToolUse` | full — `PostToolUse`, observe-only |
| Steering digest | full — `SessionStart` | full — `PreInvocation` (turn 1 step injection) |
| Context re-injection after compaction | full — `SessionStart` | **none** — no session compaction hook |

The last row is a real gap, not a rounding error. Re-injecting steering after context compaction mid-session has no hook event on Antigravity; initial turn 1 injection is handled via `PreInvocation`.

## Status

**Pre-release.** A reference implementation with a tested-against version matrix, not a supported product. The [eval suite](./evals/) is under development: its four cases are authored, but `claude plugin eval` now rejects them at load, because a `case.yaml` must declare `graders`, so they are still unrun.

Tested against: Claude Code 2.1.289 and Antigravity CLI 1.2.16 (2026-10-06) · Antigravity IDE 2.3.1 (2026-08-21) · macOS.

What *is* verified: the gates' and guards' behaviours, tested deterministically with no model in the loop ([`scripts/test-gates.sh`](./scripts/test-gates.sh) — the count is the suite's, not a number maintained here); Antigravity's `Stop` hook genuinely blocking, run rather than read from documentation ([`docs/verified.md`](./docs/verified.md)); both plugin manifests, the rulebook hashes, and the leakage guard, all in CI; every one of the thirteen skills executed at least once — the inception chain and `init` against this repository or a scratch clone of a real project, `spec`, `clarify`, `implement` and `worklog` on every spec since #17, and `archive` as repeated sweeps of this repository's own shipped specs — with what the inception and `init` runs found recorded in [`docs/verified.md`](./docs/verified.md) and filed as issues; and a review receipt on every spec since #17, under `.specs/`, from a spawned reviewer on all but three, which were reviewed inline and whose receipts say so.

What remains open is tracked in [`docs/verified.md`](./docs/verified.md) and in the issues.

## License

Apache-2.0.
