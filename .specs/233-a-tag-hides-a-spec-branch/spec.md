# Spec: a tag that shares a spec branch's name hides that branch from the gate
- Slug: 233-a-tag-hides-a-spec-branch   Issue: 233   Type: bug   Status: approved
- Author: m0m0i   Date: 2026-10-04

## 1. Requirements (WHAT / WHY)

- Reproduction: the issue's, measured again at `7ef35ab` (git 2.54.0, macOS `sh`). `12-parked` holds a finished spec and no receipt, so the gate blocks from `main` and names it (case 76). After `git tag 12-parked 12-parked`, `sh hooks/review-gate.sh` prints `{}` and exits 0, both from `main` and while standing on `12-parked`.

- Expected: a tag does not change which branches hold finished work, or which commit the gate treats as shipped.

- Actual: the issue's two sites, plus two the measurement found beside them.
  - **Naming, both sides** (the issue): `symbolic-ref --short` (`hooks/review-gate.sh:83`) and `%(refname:short)` (`:259`) shorten unambiguously, so a tag-shadowed branch becomes `heads/12-parked`. That string is then used as the slug, and `.specs/heads/12-parked/spec.md` exists nowhere. A tag is not the only ref that shadows a name. The issue's LOW finding, a branch named `origin` beside `refs/remotes/origin/HEAD`, was measured while standing on that branch, where it blocks. Scanned from `main`, a finished spec on `origin` prints `{}` and exits 0, so it is the same fail-open.
  - **The base** (found here): `:115–119` resolve `origin/HEAD`, `origin/main`, `origin/master`, `main` and `master` by bare name, and git resolves a bare name to a tag before a branch or a remote. `git tag main 12-parked` in a repository with no remote, or `git tag origin/HEAD 12-parked` in one with a remote, makes the base `12-parked`'s own tip. The scan then reads the branch as shipped and skips it, so the gate prints `{}` and exits 0.
  - **The by-hand checker** (found here): `assets/check-unreviewed-work.sh:55` defaults to `rev-parse --abbrev-ref HEAD`, which on a tag-shadowed branch prints `branch 'heads/12-parked' carries no spec … nothing else examined` and exits 0. `:63` resolves a branch argument given without a commit by bare name, so a tag at another commit is read in the branch's place, with the same sentence. CI passes both arguments from the pull-request event and is unaffected.
  - **The digest** (found here): `hooks/steering-digest.sh:41` tells a session on a tag-shadowed branch "The active branch heads/12-parked has no spec directory under .specs/." This is context rather than a gate, but it denies a spec that exists, at the start of the session that is about to implement it.

- Impact: no damage is needed, only one ordinary command, and a tag named like a release branch is a common habit. Under `- Owns: gates never fail open` a gate that passes silently is a BLOCKER (G-1). The base variant is narrower, since someone has to tag a commit `main` or `origin/HEAD`, but it fails open the same way.

- **Root cause:** every one of these reads hands git a **short** name and trusts git to resolve it to the branch. A short name is a request for disambiguation, and git's order (`refs/<name>`, then `refs/tags/`, then `refs/heads/`, then `refs/remotes/`) puts tags ahead of branches. Going the other way, git shortens only as far as stays unambiguous, so a shadowed branch comes back longer. The gate treats the short name as a slug in one direction and as a ref in the other. Both assume that branch names and tag names never collide. A branch's full refname is the only name that cannot collide.

