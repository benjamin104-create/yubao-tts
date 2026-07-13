#!/usr/bin/env python3
"""彙總 finance_ledger.csv 與 kpi_weekly.csv，輸出指定 ISO 週的週報數據段落。

用法：
    python weekly_report.py 2026-W29
"""
import csv
import sys
from datetime import date, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def iso_week_range(week_str: str):
    year, week = week_str.split("-W")
    monday = date.fromisocalendar(int(year), int(week), 1)
    return monday, monday + timedelta(days=6)


def load_ledger():
    path = DATA_DIR / "finance_ledger.csv"
    with open(path, newline="", encoding="utf-8") as f:
        return [row for row in csv.DictReader(f)]


def summarize_week(rows, start, end):
    income, expense = 0.0, 0.0
    by_line = {}
    for row in rows:
        try:
            d = date.fromisoformat(row["date"])
            amt = float(row["amount_twd"] or 0)
        except ValueError:
            continue
        if not (start <= d <= end):
            continue
        if row["type"] == "income":
            income += amt
        elif row["type"] == "expense":
            expense += amt
        line = row.get("revenue_line") or "unassigned"
        sign = amt if row["type"] == "income" else -amt
        by_line[line] = by_line.get(line, 0.0) + sign
    return income, expense, by_line


def load_kpi(week_str: str):
    path = DATA_DIR / "kpi_weekly.csv"
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    current = next((r for r in rows if r["week"] == week_str), None)
    idx = rows.index(current) if current else -1
    previous = rows[idx - 1] if idx > 0 else None
    return current, previous


def main():
    if len(sys.argv) != 2 or "-W" not in sys.argv[1]:
        sys.exit("用法：weekly_report.py {YYYY}-W{WW}，例如 2026-W29")
    week_str = sys.argv[1]
    start, end = iso_week_range(week_str)

    rows = load_ledger()
    income, expense, by_line = summarize_week(rows, start, end)
    total_in = sum(float(r["amount_twd"] or 0) for r in rows if r["type"] == "income")
    total_out = sum(float(r["amount_twd"] or 0) for r in rows if r["type"] == "expense")

    print(f"## 週報數據段落 — {week_str}（{start} → {end}）\n")
    print("### 錢\n")
    print("| 項目 | 本週 | 帳上累計 |")
    print("|------|------|----------|")
    print(f"| 收入 | {income:,.0f} | {total_in:,.0f} |")
    print(f"| 支出 | {expense:,.0f} | {total_out:,.0f} |")
    print(f"| 淨額 | {income - expense:,.0f} | {total_in - total_out:,.0f} |\n")
    if by_line:
        print("各收入線本週淨額：" + "、".join(f"{k}: {v:+,.0f}" for k, v in sorted(by_line.items())) + "\n")

    current, previous = load_kpi(week_str)
    print("### 受眾與名單\n")
    if not current:
        print(f"（kpi_weekly.csv 尚無 {week_str} 的快照，請先補記。）")
        return
    fields = [
        ("list_size", "自有名單（North Star）"),
        ("yt_subs", "YouTube 訂閱"),
        ("yt_watch_hours", "YouTube 觀看時數"),
        ("tiktok_followers", "TikTok 粉絲"),
        ("ig_followers", "IG 粉絲"),
        ("posts_published", "本週發佈則數"),
    ]
    print("| 指標 | 上週 | 本週 | Δ |")
    print("|------|------|------|---|")
    for key, label in fields:
        cur = current.get(key, "")
        prev = previous.get(key, "") if previous else "—"
        try:
            delta = f"{int(cur) - int(prev):+d}"
        except (ValueError, TypeError):
            delta = "—"
        print(f"| {label} | {prev} | {cur} | {delta} |")
    try:
        pct = int(current["yt_subs"]) / 500 * 100
        print(f"\n距離 YouTube 粉絲贊助門檻（500 訂閱）：{pct:.0f}%")
    except (ValueError, KeyError):
        pass
    if current.get("note"):
        print(f"\n大事記：{current['note']}")


if __name__ == "__main__":
    main()
