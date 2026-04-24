#!/usr/bin/env python3
"""助成金キュレーションスクリプト（ルールベース事前処理）

LLM 負荷を下げるため、機械的判定できる部分をスクリプトで処理し、
誤除外の疑いがある項目は NEEDS_VERIFY として分離する。

Usage:
  python scripts/curate.py <input.json> [options]

処理結果:
  CONFIRMED_KEEP   — 全ゲート通過、情報充分 → grants_partial.json に出力
  CONFIRMED_REMOVE — 確実に除外（期限切れ/明白な重複）→ 削除ログのみ
  NEEDS_VERIFY     — 正規化失敗や情報不足だが回復可能性あり
                     → LLM が WebSearch で検証すべき項目として curation_report.json に記録

LLM 側のワークフロー:
  1. curate.py を実行 → grants_partial.json + curation_report.json
  2. curation_report.json の needs_verify を LLM が WebSearch で検証
  3. 検証で情報補完できた項目を grants_partial.json に追記
  4. postprocess.py で最終整形 → grants.json

Usage:
  python scripts/curate.py <input.json> \
    [--output-partial docs/data/grants_partial.json] \
    [--report docs/data/curation_report.json] \
    [--overrides docs/data/overrides.json] \
    [--today YYYY-MM-DD]
"""

import argparse
import json
import re
import sys
import unicodedata
from datetime import date, datetime, timedelta
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import urlparse, urlunparse


# ── 定数 ──

# 完全に「情報なし」を表す値（確実に情報欠落）
CLEARLY_EMPTY = {"", "-", "N/A", "null", "None", "tbd", "TBD", "T.B.D."}

# 曖昧だが「検証すれば情報が得られる可能性がある」値
VERIFIABLE_UNCLEAR = {
    "要確認", "不明", "未定", "未公表", "未記載", "未明示",
    "Variable", "Variable by phase", "Not specified", "変動",
    "詳細要確認", "詳細未記載", "要問い合わせ", "金額未公開",
    "Fellowship program", "Accelerator support",
    "事業提携・投資機会",
}

# 日本語の曖昧金額表現（実際は金額情報だが、具体額はWebSearchで確認必要）
VAGUE_MONEY_HINTS = [
    "数百万", "数千万", "数億", "数十億", "億円規模", "兆円規模",
    "事業規模による", "大規模", "委託費", "委託費・補助金",
    "詳細は公募要領", "実証費用支援", "表彰・活動支援", "賞金・支援",
    "チャレンジ型", "コンテスト型", "表彰型",
]

# 金額単位パターン（具体額あり）
MONEY_PATTERNS = [
    # 日本語単位: 500万円 / 3,000万円 / 500万 / 1億
    re.compile(r"\d[\d,.]*\s*(万円|千円|円|百万|億|兆)"),
    re.compile(r"\d[\d,.]*\s*(万|億|兆|百万)(円|ドル|USD)?"),
    re.compile(r"数(十|百|千)?(万|億|兆)円?"),
    # 通貨記号 + 数値: $500K / €75,000 / S$1M
    re.compile(r"[\$€¥£]\s*\d[\d,.]*\s*[KMBkmb]?"),
    re.compile(r"(S|NT|HK)\$\s*\d[\d,.]*\s*[KMBkmb]?"),
    # 通貨コード+数値（両方向）: CHF 39,000 / 500 USD
    re.compile(r"(USD|EUR|CHF|GBP|SGD|JPY|CNY|KRW)\s*\d[\d,.]*\s*[KMBkmb]?", re.IGNORECASE),
    re.compile(r"\d[\d,.]*\s*(USD|EUR|CHF|GBP|SGD|JPY|CNY|KRW)", re.IGNORECASE),
    # 補助率・助成率・限度額系
    re.compile(r"補助率|助成率|助成限度額|交付限度額|補助限度額|助成額"),
    re.compile(r"(上限|最大|限度額|助成額|補助額|予算)\s*\d"),
    re.compile(r"\d+\s*%|\d+/\d+|分の\d+"),
    # 単独「N億」「N兆」「N百万」
    re.compile(r"\d+\s*億|\d+\s*兆|\d+\s*百万"),
]

