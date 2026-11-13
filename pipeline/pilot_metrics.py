"""Additional comparison metrics for a harness run (see docs/BLENDER_COMPARISON_HARNESS.md and the hybrid feasibility
study §9): outline contour distance, hair contour distance, face-landmark ratios and region colour difference (ΔE2000).

    python3 pipeline/pilot_metrics.py --index <reference_index.json> --harness <dir with view renders + cameras.json> \
        [--regions <dir with <view>_beauty.png / <view>_id.png>] [--landmarks <landmarks.json>] --out <metrics.json>

Silhouettes are aligned exactly as in compare_sheet.py (scaled to the reference figure height, feet and centre aligned)."""
import argparse
import json
import os
import sys

import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from compare_sheet import align, bbox, measures  # noqa: E402

REGION_BANDS = {"hair": (0.0, 0.30), "skin": (0.25, 0.38), "hoodie": (0.40, 0.66), "trousers": (0.70, 0.88),
                "shoe": (0.90, 1.0), "cream": (0.93, 1.0)}
ID = {"hair": (255, 0, 0), "skin": (0, 255, 0), "hoodie": (0, 0, 255), "trousers": (255, 255, 0), "shoe": (255, 0, 255),
      "cream": (0, 255, 255)}


def outline(mask):
    e = np.asarray(Image.fromarray(mask.astype(np.uint8) * 255).filter(ImageFilter.FIND_EDGES)) > 0
    ys, xs = np.nonzero(e & mask)
    return np.stack([xs, ys], 1).astype(float)


def nearest(a, b):
    out = np.empty(len(a))
    for i in range(0, len(a), 2048):
        d = ((a[i:i + 2048, None, :] - b[None, :, :]) ** 2).sum(2)
        out[i:i + 2048] = np.sqrt(d.min(1))
    return out


def contour(ref_mask, sub_mask, head_fraction):
    ry0, ry1 = bbox(ref_mask)[1], bbox(ref_mask)[3]
    h = ry1 - ry0
    A, B = outline(ref_mask), outline(sub_mask)
    da, db = nearest(A, B), nearest(B, A)
    both = np.concatenate([da, db])
    band = ry0 + 0.30 * h  # hair zone: above the brow line in every measured view
    ha, hb = da[A[:, 1] < band], db[B[:, 1] < band]
    hboth = np.concatenate([ha, hb])
    head_h = head_fraction * h
    return {"contour_mean_pct_height": round(100 * float(both.mean()) / h, 2),
            "contour_p95_pct_height": round(100 * float(np.percentile(both, 95)) / h, 2),
            "hair_contour_mean_pct_head": round(100 * float(hboth.mean()) / head_h, 2),
            "hair_contour_p95_pct_head": round(100 * float(np.percentile(hboth, 95)) / head_h, 2)}


def align_points(pts, sub_mask, ref_mask):
    rx0, ry0, rx1, ry1 = bbox(ref_mask)
    sx0, sy0, sx1, sy1 = bbox(sub_mask)
    s = (ry1 - ry0) / (sy1 - sy0)
    w = max(1, round((sx1 - sx0) * s))
    ox = round((rx0 + rx1) / 2 - w / 2)
    return {k: ((x - sx0) * s + ox, (y - sy0) * s + ry0) for k, (x, y) in pts.items()}


def landmark_ratios(p, figure_bottom, h):
    ew = abs(p["ear_L"][0] - p["ear_R"][0])
    eye_y = (p["eye_L"][1] + p["eye_R"][1]) / 2
    return {"eye_spacing/ear_width": abs(p["eye_L"][0] - p["eye_R"][0]) / ew,
            "mouth_below_eyes/ear_width": (p["mouth"][1] - eye_y) / ew,
            "nose_below_eyes/ear_width": (p["nose"][1] - eye_y) / ew,
            "chin_below_eyes/ear_width": (p["chin"][1] - eye_y) / ew,
            "ear_width/height": ew / h,
            "eye_line_from_feet/height": (figure_bottom - eye_y) / h}


