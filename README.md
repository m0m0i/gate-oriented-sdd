# gate-oriented-sdd

**Spec-driven development where the review gate is enforced by a hook, not requested by prose.**

One plugin directory, installing into both [Claude Code](https://claude.com/claude-code) and [Google Antigravity](https://antigravity.google/).

---

## The problem this solves

Most spec-driven setups are a folder convention plus instructions asking the model to follow them. That works until it doesn't. Instructions are advisory: late in a long session, on a task that is nearly finished, a model can simply not run the review step — and nothing notices, because the thing that was supposed to notice was also an instruction.

The result is a process that reports compliance it did not achieve. Which is worse than no process, because you stop checking.

## The idea

Sort every rule by **how much it can be talked out of**, and put it at the layer that matches.

| Layer | Mechanism | Can it be skipped? |
| :-- | :-- | :-- |
| **Process** | skills — `spec`, `clarify`, `implement`, `worklog`, `archive` | Yes. It is guidance, and that is appropriate. |
| **Judgment** | a read-only reviewer subagent with a vendored, hash-pinned rulebook | It can be skipped — so a receipt records whether it ran. |
| **Determinism** | `Stop` hook: format, lint, types, and receipt freshness | **No.** |

The bottom row is the only one that is a guarantee. The design work is deciding what earns a place there — and keeping that list short enough that the gate stays welcome.

### Two things worth stealing even if you don't use this

**The rulebook lives inside the agent's directory.** A reviewer's rules sit in `agents/<reviewer>/rules/`, not in `CLAUDE.md` and not in session context. A normal session never loads them; only the reviewer does, and only the files the diff calls for.

That is measurable rather than asserted. `claude plugin details gate-sdd` reports **~778 tokens always-on** for the entire harness — six skills and three reviewers. The rulebooks and the reviewer contract are another **~5865 tokens**, and they contribute **zero** to that always-on figure, because they are not registered components at all. Reference material you pay for on every turn is reference material you will eventually delete.

**The rulebook is pinned, and pinned honestly.** `rules-lock.json` distinguishes **vendored** files — upstream text reproduced byte-for-byte, whose hash must match upstream — from **derived** files, which are rules written here that cite first-party sources. Upstream moving does not make a derived rule wrong; it makes it *unverified*, which is a different problem with a different fix. Hashing live documentation HTML was tried and rejected: it changes for navigation edits, and an alarm that fires for non-reasons gets switched off.

### Why the gate is narrow

A gate that fires on ordinary turns gets disabled, and a disabled gate protects nothing. So `review-gate.sh` is silent unless a spec branch has every task ticked and no fresh clean review. It skips merged branches, mid-implementation turns, and the documentation commits that legitimately land *after* a review. Nine paths, [tested deterministically](./scripts/test-gates.sh) with no model in the loop.

## The flow

```
spec ──▶ clarify ──▶ (review PR) ──▶ implement ──▶ reviewer ──▶ worklog ──▶ archive
         ≤5 questions               Red/Green/Refactor   receipt
```

One issue = one spec = one branch = one PR. `clarify` is the phase most setups lack: the dominant failure of spec-driven development is not too little structure, it is a confident spec built on a misread requirement — and review cannot catch that, because the document reads the same either way.

## Install

**Claude Code**

```bash
claude plugin marketplace add m0m0i/gate-oriented-sdd
claude plugin install gate-sdd@gate-oriented-sdd
```

**Google Antigravity** — no git-based plugin install exists yet, so clone first:

```bash
git clone https://github.com/m0m0i/gate-oriented-sdd
agy plugin install ./gate-oriented-sdd
```

Then run `init` inside a project. It reads the repo before it asks you anything, runs each validator before adopting it, and verifies the gate is silent before declaring success.

## Fidelity between the two harnesses

Every row was produced by running it. Method, versions, and open questions: [`docs/verified.md`](./docs/verified.md).

| Capability | Claude Code | Antigravity |
| :-- | :-- | :-- |
| Skills, reviewers, rulebooks | full | full — same path, same format |
| Quality gate on turn end | full — `Stop`, exit 2 | full — `Stop`, `{"decision":"continue"}` |
| Review-receipt gate | full | full |
| Per-edit fast feedback | full — `PostToolUse` | full — `PostToolUse`, observe-only |
| Steering re-injection after compaction | full — `SessionStart` | **none** — no such event |

The last row is a real gap, not a rounding error. `PreInvocation` is the candidate substitute and needs a once-per-session guard before it is worth shipping.

## Status

**Pre-release.** A reference implementation with a tested-against version matrix, not a supported product. The [eval suite](./evals/) is authored but has never been run — `claude plugin eval` is in early access and was not enabled on the account this was built on, and claiming a green suite that never ran is exactly the unverified assertion this harness exists to prevent.

Tested against: Claude Code 2.1.238 · Antigravity CLI 1.1.17 · Antigravity IDE 2.3.1 · macOS.

## License

Apache-2.0.
