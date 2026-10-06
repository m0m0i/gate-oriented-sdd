# Spec: quality-gate.sh's skip check expands a bare `- Source globs:` word against the repo root and passes having run nothing
- Slug: 254-a-bare-glob-expands-against-the-root   Issue: 254   Type: bug   Status: done
- Author: m0m0i   Date: 2026-10-06

## 1. Requirements (WHAT / WHY)

- Reproduction: the issue's, measured again at `ab518af` (bash 3.2.57 as `sh`, git 2.54.0, macOS). A repository with `- Validators: sh ./validator.sh` and `- Source globs: *.py`, a validator that exits 1, `a.py` at the root and `sub/b.py` below it, all committed. Modify `sub/b.py` only and run `sh hooks/quality-gate.sh`.

- Expected: exit 2 and a block naming the validator. `sub/b.py` matches `*.py`, so the skip check finds a change and the validators run. Git itself agrees: `git status --porcelain -- '*.py'` prints ` M sub/b.py`, because a pathspec without `:(glob)` lets `*` match `/`.

- Actual: `{}` on stdout, exit 0, and the validator never runs. The issue's table, re-measured and unchanged: a bare `*.py` with a root match fails open; the same line with no root `.py` file reaches git unexpanded and blocks; `**/*.py` blocks by luck of layout; `:(glob)…` is unaffected.

- Impact: any project whose line is a bare glob rather than a `:(glob)` pathspec, with at least one unchanged match at the repository root, which is the flat layout `init` produces for a small project. For every change below the root the gate skips the validators silently, and nothing reports that it did. Under `- Owns: gates never fail open` a gate that silently stops checking is a BLOCKER (G-1). `scripts/test-gates.sh` stays green because `qg_repo`'s fixture is flat: its one `.txt` file is at the root and is the file the case changes, so the expansion happens to name the changed file. Found by a review bot on a consumer's pull request that refreshed its hook copies to 0.22.0; that consumer uses `:(glob)` and is unaffected.

- **Root cause:** `hooks/quality-gate.sh:107` splits the line with `set -- $(printf '%s' "$globs" | tr -d '\042\047')`. The substitution is unquoted on purpose, so that each glob reaches git as its own pathspec. Unquoted, the result goes through field splitting **and then pathname expansion**, so the shell matches each word against the current directory, the repository root, before `git status` sees it. `hooks/gate-lib.sh` does the identical split three times, at `:285`, `:374–376` and `:410`, and every one of them sits between `set -f` and `set +f`, with the library's #1 comment naming exactly this mechanism. The quality gate's copy was written beside them and never got the two lines. The convention that `:(glob)` "earns its place" because the shell leaves it alone (`.steering/tech.md:47`, `skills/init/SKILL.md:60`) is a workaround for this expansion stated as a rule, and it protects only a project that followed it.

- Acceptance criteria:
  - [ ] **AC1:** WHEN `- Source globs:` holds a bare glob, a file matching it is unchanged at the repository root, and a file matching it is modified below the root, THE quality gate SHALL run the validators and block on a failing one.
  - [ ] **AC2:** WHEN the line holds a bare glob and no file matching it has changed anywhere, THE quality gate SHALL still pass silently, so the skip keeps the cost it exists to save.
  - [ ] **AC3:** WHEN `- Validators:` names a command that itself relies on pathname expansion, THE quality gate SHALL run it with expansion on. `set -f` is scoped to the split, as in the library, and is not left on for the validator loop.
  - [ ] **AC4:** every existing case keeps its verdict. Cases 15–17 (the loop), `qg-clean`, `qg-docs`, `qg-src`, `qg-quoted` and 164 (`qg-multiglob`) in particular, since they are the fixtures beside the one this spec changes.
  - [ ] **AC5:** the regression case for AC1 fails against `ab518af`'s `hooks/` and passes after the fix; AC2's and AC3's cases pass before and after, and are pins.
  - [ ] **AC6:** WHEN a line of `hooks/*.sh` or `assets/*.sh` word-splits a `Source globs` value outside a `set -f` … `set +f` region, THE test suite SHALL go red, so the next copy of this split that forgets the two lines fails before it ships.
  - [ ] **AC7:** the two prose sites that present `:(glob)` as the thing that keeps the shell from expanding the line (`.steering/tech.md`'s "`:(glob)` is load-bearing" paragraph and `skills/init/SKILL.md`'s step that writes the line) say what is true after this fix: the gates disable expansion themselves, and `:(glob)` is recommended for what it means to git, not for what it hides from the shell.

- Out of scope:
  - #232, a `- Source globs:` value git rejects, which makes the staleness diff read a stale receipt as current. Same line, different fault, row 7.
  - #195, the quality gate reading an unreachable `.steering/` as absent. Same gate, different branch of it.
  - #245, how this fix reaches a project. Until it ships, a consumer gets this by re-copying `hooks/`, and the release notes say so.
  - A consumer's CI copy of the loop. The one known copy sources `gate-lib.sh` and re-implements the validator loop, not the skip check, so it does not carry the fault.

### Clarifications

Asked and answered 2026-10-06.

- **Q1. The two-line fix and a regression case close the issue. Does this spec also take AC6, a needle case that goes red on any future glob split outside `set -f`, and AC7, the two prose sites that present `:(glob)` as what keeps the shell from expanding the line?** Yes, both. The class and not the instance, and the docs stop teaching a workaround as the rule. → AC6, AC7.
- **Not asked, because the repo answers it:** the version bump is a patch. Shipped `hooks/` and a skill's prose change and the flow does not move, like #233 (0.21.8). The backlog cites #254 in row 7's `Why here`, the class it belongs to, rather than taking a row, as #222 did in row 17: it was taken ahead of row 1 by the maintainer's direction on 2026-10-06, and this branch's merge closes it.

