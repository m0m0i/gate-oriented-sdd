# Observations — 133-the-readme-stops-stating-a-version

## Review round 1 — CLEAN, 0 blockers, 0 HIGH, 1 MEDIUM, 2 LOW

Reviewed at `5c4599c5556bda3b686f71bd8c7f78c42e21c3fa` by `gate-sdd-reviewer`, `reviewed_by=subagent`.

The question worth asking of this change was whether the guard could now pass a README that had stopped making the version claim — the failure `- Owns: gates never fail open` names, reached by replacing a check rather than removing one. The reviewer established it structurally rather than by example: no shields URL containing `/badge/dynamic/` means control always reaches one of the two `problems.append` branches, there is no third way out of `if not dynamic:`, and every earlier exit on that path is also a failure exit. The success line is unreachable while `problems` is non-empty.

## Findings addressed in round 1

- **MEDIUM — the widened subject.** The first cut selected every badge containing `/badge/dynamic/` and then required each to read `plugin.json`'s `$.version`. AC4's subject is *the version badge*; the implementation's subject was *any dynamic badge*. C2 declined a wider badge row only for now, so the next badge is a live possibility — and a dynamic one measuring anything else would have gone red for an edit that broke nothing. G-6 asks for an argument **and** a case in the direction a widening can fire wrongly, and case 65b's unrelated badge is static, so it never covered this. The selector is now the badge's `label`, which fails closed: rename it and no version badge is found, which is the absence branch. Both directions have a case.
- **LOW — the prohibition's costume gap.** `VERSION` required a space or a Japanese comma after the number, so `**v1.2.3**` passed. The trailing class is dropped. Broadening further to a bare `v1.2.3` is deliberately not done: it would fire on `Antigravity CLI 1.1.17` in the tested-against line, which is a different claim about a different thing.
- **LOW — an unrecorded limit.** The Design recorded the limit it had thought of, that a badge rendering as an error still passes. Badge detection is also textual, so one inside an HTML comment counts as present while the page shows no version. Recorded beside the other stated limits rather than closed: stripping comments buys a false-block risk for a hazard that takes a deliberate edit and is visible to anyone who opens the page.

## Recorded rather than fixed

- **`Status: done` was flipped before the review, not after.** `skills/implement/SKILL.md` lists that flip among the commits landing after the receipt. No mechanical effect — `hooks/review-gate.sh` arms on unticked tasks and never reads `Status` — but the spec did read `done` while its receipt was still being written. Same slip as #141, which makes it a habit rather than an accident and worth naming here.
- **The reviewer could not run the guard under review.** `./scripts/check-readme-claims.py` is on `- Validators:` and absent from the reviewer's Bash allow-list, which is #131 — whose spec has been sitting untracked in this worktree throughout. It substituted the suite's fixture cases plus a byte comparison of both READMEs' badge URLs against `BADGE_SOURCE` and `BADGE_QUERY`. CI runs the guard on the real files unconditionally, which is what caught the drift on #141 in the first place.

## What this change actually bought

Detection existed before this spec: #115 built it, and it worked — CI caught the drift on #141 at the PR. What it could not do is stop the mistake, because the one turn that changes the version is the one turn `quality-gate.sh` is guaranteed to skip, the manifests being outside `- Source globs:` by decision on #14. Removing the second source makes the claim unable to be wrong instead of reliably caught, and moves the remaining guard onto the thing that can still break: that the badge is the dynamic form and not a static one.
