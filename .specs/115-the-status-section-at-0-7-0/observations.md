# Observations — 115-the-status-section-at-0-7-0

## Review round 1 — BLOCKED, 0 blockers, 1 HIGH, 5 MEDIUM, 3 LOW

### HIGH — the count was never removed from the README, only from the section I was looking at

The spec's Design said *"the third cannot disagree with anything, because it no longer asserts a
number."* **It still asserted one, a section above, in both languages, wrong by eleven** — and the
guard printed `no behaviour count asserted` over both files.

```
README.md:41      67 paths across the gates and guards
README.ja.md:43   ゲートとガードを合わせた67通りの経路
suite             78
```

`BEHAVIOUR_COUNT` was `(?:guards['’]|ガードの)\s*(\d+)\s*(?:behaviours|通り)` — written around the
one sentence in `## Status`. The English above it puts the **digits before the noun** and calls them
*paths*; the Japanese reads **ガードを合わせた**, not ガードの. Neither matched.

**The severity is not the stale count — it is the certification.** The guard examined one sentence
and issued a verdict about the whole file, on the same line that cites the suite as proof. That is
the anchor's shape: a success line broader than the check behind it.

**And the fixture could not have caught it**, which is the part worth keeping: `rm-count` used the
exact phrasing the regex was written around. A fixture built from the same assumption as the code
tests the assumption, not the code.

Fixed three ways: both counts removed from both files; the accuser widened to **any digit with a
counting noun** (`paths|behaviours|cases|通り|経路|挙動|ケース`) within 45 characters of
gates/guards in either direction and either language; every occurrence reported rather than the
first. Verified end to end — against `main`'s READMEs it now names both phrasings in both languages.

**The first widening was too loose and I caught it before shipping**: bare `\d+` near gates/guards
fired **eight times on a correct file** — on `gate-sdd` in a URL, on `m0m0i/gate`, on the token
count, on a table row. That is G-6, a gate firing on a correct repository. Requiring the counting
noun is what separates a claim about how many paths there are from a sentence that happens to
contain a number and the word "gate".

### The five MEDIUMs

