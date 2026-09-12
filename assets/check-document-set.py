#!/usr/bin/env python3
"""Verify the installed document set against the mode the project declared.

`init` chooses between a minimum and a full document set. Before #110 it recorded nothing,
so the harness could not tell *"minimum, deliberately"* from *"full, half-abandoned"* — and
that is exactly the distinction a checker needs before it can call a missing `CONTRACT.md` a
hole rather than a choice.

The mode is DECLARED on `.steering/tech.md`'s `- Mode:` line and verified here against the
filesystem. Declared rather than derived on purpose: the mode is *almost* computable from
which files exist, but derivation cannot distinguish a deliberate omission from an
abandonment, which is the whole feature. Declaration plus verification is the same shape as
`rules-lock.json` against its rulebook, and as `- Validators:` being declared and then run.

This is a guard the project OWNS — copied into its `scripts/` and named on its `- Validators:`
line, beside `check-steering-anchors.sh` and `check-locks.py`. No hook reads the mode. A gate
that branched on mode would be a switch that turns enforcement down.

Run from the repository root. Exits 0 when the filesystem matches the declared mode.
"""
import pathlib
import re
import sys

#: Read exactly as hooks/gate-lib.sh's gate_steering_value does — `sed -n "s/^ *- *KEY: *//p"`
#: then the first line. Keeping the two readers identical matters: a value this sees and the
#: hooks do not (or the reverse) is the #34 shape, where a line written `- **Mode: full**`
#: yields nothing, the file looks right, and nobody finds out.
STEERING = pathlib.Path(".steering/tech.md")

#: Documents every mode requires, relative to the `- Docs:` directory.
MANDATORY_DOCS = ("PRD.md", "DESIGN.md", "BACKLOG.md")
#: What `full` adds. One document per opt-in skill: northstar, epics, contract.
FULL_ONLY_DOCS = ("NORTH_STAR.md", "EPICS.md", "CONTRACT.md")
#: The issue templates sit INSIDE the chain rather than beside it — the Issue step is where
#: the type is decided, and the type decides the spec's shape. Required in both modes.
TEMPLATES = ("feature.md", "bug.md", "chore.md")
TEMPLATE_DIR = pathlib.Path(".github/ISSUE_TEMPLATE")
#: Directories the flow writes into. Their contents vary per spec and per session, so only
#: their existence is checkable — but an absent one means the harness was never installed.
MANDATORY_DIRS = (pathlib.Path(".specs"), pathlib.Path(".work_logs"))

MODES = ("minimum", "full")


def fail(message):
    print(f"check-document-set: {message}", file=sys.stderr)
    raise SystemExit(1)


def steering_value(text, key):
    for line in text.split("\n"):
        m = re.match(rf"^ *- *{key}: *(.*)$", line)
        if m:
            return m.group(1).strip()
    return ""


def main():
    if not STEERING.is_file():
        fail(f"{STEERING} does not exist, so no mode is declared and nothing can be verified.")
    try:
        text = STEERING.read_text()
    except OSError as exc:
        # Existence is not readability. A guard that reports success about a file it never
        # opened is the shape this repository has shipped four times; see #16.
        fail(f"{STEERING} cannot be read ({exc.strerror}), so the declared mode is unknown.")

    mode = steering_value(text, "Mode")
    if not mode:
        # NOT a default. Reading an absent line as `minimum` would verify the smaller set and
        # report success, which is indistinguishable from a project that chose minimum — and
        # it makes the declaration optional in practice, which is the one thing it cannot be.
        fail(
            f"{STEERING} carries no readable `- Mode:` line. Add `- Mode: minimum` or "
            f"`- Mode: full` on one physical line. A mode is declared, never assumed."
        )
    if mode not in MODES:
        fail(f"`- Mode: {mode}` is not a mode. Expected one of: {', '.join(MODES)}.")

    docs_value = steering_value(text, "Docs") or "docs/"
    if "://" in docs_value:
        # `- Docs:` may name a shared documentation repository in a multi-repo product. A URL
        # is not a directory, so every document would read as absent — a false RED — while
        # treating it as "nothing to check" would be a false GREEN. Neither is acceptable, so
        # it is its own outcome and `init` does not put this checker on such a project's
        # `- Validators:` line.
        fail(
            f"`- Docs: {docs_value}` names another repository, so the document set cannot be "
            f"verified from here. Remove this checker from `- Validators:` for a multi-repo "
            f"install, or point `- Docs:` at a local directory."
        )

    docs = pathlib.Path(docs_value)
    if not docs.is_dir():
        fail(f"`- Docs: {docs_value}` does not name a directory that exists.")

    wanted = [docs / name for name in MANDATORY_DOCS]
    if mode == "full":
        wanted += [docs / name for name in FULL_ONLY_DOCS]
    wanted += [TEMPLATE_DIR / name for name in TEMPLATES]

    missing = []
    for path in wanted:
        try:
            ok = path.is_file()
        except OSError:
            ok = False
        if not ok:
            missing.append(path)
    missing += [d for d in MANDATORY_DIRS if not d.is_dir()]

    if missing:
        listed = ", ".join(str(p) for p in missing)
        fail(f"mode is `{mode}` and {len(missing)} required item(s) are not found: {listed}")

    # Never reachable on an empty work-set: `wanted` is built from module constants, so it is
    # non-empty by construction, and the count is printed rather than the word "all" so that a
    # shrinking set is visible in CI output rather than silent.
    optional_note = "" if mode == "full" else " (the 3 opt-in documents are not required, and may be present)"
    print(
        f"check-document-set: mode `{mode}` — {len(wanted)} document(s) and "
        f"{len(MANDATORY_DIRS)} directory(ies) present{optional_note}"
    )


if __name__ == "__main__":
    main()
