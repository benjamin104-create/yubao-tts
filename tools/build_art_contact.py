"""Build enlarged contact sheets for pixel-art QA.

The game keeps both static fallback sprites and 10x3 animation atlases.  This
tool shows the first/front idle frame from either format at nearest-neighbour
scale, so silhouette, palette and ground anchors can be reviewed together.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def load_preview(path: Path, cell: int) -> Image.Image:
    source = Image.open(path).convert("RGBA")
    if source.width == cell * 10 and source.height == cell * 3:
        source = source.crop((0, 0, cell, cell))
    box = source.getchannel("A").getbbox()
    if box:
        source = source.crop(box)
    stage = Image.new("RGBA", (cell, cell), (0, 0, 0, 0))
    scale = min((cell - 2) / max(1, source.width), (cell - 1) / max(1, source.height))
    size = (max(1, round(source.width * scale)), max(1, round(source.height * scale)))
    source = source.resize(size, Image.Resampling.NEAREST)
    stage.alpha_composite(source, ((cell - size[0]) // 2, cell - size[1]))
    return stage


def build(src: Path, output: Path, cell: int, columns: int) -> None:
    paths = sorted(src.glob("*.png"))
    if not paths:
        raise SystemExit(f"no PNGs in {src}")
    zoom = 4
    card_w = cell * zoom + 20
    card_h = cell * zoom + 42
    rows = (len(paths) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * card_w, rows * card_h), "#17120f")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for index, path in enumerate(paths):
        x = (index % columns) * card_w
        y = (index // columns) * card_h
        draw.rectangle((x + 4, y + 4, x + card_w - 5, y + card_h - 5), fill="#2b211b", outline="#6d5439")
        preview = load_preview(path, cell).resize((cell * zoom, cell * zoom), Image.Resampling.NEAREST)
        sheet.paste(preview, (x + 10, y + 8), preview)
        draw.text((x + 10, y + cell * zoom + 13), path.stem, font=font, fill="#f0d9ad")
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, optimize=True)
    print(f"{len(paths)} assets -> {output}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--cell", type=int, default=32)
    parser.add_argument("--columns", type=int, default=6)
    args = parser.parse_args()
    build(args.source, args.output, args.cell, args.columns)


if __name__ == "__main__":
    main()
