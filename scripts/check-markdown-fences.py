#!/usr/bin/env python3
"""Fail when a ```markdown fence hand-wraps the Markdown it quotes.

`CONTRIBUTING.md` says a paragraph is one line and the reader's app decides the width. It
used to carve out "fenced code", which states the exemption by DELIMITER when the property
that decides it is CONTENT. A fence is a quoting mechanism; its language tag already says
what it quotes. So a ```markdown fence holding prose was exempt on the same footing as one
holding Python, and the convention — applied correctly, by reading it — restored the very
wrapping #61 removed. That is #64.

The fences this does NOT read are the point of the carve-out that remains: the receipt block
in `skills/implement/SKILL.md` and the `[SEVERITY] <file>:<line>` format in
`agents/_shared/reviewer-contract.md` are untagged, and a line break in them is meaningful.
Keying on the language tag is what separates those from prose mechanically, rather than by
asking "does this look like code".

THE PREDICATE, stated positively so it can be argued with:

    Inside a ```markdown fence, no line is a continuation of the line above it.

A line is a CONTINUATION when it is non-blank, the line above it is non-blank and did not
CLOSE a block, and the line itself OPENS no construct.

Two properties of stating it this way, and both are answers to what #61 cost.

It shares NO code with `.specs/61-.../unwrap.py`. That branch's first verifier compared
`unwrap(unwrap(x))` against `unwrap(x)` — true by construction for any idempotent transform,
destructive ones included — and reported "0 changes" on a diff that broke three issue
templates. A guard that asks "would the transform join this?" inherits every bug the
transform has. This one parses independently and asserts a property of the text.

And it clears `skills/contract/SKILL.md:47-48` for a REASON rather than by exception. Those
are two separate instructions to the skill, one per line, and `unwrap.py` folds them into
one — so the naive predicate produces a false accusation on a shipped file today. Both lines
begin `<`, which opens a template slot, so neither is a continuation. `observations.md` names
the trap this avoids: a self-test proves the checker catches the class of defect its author
imagined, and an exception carved to make a count come out right is that trap wearing a hat.

Its limit, recorded rather than papered over: a hand wrap whose continuation happens to begin
`<` is invisible to it. Not present in the tree, and contrived to produce.

WHAT IT DOES NOT CHECK: whether the Markdown inside a fence is any good, or how long a line
is. A guard on prose has to stay narrow or the prose stops being editable, and prose that
cannot be edited rots — the same argument `check-templates.py` makes about its own scope.
"""

import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

#: The language tags that mean "this fence quotes Markdown". `md` is not used in the tree
#: today; it is accepted so that writing it does not silently buy an exemption.
MARKDOWN_TAGS = ("markdown", "md")

#: A fence delimiter: three or more backticks or tildes, optionally indented, with an
#: optional info string. Both families are recognised because a nested fence written with the
#: other one is exactly the case this must refuse to guess about.
FENCE = re.compile(r"^(\s*)(`{3,}|~{3,})\s*(\S*)")

#: A line that OPENS a construct, and so cannot be a continuation of the line above it.
OPENER = re.compile(
    r"^\s*(?:"
    r"#{1,6}(?:\s|$)"          # ATX heading
    r"|[-*+](?:\s|$)"          # bullet
    r"|\d+[.)](?:\s|$)"        # ordered item
    r"|\|"                     # table row
    r"|>"                      # block quote
    r"|-{3,}\s*$"              # thematic break
    r"|\{\{[^}]*\}\}\s*$"      # a substitution slot, alone on its line
    r"|<"                      # a template placeholder — `<the thing you write here>`
    r")"
)

#: A line after which the next line ALWAYS starts fresh, so a paragraph may legitimately
#: begin under it with no blank line between. A list item is deliberately NOT here: an item
#: can be continued, and a continued item is precisely the defect being caught.
CLOSER = re.compile(r"^\s*(?:#{1,6}(?:\s|$)|\||-{3,}\s*$)")


class Unclassifiable(Exception):
    """A fence this guard will not guess about. Raised, never swallowed — see #16."""


