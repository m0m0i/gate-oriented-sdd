# Spec: init times the validators, and writes a budget line when the suite needs one
- Slug: 320-init-times-the-validators   Issue: 320   Type: feature   Status: done
- Author: m0m0i   Date: 2026-10-17

## 1. Requirements (WHAT / WHY)
- User story: As a developer installing the harness into a project whose validators take a long time, I want `init` to measure the suite while it arms the gate, and write a `- Validator budget:` line when the suite needs more than the default, so that my first experience of the quality gate is not a block at every turn end that I have to diagnose myself.
- Serves: CAP-7 (a gate people leave switched on), CAP-4 (installation into a repository that already has opinions).
- Background: since #304 the quality gate blocks at its own deadline: 170 s by default, at most 590 s with a `- Validator budget:` line. `init` step 4.1 already runs every gating validator by hand before it arms the gate. It does not time that run, so the template's "omit it unless they need more than the default 170" asks for a number nobody has. A project whose suite is over the budget learns that only from the block. Claude Code stops honouring a Stop block after eight in a row with no tool call.
- Acceptance criteria:
  - [ ] **AC1:** WHEN `init` step 4.1 runs the `- Validators:` line by hand THE SYSTEM SHALL time that run in whole wall-clock seconds and report the time to the user, whatever it is.
  - [ ] **AC2:** WHEN the timed run takes more than half of the quality gate's default budget (more than 85 s of 170) THE SYSTEM SHALL write `- Validator budget: <value>` in `.steering/tech.md`, the value being twice the measured time, and say why it wrote it. WHEN it takes 85 s or less THE SYSTEM SHALL write no line.
  - [ ] **AC3:** THE SYSTEM SHALL never write a value above the plugin's maximum (590 s). WHEN twice the measured time would exceed it, `init` SHALL write 590 and say plainly that the suite may still be cut off. It SHALL name the remedies the gate's own block names: a faster suite, or the slow validator moved to CI.
  - [ ] **AC3a:** WHEN `.steering/tech.md` already holds a `- Validator budget:` line (an upgrade) THE SYSTEM SHALL keep it unless the value AC2 and AC3 derive is higher. It SHALL then propose the raise with a diff, as `init`'s Rules require for steering, and never lower a value someone chose.
  - [ ] **AC4:** WHEN `init` writes the line THE SYSTEM SHALL write a value the anchor check accepts against the project's hook files, so that step 4's own verification stays green.
  - [ ] **AC5:** `scripts/check-skill-contracts.py` pins the sentences in `skills/init/SKILL.md` that carry AC1–AC3. The template line's "omit it unless they need more than the default 170" reflects that `init` now measures.
  - [ ] **AC6:** Every statement of what `init` does with the budget agrees with the skill: README EN/JA, `docs/`, and the template comment. `docs/BACKLOG.md` row 1's `Why here` drops #320 once it ships.
