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
# A line that is only a substitution slot is structure, not prose. `agents/_template/`
# pastes a multi-line bullet list into `{{VALIDATOR_LIST}}`, so folding the slot into the
# sentence above it turns the first pasted validator into a stray nested list once the
# template is rendered. The template's own HTML is unchanged, which is why canon.py cannot
# see it: the damage is invisible until substitution.
SLOT = re.compile(r"^\s*\{\{[A-Z_]+\}\}\s*$")
STRUCTURAL = re.compile(r"^\s*(?:#{1,6}(?:\s|$)|\|)")


def unwrap(text: str) -> str:
    lines = text.split("\n")
    out, fence, buf = [], False, None
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
            out.append(ln)
            continue
        if STRUCTURAL.match(ln) or SLOT.match(ln):
            flush()
            out.append(ln.rstrip())
            continue
        if NEW_BLOCK.match(ln) or buf is None:
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
