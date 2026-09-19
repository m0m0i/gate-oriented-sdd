# Spec: init asks for the target document set
- Slug: 141-init-asks-for-the-target-document-set   Issue: 141   Type: feature   Status: approved
- Author: Hiroyuki   Date: 2026-09-19

## 1. Requirements (WHAT / WHY)
- User story: As an operator running `init` on a fresh project, I want to say which document set the project is signing up for, so that the first block from `check-document-set.py` names the documents I chose to owe rather than ambushing me with a generic demand.
- Serves: LV-4 (install fidelity — a project where the gates work on turn one), LV-2 (gate narrowness — a first block the user was not expecting is how a gate gets switched off), CAP-4, CAP-7.
- Acceptance criteria:
  - [ ] **AC1:** WHEN `init` reaches step 3 in a project that carries no `- Mode:` line THE SYSTEM SHALL ask the operator which document set the project signs up for, naming what `minimum` and `full` each require.
  - [ ] **AC2:** WHEN the operator has answered THE SYSTEM SHALL write `- Target: <minimum|full>` on one physical line in `.steering/tech.md`, while `- Mode:` still records `bootstrap` on a fresh install.
  - [ ] **AC3:** WHEN `check-document-set.py` fails while `- Mode:` is `bootstrap` and a readable `- Target:` line is present THE SYSTEM SHALL name, by path, the documents that target requires.
  - [ ] **AC4:** WHEN `- Target:` is absent, empty or unreadable while `- Mode:` is `bootstrap` THE SYSTEM SHALL emit today's generic failure rather than assuming a target, because a defaulted target is a claim nobody made.
  - [ ] **AC5:** WHEN `- Mode:` is `minimum` or `full` THE SYSTEM SHALL neither require, forbid nor read `- Target:`, so an upgraded project that never had the line is not made red by it.
  - [ ] **AC6:** WHEN `init` runs in a project that already carries a `- Mode:` line THE SYSTEM SHALL read it as an upgrade, and neither re-ask nor move the value down.
  - [ ] **AC7:** WHEN `init` loses the target question, its destination or its wiring THE SYSTEM SHALL fail a guard rather than install silently without it.
  - [ ] **AC8:** WHEN `check-document-set.py` succeeds while `- Mode:` is `bootstrap` and a readable `- Target:` line is present THE SYSTEM SHALL name the documents that target owes, so the set is known before the first spec rather than at it.
  - [ ] **AC9:** WHEN `- Target:` carries a value that is neither `minimum` nor `full` THE SYSTEM SHALL fail naming the value, rather than falling back to the generic message and leaving a typo undetected forever.
  - [ ] **AC10:** WHEN a `- Target:` line is written in a form its reader cannot parse THE SYSTEM SHALL fail the anchor guard, as the other six machine-read lines already do.
