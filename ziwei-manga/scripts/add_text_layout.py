#!/usr/bin/env python3
"""
add_text_layout.py — 後製：把中文（標題／對白／命盤宮位名）疊到生成好的圖上。

為什麼需要它：
    AI 不生成中文（避免錯字、避免命盤宮位順序錯亂）。
    所有中文都在這一步用程式精準疊上，文字正確、順序正確、教學不誤導。

用法：
    python scripts/add_text_layout.py page01_cover            # 預設用 _v1 + layouts/page01_cover.json
    python scripts/add_text_layout.py page05_fourteen_stars --version 2
    python scripts/add_text_layout.py page04_life_map --layout layouts/page04_life_map.json

輸出：outputs/<stem>_v<version>_final.png

layout JSON 結構（boxes 為文字框陣列）：
{
  "boxes": [
    {
      "text": "潔米爸的占驗派紫微斗數",
      "xy": [80, 120],          // 左上座標（像素）
      "size": 72,                // 字級
      "color": "#d8b061",        // 文字色
      "max_width": 600,           // (選填) 超過就自動換行
      "line_spacing": 1.2,        // (選填) 行距倍率
      "stroke": 4,                // (選填) 描邊粗細
      "stroke_color": "#10142b",  // (選填) 描邊色
      "align": "left",            // (選填) left/center/right
      "bubble": {                 // (選填) 對白框底：圓角矩形
        "pad": 24, "radius": 28,
        "fill": "#f3e7c9", "outline": "#10142b", "outline_w": 3
      }
    }
  ]
}
"""
import os
import json
import argparse
import pathlib

from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUTPUTS = ROOT / "outputs"
LAYOUTS = ROOT / "layouts"
load_dotenv(ROOT / ".env")

# 可能的 CJK 字型候選（找得到哪個用哪個）；建議在 .env 設 CJK_FONT_PATH 指定。
FONT_CANDIDATES = [
    os.getenv("CJK_FONT_PATH", ""),
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "C:/Windows/Fonts/msjh.ttc",
    "/usr/share/fonts/truetype/arphic/uming.ttc",
]


def find_font_path() -> str:
    for c in FONT_CANDIDATES:
        if c and pathlib.Path(c).exists():
            return c
    raise SystemExit(
        "找不到中文字型。請在 .env 設定 CJK_FONT_PATH=（指向一個 .ttc/.otf/.ttf CJK 字型）。\n"
        "建議：思源黑體 Noto Sans CJK、教育部正楷體、或系統內建黑體。"
    )


def load_font(size: int):
    path = find_font_path()
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        # .ttc 多字重時指定 index
        return ImageFont.truetype(path, size, index=0)


def wrap_text(text, font, max_width, draw):
    """中文逐字斷行（無空白也能換行）。"""
    if not max_width:
        return text.split("\n")
    lines = []
    for raw in text.split("\n"):
        line = ""
        for ch in raw:
            test = line + ch
            w = draw.textlength(test, font=font)
            if w > max_width and line:
                lines.append(line)
                line = ch
            else:
                line = test
        lines.append(line)
    return lines


def draw_box(img, draw, box):
    size = int(box.get("size", 40))
    font = load_font(size)
    text = box["text"]
    x, y = box["xy"]
    color = box.get("color", "#f3e7c9")
    align = box.get("align", "left")
    line_spacing = float(box.get("line_spacing", 1.2))
    max_width = box.get("max_width")

    lines = wrap_text(text, font, max_width, draw)
    line_h = int(size * line_spacing)
    text_w = max((draw.textlength(ln, font=font) for ln in lines), default=0)
    text_h = line_h * len(lines)

    # 對白框底
    bubble = box.get("bubble")
    if bubble:
        pad = bubble.get("pad", 20)
        radius = bubble.get("radius", 24)
        rect = [x - pad, y - pad, x + text_w + pad, y + text_h + pad]
        draw.rounded_rectangle(
            rect, radius=radius,
            fill=bubble.get("fill", "#f3e7c9"),
            outline=bubble.get("outline"),
            width=bubble.get("outline_w", 0),
        )
        if bubble.get("fill") and color in ("#f3e7c9", "#fff", "#ffffff"):
            color = "#10142b"  # 淺底自動轉深色字

    stroke = int(box.get("stroke", 0))
    stroke_color = box.get("stroke_color", "#10142b")

    cy = y
    for ln in lines:
        lw = draw.textlength(ln, font=font)
        if align == "center":
            lx = x + (text_w - lw) / 2
        elif align == "right":
            lx = x + (text_w - lw)
        else:
            lx = x
        draw.text((lx, cy), ln, font=font, fill=color,
                  stroke_width=stroke, stroke_fill=stroke_color)
        cy += line_h


def apply_layout(stem: str, version: int, layout_path: pathlib.Path):
    src = OUTPUTS / f"{stem}_v{version}.png"
    if not src.exists():
        raise SystemExit(f"找不到圖片：{src}（請先生成）")
    if not layout_path.exists():
        raise SystemExit(
            f"找不到 layout：{layout_path}\n"
            f"可參考 layouts/page01_cover.json 自行建立。"
        )

    layout = json.loads(layout_path.read_text(encoding="utf-8"))
    img = Image.open(src).convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    for box in layout.get("boxes", []):
        draw_box(img, draw, box)

    out_img = Image.alpha_composite(img, overlay).convert("RGB")
    out = OUTPUTS / f"{stem}_v{version}_final.png"
    out_img.save(out)
    print(f"✓ 後製完成：{out}")
    return out


def main():
    ap = argparse.ArgumentParser(description="後製疊中文字")
    ap.add_argument("page", help="頁面名，如 page01_cover")
    ap.add_argument("--version", type=int, default=1, help="要上字的版本（預設 v1）")
    ap.add_argument("--layout", default=None, help="layout JSON 路徑（預設 layouts/<page>.json）")
    args = ap.parse_args()

    stem = args.page[:-3] if args.page.endswith(".md") else args.page
    layout_path = pathlib.Path(args.layout) if args.layout else (LAYOUTS / f"{stem}.json")
    apply_layout(stem, args.version, layout_path)


if __name__ == "__main__":
    main()
