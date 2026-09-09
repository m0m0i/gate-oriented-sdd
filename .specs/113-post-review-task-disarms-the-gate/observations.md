# Observations — #113

## The shape of the defect, before any change

`hooks/review-gate.sh:55` is `[ "$(gate_open_tasks "$spec")" -gt 0 ] 2>/dev/null && gate_pass`. Zero open tasks is a *proxy* for "implementation is finished", and it is sound only while every task is implementation work.

One spec in the archive violates that: `.specs/_archive/105-a-clock-on-every-allow-list/spec.md:48`, whose T5 is the version bump held until after the review because `.steering/tech.md:16-20` said to. The gate was therefore silent from the end of T4 until T5 was ticked — the whole review window.

**Prior art, found while writing the spec rather than known in advance:** `.vscode/settings.json:1-7` records #66, where Prettier-on-save unticked a spec's tasks and reverted its `Status`, leaving the branch "one step from a PR with the gate never firing". Same proxy, different cause. #66 removed the cause and left the proxy; #113 removes the proxy's second cause and guards the definition on both sides.

## What review changed

The reviewer returned BLOCKED with 2 HIGH, 3 MEDIUM, 2 LOW against `5b5de68`. Both HIGHs were fail-opens in the guard written for T1, and neither was the gap the guard's own comment had named.

| Finding | What escaped | Now |
| :-- | :-- | :-- |
| HIGH — task-id separator | `TASK_PREFIX` consumed an id only before `[:.)]`, so `- [ ] T5 — after the review, bump` left `T5` as the entire directive and the deferral was never examined | the id group takes a dash separator and a bolded id; four accusing fixtures in case 51 |
| HIGH — unreadable directory | `Path.glob` swallows the `OSError` from an unreadable `.specs/` or spec directory, so the guard printed an affirmative line about specs it never enumerated | enumeration is explicit and appends to `unreadable`; a scan of nothing says "no live spec to scan"; case 55 |
| MEDIUM — mirrored phrasing | matching only the directive missed `T5: bump both manifests — after the review`, a coin flip from #105's real wording | later clauses are matched at their start; the mirror is the fourth fixture in case 51 |
| MEDIUM — fixture built the wrong state | `specs_repo` creates `.specs/`, so the "missing `.specs/`" case tested an *empty* one and never entered the branch it claimed | `rmdir` in the case |
| MEDIUM — index drift | a new mechanical invariant had an enforcer and no row in `AGENTS.md`, `CONTRIBUTING.md`, `docs/CONTRACT.md` or `docs/DESIGN.md` | one line each, and `M-12` in the contract |
| LOW — over-reach undocumented | only the under-reach edge was written down | the over-reach edge and its rephrasing are in the guard's comment |
| LOW — blockquote | the rule reached the shared note but not the block a spec actually copies | appended to the Feature and Bug blockquotes |

The MEDIUM on the mirror is the one worth remembering: the first cut closed the phrasing that had actually occurred and left its symmetric twin open, which is a guard fitted to one example rather than to a class.

## The count claim

62 → 66 after T1-T4, then → 67 after review added case 55. Both moves were re-enumerated with `git grep` across all tracked files rather than a hand-listed set of directories — the #105 lesson, where five places were corrected and a sixth left false. Six live statements, no seventh: `.steering/structure.md:19`, `README.md:41`, `README.md:156`, `README.ja.md:43`, `README.ja.md:157`, `CONTRIBUTING.md:21`.

Records left alone, checked rather than assumed: `docs/verified.md`'s dated rows, the `.work_logs/` mentions, and the archived specs' own numbers — including #105's T5, which this guard would flag and which is excluded by name for that reason.

## AC7 discharged by a step

No task in section 3 bumps the version. `skills/implement/SKILL.md:48` does it after the receipt, which makes this branch the first to run the flow it prescribes. `check-version-bump.py` is red against `origin/main` for exactly that reason from the first commit until the step runs, and CI is the backstop.
