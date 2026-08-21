---
name: design-doc
description: Write the technical design — the architecture, the seams between components, and the decisions worth recording as ADRs. Use after the PRD and before the backlog, or when a capability needs a design bigger than one spec.
---

# design-doc — How it is built, and what was decided

Bridges the PRD's capabilities to the code's structure. Two mechanical outputs, and the skill is not finished until both exist:

- **`.steering/structure.md`** — where code belongs. Every later spec uses it to name affected files, and the reviewer uses it to judge whether a change landed in the right place.
- **ADRs** — one per decision that was genuinely contested. The reviewer's reconciliation clause escalates *to* an ADR when its rulebook and the repo conflict; without ADRs that clause points at nothing.

## Where it goes

`<docs>/DESIGN.md`, with one file per decision under `<docs>/decisions/ADR-<n>-<slug>.md` — and `.steering/structure.md` written from it.

`<docs>` is the `- Docs:` line in `.steering/tech.md`, which defaults to `docs/`. In a multi-repo product it points at the shared documentation repository instead, so product-level truth has one home rather than one per repo.

## Steps

1. **Read the PRD.** The design serves capabilities. A component serving no capability is either infrastructure that should say so, or scope that arrived without being agreed.
2. **Draw the components and the seams between them.** The seams matter more than the boxes: a seam is where two parts must agree, and every integration failure lives at one.
3. **For each seam, say what crosses it** — the shape of the data, who produces it, who consumes it, and what happens when they disagree about the shape. In a multi-repo product, give the seam a stable id so both sides cite the same document.
4. **Record the contested decisions as ADRs**, one per decision. A decision with no alternative considered is not a decision; leave it out.
5. **Write `.steering/structure.md`** from the result — the directory layout, where tests mirror it, and the conventions a newcomer would otherwise violate.
6. Name the risks, and for each say what would make you change course.

## ADR template

```markdown
# ADR-<n>: <the decision, stated as what was chosen>
- Status: proposed | accepted | superseded by ADR-<n>
- Date: <YYYY-MM-DD>

## Context
<the forces in tension — what made this a decision rather than an obvious call>

## Decision
<what was chosen, in the active voice>

## Consequences
- <what this makes easy>
- <what this makes hard — this is the half people skip, and the half that matters later>
- <what would make us revisit>

## Alternatives considered
- **<option>** — <why not, specifically>
```

## Rules

- **Numbers are permanent and sequential.** Before writing ADR-`<n>`, check both the existing set *and* any open branches or PRs — two branches racing for the same number is a merge conflict in the one place ids are supposed to be stable.
- **ADRs are append-only.** A decision that changes gets a new ADR that supersedes the old one; the old one stays, because the reasoning that was once right is what explains the code that still exists.
- **Record the consequences you dislike.** An ADR listing only benefits is advocacy, and it will not help the person who has to reverse it.
- Do not design past the current capabilities. A design for capabilities nobody has agreed to is the most expensive kind of speculation.

## Red flags

- The diagram has boxes but no arrows. Then the seams are undefined, which is where the failures will be.
- Every decision is an ADR. If nothing was contested, you are recording notes, not decisions, and the set stops being worth reading.
- The design names a technology before naming the constraint that requires it. That ordering is how a stack gets chosen by familiarity and justified afterwards.
