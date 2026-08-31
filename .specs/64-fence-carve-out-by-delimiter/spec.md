# Spec: The fence carve-out is stated by delimiter when the thing that matters is content

- Slug: 64-fence-carve-out-by-delimiter   Issue: 64   Type: bug   Status: done
- Author: m0m0i   Date: 2026-08-31

## 1. Requirements (WHAT / WHY)

- Reproduction: the same sentence, in the document and in the template that regenerates it, after #61 unwrapped only the first.

```
$ grep -n 'Ordered, not prioritized' docs/BACKLOG.md
4:- Ordered, not prioritized. Position reflects value, risk, cost, and dependency together. There is no separate priority field, and adding one would contradict this.

$ grep -n -A1 'Ordered, not prioritized' skills/backlog/SKILL.md
41:- Ordered, not prioritized. Position reflects value, risk, cost, and dependency
42-  together. There is no separate priority field, and adding one would contradict this.
```

- Expected: `CONTRIBUTING.md`'s convention says it applies to "every Markdown file in the repository — skills, rulebooks, steering, specs, work logs, documents", so the Markdown a skill emits from a ` ```markdown ` fence follows it, and the next `backlog` grooming reproduces `docs/BACKLOG.md`'s unwrapped form rather than reverting it.
- Actual: the carve-out immediately below reads "Fenced code, tables, and YAML front matter keep their line breaks — those are structure, not wrapping." That exempts a fence by its **delimiter**, so a ` ```markdown ` fence holding prose is exempt on the same footing as a fence holding Python, and seven hand-wrapped blocks survive in two shipped skills.
- Impact: every project the harness installs into. `init` copies these skills, each writes a document from its template, so a document comes out hand-wrapped in the convention's own repository. Nobody hits an error — someone eventually unwraps it by hand, which is what #61 did. It also makes #58 partly self-undoing: re-grooming `docs/BACKLOG.md` from a template that hand-wraps puts the wrapping straight back.

- **Root cause:** not a defect in the transform. `.specs/61-unwrap-hard-wrapped-markdown/unwrap.py` skips fences deliberately and correctly, because it cannot know whether a fence holds Markdown or Python. The defect is in the sentence: `CONTRIBUTING.md` scopes the carve-out by delimiter when the property that decides it is content. A fence is a quoting mechanism, and a ` ```markdown ` fence quotes Markdown — the language tag already states which, and nothing reads it. So the convention, applied correctly by the next person, restores the wrapping.

### The measurement, re-run rather than trusted

The issue's own count does not reproduce, and the spec is written against the re-run.

|                                                   | issue #64 says | re-run on `3df25b0` |
| :------------------------------------------------ | -------------: | ------------------: |
| hand-wrapped blocks inside ` ```markdown ` fences |             42 |               **7** |
| shipped files holding them                        |              8 |               **2** |

There are 10 ` ```markdown ` fences across 8 files, which is the likely origin of "eight files". Seven of them hold no hand-wrapped prose at all — `contract`, `design-doc`, `epics`, `northstar`, `prd`, `worklog`, and `skills/spec/templates.md`'s feature template at `:13` — because every line in those bodies already starts its own construct. The seven live blocks sit in the remaining three fences:

| File                               | Blocks | Lines                 |
| :--------------------------------- | -----: | :-------------------- |
| `skills/backlog/SKILL.md`          |      2 | 41–42, 50–52          |
| `skills/spec/templates.md` (bug)   |      2 | 56–57, 70–71          |
| `skills/spec/templates.md` (chore) |      3 | 96–97, 98–99, 108–110 |

Both tables are derived from `scripts/check-markdown-fences.py --list`, delivered in T1. `--list` prints each continuation line; the ranges here are the blocks those lines sit in, so a reader can re-derive every figure rather than trust it.

### One counter-example the issue did not have

`skills/contract/SKILL.md:47-48` is two **separate** placeholder lines:

```
<what the formatter owns — say "the formatter decides" rather than restating it>
<what it does not own: naming, file organisation, module boundaries>
```

`unwrap.py` folds them into one. They are not a hand wrap — they are two instructions to the skill. So the issue's "unlike most proposed guards this one has an unambiguous, mechanical test" is **false as stated**: a guard asking "would `unwrap.py` join this line?" produces a false accusation on a shipped file today. Any guard this spec ships has to be keyed on a predicate that clears those two lines for a stated reason, not by exception.

