"""ig_post_maker.py — 劇本 → IG 貼文包（輪播 / Reels / 文案）。

落實 `11_Publish/CONTENT_FACTORY.md` 的「一部作品 → 多則內容」槓桿層，
由 Marketing Manager Agent 使用。純標準庫，不需安裝任何套件。

用法：
    python3 ig_post_maker.py ../05_Scripts/JMD/S01/E01/JMD_S01_E01_script_v01.md \\
        --storyboard ../06_Storyboard/JMD/S01/E01/JMD_S01_E01_storyboard_v01.md

產出（依 NAMING_CONVENTION）：
    11_Publish/IG/{PROJECT}/S{季}/E{集}/
        {PROJECT}_S01_E01_carousel_01_v01.md   輪播貼文 8 卡（4:5）
        {PROJECT}_S01_E01_reels_01_v01.md      Reels 腳本（9:16，15–60s）
        {PROJECT}_S01_E01_caption_01_v01.md    貼文文案 + hashtag
        _brand_guard_report.md                 品牌護欄稽核

品牌護欄有阻斷項時回傳非 0（可接進 CI / Production Worker 流程）。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import studio

# ── 品牌護欄：Brand Bible「絕對禁止」的機器版 ────────────────────────────
BANNED = {
    "浮誇": ["震驚", "太神了", "神準", "史上最", "必看", "爆紅", "逆天", "無敵"],
    "恐嚇式行銷": ["不看會後悔", "不看後悔", "你命裡有劫", "小心報應", "會出事", "血光之災"],
    "保證預測": ["保證", "一定會發財", "必定發生", "絕對會", "包準", "鐵定"],
    "迷信": ["改運", "轉運符", "破解厄運", "因果報應", "前世業障", "沖煞"],
    "恐怖": ["詛咒", "鬼上身", "厄運纏身", "驚悚"],
}

# 金句評分關鍵詞：越接近「理解自己」越高分
INSIGHT_WORDS = [
    "理解", "選", "答案", "命盤", "傾向", "差別", "可以", "溫柔",
    "在乎", "不是", "決定", "允許", "自己",
]

BELIEF = "真正重要的，不是答案，而是你開始理解自己。"

BASE_HASHTAGS = [
    "#潔米爸", "#紫微斗數", "#占驗派", "#理解自己", "#自我理解",
    "#命盤不是宿命", "#情緒陪伴", "#AI動畫", "#人生課題", "#溫柔的力量",
]


# ── 劇本解析 ──────────────────────────────────────────────────────────
def _table_lookup(text: str, key_fragment: str) -> str:
    """從標頭表格取值；以「欄位名含 key_fragment」寬鬆比對（欄位名常含空白）。"""
    for line in text.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        if key_fragment in cells[0].replace(" ", ""):
            return cells[1]
    return ""


def _body(text: str) -> str:
    """取「## 劇本本文」底下 ``` 圍欄裡的正文。"""
    m = re.search(r"##\s*劇本本文\s*\n+```[a-z]*\n(.*?)\n```", text, re.DOTALL)
    return m.group(1) if m else text


def parse_script(path: Path) -> dict:
    """把劇本 markdown 解析成 {meta, scenes, lines, ending}。"""
    text = path.read_text(encoding="utf-8")
    project, season, episode = _parse_slug(text, path)

    meta = {
        "project": project,
        "season": season,
        "episode": episode,
        "title": _table_lookup(text, "標題").strip("〈〉"),
        "theme": _table_lookup(text, "主題"),
        "characters": _table_lookup(text, "出場角色"),
        "scenes_hint": _table_lookup(text, "主場景"),
        "core": _quote_block(text, "一句話核心"),
        "arc": _quote_block(text, "情緒弧線"),
    }

    scenes, lines, ending = _parse_body(_body(text))
    return {"meta": meta, "scenes": scenes, "lines": lines, "ending": ending}


