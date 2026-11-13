# Spec: the leakage guard holds no private literal, fails closed without its list, and never prints what it matched
- Slug: 357-the-leakage-guard-holds-no-private-literal   Issue: 357   Type: bug   Status: approved
- Author: m0m0i   Date: 2026-11-13

## 1. Requirements (WHAT / WHY)
- Reproduction, on `main` at `80ebb03`:
  1. Read `scripts/check-leakage.sh:22` and `:31`. The tier-1 and tier-3 lists are literals in a public repository.
  2. Plant a tier-2 hit in a tracked file and run the guard. It exits 1 and echoes the whole matching line (`:182-200`). Tier 3 echoes the same way on exit 0.
  3. Run the guard on the tree as it stands. It prints `clean` over `.work_logs/2026-10-12.md:112` and over two absolute local paths in `docs/verified.md`, because its lists do not hold those words.
  4. Give a tracked file a name that holds a tier-2 hit and keep its contents clean. It prints `clean`.
- Expected: no private context reaches the public repository (M-1 in `docs/CONTRACT.md`; `AGENTS.md:68` calls this the guard that matters most). That covers the guard's own source and its own output, and a list that is missing or incomplete must not read as a pass (`- Owns: gates never fail open`).
- Actual:
  - The guard publishes the private lists itself, in every commit since the first.
  - A hit is published again in the CI log, which is public for 90 days.
  - A word the lists do not hold passes, and the lists cannot be completed without publishing more.
  - A file's path is never scanned.
- Impact:
  - **Who:** every reader of the repository and of its CI logs.
  - **How often:** the lists, on every commit. The log, on every run that hits; one such log stood from 2026-09-05 until it was deleted on 2026-11-13.
  - **What it costs:** the names this guard exists to protect were public for 84 days. The tracker and that log were cleaned by hand on 2026-11-13. A rewrite of history to remove the earlier copies depends on this fix, because replacing the literals across history would break the guard at `HEAD` while the guard still holds them.
- **Root cause:** the script has no source for its lists other than its own text, so completing or even keeping them publishes them. It prints `grep -Hn` output because, when it was written, a reader was assumed to need the matching line; the line is the leak.
- Acceptance criteria:
  - [ ] **AC1:** `scripts/check-leakage.sh` holds no tier-1 or tier-3 pattern. It reads its private patterns from the file named by `GATE_SDD_LEAKAGE_PATTERNS`, else from `${XDG_CONFIG_HOME:-$HOME/.config}/gate-sdd/leakage-patterns`. The file has three kinds of pattern, one extended regular expression per line: fail, fail ignoring case, and warn ignoring case.
  - [ ] **AC2:** WHEN the pattern file is absent, unreadable, holds no fail pattern, holds a pattern outside any section, or holds an invalid expression, THE SYSTEM SHALL exit 1 and name the fault and the location it looked in. It never prints a pattern.
  - [ ] **AC3:** WHEN a file's contents match, THE SYSTEM SHALL report the tier, the file and the line numbers, and nothing else. WHEN a file's path matches, it reports the tier and the path's position in the listing, not the path. Neither stdout nor stderr holds the matched text or the pattern, on a fail or on a warning.
  - [ ] **AC4:** a fail match exits 1. A warn match prints a warning and does not change the exit status. With no match the guard exits 0 and says how many files it scanned and that the private patterns were loaded.
  - [ ] **AC5:** everything the guard already refuses stays refused: an empty work set, an unreadable file, a path git had to quote, a path with a space, a path beginning with `-`, and index entries with no working-tree file are counted. The existing leakage cases in `scripts/test-gates.sh` pass.
  - [ ] **AC6:** in CI the required guard job gives the script its patterns from a repository secret. On a push to `main` and on a pull request from this repository, a missing or empty secret fails the step.
  - [ ] **AC7:** the tree passes the guard under the owner's complete list. `.work_logs/2026-10-12.md:112` and the two local paths in `docs/verified.md` are reworded.
  - [ ] **AC8:** `CONTRIBUTING.md` says where the patterns live, what the file looks like, and what a contributor without private context does.
  - [ ] **AC9:** every new failure mode and both report shapes have a case in `scripts/test-gates.sh`, built on synthetic patterns only. Each new case fails on `main`.
  - [ ] **AC10:** the guard's run time on this tree stays within twice today's (0.52 s measured on 2026-11-13).
- Out of scope:
  - **Commit messages, ref names, a staged or pushed range, and tracker text.** The guard still reads the working tree only. A second issue covers them, with the checks at commit, push and issue-filing time.
  - **Rewriting history.** The owner's operation, after this merges.
  - **#57,** tier 2's collision with this repository's own ids.
  - **Moving the script to Python.**

### Clarifications
Asked and answered 2026-11-13.

- **Q1 — a machine with no pattern file?** **A:** the guard fails and says how to set one up. A contributor with no private context writes a file holding one pattern of their own. No switch passes without a file: any session could set it.
- **Q2 — a pull request from a fork, which gets no secrets?** **A:** CI runs the public tier only and prints that the private patterns were not run and that this is not a pass. A fork's author cannot know the private words.
- **Q3 — tier 2, the id shapes on `:27`?** **A:** it stays in the script as the public tier. It names nothing, and the existing cases plant it.

