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
  fine) — canonicalising the input before both is not symmetric. A normalisation that can only
  **delete** makes the clearing side louder: a removed clearing cue means the input gets flagged.
  The same normalisation on the accusing side can only make it quieter, because a removed accusing
  cue means the input is never examined at all. The second is a fail-open, and it reads as a
  tightening, which is why it survives review. HIGH.

  Check: find every normalisation — `strip`, `sub`, `lower`, `tr`, `sed` — sitting between reading an
  input and matching it, and ask which pattern consumes the normalised value.

  | consumed by | verdict |
  | :-- | :-- |
  | the accusing pattern | the finding, unless it provably cannot remove an accusing cue |
  | the clearing pattern | the fix — subject to the substitution caveat below |
  | no pattern — an extraction, an emptiness test, display text, an argument to a subprocess | not an instance |

  **A substitution that inserts is not monotonic on either side.** "Can only delete" is the premise
  that makes the clearing side safe, and `re.sub(..., " ", s)` breaks it: inserting a separator can
  *assemble* a clearing cue that was not in the input. `scripts/check-templates.py` documents that
  residue on its own clearing side and accepts it with an argument. A clearing-side substitution
  needs its own argument; it does not inherit this rule's blessing.

  **Two carve-outs, each narrower than it first looks.** A normalisation on the accusing side is
  safe when it provably cannot remove an accusing cue — trimming leading and trailing whitespace
  qualifies **only where the accusing pattern's cues cannot occur at a line's edges**. That is true
  of `check-templates.py`'s `RED` and false of any accuser whose cue is indentation or trailing
  whitespace, which is the shape a mechanical check for `G-7` would have. Separately, a *single*
  comparison with both operands mapped into the same equivalence class is canonicalisation for
  comparison rather than asymmetry — **provided the class is one the property does not
  distinguish**. `flat()` in `scripts/check-skill-contracts.py` collapses whitespace runs and a
  rewrapped sentence is the same sentence, so it qualifies; a coarser class, such as case-folding
  plus punctuation-stripping on a presence check, would not. "One comparison" alone does not earn
  the exemption.

  Introduced by #45 after #10 (PR #44), where a fix for one fail-open created another and cost a
  full extra review round, because the reviewer had to derive the principle rather than cite it. The
  instance is pinned by the `backticked-red` and `slashed-red` assertions in `scripts/test-gates.sh`
  — cited by name because the suite prints no case numbers, and its source comments and its output
  order have already diverged by twelve.
