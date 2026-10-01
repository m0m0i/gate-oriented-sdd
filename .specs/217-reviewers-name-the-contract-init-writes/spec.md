# Spec: the shipped reviewers name the contract path init writes, and the guard compares them
- Slug: 217-reviewers-name-the-contract-init-writes   Issue: 217   Type: bug   Status: done
- Author: m0m0i   Date: 2026-10-01

## 1. Requirements (WHAT / WHY)

- Reproduction: run `init` in an Antigravity project. Step 3 (`skills/init/SKILL.md:67`) copies the
  contract to `.agents/agents/_shared/reviewer-contract.md`, and copies a shipped reviewer beside it.
  Line 10 of that reviewer (`agents/{ts,python,dart-flutter}-reviewer.md:10`,
  `agents/_template/reviewer.md:12`) tells it to open `.agents/_shared/reviewer-contract.md` under
  Antigravity — a path no install has. Then run `./scripts/check-contract-path.py` here: it prints
  `check-contract-path: 11 source(s) agree on `_shared/reviewer-contract.md`` and exits 0. Observed
  2026-09-29 on an Antigravity install being upgraded to 0.21.3; every claim re-checked at `ee18a15`
  and again at `4e58da2` (the triage comment on #217 holds the measurements).

- Expected: the four shipped reviewers name the Antigravity path `init` writes, which
  `skills/init/SKILL.md:67`, `docs/layout.md:57`, `docs/fidelity.md:37` and
  `assets/check-locks.py:39` all agree is `.agents/agents/_shared/reviewer-contract.md`; and
  `check-contract-path.py` — built by #82 so that "every statement of where the reviewer contract
  lives must name the same place" — exits 1 whenever a document and a reviewer state different
  concrete paths for the same harness.

- Actual: the reviewers say `.agents/_shared/`, `init` writes `.agents/agents/_shared/`, and the
  guard certifies agreement across the difference. Under Antigravity the reviewer follows
  `agents/_shared/reviewer-contract.md:5` — "if you cannot find it, say so and stop" — so no review
  happens, no receipt is written, and the review gate blocks until the operator edits one line of the
  installed reviewer by hand. Under Claude Code nothing is wrong.

- Impact: every Antigravity or dual-target install since #146 shipped at 0.13.0 — `v0.13.0` to
  `v0.21.3` — reported from one. The consumer-side failure is closed, not open: the reviewer stops
  rather than reviewing without its severity scale. The guard-side failure is the one this repository
  owns: a validator on the `- Validators:` line and in CI exiting 0 on a comparison it never made,
  which is G-1 and #82's own shape re-opened for one harness.

- **Root cause:** `check-contract-path.py` holds its two groups of sources to two different rules,
  and the weaker one accepts any prefix. Reviewers (`EXACT`) must name each entry of `CONCRETE`
  verbatim; documents (`SUFFIX`) need only `endswith("_shared/reviewer-contract.md")`. #146 moved
  `init`'s Antigravity placement from `.agents/` to `.agents/agents/` and updated the documents but
  not `CONCRETE[1]` (`scripts/check-contract-path.py:38`) or `INSTALLED_PREFIXES` (`:101`) — and its
  spec's **Risks** section says so: "Since `.agents/agents/_shared/reviewer-contract.md` ends with
  `_shared/reviewer-contract.md`, it passes without issue." The `endswith` rule was chosen at #82 to
  reject the flat sibling `.claude/agents/reviewer-contract.md` that `docs/layout.md` once drew; it
  was never a rule about which directory, so a document and a reviewer can each satisfy their own rule
  while naming different directories, and the guard has no clause that compares the two groups to each
  other. Two smaller omissions sit beside it: `docs/fidelity.md:37`, added by #146, states the
  placement and is not a source — the "unstated omission" `check-contract-path.py:79-81` warns about
  — and `docs/verified.md:278`'s open item names the `.agents/` path.

- Acceptance criteria:
  - [x] **AC1:** WHEN `./scripts/check-contract-path.py` runs on a tree where `skills/init/SKILL.md`
        names `.agents/agents/_shared/reviewer-contract.md` and a shipped reviewer names
        `.agents/_shared/reviewer-contract.md` — the tree on `main` today — THEN it exits 1 and names
        the file that disagrees. *Evidence: the new guard on `main`'s tree (`4e58da2`) exits 1 naming all four reviewers twice — `says `.agents/_shared/…`, which is not one of the allowed forms` and `does not name .agents/agents/_shared/…`.*
  - [x] **AC2:** WHEN a document source names any concrete path other than
        `.claude/agents/_shared/reviewer-contract.md`, `.agents/agents/_shared/reviewer-contract.md`,
        the bare `_shared/reviewer-contract.md`, or the plugin's own copy
        `agents/_shared/reviewer-contract.md` THEN the guard exits 1 naming that file and that path;
        the flat sibling `.claude/agents/reviewer-contract.md` stays rejected (case 62's `cp-layout`
        and `cp-sibling`). *Evidence: case 170's `document-drifts` and `init-drifts` halves; case 62's `cp-layout` and `cp-sibling` unchanged and green.*
  - [x] **AC3:** WHEN `skills/init/SKILL.md` names fewer than both concrete destinations THEN the
        guard exits 1 saying which is missing — the file that writes the placement is held to the
        same rule as the files that read it, so the closed set in AC2 is anchored to something. *Evidence: case 170's `init-bare` half, naming both missing destinations.*
  - [x] **AC4:** `agents/ts-reviewer.md`, `agents/python-reviewer.md`,
        `agents/dart-flutter-reviewer.md` and `agents/_template/reviewer.md` name
        `.agents/agents/_shared/reviewer-contract.md` for Antigravity, and `check-contract-path.py`
        exits 0 on the tip with `docs/fidelity.md` counted among its sources — 12, not 11. *Evidence: `check-contract-path: 12 source(s) agree` at the tip; the four lines read `.agents/agents/_shared/reviewer-contract.md` under Antigravity.*
  - [x] **AC5:** the regression case in `scripts/test-gates.sh` fails against the guard on `main`
        (`4e58da2`) for AC1's reason and passes against the tip; every existing contract-path case
        (62–64) still passes, with the fixture moved to `.agents/agents/`. *Evidence: against the guard on `main` every case-170 state exits 0 with `11 source(s) agree`; at the tip `test-gates.sh` is 170 passed, 0 failed, 0 skipped, cases 62–64 included. Case 61's moved fixture is red against `main`'s reviewers too.*
  - [x] **AC6:** the twelve other validators exit 0 on the tip; `assets/check-locks.py` reports every
        lock intact, since it hashes `agents/*/rules/*.md` and no rule file moves. *Evidence: twelve validators exit 0; `check-locks: 6 pinned file(s) match their locks`, byte-identical to `main`'s output.*
  - [x] **AC7:** `docs/verified.md`'s open item about which path an Antigravity reviewer picks names
        `.agents/agents/`, and the question itself stays open — this branch makes every statement
        agree with what `init` writes, and does not verify that Antigravity looks there. *Evidence: `docs/verified.md:278` names `.agents/agents/` and keeps its open box.*

- Out of scope:
  - **Whether Antigravity discovers subagents under `.agents/agents/` at all.** `docs/verified.md:274`
    and `:278` list it unverified, and `docs/BACKLOG.md`'s fired-trigger list names what happens if
    the answer is no: the fix becomes a layout change, which is row 10's subject. Every document
    agreeing with what `init` writes is right either way.
  - **`docs/layout.md` naming both concrete paths.** The issue proposes it; the file draws two ASCII
    trees, so its only readable mention is the bare form, and `check-contract-path.py:103-109`
    rejects parsing trees. The closed set covers it.
  - **`docs/verified.md:215`**, a dated record of what #76 observed, which names the plugin's copy and
    stays as written.
  - **Renaming `check-locks.py`'s `CANDIDATE_DIRS` or any other reader of the placement.** They
    already say `.agents/agents`; this branch moves the two that do not.

### Clarifications

Recorded 2026-10-01. Two questions asked, two answered; both took the recommended answer. Three more
were drafted and dropped because the repository or the issue already answered them: the plugin's own
copy `agents/_shared/reviewer-contract.md` stays an accepted document-side form because
`scripts/check-receipt-schema.py` reads exactly that file; the bump is a patch because only shipped
prose under `agents/` changes and no flow moves; and no reviewer keeps `.agents/_shared/` as a
fallback for installs made between #82 and #146, because one concrete path per harness is the
invariant the guard enforces and the issue's **Expected** names `.agents/agents/` alone.

1. **Does AC3 stay — `skills/init/SKILL.md` held to naming both concrete destinations, as the
   shipped reviewers are?** — *Kept.* The closed set alone lets `init` drop to the bare `_shared/`
   form and still pass, and then nothing in the guard pins what `init` writes; anchoring the set to
   the writer is what makes a future move of either path loud. Costs one role in the guard and one
   sub-case.
2. **Was the reviewer on the reporting install actually spawned by Antigravity from
   `.agents/agents/`, so that `docs/verified.md:274` and `:278` could be ticked here?** — *Not
   confirmed; left open.* AC7 rewords the open item and does not close it. This branch makes every
   statement agree with what `init` writes and claims nothing about where Antigravity looks.

## 2. Design (HOW)

- Fix approach, and why this rather than the narrower or wider fix:

  **Narrower** is the issue's first three bullets — move `CONCRETE[1]` and `INSTALLED_PREFIXES` to
  `.agents/agents/` and fix the four reviewer lines. The triage measured that as green (mutation B),
  and it is the state #146 should have shipped. Rejected on the root cause: it leaves the document
  side on `endswith`, so the next move of the placement passes the guard the same way this one did.
  **Wider** is the issue's "require `docs/layout.md` to carry both concrete paths", rejected in the
  triage because that file draws trees and the guard refuses to parse them, and the question of
  whether Antigravity discovers subagents under `.agents/agents/` at all, which is Q2 and row 10.

  The fix is three rules, all in `scripts/check-contract-path.py`:

  1. **One destination per harness, stated once.** `CONCRETE` becomes
     `(".claude/agents/…", ".agents/agents/…")` and `INSTALLED_PREFIXES` moves with it, so the
     `EXACT` rule — a reviewer must name every entry of `CONCRETE` verbatim — now demands the path
     `init` writes. This alone turns the guard red on `main`'s four reviewers, which is AC1.
  2. **The document side is a closed set, not a suffix.** `SUFFIX` is renamed `DOCUMENTS`, because
     the rule it carried is gone: a mention must be one of `ALLOWED` plus the plugin's own source copy
     `agents/_shared/reviewer-contract.md`, named as `PLUGIN_COPY` with the reason it is a form a
     document may cite and a reviewer may not. The flat sibling `.claude/agents/reviewer-contract.md`
     is rejected as before, by not being in the set rather than by not ending in `_shared/`. The
     tuple gains `docs/fidelity.md`, and `MIN_DOCUMENTS` rises from 6 to 7. The failure message says
     "not a form the placement takes" and lists the set, replacing "does not end in".
  3. **The file that writes the placement names both destinations.** A one-entry role,
     `PLACING = ("skills/init/SKILL.md",)`, checked inside the `DOCUMENTS` branch: missing any entry
     of `CONCRETE` is a failure naming which. `shape_problems()` gains a floor for it and a clause
     that every `PLACING` entry is also in `DOCUMENTS` — a `PLACING` entry outside `SOURCES` is never
     iterated, so its obligation would evaporate silently, which is the exact shape the collector
     exists to refuse.

  Why the rename is in scope and not churn: a tuple called `SUFFIX` whose rule is set membership is a
  name that describes a rule the guard no longer applies, and the comment beside it says `endswith`
  is "what rejects the flat sibling", which stops being true. The old name survives only in dated
  records (`.specs/_archive/82-…`, `146-…`, the work logs), which are left as written.

- Affected files:
  - `scripts/check-contract-path.py` — the three rules above; the module comments on `CONCRETE`,
    the document tuple and the prefixes rewritten to say what is now true; the docstring gains one
    paragraph naming #217 beside #82.
  - `scripts/test-gates.sh` — `cpath_repo` builds its reviewers with `.agents/agents/_shared/…`,
    its `skills/init/SKILL.md` with both concrete paths, and a `docs/fidelity.md`; case 62's
    `names-missing` assertion reads `.agents/agents/_shared`; case 64's `shrink_cpath` and its
    "sits in" assertion use the new tuple name; and a new case, **170**, pins #217: the shipped
    reviewer line as it stood on `main` fails and is named; `init` naming a concrete path the
    reviewers do not fails and is named; `init` naming only the bare form fails for AC3's reason;
    `docs/fidelity.md` removed fails as a missing source; `PLACING` emptied fails at the floor; a
    `PLACING` entry outside `DOCUMENTS` fails as a shape problem. Each mutation edits the fixture or
    the fixture's copy of the guard, never `$ROOT`'s. *Found at T1:* case 61's Antigravity half
    installed the reviewers into `.agents/` — the directory they named and no install had — so it
    passed on `main` with the broken line; its fixture moves to `.agents/agents/` and is then red
    against `main`'s reviewers, which makes it the consumer-side regression test AC1's guard-side
    one does not cover.
  - `agents/ts-reviewer.md:10`, `agents/python-reviewer.md:10`,
    `agents/dart-flutter-reviewer.md:10`, `agents/_template/reviewer.md:12` — `.agents/_shared/`
    becomes `.agents/agents/_shared/`; nothing else on the line moves.
  - `docs/verified.md:278` — the open item names `.agents/agents/` (AC7).
  - After the review, as steps of `implement`: `plugin.json` and `.claude-plugin/plugin.json`
    0.21.3 → **0.21.4**; the work-log entry; `Status: done`.

- **Blast radius:**
  - `check-contract-path.py` runs on every turn end here (`- Validators:`), in CI's guard job, and in
    the reviewer's allow-list. Its name and exit contract do not change, so
    `check-reviewer-allow-list.py` and `.github/workflows/ci.yml` are untouched. Rules 1 and 3 and
    the reviewer edits must land in **one commit**: with rule 1 alone the four reviewers fail the
    guard, and with the reviewers alone the old `ALLOWED` rejects `.agents/agents/…` — either
    half-state ends the turn red.
  - `scripts/check-receipt-schema.py` names the plugin's copy and is a `DOCUMENTS` source; it is
    unchanged and stays green by `PLUGIN_COPY`. The control case (62, `cp-control`) pins that.
  - `assets/check-locks.py` hashes `agents/*/rules/*.md`, not `agents/*-reviewer.md`, so no lock
    moves and no re-pin is needed; AC6 runs it rather than assuming it.
  - Consumers: an installed reviewer is the consumer's file. Installs that worked around #217 by
    editing their line are unaffected; installs that have not get the corrected line on their next
    `init`. No hook, no skill and no gate script changes, so `test-gates.sh` moves only in the
    contract-path section.
  - `docs/BACKLOG.md` row 19 cites "169 cases in the suite"; this branch makes it 170. Left to the
    next refinement, which discharges row 1 from the same file.

- Why this cannot recur: the placement is now stated in one tuple and every other statement is
  compared to it in both directions — a reviewer must name each entry verbatim, a document may name
  nothing outside the set, and the file that writes the placement must name every entry — so moving
  `init`'s path without moving `CONCRETE`, or `CONCRETE` without the reviewers, or either without the
  documents, is red until all of them move together. #146's mitigation, "it ends with the suffix, so
  it passes", has no rule left to satisfy. What remains, and is recorded rather than implied: a new
  document that states the placement and is not in `DOCUMENTS` is still outside the comparison, the
  exemption-list problem the guard's own comment names and #23's class; and whether Antigravity opens
  the path at all is Q2.

## 3. Tasks (TDD-ordered)
> One task is one complete Red-Green-Refactor cycle, so one green commit. No task is sequenced after the review.

- [x] T1: case 170 in `scripts/test-gates.sh` with the fixture moved to `.agents/agents/`, run
      against the guard on `main` — red on every sub-case, since the old `CONCRETE` accepts
      `.agents/_shared/` in a reviewer and `endswith` accepts anything in a document — then the three
      rules in `scripts/check-contract-path.py` and the four reviewer lines, until case 170 and
      cases 62–64 pass and the guard exits 0 on the tree with 12 sources. Ends green on AC1–AC6, with
      the red transcript captured for the pull request body.
- [x] T2: the blast radius — `docs/verified.md:278` reworded (AC7); every validator on the
      `- Validators:` line and the full suite re-run; `check-receipt-schema.py` and `check-locks.py`
      confirmed byte-identical in output to `main`'s. Ends green on AC7 and the full validator run.
