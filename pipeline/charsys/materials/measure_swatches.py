"""Measure VISUAL_TARGET material metrics from a rendered T-015 swatch sheet.

Runs in Blender so the relay needs no third-party system-Python packages:
blender -b --factory-startup -P pipeline/charsys/materials/measure_swatches.py -- \
  --image docs/evaluation/materials/T-015/swatch_sheet.png \
  --metadata docs/evaluation/materials/T-015/swatches.json \
  --out docs/evaluation/materials/T-015/metrics.json
"""
import argparse
import hashlib
import json
import math
import os
import sys

import bpy
import numpy as np


HERE = os.path.dirname(os.path.abspath(__file__))
CHARSYS = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, CHARSYS)
from materials import builder as MATERIALS  # noqa: E402


def parse():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--metadata", required=True)
    parser.add_argument("--out", required=True)
    return parser.parse_args(argv)


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def linear_to_srgb(values):
    return np.where(values <= 0.0031308, values * 12.92, 1.055 * np.power(values, 1 / 2.4) - 0.055)


def load_display_rgb(path):
    image = bpy.data.images.load(path, check_existing=False)
    width, height = image.size
    rgba = np.asarray(image.pixels[:], dtype=np.float64).reshape(height, width, 4)
    # Blender exposes a colour-managed sRGB PNG as scene-linear floats, bottom row first.
    rgb = np.flipud(linear_to_srgb(np.clip(rgba[:, :, :3], 0.0, 1.0)))
    return rgb, width, height


def gaussian_blur(values, kernel_px):
    radius = kernel_px // 2
    sigma = kernel_px / 6.0
    x = np.arange(-radius, radius + 1, dtype=np.float64)
    kernel = np.exp(-(x * x) / (2 * sigma * sigma))
    kernel /= kernel.sum()
    horizontal_pad = np.pad(values, ((0, 0), (radius, radius)), mode="reflect")
    horizontal = sum(weight * horizontal_pad[:, i:i + values.shape[1]] for i, weight in enumerate(kernel))
    vertical_pad = np.pad(horizontal, ((radius, radius), (0, 0)), mode="reflect")
    return sum(weight * vertical_pad[i:i + values.shape[0], :] for i, weight in enumerate(kernel))


def saturation(rgb):
    maximum = rgb.max(axis=2)
    minimum = rgb.min(axis=2)
    return np.divide(maximum - minimum, maximum, out=np.zeros_like(maximum), where=maximum > 1e-8)


def color_saturation(color):
    values = np.asarray(color, dtype=np.float64) / 255.0
    return 0.0 if values.max() <= 0 else float((values.max() - values.min()) / values.max())


def target_check(value, target):
    if target is None:
        return {"value": round(float(value), 4), "target": None, "pass": None, "source": None}
    lo, hi = target["range"]
    return {
        "value": round(float(value), 4),
        "target": [lo, hi],
        "pass": bool(lo <= value <= hi),
        "source": target["source"],
    }


def measure(rgb, base_color):
    luma = (0.2126 * rgb[:, :, 0] + 0.7152 * rgb[:, :, 1] + 0.0722 * rgb[:, :, 2]) * 255.0
    residual9 = luma - gaussian_blur(luma, 9)
    fuzz_rms = math.sqrt(float(np.mean(residual9 * residual9)))
    form = np.maximum(gaussian_blur(luma, 31), 1e-6)
    normalized = luma / form
    positive = normalized[normalized >= 1.0]
    if len(positive) < 2:
        sheen = 1.0
    else:
        p50, p90 = np.percentile(positive, [50, 90])
        sheen = float(p90 / max(p50, 1e-6))
    sat = saturation(rgb)
    s50, s90 = np.percentile(sat, [50, 90])
    input_sat = color_saturation(base_color)
    retention = float(s50 / input_sat * 100.0) if input_sat > 1e-6 else 100.0
    return {
        "fuzz_rms_y255": fuzz_rms,
        "sheen_p90_p50": sheen,
        "saturation_retention_percent": retention,
        "saturation_p50_percent": float(s50 * 100.0),
        "saturation_p90_percent": float(s90 * 100.0),
        "input_saturation_percent": input_sat * 100.0,
    }


def main():
    args = parse()
    image_path = os.path.abspath(args.image)
    metadata_path = os.path.abspath(args.metadata)
    out = os.path.abspath(args.out)
    metadata = json.load(open(metadata_path, encoding="utf-8"))
    library = MATERIALS.load_library()
    rgb, width, height = load_display_rgb(image_path)
    if (width, height) != (metadata["width"], metadata["height"]):
        raise SystemExit(f"image is {width}x{height}; metadata says {metadata['width']}x{metadata['height']}")

    results = []
    for swatch in metadata["swatches"]:
        x0, y0, x1, y1 = swatch["patch_roi_px"]
        if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
            raise SystemExit(f"invalid ROI for {swatch['preset']}: {swatch['patch_roi_px']}")
        raw = measure(rgb[y0:y1, x0:x1], swatch["base_color_srgb"])
        targets = library["presets"][swatch["preset"]]["targets"]
        checks = {name: target_check(raw[name], targets[name]) for name in
                  ("fuzz_rms_y255", "sheen_p90_p50", "saturation_retention_percent")}
        applicable = [item["pass"] for item in checks.values() if item["pass"] is not None]
        results.append({
            "preset": swatch["preset"],
            "patch_roi_px": swatch["patch_roi_px"],
            "metrics": {
                **checks,
                "saturation_p50_percent": round(raw["saturation_p50_percent"], 4),
                "saturation_p90_percent": round(raw["saturation_p90_percent"], 4),
                "input_saturation_percent": round(raw["input_saturation_percent"], 4),
            },
            "pass": all(applicable),
        })

    output = {
        "schema": "plush-studio.material-metrics/1",
        "visual_target": "docs/references/VISUAL_TARGET.md#materials",
        "image": os.path.relpath(image_path, os.getcwd()).replace("\\", "/"),
        "image_sha256": sha256(image_path),
        "metadata_sha256": sha256(metadata_path),
        "measurement": {
            "colour_space": "display sRGB reconstructed from Blender's linear image buffer",
            "luma": "Y' = 0.2126 R + 0.7152 G + 0.0722 B, 0..255",
            "fuzz_rms_y255": "RMS of luma minus a 9-pixel Gaussian kernel on the patch ROI",
            "sheen_p90_p50": "P90/P50 of positive luma/(31-pixel Gaussian form blur) residuals",
            "saturation": "(max-min)/max; retention is patch S50 divided by input-colour saturation",
        },
        "presets": results,
        "pass": all(item["pass"] for item in results),
    }
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(output, handle, indent=2)
        handle.write("\n")
    print(f"[measure_swatches] {'PASS' if output['pass'] else 'FAIL'} -> {out}")
    raise SystemExit(0 if output["pass"] else 1)


if __name__ == "__main__":
    main()
