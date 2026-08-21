---
name: clarify
description: Interrogate a draft spec's Requirements for ambiguity before any Design or Tasks exist — at most 5 targeted questions, answers recorded in the spec. Use between drafting Requirements and writing the rest.
---

# clarify — Resolve ambiguity while it is still cheap

The dominant failure of spec-driven development is not too little structure. It is a confident spec built on a misread requirement: the structure produces volume rather than fidelity, and the error is only discovered in code review, or in production.

This step exists to make the model's uncertainty **visible while it is still cheap to fix** — before a design is committed to it.

## Steps

1. Read `.specs/<slug>/spec.md` section 1, the linked issue, and `.steering/`.
2. List every ambiguity you are currently resolving **by assumption**. For each, write down what you assumed and what a different reading would change.
3. Discard the ones whose readings lead to the same design. Those are details, not ambiguities.
4. Rank what survives by blast radius. An answer that changes the data contract or the affected-files list outranks one that changes a label.
5. Ask **at most 5** questions, highest blast radius first, each with your recommended answer marked so agreeing costs one word.
6. Record every question and its answer in the spec's `### Clarifications`, dated. If nothing was genuinely ambiguous, write "None needed — requirements were unambiguous." An empty section reads as skipped.
7. If an answer changes a requirement, amend section 1 before handing back to `spec` for Design and Tasks.

## Rules

- **Five is a ceiling, not a target.** Two good questions beat five padded ones, and padding trains the user to skim.
- **Never ask what the repo can answer.** `.steering/`, the issue, the existing code, and the project's own docs are yours to read first. A question whose answer sits in `.steering/tech.md` spends the user's attention to save your own.
- **Never ask for a decision that is yours.** "Which of these two equivalent namings" is not a clarification; it is you avoiding a call you are paid to make.
- An unresolved ambiguity does not block the spec PR — it is a documented open question. Say so rather than stalling.
- This skill writes no Design, no Tasks, and no code.
