# gate-oriented-sdd

*[English →](./README.md)*

**レビューのゲートを「文章でお願いする」のではなく「フックで強制する」spec 駆動開発です。**

ひとつのプラグインディレクトリが、[Claude Code](https://claude.com/claude-code) と [Google Antigravity](https://antigravity.google/) の両方にインストールできます。

---

## 何を解決するのか

spec 駆動開発の多くは、ディレクトリの規約と「こうしてください」という指示の組み合わせでできています。それはうまくいきます ── うまくいかなくなるまでは。

指示は勧告でしかありません。長いセッションの終盤、あと少しで終わるタスクで、モデルはレビュー手順を単に実行しないことができます。そして誰も気づきません。気づくはずだったものも、また指示だったからです。

結果として残るのは、**達成していない遵守を報告するプロセス**です。プロセスがないより悪いと思います。人が確認をやめてしまうからです。

## 考え方

すべてのルールを「どれくらい言い逃れできるか」で仕分けし、それに見合った層に置きます。

| 層 | 仕組み | スキップできるか |
| :-- | :-- | :-- |
| **プロセス** | skill ── `spec`, `clarify`, `implement`, `worklog`, `archive` | できます。ガイダンスなので、それでいいのです。 |
| **判断** | 読み取り専用の reviewer サブエージェント。ルールブックは vendor 済みでハッシュ固定 | できます ── だから「実行されたか」を receipt に記録します。 |
| **決定性** | `Stop` フック: format、lint、型、receipt の鮮度 | **できません。** |

保証と呼べるのは最下段だけです。設計の仕事は、**そこに置く価値があるものを見極めること**、そしてその一覧を、ゲートが疎まれない程度に短く保つことにあります。

### この設定を使わなくても持ち帰れる2つ

**ルールブックはエージェント自身のディレクトリの中に置きます。** reviewer のルールは `agents/<reviewer>/rules/` にあり、`CLAUDE.md` にもセッションのコンテキストにも入りません。通常のセッションは一度も読み込みません。読むのは reviewer だけ、しかも diff が要求したファイルだけです。

これは主張ではなく測定できます。`claude plugin details gate-sdd` は、13の skill と3つの reviewer を含むハーネス全体で **常時 ~1,300 トークン**と報告します。ルールブックと reviewer contract はさらに **~5,900 トークン**ありますが、この常時分には **0 しか寄与しません**。コンポーネントとして登録されていないからです。

なお、上流工程の6つの skill はこの常時分のうち ~450 を占めますが、発火するのはプロジェクトにつき数回でしょう。これはこの節の主張に反するコストです。今は許容できる大きさですが、上流の skill が増えるなら、毎セッションを静かに膨らませるのではなく2つ目のプラグインに分けるべきだと考えています。**毎ターン支払う参照資料は、いずれ消される参照資料です。**

**ピン留めは、正直な形で行います。** `rules-lock.json` は2種類を区別します。**vendored** は上流のテキストをそのまま複製したもので、ハッシュは上流と一致しなければなりません。**derived** はここで書かれたルールで、一次情報を出典として引きます。上流が動いても derived なルールが*間違い*になるわけではありません ── *未検証*になるだけで、それは別の問題であり対処も別です。生きたドキュメントの HTML をハッシュする案は、試して却下しました。ナビゲーションの変更で値が変わりますし、意味のない理由で鳴るアラームは切られてしまうからです。

### ゲートを狭くしている理由

普通のターンで発火するゲートは無効化されます。そして無効化されたゲートは何も守りません。だから `review-gate.sh` は、spec ブランチのタスクが全て完了していて、かつ新しいクリーンなレビューが存在しない場合にのみ声を出します。マージ済みブランチ、実装途中のターン、レビュー*後*に正当に着地するドキュメントコミットでは黙ります。この10通りの挙動を、モデルを介さず[決定的に検証しています](./scripts/test-gates.sh)。

## 最小構成

13の skill があるからといって、13のドキュメントが必須なわけではありません。そう読まれることが、これを over-engineering として片付けさせる最短ルートです。**必須は6つのドキュメントと3つのテンプレート**で、残りはプロジェクトがそれを必要とする規模になったときに足せば十分です。

```text
PRD → design doc → backlog → Issue → spec → worklog
                               ↑
                    issue templates: feature / bug / chore
```

テンプレートはこの鎖の*横*ではなく*中*にあります。Issue のステップこそ種別が決まる場所で、その種別が spec の形を決めるからです。外しても鎖は回りますが、bug に feature の形の spec が生成されます ── 存在しないユーザーストーリーと、フィクションでしかない受け入れ条件を持って。

任意なのは `northstar`、`epics`、`contract`、`archive` です。

そしてこの鎖の中心は、このプラグインの発明ではありません ── **GitHub のものです。** Issue、ブランチ、Pull Request、そして PR がそれを閉じる仕組み。これらはペアプログラミング規模から上でちゃんと機能します。30人のチームは閾値ではありません。

## 流れ

**上流 ── プロジェクトにつき一度:**

```text
northstar ──▶ prd ──▶ design-doc ──▶ epics ──▶ backlog ──▶ sprint
   指標       ケイパビリティ  アーキテクチャ   デモ単位   順序づけ   1項目:N Issue
        └───────────────▶ contract ◀───────────────┘
                  コーディング規約を
                  reviewer のルールブックへ compile
```

**下流 ── Issue につき一度:**

```text
spec ──▶ clarify ──▶ (spec の PR) ──▶ implement ──▶ reviewer ──▶ worklog ──▶ archive
         5問以内                    Red/Green/Refactor   receipt
```

Issue、ブランチ、spec ディレクトリ、PR は同じ slug を共有し、PR が Issue を閉じます。ルールは **Issue なくして spec なし**。`spec` は Issue がなければ黙って作らず、停止して尋ねます。Issue のない spec は、誰も選んでいない作業が作られているということだからです。ゲートは機械的に検査します ── slug は `<issue>-<title>` なので、Issue 番号のない spec ディレクトリはターンを止めます。

上流の skill は、ハーネスが機械的に使うものに着地しなければ採用しません。`northstar` は reviewer が重大度判定に読む品質のアンカーを、`contract` は reviewer のルールブックを、`backlog` → `sprint` は `spec` が消費する型付き Issue を、`design-doc` は `.steering/structure.md` と reviewer がエスカレーション先にする ADR を生みます。散文で終わる文書は、このリポジトリが生成すべきものではありません。

## skill 一覧

| skill | すること | 何に着地するか |
| :-- | :-- | :-- |
| `init` | プロジェクトに導入する ── ツールチェーンを検出し、推測できないことだけ尋ねる | 以下すべての配線 |
| `northstar` | 指標、レバー、優先順位のついた品質法則 | reviewer が重大度に使うアンカー |
| `prd` | 利用者、安定 ID つきのケイパビリティ、境界 | spec が引用する ID |
| `design-doc` | アーキテクチャ、その継ぎ目、記録すべき決定 | `.steering/structure.md` と ADR |
| `epics` | それぞれがデモで終わるケイパビリティ規模の塊 | まとまった作業 |
| `backlog` | ひとつの順序つきリスト ── ordered であって prioritized ではない | `sprint` が上から取る順序 |
| `sprint` | 上位を Issue に分解する。1項目:N Issue | 型付きの tracker Issue |
| `contract` | 検査方法で階層化したコーディング規約 | reviewer のルールブック |
| `spec` | Issue の種別が形を決める、レビュー可能な spec 1本 | `implement` が実行する契約 |
| `clarify` | 設計の前に、影響範囲順で5問以内 | spec に記録された曖昧さ |
| `implement` | TDD ループと、必須の reviewer パス | ゲートが検査する receipt |
| `worklog` | 追記専用のセッション記録 | 理由つきの決定 |
| `archive` | 出荷済み spec を `.specs/` の外へ | `.specs/` は「生きている作業」を意味する |

加えて、読み取り専用の reviewer が3つ ── TypeScript、Python、Dart/Flutter ── と、どれにも当てはまらないスタック向けのテンプレートがあります。

## 配置

ハーネスがプロジェクトに何をどこへ書くかは [`docs/layout.md`](./docs/layout.md) にあります。`.specs/`、`.steering/`、`.work_logs/` は固定名です。`docs/` だけが動かせます ── 複数リポジトリの製品で、プロダクトレベルの正しさを1箇所に置けるようにするためです。

## インストール

**Claude Code**

```bash
claude plugin marketplace add m0m0i/gate-oriented-sdd
claude plugin install gate-sdd@gate-oriented-sdd
```

**Google Antigravity** ── git ベースのプラグインインストールはまだ存在しないので、clone してから実行します:

```bash
git clone https://github.com/m0m0i/gate-oriented-sdd
agy plugin install ./gate-oriented-sdd
```

その後、プロジェクト内で `init` を実行してください。何かを尋ねる前にリポジトリを読み、各バリデータを採用前に実際に走らせ、ゲートが黙っていることを確認してから完了を報告します。

## 2つのハーネス間の再現度

すべての行は実際に動かして得た結果です。手順、バージョン、未解決の点は [`docs/verified.md`](./docs/verified.md) にあります。

| 機能 | Claude Code | Antigravity |
| :-- | :-- | :-- |
| skill、reviewer、ルールブック | 完全 | 完全 ── 同じパス、同じ形式 |
| ターン終了時の品質ゲート | 完全 ── `Stop`, exit 2 | 完全 ── `Stop`, `{"decision":"continue"}` |
| review receipt のゲート | 完全 | 完全 |
| 編集ごとの高速フィードバック | 完全 ── `PostToolUse` | 完全 ── `PostToolUse`, 観測のみ |
| compaction 後の steering 再注入 | 完全 ── `SessionStart` | **なし** ── 該当イベントが存在しない |

最後の行は誤差ではなく本物の欠落です。`PreInvocation` が代替候補ですが、セッションに一度だけ発火させるガードを入れないと出荷に値しません。

## ステータス

**v0.2.0 ── pre-release です。** 検証済みバージョンの一覧を伴う reference implementation であって、サポート付きのプロダクトではありません。[eval スイート](./evals/) は書いてありますが一度も走らせていません ── `claude plugin eval` が early access で、これを作ったアカウントでは有効になっていないためです。走らせたことのないスイートを「グリーンです」と言うのは、このハーネスが防ごうとしている未検証の主張そのものになってしまいます。

検証環境: Claude Code 2.1.238 · Antigravity CLI 1.1.17 · Antigravity IDE 2.3.1 · macOS。

**検証できているもの:** review ゲートの10通りの挙動を、モデルを介さず決定的に検証しています([`scripts/test-gates.sh`](./scripts/test-gates.sh))。Antigravity の `Stop` フックが実際にブロックすることも、ドキュメントを読んだのではなく動かして確認しました([`docs/verified.md`](./docs/verified.md))。2つのプラグインマニフェスト、ルールブックのハッシュ、機密混入チェックはすべて CI で実行しています。

**検証できていないもの:** skill 自体を通しで実行したことはなく、reviewer が実際の diff をレビューしたこともまだありません。

## ライセンス

Apache-2.0。
