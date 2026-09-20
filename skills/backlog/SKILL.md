---
name: backlog
description: Order the whole of the known work into a product backlog, with an explicit critical path and reasons for the order. Use after epics, and to re-groom when reality diverges. Creates no issues — sprint does that.
---

# backlog — Everything known, in one order

The **product backlog**: the whole of the known work in a single ordered list, with the reason for the order written down. It is groomed occasionally, not every iteration.

**It is ordered, not prioritized** — and the distinction is the whole point. Scrum changed that word deliberately: ordering by priority is only one technique among several, and rarely the best one. A position reflects **value, risk, cost, and dependency together**, weighed against each other, which is precisely what a single priority label cannot express.

So there is one list, every item has exactly one position, and that position is the only statement of sequence the document makes. No priority labels, no tiers, no parallel "critical" list — each of those is a second opinion that can contradict the first, and the moment two disagree the list stops being trusted and people fall back to asking someone.

A total order is uncomfortable on purpose. It forces the comparison between two things you would rather call "both high", and that comparison is the entire value of the exercise. The `Why here` column is where it gets resolved: not "P1", but *why above the item below it*.

It deliberately creates **no issues**. That is `sprint`'s job, and the separation matters: work becomes an issue at the moment someone commits to doing it, and everything before that moment is a plan that can still change cheaply.