- Acceptance criteria:
  - [ ] **AC1:** WHEN another ref shadows the name of a branch holding finished, unreviewed work (a tag of the same name, or `refs/remotes/origin/HEAD` beside a branch named `origin`), THE review gate SHALL block from another branch and name that branch by its own name, never `heads/<name>`.
  - [ ] **AC2:** WHEN HEAD is on that tag-shadowed branch, THE review gate SHALL block with the current-branch message it gives an unshadowed branch in that state.
  - [ ] **AC3:** WHEN a tag named for a base candidate (`main` with no remote; `origin/HEAD` with one) points at an unreviewed branch's tip, THE review gate SHALL still block on that branch.
  - [ ] **AC4:** WHEN `check-unreviewed-work.sh` is run by hand on a tag-shadowed branch, with no arguments or with the branch name alone, THE checker SHALL check that branch's own spec at the branch's own tip and fail.
  - [ ] **AC5:** WHEN a session starts on a tag-shadowed branch, THE steering digest SHALL name the branch `12-parked` and report its spec.
  - [ ] **AC6:** every name that is not ambiguous keeps its slug byte for byte. The cases for a detached HEAD (77) and an unborn branch (171–175) keep their verdict. The issue counts on existing cases for slashed names and linked worktrees, but none exists, so this spec adds both as pins that pass before and after.
  - [ ] **AC7:** each new case fails against `7ef35ab`'s `hooks/` and `assets/` and passes after the fix, and every existing case keeps its verdict.

- Out of scope:
  - #191, the scan's `_gate_read` reading an unavailable object as an absent spec. Same function, different fault, and it is the next issue in row 1.
  - #178's `:219`/`:221` (now `:259`/`:261`): `for-each-ref` exiting 0 over a broken ref, and `|| continue` on an unresolvable tip. This fix rewrites both lines' naming and leaves their failure handling as it is.
  - HEAD pointed outside `refs/heads/` with `git symbolic-ref HEAD refs/tags/<x>`. It is plumbing-only, and the gate reads it as detached (Design).

### Clarifications

Asked and answered 2026-10-04.

- **Q1. The issue names the gate's two naming sites, and the measurement found the same short-name read in three more. Does this spec take all of them?** Yes, all four. One root cause, one idiom, and leaving a sibling on a short name leaves the class open. → AC3, AC4, AC5.
- **Not asked, because the code answers it:** CI's call to `check-unreviewed-work.sh` passes both arguments from the event, so the checker's fix only reaches its by-hand paths. And the version bump is a patch: shipped `hooks/` and `assets/` change and the flow does not move, like #228 (0.21.7).

## 2. Design (HOW)

- **Fix approach.** Hand git only full refnames, and resolve them exactly. That takes two helpers in `hooks/gate-lib.sh`, because each question has more than one caller, and a copy per caller is #14 and #23:
  1. `gate_head_branch`. It reads `git symbolic-ref -q HEAD`. When that exits 0 and the ref starts with `refs/heads/`, it prints the ref with `refs/heads/` stripped and returns 0, for a born or an unborn branch. When it exits 1 (detached), or exits 0 with a ref outside `refs/heads/` (a plumbing-only `git symbolic-ref HEAD refs/tags/<x>`), it prints nothing and returns 1, which is the detached answer. Any other status is returned as git's own (128 for a ref store git cannot read). The statuses and their meanings are #228's, so `review-gate.sh`'s `case` keeps its three arms and their messages.
  2. `gate_ref_commit <full refname>`. It runs `git show-ref --verify -q` and then `git rev-parse --verify -q '<ref>^{commit}'`. The first half makes it exact. A full refname is still disambiguated: with no `main` branch, `rev-parse refs/heads/main` resolves a tag literally named `refs/heads/main` (measured), while `show-ref --verify` matches only that exact ref. It also follows a symbolic ref, so `refs/remotes/origin/HEAD` resolves.
  - **`review-gate.sh`.** Line 83 calls `gate_head_branch`. The base chain asks `gate_ref_commit` for `refs/remotes/origin/HEAD`, `refs/remotes/origin/main`, `refs/remotes/origin/master`, `refs/heads/main` and `refs/heads/master`, in today's order. The scan lists `%(refname)` and takes `slug=${ref#refs/heads/}`. It skips on `slug = branch` (no branch can be named `HEAD`, which git refuses, so a detached HEAD skips nothing), reads the tip and both files through `$ref`, which `for-each-ref` just listed and so names an existing ref exactly, and reports and passes `$slug` wherever a name or a path is meant. Two comments are rewritten: the one at `:77–82`, whose "shortened the way `rev-parse --abbrev-ref` shortens it" is false for `origin`, and the one at `:282–284`, which still names `rev-parse --abbrev-ref` as the source of the detached literal.
  - **`check-unreviewed-work.sh`.** The no-argument default calls `gate_head_branch`, and a branch given without a commit resolves through `gate_ref_commit refs/heads/<branch>`. No skew guard is added for the two helpers. Both calls are by-hand only, and against an older library each comes back empty, which reaches the existing exit-1 messages ("no branch name available", "cannot resolve a commit"). A guard would add a new failure to CI, which passes both arguments and never calls either helper.
  - **`steering-digest.sh`.** Line 41 calls `gate_head_branch`, and status 1 still prints the literal `HEAD`, so a detached session's line does not change. The degraded-library guard at its top checks `gate_head_branch` too, the way it checks `gate_steering_value` for #34.
  - **Narrower,** stripping a leading `heads/` from the short form. That repairs the slug and leaves every read a short name, so a tag still wins `rev-parse`; the base variant is exactly that. **Wider,** a general ref-resolution layer for every git call in the hooks. Every other call already reads `HEAD`, a sha, or a path.

