# 潔米爸 換裝拆解 — reel generator

Generates `out/jamine_pa_dressing.mp4`: a 720×1280, 30fps, **silent** vertical
reel modelled on the supplied reference clip.

## Structure

| Segment | Time | Content |
|---|---|---|
| Intro | 0.0–5.0s | Charging meter fills, `換裝載入中… → READY`, subject pushes in, title card rises |
| LOOK 01 | 5.0–8.3s | `GLASSES ON` · 日常 · 白T |
| LOOK 02 | 8.3–11.6s | `GLASSES ON` · 出門 · 後背包 |
| LOOK 03 | 11.6–17.2s | `GLASSES OFF` · 正式 · 西裝 — full body, turning FRONT → 45° → SIDE → BACK |
| Outro | 17.2–19.6s | Dimmed final card, Instagram badge, `@i_jamine_pa` |

Segments are separated by horizontal motion-blur wipes, matching the reference.

Each card carries the big title, `DRESSING BREAKDOWN` sub-line, the `潔米爸 換裝拆解`
lead, three numbered accessory boxes that stagger in from the left, and the
subject on the right with a slow push-in.

## Files

- `build_video.py` — layout, timing, transitions, encode
- `icons.py` — the flat product-style accessory icons (glasses, cap, backpack,
  tee, beads, sneakers, blazer, tie, phone, watch)
- `extract_sheet.py` — pulls the four full-body views off the character model sheet
- `relight.py` — the studio relight applied to every cut-out
- `assets/` — `g1`/`g2` (chest-up, with glasses), `ng` (without), `model_sheet.png`,
  and `body_{front,a45,side,back}.png` extracted from it

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

The chest-up cut-outs come from `rembg` (u2net, alpha matting) and are
bottom-faded at render time so they dissolve into the page.

The full-body views are cut from the model sheet by `extract_sheet.py`. That one
needs `isnet-general-use` rather than `u2net`: the suit is near-black against a
near-black navy card, and u2net swallows the card between the ankles into the
silhouette (gap opacity 209/255, versus 114 for isnet; `u2net_human_seg` is worse
at 254). No threshold tuning fixes that — the jacket sits at (24,24,32) and the
card at (14,22,38), barely 12 apart in RGB, so any key tight enough to clear the
gap also eats the trousers. Picking the right segmentation model does fix it.

Only LOOK 03 has full-body views, because the model sheet only covers the suit.
LOOKS 01 and 02 stay chest-up until sheets exist for those outfits.
