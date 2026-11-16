"""Fidelity metric functions (plain Python: numpy only). Character-independent and deterministic.

Conventions: images are HxWx3 uint8 sRGB arrays, masks are HxW boolean arrays, points are (x, y) pixels with
x right and y down. Colour difference is CIEDE2000 under D65 (as pipeline/charsys/tools/measure_colour.py).
Texture statistics follow docs/references/VISUAL_TARGET.md (fuzz: high-frequency luma RMS after subtracting a 9 px
Gaussian blur; sheen: P90/P50 of luma divided by a 31 px blur; focus: variance of the Laplacian of Y'), computed
inside the region with mask-normalised blurs so the background never leaks in."""
import json
import math

import numpy as np

# ----------------------------------------------------------------------------------------------------------- colour
_M = np.array([[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750],
               [0.0193339, 0.1191920, 0.9503041]])
_WHITE = np.array([0.95047, 1.0, 1.08883])


def srgb_to_lab(rgb):
    """sRGB (..., 3) in 0..255 -> CIE Lab (D65), same shape."""
    c = np.asarray(rgb, float) / 255.0
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    xyz = c @ _M.T / _WHITE
    f = np.where(xyz > 216 / 24389, np.cbrt(xyz), (24389 / 27 * xyz + 16) / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def lab_to_srgb(lab):
    lab = np.asarray(lab, float)
    fy = (lab[..., 0] + 16) / 116
    fx = fy + lab[..., 1] / 500
    fz = fy - lab[..., 2] / 200
    f = np.stack([fx, fy, fz], -1)
    xyz = np.where(f ** 3 > 216 / 24389, f ** 3, (116 * f - 16) / (24389 / 27)) * _WHITE
    c = xyz @ np.linalg.inv(_M).T
    c = np.clip(c, 0, 1)
    c = np.where(c <= 0.0031308, 12.92 * c, 1.055 * np.power(c, 1 / 2.4) - 0.055)
    return np.clip(np.round(c * 255), 0, 255).astype(int)


def ciede2000(lab1, lab2):
    """CIEDE2000 colour difference (kL = kC = kH = 1); broadcasts over leading dimensions."""
    lab1, lab2 = np.asarray(lab1, float), np.asarray(lab2, float)
    L1, a1, b1 = lab1[..., 0], lab1[..., 1], lab1[..., 2]
    L2, a2, b2 = lab2[..., 0], lab2[..., 1], lab2[..., 2]
    C1, C2 = np.hypot(a1, b1), np.hypot(a2, b2)
    Cb = (C1 + C2) / 2
    G = 0.5 * (1 - np.sqrt(Cb ** 7 / (Cb ** 7 + 25.0 ** 7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = np.hypot(a1p, b1), np.hypot(a2p, b2)
    h1p = np.degrees(np.arctan2(b1, a1p)) % 360
    h2p = np.degrees(np.arctan2(b2, a2p)) % 360
    dLp = L2 - L1
    dCp = C2p - C1p
    dh = h2p - h1p
    dh = np.where(dh > 180, dh - 360, np.where(dh < -180, dh + 360, dh))
    dh = np.where(C1p * C2p == 0, 0.0, dh)
    dHp = 2 * np.sqrt(C1p * C2p) * np.sin(np.radians(dh) / 2)
    Lbp = (L1 + L2) / 2
    Cbp = (C1p + C2p) / 2
    hs = h1p + h2p
    hbp = np.where(np.abs(h1p - h2p) > 180, np.where(hs < 360, (hs + 360) / 2, (hs - 360) / 2), hs / 2)
    hbp = np.where(C1p * C2p == 0, hs, hbp)
    T = (1 - 0.17 * np.cos(np.radians(hbp - 30)) + 0.24 * np.cos(np.radians(2 * hbp))
         + 0.32 * np.cos(np.radians(3 * hbp + 6)) - 0.20 * np.cos(np.radians(4 * hbp - 63)))
    dtheta = 30 * np.exp(-(((hbp - 275) / 25) ** 2))
    Rc = 2 * np.sqrt(Cbp ** 7 / (Cbp ** 7 + 25.0 ** 7))
    Sl = 1 + 0.015 * (Lbp - 50) ** 2 / np.sqrt(20 + (Lbp - 50) ** 2)
    Sc = 1 + 0.045 * Cbp
    Sh = 1 + 0.015 * Cbp * T
    Rt = -np.sin(np.radians(2 * dtheta)) * Rc
    return np.sqrt((dLp / Sl) ** 2 + (dCp / Sc) ** 2 + (dHp / Sh) ** 2 + Rt * (dCp / Sc) * (dHp / Sh))


def colour_stats(img, mask):
    """Median Lab of the masked pixels and their spread (median dE00 of each pixel to that median, and P10-P90 of
    L*). None when the mask is empty."""
    px = img[mask]
    if len(px) == 0:
        return None
    lab = srgb_to_lab(px)
    med = np.median(lab, axis=0)
    de = ciede2000(lab, med[None, :])
    return {"lab": med, "srgb": lab_to_srgb(med).tolist(), "n": int(len(px)),
            "spread_de00": float(np.median(de)), "L_p10_p90": float(np.percentile(lab[:, 0], 90)
                                                                    - np.percentile(lab[:, 0], 10))}


def colour_difference(ref, ren):
    """ref/ren: colour_stats dicts. dE00 of the medians, luma-matched dE00 (VISUAL_TARGET: compare after matching
    the patch median luma), and the signed lightness / chroma / hue differences (render minus reference)."""
    a, b = ref["lab"], ren["lab"]
    bm = np.array([a[0], b[1], b[2]])
    ca, cb = math.hypot(a[1], a[2]), math.hypot(b[1], b[2])
    ha, hb = math.degrees(math.atan2(a[2], a[1])) % 360, math.degrees(math.atan2(b[2], b[1])) % 360
    dh = (hb - ha + 180) % 360 - 180
    return {"de00": float(ciede2000(a, b)), "de00_luma_matched": float(ciede2000(a, bm)),
            "dL": float(b[0] - a[0]), "dC": float(cb - ca), "dh_deg": float(dh),
            "spread_ratio": float(ren["spread_de00"] / ref["spread_de00"]) if ref["spread_de00"] > 0 else None}


# ---------------------------------------------------------------------------------------------------- silhouettes
def iou(a, b):
    """Intersection over union of two boolean masks; None when both are empty."""
    a, b = np.asarray(a, bool), np.asarray(b, bool)
    u = np.logical_or(a, b).sum()
    if u == 0:
        return None
    return float(np.logical_and(a, b).sum() / u)


def bbox(mask):
    ys, xs = np.nonzero(mask)
    if len(ys) == 0:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def column_bottom(mask, x, x_halfwidth=2):
    """Lowest figure row in a narrow column around x (used for 'foot' points on both sides)."""
    h, w = mask.shape
    x0, x1 = max(0, int(round(x)) - x_halfwidth), min(w, int(round(x)) + x_halfwidth + 1)
    ys = np.nonzero(mask[:, x0:x1].any(axis=1))[0]
    return float(ys.max() + 1) if len(ys) else None


def crotch_y(mask, x, bottom):
    """First figure row above the floor gap between the legs at column x; None if there is no gap."""
    col = mask[:, int(round(x))]
    y = int(bottom) - 1
    while y > 0 and col[y]:
        y -= 1
    if int(bottom) - 1 - y > 2:  # the column starts inside a foot: no gap here
        return None
    while y > 0 and not col[y]:
        y -= 1
    return float(y + 1) if y > 0 else None


def width_at(mask, y):
    row = np.nonzero(mask[int(round(y))])[0] if 0 <= int(round(y)) < mask.shape[0] else []
    return float(row.max() - row.min() + 1) if len(row) else 0.0


def edge_roughness(mask):
    """Silhouette perimeter divided by the perimeter of a smoothed copy (>= 1; fuzz/locks raise it)."""
    def perim(m):
        m = m.astype(np.int8)
        return float(np.abs(np.diff(m, axis=0)).sum() + np.abs(np.diff(m, axis=1)).sum())
    sm = blur(mask.astype(float), 3.0) > 0.5
    p = perim(sm)
    return perim(mask) / p if p > 0 else None


# ------------------------------------------------------------------------------------------------------ landmarks
def landmark_errors(ref, ren, scale, y_only=()):
    """ref, ren: {name: (x, y)} in the same pixel frame; scale: normaliser (head height in px).
    Names in y_only (height markers such as hem lines) are compared on y only. Returns {name: error / scale}."""
    out = {}
    for k in sorted(set(ref) & set(ren)):
        (x1, y1), (x2, y2) = ref[k], ren[k]
        d = abs(y2 - y1) if k in y_only or any(k.startswith(p) for p in y_only) else math.hypot(x2 - x1, y2 - y1)
        out[k] = d / scale
    return out


# -------------------------------------------------------------------------------------------------------- texture
def _kernel(sigma):
    r = max(1, int(math.ceil(3 * sigma)))
    x = np.arange(-r, r + 1, dtype=float)
    k = np.exp(-0.5 * (x / sigma) ** 2)
    return k / k.sum()


def blur(a, sigma):
    """Separable Gaussian blur with edge padding."""
    k = _kernel(sigma)
    r = len(k) // 2
    p = np.pad(np.asarray(a, float), r, mode="edge")
    p = np.apply_along_axis(lambda v: np.convolve(v, k, mode="valid"), 0, p)
    p = np.apply_along_axis(lambda v: np.convolve(v, k, mode="valid"), 1, p)
    return p


def masked_blur(a, mask, sigma):
    m = mask.astype(float)
    num, den = blur(a * m, sigma), blur(m, sigma)
    return np.where(den > 1e-6, num / np.maximum(den, 1e-6), 0.0)


def erode(mask, r=1):
    m = mask.copy()
    for _ in range(r):
        p = np.pad(m, 1, constant_values=False)
        m = p[1:-1, 1:-1] & p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:]
    return m


def luma(img):
    c = np.asarray(img, float)
    return 0.299 * c[..., 0] + 0.587 * c[..., 1] + 0.114 * c[..., 2]


def texture_stats(img, mask, px_per_h=1.0):
    """VISUAL_TARGET texture statistics inside a region. px_per_h scales the blur sizes from the H = 256 px
    convention to the image (blur sigma = size / 6 * px_per_h)."""
    core = erode(mask, 2)
    if core.sum() < 30:
        return None
    y = luma(img)
    s9 = max(0.5, 9 / 6 * px_per_h)
    s31 = max(1.0, 31 / 6 * px_per_h)
    hf = y - masked_blur(y, mask, s9)
    ratio = y / np.maximum(masked_blur(y, mask, s31), 1.0)
    lap = (np.roll(y, 1, 0) + np.roll(y, -1, 0) + np.roll(y, 1, 1) + np.roll(y, -1, 1) - 4 * y)
    c = np.asarray(img, float)
    mx, mn = c.max(axis=-1), c.min(axis=-1)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
    r = ratio[core]
    return {"fuzz_hf_rms": float(np.sqrt(np.mean(hf[core] ** 2))),
            "sheen_p90_p50": float(np.percentile(r, 90) / max(np.percentile(r, 50), 1e-6)),
            "laplacian_var": float(np.var(lap[erode(core, 1)])) if erode(core, 1).sum() > 10 else None,
            "saturation_median": float(np.median(sat[core]))}


# ------------------------------------------------------------------------------------------------------- scoring
def clamp01(v):
    return max(0.0, min(1.0, v))


def mean(vals):
    vals = [v for v in vals if v is not None]
    return float(sum(vals) / len(vals)) if vals else None


def rounded(o, nd=4):
    if isinstance(o, float):
        return round(o, nd) if math.isfinite(o) else None
    if isinstance(o, dict):
        return {k: rounded(v, nd) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [rounded(v, nd) for v in o]
    if isinstance(o, np.generic):
        return rounded(o.item(), nd)
    if isinstance(o, np.ndarray):
        return rounded(o.tolist(), nd)
    return o


def dumps(o):
    """Deterministic JSON: sorted keys, rounded floats, one-space indent."""
    return json.dumps(rounded(o), sort_keys=True, indent=1) + "\n"
