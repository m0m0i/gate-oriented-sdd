#!/usr/bin/env python3
"""A canonical form that shares NO code with the transform it checks.

The first version of this check was `unwrap(unwrap(x))` compared against `unwrap(x)`, which
holds by construction for any idempotent transform — destructive ones included. It passed a
change that collapsed three issue templates' front matter and merged every heading into the
paragraph beneath it, because it re-applied the very rule whose bug it was meant to catch.

So this parses independently and compares five things a reflow must never alter:

    front matter, verbatim
    fenced code blocks, verbatim
    heading lines, verbatim and in order
    table rows, verbatim and in order
    the token stream of everything else, where each paragraph or list item contributes a
    boundary marker followed by its words

A heading that absorbs a paragraph changes the heading list. A list item that absorbs its
sibling loses a boundary marker. Front matter that collapses changes the front matter. None
of those alters the word multiset, which is why comparing words alone is not enough.
"""
import re

HEADING = re.compile(r"^\s*#{1,6}(?:\s|$)")
TABLE = re.compile(r"^\s*\|")
ITEM = re.compile(r"^\s*(?:[-*+](?:\s|$)|\d+[.)](?:\s|$)|>)")
#: A standalone substitution slot is its own structural unit, so folding one into the
#: sentence above it is visible here rather than only after the template is rendered.
SLOT = re.compile(r"^\s*\{\{[A-Z_]+\}\}\s*$")


def canon(text: str):
    lines = text.split("\n")
    front, fences, heads, tables, tokens = [], [], [], [], []
    i, fence, cur = 0, False, None

    if lines and lines[0].strip() == "---":
        for j in range(1, len(lines)):
            if lines[j].strip() == "---":
                front = [l.rstrip() for l in lines[1:j]]
                i = j + 1
                break

    def close():
        nonlocal cur
        if cur:
            tokens.append(cur)
            cur = None

    while i < len(lines):
        ln = lines[i]
        i += 1
        if ln.strip().startswith("```"):
            close()
            fence = not fence
            fences.append(ln.rstrip())
            continue
        if fence:
            fences.append(ln.rstrip())
            continue
        s = ln.strip()
        if not s or s == "---":
            close()
            continue
        if HEADING.match(ln):
            close()
            heads.append(s)
            continue
        if TABLE.match(ln):
            close()
            tables.append(s)
            continue
        if SLOT.match(ln):
            close()
            heads.append(s)
            continue
        if ITEM.match(ln):
            close()
            cur = ["<ITEM>"] + s.split()
            continue
        if cur is None:
            cur = ["<PARA>"] + s.split()
        else:
            cur += s.split()
    close()
    return (front, fences, heads, tables, tokens)
