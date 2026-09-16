# Documents

What this repository argued over, and the decisions it took. None of it is shipped — consumers get `skills/`, `agents/`, `hooks/` and `assets/`; the full table of what ships is in `.steering/structure.md`.

Two kinds of document live here, and the difference is who writes them.

## Inception documents

Written by the skills this harness ships, in the order the chain runs them. `assets/check-document-set.py` verifies this set against the `- Mode:` line in `.steering/tech.md` — `full` here, so all six are required rather than optional.

| Document | Holds | Written by | Required under |
| :-- | :-- | :-- | :-- |
| [`NORTH_STAR.md`](./NORTH_STAR.md) | the metric, its levers, and the quality laws | `northstar` | `full` |
| [`PRD.md`](./PRD.md) | users, capabilities, and the boundary | `prd` | `minimum`, `full` |
| [`DESIGN.md`](./DESIGN.md) | the architecture and its seams | `design-doc` | `minimum`, `full` |
| [`EPICS.md`](./EPICS.md) | demonstrable chunks | `epics` | `full` |
| [`BACKLOG.md`](./BACKLOG.md) | the product backlog, ordered and coarse | `backlog` | `minimum`, `full` |
| [`CONTRACT.md`](./CONTRACT.md) | the coding rules, by enforcement tier | `contract` | `full` |
| [`decisions/`](./decisions/) | one contested decision per file, append-only | `design-doc` | — |

`sprint` writes no file. It decomposes backlog items into tracker issues, and the issues are the record.

## Reference documents

Written by hand, about this repository rather than about a product.

| Document | Holds |
| :-- | :-- |
| [`layout.md`](./layout.md) | what the harness writes into a project, and how that differs from this repository's own tree |
| [`fidelity.md`](./fidelity.md) | what each target harness supports, and what this harness does about the difference |
| [`verified.md`](./verified.md) | what was observed on a real install, with versions and dates — the provenance behind `fidelity.md`'s rows |
| [`skill-anatomy.md`](./skill-anatomy.md) | the shape every skill here follows, and why |

## What is not here

`docs/` holds decisions. The record of *work* lives elsewhere, and [`layout.md`](./layout.md) has the full picture:

- `.steering/` — these decisions summarised in the form the skills and gates actually read, including the machine-read lines they parse.
- `.specs/` — live specs, one directory per issue; shipped ones are swept into `.specs/_archive/`.
- `.work_logs/` — the append-only session log.

At the repository root, `CONTRIBUTING.md` is for people and `AGENTS.md` is the canonical context file for agents, which `CLAUDE.md` points at.

## Conventions

- Markdown outside fences is not hand-wrapped: a paragraph is one physical line, and the reader's app decides the width (`CONTRIBUTING.md`).
- There is no site generator and no build — these files are read on GitHub. The two `README.md` indexes are maintained by hand, and nothing compares them to the directory; that cost is recorded in [ADR-7](./decisions/ADR-7-documentation-stays-plain-markdown-on-github.md).
