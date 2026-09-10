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
