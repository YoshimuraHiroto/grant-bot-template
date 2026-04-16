#!/usr/bin/env python3
"""後処理スクリプト: 期限切れ分離・ID正規化・フォーマット統一

grants.json を加工する。
- 期限切れ助成金を分離
- IDをGR-YYYYMMDD-NNN形式に正規化
- 日付・金額のフォーマット統一

Usage: python scripts/postprocess.py docs/data/grants.json
"""

import json
import re
import sys
from datetime import date, datetime
from pathlib import Path


def is_expired(deadline_str: str) -> bool:
    if not deadline_str or deadline_str in ("要確認", "未定", ""):
        return False
    try:
        deadline = datetime.strptime(deadline_str, "%Y-%m-%d").date()
        return deadline < date.today()
    except (ValueError, TypeError):
        return False


def normalize_date(date_str: str) -> str:
    if not date_str or date_str in ("要確認", "未定"):
        return date_str or "要確認"
    if re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        return date_str
    m = re.match(r"^(\d{4})/(\d{1,2})/(\d{1,2})$", date_str)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    m = re.match(r"令和(\d+)年(\d+)月(\d+)日", date_str)
    if m:
        year = 2018 + int(m.group(1))
        return f"{year}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    m = re.match(r"(\d{4})年(\d+)月(\d+)日", date_str)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    return date_str


def normalize_keywords(keywords) -> str:
    if isinstance(keywords, list):
        return ", ".join(str(k) for k in keywords)
    if isinstance(keywords, str):
        return keywords
    return ""


def main():
    if len(sys.argv) < 2:
        print("Usage: python postprocess.py <grants.json>")
        sys.exit(1)

    grants_path = Path(sys.argv[1])
    if not grants_path.exists():
        print(f"ERROR: {grants_path} が見つかりません")
        sys.exit(1)

    with open(grants_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    grants = data.get("grants", [])
    if not grants:
        print("助成金データがありません。")
        return

    active_grants = []
    expired_grants = []
    today_compact = date.today().strftime("%Y%m%d")

    for grant in grants:
        grant["deadline"] = normalize_date(grant.get("deadline", ""))
        grant["keywords"] = normalize_keywords(grant.get("keywords", ""))

        if is_expired(grant.get("deadline", "")):
            grant["expired_date"] = date.today().strftime("%Y-%m-%d")
            expired_grants.append(grant)
        else:
            active_grants.append(grant)

    # ID再採番
    for i, grant in enumerate(active_grants):
        grant["id"] = f"GR-{today_compact}-{i + 1:03d}"

    # grants.json を更新（activeのみ）
    data["grants"] = active_grants
    data["summary"] = data.get("summary", {})
    data["summary"]["total_grants"] = len(active_grants)
    data["summary"]["expired_count"] = len(expired_grants)

    with open(grants_path, "w", encoding="utf-8") as f:
        json.dump(data, ensure_ascii=False, indent=2, fp=f)

    print(f"後処理完了: 有効 {len(active_grants)}件, 期限切れ {len(expired_grants)}件")


if __name__ == "__main__":
    main()
