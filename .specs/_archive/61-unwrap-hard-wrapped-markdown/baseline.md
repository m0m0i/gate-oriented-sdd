# Baseline — before the unwrap

- Captured: 2026-08-30T09:18:50Z
- HEAD: 857caa8fba917bd73ebf679e6bc4f6ee14f937ae

## Validators

| Command | Exit | Last line |
| :-- | :-- | :-- |
| `./scripts/check-leakage.sh` | 0 | check-leakage: clean |
| `./scripts/check-manifests.py` | 0 | check-manifests: both manifests agree |
| `./scripts/check-receipt-schema.py` | 0 | check-receipt-schema: 7 field(s) agree across 3 copies |
| `./scripts/check-skill-contracts.py` | 0 | check-skill-contracts: 9 skill contract(s) present |
| `./scripts/check-templates.py` | 0 | check-templates: 10 task line(s) across 3 template(s), no split red steps |
| `./assets/check-steering-anchors.sh` | 0 | check-steering-anchors: 5 of 5 anchor(s) resolved, none unreadable |
| `./assets/check-locks.py` | 0 | check-locks: 6 pinned file(s) match their locks in .claude/agents, agents |
| `./scripts/test-gates.sh` | 0 | test-gates: 52 passed, 0 failed |

## Machine-read steering lines — sha256 per line

```
444370bc47bd4f8186c4885a69efe20b819d429119911cc50f443968874225b5  - Owns: gates never fail open
a14c58d23a60d75f90e73d956eedd9e4859f05f547370326a2bec20d3a72557e  - Validators: ./scripts/check-leakage.sh, ./sc
ef63ba7583cb11d45e9c4dddaaa57ce4565d3d8799e6b9c8da266dabaf657f23  - Reviewer: gate-sdd-reviewer
a10b9b57f17d1db7ee3a862d0de96c1f1ba6576c3b7a6265187165e537978cfb  - Source globs: :(glob)skills/**/*.md :(glob)a
c975302ac0129133936c1ecc2556e87bb95128ae9befcfb8eef7df06ff1b4c3d  - Docs: docs/
```

## Mirror pairs — must stay byte-identical

```
8ea0a2e554b188f7f725feee807bc3ad6bec922f23f1de7dbb09437396626afd  agents/_shared/reviewer-contract.md
8ea0a2e554b188f7f725feee807bc3ad6bec922f23f1de7dbb09437396626afd  .claude/agents/_shared/reviewer-contract.md
fb2a08669f14eded350514395e752a7f2d7511b1b699ee7ec2f3a38b370891ee  .github/ISSUE_TEMPLATE/bug.md
fb2a08669f14eded350514395e752a7f2d7511b1b699ee7ec2f3a38b370891ee  assets/issue-templates/bug.md
d2344a97f9e072f07e54e43f95ea7e4f61adc5f390c29b994666c954196c2290  .github/ISSUE_TEMPLATE/feature.md
d2344a97f9e072f07e54e43f95ea7e4f61adc5f390c29b994666c954196c2290  assets/issue-templates/feature.md
bf6eac7756a8e4b696e6017a63f07a24a61b6bff7550736775b00cecbff50cea  .github/ISSUE_TEMPLATE/chore.md
bf6eac7756a8e4b696e6017a63f07a24a61b6bff7550736775b00cecbff50cea  assets/issue-templates/chore.md
```

## Hand-wrapped blocks at baseline

```
  48  .specs/_archive/45-g9-normalisation-asymmetry/spec.md
  42  .specs/55-run-northstar-prd-epics/observations.md
  37  .specs/_archive/28-strippable-assert-guards-receipt-schema/spec.md
  29  .specs/_archive/10-tdd-task-commit-contradiction/spec.md
  21  .specs/_archive/27-spawned-reviewer-deadlocks-stop-gate/spec.md
  19  .specs/55-run-northstar-prd-epics/spec.md
  19  .work_logs/2026-08-25.md
  18  .specs/_archive/34-steering-anchors-unchecked/spec.md
  18  .work_logs/2026-08-24.md
  17  .specs/_archive/16-lock-guard-reports-nothing-as-success/spec.md
  13  .claude/agents/gate-sdd-reviewer/rules/gates-and-guards.md
  13  docs/PRD.md
  12  docs/NORTH_STAR.md
  10  .steering/tech.md
  10  docs/BACKLOG.md
   9  .specs/52-archive-off-the-per-issue-chain/spec.md
   9  .work_logs/2026-08-30.md
   8  .claude/agents/gate-sdd-reviewer/rules/claims-and-prose.md
   8  .work_logs/2026-08-26.md
   8  docs/EPICS.md
   8  docs/verified.md
   7  .specs/_archive/8-gate-false-blocks-draft-spec/spec.md
   7  .specs/_archive/9-receipt-review-provenance/spec.md
   7  .steering/product.md
   7  .work_logs/2026-08-28.md
   6  .specs/55-run-northstar-prd-epics/baseline.md
   5  evals/clarify-before-design/graders/criteria.md
   5  skills/spec/templates.md
   4  .claude/agents/gate-sdd-reviewer.md
   4  .specs/README.md
   4  .steering/structure.md
   4  .work_logs/2026-08-29.md
   4  evals/reviewer-cites-rule/graders/criteria.md
   4  evals/tdd-order-enforced/graders/criteria.md
   3  AGENTS.md
   3  evals/review-gate-blocks/graders/criteria.md
   2  .claude/agents/_shared/reviewer-contract.md
   2  .github/ISSUE_TEMPLATE/bug.md
   2  .github/ISSUE_TEMPLATE/feature.md
   2  .work_logs/README.md
   2  agents/_shared/reviewer-contract.md
   2  agents/_template/rules/starter.md
   2  assets/issue-templates/bug.md
   2  assets/issue-templates/feature.md
   2  evals/review-gate-blocks/prompt.md
   2  skills/implement/SKILL.md
   1  .github/ISSUE_TEMPLATE/chore.md
   1  .specs/_archive/README.md
   1  agents/_template/reviewer.md
   1  assets/issue-templates/chore.md
   1  docs/layout.md
   1  evals/clarify-before-design/prompt.md
   1  evals/tdd-order-enforced/prompt.md
   1  skills/epics/SKILL.md

478 hand-wrapped block(s) across 54 of 83 file(s) on `main`
```
