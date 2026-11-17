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
import struct
import sys
import zlib

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


def load_display_rgb(path):
    """Decode exact 8-bit PNG display samples without Blender colour conversion.

    ``Image.pixels`` is scene-linear for some Blender/image combinations and
    display-referred for others.  That ambiguity caused the T-015/T-016
    saturation measurements to change when the same PNG was reloaded.  The
    evidence render is an 8-bit RGB(A), non-interlaced PNG, so a small stdlib
    decoder is both deterministic and the most direct implementation of the
    VISUAL_TARGET's final-display convention.
    """
    data = open(path, "rb").read()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"not a PNG: {path}")
    pos, payload, width, height, color_type, bit_depth, interlace = 8, [], None, None, None, None, None
    while pos < len(data):
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        kind = data[pos + 4:pos + 8]
        chunk = data[pos + 8:pos + 8 + length]
        pos += 12 + length
        if kind == b"IHDR":
            width, height, bit_depth, color_type, _compression, _filter, interlace = struct.unpack(">IIBBBBB", chunk)
        elif kind == b"IDAT":
            payload.append(chunk)
        elif kind == b"IEND":
            break
    if bit_depth != 8 or color_type not in (2, 6) or interlace != 0:
        raise ValueError(f"PNG must be non-interlaced 8-bit RGB/RGBA, got depth={bit_depth} type={color_type}")
    channels = 3 if color_type == 2 else 4
    packed = zlib.decompress(b"".join(payload))
    stride = width * channels
    rows = np.empty((height, stride), dtype=np.uint8)
    previous = np.zeros(stride, dtype=np.uint8)

    def paeth(a, b, c):
        p = a + b - c
        pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
        return a if pa <= pb and pa <= pc else (b if pb <= pc else c)

    offset = 0
    for y in range(height):
        method = packed[offset]
        raw = packed[offset + 1:offset + 1 + stride]
        offset += stride + 1
        row = np.empty(stride, dtype=np.uint8)
        for x, value in enumerate(raw):
            left = int(row[x - channels]) if x >= channels else 0
            up = int(previous[x])
            upper_left = int(previous[x - channels]) if x >= channels else 0
            if method == 0:
                decoded = value
            elif method == 1:
                decoded = value + left
            elif method == 2:
                decoded = value + up
            elif method == 3:
                decoded = value + ((left + up) // 2)
            elif method == 4:
                decoded = value + paeth(left, up, upper_left)
            else:
                raise ValueError(f"unsupported PNG filter {method}")
            row[x] = decoded & 255
        rows[y] = row
        previous = row
    rgb = rows.reshape(height, width, channels)[:, :, :3].astype(np.float64) / 255.0
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


def srgb_to_linear(values):
    values = np.asarray(values, dtype=np.float64)
    return np.where(values <= 0.04045, values / 12.92, ((values + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(values):
    values = np.maximum(np.asarray(values, dtype=np.float64), 0.0)
    return np.where(values <= 0.0031308, values * 12.92, 1.055 * values ** (1.0 / 2.4) - 0.055)


def neutral_adapt(rgb, neutral_rgb):
    """Remove the measured neutral-card cast while preserving mean exposure."""
    neutral = np.median(srgb_to_linear(neutral_rgb).reshape(-1, 3), axis=0)
    mean = max(float(neutral.mean()), 1e-8)
    channel_gain = np.maximum(neutral / mean, 1e-8)
    return np.clip(linear_to_srgb(srgb_to_linear(rgb) / channel_gain), 0.0, 1.0)


def resize_bilinear(values, scale):
    if abs(scale - 1.0) < 1e-6:
        return values
    height, width = values.shape[:2]
    out_h, out_w = max(2, round(height * scale)), max(2, round(width * scale))
    xs = np.linspace(0.0, width - 1.0, out_w)
    ys = np.linspace(0.0, height - 1.0, out_h)
    x0 = np.floor(xs).astype(int)
    y0 = np.floor(ys).astype(int)
    x1 = np.minimum(x0 + 1, width - 1)
    y1 = np.minimum(y0 + 1, height - 1)
    wx = (xs - x0)[None, :, None]
    top = values[y0][:, x0] * (1.0 - wx) + values[y0][:, x1] * wx
    wy = (ys - y0)[:, None, None]
    return top * (1.0 - wy) + (values[y1][:, x0] * (1.0 - wx) + values[y1][:, x1] * wx) * wy


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


def patch_check(values, target):
    """VISUAL_TARGET "Common measurement setup" step 3 for three patches: report the median; a pass needs at least
    two of the three patches in range and none missing its nearest limit by more than 20 % of that limit. This
    implementation additionally requires the median itself to be in range (stricter, never looser)."""
    median = float(np.median(values))
    out = target_check(median, target)
    out["patches"] = [round(float(v), 4) for v in values]
    if target is None:
        return out
    lo, hi = target["range"]
    inside = [lo <= v <= hi for v in values]
    misses = [0.0 if ok else min(abs(v - lo) / abs(lo), abs(v - hi) / abs(hi)) for v, ok in zip(values, inside)]
    out["patches_in_range"] = int(sum(inside))
    out["max_patch_miss_fraction"] = round(max(misses), 4)
    out["pass"] = bool(lo <= median <= hi and sum(inside) >= 2 and max(misses) <= 0.20)
    out["rule"] = "median in range AND >=2/3 patches in range AND no patch misses its nearest limit by >20%"
    return out


def luma255(rgb):
    return (0.2126 * rgb[:, :, 0] + 0.7152 * rgb[:, :, 1] + 0.0722 * rgb[:, :, 2]) * 255.0


def fuzz_rms(rgb, projected_reference_px):
    luma = luma255(resize_bilinear(rgb, 256.0 / projected_reference_px))
    residual9 = luma - gaussian_blur(luma, 9)
    return math.sqrt(float(np.mean(residual9 * residual9)))


def sheen_ratio(rgb, projected_reference_px):
    luma = luma255(resize_bilinear(rgb, 256.0 / projected_reference_px))
    normalized = luma / np.maximum(gaussian_blur(luma, 31), 1e-6)
    positive = normalized[normalized >= 1.0]
    if len(positive) < 2:
        return 1.0
    p50, p90 = np.percentile(positive, [50, 90])
    return float(p90 / max(p50, 1e-6))


def measure(rgb, base_color, projected_reference_px, neutral_rgb=None, sheen_rgb=None):
    # VISUAL_TARGET defines the kernels at H=256.  Normalize before applying
    # them instead of silently treating a 42 px or 100 px crop as H=256.
    rgb = resize_bilinear(rgb, 256.0 / projected_reference_px)
    luma = (0.2126 * rgb[:, :, 0] + 0.7152 * rgb[:, :, 1] + 0.0722 * rgb[:, :, 2]) * 255.0
    residual9 = luma - gaussian_blur(luma, 9)
    fuzz_rms = math.sqrt(float(np.mean(residual9 * residual9)))
    sheen_rgb = resize_bilinear(sheen_rgb, 256.0 / projected_reference_px) if sheen_rgb is not None else rgb
    sheen_luma = (0.2126 * sheen_rgb[:, :, 0] + 0.7152 * sheen_rgb[:, :, 1] + 0.0722 * sheen_rgb[:, :, 2]) * 255.0
    form = np.maximum(gaussian_blur(sheen_luma, 31), 1e-6)
    normalized = sheen_luma / form
    positive = normalized[normalized >= 1.0]
    if len(positive) < 2:
        sheen = 1.0
    else:
        p50, p90 = np.percentile(positive, [50, 90])
        sheen = float(p90 / max(p50, 1e-6))
    saturation_rgb = neutral_adapt(rgb, neutral_rgb) if neutral_rgb is not None else rgb
    sat = saturation(saturation_rgb)
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
        source_rgb, source_width, source_height = rgb, width, height
        if swatch.get("image"):
            swatch_path = swatch["image"]
            if not os.path.isabs(swatch_path):
                swatch_path = os.path.join(os.path.dirname(metadata_path), swatch_path)
            source_rgb, source_width, source_height = load_display_rgb(swatch_path)
        x0, y0, x1, y1 = swatch["patch_roi_px"]
        if not (0 <= x0 < x1 <= source_width and 0 <= y0 < y1 <= source_height):
            raise SystemExit(f"invalid ROI for {swatch['preset']}: {swatch['patch_roi_px']}")
        projected_reference_px = float(swatch.get("projected_reference_px",
                                                  metadata.get("projected_reference_px", 256.0)))
        if projected_reference_px < 180.0:
            raise SystemExit(f"{swatch['preset']} has H={projected_reference_px:.1f}px; VISUAL_TARGET requires H>=180px")
        neutral_rgb = None
        if swatch.get("neutral_roi_px"):
            nx0, ny0, nx1, ny1 = swatch["neutral_roi_px"]
            if not (0 <= nx0 < nx1 <= source_width and 0 <= ny0 < ny1 <= source_height):
                raise SystemExit(f"invalid neutral ROI for {swatch['preset']}: {swatch['neutral_roi_px']}")
            neutral_rgb = source_rgb[ny0:ny1, nx0:nx1]
        sheen_rgb = None
        if swatch.get("sheen_roi_px"):
            sx0, sy0, sx1, sy1 = swatch["sheen_roi_px"]
            if not (0 <= sx0 < sx1 <= source_width and 0 <= sy0 < sy1 <= source_height):
                raise SystemExit(f"invalid sheen ROI for {swatch['preset']}: {swatch['sheen_roi_px']}")
            sheen_rgb = source_rgb[sy0:sy1, sx0:sx1]
        raw = measure(source_rgb[y0:y1, x0:x1], swatch["base_color_srgb"], projected_reference_px,
                      neutral_rgb, sheen_rgb)
        targets = library["presets"][swatch["preset"]]["targets"]
        checks = {name: target_check(raw[name], targets[name]) for name in
                  ("fuzz_rms_y255", "sheen_p90_p50", "saturation_retention_percent")}

        def crops(key):
            out = []
            for bx0, by0, bx1, by1 in swatch.get(key) or []:
                if not (0 <= bx0 < bx1 <= source_width and 0 <= by0 < by1 <= source_height):
                    raise SystemExit(f"invalid {key} for {swatch['preset']}: {[bx0, by0, bx1, by1]}")
                out.append(source_rgb[by0:by1, bx0:bx1])
            return out
        fuzz_crops, sheen_crops = crops("fuzz_rois_px"), crops("sheen_rois_px")
        if fuzz_crops:
            checks["fuzz_rms_y255"] = patch_check([fuzz_rms(c, projected_reference_px) for c in fuzz_crops],
                                                  targets["fuzz_rms_y255"])
        if sheen_crops:
            checks["sheen_p90_p50"] = patch_check([sheen_ratio(c, projected_reference_px) for c in sheen_crops],
                                                  targets["sheen_p90_p50"])
        applicable = [item["pass"] for item in checks.values() if item["pass"] is not None]
        results.append({
            "preset": swatch["preset"],
            "patch_roi_px": swatch["patch_roi_px"],
            "projected_reference_px": round(projected_reference_px, 4),
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
            "colour_space": "exact 8-bit display-sRGB PNG samples (stdlib decoder; no Blender reload conversion)",
            "scale": "ROIs bilinear-resampled so the physical reference projects to H=256 px; source H>=180 px",
            "neutral_adaptation": "saturation measured after linear-RGB channel adaptation from a co-planar neutral card",
            "luma": "Y' = 0.2126 R + 0.7152 G + 0.0722 B, 0..255",
            "fuzz_rms_y255": "RMS of luma minus a 9-pixel Gaussian kernel; median of three 64x64 px (at H=256) flat-patch "
                             "ROIs when fuzz_rois_px is present, else the single patch ROI",
            "sheen_p90_p50": "P90/P50 of positive luma/(31-pixel Gaussian form blur) residuals; median of three "
                             "sphere ROIs fully inside the key-lit side when sheen_rois_px is present, else the "
                             "single sphere highlight ROI",
            "patch_rule": "VISUAL_TARGET common setup step 3 (>=2/3 patches in range, no miss >20%) plus median in range",
            "saturation": "(max-min)/max; retention is patch S50 divided by input-colour saturation",
        },
        "presets": results,
        "pass": all(item["pass"] for item in results),
    }
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(output, handle, indent=2)
        handle.write("\n")
    print(f"[measure_swatches] {'PASS' if output['pass'] else 'FAIL'} -> {out}")
    raise SystemExit(0 if output["pass"] else 1)


if __name__ == "__main__":
    main()
