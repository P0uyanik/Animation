"""Fidelity score v2 metric functions (T-153, opt-in). Character-independent; numpy only.

Implements the T-129 ranked proposals (docs/evaluation/process/T-129/README.md):
 1. face states the owner reviews: closed-lid colour vs adjacent skin (Blink), pale band below the lens (neutral),
    mouth opening and contour vs labelled expression references; eye shape vs T-150 targets;
 2. re-weighted v1 components (silhouette 0.20 -> 0.13, face 0.05 -> 0.12), blended 80/20 with the face-state score;
 3. local hair / garment patch comparison (colour, texture, strand direction) reported per region, never pooled.
Boxes are [x0, y0, x1, y1] pixels in the image passed in. v1 (tools/fidelity/metrics.py) is reused, never changed."""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import metrics as M  # noqa: E402

V1_WEIGHTS = {"silhouette": 0.20, "regions": 0.10, "landmarks": 0.15, "proportions": 0.10, "colour": 0.10,
              "texture": 0.05, "hair": 0.15, "skin": 0.10, "face": 0.05}
# T-129 proposal 2: seven points from silhouette to face; frozen here before the next owner review.
V2_WEIGHTS = dict(V1_WEIGHTS, silhouette=0.13, face=0.12)
FACE_STATE_BLEND = 0.20      # T-129 proposal 1: 80% re-weighted total + 20% face-state score
LID_DE_SCALE = 20.0          # dE00 between closed lid and adjacent skin that scores 0
SHELF_DL = 5.0               # a shelf pixel is this much lighter (L*) than adjacent skin ...
SHELF_DC = 3.0               # ... and this much less chromatic
SHELF_FULL = 0.5             # pale fraction of the band that scores 0
MOUTH_DARK_DL = 25.0         # mouth interior: L* this far below the box's skin (P75 L*)
CURVE_SCALE = 0.15           # contour curvature difference (in box widths) that scores 0
LOCAL_DE_SCALE = 20.0


def crop(img, box):
    x0, y0, x1, y1 = (int(round(v)) for v in box)
    return np.asarray(img)[y0:y1, x0:x1]


def median_lab(px):
    return np.median(M.srgb_to_lab(np.asarray(px, float).reshape(-1, 3)), axis=0)


# ------------------------------------------------------------------------------------------- 1. face states
def lid_skin_contrast(img, lid_box, skin_box):
    """Closed-lid colour vs adjacent skin: dE00 of the medians and a score (1 = lid reads as skin)."""
    lid, skin = median_lab(crop(img, lid_box)), median_lab(crop(img, skin_box))
    de = float(M.ciede2000(lid, skin))
    return {"de00": de, "dL": float(lid[0] - skin[0]), "score": M.clamp01(1 - de / LID_DE_SCALE)}


def shelf_fraction(img, band_box, skin_box):
    """Pale band below a lens: fraction of band pixels lighter and less chromatic than adjacent skin."""
    band = M.srgb_to_lab(crop(img, band_box).reshape(-1, 3).astype(float))
    skin = median_lab(crop(img, skin_box))
    c_band, c_skin = np.hypot(band[:, 1], band[:, 2]), math.hypot(skin[1], skin[2])
    pale = (band[:, 0] > skin[0] + SHELF_DL) & (c_band < c_skin - SHELF_DC)
    f = float(pale.mean()) if len(pale) else 0.0
    return {"fraction": f, "score": M.clamp01(1 - f / SHELF_FULL)}


