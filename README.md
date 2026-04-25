# grant-bot-template

**助成金・補助金・アワード・ピッチを定期検索し、フィルタ済みの結果を GitHub Pages で共有 + Slack で通知する仕組みのテンプレート。**

Claude Code Desktop の Routine 機能を使ってクラウド実行されるため、PC のスリープ状態でも動作します。自分の事業領域に合わせた検索テーマを設定するだけで、毎週自動で関連助成金が更新されるダッシュボードが手に入ります。

> 📖 セットアップ手順は [**SETUP.md**](./SETUP.md) を参照してください（8ステップ、所要 30〜60分）。

> ⚠️ **重要 — 機密情報の取り扱い**
>
> このテンプレートを使って構築する **メインのリポジトリ（`<your-bot>`）は必ず Private** に設定してください。以下の機密情報を含みます:
> - `config/company_profile.json`: 会社名・事業領域・コア技術・過去採択実績・連携先
> - `memory/feedback_log.jsonl`: 社内フィードバックの内容
> - `memory/generalized_rules.json`: 学習済みの戦略的判断ルール
> - `memory/search_history.jsonl`: 検索戦略の履歴
>
> Pages 配信用のリポジトリ（`<your-bot>-pages`）は Public で構いません（公開助成金情報のみ）が、競合に検索戦略を推測されたくない場合は別途検討してください。

---

## 主な機能

- **5並列のインテリジェント検索** — ポータル、Web、省庁、地方自治体（東/西）を同時並行
- **7段階の品質ゲート** — 期限切れ・金額不明・重複等を機械的に除外し、要検証項目だけ LLM が WebSearch で補完
- **ユーザーフィードバックループ** — Pages の 🚩 ボタンから Slack へ報告 → 次回検索に自動反映
- **手動修正のサポート** — `overrides.json` で個別の助成金情報を上書き可能（チーム全体に反映）
- **個人用非表示** — Pages の 👁 ボタンでローカル（ブラウザ）のみ非表示
- **CSV エクスポート** — 表計算ソフトへの取り込みも可能
- **団体区分フィルタ** — 国・省庁／地方自治体／民間／海外で絞り込み

---

## システム構成

```
┌───────────────────────────────┐
│ Claude Code Routine (週次)    │
│ - 5並列検索                    │
│ - Python で機械的フィルタ      │
│ - LLM で要検証項目を再調査     │
└───────────────────────────────┘
              │ git push
              ↓
┌───────────────────────────────┐
│ <your-bot> (Private)          │
│ - コード・設定・メモリ         │
│ - 検索結果 (grants.json)      │
└───────────────────────────────┘
              │ GitHub Actions
              ↓
┌───────────────────────────────┐
│ <your-bot>-pages (Public)     │
│ - GitHub Pages                │
│ - https://<user>.github.io/   │
└───────────────────────────────┘
              │
              ↓
┌──────────┐    ┌──────────┐
│ ブラウザ  │←→│ Slack 通知 │
└──────────┘    └──────────┘
```

### 必要なもの

- GitHub アカウント（プライベートリポジトリが作れること）
- Claude Code Desktop（Slack 連携設定済み）
- Slack ワークスペース（通知用、任意）

### 構築手順の概要

| ステップ | 内容 |
|---------|------|
| 1 | 2リポジトリ作成（`<your-bot>` Private + `<your-bot>-pages` Public） |
| 2 | このテンプレートを clone |
| 3 | `config/company_profile.json` と `config/search_config.json` を編集 |
| 4 | Personal Access Token を発行し Repository Secret に登録、リポジトリ名のプレースホルダを置換 |
| 5 | 初期 push |
| 6 | GitHub Pages を有効化 |
| 7 | Claude Code Desktop で Routine 作成 |
| 8 | 動作確認 |

詳細は [SETUP.md](./SETUP.md) を参照。

---

## ファイル構成

```
grant-bot-template/
├── README.md                       # このファイル
├── SETUP.md                        # セットアップガイド (必読)
├── CLAUDE.md                       # Routine への指示書 (汎用)
├── .github/workflows/
│   └── deploy-pages.yml            # ★ Pages 同期 (リポジトリ名を編集)
├── config/
│   ├── search_config.json          # 検索テーマ・キーワード (デフォルト6テーマ)
│   └── company_profile.json        # ★ あなたの組織情報 (必須)
├── memory/
│   ├── generalized_rules.json      # 学習済み除外ルール
│   ├── keyword_registry.json       # キーワード効果統計
│   ├── feedback_log.jsonl          # Slack フィードバック履歴
│   └── search_history.jsonl        # 実行履歴
├── scripts/
│   ├── curate.py                   # キュレーション (機械的フィルタ)
│   └── postprocess.py              # 最終整形
└── docs/                           # GitHub Pages ソース
    ├── index.html                  # ★ リポジトリ名定数を編集
    └── data/
        ├── grants.json             # 助成金リスト (自動更新)
        ├── overrides.json          # 手動修正用
        └── archive/                # 過去結果
```

`★` マーク = 初期セットアップで編集が必要なファイル

---

## デフォルトの検索テーマ

`config/search_config.json` には以下の6テーマがプリセット済みです（自由に追加・削除可）:

1. 防災・減災
2. 衛星・地球観測データ解析
3. AI・データ解析
4. 脱炭素・カーボンクレジット
5. 社会課題解決・サステナビリティ
6. グローバルサウス・新興国社会課題

各テーマは日本語・英語の両方のキーワードを持ち、国内外の助成金を網羅的に探索します。

---

## 主な技術スタック

- **オーケストレーション**: Claude Code Desktop Routine（クラウド実行）
- **言語モデル**: Anthropic Claude Opus 4.6 拡張
- **検索**: Claude Code の WebSearch ツール（Agent 並列実行）
- **後処理**: Python 3（標準ライブラリのみ、追加依存なし）
- **配信**: GitHub Pages + GitHub Actions（無料）
- **通知**: Slack コネクタ（Claude Code Desktop 内蔵）
- **UI**: Vanilla JavaScript + CSS（フレームワーク非依存）

---

## カスタマイズ

### 新しい検索テーマを追加
`config/search_config.json` の `themes` 配列に追加するだけ。

### キュレーションの厳格度を調整
`scripts/curate.py` の `MONEY_PATTERNS` 等の正規表現を編集。

### Pages の表示をカスタマイズ
`docs/index.html` のフィルタ・列・色分け（CSS変数）を編集。

詳細は [SETUP.md](./SETUP.md) の「カスタマイズ Tips」を参照。

---

## トラブルシューティング

よくある問題は [SETUP.md](./SETUP.md) のトラブルシューティングセクションを参照:

- Pages が更新されない
- Routine がタイムアウトする
- grants.json が空のまま
- Slack 通知が来ない

---

## ライセンス

MIT ライセンス相当で自由に使用・改変可能です。改変版を公開する際は、元リポジトリ（[grant-bot-template](https://github.com/YoshimuraHiroto/grant-bot-template)）へのリンクを README に含めていただけると幸いです。

---

## クレジット

このテンプレートは [Claude Code](https://claude.com/claude-code) との協働で開発されました。
