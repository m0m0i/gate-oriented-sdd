# ADR-7: The plugin ships no agents; a reviewer is a file `init` copies
- Status: accepted
- Date: 2026-10-05; #235

## Context
The reviewers, their rulebooks, the shared contract and the template lived under `agents/`. Both harnesses read that directory in a plugin. Claude Code registers every Markdown file under it, at any depth, so a session registered twelve agents where three were meant: Claude Code 2.1.289's validator began reporting the nine others, and they had been registered all along. `agy plugin validate` 1.2.16 reported eight files processed.

The three that were meant did not work either. A shipped reviewer names its contract at `.claude/agents/_shared/reviewer-contract.md` or `.agents/agents/_shared/…`, and its rules beside itself. Both exist only in a project, after `init` has copied them. Before `init` the plugin's reviewer has no contract to read. After it, the project has its own adapted and pinned copy, and the plugin's sits beside it under a second name.

## Decision
The plugin has no `agents/` directory. The reviewers live in `reviewers/`, which neither harness scans and which has the shape of the directory `init` writes: `<name>.md`, `<name>/rules/`, `<name>/rules-lock.json`, `_shared/`, `_template/`. `scripts/check-manifests.py` fails if `agents/` comes back, and reads the reviewers' frontmatter now that no validator does.

## Consequences
- A session registers no agent from the plugin. The only reviewer it can invoke is the one the project installed, which is the one `- Reviewer:` names and the receipt records.
- `gate-sdd:<lang>-reviewer` can no longer be invoked without `init`. It could be invoked before, and had no contract.
- Always-on cost falls from about 1,300 tokens to about 1,000.
- The top level reads as the three layers: `skills/` for process, `hooks/` for deterministic checks, `reviewers/` for judgment. `hooks/` and `reviewers/` are both rendered into the project and registered by neither harness.
- A reviewer is now, in the tree as in practice, a set of files that conforms to the contract. That is the seam along which language-specific reviewers could later leave this repository. #249 carries the next steps and does not take that one.
- Revisit if a harness gains a way to ship a plugin agent with files only it can read, or if a pack needs a release cadence the gates do not share.

## Alternatives considered
- **List the three reviewers in the manifest's `agents` key** — measured: registration falls from twelve to three, but the validator walks `agents/` whatever the manifest says, so strict validation still fails, and the three unusable agents stay.
- **Allow-list the validator's warnings in CI** — turns an enforced check into a parsed one, and leaves every install as it was.
- **`assets/reviewers/`** — no new shipped path, but it files the judgment layer under "files copied into projects" beside the issue templates.
- **Make the reviewers self-sufficient plugin agents**, reading the contract and rules from the plugin's install directory — the rulebook would then change under a project on every plugin update, which is what the lock exists to prevent (ADR-2).
