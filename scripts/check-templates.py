#!/usr/bin/env python3
"""Fail when a shipped task template splits a red step from the green step that answers it.

`skills/implement/SKILL.md` defines its loop per task as Red -> Green -> Refactor -> tick ->
one commit, which makes a task a COMPLETE cycle. The feature and bug templates used to split
Red and Green across two tasks, which makes a task HALF a cycle. Follow both literally and
the turn ends with failing validators, because `quality-gate.sh` runs the `Validators:` line
on turn end and a red T1 is a red turn. That is #10.

The disagreement is about what a *task* is, so this guard is written against the split rather
than against the current wording. A future edit that separates red from green again fails on
the day it is made rather than on the day someone tries to follow it.

It has a SECOND subject, added for #113: this repository's live specs under `.specs/`. The
review gate arms on zero open tasks, which stands in for "implementation is finished" — and
that proxy holds only while every task is implementation work. A task sequenced after the
review holds a box unticked for the whole review window, so the gate stays silent during
exactly the stretch it exists to cover. The fix was definitional, so this checks the
definition is kept.

The two subjects have different lifetimes and only the first ships: `skills/` is installed
into consumer projects, `scripts/` is not. A consumer reading a copied version of this file
is not subject to the `.specs/` half, and the failure messages name which subject failed so
that this is legible from the output rather than from the source.

What it does NOT check: that a task is a good task, or that the words chosen are the best
ones. A guard on prose has to stay narrow or the prose stops being editable, and prose that
cannot be edited rots — a worse failure than the one this prevents.
"""

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

TEMPLATES = "skills/spec/templates.md"

#: The template sections that carry a Tasks block. Named rather than discovered so that a
#: section disappearing is a failure below, not a silently smaller scan.
#:
#: This is a FLOOR, not a filter. The split check iterates every section actually found, so a
#: fourth template section added tomorrow is scanned whether or not it is listed here — a
#: wrong entry makes this guard fail, never pass.
EXPECTED_SECTIONS = ("Feature", "Bug", "Chore")

#: A task line names a RED step. Deliberately a short list of the phrases the templates
#: actually use for "write the test that fails first".
RED = re.compile(r"failing test|regression test|test that reproduces|test .{0,20}\bfails\b", re.I)

#: ...and one that also names the GREEN step answering it.
GREEN = re.compile(
    r"\bimplementation\b|\bimplements?\b|\bthe fix\b|\bfix the\b|\bmakes? it pass\b"
    r"|\bpasses it\b|\banswers it\b",
    re.I,
)

#: Inline code spans and path-like tokens, stripped before GREEN is applied — and ONLY GREEN.
#:
#: A path is not a statement about the task. `skills/implement/SKILL.md` contains the word
#: `implement` between two slashes, and a word boundary matches there — so
#: `- [ ] T1: add a failing test, per skills/implement/SKILL.md`, a purely red task that
#: merely cites this repo's own file, read as green and cleared the check. Word-bounding the
#: alternatives does not fix it, because `/` is not a word character. Judging the line's prose
#: does. The folded templates reference implement's loop in a blockquote directly above the
#: task lines, so moving that citation onto a task line was one ordinary edit from disarming
#: this guard.
#: Its breadth is safe because the substitution only ever REMOVES characters and inserts a
#: single space, and `\S*/\S*` always consumes a whole whitespace-delimited token. So it can
#: delete a green cue but never assemble one: it cannot split a word to make a single-word cue
#: whole, and it cannot leave the one-space gap a multi-word cue like `the fix` needs. A code
#: span opened and closed INSIDE a word could do both — `re`z`implementation` clears — and that
#: is accepted rather than closed: it is not writable prose, no ordinary edit to templates.md
#: reaches it, and the alternatives are dropping the code-span branch, which reopens a real
#: hole, or a sentinel substitution, which is more machinery than the boundary is worth.
CODE_OR_PATH = re.compile(r"`[^`]*`|\S*/\S*")

#: Section heading OUTSIDE the fenced blocks — `## Feature`, not `## 1. Requirements`.
SECTION = re.compile(r"^## ([A-Z][A-Za-z ]*?)\s*$")
TASKS_HEADING = re.compile(r"^## 3\. Tasks")
#: ANY checkbox line inside a Tasks block is a task line. Deliberately not `T\d+:` — that
#: required an id and a colon, so `- [ ] **T1:** ...`, `- [ ] T1 — ...` and `- [ ] 1. ...`
#: parsed as nothing at all and were skipped in silence. Bolding an id or using an em dash is
#: ordinary drift in the file this guard watches, and each of those three forms let a split
#: red step through with the guard exiting 0.
TASK_LINE = re.compile(r"^- \[[ x]\]\s")