ACCEL_MONEY_KEYWORDS = [
    "equity", "イクイティ", "賞金", "助成金", "補助金", "委託費",
    "万円", "千円", "億", "$", "usd", "eur", "€", "chf", "investment",
    "投資"
]

OVERSEAS_KW = [
    "NASA", "ESA", "ECMWF", "European", "IEEE", "ITU", "NSF", "NIST", "MIT",
    "UC Berkeley", "Techstars", "Google", "Amazon", "Bezos", "Hatch Blue", "WWF",
    "Climate Change AI", "Climate Solutions", "Conservation International",
    "The Nature Conservancy", "I-GUIDE", "JPI Oceans", "Plug and Play",
    "Horizon Europe", "UNDP", "UNESCO", "World Bank"
]
NATIONAL_KW = [
    "環境省", "経済産業省", "国土交通省", "総務省", "文部科学省", "農林水産省",
    "防衛省", "防衛装備庁", "復興庁", "デジタル庁", "水産庁", "中小企業庁",
    "内閣府", "JAXA", "NEDO", "JST", "AMED", "科学技術振興機構",
    "新エネルギー・産業技術総合開発機構", "宇宙航空研究開発機構",
    "国立研究開発法人", "中小企業基盤整備機構", "中小機構", "SMRJ", "SBIR",
    "経済産業局", "SPACETIDE",
]
PREFS = [
    "北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県",
    "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
    "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県",
    "静岡県", "愛知県", "三重県", "滋賀県", "京都府", "大阪府", "兵庫県",
    "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県", "広島県", "山口県",
    "徳島県", "香川県", "愛媛県", "高知県", "福岡県", "佐賀県", "長崎県",
    "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県",
]
LOCAL_KW = [
    "振興公社", "産業創出支援機構", "産業振興機構", "しごと財団", "環境公社",
    "産業局", "産業労働局", "環境局", "NICO", "ISICO", "産業支援センター",
    "大阪産業局", "イノベーションハブ", "STARTUP HOKKAIDO",
    "Growth Next", "ICC", "NAGOYA",
]
PRIVATE_KW = [
    "株式会社", "一般社団法人", "公益財団法人", "一般財団法人",
    "NPO法人", "技術研究組合", "民間コンソーシアム",
]


# ── ヘルパー ──

def normalize_name(name):
    if not name:
        return ""
    s = unicodedata.normalize("NFKC", str(name))
    return re.sub(r"\s+", "", s).lower()


def normalize_url(url):
    if not url:
        return ""
    try:
        p = urlparse(str(url).strip())
        netloc = p.netloc.lower().removeprefix("www.")
        path = p.path.rstrip("/")
        return urlunparse(("https", netloc, path, "", "", ""))
    except Exception:
        return str(url).strip().lower()


