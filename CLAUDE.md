# grant-bot — 助成金自動検索・通知システム

## 概要
企業向け助成金を定期検索し、GitHub Pages で共有、Slack で通知する。
Cloud Routine により毎週日曜に自動実行。

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

## メモリ管理

### memory/keyword_registry.json
キーワードごとのヒット率・フィードバック率を追跡。検索実行後に更新する。

### memory/search_history.jsonl
各実行のサマリを1行JSONで追記。フォーマット:
```json
{"date": "YYYY-MM-DD", "grants_found": 52, "new_grants": 10, "themes": ["防災", "AI"]}
```

### memory/generalized_rules.json
ユーザーフィードバックから抽出した除外・重視ルール。検索時に参照する。

## 利用可能なスクリプト

### scripts/postprocess.py
期限切れ分離・ID正規化・フォーマット統一。
```bash
python scripts/postprocess.py docs/data/grants.json
```

## デプロイフロー
1. docs/data/grants.json を更新
2. memory/ を更新
3. `git add docs/ memory/ && git commit && git push`
4. GitHub Actions が自動で grant-pages (Public) に同期
5. GitHub Pages が自動更新

## Slack 通知フォーマット
新着助成金のサマリ（名前・団体・締切・金額）上位10件 + Pages URL リンク
