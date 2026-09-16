# ADR-7: Documentation stays plain Markdown read on GitHub, indexed by hand
- Status: accepted
- Date: 2026-09-16

## Context
`docs/` holds 16 Markdown files — 10 documents and 6 ADRs, 938 lines — beside two long READMEs, and it has grown at every grooming. Navigation is the thin part: the ADRs are six slug filenames with no index, and nothing tells a reader which of these documents a skill wrote and which this repository wrote by hand. A documentation site generator is the reflex answer to that, and Material for MkDocs is the one people reach for.

Three forces cut against it here, and none of them is about the tool's quality. `.steering/tech.md` and `docs/CONTRACT.md` both declare the stack as POSIX `sh`, Python 3 standard library, and Markdown, with **no package manager, no dependency file anywhere, and no build** — `mkdocs-material` 9.7.7 carries eleven runtime dependencies. The repository root *is* the plugin (ADR-1), so a config file, a dependency file, a theme override directory and a build output would all land in what `agy plugin install ./gate-oriented-sdd` takes and what the marketplace entry at `./` clones. And `docs/` is not a website source: it is state that `assets/check-document-set.py` verifies against the `- Mode:` line, so a generator's `docs_dir` conventions would give one directory a second owner with its own idea of what belongs in it.

There is a fourth force, smaller but load-bearing. Material's admonitions and content tabs are not Markdown, and `README.md` links straight into `./docs/layout.md` and `./docs/verified.md`. Using the features that justify the tool would leave those documents rendering correctly on the site and as literal text on GitHub — one document, two renderings, one of them wrong — which is the failure mode this repository keeps filing against itself.

## Decision
The documents stay plain Markdown, read on GitHub, with no generator, no dependency file and no build. Navigation is closed by two checked-in index files instead: `docs/README.md` and `docs/decisions/README.md`, which GitHub renders when a reader browses to either directory.

## Consequences
- The declared stack stays true, and CI keeps the supply chain it has: a repository whose first gate is a leakage guard does not acquire eleven transitive dependencies in order to typeset 938 lines.
- ADR-1's payload stays what it claims — consumers clone no build scaffolding for a site they will never build — and `docs/` keeps one owner in `check-document-set.py`.
- There is no cross-document search beyond GitHub's own, and no documentation versioned per release. At this size that is a real loss and a small one; it stops being small if the set triples.
- **The indexes are maintained by hand and nothing compares them to the directory.** A document added without a row goes unlisted, and a renamed ADR leaves a dead link. That is #23's shape — a fact stated twice, drifting — and it is accepted here deliberately and without a guard, because a guard covering two files is a worse trade than the drift it would catch. If it does bite, the fix is a guard, not a generator.
- The index is not mirrored in Japanese. `README.ja.md` is a translation of `README.md` (C-3) and `docs/` has never been bilingual, so a Japanese reader browsing `docs/` gets an English index. Recorded rather than fixed.
- Revisit if the document set roughly triples, if documentation needs to be versioned per release, or if the harness ever ships documents to consumers instead of keeping `docs/` unshipped.

## Alternatives considered
- **Material for MkDocs** — rejected on the three forces above rather than on quality; it is the best tool in its category. Its upstream state confirms the timing besides: the project is in maintenance mode, taking critical bug fixes and security updates only until an announced end of life, with feature work moved to a successor. Read the maintainer's announcement rather than quoting a date from here — its issue title and its body currently disagree, the body carrying a six-month extension the title does not. Adopting a frozen tool to solve a navigation problem that two index files close is a poor trade at any dependency count.
- **Zensical** — the successor from the same team, and the right candidate if this is ever revisited. It is pre-1.0 today, so adopting it now to escape a frozen tool buys two migrations instead of one.
- **A generated site in a separate repository** — keeps ADR-1's payload clean, and is the shape to reach for if a site is genuinely wanted. Rejected now for the same reason as the rest, plus one of its own: it splits the documents from the guards that check them.
- **An index in `README.md` alone** — the README is already long, and every claim in it must be mirrored in `README.ja.md` (C-3), so each index edit becomes two. A `docs/README.md` sits in the directory the reader is already browsing.
