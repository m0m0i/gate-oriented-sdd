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

> **Withdrawn in round 1 of review — see "HIGH 1" below.** The clause above claiming this check
> "verified to discriminate" is wrong: the demonstration was taken after `init` was already fixed.
> The paragraph is left standing rather than edited, per #102; the correction is downstream.

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

Alignment was re-verified after adding the 11-character label gutter. Measured at HEAD the `↓` row
sits at **absolute columns 12, 21, 33, 42, 49, 56, 65** in both READMEs — the pre-gutter values
(1, 10, 22, 31, 38, 45, 54) shifted by exactly the 11-character gutter — and `↑` is at absolute 42,
still the centre of `Issue` at 40-44. The two files stay byte-identical through every aligned row.

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

## Review round 2 — BLOCKED, 0 blockers, 1 HIGH, 2 MEDIUM, 2 LOW

Reviewed at `7d5042c`. Round 1's two HIGHs cleared. The new HIGH is in the same layer again — the
evidence, not the artifact — and it is the third distinct blind spot found in one check. That
pattern is the finding: **AC4 was being evidenced by pattern-matching against prose, and each fix
closed one hole while leaving the shape that produces them.** Round 3 replaces the approach rather
than patching it a third time.

### HIGH — the check was line-scoped, so it could not see the opt-in table

`git grep` matches within a physical line. Both READMEs declare their opt-in list as a **table**: the
cue is in the header (`| Skill | Why it is opt-in |`), the skill name is in a data row, and the two
are different lines. So the check could not see either README's opt-in list at all — the reviewer
proved it by running the same pattern for `northstar` and `epics`, which are genuinely opt-in at
HEAD and were returned only from `skills/init/SKILL.md`.

The consequence for AC4: had `archive` come back as a row of either opt-in table, the negative check
would have stayed at 0 hits and the positive one at 3/3, because `init` and the diagram caption
still enumerate it as mandatory. **AC4 would have reported GREEN on a state where two files
contradict themselves** — and the table is the markup *this diff introduced for exactly this list*,
so it is the likeliest regression path, not a hypothetical one.

### Round 3 — one check, recorded as a command, replacing three rounds of grep

Both MEDIUMs are the same root cause as the HIGH, so all three are answered together:

- **MEDIUM 1** — the negation carve-out cleared an entire sentence on the strength of any negation,
  with nothing binding it to `archive`. Two sentences that assert the defect *and* clear it were
  supplied, one of them native to this section's own prose style.
- **MEDIUM 2** — AC5's recorded command asserted a union (all thirteen names appear somewhere) where
  AC5 claims a partition (each file agrees on which are mandatory and which are opt-in), and it was
  not runnable as written: `section()` was undefined and the `init` branch was a comment.

The replacement is one script, run at both refs, recorded here verbatim so anyone can re-run it. It
parses markup instead of matching proximity, asserts the **partition** rather than the union, and
binds a negation to the name it negates:

```python
TEN = {"init","prd","design-doc","backlog","sprint","spec","clarify","implement","worklog","archive"}
OPT = {"northstar","epics","contract"}
ALL, CUE = TEN | OPT, r"opt-in|[Oo]ptional|任意"
# split at sentence-FINAL punctuation only: 。 always; '.' only when a sentence starts after it,
# so "e.g." and "0.5.1" cannot break a sentence apart and strand the cue from the name.
SENT = r"(?<=。)\s*|(?<=\.)\s+(?=[A-Z`|#*\-]|$)"

def names(s):
    return {n for n in re.findall(r"[a-z][a-z-]+", s)} & ALL

def optin(sec):
    """Names declared opt-in: table data rows under an opt-in header, plus prose in
       either direction. A negation clears a name only when bound to that name."""
    found, in_table = set(), False
    for line in sec.split("\n"):
        if line.startswith("|") and re.search(CUE, line):        # the table's header row
            in_table = True; continue
        if in_table:
            if not line.startswith("|"): in_table = False
            elif not re.match(r"^\|\s*:?-{2,}", line):
                found |= names(line.split("|")[1])               # first cell = the skill
    for para in sec.split("\n"):
        if para.startswith("|"): continue                        # tables handled above
        for s in re.split(SENT, para):
            if not s.strip() or not re.search(CUE, s): continue
            for n in names(s):
                if re.search(rf"`{n}`\s*(is|は)[^.。]{{0,24}}(not opt-in|ではありません)", s):
                    continue                                     # negation bound to THIS name
                found.add(n)
    return found

