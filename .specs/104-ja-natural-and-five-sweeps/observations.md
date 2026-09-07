# Observations — #104

## T1 — before

- "four sweeps": 1; 「4回のスイープ」: 1; sweeps in merged PR titles: #31, #43, #46, #51, and #99 (with #100, #101 completing it) — five.
- bullet lines in README.ja.md: 0

The Japanese sentences before, by line:

    13: スペック駆動開発の多くは、ディレクトリの規約と「この手順に従ってください」という指示の組み合わせでできています。これはだいたいうまく動きますが、いつでもうまく動き続けられるかどうかはわかりません。
    25: | **プロセス** | skill（`spec`, `clarify`, `implement`, `worklog`, `archive`）        | スキップできます。ガイダンスなので。                                |
    26: | **判断**     | 読み取り専用の reviewer サブエージェント。ルールブックはハッシュ固定 | スキップできます。なので、実行されたかどうかを receipt に残します。 |
    29: 保証と呼べるのは一番下の層だけです。設計上することは、その層に置くだけの価値があるルールを見極めること、そしてゲートがうっとおしくならない程度に、一覧を短く保つことにあります。
    35: `claude plugin details gate-sdd` は、13個の skill と3つの reviewer を含むハーネス全体で、常時消費するのは **約1,300トークン**です。ルールブックと reviewer contract はさらに **約5,900トークン**ありますが、この常時分には **1トークンも寄与しません**。コンポーネントとして登録していないからです。
    37: ただし、上流工程の6つの skill はこの常時分のうち約450トークンを占めていて、実際に発火するのはプロジェクトにつき数回になると思います。ここは、この節で述べている原則に反しているコストです。今の大きさなら許容できますが、上流の skill がこれ以上増えるなら、毎セッションを静かに太らせるのではなく、2つ目のプラグインに分けるべきだと考えています。**毎ターン支払っている参照資料は、いずれ
    39: **ピン留めは、正直な形で行います。** `rules-lock.json` は2種類のファイルを区別します。**vendored** は上流のテキストをそのまま複製したもので、ハッシュが上流と一致しなければなりません。**derived** はこのリポジトリで書いたルールで、一次情報を出典として引いています。上流が動いても、derived なルールが*間違い*になるわけではありません。*未検証*
    47: skill が13個あるからといって、必須のドキュメントが13個あるわけではありません。すべてのサイズのプロジェクトで準備すると over-engineering になりがちです。**必須は6つのドキュメントと3つのテンプレート**で、残りはプロジェクトがそれを必要とする規模になってから足せば十分です。
    55: テンプレートはこのチェーンの*横*ではなく*中*にあります。Issue のタイプが決まるのは Issue のステップで、そのタイプが spec の形を決めるからです。テンプレートを外してもチェーンは回りますが、bug に対して feature の形をした spec ができあがります。存在しないユーザーストーリーと、フィクションでしかない受け入れ条件を持ったものができちゃうかもしれません。
    59: そして、このチェーンの核心は本プラグインの発明ではありません。**GitHub のもの**です。Issue、ブランチ、Pull Request、そして PR が Issue を閉じる仕組み。これらはペアプログラミング規模から大きなチームまで、ちゃんと機能します。30人のチームでなければ使えない、という話ではありません。
    87: Issue、ブランチ、spec ディレクトリ、PR は同じ slug を共有し、PR が Issue を閉じます。ルールは **Issue なくして spec なし**。`spec` は Issue がなければ黙って作ることをせず、そこで停止して尋ねます。Issue のない spec とは、誰も選んでいない作業が始まっているということだからです。ゲートはこれを機械的に検査します。slug は `<
    91: **チェーンは PR 1本で終わります。** spec はその PR の最初のコミットであって、spec 自体の PR はありません。work log は最後のほうのコミットで、マージがおしまいです。続く PR はありません。`archive` がチェーンの傍らにあるのはそのためです。`git mv` 1回にブランチとレビューとマージを1式与えるほどの中身はなく、機械的に待っているものもありません

## T2 — after: each sentence and the English it carries

1. 「たいていはうまくいきます。うまくいかなくなるまでは。」 — "That works until it doesn't."
2. 「スキップできます。ガイダンスなので、それで構いません。」 / 「スキップできます。だから、実行されたかどうかを receipt に残します。」 — the process and judgment rows of the layer table: "Yes. It is guidance, and that is appropriate." and the judgment row; fragments made sentences, and the process cell now carries "and that is appropriate", which the old cell had dropped (reviewer's INFO).
3. 「設計上の仕事は、その層に置く価値のあるルールを見極めることと、ゲートが煩わしくならない程度に一覧を短く保つことです。」 — the design work is deciding which rules deserve the bottom layer and keeping the list short enough that the gate is not annoying. うっとおしい → 煩わしい here; in the pinning paragraph the sentence now carries the English's consequence — 「意味のない理由で鳴るアラームは、いずれ切られます。」 for "an alarm that fires for non-reasons gets switched off" — rather than only the annoyance (reviewer's INFO).
4. 「これは主張ではなく、測定した数字です。`claude plugin details gate-sdd` によれば、…常時消費するのは約1,300トークンです。」 — "That is measurable rather than asserted. `claude plugin details gate-sdd` reports ~1,300 tokens always-on"; the command is now the source, not the subject, and the opening sentence, absent from the Japanese before this branch, is carried (reviewer's INFO).
5. 「ただし、上流工程の6つの skill は、…約450トークンを占めます。実際に呼ばれるのはプロジェクトにつき一度程度でしょうから、この節で述べた原則にそのまま反するコストです。今の大きさなら受け入れられますが、…2つ目のプラグインに分けるべきです。」 — "~450 of that always-on total while firing perhaps once per project — a real cost against the same principle this section argues … should split into a second plugin". **Claim correction:** 数回 ("a few times") said more than the English's "perhaps once".
6. 「そう読んでしまうのが、これを over-engineering だと切り捨てる最短コースです。」 — "reading it that way is the fastest route to dismissing this as over-engineering". **Claim correction:** the old sentence said preparing all thirteen for every project size tends to over-engineering, which the English does not say.
7. 「存在しないユーザーストーリーと、作り話でしかない受け入れ条件を持った spec です。」 — "a user story that does not exist and acceptance criteria that are fiction"; できちゃうかもしれません dropped, since the English states it, not hedges it.
8. 「ペアプログラミングの規模から上はどこでも機能しますし、30人のチームでなければ使えない、という話でもありません。」 — "They work from pair-programming scale upward; a team of thirty is not the threshold."
9. 「`spec` は Issue がなければ、黙って作ったりせずにそこで止まって尋ねます。」 — "`spec` refuses to start without one rather than quietly creating it".
10. 「work log は最後のほうのコミットで、マージで終わりです。」 and 「`git mv` 1回のために、ブランチとレビューとマージを一式用意するほどの中身はありませんし、機械的に待っているものもありません。」 — the chain ends at the merge; a single `git mv` does not earn a branch, a review and a merge, and nothing mechanical is waiting.
11. 「`archive` は5回のスイープとして走らせました」 — "`archive` as five sweeps", the count fixed in both languages.

Register after: ですます調 throughout; zero lines beginning with `- `; zero occurrences of うっとおし. The Status section is untouched except the count.

### Validators, after the last write, stopping on failure

- `./scripts/check-leakage.sh` → exit 0 — `check-leakage: clean`
- `./scripts/check-manifests.py` → exit 0 — `check-manifests: both manifests agree`
- `./scripts/check-markdown-fences.py` → exit 0 — `check-markdown-fences: 10 ```markdown fence(s), no hand-wrapped prose`
- `./scripts/check-receipt-schema.py` → exit 0 — `check-receipt-schema: 7 field(s) agree across 3 copies`
- `./scripts/check-skill-contracts.py` → exit 0 — `check-skill-contracts: 9 skill contract(s) present`
- `./scripts/check-templates.py` → exit 0 — `check-templates: 10 task line(s) across 3 template(s), no split red steps`
- `./assets/check-steering-anchors.sh` → exit 0 — `check-steering-anchors: 5 of 5 anchor(s) resolved, none unreadable`
- `./assets/check-locks.py` → exit 0 — `check-locks: 6 pinned file(s) match their locks in .claude/agents, agents`
- `./scripts/test-gates.sh` → exit 0 — `test-gates: 54 passed, 0 failed`

**AC3, observed.** `git diff --name-only main` → `README.md`, `README.ja.md`, and the two files in this directory; `git diff --numstat main -- README.md` → 1 1. Consequences to existing documents: none — the old count lives otherwise only in #48's and #90's dated observations, which are records and stay; `docs/verified.md` states no sweep count.

**Review triage.** LOW — the process row's closing pipe drifted four columns: re-padded to the header's width. LOW — AC3's first two clauses ticked without a record: the line above. INFO ×3 — three C-3 gaps older than this branch on lines it touched, all taken since the author asked for the Japanese to be right: 「それで構いません」, 「これは主張ではなく、測定した数字です。」, 「いずれ切られます」. INFO — the reviewer's allow-list has no clock for `reviewed_at`: filed as an issue.

**Second review.** CLEAN; one LOW — two English quotations in this record were paraphrases: replaced with `README.md`'s text verbatim.