def parse_deadline(s, today):
    """deadline を正規化。戻り値 (normalized_str, status, note)
    status: 'future_date' / 'expired' / 'ongoing' / 'unclear' / 'parse_failed'
    """
    if not s:
        return ("要確認", "unclear", "空")
    s = str(s).strip()

    if s in CLEARLY_EMPTY:
        return ("要確認", "unclear", "空/ダッシュ")
    if s in VERIFIABLE_UNCLEAR:
        return ("要確認", "unclear", f"曖昧表現: {s}")
    if s == "通年募集":
        return ("通年募集", "ongoing", None)

    # YYYY-MM-DD exact
    m = re.match(r"^(\d{4}-\d{2}-\d{2})$", s)
    if m:
        try:
            d = datetime.strptime(m.group(1), "%Y-%m-%d").date()
            return (m.group(1), "expired" if d < today else "future_date", None)
        except Exception:
            pass

    # YYYY-MM-DD with suffix
    m = re.match(r"^(\d{4}-\d{2}-\d{2})", s)
    if m:
        try:
            d = datetime.strptime(m.group(1), "%Y-%m-%d").date()
            suffix = s[10:]
            status = "expired" if d < today else "future_date"
            note = f"後ろに付加文字列: '{suffix}'"
            # 「開始」「発表」系は締切ではない可能性
            if any(x in suffix for x in ["開始", "公募開始", "説明会", "発表", "開催"]):
                return ("要確認", "parse_failed", f"開始日の可能性: {s}")
            return (m.group(1), status, note)
        except Exception:
            pass

    # 随時/継続/通年
    if any(x in s for x in ["随時", "継続", "通年"]):
        return ("通年募集", "ongoing", f"正規化: {s} -> 通年募集")

    # 令和
    m = re.search(r"令和(\d+)年(\d+)月(\d+)日", s)
    if m:
        year = 2018 + int(m.group(1))
        ds = f"{year}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        try:
            d = datetime.strptime(ds, "%Y-%m-%d").date()
            return (ds, "expired" if d < today else "future_date", f"正規化: {s}")
        except Exception:
            pass

    # YYYY年MM月DD日
    m = re.search(r"(\d{4})年(\d+)月(\d+)日", s)
    if m:
        ds = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        try:
            d = datetime.strptime(ds, "%Y-%m-%d").date()
            return (ds, "expired" if d < today else "future_date", f"正規化: {s}")
        except Exception:
            pass

    # YYYY/MM/DD
    m = re.match(r"^(\d{4})/(\d{1,2})/(\d{1,2})$", s)
    if m:
        ds = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        try:
            d = datetime.strptime(ds, "%Y-%m-%d").date()
            return (ds, "expired" if d < today else "future_date", f"正規化: {s}")
        except Exception:
            pass

    # YYYY-MM-上旬/中旬/下旬 → 月の 5/15/25 日に近似
    m = re.match(r"^(\d{4})-(\d{1,2})-(上旬|中旬|下旬)", s)
    if m:
        year, month, ten = int(m.group(1)), int(m.group(2)), m.group(3)
        day = {"上旬": 5, "中旬": 15, "下旬": 25}[ten]
        try:
            d = date(year, month, day)
            return (d.isoformat(), "expired" if d < today else "future_date",
                    f"近似正規化: {s} -> {d.isoformat()}")
        except Exception:
            pass

    # YYYY年MM月上旬/中旬/下旬
    m = re.match(r"(\d{4})年\s*(\d{1,2})月\s*(上旬|中旬|下旬)", s)
    if m:
        year, month, ten = int(m.group(1)), int(m.group(2)), m.group(3)
        day = {"上旬": 5, "中旬": 15, "下旬": 25}[ten]
        try:
            d = date(year, month, day)
            return (d.isoformat(), "expired" if d < today else "future_date",
                    f"近似正規化: {s} -> {d.isoformat()}")
        except Exception:
            pass

    return ("要確認", "parse_failed", f"パース不能: {s}")


def analyze_money(amount, notes="", elig="", opp_type=""):
    """金額情報の分析。戻り値 (has_concrete, status, note)
    status: 'concrete' / 'vague_verifiable' / 'empty' / 'verifiable_unclear'
    """
    amt = str(amount or "").strip()
    full_text = f"{amt} {notes or ''} {elig or ''}"

    # 具体額パターン
    for p in MONEY_PATTERNS:
        if p.search(full_text):
            return (True, "concrete", None)

    if amt in CLEARLY_EMPTY:
        return (False, "empty", "金額記載なし")

    if amt in VERIFIABLE_UNCLEAR:
        return (False, "verifiable_unclear", f"曖昧値: {amt}（公募要領で確認可）")

    # 曖昧な金額表現（WebSearchで具体額確認できる可能性が高い）
    if any(h in full_text for h in VAGUE_MONEY_HINTS):
        return (False, "vague_verifiable", "曖昧な金額表現。公募要領で具体額確認必要")

    # accelerator 用緩和判定
    if opp_type == "accelerator":
        lower = full_text.lower()
        if any(kw.lower() in lower for kw in ACCEL_MONEY_KEYWORDS):
            return (True, "concrete", "投資/賞金系キーワード")
        return (False, "verifiable_unclear", "アクセラレーターで金銭支援不明瞭")

    # 表彰金/報奨金
    if any(kw in full_text for kw in ["表彰金", "報奨金", "優勝賞金"]):
        return (True, "concrete", "表彰金系")

    return (False, "verifiable_unclear", f"金額単位未検出: {amt[:30]}")


