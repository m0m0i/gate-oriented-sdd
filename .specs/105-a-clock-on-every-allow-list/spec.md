# Spec: A clock on every reviewer's allow-list
- Slug: 105-a-clock-on-every-allow-list   Issue: 105   Type: bug   Status: done
- Author: m0m0i   Date: 2026-09-09

## 1. Requirements (WHAT / WHY)
- Reproduction: spawn any reviewer in this harness and read its Bash policy against the Receipt block in `agents/_shared/reviewer-contract.md`. The contract requires `reviewed_at=<YYYY-MM-DDTHH:MM:SSZ>` on every receipt; none of the five allow-lists — `agents/ts-reviewer.md`, `agents/python-reviewer.md`, `agents/dart-flutter-reviewer.md`, `agents/_template/reviewer.md`, `.claude/agents/gate-sdd-reviewer.md` — names a command that reports the current time.
- Expected: a reviewer obeying its allow-list can produce every field the contract requires of it.
- Actual: it cannot produce `reviewed_at`. The contract also tells a reviewer to raise a finding rather than run an off-list command, so the two instructions conflict and each reviewer resolves the conflict on its own — running `date` off-list and disclosing it, taking the time from context, or writing a placeholder. #105 records all three shapes appearing in one week.
- Impact: every review, on every project that installs this harness. The cost is not a broken gate — `hooks/review-gate.sh` reads only `verdict` and `reviewed_sha`, so nothing fails open here — it is that the receipt's record of *when* a review happened is produced by a different method each time, and a field the contract requires while the allow-list forbids teaches a reviewer that the allow-list is negotiable. That lesson is the hazard, because the allow-list is what keeps a read-only reviewer read-only.
- **Root cause:** the Receipt block and the Bash policy are in the same document but were written against different questions. `reviewed_at` was specified as a receipt *field* — what the record must contain — with no pass over the Bash policy asking what a reviewer is actually permitted to run to fill it. The other six fields hid the omission: `reviewed_sha` comes from `git rev-parse HEAD`, which is on every list, and the rest are known to the reviewer from its own run. `reviewed_at` is the only field whose value comes from outside both the diff and the reviewer, and nothing checked that class of field against the allow-list.
- Acceptance criteria:
  - [x] **AC1:** WHEN a reviewer fills in the Receipt block obeying only its own Bash policy THE SYSTEM SHALL permit it to obtain the current UTC time, in all five reviewer files.
  - [x] **AC2:** the regression test fails before the fix and passes after.
  - [x] **AC3:** WHEN a reviewer file's Bash policy omits the clock while the contract still requires `reviewed_at` THE SYSTEM SHALL fail a validator naming the file.
  - [ ] **AC4:** WHEN this change is committed THE SYSTEM SHALL carry a version bump in both manifests, `agents/` being a shipped path.
- Out of scope: the wording of `reviewed_at` in the contract (it stays `<YYYY-MM-DDTHH:MM:SSZ>`); the receipts already written, which are records and stay as they are; #35, which is about `reviewed_sha` naming the working tree rather than the reviewed commit, and is a separate defect in the same block.

### Clarifications
- 2026-09-09 — **Is the AC3 validator in scope, and where does it live?** Extend `scripts/check-receipt-schema.py` rather than adding a tenth validator. It already owns the relationship between the contract and the receipt, already reads all three schema copies, and already byte-compares the mirror; the pairing this bug is about is the same relationship seen from the other side. #54 records that the guard count argues against growing, which a new script would.
- 2026-09-09 — **Which of the issue's two fixes?** The clock, not the HEAD commit time. #105 offers both and says `git log` is "already on every allow-list", but the listed form is `git log --oneline <base>...HEAD`, which prints no date — so the commit-time fix needs a new command on all five lists too, at identical cost, while making `reviewed_at` derivable from `reviewed_sha` and no longer a record of when the review ran.
- 2026-09-09 — Answered from the repo, not asked: the contract mirror is byte-compared by `check-receipt-schema.py`, so editing the contract is safe; and a patch bump is the convention for prose under `agents/` — #47 was the same shape and landed 0.4.3, so this is 0.4.4.

