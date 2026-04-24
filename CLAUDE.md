# grant-bot — 助成金自動検索・通知システム

## 概要
企業向け助成金を定期検索し、GitHub Pages で共有、Slack で通知する汎用的な仕組み。
Cloud Routine により定期実行され、ユーザーフィードバック（Slack投稿・overrides.json）を反映する。

検索テーマ・応募主体・除外ルール等のユーザー固有情報は以下に分離:
- `config/search_config.json` — 検索テーマ・キーワード・ポータル等
- `config/company_profile.json` — 応募主体の情報（企業プロファイル）
- `memory/generalized_rules.json` — フィードバックで学習した固有ルール

## 設定ファイルの参照

### config/search_config.json
- `themes`: 検索テーマ一覧（日英キーワード付き）
- `opportunity_types`: 対象とする機会の種別（grant/challenge/award/pitch 等）
- `portals`: 検索対象のポータルサイト
- `prefectures` / `ministries`: 地方自治体・省庁一覧
- `web_queries_template`: 汎用クエリテンプレート
- `broad_program_categories`: 広範プログラムのカテゴリヒント（具体名は含まない）
- `exclusion_patterns`: 汎用的な除外パターン

### config/company_profile.json
応募主体の情報（事業領域・専門性・過去実績・拠点・連携実績等）。
検索の関連性判定と応募資格判定に使用する。

### memory/generalized_rules.json
ユーザーフィードバックから蓄積された固有の包含/除外ルール。
例: 特定サブテーマの除外、特定対象の重視 等。検索・キュレーション時に必ず参照。

## 検索品質基準（汎用）

### 残す条件
- 金銭的支援（補助金・助成金・賞金等）があるもの
- `company_profile.json` の `organization_type` に合致する応募主体が応募可能なもの
- 募集中または近日公募開始のもの

### 除外する条件
- メンタリングのみ、技術サポートのみ（金銭支援なし）のアクセラレーター
- 賞金なしの表彰・アワード
- 応募主体外（NPO限定・個人限定・学生限定等で `company_profile.json` の応募主体が応募不可）
- 募集終了・期限切れ（Routine 実行日時点で `deadline < today`）
- 純粋な情報提供イベント、過去の成果発表
- `memory/generalized_rules.json` の `exclusion_rules` に該当するもの
- `amount` に金額単位（万円・円・$・€・CHF・助成率 等）が含まれないもの
- `amount` / `duration` / `deadline` / `eligibility_summary` のうち **3つ以上**が「要確認/不明/未定/TBD/-」
- `opportunity_type: "accelerator"` で金銭支援（投資額・助成金額）の明示がないもの
- `eligibility_summary` が10文字未満の極短記述
- `deadline` が許容フォーマット外（下記「データフォーマット規定」参照）

### 重複除去
- URL正規化（protocol/www/trailing slash/query params除去）で完全一致
- 名前+団体のSequenceMatcher類似度 85%以上でフォールバック

### 品質ゲート（3層チェック）
1. **検索エージェント段階**: 取得時点で品質基準に合致するもののみ採用
2. **curator 段階** (Routine 内): 統合後に全件を再フィルタ
   - `today = <Routine 実行日>` として `deadline < today` を除外
   - `amount` の金額単位を正規表現で検証
   - 情報充足度カウント（3つ以上が "要確認" なら除外）
   - accelerator タイプの金銭支援検証
   - `generalized_rules.json` の exclusion_rules を適用
3. **postprocess.py 段階**: 最終確認として自動除外

### 「要確認」フィールドの必須再調査
以下のフィールドが「要確認」「不明」「TBD」「-」「Variable」等の場合、
**除外判定前に必ず WebSearch で公募要領や公式ページを確認して情報を補完する**:

- `amount`: 公募要領の「研究開発費」「助成限度額」「補助率」セクション
- `duration`: 「研究開発期間」「事業期間」セクション
- `eligibility_summary`: 「応募資格」「対象者」セクション
- `deadline`: 「公募期間」「提案書受付期限」

国の研究開発プログラムは公募要領 PDF が公式サイトで公開されているため必ず確認する。
再調査で情報が得られた場合は、フィールドを更新してから品質ゲートを再評価する。

### 広範な研究開発・アワード系プログラムの網羅

`search_config.json` の `broad_program_categories` に定義された各カテゴリについて、
Routine 実行時に `query_hints` を使って最新の公募を探索する:

- 戦略的研究開発プログラム
- 社会課題解決・共創型プログラム
- ムーンショット型・超長期研究
- 環境研究総合推進費・環境関連公的助成
- 民間財団の研究助成
- サステナビリティ・ESGアワード/ピッチ
- 国際研究開発プログラム

これらは**ソリューションテーマを限定しない**ことが多く、`company_profile.json`
のコア技術が適用可能な領域で応募可能なら残す。

### 応募資格の判定ルール（共同応募可能性）