def count_unclear_fields(g):
    """空または曖昧なフィールド数を数える"""
    count = 0
    for f in ["amount", "duration", "deadline", "eligibility_summary"]:
        v = str(g.get(f, "") or "").strip()
        if not v or v in CLEARLY_EMPTY or v in VERIFIABLE_UNCLEAR:
            count += 1
    return count


def normalize_keywords(kw):
    if isinstance(kw, list):
        return ", ".join(str(k) for k in kw)
    return str(kw) if kw else ""


def is_mostly_ascii(s):
    if not s or len(s) < 4:
        return False
    return sum(1 for c in s if ord(c) < 128) / len(s) > 0.85


def classify_org(org):
    if not org:
        return ""
    s = str(org).strip()
    for kw in OVERSEAS_KW:
        if kw.lower() in s.lower():
            return "海外"
    if is_mostly_ascii(s) and not any(j in s for j in ["県", "市", "省", "庁", "府", "都"]):
        return "海外"
    for kw in NATIONAL_KW:
        if kw in s:
            return "国・省庁"
    for p in PREFS:
        if p in s:
            return "地方自治体"
    if re.search(r"[^\s]{1,5}[市区町村](?![場])", s):
        return "地方自治体"
    for kw in LOCAL_KW:
        if kw in s:
            return "地方自治体"
    for kw in PRIVATE_KW:
        if kw in s:
            return "民間"
    return ""


# ── 分類ロジック ──

def classify_grant(g, today):
    """助成金を CONFIRMED_KEEP / CONFIRMED_REMOVE / NEEDS_VERIFY のいずれかに分類。

    戻り値: (category, updated_grant, reason_dict)
    reason_dict: 分類理由と LLM への verify_hint を含む
    """
    issues = []       # 検出された問題のリスト
    verify_hints = [] # LLM が検証するためのヒント

    # === deadline ===
    dl_orig = g.get("deadline", "")
    dl_new, dl_status, dl_note = parse_deadline(dl_orig, today)
    g["deadline"] = dl_new

    if dl_status == "expired":
        # 期限切れは確実に除外
        return ("CONFIRMED_REMOVE", g, {
            "primary_reason": "expired",
            "detail": f"期限切れ: {dl_new}",
            "deadline_original": dl_orig,
        })

    if dl_status == "parse_failed":
        issues.append(f"deadline_parse_failed: '{dl_orig}' → {dl_note}")
        verify_hints.append(f"締切日を確認。元の表現: '{dl_orig}'")

    # === amount ===
    amt_orig = g.get("amount", "")
    has_money, money_status, money_note = analyze_money(
        amt_orig, g.get("notes", ""), g.get("eligibility_summary", ""),
        g.get("opportunity_type", "")
    )

    if not has_money:
        if money_status == "empty":
            # 完全空は除外寄り（ただし verify 可能性あり）
            issues.append(f"amount_empty: '{amt_orig}'")
            verify_hints.append("金額情報が空。公募要領/公式ページで金額を確認")
        elif money_status == "vague_verifiable":
            # 曖昧表現は WebSearch で具体額を引き出す価値あり
            issues.append(f"amount_vague: '{amt_orig}' ({money_note})")
            verify_hints.append(f"曖昧な金額表現「{amt_orig}」。公募要領で具体額（万円/%等）を確認")
        elif money_status == "verifiable_unclear":
            issues.append(f"amount_verifiable: '{amt_orig}' ({money_note})")
            verify_hints.append(f"金額「{amt_orig}」。公募要領で具体額を確認")

    # === 情報充足度 ===
    unclear_count = count_unclear_fields(g)
    if unclear_count >= 3:
        issues.append(f"low_info: {unclear_count}/4 フィールドが曖昧")
        verify_hints.append(
            f"金額/期間/締切/応募資格のうち{unclear_count}個が曖昧。公募要領PDFで補完"
        )

    elig = str(g.get("eligibility_summary", "") or "").strip()
    if 0 < len(elig) < 10 and elig not in VERIFIABLE_UNCLEAR and elig not in CLEARLY_EMPTY:
        issues.append(f"short_eligibility: '{elig}' ({len(elig)}文字)")
        verify_hints.append(f"応募資格が短すぎ: '{elig}'。詳細を確認")

    # === 正規化 ===
    g["keywords"] = normalize_keywords(g.get("keywords", ""))
    if not g.get("organization_category"):
        cat = classify_org(g.get("organization", ""))
        if cat:
            g["organization_category"] = cat

    # === 分類判定 ===
    if not issues:
        return ("CONFIRMED_KEEP", g, {"primary_reason": "all_gates_passed"})

    # 問題ありだが回復可能 → NEEDS_VERIFY
    return ("NEEDS_VERIFY", g, {
        "primary_reason": issues[0].split(":")[0] if ":" in issues[0] else issues[0],
        "issues": issues,
        "verify_hints": verify_hints,
        "url": g.get("url", ""),
        "deadline_original": dl_orig if dl_orig != dl_new else None,
        "amount_original": amt_orig,
    })