def mouth_shape(img, box):
    """Mouth opening (dark interior fraction of the box) and contour curvature: (centre y - mean corner y) of the
    mouth-line centroid per column (pixels darker than skin by half MOUTH_DARK_DL), in box widths. Positive = corners up (smile), negative = corners down (pout)."""
    lab = M.srgb_to_lab(crop(img, box).astype(float))
    L = lab[..., 0]
    skin_L = float(np.percentile(L, 75))
    dark = L < skin_L - MOUTH_DARK_DL
    h, w = L.shape
    line = L < skin_L - 0.5 * MOUTH_DARK_DL
    cols = [x for x in range(w) if line[:, x].any()]
    curve = 0.0
    if len(cols) >= 5:
        ys = np.array([float(np.nonzero(line[:, x])[0].mean()) for x in cols])
        n = max(1, len(cols) // 5)
        corners = (ys[:n].mean() + ys[-n:].mean()) / 2
        centre = ys[len(ys) // 2 - n // 2: len(ys) // 2 - n // 2 + n].mean()
        curve = float((centre - corners) / w)
    return {"open": float(dark.mean()), "curve": curve, "line_cols": len(cols)}


def mouth_match(ren, ref):
    """Score a rendered mouth_shape against a reference mouth_shape (1 = same opening and contour)."""
    o = 1 - abs(ren["open"] - ref["open"]) / max(ref["open"], ren["open"], 0.05)
    c = 1 - abs(ren["curve"] - ref["curve"]) / CURVE_SCALE
    return {"open": M.clamp01(o), "curve": M.clamp01(c), "score": (M.clamp01(o) + M.clamp01(c)) / 2}


def eye_shape_score(measures, targets):
    """T-150 eye-shape bands: 1 inside value +- tolerance, falling linearly to 0 at two tolerances outside.
    measures: {key: value}; targets: {key: {value, tolerance}}. -> per-key scores, in-band fraction, mean score."""
    per = {}
    for k, t in targets.items():
        if k in measures and measures[k] is not None:
            excess = max(0.0, abs(float(measures[k]) - t["value"]) - t["tolerance"])
            per[k] = M.clamp01(1 - excess / (2 * t["tolerance"])) if t["tolerance"] > 0 else float(excess == 0)
    if not per:
        return None
    return {"per_key": per, "in_band": sum(v == 1.0 for v in per.values()) / len(per), "score": M.mean(per.values())}


def face_state_score(parts):
    """Mean of the available state scores ({name: score or None}); None when nothing was measured."""
    return M.mean(parts.values())


# ---------------------------------------------------------------------------------------- 2. combined score
def reweighted(subscores, weights=None):
    """v1 subscores (0..1, None = missing) re-weighted (default V2_WEIGHTS) -> 0..100, renormalised as v1."""
    w = weights or V2_WEIGHTS
    ws = sum(w[k] for k, v in subscores.items() if v is not None and k in w)
    return 100 * sum(w[k] * v for k, v in subscores.items() if v is not None and k in w) / ws if ws else None


def v2_total(subscores, face_states=None):
    """v2 total: re-weighted v1 components, blended 80/20 with the face-state score (0..1) when one was measured."""
    base = reweighted(subscores)
    if base is None or face_states is None:
        return base
    return (1 - FACE_STATE_BLEND) * base + FACE_STATE_BLEND * 100 * face_states


# ------------------------------------------------------------------------------------- 3. local hair/garment
def orientation(gray):
    """Dominant gradient angle (deg, 0..180) and coherence (0..1) from the structure tensor."""
    g = np.asarray(gray, float)
    gy, gx = np.gradient(g)
    jxx, jyy, jxy = (gx * gx).mean(), (gy * gy).mean(), (gx * gy).mean()
    tr = jxx + jyy
    coh = math.sqrt((jxx - jyy) ** 2 + 4 * jxy ** 2) / tr if tr > 0 else 0.0
    return {"angle_deg": math.degrees(0.5 * math.atan2(2 * jxy, jxx - jyy)) % 180, "coherence": coh}


def local_patch(ref_img, ref_box, ren_img, ren_box):
    """Compare one local region (crown, fringe, back locks, collar edge ...) of a render to a matched reference crop:
    luma-matched dE00, fuzz and sheen log2 ratios (v1 texture statistics), strand direction and coherence."""
    a, b = crop(ref_img, ref_box), crop(ren_img, ren_box)
    ma, mb = np.ones(a.shape[:2], bool), np.ones(b.shape[:2], bool)
    ca, cb = M.colour_stats(a, ma), M.colour_stats(b, mb)
    cd = M.colour_difference(ca, cb)
    pa = a.shape[0] / 256.0
    ta, tb = M.texture_stats(a, ma, pa), M.texture_stats(b, mb, b.shape[0] / 256.0)
    oa, ob = orientation(M.luma(a)), orientation(M.luma(b))
    fuzz = math.log2(max(tb["fuzz_hf_rms"], 1e-6) / max(ta["fuzz_hf_rms"], 1e-6))
    sheen = math.log2(max(tb["sheen_p90_p50"], 1e-6) / max(ta["sheen_p90_p50"], 1e-6))
    dang = abs((ob["angle_deg"] - oa["angle_deg"] + 90) % 180 - 90)
    parts = {"colour": M.clamp01(1 - cd["de00_luma_matched"] / LOCAL_DE_SCALE),
             "fuzz": M.clamp01(1 - abs(fuzz)), "sheen": M.clamp01(1 - abs(sheen) / 0.5),
             "direction": M.clamp01(1 - dang / 45.0) * 0.5 + M.clamp01(1 - abs(ob["coherence"] - oa["coherence"]) / 0.5) * 0.5}
    return {"de00_luma_matched": cd["de00_luma_matched"], "log2_fuzz": fuzz, "log2_sheen": sheen,
            "angle_diff_deg": dang, "coherence_ref": oa["coherence"], "coherence_ren": ob["coherence"],
            "parts": parts, "score": M.mean(parts.values())}
