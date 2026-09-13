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