def dedup_grants(grants):
    """URL正規化 + 名前+団体類似度で重複除去。
    戻り値: (unique_list, removed_list)
    """
    seen_urls = {}
    seen_name_org = []
    unique = []
    removed = []

    for g in grants:
        gid = g.get("id", "")
        url_key = normalize_url(g.get("url", ""))
        name_key = normalize_name(g.get("name", ""))
        org_key = normalize_name(g.get("organization", ""))

        if url_key and url_key in seen_urls:
            removed.append({
                "id": gid, "name": g.get("name", ""),
                "primary_reason": "duplicate_url",
                "detail": f"URL一致: {seen_urls[url_key]}",
                "duplicate_of": seen_urls[url_key],
            })
            continue

        is_dup = False
        for (ex_name, ex_org, ex_id) in seen_name_org:
            name_sim = SequenceMatcher(None, name_key, ex_name).ratio()
            org_sim = SequenceMatcher(None, org_key, ex_org).ratio() if ex_org else 0
            if name_sim >= 0.85 and (not ex_org or org_sim >= 0.5):
                removed.append({
                    "id": gid, "name": g.get("name", ""),
                    "primary_reason": "duplicate_similar",
                    "detail": f"類似: name_sim={name_sim:.2f}, org_sim={org_sim:.2f}",
                    "duplicate_of": ex_id,
                })
                is_dup = True
                break
        if is_dup:
            continue

        if url_key:
            seen_urls[url_key] = gid
        seen_name_org.append((name_key, org_key, gid))
        unique.append(g)

    return unique, removed


# ── メイン ──

