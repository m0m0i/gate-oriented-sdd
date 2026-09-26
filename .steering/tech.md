# Tech — gate-oriented-sdd

Shell (POSIX `sh`), Python 3 (stdlib only, no dependency file anywhere), and Markdown. There is no package manager and no build. The repository root *is* the installable plugin.

Machine-read lines. Each must stay on ONE physical line — the gates read them with `sed ... | head -1`, so a wrapped value is truncated at the first newline without complaint.

- Validators: ./scripts/check-leakage.sh, ./scripts/check-manifests.py, ./scripts/check-markdown-fences.py, ./scripts/check-receipt-schema.py, ./scripts/check-skill-contracts.py, ./scripts/check-templates.py, ./assets/check-steering-anchors.sh, ./assets/check-locks.py, ./assets/check-document-set.py, ./scripts/check-contract-path.py, ./scripts/check-readme-claims.py, ./scripts/check-reviewer-allow-list.py, ./scripts/test-gates.sh
- Reviewer: gate-sdd-reviewer
- Source globs: :(glob)rules/**/*.md :(glob)skills/**/*.md :(glob)agents/**/*.md :(glob)hooks/**/*.sh :(glob)assets/**/*.py :(glob)assets/**/*.sh :(glob)assets/**/*.md :(glob)scripts/**/*.py :(glob)scripts/**/*.sh
- Docs: docs/
- Mode: full

## Why `check-version-bump.py` is not on the Validators line

`./scripts/check-version-bump.py` is CI-only, on pull requests. It is deliberately **not** a turn-end validator: mid-implementation a shipped file is routinely edited before the version moves, so running it on every turn would block normal work and teach the user to switch the gate off. CI runs it once, against the PR base, which is the moment the question is actually meaningful.

## Why `check-unreviewed-work.sh` is not on the Validators line either

`./assets/check-unreviewed-work.sh` is CI-only, on pull requests, for a different reason than
`check-version-bump.py` above. It is not that running it per turn would block normal work — it
is that `review-gate.sh` already asks its question on every turn end, and asks it better there,
in the second person, of the person who can act on it. A copy on the `- Validators:` line would
produce a second block in the same place, worded differently, for the same fact.

What CI adds is not a second opinion but a different property. A hook can be switched off, and
HEAD can be moved; a pull request can do neither, and its head branch and head commit come from
the event rather than from wherever the checkout is standing. That is the whole of #26: the one
enforced rule in this harness was one `git checkout` from silent, and a layer with no working
tree is where the guarantee can actually live.

Both callers ask `gate_spec_review_state` in `hooks/gate-lib.sh` rather than carrying the
question themselves, which is the same reason `check-steering-anchors.sh` calls
`gate_steering_read`: a copy that can disagree with its subject is #14 and #23.

## Why `Source globs` excludes the manifests, and what that costs

Since 0.2.4 this one line answers **two different questions**: the review gate asks "what re-stales a receipt?" and the quality gate asks "what should trigger the validators?". Those have different right answers for the manifests, and the line can only give one.

A version bump lands *after* the review — as a **step of `implement`** rather than as a task, which is #113 — in the same family as the work-log entry and the `Status: done` flip, so including `plugin.json` here would re-stale a receipt on every single spec and force a second review of a one-character change. Excluded, therefore.

The distinction between a step and a task is load-bearing rather than pedantic. This paragraph used to say only that the bump lands after the review, and a spec that wrote it as its last task therefore held one checkbox unticked for the whole review — which is precisely the state `review-gate.sh` reads as "still implementing", so the gate stayed silent through the review it exists to demand. `scripts/check-templates.py` now fails on a live spec that defers a task, and `scripts/check-skill-contracts.py` pins the step in `implement`.

**The cost is explicit:** a commit touching only a manifest does not run the validators locally, so `check-manifests.py` will not catch a version disagreement on that turn. CI runs it on every pull request, which is the backstop. This is a reasoned trade — local speed against a check that is duplicated in CI — not an oversight, and it is recorded on #14.

Also on #14: this line duplicates by hand the definition `scripts/check-version-bump.py` holds in its `SHIPPED` tuple, and nothing detects them disagreeing.

`:(glob)` is load-bearing. The value is interpolated unquoted, so a bare `*.py` would be expanded by the shell against the repository root before git ever saw it. `:(glob)` matches no file on disk, so the shell leaves the word alone. This is #1, and it failed silently for three releases.

## Why `check-backlog-tracker.py` is not on the Validators line either

A third exclusion, and unlike the two above it is a capability rather than a judgment. Those two are calls about noise and duplication — one would block normal work mid-implementation, the other would print a second copy of a question already asked better elsewhere. This one cannot run in a hook at all: it compares `docs/BACKLOG.md` against the tracker, so it needs the network and an authenticated `gh`. A `Stop` hook that reaches the network is a turn that hangs when the network is down, and a gate that hangs is a gate switched off — which is the failure this project does not own but still has to avoid.

So it runs in CI on pull requests, and by hand as `./scripts/check-backlog-tracker.py`. By hand is where a grooming should start: what it reports is the diff between the list and the tracker, which is the part of a grooming nobody can do from memory.

It is also the one guard here deliberately **not** shipped. The shipped form needs a machine-read tracker line and a declared command to list issues, and that contract belongs to #128. Until it exists, `backlog` terminates in nothing a consumer's harness reads — C-4 open for them, stated here rather than implied. #79.

## Why the `lint` job is not on the Validators line either

A fourth exclusion, for a reason none of the three above give. `.github/workflows/ci.yml`'s `lint`
job holds `assets/` — the one shipped path whose files are copied into a consumer's tree and then
named on that consumer's `- Validators:` line — to a consumer's toolchain: `ruff check` and
`ruff format --check` under a common configuration, and `shellcheck -s sh`. Neither tool is
installed on the machine this repository is developed on, and the first paragraph of this file is
why nothing here installs one. A `- Validators:` entry for a command that is absent locally would
fail on the developing machine rather than in CI, and a turn-end gate that reports on a toolchain
it never found is #195's shape: the person it blocks switches it off, which is the outcome every
exclusion in this file exists to avoid.

So it runs in CI, on pull requests and on pushes to `main`, as its own job rather than as steps in
`guard`, so that a red check names a lint drift and not a guard catching a defect. Its two pins are
the job's and move by hand. By hand it is the job's three commands with the same pins — on #81 they
were run through `uvx`, which installs nothing into the repository. The subject is narrow on
purpose: `scripts/` is never copied anywhere, and `hooks/gate-lib.sh` carries four deliberate
`SC2086`s (`$_globs` must word-split, above), so neither is linted, and both are recorded as such on
#81's spec rather than left for the next person to "fix". #81.

## Commit and branch convention

Conventional commits — `feat:`, `fix:`, `docs:`, `chore:` — subject in the imperative, body explaining why over what. Branches are `<issue-number>-<kebab-title>`, which is also the spec directory name; the review gate blocks a spec branch whose slug has no issue number.

## Gates

Both hooks run from the repository's own `hooks/` directory rather than from a copy under `.claude/`. This repo is the source of those scripts, and a second copy would drift — which would mean the repo tests a stale version of its own enforcement. It is the one project where pointing at the source is correct; every other install copies.

## Where the contract lives

`docs/CONTRACT.md` is the development contract. It was compiled **from** the reviewer's rulebook at `.claude/agents/gate-sdd-reviewer/rules/`, not the reverse: the rulebook was hand-authored one rule per incident, and the contract indexes it and tiers what sits around it. A new Judgment rule is added to the rulebook first and then to the contract's table, and nothing checks that the two agree.
