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

print(f"check-templates: {total} task line(s) across {len(blocks)} template(s), no split red steps")
