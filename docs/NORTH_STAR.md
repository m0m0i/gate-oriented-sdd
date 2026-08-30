# North star

- Status: draft — proposed by `northstar` on 2026-08-29, pending the author's correction. Nothing cites this document yet; see `docs/verified.md`.

## The metric

**Verified-merge rate: the share of merged changes, across projects running this harness, that carry a fresh CLEAN review receipt obtained independently.**

Not installs, not stars, not skills shipped. A harness that is installed everywhere and whose gate is switched off has moved nothing. The number goes up in exactly three ways — more of what matters is enforced, fewer people switch the gate off, and more reviews are genuinely independent — and those are the levers below.

It is deliberately measurable from artifacts that already exist: `.specs/*/.review-receipt` records `verdict`, `reviewed_sha`, and `reviewed_by`, and a merge either has a fresh one or does not. Gaming it requires running the reviews.

## Levers

- **LV-1 Enforcement depth** — how much of what actually matters sits on the deterministic layer rather than in prose. Every rule that moves from a skill to a hook stops being declinable.
- **LV-2 Gate narrowness** — false blocks per real block. This is the counterweight to LV-1 and not a footnote to it: a gate that fires on ordinary turns gets switched off, and a switched-off gate contributes zero to the metric no matter how deep LV-1 goes. #26 is this lever failing — the `git checkout` bypass was reached for four times in one week.
- **LV-3 Review independence** — the share of CLEAN receipts recording `reviewed_by=subagent` rather than `inline`. An inline review still finds real defects, but it is the author reviewing their own diff, which is not what the judgment layer is sold on.
- **LV-4 Install fidelity** — whether `init` leaves a project where the gates actually work on turn one. A misconfigured install scores zero on every lever above it, silently.
- **LV-5 Reachability** — whether a shipped fix arrives in an installed consumer. #3 is this lever at zero: six fixes existed and reached nobody, because `claude plugin update` gates on version rather than sha.

LV-1 and LV-2 are the pair that actually decides the number. LV-3 through LV-5 are the ways it quietly reads higher than it is.

## Quality laws, in priority order

1. **A gate fails closed.** A check that exits 0 having verified nothing is worse than no check, because it is indistinguishable from one that worked — so it survives exactly as long as it takes to matter. (#1, #16, #34.)
2. **A gate stays welcome.** It fires on the state it exists for and is silent otherwise. A gate people route around enforces nothing, and the routing is invisible. (#26.)
3. **A claim is reproducible.** Anything the harness asserts about itself is either tested or labelled unverified, in the same sentence that makes the claim.

When two conflict, the higher one wins. The worked example is `check-version-bump.py`: it fires on shipped paths that change without a version bump, which mid-implementation is a normal state, so as a turn-end validator it would have blocked ordinary work and been switched off. Law 2 did not weaken it — the check still fails closed. Law 2 **scoped** it: CI-only, on pull requests, which is the moment the question is meaningful. That is the shape of the resolution every time. Narrowness is bought by scoping a check, never by softening it.

The contrast is `check-locks.py`, which used to pass when it found no locks at all. Silent, welcome, and it had silently unhooked every shipped rulebook (#16). Made to fail closed it became noisier, and that was correct.

## Non-negotiable

**No check is ever reported as having run when it did not.**

The live instance: `evals/` holds four authored cases that have never executed, because `claude plugin eval` was not enabled on the account they were written on. `evals/README.md` says "Status: authored, not yet run" and the README's status line repeats it, in the same sentence that would otherwise read as maturity. One line would make this project look a release further along than it is, nobody would check it, and it is the single most tempting edit in the repository.

What it costs: the project reads as less finished than a competitor willing to write "tested".

## Owns

**Gates never fail open** — law 1, unchanged from `.steering/product.md`.

This repo and not a sibling because this repo *is* the enforcement: the hooks, the guards, and the receipt schema all live here, and a consuming project inherits whatever this one gets wrong. A defect that lets a gate exit 0 when it should have blocked is at least HIGH; one that makes a gate silently stop checking is a BLOCKER.

Not law 2, though law 2 is the one most often violated in practice: a gate that is too noisy gets switched off and someone notices. A gate that fails open is noticed by nobody, which is what makes it the property worth owning.
