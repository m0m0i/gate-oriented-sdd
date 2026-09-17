#!/usr/bin/env python3
"""AC4 and AC5: the minimum set, partitioned per file, from markup rather than proximity.

    ./verify.py                  # the working tree — expect GREEN
    ./verify.py main:red -:green  # each ref with the verdict it must produce

Every ref may carry an expected verdict (`:red` / `:green`, default `green`), and the exit code
is 0 only when every ref matched what was expected. Without that, the documented two-ref form —
whose whole point is that `main` is RED — would exit non-zero on a perfectly correct tree.

AC4 wants two things of every file that states the set: `archive` is named in the mandatory
enumeration, and it is not in the opt-in list. AC5 wants the three files to agree. Both fall
out of one assertion per file — `seen == ALL and optin == OPT and archive in mandatory` —
so the two criteria cannot disagree about what they read.

Three rounds of review were spent on greps that each had a blind spot: direction (round 1),
markup (round 2), and sentence scope (round 3). What survives is documented under RESIDUAL.
"""
import re, subprocess, sys

TEN = {"init","prd","design-doc","backlog","sprint","spec","clarify","implement","worklog","archive"}
OPT = {"northstar","epics","contract"}
ALL = TEN | OPT
FILES = ("README.md", "README.ja.md", "skills/init/SKILL.md")
HEADS = {"README.md": "## The minimum set", "README.ja.md": "## 最小構成"}

CUE  = r"opt-in|[Oo]ptional|任意"
MAND = r"mandatory|必須|minimum install|最小構成に入る"

#: A negated mandatory-cue must not read as a mandatory declaration — the mirror of NEG, on the
#: clearing side. Bound to the CUE, never to the sentence: the Japanese caption
#: 「必須だが、チェーンには出てこない」 contains 「ない」 and is that file's ONLY archive-mandatory
#: declaration, so a blanket negation filter would turn a correct README.ja.md red.
#: Every cue in MAND needs a negated form here, or the ones left out can be negated freely —
#: a guard's exemption list is part of the guard. `\W{0,4}` carries across the same bolding
#: tolerance NEG needed: in NEG a bolded negation caused a false RED, here it causes a false
#: GREEN, so it is load-bearing rather than cosmetic. `\b` keeps `cannot` from supplying a `not`.
NEG_MAND = (r"\b(?:no longer|not|never|isn't)\b\W{0,4}(?:\w+\s+){0,2}(?:mandatory|minimum install)"
            r"|(?:必須|最小構成に入る)(?:わけ)?\s*(?:ではあ?りません|ではない|ではなく|から外)")

#: Split at sentence-FINAL punctuation only. `。` always ends one; `.` only when a sentence
#: starts after it — otherwise "e.g." and "0.5.1" break a sentence apart and strand the cue
#: from the name it governs, which returns a false green.
SENT = r"(?<=。)\s*|(?<=\.)\s+(?=[A-Z`|#*\-]|$)"

#: A negation clears a name only when it negates THAT NAME'S ROLE. Binding to the name alone is
#: not enough: `archive` は任意扱いで、必須ではありません asserts the defect and negates something
#: else, so the cue must sit INSIDE the window, not outside it. `\W{0,4}` lets the English form
#: survive the bolding this repo's prose favours — `is **not** opt-in`.
NEG = (r"`{n}`\s*is[^.。]{{0,8}}not\W{{0,4}}opt-in"
       r"|`{n}`\s*は[^.。]{{0,12}}(任意|opt-in)[^.。]{{0,4}}ではありません")

def text(ref, path):
    """The file's content, or None when the ref could not be read at all.

    None is NOT the same as empty. An unresolvable ref — a clone whose default branch is
    `master`, a deleted or renamed branch, a shallow clone, a typo — gives returncode 128 and
    empty stdout. Read as empty, that reports RED, which a `:red` expectation then ACCEPTS,
    so the run exits 0 having looked at nothing. Not finding a problem and not having looked
    must not share an outcome, so unreadable is a third verdict that matches no expectation."""
    if ref is None:
        return open(path).read()
    r = subprocess.run(["git","show",f"{ref}:{path}"], capture_output=True, text=True)
    return None if r.returncode != 0 else r.stdout

def section(body, path):
    head = HEADS.get(path)
    if head is None:                      # skills/init/SKILL.md — the one upstream sentence
        for line in body.split("\n"):
            if line.startswith("**Scaffold the mandatory set"):
                return line
        return ""
    out, on = [], False
    for line in body.split("\n"):
        if line.strip() == head: on = True; continue
        if on and line.startswith("## "): break
        if on: out.append(line)
    return "\n".join(out)

def names(s):
    return {n for n in re.findall(r"[a-z][a-z-]+", s)} & ALL

def optin(sec):
    """Names declared opt-in — from the data rows of a table whose header carries the cue,
       and from prose in either direction, minus negations bound to the name's own role."""
    found, in_table = set(), False
    for line in sec.split("\n"):
        if line.startswith("|") and re.search(CUE, line):       # the table's header row
            in_table = True; continue
        if in_table:
            if not line.startswith("|"): in_table = False
            elif not re.match(r"^\|\s*:?-{2,}", line):
                found |= names(line.split("|")[1])              # first cell holds the skill
    for para in sec.split("\n"):
        if para.startswith("|"): continue                       # tables handled above
        for s in re.split(SENT, para):
            if not s.strip() or not re.search(CUE, s): continue
            for n in names(s):
                if not re.search(NEG.format(n=re.escape(n)), s):
                    found.add(n)
    return found

def mandatory(sec):
    """Names sitting in an enumeration that declares them mandatory. Asserted directly rather
       than derived as ALL - OPT: the derivation is only valid while every name appears in a
       declared role, and nothing detects that premise being lost."""
    found = set()
    for para in sec.split("\n"):
        for s in re.split(SENT, para):
            if re.search(MAND, s) and not re.search(NEG_MAND, s):
                found |= names(s)
    return found

def check(ref):
    print(f"--- {ref or 'working tree'} ---")
    bodies = {path: text(ref, path) for path in FILES}
    missing = [p for p, b in bodies.items() if b is None]
    if missing:
        print(f"  UNREADABLE at this ref: {', '.join(missing)}")
        print("  AC4/AC5: UNREADABLE\n")
        return "unreadable"
    ok = True
    for path in FILES:
        sec = section(bodies[path], path)
        seen, opt, mand = names(sec), optin(sec), mandatory(sec)
        good = seen == ALL and opt == OPT and "archive" in mand
        ok &= good
        print(f"  {path:<22} named {len(seen):>2}/13  opt-in {sorted(opt)}")
        print(f"  {'':<22} archive: mandatory={'archive' in mand!s:<5} opt-in={'archive' in opt!s}"
              f"   -> {'ok' if good else 'FAIL'}")
        if not good and seen != ALL:
            print(f"  {'':<22} not named: {sorted(ALL - seen)}")
    print(f"  AC4/AC5: {'GREEN' if ok else 'RED'}\n")
    return "green" if ok else "red"

if __name__ == "__main__":
    args = sys.argv[1:] or ["-"]
    ok = True
    for arg in args:
        ref, _, want = arg.partition(":")
        want = want or "green"
        got = check(None if ref == "-" else ref)
        if got != want:
            print(f"  MISMATCH: {ref or 'working tree'} expected {want}, got {got}")
            ok = False
    sys.exit(0 if ok else 1)
