# 潔米爸 換裝拆解 — reel generator

Generates `out/jamine_pa_dressing.mp4`: a 720×1280, 30fps, **silent** vertical
reel modelled on the supplied reference clip.

## Structure

| Segment | Time | Content |
|---|---|---|
| Intro | 0.0–5.0s | Charging meter fills, `換裝載入中… → READY`, subject pushes in, title card rises |
| LOOK 01 | 5.0–8.3s | `GLASSES ON` · 日常 · 白T |
| LOOK 02 | 8.3–11.6s | `GLASSES ON` · 出門 · 後背包 |
| LOOK 03 | 11.6–14.9s | `GLASSES OFF` · 正式 · 西裝 (glasses box struck through, `0x`) |
| Outro | 14.9–17.3s | Dimmed final card, Instagram badge, `@i_jamine_pa` |

Segments are separated by horizontal motion-blur wipes, matching the reference.

Each card carries the big title, `DRESSING BREAKDOWN` sub-line, the `潔米爸 換裝拆解`
lead, three numbered accessory boxes that stagger in from the left, and the
subject on the right with a slow push-in.

## Files

- `build_video.py` — layout, timing, transitions, encode
- `icons.py` — the flat product-style accessory icons (glasses, cap, backpack,
  tee, beads, sneakers, blazer, tie, phone, watch)
- `assets/` — background-removed cut-outs: `g1`/`g2` (with glasses), `ng` (without)

## Run

```sh
pip install pillow numpy imageio-ffmpeg
python3 build_video.py
```

`ffmpeg` must be on `PATH` (`imageio-ffmpeg` ships a binary you can symlink).

## Editing

Outfit contents live in the `LOOKS` list in `build_video.py`. Each box holds
`(icon_name, 中文標籤, 貨號, 數量)`; set the quantity to `0x` to strike an item
through, as LOOK 03 does with the glasses. Segment lengths are the `INTRO_F`,
`LOOK_F`, `OUTRO_F` frame counts.

The cut-outs were produced with `rembg` (u2net, alpha matting) from the original
photos and are bottom-faded at render time so they dissolve into the page.
