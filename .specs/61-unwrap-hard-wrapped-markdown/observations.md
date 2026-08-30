# Observations — the unwrap

## T2 — the transform destroyed structure and the verifier could not see it

Recorded because it is the run's most useful result, and because it happened in the task whose stated purpose was to prove the checker works before trusting it.

The first transform collapsed YAML front matter — `.github/ISSUE_TEMPLATE/chore.md` became `name: Chore about: Maintenance ... labels: task` on one line — joined every heading into the paragraph beneath it, and merged bare list markers (`1.` alone, which the issue templates use) with the marker below.

`verify.py` reported **0 render changes** on all of it. Its `normalise` was `unwrap(unwrap(x))`, compared against `unwrap(x)`: true by construction for any idempotent transform, destructive ones included. The check re-applied the very rule whose bug it was meant to catch.

The self-test passed too, and that is the sharper lesson. It asserted that deleting a *word* is detected. Every one of these defects **preserves every word** and moves structure, so a word-level check was blind to the whole class. *A self-test proves the checker catches the class of defect its author imagined.*

`canon.py` replaces it and shares no code with the transform: it parses independently and compares front matter, fenced blocks, headings, table rows, and a token stream where each paragraph and list item contributes a boundary marker. Heading absorption changes the heading list; a merged item loses a boundary marker. `verify.py` now asserts on both failure classes, plus the list-marker guard, before it will compare anything.

## T4 — a fail-open check of my own, and one the repo already knows about

**Mine.** The first AC5 check ran `shasum` on an unquoted pair and compared two empty strings, printing `IDENTICAL` four times without hashing anything. It was rewritten with an explicit empty-hash guard and a negative control — a pair that must *not* match — which is the only reason the second version can be trusted. Third fail-open check in this branch's own tooling, after the two in T2.

**The repo's.** `check-locks.py` proves it fails on drift: appending a comment to `agents/ts-reviewer/rules/types-and-style.md` makes it exit non-zero, and reverting restores it. But the six pinned files are the three *shipped reference* reviewers' rulebooks only. This branch reflowed `.claude/agents/gate-sdd-reviewer/rules/claims-and-prose.md` and `gates-and-guards.md` — the project's own reviewer, the one that actually reviews this repo — and **nothing checked them, because nothing pins them.** The change here is cosmetic; a substantive one would have been equally unnoticed.

That is #19 ("`--update` cannot create a lock, so a new rulebook can never be pinned") with a live instance, and `docs/BACKLOG.md` position 7 already states the consequence: *"AGENTS.md names the hash-pinned rulebook as one of the two ideas this repo exists for, and the dogfooded instance still ships unpinned."* Recorded, not fixed — pinning it is #19's job.

## What held

- **AC4.** Every machine-read line in `.steering/product.md` and `.steering/tech.md` byte-identical to `main`. The join rule refuses to cross a list marker, which is what makes `- Validators:` absorbing `- Reviewer:` impossible rather than unlikely.
- **AC5.** Both mirror pairs still byte-identical. The three issue templates are byte-*unchanged* from baseline — front matter and bare markers both survived.
- **AC1.** The tree is a fixed point: a second pass changes no file.
- **AC3.** All eight validators at their baseline values, `test-gates.sh` at 52 passed / 0 failed.

## Note on `detect.py`

It stays as the survey tool that produced the scope, and it is loose in **both** directions.

It over-counts: any block of consecutive short lines registers, so YAML front matter and a list of five short items both do. Its post-transform count of 30 across 23 files is those, not work left undone.

It also **under**-counts, which review found and this note originally missed. `wrapped()` requires every line in a block to be ≤105 columns, so a block whose first line is long hides its wrapped continuations entirely. Three shipped skills — `skills/init/SKILL.md`, `skills/spec/SKILL.md`, `skills/sprint/SKILL.md` — were modified by the transform and appear in no survey. They were reached only because AC2 compares all 83 files present on `main` rather than the 54 the survey named, which is what the design's "broader than the survey, so a file the survey missed cannot slip through" was written for. It is a hit, not a hypothetical. AC1 was amended to the exact question — whether the transform is a fixed point — in its own commit ahead of T3, per #59.

## T5 — AC2 needed one carve-out, verified rather than waived

`verify.py` compares every tracked Markdown file against `main` and reported one change: `CONTRIBUTING.md`, which gained the convention section AC6 asks for. That is intentional new content, not a reflow defect, but "the checker flagged it and I decided it was fine" is exactly the reasoning this branch exists to distrust.

So it was checked instead. Comparing the canonical forms element by element: headings +1, tokens +3, **nothing removed or altered in any of the five categories.** The change is purely additive. Excluding that one file, the remaining **82 files compare identically** against `main`.

## Review — a shipped template broke in a way canon.py could not see

The reviewer found it: `agents/_template/reviewer.md`. On `main` the substitution slot stood alone at column 0, directly under the bullet that introduces it. The reflow folded it up into the sentence.

The file's own rendering is unchanged — a placeholder alone on a line is a lazy continuation of the bullet above it, so `canon.py` saw an identical token stream and reported nothing. **The damage is invisible until substitution.** `init` pastes a multi-line indented bullet list into that slot, so the rendered reviewer would have read `- these validators, and no others:   - ./scripts/check-leakage.sh`, turning the first validator into part of the sentence and the rest into a stray nested list. `agents/` is a shipped path, so every project generated from the template would have inherited it.

