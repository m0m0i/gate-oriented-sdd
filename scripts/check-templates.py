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
EXPECTED_SECTIONS = ("Feature", "Bug", "Chore")

#: A task line names a RED step. Deliberately a short list of the phrases the templates
#: actually use for "write the test that fails first".
RED = re.compile(r"failing test|regression test|test that reproduces|test .{0,20}\bfails\b", re.I)

#: ...and one that also names the GREEN step answering it. `implement` covers "implementation"
#: too, which is the word the folded form uses.
GREEN = re.compile(r"implement|the fix\b|fix the\b|makes? it pass|passes it|answers it", re.I)

#: Section heading OUTSIDE the fenced blocks — `## Feature`, not `## 1. Requirements`.
SECTION = re.compile(r"^## ([A-Z][A-Za-z ]*?)\s*$")
TASKS_HEADING = re.compile(r"^## 3\. Tasks")
TASK_LINE = re.compile(r"^- \[[ x]\] (T\d+):")


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
    # than report success about a file it never opened — see #16, and case 32.
    print(f"check-templates: {TEMPLATES} exists but cannot be read: {exc}", file=sys.stderr)
    sys.exit(1)

blocks = tasks_by_section(text)

missing = [s for s in EXPECTED_SECTIONS if s not in blocks]
if missing:
    print("check-templates FAILED — a template section has no Tasks block", file=sys.stderr)
    print(f"  expected a Tasks block under each of: {list(EXPECTED_SECTIONS)}", file=sys.stderr)
    print(f"  found none under: {missing}", file=sys.stderr)
    print("  A section whose block vanished is not a section with nothing to check.", file=sys.stderr)
    sys.exit(1)

total = sum(len(v) for v in blocks.values())
if total == 0:
    print(
        "check-templates: found Tasks headings but no task lines at all, so there is nothing "
        "to compare. A guard with an empty work-set must not report success — see #16.",
        file=sys.stderr,
    )
    sys.exit(1)

split = []
for section, lines in blocks.items():
    for n, line in lines:
        if RED.search(line) and not GREEN.search(line):
            split.append((section, n, line))

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