- Out of scope: the post-init onboarding cascade (#142); the North Star template rework (#139); any change to which documents `minimum` and `full` require; any change to the three values `- Mode:` accepts; making `- Target:` binding on what the checker requires (rejected in C1).

### Clarifications
2026-09-19, from `clarify`:

- **C1 — How binding is the target during the bootstrap window?** The target names the documents in the failure message; it does not change what the checker requires. `full` already blocks on missing documents today (`assets/check-document-set.py:205-210` adds `FULL_ONLY_DOCS` and fails on any missing path), and that is not weakened. To clear a bootstrap block the operator still writes documents and declares `- Mode:`; declaring `full` then enforces all six as it does now. A binding target was considered and rejected: it reaches the same end state while adding one more line that can be wrong, and it makes changing your mind an edit rather than a declaration.
- **C2 — Is there already a field for this?** Yes, `- Mode:`, with values `bootstrap|minimum|full`, parsed strictly and never defaulted. It cannot express what a project is heading for while it is still `bootstrap`, because `- Mode: full` on day one is a claim about documents that do not exist — the claim the checker exists to refuse. A fourth machine-read line `- Target:` carries the choice instead: `- Mode:` stays "what is true now", `- Target:` is "what was chosen". It is read only while `- Mode:` is `bootstrap` and is inert afterwards, which is honest — that window is the only reason it exists.
- **C3 — Where does the question go, given step 2's five-question ceiling?** Step 3, not step 2. Step 3 already instructs `init` to name the opt-in three and let the user choose; the choice is present and merely unrecorded. Making it explicit there spends no interview slot and breaks no stated invariant.
- **C4 — Version.** 0.9.1. Recorded as the operator's call. Noted rather than argued: this spec adds a machine-read line and a checker branch, which the project's own sizing rule would read as a flow change rather than prose, so the bump may be worth revisiting at the post-receipt step if the diff lands larger than expected.
- Not asked, because the repo answers it: the upgrade path. `skills/init/SKILL.md` Rules already states that a project carrying a `- Mode:` line is an upgrade and the value moves up, never down. AC6 restates that boundary rather than reopening it.

## 2. Design (HOW)
- Approach and key decisions:
  - **`- Target:` is read only while `- Mode:` is `bootstrap`.** Everywhere else it is neither required nor consulted (AC5), which is what keeps an older install that never had the line from turning red on upgrade. The line is inert after the window it exists for, and that is the honest shape rather than a defect to design away.
  - **It changes messages, never the required set.** `wanted` is still built from `- Mode:` alone. C1 settled this, and it is what keeps the target off the pass/fail path: a mistyped target can misdescribe what you owe, but it can never let a document go unchecked.
  - **The value is stripped, unlike `- Mode:`.** `steering_value` deliberately does not strip, for byte parity with `gate_steering_value`, because a shell consumer reads `Mode`. Nothing in `hooks/` reads `Target`, so there is no reader to be stricter than — the same argument the file already records for `Docs`. Without the strip, `- Target: full ` would be an unrecognised value and AC9 would fire on a line that reads correctly to a human.
  - **An unrecognised value fails; an absent one does not** (AC9 vs AC4). Absent is a supported state — every project installed before this line existed — so it falls back to today's generic message. Present-but-wrong is a declaration that cannot be honoured, and silently ignoring it would leave the typo undiscovered for the whole bootstrap window, which is the only window it is read in.
  - **`- Target:` disagreeing with a settled `- Mode:` is not an error.** Once `- Mode:` is `minimum` or `full` it is the truth and the target is spent; an operator who chose `full` and declared `minimum` changed their mind, which is a decision rather than a fault. No check compares them, and this is recorded so the absence reads as deliberate.
  - **This repository does not add the line to its own `.steering/tech.md`.** Its `- Mode:` is `full`, so the line would be inert on the day it was written, and a machine-read value nothing reads is the decoration C1 rejected.
- Affected modules and files, per `.steering/structure.md`:
  - `assets/check-document-set.py` — shipped. Reads `- Target:`, and names the target's documents in the first-spec failure (AC3) and the bootstrap advisory line (AC8).
  - `assets/check-steering-anchors.sh` — shipped. One row added to `ANCHORS`, so `- **Target: full**` fails loudly (AC10). Absent stays legitimate; the guard already skips a key with no loose match.
  - `skills/init/SKILL.md` — shipped. Step 3 asks the question and documents `- Target:` in the machine-read block (AC1, AC2).
  - `scripts/check-skill-contracts.py` — CI guard, not shipped. One `CONTRACTS` entry pinning the question and its destination (AC7).
  - `scripts/test-gates.sh` — the project's whole notion of test coverage. New cases for each task below.
  - `plugin.json` and `.claude-plugin/plugin.json` — bumped to 0.9.1 as a **step of `implement`** after the review receipt, never as a task. See `.steering/tech.md` and #113.
- Contract changes, and who else consumes them: `- Target:` is a fourth machine-read line in `.steering/tech.md`. Its only consumer is `check-document-set.py`. `hooks/gate-lib.sh` is untouched, no hook branches on it, and `- Source globs:` is unaffected. AC6 needs no new work: `scripts/check-skill-contracts.py` already pins the upgrade rule verbatim, so a re-run that re-asks or moves the value down fails today.
- Risks and trade-offs:
  - A fourth line is more install surface, and LV-4 says a misconfigured install scores zero on every lever above it. AC10 is the mitigation — the anchor guard makes an unparseable form loud, which is the failure mode #34 actually produced.
  - The window is narrow enough that the line is wrong-but-unnoticed for most of a project's life. Accepted: it is read only when it matters, and AC9 makes a wrong value loud during exactly that window.
  - Naming six documents in a bootstrap message is a longer block than naming three. That is the point of the issue, but it does make the first block bigger; LV-2 says a gate that feels heavy gets switched off, so the message must read as a checklist rather than an accusation.

## 3. Tasks (TDD-ordered)
> One task is one complete Red-Green-Refactor cycle, so one green commit. No task is sequenced after the review.
- [ ] T1: failing case in `scripts/test-gates.sh` — `bootstrap` with `- Target: full` and one spec present fails naming all six documents, while the same tree with no `- Target:` line keeps today's generic wording — then the `- Target:` read and the failure-message change in `assets/check-document-set.py` (AC3, AC4)
- [ ] T2: failing case — an unrecognised `- Target:` value fails naming the value, a trailing-space value does not, and a `- Target:` line is neither read nor required once `- Mode:` is `minimum` or `full` — then the validation and the mode guard (AC5, AC9)
- [ ] T3: failing case — the bootstrap advisory line names the target's documents and their owning skills, and still counts issue templates and directories in their own units — then the print change (AC8)
- [ ] T4: failing case — `check-steering-anchors.sh` fails on `- **Target: full**` and stays silent when the line is simply absent — then the `ANCHORS` row (AC10)
- [ ] T5: failing case — `check-skill-contracts.py` fails when the target question or its destination is removed from `skills/init/SKILL.md`, and the tree init step 3 documents still passes `check-document-set.py` — then the step 3 prose, the `- Target:` entry in the machine-read block, and the `CONTRACTS` entry (AC1, AC2, AC7)
