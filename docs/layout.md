# Layout

Two directory structures matter: the harness repository, and a project after `init` has run in it. They are different, and conflating them is the easiest mistake to make when describing this.

## A project using the harness

```
your-project/
├── docs/                          ← inception documents (the `- Docs:` line in .steering/tech.md)
│   ├── NORTH_STAR.md              ← northstar    the metric, levers, quality laws
│   ├── PRD.md                     ← prd          users, capabilities, boundary
│   ├── DESIGN.md                  ← design-doc   architecture and its seams
│   ├── decisions/
│   │   └── ADR-<n>-<slug>.md      ← design-doc   one file per contested decision
│   ├── EPICS.md                   ← epics        demonstrable chunks
│   ├── BACKLOG.md                 ← backlog      product backlog, ordered, coarse
│   └── CONTRACT.md                ← contract     coding rules, by enforcement tier
│
│   sprint writes NO file. It decomposes backlog items into tracker
│   issues (1 item : N issues) — the issues are the record.
│
├── .github/ISSUE_TEMPLATE/        ← init         feature.md, bug.md, chore.md, config.yml
├── .github/workflows/             ← init         steps added to the project's CI: the copied checks, and on
│                                                 Claude Code a checkout of the plugin, its hooks/ in GATE_SDD_HOOKS
│   
├── .steering/                     ← init         persistent context, read by every skill
│   ├── product.md                 ←   what this is, and `- Owns:` the quality anchor
│   ├── tech.md                    ←   stack, and the machine-read lines the gates parse
│   └── structure.md               ←   where code belongs
│
├── .specs/                        ← spec         LIVE work only
│   ├── 42-add-retry-policy/
│   │   ├── spec.md                ←   Requirements → Design → TDD Tasks
│   │   └── .review-receipt        ← implement    what the reviewer found, and at which SHA
│   └── _archive/
│       └── 17-parse-durations/    ← archive      swept on request, git mv, slug preserved
│
├── .work_logs/
│   └── 2026-08-21.md              ← worklog      append-only session log
│
├── AGENTS.md                      ← init         canonical rulebook, always generated
├── CLAUDE.md                      ← init         pointer for Claude Code (points to AGENTS.md)
├── GEMINI.md                      ← init         pointer for Antigravity (points to AGENTS.md)
│
├── .claude/                       ← init         Claude Code wiring — no gate script: the gates ship from the plugin
│   ├── settings.json              ←   the marketplace declaration, the enabled plugin, the PostToolUse fast check
│   └── agents/
│       ├── _shared/reviewer-contract.md ←  severity, output format, the receipt
│       ├── <name>-reviewer.md     ←   the project's reviewer
│       └── <name>-reviewer/
│           ├── rules/*.md         ←   the rulebook — never enters a normal session
│           └── rules-lock.json    ←   hashes, and what each rule is grounded in
│
├── .agents/                       ← init         Antigravity wiring — the gates are copies here
│   ├── hooks.json                 ←   the hook layers (flat & matcher schema)
│   ├── hooks/                     ←   gate-lib.sh, quality-gate.sh, review-gate.sh, steering-digest.sh,
│   │                                  steering-digest-antigravity.sh
│   └── agents/
│       ├── _shared/reviewer-contract.md ←  severity, output format, the receipt
│       ├── <name>-reviewer.md     ←   the project's reviewer
│       └── <name>-reviewer/
│           ├── rules/*.md         ←   the rulebook — never enters a normal session
│           └── rules-lock.json    ←   hashes, and what each rule is grounded in
│
├── scripts/                       ← init         copied checks, in the project's own scripts directory:
│                                                 check-steering-anchors.sh, check-document-set.py,
│                                                 check-unreviewed-work.sh, check-locks.py
│
└── <your source>                  ← untouched by the harness
```

### Where the gates run from

