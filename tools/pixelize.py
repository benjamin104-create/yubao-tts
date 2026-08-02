#!/usr/bin/env python3
"""
把 AI 生成的圖轉成真正可用的像素美術。

為什麼需要這一步：影像模型不會產出 24x24 的圖。你要 24x24 像素風，
它會給你一張 1024x1024、「看起來像」像素風但每個「像素」其實是 42x42 一團、
邊緣還帶抗鋸齒與雜色的圖。直接丟進遊戲會糊掉，而且每張圖的色調都不一樣。

這支工具做三件事：
  1. 切格     —— 一張大圖切成 N 張獨立小圖（sheet 模式）
  2. 降取樣   —— 用區域平均縮到目標尺寸，再硬邊重建
  3. 統一調色 —— 全部量化到同一組固定色盤

第 3 步是讓不同批次生成的圖看起來像同一款遊戲的關鍵。

用法：
    # 單張
    python3 tools/pixelize.py in.png -o godot/assets/items/herb_00.png

    # 一張 4x4 的 sheet 切成 16 張，依序命名
    python3 tools/pixelize.py sheet.png --grid 4x4 \\
        --out-dir godot/assets/items --prefix herb_ --start 0

    # 檢查既有資產是否合規
    python3 tools/pixelize.py --check godot/assets
"""

import argparse
import os
import sys

from PIL import Image

TILE = 24

# 32 色固定色盤。所有資產都量化到這裡 —— 這是把不同批次的生成結果
# 綁成同一種視覺語言最有效的手段，比在提示詞裡描述顏色可靠得多。
PALETTE_HEX = [
    # 石材 / 灰階
    "0d0d12", "1a1a24", "2b2b38", "3d3d4d", "565668", "757589", "c8c8d4",
    # 泥土 / 木頭 / 地板
    "2a1d14", "43301f", "5e442c", "7d5c3c", "9c7850", "bb9668", "ecd3ae",
    # 血 / 火 / 敵意
    "6b1a1e", "9c2b2b", "c94a3a", "e87a4a", "f5a95e",
    # 綠 / 毒 / 自然
    "1e5230", "2f7d45", "4aa85e", "79c97a",
    # 藍 / 魔法 / 冰
    "101c3a", "1d3468", "2f57a0", "4a86cf", "7cb8ea",
    # 金 / 高光
    "6b4a12", "a87a1e", "dcae35", "f5dc7a",
]


def hex_to_rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def build_palette_image():
    pal = Image.new("P", (1, 1))
    flat = []
    for h in PALETTE_HEX:
        flat.extend(hex_to_rgb(h))
    flat.extend([0, 0, 0] * (256 - len(PALETTE_HEX)))
    pal.putpalette(flat)
    return pal


def strip_background(im, tolerance=18):
    """把四角的共同顏色視為背景並轉成透明。

    生成圖多半是不透明的方形。用四角取樣而非固定色鍵，才不會在
    背景色換了一批之後整個失效。
    """
    im = im.convert("RGBA")
    w, h = im.size
    corners = [im.getpixel(p) for p in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1))]
    r = sum(c[0] for c in corners) // 4
    g = sum(c[1] for c in corners) // 4
    b = sum(c[2] for c in corners) // 4

    px = im.load()
    for y in range(h):
        for x in range(w):
            cr, cg, cb, ca = px[x, y]
            if abs(cr - r) <= tolerance and abs(cg - g) <= tolerance \
                    and abs(cb - b) <= tolerance:
                px[x, y] = (cr, cg, cb, 0)
    return im


def pixelize(im, size, palette, keep_bg=False):
    if not keep_bg:
        im = strip_background(im)
    im = im.convert("RGBA")

    # BOX（區域平均）而非 LANCZOS：後者會製造出色盤外的中間色與振鈴，
    # 量化之後變成髒邊
    small = im.resize((size, size), Image.BOX)

    alpha = small.getchannel("A").point(lambda a: 255 if a >= 128 else 0)
    rgb = small.convert("RGB").quantize(palette=palette, dither=Image.NONE)
    out = rgb.convert("RGBA")
    out.putalpha(alpha)
    return out


def split_grid(im, cols, rows):
    w, h = im.size
    cw, ch = w // cols, h // rows
    for r in range(rows):
        for c in range(cols):
            yield im.crop((c * cw, r * ch, (c + 1) * cw, (r + 1) * ch))


def check_assets(root, size):
    palette = {hex_to_rgb(h) for h in PALETTE_HEX}
    problems = 0
    checked = 0
    for dirpath, _, files in os.walk(root):
        for name in sorted(files):
            if not name.endswith(".png"):
                continue
            path = os.path.join(dirpath, name)
            im = Image.open(path).convert("RGBA")
            checked += 1
            w, h = im.size
            rel = os.path.relpath(path, root)

            if h != size or w % size != 0:
                print("  [尺寸] %s 是 %dx%d，應為 %d 的倍數 x %d"
                      % (rel, w, h, size, size))
                problems += 1

            off = {c[:3] for c in im.getdata() if c[3] > 0} - palette
            if off:
                print("  [色盤] %s 有 %d 個色盤外的顏色（例：%s）"
                      % (rel, len(off), list(off)[:3]))
                problems += 1

            if all(c[3] == 255 for c in im.getdata()):
                print("  [透明] %s 完全不透明，背景可能沒去乾淨" % rel)
                problems += 1

    print("檢查 %d 個檔案，%d 個問題" % (checked, problems))
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", nargs="?")
    ap.add_argument("-o", "--out")
    ap.add_argument("--out-dir")
    ap.add_argument("--prefix", default="")
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--grid", help="例如 4x4：把來源切成 4 欄 4 列")
    ap.add_argument("--size", type=int, default=TILE)
    ap.add_argument("--keep-bg", action="store_true")
    ap.add_argument("--check", help="檢查資產目錄是否合規")
    args = ap.parse_args()

    if args.check:
        sys.exit(1 if check_assets(args.check, args.size) else 0)

    if not args.src:
        ap.error("需要來源圖，或用 --check")

    palette = build_palette_image()
    im = Image.open(args.src)

    if args.grid:
        cols, rows = (int(x) for x in args.grid.lower().split("x"))
        out_dir = args.out_dir or "."
        os.makedirs(out_dir, exist_ok=True)
        for i, cell in enumerate(split_grid(im, cols, rows)):
            path = os.path.join(
                out_dir, "%s%02d.png" % (args.prefix, args.start + i))
            pixelize(cell, args.size, palette, args.keep_bg).save(path)
            print("寫出 %s" % path)
    else:
        if not args.out:
            ap.error("單張模式需要 -o")
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        pixelize(im, args.size, palette, args.keep_bg).save(args.out)
        print("寫出 %s" % args.out)


if __name__ == "__main__":
    main()
