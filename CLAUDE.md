# grant-bot — 助成金自動検索・通知システム

## 概要
企業向け助成金を定期検索し、GitHub Pages で共有、Slack で通知する。
Cloud Routine により毎週日曜に自動実行。ユーザーフィードバック（Slack投稿・overrides.json）を反映する。

## 検索テーマ
config/search_config.json を参照。主要テーマ:
- 防災・減災
- 衛星・リモートセンシング
- AI・データ解析
- 脱炭素・カーボンクレジット
- 生物多様性・ブルーカーボン

## 企業プロファイル
config/company_profile.json を参照。応募主体は株式会社（企業）。
主な事業領域: 人工衛星データ解析、AI・データサイエンス開発、気候モデル・物理シミュレーション。

## 検索品質基準

### 残す条件
- 金銭的支援（補助金・助成金・賞金等）があるもの
- 企業（株式会社等）が応募可能なもの
- 募集中または近日公募開始のもの

### 除外する条件
- メンタリングのみ、技術サポートのみ（金銭支援なし）のアクセラレーター
- 賞金なしの表彰・アワード
- NPO限定・個人限定・学生限定で企業応募不可
- 募集終了・期限切れ
- 純粋な情報提供イベント、過去の成果発表
- memory/generalized_rules.json の exclusion_rules に該当するもの

### 重複除去
- URL正規化（protocol/www/trailing slash/query params除去）で完全一致
- 名前+団体のSequenceMatcher類似度 85%以上でフォールバック

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
〜省、〜庁、内閣府、JAXA、NEDO、JST、AMED、国立研究開発法人〜、中小企業基盤整備機構

### 地方自治体
都道府県名を含む、〜市・〜区・〜町・〜村、〜振興公社、〜産業創出支援機構

### 民間
株式会社、一般社団法人、公益財団法人、一般財団法人、NPO法人、技術研究組合

### 海外
英語名の組織（NASA, ESA, Google, etc.）、国際機関（ITU, UN系）、外国政府機関

## overrides.json の扱い

`docs/data/overrides.json` は Pages ユーザーが手動で修正を書き込む場所。形式:

```json
{
  "GR-20260318-001": {
    "deadline": "2026-05-20",
    "notes": "[修正] 締切延長"
  },
  "GR-20260318-099": {
    "hidden": true
  }
}
```

### Routine での扱い
1. 検索前に overrides.json を読み込む
2. 新しい grants.json を生成後、overrides.json の各エントリについて:
   - 対応する助成金 ID が新 grants.json にも存在する → overrides をそのまま保持
   - 対応する ID が消えた → overrides.json から削除（grants.json 側から消えたら修正意図も失効）
3. `hidden: true` の助成金は Pages 上で非表示になる（UI側でフィルタ）
4. overrides.json も git commit に含める

## フィードバック取り込み

### Slack フィードバック
Pages から 🚩 ボタンで投稿される Slack メッセージは以下の形式:

```
🚩 Grant Feedback
ID: GR-YYYYMMDD-NNN
Name: ...
Type: 除外希望 | 情報修正 | ルール提案 | その他
Comment: ...
```

### 処理手順（Routine 実行時の冒頭で実施）

1. **memory/feedback_log.jsonl の最終 slack_ts を確認**
2. **Slack コネクタで通知チャンネルの新着メッセージを取得**（前回以降 or 過去2週間）
3. 各メッセージを解析:
   - `🚩 Grant Feedback` で始まるもの → 構造化フィードバック
   - 自由記述のもの → Type を推論
4. **フィードバックの反映**:
   - **除外希望 (exclude)**:
     - 該当 ID を overrides.json に `{"hidden": true}` で追加
     - 似た助成金が繰り返し除外される傾向があれば exclusion_rules を追加
   - **情報修正 (correct)**:
     - コメントを解析して修正内容を抽出
     - overrides.json に該当 ID の修正を追加（例: `{"deadline": "2026-05-20"}`）
   - **ルール提案 (rule)**:
     - memory/generalized_rules.json の exclusion_rules または search_preferences に追加
     - confidence は 0.5 で初期値、繰り返されたら 0.8 以上に引き上げ
   - **その他**:
     - メタ情報として memory/feedback_log.jsonl に記録のみ
5. **memory/feedback_log.jsonl に追記**:
   ```json
   {"date": "YYYY-MM-DD", "slack_ts": "...", "grant_id": "GR-...", "type": "exclude", "comment": "...", "action_taken": "overrides.json updated"}
   ```
6. 処理済み slack_ts を次回の起点として記録

## メモリ管理

### memory/keyword_registry.json
キーワードごとのヒット率・フィードバック率を追跡。検索実行後に更新する。

### memory/search_history.jsonl
各実行のサマリを1行JSONで追記。フォーマット:
```json
{"date": "YYYY-MM-DD", "grants_found": 52, "new_grants": 10, "themes": ["防災", "AI"]}
```

### memory/generalized_rules.json
ユーザーフィードバックから抽出した除外・重視ルール。検索時に必ず参照する。

### memory/feedback_log.jsonl
Slack フィードバックの処理履歴。

## 利用可能なスクリプト

### scripts/postprocess.py
期限切れ分離・ID正規化・フォーマット統一。
```bash
python scripts/postprocess.py docs/data/grants.json
```

## デプロイフロー
1. docs/data/grants.json を更新
2. docs/data/overrides.json の不要エントリ（grants.json に存在しない ID）を削除
3. memory/ を更新
4. `git add docs/ memory/ && git commit && git push`
5. GitHub Actions が自動で grant-pages (Public) に同期
6. GitHub Pages が自動更新

## Slack 通知フォーマット
新着助成金のサマリ（名前・団体・締切・金額）上位10件 + Pages URL リンク
