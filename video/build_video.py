"""Build the "潔米爸 換裝拆解" vertical reel.

Layout and pacing follow the reference clip: a charging-meter intro, then a run
of outfit-breakdown cards (big title, numbered accessory grid on the left, the
subject on the right), each separated by a horizontal motion-blur wipe, closing
on a dimmed frame with the handle.

Output: 720x1280, 30fps, silent H.264.
"""

import math
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

import icons
import relight

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")
OUT = os.path.join(HERE, "out", "jamine_pa_dressing.mp4")

W, H = 720, 1280
FPS = 30
BG = (255, 255, 255)
INK = (17, 17, 17)
GREY = (138, 140, 146)
LINE = (24, 24, 24)
HANDLE = "@i_jamine_pa"

FD = "/usr/share/fonts/truetype/dejavu/"
CJK_PATH = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"


def font(name, size):
    return ImageFont.truetype(FD + name, size)


def cjk(size):
    return ImageFont.truetype(CJK_PATH, size)


F_TITLE = font("DejaVuSans-Bold.ttf", 76)
F_SUB = font("DejaVuSans-Bold.ttf", 35)
F_NUM = font("DejaVuSans-Bold.ttf", 44)
F_TAG = font("DejaVuSans-Bold.ttf", 25)
F_QTY = font("DejaVuSans-Bold.ttf", 21)
F_CODE = font("DejaVuSans.ttf", 11)
F_HANDLE = font("DejaVuSans-Bold.ttf", 30)
C_LEAD = cjk(30)
C_LABEL = cjk(26)
C_ITEM = cjk(17)
C_PILL = cjk(20)
C_BRAND = cjk(14)

# ---------------------------------------------------------------- layout grid
PAD_X = 40
TITLE_Y = 168
SUB_Y = 256
LEAD_Y = 302

BOX_X0, BOX_X1 = 40, 292
BOX_Y0, BOX_H, BOX_GAP = 400, 205, 15

COL_X0, COL_X1 = 305, 715
LOOK_Y = 352
PERSON_BOTTOM = 1090
PERSON_MAX_W, PERSON_MAX_H = 415, 645
BODY_H = 690          # full-body views run taller than the chest-up cut-outs


def box_rect(i):
    y = BOX_Y0 + i * (BOX_H + BOX_GAP)
    return BOX_X0, y, BOX_X1, y + BOX_H


# ------------------------------------------------------------------- looks
# Items are (icon, 中文名, brand, official reference, qty). Brand/reference are
# real agnès b. catalogue entries where the piece is theirs; personal items are
# marked 個人單品 with no reference.
OWN = "個人單品"

LOOKS = [
    {
        "photo": "g1",
        "title": "GLASSES ON",
        "tag": "LOOK 01",
        "label": "日常 · 白T",
        "pill": ("眼鏡 ON", True),
        "boxes": [
            [("glasses", "黑框眼鏡", OWN, "", "1x"),
             ("beads", "木珠項鍊", OWN, "", "1x")],
            [("tshirt", "G&G 白T", "agnès b.", "EAI1SFC0_010", "1x"),
             ("cap", "logo 棒球帽", "agnès b.", "2572GT47_000", "1x")],
            [("sneakers", "灰色球鞋", OWN, "", "1x"),
             ("phone", "手機", OWN, "", "1x")],
        ],
    },
    {
        "photo": "g2",
        "title": "GLASSES ON",
        "tag": "LOOK 02",
        "label": "出門 · 後背包",
        "pill": ("眼鏡 ON", True),
        "boxes": [
            [("glasses", "黑框眼鏡", OWN, "", "1x"),
             ("cap", "b. 棒球帽", "agnès b.", "2572K032_834", "1x")],
            [("tshirt", "G&G 白T", "agnès b.", "EAI1SFC0_010", "1x"),
             ("backpack", "機能後背包", "agnès b. VOYAGE", "O066VNP8_000", "1x")],
            [("sneakers", "灰色球鞋", OWN, "", "1x"),
             ("watch", "手錶", OWN, "", "1x")],
        ],
    },
    {
        "photo": "ng",
        "views": ["body_front", "body_a45", "body_side", "body_back"],
        "view_labels": ["FRONT", "45\u00b0", "SIDE", "BACK"],
        "title": "GLASSES OFF",
        "tag": "LOOK 03",
        "label": "正式 · 西裝",
        "pill": ("眼鏡 OFF", False),
        "boxes": [
            [("glasses", "黑框眼鏡", OWN, "", "0x"),
             ("blazer", "黑色西裝外套", OWN, "", "1x")],
            [("tshirt", "Tom 白襯衫", "agnès b.", "W501UQ36_010", "1x"),
             ("tie", "素面領帶", OWN, "", "1x")],
            [("cardigan", "排釦開襟衫", "agnès b.", "Cardigan Pression", "1x"),
             ("watch", "手錶", OWN, "", "1x")],
        ],
    },
]

