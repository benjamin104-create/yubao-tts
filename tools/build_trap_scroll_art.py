"""Build production 32px trap and scroll sprites from ImageGen art masters.

The source images are deliberately generated large so their silhouettes and
materials can be art-directed.  This script crops those masters, removes soft
alpha/glow, reduces the palette, and snaps the result back to the project's
hard-edged 32px item specification.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image
from pixelize import ANIM_PALETTE_HEX, PALETTE_HEX, hex_to_rgb, nearest


TRAP_NAMES = ("bear", "poison", "arrow", "plant", "acid")
TRAP_PALETTE = tuple(hex_to_rgb(value) for value in ANIM_PALETTE_HEX)
ITEM_PALETTE = tuple(hex_to_rgb(value) for value in PALETTE_HEX)


def solid_bbox(image: Image.Image, threshold: int = 72) -> tuple[int, int, int, int]:
    alpha = image.getchannel("A")
    mask = alpha.point(lambda value: 255 if value >= threshold else 0)
    return mask.getbbox() or (0, 0, image.width, image.height)


def pixel_finish(
    source: Image.Image,
    size: int,
    palette: tuple[tuple[int, int, int], ...],
    side_pad: int = 1,
    bottom_pad: int = 0,
) -> Image.Image:
    source = source.convert("RGBA")
    box = solid_bbox(source)
    source = source.crop(box)
    limit_w = size - side_pad * 2
    limit_h = size - bottom_pad
    scale = min(limit_w / source.width, limit_h / source.height)
    width = max(1, round(source.width * scale))
    height = max(1, round(source.height * scale))

    # BOX preserves large ImageGen pixel clusters while collapsing their scale.
    source = source.resize((width, height), Image.Resampling.BOX)
    alpha = source.getchannel("A").point(lambda value: 255 if value >= 64 else 0)
    reduced = source.quantize(colors=18, method=Image.Quantize.FASTOCTREE).convert("RGBA")
    reduced.putalpha(alpha)
    snapped = []
    for red, green, blue, opacity in reduced.getdata():
        if not opacity:
            snapped.append((0, 0, 0, 0))
            continue
        nr, ng, nb = nearest((red, green, blue), palette)
        snapped.append((nr, ng, nb, 255))
    reduced.putdata(snapped)

    output = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    x = (size - width) // 2
    y = size - bottom_pad - height
    output.alpha_composite(reduced, (x, y))
    return output


def build_traps(source_path: Path, output_dir: Path) -> None:
    sheet = Image.open(source_path).convert("RGBA")
    cell_w, cell_h = sheet.width // 3, sheet.height // 2
    # ImageGen order: poison, arrow, bear / plant, acid, blank.
    cells = {
        "poison": (0, 0),
        "arrow": (1, 0),
        "bear": (2, 0),
        "plant": (0, 1),
        "acid": (1, 1),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    for name in TRAP_NAMES:
        col, row = cells[name]
        crop = sheet.crop((col * cell_w, row * cell_h, (col + 1) * cell_w, (row + 1) * cell_h))
        sprite = pixel_finish(crop, 32, TRAP_PALETTE)
        # 紫色機關必須在暗地板上保有一塊讀得出的受光面，不可只剩暗紫外框。
        if name in {"acid", "bear"}:
            px = sprite.load()
            box = sprite.getchannel("A").getbbox()
            if box:
                candidates = [
                    (x, y)
                    for y in range(box[1], min(box[3], box[1] + 8))
                    for x in range(box[0], min(box[2], box[0] + 12))
                    if px[x, y][3] and px[x, y][:3] != hex_to_rgb("0d0d12")
                ]
                highlight = "e8edf4" if name == "acid" else "c8c8d4"
                for x, y in candidates[:3]:
                    px[x, y] = (*hex_to_rgb(highlight), 255)
        sprite.save(output_dir / f"{name}.png", optimize=True)


def build_scroll(source_path: Path, output_path: Path) -> None:
    source = Image.open(source_path).convert("RGBA")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pixel_finish(source, 32, ITEM_PALETTE).save(output_path, optimize=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--traps", type=Path, required=True)
    parser.add_argument("--scroll", type=Path, required=True)
    parser.add_argument("--trap-output", type=Path, required=True)
    parser.add_argument("--scroll-output", type=Path, required=True)
    args = parser.parse_args()
    build_traps(args.traps, args.trap_output)
    build_scroll(args.scroll, args.scroll_output)


if __name__ == "__main__":
    main()
