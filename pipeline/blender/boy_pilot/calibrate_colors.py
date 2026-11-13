"""Automated albedo calibration for the boy pilot (runs with the system Python; calls Blender headless).

    python3 pipeline/blender/boy_pilot/calibrate_colors.py --blender "<blender or python+bpy runner>" --out <dir> [--iters 3]

Loop: build the model -> render beauty + region-ID images from the harness cameras (front, side, back) -> measure the
mean rendered colour per region in the same height bands used for the reference measurement -> scale each albedo in
linear space by (reference / rendered) -> write albedo_calibration.json (read by build_boy_pilot.py). The targets are
the colours measured on references #7 and #27 (docs/evaluation/boy_pilot/), i.e. the result matches the references
under the harness lighting, not an absolute paint colour."""
import argparse
import json
import os
import shlex
import subprocess
import sys

import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CAL = os.path.join(HERE, "albedo_calibration.json")
# Reference colours (sRGB), mean of #7 front and #27 front/side/back, measured in these figure-height bands.
TARGETS = {"hair": (48, 39, 36), "skin": (193, 144, 122), "hoodie": (192, 145, 80), "trousers": (40, 33, 32),
           "shoe": (184, 139, 77), "cream": (210, 197, 188)}
BANDS = {"hair": (0.0, 0.30), "skin": (0.25, 0.38), "hoodie": (0.40, 0.66), "trousers": (0.70, 0.88),
         "shoe": (0.90, 1.0), "cream": (0.93, 1.0)}
ID = {"hair": (255, 0, 0), "skin": (0, 255, 0), "hoodie": (0, 0, 255), "trousers": (255, 255, 0), "shoe": (255, 0, 255),
      "cream": (0, 255, 255)}
ALBEDO_KEYS = {"hair": ["hair", "hair_fur"], "skin": ["skin"], "hoodie": ["hoodie", "hoodie_fur"],
               "trousers": ["trousers", "trousers_fur"], "shoe": ["shoe", "shoe_fur"], "cream": ["cream"]}
DEFAULTS = {"skin": (226, 172, 146), "hair": (34, 31, 30), "hair_fur": (40, 36, 34), "hoodie": (206, 142, 48),
            "hoodie_fur": (210, 146, 52), "trousers": (36, 32, 32), "trousers_fur": (40, 36, 35), "shoe": (204, 142, 50),
            "shoe_fur": (208, 146, 54), "cream": (226, 214, 200)}


def to_lin(c):
    c = np.asarray(c, float) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def to_srgb(c):
    c = np.clip(np.asarray(c, float), 0, 1)
    return np.round(255 * np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)).astype(int)


def region_means(beauty_path, id_path):
    """Mean sRGB per region of a harness render, restricted to the region's figure-height band (eroded ID masks)."""
    b = np.asarray(Image.open(beauty_path).convert("RGBA"), float)
    idimg = np.asarray(Image.open(id_path).convert("RGB"), int)
    alpha = b[..., 3] > 127
    ys = np.nonzero(alpha.any(1))[0]
    y0, y1 = ys.min(), ys.max() + 1
    f = (np.arange(b.shape[0])[:, None] - y0) / (y1 - y0) * np.ones((1, b.shape[1]))
    out = {}
    for k, col in ID.items():
        m = (np.abs(idimg - np.array(col)).sum(2) < 60) & alpha
        m = np.asarray(Image.fromarray(m.astype(np.uint8) * 255).filter(ImageFilter.MinFilter(5))) > 127
        a, z = BANDS[k]
        m &= (f >= a) & (f < z)
        if m.sum() >= 30:
            out[k] = (b[..., :3][m].mean(0), int(m.sum()))
    return out


def run(cmd):
    r = subprocess.run(cmd, shell=True, cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stdout[-3000:] + r.stderr[-3000:])
        raise SystemExit(f"failed: {cmd}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blender", required=True, help="command prefix that runs a Blender script, e.g. 'blender -b -P'")
    ap.add_argument("--out", required=True)
    ap.add_argument("--iters", type=int, default=3)
    ap.add_argument("--fur-scale", type=float, default=0.5)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    alb = {k: list(v) for k, v in DEFAULTS.items()}
    if os.path.exists(CAL):
        alb.update(json.load(open(CAL)))
    history = []
    for it in range(a.iters + 1):
        json.dump(alb, open(CAL, "w"), indent=1)
        bd = os.path.join(a.out, f"iter{it}")
        run(f"{a.blender} pipeline/blender/boy_pilot/build_boy_pilot.py -- --out {shlex.quote(bd)} --stage model --fur-scale {a.fur_scale}")
        run(f"{a.blender} pipeline/blender/boy_pilot/render_regions.py -- {shlex.quote(bd)}/boy_yellow_hoodie_pilot_compare.blend "
            f"assets/characters/boy_yellow_hoodie/references/reference_index.json {shlex.quote(bd)}/regions")
        acc = {}
        for v in ("val27_front", "val27_side_right", "val27_back"):
            for k, (mean, n) in region_means(f"{bd}/regions/{v}_beauty.png", f"{bd}/regions/{v}_id.png").items():
                acc.setdefault(k, []).append((mean, n))
        measured = {k: np.average([m for m, _ in vals], axis=0, weights=[n for _, n in vals]) for k, vals in acc.items()}
        row = {"iteration": it, "albedo": {k: list(map(int, v)) for k, v in alb.items()},
               "rendered": {k: [round(float(x), 1) for x in v] for k, v in measured.items()},
               "target": TARGETS}
        history.append(row)
        print(f"iter {it}: " + ", ".join(f"{k} {np.round(measured[k]).astype(int).tolist()}/{list(TARGETS[k])}" for k in measured), flush=True)
        if it == a.iters:
            break
        for k, keys in ALBEDO_KEYS.items():
            if k not in measured:
                continue
            ratio = to_lin(TARGETS[k]) / np.maximum(to_lin(measured[k]), 1e-4)
            ratio = np.clip(ratio, 0.4, 2.5)
            for key in keys:
                alb[key] = to_srgb(np.clip(to_lin(alb[key]) * ratio, 0.002, 0.92)).tolist()
    json.dump(history, open(os.path.join(a.out, "calibration_history.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
