# Observations — 82-one-path-for-the-reviewer-contract

## Review round 1 — BLOCKED, 0 blockers, 2 HIGH, 4 MEDIUM, 2 LOW

Reviewed at `9b3b620`. **The second HIGH is the most valuable finding this harness has produced,
because the reviewer found it by being the thing the fix was written for.**

### HIGH 2 — the fix did not resolve, and the reviewer discovered that by trying to use it

The branch replaced a plugin-relative path (`agents/_shared/…`) with a reviewer-relative one
(`_shared/…`), reasoning that one string is then correct under both harness layouts. The
reasoning is sound and the result did not work.

The reviewer's *first action* was to follow `.claude/agents/gate-sdd-reviewer.md:10` literally.
It failed. It then reached the contract only by guessing `agents/_shared/` — **the plugin's
copy, not the install's**, identical here by luck alone.

Verified directly afterwards:

```
_shared/reviewer-contract.md                   does not exist
.claude/agents/_shared/reviewer-contract.md    EXISTS
agents/_shared/reviewer-contract.md            EXISTS   <- the guess: the wrong file
```

**The cause is a category error in the fix.** A reviewer reading its own instruction is a
tool-using agent whose working directory is the **project root**, not the directory its own file
sits in. So a bare relative path names nothing from either root — which is the same class of miss
as the plugin-relative form it replaced, arrived at from the opposite direction.

The bare relative form is the right way to *say* where the file lives and useless for *opening*
it. The instruction now says both:

> **Read the reviewer contract first** — `_shared/reviewer-contract.md`, beside this file:
> `.claude/agents/_shared/reviewer-contract.md` under Claude Code,
> `.agents/_shared/reviewer-contract.md` under Antigravity.

The guard encodes it as two rules: every mention must be one of three allowed forms, **and** at
least one must be concrete, because that is what "resolves there" actually means. The dogfood
reviewer is an install rather than a template, so it names the concrete form only.

**This is the limit of dogfooding, stated plainly.** The instance we run was already correct when
#82 was filed, which is exactly why running it never surfaced the bug. Round 1 then produced the
inverse: a fix that was correct in the shipped files and broken in the one that gets executed.
Only a reader who *used* the instruction could tell — and that is what a review by an independent
agent is for, as opposed to a review by reading.

### HIGH 1 — the guard could agree with nothing

`EXACT` and `SUFFIX` are hard-coded tuples with no floor, so emptying either made every loop run
zero times and printed `0 source(s) agree` at exit 0. Emptying `EXACT` was the worse half: the
three shipped reviewers silently leave the comparison, `3 source(s) agree` prints, and **the exact
defect #82 exists for passes**.

`check-receipt-schema.py:150,256` already carries floors for its two tuples, and case 49 pins
them — its own comment says that file's newer tuple "arrived without the equivalent". This guard
arrived the same way one release later. Floors added, and case 64 asserts the success line is
*not* printed.

### The four MEDIUMs

- **Case 61's accusing half did not exist.** It installed the current reviewers and asserted the
  output was empty — which a function that printed nothing at all would also satisfy. It also
  defined resolution *relative to the agents directory*, assuming the base that makes the answer
  yes, which is precisely why it could not see HIGH 2. Rewritten to resolve **from the project
  root** and to carry a fifth, deliberately broken reviewer that must be named — and named alone.
- **The guard certified a set larger than the one it compared.** `docs/CONTRACT.md` and
  `AGENTS.md` both state the placement and were in neither tuple, while the docstring, the CI step
  name and the commit message all said "every statement". Both added; a guard's exemption list is
  part of the guard, and an unstated omission is the defect this file exists for.
- **The 16th `check-skill-contracts.py` entry was argued in the wrong place.** That guard's
  docstring requires the argument **in the spec proposing it**, precisely so the count cannot grow
  by an argument written only in the code it adds. The entry is right on merits — a reverted "next
  to it" still ends in the canonical suffix, so `check-contract-path.py` passes it and the
  destination sentence really is otherwise unguarded — but the spec did not say so, and two files
  the diff touches were missing from its Affected-files table. Both fixed.