「応募主体外」の明示的な除外条項がない限り、共同応募の可能性を WebSearch で確認する。

#### 「大学等との連携必須」タイプ
国の研究開発プログラムには「研究代表者または協働実施者の少なくとも一方が大学等」
という条件が多い。応募主体単独では応募不可でも、
`company_profile.json` の `partnerships` に記載された大学・公的研究機関との
共同提案なら参加可能なケースが多い。

→ **除外せず残す**が、`notes` に **`[応募可能性] 大学等との共同提案必須`** を明記。

#### 「地域拠点が必要」タイプ
地方自治体の助成金で「県内事業所を有する者」が要件の場合、
補助事業期間中に拠点を設置する予定があれば応募可能なケースがある。
WebSearch で確認し、可能なら残す（`notes` に条件を明記）。

#### 明確に除外すべきもの
- 「NPO法人のみ」「個人事業主のみ」「学生のみ」明示
- 「大学・研究機関のみ」（企業参加不可）明示
- `company_profile.json` の応募主体に該当しない業種限定

### ユーザー固有の選好・除外ルール

テーマの絞り込み（例: ある分野の中でも特定サブテーマのみ対象）は、
`memory/generalized_rules.json` の `exclusion_rules` / `search_preferences` に
記載されたルールに従う。このファイルはユーザーフィードバックで更新される。

ルール文言に該当する助成金の扱い方:
- **完全除外**: ルールが `confidence >= 0.8` かつ明確な除外指示
- **条件付き残存**: ルールが「複数テーマを含む場合はテーマ限定で応募可能なら残す」
  という趣旨なら、notes に `[応募対象] <対象テーマ>のみ。<除外テーマ>は対象外` を明記して残す

## データフォーマット規定

### deadline の許容値（これ以外は禁止）
- `YYYY-MM-DD` 形式（例: `2026-05-20`）— 具体日
- `通年募集` — 明確に通年受付している場合のみ
- `要確認` — やむを得ない場合のみ、notes に状況を追記

**禁止例**: `"2026-02-24説明会実施"`, `"随時公募"`, `"継続募集"`, `"公募時期要確認"`, `"年1回公募（令和7年度は5月21日締切）"`, `"TBD"`

曖昧な記述は以下のように正規化:
- 「〜年度は〜日締切」→ その日付を YYYY-MM-DD に変換
- 「随時」「継続」→ `通年募集` か除外かを判定
- 「説明会実施」「公募開始」「発表済」等の混入 → 具体日だけ抽出

### amount の必須要件（これ以外は除外）
必ず以下のいずれかを含むこと:
- 数値 + 金額単位: `万円`, `千円`, `円`, `$`, `USD`, `EUR`, `€`, `CHF` 等
- 助成率: `補助率2/3`, `50%`, `分の1` 等
- プロジェクト予算規模: `$500K-$3M`, `上限1億円`, `〜千万円規模` 等

**禁止例**: `"Variable"`, `"Fellowship program"`, `"Accelerator support"`, `"-"`, `"未明示"`, `"要確認"`, `"事業提携・投資機会"`

該当しない場合は WebSearch で再調査し、確認できなければ除外する。

### 期限3日以内の警告
`deadline` が `YYYY-MM-DD` 形式で、実行日から3日以内のものは `notes` の先頭に `⚠️ 締切3日以内` を追記する。

## 出力スキーマ (docs/data/grants.json)

```json
{
  "date": "YYYY-MM-DD",
  "summary": {
    "total_grants": 52,
    "by_category": {"海外": 6, "国・省庁": 15, "地方自治体": 27, "民間": 4}
  },
  "grants": [
    {
      "id": "GR-YYYYMMDD-NNN",
      "name": "助成金名",
      "organization": "助成団体名",
      "organization_category": "国・省庁 | 地方自治体 | 民間 | 海外",
      "keywords": "キーワード1, キーワード2",
      "amount": "最大1,000万円（補助率2/3）",
      "duration": "最大3年",
      "eligibility_summary": "応募条件のサマリ",
      "deadline": "YYYY-MM-DD",
      "url": "https://...",
      "opportunity_type": "grant | challenge | award | pitch | accelerator | certification",
      "confidence": 0.9,
      "notes": "補足情報"
    }
  ]
}
```

## 団体区分 (organization_category) の分類ルール

### 国・省庁
〜省、〜庁、内閣府、国立研究開発法人〜、中小企業基盤整備機構 等の国の機関

### 地方自治体
都道府県名を含む、〜市・〜区・〜町・〜村、〜振興公社、〜産業創出支援機構 等

### 民間
株式会社、一般社団法人、公益財団法人、一般財団法人、NPO法人、技術研究組合 等

### 海外
英語名の組織、国際機関、外国政府機関

## overrides.json の扱い

`docs/data/overrides.json` は Pages ユーザーが手動で修正を書き込む場所。形式:

