# Spec: Unwrap hard-wrapped Markdown and write the convention down

- Slug: 61-unwrap-hard-wrapped-markdown Issue: 61 Type: chore Status: done
- Author: m0m0i Date: 2026-08-30

## 1. Requirements (WHAT / WHY)

- What changes: join every hand-wrapped block in the tracked Markdown files that contain one — 50 files as it turned out, 49 of them reflow-only, against a survey of 54 by a deliberately loose detector — so a paragraph and a list item are each one physical line and the reader's app decides the width. Add one sentence to `CONTRIBUTING.md` stating the convention, so it stops being inferred from whatever file is nearby.

- **What must NOT change:**
  - **Rendered output.** Joining a wrapped paragraph's lines produces identical HTML. A file whose rendering changes has had its structure altered, not its wrapping — that is the invariant this chore is defined by, and without it a reflow and a rewrite are the same diff.
  - **The machine-read steering lines**, each on one physical line and byte-identical: `- Owns:`, `- Validators:`, `- Reviewer:`, `- Source globs:`, `- Docs:`. They are read with `sed … | head -1`, so a join that pulled a following line into one of them corrupts the value in a way nothing reports. `assets/check-steering-anchors.sh` must resolve 5 of 5 throughout.
  - **Both mirror pairs, still byte-identical.** `agents/_shared/reviewer-contract.md` ↔ `.claude/agents/_shared/reviewer-contract.md`, enforced by `check-receipt-schema.py`; and `.github/ISSUE_TEMPLATE/*.md` ↔ `assets/issue-templates/*.md`, currently identical and enforced by nothing.
  - **Every guard's count**: 9 skill contracts, 10 task lines across 3 templates, 7 receipt fields across 3 copies, 5 of 5 anchors, a nonzero pinned-lock count, and `test-gates.sh` at 52/0.
  - **Rule ids and rule text.** None of the six hash-pinned rulebooks changed, so no lock needed re-pinning; the **three** that did change are the two under `.claude/agents/gate-sdd-reviewer/rules/` and `agents/_template/rules/starter.md`, which is a shipped path with no lock of its own — nothing covers any of them — see `observations.md` T4 and #19.
  - Code fences, tables, headings, front matter, and list nesting. Only line joins.

- Why now: nothing defines the width — no `.editorconfig`, no Prettier, no markdownlint, no formatter in CI, and no rule in `AGENTS.md`, `CONTRIBUTING.md`, `.steering/`, or any rulebook. It has already cost a review round: on #55's branch the reviewer twice cited "repo convention" for a wrap width it had inferred from a file written minutes earlier in the same session, and commit `7916a52` exists only to chase that. A convention nothing states gets enforced from whatever is nearby, which is #23's shape applied to style.

- Acceptance criteria:
  - [x] **AC1:** WHEN the change is complete THE SYSTEM SHALL be a fixed point of the transform — applying it again changes no file — verified by running it over every tracked Markdown file and reporting the count that would change, which must be zero. _Amended 2026-08-30, before T3 was committed — see clarification 3._
  - [x] **AC2:** THE SYSTEM SHALL render identically before and after, demonstrated per file by comparing both sides with intra-block newlines collapsed to single spaces and reporting the count of files compared — not asserted by inspection.
  - [x] **AC3:** WHEN the change is complete all eight `- Validators:` commands SHALL exit 0 at their recorded baseline values: `check-steering-anchors.sh` 5 of 5, `check-skill-contracts.py` 9 contracts, `check-templates.py` 10 task lines across 3 templates, `check-receipt-schema.py` 7 fields across 3 copies, `check-locks.py` a nonzero pinned count, `test-gates.sh` 52 passed 0 failed.
  - [x] **AC4:** WHEN the change is complete `.steering/tech.md` and `.steering/product.md` SHALL still carry each machine-read line on one physical line, byte-identical to the baseline, verified by sha256 per line rather than by the anchor check alone.
  - [x] **AC5:** WHEN the change is complete both mirror pairs SHALL still be byte-identical, verified by sha256.
  - [x] **AC6:** THE SYSTEM SHALL state the convention in `CONTRIBUTING.md` in one sentence naming what it applies to and why.
  - [x] **AC7:** WHEN shipped paths change THE SYSTEM SHALL carry a version bump in both manifests, agreeing, so `check-version-bump.py` and `check-manifests.py` both pass.

- Out of scope:
  - Adding a formatter, an `.editorconfig`, or a lint rule. The convention is "do not hand-wrap", which needs no tool and gains a dependency if it gets one.
  - Rewording anything. This changes line breaks and nothing else.
  - Tagging the release. #62 owns the tag, and the untagged-0.4.0 problem it describes exists independently of this change.

### Clarifications
Resolved 2026-08-30.