- **The diagram constraint was undocumented.** The guard's deliberately dumb regex means a
  document must write the whole path on one physical line. Recorded at the tuple, with the reason
  a tree-aware parser was rejected: more code between reading an input and deciding, every branch
  a new way to match nothing and pass — G-1 risk bought for a cosmetic gain.

### A mistake of mine worth recording

Mutation-testing the guard, I reverted a fixture with `git checkout scripts/test-gates.sh` — and
**destroyed two uncommitted case rewrites in that same file.** I had backed up
`check-contract-path.py` to `/tmp` before mutating it and did not extend the same care to the
suite. Both had to be rewritten from scratch.

The rule that would have prevented it: **mutate through a backup, never through source control,
while the working tree holds work you have not committed.** `git checkout` does not distinguish
the mutation from everything else in the file.

### Mutation results, after the fixes

| Mutation | Caught by |
| :-- | :-- |
| floors removed | `empty contract-path work-set` — exact-exit, says-floor. ~~no-success-line~~ **did not catch it**: that assertion grepped stderr for a string that only reaches stdout, which `run_cpath` discarded. Corrected in round 2; see below. |
| concrete-path rule removed | `relative-only reviewer fails` |
| ALLOWED-set check removed | `extra-form` (isolated on purpose — see below) |
| a shipped reviewer reverted to relative-only | `resolves from the project root` |

The third needed its own sub-case. Every mutation that removes the `ALLOWED` check is **also**
caught by the concrete-path check, so without a reviewer naming a valid concrete form *and* a junk
one, that rule could have been deleted with the suite green — a guard half that cannot fail.
Found by mutating it and watching nothing go red.

## Review round 2 — BLOCKED, 0 blockers, 2 HIGH, 3 MEDIUM, 2 LOW

Reviewed at `1178f08`. Both round-1 HIGHs cleared. Both new ones are **residue of that fix** —
one in a file the fix did not revisit, one inside the condition the fix added.

### HIGH 1 — `init` still ordered the operator to delete the working paths

Round 1 corrected every reviewer and left `skills/init/SKILL.md:60` untouched:

> "The reviewer names it relative to itself, so that one path is correct under either harness
> **and must not be rewritten to an absolute one**."

Both halves were false by then. The premise is what round 1 refuted. The instruction is worse:
every reviewer `init` hands the operator now contains exactly the two absolute forms that
sentence forbids, so an operator — or an agent — following `init` literally has a standing
instruction to strip the only paths a reviewer can open. **The fix's own installer was the
reintroduction route for the defect.**

`check-contract-path.py` could not see it: `SUFFIX` inspects paths, and this is a sentence *about*
paths. A guard that reads mentions cannot read intent, which is the same seam the 16th
`check-skill-contracts.py` entry exists in.

### HIGH 2 — "at least one concrete form" let a shipped reviewer serve one harness

`if not any(m in CONCRETE for m in mentions)` asked for *at least one*, and `EXACT` held two
kinds of file with two different obligations. Deleting `.agents/_shared/…` from a shipped
reviewer left `_shared/…` (in `ALLOWED`) and `.claude/agents/…` (in `CONCRETE`) — both conditions
satisfied, eleven validators green, **and every Antigravity consumer handed a reviewer that
cannot open its contract.** Demonstrated before fixing.

That is #82's own shape narrowed to one harness — and two-harness correctness is the entire
reason the issue's proposed fix was overruled, so it was this branch's central invariant left
unguarded. Case 61 could not see it either: it installs into one layout at a time and asks
`any`, so the `.claude/` mention alone satisfies the `.claude/` run.

