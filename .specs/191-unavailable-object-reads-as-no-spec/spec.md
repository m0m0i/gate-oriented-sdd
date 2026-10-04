# Spec: an object git cannot get reads as a spec that is not there
- Slug: 191-unavailable-object-reads-as-no-spec   Issue: 191   Type: bug   Status: approved
- Author: m0m0i   Date: 2026-10-04

## 1. Requirements (WHAT / WHY)

- Reproduction: measured at `dbf51df` (git 2.54.0, macOS `sh`). `12-parked` holds a finished spec and no receipt, so the gate blocks from `main` and names it (case 76). Move the spec blob's loose object out of `.git/objects/`, and `sh hooks/review-gate.sh` prints `{}` and exits 0. The issue's fixture reaches the same state with no damage: a `--filter=blob:none` clone, `git branch 12-parked origin/12-parked`, and `origin` re-pointed at a path that does not exist.

- Expected: the issue's. A tree that does not name the path is silence. A tree that names it, whose object git cannot get, is a branch the gate did not look at, and the gate says so.

- Actual: one test, `git cat-file -e <ref>:<path> 2>/dev/null`, whose non-zero status each site reads as "no spec".
  - **The current-branch fallback** (the issue): `hooks/review-gate.sh:171`, `|| return 0`. Standing on `12-parked` with the spec out of the working tree, the gate prints `{}` and exits 0.
  - **The library** (the triage): `_gate_read`, `hooks/gate-lib.sh:172`, `|| return 1`. The scan from `main` prints `{}` and exits 0. The receipt is read through the same line, so an unavailable receipt reads as `no-receipt`. That one blocks, with a remedy for a receipt nobody wrote.
  - **The by-hand and CI checker** (found here): `assets/check-unreviewed-work.sh:96` carries its own copy of the test in front of the library call. It prints "carries no spec … nothing else examined" and exits 0. The triage's "reads through the same function" is true only of the lines after this one.
  - **An unreadable tree** (found here): the same flattening one level up. With the `.specs` tree object removed, `cat-file -e` exits 128 and all three sites read it as absent.

- Impact: the triage's, narrowed by measurement. A blobless clone makes one local branch, and the scan reads `refs/heads/` only, so the state needs a local branch whose spec blob was never fetched: one made without a checkout (`git branch x origin/x`, `git fetch origin x:x`), or one checked out under a sparse checkout that excludes `.specs/`. A branch checked out once in full has its blobs and blocks offline as it should. Not "every branch except the checked-out one". Still an ordinary clone mode and no damage, and under `- Owns: gates never fail open` a silent pass is a BLOCKER (G-1).

