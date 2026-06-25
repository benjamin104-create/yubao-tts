"""
Instagram Reels 數據審計引擎  —  透過 Windsor.ai 串接 IG Insights
=====================================================================
這支程式做三件事：
  1) 串接：用 Windsor.ai 的 Connector API 把你 Instagram 帳號的貼文/Reels
     數據拉下來（最近 N 天）。
  2) 整理：把每日列、別名欄位、累計指標 normalize 成「每支 Reel 一列」。
  3) 審計：用「觀看量 / 互動率 / 分享數」算綜合分，排出前 N 名，
     並把整份資料輸出成 JSON + CSV + Markdown 報告，讓 AI 夥伴（我）
     之後能直接讀檔做毒舌診斷。

為什麼要這支程式？
  Windsor.ai 後台「授權」≠「聊天視窗看得到數字」。中間需要一把 API key
  和一次 HTTP 請求。這支就是那座橋。跑完你會得到 audit_output/ 底下的檔，
  把它（或匯出的 Google Sheet）丟給我，我就停止講道理、開始動刀。

用法：
  export WINDSOR_API_KEY="你的_windsor_api_key"
  python windsor_audit.py                 # 拉最近 30 天，輸出報告
  python windsor_audit.py --days 60       # 改天數
  python windsor_audit.py --top 5         # 改排行榜名次
  python windsor_audit.py --self-test     # 不需金鑰，用假資料驗證程式跑得動
  python windsor_audit.py --raw-only      # 只拉原始資料、不算審計（除錯用）

環境變數：
  WINDSOR_API_KEY     必填。Windsor.ai 後台 → onboarding/Account 取得。
  WINDSOR_CONNECTOR   來源連接器，預設 "instagram"。
                      （Windsor 的 IG 連接器在 API 路徑上就叫 instagram）
  WINDSOR_FIELDS      可選。覆寫要抓的欄位（逗號分隔）。不填用內建預設。
  WINDSOR_BASE        可選。預設 https://connectors.windsor.ai
"""
import argparse
import csv
import json
import os
import sys
from datetime import date, datetime, timedelta

try:
    import httpx
except ImportError:  # 與專案一致用 httpx；沒裝就退回標準庫
    httpx = None
    import urllib.parse
    import urllib.request


# ─────────────────────────────────────────────────────────────────────────
# 設定
# ─────────────────────────────────────────────────────────────────────────
WINDSOR_BASE = os.environ.get("WINDSOR_BASE", "https://connectors.windsor.ai").rstrip("/")
WINDSOR_CONNECTOR = os.environ.get("WINDSOR_CONNECTOR", "instagram")
WINDSOR_API_KEY = os.environ.get("WINDSOR_API_KEY", "").strip()

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "audit_output")

# 向 Windsor 要的欄位。不同帳號/連接器命名會有差異，所以這裡要「寬」，
# 後面再用別名表把它收斂。多要欄位不會報錯，少要才會漏資料。
DEFAULT_FIELDS = [
    "date", "user_name", "account_id", "timestamp",
    "media_id", "media_caption", "media_permalink", "media_url",
    "media_type", "media_product_type",
    "media_reel_video_views", "media_views", "media_plays",
    "media_impressions", "media_reach",
    "media_like_count", "media_comments_count",
    "media_shares", "media_saved",
    "media_reel_total_interactions", "media_total_interactions",
    "media_reel_avg_watch_time",
]

# 別名表：把 Windsor 可能回的各種欄名，對應到我們內部統一的鍵。
# 取值時會「依序」嘗試這些候選，命中第一個有數字的就用。
FIELD_ALIASES = {
    "post_id":       ["media_id", "post_id", "id"],
    "caption":       ["media_caption", "post_caption", "caption", "title", "message"],
    "permalink":     ["media_permalink", "media_url", "post_permalink", "permalink", "link"],
    "created_time":  ["timestamp", "media_timestamp", "post_created_time", "created_time", "date"],
    "media_type":    ["media_type", "post_media_type"],
    "product_type":  ["media_product_type", "post_media_product_type", "product_type"],
    "views":         ["media_reel_video_views", "media_views", "media_plays",
                      "video_views", "reels_plays", "plays", "views", "media_impressions", "impressions"],
    "reach":         ["media_reach", "reach"],
    "impressions":   ["media_impressions", "impressions"],
    "likes":         ["media_like_count", "likes", "like_count"],
    "comments":      ["media_comments_count", "comments", "comments_count", "comment_count"],
    "shares":        ["media_shares", "shares", "share_count"],
    "saves":         ["media_saved", "saved", "saves", "save_count"],
    "interactions":  ["media_reel_total_interactions", "media_total_interactions",
                      "total_interactions", "engagement", "post_engagements"],
    "avg_watch_time":["media_reel_avg_watch_time", "ig_reels_avg_watch_time", "avg_watch_time"],
    "total_watch_time":["ig_reels_video_view_total_time", "video_view_total_time"],
    "follows":       ["follows", "follower_count", "new_followers"],
}