```json
{
  "GR-YYYYMMDD-NNN": {
    "deadline": "2026-05-20",
    "notes": "[修正] 締切延長"
  },
  "GR-YYYYMMDD-NNN": {
    "hidden": true
  }
}
```

### Routine での扱い
1. 検索前に overrides.json を読み込む
2. 新しい grants.json を生成後、overrides.json の各エントリについて:
   - 対応する ID が新 grants.json にも存在する → overrides をそのまま保持
   - 対応する ID が消えた → overrides.json から削除
3. `hidden: true` の助成金は Pages 上で非表示になる（UI側でフィルタ）
4. overrides.json も git commit に含める

## フィードバック取り込み

### Slack フィードバック形式
Pages から 🚩 ボタンで投稿される Slack メッセージ:

```
🚩 Grant Feedback
ID: GR-YYYYMMDD-NNN
Name: ...
Type: 除外希望 | 情報修正 | ルール提案 | その他
Comment: ...
```

### 処理手順（Routine 実行時の冒頭で実施）

1. `memory/feedback_log.jsonl` の最終 slack_ts を確認
2. Slack コネクタで通知チャンネルの新着メッセージを取得
3. 各メッセージを解析（`🚩 Grant Feedback` で始まる構造化と自由記述）
4. フィードバックの反映:
   - **除外希望**: 該当 ID を overrides.json に `{"hidden": true}` で追加。類似傾向があれば exclusion_rules に追加
   - **情報修正**: overrides.json に該当 ID の修正を追加
   - **ルール提案**: `generalized_rules.json` に追加（初期 confidence 0.5、繰り返されたら引き上げ）
   - **その他**: feedback_log.jsonl に記録のみ
5. `feedback_log.jsonl` に処理履歴を追記

## メモリ管理

### memory/keyword_registry.json
キーワードごとのヒット率・フィードバック率を追跡。検索実行後に更新。

### memory/search_history.jsonl
各実行のサマリを1行JSONで追記。

### memory/generalized_rules.json
ユーザーフィードバックから抽出した包含/除外ルール。検索時に必ず参照。

### memory/feedback_log.jsonl
Slack フィードバックの処理履歴。

## 利用可能なスクリプト

### scripts/curate.py（キュレーションの主体）
検索エージェントが集めた生の統合 JSON を機械的に処理し、3分類する:

- **CONFIRMED_KEEP**: 全ゲート通過、情報充分 → `docs/data/grants_partial.json` に出力
- **CONFIRMED_REMOVE**: 確実に除外（期限切れ・明白な重複）
- **NEEDS_VERIFY**: 正規化失敗や情報不足だが回復可能性あり → LLM が WebSearch で検証

```bash
python scripts/curate.py <input.json> \
  --output-partial docs/data/grants_partial.json \
  --report docs/data/curation_report.json \
  --today YYYY-MM-DD
```

### scripts/postprocess.py（最終整形）
LLM の検証完了後、ID再採番・期限切れ最終チェック・フォーマット統一。
```bash
python scripts/postprocess.py docs/data/grants.json
```

## Routine の推奨ワークフロー（タイムアウト対策）

LLM の Extended Thinking 時間を最小化するため、**機械的判定は Python、意味判定のみ LLM** で分担:

1. **並列検索**（LLM, Agent ツール）: 5エージェントで生データ収集 → `combined.json` に統合
2. **curate.py 実行**（Python, 数秒）: ゲート2/3/4/5/6を一括適用
   - 出力: `grants_partial.json`（確定キープ）+ `curation_report.json`（除外ログ + 要検証リスト）
3. **検証ループ**（LLM, WebSearch）: `curation_report.json` の `needs_verify` を読み、各項目について:
   - `verify_hints` を参考に WebSearch/WebFetch で公式情報を確認
   - 正規化失敗の場合: パース不能だった表現から実際の締切を取り出す
   - 曖昧金額の場合: 公募要領で具体額を確認
   - 情報不足の場合: 公募要領 PDF で補完
   - 基準を満たしたら `grants_partial.json` の grants 配列に追記
   - 満たさなければ除外ログに追加
4. **postprocess.py 実行**（Python）: ID再採番、最終整形
5. **Git コミット・プッシュ**
6. **Slack 通知**

この分担により、LLM は 10〜30件程度の verify 処理のみを担当し、
ストリームのアイドルタイム（idle timeout 原因）を大幅に削減できる。

## デプロイフロー
1. docs/data/grants.json を更新
2. docs/data/overrides.json の不要エントリを削除
3. memory/ を更新
4. `git add docs/ memory/ && git commit && git push`
5. GitHub Actions が自動で grant-pages (Public) に同期
6. GitHub Pages が自動更新

## Slack 通知フォーマット
新着助成金のサマリ（名前・団体・締切・金額）上位N件 + Pages URL リンク。
N と投稿先チャンネルは Routine プロンプトで指定。
