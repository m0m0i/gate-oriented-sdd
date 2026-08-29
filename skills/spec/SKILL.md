---
name: spec
description: Turn a feature idea or tracker issue into ONE reviewable spec — Requirements, Design, TDD-ordered Tasks — under .specs/. Use at the start of any new feature, before writing code.
---

# spec — Author a feature spec

Produce ONE document a teammate can review *before* any code is written. That document is the contract `implement` executes.

## Steps

1. **Require a tracker issue. No issue, no spec.** `.steering/tech.md` names this project's tracker and the command to read issues. Read the issue you were given.
   If there is no issue, **stop and say so.** Do not create one to proceed. An issue created here is unplanned work entering through the side door, bypassing the sprint that was supposed to decide what gets built — and the sprint stops meaning anything the first time it is bypassed silently. Offer to run `sprint`, or to create the issue explicitly as acknowledged unplanned work; either way it is the user's call, made out loud.
   The slug is `<n>-<kebab-title>`. It names **both** the branch and the spec directory, so an issue, a branch, a spec, and a PR are always the same unit of work.
   **The issue's type decides the spec's shape** — take it from the template used or the label applied: `feature`, `bug`, or `chore`. If it is genuinely unclear, ask. Do not default to feature; feature is the shape that fits a bug worst.
2. **Read the context you are about to design against**, and do not skip it: `.steering/product.md`, `.steering/tech.md`, `.steering/structure.md`, the issue body, and any design docs those point to.
3. **Draft section 1 (Requirements) only. Then stop and run `clarify`.** Design decided on top of a misread requirement is the most expensive rework there is, and it is invisible in review — a spec reads as confident either way.
4. After `clarify` resolves, write the rest of `.specs/<n>-<slug>/spec.md` with `Status: draft`, using the shape for this issue's type from **[`templates.md`](./templates.md)** — read only the one you need. Keep it tight; this is a working document, not a document to be admired.
5. State remaining open questions in the spec rather than resolving them silently. Ask the user about anything that changes scope.
6. Close by proposing the branch `<n>-<slug>` and the next command: `implement <n>-<slug>`.

## Status lifecycle

`draft` → `approved` → `done` → `archived`. One skill owns each edge, so a spec's status always says something true about who touched it last.

| Status | Meaning | Set by |
| :-- | :-- | :-- |
| `draft` | Written, not yet agreed. Not implementable. | `spec` |
| `approved` | The spec is agreed. `implement` may start. | you, when you accept it |
| `done` | Every task ticked, reviewer gate CLEAN, PR open. | `implement` |
| `archived` | Shipped, moved to `.specs/_archive/<slug>/` by a sweep run on request. | `archive` |

**Four statuses, not four steps.** Delivery ends at `done`: the PR merges and the issue closes there. `archived` is bookkeeping applied whenever `.specs/` has grown noisy, so a merged spec still sitting in `.specs/` is finished work, not an unfinished one.

**The spec is not a separate pull request.** One issue is one branch and one PR, and the spec is the first commit on that branch — so the diff reads spec first, then the code that satisfies it, and a reader can see what was agreed before any code existed.

What that gives up is worth stating: a merge used to sit between agreeing and building, and now nothing mechanical does. `approved` is a judgment you record, not an event a merge proves. If a spec is contentious enough that you want it settled before anyone writes code, push the spec commit and say so — the branch is reviewable at any point, and `clarify` still runs before Design exists, which is where the expensive misunderstandings actually get caught.

## Spec shapes

Three of them, in [`templates.md`](./templates.md). They share front matter and the TDD-ordered Tasks section; section 1 is where the type matters.

| Type | Section 1 is built around | The first task always begins with |
| :-- | :-- | :-- |
| `feature` | a user story and numbered acceptance criteria | a failing test for the new behavior |
| `bug` | reproduction, expected vs actual, and the **root cause** | a regression test that fails for the right reason |
| `chore` | **what must not change** — the invariant | tests covering preserved behavior that is currently untested |

**Begins with, not consists of.** The failing test and the code that answers it are **folded into a single task that ends green** — one task is one complete Red-Green-Refactor cycle, and therefore one commit. Splitting them across two tasks produces a first task that cannot be committed without ending the turn red, which the quality gate blocks. That is #10, and `scripts/check-templates.py` fails if the split returns to the templates.

A bug written to the feature template produces a user story that does not exist and acceptance criteria that are fiction. A chore with no stated invariant is indistinguishable from a rewrite, and the reviewer has no way to tell them apart.

## Rules

- One issue = one spec = one feature = one branch = one PR. If a spec needs two branches, it is two specs.
- Tasks are TDD-ordered: a failing test precedes the implementation it describes.
- **No issue, no spec.** The issue is the commitment; the spec is how it gets built. Writing the second without the first means something is being built that nobody chose.
- **The type is not cosmetic.** It selects the shape, and the shape decides what the first task is. Getting it wrong produces a spec that looks complete and tests the wrong thing.
- **Number the acceptance criteria.** The reviewer reports coverage by id, and criteria it cannot address by id read as covered when they are not.
- Write acceptance criteria an observer could check. "The code is clean" is not a criterion; "WHEN the token is expired THE SYSTEM SHALL reject the request with 401" is.
- Do not implement here. Hand off to `implement`.
