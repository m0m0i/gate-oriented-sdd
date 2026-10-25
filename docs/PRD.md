# Product requirements

- Serves: re-entry time — the minutes from opening a project after time away until the engineer can answer what was done last, what is in progress and where it stopped, and what is next and why; guardrail, plan adherence (`docs/NORTH_STAR.md`)
- Status: draft

`docs/DESIGN.md` and `docs/ROADMAP.md` cite the capability ids below in prose. Nothing consumes them mechanically yet, and no check requires one to exist; CAP-9 is the capability that would change that.

## Users

- **An engineer with many duties, building real applications in short slots, who designs while agents build** — no three-hour focus block; every slot starts by reloading a project's context, and today that reload is the bottleneck. They want agents to build at full speed without building anything they did not decide. Their projects differ — fresh or with an existing linter, CI and commit style, on Claude Code or Antigravity — but the job is the same, so it is one user.

## Capabilities

### CAP-1 — Review that cannot be declined

- Serves: LV-2
- The user can: rely on a change being unable to end a turn while its spec's tasks are ticked and no fresh CLEAN receipt exists.
- So that: every finished change carries a review the engineer can trust without re-reading the diff, and that receipt is what plan adherence counts.
- Done when: `review-gate.sh` blocks on **both** channels — JSON for Antigravity, exit 2 for Claude Code — every path is pinned by a deterministic case with no model in the loop, and the only way past a block that is not the work's fault is a visible override the engineer approved, which CI checks again.
- Falsified by: the engineer reaching for a bypass instead of a review. #26 found the `git checkout` escape used four times in one week; #175 closed that escape, and the falsifier stands for the next one.

### CAP-2 — Enforcement the project defines, not the hook

- Serves: LV-4
- The user can: change what is enforced in a project by editing `.steering/tech.md`, without editing a hook.
- So that: what a project enforces is one line the engineer can read on re-entry, and it changes with the project rather than with the plugin.
- Done when: `quality-gate.sh` carries no validator commands of its own and runs the `- Validators:` line; a project changes enforcement by changing steering.
- Falsified by: a project's hook scripts being edited to change what runs — which would mean the indirection buys nothing and the line is a worse interface than the file it replaced.

### CAP-3 — Judgment that is independent, and says when it was not

- Serves: LV-2
- The user can: get findings that cite a rule id from a rulebook that cannot drift unnoticed, and read from the receipt whether the review was independent or the author's own.
- So that: the engineer can tell which reviews were independent without re-running them, and a self-review cannot pass as one.
- Done when: `reviewed_by` distinguishes `subagent` from `inline`, and `check-locks.py` fails closed when a rulebook and its lock disagree.
- Falsified by: receipts that are predominantly `inline`. On a fresh install that is a certainty rather than a risk — a reviewer registered mid-session cannot be spawned until restart — which is why `init` has to say so out loud, and why #25 exists.

### CAP-4 — Installation into any of the user's projects

- Serves: LV-4
- The user can: install the harness into a new project or one that already has opinions, and keep its linter, issue templates, commit convention and labels.
- So that: every one of the engineer's projects runs under the same gates, whatever state it was in before, and none is left outside the chain.
- Done when: `init` detects the toolchain and the real validator commands, runs each before adopting it, merges into existing templates rather than replacing them, and arms the gate only on a tree that is already green.
- Falsified by: a first turn blocked by a failure that predates the install. That is the moment the gate gets switched off, and it never gets switched back on.

### CAP-5 — Fixes that reach the projects running it

- Serves: LV-5
- The user can: receive a shipped fix in every project by updating, without copying files.
- So that: no project keeps running a gate already known to be wrong.
- Done when: a change to a shipped path cannot merge without a version bump, checked rather than remembered.
- Falsified by: a merged fix that reaches no project. Historically true — #3 records six commits that shipped and reached no one, because `claude plugin update` gates on version rather than sha.

### CAP-6 — Planning that terminates in something the harness reads

