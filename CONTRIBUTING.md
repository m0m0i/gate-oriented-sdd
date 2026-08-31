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
3. Come with a case in `scripts/test-gates.sh`. 54 paths are covered; a 55th behaviour needs a 55th test.

## Releasing

**Bump `version` in both manifests, or the release does not exist.** A consumer running `claude plugin update` against an unchanged version is told "already at the latest version" and silently keeps the old content — the update appears to succeed and nothing changes.

This used to be a habit. It is now a check: `scripts/check-version-bump.py` fails a pull request that touches `skills/`, `agents/`, `hooks/`, `assets/`, or a manifest without moving the version, and `scripts/check-manifests.py` still fails when the two manifests disagree about what that version is. Six commits shipped before the guard existed and none of them reached anyone, including a fix to `agents/_template/reviewer.md` that every non-TS/Python/Dart project needed.

**A `#non-breaking` change still needs a bump.** Semver describes compatibility; the updater cares about reachability. An unreachable fix is not a fix, and the marker is about the first thing while the problem is the second.

Editing `docs/`, `evals/`, `scripts/`, CI, or the READMEs does not require a release, and the guard stays quiet for those. That exemption is what keeps it from firing on most PRs — a guard that cries wolf gets deleted, which is the same argument `rules-lock.json` makes about hashing live documentation.

```bash
claude plugin tag        # creates {name}--v{version}, validating manifest against marketplace entry
```

## Markdown is not hand-wrapped

A paragraph is one line, and the reader's app decides the width. This applies to every Markdown file in the repository — skills, rulebooks, steering, specs, work logs, documents. Do not break prose at a column, and do not "fix" a long line you find.

It is written down because nothing enforces it and it was already inferred wrongly once: a reviewer twice cited "repo convention" for a wrap width it had taken from the file it was reading, which had been written minutes earlier in the same session. A convention nothing states gets enforced from whatever happens to be nearby.

Tables and YAML front matter keep their line breaks — those are structure, not wrapping. So do the machine-read `- Validators:` / `- Reviewer:` / `- Source globs:` / `- Docs:` / `- Owns:` lines in `.steering/`, which the gates read with `sed … | head -1` and which must each stay on one physical line for a different reason.

A fence keeps its line breaks when it holds literal code, output, or a line-sensitive format — and **the fence's language tag decides which, because the property that matters is the content and not the delimiter.** A ` ```markdown ` fence quotes Markdown, so the Markdown inside it follows this convention like every other Markdown in the repository. An untagged fence does not: `implement`'s `reviewed_sha=` receipt block and the reviewer contract's `[SEVERITY] <file>:<line>` format are formats where a line break is meaningful, and unwrapping either would destroy one. `scripts/check-markdown-fences.py` enforces exactly that split.

Stating the carve-out by delimiter instead is what #64 cost: the skills that generate this repository's own documents went on emitting the wrapping the convention had just removed, and the next reader, applying the rule correctly, would have put it back.

## Before you open a PR

```bash
./scripts/check-leakage.sh          # no private context
./scripts/check-manifests.py        # both manifests agree; hook shapes correct
./scripts/check-receipt-schema.py   # the receipt schema agrees across its copies
./scripts/check-skill-contracts.py  # skills still carry their load-bearing instructions
./scripts/check-templates.py        # no spec template splits a red step from its green step
./scripts/check-markdown-fences.py  # no ```markdown fence hand-wraps the Markdown it quotes
./assets/check-steering-anchors.sh  # steering's machine-read lines still parse
./assets/check-locks.py             # rulebooks match their locks (--update to re-pin)
./scripts/test-gates.sh             # the gates still behave
./scripts/check-version-bump.py     # shipped changes carry a version bump (PR-only in CI)
claude plugin validate . --strict
```

If you edited a rulebook on purpose, re-pin it: `./assets/check-locks.py --update`.

It sits in `assets/` rather than `scripts/` because projects need a copy of it, not a reference to it — `init` installs it so a project can re-pin its own rulebook. That also puts it on a shipped path, so a fix to it is covered by the version guard.

## What this repo is not

It is not a general agent-configuration framework. If a change adds configuration describing how to describe a language, it is going the wrong way — three concrete reviewers people copy beat one abstraction people configure. That boundary is deliberate and worth defending in review.