# 綜合分權重（呼應你的需求：觀看量 / 互動率 / 分享數）
WEIGHTS = {"views": 0.40, "engagement_rate": 0.35, "shares": 0.25}


# ─────────────────────────────────────────────────────────────────────────
# 小工具
# ─────────────────────────────────────────────────────────────────────────
def _to_float(v):
    """把各種髒值（None / "" / "1,234" / "12.0"）安全轉成 float。"""
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(",", "")
    if s == "" or s.lower() in ("none", "null", "nan"):
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def _pick(row, key):
    """依別名表從一列資料取值；數字類回 float，文字類回字串。"""
    for cand in FIELD_ALIASES.get(key, [key]):
        if cand in row and row[cand] not in (None, ""):
            return row[cand]
    return None


def _pick_num(row, key):
    return _to_float(_pick(row, key))


# ─────────────────────────────────────────────────────────────────────────
# 1) 串接：呼叫 Windsor.ai
# ─────────────────────────────────────────────────────────────────────────
def fetch_windsor(api_key, days, connector=WINDSOR_CONNECTOR, fields=None):
    """向 Windsor.ai Connector API 拉資料，回傳 list[dict]（原始列）。"""
    if not api_key:
        raise SystemExit(
            "✗ 沒有 WINDSOR_API_KEY。\n"
            "  到 Windsor.ai 後台拿 API key，然後：\n"
            "    export WINDSOR_API_KEY=\"你的金鑰\"\n"
            "  或先跑 `python windsor_audit.py --self-test` 驗證程式能動。"
        )
    fields = fields or DEFAULT_FIELDS
    date_to = date.today()
    date_from = date_to - timedelta(days=days)
    params = {
        "api_key": api_key,
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "fields": ",".join(fields),
        "_renderer": "json",
    }
    url = f"{WINDSOR_BASE}/{connector}"
    print(f"→ 向 Windsor.ai 拉資料：{connector}  {date_from} ~ {date_to}")

    data = _http_get_json(url, params)
    rows = data.get("data", data if isinstance(data, list) else [])
    if not isinstance(rows, list):
        raise SystemExit(f"✗ Windsor 回傳格式非預期：{str(data)[:300]}")
    print(f"✓ 取得 {len(rows)} 列原始資料")
    return rows


