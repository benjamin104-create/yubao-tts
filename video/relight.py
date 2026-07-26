"""Studio relight for the cut-out portraits.

The source selfies are lit by warm shop tungsten, which is what reads as dull /
"老氣": whites go yellow, the shadow side collapses, and there is no separation
from the background. This rebuilds them as a soft three-point studio setup —
neutral white balance, a big soft key from the upper left, a fill that opens the
shadows, and a rim light that lifts the subject off the page.

Everything runs on the alpha matte, so the light wraps the subject only and the
page stays clean white.
"""

import numpy as np
from PIL import Image, ImageFilter


def _srgb_to_linear(x):
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def _linear_to_srgb(x):
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * x ** (1 / 2.4) - 0.055)


def white_balance(rgb, mask, strength=0.88):
    """Neutralise the colour cast by driving the brightest garment tones grey."""
    sel = rgb[mask]
    if sel.size == 0:
        return rgb
    hi = np.percentile(sel, 92, axis=0)
    hi = np.maximum(hi, 1e-3)
    target = hi.mean()
    gain = target / hi
    gain = 1.0 + (gain - 1.0) * strength
    return rgb * gain


def tone_curve(rgb, shadow_lift=0.16, contrast=0.20, highlight_rolloff=0.22):
    """Open the shadows, then put contrast back through the midtones."""
    x = np.clip(rgb, 0, 1)
    # lift shadows without crushing the black point flat
    x = x + shadow_lift * (1.0 - x) ** 3.0
    # gentle S around mid grey
    x = x + contrast * (x - 0.5) * (1.0 - np.abs(x - 0.5) * 2.0) ** 1.5
    # soft shoulder so skin highlights roll off instead of clipping
    x = x - highlight_rolloff * np.clip(x - 0.72, 0, None) ** 2 * 2.4
    return np.clip(x, 0, 1)


def _gradient(shape, cx, cy, radius, softness=1.6):
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((xx - cx * w) / (radius * w)) ** 2 + ((yy - cy * h) / (radius * h)) ** 2)
    return np.clip(1.0 - d, 0, 1) ** softness


def key_light(rgb, shape, strength=0.17):
    """Big soft box, upper left, the way a beauty key falls on the face."""
    g = _gradient(shape, 0.34, 0.26, 1.05)[..., None]
    return rgb * (1.0 + strength * g)


def rim_light(rgb, alpha, strength=0.42, width=9):
    """Kicker along the top-right edge so the subject separates from white."""
    m = (alpha > 0.5).astype(np.float32)
    inner = np.zeros_like(m)
    inner[width:, :-width] = m[:-width, width:]     # push down-left
    band = np.clip(m - inner, 0, 1)
    band = np.asarray(
        Image.fromarray((band * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(width * 0.85)),
        dtype=np.float32) / 255.0
    band *= m                                        # keep the glow inside the matte
    # cool-neutral kicker, brightest at the top of the frame
    h = band.shape[0]
    falloff = np.clip(np.linspace(1.25, 0.25, h), 0, None)[:, None]
    band = band * falloff
    add = band[..., None] * strength * np.array([0.98, 0.99, 1.0], dtype=np.float32)
    return rgb + add


def vibrance(rgb, amount=0.14, yellow_pull=0.10):
    """Lift saturation where it is low, and walk the hue off yellow."""
    lum = (rgb * np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)).sum(axis=2, keepdims=True)
    sat = np.abs(rgb - lum).max(axis=2, keepdims=True)
    boost = amount * (1.0 - np.clip(sat * 2.2, 0, 1))
    out = lum + (rgb - lum) * (1.0 + boost)
    # trim the yellow/orange bias that makes tungsten skin look tired
    out[..., 2] += yellow_pull * np.clip(out[..., 0] - out[..., 2], 0, None) * 0.5
    out[..., 0] -= yellow_pull * np.clip(out[..., 0] - out[..., 2], 0, None) * 0.12
    return out


def clarity(rgb, amount=0.30, radius=14):
    """Local contrast, so features read crisp at small sizes."""
    src = Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8))
    blur = np.asarray(src.filter(ImageFilter.GaussianBlur(radius)), dtype=np.float32) / 255.0
    return np.clip(rgb + amount * (rgb - blur), 0, 1)


def relight(im, key=0.17, rim=0.34, lift=0.16, wb=0.88,
            clar=0.16, vib=0.12, yellow=0.03, contrast=0.20):
    """Full chain. `im` is an RGBA cut-out; returns a new RGBA cut-out."""
    a = np.asarray(im.convert("RGBA"), dtype=np.float32) / 255.0
    rgb, alpha = a[..., :3], a[..., 3]
    mask = alpha > 0.5

    rgb = white_balance(rgb, mask, strength=wb)
    lin = _srgb_to_linear(np.clip(rgb, 0, 1))
    lin = key_light(lin, alpha.shape, strength=key)
    rgb = _linear_to_srgb(lin)
    rgb = tone_curve(rgb, shadow_lift=lift, contrast=contrast)
    rgb = rim_light(rgb, alpha, strength=rim)
    rgb = vibrance(rgb, amount=vib, yellow_pull=yellow)
    rgb = clarity(rgb, amount=clar, radius=18)
    rgb = np.clip(rgb, 0, 1)

    out = np.dstack([rgb * 255.0, alpha * 255.0]).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


# Per-source grades. The two selfies are shot under warm shop tungsten and need
# the full treatment; `ng` is already a retouched studio-style composite, so it
# only gets a light polish or it blows out.
PRESETS = {
    "g1": dict(key=0.17, rim=0.34, lift=0.17, wb=0.90, clar=0.16, vib=0.13, contrast=0.21),
    "g2": dict(key=0.15, rim=0.30, lift=0.13, wb=0.85, clar=0.14, vib=0.11, contrast=0.18),
    "ng": dict(key=0.06, rim=0.12, lift=0.05, wb=0.35, clar=0.08, vib=0.06, contrast=0.08),
}


def relight_named(im, key_name):
    return relight(im, **PRESETS[key_name])
