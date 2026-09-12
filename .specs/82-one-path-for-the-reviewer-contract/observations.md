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