Split by obligation rather than patched with a flag: **`SHIPPED`** (templates copied into either
harness — every form in `ALLOWED`, and **both** concrete destinations present) and
**`INSTALLED`** (this repo's own reviewer — exactly one, its own), each with its own floor.

### MEDIUM — the assertion that credited itself with a catch it never made

Round 1's `no-success-line` sub-case grepped **stderr** for `source(s) agree`, a string that only
ever reaches **stdout**, which `run_cpath` sent to `/dev/null`. `c3=ok` unconditionally. Case 49 —
the case this was modelled on — captures stdout and greps that; this helper did not.

The round-1 mutation table above credited it with catching the floor mutation. **It caught
nothing**, and that row is now corrected in place rather than rewritten, per #102. `run_cpath`
captures stdout; a mutant that prints the success line on the floor path now turns it red, which
is how that was verified rather than assumed.

This is the third time on this branch that a check written to catch something could not have.
The pattern is specific enough to name: **an assertion about output must read the stream the
output actually goes to**, and the only way to know is to make the thing it forbids happen.

### The rest

- **The guard's docstring and failure epilogue still taught the refuted rule** — and the epilogue
  is the closing paragraph of *every* failure, so someone tripping `does not name .agents/…` was
  told in the same breath that the relative form resolves and absolute paths are the mistake.
  A guard's failure text is read at the worst possible moment and treated as authoritative. Both
  corrected.
- **The clarification in `spec.md` still recorded the refuted answer**, unmarked, and that is what
  a later spec reads to learn how this was settled. Amended in place with today's date, no AC line
  touched — the `docs/verified.md` convention of leaving the original and adding the supersession
  in the same document.
- **`unresolved()` lost its position anchor** in round 1's rewrite, so a reviewer keeping the path
  in a footnote would have passed. Restored as an explicit assertion that every shipped reviewer's
  first instruction is the contract line.
- The reviewers now end "— open whichever your project has", because the contract's stop rule is
  deliberately aggressive and a reviewer that tries one path, misses, and stops would be the
  failure mode reintroduced by naming two.

### What three rounds of this have actually been about

Twice now the branch has been wrong about where a reviewer can open its contract —
plugin-relative, then reviewer-relative — and both times the error was invisible to eleven green
validators and obvious to someone who **tried to use the instruction**. The guards were never the
problem; what they check was.

## Review round 3 — CLEAN, 0 blockers, 0 HIGH, 3 MEDIUM, 2 LOW

Reviewed at `3ce1cda`. Both round-2 HIGHs closed. The three MEDIUMs were advisory and **all
three were fixed anyway**, because two of them were fail-opens one mutation away and this
repository's anchor is that gates never fail open.

### The three, and what they had in common

- **`cp-one-harness`'s naming assertion could not fail.** It grepped stderr for `.agents/_shared`
  — and the failure epilogue enumerates `CONCRETE` on *every* failure, so the string was always
  present. Loosen the `SHIPPED` message to a generic "does not name both" and the assertion stays
  green, while saying *which* destination is missing is the entire value of that rule. Created by
  the epilogue rewrite that fixed round 2's MEDIUM.
- **The `INSTALLED` floor clause was pinned by nothing.** Delete it and the suite stayed green;
  emptying `INSTALLED` then drops this repository's own reviewer out of the comparison and prints
  `9 source(s) agree` at exit 0 — the dogfood file leaving the guard silently, which is the exact
  reason it was added.
- **The grouping was an exemption list with no shape check.** `SHIPPED` must name both
  destinations and `INSTALLED` only its own, so moving one entry between the tuples grants an
  exemption in a diff that reads as tidying. Demonstrated: move `agents/ts-reviewer.md` to
  `INSTALLED` alongside a fifth shipped reviewer and both floors pass while every Antigravity
  consumer is back where round 2 found them.

Also fixed: floors counted **entries, not distinct names**, so replacing `agents/python-reviewer.md`
with a second copy of `agents/ts-reviewer.md` satisfied `MIN_SHIPPED` while python-reviewer stopped
being compared. A source displaced by a duplicate is a source that stopped being checked.

Now four shape clauses before any comparison: floors, duplicates, `SHIPPED` under `agents/`,
`INSTALLED` under a harness directory.

### The fixture broke in the way this branch keeps breaking

Mutation-testing the new `INSTALLED` floor, the case stayed **green**. Not because the floor was
redundant — because `shrink_cpath`'s regex was `^NAME = \(.*?^\)`, which needs a closing paren at
the start of a line. `SHIPPED` and `SUFFIX` are multi-line tuples and match; `INSTALLED` is
**one line**, so the scan ran past it, swallowed `EXACT = SHIPPED + INSTALLED`, and the guard died
of `NameError` — **exit 1 for the wrong reason**, which the case read as a pass.

Third instance on this branch of a fixture failure wearing a guard failure's clothes, after the
`set -u` empty path on #110 and the stderr/stdout mix-up in round 2. `shrink_cpath` now scans to
the balanced closing paren and **`ast.parse`s the result**, so a mutation that mangles the source
says so instead of being counted as a catch.

The rule this keeps producing, now three ways: **a mutation must fail the thing it is aiming at,
and the only way to know is to read why it failed.** Exit code alone has been wrong every time.

### The two LOWs

The first-instruction anchor asserted less than its comment claimed — it matched a line *starting*
with the phrase, so a file with the paths in a footnote passed. The pattern now ties the path to
that line. And `init` gave a bold imperative followed immediately by permission to do the
opposite; collapsed to one rule, since an install legitimately keeps a single destination and
that is what `INSTALLED` encodes.

### Not done here, filed instead

The reviewer proposed lifting *"an assertion about output must read the stream the output actually
goes to"* into `rules/gates-and-guards.md` as a `G-*` clause, on the grounds that three occurrences
on one branch is this repository's own bar for a convention. That is a rulebook change and belongs
to its own issue rather than to #82's diff.

## Review round 4 — CLEAN, 0 blockers, 0 HIGH, 2 MEDIUM, 1 LOW

Reviewed at `7277dbe`. All three advisory findings fixed, because one of the MEDIUMs was **the
pattern #124 was filed for, sitting in the commit that filed it.**

- **The `SHIPPED` prefix clause was pinned by nothing.** Set `SHIPPED_PREFIX = ""` and all 76
  cases stayed green. It is load-bearing, not decoration: it closes the round-3 mutation of
  padding `SHIPPED` with a non-reviewer to hold the floor while a real reviewer leaves it, which
  passes floors and distinctness and was caught by nothing else.
- **`cp-empty-suffix` and `cp-empty-installed` asserted only exit 1**, so a guard dying during
  import would have read as the floor firing — the exact incident of round 3, one layer up from
  where it was fixed. Both now assert the reason and exclude a traceback, which is what case 49
  already did and these did not inherit.
- **`SUFFIX` was the remaining sink.** `SHIPPED` and `INSTALLED` now certify their own membership
  and `SUFFIX` accepted anything, so a reviewer moved there drops to "ends with the canonical
  suffix" — under which `agents/_shared/reviewer-contract.md`, **the original #82 defect**,
  passes. Closed.

Six shape clauses now, each with its own fixture, and all seven mutations of them go red.

### The same trap, twice in ten minutes, in the commit that named it

Writing the `SUFFIX` sink fixture, the case reported red — and the clause was fine. The
fixture's Python contained `'…",\n    "agents/ts-reviewer.md",'`, and the `\n` was written into
the shell heredoc as a **literal newline**, splitting the string literal across two lines. Python
exited on a `SyntaxError`, nothing mutated, the guard passed, and the assertion read that as the
clause failing to fire.

**Fourth instance on this branch**, hours after filing #124 for the first three. Both halves of
the fix were already written down in that issue: escape the sequence so the heredoc carries it
intact, and **bind the fixture's exit status into the assertion** so a fixture that did not run
cannot be mistaken for a guard that did not fire.

That it happened again while writing the issue about it is the most useful thing in this record.
The lesson is not "be careful" — it is that **every fixture which edits source needs its status
checked, mechanically, every time**, because the failure is silent and reads as a finding.

### Round 4's disposition

Filed rather than fixed here: nothing. Fixed rather than accepted: all three, on the grounds that
two were fail-opens and the third was the pattern this branch has now hit four times.
