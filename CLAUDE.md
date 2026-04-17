# grant-bot — 助成金自動検索・通知システム

## 概要
企業向け助成金を定期検索し、GitHub Pages で共有、Slack で通知する。
Cloud Routine により毎週日曜に自動実行。ユーザーフィードバック（Slack投稿・overrides.json）を反映する。

## 検索テーマ
config/search_config.json を参照。主要テーマ:
- 防災・減災
- **地球観測衛星データの解析・利活用**（SAR/InSAR、リモートセンシング）
- AI・データ解析
- 脱炭素・カーボンクレジット
- 生物多様性・ブルーカーボン

### 宇宙・衛星関連の判定基準（重要）

宇宙関連の助成金は、**地球観測衛星データの解析・利活用をテーマに応募可能なもののみ** 対象とする。

#### 対象（残す）
- SAR/InSAR 解析、リモートセンシング
- 衛星データプラットフォーム、EO ソリューション開発
- 衛星データを活用した防災・気候・環境アプリケーション

#### 非対象（除外）
- **衛星通信**: 通信衛星、光通信、5G/Beyond 5G 通信インフラ
- **衛星打ち上げ**: ロケット開発、射場整備、輸送技術
- **衛星本体製造**: コンステレーション構築、衛星コンポーネント開発、軌道上サービス

#### 複数テーマを含む助成金（JAXA宇宙戦略基金・NASA SBIR等）
→ EO/データ利活用テーマで応募可能なら **残す**。
   `notes` に **`[応募対象] <EO関連テーマ>のみ。<除外テーマ>は対象外`** を明記する。

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
- 募集終了・期限切れ（Routine 実行日時点で `deadline < today`）
- 純粋な情報提供イベント、過去の成果発表
- memory/generalized_rules.json の exclusion_rules に該当するもの
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
3. **postprocess.py 段階**: 最終確認として自動除外

### 「要確認」フィールドの必須再調査
以下のフィールドが「要確認」「不明」「TBD」「-」「Variable」等の場合、
**除外判定前に必ず WebSearch で公募要領や公式ページを確認して情報を補完する**:

- `amount`: 公募要領の「研究開発費」「助成限度額」「補助率」セクションから取得
- `duration`: 「研究開発期間」「事業期間」セクション
- `eligibility_summary`: 「応募資格」「対象者」セクション
- `deadline`: 「公募期間」「提案書受付期限」

特に国の研究開発プログラム（JST / NEDO / AMED / 内閣府SIP等）は、
公募要領の PDF が公式サイトで公開されているため、必ず確認する。

再調査で情報が得られた場合は、フィールドを更新してから品質ゲートを再評価する。

### 広範な気候変動・SDGs プログラムの網羅

テーマを限定しないが ME-Lab Japan のコア技術（衛星データ解析・AI・気候シミュレーション）が適用可能な助成金を見逃さないこと。

#### 重点探索カテゴリ

1. **社会課題解決型研究開発プログラム**
   - JST RISTEX SOLVE for SDGs、未来社会創造事業
   - JST CREST / さきがけ（戦略的創造研究推進事業）
   - NEDO ムーンショット（特に目標8: 気象制御、目標10: 脱炭素）
   - 環境研究総合推進費（環境省）
   - 「共創」「社会実装」「地域課題解決」「産学連携」等の文言を含むプログラム

2. **サステナビリティ・ESG 系アワード/ピッチ**
   - SDGsアワード、サステナビリティアワード
   - Climate Tech Pitch、グリーンイノベーション大賞
   - ESG関連ビジネスコンテスト

3. **民間財団の環境・気候研究助成**
   - 住友財団、トヨタ財団、三菱財団、日産財団
   - 旭硝子財団（ブループラネット賞）
   - 大川情報通信基金、電気通信普及財団 等

4. **国際プログラム**
   - Horizon Europe（EU）climate calls
   - ERC / REA プログラム
   - XPRIZE、Earthshot Prize 等の global challenge

#### 判定原則

- **「ソリューションを問わない」** テーマで応募可能なら、気候・AI・衛星に貢献できるアプローチを提案する余地があるため **残す**
- 具体的テーマが指定されていない研究開発プログラム（JST CREST 等）は、
  ME-Lab の技術（SAR/InSAR/気候AI）が応用可能な研究領域で応募可能なら残す
- `config/search_config.json` の `known_broad_programs` リストの各プログラムについて、
  Routine 実行時に毎回公募状況を確認する

### 応募資格の判定ルール（企業の共同応募可能性）

「企業のみ」「株式会社のみ」等の明示的な企業除外条項がない限り、
企業応募の可能性を WebSearch で確認する。特に以下のパターンに注意:

#### 「大学等との連携必須」タイプ（企業は共同実施機関として参加可能）
- JST RISTEX（社会技術研究開発センター）
- JST A-STEP / CREST / さきがけ
- NEDO 先導研究プログラム
- AMED プログラム
- 文部科学省 戦略的創造研究推進事業

これらは「研究代表者または協働実施者の少なくとも一方が大学等」という条件が
多く、企業単独では応募不可だが、大学・公的研究機関との共同提案なら参加可能。

このケースに該当する助成金は **除外せず残す** が、
`notes` に **`[応募可能性] 大学等との共同提案必須`** を明記する。

#### 「企業対象」だが県内拠点が必要なタイプ
地方自治体の助成金で「県内事業所を有する者」が要件の場合、
補助事業期間中に県内拠点を設置する予定があれば応募可能なケースが多い。
WebSearchで確認し、可能なら残す（`notes` に条件を明記）。

#### 明確に除外すべきもの
- 「NPO法人のみ」「個人事業主のみ」「学生のみ」明示
- 「大学・研究機関のみ」（企業参加不可）明示
- 「特定業種のみ」（自社が該当しない業種）

## データフォーマット規定

### deadline の許容値（これ以外は禁止）
- `YYYY-MM-DD` 形式（例: `2026-05-20`）— 具体日
- `通年募集` — 明確に通年受付している場合のみ
- `要確認` — やむを得ない場合のみ、notes に状況を追記

**禁止例**: `"2026-02-24説明会実施"`, `"随時公募"`, `"継続募集"`, `"公募時期要確認"`, `"年1回公募（令和7年度は5月21日締切）"`, `"2026-02-17公募開始"`, `"2025-07-17開始（継続中）"`, `"TBD"`

曖昧な記述は以下のように正規化:
- 「〜年度は〜日締切」→ その日付を YYYY-MM-DD に変換
- 「随時」「継続」→ `通年募集` か除外かを判定
- 「説明会実施」「公募開始」「発表済」等の混入 → 具体日だけ抽出

### amount の必須要件（これ以外は除外）
必ず以下のいずれかを含むこと:
- 数値 + 金額単位: `万円`, `千円`, `円`, `$`, `USD`, `EUR`, `€`, `CHF` 等
- 助成率: `補助率2/3`, `50%`, `分の1` 等
- プロジェクト予算規模: `$500K-$3M`, `上限1億円`, `〜千万円規模` 等

**禁止例**: `"Variable"`, `"Fellowship program"`, `"Accelerator support"`, `"-"`, `"未明示"`, `"要確認"`, `"事業提携・投資機会"`, `"投資付きアクセラレーター（金額詳細要確認）"`

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