- Acceptance criteria:
  - [x] **AC1:** WHEN a reader applies `CONTRIBUTING.md`'s Markdown convention to a ` ```markdown ` fence THE SYSTEM SHALL scope the carve-out by content — fences holding literal code, output, or a line-sensitive format — and state that a ` ```markdown ` fence holds Markdown and follows the convention.
  - [x] **AC2:** the regression test fails before the fix and passes after — it reports the seven blocks on `3df25b0` and none after, and it clears `skills/contract/SKILL.md:47-48` in both states.
  - [x] **AC3:** no line inside a ` ```markdown ` fence in a tracked file is a continuation of the line above it.
  - [x] **AC4:** the fences holding a line-sensitive format are byte-identical to `3df25b0`: `skills/implement/SKILL.md`'s `reviewed_sha=` receipt block, and the `[SEVERITY] <file>:<line>` finding format in **both** `agents/_shared/reviewer-contract.md` and `.claude/agents/_shared/reviewer-contract.md`.
  - [x] **AC5:** the existing validators hold their baseline values — `check-receipt-schema` 7 fields across 3 copies, `check-templates` 10 task lines across 3 templates, `check-steering-anchors` 5 of 5, `check-locks` 6 pinned files, and the other three clean — and `test-gates.sh` reports 54 passed / 0 failed: the 52 on `3df25b0` plus the two new cases named in T3.
  - [x] **AC6:** in `skills/backlog/SKILL.md` and `skills/spec/templates.md` — the only files whose fence bodies change — each ` ```markdown ` fence body holds the same word stream as on `3df25b0`, word for word and in order, and every byte outside those fences is unchanged.

