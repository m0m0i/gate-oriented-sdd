# Observations — 109-minimum-set-in-one-unit

## T1 — the four greps, recorded red against `main`

Run at `18205d5`, before any edit. Each fails for the reason the spec states, not for a setup error.

| AC | Command | Red result |
| :-- | :-- | :-- |
| AC1 | `git grep -nE "Six documents and three templates\|6つのドキュメントと3つのテンプレート"` | 3 hits — `README.md:80`, `README.ja.md:47`, `skills/init/SKILL.md:40` |
| AC2 | `` `(sprint\|clarify\|implement)` `` within the minimum-set section of each README | 0 hits in both. The three mandatory skills that produce no document are absent from the section entirely. |
| AC3 | `git grep -nicE "five documents\|5つのドキュメント"` | 0 hits. The corrected count is stated nowhere. |
| AC4 | `` `archive` `` on a line matching `optional\|opt-in\|任意` | 3 hits — the same three files, all placing `archive` in the opt-in list. |

**AC1 and AC4 hit the same three files in the same order**, which is the root cause visible in the test output: one sentence, mirrored twice. A guard comparing the three files against each other would have found them in perfect agreement. That is the evidence behind Design's no-new-guard call, and it is recorded here rather than argued, because the alternative guard is the one a reviewer is most likely to ask for.

## T1 — green

`skills/init/SKILL.md:40` rewritten to state each side in its own unit. The sentence now names the ten, names the five of them that produce no document (which is what made them uncountable in the old framing), gives five documents and three issue templates with the templates counted once, and gives the three opt-ins a reason each rather than a shared label.

### AC4's grep needed tightening, and the reason is the bug itself

The spec states AC4 as a property — `archive` named in the mandatory set and not in the optional
list — and names no command. The obvious command is line-scoped:

```sh
git grep -nE '`archive`' -- <files> | grep -iE 'optional|opt-in|任意'
```

It reports `skills/init/SKILL.md:40` as **red after the fix**, and it is wrong. That paragraph is one
physical line carrying both lists, so `archive` (mandatory, early in the line) and `opt-in` (the
other three, later in the line) co-occur with nothing between them but distance. The check
implementing AC4 is therefore clause-scoped, not line-scoped:

```sh
git grep -nPo '(opt-in|[Oo]ptional|任意)[^.。]{0,160}`archive`' -- <files>
```

`[^.。]` refuses to cross a sentence boundary in either language, so it matches only an `archive`
that is genuinely inside an opt-in clause. Verified to discriminate: it reports `init` green and both
READMEs red at the same commit, which the line-scoped form cannot do.

Worth stating plainly, because it is the same defect one level down: **a line is not a unit of
meaning here, exactly as a document was not a unit of the minimum set.** The naive grep counts the
wrong thing and reports a false failure; the old sentence counted the wrong thing and reported a
false set. Neither is a wording problem.

## T3 — the Japanese, and one amendment to AC1

