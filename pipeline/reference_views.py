"""Crops the camera-matched reference views listed in the reference index and extracts the figure silhouette where
the background allows it (plain light/grey backgrounds). Outputs, per view, in <asset>/references/views/:
  <id>.png        the cropped reference
  <id>_mask.png   silhouette (white = figure), only for views marked "silhouette": true
  <id>_check.png  the crop with the silhouette outline drawn on it (for checking the mask by eye)
Run from the repository root:  python3 pipeline/reference_views.py [assets/characters/boy_yellow_hoodie]
Needs numpy and Pillow only."""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageFilter


def largest_component(mask):
    """Keeps the largest 4-connected component (iterative flood fill, no SciPy)."""
    h, w = mask.shape
    labels = np.zeros((h, w), np.int32)
    best, best_size, cur = 0, 0, 0
    for y0, x0 in zip(*np.nonzero(mask)):
        if labels[y0, x0]:
            continue
        cur += 1
        stack, size = [(y0, x0)], 0
        labels[y0, x0] = cur
        while stack:
            y, x = stack.pop()
            size += 1
            for yy, xx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                if 0 <= yy < h and 0 <= xx < w and mask[yy, xx] and not labels[yy, xx]:
                    labels[yy, xx] = cur
                    stack.append((yy, xx))
        if size > best_size:
            best, best_size = cur, size
    return labels == best


def fill_holes(mask):
    """Background = everything connected to the crop border; the rest is figure."""
    inv = ~mask
    h, w = mask.shape
    reach = np.zeros_like(mask)
    stack = [(y, x) for y in range(h) for x in (0, w - 1) if inv[y, x]] + \
            [(y, x) for x in range(w) for y in (0, h - 1) if inv[y, x]]
    for y, x in stack:
        reach[y, x] = True
    while stack:
        y, x = stack.pop()
        for yy, xx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if 0 <= yy < h and 0 <= xx < w and inv[yy, xx] and not reach[yy, xx]:
                reach[yy, xx] = True
                stack.append((yy, xx))
    return ~reach


def segment(rgb, threshold=48.0, opening=5):
    a = np.asarray(rgb, np.float32)
    border = np.concatenate([a[:6].reshape(-1, 3), a[-6:].reshape(-1, 3), a[:, :6].reshape(-1, 3), a[:, -6:].reshape(-1, 3)])
    bg = np.median(border, axis=0)
    dist = np.sqrt(((a - bg) ** 2).sum(axis=2))
    m = Image.fromarray((dist > threshold).astype(np.uint8) * 255)
    # Opening removes thin guide lines, dotted lines and label leader lines; closing seals small gaps.
    m = m.filter(ImageFilter.MinFilter(opening)).filter(ImageFilter.MaxFilter(opening))
    m = m.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3))
    mask = np.asarray(m) > 127
    mask = fill_holes(largest_component(mask))
    return mask, bg


def outline(rgb, mask):
    m = Image.fromarray(mask.astype(np.uint8) * 255)
    edge = np.asarray(m.filter(ImageFilter.FIND_EDGES)) > 0
    out = np.asarray(rgb).copy()
    out[edge] = (255, 0, 255)
    return Image.fromarray(out)


def main():
    asset = sys.argv[1] if len(sys.argv) > 1 else "assets/characters/boy_yellow_hoodie"
    index = json.load(open(os.path.join(asset, "references", "reference_index.json")))
    files = {e["upload"]: e["file"] for e in index["uploads"] if e.get("stored")}
    out_dir = os.path.join(asset, "references", "views")
    os.makedirs(out_dir, exist_ok=True)
    for v in index["views"]:
        crop = Image.open(files[v["upload"]]).convert("RGB").crop(tuple(v["crop"]))
        crop.save(os.path.join(out_dir, v["id"] + ".png"))
        line = f"{v['id']:28s} {crop.size[0]}x{crop.size[1]}"
        if v["silhouette"]:
            mask, bg = segment(crop, **v.get("segmentation", {}))
            Image.fromarray(mask.astype(np.uint8) * 255).save(os.path.join(out_dir, v["id"] + "_mask.png"))
            outline(crop, mask).save(os.path.join(out_dir, v["id"] + "_check.png"))
            ys, xs = np.nonzero(mask)
            line += f"  figure {xs.max() - xs.min() + 1}x{ys.max() - ys.min() + 1}px, coverage {mask.mean():.2f}, bg {bg.astype(int).tolist()}"
        print(line)


if __name__ == "__main__":
    main()