On Claude Code the gates run from the installed plugin, so `init` writes no gate script. `.claude/settings.json` declares the marketplace with `"autoUpdate": true`, enables the plugin and keeps the per-language fast check, and a gate fix arrives by plugin update (#256, ADR-8). On Antigravity a plugin hook runs with the plugin directory as its working directory, so `init` copies the five scripts into `.agents/hooks/`, and a fix arrives by running `init` again. A dual-target project gets both halves. On either harness, the copied checks in `scripts/` and the reviewer contract change only when someone copies them again or re-runs `init`; a plugin update does not reach them. The README's Install section says how to do each.

### The chain

```
inception docs ──▶ backlog ──▶ sprint ──▶ Issue ──▶ branch ──▶ spec ──▶ PR ──▶ Issue closed
                   ordered,     1 item :   └──────────── same slug ────────────┘
                   coarse       N issues
```

The **issue, the branch, the spec directory, and the PR share one slug** — `<issue-number>-<kebab-title>` — and a PR closes its issue. That is the invariant everything else is arranged around, and the review gate checks the first half of it mechanically: a spec directory whose slug has no issue number blocks the turn.

The chain ends when that PR merges. `archive` is not part of it — shipped specs move to `_archive/` in a sweep run on request, whenever `.specs/` has grown noisy enough that a session's glob returns work that is no longer live.

A **milestone** (or Linear cycle, or Jira sprint) is an optional grouping label over issues. Nothing in the chain depends on one — no spec, branch, or PR hangs off it.

### The three fixed names

`.specs/`, `.steering/`, and `.work_logs/` are **not configurable.** Every skill body references them literally, and that is exactly what lets one copy of a skill serve every project with no templating engine and no drift. `docs/` is the one location that moves, because a multi-repo product needs product-level truth in one shared place rather than one copy per repo.

### What is a document and what is state

`docs/` holds decisions — slow-moving, argued over, occasionally refined. `.specs/` and `.work_logs/` hold the record of work — fast-moving, append-only, archived when done. `.steering/` is the bridge: a summary of the decisions, in the form the skills and gates actually read.

## The harness repository

```
gate-oriented-sdd/                 ← the repo root IS the plugin
├── .claude-plugin/
│   ├── plugin.json                ← Claude Code manifest
│   ├── hooks.json                 ← the Claude Code gates, run from the plugin (#256)
│   └── marketplace.json           ← this repo is also its own marketplace
├── plugin.json                    ← Antigravity manifest (different path, no collision)
├── skills/<name>/SKILL.md         ← read by BOTH harnesses, one copy
├── reviewers/                     ← copied into the project by init; registered by neither harness
│   ├── _shared/reviewer-contract.md
│   ├── _template/                 ← what init clones for an unrecognised stack
│   └── <lang>-reviewer.md + <lang>-reviewer/rules/
├── hooks/
│   ├── gate-lib.sh                ← emits both harnesses' blocking signals
│   ├── quality-gate.sh            ← runs the validators named in .steering/tech.md
│   ├── review-gate.sh
│   ├── plugin-gate.sh             ← what .claude-plugin/hooks.json runs: silent without .steering/,
│   │                                and standing down where a project still runs its own copy
│   │                                through an entry it can resolve; otherwise both run
│   │                                (ADR-8 says which)
│   ├── steering-digest.sh
│   ├── steering-digest-antigravity.sh
│   └── templates/                 ← rendered into the project by init
├── assets/issue-templates/        ← copied into the project's .github/
├── scripts/                       ← the CI guards
├── evals/                         ← under development: authored, unverified
└── docs/                          ← verified.md, fidelity.md, skill-anatomy.md, layout.md,
                                     and the inception documents this repo wrote about itself:
                                     NORTH_STAR, PRD, EPICS, BACKLOG, CONTRACT, DESIGN, decisions/
```

### Distribution artifact (`gate-sdd.zip`) vs direct clone

The repository root contains both the runtime plugin payload and this harness's internal development tooling (`.specs/`, `.steering/`, `.work_logs/`, `scripts/`, `evals/`, `docs/`).

- **Direct `git clone` or local path install** (`agy plugin install ./gate-oriented-sdd`): Clones or unpacks the whole repository. The agent runtime safely ignores unrecognized directories via progressive disclosure (only loading `plugin.json`, `skills/`, `agents/`, `hooks/`, `rules/`; this plugin has no `agents/`, on purpose — #235), but extraneous files remain visible in workspace search or status.
- **CI Release distribution artifact** (`gate-sdd.zip`): Built on tag release via `.github/workflows/release.yml` and `scripts/package-release.py`. Contains strictly the runtime payload (`plugin.json`, `.claude-plugin/`, `skills/`, `reviewers/`, `hooks/`, `rules/`, `assets/`, `AGENTS.md`, `README.md`, `README.ja.md`, `LICENSE`), excluding all internal development tooling. Consumers wanting a completely isolated plugin directory can download and unpack `gate-sdd.zip`.

#### Rejected alternatives (Issue #140)

- **Option 1 (`.gitattributes export-ignore`)**: Rejected because marketplace installs and local development workflows clone the repository via git. Export-ignore attributes only affect archive generation and never apply to git clone operations.
- **Option 2 (`plugins/gate-sdd/` subfolder layout)**: Rejected because it violates the foundational design ("the repo root IS the plugin") and breaks the dual-manifest arrangement, requiring moves of both manifests, `marketplace.json`, guard scripts, and downstream references in one disruptive change.

