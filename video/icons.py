"""Flat product-style icons for the outfit-breakdown reel.

Every draw_* function paints one item into an RGBA tile of the given size and
returns it. Icons share a muted grey-scale palette so the numbered boxes read as
a single product grid, the way the reference reel's flat-lays do.
"""

from PIL import Image, ImageDraw, ImageFilter

INK = (34, 34, 34, 255)
DARK = (58, 58, 62, 255)
MID = (150, 152, 158, 255)
LIGHT = (214, 216, 220, 255)
PAPER = (240, 241, 243, 255)
WHITE = (252, 252, 253, 255)
WOOD = (150, 118, 76, 255)
WOOD_D = (110, 84, 52, 255)
NAVY = (52, 62, 84, 255)
NAVY_D = (36, 44, 62, 255)


def _tile(size):
    im = Image.new("RGBA", size, (0, 0, 0, 0))
    return im, ImageDraw.Draw(im)


def _shadow(im, blur=7, offset=(0, 5), opacity=60):
    """Drop a soft shadow under the opaque pixels of `im`."""
    alpha = im.split()[3].point(lambda a: opacity if a > 40 else 0)
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    sh.putalpha(alpha.filter(ImageFilter.GaussianBlur(blur)))
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    out.paste(sh, offset, sh)
    out.alpha_composite(im)
    return out


def draw_glasses(size):
    w, h = size
    im, d = _tile(size)
    cx, cy = w / 2, h / 2
    lw = max(3, int(w * 0.030))
    lens_w, lens_h = w * 0.345, h * 0.255
    bridge = w * 0.055
    for sign in (-1, 1):
        x0 = cx + sign * bridge - (lens_w if sign > 0 else 0) + (0 if sign > 0 else -lens_w)
        x0 = cx + (bridge if sign > 0 else -bridge - lens_w)
        box = [x0, cy - lens_h / 2, x0 + lens_w, cy + lens_h / 2]
        d.rounded_rectangle(box, radius=lens_h * 0.22, fill=(228, 236, 242, 120), outline=INK, width=lw)
    d.line([(cx - bridge, cy - lens_h * 0.18), (cx + bridge, cy - lens_h * 0.18)], fill=INK, width=lw)
    # temples folding back
    for sign in (-1, 1):
        ex = cx + sign * (bridge + lens_w)
        d.line([(ex, cy - lens_h * 0.28), (ex + sign * w * 0.10, cy - lens_h * 0.46)], fill=INK, width=lw)
    return _shadow(im, blur=6, offset=(0, 4), opacity=52)


def draw_cap(size):
    w, h = size
    im, d = _tile(size)
    cx = w / 2
    top = h * 0.32
    crown_w, crown_h = w * 0.54, h * 0.30
    base = top + crown_h                      # where crown meets brim
    brim_h = h * 0.11
    # brim sweeping to the right, its top edge sitting on the crown base
    d.chord([cx - crown_w * 0.42, base - brim_h, cx + crown_w * 1.00, base + brim_h],
            start=0, end=180, fill=NAVY_D)
    # crown (top half of an ellipse -> lands exactly on `base`)
    d.pieslice([cx - crown_w / 2, top, cx + crown_w / 2, top + crown_h * 2],
               start=180, end=360, fill=NAVY)
    # panel seams + button
    d.line([(cx, top + crown_h * 0.06), (cx, base - 2)], fill=NAVY_D, width=max(2, int(w * 0.011)))
    d.ellipse([cx - w * 0.017, top - w * 0.020, cx + w * 0.017, top + w * 0.014], fill=NAVY_D)
    # sweatband edge + tiny front patch
    d.line([(cx - crown_w * 0.49, base - 1), (cx + crown_w * 0.49, base - 1)],
           fill=NAVY_D, width=max(2, int(w * 0.012)))
    d.rounded_rectangle([cx - w * 0.095, base - crown_h * 0.52, cx + w * 0.095, base - crown_h * 0.24],
                        radius=3, fill=(226, 229, 236, 235))
    return _shadow(im, blur=8, offset=(0, 6), opacity=58)