def tasks_by_section(text: str) -> dict[str, list[tuple[int, str]]]:
    """Every Tasks block's task lines, keyed by the template section holding it.

    Located by heading rather than by line number so that editing the prose around a block
    does not silently change what is checked.
    """
    found: dict[str, list[tuple[int, str]]] = {}
    section = None
    collecting = False
    for n, line in enumerate(text.splitlines(), 1):
        m = SECTION.match(line)
        if m:
            section, collecting = m.group(1), False
            continue
        if TASKS_HEADING.match(line):
            # A Tasks block with no enclosing section would be collected under None and
            # reported as such, rather than dropped.
            collecting = True
            found.setdefault(section, [])
            continue
        if not collecting:
            continue
        if line.startswith("```") or line.startswith("## "):
            collecting = False  # the fence closed, or the next heading began
            continue
        t = TASK_LINE.match(line)
        if t:
            found[section].append((n, line.strip()))
    return found


path = ROOT / TEMPLATES
if not path.is_file():
    print(f"check-templates: {TEMPLATES} is missing", file=sys.stderr)
    sys.exit(1)
try:
    text = path.read_text()
except OSError as exc:
    # Existence is not readability. A guard that cannot read its subject must fail rather
    # than report success about a file it never opened — see #16, and test-gates.sh's
    # "unreadable steering file" case. Cited by name: the suite prints no case numbers, and
    # its source comments and its output order have already diverged.
    print(f"check-templates: {TEMPLATES} exists but cannot be read: {exc}", file=sys.stderr)
    sys.exit(1)

blocks = tasks_by_section(text)

#: Per SECTION, not in aggregate. The first version asserted only that each expected section
#: had a KEY in `blocks` — which `setdefault` creates at the `## 3. Tasks` heading whether or
#: not a line parsed underneath it — and then checked the total across all sections for zero.
#: One section could therefore contribute an empty work-set while the other two kept the total
#: non-zero, and the success line was reachable with the split still in the file. The floor has
#: to be as deep as the work-set, and the work-set is task lines, not headings. See #16.
thin = []
for name in EXPECTED_SECTIONS:
    lines = blocks.get(name)
    if lines is None:
        thin.append((name, "has no Tasks block at all"))
    elif not lines:
        thin.append((name, "has a Tasks block with no task line this guard could parse"))
if thin:
    print("check-templates FAILED — a template section contributed nothing to check", file=sys.stderr)
    for name, why in thin:
        print(f"  {name}: {why}", file=sys.stderr)
    print("", file=sys.stderr)
    print("  A section the guard could not read is not a section with nothing wrong in it.", file=sys.stderr)
    print("  A task line is any `- [ ] ...` line inside the section's Tasks block.", file=sys.stderr)
    sys.exit(1)

total = sum(len(v) for v in blocks.values())

split = []
for section, lines in blocks.items():
    for n, line in lines:
        # ACCUSE on the raw line, CLEAR only on the stripped prose. Normalisation is not
        # symmetric and applying it to both sides was a fail-open: stripping before GREEN can
        # only make this guard louder — a stripped green cue means the line gets flagged — but
        # stripping before RED can only make it quieter, because a stripped red cue means the
        # line is never examined at all. With it on both sides, `write the \`failing test\` for
        # X` and `add the failing/regression test for X` both cleared, and neither is contrived.
        if RED.search(line) and not GREEN.search(CODE_OR_PATH.sub(" ", line)):
            split.append((section, n, line))   # report the line as written, not as stripped

if split:
    print("check-templates FAILED — a task names a red step with no green step to answer it", file=sys.stderr)
    for section, n, line in split:
        print(f"  {TEMPLATES}:{n} ({section})", file=sys.stderr)
        print(f"    {line}", file=sys.stderr)
    print("", file=sys.stderr)
    print("  `implement`'s loop is per task: Red -> Green -> Refactor -> tick -> one commit,", file=sys.stderr)
    print("  so one task is one COMPLETE cycle and one green commit. A task that is only the", file=sys.stderr)
    print("  red half cannot be committed without ending the turn red, which quality-gate.sh", file=sys.stderr)
    print("  blocks. Fold the pair:", file=sys.stderr)
    print("      - [ ] T1: failing test for X — then the implementation that passes it", file=sys.stderr)
    print("  See #10.", file=sys.stderr)
    sys.exit(1)

