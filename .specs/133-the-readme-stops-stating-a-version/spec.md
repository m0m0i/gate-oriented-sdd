# Spec: the README stops stating a version
- Slug: 133-the-readme-stops-stating-a-version   Issue: 133   Type: bug   Status: approved
- Author: Hiroyuki   Date: 2026-09-19

## 1. Requirements (WHAT / WHY)
- Reproduction: bump both manifests as `implement` step 5, commit, open the PR. The bump commit touches only paths outside `- Source globs:`, so `quality-gate.sh` runs no validators on that turn, and `README.md` and `README.ja.md` still state the previous version until someone edits them by hand.
- Expected: the version a reader sees in the README is the version in `plugin.json`, with no step anyone can forget.
- Actual: the READMEs assert the version independently, the turn that changes the manifest cannot run the guard that would catch the disagreement, and the failure surfaces at the PR — one step after the mistake, and only because CI runs the guard unconditionally.
- Impact: it has escaped twice. On #115 `v0.4.3` survived three releases and an edit to the same file before anyone noticed, silently, because no guard existed. On #141 / PR #148 it was caught by CI rather than locally, exactly as this issue predicted, and cost a round trip on a merged-ready branch. Every release pays a hand edit in two files, and #115's detection made the cost visible without removing it.
- **Root cause:** the README asserts a fact the manifest already holds, so two sources exist for one value and can disagree. #115 added detection and left the assertion in place; its Design's claim that the version became "derived rather than asserted" was false and is corrected on that spec. The second half is structural: the manifests sit outside `- Source globs:` by a deliberate decision on #14, so the one turn that changes the version is the one turn the local gate is guaranteed not to check.
- Acceptance criteria:
  - [ ] **AC1:** WHEN either README is rendered THE SYSTEM SHALL show the version read from `plugin.json` at view time, and neither file SHALL contain a version literal.
  - [ ] **AC2:** WHEN a README carries no version badge THE SYSTEM SHALL fail `check-readme-claims.py`, naming the file — a guard that stops covering this claim while still exiting 0 is the defect, not the fix.
  - [ ] **AC3:** WHEN a README's version badge is a static badge rather than one that reads `plugin.json` THE SYSTEM SHALL fail, because a static badge restores exactly the drift this change removes and its deletion reads as a simplification.
  - [ ] **AC4:** WHEN a version badge reads a source other than this repository's `plugin.json` THE SYSTEM SHALL fail, so a badge pointed at a fork or a stale path cannot report a version nobody ships.
  - [ ] **AC5:** WHEN a version literal in the form the old claim used reappears in either README THE SYSTEM SHALL fail, because two sources for one value is the root cause returning.
  - [ ] **AC6:** WHEN this change ships THE SYSTEM SHALL leave `check-readme-claims.py`'s other two subjects — the receipt counts and the no-behaviour-count rule — passing unchanged.
- Out of scope: `docs/verified.md`, which records what the harness was *tested against* rather than what it *is*, and is deliberately a different claim; `skills/implement/SKILL.md` step 5, which gains no clause under this approach and therefore owes no version bump of its own; #68, the adjacent gap where a bump proves a version moved and nothing proves a tag followed.

### Clarifications
2026-09-19, from `clarify`:

- **C1 — What does the badge claim, the manifest or the latest release?** The manifest, read from `plugin.json` on `main`. That is the only source that cannot drift from what the repository ships, which is the defect being fixed; a release-derived badge would decouple the claim from `plugin.json`, so a manifest that disagreed with its release would be hidden by the badge rather than caught by it. The cost is accepted and stated: between a merge and its tag the badge shows a version with no release yet. It is accurate about the manifest and slightly ahead of what is installable, and the `## Status` prose already says pre-release. A second, release-derived badge was considered — it would make a manifest/release mismatch visible, which is #68's gap — and declined here as #68's work, not this issue's.
- **C2 — Where does it go?** A badge row under the title, matching the convention the operator already uses on their other project. `## Status` keeps its prose — pre-release, the eval-suite sentence — with the number removed. Adding the remaining badges from that project (license, spec-driven) was offered and declined: it grows the diff past this issue.
- Not asked, because it is settled or mine: whether a third-party render path is acceptable — chosen with that cost stated before this spec existed; how strictly the guard parses the badge URL — an implementation decision this spec owes an answer to rather than a question; and whether `README.ja.md` carries the same badge — it does, with the same label, because the label is a name rather than prose and both READMEs must make the identical claim.

