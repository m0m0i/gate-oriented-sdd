# Spec: Five README sentences describe an implementation that has moved on
- Slug: 219-five-readme-sentences-moved-on   Issue: 219   Type: chore   Status: approved
- Author: m0m0i   Date: 2026-09-30

## 1. Requirements (WHAT / WHY)

- What changes: #219's **What changes** — five sentences in `README.md`, three of them mirrored in `README.ja.md`, the `## Status` paragraph of `evals/README.md`, and row 19 of `docs/BACKLOG.md`. The replacement text is fixed here so the diff can be read against a decision rather than invented at edit time:
  1. `README.md:37` "The six inception skills account for ~450 of that always-on total" → "The seven inception skills account for ~580 of that always-on total". `README.ja.md:39` 「上流工程の6つの skill は、この常時分のうち約450トークンを占めます」→「上流工程の7つの skill は、この常時分のうち約580トークンを占めます」.
  2. `README.md:76` "`backlog` creates the tracker issues `spec` consumes" → "`backlog` orders the list from which `sprint` creates the typed tracker issues `spec` consumes". `README.ja.md:113` already reads `backlog` → `sprint` and is not touched.
  3. `README.md:103` and `README.ja.md:70`: `#22` → `#166`, nothing else on either row.
  4. `README.md:183` "its four cases are authored, and `claude plugin eval` is still in early access on this account." → "its four cases are authored, but `claude plugin eval` now rejects them at load, because a `case.yaml` must declare `graders`, so they are still unrun." `README.ja.md:184` 「4つのケースは書いてあり、`claude plugin eval` はこのアカウントではまだ early access のままです。」→「4つのケースは書いてありますが、`claude plugin eval` は読み込み時にそれらを拒否する（`case.yaml` に `graders` が必要）ため、まだ一度も実行できていません。」. `evals/README.md:12`, the first sentence under `## Status`, states the same rejection in place of "was not enabled on the account these were written on".
  5. `README.md:26` "a vendored, hash-pinned rulebook" → "a hash-pinned rulebook". `README.ja.md:27` already reads 「ハッシュ固定」 and is not touched.
- **What must NOT change:** #219's **What must NOT change**, stated as checks. `./scripts/check-readme-claims.py` prints at the tip the line it prints at the merge-base. `README.md:185` and `README.ja.md:186` are byte-identical to the merge-base. Against the merge-base, `git diff --numstat` names `README.md` with 5 lines changed, `README.ja.md` with 3, `evals/README.md` with 1 and `docs/BACKLOG.md` with 1, and no other path outside `.specs/219-five-readme-sentences-moved-on/` and `.work_logs/`. No row of the ordered list other than 19 changes in any cell; `## Unshaped` and `## Open, not planned` are untouched; nothing is written under `## What changed at this refinement`.
- Why now: #219's **Why now**.
- Acceptance criteria:
  - [ ] **AC1:** every old string in the Design's grep table is absent from its file and every new one present exactly once.
  - [ ] **AC2:** `./scripts/check-readme-claims.py` exits 0 and prints `check-readme-claims: 2 README(s) carry a version badge (plugin.json is at v0.21.3), 3 of 56 receipts inline, no behaviour count asserted`, the merge-base's line.
  - [ ] **AC3:** `git diff --numstat <merge-base> -- . ':!.specs' ':!.work_logs'` lists exactly `README.md` 5/5, `README.ja.md` 3/3, `evals/README.md` 1/1 and `docs/BACKLOG.md` 1/1.
  - [ ] **AC4:** `git diff <merge-base> -- README.md README.ja.md` contains no hunk touching `README.md:185` or `README.ja.md:186`.
  - [ ] **AC5:** row 19's Item cell in `docs/BACKLOG.md` names **#219**; its `Why here` no longer says that `README.md:183` waits on row 16 or that three sit unfiled; `./scripts/check-backlog-tracker.py` exits 0 on the pull request, where CI runs it.
  - [ ] **AC6:** `evals/README.md`'s `## Status` paragraph names the load rejection, and everything from `## Running them` down is byte-identical to the merge-base.
  - [ ] **AC7:** every validator on `.steering/tech.md`'s `- Validators:` line exits as it does at the merge-base, and `./scripts/check-version-bump.py <merge-base>` prints `no shipped file changed`.
  - [ ] **AC8:** the figures written for item 1 are the ones `claude --plugin-dir . plugin details gate-sdd` reports at the tip, summed over the seven components the Inception diagram names; the run is quoted in T2's commit body, because no guard reads these numbers.
