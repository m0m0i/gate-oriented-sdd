# Spec: A gate's block says who it is for, and a reviewer that meets one ends its turn

- Slug: 329-reviewer-ends-its-turn-on-a-gate-block   Issue: 329   Type: bug   Status: approved
- Author: m0m0i (Claude Code)   Date: 2026-10-27
- Approved: by the maintainer on 2026-10-27, whose go was "spec, clarify, then implement 329 for review".

The prose half of #329, as its triage of 2026-10-21 scoped it, plus one sentence in every gate's block (C1). The gate-side half, a skip for a subagent's own turn, needs a marker an agent cannot forge. The probe run at `clarify` (C3) found none, so the skip stays out of scope and backlog row 2 keeps the question.

## 1. Requirements (WHAT / WHY)

- **Reproduction:**
  1. In an Antigravity project, tick every task in `.specs/<slug>/spec.md`, with no `.review-receipt` yet.
  2. Follow `implement` step 2's Antigravity route (`skills/implement/SKILL.md:33-36`): register the reviewer with `define_subagent`, write tools off, and run it with `invoke_subagent` in the shared workspace.
  3. The reviewer sends its report and Receipt block to the parent with `send_message`, and ends its turn.
  4. Antigravity runs the workspace's `Stop` hooks in the reviewer's own turn. `review-gate.sh` blocks with the no-receipt message (`hooks/review-gate.sh:499`): "Run <reviewer> on the branch diff, then write its Receipt block to <receipt>. If <reviewer> is already running, wait for it and write the receipt from its result".
- **Expected:**
  - A reviewer that meets a gate's block ends its turn. It writes nothing, fixes nothing, starts nothing and waits for nothing: the contract makes it read-only (`reviewers/_shared/reviewer-contract.md:9`), and its report is already delivered.
  - The parent writes the receipt, CLEAN or BLOCKED, and then ends the reviewer.
- **Actual:**
  - In the field report, the reviewer read the block as addressed to itself. With no write tools, it polled the receipt with `view_file` until the parent wrote it and killed the reviewer with `manage_subagents`.
  - On CLI 1.4.7 (Q2, below), a stand-in gate that kept blocking the subagent re-entered it 10 times after its first turn end. That is A4's cap of 10 (`docs/verified.md:487`), and it applies to a subagent too. Only after the cap ran out was the parent told that the subagent "has gone idle". This is the BLOCKED arm's case (`hooks/review-gate.sh:507`), which blocks every turn end until the receipt changes.
  - The `self` route (`skills/implement/SKILL.md:35`) runs a subagent with its write tools on. On that route, the verdict arm's "Address every BLOCKER and HIGH finding" and the quality gate's "fix the failure" (`hooks/quality-gate.sh:625`) are instructions the reviewer can carry out.
- **Impact:** every Antigravity project that runs `implement` step 2, on every review. Triaged MEDIUM on 2026-10-21: a false block and a loop. The parent's own gate is untouched and still blocks, so nothing fails open. The field report is one consumer's Antigravity install; Q1 to Q3 reproduce its mechanism on the CLI.
- **Root cause:**
  - Antigravity runs a workspace's `Stop` hooks in every conversation in that workspace, a subagent's included. That was measured on CLI 1.4.7 (Q1).
  - The gates cannot tell whose turn it is. A subagent's `Stop` payload has the same keys as the parent's (Q1). #27's AC4 rules out an in-flight token (`.specs/_archive/27-spawned-reviewer-deadlocks-stop-gate/spec.md:35`), and an environment variable or a file the parent can set is that token.
  - So every block reaches the reviewer too. Each is written in the second person to the author (`hooks/review-gate.sh:338-339`), and neither the contract nor `implement` says what a reviewer does with a block, or that the parent ends the reviewer.
