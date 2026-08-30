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

It stays as the survey tool that produced the scope, and it is deliberately loose: it counts any block of consecutive short lines, so YAML front matter and a list of five short items both register. Its post-transform count of 30 across 23 files is those, not work left undone. AC1 was amended to the exact question — whether the transform is a fixed point — in its own commit ahead of T3, per #59.

## T5 — AC2 needed one carve-out, verified rather than waived

`verify.py` compares every tracked Markdown file against `main` and reported one change: `CONTRIBUTING.md`, which gained the convention section AC6 asks for. That is intentional new content, not a reflow defect, but "the checker flagged it and I decided it was fine" is exactly the reasoning this branch exists to distrust.

So it was checked instead. Comparing the canonical forms element by element: headings +1, tokens +3, **nothing removed or altered in any of the five categories.** The change is purely additive. Excluding that one file, the remaining **82 files compare identically** against `main`.

## Review — a shipped template broke in a way canon.py could not see

The reviewer found it: `agents/_template/reviewer.md`. On `main` the substitution slot stood alone at column 0, directly under the bullet that introduces it. The reflow folded it up into the sentence.

The file's own rendering is unchanged — a placeholder alone on a line is a lazy continuation of the bullet above it, so `canon.py` saw an identical token stream and reported nothing. **The damage is invisible until substitution.** `init` pastes a multi-line indented bullet list into that slot, so the rendered reviewer would have read `- these validators, and no others:   - ./scripts/check-leakage.sh`, turning the first validator into part of the sentence and the rest into a stray nested list. `agents/` is a shipped path, so every project generated from the template would have inherited it.

Two things worth keeping from this.

**The blind spot was structural, not accidental.** `canon.py` was written to be independent of `unwrap.py`, and it is — but both were written by someone thinking about Markdown, and neither was thinking about a template that is not yet Markdown. A canonical form can only compare what it parses, and it parsed the pre-substitution file correctly.

**The durable fix is a rule, not an edit.** A line that is only a `{{PLACEHOLDER}}` is now structural in both files: `unwrap.py` never joins one, and `canon.py` treats it as its own unit so a future fold is visible rather than silent. Verified both ways — the transform now leaves `agents/_template/reviewer.md` unchanged, and `canon` reports a difference between the correct and folded forms. Restoring the line by hand without the rule would have left the next run to break it again.

`{{RULEBOOK_TABLE}}` is the only other standalone slot in the repository. It survived because a blank line preceded it.
