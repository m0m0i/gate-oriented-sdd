#!/usr/bin/env python3
"""Join hand-wrapped lines so a paragraph or list item is one physical line.

Within a block, line n+1 is joined into line n UNLESS it starts a new construct. Three
things pass through completely untouched, because their line breaks are structure rather
than cosmetics: YAML front matter, fenced code, and tables.

Refusing to join across a list marker is what makes the steering hazard impossible rather
than merely unlikely: `- Validators: a, b, c` must never absorb the `- Reviewer: …` line
beneath it, because the gates read those with `sed … | head -1` and would keep returning
something that looked plausible.

A heading also terminates its block. An earlier version did not, so every heading absorbed
the paragraph under it — words preserved, structure destroyed. See verify.py, which is
written to detect exactly that and originally could not.
"""
import re
import sys

# A marker may be bare: an issue template's "1." on its own line is a list item with no
# content yet, and treating it as prose merged it with the "2." beneath it.
NEW_BLOCK = re.compile(r"^\s*(?:[-*+](?:\s|$)|\d+[.)](?:\s|$)|>|#{1,6}(?:\s|$)|\|)")
#: A list marker plus its trailing space; the width of the two is the item's content column.
MARKER = re.compile(r"^(\s*)([-*+]\s+|\d+[.)]\s+)")
# A line that is only a substitution slot is structure, not prose. `agents/_template/`
# pastes a multi-line bullet list into `{{VALIDATOR_LIST}}`, so folding the slot into the
# sentence above it turns the first pasted validator into a stray nested list once the
# template is rendered. The template's own HTML is unchanged, which is why canon.py cannot
# see it: the damage is invisible until substitution.
SLOT = re.compile(r"^\s*\{\{[A-Z_]+\}\}\s*$")
# A comment delimiter is structure only when it stands ALONE. `starter.md` relies on that;
# matching a bare prefix instead made `reviewer.md`'s content-bearing `<!--` opaque, so the
# transform emitted it verbatim and left the paragraph under it hand-wrapped — in the branch
# that writes down "do not hand-wrap".
STRUCTURAL = re.compile(r"^\s*(?:#{1,6}(?:\s|$)|\||-->\s*$|<!--\s*$)")


def unwrap(text: str) -> str:
    lines = text.split("\n")
    out, fence, buf = [], False, None
    open_cols = []  # content columns of the currently open list items, outermost first
    i = 0

    # YAML front matter: verbatim, including its internal line breaks.
    if lines and lines[0].strip() == "---":
        for j in range(1, len(lines)):
            if lines[j].strip() == "---":
                out.extend(lines[: j + 1])
                i = j + 1
                break

    def flush():
        nonlocal buf
        if buf is not None:
            out.append(buf)
            buf = None

    while i < len(lines):
        ln = lines[i]
        i += 1
        if ln.strip().startswith("```"):
            flush()
            fence = not fence
            out.append(ln)
            continue
        if fence:
            out.append(ln)
            continue
        s = ln.strip()
        if not s or s == "---":
            flush()
            open_cols = []
            out.append(ln)
            continue
        if STRUCTURAL.match(ln) or SLOT.match(ln):
            flush()
            out.append(ln.rstrip())
            continue
        if (m := MARKER.match(ln)):
            flush()
            col = len(m.group(1)) + len(m.group(2))
            while open_cols and open_cols[-1] > col:
                open_cols.pop()
            if not open_cols or open_cols[-1] != col:
                open_cols.append(col)
            buf = ln.rstrip()
            continue
        if NEW_BLOCK.match(ln) or buf is None:
            flush()
            open_cols = []
            buf = ln.rstrip()
            continue
        # A continuation sitting at an ENCLOSING item's content column belongs to that outer
        # item. `skills/sprint/SKILL.md` closes a three-item sub-list with a sentence
        # summarising all three, at the parent item's column; joining it attached the summary
        # to the third seam alone. CommonMark renders both the same way, which is why canon.py
        # cannot see it — the reader that suffers is the model reading skills/ as source.
        #
        # Deliberately "equals an enclosing column" and not "less than the current one": a
        # continuation at column 0 under an indented item is usually a plain hard wrap that
        # SHOULD join — `.specs/55-.../spec.md` puts one there so a code span does not gain a
        # stray space — and the broader test refused it, leaving the transform unable to
        # reproduce its own output.
        ind = len(ln) - len(ln.lstrip())
        if any(c == ind for c in open_cols[:-1]):
            flush()
            buf = ln.rstrip()
            continue
        buf = buf.rstrip() + " " + s
    flush()
    return "\n".join(out)


if __name__ == "__main__":
    for path in sys.argv[1:]:
        src = open(path).read()
        open(path, "w").write(unwrap(src))