Decided rather than asked:
- **The work-log line is reworded,** against `.work_logs/README.md:7`'s append-only rule. The owner asked for the word removed on 2026-11-13, and the history rewrite changes that line in every commit anyway.
- **Paths are scanned as well as contents** (reproduction step 4). The listing is already in hand.
- **The public tier alone is a command-line flag, not an environment variable.** The `- Validators:` line and the hooks run the command as written, so a flag cannot be set from outside the repository's own files.
- **The guard stops excluding itself.** Its own text is then scanned under the owner's list, which is what keeps a literal from returning.

## 2. Design (HOW)
- **Fix approach.** The file-listing half of the script (`:36-178`) stays as it is. The pattern half is replaced.
  1. **The pattern file.** Sections `[fail]`, `[fail ignore-case]` and `[warn ignore-case]`, one extended regular expression per line; blank lines and lines starting with `#` are dropped, because an empty expression matches every line. The loader splits it into one file per section under a `mktemp -d` directory removed on exit, and tests each expression against empty input: a `grep` status above 1 is an invalid expression, reported by section and position.
  2. **The public tier.** `:27`'s expression stays in the script and is scanned as a fail tier on every run.
  3. **`--public-only`.** Runs the public tier alone, prints `check-leakage: PRIVATE PATTERNS NOT RUN (--public-only): not a pass for private context`, and exits by the public tier's result. Only `ci.yml` passes it, and only for a fork (step 6). Any other argument is refused.
  4. **The scan.** Per tier, one batched `xargs -0 grep -lE --null -f <tier file> --` over the scan list finds the files that hit, which keeps the run time (AC10). For each such file a second `grep -nE -f` gives the line numbers, cut to the number before the first `:`. The listing itself is piped to `grep -nE -f` for path hits, reported as positions in `git ls-files` order.
  5. **The report.** `LEAK [<tier>] <file> line(s): <n> <n>` or `LEAK [<tier>] path number(s) in the listing: <n>`, and `WARNING` in place of `LEAK` for the warn tier. Then the existing clean-room sentence, with one more: the matched text is withheld on purpose, open the location. The clean line becomes `check-leakage: clean — <n> file(s) scanned, private patterns loaded`.
  6. **CI.** The `Leakage guard` step takes the secret `LEAKAGE_PATTERNS` and the fork test through `env:`, never by interpolation into `run:`. For a fork it runs `--public-only`. Otherwise it writes the secret to a `mktemp` file and names it in `GATE_SDD_LEAKAGE_PATTERNS`; an unset secret gives an empty file, which AC2 already fails.
  7. **No `SELF`.** The exclusion at `:19` and `:52` goes. The public tier's own expression does not match itself, since `ADR-[0-9]{4}` holds no four digits.
- **Why not narrower:** hiding the lists behind a hash keeps them guessable, since the words are short and a salt in the tree is public. Withholding only the echo leaves the lists published.
- **Why not wider:** see Out of scope. A Python rewrite would rename a file five enumerations name.
- **Affected files:**
  - `scripts/check-leakage.sh`;
  - `scripts/test-gates.sh`, the leakage section: `run_leak` gives every existing case a synthetic pattern file and a `HOME` under `$TMP`, so no case reads the developer's own file;
  - `.github/workflows/ci.yml`, the one step;
  - `CONTRIBUTING.md`;
  - `.work_logs/2026-10-12.md:112`, `docs/verified.md:499` and `:501`;
  - the work log.
  Nothing shipped changes, so no version moves.
- **Blast radius:**
  - **Every turn end and every review on a machine with no pattern file blocks,** with the setup message. That includes a cloud session, which is already outside what the gates cover (#261).
  - **Every pull request after the merge needs the secret.** It is set before this branch is pushed, or this branch's own run fails.
  - **A branch cut before the merge** carries the old script and the old step, and passes as before until it is rebased.
  - **The suite's two fixtures that write a `- Validators:` line naming the guard** (`scripts/test-gates.sh:10963`, `:11033`) only name it; they do not run it.
- **Why this cannot recur:**
  - The script has nowhere to hold a private word, and it scans itself.
  - No report carries text, so a hit in CI publishes a location.
  - Completing the list costs an edit to a file outside the repository.

## 3. Tasks (TDD-ordered)
> One task is one complete Red-Green-Refactor cycle, so one green commit. No task is sequenced after the review.
- [ ] **T1:** the loader (AC1, AC2, AC5, AC7). Cases after `leak_repo` and `run_leak`: each of AC2's five faults exits 1, names the fault and the location, and prints no pattern; the default path is found through `HOME` and through `XDG_CONFIG_HOME`; the existing cases pass under a synthetic file. Then Design steps 1 and 2, the literals removed, and the three lines reworded so the guard passes under the owner's list.
- [ ] **T2:** the report (AC3, AC4, AC10). Cases: a content hit in each tier gives the tier, the file and the line numbers, and neither stream holds the planted text or the pattern; a path hit gives a position and not the path; a warn hit leaves the status at 0; a pattern planted in the fixture's copy of the guard itself is caught. Then Design steps 4, 5 and 7, and the timing recorded in the commit.
- [ ] **T3:** the public tier alone, and CI (AC6). Cases: `--public-only` with no pattern file prints the notice, passes a clean tree and fails a public-tier hit; an unknown argument is refused; an empty pattern file fails, which is CI's unset secret. Then Design steps 3 and 6.
- [ ] **T4:** `CONTRIBUTING.md` (AC8): where the file lives, its three sections with a synthetic example, the fork rule, and what a contributor without private context writes.
