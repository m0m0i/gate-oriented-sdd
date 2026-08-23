# Claims and prose

Markdown under `skills/` and `agents/` is executed by a model, so it is source. Everything else
here is about the repository's claims about itself.

- **C-1 — a claim of verification must name what was run.** "Tested", "verified", and "works" are
  not claims unless a command, a test case, or a `docs/verified.md` row backs them. The Status
  section exists to separate verified from asserted; a sentence that blurs them is a defect in the
  thing this repo sells. HIGH.

- **C-2 — a count in prose must match the thing it counts.** "Eighteen paths", "six documents",
  "three reviewers". These go stale silently and were wrong in three files simultaneously as
  recently as `620c3f4`. When a diff changes a count, grep for every other statement of it —
  including `README.ja.md`, which drifts first. MEDIUM.

- **C-3 — the Japanese README is a translation, not a separate document.** A change to a claim in
  `README.md` that is not mirrored in `README.ja.md` leaves one of them false. MEDIUM.

- **C-4 — a skill must terminate in something the harness mechanically uses.** A skill whose only
  output is a document nothing reads is out of scope for this repo, however well written. HIGH.

- **C-5 — instructions must not describe a file the project was never given.** Telling a project to
  run `check-locks.py --update` while shipping it no copy is how a lock quietly stops being checked
  (#3). Any instruction naming a script must be traceable to something `init` installs. HIGH.

- **C-6 — a shipped-path change carries a version bump.** `skills/`, `agents/`, `hooks/`, `assets/`,
  and the two manifests. `claude plugin update` compares version strings, not shas, so an
  unbumped fix is unreachable and reports success (#3). CI enforces this on PRs; flag it earlier.
  HIGH.

- **C-7 — do not add frontmatter to `agents/*/rules/*.md`.** They are reference material, and
  frontmatter risks registering them as phantom subagents. BLOCKER if introduced.
