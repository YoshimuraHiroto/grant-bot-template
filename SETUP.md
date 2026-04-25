# grant-bot — セットアップガイド

このテンプレートは、**自分の事業領域に合わせた助成金・アワード・ピッチを定期検索 → 自動キュレーション → GitHub Pages で共有 → Slack で通知** する仕組みのスケルトンです。Claude Code Desktop の Routine 機能を使ってクラウド実行されるため、PC のスリープ状態でも動作します。

## システム概要

```
[Routine 実行 (週次)]
      ↓
1. Slack フィードバック取り込み (前回以降のメッセージ)
2. 5並列検索 (ポータル/Web/省庁/都道府県東/都道府県西)
3. python scripts/curate.py で機械的フィルタ
   → 確定キープ / 確定除外 / 要検証 に3分類
4. LLM が要検証項目を WebSearch で補完
5. python scripts/postprocess.py で最終整形
6. git push → GitHub Actions が Pages へ自動同期
7. Slack に新着サマリ通知
```

## 前提

- GitHub アカウント
- Claude Code Desktop (Slack 連携設定済み)
- Slack ワークスペース (通知用、任意)

---

## Step 1: 2つの GitHub リポジトリを作成

| リポジトリ | 公開設定 | 用途 |
|-----------|---------|------|
| `<your-bot>` | **Private** | コード・設定・メモリ。Routine の接続先 |
| `<your-bot>-pages` | **Public** | GitHub Pages 配信用 (HTML + grants.json のみ) |

例: `grant-bot` (Private) + `grant-pages` (Public)

```bash
# GitHub UI で作成、または gh コマンド
gh repo create <YOUR_USERNAME>/<your-bot> --private
gh repo create <YOUR_USERNAME>/<your-bot>-pages --public
```

---

## Step 2: テンプレートを clone

```bash
git clone -b template https://github.com/<original-repo-owner>/grant-bot.git my-bot
cd my-bot
git remote set-url origin https://github.com/<YOUR_USERNAME>/<your-bot>.git
git checkout -b main
```

---

## Step 3: 設定ファイルを編集

### a) `config/company_profile.json` — 必須

応募主体の情報。検索エージェントが「関連性判定」と「応募資格判定」に使用します。

| フィールド | 内容 | 例 |
|----------|-----|---|
| `company_name` | 会社・組織名 | `株式会社〇〇` |
| `organization_type` | 法人格 | `株式会社`, `合同会社`, `一般社団法人` |
| `business_domains` | 事業領域 (複数) | `["AI開発", "データ解析"]` |
| `key_expertise` | コア技術・専門性 | `["深層学習", "気候モデル"]` |
| `eligibility_facts.location` | 拠点 (都道府県) | `東京都` |
| `research_capabilities.partnerships` | 大学・研究機関との連携実績 | `["〇〇大学〇〇研究室"]` |
| `notes` | 自由記述 (業界での立ち位置等) | — |

`partnerships` は重要です。多くの公的研究助成（JST CREST、RISTEX 等）は「大学等との共同提案必須」のため、連携実績がある大学を記載しておくと適格性判定が正確になります。

### b) `config/search_config.json` — 任意

`themes` を編集して、自分の検索テーマに置き換えます。デフォルトでは以下6テーマが設定済み:

- 防災・減災
- 衛星 (地球観測データ解析)
- AI・データ解析
- 脱炭素・環境
- 社会課題解決・サステナビリティ
- グローバルサウス・新興国社会課題

**カスタマイズ方法**:

```json
{
  "id": "your_theme_id",
  "name_ja": "あなたのテーマ名",
  "keywords_ja": ["キーワード1", "キーワード2"],
  "keywords_en": ["keyword1", "keyword2"]
}
```

不要なテーマは配列から削除してください。

### c) `memory/generalized_rules.json` — 任意

固有の除外ルール (例: 「特定分野は対象外」) を初期から書いておけます。Routine がユーザーフィードバック (Slack) から自動学習しますが、明確なルールがあれば最初から書いておくと精度が上がります。

```json
{
  "exclusion_rules": [
    {
      "id": "ex_0001",
      "rule": "個人向けの奨学金や留学助成は除外する",
      "confidence": 0.9
    }
  ]
}
```

---

## Step 4: Pages リポジトリへのデプロイを設定

### a) Personal Access Token (PAT) を作成

1. https://github.com/settings/tokens?type=beta → **Fine-grained tokens** → **Generate new token**
2. **Repository access**: `<your-bot>-pages` のみ
3. **Repository permissions** → **Contents** → **Read and write**
4. **Generate** → 表示されたトークンをコピー

### b) Repository Secret に登録

