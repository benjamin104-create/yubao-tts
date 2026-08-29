"""Split three generated storyboard atlases and clean the shared hero cutout.

Usage:
  python tools/import_chapter_preludes.py ATLAS_1 ATLAS_2 ATLAS_3 HERO

The source atlases are 2 x 3 contact sheets.  Each panel is centre-cropped to
the same 3:2 frame as the existing prologue, then exported as a lightweight
progressive JPEG.  The hero generator occasionally paints a pale checkerboard
instead of real alpha; the border-connected checkerboard is removed here while
preserving the pale sword and eyes inside the outlined character.
"""

from collections import deque
from pathlib import Path
import sys

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "web" / "art" / "promo"


def panel_box(width, height, col, row):
    x0 = round(width * col / 2)
    x1 = round(width * (col + 1) / 2)
    y0 = round(height * row / 3)
    y1 = round(height * (row + 1) / 3)
    # Leave the atlas gutter outside the crop.
    if col:
        x0 += 3
    else:
        x1 -= 3
    if row:
        y0 += 3
    else:
        y1 -= 3
    if row < 2:
        y1 -= 3
    pw, ph = x1 - x0, y1 - y0
    want = round(ph * 1.5)
    left = x0 + max(0, (pw - want) // 2)
    return left, y0, min(x1, left + want), y1


def split_atlas(path, first):
    src = Image.open(path).convert("RGB")
    for row in range(3):
        for col in range(2):
            number = first + row * 2 + col
            crop = src.crop(panel_box(*src.size, col, row))
            crop = crop.resize((1200, 800), Image.Resampling.LANCZOS)
            target = OUT / f"chapter-charcoal-{number:02d}-v1.jpg"
            crop.save(target, "JPEG", quality=83, optimize=True, progressive=True,
                      subsampling="4:2:0")
            print(target.relative_to(ROOT), target.stat().st_size)


def transparent_hero(path):
    im = Image.open(path).convert("RGBA")
    w, h = im.size
    pix = im.load()
    seen = bytearray(w * h)
    q = deque()

    def pale(x, y):
        r, g, b, _ = pix[x, y]
        return min(r, g, b) >= 208 and max(r, g, b) - min(r, g, b) <= 30

    for x in range(w):
        for y in (0, h - 1):
            if pale(x, y):
                seen[y * w + x] = 1
                q.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            if pale(x, y) and not seen[y * w + x]:
                seen[y * w + x] = 1
                q.append((x, y))
    while q:
        x, y = q.popleft()
        pix[x, y] = (*pix[x, y][:3], 0)
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if 0 <= nx < w and 0 <= ny < h:
                i = ny * w + nx
                if not seen[i] and pale(nx, ny):
                    seen[i] = 1
                    q.append((nx, ny))

    alpha = im.getchannel("A")
    box = alpha.getbbox()
    if not box:
        raise SystemExit("hero background removal erased the whole image")
    im = im.crop(box)
    scale = min(1, 430 / im.width, 405 / im.height)
    im = im.resize((round(im.width * scale), round(im.height * scale)),
                   Image.Resampling.LANCZOS)
    target = OUT / "chapter-charcoal-hero-v1.png"
    im.save(target, "PNG", optimize=True)
    print(target.relative_to(ROOT), target.stat().st_size, im.size)


def main():
    if len(sys.argv) != 5:
        raise SystemExit("pass three atlas paths and one hero path")
    OUT.mkdir(parents=True, exist_ok=True)
    for i, src in enumerate(sys.argv[1:4]):
        split_atlas(src, 1 + i * 6)
    transparent_hero(sys.argv[4])


if __name__ == "__main__":
    main()