- **Acceptance criteria:**
  - [ ] **AC1:** WHEN any gate blocks a turn THE SYSTEM SHALL end the block's reason, on both channels, with one paragraph saying the block is for the session doing the work, and that a reviewer that receives it ends its turn without writing, fixing, starting or waiting for anything. "Any gate" covers every `gate_block`, its fixed fallback reason, and the bootstrap blocks in `quality-gate.sh`, `review-gate.sh` and `plugin-gate.sh` (C1). The paragraph appears once, including in a block a bounded child hands on.
  - [ ] **AC2:** WHEN the parent's turn ends with every task ticked and no CLEAN receipt THE SYSTEM SHALL block exactly as before. The no-receipt arm still names waiting for a running reviewer as the valid action (#27's AC2), and no gate gains a skip, a state or a marker (#27's AC4).
  - [ ] **AC3:** WHEN a turn-end gate's block reaches a reviewer THE reviewer contract SHALL tell it to end its turn. It writes no file, the receipt included; fixes nothing; starts no agent; and does not poll for the receipt. It may say in one line that the block is for the author. `.claude/agents/_shared/reviewer-contract.md` stays byte-identical to the shipped contract.
  - [ ] **AC4:** WHEN the reviewer's report reaches the parent on Antigravity THE `implement` skill SHALL have the parent write the receipt from its Receipt block, CLEAN or BLOCKED, and then end the reviewer with `manage_subagents`' `kill`. The report arrives as the reviewer's message or as the notice that it has gone idle (Q2). After fixing a BLOCKED review, the parent registers and invokes a fresh reviewer, never re-tasking the old one.
  - [ ] **AC5:** WHEN `implement` runs the reviewer on Antigravity THE skill SHALL name `define_subagent` first, with write tools and subagent tools off. The `self` route is only for when `define_subagent` is unavailable, and its prompt forbids writing any file, the receipt included, and starting any agent (C2).
  - [ ] **AC6:** WHEN this ships, these say what the code does and what was measured:
    - `docs/fidelity.md`'s reviewer paragraph: `Stop` runs in a subagent's turn, the lifecycle, the route order;
    - `docs/verified.md`: a section for Q1 to Q3, and its open subagent item, narrowed to what is still unmeasured.
  - [ ] **AC7:** the regression tests fail before the fix and pass after: AC1 over every gate's block on both channels, and AC3 to AC5 pinned in their files.
- **Out of scope:**
  - A gate-side skip for a subagent's turn. Q1 found no field that marks one. The empty `lastUserInput` is incidental, and a skip read from it would pass any parent turn that ever has one: that is a fail-open. Row 2 keeps the question.
  - #312, Claude Code spawning a reviewer from its start-of-session definition. It edits the same step and contract, and builds on this.
  - #25, the gate refusing an inline review.
  - How the parent waits on Antigravity. Q2 and Q3's parents ended their own turn after `invoke_subagent` and were woken by the reviewer's message. With the real gate that is #27's block, which step 2 already covers.

### Clarifications

2026-10-27, `clarify`, answered by the maintainer:

- **C1: where a block says who it is for.** Every block, in `gate_block`, the maintainer's choice from three:
  - every block;
  - the review gate's current-branch arms;
  - the no-receipt arm only.

  A reviewer can meet five kinds of block:
  - the no-receipt arm, on any first review;
  - the BLOCKED arm, on a re-review after a BLOCKED round;
  - the stale arm, on a re-review after fixes;
  - the quality gate's failure, on any red validator at its turn end;
  - the other-branch scan.

  The narrower options leave a re-review or a red validator able to loop it.
- **C2: the `self` route.** Kept as the fallback, with a write ban. `define_subagent` with write tools off comes first, and `self` is used only where that is unavailable. Dropping `self` would send such installs to an inline review, which #25 plans to refuse. Claude Code's reviewer has `Bash` and is held back by its prompt too.
- **C3: probe now, or leave it to row 2.** Probe now. Q1 to Q3 were run on Antigravity CLI 1.4.7 the same day, in scratch trusted projects. Each used one headless `agy` turn with a `Stop` hook that logged every firing's stdin and environment. The projects are deleted.
  - **Q1, observe only.** The parent defined a subagent with `define_subagent` and invoked it. The hook fired twice: in the subagent's conversation, then in the parent's.
    - The two payloads have the same keys.
    - In the subagent's payload, `conversationId` and `ANTIGRAVITY_CONVERSATION_ID` are the subagent's, and `lastUserInput` is empty.
    - `define_subagent`'s definition carries `enable_write_tools`, `enable_subagent_tools` and `enable_mcp_tools`.
    - `invoke_subagent` returned in 0.16 s, and the reply reached the parent as a system message.
  - **Q2, a stand-in gate blocking every subagent turn** with today's no-receipt message.
    - The subagent's `Stop` fired 11 times in 51 s, at `executionNum` 0 to 10: A4's cap of 10.
    - The subagent sent its report with `send_message` before the first block, and repeated it at each re-entry.
    - The parent got the report as a message, then, after the cap, a notice that the subagent "has gone idle", carrying its last response.
  - **Q3, the same gate, with the AC1 paragraph appended.** The parent was told to write the receipt, then kill.
    - Given the paragraph, the subagent answered "As a reviewer receiving this notification, I am ending my turn without writing files or performing further actions." That is one sample.
    - The parent wrote the receipt and called `manage_subagents` with `Action: kill`. It returned in 0.12 s: "Successfully killed 1 subagent(s) and their descendants".
    - The subagent's `Stop` fired twice, the second time within the second before the kill. It fired no more after it.

## 2. Design (HOW)

- **Fix approach, and why this rather than the narrower or wider fix:**
  - **The gate (AC1, AC2).** `gate-lib.sh` gains one constant paragraph, and `gate_block` appends it to the message before escaping, so the JSON reason and stderr both carry it. The fixed fallback reason carries it too.
    - Three bootstrap blocks cannot call the library: `_gate_bootstrap_block` in `quality-gate.sh` and `review-gate.sh`, and `_plugin_gate_block` in `plugin-gate.sh`. Each appends the same literal paragraph, and a test holds the four copies equal.
    - `gate_replay` prints a child's verdict as it is, and that verdict already ends in the paragraph, so it appears once.
    - No arm's own text changes, the no-receipt arm's "wait for it" included.
    - Narrower fixes were C1's other options. A wider fix, a gate-side skip, is out of scope.
  - **The contract (AC3).** A short section after "What a reviewer is", "When a gate blocks your turn": what the block is, whom it is for, and the four things the reviewer does not do. It names no repository path: the contract is copied into projects that have no `docs/`. The `.claude/agents/_shared/` mirror is a `cp`.
  - **`implement` step 2 (AC4, AC5).**
    - The Antigravity bullet lists `define_subagent` first, with `enable_write_tools` and `enable_subagent_tools` false (Q1's field names). `self` becomes the fallback, with its ban.
    - A paragraph follows on the reviewer's lifecycle there: why the gates block it, how the report arrives, receipt first, then the kill, and a fresh reviewer after fixes.
    - Writing the receipt first means a CLEAN receipt clears the reviewer's next `Stop` even if the kill fails.
    - The #147 needle's sentence is kept word for word.
  - **The docs (AC6).** A #329 section in `docs/verified.md` with Q1 to Q3. Its open subagent item is narrowed to what Q1 to Q3 did not measure:
    - the `self` route's tools;
    - whether a parent waiting with `wait` is woken by the message;
    - any marker.

    `docs/fidelity.md`'s reviewer paragraph says what was measured and the lifecycle.
- **Affected files:**
  - `hooks/gate-lib.sh`, `hooks/quality-gate.sh`, `hooks/review-gate.sh`, `hooks/plugin-gate.sh`;
  - `reviewers/_shared/reviewer-contract.md`, `.claude/agents/_shared/reviewer-contract.md`;
  - `skills/implement/SKILL.md`;
  - `scripts/check-skill-contracts.py` (needles for AC3 to AC5);
  - `scripts/test-gates.sh`;
  - `docs/verified.md`, `docs/fidelity.md`.
- **Blast radius:**
  - Every block on both harnesses grows by one paragraph. `test-gates.sh` matches blocks by substring (`*…*`), so existing cases keep passing. A case that compares a whole reason would need the paragraph, and T1 finds any.
  - Claude Code shows the paragraph to the session that is blocked. Its reviewers do not run `Stop`.
  - An Antigravity install gets the gate's paragraph and the contract only by re-running `init` (A12, #343). `implement`'s text arrives with the plugin update.
- **Why this cannot recur:**
  - One test runs every block kind through both channels and requires the paragraph exactly once. The four literal copies are compared.
  - `check-skill-contracts.py` gains three entries, its thirty-ninth to forty-first. Each comes with the argument its docstring asks for, why review cannot defend the sentence:
    - **The contract's rule.** Deleting it reads as trimming a harness-specific aside from a harness-neutral contract. What that restores is a reviewer that takes the author's instructions as its own on Antigravity: it loops, and on the `self` route it can edit the diff it is reviewing.
    - **Receipt, then kill.** Dropping the kill reads as dropping cleanup, and swapping the two reads as neutral. Without the kill, the reviewer is re-entered until the cap, and the parent hears it has gone idle only then (Q2). With the kill first, a failed receipt write leaves nothing to clear the next review.
    - **The `self` ban.** Without it, "use `self`" reads as an equivalent route. It is the one route with write tools on, so what that restores is a reviewer that can carry out the blocks it meets.

    The fresh reviewer after a BLOCKED review needs no entry: a killed reviewer cannot be re-tasked.

## 3. Tasks (TDD-ordered)
> One task is one complete Red-Green-Refactor cycle, so one green commit. No task is sequenced after the review.
- [x] T1: AC1 and AC2. Red: test-gates cases asserting the paragraph exactly once, on both channels, for a no-receipt block, a BLOCKED block, the other-branch scan, a quality failure, a budget block, the fallback reason, the three bootstrap blocks and a replayed child's block, plus the four copies equal. Then the paragraph in `gate_block` and the bootstrap blocks.
- [x] T2: AC3. Red: the `check-skill-contracts.py` needle for the contract's rule. Then the section in the contract and its mirror.
- [ ] T3: AC4 and AC5. Red: needles for the receipt-then-kill order and the `self` ban. Then step 2's Antigravity bullet and the lifecycle paragraph.
- [ ] T4: AC6. `docs/verified.md`'s #329 section and open item, and `docs/fidelity.md`'s reviewer paragraph.
