# Roadmap

- Reconciled against PRD: 5e33fa0176dc3e423776699043e2b01d6116ca26

Major versions are content commitments, milestone demos, and capability completions — not dates or calendar quarters. Issue and backlog row membership are derived in BACKLOG.md from position relative to version lines in ## Lines, never listed here.

## 1.0-baseline-harness
- Completes: CAP-1, CAP-2, CAP-3, CAP-4, CAP-5, CAP-7, CAP-9
- Demo: "Watch a turn end without a fresh, independent clean review blocked on both channels — exit 2 on Claude Code, `{"decision": "continue"}` on Antigravity — watch a change to source with no spec blocked, and its pull request fail the chain check when it is created and again in CI, watch init adopt an existing project without touching its conventions, and read how many of the gate's blocks were false."
- Depends on: nothing
- Not included: answering where you stopped, which is 2.0; context re-injection after mid-session compaction on Antigravity, which has no hook for it (`docs/fidelity.md`).

## 2.0-re-entry
- Completes: CAP-6, CAP-8, CAP-10
- Demo: "After a week away, ask a project what's next and get the right answer in seconds, from a plan whose every issue traces to a capability and is sized to decide in one slot."
- Depends on: 1.0-baseline-harness — an answer about what is next is only right if every change traces to the plan, which 1.0's CAP-9 enforces.
- Not included: a session that shows the state before anyone asks. CAP-8 asks for a right answer on request; showing it up front is a design choice inside its spec, weighed against its cost on every session.
