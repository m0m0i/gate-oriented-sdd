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