## 2. Design (HOW)
- Approach and key decisions:
  - **The badge replaces the literal; it does not sit beside it.** Two sources for one value is the root cause, so leaving the prose number in place and adding a badge would be the defect with better typography. The `## Status` sentence keeps everything that is not the number.
  - **The guard is repointed, never dropped.** `check-readme-claims.py` stops asking "does this number match the manifest" — a question that can no longer be wrong — and starts asking "is the badge still the thing that makes it unable to be wrong". That is the claim with a live failure mode: a later editor replaces the dynamic badge with a static one because it renders faster or reads cleaner, drift returns, and nothing says so. A guard that quietly stops covering a claim while still exiting 0 is precisely what `- Owns: gates never fail open` forbids.
  - **The guard verifies the badge's form, not its rendering.** It cannot know whether shields.io is reachable, and it must not try — a validator that makes a network call would fail on an aeroplane and teach the user to switch it off, which is LV-2. What it can check is that the URL still names this repository's `plugin.json` and still asks for `$.version`. The limit is stated here rather than discovered: a badge that renders as an error still passes this guard, and the failure is visible to any human who opens the page.
  - **The old literal becomes a prohibition.** The existing `VERSION` pattern is kept and inverted: it now fails when it matches. Without that, the number can be reintroduced by an editor who thinks the badge is decorative, and the two-source state returns with no complaint.
  - **No version bump.** `scripts/check-version-bump.py:31` lists `skills/`, `agents/`, `hooks/`, `assets/` and the two manifests as shipped; `README.md` and `scripts/` are in none of them. This is the route #133 predicted would avoid making the fix for a version-drift bug into a version bump of its own.
- Affected modules and files, per `.steering/structure.md`:
  - `README.md`, `README.ja.md` — the badge row under the title, the number out of `## Status`. Not shipped, not reviewable source; the identical claim in both.
  - `scripts/check-readme-claims.py` — CI guard. `VERSION` inverted to a prohibition, a `BADGE` check added in its place.
  - `scripts/test-gates.sh` — one case per new behaviour.
- Contract changes, and who else consumes them: none. No steering line, no hook, no skill and no manifest changes. `skills/implement/SKILL.md` step 5 is deliberately untouched — under this approach the bump step has nothing new to remember, which is the half #115 left open.
- Risks and trade-offs:
  - **A third-party render path for a fact about this repository.** Accepted before the spec, and the failure mode is honest: shields.io or `raw.githubusercontent.com` being unreachable shows a broken badge, never a wrong version. The repository's no-dependency rule is about what the plugin *runs*; nothing here is installed or executed.
  - **The badge reads `main`, so between a merge and its tag it is ahead of what is installable.** C1 accepted this; `## Status` still says pre-release in both languages.
  - **The guard's subject is now a URL, which is easy to get subtly wrong.** A pattern too strict fails on a harmless reordering of query parameters; too loose and a fork's URL passes. The check therefore parses the URL rather than matching the whole string literally, and the cases below assert both directions.

## 3. Tasks (TDD-ordered)
> One task is one complete Red-Green-Refactor cycle, so one green commit. No task is sequenced after the review.
- [x] T1: failing case — a README with no dynamic version badge fails naming the file, and one carrying it passes — then swap the literal check for the badge check in `check-readme-claims.py` and put the badge row in both READMEs with the number removed from `## Status` (AC1, AC2)
- [x] T2: failing case — a static shields badge in place of the dynamic one fails with a message naming that specific substitution, not the generic absence — then the distinguishing branch (AC3)
- [x] T3: failing case — a dynamic badge whose `url=` names another repository, another branch or a path that is not `plugin.json` fails, while a harmless reordering of the query parameters still passes — then parse the URL rather than match it whole (AC4)
- [ ] T4: failing case — a `**v<x.y.z>` literal reappearing in either README's prose fails, saying that the badge is the source and a second one is the bug returning — then invert the existing `VERSION` pattern into a prohibition (AC5)