def to_lab(rgb):
    c = np.asarray(rgb, float) / 255
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = M @ c / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > (6 / 29) ** 3, np.cbrt(xyz), xyz / (3 * (6 / 29) ** 2) + 4 / 29)
    return np.array([116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2])])


def de2000(rgb1, rgb2):
    L1, a1, b1 = to_lab(rgb1)
    L2, a2, b2 = to_lab(rgb2)
    C1, C2 = np.hypot(a1, b1), np.hypot(a2, b2)
    Cm = (C1 + C2) / 2
    G = 0.5 * (1 - np.sqrt(Cm ** 7 / (Cm ** 7 + 25 ** 7)))
    a1p, a2p = a1 * (1 + G), a2 * (1 + G)
    C1p, C2p = np.hypot(a1p, b1), np.hypot(a2p, b2)
    h1p, h2p = np.degrees(np.arctan2(b1, a1p)) % 360, np.degrees(np.arctan2(b2, a2p)) % 360
    dL, dC = L2 - L1, C2p - C1p
    dh = h2p - h1p
    if C1p * C2p == 0:
        dh = 0
    elif dh > 180:
        dh -= 360
    elif dh < -180:
        dh += 360
    dH = 2 * np.sqrt(C1p * C2p) * np.sin(np.radians(dh / 2))
    Lm, Cmp = (L1 + L2) / 2, (C1p + C2p) / 2
    hs = h1p + h2p
    hm = hs / 2 if abs(h1p - h2p) <= 180 else ((hs + 360) / 2 if hs < 360 else (hs - 360) / 2)
    if C1p * C2p == 0:
        hm = hs
    T = 1 - 0.17 * np.cos(np.radians(hm - 30)) + 0.24 * np.cos(np.radians(2 * hm)) + 0.32 * np.cos(np.radians(3 * hm + 6)) \
        - 0.20 * np.cos(np.radians(4 * hm - 63))
    SL = 1 + 0.015 * (Lm - 50) ** 2 / np.sqrt(20 + (Lm - 50) ** 2)
    SC, SH = 1 + 0.045 * Cmp, 1 + 0.015 * Cmp * T
    RT = -2 * np.sqrt(Cmp ** 7 / (Cmp ** 7 + 25 ** 7)) * np.sin(np.radians(60 * np.exp(-((hm - 275) / 25) ** 2)))
    return float(np.sqrt((dL / SL) ** 2 + (dC / SC) ** 2 + (dH / SH) ** 2 + RT * (dC / SC) * (dH / SH)))


def reference_regions(img, mask):
    """Same colour classes and height bands as the reference colour measurement."""
    a = np.asarray(img, float) / 255
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mx, mn = a.max(2), a.min(2)
    sat, lum = (mx - mn) / (mx + 1e-6), 0.299 * r + 0.587 * g + 0.114 * b
    d = mx - mn + 1e-6
    hue = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
    ys = np.nonzero(mask.any(1))[0]
    y0, y1 = ys.min(), ys.max() + 1
    f = (np.arange(a.shape[0])[:, None] - y0) / (y1 - y0) * np.ones((1, a.shape[1]))
    dark = (lum < 0.32) & mask
    yellow = (hue > 28) & (hue < 55) & (sat > 0.45) & (mx > 0.45) & mask & ~dark
    cream = (sat < 0.25) & (lum > 0.72) & mask & ~dark
    skin = mask & ~dark & ~yellow & ~cream & (r > 0.55) & (r > b + 0.05)
    cls = {"hair": dark, "skin": skin, "hoodie": yellow, "trousers": dark, "shoe": yellow, "cream": cream}
    out = {}
    for k, (lo, hi) in REGION_BANDS.items():
        m = cls[k] & (f >= lo) & (f < hi)
        if m.sum() >= 30:
            out[k] = np.asarray(img, float)[m].mean(0)
    return out


