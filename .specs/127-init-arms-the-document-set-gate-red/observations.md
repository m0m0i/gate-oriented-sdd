# Observations — 127-init-arms-the-document-set-gate-red

Eight reviewer rounds. Two BLOCKED-equivalent findings (one HIGH), and six rounds of MEDIUM
and LOW after the code was correct — almost all of them in prose *about* the code, which is
its own finding and is recorded as such at the end.

## Round 1 — BLOCKED, 1 HIGH

**[HIGH] `assets/check-document-set.py` — the third outcome, one level in.** `spec_slugs`
guarded `os.scandir` against `OSError` and then tested each entry with `Path.is_file()`, which
delegates to `os.path.isfile` and swallows every `OSError`. A slug directory the process could
not traverse read as *no `spec.md` here*, so `bootstrap` reported the grace period intact with a
real spec on disk — the function's own docstring promise, honoured for the outer directory and
broken one level in. Interpreter-dependent besides, which the reviewer named precisely: *a guard
whose verdict changes with the Python version is not a verdict.*

Fixed with `os.stat` + `stat.S_ISREG`, `FileNotFoundError` caught separately as the one
exception meaning *genuinely not a spec*. Case 69 gained `slug-unreadable-red` / `names-slug`.

Also fixed: the seventeenth skill-contract pin had no mutation fixture (the five before it each
have one); `Required in both modes.` in a file that now has three; the unreadable message naming
`.specs` for an `_archive` failure; `contracts-nomode` mutating the pre-#127 literal; and case
68's comment claiming every validator step 3 arms while arming one.

## Round 2 — CLEAN, 2 MEDIUM

**A fourth outcome the function claimed to have three of.** `entry.is_dir(follow_symlinks=False)`
skipped a symlinked slug directory *before* the stat, so it landed in neither `found` nor
`unreadable` — the fail-open direction, from a definition of "spec directory" narrower than the
design's. Now follows symlinks: a loop is an `OSError` and therefore `unreadable`; a dangling
link is a definite `ENOENT` and honestly green.

**The remediation text is part of the guard.** The absent-`- Mode:` message offered `minimum` or
`full`, sending a project with no documents to declare a set it had not written — this issue's
own defect, spoken by the checker that closes it. Now built from `MODES`.

## Round 3 — CLEAN, 1 MEDIUM

**A half-assertion that could not run was counted as one that passed.** Several branches
self-disable when the environment cannot produce the state they need (`chmod 000` under root,
mainly) and then set their variable to `ok`; `report` printed the same line as a real pass. G-1
one layer out, inside the suite that exists to enforce G-1. Under root, four halves of the new
case stop testing anything and the output is identical. `note_skip` added: the skip is spoken
with an id and counted in the summary.

## Round 4 — CLEAN, 2 MEDIUM

**The skip mechanism missed three of its own sites, and two of those manufactured a pass.** I
claimed seven; there are thirteen. Two of the three missed called `report ... ok` on the skip
path, incrementing the counter — and the new summary line then *certified* that nothing had been
skipped, making the silence louder rather than quieter in exactly the environment the mechanism
was added for.

**AC1 was wider than its evidence.** It said *every validator it placed on the `- Validators:`
line*; the fixture arms one of the two. Narrowed, with the unexercised axis recorded in Design
rather than left in a code comment.

## Round 5 — CLEAN, 2 MEDIUM

Both were the same defect: **the recount was itself written down wrong**, twice — `twelve` and
`nine` in the header and in the spec, in the paragraph whose subject is not counting.

## Round 6 — CLEAN, 2 MEDIUM

**A commit message that described four fixes over a diff carrying two.** The edit script raised
on a stale needle, and its single `write_text` came *after* the raise, so two `spec.md` hunks
were discarded while the message describing them was committed anyway. This is the #126 defect
exactly — *a commit that claimed two fixes and made neither* — and the reviewer found it by
doing the one thing that catches it: reading the diff against the message.

The remedy is procedural and is now the habit: write each file, read it back, and check the
diff before writing the message.

**The "count the guards" instruction yielded eleven.** Written to stop the next recount going
wrong, it would have caused it: twelve `chmod 000` lines minus the unguarded case 14 is eleven,
and the last two guards are symlink-availability, not permission. 11 + 2 = 13, now stated.

## Round 7 — CLEAN, 1 MEDIUM, 1 LOW

**`note_skip`'s twenty-five-line header shifted four `:NNN` cross-references by exactly that
much**, landing them on a `printf`, a function definition and two case headers. They exist to
stop a future editor recreating a fail-open — one ends *"Copy the glob into a case with no
corroborator and it breaks again"* — and a warning nobody can follow gets deleted rather than
obeyed. The same class the three previous commits closed, reintroduced by the commit that closed
them.

The reviewer also caught that **I cited a sha that does not exist** (`7fe28a1`) in the round-7
prompt: I wrote it from memory instead of reading `git log`. One layer out from the commit
message it was describing, and the same defect.

## Round 8 — CLEAN, nothing at LOW or above

Verdict: *ship it.* The reviewer re-derived every count, pointer and span from the tree rather
than from the prose, and walked the new `bootstrap` branch against the anchor: every path that
cannot do its job exits non-zero, and the one swallowed `OSError` (`ARCHIVE.is_dir()`) is covered
by an invariant now written at its call site.

## What this spec should be remembered for

The code was right after round 2. Rounds 3–7 were about **claims**: a count, a derivation, a
commit message, a set of line pointers, a sha. Every one of them was a statement that was true
when written and stopped being true, or was never checked against the thing it described.

That is the same defect as #127 itself. `init` step 3 opened with *"Scaffold the mandatory set"*
and the sentence was true of the intent and false of the bullets below it. Six rounds were spent
reproducing that shape in the meta-commentary of the fix for it — which is worth writing down,
because the lesson is not "count more carefully". It is that **a number, a pointer or a sha is a
claim, and a claim needs the same derivation a gate does.** `grep -c` before asserting a total;
read the line before citing it; read the diff before describing it.

## What review never saw

- **AC2's red is asserted, not observed.** T1 and T2 landed test and fix in one commit each,
  which is this repo's one-green-commit-per-cycle convention, so "fails before the fix" is the
  author's claim. The reviewer is read-only and said so plainly each round rather than implying
  coverage.
- **Three validators were never run against this tree** by the reviewer, in all eight rounds:
  `check-document-set.py` — the file this branch changes — plus `check-contract-path.py` and
  `check-readme-claims.py`, none of which are on its Bash allow-list. Their logic is exercised by
  `test-gates.sh` against fixtures, which is not the same thing. That gap is **#131**, and it
  widened here: the changed checker is now among the three the reviewer cannot run. I ran all
  twelve by hand before each commit.
- **`bootstrap` has no dogfooding in this repository.** This repo declares `- Mode: full`, so the
  new value is exercised only by the suite's fixtures — the same gap #110's spec recorded for
  `minimum`, one value over.