## 2. Design (HOW)

- **Fix approach.** Disable pathname expansion across the split and re-enable it on the next line, exactly as the library does at its three sites:
  ```sh
  set -f
  set -- $(printf '%s' "$globs" | tr -d '\042\047')
  set +f
  git status --porcelain -- "$@" 2>/dev/null | grep -q . || gate_pass
  ```
  `set -f` and `set +f` are written as whole lines of their own, because AC6's needle recognises a region by those lines (below). The comment above the split is rewritten: it currently says the split is unquoted "on purpose" and cites #1 as the reason the quotes are stripped, without saying that unquoted means expanded. It will say both halves, and name this issue beside #1.
  - **Narrower:** none. Two lines is the fix.
  - **Wider:** quote the substitution and split with `IFS`, or read the line into positional parameters with `read`. Both change a line that four cases and the library's three sites agree on; `set -f` makes the quality gate's split the same shape as the library's, which is what the needle then pins.
- **AC6, the needle.** A case in `scripts/test-gates.sh` beside 189, the same shape: an `awk` over `hooks/*.sh` and `assets/*.sh` that tracks a `set -f` region per file. A whole line that is `set -f` opens the region and a whole line that is `set +f` closes it, so the inline `|| { set +f; return 1; }` on a read inside the region does not close it, and a read that follows one of those does not go red by accident. Outside the region, a line that is not a whole-line comment and holds either an unquoted expansion of a variable whose name ends in `globs` (`$_globs`, `$_wglobs`, `$globs`, not preceded by `"`) or `set -- $(` is a hit. Self-tested on a hit file and a miss file before the tree is read, and `awk`'s status is checked, as case 189 does, so a broken pattern or an empty list cannot report ok having read nothing. A `set -f` region that reaches the end of its file unclosed is a hit too, so dropping the `set +f` line cannot hide every split after it. At `ab518af` it finds exactly one line, `quality-gate.sh:107`, and after T1 none.
- **AC7, the two prose sites.** `.steering/tech.md`'s "`:(glob)` is load-bearing" paragraph becomes: the gates disable pathname expansion across the split, since #254, so a bare `*.py` reaches git as written; `:(glob)` is still the recommended form, because it says to git what the author means, where a bare `*` in a plain pathspec matches `/` as well. `skills/init/SKILL.md:60` says the same in its own words. The line `init` writes keeps its `:(glob)` examples. `scripts/check-skill-contracts.py` pins nothing in that bullet, measured by grep.
- **Affected files:** `hooks/quality-gate.sh`, `scripts/test-gates.sh`, `.steering/tech.md`, `skills/init/SKILL.md`, `docs/BACKLOG.md`. Shipped, so `implement`'s version step bumps the patch.
- **Blast radius:**
  - **The validator loop.** `set +f` precedes it, so a validator that relies on expansion runs as before. AC3 pins it: the validator runs under `eval` in the gate's own shell, so a leaked `set -f` would reach it.
  - **The four fixtures beside the fixed line.** `qg-clean`, `qg-docs`, `qg-src`, `qg-quoted` and case 164 all use a bare `*.txt` or `:(glob)` patterns against a flat tree; with expansion off, a bare `*.txt` reaches git literally and git matches the same root file. AC4 holds them.
  - **The library.** Untouched. Its three sites already carry the region.
  - **A consumer.** The skip now blocks on a change below the root, which is the turn it was always meant to block. A consumer whose line is `:(glob)…` sees no change.
### Mutation record

Measured 2026-10-06 in T1, bash 3.2.57 as `sh`, git 2.54.0. Unmutated, the suite is 206 passed / 0 failed / 0 skipped. Each row is the shipped `hooks/quality-gate.sh` with one mutation applied; the suite at `ab518af` with case 202 present is the first row's shape (205 / 1 / 0, `docs-silent=ok blocks=no ran=no`).

| Mutation | Cases red | Suite |
| :-- | :-- | :-- |
| the `set -f` line deleted | 202 | 205 / 1 / 0 |
| the `set +f` line deleted (T2, suite 208 unmutated) | 203, 204 | 206 / 2 / 0 |

Case 204's needle, run over `hooks/` as shipped at `ab518af`, reports exactly `quality-gate.sh:107`, the split this spec fixes, and nothing in `gate-lib.sh` or `assets/`. Its first draft left the `set +f` mutation green, because an opened region that never closes read as covering the rest of the file; an unclosed region is now a hit of its own, which is why the second row has two cases.
- **Why this cannot recur:** the needle (AC6). The next copy of the split that forgets the two lines goes red before it ships, and the comment at the fixed site names the case that would catch it.

## 3. Tasks (TDD-ordered)
> One task is one complete Red-Green-Refactor cycle, so one green commit. No task is sequenced after the review.
- [x] T1: a case for AC1 and AC2 in one, after case 164: a `qg_repo` fixture with a root `a.txt` unchanged and `sub/b.txt` modified, red at `ab518af`; then a docs-only change on the same fixture, silent before and after. Then the two lines and the rewritten comment in `hooks/quality-gate.sh` → green.
- [x] T2: the AC3 pin (a validator of `ls sub/*.txt`, which fails only if `set -f` leaks; green before and after, red under the mutation that drops `set +f`) and the AC6 needle with its self-test → green.
- [x] T3: AC7's two prose sites, and #254's citation in `docs/BACKLOG.md` row 7. Full suite and every validator green.