- Out of scope:
  - timing the review gate, whose budget is fixed;
  - re-timing the suite after `init`, or on any later turn, which is not a step of the flow;
  - any change to the gates, the library or the anchor check (#304 owns them);
  - a script or shipped asset that does the timing: the issue scopes this as skill prose plus a pin.

### Clarifications
Asked 2026-10-17; the maintainer took the recommended answer each time.

- **Q1: what value, when the run is over 85 s?** Twice the measured time, rounded up and capped at 590. The doubling is the value rule #304's spec applies to this repository, and it absorbs a second session running at the same time. The 85 s threshold is new: #304 writes this repository's line only above 120 s, from the slower of two runs, one alone and one beside a concurrent run. Under #320's rule this repository's own init would write a line (100–103 s measured on 2026-10-17); it keeps #304's decision and writes none, and whether it should adopt the shipped rule is an open question for the maintainer, raised in the PR. A fixed margin and 1.5× were rejected (AC2).
- **Q2: an upgrade that already has a line?** Raise only, with a diff; never lower a value someone chose. Report-only and replace-both-ways were rejected (AC3a).
- **Q3: twice the time over 590?** Write 590 and warn, naming the gate's own remedies. Writing nothing was rejected (AC3).

Decided without asking, because the repository answers them:
- **What is timed** is the by-hand run of the `- Validators:` line in step 4.1, not the quality gate's run. On an upgrade the gate can skip on a recorded pass and time nothing, while the by-hand run always runs the whole line.
- **The value is also held below what a project hook file allows (AC4).** The bound is normally the 590 maximum: Claude Code's rendered settings carry no quality-gate entry, so the gate falls back to its 600 s ceiling, and on Antigravity `init` renders 600 itself. A hook file the project keeps with a lower `"timeout"` caps it at that file's `timeout` less 10 s, and `init` names the file, because a line above it fails the anchor check and the gate would lower it anyway. When that bound is below twice the time, `init` gives AC3's warning with the gate's own remedy for a file-set bound: raise that `"timeout"` to 600, or re-run `init`.

## 2. Design (HOW)
- **Approach: prose in `init` step 4.1, pinned.** `init` already runs every gating validator by hand before it arms the gate. That run becomes the measurement:
  - start and end with `date +%s` around the by-hand run of the whole `- Validators:` line, in the session's own shell, so the seconds are the ones a turn end will see. The timing and the line come **before the quality gate's first run** in step 4.1: a suite over 170 s would otherwise be blocked at the default before any line exists, and a first run that passes records a pass the later run then skips on, since `.steering/tech.md` is outside `- Source globs:`;
  - report the time;
  - apply AC2, AC3 and AC3a. The value is `min(2 × t, 590, the hook-file bound)`, where `t` is in whole seconds and the hook-file bound is the shortest `"timeout"` any project hook file gives `quality-gate.sh`, less 10 s;
  - when a line is written or raised, re-run `check-steering-anchors.sh`, because the by-hand run checked a tree without it; the quality gate then runs once, on the tree that holds it, and step 4 arms the gate only when that is green.
- **The template comment** in step 3 keeps its pinned text, `... omit it unless they need more than the default 170`, and gains `; step 4 measures the suite and writes it when they do`, so the pin #304 added stays a substring.
- **One new pin** in `scripts/check-skill-contracts.py`, the thirty-eighth, on the contiguous run of sentences that carries AC1–AC4: what is timed and the report, the 85 s threshold, twice the time and the reason, the 590 cap with its warning and remedies, raise only, and the hook-file bound with its own warning and remedy. The docstring's count moves with it, as its own paragraph demands. The argument it asks for:
  - review cannot defend the sentence, because it is prose a model executes;
  - deleting it leaves every install working, with no line and no complaint, until a slow suite is blocked at every turn end. That is the failure #304 made loud and this issue exists to pre-empt;
  - #304's pin comment ("#320 will time the suite") is updated to name the new pin.
- **Docs (AC6).**
  - `README.md:43` and `README.ja.md:45` say the budget is 170 s unless the line changes it. Each gains that `init` times the suite and writes the line when it needs one. The claims stay identical, and the Japanese is a draft for the maintainer.
  - `docs/BACKLOG.md` row 1's `Why here` drops the #320 sentence, which names it as an open finding of #304's spec, and keeps the scan-cost finding.
  - No other statement describes what `init` does with the budget (`git grep -i 'validator budget'`, checked 2026-10-17).
- **Affected files:** `skills/init/SKILL.md`, `scripts/check-skill-contracts.py`, `README.md`, `README.ja.md`, `docs/BACKLOG.md`.
- **Contract changes:** none. The line, its reader and its range are #304's. `init` becomes one more writer of a line it already templated.
- **Risks and trade-offs:**
  - **A measurement, not a guarantee.** One run on the installing machine can be faster than a CI runner or a loaded laptop. Twice the time is the headroom, and the gate's own block remains the backstop when it is not enough.
  - **A presence check, not a behaviour check.** The pin asserts the instruction is written, not that a model follows it, as the checker's docstring says; `evals/` is unverified.
  - **Fresh installs only see the default rendered timeouts.** A project that later lowers a hook file's `"timeout"` below the written line is caught by the anchor check, which #304 already ships.
- **Version:** `skills/` is shipped, so the bump lands after the review receipt. It is a minor version, because `init` gains a step that writes steering.

## 3. Tasks (TDD-ordered)
> One task is one complete Red-Green-Refactor cycle, so one green commit. No task is sequenced after the review.
- [x] T1: the pin first: `scripts/check-skill-contracts.py` gains the thirty-eighth entry, with the argument above, and the docstring's count. Red: the checker exits 1 naming the missing sentence, and the five contract cases in `scripts/test-gates.sh` go red on their control halves, as they did for #304's pin. Green: `skills/init/SKILL.md` step 4.1 carries the timing, the rule (AC1–AC4, AC3a) and the re-run, and step 3's template comment gains its clause. #304's pin comment names the new pin. Full Validators line green.
- [x] T2: AC6. The README sentence in both languages, and row 1's `Why here` in `docs/BACKLOG.md`. Then `check-readme-claims.py`, `check-backlog-tracker.py` and `check-leakage.sh` green.