`<your-bot>` (Private) リポジトリで:

Settings → Secrets and variables → Actions → **New repository secret**
- Name: `PAGES_DEPLOY_TOKEN`
- Value: 上で取得したトークン

### c) リポジトリ名のプレースホルダを置換

以下2ファイルの `<YOUR_GITHUB_USERNAME>` と `<YOUR_PAGES_REPO_NAME>` を実際の値に書き換える:

**`.github/workflows/deploy-pages.yml`** (line 19付近):
```yaml
git push --force https://x-access-token:${{ secrets.PAGES_DEPLOY_TOKEN }}@github.com/<YOUR_GITHUB_USERNAME>/<YOUR_PAGES_REPO_NAME>.git main
```

**`docs/index.html`** (line 240付近):
```javascript
const REPO_OWNER = '<YOUR_GITHUB_USERNAME>';
const REPO_PAGES = '<YOUR_PAGES_REPO_NAME>';
```

---

## Step 5: 初期 push

```bash
git add -A
git commit -m "Initial setup"
git push -u origin main
```

GitHub Actions が起動し、`<your-bot>-pages` に空のサイトがデプロイされます。

---

## Step 6: GitHub Pages を有効化

`<your-bot>-pages` リポジトリで:

Settings → Pages → **Source**: `Deploy from a branch` → **Branch**: `main` / `(root)` → **Save**

数十秒で `https://<YOUR_USERNAME>.github.io/<your-bot>-pages/` が公開されます (この時点では空のリスト)。

---

## Step 7: Claude Code Desktop で Routine を作成

1. Claude Code Desktop → Routines → **新規作成**
2. **設定**:
   - **名前**: 助成金定期検索 (任意)
   - **モデル**: Opus 4.6 拡張
   - **リポジトリ**: `<your-bot>`
   - **トリガー**: スケジュール `0 2 * * 0` (毎週日曜 02:00)
   - **コネクタ**: Slack (通知用)
3. **プロンプト**: 下記をコピーして貼り付け、**`#YOUR_SLACK_CHANNEL`** を実際のチャンネル名に置換

### Routine プロンプト

```
CLAUDE.md の指示に従い、助成金の定期検索パイプラインを実行する。

### 0. フィードバック取り込み
memory/feedback_log.jsonl の最終 slack_ts を確認し、Slack コネクタで
通知チャンネル #YOUR_SLACK_CHANNEL の新着メッセージを取得する。
「🚩 Grant Feedback」で始まるメッセージと自由記述を解析し、
CLAUDE.md の「フィードバック取り込み」セクションに従って memory/ を更新する。

### 1. 準備
config/search_config.json、config/company_profile.json、memory/ を読み込む。
docs/data/overrides.json、docs/data/archive/ の過去結果も参照する。

### 2. 並列検索 (Agent ツールで5並列)
- Agent A: ポータルサイト検索 (search_config.json の portals)
- Agent B: Web検索 (日本語15-20件 + 英語5-10件、全 themes 対象)
- Agent C: 省庁別検索 (search_config.json の ministries)
- Agent D: 都道府県検索・東日本 (北海道〜中部)
- Agent E: 都道府県検索・西日本 (近畿〜沖縄)

各エージェントには search_config.json のテーマと company_profile.json、
generalized_rules.json を渡す。結果は CLAUDE.md のスキーマに従う JSON で返す。

### 3. 統合・キュレーション (Python に委譲してアイドルタイム削減)
全エージェント結果を /tmp/combined.json に統合し、以下を実行:

  python3 scripts/curate.py /tmp/combined.json \
    --output-partial docs/data/grants_partial.json \
    --report docs/data/curation_report.json

curation_report.json の needs_verify を読み、各項目について WebSearch で
verify_hints に従って情報補完。基準を満たしたら grants_partial.json の
grants 配列に追記。

### 4. 最終整形
docs/data/grants.json の前回版を docs/data/archive/grants-<date>.json に退避。
grants_partial.json を docs/data/grants.json に rename。
overrides.json から、新 grants.json に存在しない ID を削除。
postprocess.py で ID 再採番:

  python3 scripts/postprocess.py docs/data/grants.json

memory/keyword_registry.json (hit_rate) と memory/search_history.jsonl を更新
(本回のゲート除外件数も含める)。

### 5. デプロイ
git add docs/ memory/
git commit -m "検索結果更新: $(date +%Y-%m-%d)"
git push

GitHub Actions が <your-bot>-pages に自動同期する。

### 6. Slack 通知
Slack コネクタで #YOUR_SLACK_CHANNEL に投稿:
- 検索日、新着件数、合計件数、ゲート毎の除外件数
- 新着助成金の上位10件サマリ (名前・団体・締切・金額)
- GitHub Pages URL: https://<YOUR_USERNAME>.github.io/<your-bot>-pages/
```