- **Root cause:** `git cat-file -e <ref>:<path>` asks two questions, whether the tree names the path and whether the named object is here, and answers both with one non-zero status. Each site wanted only the first. `_gate_read` already had the vocabulary for the second (1 absent, 2 unreadable, #39's), and the test in front of it could not say 2.

- Acceptance criteria:
  - [ ] **AC1:** WHEN a branch's tree names its spec and git cannot get that object, THE review gate's scan SHALL block from another branch, name the branch, and say its spec cannot be read and why.
  - [ ] **AC2:** WHEN HEAD is on that branch and the spec is not in the working tree, THE review gate SHALL block in the second person, and the remedy SHALL be one for an object git cannot get (reconnect and fetch, or check the repository), not a file mode.
  - [ ] **AC3:** WHEN `check-unreviewed-work.sh` is asked about that branch, THE checker SHALL exit 1 and say the spec cannot be read, never "carries no spec".
  - [ ] **AC4:** WHEN the spec is readable and the receipt's object is not, THE gate SHALL say the receipt cannot be read, not that none exists.
  - [ ] **AC5:** WHEN a tree on the way to the spec cannot be read, THE scan, the current-branch fallback and the checker SHALL each block or fail rather than read the spec as absent.
  - [ ] **AC6:** the issue's regression risk, as pins that are green before and after: a fresh blobless clone, offline, on its default branch stays silent; a blobless clone whose parked branch has its blobs blocks with the ordinary no-receipt sentence. A branch with no spec in either tree (case 148), an unborn branch (171–173) and a detached HEAD (77) keep their verdicts.
  - [ ] **AC7:** each new case that is not a pin fails against `dbf51df`'s `hooks/` and `assets/` for its stated reason and passes after. Every existing case keeps its verdict.
  - [ ] **AC8:** WHEN the gate or the checker runs against a `gate-lib.sh` that predates the new reader, IT SHALL block or fail with the re-copy remedy.

- Out of scope:
  - `gate_work_reached_base`'s step 1 (`hooks/gate-lib.sh:304–305`), the same test. Its failure leaves the skip unfired, which is the safe direction, and it is #182's function.
  - #178 (the scan's `|| continue` on a tip that does not resolve), #176 (no default arm on the `case`) and #232.
  - Reading git's stderr. Exit statuses and stdout only, so the issue's stated risk, a match loose enough to block every fresh clone, has nothing to be loose about.
  - The checker's failure footer, which says "carries finished work that no review covers" under every state. Under an unreadable spec that is not known; the line above the footer says which state it is.

### Clarifications

Asked and answered 2026-10-04.

- **Q1. The measurement found a third copy of the test, in `check-unreviewed-work.sh`. Does this spec take it?** Yes. Same root cause, and the same reader answers it. → AC3.
- **Q2. The triage's replacement, `git rev-parse --verify -q <ref>:<path>`, exits 1 with empty stderr when a tree object on the way to the spec is gone, the same as for an absent path. Does this spec close the unreadable-tree case too?** Yes, by building the reader on `git ls-tree`, which exits non-zero there. → AC5.
- **Not asked, because the code answers it:** the version bump is a patch, since shipped `hooks/` and `assets/` change and the flow does not move, like #233 (0.21.8).

## 2. Design (HOW)

- **Fix approach.** One reader for the tree's half of the question, and the three sites ask it.
  - **`gate_tree_names <ref> <path>`** in `hooks/gate-lib.sh`, on `git ls-tree --full-tree <ref> -- <path>`. It returns 0 when the tree names the path, 1 when the tree was read and does not, and 2 when git could not read the tree (any non-zero status from `ls-tree`). Measured: it reads trees only, so it answers offline in a blobless clone with no fetch; a removed tree object exits 1 or 128, and a treeless clone offline exits 128. `--full-tree` because without it the path is relative to the working directory. A ref with no commit is 2, which is the caller's to rule out.
  - **`_gate_read`'s ref branch** returns the reader's 1 or 2, then reads with `git show` as it does today, where a failure is already 2. Any status that is not the reader's own is a 2 as well: `gate_spec_review_state` reads whatever is neither 1 nor 2 as a file it read, which T3 found when a fixture took the reader out of the library (case 200).
  - **`review-gate.sh`'s fallback** resolves `head` first (the line moves up from below it) and returns for an unborn branch, which has no commit and so no tree; `ls-tree` exits 128 there, and cases 171 and 172 pin the silence. Then it returns only on 1. On 0 or 2 it sets `tree=HEAD` and goes on, so the shipped-work skip still runs first, and `gate_spec_review_state` says which state it is.
  - **`check-unreviewed-work.sh:96`** prints "carries no spec" only on 1, and otherwise asks the library as it does today. It also fails with the re-copy remedy when the library lacks the reader. #233 argued against a guard for its two readers because both sat on by-hand paths. This one sits on CI's path, where an older library would print "holds no finished, unreviewed work" for a branch with no spec, a sentence that claims a check.
  - **`review-gate.sh`'s skew guard** gains the reader's name. Its sentence names what #233's two readers do, so it is reworded to hold for three.
  - **Messages.** `$corrupt` goes. It was a correction appended to a file-mode remedy, written when only damage could reach it and no fixture could. An ordinary environment reaches it now, so the two unreadable arms each get their own sentence when the read came from the branch's tree: git could not get the object, a partial clone that cannot reach its remote or a damaged object store, reconnect and fetch or check the repository. The working-tree sentences stay character for character. `gate_review_state_sentence`'s two unreadable sentences, which only ref readers call, name the same cause.
  - **Narrower,** the triage's `rev-parse`, which is blind to a tree it cannot read (Q2). **Narrower still,** matching stderr, which is the issue's own risk. **Wider,** a new state name for "unavailable". Every consumer's `case` would need its arm, and `check_current_branch`'s has no default (#176), so a gate older than the library would pass on it. `unreadable` is already the word for "there, and could not be read".

- **Affected files:** `hooks/gate-lib.sh`, `hooks/review-gate.sh`, `assets/check-unreviewed-work.sh`, `scripts/test-gates.sh`. Shipped, so `implement`'s version step bumps the patch.

- **Blast radius:**
  - **A full, healthy clone.** Every object is present, so "the tree names it" and "`cat-file -e` succeeds" are the same answer, and every existing case keeps its verdict.
  - **A partial clone, online.** `git show` makes the lazy fetch `cat-file -e` used to make. One fetch, same answer.
  - **A partial clone, offline.** A local branch whose spec blob was never fetched now blocks (AC1). That includes a shipped, undeleted branch in that state when `gate_work_reached_base` cannot answer offline either. Louder, which case 141 already says is allowed where quieter is not.
  - **A fresh clone of any kind.** Its one local branch is the base, which the scan skips, and it has no `.specs/<default branch>/`, which is a 1. AC6 pins the blobless one.
  - **Callers.** `_gate_read` receives a full ref from the scan, `HEAD` from the current branch and a sha from CI, and `ls-tree` takes all three. CI's path through the checker is online and unchanged; a pull request with no spec still exits 0 with the same sentence.
  - **Skew.** A new library under an older gate fixes the scan and leaves that gate's own line as it was. A new gate or checker over an older library is AC8.

- **Why this cannot recur:** the three sites no longer carry the test, and a needle case holds that. Outside whole-line comments, `cat-file -e` may appear in `hooks/*.sh` and `assets/*.sh` only on `gate_work_reached_base`'s two lines, which are out of scope above. Measured at `dbf51df`, the needle finds five lines: those two and the three sites. The next existence test that asks the object when it means the tree goes red before it ships.

## 3. Tasks (TDD-ordered)
> One task is one complete Red-Green-Refactor cycle, so one green commit. No task is sequenced after the review.
- [x] T1: the library. Cases for AC1 (a removed blob, and the issue's offline blobless clone), AC4 and AC5's scan half, red against `dbf51df`; AC6's two blobless pins, green before and after. Then `gate_tree_names`, `_gate_read` and the two sentences → green.
- [x] T2: the gate. Cases for AC2, AC5's current-branch half and AC8's gate half, red. Then the fallback, the two tree-read sentences and the skew guard → green.
- [x] T3: the checker. Cases for AC3, AC5's checker half and AC8's checker half, red. Then `check-unreviewed-work.sh` → green.
- [ ] T4: the needle case, and the comments this change made false (case 146's "not pinned" note, the fallback's own). Full suite green.
