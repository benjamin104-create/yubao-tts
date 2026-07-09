#!/usr/bin/env python3
"""把生成好的分格畫 + panels.json 的文字，排版成完整漫畫頁。

用法:
    python3 comic/pipeline/assemble.py comic/episodes/ep16 [--pages 1,3-5]

輸入:  <episode>/panels.json、comic/art/ep<N>/<panel_id>.png(缺圖時以佔位圖代替)
輸出:  comic/out/ep<N>/page_NN.png
文字一律由本引擎以真實字型繪製，圖像模型只畫「無文字」的畫面。
"""
import argparse
import json
import math
import random
import sys
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent  # comic/
PAGE_W, PAGE_H = 1200, 1536
OUTER = 30          # 黑底外緣
FRAME_GAP = 10      # 雙金線間距
GUTTER = 8          # 分格間距

INK_BLACK = (18, 16, 13)
GOLD = (201, 162, 39)
GOLD_DARK = (138, 109, 31)
PARCHMENT = (240, 230, 210)
PARCHMENT_EDGE = (90, 70, 30)
INDIGO = (27, 36, 64)

FONT_URL = ("https://raw.githubusercontent.com/google/fonts/main/"
            "ofl/notoseriftc/NotoSerifTC%5Bwght%5D.ttf")
FONT_PATH = ROOT / "fonts" / "NotoSerifTC.ttf"
FALLBACK_FONTS = [
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
]

# 直式標點對映(缺字時自動保留原字)
V_PUNCT = {
    "，": "︐", "。": "︒", "、": "︑", "：": "︓",
    "；": "︔", "！": "︕", "？": "︖", "…": "︙",
    "（": "︵", "）": "︶", "「": "﹁", "」": "﹂",
    "《": "︽", "》": "︾", "〈": "︿", "〉": "﹀",
    "—": "︱", "｜": "︱",
}


def ensure_font() -> Path:
    if FONT_PATH.exists() and FONT_PATH.stat().st_size > 1_000_000:
        return FONT_PATH
    FONT_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        print("下載字型 Noto Serif TC …")
        urllib.request.urlretrieve(FONT_URL, FONT_PATH)
        if FONT_PATH.stat().st_size > 1_000_000:
            return FONT_PATH
    except Exception as exc:  # noqa: BLE001
        print(f"字型下載失敗({exc})，改用系統字型", file=sys.stderr)
    for fb in FALLBACK_FONTS:
        if Path(fb).exists():
            return Path(fb)
    raise SystemExit("找不到可用中文字型")


_font_cache: dict[tuple[int, str], ImageFont.FreeTypeFont] = {}


def get_font(size: int, weight: str = "SemiBold") -> ImageFont.FreeTypeFont:
    key = (size, weight)
    if key not in _font_cache:
        font = ImageFont.truetype(str(ensure_font()), size)
        try:
            font.set_variation_by_name(weight)
        except Exception:  # noqa: BLE001 — 非可變字型
            pass
        _font_cache[key] = font
    return _font_cache[key]


def has_glyph(font: ImageFont.FreeTypeFont, ch: str) -> bool:
    try:
        return font.getmask(ch).getbbox() is not None
    except Exception:  # noqa: BLE001
        return False


def to_vertical(text: str, font: ImageFont.FreeTypeFont) -> str:
    return "".join(
        V_PUNCT[c] if c in V_PUNCT and has_glyph(font, V_PUNCT[c]) else c
        for c in text
    )