---

## Step 8: 動作確認

1. Routine の **手動実行** ボタンで初回テスト
2. 完了後、`<your-bot>` のコミット履歴に `検索結果更新: YYYY-MM-DD` が追加されているか確認
3. `<your-bot>-pages` の Actions が成功していることを確認
4. `https://<YOUR_USERNAME>.github.io/<your-bot>-pages/` で助成金リストが表示されるか確認
5. Slack チャンネルにサマリが投稿されているか確認

---

## カスタマイズ Tips

### 新しいテーマを追加
`config/search_config.json` の `themes` 配列に追加:

```json
{
  "id": "my_new_theme",
  "name_ja": "新テーマ",
  "keywords_ja": ["キーワード1", "キーワード2"],
  "keywords_en": ["keyword1", "keyword2"]
}
```

### キュレーションの厳格度を調整

`scripts/curate.py` で以下を編集:

| 定数 | 用途 |
|------|-----|
| `MONEY_PATTERNS` | 「具体的な金額あり」と判定する正規表現 |
| `UNCLEAR_VALUES` | 曖昧と判定する文字列 (要確認、TBD 等) |
| `VAGUE_MONEY_HINTS` | 「金額の手がかりはあるが具体額は要確認」と判定するパターン |
| `OVERSEAS_KW` / `NATIONAL_KW` / `LOCAL_KW` / `PRIVATE_KW` | 団体区分の分類キーワード |

### Pages の表示をカスタマイズ

`docs/index.html` で:
- フィルタ項目の追加/削除
- 列の追加/削除
- カテゴリの色分け (`--cat-*` CSS 変数)

### ユーザーフィードバックの活用

Pages の各行に **🚩** ボタンがあり、クリックすると Slack 投稿用テンプレートがクリップボードにコピーされます。Slack に貼り付けて送信すれば、次回の Routine 実行時に自動で `memory/generalized_rules.json` に学習されます。

---

## トラブルシューティング

### Pages が更新されない
- `<your-bot>` の Actions タブでデプロイエラーを確認
- `PAGES_DEPLOY_TOKEN` の権限を確認 (Contents: Read and write)
- PAT の有効期限を確認 (Fine-grained は最大1年)

### Routine がタイムアウトする
- Extended Thinking が長時間かかると `Stream idle timeout` が発生する
- `scripts/curate.py` で機械的処理を Python に寄せている (LLM のアイドルタイム削減)
- 並列検索エージェント数を5以下に保つ (Agent A〜E)
- WebSearch 対象を `needs_verify` のみに絞る (curation_report.json の指示通り)

### grants.json が空のまま
- 検索結果が `combined.json` に正しく統合されているか確認
- `search_config.json` のテーマが狭すぎないか確認
- `company_profile.json` の記述が薄いと関連性判定が機能しないので、`notes` フィールドを充実させる

### Slack 通知が来ない
- Slack コネクタが Routine に追加されているか確認
- プロンプト内の `#YOUR_SLACK_CHANNEL` を実際のチャンネル名に置換しているか確認
- 通知用チャンネルに Bot を招待 (Slack: `/invite @Claude`)

---

## ファイル構成

```
<your-bot>/
├── CLAUDE.md                       # ルーチンへの指示書 (汎用、編集不要)
├── SETUP.md                        # このファイル
├── .github/workflows/
│   └── deploy-pages.yml            # ★Step 4-c で編集
├── config/
│   ├── search_config.json          # ★Step 3-b で編集 (任意)
│   └── company_profile.json        # ★Step 3-a で編集 (必須)
├── memory/
│   ├── generalized_rules.json      # ★Step 3-c で編集 (任意)
│   ├── keyword_registry.json       # 自動更新
│   ├── feedback_log.jsonl          # 自動更新
│   └── search_history.jsonl        # 自動更新
├── scripts/
│   ├── curate.py                   # キュレーションスクリプト (汎用)
│   └── postprocess.py              # 最終整形 (汎用)
├── docs/                           # GitHub Pages ソース
│   ├── index.html                  # ★Step 4-c で REPO 定数を編集
│   └── data/
│       ├── grants.json             # 自動更新
│       ├── overrides.json          # ユーザー手動修正用
│       └── archive/                # 過去結果
└── .gitignore
```

`★` マーク = 初期セットアップで編集が必要なファイル

---

## ライセンス・帰属

このテンプレートは MIT ライセンス相当で自由に使用・改変可能です。改変版を公開する際は、元リポジトリへのリンクを README に含めていただけると幸いです。
