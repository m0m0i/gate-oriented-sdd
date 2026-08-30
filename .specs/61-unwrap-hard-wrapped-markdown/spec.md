# Spec: Unwrap hard-wrapped Markdown and write the convention down

- Slug: 61-unwrap-hard-wrapped-markdown Issue: 61 Type: chore Status: draft
- Author: m0m0i Date: 2026-08-30

## 1. Requirements (WHAT / WHY)

- What changes: join every hand-wrapped block in the 54 tracked Markdown files that contain one, so a paragraph and a list item are each one physical line and the reader's app decides the width. Add one sentence to `CONTRIBUTING.md` stating the convention, so it stops being inferred from whatever file is nearby.

- **What must NOT change:**
  - **Rendered output.** Joining a wrapped paragraph's lines produces identical HTML. A file whose rendering changes has had its structure altered, not its wrapping — that is the invariant this chore is defined by, and without it a reflow and a rewrite are the same diff.
  - **The machine-read steering lines**, each on one physical line and byte-identical: `- Owns:`, `- Validators:`, `- Reviewer:`, `- Source globs:`, `- Docs:`. They are read with `sed … | head -1`, so a join that pulled a following line into one of them corrupts the value in a way nothing reports. `assets/check-steering-anchors.sh` must resolve 5 of 5 throughout.
  - **Both mirror pairs, still byte-identical.** `agents/_shared/reviewer-contract.md` ↔ `.claude/agents/_shared/reviewer-contract.md`, enforced by `check-receipt-schema.py`; and `.github/ISSUE_TEMPLATE/*.md` ↔ `assets/issue-templates/*.md`, currently identical and enforced by nothing.
  - **Every guard's count**: 9 skill contracts, 10 task lines across 3 templates, 7 receipt fields across 3 copies, 5 of 5 anchors, a nonzero pinned-lock count, and `test-gates.sh` at 52/0.
  - **Rule ids and rule text.** The rulebooks are hash-pinned; their content changes only in line breaks, and the locks are re-pinned to match.
  - Code fences, tables, headings, front matter, and list nesting. Only line joins.

- Why now: nothing defines the width — no `.editorconfig`, no Prettier, no markdownlint, no formatter in CI, and no rule in `AGENTS.md`, `CONTRIBUTING.md`, `.steering/`, or any rulebook. It has already cost a review round: on #55's branch the reviewer twice cited "repo convention" for a wrap width it had inferred from a file written minutes earlier in the same session, and commit `7916a52` exists only to chase that. A convention nothing states gets enforced from whatever is nearby, which is #23's shape applied to style.

- Acceptance criteria:
  - [ ] **AC1:** WHEN the change is complete THE SYSTEM SHALL contain no hand-wrapped block in any tracked Markdown file — every prose paragraph and every list item is one physical line — verified by the same detector that produced the scope, reporting zero.
  - [ ] **AC2:** THE SYSTEM SHALL render identically before and after, demonstrated per file by comparing both sides with intra-block newlines collapsed to single spaces and reporting the count of files compared — not asserted by inspection.
  - [ ] **AC3:** WHEN the change is complete all eight `- Validators:` commands SHALL exit 0 at their recorded baseline values: `check-steering-anchors.sh` 5 of 5, `check-skill-contracts.py` 9 contracts, `check-templates.py` 10 task lines across 3 templates, `check-receipt-schema.py` 7 fields across 3 copies, `check-locks.py` a nonzero pinned count, `test-gates.sh` 52 passed 0 failed.
  - [ ] **AC4:** WHEN the change is complete `.steering/tech.md` and `.steering/product.md` SHALL still carry each machine-read line on one physical line, byte-identical to the baseline, verified by sha256 per line rather than by the anchor check alone.
  - [ ] **AC5:** WHEN the change is complete both mirror pairs SHALL still be byte-identical, verified by sha256.
  - [ ] **AC6:** THE SYSTEM SHALL state the convention in `CONTRIBUTING.md` in one sentence naming what it applies to and why.
  - [ ] **AC7:** WHEN shipped paths change THE SYSTEM SHALL carry a version bump in both manifests, agreeing, so `check-version-bump.py` and `check-manifests.py` both pass.

- Out of scope:
  - Adding a formatter, an `.editorconfig`, or a lint rule. The convention is "do not hand-wrap", which needs no tool and gains a dependency if it gets one.
  - Rewording anything. This changes line breaks and nothing else.
  - Tagging the release. #62 owns the tag, and the untagged-0.4.0 problem it describes exists independently of this change.

### Clarifications
<pending — `clarify` has not run>

## 2. Design (HOW)
<not yet written — Requirements first, per `spec` step 3>

## 3. Tasks (TDD-ordered)
<not yet written>