Two things worth keeping from this.

**The blind spot was structural, not accidental.** `canon.py` was written to be independent of `unwrap.py`, and it is — but both were written by someone thinking about Markdown, and neither was thinking about a template that is not yet Markdown. A canonical form can only compare what it parses, and it parsed the pre-substitution file correctly.

**The durable fix is a rule, not an edit.** A line that is only a `{{PLACEHOLDER}}` is now structural in both files: `unwrap.py` never joins one, and `canon.py` treats it as its own unit so a future fold is visible rather than silent. Verified both ways — the transform now leaves `agents/_template/reviewer.md` unchanged, and `canon` reports a difference between the correct and folded forms. Restoring the line by hand without the rule would have left the next run to break it again.

`{{RULEBOOK_TABLE}}` is the only other standalone slot in the repository. *(Corrected on review: this first said it survived "because a blank line preceded it". No blank line precedes it — `agents/_template/reviewer.md:28` is a table separator row, and a table row already terminates the block under `unwrap.py`'s `STRUCTURAL` rule. The near-miss was real; the reason recorded for it was a different mechanism from the one that actually held, in the document whose job is to record why it did not bite.)*

One more thing the fix changed and this note did not, until review pointed it out. The `SLOT` regex is now duplicated **verbatim** in both files, which reinstates at narrower scope exactly the shared assumption the paragraph above calls structural: a slot neither recogniser matches is folded by `unwrap.py` and invisible to `canon.py`, which is the failure that just shipped. It is not live — all **fourteen** distinct slot names in the repository are `[A-Z_]+`, and the six brace tokens that are not (`{{ github.event… }}` and friends) never stand alone on a line — but a slot named with a digit or a lowercase letter would reopen it. Left as one regex rather than two: a second independent recogniser for two lines would cost more than it protects, and saying so is better than implying the blind spot is gone.

## The commit that claimed a fix it did not contain, twice

`5a9e7ff` says it corrected three false statements. It corrected two. The edit script wrote `observations.md`, then failed an assertion on `spec.md`, and the commit went ahead anyway — so the spec kept promising locks "re-pinned to match" while the message said otherwise.

This is the second instance on this branch, after `2e0238f` in #55 did the same thing. Both times the cause was identical: a multi-file edit script that writes as it goes and asserts as it goes, so a late failure leaves earlier writes committed under a message describing all of them. Both times it was caught by re-running the check rather than by reading the diff.

The fix is not a better script. It is that a commit message is a claim like any other, and this branch's own standard applies to it: **assert nothing you have not just verified.** Recorded here rather than left in the log, because the log is where the wrong claim already is.

## Review — a fourth fail-open, in the tool written to police fail-opens

`verify.py` exited **0** on a ref that does not resolve. Every `git show` failed, every file was skipped by `if old.returncode: continue`, and it printed `0 file(s) compared, 0 change(s)` and reported success. "Verified everything" and "compared nothing" shared an exit code.

That is #16's and #39's exact shape, occurring in the verifier this branch wrote to prove a transform safe — after `observations.md` had already recorded three other fail-opens in the same branch's tooling. It now fails when `checked == 0` and prints how many files were absent from the ref, so a partial comparison is visible rather than silently equivalent to a full one.

Worth stating plainly: the AC2 evidence was never actually at risk, because the reviewer reproduced 83/1 independently rather than taking the tool's word. The defect is that the tool would have said yes to a question it had not asked, and nothing in this branch would have noticed.

`baseline.md`'s per-file table was also truncated — T1 piped `detect.py` through `tail -3`, so one of 54 rows survived under a heading promising a per-file count. The full listing is restored.

## Review — the blind spot's second instance, and the rule that closes it

The reviewer found `skills/sprint/SKILL.md`. Step 2 lists three seams as a sub-list and then closes them with a sentence summarising all three, sitting at the **parent** item's content column. The transform joined that sentence onto the third seam, so the shipped skill read `- a migration, rename, or dependency bump the change forces These are different issue *types*…`.

CommonMark renders both forms identically — a lazy continuation belongs to the preceding item either way — which is exactly why `canon.py` reported nothing. This is the second instance of the class recorded above for `agents/_template/reviewer.md`: **a fold invisible to a rendering-equivalence check, because the damage is not in the rendering.** The reader that suffers is the model reading `skills/` as source.

Fixed with a rule rather than an edit, as the slot case was. A continuation indented **less** than the open item's content column belongs to an outer block, so the transform now closes the item instead of joining. Surveying `main` for the pattern found five instances across the repository; two were already handled by the `SLOT` rule and the fence boundary, and the indent rule closes the remaining three — `skills/sprint/SKILL.md`, `agents/_template/rules/starter.md` (whose HTML comment terminator `-->` had been pulled onto the last bullet), and one in this branch's own spec.

Both instances of this class were found by the reviewer and neither by the tooling, which is the honest summary of what a rendering-equivalence check is worth: it proves the HTML is unchanged, and the HTML was never the thing at risk.
