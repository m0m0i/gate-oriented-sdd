# Product requirements

- Serves: verified-merge rate — the share of merged changes carrying a fresh CLEAN receipt obtained independently (`docs/NORTH_STAR.md`)
- Status: draft

Nothing cites the capability ids below yet. That is recorded deliberately rather than left to be discovered — see `docs/verified.md` and #22.

## Users

- **Running an agent against a codebase and needing the review step to be a fact** — today they write the review step into `CLAUDE.md` or `AGENTS.md` and find out it was skipped when a defect lands. The instruction that was supposed to catch the skip was also an instruction.
- **Adopting the harness into a repository that already has conventions** — a linter, CI, issue templates, a commit style. They want enforcement added, not their conventions replaced, and a first turn that is not blocked by a failure predating them.
- **Reading it as a reference implementation of hook-enforced process** — they will copy two or three ideas and never install it. This user is real and the README is written for them, but no capability below is built for them.

## Capabilities

### CAP-1 — Review that cannot be declined

- Serves: LV-1
- The user can: rely on a change being unable to end a turn while its spec's tasks are ticked and no fresh CLEAN receipt exists.
- Done when: `review-gate.sh` blocks on **both** channels — JSON for Antigravity, exit 2 for Claude Code — and every path is pinned by a deterministic case with no model in the loop.
- Falsified by: users reaching for a bypass instead of a review. **This is currently firing.** #26 records the `git checkout` escape being used four times in one week, which says the gate is enforced against the model and negotiable by the human. A capability whose falsifier is live is worth more written down than quietly restated as a success.

### CAP-2 — Enforcement the project defines, not the hook

- Serves: LV-1, LV-4
- The user can: change what is enforced by editing `.steering/tech.md`, without editing a hook.
- Done when: `quality-gate.sh` carries no validator commands of its own and runs the `- Validators:` line; a project changes enforcement by changing steering.
- Falsified by: projects editing the hook scripts to change what runs — which would mean the indirection buys nothing and the line is a worse interface than the file it replaced.

### CAP-3 — Judgment that is independent, and says when it was not

- Serves: LV-3
- The user can: get findings that cite a rule id from a rulebook that cannot drift unnoticed, and read from the receipt whether the review was independent or the author's own.
- Done when: `reviewed_by` distinguishes `subagent` from `inline`, and `check-locks.py` fails closed when a rulebook and its lock disagree.
- Falsified by: receipts that are predominantly `inline`. On a fresh install that is not a risk but a certainty — a reviewer registered mid-session is not spawnable until restart — which is why `init` is required to say so out loud, and why #25 exists.

### CAP-4 — Installation into a repository that already has opinions

- Serves: LV-4
- The user can: install the harness into an existing project and keep their linter, their issue templates, their commit convention, and their labels.
- Done when: `init` detects the toolchain and the real validator commands, runs each before adopting it, merges into existing templates rather than replacing them, and arms the gate only on a tree that is already green.
- Falsified by: a user's first turn blocked by a failure that predates them. That is the moment the gate gets switched off, and it never gets switched back on.

### CAP-5 — Fixes that reach the people running it

- Serves: LV-5
- The user can: receive a shipped fix by updating.
- Done when: a change to a shipped path cannot merge without a version bump, checked rather than remembered.
- Falsified by: a merged fix that reaches nobody. Historically true — #3 records six commits that shipped and reached no one, because `claude plugin update` gates on version rather than sha.

### CAP-6 — Planning that terminates in something the harness reads

- Serves: LV-4
- The user can: turn a product idea into ordered, typed tracker issues, each sized as one spec, one branch, one PR.
- Done when: every inception skill terminates in state the harness mechanically consumes — the `- Owns:` anchor, `.steering/structure.md`, the reviewer's rulebook, and typed issues `spec` reads to choose a shape.
- Falsified by: inception skills producing documents nothing downstream reads. **Currently true for two of them.** `PRD.md` and `EPICS.md` have no mechanical consumer in this repository as of this run; `.steering/product.md` says the project is not a document generator, and this capability is the one that claim rests on. See #22 and `docs/verified.md`.

### CAP-7 — A gate people leave switched on

- Serves: LV-2
- The user can: work ordinary turns without the gate firing — merged branches, mid-implementation commits, documentation landing after a review, branches with no spec at all.
- Done when: silence on those states is pinned by deterministic cases, so narrowness is a tested property rather than a claim, and a new gate behaviour cannot be added without a case saying when it must **not** fire.
- Falsified by: a bypass being easier than a review. Distinct from CAP-1's falsifier and pointing at the same evidence: #26 records four uses in one week, which is as much a statement about false blocks as about the escape existing.

## Out of scope

- **Being a document generator.** A skill whose only output is prose a human might read does not belong here. That need is met by any writing tool; what this product adds is the mechanical terminus, and a skill without one is a skill that should be deleted.
- **Configurable directory names.** `.specs/`, `.steering/`, `.work_logs/` are literal in every skill body. Met instead by: not needing it — literal paths are what let one copy of a skill serve every project without templating.
- **A language abstraction for reviewers.** Three concrete reviewers people copy, not one abstraction people configure. Met instead by `agents/_template/` for an unrecognised stack.
- **Replacing human review.** The judgment layer is a first pass with a citable rulebook, not an approver. Met instead by the pull request, which is still where a person reads the diff.
- **Being a supported product.** Pre-release, with a tested-against version matrix.

## Open questions

- **Does CAP-6 survive its own falsifier?** Two of the six inception skills currently produce documents nothing reads. Either something must come to consume them, or the capability is narrower than stated and `prd`/`epics` are out of scope by this document's own boundary. Answerable by: #22, and the run recording this.
- **Is the third user real enough to serve?** The reference-implementation reader gets the README and nothing else. If no capability is ever built for them, the honest move is to delete the user rather than carry it. Answerable by: the author.
