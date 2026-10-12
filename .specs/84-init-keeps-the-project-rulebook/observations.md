# Observations — #84's upgrade path on a scratch clone of #76's target

Recorded 2026-10-12 for AC7. The target is #76's: the plugin's first consumer, a Python project with `uv`, `ruff`, `mypy`, `pytest` and a `src/` layout, now migrated to the plugin-run gates. By #76's rule, nothing here names the project, a path inside it beyond the harness's own, a rule id, or a commit from it. The clone was made locally with `git clone` from the working checkout's default branch, into a `mktemp -d` directory in the session scratchpad. Nothing was pushed, and the real checkout was only read.

## What the target carries

- `.steering/tech.md` names `- Reviewer: python-reviewer` and `- Docs: docs/`.
- `.claude/agents/python-reviewer/` is the project's own reviewer. `rules/` holds three files: the reference's two, edited, and a third with no counterpart in the plugin. `rules-lock.json` pins all three. `python-reviewer.md` and the lock both differ from the plugin's.
- `docs/CONTRACT.md` has a tier-definition table (`| Tier | Destination | ... |`, no `id` column) and a Rules table (`| id | Rule | Tier | Severity | Enforced by |`). The Rules table cites **15 ids** as Judgment, matching #76's count. **Ten rows are tiered `Judgment` and five are tiered `Mechanical + Judgment`.**
- `scripts/check-locks.py` is the copy from an earlier install, 128 diff lines from the plugin's. `.claude/agents/_shared/reviewer-contract.md` matches the plugin's byte for byte.

## Upgrade path — step 3's reviewer bullet as amended

Followed as written: kept the reviewer, its `rules/` and its lock, and compared only the two plugin-owned files. `check-locks.py` differed and was copied; the reviewer contract did not differ and was left alone. Then `check-locks.py --update`, then `check-locks.py`.

| Run | Exit | Output |
| :-- | :-- | :-- |
| the project's own copy, before | 0 | `3 pinned file(s) match their locks in .claude/agents` |
| first build of the new copy, after `--update` | 0 | `docs/CONTRACT.md cites 10 Judgment rule id(s), each defined in .claude/agents/python-reviewer/rules` |
| fixed build (`efb27c6`, then the T4 commit) | 0 | `docs/CONTRACT.md cites 15 Judgment rule id(s), each defined in ...`, then `3 pinned file(s) match their locks` |

`--update` re-pinned nothing, because no rule file had moved. The lock, the reviewer and its rules were byte-identical to `HEAD` afterwards; `git status` showed only `scripts/check-locks.py`.

**The defect this run found: 10 where the contract cites 15.** The first build counted a row only when its whole Tier cell was `Judgment`, so the five `Mechanical + Judgment` rows were never checked. That is a guard reporting success on a subject it did not read, the class this repository's anchor exists to refuse, and no synthetic fixture had a combined tier. The spec's design was amended in its own commit (`efb27c6`). `test-gates.sh` case 235 was red against the first build, and the parse now accepts any tier that names `Judgment` as a word.

## The #84 state, reproduced on the real target

The reviewer directory and agent file were removed and the reference `python-reviewer` was copied in their place. That is #76's stripped path followed by a fresh install, and what the issue reports.

| Guard | Exit | Output |
| :-- | :-- | :-- |
| the project's old copy | 0 | `2 pinned file(s) match their locks in .claude/agents` — the reference lock matching the reference rules |
| the new copy | 1 | `.claude/agents/python-reviewer/rules: docs/CONTRACT.md cites Judgment rule(s) this rulebook does not define:` and 15 ids, then the restore-or-`contract` line |

**Copying the reference over the project's directory, without removing it first, did not reproduce it.** The reference has no file by the name of the project's third rule file, so `cp -R` left that file in place, and all 15 ids are defined there. The new guard passed, correctly, because every cited rule is still defined. But the reference lock then pins **2** files, so the project's third file is in the rulebook and **outside the lock**: `check-locks.py` hashes only what a lock lists, and a rule file the lock does not name is never checked. That is adjacent to #19 rather than inside this spec, and it is recorded here, not filed, because filing it mid-branch reddens this pull request (`check-backlog-tracker.py`). Whether it becomes an issue is the maintainer's call.

## Stripped path — history first

| Case | Before restore | Restore | After |
| :-- | :-- | :-- | :-- |
| `.claude/agents/` deleted, not committed | exit 1: `docs/CONTRACT.md cites Judgment rule(s)` (15 ids) `of reviewer \`python-reviewer\`, but there is no rulebook for it: no \`python-reviewer/rules/\` in any reviewer directory.` | `git checkout HEAD -- .claude/agents/` | exit 0, 15 defined, 3 pinned |
| `.claude/agents/` deleted in a commit | exit 1, same message | `git log --diff-filter=D --format=%H -1 -- .claude/agents/ .agents/agents/` named the commit; `git checkout <that>^ -- .claude/agents/` | exit 0, 15 defined, 3 pinned |

Both restore commands are the ones step 3 now gives, run verbatim. In both cases the restore brought back the reviewer, its three rule files and its lock as they were.

## Not exercised

- The rest of `init`'s upgrade path: detection, the interview, steering, the hooks and the document set. This run exercised step 3's reviewer bullet and the guard it relies on, which is what #84 is about.
- An Antigravity install (`.agents/agents/`), and a dual-target one on a real project. Case 231 covers the dual-target check on a fixture only.
- A project reviewer with no `rules-lock.json`, so the step 3 sentence about saying so (#19) was not reached on a real target.
- The fallback to `contract` when history holds no rulebook. This target's history always had it.
