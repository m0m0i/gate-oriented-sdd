---
name: Bug
about: Something behaves differently from what it should
title: ""
labels: bug
assignees: ""
---

## Reproduction
<The shortest sequence that shows it. A bug nobody can reproduce becomes a spec nobody can write a failing test for — and the failing test is the first task.>

1.
2.

## Expected
<What should happen, and what says so — a spec, a contract, a documented behavior.>

## Actual
<What happens instead. Exact output, error, or screenshot.>

## Scope of impact
<Who hits this, how often, and what it costs them. This decides severity, and severity decides whether it goes ahead of planned work.>

## First suspicion
<Where you think it lives, if you have a guess. Say "unknown" rather than guessing plausibly — a confident wrong pointer costs more than no pointer.>

## Regression risk
<What else touches this code path and could break when it is fixed.>

---
*The spec for this starts with a failing test that reproduces it. If the reproduction above is not concrete enough to write that test from, the issue is not ready.*
