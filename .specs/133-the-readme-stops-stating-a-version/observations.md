# Observations — 133-the-readme-stops-stating-a-version

## Review round 1 — CLEAN, 0 blockers, 0 HIGH, 1 MEDIUM, 2 LOW

Reviewed at `5c4599c5556bda3b686f71bd8c7f78c42e21c3fa` by `gate-sdd-reviewer`, `reviewed_by=subagent`.

The question worth asking of this change was whether the guard could now pass a README that had stopped making the version claim — the failure `- Owns: gates never fail open` names, reached by replacing a check rather than removing one. The reviewer established it structurally rather than by example: no shields URL containing `/badge/dynamic/` means control always reaches one of the two `problems.append` branches, there is no third way out of `if not dynamic:`, and every earlier exit on that path is also a failure exit. The success line is unreachable while `problems` is non-empty.

## Findings addressed in round 1

- **MEDIUM — the widened subject.** The first cut selected every badge containing `/badge/dynamic/` and then required each to read `plugin.json`'s `$.version`. AC4's subject is *the version badge*; the implementation's subject was *any dynamic badge*. C2 declined a wider badge row only for now, so the next badge is a live possibility — and a dynamic one measuring anything else would have gone red for an edit that broke nothing. G-6 asks for an argument **and** a case in the direction a widening can fire wrongly, and case 65b's unrelated badge is static, so it never covered this. The selector is now the badge's `label`, which fails closed: rename it and no version badge is found, which is the absence branch. Both directions have a case.
- **LOW — the prohibition's costume gap.** `VERSION` required a space or a Japanese comma after the number, so `**v1.2.3**` passed. The trailing class is dropped. Broadening further to a bare `v1.2.3` is deliberately not done: it would fire on `Antigravity CLI 1.1.17` in the tested-against line, which is a different claim about a different thing.
- **LOW — an unrecorded limit.** The Design recorded the limit it had thought of, that a badge rendering as an error still passes. Badge detection is also textual, so one inside an HTML comment counts as present while the page shows no version. Recorded beside the other stated limits rather than closed: stripping comments buys a false-block risk for a hazard that takes a deliberate edit and is visible to anyone who opens the page.

## Review round 2 — BLOCKED, 0 blockers, 1 HIGH, 2 LOW

Reviewed at `9e8c78e83ed460ecfcaffb74a74c2d7dee292fb7`. The first non-clean verdict in this spec, and it was earned.

- **HIGH — the widened prohibition shipped unpinned.** Round 1's LOW fix dropped `[ ,、]` from `VERSION`, which is a behaviour change: the guard now fires on inputs it used to pass. Every `**v` fixture in the suite carries a trailing delimiter, so restoring the narrow pattern left all 91 cases green. A check that can be reverted with the suite staying green has stopped covering its claim in silence — G-4 exactly, and the anchor this repository owns. It arrived in a commit that *did* add a case for the other fix, which is what makes it an omission rather than a recorded trade.
  Fixed with a case that asserts `**v1.2.3**` with no trailing delimiter reddens, and **mutation-verified**: reverting the pattern to `[ ,、]` turns exactly `bold-no-delimiter-red` and `says-states-bold` red and nothing else. The reviewer's companion suggestion is taken too — `readme_repo`'s README now carries a `Tested against: Antigravity CLI 1.1.17` line, and `rm-control` staying green pins the deliberate decision *not* to broaden the pattern to a bare version number. Nothing had pinned that decision before; it lived only in a comment.
- **LOW — a relabelled badge was reported as an absent one.** The routing is fail-closed and correct, but the message told an author looking at a correctly-rendering badge that the file "states no version at all". That is the wrong-remedy harm the static-badge branch was split out to avoid, reappearing one branch over. `label=` had become load-bearing and no message said so; the absence message now names it.
- **LOW — the new limit was filed under the wrong name.** Round 1's textual-detection note landed after `BADGE =` with no blank line before `DYNAMIC`'s comment, so it read as documentation of `DYNAMIC`. Separated.

## Review round 3 — BLOCKED, 0 blockers, 1 HIGH, 1 LOW

Reviewed at `ceacdcbe5a8345a9a7b85a0ba8f3844b0a744f3b`. The round-2 HIGH was confirmed closed, and a new one was found in the commit that closed it.

- **HIGH — an assertion that could no longer go red.** Round 2's fix reworded the absence message and updated the two assertions that matched the old wording *positively*. Case 65b's `not-called-absent` matched it **negatively** — `case "$err" in *"carries no version badge"*) s3=no` — so once the string no longer existed anywhere the guard can emit, `s3` was permanently `ok` while the failure line still printed it as though it had been checked. That is the same class as the round-2 HIGH, one assertion over, inside the commit that fixed it: the reword was treated as a text change when it was a change to what the suite is capable of noticing.
  Repaired to match the substring the other two use, and **mutation-verified**: making the static branch also emit the absence message turns `not-called-absent` red and leaves the other three halves green.
- **LOW — a comment quoting the deleted message.** The rationale for splitting the branch quoted `"Carries no version badge"`, so anyone grepping for it to find what the branch prints landed on comments only. Requoted.
- **INFO taken rather than recorded** — `rm-bare-version` was byte-identical to `rm-control`, so it was one assertion under two names, which is duplication that later reads as independent evidence. It now adds a bare number **equal to the manifest version**, which is the hardest input for a broadened pattern because the digits are exactly the ones the badge renders. Mutation-verified too: broadening `VERSION` to a bare `\d+\.\d+\.\d+` turns `bare-number-green` red and nothing else.

Three rounds, and the pattern across them is worth naming: every finding after round 1 was **introduced by the previous round's fix**, and each was a check that had quietly stopped being able to fail. None was reachable by running the suite, because a suite that cannot fail is green. The mutation runs are now part of the record for exactly that reason — a green assertion proves nothing on its own.

## Recorded rather than fixed

- **`Status: done` was flipped before the review, not after.** `skills/implement/SKILL.md` lists that flip among the commits landing after the receipt. No mechanical effect — `hooks/review-gate.sh` arms on unticked tasks and never reads `Status` — but the spec did read `done` while its receipt was still being written. Same slip as #141, which makes it a habit rather than an accident and worth naming here.
- **The reviewer could not run the guard under review.** `./scripts/check-readme-claims.py` is on `- Validators:` and absent from the reviewer's Bash allow-list, which is #131 — whose spec has been sitting untracked in this worktree throughout. It substituted the suite's fixture cases plus a byte comparison of both READMEs' badge URLs against `BADGE_SOURCE` and `BADGE_QUERY`. CI runs the guard on the real files unconditionally, which is what caught the drift on #141 in the first place.

## What this change actually bought

Detection existed before this spec: #115 built it, and it worked — CI caught the drift on #141 at the PR. What it could not do is stop the mistake, because the one turn that changes the version is the one turn `quality-gate.sh` is guaranteed to skip, the manifests being outside `- Source globs:` by decision on #14. Removing the second source makes the claim unable to be wrong instead of reliably caught, and moves the remaining guard onto the thing that can still break: that the badge is the dynamic form and not a static one.
