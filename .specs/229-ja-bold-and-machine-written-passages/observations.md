# Observations — #229

## T1 — before

Measured on `README.ja.md` at `origin/main` 6dca392. The bold check pairs the `**` markers on each line and counts the closing ones that sit between `。` and a non-space character. The space count covers a half-width space between Latin text (letters, digits, backtick, bracket, `*`) and Japanese, in either order.

- unrendered bold closings: **2** (L75, L95). The yomiyasu linter's `bold_not_rendered` agrees: 2.
- Latin–Japanese spaces: 380
- `ではなく`: 17

The sentences to change, each with the English sentence it carries. Line numbers are `README.ja.md` before the change; English is quoted from `README.md`.

1. L15 `たいていはうまくいきます。うまくいかなくなるまでは。` ⟷ "That works until it doesn't."
2. L31 `` だから `git checkout main` ひとつで唯一の強制ルールが黙り、痕跡も残りませんでした。 `` ⟷ "so `git checkout main` turned the only enforced rule off and left no trace."
3. L37 `常時消費するのは **約1,300トークン**です。` and `さらに **約5,900トークン**ありますが` ⟷ "reports **~1,300 tokens always-on**" and "another **~5,900 tokens**"
4. L39 `毎セッションを静かに太らせるのではなく、2つ目のプラグインに分けるべきです。` ⟷ "it should split into a second plugin rather than quietly inflate every session."
5. L45 `狭さは条件の性質であって、HEAD がどこを指しているかの性質ではない——その違いが #26 でした。` ⟷ "narrow is a property of the condition, not of where HEAD happens to point, and the difference is what #26 was."
6. L63 `いちばん儀式の少ないフェーズこそ、死んだ spec がいちばん早く溜まります。` ⟷ "the phase with the least ceremony is the one that accumulates dead specs fastest."
7. L75 `` **入れたばかりのプロジェクトは `bootstrap` です。**ハーネスは `` (unrendered bold; also the first of the paragraph's two split points) ⟷ "**A fresh install is `bootstrap`** — the harness is in place"
8. L75 `**そして、選んだ内容はこの期間を越えて残ります。**` (the second split point; the sentence itself is unchanged)
9. L93 `1つのラベルに潰さないためです。` ⟷ "rather than flattening them into a label."
10. L95 `**backlog の1項目は、たいてい複数の Issue になります。**変更そのもの` (unrendered bold) ⟷ "**one backlog item usually becomes several**"
11. L111 `掃除の代金はマージごとではなく、散らかったディレクトリごとに払います。` ⟷ "Sweeping is therefore paid per noisy directory, not per merge."
12. L133 `…との間の静かな乖離を防ぐ専用ガード` ⟷ "a dedicated guard prevents silent drift between …"
13. L148 `**Google Antigravity** — スタンドアロンのリリースアーカイブ、または clone からインストールします:` ⟷ "**Google Antigravity** — install either from a standalone release archive or a clone:"
14. L150 `*方法1: スタンドアロンのリリースアーカイブ（推奨 — リポジトリ内部の開発用ファイルを除外）:*` ⟷ "*Option 1: Standalone release archive (recommended — excludes repo-internal tooling):*"
15. L151 `…解凍し、インストールします:` ⟷ "Download and extract `gate-sdd.zip` from […], then:"
16. L157 `*方法2: 直接 clone:*` ⟷ "*Option 2: Direct clone:*"
17. L180 `初回ターン（turn 1）での注入は` ⟷ "initial turn 1 injection is handled via `PreInvocation`."

## T2 — after

- unrendered bold closings: **0**. The yomiyasu linter's `bold_not_rendered`: 0.
- Latin–Japanese spaces: 377. The three that went are `は **約1,300` and `に **約5,900` (the bold markers removed by item 3) and `が #26` (`#26` now opens its own sentence, item 5). No pair whose Latin and Japanese neighbours both survive lost its space (AC3 as amended).
- `ではなく`: 17

Each changed sentence after, numbered as in T1, with the C-3 reading against the English.

1. `たいていはそれでうまくいきますが、いずれうまくいかなくなります。` "until it doesn't" asserts that it stops working. 「いずれ」 keeps the assertion. A draft that read 「いつまでもうまくいくとは限りません」 weakened it to a possibility and was reverted.
2. `` だから `git checkout main` ひとつで唯一の強制ルールが止まり、痕跡も残りませんでした。 `` "turned … off and left no trace": 止まり is "turned off", without the personification of 黙り. A draft that read 「働かなくなっていました」 drifted from "turned off" and was reverted.
3. `常時消費するのは約1,300トークンです。` / `さらに約5,900トークンありますが`. The numbers and claims are unchanged. Only the bold goes, to bring the density down. `**1トークンも寄与しません**` keeps its bold, so the sentence's emphasis lands where the English "**zero**" puts it.
4. `気づかないうちに毎セッションの常時分を増やすのではなく、2つ目のプラグインに分けるべきです。` "quietly inflate every session": 気づかないうちに is "quietly", and 常時分 names the always-on figure the same paragraph is about. The obligation (べき) is unchanged.
5. `狭さは条件の性質であって、HEAD がどこを指しているかの性質ではありません。#26 は、この違いをめぐる問題でした。` The em dash goes, and the contrast is kept. "the difference is what #26 was" says only what #26 was about. A draft that read 「#26 で直したのは」 added "fixed", which the English does not say, and was reverted.
6. `いちばん儀式の少ないフェーズこそ、もう使われない spec がいちばん早く溜まります。` "dead specs" means specs no longer live work, which is what もう使われない says without the metaphor.
7. `` **入れたばかりのプロジェクトは `bootstrap` です**。ハーネスは `` The `。` moves outside the span, so the bold renders. A new paragraph starts here.
8. `**そして、選んだ内容はこの期間を越えて残ります。**` Unchanged. A new paragraph starts here. The closing `**` is followed by a space, so it already rendered.
9. `1つのラベルにまとめてしまわないためです。` "rather than flattening them into a label": まとめてしまう keeps the sense of losing the distinctions, without 潰す.
10. `**backlog の1項目は、たいてい複数の Issue になります**。変更そのもの` The `。` moves outside the span, so the bold renders. The text is unchanged.
11. `掃除のコストは、マージごとではなく、散らかったディレクトリごとにかかります。` "paid per noisy directory, not per merge": the cost and both units stay, and only the 代金/払う metaphor goes. The negation stays.
12. `…との間で気づかないうちに生じる乖離を防ぐ専用ガード` "silent drift": a drift nobody notices, with no claim about error output.
13. `**Google Antigravity**` on its own line, then `スタンドアロンのリリースアーカイブ、または clone からインストールします。` Same two install routes. The line-final colon becomes `。`. The em dash goes, and the heading now sits the way `**Claude Code**` already does.
14. `*方法1: スタンドアロンのリリースアーカイブ（推奨。リポジトリ内部の開発用ファイルを含みません）*` "recommended — excludes repo-internal tooling": both claims are kept, without the em dash or the trailing colon.
15. `…解凍し、インストールします。` "then:" introduces the code block. `。` does the same in Japanese prose.
16. `*方法2: 直接 clone*` The trailing colon goes.
17. `初回ターンでの注入は` "initial turn 1 injection". 初回ターン already says turn 1, so the parenthetical only repeated it.
