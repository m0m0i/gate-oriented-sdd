---
name: spec
description: Turn a feature idea or tracker issue into ONE reviewable spec — Requirements, Design, TDD-ordered Tasks — under .specs/. Use at the start of any new feature, before writing code.
---

# spec — Author a feature spec

Produce ONE document a teammate can review *before* any code is written. That document is the contract `implement` executes.

## Steps

1. **Anchor the work to a tracker issue.** `.steering/tech.md` names this project's tracker and the command to read and create issues. If invoked with an existing issue number, read it. Otherwise draft a title and body — the problem, the outcome, acceptance criteria — create the issue, and capture its number `<n>`.
   The slug is `<n>-<kebab-title>`. It names **both** the branch and the spec directory, so an issue, a branch, a spec, and a PR are always the same unit of work.
2. **Read the context you are about to design against**, and do not skip it: `.steering/product.md`, `.steering/tech.md`, `.steering/structure.md`, the issue body, and any design docs those point to.
3. **Draft section 1 (Requirements) only. Then stop and run `clarify`.** Design decided on top of a misread requirement is the most expensive rework there is, and it is invisible in review — a spec reads as confident either way.
4. After `clarify` resolves, write the rest of `.specs/<n>-<slug>/spec.md` from the template below, with `Status: draft`. Keep it tight; this is a working document, not a document to be admired.
5. State remaining open questions in the spec rather than resolving them silently. Ask the user about anything that changes scope.
6. Close by proposing the branch `<n>-<slug>` and the next command: `implement <n>-<slug>`.

## Status lifecycle

`draft` → `approved` → `done` → `archived`. One skill owns each edge, so a spec's status always says something true about who touched it last.

| Status | Meaning | Set by |
| :-- | :-- | :-- |
| `draft` | Written, under review in its own PR. Not implementable. | `spec` |
| `approved` | The spec PR merged. `implement` may start. | you, when that PR merges |
| `done` | Every task ticked, reviewer gate CLEAN, PR open. | `implement` |
| `archived` | Shipped, moved to `.specs/_archive/<slug>/`. | `archive` |

## Spec template

```markdown
# Spec: <Feature title>
- Slug: <slug>   Issue: <n>   Status: draft
- Author: <you>   Date: <YYYY-MM-DD>

## 1. Requirements (WHAT / WHY)
- User story: As a <role>, I want <goal>, so that <benefit>.
- Why now / what it serves: <the goal, metric, or quality property this moves>
- Acceptance criteria, EARS-style and individually numbered:
  - [ ] **AC1:** WHEN <event> THE SYSTEM SHALL <observable behavior>.
  - [ ] **AC2:** ...
- Out of scope: <what this deliberately does not do, and where that work lives instead>

### Clarifications
<Filled by `clarify`: question, answer, date. "None needed" if the requirements were unambiguous.>

## 2. Design (HOW)
- Approach and key decisions:
- Affected modules and files, per .steering/structure.md:
- Contract changes (schemas, APIs, storage shapes) — and who else consumes them:
- Risks and trade-offs:

## 3. Tasks (TDD-ordered)
- [ ] T1: write the failing test for ...
- [ ] T2: implement ... to make it pass
- [ ] T3: refactor ...
```

## Rules

- One issue = one spec = one feature = one branch = one PR. If a spec needs two branches, it is two specs.
- Tasks are TDD-ordered: a failing test precedes the implementation it describes.
- **Number the acceptance criteria.** The reviewer reports coverage by id, and criteria it cannot address by id read as covered when they are not.
- Write acceptance criteria an observer could check. "The code is clean" is not a criterion; "WHEN the token is expired THE SYSTEM SHALL reject the request with 401" is.
- Do not implement here. Hand off to `implement`.
