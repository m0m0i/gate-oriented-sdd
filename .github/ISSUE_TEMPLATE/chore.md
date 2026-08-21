---
name: Chore
about: Maintenance, refactor, dependency, tooling, or infrastructure work
title: ""
labels: task
assignees: ""
---

## What changes
<The mechanical description. Upgrade X, extract Y, rename Z.>

## What must NOT change
<The observable behavior this work is required to preserve. This is the most important line in a chore issue: it is what the tests assert and what the reviewer checks, and a refactor without it is indistinguishable from a rewrite.>

## Why now
<What this unblocks, or what it costs to keep deferring. "Tidiness" is a reason; say so plainly rather than dressing it as urgency.>

## How we will know nothing broke
<The existing tests that cover it, or the tests that must be written first because they do not exist yet.>

## Rollback
<How to undo this if it goes wrong in a way tests did not catch.>

---
*Sized so this becomes one spec, one branch, one PR. A chore that touches everything is several chores.*
