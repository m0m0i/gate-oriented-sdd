# Decisions

One file per decision that was genuinely contested, named `ADR-<n>-<slug>.md`. A decision with no alternative considered is not a decision, and does not get a file.

Two rules govern this directory, both from the `design-doc` skill that writes into it:

- **Numbers are permanent and sequential.** Before writing ADR-`<n>`, check the existing set *and* any open branches or pull requests — two branches racing for one number is a merge conflict in the one place ids are supposed to be stable.
- **ADRs are append-only.** A decision that changes gets a new ADR that supersedes the old one, and the old one stays, because the reasoning that was once right is what explains the code that still exists.

An ADR listing only benefits is advocacy. Each file below records the consequences its author disliked, which is the half that matters to whoever eventually has to reverse it.

| # | Decision | Status | Decided |
| :-- | :-- | :-- | :-- |
| [1](./ADR-1-the-repository-root-is-the-plugin.md) | The repository root is the plugin — nothing nested, the marketplace entry points at `./`, and `agy plugin install` takes the clone itself | accepted | 2026-08-21 |
| [2](./ADR-2-the-rulebook-lives-in-the-reviewers-directory.md) | The rulebook lives in `agents/<name>/rules/`, loaded on demand by the reviewer and by nothing else, and hash-pinned by `rules-lock.json` | accepted | 2026-08-21 |
| [3](./ADR-3-one-source-globs-line-serves-both-gates.md) | One `- Source globs:` line serves both gates, and the manifests are not on it | accepted | 2026-08-22 |
| [4](./ADR-4-the-spec-is-the-first-commit-not-its-own-pull-request.md) | One issue is one branch, one spec, one pull request — and the spec is the first commit on that branch | accepted | 2026-08-25 |
| [5](./ADR-5-the-version-bump-check-runs-in-ci-only.md) | `check-version-bump.py` runs in CI against the pull request base, and is not on the `- Validators:` line | accepted | 2026-08-22 |
| [6](./ADR-6-this-repository-runs-its-hooks-from-source-and-leaves-its-reviewer-unpinned.md) | This repository's own instance runs the hooks from source and leaves its reviewer unpinned | accepted | 2026-08-24 |
| [7](./ADR-7-documentation-stays-plain-markdown-on-github.md) | Documentation stays plain Markdown read on GitHub, indexed by hand — no site generator, no dependency file, no build | accepted | 2026-09-16 |

ADRs 1 through 6 were decided on the dates above and *recorded* on 2026-09-05, when `design-doc` was first run against this repository. Each file carries both dates, and most name the issue the decision came from.