def draw_backpack(size):
    w, h = size
    im, d = _tile(size)
    cx = w / 2
    bw, bh = w * 0.50, h * 0.56
    x0, y0 = cx - bw / 2, h * 0.26
    # padded shoulder straps peeking out either side, behind the body
    for sign in (-1, 1):
        sx = cx + sign * bw * 0.46
        d.rounded_rectangle([sx - bw * 0.075, y0 + bh * 0.14, sx + bw * 0.075, y0 + bh * 0.86],
                            radius=bw * 0.075, fill=(70, 72, 80, 255))
    # grab loop on top
    d.arc([cx - bw * 0.15, y0 - bh * 0.13, cx + bw * 0.15, y0 + bh * 0.12],
          start=180, end=360, fill=(70, 72, 80, 255), width=max(3, int(w * 0.024)))
    # main body
    d.rounded_rectangle([x0, y0, x0 + bw, y0 + bh], radius=bw * 0.22, fill=DARK)
    # top lid seam
    d.arc([x0, y0 + bh * 0.10, x0 + bw, y0 + bh * 0.58], start=180, end=360,
          fill=(96, 98, 106, 255), width=max(2, int(w * 0.014)))
    # front pocket
    d.rounded_rectangle([x0 + bw * 0.18, y0 + bh * 0.52, x0 + bw * 0.82, y0 + bh * 0.90],
                        radius=bw * 0.10, fill=(88, 90, 98, 255))
    # buckle
    d.rounded_rectangle([cx - bw * 0.07, y0 + bh * 0.46, cx + bw * 0.07, y0 + bh * 0.58],
                        radius=2, fill=(198, 200, 206, 255))
    return _shadow(im, blur=8, offset=(0, 6), opacity=62)


def draw_tshirt(size, body=WHITE, outline=(206, 208, 214, 255)):
    w, h = size
    im, d = _tile(size)
    cx = w / 2
    top = h * 0.28
    sh = w * 0.44          # shoulder half-width
    sleeve = w * 0.15
    hem = h * 0.78
    waist = w * 0.30
    pts = [
        (cx - waist, hem), (cx - waist, top + h * 0.14),
        (cx - sh, top + h * 0.20), (cx - sh - sleeve * 0.15, top + h * 0.04),
        (cx - waist * 0.72, top - h * 0.02), (cx - waist * 0.30, top + h * 0.05),
        (cx + waist * 0.30, top + h * 0.05), (cx + waist * 0.72, top - h * 0.02),
        (cx + sh + sleeve * 0.15, top + h * 0.04), (cx + sh, top + h * 0.20),
        (cx + waist, top + h * 0.14), (cx + waist, hem),
    ]
    d.polygon(pts, fill=body, outline=outline)
    # collar
    d.arc([cx - waist * 0.34, top - h * 0.045, cx + waist * 0.34, top + h * 0.085],
          start=0, end=180, fill=outline, width=max(2, int(w * 0.014)))
    # hem + fold hints
    d.line([(cx - waist, hem), (cx + waist, hem)], fill=outline, width=2)
    d.line([(cx - waist * 0.42, hem - h * 0.20), (cx - waist * 0.30, hem - h * 0.03)],
           fill=(226, 228, 233, 255), width=2)
    return _shadow(im, blur=7, offset=(0, 5), opacity=46)


def draw_beads(size):
    w, h = size
    im, d = _tile(size)
    cx, cy = w / 2, h * 0.50
    rx, ry = w * 0.26, h * 0.28
    r = max(3.0, w * 0.036)
    import math
    n = 26
    for i in range(n):
        a = math.pi * 2 * i / n - math.pi / 2
        x, y = cx + rx * math.cos(a), cy + ry * math.sin(a)
        d.ellipse([x - r, y - r, x + r, y + r], fill=WOOD, outline=WOOD_D)
        d.ellipse([x - r * 0.42, y - r * 0.52, x - r * 0.02, y - r * 0.12],
                  fill=(196, 168, 128, 220))
    return _shadow(im, blur=6, offset=(0, 4), opacity=48)