1. **Q: This branch touches shipped paths, so `check-version-bump.py` forces a bump — but 0.4.0 is already in both manifests and was never tagged. What does this PR bump to?** **A: 0.4.1.** 0.4.0 becomes a version that existed only in the manifests, and consumers move 0.3.9 → 0.4.1 carrying both #52's flow change and this reflow. Rejected: retroactively tagging 0.4.0 from today's `main`, because that tag would point at a tree containing #55's documents rather than at where 0.4.0 was set, which is honest about the number and dishonest about its contents. Also rejected: 0.5.0, since a reflow changes no meaning and #52 already had its bump. Consequence for #62: it is no longer "tag the version that exists" but "tag 0.4.1, and add the guard that would have caught a bumped-but-untagged version" — the check-version-bump/tag gap it describes is unchanged by this decision.

2. Nothing else was genuinely ambiguous. Two candidates were discarded because both readings lead to the same design: whether a reflow of shipped skill text is patch or minor (it changes no meaning a model reads, so patch), and whether `evals/` needs a bump (it is not in `check-version-bump.py`'s `SHIPPED` tuple, and `.steering/structure.md` records it as not shipped).

3. **Q: AC1 said "verified by the same detector that produced the scope, reporting zero". That detector counts any block of consecutive short lines, which includes YAML front matter and a list of five short items — both legitimately multi-line. It cannot reach zero.** **A: Restate AC1 as a fixed point.** The exact question is whether the transform would still change anything, so AC1 now asserts that applying it again changes no file. Raised after T2's tooling was corrected and before T3's application was committed, so the amendment precedes the artifact it judges — the convention #59 exists to write down, and which #55 got wrong once. `detect.py` stays in the branch as the survey tool that produced the scope. It is deliberately loose, and its remaining count of 30 across 23 files is front matter and short-item lists, not work left undone.

## 2. Design (HOW)

- **The transform.** Within a block, join line *n+1* into line *n* unless *n+1* starts a new construct — a list marker (`- `, `* `, `N. `), a heading, a table row, a blockquote marker, or a fence. Blank lines, fenced code, tables, headings, and front matter pass through untouched. Nesting is preserved by keeping the first line's indentation and discarding the continuation's.

- **The one-way hazard, and why the rule above is written as it is.** A machine-read steering line is a list item. If the join rule were "join every consecutive pair", `- Validators: a, b, c` would absorb the following `- Reviewer: …` line and both values would be destroyed while `sed … | head -1` kept returning something that looked plausible. Refusing to join across a list marker is what makes that impossible, and AC4 checks the result per line rather than trusting the rule.

- **Verification is the deliverable, not the diff.** AC2 compares each file before and after under `canon.py`, which parses independently of the transform. It runs over all 83 Markdown files present on `main`, not only the ones that changed — broader than the survey, so a file the survey missed cannot slip through.

- **Order of operations.** The baseline (T1) must precede the transform, because AC3 and AC4 are comparisons and there is nothing to compare against otherwise — the lesson #55 recorded. The version bump lands with the shipped-path change, not after it, because `check-version-bump.py` evaluates the PR as a whole.

- **Affected files.** 50 Markdown files across `.specs/`, `.work_logs/`, `evals/`, `docs/`, `.claude/agents/`, `.steering/`, `agents/`, `skills/`, and `AGENTS.md`; plus `CONTRIBUTING.md` for the convention, and both manifests for the bump. Eight surveyed files come out unmodified — the six issue templates, whose front matter and bare list markers are all structure, plus `evals/clarify-before-design/prompt.md` and `skills/epics/SKILL.md`. Four modified files were in no survey, three of them shipped skills; see `observations.md` on the detector under-reporting.

- **Coverage gap.** Nothing in this repo asserts that the two issue-template mirrors are byte-identical — `check-receipt-schema.py` covers the reviewer-contract pair only. They are identical today by habit. AC5 checks both pairs here, but after this branch the issue-template pair remains unguarded; that is a finding to record, not to fix under this spec.

- **Rollback.** `git revert`, then `./assets/check-locks.py --update`.

## 3. Tasks (TDD-ordered)
> One task is one complete Red-Green-Refactor cycle, so one green commit.

- [x] T1: capture the baseline — the eight validator results, `test-gates.sh`, a sha256 per machine-read steering line, a sha256 per mirror-pair member, and the hard-wrapped-block count per file — into the branch. This is the before-side of AC1, AC3, AC4 and AC5.
- [x] T2: write the transform and the normalised-equivalence check, and prove the check catches a real difference before trusting it — feed it a file with a word deleted and confirm it reports a mismatch. A verifier that cannot fail is the guard this repo exists to reject.
- [x] T3: apply the transform to every tracked Markdown file; assert AC1 (a second pass changes no file) and AC2 (every file compares identically under `canon.py`), with the compared count recorded.
- [x] T4: assert AC4 and AC5 — every machine-read line byte-identical by sha256, both mirror pairs byte-identical — confirm no pinned rulebook changed, so no lock needs re-pinning, and assert AC3's eight validators at their baseline values.
- [x] T5: bump both manifests to 0.4.1 and add the convention sentence to `CONTRIBUTING.md`; assert AC6, AC7, `check-manifests.py`, and `check-version-bump.py` against the merge base.
