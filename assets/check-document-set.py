#!/usr/bin/env python3
"""Verify the installed document set against the mode the project declared.

`init` chooses between a minimum and a full document set. Before #110 it recorded nothing,
so the harness could not tell *"minimum, deliberately"* from *"full, half-abandoned"* — and
that is exactly the distinction a checker needs before it can call a missing `CONTRACT.md` a
hole rather than a choice.

A third value, `bootstrap`, was added by #127: the harness is installed and the inception
documents are not written yet. It exists because this checker was asking two questions through
one exit code — *is the harness installed correctly* (directories, issue templates, a readable
mode), which `init` can make true, and *has this project authored its documents*, which `init`
cannot make true without writing the user's thinking for them. Arming the second at install
time made every first install start red, which is CAP-4's falsifier exactly. `bootstrap` claims
only the first and says so in its own success line; it is **declared**, not inferred from an
empty `docs/`, for the same reason the other two are. It is also self-terminating: it stops
passing once `.specs/` holds a spec, so it cannot become a gate switched off and left off.

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
import os
import pathlib
import re
import stat
import sys

#: Read exactly as hooks/gate-lib.sh's gate_steering_value does — `sed -n "s/^ *- *KEY: *//p"`
#: then the first line. Keeping the two readers identical matters: a value this sees and the
#: hooks do not (or the reverse) is the #34 shape, where a line written `- **Mode: full**`
#: yields nothing, the file looks right, and nobody finds out.
STEERING = pathlib.Path(".steering/tech.md")

#: Documents `minimum` and `full` require, relative to the `- Docs:` directory. Not `bootstrap`,
#: which is the state of not having written them yet.
MANDATORY_DOCS = ("PRD.md", "DESIGN.md", "BACKLOG.md")
#: The skill that writes each. `bootstrap` names them in its output: telling a user three
#: documents are owed without naming what writes them leaves them to search the skill list.
DOC_OWNER = {"PRD.md": "prd", "DESIGN.md": "design-doc", "BACKLOG.md": "backlog"}
#: What `full` adds. One document per opt-in skill: northstar, epics, contract.
FULL_ONLY_DOCS = ("NORTH_STAR.md", "EPICS.md", "CONTRACT.md")
#: The issue templates sit INSIDE the chain rather than beside it — the Issue step is where
#: the type is decided, and the type decides the spec's shape. Required in every mode —
#: they are part of the install-time invariant, which is the half `bootstrap` still claims.
TEMPLATES = ("feature.md", "bug.md", "chore.md")
TEMPLATE_DIR = pathlib.Path(".github/ISSUE_TEMPLATE")
#: Directories the flow writes into. Their contents vary per spec and per session, so only
#: their existence is checkable — but an absent one means the harness was never installed.
SPECS = pathlib.Path(".specs")
MANDATORY_DIRS = (SPECS, pathlib.Path(".work_logs"))
#: Shipped specs are swept here rather than deleted, so it is part of the same question.
ARCHIVE = SPECS / "_archive"

#: Ordered as a project moves through them. `bootstrap` is first because every project passes
#: through it, including the ones that leave it in the same hour.
MODES = ("bootstrap", "minimum", "full")


def fail(message):
    print(f"check-document-set: {message}", file=sys.stderr)
    raise SystemExit(1)


def spec_slugs(directory):
    """`(found, unreadable)` for the directories under `directory`. May raise OSError.

    Three outcomes at BOTH levels, which is the whole of this function. `os.scandir`, not
    `Path.glob`: glob swallows OSError and yields nothing, so an unreadable `.specs/` would read
    as "no specs" and report the grace period intact *because it could not look* — G-1, and
    #115's lesson in the same shape one file over. The scandir failure propagates; the caller
    names the directory it was scanning.

    The per-entry test is `os.stat`, NOT `Path.is_file()`, and that is not a stylistic choice.
    `Path.is_file()` delegates to `os.path.isfile`, which swallows every OSError — so a slug
    directory the process cannot traverse read as "no spec.md here" and the guard exited 0 with
    a real spec on disk: this docstring's own promise, honoured for the outer directory and
    broken one level in, and interpreter-dependent besides. Found in review of this file.

    A directory with no `spec.md` is not a spec: `_archive/` itself is one of those, and so is
    anything a session left behind. FileNotFoundError is that answer and nothing more, which is
    why it is caught separately from the OSErrors that mean "could not tell".

    `entry.is_dir()` FOLLOWS symlinks, and that is the third deliberate choice here. With
    `follow_symlinks=False` a symlinked slug directory was skipped before the stat and landed
    in neither list — a fourth outcome, in the fail-open direction, from a definition of "spec
    directory" narrower than the design's *a directory containing `spec.md`*. Following makes a
    loop an OSError, which is `unreadable`, and a dangling link a plain False, which is the
    honest "no spec here".
    """
    found = []
    unreadable = []
    with os.scandir(directory) as entries:
        for entry in entries:
            try:
                if not entry.is_dir():
                    continue
                mode = os.stat(os.path.join(entry.path, "spec.md")).st_mode
            except FileNotFoundError:
                continue
            except OSError:
                unreadable.append(entry.path)
                continue
            if stat.S_ISREG(mode):
                found.append(entry.path)
    return found, unreadable


def steering_value(text, key):
    """The first value for `key`, byte-for-byte as `gate_steering_value` would return it.

    No `.strip()`. `sed -n "s/^ *- *KEY: *//p"` removes what precedes the value and nothing
    that follows it, so `- Mode: full   ` is the string `full   ` to every shell consumer.
    Stripping here would make this reader accept a value the hooks would not — the #34 shape
    inverted, and in the direction that passes silently. Parity is the stricter behaviour, so
    parity is what this does; the `mode.strip()` branch in `main` below turns the resulting
    failure into a sentence that names the real cause instead of a confusing one.
    """
    for line in text.split("\n"):
        m = re.match(rf"^ *- *{key}: *(.*)$", line)
        if m:
            return m.group(1)
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
        # The remediation text is part of the guard. Naming only the two document sets sent a
        # project with no documents to declare one it had not written, which is the red gate
        # #127 closes — the checker contradicting its own advice one run later.
        offered = ", ".join(f"`- Mode: {m}`" for m in MODES)
        fail(
            f"{STEERING} carries no readable `- Mode:` line. Add one of {offered} on one "
            f"physical line — `bootstrap` if the inception documents are not written yet. "
            f"A mode is declared, never assumed."
        )
    if mode not in MODES:
        if mode.strip() in MODES:
            # Parity with the shell reader means trailing whitespace is part of the value, so
            # this really is a malformed line rather than a near miss — but saying only "not a
            # mode" about a line that reads `- Mode: full` to a human is a diagnosis nobody
            # can act on.
            fail(
                f"`- Mode:` carries trailing whitespace, so its value is {mode!r} rather than "
                f"{mode.strip()!r}. The hooks read this line with sed and do not trim it either. "
                f"Remove the trailing space."
            )
        fail(f"`- Mode: {mode}` is not a mode. Expected one of: {', '.join(MODES)}.")

    # Stripped, unlike `mode` — and the asymmetry is deliberate. The parity argument above
    # only bites where a shell consumer reads the same value: `gate_steering_value` is called
    # for Validators, Source globs, Owns and Reviewer, and check-steering-anchors.sh reads
    # Docs solely to test it non-empty. Nothing paths on it, so there is no reader here to be
    # stricter than — while `Path("docs/ ")` is a directory named " " inside docs/, which
    # fails with a message whose cause is invisible in rendered Markdown.
    # The strip goes INSIDE the `or`, not outside it. Outside, a whitespace-only value is
    # truthy, survives the default, and is then emptied — and `pathlib.Path("")` is `.`, a
    # directory that always exists. The guard would then verify the set at the repository
    # root and, on a project keeping its documents there, print a success line naming no
    # directory at all: exit 0 having checked somewhere nobody configured. `- Docs: \t`
    # reaches this, and so does a non-breaking space pasted from a rendered page, because the
    # regex's ` *` is ASCII-space-only. Inside, a whitespace-only value falls back to `docs/`
    # exactly as an absent line does, and `Path("")` is unreachable.
    docs_value = steering_value(text, "Docs").strip() or "docs/"
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

    # The URL branch above stays AHEAD of this one in all three modes. A `- Docs:` value that is
    # not a path is a misconfiguration whatever the mode, and reading it under `bootstrap` as
    # "nothing to check yet" would be the false GREEN that branch exists to refuse, reached
    # again through the new value.
    docs = pathlib.Path(docs_value)

    wanted = []
    if mode != "bootstrap":
        if not docs.is_dir():
            fail(f"`- Docs: {docs_value}` does not name a directory that exists.")
        wanted += [docs / name for name in MANDATORY_DOCS]
        if mode == "full":
            wanted += [docs / name for name in FULL_ONLY_DOCS]
    # `docs/` itself is not required under `bootstrap`: nothing has been written into it, and a
    # directory created to hold nothing is the placeholder `init` step 3 forbids one level up.
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

    if mode == "bootstrap":
        # AC4. Without this, `bootstrap` is a gate switched off with a note attached — the
        # exact failure `.steering/product.md` names, reached by a route that looks principled.
        # The grace period ends at the first spec because a spec is where a capability id gets
        # cited, and it is the first moment the harness is genuinely in use. The failure then
        # lands INSIDE the flow with the cause one command behind the user, which is what CAP-4
        # asks for: not "never block", but never block on a failure that predates them.
        started = []
        unreadable = []
        for directory in (SPECS, ARCHIVE):
            # `Path.is_dir()` swallows OSError, and this is the one place that is safe —
            # but only by an invariant worth writing down, because it lives elsewhere.
            # `_archive` is itself an entry of `.specs`, so the scan above has already
            # classified it with error-visible stats: unreadable in any way, it is in
            # `unreadable` and we never reach a verdict. A dangling link is False in both
            # places, which is honest. Skipping `_archive` by name in that loop — the natural
            # way to stop it being listed twice — would activate this swallow with nothing
            # left to catch it.
            if directory is ARCHIVE and not ARCHIVE.is_dir():
                continue
            try:
                found, unread = spec_slugs(directory)
            except OSError as exc:
                # The scanned directory, not always `.specs` — a failure in `_archive/` that
                # sent the reader to the parent would be a diagnosis they cannot act on.
                fail(
                    f"{directory} cannot be read ({exc.strerror}), so whether this project has "
                    f"begun building cannot be established — and `bootstrap` is only true "
                    f"before it has."
                )
            started += found
            unreadable += unread
        if unreadable:
            listed = ", ".join(sorted(unreadable))
            fail(
                f"{len(unreadable)} director(ies) under {SPECS} cannot be read: {listed}. "
                f"Whether they hold a spec is unknown, and `bootstrap` is only true while none "
                f"does — so this is neither `no specs` nor `a spec`, and not a pass."
            )
        if started:
            listed = ", ".join(sorted(started))
            fail(
                f"mode is `bootstrap` — documents not yet authored — but {len(started)} spec(s) "
                f"already exist: {listed}. A spec cites the documents this mode says are "
                f"unwritten. Write {', '.join(MANDATORY_DOCS)} (via "
                f"{', '.join(DOC_OWNER[d] for d in MANDATORY_DOCS)}) and declare `minimum` or "
                f"`full` in {STEERING}."
            )

        owed = ", ".join(f"{name} ({DOC_OWNER[name]})" for name in MANDATORY_DOCS)
        # A separate sentence, not the line below with a smaller number in it. G-1: "the
        # documents are present" and "the documents were not looked at" cannot share an
        # outcome, and exit 0 is already shared between them — so the words carry the whole
        # difference, and a count of documents this run never examined must not appear in them.
        print(
            f"check-document-set: mode `{mode}` — the harness is installed "
            f"({len(TEMPLATES)} issue template(s) and {len(MANDATORY_DIRS)} directory(ies) "
            f"present). {len(MANDATORY_DOCS)} document(s) not yet authored: {owed}. "
            f"Declare `minimum` or `full` in {STEERING} once they are written."
        )
        return

    # Never reachable on an empty work-set: `wanted` is built from module constants, so it is
    # non-empty by construction, and the count is printed rather than the word "all" so that a
    # shrinking set is visible in CI output rather than silent.
    optional_note = "" if mode == "full" else " (the 3 opt-in documents are not required, and may be present)"
    # Counted in their own units. This spec exists partly because #109's section counted issue
    # templates once inside a total and again beside it; reintroducing that conflation in the
    # checker's own output would be the same defect one layer down.
    n_docs = len(wanted) - len(TEMPLATES)
    print(
        f"check-document-set: mode `{mode}` at `{docs}/` — {n_docs} document(s), "
        f"{len(TEMPLATES)} issue template(s) and {len(MANDATORY_DIRS)} directory(ies) "
        f"present{optional_note}"
    )


if __name__ == "__main__":
    main()
