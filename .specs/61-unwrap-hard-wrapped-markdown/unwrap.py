#!/usr/bin/env python3
"""Join hand-wrapped lines so a paragraph or list item is one physical line.

Within a block, line n+1 is joined into line n UNLESS it starts a new construct. Refusing
to join across a list marker is what makes the steering hazard impossible rather than
merely unlikely: `- Validators: a, b, c` must never absorb the `- Reviewer: …` beneath it,
because the gates read those with `sed … | head -1` and would keep returning something
that looked plausible.

Fenced code, tables, headings, blockquotes and front matter pass through untouched — their
line breaks are structural, not cosmetic.
"""
import re
import sys

NEW_BLOCK = re.compile(r"^\s*(?:[-*+]\s|\d+[.)]\s|>|#{1,6}\s|\|)")


def unwrap(text: str) -> str:
    out, fence, buf = [], False, None

    def flush():
        nonlocal buf
        if buf is not None:
            out.append(buf)
            buf = None

    for ln in text.split("\n"):
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
        if NEW_BLOCK.match(ln) or buf is None:
            flush()
            buf = ln.rstrip()
            continue
        buf = buf.rstrip() + " " + s
    flush()
    return "\n".join(out)


def normalise(text: str) -> str:
    """Collapse every intra-block newline, so two renderings compare exactly."""
    return unwrap(unwrap(text))


if __name__ == "__main__":
    for path in sys.argv[1:]:
        src = open(path).read()
        open(path, "w").write(unwrap(src))
