#!/usr/bin/env python3
"""
把 play_demo.gd 錄下的逐回合畫面組成動畫 GIF 與接觸表。

用法：
    python3 tools/make_demo_media.py <frames_dir> <out_dir> [--key 0,4,17,...]

GIF 是回合制遊戲最適合的展示格式 —— 每一格就是一個回合，
播放速度直接反映「玩家按一次、世界動一次」的節奏。
"""

import argparse
import os
import sys
from PIL import Image


def load_frames(src: str):
    names = sorted(f for f in os.listdir(src) if f.endswith(".png"))
    if not names:
        sys.exit("找不到任何 PNG：%s" % src)
    return [(n, os.path.join(src, n)) for n in names]


def build_gif(frames, out_path: str, scale: float, fps: float, max_colors: int):
    imgs = []
    for _, path in frames:
        im = Image.open(path).convert("RGB")
        w, h = im.size
        im = im.resize((int(w * scale), int(h * scale)), Image.NEAREST)
        # NEAREST 而非 LANCZOS：這是像素網格畫面，插值只會把格線糊掉
        imgs.append(im.quantize(colors=max_colors, method=Image.MEDIANCUT))

    duration = int(1000.0 / fps)
    imgs[0].save(
        out_path,
        save_all=True,
        append_images=imgs[1:],
        duration=duration,
        loop=0,
        optimize=True,
        disposal=2,
    )
    return out_path


def build_contact_sheet(frames, indices, out_path: str, cols: int, cell_w: int):
    picked = []
    for i in indices:
        if 0 <= i < len(frames):
            picked.append(frames[i][1])
    if not picked:
        return None

    sample = Image.open(picked[0])
    ratio = sample.size[1] / sample.size[0]
    cell_h = int(cell_w * ratio)
    rows = (len(picked) + cols - 1) // cols
    pad = 6

    sheet = Image.new(
        "RGB",
        (cols * cell_w + (cols + 1) * pad, rows * cell_h + (rows + 1) * pad),
        (18, 18, 22),
    )
    for idx, path in enumerate(picked):
        im = Image.open(path).convert("RGB").resize((cell_w, cell_h), Image.NEAREST)
        r, c = divmod(idx, cols)
        sheet.paste(im, (pad + c * (cell_w + pad), pad + r * (cell_h + pad)))
    sheet.save(out_path)
    return out_path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--key", default="")
    ap.add_argument("--scale", type=float, default=0.5)
    ap.add_argument("--fps", type=float, default=7.0)
    ap.add_argument("--colors", type=int, default=96)
    ap.add_argument("--cols", type=int, default=3)
    ap.add_argument("--cell", type=int, default=420)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    frames = load_frames(args.src)
    print("讀入 %d 張畫面" % len(frames))

    gif = build_gif(
        frames, os.path.join(args.out, "gameplay.gif"),
        args.scale, args.fps, args.colors)
    print("GIF  : %s（%.1f MB）" % (gif, os.path.getsize(gif) / 1e6))

    if args.key:
        idxs = [int(x) for x in args.key.split(",") if x.strip()]
        sheet = build_contact_sheet(
            frames, idxs, os.path.join(args.out, "moments.png"),
            args.cols, args.cell)
        if sheet:
            print("接觸表: %s（%.1f MB）" % (sheet, os.path.getsize(sheet) / 1e6))


if __name__ == "__main__":
    main()
