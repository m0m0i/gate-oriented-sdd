# gate-oriented-sdd

[![gate-sdd](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2Fm0m0i%2Fgate-oriented-sdd%2Fmain%2Fplugin.json&query=%24.version&prefix=v&label=gate-sdd&color=blue)](./plugin.json)

_[English →](./README.md)_

**レビューのゲートを、フックで強制するスペック駆動開発セットアップです。**

[Claude Code](https://claude.com/claude-code) と [Google Antigravity](https://antigravity.google/) の両方にインストールできます。

---

## 何を解決するのか

スペック駆動開発の多くは、ディレクトリの規約と「この手順に従ってください」という指示の組み合わせでできています。たいていはそれでうまくいきますが、いずれうまくいかなくなります。

指示はあくまで勧告です。長いセッションの終盤、あと一歩で終わるタスクを前にして、モデルがレビュー手順を実行しないことは起こりえます。しかも、誰も気づきません。気づくはずだった仕組みも、また指示だからです。

そうして残るのは、実際には守っていない手順を「守りました」と報告するプロセスです。これはプロセスがない状態より厄介だと考えています。人が確認をやめてしまうからです。

## 考え方

すべてのルールを「どれだけ無視できてしまうか」で仕分けして、その強度に見合った層に置きます。

| 層           | 仕組み                                                               | スキップできるか                                                    |
| :----------- | :------------------------------------------------------------------- | :------------------------------------------------------------------ |
| **プロセス** | skill（`spec`, `clarify`, `implement`, `worklog`, `archive`）        | スキップできます。ガイダンスなので、それで構いません。              |
| **判断**     | 読み取り専用の reviewer サブエージェント。ルールブックはハッシュ固定 | スキップできます。だから、実行されたかどうかを receipt に残します。 |
| **決定性**   | `Stop` フック（format、lint、型、receipt の鮮度）。receipt の鮮度については、フックの弱点が届かない pull request 上のチェックも | **できません。**                                                    |

保証と呼べるのは一番下の層だけで、そしてそれが保証であるためには2か所が要ります。`Stop` フックは手元で速く効く半分、pull request 上のチェックは作業ツリーごと抜け出すことができない半分です。#26 以前はフックしかなく、しかもそれが訊いていたのは「完了した spec ブランチの上に*立っているか*」であって「このリポジトリが完了した spec ブランチを*抱えているか*」ではありませんでした。だから `git checkout main` ひとつで唯一の強制ルールが止まり、痕跡も残りませんでした。設計上の仕事は、この層に置く価値のあるルールを見極めることと、ゲートが煩わしくならない程度に一覧を短く保つことです。

### この構成を採用しない場合でも参考になる2点

**ルールブックは、reviewer 自身のディレクトリの中に置きます。** reviewer のルールは reviewer の隣の `<reviewer>/rules/` にあります。このプラグインの中では `reviewers/<reviewer>/rules/`、`init` が設置したあとは `.claude/agents/<reviewer>/rules/` か `.agents/agents/<reviewer>/rules/` です。`AGENTS.md`（または `CLAUDE.md` / `GEMINI.md`）にもセッションのコンテキストにも入りません。通常のセッションは一度も読み込みません。読むのは reviewer だけで、しかも diff が必要としたファイルだけです。

これは主張ではなく、測定した数字です。`claude plugin details gate-sdd` によれば、ハーネス全体で常時消費するのは約1,000トークンです。内訳は13個の skill で、エージェントはありません。3つの reviewer はさらに約2,100トークン、ルールブックと reviewer contract は約5,900トークンありますが、この常時分には **1トークンも寄与しません**。プラグインはどれも登録せず、`init` がプロジェクトにコピーするファイルとして持っているだけだからです。プロジェクトの側では、設置した reviewer 1つの説明文が約100トークン加わり、ルールブックはレビューのときにだけ読まれます。

ただし、上流工程の7つの skill は、この常時分のうち約580トークンを占めます。実際に呼ばれるのはプロジェクトにつき一度程度でしょうから、この節で述べた原則にそのまま反するコストです。今の大きさなら受け入れられますが、上流の skill が増えるなら、気づかないうちに毎セッションの常時分を増やすのではなく、2つ目のプラグインに分けるべきです。**毎ターン支払っている参照資料は、いずれ消される参照資料です。**

**ピン留めは、正直な形で行います。** `rules-lock.json` は2種類のファイルを区別します。**vendored** は上流のテキストをそのまま複製したもので、ハッシュが上流と一致しなければなりません。**derived** はこのリポジトリで書いたルールで、一次情報を出典として引いています。上流が動いても、derived なルールが*間違い*になるわけではありません。*未検証*になるだけで、これは別の問題であり、対処の仕方も別です。生きたドキュメントの HTML をハッシュする案も試しましたが、採用しませんでした。ナビゲーションが変わるだけでハッシュも変わりますし、意味のない理由で鳴るアラームは、いずれ切られます。

### ゲートを狭くしている理由

普通のターンで発火するゲートは、いずれ無効化されます。そして無効化されたゲートに守れるものはありません。そのため `review-gate.sh` が口を出すのは、タスクがすべて完了していて新しいクリーンなレビューが存在しない spec ブランチを、このリポジトリが抱えている場合だけです。マージ済みのブランチ、実装途中のターン、レビューの*後*に正当に入るドキュメントコミットでは何も言いません。一方で、いま立っていないブランチは見逃しません。狭さは条件の性質であって、HEAD がどこを指しているかの性質ではありません。#26 は、この違いをめぐる問題でした。もう半分が `quality-gate.sh` で、こちらは自前のコマンドを一切持ちません。`.steering/tech.md` の `- Validators:` 行をそのまま実行するので、何を強制するかはフックではなくプロジェクト側の性質になります。ゲートとガードの挙動は、モデルを介さず[決定的にテストしています](./scripts/test-gates.sh)。

## 最小構成

skill が13個あるからといって、必須のドキュメントが13個あるわけではありません。そう読んでしまうのが、これを over-engineering だと切り捨てる最短コースです。**最小構成に入る skill は13個中10個**で、その10個が生み出すドキュメントは**5つ、それに3つの issue テンプレート**です。skill とドキュメントは数える単位が違うので、両者の数は一致しません。この節があるのは、まさにその取り違えを防ぐためです。

```text
skill:     prd   design-doc   backlog  sprint   spec implement worklog
            ↓        ↓           ↓        ↓      ↓      ↓        ↓
成果物:    PRD → design doc → backlog → Issue → spec → code → worklog
                                          ↑         + receipt
                               issue templates: feature / bug / chore

必須だが、チェーンには出てこない: init, clarify, archive
```

テンプレートはこのチェーンの*横*ではなく*中*にあります。Issue のタイプが決まるのは Issue のステップで、そのタイプが spec の形を決めるからです。テンプレートを外してもチェーンは回りますが、bug に対して feature の形をした spec ができあがります。存在しないユーザーストーリーと、作り話でしかない受け入れ条件を持った spec です。

10個のうち、ドキュメントを作るのは5個、作らないのが5個です。ドキュメントを数えても正しい集合にたどり着かないのは、これが理由です。`sprint` と `implement` がそれでもチェーン上にあるのは、Issue と receipt がドキュメントではないにせよ、チェーンの一段ではあるからです。`init`、`clarify`、`archive` はチェーンのどこにも出てきません。`init` はハーネス自体を設置し、`clarify` は spec の中の一節を書き、`archive` は `git mv` と `Status` の書き換えです。それでもこの3つは必須です。とくに `archive` は、小さいから任意、ではありません。いちばん儀式の少ないフェーズこそ、もう使われない spec がいちばん早く溜まります。

任意なのは次の3つで、任意である理由はそれぞれ違います。

| Skill | 任意である理由 |
| :-- | :-- |
| `northstar` | `init` の対話が、別ルートで同じ `- Owns:` アンカーを作ってしまう |
| `epics` | 機械的に読む先が**まだ**どこにもない。これは決定ではなく、#166 で埋めるべき穴です |
| `contract` | commit もレビュー指摘も溜まらないうちに走らせると、ルールブックが「無い」のではなく「悪い」ものができあがる |

**skill はどれも、常に使えます。** `init` はアクティブなハーネス（Claude Code、Google Antigravity、または両方）を検出し、`.steering/`、`.specs/`、`.work_logs/`、issue テンプレート、適切なルールポインタ（`CLAUDE.md` / `GEMINI.md`）、reviewer、そして hook を設置します。skill 本体はプラグインに同梱されているので、設置しません。Claude Code ではゲートも同梱されているので設置せず、`init` が書くのはプラグインを有効にする設定と言語ごとの高速チェックだけです。ここでの選択が決めるのは、どのドキュメントを作るか、どの skill をフローに乗せるかであって、その skill を使えるかどうかではありません。

**この選択は、推測ではなく記録されます。** `init` が `.steering/tech.md` に `- Mode: bootstrap`、`- Mode: minimum`、`- Mode: full` のいずれかを書き、`- Validators:` に載ったチェッカーが、品質ゲートの走るタイミングと CI とで、宣言とファイルの実態が合っているかを検証します。実際に効くのは CI のほうです。ゲートがこの行を走らせるのはソースが変わったターンだけであり、ドキュメントはソースではないからです。どのファイルが存在するかから後づけで判断するのではなく、宣言する形にしてあります。存在から逆算しても「意図して作らなかった」のか「作りかけで放置された」のかは区別できないからで、その2つを見分けることこそ、この行が存在する唯一の理由です。

**入れたばかりのプロジェクトは `bootstrap` です**。ハーネスは設置されているが、起点となるドキュメントはまだ書かれていない、という状態で、これは残り2つのどちらでもありません。以前はそのどちらかとして記録していたため、初回インストールはどれも自分でゲートを赤にしていました（#127）。この状態は最初の spec で失効します。ドキュメントが引用され始めるのがそこだからです。終わりの来ない状態は、注釈つきでゲートを切ってあるのと同じです。

**そして、選んだ内容はこの期間を越えて残ります。** `init` は `- Target: minimum` または `- Target: full` も記録します。これは「まだ何が真であるか」とは別に「何を選んだか」を表す値です。チェッカーは、その target が必要とするドキュメントを、それぞれを書くスキルの名前とあわせて、最初の spec より前の案内行でも、そこで止めるときのメッセージでも挙げます。target は判定を変えません。何が必要かは `- Mode:` だけから決まるので、target を書き間違えれば「何を負っているか」の説明は狂いますが、ドキュメントが検査されないままになることはありません。

**強制の強さは、モードによって一切変わりません。** ゲートも reviewer も receipt も TDD ループも同じです。違うのは、最初の spec を書くまでにどれだけ計画を書くか、それだけです。そしてこれは決め打ちでもありません。`minimum` のプロジェクトでも、レビュー指摘が繰り返され始めた時点で `contract` を走らせればよく、すでにモードを宣言したプロジェクトに `init` を再実行すれば、入れ直しではなくアップグレードを提案します。動くのは上方向だけで、下には戻しません。

そして、このチェーンの核心は本プラグインの発明ではありません。**GitHub のもの**です。Issue、ブランチ、Pull Request、そして PR が Issue を閉じる仕組み。ペアプログラミングの規模から上はどこでも機能しますし、30人のチームでなければ使えない、という話でもありません。

## 流れ

**上流。プロジェクトにつき一度:**

```text
northstar ──▶ prd ──▶ design-doc ──▶ epics ──▶ backlog ──▶ sprint
   指標       ケイパビリティ  アーキテクチャ   デモ単位   順序づけ   1項目:N Issue
        └───────────────▶ contract ◀───────────────┘
                  コーディング規約を
                  reviewer のルールブックへ compile
```

`backlog` が作るのは**プロダクトバックログ**です。既知のタスクを集めたものではなく、プロダクトが達成すべきことの全体を、ひとつの順序つきリストとして並べたものを指します。**prioritized ではなく ordered** であることが要点で、位置そのものが価値・リスク・コスト・依存関係をまとめて表します。1つのラベルにまとめてしまわないためです。並べること自体が価値であって、作るものを列挙しただけのリストはバックログではなく在庫です。

`backlog` は Issue を1つも作りません。`sprint` がその上位を tracker の Issue に分解します。**backlog の1項目は、たいてい複数の Issue になります**。変更そのものと、その過程で必要だとわかったテストと、そこから強制されるマイグレーションは、別々の Issue であり spec の形も違うからです。順序を変えるのは安上がりで、いつでもやり直せます。一方、Issue を切ることは「やる」という約束です。だからこの2つを別のステップに分けています。

**下流。Issue につき一度:**

```text
spec ──▶ clarify ──▶ implement ──▶ reviewer ──▶ worklog ──▶ PR 1本、Issue を閉じる
         5問以内     Red/Green/Refactor  receipt

archive ····· チェーンの中ではなく、その傍らに。出荷済みの spec を .specs/ から掃き出す
              作業で、マージのたびではなく、ディレクトリが散らかってきたときに走らせる
```

Issue、ブランチ、spec ディレクトリ、PR は同じ slug を共有し、PR が Issue を閉じます。ルールは **Issue なくして spec なし**。`spec` は Issue がなければ、黙って作ったりせずにそこで止まって尋ねます。Issue のない spec とは、誰も選んでいない作業が始まっているということだからです。ゲートはこれを機械的に検査します。slug は `<issue>-<title>` なので、Issue 番号のない spec ディレクトリはターンを止めます。

1つの Issue に対して、spec もブランチも PR も1つです。そしてこのチェーンの中で、多くのスペック駆動開発に欠けていると思うのが `clarify` です。スペック駆動開発でいちばん多い失敗は、構造が足りないことではありません。要件を読み違えたまま、自信を持って書かれた spec です。しかもこれはレビューでは捕まえられません。読み違えていても、いなくても、ドキュメントの見た目は同じだからです。

**チェーンは PR 1本で終わります。** spec はその PR の最初のコミットであって、spec 自体の PR はありません。work log は最後のほうのコミットで、マージで終わりです。続く PR はありません。`archive` がチェーンの傍らにあるのはそのためです。`git mv` 1回のために、ブランチとレビューとマージを一式用意するほどの中身はありませんし、機械的に待っているものもありません。review gate はいま立っているブランチの外も見るようになったので、`.specs/` に残った出荷済みの spec も視界には入ります。それでも何も言わないのは、receipt がクリーンでブランチがマージ済みだからで、これは確かめたうえでの沈黙です。ただしブランチ自体が削除されている場合は、spec を読み出す先がもうありません。そちらは確かめたうえでの沈黙ではありません。掃除のコストは、マージごとではなく、散らかったディレクトリごとにかかります。

上流の skill は、ハーネスが機械的に使うものに行き着かないかぎり採用しません。`northstar` は reviewer が重大度の判断に読む品質のアンカーを、`contract` は reviewer のルールブックを、`backlog` → `sprint` は `spec` が消費する型付きの Issue を、`design-doc` は `.steering/structure.md` と reviewer がエスカレーション先にする ADR を生みます。文章で終わるだけのドキュメントは、このリポジトリが生成すべきものではありません。

## skill 一覧

| skill        | すること                                                                   | 何が生まれるか                               |
| :----------- | :------------------------------------------------------------------------- | :------------------------------------------- |
| `init`       | プロジェクトに導入する。ツールチェーンとアクティブなハーネスを検出し、推測できないことだけ尋ねる | 以下すべての配線                             |
| `northstar`  | 指標、そのレバー、優先順位をつけた品質法則                                 | reviewer が重大度判定に読む `Owns:` アンカー |
| `prd`        | 利用者、安定した ID つきのケイパビリティ、対象外の線引き                   | spec が引用する ID                           |
| `design-doc` | アーキテクチャ、その継ぎ目、記録すべき決定                                 | `.steering/structure.md` と ADR              |
| `epics`      | それぞれがデモで終わる、ケイパビリティ規模の塊                             | まとまった作業                               |
| `backlog`    | ひとつの順序つきリスト。ordered であって prioritized ではない              | `sprint` が上から取る順序                    |
| `sprint`     | 上位を Issue に分解する（1項目:N Issue）                                   | 型付きの tracker Issue                       |
| `contract`   | 検査方法で階層化したコーディング規約                                       | reviewer のルールブック                      |
| `spec`       | Issue の種別が形を決める、レビュー可能な spec 1本                          | `implement` が実行する契約                   |
| `clarify`    | 設計の前に、影響範囲の大きい順で5問まで                                    | spec に記録された曖昧さ                      |
| `implement`  | TDD ループと、必須の reviewer パス                                         | ゲートが検査する receipt                     |
| `worklog`    | 追記のみのセッション記録                                                   | 理由つきの決定                               |
| `archive`    | 出荷済みの spec を `.specs/` の外へ、頼まれたときにまとめて                | `.specs/` が「生きている作業」を意味する状態 |

加えて、読み取り専用の reviewer が3つ（TypeScript、Python、Dart/Flutter）と、どれにも当てはまらないスタック向けのテンプレートがあります。この3つは参照実装です。`init` がいちばん近いものをプロジェクトにコピーし、プラグインはどれもエージェントとして登録しません。各 reviewer の Bash ポリシー許可リストは、読み取り専用の証拠収集（diff/log、時計、インストール済みバージョン確認、プロジェクトのターン終了バリデータ、そして reviewer ファイルが理由を添えて名指しした情報源。たとえばロック確認のためのハッシュ）に厳格に限定されており、`.steering/tech.md` の `- Validators:` 行と reviewer の許可リストとの間で気づかないうちに生じる乖離を防ぐ専用ガードを備えています。

## 配置

ハーネスがプロジェクトの何をどこへ書くかは [`docs/layout.md`](./docs/layout.md) にまとめてあります。`.specs/`、`.steering/`、`.work_logs/` は固定名です。動かせるのは `docs/` だけで、これは複数リポジトリにまたがる製品で、プロダクトレベルの正しさを1箇所に置けるようにするためです。

## インストール

**Claude Code**

```bash
claude plugin marketplace add m0m0i/gate-oriented-sdd
claude plugin install gate-sdd@gate-oriented-sdd
```

そのあと、プロジェクトの中で `init` を実行してください。Claude Code では、`init` がコミット対象の `.claude/settings.json` に、言語ごとの高速チェックと並べて次の宣言を書き込みます。

```json
{
  "extraKnownMarketplaces": {
    "gate-oriented-sdd": {
      "source": { "source": "github", "repo": "m0m0i/gate-oriented-sdd" },
      "autoUpdate": true
    }
  },
  "enabledPlugins": { "gate-sdd@gate-oriented-sdd": true },
  "env": { "FORCE_AUTOUPDATE_PLUGINS": "1" }
}
```

下のずれの表に挙げる場合を除き、これでリポジトリを開く全員の環境でハーネスが有効になります。ゲートはプラグインから実行されます（検証済み。[`docs/verified.md`](./docs/verified.md) の V1）。そのため、ゲートの修正はプラグインの更新でプロジェクトに届き、プロジェクトに pull request を出す必要はありません。更新が届くかどうか、届くならいつかは、「**ゲートを最新に保つ**」で説明します。`env` の行は、Claude デスクトップアプリから始めたセッションでも自動更新を有効に保ちます。この行がなければ、そのセッションでは自動更新が行われません（検証済み。[`docs/verified.md`](./docs/verified.md) の U2 と F2）。自分の環境でだけ無効にしたい場合は、自分の `.claude/settings.local.json` で同じキーに `"0"` を設定します。このファイルはプロジェクトのファイルより優先されます（ドキュメント記載、未実施）。`claude plugin install gate-sdd@gate-oriented-sdd --scope project` はこの宣言の代わりになりません。このコマンドが書き込むのは `enabledPlugins` の部分だけだからです（検証済み。[`docs/verified.md`](./docs/verified.md) の M1）。

**Google Antigravity**

スタンドアロンのリリースアーカイブ、または clone からインストールします。

*方法1: スタンドアロンのリリースアーカイブ（推奨。リポジトリ内部の開発用ファイルを含みません）*
[GitHub Releases](https://github.com/m0m0i/gate-oriented-sdd/releases/latest) から `gate-sdd.zip` をダウンロードして解凍し、インストールします。

```bash
agy plugin install /path/to/extracted/gate-sdd
```

*方法2: 直接 clone*

```bash
git clone https://github.com/m0m0i/gate-oriented-sdd
agy plugin install ./gate-oriented-sdd
```

そのあと、Claude Code と同じくプロジェクトの中で `init` を実行してください。どちらのハーネスでも、`init` は何かを尋ねる前にリポジトリを読み、各バリデータを採用する前に実際に走らせ、ゲートが黙っていることを確認してから完了を報告します。

### ゲートを最新に保つ

以下の記述には、3つの印のいずれかを付けています。**検証済み**の記述には、根拠になった [`docs/verified.md`](./docs/verified.md) の実行記録か [`scripts/test-gates.sh`](./scripts/test-gates.sh) のケースを添えています。**ドキュメント記載**の記述には出典の Claude Code ドキュメントを添えており、ここでは実行していません。**未実施**は、実行記録も出典もないことを表します。記述の横にある Issue 番号は、ここでの実行ではなく、下流のプロジェクトでの観測を指します。

**`"autoUpdate": true` が必要な理由。** サードパーティのマーケットプレイスは、既定では自動更新されません。この設定がないと、プロジェクトは各マシンでインストールしたときのバージョンのままになり、ゲートの修正が届かなくなります。0.23.0 で解消したコピーのずれが、気づきにくい形で戻ってくるということです。設定があれば、対話セッションで最初のメッセージを送ったあと、最大10分のランダムな待ち時間をおいてマーケットプレイスが更新され、ディスク上のプラグインも更新されます。実行中のセッションは読み込んだバージョンのまま動き、新しいバージョンは次の起動時か `/reload-plugins` で読み込まれます。プラグインのマニフェストがバージョンを固定しているので、更新はコミットごとではなくリリースごとに届きます。自動更新するかどうかは、次の順に見て最初に設定されているもので決まります。まず、設定ファイルにあるマーケットプレイスのエントリの `autoUpdate` です。同じ名前のエントリが複数のファイルにあるときは、優先度が最も高いファイルのエントリがまるごと使われるので、プロジェクトの中ではプロジェクト自身の宣言で決まります。次が `/plugin` → **Marketplaces** のトグルで、どちらも設定されていなければ既定値のオフになります。`DISABLE_UPDATES=1`、`DISABLE_AUTOUPDATER=1`、`CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1` のどれかを設定すると、`FORCE_AUTOUPDATE_PLUGINS=1` も設定しない限り自動更新は行われません。ドキュメント記載（[プラグインの読み込み](https://code.claude.com/docs/en/plugins/loading#when-auto-update-runs)、[設定](https://code.claude.com/docs/en/settings-reference#extraknownmarketplaces)）。Claude デスクトップアプリはすべてのセッションを `DISABLE_AUTOUPDATER=1` 付きで起動するので、その Code タブのセッションでは自動更新が行われません（検証済み、`docs/verified.md` の U2）。設定ファイルの `env` に `FORCE_AUTOUPDATE_PLUGINS=1` があれば、そのセッションでも自動更新が行われます。0.25.0 からは上の宣言にこの行が含まれています（デスクトップセッションのシェルから検証、`docs/verified.md` の F2）。

**ずれの種類ごとに起きること。**

| 状況 | 起きること | 根拠 |
| :-- | :-- | :-- |
| チームメンバーが初めてリポジトリを開き、フォルダを信頼する | 宣言されたマーケットプレイスが clone されます。マーケットプレイスにあるプラグインのエントリが相対パスなので、プラグインも一緒に取得されます。`/plugin` に `Plugin "gate-sdd" is enabled in project settings but isn't installed here` と表示されたら、`claude plugin install gate-sdd@gate-oriented-sdd --scope project` を一度実行すれば直ります。 | ドキュメント記載（[プラグインの読み込み](https://code.claude.com/docs/en/plugins/loading#enabled-in-project-settings-but-not-installed)）。未実施。ただし M2b では、マーケットプレイスが登録される前に `Skipped auto-recording … enabled only by repo-authored settings` がログに出ている |
| ユーザースコープとプロジェクトスコープの両方で、ピン留めせずにプラグインを有効にしている | プラグイン ID は1つ、キャッシュのパスも1つで、読み込まれるのは1回です。 | 検証済み（V4） |
| ユーザースコープの宣言は `autoUpdate` を書かない `marketplace add` によるもので、プロジェクトは `autoUpdate` 付きで宣言している | プロジェクトの中ではプロジェクトのエントリがまるごと使われるので、そこでは自動更新が有効です。更新されるのはマシンに1つだけのインストールで、そのマシンのすべてのプロジェクトがそれを読み込みます。 | ドキュメント記載（[設定](https://code.claude.com/docs/en/settings-reference#extraknownmarketplaces)）。検証済み（M1、V4） |
| マシン上のセッションをすべて Claude デスクトップアプリから始めていて、プロジェクトの宣言が 0.25.0 より前のもので `env` の行がない | 自動更新は行われないので、手で更新するか、ターミナルでセッションを始めるか、この行を加えるまで、プラグインはインストールしたときのバージョンのままで、その後にリリースされたゲートの修正は届きません。 | 検証済み（U2、U4）。ターミナルのセッションでの自動更新は1回観測（U3）。この行で自動更新が戻ることは F2 |
| マシンのインストールが 0.23.0 より前で、プロジェクトは移行済み | そのマシンでの最初のセッションでは `Stop` のゲートが一切動かず、何も知らせません。0.23.0 より前のバージョンは Claude Code のフックを持たないからです。`env` の行があれば、そのセッションの自動更新でプラグインが更新され、次のセッションからゲートが動きます。行がなければ、手で更新します。バージョンは `claude plugin list` で確認できます。 | キャッシュされた 0.21.3 から 0.24.1 のマニフェストを読んで確認（#274）。セッションでの実行は未実施 |
| マーケットプレイスがすでに登録されているマシンで、プロジェクトが `"ref"` でピン留めする | ピン留めは無視され、共有の clone も動きません。 | 検証済み（V3） |
| マーケットプレイスがまだ登録されていないマシンで、プロジェクトが `"ref"` でピン留めする | ピン留めが有効になり、そのままマシンへの登録になります。そのため、そのマシンのすべてのプロジェクトがそのタグに固定され、あとから同じ名前のピン留めなしの宣言があっても置き換わりません。 | 検証済み（M2c で、`--settings` 経由の宣言がマシン全体で有効になること。V3 で、登録済みの名前に対するあとからの宣言が無視されること）。置き換わらないことはドキュメント記載（[設定](https://code.claude.com/docs/en/settings-reference#extraknownmarketplaces)）。プロジェクト自身のファイルに対する信頼ダイアログは未実施 |
| 同じリポジトリを、別のマーケットプレイス名でも宣言する | プラグイン ID が2つになります。ハーネスはフックの重複を取り除きません（V2）。また、プラグイン側のゲートを止めるかどうかはプロジェクトの設定だけで判定するので、両方のプラグインのゲートが動くことになります。同じ名前のプラグインが2つとも読み込まれるかは、ドキュメントに書かれていません。この宣言はしないでください。 | 未実施 |
| 0.23.0 より前のコピーが `.claude/hooks/` に残り、それを実行する `Stop` エントリもある | セッションが読み込んだ設定のエントリが、コピーを相対パスか絶対パス、または `$CLAUDE_PROJECT_DIR` 経由で指していて、そのコピーがディスク上にあれば、プラグイン側のゲートは動かず、古いコピーが動き続けます。`init` で移行するまでこの状態が続きます。それ以外の方法でコピーにたどり着くエントリでは、プラグイン側のゲートは止まらず、両方が動きます。エントリがなくコピーだけが残っている場合も、プラグイン側のゲートは止まりません。 | 検証済み（`test-gates.sh` の「plugin-gate stands down on a settings entry for the same gate and event, and on nothing less」「plugin-gate stands down on an entry that names the copy through `$CLAUDE_PROJECT_DIR`, and on nothing less」「plugin-gate reads the settings a launch below the git root reads, and resolves from where it was launched」）。`init` が書く、ファイルの存在を確かめてから実行する形は、そこからの推論でテストケースはない。実セッションでは未実施 |
| フォルダが信頼されていない clone、または `.claude/settings.local.json` でプラグインがオフになっている clone | ターン終了時にゲートは動かず、それを知らせるものもありません。CI のバリデータと `check-unreviewed-work.sh` は、pull request 上で引き続き動きます。 | ドキュメント記載（[設定](https://code.claude.com/docs/en/settings-reference#extraknownmarketplaces)）。信頼されていないフォルダの宣言が無視されることは M2b で確認 |
| クラウドセッション（claude.ai/code、`claude --cloud`、routine） | クラウドセッションはリポジトリ自身の設定にあるフックを実行しますが、リポジトリが有効にするプラグインはインストールしません。そのため、移行済みのプロジェクトではそこでゲートが動きません（#260）。 | ドキュメント記載（[クラウド環境](https://code.claude.com/docs/en/cloud-environments#what-carries-over-from-your-setup)）。未実施 |
| Antigravity | 変更はありません。`init` がゲートを `.agents/hooks/` にコピーし、修正はコピーを更新することで届きます。 | 検証済み（コピーがブロックすること。`docs/verified.md` の Antigravity hooks）。`init` の再実行による更新は未実施 |

**ピン留め。** プロジェクトをピン留めしないでください。`init` はピン留めなしの宣言を書きます。これは既定であると同時に、推奨する形でもあります。プロジェクトの宣言に `"ref"` を書いても、固定されるのはプロジェクトではなくマシンで、しかもその宣言でマーケットプレイスを初めて登録したマシンだけです（上の表のピン留めの2行）。その結果、同じコミットでも固定されるチームメンバーとされないメンバーに分かれ、固定されたマシンではほかのプロジェクトもすべて固定されます。また、すべてのリリースにタグが付いているわけではないので、ピン留めで指定できるのは `gate-sdd--v<version>` タグのあるリリースだけです。

**更新。**

- **Claude Code で、次の自動更新を待たずに更新する。** `claude plugin marketplace update gate-oriented-sdd`、続いて `claude plugin update gate-sdd@gate-oriented-sdd` を実行し、新しいセッションを始めます。`/reload-plugins` は更新後のゲートを実行中のセッションに読み込みます（ドキュメント記載）が、その後は `/reload-plugins` もセッションの再開も `GATE_SDD_PLUGIN_ROOT` を設定しなかったので（検証済み、R1）、手で実行するチェックのためには新しいセッションが必要です。ドキュメント記載（[インストール](https://code.claude.com/docs/en/plugins/install#update-plugins-now)）。
- **0.23.0 より前にインストールした Claude Code のプロジェクト**には、まだコピーが残っています。次のコマンドでコピーが表示されます。移行済みのプロジェクトでは何も表示されません。

  ```bash
  ls .claude/hooks/ 2>/dev/null; grep -nE '"(Stop|SessionStart)"' .claude/settings.json
  ```

  `init` をもう一度実行してください。`init` は `gate-lib.sh`、`quality-gate.sh`、`review-gate.sh`、`steering-digest.sh` と、それらの `Stop`・`SessionStart` エントリを削除し、`PostToolUse` の高速チェックは残したまま、`env` の行を含む宣言を書き込みます。ゲートの修正のためにそのプロジェクトで pull request が必要になるのは、これが最後です。0.25.0 より前に移行したプロジェクトの宣言には `env` の行がないので、手で加えるか、`init` をもう一度実行してください。あわせて、`check-steering-anchors.sh` と `check-unreviewed-work.sh` をコピーし直します。0.23.0 より前のコピーのままだと、ソースを変えるターンのたびに品質ゲートがブロックするからです。それらを実行する CI のジョブにはすべてプラグインの checkout と `GATE_SDD_HOOKS` を追加し、`.claude/hooks/` を読んでいたものがほかにないかをプロジェクトの中で探します。どの変更も、先に差分を見せてから行います（#263）。Claude Code のセッションの中でどちらかのチェックを手で実行すると、`GATE_SDD_PLUGIN_ROOT` を通じてプラグインが見つかります。この変数は、セッションの開始時にプラグインが設定します。セッションの外のターミナルでは、`GATE_SDD_HOOKS` にプラグインの `hooks/` を設定してください（#264）。`docs/verified.md` のために、実在する Claude Code のプロジェクトを1つ、この手順に沿って移行しました。`init` のスキル自体は実行していません。ゲート、手で実行したバリデータ、サブエージェントで実行したバリデータ、CI のどれも通っています。新しく加わった次の手順は、この実行で見つかったものです。CI がチェックアウトしたプラグインを `.gitignore` に入れておかないと、ツリー全体を走査するリンターがそのファイルで失敗します。移行済みのプロジェクトでは、クラウドセッションでゲートが動きません（#260）。この欠落は、現時点では対象外としています。
- **Antigravity** には更新コマンドがありません。1.2.16 の `agy plugin` のコマンド一覧にありません（検証済み。`docs/verified.md` の #257 の節）。一度アンインストールしてから、新しい clone かリリースアーカイブからインストールし直します。この手順はここでは実行していません。そのあと、`init` の再実行か手作業でコピーを更新します。5つのファイルはまとめてコピーしてください。各ゲートは、自分より古い `gate-lib.sh` と一緒に使われるとブロックするからです。

  ```bash
  P=/path/to/gate-oriented-sdd   # インストール元の clone、または展開したアーカイブ
  for f in gate-lib.sh quality-gate.sh review-gate.sh steering-digest.sh steering-digest-antigravity.sh; do
    cp "$P/hooks/$f" .agents/hooks/
  done
  ```

- **プラグインを更新しても届かないもの（両ハーネス共通）。** `init` がプロジェクトの scripts ディレクトリにコピーした `check-steering-anchors.sh`、`check-document-set.py`、`check-unreviewed-work.sh`、`check-locks.py`、`_shared/reviewer-contract.md` にある reviewer の契約、そして reviewer とそのルールブックです。スクリプトと reviewer の契約は、プラグインのものと比べて違うものをコピーするか、`init` をもう一度実行してください。ただし、`init` によるアップグレードはまだ検証していません。reviewer は決して上書きしないでください。プロジェクトに合わせて調整されているので、必要な変更は手で取り込み、`check-locks.py --update` でピン留めし直してください。CI でのプラグインの checkout は、ワークフローが指定する `ref` までしか進みません。

  ```bash
  # P: Antigravity では上と同じ。Claude Code では ~/.claude/plugins/installed_plugins.json にある
  # gate-sdd@gate-oriented-sdd の installPath。Antigravity の契約は .agents/agents/ の下にある。
  for f in check-steering-anchors.sh check-document-set.py check-unreviewed-work.sh check-locks.py; do
    [ -f "scripts/$f" ] && diff -q "$P/assets/$f" "scripts/$f"
  done
  diff -q "$P/reviewers/_shared/reviewer-contract.md" .claude/agents/_shared/reviewer-contract.md
  ```

## 2つのハーネス間の再現度

表の各行は、実際に動かして得た結果です。手順、バージョン、未解決の点は [`docs/verified.md`](./docs/verified.md) にあります。

| 機能                            | Claude Code            | Antigravity                               |
| :------------------------------ | :--------------------- | :---------------------------------------- |
| skill | 完全 | 完全（同じパス、同じ形式） |
| reviewer とルールブック | 完全。`init` が `.claude/agents/` にコピーし、reviewer は名前で呼び出します | 完全。同じファイルを `.agents/agents/` にコピーし、そのファイルから `define_subagent` で登録します |
| ルール検出                      | ルートの `AGENTS.md`（正のコンテキストとして読み込み） | `rules/AGENTS.md`（プラグインローダーが自動検出してマージ） |
| ターン終了時の品質ゲート        | 完全（`Stop`, exit 2） | 完全（`Stop`, `{"decision":"continue"}`） |
| review receipt のゲート         | 完全                   | 完全                                      |
| ゲートの配布 | プラグインから（`.claude-plugin/hooks.json` がゲートを実行する。V1、V2）。修正はプラグインの更新で届く。デスクトップアプリから始めたセッションでは、`init` が書く `env` の行があるときだけ自動更新が行われる（#274）。移行済みのプロジェクトでの実セッションは検証済み（`docs/verified.md` の #263 の節）。更新が届くことの確認は未実施（#265）。この行で自動更新が戻ることはデスクトップセッションのシェルから検証（F2） | `init` が `.agents/hooks/` にコピー。修正はコピーの更新で届き、`init` の再実行による更新は未実施 |
| 編集ごとの高速フィードバック    | 完全（`PostToolUse`）  | 完全（`PostToolUse`、観測のみ）           |
| steering digest の注入          | 完全（`SessionStart`） | 完全（`PreInvocation`、ターン1のステップ注入） |
| compaction 後の steering 再注入 | 完全（`SessionStart`） | **なし**（該当するイベントが存在しない）  |

最後の行は誤差ではなく、本物の欠落です。Antigravity にはセッション途中の compaction を検知するイベントが存在しないため、初回ターンでの注入は `PreInvocation` で行いますが、途中でコンテキストが圧縮された場合の再注入は行われません。

## ステータス

**pre-release です。** 検証済みバージョンの一覧を添えた reference implementation であって、サポート付きのプロダクトではありません。[eval スイート](./evals/) は開発中です。4つのケースは書いてありますが、`claude plugin eval` は読み込み時にそれらを拒否する（`case.yaml` に `graders` が必要）ため、まだ一度も実行できていません。

検証環境: Claude Code 2.1.289 / Antigravity CLI 1.2.16（2026-10-06）· Antigravity IDE 2.3.1（2026-08-21）· macOS

**検証できていること。** まず、ゲートとガードの挙動です。モデルを介さず、決定的にテストしています（[`scripts/test-gates.sh`](./scripts/test-gates.sh)。何通りあるかはスイートが持つ数字であって、ここで維持している数字ではありません）。Antigravity の `Stop` フックが実際にブロックすることも、ドキュメントを読んで済ませたのではなく、動かして確かめました（[`docs/verified.md`](./docs/verified.md)）。2つのプラグインマニフェスト、ルールブックのハッシュ、機密混入チェックは、CI で毎回実行しています。skill は13個すべてが、少なくとも一度は実際に動いています。inception の一連の skill と `init` はこのリポジトリ自身か、実在するプロジェクトの使い捨てクローンに対して実行し、`spec`・`clarify`・`implement`・`worklog` は #17 以降のすべての spec で使い、`archive` はこのリポジトリ自身の出荷済み spec に対して何度もスイープしています。inception と `init` の実行で見つかったことは [`docs/verified.md`](./docs/verified.md) に記録し、Issue として起票してあります。そして #17 以降のすべての spec には、`.specs/` の下に review receipt があります。3件を除いてサブエージェントとして起動した reviewer によるレビューで、その3件は inline でレビューしたことが receipt 自体に記録されています。

これから確かめる項目は、[`docs/verified.md`](./docs/verified.md) と Issue に載せています。

## ライセンス

Apache-2.0。
