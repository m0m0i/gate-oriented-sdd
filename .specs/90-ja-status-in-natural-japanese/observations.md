# Observations — #90

## T1 — before

Register of the rest of `README.ja.md`: ですます調, paragraphs and tables, zero lines beginning with `- `. The current ステータス section, verbatim:

    ## ステータス
    
    **v0.4.3、pre-release です。** 検証済みバージョンの一覧を伴う reference implementation であって、サポート付きのプロダクトではありません。[eval スイート](./evals/) は書いてありますが、まだ走らせていません。2026-09-05 時点で、このアカウントの `claude plugin eval` はヘルプこそ表示するものの、どう呼び出しても「in early access」と出力して exit 0 で終わり、ケースを1つも実行しません。走らせたことのないスイートを「グリーンです」と言うのは、このハーネスが防ごうとしている未検証の主張そのものであり、その exit 0 を合格と読むのも同じことです。
    
    検証環境: Claude Code 2.1.252（2026-09-05）· Antigravity CLI 1.1.17 と IDE 2.3.1（最終確認 2026-08-21、以後再実行なし）· macOS。
    
    **検証できていること:** ゲートとガードの54通りの挙動を、モデルを介さず決定的にテストしています（[`scripts/test-gates.sh`](./scripts/test-gates.sh)）。Antigravity の `Stop` フックが実際にブロックすることも、ドキュメントを読んだのではなく動かして確認しました（[`docs/verified.md`](./docs/verified.md)）。2つのプラグインマニフェスト、ルールブックのハッシュ、機密混入チェックは、すべて CI で実行しています。13個の skill をすべて少なくとも一度は実行しました。inception の連鎖と `init` はこのリポジトリ自身、または実プロジェクトの使い捨てクローンに対して、`spec`・`clarify`・`implement`・`worklog` は #17 以降のすべての spec で、`archive` は4回のスイープとして走らせており、inception と `init` の実行で見つかったことは [`docs/verified.md`](./docs/verified.md) に記録し、Issue として起票しています。#17 以降のすべての spec には review receipt が `.specs/` の下にあり、2件を除いてサブエージェントとして起動した reviewer によるものです。その2件は inline でレビューされ、receipt 自体がそう記しています。
    
    **検証できていないこと:** それらの実行で作者に投げた質問はすべて推奨案どおりに答えられたため、skill が動くことは示せても、答えを持たない人から判断を引き出せるかは示せていません。eval スイート、`init` の greenfield とアップグレードの経路、そして 2026-08-21 以降の Antigravity の行も未検証です。
    

English claims to carry, one per line:

1. v0.4.3, pre-release; a reference implementation with a tested-against matrix, not a supported product.
2. The eval suite is authored and has still not run.
3. As of 2026-09-05 `claude plugin eval` exists on this account and renders its help; any invocation prints "in early access" and exits 0 without running a case.
4. Claiming a green suite that never ran is the unverified assertion the harness exists to prevent; reading that exit 0 as a pass would be the same.
5. Matrix: Claude Code 2.1.252 (2026-09-05); Antigravity CLI 1.1.17 and IDE 2.3.1 last verified 2026-08-21, not re-run since; macOS.
6. Verified: the gates' and guards' 54 behaviours, deterministically, no model in the loop, `scripts/test-gates.sh`.
7. Verified: Antigravity's `Stop` hook genuinely blocking, run rather than read, `docs/verified.md`.
8. Verified: both manifests, the rulebook hashes, the leakage guard, all in CI.
9. Verified: every one of the thirteen skills executed at least once — inception chain and `init` against this repo or a scratch clone of a real project; `spec`, `clarify`, `implement`, `worklog` on every spec since #17; `archive` as four sweeps.
10. What the inception and `init` runs found is recorded in `docs/verified.md` and filed as issues.
11. A review receipt on every spec since #17 under `.specs/`, from a spawned reviewer on all but two, which were reviewed inline and whose receipts say so.
12. Not verified: the interviews were all answered as recommended, so the skills are shown to work, not to elicit decisions from someone without the answers.
13. Not verified: the eval suite.
14. Not verified: `init`'s greenfield and upgrade paths.
15. Not verified: the Antigravity rows of the matrix since 2026-08-21.