def _http_get_json(url, params):
    """用 httpx（專案既有相依）打 GET；沒裝就退回 urllib。"""
    if httpx is not None:
        r = httpx.get(url, params=params, timeout=60.0)
        if r.status_code != 200:
            raise SystemExit(f"✗ Windsor HTTP {r.status_code}：{r.text[:300]}")
        return r.json()
    # 退路：標準庫
    qs = urllib.parse.urlencode(params)
    req = urllib.request.Request(f"{url}?{qs}", headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310
        return json.loads(resp.read().decode("utf-8"))


# ─────────────────────────────────────────────────────────────────────────
# 2) 整理：每日列 → 每支 Reel 一列
# ─────────────────────────────────────────────────────────────────────────
def is_reel(row):
    """判斷一列是否為 Reels。命名不一，盡量寬鬆。"""
    pt = str(_pick(row, "product_type") or "").upper()
    mt = str(_pick(row, "media_type") or "").upper()
    if "REEL" in pt:
        return True
    if pt in ("", "FEED") and mt in ("VIDEO", "REELS"):
        return True
    # 沒有任何型別欄位時，有 reels_plays / video_views 也當作影片
    if pt == "" and mt == "" and _pick_num(row, "views") > 0:
        return True
    return False


def consolidate(rows):
    """
    把同一支貼文的多個每日列，合併成一列。
    IG Insights 多數指標是「累計值」，所以同一 post_id 取各指標的 max 最安全。
    """
    by_post = {}
    for row in rows:
        if not is_reel(row):
            continue
        pid = _pick(row, "post_id") or _pick(row, "permalink") or _pick(row, "caption")
        if pid is None:
            continue
        pid = str(pid)
        cur = by_post.setdefault(pid, {
            "post_id": pid,
            "caption": (_pick(row, "caption") or "")[:280],
            "permalink": _pick(row, "permalink") or "",
            "created_time": _pick(row, "created_time") or "",
            "account": _pick(row, "account_name") or _pick(row, "account") or "",
        })
        for key in ("views", "reach", "impressions", "likes", "comments",
                    "shares", "saves", "interactions", "avg_watch_time",
                    "total_watch_time", "follows"):
            cur[key] = max(cur.get(key, 0.0), _pick_num(row, key))
        # 文字欄位若先前為空，補上
        if not cur["caption"]:
            cur["caption"] = (_pick(row, "caption") or "")[:280]
        if not cur["permalink"]:
            cur["permalink"] = _pick(row, "permalink") or ""

    reels = list(by_post.values())
    for r in reels:
        # 互動數：有 total_interactions 用它，否則自己加總
        inter = r["interactions"] or (r["likes"] + r["comments"] + r["shares"] + r["saves"])
        r["interactions"] = inter
        denom = r["reach"] or r["views"] or r["impressions"] or 0.0
        r["engagement_rate"] = (inter / denom * 100.0) if denom else 0.0
        r["comment_rate"] = (r["comments"] / denom * 100.0) if denom else 0.0
        r["share_rate"] = (r["shares"] / denom * 100.0) if denom else 0.0
        r["save_rate"] = (r["saves"] / denom * 100.0) if denom else 0.0
    return reels


# ─────────────────────────────────────────────────────────────────────────
# 3) 審計：綜合分排行榜
# ─────────────────────────────────────────────────────────────────────────
def _minmax_norm(values):
    lo, hi = min(values), max(values)
    if hi - lo < 1e-9:
        return [0.0 for _ in values]
    return [(v - lo) / (hi - lo) for v in values]


def rank(reels):
    """用 views / engagement_rate / shares 三軸 min-max 正規化後加權，算綜合分。"""
    if not reels:
        return []
    norm = {}
    for axis in ("views", "engagement_rate", "shares"):
        norm[axis] = _minmax_norm([r[axis] for r in reels])
    for i, r in enumerate(reels):
        r["score"] = round(
            100.0 * sum(WEIGHTS[a] * norm[a][i] for a in WEIGHTS), 2
        )
    return sorted(reels, key=lambda r: r["score"], reverse=True)


def account_summary(reels, days):
    n = len(reels)
    if n == 0:
        return {"reels": 0}
    s = lambda k: sum(r[k] for r in reels)
    avg = lambda k: s(k) / n
    return {
        "window_days": days,
        "reels": n,
        "post_frequency_per_week": round(n / (days / 7.0), 2),
        "total_views": int(s("views")),
        "avg_views": int(avg("views")),
        "avg_engagement_rate": round(avg("engagement_rate"), 2),
        "avg_comment_rate": round(avg("comment_rate"), 3),
        "avg_share_rate": round(avg("share_rate"), 3),
        "avg_save_rate": round(avg("save_rate"), 3),
        "total_shares": int(s("shares")),
        "total_saves": int(s("saves")),
        "total_new_follows": int(s("follows")),
    }


# ─────────────────────────────────────────────────────────────────────────
# 輸出
# ─────────────────────────────────────────────────────────────────────────
def write_outputs(ranked, summary, top, days):
    os.makedirs(OUT_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    json_path = os.path.join(OUT_DIR, f"audit_{stamp}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "reels": ranked}, f, ensure_ascii=False, indent=2)

    csv_path = os.path.join(OUT_DIR, f"audit_{stamp}.csv")
    cols = ["score", "views", "reach", "engagement_rate", "likes", "comments",
            "shares", "saves", "comment_rate", "share_rate", "save_rate",
            "avg_watch_time", "permalink", "caption"]
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in ranked:
            w.writerow([r.get(c, "") for c in cols])

    md_path = os.path.join(OUT_DIR, f"audit_{stamp}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(_render_markdown(ranked, summary, top, days))

    return json_path, csv_path, md_path


def _render_markdown(ranked, summary, top, days):
    L = []
    L.append(f"# Instagram Reels 審計報告（最近 {days} 天）\n")
    L.append(f"產出時間：{datetime.now():%Y-%m-%d %H:%M}\n")
    L.append("## 帳號總覽\n")
    if summary.get("reels", 0) == 0:
        L.append("> ⚠️ 這段期間沒有抓到任何 Reels。確認 connector / 日期 / 帳號是否正確。\n")
        return "\n".join(L)
    L.append(f"- 發片數：**{summary['reels']}** 支（約 {summary['post_frequency_per_week']} 支/週）")
    L.append(f"- 平均觀看：**{summary['avg_views']:,}**　總觀看：{summary['total_views']:,}")
    L.append(f"- 平均互動率：**{summary['avg_engagement_rate']}%**")
    L.append(f"- 平均留言率：{summary['avg_comment_rate']}%　平均分享率：{summary['avg_share_rate']}%　平均收藏率：{summary['avg_save_rate']}%")
    L.append(f"- 期間總分享：{summary['total_shares']:,}　總收藏：{summary['total_saves']:,}　新追蹤(歸因)：{summary['total_new_follows']:,}\n")

    L.append(f"## 績效排行榜 TOP {top}\n")
    L.append("| # | 綜合分 | 觀看 | 互動率 | 留言 | 分享 | 收藏 | 連結 |")
    L.append("|---|---|---|---|---|---|---|---|")
    for i, r in enumerate(ranked[:top], 1):
        L.append(
            f"| {i} | {r['score']} | {int(r['views']):,} | {r['engagement_rate']:.2f}% "
            f"| {int(r['comments'])} | {int(r['shares'])} | {int(r['saves'])} "
            f"| {r['permalink'] or '—'} |"
        )
    L.append("\n## 待診斷清單（給 AI 夥伴讀）\n")
    L.append("把這份報告（或 JSON）丟回對話，我會逐支拆 Hook、內容架構、")
    L.append("找出流量在第幾秒流失、點出最大盲點，並給可立即執行的 Action Plan。\n")
    return "\n".join(L)


# ─────────────────────────────────────────────────────────────────────────
# Self-test：用「明顯標示為假」的資料驗證 pipeline，不需金鑰
# ─────────────────────────────────────────────────────────────────────────
def _fake_rows():
    print("⚠️  SELF-TEST：以下為【虛構假資料】，僅用來驗證程式跑得動，"
          "不是你的真實數據，不可用於決策。")
    base = []
    samples = [
        ("hook 把痛點砸臉上", 124000, 90000, 5200, 480, 320, 410, "VIDEO", "REELS"),
        ("純字卡教學第3集",   86000, 70000, 3100, 95,  40,  610, "VIDEO", "REELS"),
        ("真人口播日常",       210000,160000, 6400, 88,  22,  120, "VIDEO", "REELS"),
        ("跟風熱門音樂",       52000, 41000, 1500, 12,  6,   30,  "VIDEO", "REELS"),
        ("一張圖貼文(非reel)", 9000,  8000,  300,  5,   2,   10,  "IMAGE", "FEED"),
    ]
    for i, (cap, views, reach, likes, comments, shares, saves, mt, pt) in enumerate(samples):
        base.append({
            "post_id": f"FAKE{i}", "post_caption": cap, "post_permalink": f"https://instagram.com/reel/FAKE{i}",
            "post_media_type": mt, "post_media_product_type": pt, "video_views": views,
            "reach": reach, "likes": likes, "comments": comments, "shares": shares, "saved": saves,
        })
    return base


# ─────────────────────────────────────────────────────────────────────────
# 主程式
# ─────────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="Instagram Reels 審計（透過 Windsor.ai）")
    ap.add_argument("--days", type=int, default=30, help="回看天數（預設 30）")
    ap.add_argument("--top", type=int, default=3, help="排行榜名次（預設 3）")
    ap.add_argument("--connector", default=WINDSOR_CONNECTOR, help="Windsor 連接器名稱")
    ap.add_argument("--self-test", action="store_true", help="用假資料驗證程式（不需金鑰）")
    ap.add_argument("--raw-only", action="store_true", help="只拉原始資料、不算審計")
    args = ap.parse_args()

    if args.self_test:
        rows = _fake_rows()
    else:
        fields = os.environ.get("WINDSOR_FIELDS")
        fields = [x.strip() for x in fields.split(",")] if fields else None
        rows = fetch_windsor(WINDSOR_API_KEY, args.days, args.connector, fields)

    if args.raw_only:
        os.makedirs(OUT_DIR, exist_ok=True)
        p = os.path.join(OUT_DIR, "raw.json")
        with open(p, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)
        print(f"✓ 原始資料已存：{p}（{len(rows)} 列）")
        return

    reels = consolidate(rows)
    ranked = rank(reels)
    summary = account_summary(ranked, args.days)

    print(f"\n✓ 解析出 {len(ranked)} 支 Reels")
    if ranked:
        print(f"  TOP1：score={ranked[0]['score']}  views={int(ranked[0]['views']):,}  "
              f"互動率={ranked[0]['engagement_rate']:.2f}%")
    jp, cp, mp = write_outputs(ranked, summary, args.top, args.days)
    print("\n輸出檔：")
    for p in (mp, cp, jp):
        print(f"  • {p}")
    print("\n把 .md 或 .json 丟回對話，我就開始毒舌審計。")


if __name__ == "__main__":
    main()