`sprint` is the one other skill that writes here, and only one way: when it turns a row into issues it records those issue numbers on the row it took, and changes nothing else. That is not a second author — it is the single moment when this document is knowably wrong and the skill that made it wrong is still running (#79).

**Two doors stay open that no skill can close**: an issue closed by a merge, and an issue filed outside a grooming. Nothing runs at either moment, so nothing can be instructed to write them down. Compare the list against the tracker instead — no open issue missing from it, and no `Item` cell citing work that has finished — and start a grooming from what that comparison turns up rather than from a re-read of the whole document. Whether a command does the comparing or a person does it by hand, it is the half of a grooming nobody can do from memory.

When that comparison finds a row whose work has finished **between** groomings, the correction is bounded and does not wait for the next one: append the row to `## Discharged since last grooming` and drop it from the table. No order is revisited and no reasoning rewritten — though the positions below it do shift, which is the part of a discharge this section does not make cheaper. Treating a discharge as a re-groom is why it gets deferred to a grooming that is months away, and why the trace ends up wherever the person writing it could find room.

Ordering is the entire value. A list of everything that must be built is not a backlog; it is an inventory.

## Where it goes

`<docs>/BACKLOG.md` — the product backlog, groomed in place.

`<docs>` is the `- Docs:` line in `.steering/tech.md`, which defaults to `docs/`. In a multi-repo product it points at the shared documentation repository instead, so product-level truth has one home rather than one per repo.

## Steps

1. Read the epics. Start from the walking skeleton — it is always first, because it is what discovers integration problems while they are cheap.
2. **Weigh value, risk, cost, and dependency together** — not size alone, and not enthusiasm. The item that would most change the plan if it went badly goes as early as its dependencies allow.
3. **Force a total order.** No ties. When two items feel equal, that is the comparison worth making, not the one to avoid — ask which you would drop if only one could ship, and order by the answer.
4. **Flag the ones that block others.** A slip on a blocking item moves everything after it, so mark it on its row. It is an attribute of the item, not a second ranking.
5. **Note roughly how many issues each item is worth.** One backlog item usually becomes several issues — a change, the tests that were missing around it, the migration it forces. An item nobody can size at all is a signal: it needs a spike, or it needs to go back to `epics`.
6. **Record what left before recording the order.** Every row discharged since the last grooming goes under `## Discharged since last grooming`, one line and all four parts of it, and that section is pruned to the two most recent groomings' worth on the way past. Then record the order and the reasoning, so the next grooming starts from the argument rather than from scratch, and hand to `sprint`, which decomposes the top items into issues.

## Template

```markdown
# Product backlog

- Last groomed: <YYYY-MM-DD>
- Ordered, not prioritized. Position reflects value, risk, cost, and dependency together. There is no separate priority field, and adding one would contradict this.

| # | Item | Epic | Blocks | Rough size | Why here |
| :-- | :-- | :-- | :-- | :-- | :-- |
| 1 | <item> — **#n**, **#n** | EPIC-n | #3, #7 | <~n issues> | <the risk it retires, or what it unblocks> |
| 2 | <item> | EPIC-n | — | <~n issues> | <why above #3 specifically> |

The **Item** cell names the issues this row is live work for. `Why here` may cite any issue, including closed ones, as reasoning — "#146 left this row by shipping" is correct and has to stay sayable. That split is what lets the list be compared against the tracker without every piece of history reading as stale work.

## Discharged since last grooming
Rows that have left. One line each, and all four parts of it: the issue, the position it held, the date, and how it left — shipped by a named pull request, closed without shipping, or folded into a named row. A line missing one of the four is not a record; each is the question the next reader asks first.

- <#n> — row <n>, <YYYY-MM-DD> — shipped as <#n> | closed without shipping: <why> | folded into row <n>

One bullet per discharge, **never a table**. A second table here is indistinguishable from the ordered list to anything comparing this document against the tracker, so every issue a discharge table named would stop being reported as missing from the list — the section would quietly become an exemption list, which is the one thing it must not be.

This is the only home a discharge has, and appending to it is a bounded edit rather than a re-groom. Without it the trace lands in a surviving row's `Why here`, or in **What changed at this grooming**, or in the work log, or nowhere at all — a row that ships whole leaves no cell to carry the sentence. Prune at each grooming to the **two most recent groomings' worth** and drop what is older: the spec archive and the work log hold the detail, and a third grooming's worth makes this a second history of the list.

A rescoped row is not discharged. It did not leave, it was retitled, and its position still exists — that belongs below.

## What changed at this grooming
The **judgments** this grooming made: what moved and why, what was re-argued, what it deliberately did not do. Facts about rows that left go in the section above. A grooming whose whole record is "row 1 shipped" has recorded no judgment at all, and the next grooming starts from scratch rather than from the argument.

## Unshaped
Items that cannot be ordered yet because nobody knows what they are. This is a queue to empty, not a tier — anything sitting here is undecided work, and it does not get built while it stays here.

- <item> — <what has to be answered before it can take a position>

## Open, not planned
Issues that are open and deliberately not rows. One line each: the issue, why it is not planned, and the condition that would make it one. Not a tier and not a second backlog — an entry here is a decision that has been made, and the condition beside it is what reopens it.

- <#n> — <why it is not a row> — <what would make it one>
```

## Rules

- **The walking skeleton goes first.** Always. Reordering it later is how integration risk gets discovered at the end.
- **One list, one position per item.** No priority labels, no tiers, no separate critical list. A second statement of sequence can contradict the first, and then neither is believed.
- **"Ordered" rather than "prioritized" is not pedantry.** Priority reads as one dimension; a position has to absorb value, risk, cost, and dependency at once. The `Why here` column is where that reasoning lives, and a backlog without it is a ranking nobody can argue with — which means nobody can correct it either.
- **No ties.** "These two are both high" is the comparison being dodged.
- **This skill creates no issues.** Ordering is cheap and reversible; an issue is a commitment. Keeping them separate is what lets the plan change without leaving debris in the tracker.
- **A backlog item is not an issue.** One item commonly becomes several — the change, the test coverage it turns out to need, the migration it forces. Sizing them 1:1 at this stage is how a plan quietly becomes wrong, because the decomposition has not happened yet and cannot be guessed accurately.
- **The `Item` cell is the claim; `Why here` is the argument.** Only the Item cell asserts that an issue is live work, which is what lets a shipped issue stay quotable in the reasoning without reading as stale.
- **An open issue is either a row, unshaped, or deliberately not planned.** There is no fourth state, and silence is not one of them — an issue nobody has placed is work the list does not know about.
- Items are coarse on purpose. Fine-grained ordering of work nobody has decomposed is precision without accuracy.
- Every row states why *now*, in `Why here`. Without it the order is preference, and preference gets re-argued.
- Re-sequence when reality diverges. A backlog that has not moved in a month is either a finished plan or an ignored one.

## Red flags

- A priority column has appeared beside the position column. One of them is now lying, and people will learn which by trial.
- Half the list is flagged as blocking. Then blocking means nothing, and the flag has become a way of saying "important" without paying for a position.
- The order matches the epic numbers. Ordering by the sequence things were thought of is not ordering.
- `## Unshaped` never empties. Those items are being deferred without anyone deciding to defer them.
- Items read like issue titles. Then they have been decomposed too early, and the decomposition is now frozen into an ordering decision that has to be redone.
- The backlog has been created as issues. Then the tracker is a plan rather than a commitment, and every future search filters through work nobody chose.
- `## Unshaped` is empty while the table carries items nobody can size. Either the plan is unusually complete, or work that has not been shaped is being ordered as though it were actionable.
- `## What changed at this grooming` is a list of what shipped. Then the grooming recorded facts the section above it already holds and made no judgment at all, and the next grooming starts from scratch — which is the cost this whole document exists to avoid.