def markdown_fences(text: str):
    """Yield (open_line_1based, [body lines]) for every ```markdown fence.

    Raises Unclassifiable for a nested fence inside a Markdown body or a fence left open at
    end of file. Neither exists in the tree today; both would make the body's structure a
    guess, and a guard that guesses is a guard that fails open.
    """
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        m = FENCE.match(lines[i])
        if not m:
            i += 1
            continue
        delim, tag = m.group(2), m.group(3).lower()
        opened_at, body = i + 1, []
        i += 1
        closed = False
        while i < len(lines):
            c = FENCE.match(lines[i])
            if c and c.group(2)[0] == delim[0] and len(c.group(2)) >= len(delim) and not c.group(3):
                closed = True
                i += 1
                break
            if c and tag in MARKDOWN_TAGS:
                raise Unclassifiable(
                    f"line {i + 1}: a fence opens inside the ```{tag} fence at line {opened_at}. "
                    "Its body's structure cannot be determined without guessing."
                )
            body.append(lines[i])
            i += 1
        if not closed:
            raise Unclassifiable(f"line {opened_at}: fence is never closed")
        if tag in MARKDOWN_TAGS:
            yield opened_at, body


def continuations(body, first_line):
    """1-based line numbers, in the whole file, of every continuation line in a fence body."""
    hits = []
    prev = None  # the previous non-empty line, or None when a block boundary intervened
    for offset, line in enumerate(body):
        if not line.strip():
            prev = None
            continue
        if prev is not None and not OPENER.match(line):
            hits.append(first_line + 1 + offset)
        prev = None if CLOSER.match(line) else line
    return hits


def blocks(hits):
    """Runs of consecutive line numbers. A wrapped paragraph is one block, however long."""
    return 1 + sum(1 for a, b in zip(hits, hits[1:]) if b != a + 1) if hits else 0


def _selftest_failed(why: str, detail: str = "") -> None:
    """Refuse to run. Deliberately not `assert`: `python -O` strips those, and a guard whose
    safety checks vanish under a flag is a guard that fails open. That is #28, and
    `test-gates.sh` pins it for every script in scripts/, assets/ and hooks/.
    """
    print(f"check-markdown-fences SELFTEST FAILED — {why}", file=sys.stderr)
    if detail:
        print(f"  {detail}", file=sys.stderr)
    print("  This guard will not check anything until it can prove it still works.", file=sys.stderr)
    sys.exit(1)


#: (expected continuation lines, fixture, what a mismatch would mean).
#:
#: Both directions, because a checker that only proves it FIRES has proved half of what
#: matters — the half that keeps it useful is that it stays quiet on the shapes these fences
#: legitimately use. Every fixture is a real shape lifted from the tree, not one invented to
#: pass: a fixture written to satisfy the checker proves only that its author imagined the
#: defect, which is the trap `.specs/61-.../observations.md` records.
SELFTEST_CASES = (
    ([2], "- Ordered, not prioritized. Position reflects value\n  together. There is no field.",
     "cannot detect a continued list item — the defect this exists for"),
    ([2], '- **Root cause:** <the mechanism. Not "a null check"\n  but why the value was null.>',
     "cannot detect a continued placeholder"),
    ([2, 3], "Items that cannot be ordered yet.\nqueue to empty, not a tier\ndoes not get built.",
     "cannot detect a wrapped paragraph"),
    ([], "<what the formatter owns>\n<what it does not own>",
     "false-accuses two sibling placeholder lines — skills/contract/SKILL.md:47-48, the "
     "counter-example that a naive 'would unwrap.py join it?' predicate gets wrong"),
    ([], "## Unshaped\nItems that cannot be ordered yet.",
     "false-accuses a paragraph opening directly under a heading"),
    ([], "- one\n- two\n1. three", "false-accuses sibling list items"),
    ([], "| a | b |\n| :-- | :-- |\nWhen two conflict, the higher one wins.",
     "false-accuses a table row or the paragraph after one"),
    ([], "- an item\n\nA new paragraph.", "false-accuses across a blank line"),
)


def selftest():
    """Runs first and unconditionally, on both the firing and the quiet direction."""
    for expected, fixture, why in SELFTEST_CASES:
        got = continuations(fixture.split("\n"), 0)
        if got != expected:
            _selftest_failed(why, f"expected {expected}, got {got}, on: {fixture!r}")

    # The language tag decides which fences are read, and nothing else. The receipt block in
    # skills/implement/SKILL.md and the [SEVERITY] <file>:<line> format in the reviewer
    # contract are untagged, and unwrapping either would destroy a line-sensitive format.
    if list(markdown_fences("```\nreviewed_sha=<sha>\nreviewer=<name>\n```\n")):
        _selftest_failed("reads an untagged fence — the receipt block and finding format must stay exempt")
    if len(list(markdown_fences("```markdown\n- a\n```\n"))) != 1:
        _selftest_failed("does not read a ```markdown fence at all")

    # A fence it cannot classify must raise rather than guess. Neither shape exists in the
    # tree; both would make a body's structure a guess, and a guard that guesses fails open.
    for bad, why in (("```markdown\n- a\n", "an unclosed fence"),
                     ("```markdown\n```python\nx\n```\n```\n", "a nested fence")):
        try:
            list(markdown_fences(bad))
        except Unclassifiable:
            continue
        _selftest_failed(f"does not refuse {why} — it guessed instead")

    print("selftest: fires on wrapped prose, stays quiet on sibling slots, headings, tables and untagged fences")