def _one_sneaker(d, x0, y0, sw, sh_, body):
    """Side-profile trainer: heel counter at the left, toe box at the right."""
    toe = x0 + sw
    d.polygon([
        (x0 + sw * 0.06, y0 + sh_ * 0.94),        # heel bottom
        (x0 + sw * 0.02, y0 + sh_ * 0.44),        # heel counter back
        (x0 + sw * 0.14, y0 + sh_ * 0.20),        # collar back
        (x0 + sw * 0.30, y0 + sh_ * 0.16),        # collar dip
        (x0 + sw * 0.40, y0 + sh_ * 0.40),        # tongue front
        (x0 + sw * 0.72, y0 + sh_ * 0.58),        # vamp
        (toe - sw * 0.02, y0 + sh_ * 0.78),       # toe cap
        (toe, y0 + sh_ * 0.94),
    ], fill=body)
    # midsole slab
    d.rounded_rectangle([x0, y0 + sh_ * 0.84, toe + sw * 0.02, y0 + sh_ * 1.14],
                        radius=sh_ * 0.15, fill=WHITE, outline=(198, 200, 206, 255), width=2)
    # outsole shade
    d.rounded_rectangle([x0, y0 + sh_ * 1.02, toe + sw * 0.02, y0 + sh_ * 1.14],
                        radius=sh_ * 0.08, fill=(196, 198, 204, 255))
    # laces across the vamp
    for k in range(3):
        lx = x0 + sw * (0.40 + k * 0.13)
        d.line([(lx, y0 + sh_ * (0.40 + k * 0.06)), (lx + sw * 0.09, y0 + sh_ * (0.30 + k * 0.06))],
               fill=(148, 150, 158, 255), width=max(2, int(sw * 0.030)))
    # swoosh-free side seam
    d.line([(x0 + sw * 0.22, y0 + sh_ * 0.80), (x0 + sw * 0.62, y0 + sh_ * 0.66)],
           fill=(172, 174, 182, 255), width=max(2, int(sw * 0.026)))


def draw_sneakers(size):
    w, h = size
    im, d = _tile(size)
    # back shoe, slightly smaller and higher
    _one_sneaker(d, w * 0.30, h * 0.30, w * 0.52, h * 0.24, (176, 178, 186, 255))
    # front shoe
    _one_sneaker(d, w * 0.16, h * 0.46, w * 0.58, h * 0.26, (206, 208, 214, 255))
    return _shadow(im, blur=7, offset=(0, 5), opacity=52)


def draw_blazer(size):
    w, h = size
    im, d = _tile(size)
    cx = w / 2
    top, hem = h * 0.22, h * 0.86
    sh = w * 0.40
    # body
    d.polygon([(cx - sh, top + h * 0.10), (cx - sh * 0.92, hem), (cx + sh * 0.92, hem),
               (cx + sh, top + h * 0.10), (cx + sh * 0.44, top),
               (cx, top + h * 0.30), (cx - sh * 0.44, top)], fill=DARK)
    # white shirt V
    d.polygon([(cx - sh * 0.30, top + h * 0.01), (cx, top + h * 0.34),
               (cx + sh * 0.30, top + h * 0.01), (cx, top - h * 0.02)], fill=WHITE)
    # lapels
    d.polygon([(cx - sh * 0.46, top), (cx - sh * 0.06, top + h * 0.36),
               (cx - sh * 0.30, top + h * 0.44)], fill=(78, 80, 88, 255))
    d.polygon([(cx + sh * 0.46, top), (cx + sh * 0.06, top + h * 0.36),
               (cx + sh * 0.30, top + h * 0.44)], fill=(78, 80, 88, 255))
    # buttons
    for k in range(2):
        by = top + h * 0.46 + k * h * 0.12
        d.ellipse([cx - w * 0.016, by, cx + w * 0.016, by + w * 0.032], fill=(150, 152, 158, 255))
    return _shadow(im, blur=8, offset=(0, 6), opacity=58)


def draw_cardigan(size):
    """agnès b.'s signature snap cardigan — open front, ribbed placket of snaps."""
    w, h = size
    im, d = _tile(size)
    cx = w / 2
    top, hem = h * 0.24, h * 0.84
    sh = w * 0.38
    body = (206, 208, 214, 255)
    d.polygon([(cx - sh, top + h * 0.09), (cx - sh * 0.94, hem), (cx + sh * 0.94, hem),
               (cx + sh, top + h * 0.09), (cx + sh * 0.40, top),
               (cx - sh * 0.40, top)], fill=body)
    # open front gap
    d.polygon([(cx - sh * 0.10, top + h * 0.02), (cx + sh * 0.10, top + h * 0.02),
               (cx + sh * 0.13, hem), (cx - sh * 0.13, hem)], fill=(236, 238, 242, 255))
    # ribbed collar band
    d.polygon([(cx - sh * 0.40, top), (cx + sh * 0.40, top),
               (cx + sh * 0.34, top + h * 0.06), (cx - sh * 0.34, top + h * 0.06)],
              fill=(180, 182, 190, 255))
    # the row of pearly snaps
    for k in range(7):
        by = top + h * 0.10 + k * h * 0.098
        if by > hem - h * 0.04:
            break
        d.ellipse([cx - sh * 0.22 - w * 0.013, by, cx - sh * 0.22 + w * 0.013, by + w * 0.026],
                  fill=(250, 250, 252, 255), outline=(160, 162, 170, 255))
    return _shadow(im, blur=7, offset=(0, 5), opacity=48)


