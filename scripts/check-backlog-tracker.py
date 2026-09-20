#!/usr/bin/env python3
"""The ordered list and the tracker must agree, in both directions.

#79. Each row of `BACKLOG.md` restates two facts the tracker also holds — which issues exist
for this item, and which of them are still live — and nothing derived either or compared them.
The tracker changes continuously and from three directions (`sprint` creating, a merge closing,
a review filing); the document changes only when `backlog` runs, which its own preamble scopes
to "occasionally". A copy updated on a slower clock than its subject, with no comparison
between them, does not drift loudly: the reader cannot tell a current row from a stale one by
looking. That is #14's and #23's class, one document over.

**The two directions read different regions, and that asymmetry is load-bearing.** It was
chosen against the real document rather than assumed. On 2026-09-20 the table's Item cells
cited zero closed issues, while whole rows cited eleven — #9, #26, #113, #118, #126, #127,
#130, #131, #133, #140 and #146 — every one of them correct history in a `Why here` cell
("#146 left this row by shipping"). So:

  * ABSENT (direction A) is generous. An open issue counts as known to the list if it is cited
    anywhere in the ordered table or under `## Unshaped`.
  * FINISHED (direction B) is strict. Only the **Item** cell asserts that an issue is live
    work; `Why here` is reasoning and may cite anything, including closed issues.

A checker reading whole rows for direction B would have reported all eleven on its first run
and been switched off the same day. `skills/backlog/SKILL.md` states the convention this
relies on, so the rule is a documented contract rather than a habit that happened to hold.

Not on `- Validators:` and not shipped. It needs the tracker, so a turn-end hook cannot run it
— see `.steering/tech.md`. Run from the repository root; CI runs it on pull requests.
"""
import json
import os
import pathlib
import re
import subprocess
import sys

STEERING = pathlib.Path(".steering/tech.md")

#: The document. Its name is fixed across every install — `.specs/`, `.steering/` and the
#: document names are literal in every skill, which is what lets one copy of a skill serve
#: every project. Only the directory is configurable, and it comes from `- Docs:`.
BACKLOG_NAME = "BACKLOG.md"

#: A table line, and an ordered row within it. Up to three leading spaces, because Markdown
#: allows them and such a row renders identically — one that picked a space up used to vanish
#: from BOTH directions at once: its Item cell went unchecked, and when its issues closed the
#: absent direction had nothing to say either. The quietest failure this guard had.
TABLE_LINE = re.compile(r"^\s{0,3}\|")
ROW = re.compile(r"^\s{0,3}\|\s*(\d+)\s*\|")

#: The column carrying the live-work claim, located BY NAME rather than by position. Position
#: is not stable: the `Epic` column was deleted from this repository's own table in 2026-09 and
#: #164 is scheduled to replace it with version lines, so a column arriving before `Item` is
#: planned work rather than a hypothetical. Bound to "the second cell", such a column would push
#: `Item` sideways and leave the finished-work direction reading a cell that never carries a
#: citation — finding nothing, and printing `no drift`.
ITEM_COLUMN = "Item"

#: Any issue citation. `\d+` is greedy, so `#146` yields 146 rather than 14 — the bug a
#: shorter pattern would introduce silently, reporting row after row for issues nobody wrote.
ISSUE = re.compile(r"#(\d+)")

#: Sections outside the table that still speak about live work, and the one that records a
#: deliberate exclusion. Matched on the heading line, so renaming a section in the template
#: without updating this list turns its contents invisible — which is why the floors below
#: exist and why `## Open, not planned` being absent is legal while an empty table is not.
UNSHAPED_HEADING = "## Unshaped"
NOT_PLANNED_HEADING = "## Open, not planned"

