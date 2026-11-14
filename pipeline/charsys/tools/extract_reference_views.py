"""Extracts camera-matchable reference views from a character sheet (plain Python; numpy and Pillow only).
Generic: works for any sheet whose figures stand on a roughly uniform background.

    python3 pipeline/charsys/tools/extract_reference_views.py --image <sheet> --band y0 y1 --ids a,b,c,... \
        --out <references/views> [--bg-box x0 y0 x1 y1] [--threshold 40] [--pad 6] [--min-width 20]

For the horizontal band [y0, y1): the background colour is the median of --bg-box (default: the left 12 px of the
band). Figures are separated by empty columns. For each figure, the largest connected foreground component is kept
(labels and leader lines that do not touch the figure are dropped), holes are filled, and the crop (with padding)
and its silhouette mask are written as <id>.png and <id>_mask.png, the format compare_sheet.py and pilot_metrics.py
read. Prints the crop boxes (sheet pixel coordinates) for the reference index."""
import argparse
import json
import os

import numpy as np
from PIL import Image
from collections import deque


def _flood(mask, seeds):
    """Pixels of `mask` 4-connected to any seed (BFS)."""
    h, w = mask.shape
    seen = np.zeros_like(mask)
    q = deque((y, x) for y, x in seeds if mask[y, x])
    for y, x in q:
        seen[y, x] = True
    while q:
        y, x = q.popleft()
        for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                seen[ny, nx] = True
                q.append((ny, nx))
    return seen


def largest_component(mask):
    left, best = mask.copy(), np.zeros_like(mask)
    while left.any():
        ys, xs = np.nonzero(left)
        comp = _flood(left, [(ys[0], xs[0])])
        if comp.sum() > best.sum():
            best = comp
        left &= ~comp
    return best


def fill_holes(mask):
    h, w = mask.shape
    border = [(y, x) for y in (0, h - 1) for x in range(w)] + [(y, x) for x in (0, w - 1) for y in range(h)]
    outside = _flood(~mask, border)
    return ~outside


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--band", type=int, nargs=2, required=True)
    ap.add_argument("--ids", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--bg-box", type=int, nargs=4)
    ap.add_argument("--threshold", type=float, default=40)
    ap.add_argument("--pad", type=int, default=6)
    ap.add_argument("--min-width", type=int, default=20)
    a = ap.parse_args()
    img = Image.open(a.image).convert("RGB")
    im = np.asarray(img).astype(int)
    y0, y1 = a.band
    bx = a.bg_box or [0, y0, 12, y1]
    bg = np.median(im[bx[1]:bx[3], bx[0]:bx[2]].reshape(-1, 3), 0)
    band = im[y0:y1]
    fg = np.abs(band - bg).sum(2) > a.threshold
    occ = fg.sum(0) > 3
    runs, s = [], None
    for x, o in enumerate(list(occ) + [False]):
        if o and s is None:
            s = x
        elif not o and s is not None:
            if x - s >= a.min_width:
                runs.append((s, x))
            s = None
    ids = a.ids.split(",")
    if len(runs) != len(ids):
        raise SystemExit(f"found {len(runs)} figures, expected {len(ids)}: {runs}")
    os.makedirs(a.out, exist_ok=True)
    out = {}
    for vid, (xa, xb) in zip(ids, runs):
        keep = fill_holes(largest_component(fg[:, xa:xb]))
        ys, xs = np.nonzero(keep)
        cx0, cy0 = max(0, xa + xs.min() - a.pad), max(0, y0 + ys.min() - a.pad)
        cx1, cy1 = min(im.shape[1], xa + xs.max() + 1 + a.pad), min(im.shape[0], y0 + ys.max() + 1 + a.pad)
        full = np.zeros(im.shape[:2], bool)
        full[y0:y1, xa:xb] = keep
        img.crop((cx0, cy0, cx1, cy1)).save(os.path.join(a.out, vid + ".png"))
        Image.fromarray((full[cy0:cy1, cx0:cx1] * 255).astype(np.uint8)).save(os.path.join(a.out, vid + "_mask.png"))
        out[vid] = {"crop": [int(cx0), int(cy0), int(cx1), int(cy1)], "figure_px": [int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)]}
    print(json.dumps(out))


if __name__ == "__main__":
    main()