INTRO_F = 150
LOOK_F = 99
LOOK3_F = 168         # the turn needs 4 views held in sequence
OUTRO_F = 73


# ------------------------------------------------------------------ helpers
def tracked(d, xy, text, fnt, fill, tracking=-3):
    """Draw text with manual letter-spacing; returns the advance width."""
    x, y = xy
    for ch in text:
        d.text((x, y), ch, font=fnt, fill=fill)
        x += d.textlength(ch, font=fnt) + tracking
    return x - xy[0]


def tracked_width(d, text, fnt, tracking=-3):
    return sum(d.textlength(c, font=fnt) + tracking for c in text)


def ease_out(t):
    return 1 - (1 - t) ** 3


def ease_in(t):
    return t ** 3


def shift_x(arr, off):
    out = np.full_like(arr, 255)
    if off > 0:
        out[:, off:] = arr[:, :-off]
    elif off < 0:
        out[:, :off] = arr[:, -off:]
    else:
        out[:] = arr
    return out


def motion_blur(img, px, samples=None):
    """Horizontal smear, the way the reference wipes between looks."""
    if px < 1:
        return img
    if samples is None:
        # keep the step under ~2px, otherwise the taps read as discrete ghosts
        samples = max(11, int(px / 2) | 1)
    arr = np.asarray(img, dtype=np.float32)
    acc = np.zeros_like(arr)
    for i in range(samples):
        off = int(round((i / (samples - 1) - 0.5) * px))
        acc += shift_x(arr, off)
    return Image.fromarray(np.clip(acc / samples, 0, 255).astype(np.uint8))


def toward_white(img, amount):
    if amount <= 0:
        return img
    return Image.blend(img, Image.new("RGB", img.size, BG), min(1.0, amount))


def fit(im, max_w, max_h):
    s = min(max_w / im.width, max_h / im.height)
    return im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)


def fade_bottom(im, px):
    """Dissolve the last `px` rows of a cut-out so it melts into the page
    instead of ending on the hard edge left by the matte."""
    im = im.copy()
    a = np.asarray(im.split()[3], dtype=np.float32)
    px = min(px, im.height)
    ramp = np.linspace(1.0, 0.0, px, dtype=np.float32) ** 1.5
    a[-px:, :] *= ramp[:, None]
    im.putalpha(Image.fromarray(a.astype(np.uint8)))
    return im


def ig_glyph(size, colour):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    lw = max(2, int(size * 0.075))
    d.rounded_rectangle([lw, lw, size - lw, size - lw], radius=size * 0.28,
                        outline=colour, width=lw)
    r = size * 0.20
    d.ellipse([size / 2 - r, size / 2 - r, size / 2 + r, size / 2 + r], outline=colour, width=lw)
    dr = size * 0.055
    d.ellipse([size * 0.70 - dr, size * 0.30 - dr, size * 0.70 + dr, size * 0.30 + dr], fill=colour)
    return im


