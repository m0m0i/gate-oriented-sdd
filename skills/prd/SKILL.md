---
name: prd
description: Write the product requirements — who it is for, what capabilities it must have, what it deliberately is not — with stable capability ids that specs cite. Use at project inception, after northstar and before any technical design.
---

# prd — What to build, and for whom

The document that later specs point back to. Its job is not to describe features in detail — that is what a spec does, one feature at a time. Its job is to name the **capabilities**, give each a stable id, and draw the boundary around what this product is not.

Capability ids are the mechanical output — in whatever prefix this project uses: a spec cites the capability it serves, and a capability with no spec after six months is either dead or a lie.

## Where it goes

`<docs>/PRD.md` — summarised into `.steering/product.md`.

`<docs>` is the `- Docs:` line in `.steering/tech.md`, which defaults to `docs/`. In a multi-repo product it points at the shared documentation repository instead, so product-level truth has one home rather than one per repo.

## Steps

1. **Read `northstar`** if it exists. Every capability must move a named lever; a capability that moves none is one to argue about now rather than after it is built.
2. **Name the users** — not personas with invented names, but the distinct jobs people bring to the product. Two users with the same job are one user.
3. **Write capabilities, not features.** A capability is what the user can now do; a feature is how. A capability id survives three redesigns of the screen that delivers it; a feature id does not.
4. **Give each a stable id and the lever it serves.** Ids never change, even when the wording does.
5. **Write the boundary.** What this product deliberately does not do, and where that need is met instead. This section prevents more work than the rest of the document combined.
6. **State what would falsify it** — the observation that would tell you a capability was wrong. A requirement nobody could ever disprove is a wish.
7. Register the ids wherever this project tracks them, and summarise into `.steering/product.md`.

## Template

```markdown
# Product requirements

- Serves: <the metric from northstar>
- Status: draft | agreed

## Users
- **<the job they bring>** — <what they are trying to get done, and what they do today instead>

## Capabilities
### <capability id> — <name>
- Serves: <lever id>
- The user can: <one sentence, from the user's side>
- Done when: <the observable condition — not "the feature ships">
- Falsified by: <what you would see if this were the wrong capability>

## Out of scope
- <what this product does not do> — <where that need is met instead, and why not here>

## Open questions
- <ambiguity that changes what gets built, with who can answer it>
```

## Rules

- **Capabilities, not screens.** If the id would have to change when the UI is redesigned, it is a feature.
- **"Done when" is observable.** "Users are happy" is not; "a user completes the flow without asking support" is.
- Every capability cites a lever. If none fits, either the lever list is incomplete or the capability does not belong.
- Ids are immutable once anything cites them. Change the wording freely; never the id.
- Ask rather than invent. A PRD full of plausible assumptions is the most expensive document in the project, because everything downstream inherits them.

## Red flags

- The capability list reads like the current sprint. A PRD that describes what is already being built is a summary, not a requirement.
- Nothing is out of scope. Then the boundary has not been drawn, and every future argument about scope starts from zero.
- Every capability serves the same lever. Either the levers are wrong or the product is narrower than the north star claims.
