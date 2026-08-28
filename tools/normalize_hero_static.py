"""Normalize the 32px static hero to the equipment anchor and ground line.

The animated hero uses 48px cells, while the inventory/preview fallback is a
32px still.  Cropping the whole 48px cell to 32px made that still too small and
left its head below every hat anchor.  This keeps the four feet and side hands,
but fits the actual silhouette between y=8 and the ground line at y=31.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


def normalize(source_path: Path, output_path: Path) -> None:
    source = Image.open(source_path).convert("RGBA")
    box = source.getchannel("A").getbbox()
    if not box:
        raise SystemExit(f"empty hero image: {source_path}")
    subject = source.crop(box)
    scale = min(30 / subject.width, 24 / subject.height)
    width = max(1, round(subject.width * scale))
    height = max(1, round(subject.height * scale))
    subject = subject.resize((width, height), Image.Resampling.NEAREST)
    alpha = subject.getchannel("A").point(lambda value: 255 if value >= 128 else 0)
    subject.putalpha(alpha)

    output = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    output.alpha_composite(subject, ((32 - width) // 2, 32 - height))

    # Keep the bright top-left plane, and add the contract's #d97757 body tone
    # to the lower/right plane.  It is both the readable shadow step and the
    # colour-replacement anchor used by the selectable hero palettes.
    pixels = output.load()
    for y in range(32):
        for x in range(32):
            if pixels[x, y][:3] == (232, 122, 74) and (x >= 16 or y >= 21):
                pixels[x, y] = (217, 119, 87, pixels[x, y][3])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output.save(output_path, optimize=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    normalize(args.source, args.output)


if __name__ == "__main__":
    main()