- Out of scope: #162, the "Tested against" line; `CONTRIBUTING.md:21` and `docs/DESIGN.md:13`, row 19's other unfiled counts; `.steering/product.md`'s "see #22", which points at a discussion and not at an open gap; any guard for these sentences, which is #137; any change to the order of the backlog.

### Clarifications

Run 2026-09-30. Three assumptions survived step 3. The first is the only one that changes a sentence's content; the maintainer asked for the flow to run end to end, so the recommended answer is taken here and named in the pull request.

- **Q1. Does "inception skills" count `contract`?** Yes — seven, ~580. The Inception diagram draws `contract` beneath the chain, and the paragraph's argument is about skills that fire once per project, which `contract` does. The reading that keeps "six" — the diagram's top row only — gives ~480 and would need the word "chain" rather than "inception". Recommended answer taken; the other costs one edit if the maintainer prefers it.
- **Q2. Does retiring `README.md:183` pre-empt row 16?** No. Row 16 owns re-authoring the cases and running them; this sentence states what is true today, and row 16's "retire" step becomes a rewrite of the new sentence rather than of the old one. Mine to decide, and decided.
- **Q3. Where does #219 go, and is it a refinement?** Row 19's Item cell, beside #162, with one sentence in `Why here`; no ordering change and nothing under `## What changed at this refinement` — the form of #209's Q1 and of #215's one-number correction. A placement between refinements is not one. Mine to decide, and decided.

## 2. Design (HOW)

- Approach, and the order of operations: three commits after this spec, each green. **First the placement** — row 19 gains #219, and `check-backlog-tracker.py` is that commit's failing test on the pull request: red on `main` from the moment #219 was filed, green with the row. **Then the two READMEs in one commit**, so no commit on the branch leaves the pair disagreeing, which is C-3's whole point. **Then `evals/README.md`**, the sibling statement of item 4, alone, so its diff reads as one paragraph.
- Affected files: `README.md` (lines 26, 37, 76, 103, 183); `README.ja.md` (39, 70, 184); `evals/README.md` (the first sentence under `## Status`); `docs/BACKLOG.md` (row 19). None is a shipped path, so `check-version-bump.py` asks for nothing.
- The greps that are AC1's test, each run as `grep -c` on the named file; "0" is the count after the change, "1" the count before it for old strings and after it for new ones:

  | File | Old string (0 after) | New string (1 after) |
  | :-- | :-- | :-- |
  | `README.md` | `six inception skills` | `seven inception skills` |
  | `README.md` | `~450` | `~580` |
  | `README.md` | `` `backlog` creates the tracker issues `` | `` orders the list from which `sprint` creates `` |
  | `README.md` | `the gap is #22` | `the gap is #166` |
  | `README.md` | `still in early access` | `rejects them at load` |
  | `README.md` | `vendored, hash-pinned` | `a hash-pinned rulebook` |
  | `README.ja.md` | `6つの skill` | `7つの skill` |
  | `README.ja.md` | `約450` | `約580` |
  | `README.ja.md` | `#22` | `#166` |
  | `README.ja.md` | `まだ early access` | `読み込み時にそれらを拒否` |
  | `evals/README.md` | `was not enabled on the account` | `graders: Required` |

- **Coverage gap:** none of the five sentences is in `check-readme-claims.py`'s claim class, and none can join it cheaply: items 1 and 4 have a tool run as their only source, item 3 needs the tracker, and items 2 and 5 are prose agreeing with other prose. Widening the class is #137 on row 19. So the tests here are the grep table and the validators, run before the change as the baseline and re-run after — the shape #97 and #157 used for the same two files.
- Rollback: revert the three commits. Nothing installed changes.

## 3. Tasks (TDD-ordered)
> One task is one complete Red-Green-Refactor cycle, so one green commit. No task is sequenced after the review.
- [x] T1: record the baseline — the grep table with every old string at 1 and every new one at 0, `check-readme-claims.py`'s line, and the validators' exit codes at the merge-base — then place #219 on row 19 (AC5's text half); the tracker check is the failing test, and CI runs it on the pull request.
- [x] T2: the five English edits and the three Japanese edits, one commit, with the `plugin details` run quoted in the body; AC1's README rows, AC2, AC4, AC8.
- [ ] T3: `evals/README.md`'s `## Status` paragraph; AC1's last row, AC3, AC6, AC7.