- Serves: LV-2
- The user can: turn a product idea into ordered, typed tracker issues, each sized as one spec, one branch, one pull request.
- So that: "what is next and why" has a written answer the harness can read: the backlog's top row and the capability it serves.
- Done when: every inception skill terminates in state the harness mechanically consumes — the `- Owns:` anchor, `.steering/structure.md`, the reviewer's rulebook, the `- Reconciled against PRD:` lines, and typed issues `spec` reads to choose a shape.
- Falsified by: inception skills producing documents nothing downstream reads. The cascade check (#166) now reads which commit of the PRD each downstream document reconciled against, but nothing reads the capability ids themselves until CAP-9's chain check does.

### CAP-7 — A gate people leave switched on

- Serves: LV-4
- The user can: work ordinary turns without the gate firing on guesses — merged branches, mid-implementation commits, documentation landing after a review.
- So that: the gate stays switched on, because a gate that has been switched off checks nothing.
- Done when: false blocks per real block is measured, silence on those states is pinned by deterministic cases, and every narrowing is a choice of **when** a check runs, never of **what** it checks. A new gate behaviour cannot be added without a case saying when it must not fire.
- Falsified by: a bypass being easier than a review. The old reading of this capability kept the gates silent on work with no spec, and 24 of 31 unreviewed merges in the 2026-10-11 field review were exactly that work; narrowness bought by softening is the failure this capability exists to prevent, not an instance of it.

### CAP-8 — Where you stopped

- Serves: LV-3
- The user can: ask a project what was done last, what is in progress and where it stopped, and what is next and why, and get a right answer quickly and cheaply.
- So that: a free half hour goes to deciding the next piece, not to finding where they stopped.
- Done when: the answer is read from state the harness keeps current — the newest work log's open next steps, the active pull request, the backlog's top row — rather than rebuilt from code and history, and the re-entry check records each answer's correctness, latency and token cost.
- Falsified by: answers that are fast and cheap but wrong — a wrong "what is next" is worse than a slow one — or the engineer still reading code and logs to find their place.

### CAP-9 — Every change traces to a decision

- Serves: LV-2
- The user can: rely on no change to source reaching a merge unless it traces through the whole chain — pull request, spec, issue, backlog item or triage record, PRD capability — with a review receipt at the pull request's head.
- So that: nothing in a project exists that the engineer did not decide, and "why was this built" always has an answer.
- Done when: a change to source with no spec is blocked, dependency manifests and lockfiles counting as source; the chain check runs when the pull request is created and again in CI, and fails closed on a missing link; the only way past is a visible override the engineer approved.
- Falsified by: the chain being intact while the decision was not made first — specs written after the code to satisfy the gate, or overrides becoming routine. Either keeps plan adherence high and the non-negotiable broken.

### CAP-10 — Pieces one engineer can hold

- Serves: LV-1
- The user can: understand and decide each issue, spec and pull request in one short slot, without reading the code.
- So that: the engineer stops being the blocker without stopping being the one who decides.
- Done when: `sprint` and issue creation size each issue so its spec can be decided in one short slot, and split one that cannot; the engineer writes each spec's deciding sentences and approves it from the spec alone.
- Falsified by: approval without reading — specs approved unchanged as a matter of course — or the engineer having to read the diff to learn what a pull request decided.

## Out of scope

- **Being a document generator.** A skill whose only output is prose a human might read does not belong here. That need is met by any writing tool; what this product adds is the mechanical terminus, and a skill without one should be deleted.
- **The agent deciding what to build.** Agents draft, order and build; the sentences that decide — the north star, a capability, a backlog position, a spec's scope — are the engineer's. Met instead by: the engineer, in a short slot, which is what CAP-10 makes possible.
- **Configurable directory names, for now.** `.specs/`, `.steering/`, `.work_logs/` are literal in every skill body, which lets one copy of a skill serve every project without templating. If that changes, it comes in through the roadmap.
- **A language abstraction for reviewers, for now.** Three concrete reviewers people copy, not one abstraction people configure. Met instead by `reviewers/_template/` for an unrecognised stack. A generator that produces a language's reviewer and gates may come later, through the roadmap.
- **Depending on a human reading the diff.** No change is safe only because the engineer read it line by line; the reviewer subagent and the gates do that work. Met instead by: the engineer reviewing each pull request for what it means — does it do what the spec decided, and nothing more — from its description and spec. Reading the diff as well is welcome when there is time.
- **Backward compatibility while pre-release.** A change takes the right design even when it breaks an existing install. Met instead by: version pinning, and release notes that say what to re-run.

## Open questions

- **Does the re-entry check CAP-8 names exist yet?** The 2026-10-19 baseline was a manual run; the north star calls for a scheduled one. Until it exists, CAP-8's "done when" cannot be observed. Answerable by: an issue for the check.