# per file: seen == ALL and optin == OPT  =>  mandatory == TEN, and archive is in it
```

> **Superseded in round 3.** This excerpt was never runnable and the file it named was never
> committed — see "HIGH" under round 3. The real check is [`verify.py`](./verify.py) in this
> directory, and the excerpt above is retained only as the record of what round 3 inherited.

**Result.** Both AC4 and AC5 now fall out of one assertion — `seen == ALL and optin == OPT` — which
is the partition AC5 claims and which entails AC4's property.

| Ref | `README.md` | `README.ja.md` | `skills/init/SKILL.md` | Verdict |
| :-- | :-- | :-- | :-- | :-- |
| `main` | 7/13 named, opt-in includes `archive` | 7/13, same | 6/13, opt-in includes `archive` | **RED** |
| HEAD | 13/13, opt-in `{contract, epics, northstar}` | 13/13, same | 13/13, same | **GREEN** |

At `main` all three files fail, `skills/init/SKILL.md` included — the file round 1's check was blind
to — and `archive` is reported `mandatory=False opt-in=True` in every one of them.

### Mutation tests — five attacks, all caught

Assumption is what produced three rounds of this, so the check is attacked rather than trusted. Each
mutant asserts `archive` is opt-in; each must be caught.

| Mutant | Source | Caught |
| :-- | :-- | :-- |
| `archive` added as a row of README.md's opt-in **table** | round 2 HIGH | yes |
| `… and \`archive\` — the rest are not opt-in.` | round 2 MEDIUM 1 (EN) | yes |
| `任意なのは …、\`archive\` の4つで、必須ではありません。` | round 2 MEDIUM 1 (JA) | yes |
| `Optional (e.g. small repos): … \`archive\`.` | splitter evasion | yes |
| `Optional since 0.5.1: … \`archive\`.` | splitter evasion | yes |

Controls: the two legitimate negations actually in the READMEs — `` `archive` is not opt-in for
being small `` and 「`archive` は、小さいから任意、ではありません」 — both stay clear, so the
carve-out still does the job it exists for.

The last two mutants are ones the reviewer did not raise. The round-2 splitter broke a sentence at
any `.`, so `e.g.` and a version number both stranded the cue from the name and returned a false
green. Found by probing the splitter rather than by being told, and fixed in `SENT` above.

### LOW 1 — the arrow columns were quoted pre-gutter — fixed

Corrected in the round-1 section above: absolute 12, 21, 33, 42, 49, 56, 65, with the pre-gutter
values named as such.

### LOW 2 — `produces:` is an English label in the Japanese diagram — recorded, for the author

Round 1 justified `issue templates:` staying English on the grounds that the section already did
that before this change. `produces:` has no such precedent — it is new, and it is the one word in
the diagram a Japanese reader must translate. `skill:` is unremarkable, `skill` being an established
loanword in this README (`skill が13個…`).

