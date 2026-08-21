---
name: epics
description: Decompose capabilities into epics — chunks of work with a demonstrable outcome — each grouping the issues that specs will be written from. Use between the PRD and the backlog.
---

# epics — Capability-sized work, cut into demonstrable chunks

A capability is too large to build in one branch. An epic is the largest chunk that still ends in **something you can show someone.** That test is the whole definition: if finishing an epic produces nothing demonstrable, it is a phase of work, not an epic, and it will slip invisibly.

## Where it goes

`<docs>/EPICS.md` — one section per epic.

`<docs>` is the `- Docs:` line in `.steering/tech.md`, which defaults to `docs/`. In a multi-repo product it points at the shared documentation repository instead, so product-level truth has one home rather than one per repo.

## Steps

1. Read the PRD. Work one capability at a time, and say plainly if a capability is already small enough to be a single epic.
2. **Cut by outcome, not by layer.** "Database, then API, then UI" is three epics that each demonstrate nothing until the last. "The user can add one card and see one recommendation" is one epic that proves the whole path.
3. Give each an id and name the capability it serves.
4. **Name the demo** — the sentence you would say when showing it. If you cannot write that sentence, the cut is wrong.
5. List the issues each epic contains, at the granularity `spec` consumes: one issue = one spec = one branch = one PR.
6. Say which epic is the **walking skeleton** — the thinnest end-to-end path through the whole system. It goes first, always, because it is the only thing that discovers integration problems while they are still cheap.

## Template

```markdown
# Epics

## EPIC-<n> — <name>
- Serves: <capability id>
- Demo: "<the sentence you would say while showing it>"
- Walking skeleton: yes | no
- Issues:
  - <issue title> — <one line of scope>
- Depends on: <EPIC-n, or nothing>
- Not included: <the adjacent thing people will assume is in here>
```

## Rules

- **Every epic ends in a demo.** No exceptions; an epic without one is a layer.
- **Cut vertically.** Horizontal cuts feel efficient and defer all the risk to the end.
- Dependencies are stated, and an epic depending on more than two others is probably cut wrong.
- "Not included" is not padding. Most scope disputes are about the adjacent thing everyone assumed.

## Red flags

- The first epic is "set up the project". Infrastructure with no demo attached expands to fill whatever time it is given; fold it into the walking skeleton instead.
- Epics map one-to-one onto components. That is a layer cut wearing epic labels.
- No epic is the walking skeleton. Then integration risk is being deferred, and it is the risk most likely to invalidate the design.