def _parse_slug(text: str, path: Path) -> tuple[str, str, str]:
    """從標頭「專案 / 季 / 集」或檔名推出 (PROJECT, S01, E01)。"""
    cell = _table_lookup(text, "專案")
    m = re.search(r"([A-Z][A-Z0-9]+)\s*/\s*(S\d+)\s*/\s*(E\d+)", cell)
    if m:
        return m.group(1), m.group(2), m.group(3)
    m = re.match(r"([A-Z][A-Z0-9]+)_(S\d+)_(E\d+)", path.stem)
    if m:
        return m.group(1), m.group(2), m.group(3)
    return "PROJECT", "S01", "E01"


def _quote_block(text: str, heading: str) -> str:
    """取「## {heading}」後第一段 > 引用或反引號行。"""
    m = re.search(rf"##\s*{re.escape(heading)}[^\n]*\n+[>`]\s*(.+?)\n", text)
    return m.group(1).strip().strip("`").strip() if m else ""


SCENE_RE = re.compile(r"^場景\s*(\d+)\s*[—–\-]\s*(.+)$")
LINE_RE = re.compile(r"^(?P<who>[^\s（(：:][^：:]{0,14})[：:]\s*(?P<text>.+)$")


def _parse_body(body: str) -> tuple[list[dict], list[dict], list[str]]:
    """逐行掃劇本正文，抽出場景、對白/旁白、片尾字卡。"""
    scenes: list[dict] = []
    lines: list[dict] = []
    ending: list[str] = []
    scene_no, scene_title = 0, ""
    in_ending = False
    stage_depth = 0  # 跨行的場面指示（（…\n…））

    for raw in body.splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped or set(stripped) <= set("-—–"):
            continue

        if stage_depth > 0:  # 仍在多行場面指示裡
            stage_depth = max(0, stage_depth + _paren_delta(stripped))
            continue

        if "片尾" in stripped and stripped.startswith("——"):
            in_ending = True
            continue
        if in_ending:
            if stripped.startswith(("（", "(")):
                stage_depth = max(0, _paren_delta(stripped))
                continue
            ending.append(stripped)
            continue

        m = SCENE_RE.match(stripped)
        if m:
            scene_no = int(m.group(1))
            scene_title = m.group(2).strip()
            scenes.append({"no": scene_no, "title": scene_title})
            continue

        if stripped.startswith(("（", "(")):  # 場面指示（可能跨行）
            delta = _paren_delta(stripped)
            if delta > 0:
                stage_depth = delta
                continue
            # `（停頓）真正卡住的人…` 這種：括號只是表演指示，後面仍是台詞
            rest = re.sub(r"^[（(][^）)]*[）)]", "", stripped).strip()
            if rest and lines:
                lines[-1]["text"] = (lines[-1]["text"] + _clean(rest)).strip()
            continue

        m = LINE_RE.match(stripped)
        if m:
            who, kind = _split_speaker(m.group("who"))
            lines.append({
                "scene": scene_no,
                "scene_title": scene_title,
                "speaker": who,
                "kind": kind,
                "text": _clean(m.group("text")),
            })
            continue

        # 縮排續行 → 接到上一句
        if raw.startswith((" ", "\t")) and lines:
            lines[-1]["text"] = (lines[-1]["text"] + _clean(stripped)).strip()

    return scenes, _merge_runons(lines), ending


def _paren_delta(text: str) -> int:
    """一行內未閉合的全形/半形括號數（>0 表示場面指示還沒結束）。"""
    return (text.count("（") + text.count("(")) - (text.count("）") + text.count(")"))


def _merge_runons(lines: list[dict]) -> list[dict]:
    """同角色同場景、前句以逗號/破折號收尾者合併成完整一句（金句才不會被切一半）。"""
    merged: list[dict] = []
    for ln in lines:
        prev = merged[-1] if merged else None
        if (prev and prev["speaker"] == ln["speaker"] and prev["scene"] == ln["scene"]
                and prev["kind"] == ln["kind"]
                and prev["text"].endswith(("，", "、", "——", "－", "—"))):
            prev["text"] += ln["text"]
            continue
        merged.append(dict(ln))
    return merged