The argument for leaving it: both READMEs stay byte-identical through every aligned row, so the two
diagrams cannot drift apart in alignment, and that property has already caught one error in this
branch. The argument against: it is a Japanese-wording call in a file whose whole standard (#104,
#90) is that it reads as Japanese rather than as a translation.

**Left as `produces:` and flagged for the author's judgment rather than decided here**, since the
Japanese README is theirs to call. `生成物:` is the obvious alternative and is the same display width
in a monospace font only if the gutter is re-measured — the aligned rows would need regenerating,
which is mechanical.

### Also from round 2's INFO

- A forward pointer now sits at the round-1 AC4 paragraph, marking it withdrawn and naming where.
  The paragraph itself stays, per #102.
- The eight AC checkboxes still read `[ ]` under `Status: done`. The reviewer found the convention
  mixed across archived specs and `skills/implement/SKILL.md` silent on it. Ticked in the
  post-receipt step, with the version bump.

## Review round 3 — BLOCKED, 0 blockers, 1 HIGH, 3 MEDIUM, 1 LOW

Reviewed at `4df1f07`. The redesign was accepted — the reviewer attacked `optin()`'s table parser
as asked and could not reach a false green through it, because `optin == OPT` is an *equality*, so
every parser failure drops all four names at once and lands red. Recording that negative result
because it is the load-bearing one.

### HIGH — the script was never committed, and the repo already had a convention for that

`observations.md` claimed the check was "recorded here verbatim so anyone can re-run it" and then
named a file that does not exist: `git ls-files | grep -i minset` returns nothing, `git status` was
clean, so it was not even untracked. What was printed was the logic, not the check — `section()`
undefined, `seen` computed nowhere, no driver — so **seven claimed results** (two refs × three
files, five mutants, two controls) rested on something nobody could execute, the reviewer included.
That is precisely the gap C-1 exists to close, and round 2's MEDIUM 2 had already named the two
missing pieces; they were left missing while more weight was piled on them.

**The repo knew the answer and this spec did not look.** Verification scripts for a spec are
committed into the spec directory: `.specs/_archive/61-unwrap-hard-wrapped-markdown/` carries four,
`64-fence-carve-out-by-delimiter/` and `66-pin-format-on-save-off-for-markdown/` carry `verify.py`.
Three call sites — convention, not preference. And #61 is the same spec already cited above as the
shape to copy for C-8, so the precedent was one directory away the whole time.

Now committed as [`verify.py`](./verify.py), matching the name those three use. AC7 already admits
"this spec directory", so no AC line moves and no C-8 exposure is created. It exits non-zero on
failure, so it is runnable in CI or by hand:

```
./.specs/109-minimum-set-in-one-unit/verify.py main -     # `main` RED, working tree GREEN
```

### MEDIUM 1 — the Japanese carve-out bound to the copula, not to the predicate — fixed

A real fail-open, and the sharpest finding of the three rounds. The carve-out was
`` `{n}`\s*(is|は)[^.。]{0,24}(not opt-in|ではありません) ``. The English branch pins the whole negated
predicate (`not opt-in`), so it is sound. The Japanese branch pinned only the copula and left the
predicate inside an unconstrained window — and `ではありません` negates whatever precedes it. So these
two were indistinguishable:

| Sentence | Means | Old carve-out |
| :-- | :-- | :-- |
| `` `archive` は、小さいから任意、ではありません `` | *not* opt-in | cleared — correct |
| `` `archive` は任意扱いで、必須ではありません `` | **is** opt-in | cleared — **wrong** |

The second carries the cue, names `archive`, and asserts the defect; clearing it leaves
`optin == OPT` intact and the check GREEN on a file that has just declared `archive` optional. Fixed
by moving the cue *inside* the window — `` `{n}`\s*は[^.。]{0,12}(任意|opt-in)[^.。]{0,4}ではありません ``
— so a negation of `必須` can no longer clear. The real sentence still clears; the defeater is now
caught.

### MEDIUM 2 — `mandatory == TEN` was derived, not observed — fixed

Round 2's positive check was dropped when the partition replaced it, on the reasoning that
`ALL - OPT` gives the mandatory set. That inference is valid only under a premise the check never
verified: **that every skill the section mentions is mentioned in a declared role.** `seen == ALL`
is pure presence. A file that drops its mandatory enumeration while still mentioning all thirteen in
passing keeps `seen == ALL and optin == OPT` true with nothing declared mandatory at all.

`mandatory()` is restored as a direct assertion, and the mutant proves the gap was real rather than
theoretical: with both of `README.md`'s mandatory declarations removed, **`seen == ALL` still
holds** while `archive in mandatory` goes false. The derivation would have passed; the direct check
fails. Asserting a premise beats deriving from it.

### MEDIUM 3 — sentence-scoped matching cannot see anaphora — recorded as a residual, not patched

Both languages can move the name out of the cue's sentence:

```
… `northstar`, `epics` and `contract` are opt-in. So is `archive`.
任意なのは `northstar`、`epics`、`contract` です。`archive` も同様です。
```

The reviewer's disposal is taken as offered, and it is the right one: **not a sixth patch.** A
prose-matching check cannot be made paraphrase-proof, and each patch has cost a review round. The
distinction that decides it: rounds 1 and 2 were green on text that *actually existed* — at `main`,
and in the markup at HEAD. This one is a string constructed to defeat it and present nowhere.

**RESIDUAL — what `verify.py` provably cannot see.** A role declared across a sentence boundary by
anaphora ("So is `archive`.", 「`archive` も同様です。」), and a role declared in markup other than a
pipe table. Both are unreachable by any amount of pattern-matching against prose, because the
information is not local to the text being matched. This is the floor of the approach, and the exit
is **#110** — once the installed set is a value the harness reads, membership stops being a
question about sentences. Recorded as a documented limit rather than chased, which is how
`.steering/product.md` already handles the `CAP-`/#22 gap.

### LOW — a bolded negation broke the carve-out — fixed

The English branch matched the literal `not opt-in`, and this section's house style bolds the key
word (`**Every skill is always available.**`, `**まだ**`, `**Ten of the thirteen**`). An editor
writing `` `archive` is **not** opt-in `` would have inserted `**` into the middle of the literal,
stopping the carve-out and turning AC4 **red on a correct file**. The safe direction, but a trap
laid in a file whose style invites it. Now `not\W{0,4}opt-in`, which survives the bolding —
tolerated on the clearing side only, which is the side `G-9` permits.

### Mutation tests — seven attacks, all caught

| Mutant | Source | Caught |
| :-- | :-- | :-- |
| `archive` as a row of README.md's opt-in **table** | r2 HIGH | yes |
| `` … and `archive` — the rest are not opt-in. `` | r2 MEDIUM (EN) | yes |
| `` 任意なのは …、`archive` の4つで、必須ではありません。 `` | r2 MEDIUM (JA) | yes |
| `` Optional (e.g. small repos): … `archive`. `` | splitter evasion | yes |
| `` Optional since 0.5.1: … `archive`. `` | splitter evasion | yes |
| `` `archive` は任意扱いで、必須ではありません。 `` | r3 MEDIUM 1 | yes |
| both mandatory declarations removed, all thirteen still named | r3 MEDIUM 2 | yes |

Controls: both real negations still clear, and a bolded `is **not** opt-in` still clears.

**One mutant was wrong on the first attempt, and it is worth recording why.** The
mandatory-dropped mutant initially edited only the diagram caption and reported MISSED. The check
was right and the mutant was not: the section declares `archive` mandatory *twice*, and the prose
sentence — "and all three are mandatory regardless" — still carried the claim. A mutant that does
not actually remove the property proves nothing about the check, and reading that MISSED as a
finding would have produced a sixth round chasing a defect that was not there.

## Review round 4 — CLEAN, 0 blockers, 0 HIGH, 2 MEDIUM (advisory)

Reviewed at `987fb97`: **CLEAN**. The HIGH cleared — `verify.py` is committed at `100755`, the same
mode as the three scripts it was modelled on, so the documented invocation actually runs. The
reviewer did **not** execute it, saying so rather than running an off-list command: its allow-list
names the nine `- Validators:` commands and a script in a spec directory is not among them. Both
MEDIUMs are therefore source audits — possible only because the file now exists, which was the
point of round 3's HIGH.

Both were advisory and neither blocked the PR. **Both are fixed anyway**, because one is a
fail-open and this repository's anchor is that gates never fail open — accepting it with a note
would have been the cheaper answer and the wrong one.

### MEDIUM 1 — `mandatory()` had no negation handling — fixed

The same defect round 3 fixed in `optin()`, left unmirrored on the other side of the conjunction.
`optin()` accuses and carries `NEG`; `mandatory()` *clears* — a hit satisfies `"archive" in mand`,
the third conjunct — and it keyed on the bare word. So a negated mandatory read as a mandatory
declaration, and a one-sentence fail-open existed in both languages with no anaphora and no exotic
markup:

| Mutation | Old result |
| :-- | :-- |
| caption drops the cue, and `README.md:94` ends `… and \`archive\` is no longer mandatory` | GREEN |
| 「`archive` は必須ではありません。」 — carries no `CUE`, so `optin()` never examines it | GREEN |

`NEG_MAND` now binds the negation to the cue: `(?:no longer|not)\s+(?:\w+\s+){0,2}mandatory` or
`(?:mandatory|必須)\s*(?:ではあ?りません|ではなく)`. Both mutants are caught and both controls stay
green.

**Bound to the cue, never to the sentence** — and the reviewer supplied the reason, which is the
part worth keeping. `README.ja.md`'s caption 「必須だが、チェーンには出てこない」 contains 「ない」
**and is that file's only `archive`-mandatory declaration**. A blanket sentence-level negation
filter would have turned a correct `README.ja.md` red. Verified after the fix: the caption survives.

That asymmetry is worth recording on its own. `README.md` declares `archive` mandatory **twice** —
the caption and the prose at `:94` — while `README.ja.md` declares it **once**, because
「それでもこの3つは必須です。」 names no skill after the sentence split. The two files are not equally
robust to a diagram edit. The direction is safe — a caption edit turns the Japanese file red, not
green — so it is a note rather than a defect.

### MEDIUM 2 — the documented invocation exited 1 on a correct tree — fixed

`sys.exit(0 if all(...) else 1)` meant "every ref was GREEN", while both recorded invocations pass a
ref that is *supposed* to be RED. Run as documented on a perfectly correct tree, the exit code was
1 — and `observations.md` then said "it exits non-zero on failure, so it is runnable in CI", which
would have put a permanently-failing command in CI. A check that fires on a correct state is one
people switch off.

Each ref now carries the verdict it must produce, and the exit code is 0 only when every ref matched:

```
./.specs/109-minimum-set-in-one-unit/verify.py main:red -:green    # exits 0
```

### On the mutant I called wrong — the reviewer checked, and it holds

Flagged for scrutiny because "the test was wrong, not the code" is the conclusion most likely to be
self-serving. Verified independently: `README.md`'s section matches `MAND` in exactly three
sentences, exactly two contain `archive`, and a mutant editing only the caption leaves the second
intact — so `MISSED` was the correct answer about a file that still declared the property. The
reviewer also looked for the failure mode that would have made the conclusion wrong — a spurious
third path putting `archive` into `mand` — and found none.

### Four rounds, and what they were actually about

**The artifact was correct after round 1.** Every finding from round 2 onward was in the evidence
layer — the checks, not the READMEs. Written down because it is the opposite of the expected shape
and it is the reusable lesson: the fix was easy and proving it was not, and each round found a way
the proof could pass while the property was false. Round 1 direction, round 2 markup, round 3
sentence scope and an uncommitted script, round 4 a negation on the clearing side. Five distinct
fail-opens in the evidence for a three-file prose change.

The exit from that regress is not a better regex. It is #110 — a machine-readable set, after which
membership stops being a question about sentences at all.

## Review round 5 — BLOCKED, 0 blockers, 1 HIGH, 1 MEDIUM, 1 LOW

Reviewed at `092badf`. **The HIGH was introduced by round 4's fix**, on the exact path the fix was
meant to improve, and it is the most instructive finding of the five rounds.

### HIGH — making the check self-testing made it fail open

Round 4 replaced `sys.exit(0 if all(check(r)) else 1)` with a per-ref expected verdict, so that
`./verify.py main:red -:green` could assert the check *can* fail — self-testing, and a direct
answer to round 1's defect, where "verified to discriminate" had been demonstrated against a file
already fixed.

`text()` discarded the subprocess return code. An unresolvable ref gives returncode 128 and empty
stdout, so `section()` returned `""`, `seen` was empty, and `check()` reported **RED**. Under round
4's exit that was harmless — the reviewer had audited it and called it fail-closed, correctly,
because red always meant exit 1. **Round 5 inverted it.** `got = "red"` now *matched* `want = "red"`,
and the run exited **0 having read nothing at `main`**.

The irony is the finding: the expectation added to prove the check can fail was satisfiable by the
check never having looked. That is round 1's defect returning at the outermost layer, and it is
`G-1`'s own worked example — `check-locks.py` printing `0 pinned file(s)` and exiting 0, #16, one of
the first five bugs filed against this repository.

It needed **no text change to reach**, unlike every finding since round 3: a clone whose default
branch is `master`, a renamed or deleted branch, a shallow clone, or a typo. `./verify.py mian:red
-:green` exited 0, and the output *reassured*, because `main` printed RED exactly as expected.

Fixed by making unreadable a **third verdict** that matches no expectation. `text()` returns `None`
on a non-zero return code — `None` is not the same as empty — and `check()` reports `unreadable`
before examining anything. Verified: `mian:red -:green` now exits 1, `main:red -:green` exits 0, and
the no-argument form exits 0.

**Red, green, and could-not-look are three things.** Two of them is how #16 happened.

### MEDIUM — `NEG_MAND` guarded two of `MAND`'s four cues — fixed

`MAND` carries `mandatory|必須|minimum install|最小構成に入る`; `NEG_MAND` named only the first two, so
the phrase-cues could be negated freely. A guard's exemption list is part of the guard. Six
reachable forms, all now caught:

| Sentence | Why it escaped |
| :-- | :-- |
| `` `archive` is not in a minimum install. `` | no clause for `minimum install` |
| 「`archive` は最小構成に入るわけではありません。」 | no clause for `最小構成に入る` |
| `` `archive` is **not** mandatory `` | `not` followed by `**`, not `\s+` |
| `` `archive` is never mandatory. `` | `never` absent from the alternation |
| 「`archive` は必須ではない。」 | plain form missing beside `ではありません` |
| 「`archive` を必須から外しました。」 | the most natural Japanese for the real regression |

The third row is the one that matters beyond its own fix: **the same bolding hazard was already
fixed once**, in round 3's LOW, where `NEG` gained `not\W{0,4}opt-in` because this section's house
style bolds the key word. The tolerance was not carried across — and the direction reversed. In
`NEG` a bolded negation produced a false *red*; in `NEG_MAND` it produced a false *green*. A
cosmetic tolerance on the accusing side is load-bearing on the clearing side, and copying a pattern
without re-deciding its direction is how that got missed.

### LOW — `not` was unanchored, so `cannot` supplied one — fixed

"You **cannot** skip the mandatory set." matched via the `not` inside `cannot`, discarding a
sentence that asserts the property. Always the safe direction — a false red, never a false green —
and none of the three live sections was hit. `\b` on both alternatives removes the path.

### The shape of five rounds, restated now that it has a second instance

Round 4's entry said every finding since round 1 had been in the evidence layer. Round 5 adds the
sharper version: **the round-4 fix introduced the round-5 defect.** Not a missed case — a
regression, in the direction the fix was reaching for, caught only because the reviewer was asked to
be hostile to that specific path.

Two general things worth keeping, both cheap to state and both learned the expensive way:

1. **A pattern copied between an accusing check and a clearing check must have its direction
   re-decided.** `\W{0,4}` was cosmetic in `NEG` and load-bearing in `NEG_MAND`. Same characters,
   opposite consequence.
2. **An expectation that a check fails is not evidence the check works** unless "could not look" is
   distinguishable from "looked and found the problem". Otherwise the self-test is satisfied by the
   absence of the test.

## Review round 6 — CLEAN, 0 blockers, 0 HIGH, 0 MEDIUM

Reviewed at `0c03945`; receipt written. The `unreadable` path was attacked and holds, including the
partial case: `bodies` is built for all three files before anything is examined, so a ref that
resolves for two and not the third returns `unreadable` rather than grading the two it could read.
That is a real ref in this repo's history — `git show <old-ref>:README.ja.md` fails at any commit
predating that file. The crux is `if b is None` rather than `if not b`: an empty-but-readable file
flows through and reports **red**, correctly, because a README with no section genuinely fails
AC4/AC5, while a ref that cannot be read is a different fact. `if not b` would have collapsed the two
and quietly reintroduced round 5's HIGH.

### Two LOWs — accepted rather than fixed, and the reasons

Both are fail-closed, and the reviewer's own disposal was that neither is worth another round. This
is recorded **after** the receipt, which is why nothing was changed to accommodate it: `verify.py`'s
logic is exactly what was reviewed at `0c03945`.

- **The working-tree path raises instead of returning `unreadable`.** `text()` returns `None` for a
  bad ref, but `ref is None` still calls `open()` bare, so a missing file raises out of the
  comprehension. A traceback exits 1, so the direction is safe, and the same line would benefit from
  an explicit `encoding="utf-8"` — on a non-UTF-8 locale `README.ja.md` decodes to mojibake and the
  Japanese cues stop matching. Traced: that cannot go the other way, because `CUE`, `MAND` and
  `NEG_MAND` are all Japanese on that file, so they fail together and the result is red.
- **The recorded invocation rots on merge.** `./verify.py main:red -:green` depends on `main` still
  holding the defect. Once this merges, `main` carries the corrected text, goes GREEN, mismatches
  the expectation and exits 1 — and a future reader re-running the recorded evidence would conclude
  the check is broken. **The remedy, for whoever re-runs this:** use the pre-branch commit, which is
  a SHA that will always be red — `./verify.py 18205d5:red -:green`. The script stays correct
  either way; it is only the example that ages.

Also noted and not acted on: the mismatch line prints the raw argument, so the working tree shows as
`-` where `check()` prints `working tree`; and a bare `:green` yields an empty ref, which
`git show :README.md` accepts as the *index* rather than erroring.

### The residual, extended

`observations.md`'s RESIDUAL paragraph speaks only of `optin()`. It applies equally to
`mandatory()`: its negation guard is bounded by the same enumeration, in the same way, with the same
exit at #110. The structural asymmetry that made round 5's finding a MEDIUM is gone — `NEG_MAND` now
covers all four of `MAND`'s cues — and what remains is paraphrase (「必須とはいえません」,
「必須の対象外です」 and their English cousins), which is enumeration against natural language and is
the documented floor rather than a defect to chase.