# ------------------------------------------------------------- photo loading
def load_people():
    people = {}
    for key in ("g1", "g2", "ng"):
        im = Image.open(os.path.join(ASSETS, key + ".png")).convert("RGBA")
        im = relight.relight_named(im, key)
        people[key] = fade_bottom(fit(im, PERSON_MAX_W, PERSON_MAX_H), 90)

    # Full-body views off the character model sheet. They are scaled as a group
    # against the tallest of them, so the figure keeps one constant height while
    # it turns — scaling each to fit its own box would make him bob.
    raw = {}
    for name in ("front", "a45", "side", "back"):
        im = Image.open(os.path.join(ASSETS, "body_%s.png" % name)).convert("RGBA")
        raw[name] = relight.relight_named(im, "body")
    tallest = max(im.height for im in raw.values())
    scale = BODY_H / tallest
    for name, im in raw.items():
        people["body_" + name] = im.resize(
            (max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.LANCZOS)
    return people


PEOPLE = load_people()
INTRO_PERSON = fade_bottom(
    fit(relight.relight_named(
        Image.open(os.path.join(ASSETS, "g1.png")).convert("RGBA"), "g1"), 520, 800), 120)
ICON_CACHE = {}


def icon(name, size):
    key = (name, size)
    if key not in ICON_CACHE:
        ICON_CACHE[key] = icons.render(name, (size, size))
    return ICON_CACHE[key]


# ------------------------------------------------------------------ drawing
def draw_head(d, look):
    """Big title block shared by every card."""
    tracked(d, (PAD_X, TITLE_Y), look["title"], F_TITLE, INK, tracking=-4)
    tracked(d, (PAD_X, SUB_Y), "DRESSING BREAKDOWN", F_SUB, INK, tracking=-1)
    d.text((PAD_X + 2, LEAD_Y), "潔米爸 換裝拆解", font=C_LEAD, fill=GREY)


def fit_text(d, cx, y, text, fnt, max_w, fill, mk):
    """Centre `text` at `cx`, stepping the point size down until it fits."""
    size = fnt.size
    while size > 9 and d.textlength(text, font=fnt) > max_w:
        size -= 1
        fnt = mk(size)
    d.text((cx - d.textlength(text, font=fnt) / 2, y), text, font=fnt, fill=fill)


def draw_box(canvas, d, idx, items, reveal):
    """One numbered accessory box. `reveal` is 0..1 for the pop-in."""
    if reveal <= 0:
        return
    x0, y0, x1, y1 = box_rect(idx)
    cy = (y0 + y1) / 2
    # pop-in: box grows about its own centre and fades up
    k = 0.86 + 0.14 * ease_out(reveal)
    hw, hh = (x1 - x0) / 2 * k, (y1 - y0) / 2 * k
    cx = (x0 + x1) / 2
    d.rounded_rectangle([cx - hw, cy - hh, cx + hw, cy + hh], radius=4,
                        outline=LINE, width=3)
    if reveal < 0.55:
        return
    d.text((x0 + 14, y0 + 8), str(idx + 1), font=F_NUM, fill=INK)
    if idx == 2:
        d.ellipse([x1 - 40, y0 + 14, x1 - 16, y0 + 38], outline=INK, width=2)
        d.text((x1 - 30, y0 + 18), "i", font=F_QTY, fill=INK)

    cell_w = (x1 - x0) / len(items)
    for j, (name, zh, brand, code, qty) in enumerate(items):
        ix = x0 + cell_w * (j + 0.5)
        sz = 88
        tile = icon(name, sz)
        pos = (int(ix - sz / 2), int(y0 + 22))
        canvas.alpha_composite(tile, pos)
        if qty == "0x":
            # crossed out — this piece is *not* worn in this look
            d.line([(pos[0] + 14, pos[1] + sz - 15), (pos[0] + sz - 14, pos[1] + 15)],
                   fill=(196, 60, 52), width=4)
        # rotated reference beside the icon, as in the reference flat-lays
        if code:
            code_im = Image.new("RGBA", (66, 16), (0, 0, 0, 0))
            ImageDraw.Draw(code_im).text((0, 1), code, font=F_CODE, fill=(172, 174, 180, 255))
            canvas.alpha_composite(code_im.rotate(90, expand=True),
                                   (int(ix + sz / 2 - 2), int(y0 + 34)))

        fit_text(d, ix, y0 + 116, zh, C_ITEM, cell_w - 8, (104, 106, 112), cjk)
        fit_text(d, ix, y0 + 137, brand, C_BRAND, cell_w - 8,
                 INK if brand != OWN else (176, 178, 184), cjk)
        qw = d.textlength(qty, font=F_QTY)
        d.text((ix - qw / 2, y0 + 158), qty, font=F_QTY,
               fill=(196, 60, 52) if qty == "0x" else INK)


def draw_pill(d, xy, text, on):
    x, y = xy
    tw = d.textlength(text, font=C_PILL)
    w = tw + 30
    fill = INK if on else (255, 255, 255)
    d.rounded_rectangle([x, y, x + w, y + 36], radius=18, fill=fill, outline=INK, width=2)
    d.text((x + 15, y + 6), text, font=C_PILL, fill=(255, 255, 255) if on else INK)


TURN_START = 40          # frame the figure begins to rotate
TURN_HOLD = 20           # frames each view is held
TURN_SWAP = 7            # frames of smear covering each change of view


def turn_frame(look, f, total):
    """Pick the body view for this frame and say how hard to smear it.

    The reference reel turns the model on camera; with four stills off the model
    sheet the same beat is built by cutting FRONT → 45° → SIDE → BACK under a
    horizontal smear, which is what the eye reads as a body rotating.
    """
    views = look["views"]
    t = f - TURN_START
    if t < 0:
        return PEOPLE[views[0]], 0, 0.0
    step = TURN_HOLD + TURN_SWAP
    idx = min(len(views) - 1, t // step)
    within = t - idx * step
    if within >= TURN_HOLD and idx < len(views) - 1:
        # inside a swap: smear peaks mid-way, and the new view takes over there
        k = (within - TURN_HOLD) / TURN_SWAP
        smear = math.sin(k * math.pi) * 88
        return PEOPLE[views[idx + 1 if k > 0.5 else idx]], int(idx + (1 if k > 0.5 else 0)), smear
    return PEOPLE[views[idx]], int(idx), 0.0


def render_look(look, f, total):
    """One frame of an outfit card."""
    canvas = Image.new("RGBA", (W, H), BG + (255,))
    d = ImageDraw.Draw(canvas)
    p = f / (total - 1)

    draw_head(d, look)

    # boxes stagger in
    for i in range(3):
        start = 4 + i * 9
        reveal = np.clip((f - start) / 13.0, 0, 1)
        draw_box(canvas, d, i, look["boxes"][i], reveal)

    # look tag + label + glasses pill
    tag_r = np.clip((f - 2) / 10.0, 0, 1)
    if tag_r > 0:
        dy = int((1 - ease_out(tag_r)) * 18)
        tracked(d, (COL_X0 + 12, LOOK_Y + dy), look["tag"], F_TAG, INK, tracking=1)
        d.text((COL_X0 + 12, LOOK_Y + 32 + dy), look["label"], font=C_LABEL, fill=(96, 98, 104))
        draw_pill(d, (COL_X0 + 12, LOOK_Y + 72 + dy), *look["pill"])

    # subject, bottom-anchored, with a slow push-in
    if look.get("views"):
        person, view_i, smear = turn_frame(look, f, total)
        zoom = 1.0
    else:
        person = PEOPLE[look["photo"]]
        view_i, smear = None, 0.0
        zoom = 1.0 + 0.055 * p
    pw, ph = int(person.width * zoom), int(person.height * zoom)
    ps = person.resize((pw, ph), Image.LANCZOS) if zoom != 1.0 else person
    slide = int((1 - ease_out(min(1.0, f / 12.0))) * 40)
    px = int((COL_X0 + COL_X1) / 2 - pw / 2) + slide
    py = PERSON_BOTTOM - ph

    if smear > 0:
        # blur the figure alone, not the page, so the turn reads as the body
        # moving while the layout stays locked
        plate = Image.new("RGBA", (W, H), (255, 255, 255, 0))
        plate.alpha_composite(ps, (px, py))
        plate = plate.filter(ImageFilter.GaussianBlur(smear * 0.22))
        plate = Image.fromarray(
            np.asarray(motion_blur(Image.fromarray(
                np.asarray(plate)[..., :3]), int(smear))).astype(np.uint8))
        alpha = Image.new("RGBA", (W, H), (255, 255, 255, 0))
        alpha.alpha_composite(ps, (px, py))
        a = np.asarray(alpha)[..., 3]
        a = np.asarray(Image.fromarray(a).filter(ImageFilter.GaussianBlur(smear * 0.22)))
        merged = np.dstack([np.asarray(plate), a])
        canvas.alpha_composite(Image.fromarray(merged.astype(np.uint8), "RGBA"))
    else:
        canvas.alpha_composite(ps, (px, py))

    if view_i is not None:
        tag = look["view_labels"][view_i]
        tw = tracked_width(d, tag, F_QTY, 1)
        d.rounded_rectangle([COL_X1 - tw - 34, PERSON_BOTTOM + 14,
                             COL_X1 - 10, PERSON_BOTTOM + 46], radius=16, fill=INK)
        tracked(d, (COL_X1 - tw - 22, PERSON_BOTTOM + 19), tag, F_QTY, (255, 255, 255), tracking=1)

    wm = ig_glyph(30, (206, 208, 214, 255))
    canvas.alpha_composite(wm, (W - 52, 330))

    return canvas.convert("RGB")


def render_intro(f, total):
    canvas = Image.new("RGBA", (W, H), BG + (255,))
    d = ImageDraw.Draw(canvas)
    p = f / (total - 1)

    # charging meter
    mw, mh = 210, 92
    mx, my = W / 2 - mw / 2, 96
    d.rounded_rectangle([mx, my, mx + mw, my + mh], radius=16, outline=INK, width=8)
    d.rounded_rectangle([mx + mw + 8, my + mh * 0.32, mx + mw + 24, my + mh * 0.68],
                        radius=6, fill=INK)
    charge = np.clip((p - 0.06) / 0.72, 0, 1)
    inner_w = (mw - 32) * charge
    if inner_w > 4:
        d.rounded_rectangle([mx + 16, my + 16, mx + 16 + inner_w, my + mh - 16],
                            radius=8, fill=INK)

    # caption under the meter flips once the meter is full
    if charge < 1.0:
        cap, col = "換裝載入中…", (120, 122, 128)
    else:
        cap, col = "READY", INK
        blink = (f // 5) % 2 == 0
        col = INK if blink else (170, 172, 178)
    cw = d.textlength(cap, font=C_LEAD) if cap != "READY" else tracked_width(d, cap, F_SUB, 2)
    if cap == "READY":
        tracked(d, (W / 2 - cw / 2, my + mh + 18), cap, F_SUB, col, tracking=2)
    else:
        d.text((W / 2 - cw / 2, my + mh + 22), cap, font=C_LEAD, fill=col)

    # subject rises in and pushes forward
    base = INTRO_PERSON
    zoom = 1.0 + 0.09 * ease_out(min(1.0, p / 0.9))
    pw, ph = int(base.width * zoom), int(base.height * zoom)
    ps = base.resize((pw, ph), Image.LANCZOS)
    rise = int((1 - ease_out(min(1.0, f / 20.0))) * 60)
    canvas.alpha_composite(ps, (int(W / 2 - pw / 2), 1120 - ph + rise))

    # title card slides up in the lower third once charged
    tr = np.clip((p - 0.52) / 0.24, 0, 1)
    if tr > 0:
        dy = int((1 - ease_out(tr)) * 40)
        a = int(255 * min(1.0, tr * 1.4))
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        t1 = "GLASSES ON / OFF"
        w1 = tracked_width(ld, t1, F_SUB, -1)
        tracked(ld, (W / 2 - w1 / 2, 1156 + dy), t1, F_SUB, INK + (a,), tracking=-1)
        t2 = "潔米爸 換裝拆解"
        w2 = ld.textlength(t2, font=C_LEAD)
        ld.text((W / 2 - w2 / 2, 1200 + dy), t2, font=C_LEAD, fill=GREY + (a,))
        canvas.alpha_composite(layer)

    return canvas.convert("RGB")


def render_outro(f, total):
    """Final look, dimmed, with the handle."""
    # frame 38: boxes fully revealed, still on FRONT — the turn starts at 40, and
    # ending the reel on the back of his head is a poor last impression
    base = render_look(LOOKS[-1], 38, LOOK3_F)
    p = f / (total - 1)
    dim = 0.88 * min(1.0, f / 10.0)
    canvas = Image.blend(base, Image.new("RGB", (W, H), (22, 22, 24)), dim).convert("RGBA")
    d = ImageDraw.Draw(canvas)

    a = int(255 * min(1.0, max(0.0, (f - 6) / 12.0)))
    if a > 0:
        # gentle pulse on the badge
        pulse = 1.0 + 0.03 * math.sin(p * math.pi * 4)
        gsz = int(96 * pulse)
        canvas.alpha_composite(ig_glyph(gsz, (255, 255, 255, a)),
                               (int(W / 2 - gsz / 2), int(576 - gsz / 2)))
        hw = tracked_width(d, HANDLE, F_HANDLE, 0)
        tracked(d, (W / 2 - hw / 2, 650), HANDLE, F_HANDLE, (255, 255, 255, a), tracking=0)
    return canvas.convert("RGB")


# --------------------------------------------------------------- transitions
WIPE_OUT, WIPE_IN = 7, 6


def apply_wipe(img, f, total, first, last):
    """Motion-blur the head and tail of a segment so cuts read as a wipe."""
    if not first and f < WIPE_IN:
        t = 1 - (f + 1) / (WIPE_IN + 1)
        return toward_white(motion_blur(img, int(150 * t)), 0.55 * t)
    if not last and f >= total - WIPE_OUT:
        t = (f - (total - WIPE_OUT) + 1) / WIPE_OUT
        return toward_white(motion_blur(img, int(170 * t)), 0.6 * t)
    return img


def frames():
    yield from (("intro", f, INTRO_F) for f in range(INTRO_F))
    for i in range(len(LOOKS)):
        n = LOOK3_F if LOOKS[i].get("views") else LOOK_F
        yield from ((("look", i), f, n) for f in range(n))
    yield from (("outro", f, OUTRO_F) for f in range(OUTRO_F))


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-an", "-c:v", "libx264", "-preset", "slow", "-crf", "18",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT,
    ]
    seq = list(frames())
    total = len(seq)
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for n, (kind, f, seg_total) in enumerate(seq):
        if kind == "intro":
            img = render_intro(f, seg_total)
            img = apply_wipe(img, f, seg_total, first=True, last=False)
        elif kind == "outro":
            img = render_outro(f, seg_total)
            img = apply_wipe(img, f, seg_total, first=False, last=True)
        else:
            idx = kind[1]
            img = render_look(LOOKS[idx], f, seg_total)
            img = apply_wipe(img, f, seg_total, first=False, last=False)
        proc.stdin.write(img.tobytes())
        if n % 40 == 0:
            print(f"  {n}/{total}", file=sys.stderr, flush=True)
    proc.stdin.close()
    rc = proc.wait()
    if rc:
        raise SystemExit(f"ffmpeg exited {rc}")
    print(f"wrote {OUT}  ({total} frames, {total / FPS:.2f}s)")


if __name__ == "__main__":
    main()