# ---------------------------------------------------------------- 佔位圖 --
def placeholder_art(w: int, h: int, panel_id: str) -> Image.Image:
    """缺圖時的程式繪製佔位畫面(靛藍夜空+星點)，方便先驗版面。"""
    img = Image.new("RGB", (w, h))
    px = img.load()
    for y in range(h):
        t = y / max(h - 1, 1)
        r = int(INDIGO[0] * (1 - t) + INK_BLACK[0] * t)
        g = int(INDIGO[1] * (1 - t) + INK_BLACK[1] * t)
        b = int(INDIGO[2] * (1 - t) + INK_BLACK[2] * t)
        for x in range(w):
            px[x, y] = (r, g, b)
    d = ImageDraw.Draw(img)
    rng = random.Random(panel_id)
    for _ in range(w * h // 3500):
        x, y = rng.randrange(w), rng.randrange(h)
        s = rng.choice([1, 1, 1, 2])
        c = rng.randint(140, 230)
        d.ellipse([x, y, x + s, y + s], fill=(c, c, int(c * 0.8)))
    d.ellipse([w * 0.3, h * 0.25, w * 0.7, h * 0.95], outline=GOLD_DARK, width=2)
    d.ellipse([w * 0.36, h * 0.35, w * 0.64, h * 0.85], outline=GOLD_DARK, width=1)
    f = get_font(24, "Regular")
    d.text((w / 2, h / 2), f"[ 待生成:{panel_id} ]", font=f,
           fill=(120, 110, 80), anchor="mm")
    return img


def load_art(art_dir: Path, panel_id: str, w: int, h: int) -> Image.Image:
    for ext in ("png", "jpg", "jpeg", "webp"):
        p = art_dir / f"{panel_id}.{ext}"
        if p.exists():
            img = Image.open(p).convert("RGB")
            scale = max(w / img.width, h / img.height)  # cover-crop 置中
            img = img.resize((round(img.width * scale), round(img.height * scale)))
            x = (img.width - w) // 2
            y = (img.height - h) // 2
            return img.crop((x, y, x + w, y + h))
    return placeholder_art(w, h, panel_id)


# ------------------------------------------------------------ 文字量測 --
def measure_v(lines: list[str], size: int, char_gap: int, col_gap: int):
    cell = size + char_gap
    hgt = max(len(ln) for ln in lines) * cell
    wid = len(lines) * size + (len(lines) - 1) * col_gap
    return wid, hgt


def draw_v_text(d: ImageDraw.ImageDraw, lines: list[str], right_x: int, top_y: int,
                size: int, fill, char_gap: int, col_gap: int, weight="SemiBold"):
    font = get_font(size, weight)
    cell = size + char_gap
    x = right_x
    for ln in lines:  # 直式：行=直欄，右→左
        col_x = x - size
        for i, ch in enumerate(to_vertical(ln, font)):
            d.text((col_x + size / 2, top_y + i * cell + size / 2),
                   ch, font=font, fill=fill, anchor="mm")
        x = col_x - col_gap


# ------------------------------------------------------------ 文字元件 --
def paste_parchment(page: Image.Image, box: tuple[int, int, int, int],
                    ellipse=False, tail=None):
    """米色紙面(方框加金邊、泡泡加墨線)。tail=(tip_x, tip_y) 畫泡泡尾巴。"""
    x0, y0, x1, y1 = box
    layer = Image.new("RGBA", page.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    shadow = Image.new("RGBA", page.size, (0, 0, 0, 0))
    ds = ImageDraw.Draw(shadow)
    if ellipse:
        ds.ellipse([x0 + 5, y0 + 7, x1 + 5, y1 + 7], fill=(0, 0, 0, 110))
        if tail:
            cx = (x0 + x1) / 2
            base_y = y1 - (y1 - y0) * 0.12
            pts = [(cx - 24, base_y), (cx + 10, base_y), tail]
            d.polygon(pts, fill=PARCHMENT, outline=PARCHMENT_EDGE)
        d.ellipse(box, fill=PARCHMENT, outline=PARCHMENT_EDGE, width=3)
    else:
        ds.rectangle([x0 + 5, y0 + 7, x1 + 5, y1 + 7], fill=(0, 0, 0, 110))
        d.rectangle(box, fill=PARCHMENT, outline=GOLD_DARK, width=3)
        d.rectangle([x0 + 7, y0 + 7, x1 - 7, y1 - 7], outline=GOLD, width=1)
    shadow = shadow.filter(ImageFilter.GaussianBlur(4))
    page.paste(Image.alpha_composite(shadow, layer),
               (0, 0), Image.alpha_composite(shadow, layer))


def place_box(anchor: str, bw: int, bh: int, slot) -> tuple[int, int]:
    sx0, sy0, sx1, sy1 = slot
    m = 26
    pos = {
        "tl": (sx0 + m, sy0 + m), "tr": (sx1 - m - bw, sy0 + m),
        "bl": (sx0 + m, sy1 - m - bh), "br": (sx1 - m - bw, sy1 - m - bh),
        "left": (sx0 + m, sy0 + (sy1 - sy0 - bh) // 3),
        "right": (sx1 - m - bw, sy0 + (sy1 - sy0 - bh) // 3),
        "center": ((sx0 + sx1 - bw) // 2, (sy0 + sy1 - bh) // 2),
    }
    return pos.get(anchor, pos["tl"])


def draw_text_item(page: Image.Image, item: dict, slot):
    d = ImageDraw.Draw(page)
    kind = item["kind"]
    orient = item.get("orient", "v")
    lines = item["text"].split("\n")
    size = item.get("size", 30 if kind == "bubble" else 28)
    char_gap, col_gap = 6, 14

    if orient == "v":
        tw, th = measure_v(lines, size, char_gap, col_gap)
    else:
        font = get_font(size)
        tw = max(int(d.textlength(ln, font=font)) for ln in lines)
        th = len(lines) * (size + 12) - 12

    if kind == "bubble":
        bw, bh = int(tw * 1.55) + 40, int(th * 1.18) + 36
        bx, by = place_box(item.get("anchor", "left"), bw, bh, slot)
        paste_parchment(page, (bx, by, bx + bw, by + bh), ellipse=True)
    else:
        pad = 22
        bw, bh = tw + pad * 2, th + pad * 2
        bx, by = place_box(item.get("anchor", "tl"), bw, bh, slot)
        paste_parchment(page, (bx, by, bx + bw, by + bh), ellipse=False)

    tx = bx + (bw - tw) // 2
    ty = by + (bh - th) // 2
    if orient == "v":
        draw_v_text(d, lines, tx + tw, ty, size, INK_BLACK, char_gap, col_gap)
    else:
        font = get_font(size)
        for i, ln in enumerate(lines):
            d.text((bx + bw / 2, ty + i * (size + 12) + size / 2),
                   ln, font=font, fill=INK_BLACK, anchor="mm")


# ------------------------------------------------------------ 頁面裝飾 --
def draw_corner(d: ImageDraw.ImageDraw, cx: int, cy: int, sx: int, sy: int):
    """四角回紋角飾。(cx,cy)=角點，sx/sy=±1 指向頁面內側。"""
    for k, w in ((0, 3), (10, 2)):
        d.line([(cx + sx * k, cy + sy * (k + 34)), (cx + sx * k, cy + sy * k),
                (cx + sx * (k + 34), cy + sy * k)], fill=GOLD, width=w)
    d.rectangle([min(cx + sx * 16, cx + sx * 26), min(cy + sy * 16, cy + sy * 26),
                 max(cx + sx * 16, cx + sx * 26), max(cy + sy * 16, cy + sy * 26)],
                outline=GOLD, width=2)


def draw_frame(page: Image.Image):
    d = ImageDraw.Draw(page)
    a, b = OUTER, OUTER + FRAME_GAP
    d.rectangle([a, a, PAGE_W - a, PAGE_H - a], outline=GOLD, width=3)
    d.rectangle([b, b, PAGE_W - b, PAGE_H - b], outline=GOLD_DARK, width=1)
    for cx, sx in ((a + 4, 1), (PAGE_W - a - 4, -1)):
        for cy, sy in ((a + 4, 1), (PAGE_H - a - 4, -1)):
            draw_corner(d, cx, cy, sx, sy)


def draw_plaque(page: Image.Image, text: str, cy: int, size: int, gold_text=True):
    d = ImageDraw.Draw(page)
    font = get_font(size, "Bold")
    tw = int(d.textlength(text, font=font))
    bw, bh = tw + 56, size + 26
    x0, y0 = (PAGE_W - bw) // 2, cy - bh // 2
    d.rectangle([x0, y0, x0 + bw, y0 + bh], fill=INK_BLACK, outline=GOLD, width=2)
    d.rectangle([x0 + 5, y0 + 5, x0 + bw - 5, y0 + bh - 5], outline=GOLD_DARK, width=1)
    d.text((PAGE_W / 2, y0 + bh / 2), text, font=font,
           fill=GOLD if gold_text else PARCHMENT, anchor="mm")
    return y0, y0 + bh


# ------------------------------------------------------------- 組頁面 --
def build_page(meta: dict, page_def: dict, art_dir: Path) -> Image.Image:
    page = Image.new("RGB", (PAGE_W, PAGE_H), INK_BLACK)
    inner0 = OUTER + FRAME_GAP + 8
    top = inner0
    bottom = PAGE_H - inner0

    is_first = page_def["page"] == 1
    header_h = 0
    if is_first:
        header_h = 100
    else:
        bottom -= 56  # 底部頁碼牌空間

    panels = page_def["panels"]
    total_h = bottom - top - header_h - GUTTER * (len(panels) - 1)
    weights = [p.get("h", 1.0 / len(panels)) for p in panels]
    wsum = sum(weights)

    y = top + header_h
    for p in panels:
        ph = int(total_h * p.get("h", 1.0 / len(panels)) / wsum)
        slot = (inner0, y, PAGE_W - inner0, y + ph)
        art = load_art(art_dir, p["id"], slot[2] - slot[0], ph)
        page.paste(art, (slot[0], slot[1]))
        d = ImageDraw.Draw(page)
        d.rectangle(slot, outline=GOLD_DARK, width=2)
        for item in p.get("texts", []):
            draw_text_item(page, item, slot)
        y += ph + GUTTER

    draw_frame(page)
    if is_first:
        draw_plaque(page, meta["series_header"], top + 26, 40)
        draw_plaque(page, f"第{page_def['page']}頁", top + 82, 22)
    else:
        draw_plaque(page, f"第{page_def['page']}頁", PAGE_H - inner0 - 24, 22)
    return page


def parse_pages(spec: str | None, n: int) -> set[int]:
    if not spec:
        return set(range(1, n + 1))
    out: set[int] = set()
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-")
            out.update(range(int(a), int(b) + 1))
        else:
            out.add(int(part))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("episode_dir", help="例: comic/episodes/ep16")
    ap.add_argument("--pages", help="只組某幾頁, 例: 1,3-5")
    args = ap.parse_args()

    ep_dir = Path(args.episode_dir)
    meta = json.loads((ep_dir / "panels.json").read_text(encoding="utf-8"))
    ep = meta["episode"]
    art_dir = ROOT / "art" / f"ep{ep}"
    out_dir = ROOT / "out" / f"ep{ep}"
    out_dir.mkdir(parents=True, exist_ok=True)

    wanted = parse_pages(args.pages, len(meta["pages"]))
    for page_def in meta["pages"]:
        if page_def["page"] not in wanted:
            continue
        img = build_page(meta, page_def, art_dir)
        out = out_dir / f"page_{page_def['page']:02d}.png"
        img.save(out)
        print("輸出", out)


if __name__ == "__main__":
    main()