### Six rounds, and what the record is actually for

The artifact was correct after round 1. Every finding since was in the evidence: three blind spots in
a grep (direction, markup, sentence scope), an uncommitted script, a fail-open introduced by a fix,
and a negation guard covering half its cues. Five of those six were fail-opens — checks that would
have reported the property true while it was false.

The two lessons that transfer beyond this spec:

1. **A pattern copied between an accusing check and a clearing check must have its direction
   re-decided.** The same bolding gap appeared twice: in `NEG` it produced a false red, in
   `NEG_MAND` a false green. `G-9`'s side decides the severity, not the gap.
2. **An expectation that a check fails is not evidence the check works** unless *could not look* is
   distinguishable from *looked and found it*. Round 5's HIGH was exactly this, and it is #16 —
   one of the first five bugs filed against this repository — reappearing at the outermost layer.

## Post-receipt — `produces:` → `成果物:`, on the author's call

Round 6's LOW 2 left the Japanese label open for the author, who chose **`成果物:`**. Applied after
the CLEAN receipt at `0c03945`; `README.ja.md` is outside `Source globs`, so the review gate does
not re-fire, and this is recorded rather than re-reviewed. Stating that plainly because it is a
content change to a reviewed artifact, not a work-log entry.

**It is the first label in this diagram that is not ASCII, and that breaks an assumption the
previous six rounds ran on.** Every alignment claim in this file until now was in *character
indices*, and that worked only because every row was ASCII, where one character is one column.
`成果物:` is 4 characters and **7 display columns** — the three kanji are East Asian Wide. Padded to
the gutter it is 8 characters but 11 columns:

| Row | Gutter | Characters | Display columns |
| :-- | :-- | :-- | :-- |
| skill | `skill:` + 5 spaces | 11 | 11 |
| arrows | 11 spaces | 11 | 11 |
| chain (EN) | `produces:` + 2 spaces | 11 | 11 |
| chain (JA) | `成果物:` + 4 spaces | **8** | **11** |

Aligned on **display columns**, not characters, because that is what a reader sees — the
character-count convention recorded at the top of this file was always a proxy for it, and the proxy
holds only while the text is ASCII. Verified in both files after the change: gutters 11/11/11,
node centres and arrow columns both `[12, 21, 33, 42, 49, 56, 65]`, and `↑` at 42 on the centre of
`Issue`. A character-index check would now report `README.ja.md` misaligned and be wrong.

**What it costs, stated rather than glossed:** the two READMEs are no longer byte-identical through
*every* aligned row. The skill row, the arrow row, the `↑` row and the templates row still are; only
the chain row's gutter differs. That byte-identity was cited in round 1 as the property that keeps
the two diagrams from drifting, and it caught one real error on this branch, so giving up part of it
is a genuine trade and not a free one. What replaces it is the display-column check above, which is
the stronger invariant — it is what byte-identity was standing in for.
