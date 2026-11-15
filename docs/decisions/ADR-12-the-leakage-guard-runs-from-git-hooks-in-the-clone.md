# ADR-12: The leakage guard runs from git hooks in the clone
- Status: accepted
- Date: 2026-11-15; #360

## Context
`scripts/check-leakage.sh` scanned the working tree, at turn end and in CI. Four things a repository publishes are never in the tree at the tip: a commit message, a file one commit adds and a later one removes, a branch name and a tag name. CI sees a commit after it is pushed, and this repository is public, so by then the text is published; a ref name is public on arrival and CI never reads it.

M-1 in `docs/CONTRACT.md` is that no private context reaches the repository. For this rule a check that runs after publication reports the leak and prevents nothing. The only point before publication is the machine the commit is made on.

ADR-5 considered a `pre-push` hook for the version bump and rejected it for two reasons: it is "outside both harnesses' hook models", and it is "installed per clone rather than per project".

## Decision
The guard gains four inputs beside the working tree, staged changes, text on standard input, a set of commits and a list of ref names, and three git hooks run them: `commit-msg`, `pre-commit` and `pre-push`. `scripts/install-git-hooks.sh` installs a shim under each name in the clone's common hooks directory, with a snapshot of the guard and the hook scripts beside it. CI's leakage step scans a pull request's commits, branch name, title and body, and a push's commits, as the backstop.

ADR-5 stands. Its two objections are answered here for this check, not withdrawn for the bump:

- **Installed per clone.** A hook that is not installed is silent, which is the defect this repository exists to refuse. So the working-tree scan, the first entry on the `- Validators:` line, fails in a clone whose hooks are missing, cannot run, were edited or are older than its checkout's, and names the installer. The absence cannot outlive one turn end or one contributor's run. The bump check had no such carrier and did not need one, because CI is early enough for it.
- **Outside both harnesses' hook models.** Nothing here ships: the hooks are this repository's own, under `scripts/`, and no project that installs the plugin receives them. A harness hook also sees only what a session does. A commit typed in a terminal, and one made by `rebase` or `cherry-pick`, pass no harness hook, and the leak this guards against is as likely from either.

Why CI is too late here and was not for the bump: an unbumped change that reaches a pull request has harmed nothing, and the check blocks the merge. A private word that reaches a pull request is already public, in the commit, in the branch name and in the pull request's own text.

What the hooks read is settled by measurement, on git 2.54.0 on 2026-11-15:

- Every git call is `git --no-replace-objects -c core.quotePath=false`, and every diff takes `--no-color --no-ext-diff --no-textconv --no-relative`. `color.ui=always`, a `textconv` filter, `diff.relative` and a `refs/replace/` entry each made an unpinned scan report clean over a commit that added the word, and `log.diffMerges=off` hid a line only a merge added.
- The `pre-push` hook asks the destination what it holds with `git ls-remote` on the URL git is pushing to. The remote-tracking refs hid unpublished commits when a remote's push URL differed from its fetch URL, and after the destination's history was rewritten they hid the whole old history.
- No git command feeds a pipe. `git log … | grep -q … && exit 1` exits 0 when git dies.
- A shim does not use `core.hooksPath`. A relative path resolves in each worktree, and a worktree whose branch has no such directory commits with no hook and no warning.

## Consequences
- Every commit in this clone takes about 0.15 s longer: 0.18 s against 0.03 s for a one-file commit. A clean push of 199 commits took 1.78 s against 0.27 s, to a destination on the same disk; against GitHub the push also pays one `git ls-remote`, measured at 2.0 s. Both are inside #360's AC10. A push that holds a hit takes longer, because each commit that hit is read again for a location: 6 s for four hits among 277 commits.
- A clone without a pattern file cannot commit once the hooks are installed: the guard fails closed without its list, in a hook as at turn end. `CONTRIBUTING.md` says what a contributor without private context writes in one.
- After this repository's history is rewritten, a push from a branch still on the old history is refused whole, because the destination no longer holds those commits. That is the check working. Each such branch is rebuilt on the new history first.
- `--no-verify`, `git -c core.hooksPath=…` and a clone that never ran the guard skip the hooks in silence. CI then reports the commits and the pull request's text after they are public. Nothing reports a branch or tag name pushed that way.
- The snapshot beside the shims is a copy, refreshed only when the installer runs. It serves worktrees whose branch holds no hook scripts, and the version check covers the shims, not the snapshot.
- The suite's hook cases run real `git commit` and `git push`. The whole suite took 288 s with them, against 276 s before, inside the 336 s `- Validator budget:`.
- Tracker text written with `gh` is not covered. #361 holds it.

## Alternatives considered
- **CI only** — reports after publication, and never reads a ref name. It stays as the backstop, not the gate.
- **`core.hooksPath` pointing at a tracked directory** — one setting instead of copied shims, but it resolves per worktree and fails open on a branch that predates the directory, with no warning. An absolute path would name one checkout and run another session's uncommitted edits.
- **A harness tool hook on `git commit` and `git push`** — sees only what a session runs, exists on one of the two harnesses in a form that can deny a command, and parses a command line where a git hook is handed the commit itself. #361 uses one for `gh`, where git offers no hook.
- **Falling back to the main checkout's scripts** for a worktree whose branch has none — refuses every commit in such a worktree until that checkout is updated, and reads a working tree another session may be editing.
- **Scanning author and committer identities** — declined by the maintainer on 2026-11-13: the names in commit metadata stay, and a pattern that matched the maintainer's own identity would refuse every commit.