#: An exclusion's SUBJECT: the first issue cited on a `- ` entry line, and nothing else on it.
#:
#: Found by running this checker against this repository's own document. The entry excluding #36
#: explains itself by citing #26, and reading the whole section counted both — harmless there
#: only because #26 is closed and the absent direction reads open issues. Written as "rejected
#: while specing #<open issue>" it is an exemption granted by a sentence of prose, which is this
#: guard's own fail-open. It is also exactly the Item-versus-`Why here` split one section over:
#: an entry states what is excluded, and its reason may cite anything.
#:
#: Column 0 only, unlike every other pattern here: the section's contract is one line per entry, so an indented
#: sub-bullet is continuation prose, and treating it as an entry would let `  - Blocked on #141.` buy #141 an
#: exemption. Indenting an entry now costs it its exemption, which fails closed.
#:
#: This checks ONE of the section's three parts. The issue and a reason are enforced; the falsifier — the
#: condition that would make it a row — is not, and a later author should not read this as complete.
ENTRY = re.compile(r"^[-*]\s+(.*?)#(\d+)(.*)$")

#: How many issues to ask the tracker for. A cap that silently truncates is a fail-open: the
#: absent direction would stop seeing the issues past it and report agreement about a list it
#: had not finished reading. So the cap is checked against the result below rather than
#: trusted, and a full page is treated as "there may be more" rather than as an answer.
TRACKER_LIMIT = 1000


def fail(message):
    print("check-backlog-tracker FAILED", file=sys.stderr)
    print(f"  {message}", file=sys.stderr)
    raise SystemExit(1)


def steering_value(text, key):
    """The `- Key: value` reader, in the form `gate_steering_value` and check-document-set.py
    already use. Not trimmed here for the same reason it is not trimmed there: the hooks read
    these lines with sed and do not trim either, and a reader that is quietly more forgiving
    than its siblings is how one line comes to mean two things."""
    for line in text.split("\n"):
        m = re.match(rf"^ *- *{key}: *(.*)$", line)
        if m:
            return m.group(1)
    return ""


def section(text, heading):
    """The lines under `heading`, up to the next `## `. Returns "" when the heading is absent,
    which is a legal state for both callers: a project with nothing unshaped and nothing
    deliberately excluded has neither section."""
    out, inside = [], False
    for line in text.split("\n"):
        if line.strip() == heading:
            inside = True
            continue
        if inside and line.startswith("## "):
            break
        if inside:
            out.append(line)
    return "\n".join(out)


def tracker_state():
    """`{number: state}` for every issue, from an injected file or from the tracker.

    The override exists because `scripts/test-gates.sh` builds throwaway repositories with no
    network, and a guard whose only path needs one cannot have a red-capable case (G-4). It is
    also where G-1 bites hardest: an absent, empty or unparseable list must fail, never pass.
    "No issues" satisfies BOTH directions vacuously — nothing to find absent, nothing to find
    finished — so it is the one input that would print a clean success while checking nothing.
    """
    injected = os.environ.get("BACKLOG_TRACKER_ISSUES")
    if injected:
        path = pathlib.Path(injected)
        if not path.is_file():
            fail(f"BACKLOG_TRACKER_ISSUES={injected} does not name a file that exists.")
        try:
            raw = path.read_text()
        except OSError as exc:
            fail(f"BACKLOG_TRACKER_ISSUES={injected} cannot be read ({exc.strerror}).")
        states = {}
        for lineno, line in enumerate(raw.split("\n"), 1):
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) != 2 or not parts[0].isdigit() or parts[1] not in ("OPEN", "CLOSED"):
                fail(
                    f"{injected}:{lineno}: {line!r} is not `<number> OPEN|CLOSED`. An issue "
                    f"list that cannot be parsed is not an empty issue list."
                )
            states[int(parts[0])] = parts[1]
        if not states:
            fail(
                f"BACKLOG_TRACKER_ISSUES={injected} is empty. No issues would satisfy both "
                f"directions with nothing to compare, which is not agreement."
            )
        return states

    try:
        proc = subprocess.run(
            ["gh", "issue", "list", "--state", "all", "--limit", str(TRACKER_LIMIT),
             "--json", "number,state"],
            capture_output=True, text=True,
        )
    except OSError as exc:
        # Not "nothing to check". A tracker that cannot be reached and a list that agrees with
        # it must not produce the same output — the anchor is `gates never fail open`.
        fail(f"the tracker cannot be reached: `gh` could not be run ({exc.strerror}).")
    if proc.returncode != 0:
        detail = proc.stderr.strip().split("\n")[0] if proc.stderr.strip() else "no diagnostic"
        fail(f"the tracker cannot be reached: `gh issue list` exited {proc.returncode} ({detail}).")
    try:
        rows = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        fail(f"the tracker's reply could not be parsed as JSON ({exc.msg}).")
    if not rows:
        fail(
            "the tracker reports no issues at all. That satisfies both directions with "
            "nothing to compare, so it is refused rather than reported as agreement."
        )
    if len(rows) >= TRACKER_LIMIT:
        # The page was filled, so there may be more behind it, and the absent direction would
        # simply stop seeing them.
        fail(
            f"the tracker returned {len(rows)} issues, filling the {TRACKER_LIMIT} cap, so the "
            f"list may be truncated and the absent direction incomplete. Raise TRACKER_LIMIT."
        )
    return {int(r["number"]): r["state"] for r in rows}


