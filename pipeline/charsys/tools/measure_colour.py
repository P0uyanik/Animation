"""Colour check of character renders against reference views (plain Python: numpy + Pillow; no Blender).

    python3 pipeline/charsys/tools/measure_colour.py <checks.json> <render_dir> <out.json> [--label name]

checks.json (character data): {"reference_dir": "<dir relative to the repo>", "checks": [
    {"name": "hair_back", "slot": "M_hair", "view": "sheet30_back", "ref_boxes": [[x0, y0, x1, y1], ...]}, ...]}
The render side is the median sRGB of every pixel of the material slot in <view>.png (from <view>_ids.png and ids.json
written by groom_turnaround.py --ids; the mask is eroded by one pixel against edge blending unless "erode": false). The reference side is the
median over the given boxes of the reference view. Reports both medians, CIEDE2000 (D65), luma Y' and saturation,
and the luma-matched dE00 (VISUAL_TARGET.md: compare Lab after matching the patch median luma)."""
import argparse
import json
import os

import numpy as np
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def srgb_to_lab(rgb):
    c = np.asarray(rgb, float) / 255.0
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    m = np.array([[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750], [0.0193339, 0.1191920, 0.9503041]])
    xyz = m @ c / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 216 / 24389, np.cbrt(xyz), (24389 / 27 * xyz + 16) / 116)
    return np.array([116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2])])


def de2000(lab1, lab2):
    L1, a1, b1 = lab1
    L2, a2, b2 = lab2
    C1, C2 = np.hypot(a1, b1), np.hypot(a2, b2)
    Cb = (C1 + C2) / 2
    G = 0.5 * (1 - np.sqrt(Cb ** 7 / (Cb ** 7 + 25 ** 7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = np.hypot(a1p, b1), np.hypot(a2p, b2)
    h1p, h2p = np.degrees(np.arctan2(b1, a1p)) % 360, np.degrees(np.arctan2(b2, a2p)) % 360
    dLp, dCp = L2 - L1, C2p - C1p
    dh = h2p - h1p
    if C1p * C2p == 0:
        dh = 0
    elif dh > 180:
        dh -= 360
    elif dh < -180:
        dh += 360
    dHp = 2 * np.sqrt(C1p * C2p) * np.sin(np.radians(dh / 2))
    Lbp, Cbp = (L1 + L2) / 2, (C1p + C2p) / 2
    if C1p * C2p == 0:
        hbp = h1p + h2p
    elif abs(h1p - h2p) <= 180:
        hbp = (h1p + h2p) / 2
    else:
        hbp = (h1p + h2p + 360) / 2 if h1p + h2p < 360 else (h1p + h2p - 360) / 2
    T = (1 - 0.17 * np.cos(np.radians(hbp - 30)) + 0.24 * np.cos(np.radians(2 * hbp))
         + 0.32 * np.cos(np.radians(3 * hbp + 6)) - 0.20 * np.cos(np.radians(4 * hbp - 63)))
    dth = 30 * np.exp(-(((hbp - 275) / 25) ** 2))
    Rc = 2 * np.sqrt(Cbp ** 7 / (Cbp ** 7 + 25 ** 7))
    Sl = 1 + 0.015 * (Lbp - 50) ** 2 / np.sqrt(20 + (Lbp - 50) ** 2)
    Sc, Sh = 1 + 0.045 * Cbp, 1 + 0.015 * Cbp * T
    Rt = -np.sin(np.radians(2 * dth)) * Rc
    return float(np.sqrt((dLp / Sl) ** 2 + (dCp / Sc) ** 2 + (dHp / Sh) ** 2 + Rt * (dCp / Sc) * (dHp / Sh)))


def luma(rgb):
    return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]


def sat(rgb):
    return (max(rgb) - min(rgb)) / max(1e-6, max(rgb))


def slot_median(render_dir, view, colour, erode=True):
    img = np.asarray(Image.open(os.path.join(render_dir, view + ".png")).convert("RGB")).astype(int)
    ids = np.asarray(Image.open(os.path.join(render_dir, view + "_ids.png")).convert("RGB")).astype(int)
    m = np.all(np.abs(ids - np.array(colour)) <= 2, axis=2)
    e = m.copy()  # one-pixel erosion (off for thin parts)
    if erode:
        e[1:, :] &= m[:-1, :]
        e[:-1, :] &= m[1:, :]
        e[:, 1:] &= m[:, :-1]
        e[:, :-1] &= m[:, 1:]
    if not e.any():
        return [float("nan")] * 3, 0
    px = img[e]
    return [float(v) for v in np.median(px, axis=0)], int(e.sum())


def box_median(path, boxes):
    img = np.asarray(Image.open(path).convert("RGB")).astype(int)
    px = np.concatenate([img[y0:y1, x0:x1].reshape(-1, 3) for x0, y0, x1, y1 in boxes])
    return [float(v) for v in np.median(px, axis=0)], int(len(px))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("checks")
    ap.add_argument("render_dir")
    ap.add_argument("out")
    ap.add_argument("--label", default="")
    a = ap.parse_args()
    cfg = json.load(open(a.checks))
    ids = json.load(open(os.path.join(a.render_dir, "ids.json")))
    ref_dir = os.path.join(ROOT, cfg["reference_dir"])
    rows = []
    for c in cfg["checks"]:
        r, n = slot_median(a.render_dir, c["view"], ids[c["slot"]], c.get("erode", True))
        t, nt = box_median(os.path.join(ref_dir, c["view"] + ".png"), c["ref_boxes"])
        lr, lt = luma(r), luma(t)
        r_matched = [min(255.0, v * lt / max(1e-6, lr)) for v in r]
        rows.append({"name": c["name"], "slot": c["slot"], "view": c["view"], "render_median_srgb": [round(v, 1) for v in r],
                     "render_pixels": n, "reference_median_srgb": [round(v, 1) for v in t], "reference_pixels": nt,
                     "dE00": round(de2000(srgb_to_lab(r), srgb_to_lab(t)), 2),
                     "dE00_luma_matched": round(de2000(srgb_to_lab(r_matched), srgb_to_lab(t)), 2),
                     "luma": [round(lr, 1), round(lt, 1)], "saturation": [round(sat(r), 3), round(sat(t), 3)]})
    out = {"label": a.label, "render_dir": a.render_dir, "checks": rows}
    json.dump(out, open(a.out, "w"), indent=1)
    for r in rows:
        print(f"{r['name']:<16} render {r['render_median_srgb']} ref {r['reference_median_srgb']} "
              f"dE00 {r['dE00']} (luma-matched {r['dE00_luma_matched']}) sat {r['saturation']}")


if __name__ == "__main__":
    main()
