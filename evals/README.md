# Evals

A harness whose thesis is *enforcement* cannot ship unverified. These cases exist to test the claims this repo makes, with the two that matter most being behavioural rather than textual:

| Case | Tests | Claim under test |
| :-- | :-- | :-- |
| `review-gate-blocks` | the **hook**, not the model | "enforced, not advisory" is a fact |
| `tdd-order-enforced` | `implement` | no implementation before a failing test |
| `clarify-before-design` | `spec` + `clarify` | ambiguity surfaces before design, not after |
| `reviewer-cites-rule` | a reviewer | every finding cites a rule id and `file:line` |

`review-gate-blocks` is the important one. It exercises `hooks/review-gate.sh` directly — a shell script with a spec fixture — so it passes or fails on mechanism rather than on model behaviour, and it is the case that distinguishes this harness from a folder of instructions.

## Status: authored, not yet run

`claude plugin eval` is in early access and was not enabled on the account these were written on, so **these cases have never been executed.** They are written to the documented bare shape (`prompt.md` plus `graders/*.md`) and should be treated as a specification of intent until someone runs them.

They are deliberately **not** wired into CI as a passing gate. Claiming a green eval suite that has never run would be exactly the kind of unverified assertion this harness exists to prevent.

## Running them

```bash
claude plugin eval .                      # all cases, with a no-plugin baseline arm
claude plugin eval . --case review-gate\* # one case
```

The baseline arm is the point: it reports the score delta between running with the plugin and without it, which is the difference between demonstrating that the harness changes behaviour and asserting that it does.

## When these pass, say so here

Replace this section with the versions tested against, the date, and the observed deltas. Until then this file says "unrun", because that is what is true.