def main():
    if not STEERING.is_file():
        fail(f"{STEERING} does not exist, so the document directory cannot be resolved.")
    try:
        steering = STEERING.read_text()
    except OSError as exc:
        # Existence is not readability — #16's shape, and this repository has shipped it.
        fail(f"{STEERING} cannot be read ({exc.strerror}).")

    docs_value = steering_value(steering, "Docs").strip() or "docs/"
    if "://" in docs_value:
        # `- Docs:` may name a shared documentation repository in a multi-repo product, which
        # `assets/check-document-set.py` already recognises. The file is then not on disk, and
        # reading its absence as "no rows to check" would be the false GREEN in the direction
        # this whole guard exists to close.
        fail(
            f"`- Docs: {docs_value}` names another repository, so {BACKLOG_NAME} is not local "
            f"and cannot be compared from here. Run this check in the repository that holds it."
        )

    backlog = pathlib.Path(docs_value) / BACKLOG_NAME
    if not backlog.is_file():
        fail(f"{backlog} does not exist, so there is no list to compare against the tracker.")
    try:
        text = backlog.read_text()
    except OSError as exc:
        fail(f"{backlog} cannot be read ({exc.strerror}).")

    lines = text.split("\n")
    item_index = None
    for line in lines:
        if not TABLE_LINE.match(line) or ROW.match(line):
            continue
        for i, cell in enumerate(line.split("|")):
            if cell.strip() == ITEM_COLUMN:
                item_index = i
                break
        if item_index is not None:
            break
    if item_index is None:
        # Guessing an index here is the whole defect. A header that no longer names `Item`
        # means the table's shape has moved under the guard, and the finished-work direction
        # has no claim to read — which must be a refusal, not a column number picked by hope.
        fail(
            f"{backlog} has no table header naming an `{ITEM_COLUMN}` column, so the cell that "
            f"states live work cannot be located and the finished-work direction cannot run."
        )

    rows = []
    for line in lines:
        m = ROW.match(line)
        if not m:
            continue
        cells = line.split("|")
        if len(cells) <= item_index:
            fail(
                f"{backlog}: row {m.group(1)} has {len(cells) - 2} cell(s), fewer than the "
                f"header's `{ITEM_COLUMN}` column, so its claim cannot be read."
            )
        rows.append((m.group(1), cells[item_index]))
    if not rows:
        # An empty work-set makes both loops run zero times and prints `0 row(s), no drift` at
        # exit 0 — a guard certifying a comparison it never made. check-contract-path.py:96
        # carries the same floor for the same reason.
        fail(
            f"{backlog} has no ordered rows matching `| <n> | ... |`, so nothing was compared. "
            f"Either the table is empty or its shape changed."
        )

    states = tracker_state()

    exempt, unreasoned = set(), []
    for line in section(text, NOT_PLANNED_HEADING).split("\n"):
        entry = ENTRY.match(line)
        if not entry:
            continue
        number = int(entry.group(2))
        exempt.add(number)
        # G-8: an exemption needs a stated reason, or it is a number someone added to make a
        # guard quiet. The threshold is arbitrary and deliberately low — it separates a
        # sentence from a bare citation, and nothing finer would survive being argued about.
        if len((entry.group(1) + entry.group(3)).replace("*", "").strip(" -—:")) < 20:
            unreasoned.append(number)

    # The generous region for the absent direction: every cell of every row, plus Unshaped.
    # Deliberately wider than the Item cells the finished-work direction reads below.
    cited = set()
    for line in text.split("\n"):
        if ROW.match(line):
            cited.update(int(n) for n in ISSUE.findall(line))
    cited.update(int(n) for n in ISSUE.findall(section(text, UNSHAPED_HEADING)))

    problems = []
    open_issues = sorted(n for n, s in states.items() if s == "OPEN")
    for number in open_issues:
        if number in cited or number in exempt:
            continue
        problems.append(
            f"#{number} is open and no row cites it. Either it belongs in the list, or it "
            f"belongs under `{NOT_PLANNED_HEADING}` with the reason and what would make it a row."
        )
    for position, item in rows:
        for number in sorted({int(n) for n in ISSUE.findall(item)}):
            state = states.get(number)
            if state == "CLOSED":
                problems.append(
                    f"row {position} names #{number} in its `{ITEM_COLUMN}` cell, and "
                    f"#{number} is closed. That cell states live work; move the citation into "
                    f"`Why here` if it is now history."
                )
            elif state is None:
                # `--state all` was asked for, so absence is knowledge rather than a gap: a
                # typo, a pull request number (`gh issue list` never returns one), or another
                # repository's issue. Throwing that away would leave `no drift` covering it.
                problems.append(
                    f"row {position} names #{number} in its `{ITEM_COLUMN}` cell, and this "
                    f"tracker has no such issue — a typo, a pull request number, or another "
                    f"repository's."
                )

    # An exclusion outlives the decision that made it unless something compares it, which is
    # #14's and #23's class reappearing inside the fix for it.
    for number in sorted(exempt):
        state = states.get(number)
        if state != "OPEN":
            was = "is closed" if state == "CLOSED" else "is not an issue in this tracker"
            problems.append(
                f"`{NOT_PLANNED_HEADING}` excludes #{number}, which {was}. An exclusion is a "
                f"claim about open work and stops being true when the issue does."
            )
    for number in sorted(unreasoned):
        problems.append(
            f"`{NOT_PLANNED_HEADING}` excludes #{number} with no stated reason. An exemption "
            f"without one is a number added to keep a guard quiet (G-8)."
        )

    if problems:
        print("check-backlog-tracker FAILED", file=sys.stderr)
        for p in problems:
            print(f"  {p}", file=sys.stderr)
        print(
            f"\n  The list and the tracker disagree. `sprint` records the issue numbers on the "
            f"rows it\n  takes; a merge closing an issue and an issue filed outside a grooming "
            f"belong to no\n  skill, which is why this check exists rather than an instruction.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    # The excluded issues are NAMED, not counted. A count leaves the CI log unable to say which
    # issues were waved through, and an exemption nobody can see is one nobody revisits (G-8).
    excluded = ""
    if exempt:
        excluded = (f"; excluded by `{NOT_PLANNED_HEADING}`: "
                    + ", ".join(f"#{n}" for n in sorted(exempt)))
    print(
        f"check-backlog-tracker: {len(open_issues)} open issue(s) against {len(rows)} row(s), "
        f"no drift{excluded}"
    )


if __name__ == "__main__":
    main()
