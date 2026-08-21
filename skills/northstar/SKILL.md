---
name: northstar
description: Name the one metric this product moves, the levers that move it, and the quality property a defect would most damage. Use at project inception, before the PRD. Produces the anchor that every reviewer severity is judged against.
---

# northstar — What this product is for

One page. It exists so that every later argument — which feature first, how bad is this bug, is this trade-off acceptable — has something to be argued *against* other than preference.

Its most load-bearing output is a single line: **the quality property this project owns.** That line lands in `.steering/product.md` as `- Owns:`, and the reviewer reads it to decide whether a swallowed error is a Blocker or a nit. A project that has not answered it gets a reviewer working from taste.

## Where it goes

`<docs>/NORTH_STAR.md` — and the `- Owns:` line it derives goes into `.steering/product.md`.

`<docs>` is the `- Docs:` line in `.steering/tech.md`, which defaults to `docs/`. In a multi-repo product it points at the shared documentation repository instead, so product-level truth has one home rather than one per repo.

## Steps

1. **Name the metric.** One number that goes up when the product is working. Not a proxy the team can game, and not revenue unless revenue is genuinely the thing.
2. **Name the levers** — the three to five inputs that actually move it. Give each a stable id in whatever prefix this project uses, so a spec can cite the lever it serves. The harness does not impose a vocabulary; pick one and keep it.
3. **Name the quality laws**, in priority order. Two or three. The order matters more than the words: it is what settles a conflict between them, and conflicts are the only time anyone reads this.
4. **Name the non-negotiable** — the thing this product will not do even when it would help the metric. A north star without one is a growth plan.
5. **Derive the `Owns:` line** — of the laws, which property would a defect in *this* repo most damage. In a multi-repo product, each repo owns a different one; say which and why.
6. Write it, then update `.steering/product.md` with the `- Owns:` line.

## Template

```markdown
# North star

## The metric
<one number, and what it means when it moves>

## Levers
- **<L1> <name>** — <the input, and how it moves the metric>
- **<L2> <name>** — ...

## Quality laws, in priority order
1. **<law>** — <what it means concretely>
2. **<law>** — ...

When two conflict, the higher one wins. <Give the worked example that made you order them this way.>

## Non-negotiable
<the thing this product will not do, and what it costs to hold that line>

## Owns
<the quality property this repo owns, and why this repo and not a sibling>
```

## Rules

- **One page.** If it needs two, the metric is not yet one metric.
- Levers get ids, because a spec that says "serves <L2>" is checkable and a spec that says "improves the experience" is not.
- **Order the laws.** An unordered list of virtues resolves nothing, which is the only job this section has.
- Do not write this from the code. It is a product decision; ask the user, and record their answer rather than a plausible one.

## Red flags

- Every lever sounds equally important. Then they have not been ranked, and the document cannot settle anything.
- The non-negotiable is something the product would never be tempted to do anyway. That is not a commitment, it is decoration.
- The `Owns:` line names all three laws. Owning everything is owning nothing, and the reviewer ends up with no anchor.