The Japanese section is written as Japanese, not translated (#104's standard), and carries claims
identical to the English (C-3). Verified mechanically rather than by reading: all ten mandatory
skills and exactly the three opt-ins are named in each of the three files, and the check reports
10/10 and the same opt-in triple for `README.md`, `README.ja.md` and `skills/init/SKILL.md`.

**The diagram is byte-identical to the English one except its last line.** The aligned rows are
untouched, so the two files cannot drift apart in alignment. Only the free-floating caption is
Japanese — `必須だがドキュメントを作らない:` — because it is a sentence rather than a label, and it
sits below everything the alignment depends on. `issue templates: feature / bug / chore` stays
English, which is what the section already did before this change.

**AC1 was amended during this task**, and it is the more interesting half of T3. Its exclusion list
named `.specs/_archive/` and `.work_logs/`, and the grep then failed on `.specs/109-.../spec.md`
and this file — both of which quote the false wording, because a bug spec's Reproduction *is* the
wording. The exclusion is now `.specs/` rather than `.specs/_archive/`, on #102's principle:
rewriting a record to satisfy a later check destroys its value as evidence. The intent did not
move — the claim is gone from every file that asserts it, which is what AC1 was always for.

Worth noting for the reviewer, since it is the shape that usually deserves suspicion: this widens a
test's exclusion mid-implementation, which is how a fail-open normally gets introduced. What makes
it sound here is that the excluded files do not assert the claim in the repository's voice — they
quote it as the defect under repair — and the narrower `':!.specs'` still fails loudly if the
wording returns to `README.md`, `README.ja.md` or `skills/init/SKILL.md`. Verified: the grep is red
at `main` and green at HEAD with the same exclusion.

## Review round 1 — BLOCKED, 0 blockers, 2 HIGH, 2 MEDIUM, 2 LOW

Reviewed at `1c7f32a`, `reviewed_by=subagent`. Both HIGH findings were in the **evidence**, not the
artifact — the READMEs and `init` were already correct. That is worth stating plainly: the fix was
right and the proof of it was not, which is the harder half to notice.

### HIGH 1 — AC4's recorded check was direction-dependent, and green on the root-cause file

The check was `(opt-in|[Oo]ptional|任意)[^.。]{0,160}` + `` `archive` ``, which matches only when the
opt-in cue comes **before** `archive`. At `main` the two READMEs phrase it that way and hit. The
upstream sentence does not:

```
main:skills/init/SKILL.md:40  … `northstar`, `epics`, `contract`, and `archive` are opt-in.
```

`archive` precedes the cue, so the file **this entire spec exists to repair** was green under AC4's
own check. Worse, the demonstration recorded above — "reports `init` green and both READMEs red" —
was taken *after* `init` was fixed, so it showed the check agreeing with a correct file and never
showed it able to disagree with a wrong one. That is the fail-open shape `.steering/product.md`
names, one level down in the evidence: a check indistinguishable from a working one.

**Corrected**, in two halves, because one direction of grep cannot carry this:

- **(a) negative, bidirectional and sentence-scoped** — no sentence in any of the three files puts
  `archive` in an opt-in clause in *either* order, with a carve-out for negation (`not opt-in`,
  `ではありません`), which HEAD needs because both READMEs now say in prose that `archive` is *not*
  opt-in.
- **(b) positive** — `archive` appears inside an enumerated mandatory set in all three files. This
  is direction-free and is the assertion AC4 actually makes.

| Ref | (a) opt-in-clause hits | (b) mandatory-set files | AC4 |
| :-- | :-- | :-- | :-- |
| `main` | **3** — all three files, `init` included | 0/3 | **RED** |
| `HEAD` | 0 | 3/3 | **GREEN** |

The check now goes red on the file it was previously blind to. **The negation carve-out was
mutation-tested rather than assumed:** disabling it leaves `main` at 3 hits — unchanged, so it
suppresses nothing there — and moves `HEAD` from 2 to 0, those 2 being exactly the two negation
sentences. A carve-out that cannot alter the failing case is a carve-out that cannot hide the bug.

### HIGH 2 — AC5's evidence named no command (C-1)

"Verified mechanically rather than by reading" claimed a result and cited nothing, while AC1 and AC4
in the same file are written out as commands. The command is recorded here instead. It enumerates
the skills on disk, then the skills named in each file's section, and asserts set equality:

```python
TEN = {"init","prd","design-doc","backlog","sprint","spec","clarify","implement","worklog","archive"}
OPT = {"northstar","epics","contract"}
# skills on disk, from git rather than the filesystem
disk = {d.split("/")[1] for d in
        subprocess.run(["git","ls-tree","-d","--name-only","HEAD","skills/"],
                       capture_output=True, text=True).stdout.split() if "/" in d}
assert disk == TEN | OPT                      # 13 on disk, and they are these 13
for path, head in (("README.md","## The minimum set"),
                   ("README.ja.md","## 最小構成"),
                   ("skills/init/SKILL.md", None)):   # None -> line 40, the upstream sentence
    named = set(re.findall(r"[a-z][a-z-]+", section(path, head))) & (TEN | OPT)
    assert named & TEN == TEN and named & OPT == OPT  # all ten, exactly those three
```

Result: `disk == TEN | OPT` true at 13, and `parity=True` for all three files.

### MEDIUM 1 — C-8, the AC1 amendment landed with the artifact it judges

`a827e84` carries the AC1 hunk **and** `README.ja.md` (covered by AC1's grep) **and** this file
(newly exempted by the widening). AC1's tick therefore cannot be read as an independent check.

**Accepted, not fixed, and deliberately not rewritten.** The branch is unpushed, so the commit could
be split — but C-8 protects the *evidence trail*, and rewriting history to make a process defect
disappear from it is the same move as rewriting a record to satisfy a later check, which #102
settled against. The reviewer's own guidance is to note it and split going forward. Noted here, and
observed for the rest of this branch: round 2 changes no AC line, so it raises no new C-8 exposure.
`#61`'s `67befe3` is the shape to copy next time.

### MEDIUM 2 — `epics` contradicted the rule twenty lines above it — fixed

`README.md:74` says an inception skill terminates in something mechanical "or it does not ship", and
lists four skills, pointedly not `epics`. The new opt-in table then said `epics` is consumed by
nothing. Both cannot read as true. The fact is pre-existing and recorded in `.steering/product.md`,
so the diff surfaced it rather than caused it — but it published the contradiction. Now
"nothing consumes it mechanically **yet** — the gap is #22, not a decision", and the mirror at
`README.ja.md` (C-3).

### LOW 1 — the diagram's rows were unlabelled, and its caption implied a falsehood — fixed

Two defects in one picture. The rows carried no labels, so `prd` over `PRD` left the reader to infer
which row was which — and the approved clarification chose this diagram precisely so the picture
would not need the prose. They are now `skill:` and `produces:`. Separately the caption read
"also mandatory, producing no document", which sets up a contrast that is false for `sprint` and
`implement` directly above it, implying seven documents against the prose's five. Now
"also mandatory, off the chain", which is true of exactly the three it names.

Alignment was re-verified after adding the 11-character label gutter: `↓` at columns 1, 10, 22, 31,
38, 45, 54 in both READMEs, matching the node centres, and the two files stay byte-identical through
every aligned row.

### LOW 2 — the availability fact was fixed only downstream — fixed

Both READMEs stated that every skill is always available; `skills/init/SKILL.md:40`, the source they
mirror, did not. That is this bug's own shape inverted — the render asserting what the source is
silent on — and the reader who suffers it is the model running `init`. The clause is now in the
upstream sentence too.

### Also corrected, from the reviewer's spec-conformance note

AC3's recorded grep (`five documents|5つのドキュメント`) could not match the Japanese, which reads
`ドキュメントは**5つ`. It under-reported 2/3 while the criterion was met in all three — over-strict
rather than fail-open, the harmless direction, but it is still a check that does not check what it
says. Corrected pattern `five documents|ドキュメントは\*\*5つ|5つのドキュメント`: 1/1/1 across the
three files.
