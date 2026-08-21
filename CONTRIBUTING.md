# Contributing

## The bar for a rule

Every rule in a rulebook must be:

- **Specific.** It names a property that must hold, not a virtue to aspire to. "Be careful with concurrency" is not a rule; "shared mutable state across tasks names its lock, queue, or immutability" is.
- **Checkable.** Two reviewers reading the same diff should flag the same lines. If a rule's application is a matter of taste, it will be argued with and then ignored.
- **Not already enforced.** If the linter or type checker catches it, delete the rule. Duplicated enforcement produces double findings and teaches people to skim the report.
- **Justified by a failure.** State what goes wrong when it is violated. A rule whose rationale is "it reads better" loses every argument it is ever in.
- **Cited.** A rule id, so a finding can be argued with in a commit message six months later.

Six to ten rules per file. A rulebook nobody finishes is a rulebook nobody applies.

## The bar for a change to the enforcement layer

The gates are the reason this repo exists. A change to `hooks/` must:

1. Keep both blocking channels. One script emits JSON for Antigravity **and** exits 2 for Claude Code. A change that serves one harness only is a change that makes the other silently advisory.
2. Keep the gate narrow. It stays silent on merged branches, mid-implementation turns, and post-review documentation commits. A gate that fires on ordinary turns gets switched off, and a switched-off gate protects nothing.
3. Come with a case in `scripts/test-gates.sh`. Nine paths are covered; a tenth behaviour needs a tenth test.

## Before you open a PR

```bash
./scripts/check-leakage.sh      # no private context
./scripts/check-manifests.py    # both manifests agree, hook shapes correct
./scripts/check-locks.py        # rulebooks match their locks
./scripts/test-gates.sh         # the gate still behaves
claude plugin validate . --strict
```

If you edited a rulebook on purpose, re-pin it: `./scripts/check-locks.py --update`.

## What this repo is not

It is not a general agent-configuration framework. If a change adds configuration describing how to describe a language, it is going the wrong way — three concrete reviewers people copy beat one abstraction people configure. That boundary is deliberate and worth defending in review.
