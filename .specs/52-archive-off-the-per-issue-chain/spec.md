# Spec: Archive leaves the per-issue chain, and the chain stops describing a PR that is gone
- Slug: 52-archive-off-the-per-issue-chain   Issue: 52   Type: feature   Status: done
- Author: m0m0i   Date: 2026-08-29

## 1. Requirements (WHAT / WHY)

- User story: As someone shipping an issue through this harness, I want the whole issue to cost
  **one** pull request and archiving to be a sweep I run when I choose, so that finishing work
  costs one merge rather than two and the documented chain matches the one I actually run.
- Serves: the process layer of the three-layer claim. Skills are the layer that *can* be skipped,
  and a chain carrying a step that produces no reviewable change is the kind of ceremony that gets
  the whole harness skipped along with it.
- Acceptance criteria:
  - [ ] **AC1:** WHEN any document in this repository describes the delivery chain — `README.md`,
    `README.ja.md`, `hooks/steering-digest.sh`, `.specs/README.md`, `docs/layout.md`, and the
    `description` field of **both manifests**, which is the chain a marketplace listing shows
    before a single skill body loads — THE SYSTEM SHALL name it as
    `spec → clarify → implement → reviewer → worklog`, containing neither a spec review PR nor an
    `archive` step.
  - [ ] **AC2:** WHEN a session starts THE SYSTEM SHALL state in the digest that archiving shipped
    specs is a sweep run on request, not a step in the per-issue flow.
  - [ ] **AC3:** WHEN `implement` reaches its closing step THE SYSTEM SHALL have the work-log entry
    committed on the issue's own branch, so it ships inside that issue's single PR, and SHALL NOT
    propose archiving or any follow-up pull request.
  - [ ] **AC4:** WHEN `archive` is read — its `description:` line included, since that is what a
    harness surfaces before the body is ever loaded — THE SYSTEM SHALL present it as an on-request
    sweep of shipped specs rather than as the step that follows a merge.
  - [ ] **AC5:** WHEN this change lands THE SYSTEM SHALL carry a version bump to `0.4.0` in both
    manifests, since `skills/` and `hooks/` are shipped paths and `check-version-bump.py` fails
    otherwise.
- Out of scope:
  - **Moving the work log out of the feature PR.** Considered and rejected: a per-session work-log
    PR trades one bookkeeping PR for another.
  - **Any change to `review-gate.sh` or `quality-gate.sh`.** Neither reads archive state — the
    review gate keys on `.specs/$branch/spec.md`, the current branch only, so an un-archived
    shipped spec cannot trip it. That is precisely why deferring the sweep is safe, and it is also
    why this issue must not become a gate change.
  - **Automatic archiving** — a hook or a session-start prompt that sweeps on its own. "Ad-hoc"
    here means *on request*, not *on a trigger*.
  - **#48**, the READMEs' stale `0.2.3` Status claim. AC5 moves the manifests; the Status sections
    are that issue's work and touching them here would hide it.

### Clarifications

Recorded 2026-08-29. Three answered before drafting, three during `clarify`.

1. **Where does the work-log entry land?** → It stays in the feature PR, exactly where `implement`
   puts it today. A separate per-session work-log PR was the alternative; it was rejected because
   it removes a bookkeeping PR by adding one. *Changes:* nothing in `worklog`'s behaviour; AC3 is
   about what `implement` must *not* do afterwards, not about moving the entry.
2. **When does `archive` run?** → Only when asked. Rejected: sweeping inside a housekeeping PR, and
   prompting for it from the session-start digest. *Changes:* the digest states the fact and stops
   there — it does not offer, because an offer every session is a trigger wearing an offer's
   clothes.
3. **How is this change itself made?** → Through the harness: issue #52, this spec, one branch, one
   PR.
4. **Do the new sentences get pinned in `check-skill-contracts.py`?** → Yes, both — `implement`'s
   closing step and `archive`'s framing. *Changes:* the guard grows from 7 contracts to 9, against
   its own "keep the list short" instruction. Accepted deliberately: both sentences are ones whose
   silent deletion restores the second pull request, which is the exact failure this spec exists to
   remove, and a prose rule with no guard is what let the `(review PR)` node survive #30 by four
   months of edits.
5. **Does `archive` stay in the README delivery diagram?** → Yes, beside the chain, not in it. The
   alternative — dropping it from the flow section entirely — leaves a reader of that section never
   learning when to sweep.
6. **How far does the version move?** → `0.4.0`. The documented delivery flow changes for every
   consumer, which is a behaviour change to shipped skills and a shipped hook, not a fix.

## 2. Design (HOW)

### Approach and key decisions

The change is prose and one `echo` line. That is the whole risk: **prose has no compiler**, which is
the reason `check-skill-contracts.py` exists at all. So each of the two sentences that carry real
consequence gets pinned by a guard, and the digest's flow line — the one statement every cold
session reads — gets a case in `scripts/test-gates.sh`. What is left over is documentation whose
only check is the reviewer, and this spec says so plainly rather than implying coverage it does not
have.

Three decisions worth recording:

- **The digest asserts, it does not offer.** `steering-digest.sh`'s header says everything it prints
  is a factual statement, because imperative out-of-band text is surfaced to the user as an injected
  instruction. "Archiving is a sweep run on request" is a fact; "consider archiving" is not, and
  would also re-create the per-merge habit the spec removes.
