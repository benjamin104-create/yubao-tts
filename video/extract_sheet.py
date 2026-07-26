"""Pull the four full-body views out of the 潔米爸 character model sheet.

The sheet lays out 正面 / 側面 / 背面 / 45度角 across the top panel. Matting them
is awkward because the suit is near-black against a near-black navy card, so
rembg leaves the card showing through gaps between the legs and under the arms.

The fix is a colour key run after the matte: the card is navy (blue channel well
above red) while the suit is neutral (blue ≈ red), so `blue - red` separates them
cleanly where luminance alone cannot.
"""

import os

import numpy as np
from PIL import Image, ImageFilter
from rembg import remove, new_session

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")

# Panel centres on the 1080-wide sheet, measured from the view labels.
VIEWS = [("front", 388), ("a45", 972), ("side", 585), ("back", 780)]
PANEL_HALF = 95
TOP, BOTTOM = 104, 640
UPSAMPLE = 3


def key_navy(im, bias=16.0, soft=12.0):
    """Drop pixels whose blue channel runs ahead of red — the navy card, not the
    neutral-black suit.

    Only the blue/red *ratio* separates these two; absolute RGB does not. The
    jacket sits at (24,24,32) and the card at (14,22,38) — barely 12 units apart
    in RGB, so a plain colour-distance key deletes the suit. In B-R terms though
    the jacket is 8 and the card 24, which is a workable margin.

    The threshold stays loose on purpose. Pushing it tighter to chase the last
    of the card only chews nibbles out of the trouser silhouette — that residue
    is a segmentation problem, and it is solved by the model choice in `extract`,
    not by the key.
    """
    a = np.asarray(im, dtype=np.float32)
    rgb, alpha = a[..., :3], a[..., 3]

    blueness = rgb[..., 2] - rgb[..., 0]
    navy = np.clip((blueness - bias) / soft, 0, 1)
    # never touch anything bright — skin, shirt, shoe highlights
    dim = np.clip((110.0 - rgb.max(axis=2)) / 40.0, 0, 1)
    alpha = alpha * (1.0 - navy * dim)
    return Image.fromarray(np.dstack([rgb, alpha]).astype(np.uint8), "RGBA")


def close_holes(im, radius=2):
    """Morphological close on the raw matte, to seal pinholes inside the garment.

    Runs AFTER the key, with a small radius: its job is to repair the edge
    nibbles the tighter below-hip key leaves in the trousers. The radius is well
    under the width of the (now open) gap between the ankles, so it repairs the
    silhouette without bridging the legs back together.
    """
    a = np.asarray(im, dtype=np.uint8)
    al = Image.fromarray(a[..., 3])
    al = al.filter(ImageFilter.MaxFilter(radius * 2 + 1))
    al = al.filter(ImageFilter.MinFilter(radius * 2 + 1))
    return Image.fromarray(np.dstack([a[..., :3], np.asarray(al)]), "RGBA")


def keep_wide_runs(im, hip=0.52, ratio=0.30):
    """Below the hip, drop any horizontal run of pixels much thinner than the
    widest run on that row.

    This is the last of the card residue — the sliver between the ankles on the
    back view, which no colour rule can reach because it sits inside the garment's
    own value range. Geometry can: on a given row the legs are wide runs and the
    leftover card is a thin one, and the test never touches the legs themselves,
    so unlike a tighter key it cannot eat into the suit.
    """
    a = np.asarray(im, dtype=np.uint8).copy()
    alpha = a[..., 3]
    h, w = alpha.shape
    for y in range(int(h * hip), h):
        row = alpha[y] > 0
        if not row.any():
            continue
        edges = np.diff(np.concatenate(([0], row.view(np.int8), [0])))
        starts, ends = np.where(edges == 1)[0], np.where(edges == -1)[0]
        lengths = ends - starts
        if len(lengths) < 2:
            continue
        cutoff = lengths.max() * ratio
        for s, e, L in zip(starts, ends, lengths):
            if L < cutoff:
                alpha[y, s:e] = 0
    return Image.fromarray(a, "RGBA")


def clean(im, floor=90):
    """Hard-cut the key's semi-transparent residue, keep only the figure, feather."""
    from scipy import ndimage

    a = np.asarray(im, dtype=np.uint8).copy()
    alpha = a[..., 3].astype(np.float32)
    # anything this faint is key residue, not fabric
    alpha[alpha < floor] = 0

    # drop every blob but the body — kills stray marks above the head and the
    # slivers of card left between the legs
    lab, n = ndimage.label(alpha > 0)
    if n > 1:
        sizes = ndimage.sum(alpha > 0, lab, range(1, n + 1))
        alpha[lab != int(np.argmax(sizes)) + 1] = 0

    al = Image.fromarray(alpha.astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.9))
    return Image.fromarray(np.dstack([a[..., :3], np.asarray(al)]), "RGBA")


def extract(sheet_path, out_dir=ASSETS):
    im = Image.open(sheet_path).convert("RGB")
    # isnet-general-use, not u2net: on this sheet u2net swallows the navy card
    # between the ankles into the silhouette (gap opacity 209/255 vs isnet's 114),
    # and u2net_human_seg is worse still (254) — it fills the gap solid.
    session = new_session("isnet-general-use")
    made = {}
    for name, cx in VIEWS:
        panel = im.crop((cx - PANEL_HALF, TOP, cx + PANEL_HALF, BOTTOM))
        panel = panel.resize((panel.width * UPSAMPLE, panel.height * UPSAMPLE), Image.LANCZOS)
        # No alpha matting here: on a near-black suit against a near-black card
        # the matte's foreground estimation washes the edge out into a pale halo
        # that survives the key. A hard mask plus a light feather is cleaner.
        cut = remove(panel, session=session, alpha_matting=False)
        cut = clean(keep_wide_runs(close_holes(key_navy(cut), radius=1)))
        cut = cut.crop(cut.getbbox())
        path = os.path.join(out_dir, "body_%s.png" % name)
        cut.save(path)
        made[name] = cut.size
    return made


if __name__ == "__main__":
    import sys
    print(extract(sys.argv[1]))