def subject_regions(beauty, idimg):
    b = np.asarray(Image.open(beauty).convert("RGBA"), float)
    ids = np.asarray(Image.open(idimg).convert("RGB"), int)
    alpha = b[..., 3] > 127
    ys = np.nonzero(alpha.any(1))[0]
    y0, y1 = ys.min(), ys.max() + 1
    f = (np.arange(b.shape[0])[:, None] - y0) / (y1 - y0) * np.ones((1, b.shape[1]))
    out = {}
    for k, col in ID.items():
        m = (np.abs(ids - np.array(col)).sum(2) < 60) & alpha
        m = np.asarray(Image.fromarray(m.astype(np.uint8) * 255).filter(ImageFilter.MinFilter(5))) > 127
        lo, hi = REGION_BANDS[k]
        m &= (f >= lo) & (f < hi)
        if m.sum() >= 30:
            out[k] = b[..., :3][m].mean(0)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", required=True)
    ap.add_argument("--harness", required=True)
    ap.add_argument("--regions", default="")
    ap.add_argument("--landmarks", default="")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    index = json.load(open(a.index))
    vdir = os.path.join(os.path.dirname(a.index), "views")
    cams = json.load(open(os.path.join(a.harness, "cameras.json")))
    cam = {v["id"]: v for v in cams["views"]}
    lmref = json.load(open(a.landmarks))["views"] if a.landmarks else {}
    res = {"views": {}}
    for v in index["views"]:
        mpath = os.path.join(vdir, v["id"] + "_mask.png")
        rpath = os.path.join(a.harness, v["id"] + ".png")
        if not (v.get("silhouette") and os.path.exists(mpath) and os.path.exists(rpath)):
            continue
        ref_mask = np.asarray(Image.open(mpath)) > 127
        sub_mask = np.asarray(Image.open(rpath).convert("RGBA"))[:, :, 3] > 127
        al = align(sub_mask, ref_mask)
        hf = measures(ref_mask)["head_fraction"]
        e = {"iou": round(float((al & ref_mask).sum() / (al | ref_mask).sum()), 3)}
        e.update(contour(ref_mask, al, hf))
        if v["id"] in lmref and "landmarks_px" in cam.get(v["id"], {}):
            ry0, ry1 = bbox(ref_mask)[1], bbox(ref_mask)[3]
            h = ry1 - ry0
            sub_pts = align_points({k: tuple(p[:2]) for k, p in cam[v["id"]]["landmarks_px"].items()}, sub_mask, ref_mask)
            rr, ss = landmark_ratios(lmref[v["id"]], ry1, h), landmark_ratios(sub_pts, ry1, h)
            e["landmarks"] = {k: {"reference": round(rr[k], 3), "subject": round(ss[k], 3),
                                  "error_pct": round(100 * (ss[k] - rr[k]) / abs(rr[k]), 1)} for k in rr}
        if a.regions and os.path.exists(os.path.join(a.regions, v["id"] + "_beauty.png")):
            ref_img = Image.open(os.path.join(vdir, v["id"] + ".png")).convert("RGB")
            rc = reference_regions(ref_img, ref_mask)
            sc = subject_regions(os.path.join(a.regions, v["id"] + "_beauty.png"), os.path.join(a.regions, v["id"] + "_id.png"))
            e["colour"] = {k: {"reference": np.round(rc[k]).astype(int).tolist(), "subject": np.round(sc[k]).astype(int).tolist(),
                               "dE2000": round(de2000(rc[k], sc[k]), 1)} for k in rc if k in sc}
        res["views"][v["id"]] = e
    V = res["views"].values()
    summ = {"views": len(res["views"]),
            "mean_iou": round(float(np.mean([e["iou"] for e in V])), 3),
            "mean_contour_pct_height": round(float(np.mean([e["contour_mean_pct_height"] for e in V])), 2),
            "mean_hair_contour_pct_head": round(float(np.mean([e["hair_contour_mean_pct_head"] for e in V])), 2)}
    lm = [e["landmarks"] for e in V if "landmarks" in e]
    if lm:
        summ["landmark_max_abs_error_pct"] = max(abs(x["error_pct"]) for d in lm for x in d.values())
    col = [e["colour"] for e in V if "colour" in e]
    if col:
        regions = sorted({k for d in col for k in d})
        summ["mean_dE2000"] = {k: round(float(np.mean([d[k]["dE2000"] for d in col if k in d])), 1) for k in regions}
    res["summary"] = summ
    json.dump(res, open(a.out, "w"), indent=1)
    print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    main()