def _split_speaker(who: str) -> tuple[str, str]:
    """`旁白（阿哲）` → (阿哲, 旁白)；`潔米爸（畫外）` → (潔米爸, 畫外)。"""
    m = re.match(r"^([^（(]+)[（(]([^）)]+)[）)]$", who.strip())
    if not m:
        return who.strip(), "對白"
    head, paren = m.group(1).strip(), m.group(2).strip()
    if head in {"旁白", "OS", "獨白"}:
        return paren, "旁白"
    return head, paren


def _norm(text: str) -> str:
    """比對用：去標點與空白，避免同一句因標點差異被當成兩句。"""
    return re.sub(r"[\s，。、！？「」『』—…·,.!?\"']", "", text)


def _clean(text: str) -> str:
    """去掉行內場面指示 `（溫和）`，收乾空白。"""
    text = re.sub(r"[（(][^）)]{0,12}[）)]", "", text)
    return re.sub(r"\s+", "", text).strip()


# ── 金句挑選 ──────────────────────────────────────────────────────────
def score_quote(item: dict) -> int:
    text = item["text"]
    score = sum(2 for w in INSIGHT_WORDS if w in text)
    if item.get("speaker") == "潔米爸":
        score += 3
    if item.get("kind") == "旁白":
        score += 1
    if 10 <= len(text) <= 28:
        score += 2
    if text.endswith("？"):
        score += 1
    return score


def pick_quotes(script: dict, want: int) -> list[dict]:
    """挑最能代表「理解自己」的金句，並保留劇本順序（情緒弧線不亂）。"""
    pool = [ln for ln in script["lines"] if 6 <= len(ln["text"]) <= 44]
    seen: set[str] = set()
    uniq = []
    for ln in pool:
        if ln["text"] in seen:
            continue
        seen.add(ln["text"])
        uniq.append(ln)
    ranked = sorted(uniq, key=score_quote, reverse=True)[:want]
    order = {id(x): i for i, x in enumerate(uniq)}
    return sorted(ranked, key=lambda x: order[id(x)])


# ── 分鏡對照（給視覺指示 / Reels 選段） ──────────────────────────────
def index_shots(sb_path: Path | None) -> list[dict]:
    if not sb_path:
        return []
    return studio.parse_storyboard(sb_path)


def match_shot(shots: list[dict], text: str) -> dict | None:
    """用對白前幾個字回查分鏡列，取得場景 / 運鏡 / 光線。"""
    if not shots or len(text) < 4:
        return None
    key = text[:5]
    for row in shots:
        cell = re.sub(r"\s+", "", row.get("對白/旁白", ""))
        if key and key in cell:
            return row
    return None


def _seconds(row: dict) -> int:
    m = re.search(r"\d+", row.get("秒", ""))
    return int(m.group()) if m else 4