- **`done` becomes the terminal state of delivery.** `archived` stays in the lifecycle and stays
  owned by `archive` — nothing about the state machine changes — but the documents stop implying a
  spec is unfinished until it moves. `.specs/README.md` and `skills/spec/SKILL.md` carry that.
- **No guard is added for AC1.** A grep asserting no README says "(review PR)" would pass the day it
  is written and pin a phrasing rather than a fact. AC1 is reviewer-checked, and T4 is the task
  where that is true.

### Affected modules and files, per `.steering/structure.md`

| File | Shipped | Change |
| :-- | :-- | :-- |
| `hooks/steering-digest.sh` | yes | the flow line loses `-> archive`; a line states the sweep is on request |
| `skills/implement/SKILL.md` | yes | step 5 states the work log is committed on this branch and that the PR is the last step |
| `skills/archive/SKILL.md` | yes | `description:` and body reframed from post-merge step to on-request sweep |
| `skills/worklog/SKILL.md` | yes | one line: following `implement`, the entry ships in that issue's PR |
| `skills/spec/SKILL.md` | yes | lifecycle table: `archived` is bookkeeping, not the end of delivery |
| `scripts/check-skill-contracts.py` | no | two new `CONTRACTS` entries |
| `scripts/test-gates.sh` | no | one case over the digest's flow line |
| `README.md`, `README.ja.md` | no | delivery diagram: `(review PR)` gone, `archive` moved beside the chain |
| `.specs/README.md`, `docs/layout.md` | no | same chain, stated once each |
| `plugin.json`, `.claude-plugin/plugin.json` | yes | `0.3.9` → `0.4.0`, and the `description` chain — an AC1 surface, found in review |

### Contract changes, and who else consumes them

- `check-skill-contracts.py`'s `CONTRACTS` tuple is the contract being extended. Its consumers are
  the Validators line and CI; both run the script, neither reads the tuple.
- The digest's output is consumed by every session start, resume, clear and compact. It is also
  asserted by two existing `test-gates.sh` cases (26 and 33), which check the quality anchor and
  the degraded-library path — neither reads the flow line, so they are unaffected.
- No hook interface, receipt field, or steering anchor changes. `Source globs` already covers
  `skills/**/*.md` and `hooks/**/*.sh`, so editing them re-stales a receipt correctly.

### Risks and trade-offs

- **The guard list grows against its own advice.** Recorded in Clarification 4. If a tenth contract
  is proposed, the right response is to re-read that docstring, not to keep adding.
- **A shipped skill and its guard can drift in the other direction:** the needle is a substring, so
  rewording the sentence fails the build even when the meaning survives. That is the intended cost —
  it forces the edit to be deliberate — but it means the needles must be short and quote the load-
  bearing clause only, not a whole sentence with punctuation in it.

  Two exceptions were argued in review and are recorded here so they are not re-opened as
  oversights. The `implement` needle keeps its conjunction — "Do not propose archiving, **and** do
  not open a follow-up pull request" — and is deliberately not split into two entries. The reason
  is *not* the init precedent about pinning one half of a conjunction: splitting would pin both
  halves and would not repeat that mistake. It is that one conjoined string already asserts both
  halves, so splitting buys zero coverage while spending the budget the docstring's new limit was
  just given. And the `archive` needle is deliberately *longer* than this bullet advises,
  `"to be noise — not after every merge"`, because the short form occurs in `README.md` and in
  near-miss wording in this skill's own body — a needle that can be satisfied somewhere other than
  the line it claims to pin is a guard that goes green having checked nothing.
- **`check-version-bump.py` is red from T1 until T5.** It is CI-only and deliberately not on the
  Validators line, so this blocks no turn; it is stated here so a reader of a mid-branch failure
  knows it is expected.
- **The consumer-visible flow changes without a migration.** Anyone who installed 0.3.x and reads
  the old chain from a cached skill keeps archiving per merge — which is harmless, since the sweep
  is idempotent and the gate ignores it.

## 3. Tasks (TDD-ordered)

> One task is one complete Red-Green-Refactor cycle, so one green commit.

- [x] **T1:** failing `test-gates.sh` case asserting the digest names the chain through `worklog`
      with no `archive` step and states the sweep is on request — then the `hooks/steering-digest.sh`
      edit that makes it pass. (AC1 digest half, AC2)
- [x] **T2:** failing `check-skill-contracts.py` — add the `implement` contract pinning the closing
      step's "no follow-up pull request" clause — then the `skills/implement/SKILL.md` edit that
      makes it pass. (AC3)
- [x] **T3:** failing `check-skill-contracts.py` — add the `archive` contract pinning the
      on-request-sweep clause — then the `skills/archive/SKILL.md` rewrite, `description:` line
      included, that makes it pass. (AC4)
- [x] **T4:** the prose with no guard, in one commit: `README.md`, `README.ja.md`,
      `.specs/README.md`, `docs/layout.md`, plus the lifecycle sentence in `skills/spec/SKILL.md`
      and the one line in `skills/worklog/SKILL.md`. Verified by the reviewer against AC1, not by a
      check — and this task is where that limitation is acknowledged rather than papered over.
      The `description` field of both manifests belongs to this task and was missed: review found
      it, and it is the AC1 surface a consumer sees first. (AC1)
- [x] **T5:** failing `./scripts/check-version-bump.py origin/main` — red since T1 touched a shipped
      path — then `0.3.9` → `0.4.0` in both manifests, green, with `./scripts/check-manifests.py`
      confirming they still agree. (AC5)
