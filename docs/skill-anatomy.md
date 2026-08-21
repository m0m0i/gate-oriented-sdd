# Skill anatomy

Every skill here follows the same shape, because the shape is what makes a skill usable by a model that has never read it before.

## Frontmatter

```yaml
---
name: <lowercase, hyphenated, matches the directory>
description: <what it does, when to use it — this is the only part loaded at session start>
---
```

The `description` is doing more work than it looks. Both harnesses load *name and description only* at session start and read the body when the skill activates, so the description is the entire basis on which the model decides whether this skill is relevant. Write it as **what it does plus when to use it**, in the vocabulary someone would use when they need it — not a summary of the body.

## Body

1. **Title line and the one-sentence claim.** What this produces.
2. **Why it exists**, when that is not obvious. A skill whose rationale is missing gets followed literally in situations it was never meant for.
3. **Steps**, numbered, imperative, in order.
4. **Templates**, in fenced blocks, if the skill produces a document.
5. **Rules** — the invariants that hold regardless of the steps, especially the ones that say *stop*.

## What belongs in a skill, and what does not

| Belongs | Does not |
| :-- | :-- |
| Process: the order of operations, and when to stop | Project specifics: validators, paths, commit conventions |
| Invariants that hold for every project | Anything a `.steering/` file can say instead |
| The reason a rule exists | Reference material the model will not need every time |

**Project specifics live in `.steering/`, and skills read them.** That single rule is what lets one copy of a skill serve every project without a templating engine, and it is why the directory names are fixed rather than configurable — the moment a path becomes a variable, every skill body becomes a rendered artifact and can drift.

## Length

If a skill needs more than roughly a hundred lines, most of it is probably reference material rather than process. Move that into a file the skill points to, so it is read when needed instead of every time. That is the same economy the reviewer's rulebook uses.