## 2. Design (HOW)
- Fix approach, and why this rather than the narrower or wider fix: add `date -u +%Y-%m-%dT%H:%M:%SZ` to the Bash policy of all five reviewer files, sanction the clock as a **category** in the contract's own Bash policy list, and pair the two in `check-receipt-schema.py`. The narrower fix — five allow-list edits alone — closes this instance and leaves the class open: nothing would stop the next required field from arriving with no permitted producer, which is exactly how this one arrived. The wider fix — redefining `reviewed_at` as the HEAD commit's time — is rejected in the Clarifications. Sanctioning the category in the contract matters because the contract is what a person writing a sixth reviewer by hand reads; five files agreeing on a command the shared document never mentions is how the template drifts.
- Affected files:
  - `agents/ts-reviewer.md`, `agents/python-reviewer.md`, `agents/dart-flutter-reviewer.md`, `agents/_template/reviewer.md`, `.claude/agents/gate-sdd-reviewer.md` — one Bash-policy bullet each
  - `agents/_shared/reviewer-contract.md` and its byte-identical mirror `.claude/agents/_shared/reviewer-contract.md` — the category
  - `scripts/check-receipt-schema.py` — the pairing check
  - `scripts/test-gates.sh` — the cases that prove it
  - `.steering/structure.md`, `README.md`, `README.ja.md` — the suite's path count, which the new cases change
  - `plugin.json`, `.claude-plugin/plugin.json` — 0.4.3 → 0.4.4, after the review
- **Blast radius:**
  - `check-receipt-schema.py` is on the `Validators` line, so it runs at every turn end through the quality gate and again in CI. A false positive blocks every turn in every project, so the clock detection is matched against the reviewer's Bash-policy section only, not the whole file.
  - The guard runs under `python3 -O` and via a `PYTHONOPTIMIZE=1` shebang in the existing cases at `scripts/test-gates.sh:756-759`, because #28 was an assert stripped by `-O`. The new check must therefore not be written with `assert`.
  - The three shipped reviewers are consumed by installs, so this widens what a reviewer is permitted to run — a shipped behaviour change, hence AC4. It does not weaken the read-only guarantee the allow-list exists to hold: `date` reads a clock and writes nothing.
  - Receipts already written are records and are not revisited; see Out of scope.
  - **Found during T1, not anticipated when this spec was written:** the suite's path count is a claim in five live places — `.steering/structure.md:19`, `README.md:41`, `README.md:156`, `README.ja.md:43`, `README.ja.md:157` — and the three new cases move it from 54 to 57 — 56 after T1, and 57 once T3 adds its own. Those are corrected in T4. The dated row at `docs/verified.md:151` says 54/0 and stays as it is: it records what a run observed on its date, and records stay records (the #102 precedent).
- Why this cannot recur: the guard holds a table mapping each required receipt field to the evidence a reviewer's allow-list must show for it. `reviewed_at` maps to a clock; the remaining fields are listed explicitly as known to the reviewer from its own run, so the work-set is complete and non-empty rather than defaulting to silence — the failure mode #16 and #39 are both about. A future field added to the contract with no entry in that table fails the guard rather than reaching a reviewer that cannot produce it.

## 3. Tasks (TDD-ordered)
> One task is one complete Red-Green-Refactor cycle, so one green commit.
- [x] T1: cases in `scripts/test-gates.sh` — a reviewer whose Bash policy names no clock fails `check-receipt-schema.py` with the file named, and one that names it passes — failing for the right reason against today's tree; then the pairing check in `check-receipt-schema.py` and the clock on all five allow-lists, ending green. (AC1, AC2, AC3)
- [x] T2: the clock as a sanctioned category in `agents/_shared/reviewer-contract.md`, copied to its mirror; the byte-compare at `check-receipt-schema.py:98` is the check. (AC3)
- [x] T3: blast radius — a case proving the new failure still fires under `python3 -O`, so the check cannot be stripped the way #28 was. (AC2)
- [x] T4: the path-count claim from 54 to 56 in the five live places named in the Blast radius; then refactor and the full validator line, `./scripts/check-leakage.sh` included.
- [ ] T5: **after the reviewer gate is CLEAN** — bump both manifests to 0.4.4. `.steering/tech.md` puts the bump after the review deliberately, with the work-log entry and the `Status: done` flip, because `plugin.json` is outside `Source globs` and a bump before the receipt would re-stale it. (AC4)
