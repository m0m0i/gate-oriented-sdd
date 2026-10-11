---
name: roadmap
description: Define major versions as content commitments with milestone demos and capability completions. Use between the PRD and the backlog.
---

# roadmap — Major versions, content commitments, and milestone demos

A capability is too large to build in one branch. A major version is the largest chunk that still ends in **something demonstrable you can show someone** — a content commitment, a theme, and the PRD capabilities it completes. It is not a date, a calendar quarter, or a sprint phase. If finishing a version produces nothing demonstrable, it is a phase of work, not a milestone, and it will slip invisibly.

## Where it goes

`<docs>/ROADMAP.md` — one section per major version (`## <major.minor>-<name>`).

`<docs>` is the `- Docs:` line in `.steering/tech.md`, which defaults to `docs/`. In a multi-repo product it points at the shared documentation repository instead, so product-level truth has one home rather than one per repo.

## Steps

1. Read the PRD. Work one major version at a time, and define each as a content commitment with a clear theme.
2. **Format version headers as `## <major.minor>-<name>`** (e.g. `## 1.0-baseline-harness`, `## 2.0-dual-target-parity`).
3. **1.0 is the walking skeleton by definition** — the thinnest end-to-end path through the whole system that discovers integration problems while they are still cheap. Subsequent versions build on it and do not carry a walking skeleton field.
4. **Name the capabilities completed** from the PRD on the `- Completes:` line (e.g. `CAP-1, CAP-2`).
5. **Name the demo** — the sentence you would say when showing the completed version. If you cannot write that sentence, the cut is wrong.
6. **Do NOT list issues or name backlog rows.** Version and issue membership are derived in `BACKLOG.md` from sequence relative to boundary lines in `## Lines`.
7. Specify dependencies on earlier versions (`- Depends on:`) and explicit scope boundaries (`- Not included:`).

## Template

```markdown
# Roadmap

Major versions are content commitments, milestone demos, and capability completions — not dates or calendar quarters. Issue and backlog row membership are derived in BACKLOG.md from position relative to version lines in ## Lines, never listed here.

## <major.minor>-<name>
- Completes: <capability id, ...>
- Demo: "<the sentence you would say while showing it>"
- Depends on: <earlier version, or nothing>
- Not included: <the adjacent thing people will assume is in here>
```

## Rules

- **Every major version ends in a demo.** No exceptions; a version without one is a layer or a date commitment.
- **Versions are content commitments, not calendar commitments.** Never date a version or tie it to a quarter.
- **Never list issues or name backlog rows.** Membership is derived from total order in `BACKLOG.md`.
- **1.0 is the walking skeleton by definition.** Do not write a `Walking skeleton` field.
- **Cut vertically.** Horizontal cuts feel efficient and defer all the integration risk to the end.
- Dependencies are stated, and a version depending on more than one or two others is probably scoped wrong.
- "Not included" is not padding. Most scope disputes are about the adjacent thing everyone assumed.

## Red flags

- A version is defined by a date, calendar quarter, or sprint phase instead of a content commitment.
- A version lists individual issues or names backlog rows (derive them in `BACKLOG.md`).
- A version carries a `Walking skeleton` field (1.0 is the skeleton by definition).
- The first version is "set up the project". Infrastructure with no demo attached expands to fill whatever time it is given; fold it into 1.0 instead.
- Versions map one-to-one onto components. That is a layer cut wearing milestone labels.
- No demo is attached (infrastructure with no demo attached slips invisibly).