def tracked_markdown():
    out = subprocess.run(["git", "ls-files", "-z", "*.md"], cwd=ROOT, capture_output=True, text=True)
    if out.returncode:
        print("check-markdown-fences: `git ls-files` failed; cannot determine the work-set", file=sys.stderr)
        sys.exit(1)
    return [f for f in out.stdout.split("\0") if f]


if __name__ == "__main__":
    selftest()
    listing = "--list" in sys.argv[1:]

    fences = 0
    findings = []   # (path, [line numbers])
    for rel in tracked_markdown():
        path = ROOT / rel
        try:
            text = path.read_text()
        except OSError as exc:
            # Existence is not readability. A guard that cannot read its subject must fail
            # rather than report success about a file it never opened. See #16.
            print(f"check-markdown-fences: {rel} exists but cannot be read: {exc}", file=sys.stderr)
            sys.exit(1)
        try:
            found = list(markdown_fences(text))
        except Unclassifiable as exc:
            print(f"check-markdown-fences FAILED — {rel}:{exc}", file=sys.stderr)
            print("", file=sys.stderr)
            print("  This guard will not guess at a fence's structure. Rewrite the nesting, or", file=sys.stderr)
            print("  teach this script the case deliberately — do not let it pass by accident.", file=sys.stderr)
            sys.exit(1)
        for opened_at, body in found:
            fences += 1
            hits = continuations(body, opened_at)
            if hits:
                findings.append((rel, opened_at, hits))

    if fences == 0:
        # An empty work-set must not report success. "Verified everything" and "read nothing"
        # sharing an exit code is #16, #39, and the fourth fail-open #61's own verifier
        # shipped — in the tool written to police exactly that.
        print("check-markdown-fences FAILED — no ```markdown fence was found anywhere.", file=sys.stderr)
        print("  This guard read nothing, which is not the same as finding nothing wrong.", file=sys.stderr)
        sys.exit(1)

    if listing:
        total_blocks = sum(blocks(h) for _, _, h in findings)
        total_lines = sum(len(h) for _, _, h in findings)
        print(f"| File | Fence | Blocks | Lines |")
        print(f"| :-- | --: | --: | :-- |")
        for rel, opened_at, hits in findings:
            print(f"| `{rel}` | :{opened_at} | {blocks(hits)} | {', '.join(str(h) for h in hits)} |")
        print(f"\n{total_blocks} block(s) over {total_lines} line(s) in {len({f for f, _, _ in findings})} file(s),")
        print(f"out of {fences} ```markdown fence(s) scanned.")

    if findings:
        n_blocks = sum(blocks(h) for _, _, h in findings)
        n_lines = sum(len(h) for _, _, h in findings)
        print(f"check-markdown-fences FAILED — {n_blocks} hand-wrapped block(s) over {n_lines} line(s) "
              f"inside ```markdown fence(s)", file=sys.stderr)
        for rel, opened_at, hits in findings:
            print(f"  {rel} (fence at :{opened_at})", file=sys.stderr)
            for h in hits:
                print(f"    :{h}", file=sys.stderr)
        print("", file=sys.stderr)
        print("  A ```markdown fence quotes Markdown, so the Markdown inside it follows the", file=sys.stderr)
        print("  repository's convention: a paragraph is one line and the reader's app decides", file=sys.stderr)
        print("  the width. Join each line above onto the one before it.", file=sys.stderr)
        print("  A fence holding literal code, output, or a line-sensitive format is exempt —", file=sys.stderr)
        print("  that is what the language tag is for. See CONTRIBUTING.md and #64.", file=sys.stderr)
        sys.exit(1)

    print(f"check-markdown-fences: {fences} ```markdown fence(s), no hand-wrapped prose")