- **An absent `reviewed_by` was counted as spawned.** The contract says silence is not evidence of
  independence — which is the whole reason the field exists — and the corpus predates it (#105).
  `reviewed_by` is a three-way fact and the README's sentence has room for two, so **unknown is now
  its own outcome and a problem**, not a silent promotion to the favourable bucket.
- **`Path.glob` swallowed an unreadable spec directory**, so a partially scanned corpus would have
  agreed. The `total == 0` branch only caught a corpus that vanished entirely. Now `os.scandir`,
  with `OSError` on the directory *and* on each receipt appended as a named problem rather than
  raised as a traceback.
- **The two vocabularies had different ceilings.** English stopped at `six`, the Japanese pattern
  accepted 八九十. At seven inline receipts a **truthful** README would have failed. The count is 3
  and has already risen once.
- **The version is checked, not derived**, and the spec's Design said otherwise. Detection is closed;
  prevention is not — `implement`'s post-receipt step still says nothing about the README, and the
  bump turn does not even trigger the validators, since the manifests sit outside `Source globs` by
  design (#14). The failure now lands at the PR instead of eight days later, which is an
  improvement and not the thing the sentence claimed. **The sentence is corrected in place and the
  gap is filed as #133** rather than fixed here: tying the README to the bump step touches
  `skills/`, a shipped path, and would owe a version bump AC8 says this spec does not carry.
- **The twelfth validator does not reach the reviewer's allow-list**, taking #131 from two entries
  to three. Left to #131 rather than folded in: one issue, one spec, one branch, one PR, and the
  reviewer itself flagged that landing both would break that rule.

### The three LOWs

`VERSION.search` took the first `**v<x.y.z>` anywhere — and `README.md:41` is this repository's own
proof that a `## Status` claim gets restated outside the section anyone is watching; multiple
versions now disagree loudly. The Japanese states the receipt count **twice** where the English
states it once, so both occurrences are matched and must agree. And case 65's Japanese assertion
pinned only the filename, which this guard emits for four different problems — now pinned to its
own message.

### What this round was about

The HIGH is the same failure the branch was fixing, one level up. #115 was filed because a number in
the README disagreed with the thing it counted. The fix **scoped itself to a section heading** and
shipped a guard that certified the whole file — so the spec, the guard and the success line all
agreed with each other and all disagreed with the README.

The boundary was drawn by `## Status` because that is where the issue pointed. The falsehood was one
anchor above it. **A scope drawn from where a defect was reported is not a scope drawn around where
that defect lives.**

## Review round 2 — BLOCKED, 0 blockers, 2 HIGH, 1 MEDIUM, 4 LOW

Round 1's HIGH is fixed at the right level. **Both new HIGHs were introduced by that fix**, and both
in the half I had asked the reviewer to attack.

### HIGH — I replaced a falsifiable claim with an unfalsifiable one

Removing the count, I wrote *"every path across the gates and guards, tested deterministically"* and
「ゲートとガードのすべての経路」. `67 paths` was **false but falsifiable** — a number with a source.
**`every path` is unfalsifiable and unsourced**: there is no coverage artifact for shell gates, the
suite reports named behaviours and not a proportion, and this repository's own G-4 records case 7
passing for three releases while the gate did nothing — its own evidence that coverage is not
exhaustive.

So the drift surface was not removed. It was **converted into a form the guard has no digit to
catch**, which would have been certified forever.

The fix was already written, twenty lines further down: `README.md:174` — the sentence the spec
composed carefully — says *"the gates' and guards' behaviours … (the count is the suite's, not a
number maintained here)"*. That **defers** scope; line 41 **asserted totality**. Both lines now
defer.

**A claim the guard can check is worth more than a universal it cannot** — and a weaker true
statement beats a stronger unverifiable one, which is the whole argument this repository makes
about receipts.

### HIGH — the Japanese widening only reached the phrasing that shipped

Both alternatives required the counting noun **flush against the digits**, which is the least common
way Japanese writes a count — a counter or a particle almost always intervenes:

```
ゲートとガードを合わせた67通りの経路   caught  (通り happens to sit flush)
ゲートとガードを合わせて67の経路       MISSED  (の)
ゲートとガードの67もの経路             MISSED  (もの)
ゲートとガードの67種類の挙動           MISSED  (種類の)
ゲートとガードの67パターンの挙動       MISSED  (パターン, and の)
```

The one form caught was **the one that shipped** — so `rm-count-ja` reproduced the historical string
and passed while the pattern behind it could not hold AC2 for the forms a future edit would more
likely use. That is round 1's defect surviving in one language, under a case that looked like
coverage.

**And the gap was self-concealing**, which is why my end-to-end check missed it: the same flush-noun
requirement is what keeps `README.ja.md`'s 「4つのケース」 green. The blind spot and the safety margin
were one mechanism, so widening one moved the other. The fix therefore had to come with **both**
directions pinned — 「ゲートとガードを合わせて67の経路」 red, 「4つのケース」 and "its four cases are
authored" green — and it does.

### MEDIUM — the Japanese anchor was traded away to reach the echo

Closing round 1's LOW (the count stated twice), I dropped `を除いて` from `INLINE_JA` so it would
find both occurrences. 件 is one of the most common counters in Japanese, so that matched **any**
`N件` in the file: a false red on 「issue が2件」, and a **fail-open** if the receipt sentence were
ever deleted while a stray `N件` remained — `search` would find it, it would happen to equal the
corpus, and the guard would pass over a README that no longer makes the claim.

The anchored pattern now carries the **value**, and a separate `JA_ECHO` checks the second
occurrence agrees — which is what the LOW actually asked for. The English kept its anchor
throughout; this restores the symmetry rather than trading one language's rigour for the other's
coverage.

### And the same fixture failure, for the third time in two days

Three of the fixtures I added this round had their Python string literals **split by literal
newlines** — `\n` written into the heredoc as an actual line break. Python died on a `SyntaxError`,
the fixtures no-op'd, and `rm-ja-silent` went red **for the wrong reason**. I found it only by
reproducing the scenario by hand.

This is the failure #124 was filed for, and the rule was written down *yesterday*: escape the
sequence, and **bind the fixture's exit status into the assertion**. I did neither. All three are
repaired and all three now report their status.

The mutation round after that found one more: the echo-consistency check was pinned by nothing —
mutating it produced **zero** failures. A case now covers it.

### What both rounds have in common

Round 1: a scope drawn from where the defect was reported, not around where it lived. Round 2: a
pattern built around the phrasing in front of me, and a universal substituted for a number because
it was easier than checking one. **Every one of these was a check narrowed to the example that
prompted it** — and the example is always the case that is already fixed.

## Review round 3 — CLEAN, 0 blockers, 0 HIGH, 1 MEDIUM, 3 LOW

Both round-2 HIGHs closed, and the reviewer checked they were closed **for the right reason rather
than for the reported example** — which is the test this record's own closing line asks for.

### MEDIUM — a no-op detector that could not fire

`rm-ja-echo` read:

```python
out = src.replace("1件を除いて", "1件を除いて") + "その5件は inline …"
if out == src:
    raise SystemExit("fixture no-op: …")
```

`str.replace(x, x)` is the identity function and the concatenation then guarantees `out != src`, so
the `if` was unreachable. Every sibling in the block uses that idiom for real; this one reproduced
the **shape** of a no-op detector with the substance removed.

That is #124's failure one level further in. Yesterday's instances were fixtures that no-op'd
silently; this was a fixture whose **no-op detector** was silent — the guard against the guard,
inert. The fixture appends rather than substitutes, so the precondition is now the check, and
breaking it turns `ja-echo-exit` red, verified.

_The first probe of that fix reported nothing, because I wrote the needle with single quotes where
the file uses double, so the mutation never applied. Caught by asking whether it had — which is the
same question this whole thread keeps turning on._

### The three LOWs

- **`JA_ECHO` was unanchored** where its sibling had just been re-anchored — the same asymmetry,
  one notch down. Now `(?=は\s*inline)`, which both the real sentence and the fixture satisfy.
- **`ケース` moved to the counter group.** Dropping it from the *noun* list was right for 「4つのケース」,
  but it left 「ゲートとガードの67ケースの挙動」 uncatchable. In counter position a list-noun must
  follow, so the gate form is caught and the eval form stays green **by construction rather than by
  margin** — which is the difference worth having.
- **Two gaps recorded rather than closed.** A trailing bare counter (「挙動を67件」) is missed,
  because letting a counter terminate a match re-opens 「3件を除いて」 and 「13個の skill」 whose only
  remaining protection would be the proximity window. This pattern has been wrong in **both**
  directions on this branch, and this is where the two failure modes sit closest, so it is a named
  limitation instead of a third swing. English `cases` is likewise a chosen trade — there is no safe
  counter position in English, and the eval sentence lives in the same paragraph.

**An unrecorded known gap is how round 1's defect survived. A recorded one is a decision.**

### Where the margin actually sits, from the reviewer

`README.ja.md` carries at least five `<digits><counter>の` constructions — 13個の skill, 3つの
reviewer, 6つの skill, 2種類のファイル, 2つのハーネス間 — whose only protection is that the following
word is not one of the nine nouns, and each also needs a gate word within 45 characters. 「2種類の
ファイル」 is closest, because 種類 is in the counter group *specifically* to catch 「67種類の挙動」.
Recorded because the false-positive direction is an accepted trade, and this is where it would
surface first.

## Review round 4 — APPROVE, zero findings at every level

Reviewed at `4ef9529`; receipt written, and it is the **first** receipt for this spec. Waiting for
the shipping SHA rather than writing one per round was deliberate: a receipt is a claim about a
diff, and there were three diffs before this one.

The reviewer traced the `ケース` move by **backtracking** rather than by trusting the suite, and
confirmed the property that made it the one safe widening left: 「4つのケース」 stays green because
`ケース` cannot occupy noun position at all, so every backtracking path fails — not because the
following word happens to be off a list.

It also named one consequence of the anchoring I had asked for and did not see: a Japanese rewrite
keeping the echo but dropping 「は inline」 leaves `JA_ECHO` unmatched, so the consistency check goes
quiet while the anchored value still verifies the count. That is the correct trade — the English has
no echo check at all, and requiring the echo to exist would block a legitimate rewrite — and it is
recorded rather than raised.

### What ships, stated so the merge commit is not misread

The reviewer's closing note, carried because it is the thing a reader would otherwise get wrong:
**this branch closed the version drift for detection, not for prevention.** #133 owns the
prevention half. And it added a twelfth validator the reviewer's own allow-list cannot run, which
#131 owns. Both were filed rather than folded in, on AC8's boundary.

So the honest summary is not *the version claim can no longer go stale*. It is: **it can no longer
go stale quietly.**

### Four rounds, and what the record carries

Every miss, including three the reviewer never saw and I reported against myself: the widening that
fired eight times on a correct file and was caught before shipping; three fixtures whose Python
string literals were split by literal newlines, against a rule written down the day before; and the
mis-quoted probe that reported nothing and was found by asking whether the mutation had applied.

The synthesis, which is the part that outlives this spec: **every one of these was a check narrowed
to the example that prompted it — and the example is always the case that is already fixed.**

Round 1 scoped to the section the issue pointed at, and the falsehood was one anchor above it.
Round 2 built a pattern around the phrasing in front of it, and substituted an unfalsifiable
universal for a number because it was easier than checking one. Round 3's no-op detector reproduced
the shape of a guard with the substance removed. Each was written from the instance, and each was
blind to the class.
