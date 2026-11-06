# ADR-11: A re-run tells a shipped text from an edit by a table of every text
- Status: accepted
- Date: 2026-11-04; #343

## Context
On Antigravity a plugin-shipped hook runs with the plugin directory as its working directory (A12), so `init` copies the gates, the runner and the harness checks into `.agents/hooks/` and renders `.agents/hooks.json` from a template (ADR-8, ADR-10). A fix reaches such an install only when `init` runs again. Nothing defined that re-run. `init` said "diff and upgrade" and "refreshed together by a re-run", and its only compare-and-ask, #340's guard migration, compared a copy with the current plugin alone. To that comparison, a copy an older version wrote and a copy the project edited look the same.

No copy records the version that wrote it. Tags miss shipped states: 35 tags cover 71 version bumps, and some untagged bumps carry texts no tag holds. The template changed shape six times since v0.2.3, and its gate commands are byte-identical from v0.21.0 to v0.37.0, so a gate command cannot tell those renders apart.

## Decision
A shipped stdlib script, `assets/upgrade-install.py`, is the re-run's deterministic half. `init` runs it, asks the questions it reports, and runs it again with the answers to write. The script reads `assets/shipped-texts.json`, a table of the sha256 of every text each copied file's source has had at a first-parent commit of the default branch, plus the working tree's current text. It also holds every text the Antigravity template has had since v0.2.3.

A copy whose text is in the table and is not current was written by this plugin, so it is replaced. One whose text is not in the table is the project's edit: it is shown as a diff and replaced only when the user names it. The hooks file is re-rendered from the template that wrote it, which is identified by its whole structure, so the project's own values survive the shape changing. What the script cannot place, it asks about rather than guessing.

`scripts/build-shipped-texts.py` builds the table from history. A `scripts/test-gates.sh` case fails when the table is not exactly the history's texts plus the tree's. So a change to a copied file cannot merge without the table naming its new text, as a shipped change cannot merge without a bump. The table records no version per text. A text enters it on its branch, before its release has a version or a tag, so a recorded version would go stale at every bump and release, and the bump lands after the review.

The table's `copy_set` is the copy set's one machine-read statement. `init`, both READMEs and the templates README cite it instead of listing the files, and a fresh Antigravity install goes through the same script.

## Consequences
- An existing Antigravity install, from v0.2.3 on, can be upgraded without losing an edit to a copy or to its hooks file, and nothing is written that the user did not answer for.
- The copies are written only when the hooks file will be current after the run. Every destination is checked before any file is written, and the hooks file is written last. A write that still fails part way, as a sandbox refusing the temporary file can make it, exits 1 and names what was already written. Gates refreshed under an older hooks file then hold themselves to its `timeout`s and block, under #304's deadline, rather than pass.
- A project installed from a feature branch that never reached the default branch reads that branch's texts as edits. That costs a question, not a loss.
- CAP-5 stays unmet on Antigravity in ADR-10's sense: a fix still needs a re-run. What changed is that the re-run is defined, and safe to run.
- On Claude Code, the script handles the reviewer contract copy only. The gates there arrive by plugin update (ADR-8), and the `.claude/settings.json` declaration stays with `init`'s migrations.

## Alternatives considered
- **An install stamp** that `init` writes, naming the version it installed. It helps only installs made after it ships, and no existing install has one. It still needs the stamped version's texts, which is the table again.
- **Compare with the current text only**, as #340's migration did. Every stale copy becomes a question, and a stale copy cannot be told from an edit.
- **Skill prose only.** The comparison and the JSON merge are deterministic work a model can get wrong, which the layer rule (`AGENTS.md`) puts in a script, and `sed` corrupts a fast check holding `&`.
- **A table built from tags.** It misses every untagged release's texts.