def pick_reels_window(shots: list[dict], anchor: dict | None,
                      lo: int = 15, hi: int = 60, target: int = 35) -> list[dict]:
    """以情緒高峰鏡頭為中心，向外擴到 target 秒（夾在 15–60s）。"""
    if not shots:
        return []
    start = shots.index(anchor) if anchor in shots else max(0, len(shots) // 2 - 3)
    lo_i = hi_i = start
    total = _seconds(shots[start])
    while total < target and (lo_i > 0 or hi_i < len(shots) - 1):
        if hi_i < len(shots) - 1 and (total + _seconds(shots[hi_i + 1])) <= hi:
            hi_i += 1
            total += _seconds(shots[hi_i])
        elif lo_i > 0 and (total + _seconds(shots[lo_i - 1])) <= hi:
            lo_i -= 1
            total += _seconds(shots[lo_i])
        else:
            break
    window = shots[lo_i:hi_i + 1]
    return window if total >= lo or len(window) == len(shots) else shots[:12]


# ── 產出 ──────────────────────────────────────────────────────────────
def _visual(row: dict | None, fallback: str) -> str:
    if not row:
        return f"{fallback}（暖光為主、留白、命盤金色點綴）"
    return (f"{row.get('場景', fallback)}｜運鏡 `{row.get('運鏡', '—')}`"
            f"｜光線 `{row.get('光線', '—')}`｜取自 {row.get('Shot Prompt', '—')}")


def build_carousel(script: dict, quotes: list[dict], shots: list[dict], cards: int) -> str:
    meta = script["meta"]
    hook = _hook(script, quotes)
    # 封面與收束卡（信念句）已經佔掉的句子不重複出現在金句卡
    used = {_norm(hook), _norm(BELIEF)}
    body_quotes = [q for q in quotes if _norm(q["text"]) not in used][: max(1, cards - 3)]

    out = [
        f"# {meta['project']}_{meta['season']}_{meta['episode']} — IG 輪播貼文",
        "",
        f"> 主題：{meta['theme']}",
        f"> 版位：4:5（1080×1350）｜共 {len(body_quotes) + 3} 張｜依 Brand Bible：溫暖 · 理性 · 電影感",
        "",
        "---",
        "",
        "## 卡 1 — 封面（鉤子）",
        "",
        f"**大字**：{hook}",
        "",
        f"**副標**：〈{meta['title']}〉",
        f"**視覺**：{_visual(match_shot(shots, hook), meta['scenes_hint'])}",
        "",
    ]

    n = 1
    for q in body_quotes:
        n += 1
        row = match_shot(shots, q["text"])
        speaker = q["speaker"] + ("（旁白）" if q["kind"] == "旁白" else "")
        out += [
            "---",
            "",
            f"## 卡 {n} — 金句（場景 {q['scene']}｜{q['scene_title']}）",
            "",
            f"**大字**：{q['text']}",
            "",
            f"**來源**：{speaker}",
            f"**視覺**：{_visual(row, q['scene_title'])}",
            "",
        ]

    n += 1
    out += [
        "---",
        "",
        f"## 卡 {n} — 收束（回扣信念）",
        "",
        f"**大字**：{BELIEF}",
        "",
        "**視覺**：黑底金字，留白 60%，字幕乾淨不塞滿。",
        "",
        "---",
        "",
        f"## 卡 {n + 1} — CTA",
        "",
        "**文字**：你開始理解自己了嗎？",
        "**副文字**：完整一集在 YouTube｜留言告訴我，你今天替自己選了什麼。",
        "**視覺**：雨後街道暖光滲入冷城，人物背影走進人群。",
        "",
        "---",
        "",
        "## 產製備註",
        "",
        "- 每張卡文字 ≤ 24 字，其餘交給畫面（Brand Bible：不塞滿）。",
        "- 標題一律不用浮誇或恐嚇式話術（禁止清單見 Brand Bible 第五節）。",
        "- 金句卡順序沿用劇本情緒弧線，收在釋懷。",
        "",
    ]
    return "\n".join(out)


def _hook(script: dict, quotes: list[dict]) -> str:
    """封面鉤子：優先取短金句，其次取核心句第一段。"""
    short = [q["text"] for q in quotes if 8 <= len(q["text"]) <= 20]
    if short:
        return short[0]
    core = script["meta"]["core"] or script["meta"]["theme"]
    return re.split(r"[，。；]", core)[0][:20] if core else script["meta"]["title"]


def build_reels(script: dict, quotes: list[dict], shots: list[dict]) -> str:
    meta = script["meta"]
    peak = quotes[len(quotes) // 2] if quotes else None
    anchor = match_shot(shots, peak["text"]) if peak else None
    window = pick_reels_window(shots, anchor)
    total = sum(_seconds(r) for r in window) if window else 0

    out = [
        f"# {meta['project']}_{meta['season']}_{meta['episode']} — IG Reels 腳本",
        "",
        f"> 版位：9:16｜長度：{total or '15–60'} 秒｜單一情緒：{_peak_emotion(window)}",
        "> 規格依 `11_Publish/CONTENT_FACTORY.md`：前 3 秒鉤子、全程字幕、單一情緒。",
        "",
        "## 前 3 秒鉤子",
        "",
        f"**字幕**：{_hook(script, quotes)}",
        "**畫面**：冷色 → 一顆星微亮的暖點（不要爆閃、不要驚嚇式剪接）。",
        "",
        "## 分鏡選段",
        "",
    ]

    if window:
        out += ["| # | 秒 | 場景 | 光線 | 運鏡 | 字幕 |",
                "|---|----|------|------|------|------|"]
        for row in window:
            out.append(
                f"| {row.get('#', '')} | {row.get('秒', '')} | {row.get('場景', '')} "
                f"| `{row.get('光線', '')}` | `{row.get('運鏡', '')}` | {row.get('對白/旁白', '')} |"
            )
    else:
        out.append("_（未提供分鏡表，以下用劇本金句排序，剪輯時再對鏡頭。）_")
        out += [""] + [f"- {q['speaker']}：{q['text']}" for q in quotes]

    out += [
        "",
        "## 收尾（最後 3–5 秒）",
        "",
        f"**字幕**：{BELIEF}",
        "**畫面**：黑底金字 → 品牌卡。留白，不加音效轟炸。",
        "",
        "## 聲音",
        "",
        "- 配音沿用 `09_Voice` 固定聲線（潔米爸低沉溫暖、語速慢）。",
        "- 音樂：低限鋼琴／弦樂持續音，不用懸疑鼓點（神秘但不玄幻）。",
        "",
    ]
    return "\n".join(out)


def _peak_emotion(window: list[dict]) -> str:
    if not window:
        return "relief（釋懷）"
    counts: dict[str, int] = {}
    for row in window:
        e = row.get("情緒", "").strip()
        if e and e != "—":
            counts[e] = counts.get(e, 0) + 1
    return max(counts, key=counts.get) if counts else "relief（釋懷）"


def build_caption(script: dict, quotes: list[dict]) -> str:
    meta = script["meta"]
    hook = _hook(script, quotes)
    used = {_norm(hook), _norm(BELIEF)}  # 文案結尾已有信念句，內文不重複
    picks = [q["text"] for q in quotes if _norm(q["text"]) not in used][:3]
    tags = hashtags(meta)

    out = [
        f"# {meta['project']}_{meta['season']}_{meta['episode']} — IG 貼文文案",
        "",
        "## 正式文案（可直接貼）",
        "",
        "```",
        hook,
        "",
        meta["core"] or meta["theme"],
        "",
    ]
    for p in picks:
        out += [f"「{p}」", ""]
    out += [
        "命盤講的是傾向，不是判決。",
        "同一顆星，你可以讀成軟弱，也可以讀成溫柔——差別不在星，在讀它的人。",
        "",
        BELIEF,
        "",
        "👉 完整一集在 YouTube（連結在個人簡介）",
        "💬 留言告訴我：你今天替自己選了什麼？",
        "",
        " ".join(tags),
        "```",
        "",
        "## 備用鉤子（A/B 測試）",
        "",
    ]
    for q in quotes[:4]:
        out.append(f"- {q['text']}")
    out += [
        "",
        "## 品牌守則檢查點",
        "",
        "- 不用浮誇或恐嚇式話術（禁止清單見 Brand Bible 第五節）。",
        "- 不做吉凶預測、不對結果下絕對承諾。",
        "- 結尾回扣：你開始理解自己了嗎？",
        "",
    ]
    return "\n".join(out)


def hashtags(meta: dict) -> list[str]:
    tags = list(BASE_HASHTAGS)
    for name in re.split(r"[、,／/]", meta.get("characters", "")):
        name = name.strip()
        if name and f"#{name}" not in tags:
            tags.append(f"#{name}")
    return tags[:14]


# ── 品牌護欄稽核 ──────────────────────────────────────────────────────
def brand_guard(docs: dict[str, str]) -> list[tuple[str, str, str]]:
    """回傳 [(檔名, 違反類別, 命中詞)]。"""
    hits = []
    for name, text in docs.items():
        for category, words in BANNED.items():
            for w in words:
                if w in text:
                    hits.append((name, category, w))
    return hits


def guard_report(docs: dict[str, str], hits: list[tuple[str, str, str]]) -> str:
    out = ["# IG 貼文包 — 品牌護欄稽核", "",
           "> 依 `01_Brand/BRAND_BIBLE.md` 第五節「絕對禁止」自動掃描。", ""]
    if not hits:
        out += ["✅ **通過**：未發現恐怖／迷信／浮誇／恐嚇／保證預測用語。", ""]
    else:
        out += ["⛔ **不合格，需重做**（Brand Bible：觸犯任一條一律重做）", "",
                "| 檔案 | 類別 | 命中詞 |", "|------|------|--------|"]
        out += [f"| `{n}` | {c} | `{w}` |" for n, c, w in hits]
        out.append("")
    out += ["## 掃描範圍", ""] + [f"- `{n}`（{len(t)} 字）" for n, t in docs.items()] + [""]
    return "\n".join(out)


# ── CLI ───────────────────────────────────────────────────────────────
def default_out(meta: dict) -> Path:
    return (studio.OS_ROOT / "11_Publish" / "IG" / meta["project"]
            / meta["season"] / meta["episode"])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="劇本 → IG 貼文包（輪播 / Reels / 文案）")
    ap.add_argument("script", type=Path, help="05_Scripts 的劇本 markdown")
    ap.add_argument("--storyboard", type=Path, default=None,
                    help="06_Storyboard 分鏡表（有的話視覺指示與 Reels 選段會更準）")
    ap.add_argument("--out", type=Path, default=None, help="輸出資料夾（預設 11_Publish/IG/…）")
    ap.add_argument("--formats", default="carousel,reels,caption",
                    help="要產出的格式，逗號分隔")
    ap.add_argument("--cards", type=int, default=8, help="輪播張數（預設 8，規格 6–10）")
    ap.add_argument("--version", default="v01", help="檔名版本（預設 v01）")
    ap.add_argument("--index", default="01", help="檔名編號（預設 01）")
    ap.add_argument("--dry-run", action="store_true", help="只印出，不寫檔")
    args = ap.parse_args(argv)

    if not args.script.exists():
        print(f"找不到劇本：{args.script}", file=sys.stderr)
        return 2
    if not 6 <= args.cards <= 10:
        print("⚠️  輪播張數規格為 6–10（CONTENT_FACTORY.md），已夾住。", file=sys.stderr)
        args.cards = min(10, max(6, args.cards))

    script = parse_script(args.script)
    meta = script["meta"]
    shots = index_shots(args.storyboard)
    # 封面鉤子與收束的信念句會各用掉一句 → 多挑兩句，讓輪播湊得滿 args.cards 張
    quotes = pick_quotes(script, args.cards - 1)

    if not quotes:
        print("劇本中找不到可用金句（對白解析為空）。", file=sys.stderr)
        return 2

    formats = [f.strip() for f in args.formats.split(",") if f.strip()]
    stem = f"{meta['project']}_{meta['season']}_{meta['episode']}"
    docs: dict[str, str] = {}
    if "carousel" in formats:
        docs[f"{stem}_carousel_{args.index}_{args.version}.md"] = \
            build_carousel(script, quotes, shots, args.cards)
    if "reels" in formats:
        docs[f"{stem}_reels_{args.index}_{args.version}.md"] = \
            build_reels(script, quotes, shots)
    if "caption" in formats:
        docs[f"{stem}_caption_{args.index}_{args.version}.md"] = \
            build_caption(script, quotes)

    hits = brand_guard(docs)
    report = guard_report(docs, hits)

    if args.dry_run:
        for name, text in docs.items():
            print(f"\n===== {name} =====\n{text}")
        print(f"\n===== _brand_guard_report.md =====\n{report}")
        return 1 if hits else 0

    out_dir = args.out or default_out(meta)
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, text in docs.items():
        (out_dir / name).write_text(text, encoding="utf-8")
    (out_dir / "_brand_guard_report.md").write_text(report, encoding="utf-8")

    print(f"📦 IG 貼文包 → {out_dir}")
    for name in docs:
        print(f"   ✅ {name}")
    print("   📋 _brand_guard_report.md")
    print(f"   金句 {len(quotes)} 句｜分鏡對照 {'有' if shots else '無'}")
    if hits:
        print(f"⛔ 品牌護欄不合格：{len(hits)} 項，見稽核報告。", file=sys.stderr)
        return 1
    print("✅ 品牌護欄通過。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