def draw_tie(size):
    w, h = size
    im, d = _tile(size)
    cx = w / 2
    top = h * 0.20
    kw = w * 0.095            # knot half-width
    bw = w * 0.155            # blade half-width at its widest
    knot_b = top + h * 0.13
    # collar wings tucked behind the knot
    d.polygon([(cx - kw * 2.4, top - h * 0.03), (cx - kw * 0.9, top),
               (cx - kw * 1.0, knot_b), (cx - kw * 2.6, top + h * 0.07)], fill=(228, 230, 235, 255))
    d.polygon([(cx + kw * 2.4, top - h * 0.03), (cx + kw * 0.9, top),
               (cx + kw * 1.0, knot_b), (cx + kw * 2.6, top + h * 0.07)], fill=(228, 230, 235, 255))
    # knot
    d.polygon([(cx - kw * 0.78, top), (cx + kw * 0.78, top),
               (cx + kw, knot_b), (cx - kw, knot_b)], fill=INK)
    # blade: narrow under the knot, flaring out, then the pointed tip
    d.polygon([(cx - kw * 0.86, knot_b), (cx + kw * 0.86, knot_b),
               (cx + bw, h * 0.60), (cx, h * 0.86), (cx - bw, h * 0.60)],
              fill=(46, 46, 50, 255))
    # single highlight fold
    d.line([(cx - kw * 0.30, knot_b + h * 0.04), (cx - bw * 0.55, h * 0.60)],
           fill=(88, 88, 96, 255), width=max(2, int(w * 0.012)))
    return _shadow(im, blur=7, offset=(0, 5), opacity=54)


def draw_phone(size):
    w, h = size
    im, d = _tile(size)
    pw, ph = w * 0.26, h * 0.52
    x0, y0 = w / 2 - pw / 2, h / 2 - ph / 2
    d.rounded_rectangle([x0, y0, x0 + pw, y0 + ph], radius=pw * 0.20, fill=(226, 228, 233, 255),
                        outline=(180, 182, 188, 255), width=2)
    d.rounded_rectangle([x0 + pw * 0.10, y0 + ph * 0.05, x0 + pw * 0.55, y0 + ph * 0.24],
                        radius=pw * 0.12, fill=(96, 98, 106, 255))
    for k in range(3):
        d.ellipse([x0 + pw * 0.16 + (k % 2) * pw * 0.20, y0 + ph * 0.08 + (k // 2) * pw * 0.20,
                   x0 + pw * 0.30 + (k % 2) * pw * 0.20, y0 + ph * 0.08 + pw * 0.14 + (k // 2) * pw * 0.20],
                  fill=(58, 60, 66, 255))
    return _shadow(im, blur=7, offset=(0, 5), opacity=48)


def draw_watch(size):
    w, h = size
    im, d = _tile(size)
    cx, cy = w / 2, h / 2
    r = w * 0.14
    d.rounded_rectangle([cx - r * 0.62, cy - r * 2.5, cx + r * 0.62, cy + r * 2.5],
                        radius=r * 0.30, fill=(72, 74, 80, 255))
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(232, 234, 238, 255),
              outline=(120, 122, 128, 255), width=3)
    d.line([(cx, cy), (cx, cy - r * 0.55)], fill=INK, width=2)
    d.line([(cx, cy), (cx + r * 0.42, cy + r * 0.20)], fill=INK, width=2)
    return _shadow(im, blur=6, offset=(0, 4), opacity=50)


ICONS = {
    "glasses": draw_glasses,
    "cap": draw_cap,
    "backpack": draw_backpack,
    "tshirt": draw_tshirt,
    "beads": draw_beads,
    "sneakers": draw_sneakers,
    "blazer": draw_blazer,
    "cardigan": draw_cardigan,
    "tie": draw_tie,
    "phone": draw_phone,
    "watch": draw_watch,
}


def render(name, size):
    return ICONS[name](size)
