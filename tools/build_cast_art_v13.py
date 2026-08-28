#!/usr/bin/env python3
"""Build the v13 unified character/item art pass.

This pass deliberately keeps the established monster, boss and equipment
silhouettes.  Their animation timing and authored pixels are already part of
the game language; replacing them wholesale would make the cast unfamiliar.
Instead it applies one palette-closed lighting finish to every frame:

* top/left planes gain a compact highlight cluster;
* bottom/right planes retain a readable shadow step;
* the near-black outline and fully transparent background are preserved;
* no antialiasing or colours outside the project's closed palette are added.

The village cast is the one category that genuinely needed new source art.
It is cut from the retained ImageGen master, reduced to 48px, palette-closed,
and grounded with the same four-foot body language as the 48px hero.

By default files are written to work/v13-art-preview for visual QA.  Pass
--apply only after reviewing those contacts to replace web/art assets.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from PIL import Image, ImageDraw

from pixelize import ANIM_PALETTE_HEX, PALETTE_HEX, hex_to_rgb, pixelize, strip_background


ROOT = Path(__file__).resolve().parent.parent
WEB_ART = ROOT / "web" / "art"
MASTER = ROOT / "art_raw" / "concepts" / "village-cast-v13" / "village-cast-imagegen-master.png"
MIND_ECHO_MASTER = ROOT / "art_raw" / "b_mind2-source.png"
PREVIEW = ROOT / "work" / "v13-art-preview"

OUTLINE = hex_to_rgb("0d0d12")
BASE_COLOURS = {hex_to_rgb(c) for c in PALETTE_HEX}
ANIM_COLOURS = {hex_to_rgb(c) for c in ANIM_PALETTE_HEX}

# Ordered material ramps.  All entries already belong to ANIM_PALETTE_HEX.
# The ordering is the only information the finishing pass needs: move one
# step toward light at the top/left and one step toward shadow at bottom/right.
RAMP_HEX = (
    ("1a1a24", "2b2b38", "3d3d4d", "565668", "757589", "c8c8d4", "e8edf4", "f7f5eb"),
    ("2a1d14", "43301f", "5e442c", "7d5c3c", "9c7850", "bb9668", "ecd3ae", "f7f5eb"),
    ("6b1a1e", "9c2b2b", "c94a3a", "e87a4a", "f5a95e", "f7f5eb"),
    ("1e5230", "2f7d45", "4aa85e", "79c97a", "a5ebeb"),
    ("101c3a", "1d3468", "2f57a0", "4a86cf", "7cb8ea", "a5ebeb", "e8edf4"),
    ("6b4a12", "a87a1e", "dcae35", "f5dc7a", "f7f5eb"),
    ("1d6475", "2f90a6", "58c2cf", "a5ebeb", "e8edf4"),
    ("382044", "573060", "75407f", "a85aaa", "d978c4", "f2b2df", "f7f5eb"),
)
RAMPS = [[hex_to_rgb(c) for c in ramp] for ramp in RAMP_HEX]
STEP = {colour: (ramp, index) for ramp in RAMPS for index, colour in enumerate(ramp)}


def alpha_at(px, x: int, y: int, w: int, h: int) -> int:
    return px[x, y][3] if 0 <= x < w and 0 <= y < h else 0


def colour_at(px, x: int, y: int, w: int, h: int):
    return px[x, y][:3] if 0 <= x < w and 0 <= y < h and px[x, y][3] else None


def ramp_step(ramp, index: int, direction: int, allowed) -> tuple[int, int, int]:
    """Move at most one authored value step, without escaping this category palette."""
    target = index + direction
    if 0 <= target < len(ramp) and ramp[target] in allowed:
        return ramp[target]
    return ramp[index]


def finish_frame(frame: Image.Image, strength: int = 1, allowed=ANIM_COLOURS) -> Image.Image:
    """Add compact directional light/shadow clusters without changing shape."""
    source = frame.convert("RGBA")
    out = source.copy()
    src = source.load()
    dst = out.load()
    w, h = source.size
    bbox = source.getchannel("A").getbbox()
    if not bbox:
        return out
    x0, y0, x1, y1 = bbox

    def dark_outline(x, y):
        c = colour_at(src, x, y, w, h)
        return c == OUTLINE

    for y in range(y0, y1):
        for x in range(x0, x1):
            rgba = src[x, y]
            if rgba[3] == 0 or rgba[:3] == OUTLINE or rgba[:3] not in STEP:
                continue
            ramp, index = STEP[rgba[:3]]
            if len(ramp) < 3:
                continue

            # The visible colour immediately inside a north/west outline is a
            # genuine surface plane, not a glow.  Promote only small clusters
            # that still have material to their right/below, so eyes, cracks
            # and single-pixel markings are not accidentally repainted.
            nw_outline = dark_outline(x - 1, y) or dark_outline(x, y - 1)
            nw_air = alpha_at(src, x - 2, y, w, h) == 0 or alpha_at(src, x, y - 2, w, h) == 0
            supported = (colour_at(src, x + 1, y, w, h) in ramp or
                         colour_at(src, x, y + 1, w, h) in ramp)

            # Conversely, keep a deliberate lower-right dark plane.  This is
            # especially important on shields, armour and large bosses where
            # a flat midtone is what made the old art feel pasted on.
            se_outline = dark_outline(x + 1, y) or dark_outline(x, y + 1)
            se_air = alpha_at(src, x + 2, y, w, h) == 0 or alpha_at(src, x, y + 2, w, h) == 0
            backed = (colour_at(src, x - 1, y, w, h) in ramp or
                      colour_at(src, x, y - 1, w, h) in ramp)

            if supported and (nw_outline or (strength > 1 and nw_air)) and index < len(ramp) - 1:
                dst[x, y] = (*ramp_step(ramp, index, 1, allowed), 255)
            elif backed and (se_outline or (strength > 1 and se_air)) and index > 0:
                dst[x, y] = (*ramp_step(ramp, index, -1, allowed), 255)

    return out


def finish_sheet(source: Image.Image, cell: int, strength: int, allowed=ANIM_COLOURS) -> Image.Image:
    source = source.convert("RGBA")
    if source.width % cell or source.height % cell:
        raise ValueError(f"{source.size} is not divisible by {cell}px cells")
    out = Image.new("RGBA", source.size, (0, 0, 0, 0))
    for y in range(0, source.height, cell):
        for x in range(0, source.width, cell):
            frame = source.crop((x, y, x + cell, y + cell))
            out.alpha_composite(finish_frame(frame, strength, allowed), (x, y))
    return out


def ensure_four_feet(sprite: Image.Image) -> Image.Image:
    """Normalize the species read: two arms, four short feet at ground level.

    Image generation is excellent at costume identity but inconsistent at
    tiny repeated appendages.  At 48px we reserve four separated 3px foot pads
    along the grounded body edge.  The pads borrow the local body/shadow hues,
    so this is a pixel correction, not an added generic symbol.
    """
    im = sprite.convert("RGBA")
    a = im.getchannel("A")
    bbox = a.getbbox()
    if not bbox:
        return im
    x0, y0, x1, y1 = bbox
    px = im.load()
    ground = min(47, y1 - 1)

    # Find a representative body midtone and its darker ramp neighbour.
    colours = {}
    for y in range(max(y0, ground - 15), ground + 1):
        for x in range(x0, x1):
            c = px[x, y]
            if c[3] and c[:3] != OUTLINE:
                colours[c[:3]] = colours.get(c[:3], 0) + 1
    body = max(colours, key=colours.get) if colours else hex_to_rgb("7d5c3c")
    ramp_index = STEP.get(body)
    shadow = ramp_index[0][max(0, ramp_index[1] - 1)] if ramp_index else hex_to_rgb("43301f")

    # Remove only the last three rows inside the central body span.  Arms and
    # costume hems are above this band; the operation is therefore stable for
    # cane, hammer, sack and tablet silhouettes.
    centre = (x0 + x1 - 1) / 2
    span = max(14, min(28, x1 - x0 - 6))
    left = int(round(centre - span / 2))
    right = int(round(centre + span / 2))
    for y in range(max(0, ground - 2), min(48, ground + 1)):
        for x in range(max(0, left), min(48, right + 1)):
            px[x, y] = (0, 0, 0, 0)

    # Four distinct feet; outer pair sit a pixel higher to suggest 3/4 depth.
    centres = [left + 3, left + 8, right - 8, right - 3]
    for i, cx in enumerate(centres):
        top = ground - (1 if i in (0, 3) else 0)
        for yy in range(top - 2, top + 1):
            for xx in range(cx - 2, cx + 2):
                if 0 <= xx < 48 and 0 <= yy < 48:
                    edge = xx in (cx - 2, cx + 1) or yy == top
                    px[xx, yy] = (*OUTLINE, 255) if edge else (*shadow, 255)
        # One lit top-left pixel keeps the feet dimensional at mobile size.
        if 0 <= cx - 1 < 48 and 0 <= top - 1 < 48:
            px[cx - 1, top - 1] = (*body, 255)
    return im


def build_villagers(out_root: Path) -> None:
    if not MASTER.is_file():
        raise SystemExit(f"missing retained village source: {MASTER}")
    source = Image.open(MASTER).convert("RGB")
    cols, rows = 3, 2
    cell_w, cell_h = source.width // cols, source.height // rows
    names = ("elder", "smith", "merchant", "child", "chief", "mason")
    target = out_root / "npc"
    target.mkdir(parents=True, exist_ok=True)
    palette = tuple(hex_to_rgb(c) for c in ANIM_PALETTE_HEX)
    for index, name in enumerate(names):
        gx, gy = index % cols, index // cols
        cut = source.crop((gx * cell_w, gy * cell_h, (gx + 1) * cell_w, (gy + 1) * cell_h))
        # Flood-fill stripping preserves enclosed eye whites while removing the
        # pure white cell background.
        cut = strip_background(cut)
        sprite = pixelize(cut, 48, palette=palette, trim=True, headroom=.06, pad=.08)
        sprite = ensure_four_feet(sprite)
        sprite = finish_frame(sprite, strength=2)
        sprite.save(target / f"{name}.png", optimize=True)


def build_gold(out_root: Path) -> None:
    """Draw a readable 32px gold pickup: two ingots plus loose ancient coins."""
    im = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    ink = hex_to_rgb("2a1d14") + (255,)
    deep = hex_to_rgb("6b4a12") + (255,)
    mid = hex_to_rgb("a87a1e") + (255,)
    gold = hex_to_rgb("dcae35") + (255,)
    hi = hex_to_rgb("f5dc7a") + (255,)

    def ingot(x, y, w=13):
        # dark bottom/right, broad midtone body, and a whole lit top plane
        d.polygon([(x, y + 4), (x + 3, y), (x + w - 3, y), (x + w, y + 4),
                   (x + w, y + 9), (x, y + 9)], fill=ink)
        d.polygon([(x + 2, y + 4), (x + 4, y + 2), (x + w - 4, y + 2),
                   (x + w - 2, y + 4)], fill=hi)
        d.rectangle((x + 2, y + 5, x + w - 3, y + 7), fill=gold)
        d.rectangle((x + 3, y + 8, x + w - 2, y + 8), fill=deep)
        d.point((x + 4, y + 3), fill=hi)

    ingot(5, 14, 14)
    ingot(13, 9, 14)

    def coin(cx, cy):
        d.ellipse((cx - 4, cy - 3, cx + 4, cy + 3), fill=ink)
        d.ellipse((cx - 3, cy - 2, cx + 3, cy + 2), fill=gold)
        d.rectangle((cx - 2, cy - 2, cx + 1, cy - 1), fill=hi)
        d.rectangle((cx + 2, cy, cx + 3, cy + 1), fill=mid)
        d.point((cx, cy), fill=deep)

    coin(9, 24)
    coin(21, 23)
    target = out_root / "item"
    target.mkdir(parents=True, exist_ok=True)
    im.save(target / "gold00.png", optimize=True)


def build_mind_echo(out_root: Path) -> None:
    """Restore the missing nineteenth boss from its retained unique master.

    The game table has three Consciousness phases, but phase two had no
    48px/static or 10x3 asset and silently fell back to a 16px program sprite.
    The retained source already depicts the intended echoing split-body form;
    crop the central identity and author restrained motion without inventing a
    different boss.
    """
    if not MIND_ECHO_MASTER.is_file():
        raise SystemExit(f"missing Consciousness Echo source: {MIND_ECHO_MASTER}")
    master = Image.open(MIND_ECHO_MASTER).convert("RGB")
    # Isolate the central copy; the two side copies in the concept describe
    # the skill effect, not three permanent bodies in every animation frame.
    cut = master.crop((420, 42, 1115, 900))
    palette = tuple(hex_to_rgb(c) for c in ANIM_PALETTE_HEX)
    base = pixelize(strip_background(cut), 48, palette=palette, trim=True, headroom=.06, pad=.08)
    base = finish_frame(base, strength=2, allowed=ANIM_COLOURS)

    boss_dir = out_root / "boss"
    boss_dir.mkdir(parents=True, exist_ok=True)
    base.save(boss_dir / "b_mind2.png", optimize=True)

    def anchored_resize(im: Image.Image, width: int, height: int, dx: int = 0, dy: int = 0) -> Image.Image:
        bb = im.getchannel("A").getbbox()
        if not bb:
            return im.copy()
        cut2 = im.crop(bb).resize((max(1, width), max(1, height)), Image.Resampling.NEAREST)
        stage = Image.new("RGBA", (48, 48), (0, 0, 0, 0))
        x = (48 - cut2.width) // 2 + dx
        y = 47 - cut2.height + dy
        stage.alpha_composite(cut2, (x, y))
        return stage

    bb = base.getchannel("A").getbbox()
    bw, bh = bb[2] - bb[0], bb[3] - bb[1]
    frames = []
    for col in range(10):
        if col == 0: frame = anchored_resize(base, bw, bh)
        elif col == 1: frame = anchored_resize(base, bw, bh, dy=-1)          # breath
        elif col == 2: frame = anchored_resize(base, bw, bh, dx=-1)          # ripple left
        elif col == 3: frame = anchored_resize(base, bw + 1, bh - 2)         # compress
        elif col == 4: frame = anchored_resize(base, bw, bh, dx=1)           # ripple right
        elif col == 5: frame = anchored_resize(base, bw - 1, bh - 1)
        elif col == 6: frame = anchored_resize(base, bw + 2, bh - 4)         # gather copies
        elif col == 7: frame = anchored_resize(base, min(46, bw + 5), min(47, bh + 3), dy=-1)  # echo burst
        elif col == 8: frame = anchored_resize(base, bw + 2, bh, dx=2)       # recoil
        else:
            # Hurt frame: upper body recoils while the lowest eight rows keep
            # the common ground anchor.  This reads as a hit, not teleporting.
            frame = anchored_resize(base, bw, bh)
            top = frame.crop((0, 0, 48, 40))
            frame.paste((0, 0, 0, 0), (0, 0, 48, 40))
            frame.alpha_composite(top, (2, 1))
        frames.append(finish_frame(frame, strength=1, allowed=ANIM_COLOURS))

    sheet = Image.new("RGBA", (480, 144), (0, 0, 0, 0))
    for row in range(3):
        for col, frame in enumerate(frames):
            # The form is deliberately near-symmetrical and has no physical
            # back; direction is communicated by movement/attack, not a fake
            # costume turn that would change its identity.
            sheet.alpha_composite(frame, (col * 48, row * 48))
    anim_dir = out_root / "anim" / "boss"
    anim_dir.mkdir(parents=True, exist_ok=True)
    sheet.save(anim_dir / "b_mind2.png", optimize=True)


def build_existing(out_root: Path) -> None:
    jobs = (
        ("anim/mon", 32, 1, ANIM_COLOURS),
        ("anim/boss", 48, 1, ANIM_COLOURS),
        ("anim/weapon", 32, 2, ANIM_COLOURS),
        ("anim/shield", 32, 2, ANIM_COLOURS),
        ("mon", 32, 1, BASE_COLOURS),
        ("boss", 48, 1, ANIM_COLOURS),
        ("item", 32, 2, BASE_COLOURS),
    )
    for rel, cell, strength, allowed in jobs:
        source_dir = WEB_ART / rel
        target_dir = out_root / rel
        target_dir.mkdir(parents=True, exist_ok=True)
        for path in sorted(source_dir.glob("*.png")):
            # gold is newly authored below; don't copy a stale version on top.
            if path.name == "gold00.png":
                continue
            im = Image.open(path).convert("RGBA")
            finished = finish_sheet(im, cell, strength, allowed)
            finished.save(target_dir / path.name, optimize=True)


def copy_into_web(preview: Path) -> None:
    for path in preview.rglob("*.png"):
        rel = path.relative_to(preview)
        target = WEB_ART / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="replace web/art after building the preview")
    parser.add_argument("--output", type=Path, default=PREVIEW)
    args = parser.parse_args()
    output = args.output.resolve()
    if output == WEB_ART.resolve():
        raise SystemExit("build to a preview directory; use --apply after QA")
    if output.exists():
        shutil.rmtree(output)
    build_existing(output)
    build_mind_echo(output)
    build_villagers(output)
    build_gold(output)
    print(f"v13 preview built: {output}")
    if args.apply:
        copy_into_web(output)
        print(f"v13 art applied to: {WEB_ART}")


if __name__ == "__main__":
    main()
