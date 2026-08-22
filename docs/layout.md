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
│       └── 17-parse-durations/    ← archive      shipped, moved with git mv, slug preserved
│
├── .work_logs/
│   └── 2026-08-21.md              ← worklog      append-only session log
│
├── .claude/                       ← init         Claude Code wiring
│   ├── settings.json              ←   the three hook layers
│   ├── hooks/                     ←   gate-lib.sh, quality-gate.sh, review-gate.sh, steering-digest.sh
│   └── agents/
│       ├── reviewer-contract.md   ←   severity, output format, the receipt
│       ├── <name>-reviewer.md     ←   the project's reviewer
│       └── <name>-reviewer/
│           ├── rules/*.md         ←   the rulebook — never enters a normal session
│           └── rules-lock.json    ←   hashes, and what each rule is grounded in
│
├── .agents/                       ← init         Antigravity wiring (same scripts)
│   └── hooks.json
│
└── <your source>                  ← untouched by the harness
```

### The chain

```
inception docs ──▶ backlog ──▶ sprint ──▶ Issue ──▶ branch ──▶ spec ──▶ PR ──▶ Issue closed
                   ordered,     1 item :   └──────────── same slug ────────────┘
                   coarse       N issues
```

The **issue, the branch, the spec directory, and the PR share one slug** — `<issue-number>-<kebab-title>` — and a PR closes its issue. That is the invariant everything else is arranged around, and the review gate checks the first half of it mechanically: a spec directory whose slug has no issue number blocks the turn.

A **milestone** (or Linear cycle, or Jira sprint) is an optional grouping label over issues. Nothing in the chain depends on one — no spec, branch, or PR hangs off it.

### The three fixed names

`.specs/`, `.steering/`, and `.work_logs/` are **not configurable.** Every skill body references them literally, and that is exactly what lets one copy of a skill serve every project with no templating engine and no drift. `docs/` is the one location that moves, because a multi-repo product needs product-level truth in one shared place rather than one copy per repo.

### What is a document and what is state

`docs/` holds decisions — slow-moving, argued over, occasionally re-groomed. `.specs/` and `.work_logs/` hold the record of work — fast-moving, append-only, archived when done. `.steering/` is the bridge: a summary of the decisions, in the form the skills and gates actually read.

## The harness repository

```
gate-oriented-sdd/                 ← the repo root IS the plugin
├── .claude-plugin/
│   ├── plugin.json                ← Claude Code manifest
│   └── marketplace.json           ← this repo is also its own marketplace
├── plugin.json                    ← Antigravity manifest (different path, no collision)
├── skills/<name>/SKILL.md         ← read by BOTH harnesses, one copy
├── agents/
│   ├── _shared/reviewer-contract.md
│   ├── _template/                 ← what init clones for an unrecognised stack
│   └── <lang>-reviewer.md + rules/
├── hooks/
│   ├── gate-lib.sh                ← emits both harnesses' blocking signals
│   ├── quality-gate.sh            ← runs the validators named in .steering/tech.md
│   ├── review-gate.sh
│   ├── steering-digest.sh
│   └── templates/                 ← rendered into the project by init
├── assets/issue-templates/        ← copied into the project's .github/
├── scripts/                       ← the CI guards
├── evals/                         ← authored, not yet run
└── docs/                          ← verified.md, fidelity.md, skill-anatomy.md, layout.md
```
