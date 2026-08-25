# gate-oriented-sdd

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
| **Judgment** | a read-only reviewer subagent with a vendored, hash-pinned rulebook | It can be skipped — so a receipt records whether it ran. |
| **Determinism** | `Stop` hook: format, lint, types, and receipt freshness | **No.** |

The bottom row is the only one that is a guarantee. The design work is deciding what earns a place there — and keeping that list short enough that the gate stays welcome.

### Two things worth stealing even if you don't use this

**The rulebook lives inside the agent's directory.** A reviewer's rules sit in `agents/<reviewer>/rules/`, not in `CLAUDE.md` and not in session context. A normal session never loads them; only the reviewer does, and only the files the diff calls for.

That is measurable rather than asserted. `claude plugin details gate-sdd` reports **~1,300 tokens always-on** for the entire harness — thirteen skills and three reviewers. The rulebooks and the reviewer contract are another **~5,900 tokens**, and they contribute **zero** to that always-on figure, because they are not registered components at all.

The six inception skills account for ~450 of that always-on total while firing perhaps once per project — a real cost against the same principle this section argues. It is small enough to accept today; if the inception set grows, it should split into a second plugin rather than quietly inflate every session. Reference material you pay for on every turn is reference material you will eventually delete.

**The rulebook is pinned, and pinned honestly.** `rules-lock.json` distinguishes **vendored** files — upstream text reproduced byte-for-byte, whose hash must match upstream — from **derived** files, which are rules written here that cite first-party sources. Upstream moving does not make a derived rule wrong; it makes it *unverified*, which is a different problem with a different fix. Hashing live documentation HTML was tried and rejected: it changes for navigation edits, and an alarm that fires for non-reasons gets switched off.

### Why the gate is narrow

A gate that fires on ordinary turns gets disabled, and a disabled gate protects nothing. So `review-gate.sh` is silent unless a spec branch has every task ticked and no fresh clean review. It skips merged branches, mid-implementation turns, and the documentation commits that legitimately land *after* a review. `quality-gate.sh` is the other half, and it carries no commands of its own — it runs the `- Validators:` line from `.steering/tech.md`, so enforcement is a property of the project rather than of the hook. 33 paths across the two, [tested deterministically](./scripts/test-gates.sh) with no model in the loop.

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
spec ──▶ clarify ──▶ (review PR) ──▶ implement ──▶ reviewer ──▶ worklog ──▶ archive
         ≤5 questions               Red/Green/Refactor   receipt
```

The issue, the branch, the spec directory, and the PR all share one slug, and the PR closes the issue. The rule is **no issue, no spec**. `sprint` creates typed issues from templates; `spec` refuses to start without one rather than quietly creating it, because a spec written without an issue is something being built that nobody chose. The gate checks it mechanically: the slug is `<issue>-<title>`, so a spec directory without a numeric prefix blocks the turn. `spec` reads the type — `feature`, `bug`, or `chore` — and writes a differently shaped spec for each. A bug pushed through feature scaffolding produces a user story that does not exist and acceptance criteria that are fiction, so the type is not decoration: it decides what the first task is.

Each inception skill has to terminate in something the harness mechanically uses, or it does not ship: `northstar` produces the quality anchor the reviewer reads for severity, `contract` compiles its enforceable rules into the rulebook, `backlog` creates the tracker issues `spec` consumes, `design-doc` writes `.steering/structure.md` and the ADRs the reviewer escalates to. A document that ends in prose alone is one this repo has no business generating.

One issue = one spec = one branch = one PR. `clarify` is the phase most setups lack: the dominant failure of spec-driven development is not too little structure, it is a confident spec built on a misread requirement — and review cannot catch that, because the document reads the same either way.

## The minimum set

Thirteen skills is not thirteen required documents, and reading it that way is the fastest route to dismissing this as over-engineering. Six documents and three templates are mandatory; the rest earn their place when a project is large enough to need them.

```text
PRD → design doc → backlog → Issue → spec → worklog
                               ↑
                    issue templates: feature / bug / chore
```

The templates sit **inside** that chain rather than beside it: the Issue step is where the type is decided, and the type is what shapes the spec. Without them the chain still runs — it just produces feature-shaped specs for bugs, with a user story that does not exist and acceptance criteria that are fiction.

Optional, and worth adding when the project justifies them: `northstar`, `epics`, `contract`, and `archive`.

The middle of that chain is not this plugin's invention — it is **GitHub's**. Issues, branches, pull requests, closed by their PR. They work from pair-programming scale upward; a team of thirty is not the threshold.

## The skills

| Skill | Does | Ends in |
| :-- | :-- | :-- |
| `init` | sets the harness up in a project — detects the toolchain, asks only what it cannot infer | everything below, wired |
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
| `archive` | shipped specs out of `.specs/` | `.specs/` means live work |

Plus three read-only reviewers — TypeScript, Python, Dart/Flutter — and a template for a stack none of them fit.

## Layout

What the harness writes into a project, and where: [`docs/layout.md`](./docs/layout.md). `.specs/`, `.steering/`, and `.work_logs/` are fixed names; `docs/` is the one location that moves, so a multi-repo product can keep product-level truth in one shared place.

## Install

**Claude Code**

```bash
claude plugin marketplace add m0m0i/gate-oriented-sdd
claude plugin install gate-sdd@gate-oriented-sdd
```

**Google Antigravity** — no git-based plugin install exists yet, so clone first:

```bash
git clone https://github.com/m0m0i/gate-oriented-sdd
agy plugin install ./gate-oriented-sdd
```

Then run `init` inside a project. It reads the repo before it asks you anything, runs each validator before adopting it, and verifies the gate is silent before declaring success.

## Fidelity between the two harnesses

Every row was produced by running it. Method, versions, and open questions: [`docs/verified.md`](./docs/verified.md).

| Capability | Claude Code | Antigravity |
| :-- | :-- | :-- |
| Skills, reviewers, rulebooks | full | full — same path, same format |
| Quality gate on turn end | full — `Stop`, exit 2 | full — `Stop`, `{"decision":"continue"}` |
| Review-receipt gate | full | full |
| Per-edit fast feedback | full — `PostToolUse` | full — `PostToolUse`, observe-only |
| Steering re-injection after compaction | full — `SessionStart` | **none** — no such event |

The last row is a real gap, not a rounding error. `PreInvocation` is the candidate substitute and needs a once-per-session guard before it is worth shipping.

## Status

**v0.2.3 — pre-release.** A reference implementation with a tested-against version matrix, not a supported product. The [eval suite](./evals/) is authored but has never been run — `claude plugin eval` is in early access and was not enabled on the account this was built on, and claiming a green suite that never ran is exactly the unverified assertion this harness exists to prevent.

Tested against: Claude Code 2.1.238 · Antigravity CLI 1.1.17 · Antigravity IDE 2.3.1 · macOS.

What *is* verified: the two gates' 33 behaviours, tested deterministically with no model in the loop ([`scripts/test-gates.sh`](./scripts/test-gates.sh)); Antigravity's `Stop` hook genuinely blocking, run rather than read from documentation ([`docs/verified.md`](./docs/verified.md)); both plugin manifests, the rulebook hashes, and the leakage guard, all in CI.

What is not: the skills themselves have never been executed end to end, and no reviewer has yet reviewed a real diff.

## License

Apache-2.0.
