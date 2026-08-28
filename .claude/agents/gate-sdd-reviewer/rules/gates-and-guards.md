# Gates and guards

Rules for anything that can block a turn or fail a build. The project's anchor is *gates never fail
open*, and every rule here is a way that has already happened.

- **G-1 — a guard must not exit 0 on a path where it could not do its job.** Not finding a problem
  and not having looked are different outcomes and must not share an exit code. `check-locks.py`
  printing `0 pinned file(s)` and exiting 0 (#16), and `review-gate.sh` exiting 0 with a pathspec
  matching no files (#1), are the same defect twice. BLOCKER.

- **G-2 — a value interpolated into `git` must reach it intact.** Shell quoting and globbing both
  get a say before git does: a quoted `'*.py'` keeps its quotes inside a variable, and a bare
  `*.py` is expanded against the repository root. Use `:(glob)` pathspecs, strip quotes, and
  disable globbing across the word split. BLOCKER.

- **G-3 — a blocking gate must speak both channels.** Exit 2 with a message on stderr for Claude
  Code, and `{"decision":"continue","reason":...}` on stdout for Antigravity. Go through
  `gate_lib`'s `gate_block`/`gate_pass` rather than writing either by hand. A gate that serves one
  harness is silently advisory on the other. BLOCKER.

- **G-4 — every new gate behaviour needs a case in `scripts/test-gates.sh`.** No case, not shipped.
  A fixture must be able to *fail* for the reason it claims to test: case 7 passed for three
  releases while the gate did nothing, because its fixture happened to match. When adding a case,
  verify it by reverting the fix and confirming it goes red. HIGH.

- **G-5 — hooks are POSIX `sh`, not bash.** No `[[`, no arrays, no `local`, no `$'...'`. The
  shebang is `#!/bin/sh` and it means it. HIGH.

- **G-6 — a gate must stay narrow.** It may only fire on the case it exists for. Firing on an
  ordinary turn is how a gate gets switched off, and a switched-off gate protects nothing. Any new
  condition that widens when a gate fires needs an explicit argument and a no-false-block test
  case. HIGH.

- **G-7 — steering values are read with `sed ... | head -1`.** A machine-read line must stay on one
  physical line; a wrapped value is truncated silently. Flag any documentation or template that
  shows one wrapped. MEDIUM.

- **G-8 — a guard's exemption list is part of the guard.** A wrong entry in it is worse than no
  guard, because the guard now certifies the thing it is not checking. Exemptions need a stated
  reason. HIGH.

- **G-9 — normalisation belongs on the clearing side, not the accusing one.** Where a guard has two
  patterns — one that *accuses* (the input is wrong) and one that *clears* (but here is why it is
  fine) — canonicalising the input before both is not symmetric. Stripping before the clearing
  pattern can only make the guard louder: a removed clearing cue means the input gets flagged.
  Stripping before the accusing pattern can only make it quieter, because a removed accusing cue
  means the input is never examined at all. The second is a fail-open, and it reads as a tightening,
  which is why it survives review. HIGH.

  Check: find every normalisation — `strip`, `sub`, `lower`, `tr`, `sed` — that runs between reading
  an input and matching it. Ask which pattern consumes the normalised value. Accusing on normalised
  input is the finding; clearing on it is the fix.

  **Two things this rule does not condemn.** A normalisation on the accusing side is safe when it
  provably cannot remove an accusing cue — trimming leading and trailing whitespace qualifies, since
  cues live in a line's interior; anything that removes interior content does not.
  `scripts/check-templates.py` does both, and the difference between its `line.strip()` and its
  `CODE_OR_PATH.sub` is the worked example. Separately, a *single* comparison with both operands
  canonicalised — `flat(needle) not in flat(haystack)` in `scripts/check-skill-contracts.py` — is
  canonicalisation for comparison, not asymmetry; there is no second pattern for it to be asymmetric
  against.

  Introduced by #45 after #10 (PR #44), where a fix for one fail-open created another and it took a
  full extra review round to find, because the reviewer had to derive the principle rather than cite
  it. The instance is pinned by case 39 in `scripts/test-gates.sh`.
