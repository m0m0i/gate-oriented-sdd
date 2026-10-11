# Spec: init step 3 lists three READMEs the plugin ships no source for
- Slug: 83-init-readme-sources   Issue: 83   Type: bug   Status: approved
- Author: m0m0i   Date: 2026-10-12

## 1. Requirements (WHAT / WHY)
- Reproduction: run `init` in a project. Step 3 of `skills/init/SKILL.md` lists `.specs/README.md`, `.specs/_archive/README.md` and `.work_logs/README.md` — "each stating its contract" — among the files to write. Look for their source in the plugin: `assets/` holds the check scripts and `issue-templates/`, `hooks/templates/` the hook wiring, and nothing else.
- Expected: step 3 copies the three from a source the plugin ships, as it copies the issue templates from `assets/issue-templates/`.
- Actual: `init` either invents the three or leaves the directories without a contract. On #76 (`docs/verified.md`, "Where do the three READMEs come from?") they were copied from this repository's own dogfood files, which a consumer does not have.
- Impact: every install. `.specs/README.md` is the only installed statement of the status lifecycle and of what the review gate reads in the directory; `.work_logs/README.md` the only one of append-only. Each install writes its own version or none, and #83 sits on the 1.0.0 critical path (`docs/BACKLOG.md` row 1) because the installed layout cannot be frozen while it does.
- **Root cause:** the three READMEs were written as dogfood files in this repository and named in `init` from there. `init` names its other sources by plugin path (`assets/issue-templates/`, `assets/check-*.{sh,py}`, `reviewers/`, `hooks/templates/`), and these three were never given one, so the bullet describes a destination with no origin. Nothing ties a file `init` tells a consumer to write to a file the plugin ships.
- Acceptance criteria:
  - [ ] **AC1:** The plugin ships `assets/directory-contracts/specs/README.md`, `assets/directory-contracts/specs/_archive/README.md` and `assets/directory-contracts/work_logs/README.md`, each byte-identical to this repository's `.specs/README.md`, `.specs/_archive/README.md` and `.work_logs/README.md` respectively.
  - [ ] **AC2:** `scripts/check-manifests.py` fails, naming the path, when any of the three sources is missing or differs from this repository's copy at the matching dotted path — failing on the tree before AC1's files exist, passing after.
  - [ ] **AC3:** WHEN `init` runs step 3, `skills/init/SKILL.md` tells it to copy each of the three from `assets/directory-contracts/` to the same path under the leading dot, and to treat one that already exists as the project's file; the Rules' list of files never changed without a diff names `.work_logs/` beside `.specs/`.
  - [ ] **AC4:** `docs/layout.md` shows the three READMEs in the project tree as written by `init`, and `assets/directory-contracts/` in the harness tree.
  - [ ] **AC5:** `docs/BACKLOG.md` cites #83 in neither row 1's Item cell nor the 1.0.0 line, and row 1's `Why here` records that it left by shipping, so `./scripts/check-backlog-tracker.py` stays clean after the merge closes it.
  - [ ] **AC6:** every command on the `- Validators:` line exits 0.
- Out of scope: a consumer-side check that the three READMEs exist (the issue's "nothing enforces" — it would block every existing install on a re-run's absence and is a decision for the document-set checker, not this fix); `docs/verified.md`'s #76 row, a dated observation that stays true of that run; rewording the READMEs themselves.

### Clarifications
- Q: Where do the sources live, and under what names? → A: `assets/directory-contracts/`, mirroring the destination with the leading dots dropped — `specs/README.md`, `specs/_archive/README.md`, `work_logs/README.md` — so the mapping is read off the path and no glob for `.specs/` from the plugin root finds them.
- Q: Does this repository's dogfood copy stay a copy, or become a symlink like `rules/AGENTS.md`? → A: a copy, held identical by `check-manifests.py`, the same check that holds `rules/AGENTS.md` to `AGENTS.md`. A copy is what a consumer has, so the dogfood stays a normal install here and `AGENTS.md`'s list of the two things deliberately unlike one does not grow.
- Q: Version size? → A: minor, 0.28.0 → 0.29.0. `init` step 3 now copies files it did not, which moves the flow; #130's one-bullet absorb went to 0.9.0 on the same argument. The bump is a step of `implement` after the receipt, not a task.

## 2. Design (HOW)
- Fix approach, and why this rather than the narrower or wider fix: copy the three dogfood READMEs into `assets/directory-contracts/`, name that directory as the source in `init` step 3, and add an identity check beside the `rules/AGENTS.md` one in `check-manifests.py`. Narrower — shipping the files with no check — leaves the dogfood and the shipped copies free to drift, so a consumer gets a contract this repository no longer holds itself to. Wider — a consumer-side check for the READMEs — is the out-of-scope item above.
- Affected files: `assets/directory-contracts/{specs,specs/_archive,work_logs}/README.md` (new), `scripts/check-manifests.py`, `skills/init/SKILL.md`, `docs/layout.md`, `docs/BACKLOG.md`.
- **Blast radius:** `assets/` ships wholesale (`scripts/package-release.py`'s `assets` component), so the new files reach the release with no list to edit. `assets/**/*.md` is already in `- Source globs:`. The CI `lint` job globs `assets/*.py` and `assets/*.sh` only, so Markdown under a subdirectory does not touch #206's latent gap. `check-document-set.py` already treats `.specs/README.md` and `.specs/_archive/` as no spec (`test-gates.sh` bootstrap cases), so a consumer's installed READMEs do not expire `bootstrap`. Neither harness scans `assets/`, so nothing registers.
- Why this cannot recur: the check fails whenever a source is missing or the dogfood copy differs, so the shipped contract cannot silently fall behind the one this repository runs; the class beyond these three — any file `init` names with no plugin source — is the reviewer's to judge.

## 3. Tasks (TDD-ordered)
> One task is one complete Red-Green-Refactor cycle, so one green commit. No task is sequenced after the review.
- [ ] T1: identity check in `check-manifests.py`, run red on the tree without the sources, then the three sources — green (AC1, AC2)
- [ ] T2: `init` step 3 and its Rules line, `docs/layout.md`, `docs/BACKLOG.md` row 1 (AC3, AC4, AC5), every validator green (AC6)