def run(input_path, output_partial, report_path, overrides_path, today):
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    grants = data.get("grants", [])
    if not grants:
        print("ERROR: 入力に grants がありません")
        sys.exit(1)

    confirmed_keep = []
    confirmed_remove = []
    needs_verify = []

    # 個別判定
    for g in grants:
        category, updated_g, reason = classify_grant(g, today)
        if category == "CONFIRMED_KEEP":
            confirmed_keep.append(updated_g)
        elif category == "CONFIRMED_REMOVE":
            confirmed_remove.append({
                "id": updated_g.get("id", ""),
                "name": updated_g.get("name", ""),
                "url": updated_g.get("url", ""),
                **reason,
            })
        else:  # NEEDS_VERIFY
            needs_verify.append({
                "grant": updated_g,
                "reason": reason,
            })

    # confirmed_keep に対して重複除去
    deduped_keep, dup_removed = dedup_grants(confirmed_keep)
    confirmed_remove.extend(dup_removed)

    # 締切3日以内警告
    three_days = today + timedelta(days=3)
    near_warned = 0
    for g in deduped_keep:
        dl = g.get("deadline", "")
        if re.match(r"^\d{4}-\d{2}-\d{2}$", dl):
            try:
                d = datetime.strptime(dl, "%Y-%m-%d").date()
                if today <= d <= three_days:
                    existing = g.get("notes", "")
                    if not existing.startswith("⚠️"):
                        g["notes"] = f"⚠️ 締切3日以内: {existing}".strip()
                        near_warned += 1
            except Exception:
                pass

    # カテゴリ集計
    cats = {}
    for g in deduped_keep:
        c = g.get("organization_category", "不明")
        cats[c] = cats.get(c, 0) + 1

    # ── 出力1: 確定キープリスト（部分 grants.json） ──
    partial_data = {
        "date": today.strftime("%Y-%m-%d"),
        "stage": "partial_after_curate_script",
        "summary": {
            "input_count": len(grants),
            "confirmed_keep": len(deduped_keep),
            "confirmed_remove": len(confirmed_remove),
            "needs_verify": len(needs_verify),
            "by_category": cats,
            "near_deadline_warnings": near_warned,
        },
        "grants": deduped_keep,
    }
    Path(output_partial).parent.mkdir(parents=True, exist_ok=True)
    with open(output_partial, "w", encoding="utf-8") as f:
        json.dump(partial_data, ensure_ascii=False, indent=2, fp=f)

    # ── 出力2: キュレーションレポート ──
    report = {
        "date": today.strftime("%Y-%m-%d"),
        "summary": {
            "input_count": len(grants),
            "confirmed_keep": len(deduped_keep),
            "confirmed_remove": len(confirmed_remove),
            "needs_verify": len(needs_verify),
        },
        "confirmed_remove": confirmed_remove,
        "needs_verify": needs_verify,
        "instructions_for_llm": [
            "needs_verify 内の各項目について、grant.url や公募要領 PDF を WebSearch/WebFetch で確認。",
            "verify_hints を参考に、amount / deadline / eligibility_summary を補完。",
            "補完できた項目は grants_partial.json の grants 配列に追加（IDは一時的なもの、後で再採番）。",
            "補完しても基準を満たさない項目は confirmed_remove に移動。",
            "全件処理後、scripts/postprocess.py で最終整形（ID再採番 + 期限切れ最終チェック）。",
        ],
    }
    Path(report_path).parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, ensure_ascii=False, indent=2, fp=f)

    # ── コンソール出力 ──
    print(f"=== curate.py 完了 ===")
    print(f"入力: {len(grants)}件")
    print(f"  CONFIRMED_KEEP:   {len(deduped_keep)}件（partial_grants.json）")
    print(f"  CONFIRMED_REMOVE: {len(confirmed_remove)}件（確実除外）")
    print(f"  NEEDS_VERIFY:     {len(needs_verify)}件（LLMで再調査）")
    print(f"カテゴリ: {cats}")
    print(f"締切3日以内警告: {near_warned}件")
    print(f"\n出力:")
    print(f"  {output_partial}")
    print(f"  {report_path}")
    print(f"\n次のステップ（LLM側）:")
    print(f"  1. curation_report.json の needs_verify を読む")
    print(f"  2. 各項目について WebSearch/WebFetch で情報補完")
    print(f"  3. 基準を満たしたら grants_partial.json に追記")
    print(f"  4. postprocess.py で最終整形")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="検索エージェントの統合 JSON")
    ap.add_argument("--output-partial", default="docs/data/grants_partial.json")
    ap.add_argument("--report", default="docs/data/curation_report.json")
    ap.add_argument("--overrides", default="docs/data/overrides.json")
    ap.add_argument("--today", default=None,
                    help="基準日 YYYY-MM-DD（省略時は実行日）")
    args = ap.parse_args()

    today = (datetime.strptime(args.today, "%Y-%m-%d").date()
             if args.today else date.today())

    run(args.input, args.output_partial, args.report, args.overrides, today)


if __name__ == "__main__":
    main()
