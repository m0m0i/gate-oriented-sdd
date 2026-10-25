# Roadmap

- Reconciled against PRD: 5e33fa0176dc3e423776699043e2b01d6116ca26

Major versions are content commitments, milestone demos, and capability completions — not dates or calendar quarters. Issue and backlog row membership are derived in BACKLOG.md from position relative to version lines in ## Lines, never listed here.

CAP-8, CAP-9 and CAP-10 are not yet placed in any version; the next roadmap pass places them.

## 1.0-baseline-harness
- Completes: CAP-1, CAP-2, CAP-3, CAP-4, CAP-5, CAP-7
- Demo: "Watch a turn end without an approved spec or an independent clean review receipt fail on exit code 2, and watch init adopt an existing project without touching its conventions."
- Depends on: nothing
- Not included: dual-target execution on Antigravity; mechanical planning chain derivation.

## 2.0-dual-target-parity
- Completes: CAP-6
- Demo: "Install the plugin into both Claude Code and Antigravity from the repository root, and run the complete planning chain from roadmap through backlog to sprint with every version boundary and issue derivation verified mechanically."
- Depends on: 1.0-baseline-harness
- Not included: runtime IDE sidecars or multi-tenant remote agent registries.