- **Affected files:** `hooks/gate-lib.sh`, `hooks/review-gate.sh`, `hooks/steering-digest.sh`, `assets/check-unreviewed-work.sh`, `scripts/test-gates.sh`. Shipped, so `implement`'s version step bumps the patch.

- **Blast radius:**
  - **Slugs.** `${ref#refs/heads/}` equals `%(refname:short)` and `symbolic-ref --short` exactly when git did not lengthen them, which is whenever the name is not ambiguous. The five pins in AC6 hold the plain, slashed, linked-worktree, detached and unborn shapes.
  - **The base.** When the exact ref exists and nothing shadows it, the full name resolves to the commit the bare name did. Two shapes now resolve differently, and both in the safe direction. A shadowing tag is no longer taken, which is the fix. A base that existed only under another rule, such as a remote named `main` with no `main` branch, is no longer found: the base comes back empty, and the scan names every branch with the existing no-base note.
  - **Callers.** The CI path of `check-unreviewed-work.sh` is unchanged, since both arguments come from the event. The digest now names an unborn branch instead of printing `HEAD`. `quality-gate.sh` and the Antigravity digest wrapper read no branch. `gate_spec_review_state`'s third argument is now a full ref from the scan, `HEAD` from the current branch, or a sha from CI, and `_gate_read` treats all three the same.

- **Why this cannot recur:** a case for each site, plus a needle case. The needle fails if a non-comment line of `hooks/*.sh` or `assets/check-unreviewed-work.sh` contains `refname:short`, `--abbrev-ref` or `symbolic-ref` with `--short`. Measured at `7ef35ab`, those non-comment lines are exactly the four sites this spec rewrites. The needle skips comments, which cite the old commands as history, and `rev-parse --short <sha>`, which abbreviates a commit rather than naming a ref. That makes it a check on the class rather than the instance: the next short-name read goes red before it ships.

## 3. Tasks (TDD-ordered)
> One task is one complete Red-Green-Refactor cycle, so one green commit. No task is sequenced after the review.
- [x] T1: cases for AC1 (a tag, and `origin` beside `origin/HEAD`, each scanned from `main`) and AC2, all red against `7ef35ab`, plus AC6's slashed-name and linked-worktree pins, green before and after. Then `gate_head_branch` and the naming half of `review-gate.sh` (line 83, the scan) → green.
- [x] T2: cases for AC3 (a tag `main` with no remote, a tag `origin/HEAD` with one, both red), plus a pin for a tag literally named `refs/heads/main` in a repository without a `main` branch, which is green before and must stay green. Then `gate_ref_commit` and the base chain → green.
- [ ] T3: cases for AC4 (no arguments on a shadowed branch; the branch name alone, with a tag at another commit), both red. Then `check-unreviewed-work.sh` → green.
- [ ] T4: cases for AC5 (a shadowed branch, and an unborn one, which is named rather than printed as `HEAD`), both red. Then `steering-digest.sh` and its guard → green.
- [ ] T5: the needle case and the two comments. Full suite green.