> **AC6 amended, 2026-08-31, in its own commit ahead of the task it judges (#59).** It first read "every modified file renders identically to `3df25b0`". The work falsifies that: a fenced block's content is literal, so joining two lines inside one genuinely changes what the fence renders — that is the entire point of T1, and the criterion would have had to be waived on the files it most needed to judge. `.specs/61-.../observations.md` already says what a rendering-equivalence check is worth here: "it proves the HTML is unchanged, and the HTML was never the thing at risk." The property that actually matters for a join is that no word was added, dropped, or reordered, and that the edit stayed inside the fence. AC6 now asks that instead.

- Out of scope: the seven ` ```markdown ` fences with nothing wrong in them; the hand-wrapped blocks inside untagged fences — directory trees, command output, and line-sensitive formats — which are correctly exempt. No count is given for those: the issue's 6 and a survey's 23 are two different predicates over the same set, and neither is the one this guard applies, so any figure here would be a number nobody can re-derive. #58's re-grooming of `docs/BACKLOG.md`, which this unblocks but does not do.

### Clarifications

From `clarify`, 2026-08-31. Three questions, all answered as recommended.

- **Does a mechanical guard ship, and at which enforcement layer?** A new validator, `scripts/check-markdown-fences.py`, on `.steering/tech.md`'s `- Validators:` line. Rejected: keeping it spec-local like #61's `verify.py`, which satisfies AC2 and then gates nothing — the convention regressed silently once already, inside the branch that wrote it down, so leaving it to memory has been tried. Also rejected: folding it into `check-templates.py`, whose docstring commits it to one file and one question and which has no business reading `skills/backlog/SKILL.md`.
- **What paths does the rule cover?** Every tracked `.md`. Scoping enforcement to shipped paths only would restate the rule by _path_ — the same category of mistake as stating it by _delimiter_, which is the bug. All 10 ` ```markdown ` fences are under `skills/` today, so the two answers scan the same set now and differ only when a spec or work log grows one.
- **Does the rule travel to consumers through the skills?** No. The templates come out unwrapped and consumers do as they like. `.steering/product.md` draws the line at "not a document generator" and "not a language abstraction"; a prose-style instruction added to shipped skills is the harness taking a position on how consumers write, which #64 did not ask for.

## 2. Design (HOW)

- Fix approach, and why this rather than the narrower or wider fix:

Three parts, and only the second is the root cause.

1. **`CONTRIBUTING.md`, restated by content.** The carve-out becomes "fences holding literal code, output, or a line-sensitive format", and says a ` ```markdown ` fence holds Markdown and follows the convention. This is the half that lasts: without it the next person restores the wrapping _correctly_, by reading the rule.
2. **The 7 blocks unwrapped**, in `skills/backlog/SKILL.md` and `skills/spec/templates.md`. Mechanical, and 9 physical lines.
3. **`scripts/check-markdown-fences.py`**, so part 1 is enforced rather than remembered.

The narrower fix is 1 and 2 alone. Rejected under `clarify`. The wider fix propagates the rule into the shipped skills so consumers inherit it; rejected as scope the product deliberately excludes.

- **The guard's predicate, stated so it can be argued with:**

> Inside a ` ```markdown ` fence, no line is a continuation of the line above it.

A line is a **continuation** when it is non-blank, the line above it is non-blank and did not close a block, and the line itself opens no construct. Constructs are: an ATX heading, a list marker (`-`, `*`, `+`, `1.`, `1)`), a table row, a blockquote, a thematic break, a `{{SLOT}}`, and a line beginning `<`. Headings, table rows, and fence delimiters **close** a block, so the line after one always starts fresh.

Two properties of this predicate matter, and both are answers to what #61 cost.

**It does not ask what the transform would do.** `.specs/61-.../observations.md` records a verifier whose `normalise` was `unwrap(unwrap(x))` compared against `unwrap(x)` — true by construction for any idempotent transform — reporting `0 changes` on a diff that broke three issue templates. A guard that asks "would the transform join this?" inherits every bug the transform has. This one states a property of the text instead.

Stated at its real scope, after two rounds of review narrowed it: `OPENER`'s first five alternatives are `unwrap.py`'s `NEW_BLOCK` reordered, so an error in the construct vocabulary would be common to both. Of the three remaining alternatives, only the bare `<` that clears `skills/contract/SKILL.md:47-48` has no counterpart anywhere in `unwrap.py` — the thematic break and `{{SLOT}}` both do, at `unwrap.py:70` and `:30`, outside `NEW_BLOCK`. What is genuinely not shared is the decision procedure.

**It is stated positively, which is why `skills/contract/SKILL.md:47-48` clears it.** Those two lines both begin `<`, so both open a construct and neither is a continuation. That is a _reason_, not an exception carved to make the count come out right — which is the trap `observations.md` names as "a self-test proves the checker catches the class of defect its author imagined." The line beginning `<` is a template slot: the notation these fences use for "the author writes this here."

Its stated limit: a hand wrap whose continuation line happens to begin with `<` is invisible to it. Contrived, not present in the tree, and recorded rather than papered over.

- **The guard fails closed, three ways.** Finding zero ` ```markdown ` fences is a failure, not a pass — "verified everything" and "compared nothing" must not share an exit code, which is #16, #39, and the fourth fail-open `verify.py` shipped. A fence it cannot classify — a nested fence inside a ` ```markdown ` body, which no file has today — is a failure rather than a guess. A file that exists but cannot be read is a failure, matching `check-templates.py`.

- Affected files:

| File                                        | Change                                                                        |
| :------------------------------------------ | :---------------------------------------------------------------------------- |
| `CONTRIBUTING.md`                           | the carve-out restated by content; the new validator added to the pre-PR list |
| `skills/backlog/SKILL.md`                   | 2 blocks unwrapped, inside the ` ```markdown ` fence at :37                   |
| `skills/spec/templates.md`                  | 5 blocks unwrapped, inside the fences at :46 and :86                          |
| `scripts/check-markdown-fences.py`          | new                                                                           |
| `.steering/tech.md`                         | the new validator on the `- Validators:` line                                 |
| `AGENTS.md`                                 | "Run all nine" becomes ten, and the listing gains a row                       |
| `scripts/test-gates.sh`                     | two cases for the guard                                                       |
| `.claude-plugin/plugin.json`, `plugin.json` | 0.4.1 → 0.4.2                                                                 |
| `.github/workflows/ci.yml` | the new validator as a CI step |
| `.steering/structure.md`, `README.md`, `README.ja.md` | the `test-gates.sh` count, which this branch moves |
| `.claude/agents/gate-sdd-reviewer.md` | the new validator on the Bash whitelist — **this resolves #49**, which is open until this merges |
| `.specs/64-.../verify.py` | new; AC4 and AC6 against the base revision |
| `docs/EPICS.md` | #49's line, which this branch falsifies |

- **Blast radius:** `skills/spec/templates.md` is parsed by `check-templates.py`, which locates Tasks blocks by heading rather than by line number, so unwrapping shifts line numbers and must leave its count at 10 task lines across 3 templates. `.steering/tech.md`'s `- Validators:` line is read by `quality-gate.sh` with `sed … | head -1` and must stay one physical line; `check-steering-anchors.sh` counts anchor _keys_, so it stays at 5 of 5. `Source globs` already covers `skills/**/*.md` and `scripts/**/*.py`, so the new validator runs on exactly the turns that touch its subject. `skills/` is a shipped path, so `check-version-bump.py` requires the bump. The untagged fences holding line-sensitive formats are not touched — AC4 pins them byte-for-byte, and `check-receipt-schema.py` independently guards the receipt block across its 3 copies.

- **Why this cannot recur:** the rule that let it happen was stated by delimiter, and prose stated by the wrong property fails silently — nobody hits an error, the documents simply come out wrapped. Restating it by content fixes the reading; the validator makes the reading unnecessary. The class closes because the guard tests the property directly rather than testing whether someone remembered it.

## 3. Tasks (TDD-ordered)

> One task is one complete Red-Green-Refactor cycle, so one green commit.

- [x] T1: `scripts/check-markdown-fences.py` with a self-test that fails for the right reason — it reports 7 blocks over 9 lines on `3df25b0` and clears `skills/contract/SKILL.md:47-48` — then the unwrap of those 9 lines in the two files, which makes it pass
- [x] T2: the root cause — `CONTRIBUTING.md`'s carve-out restated by content, the validator wired onto `.steering/tech.md`'s `- Validators:` line, and `AGENTS.md` and the pre-PR list brought into agreement
- [x] T3: check the blast radius — two `test-gates.sh` cases for the guard's fail-closed paths (zero fences found, and an unclassifiable nested fence), plus a negative control proving it fails on a deliberately re-wrapped fence
- [x] T4: AC4 and AC6 — byte-identity of the three line-sensitive fences against `3df25b0`, and, per the amended AC6, word-stream identity inside the changed fences with byte identity everywhere outside them
- [x] T5: version bump 0.4.1 → 0.4.2 in both manifests; refactor