# --- second subject: this repository's live specs ----------------------------------
#
# #113. The guard is positional, and the position is the load-bearing part.
#
# A task announces its SCHEDULE in its directive — the text before its first clause break.
# What follows the break describes the work, not when it runs. Scanning the whole line
# instead would flag the very spec that introduced this check, whose T1 and T3 describe
# deferral at length while being ordinary pre-review tasks, and the two available repairs
# from there are both worse than the gap: narrowing the phrase list until one document
# passes tunes the guard to that document, and exempting the spec that owns the guard
# exempts the file most likely to get it wrong.
#
# The gap this leaves, stated rather than hidden: a task that buries its deferral in a
# trailing clause — `T5: bump both manifests — after the review` — is not caught. Closing it
# means reading the tail, and the tail is where a compliant task legitimately says the word.
# A guard with a named edge beats a guard tuned until its own spec passes.

SPECS = ".specs"

#: Phrases that schedule work after the review. Deliberately short and literal, in the
#: manner of RED and GREEN above: the guard recognises the idiom this project actually
#: writes, not every English sentence that could mean the same thing.
DEFERRAL = re.compile(
    r"after the review\b|after the reviewer\b|after the receipt\b|after the gate\b"
    r"|post-review\b|once the review\b|once the reviewer\b",
    re.I,
)

#: `- [x] T5: **` — the checkbox, an optional task id, and optional bold. The id is optional
#: because TASK_LINE above already accepts a line without one, and a directive extracted from
#: a line this failed to strip would start with "T5:" and simply never match.
TASK_PREFIX = re.compile(r"^- \[[ xX]\]\s*(?:\*\*)?\s*(?:T?\d+[:.)]\s*)?(?:\*\*)?\s*")

#: Em dash, en dash, semicolon, or a sentence end. The first of these closes the directive.
CLAUSE_BREAK = re.compile(r"\s[\u2014\u2013]\s|;|(?<=\.)\s")


def directive(line: str) -> str:
    """The part of a task line that states what the task IS, before any elaboration."""
    return CLAUSE_BREAK.split(TASK_PREFIX.sub("", line.strip()), 1)[0].strip()


spec_root = ROOT / SPECS
deferred: list[tuple[str, int, str]] = []
unreadable: list[tuple[str, str]] = []
scanned = 0

if spec_root.is_dir():
    for spec in sorted(spec_root.glob("*/spec.md")):
        # `.specs/_archive/<slug>/spec.md` sits one level deeper than the glob reaches, so
        # this is belt and braces — and it is kept because the exclusion is a DECISION, not
        # an accident of the pattern. #105's T5 is exactly the forbidden shape, and it is a
        # record of what was done. Rewriting a record to satisfy a guard written afterwards
        # destroys its value as evidence; that is the #102 precedent.
        if "_archive" in spec.relative_to(spec_root).parts:
            continue
        try:
            spec_text = spec.read_text()
        except OSError as exc:
            # Existence is not readability, and the two are indistinguishable downstream: a
            # spec never opened contributes no task lines, and no task lines is what a
            # compliant spec looks like. Fail closed. See #16, and case 53.
            unreadable.append((str(spec.relative_to(ROOT)), str(exc)))
            continue
        scanned += 1
        for lines in tasks_by_section(spec_text).values():
            for n, line in lines:
                head = directive(line)
                if DEFERRAL.search(head):
                    deferred.append((str(spec.relative_to(ROOT)), n, head))

if unreadable:
    print("check-templates FAILED — a live spec exists but cannot be read", file=sys.stderr)
    for name, why in unreadable:
        print(f"  {name}: {why}", file=sys.stderr)
    print("", file=sys.stderr)
    print("  A spec this guard could not open is not a spec with nothing wrong in it.", file=sys.stderr)
    sys.exit(1)

if deferred:
    print("check-templates FAILED — a task is sequenced after the review", file=sys.stderr)
    for name, n, head in deferred:
        print(f"  {name}:{n}", file=sys.stderr)
        print(f"    {head}", file=sys.stderr)
    print("", file=sys.stderr)
    print("  review-gate.sh arms when a spec has no unticked tasks, which stands in for", file=sys.stderr)
    print("  'implementation is finished'. A task held back until after the review keeps", file=sys.stderr)
    print("  that box unticked for the whole review, so the gate stays silent during the", file=sys.stderr)
    print("  one stretch it exists to cover.", file=sys.stderr)
    print("", file=sys.stderr)
    print("  Work that belongs after the review is a STEP of `implement`, beside the work", file=sys.stderr)
    print("  log entry and the `Status: done` flip — not a task. See #113.", file=sys.stderr)
    sys.exit(1)

print(
    f"check-templates: {total} task line(s) across {len(blocks)} template(s), no split red steps; "
    f"{scanned} live spec(s), no task sequenced after the review"
)
