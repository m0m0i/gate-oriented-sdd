# Spec: init and the checker disagree on a template's filename
- Slug: 130-init-and-the-checker-disagree-on-a-filename   Issue: 130   Type: bug   Status: draft
- Author: Claude Opus 5   Date: 2026-09-13

## 1. Requirements (WHAT / WHY)

- Reproduction: run `init` against a project that already carries a bug template under another
  name — `.github/ISSUE_TEMPLATE/bug_report.md` — then run `./scripts/check-document-set.py`.
  Observed 2026-09-12 while reviewing #126; the run itself never surfaced it, because #127's
  `docs.is_dir()` failure came first.
- Expected: after `init`, the checker `init` places on the `- Validators:` line two bullets
  later passes.
- Actual: two bullets of the same step contradict each other. The issue-templates bullet
  (`skills/init/SKILL.md:58`) says *"If templates already exist, **merge rather than replace**:
  keep their wording and their labels, and add only the missing types."* On that project `bug`
  is **not** a missing type, so `bug.md` is never written — and
  `assets/check-document-set.py:54` requires `TEMPLATES = ("feature.md", "bug.md", "chore.md")`
  by literal filename, in every mode. Following step 3 correctly produces a project whose gate
  fails on a file step 3 told the installer not to create.
- Impact: every install onto a project that already has issue templates under its own names —
  which is the migration case `init` calls *the common case*. With #127 fixed, this is now the
  **first** thing such a project hits rather than the second.
- **Root cause:** the checker identifies a template by **filename**; `init`'s merge rule
  identifies one by **type**. Nothing translates between them, and nothing records that
  `bug_report.md` *is* this project's bug template. It is the same missing seam as #128, where
  the untranslated pair is label→type rather than type→filename.
- Acceptance criteria:
  - [ ] **AC1:** WHEN `init` completes on a project that already carried a bug template under a
        non-canonical name THEN `check-document-set.py` exits 0 on the resulting tree.
  - [ ] **AC2:** the regression test fails before the fix and passes after.
  - [ ] **AC3:** WHEN a type has no template at all THEN the checker still exits non-zero and
        names the missing type — the fix must not become "templates are no longer checked".
  - [ ] **AC4:** the project's own wording and labels survive. `init`'s bullet exists because
        *an existing template encodes decisions the team already made*, and that reason is not
        weakened by this fix.
  - [ ] **AC5:** the issue picker offers **one** template per type. Two bug templates is its own
        defect and must not be the price of this one.
  - [ ] **AC6:** `init`'s two bullets agree with each other and with the checker, so a reader
        following step 3 literally cannot produce a red gate.
- Out of scope:
  - **#128** — `spec` has no way to read an issue's *type* from a project's own labels. It is
    the same seam on the other axis and this spec must not claim to close it. Whether the fix
    here supplies what #128 needs is a clarify question, not an assumption.
  - **#83** — the three READMEs step 3 lists and ships no source for.

### Clarifications

- 2026-09-13 — **Does `init` change what it writes, or does the checker change what it looks
  for?** **Answered: `init` absorbs into the canonical name.** The merge bullet becomes a
  `git mv` of the project's `bug_report.md` to `bug.md`, keeping its body, front matter and
  labels untouched — one template per type, canonical filenames, the team's wording preserved.
  Self-contained: no new steering line and no dependency on #128. Rejected: *a declared
  `- Issue types:` line the checker reads* (elegant, but it couples this spec to #128 and makes
  it the larger of the two); *write the three canonical files alongside* (contradicts "keep
  their wording" and leaves two bug templates in the picker, which AC5 forbids); *infer the type
  from front matter* (it is inference, and #128's whole argument is that a project's taxonomy
  must be **declared** rather than guessed — the same reasoning that gave #110 a declared mode).
- 2026-09-13 — **How much of #128 should this spec absorb?** **Answered: the filename axis
  only.** One issue = one spec, and #128's real problem — a project's `labels: defect` meaning
  nothing to `spec` — is untouched by any choice above. Rejected: *both axes in one spec* (two
  issues on one branch, which the flow forbids, and it would need #128 closed as superseded).
- 2026-09-13 — **Version bump.** **Answered: 0.9.0, minor.** Precedent: #110's `- Mode:` line
  and #127's third value → minor; #109's prose → patch. `init` gains a behaviour it did not
  have — it renames a file in the user's repository — which is a change to what the installer
  does rather than to how it is described, and the flow argument wins when the two pull apart.
- Not asked, because `init`'s own rules settle it: **the rename is shown as a diff and agreed
  first.** Step 3's closing rules already say *"Never overwrite an existing `.steering/`,
  `.specs/`, or `AGENTS.md` without showing a diff and getting agreement"*, and renaming a file
  the project owns is the same class of act. **`git mv` rather than copy-and-delete**, so the
  template's history follows it.
