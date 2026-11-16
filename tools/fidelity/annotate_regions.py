"""One-time helper for annotating reference region polygons (plain Python: numpy + Pillow). Character-independent.

    python3 tools/fidelity/annotate_regions.py <hints.json> <view_id> [--write <annotation.json>] [--preview <png>]

Semi-automatic method (documented in docs/CHARACTER_FIDELITY.md):
  1. The figure is the existing silhouette mask of the reference view (references/views/<view>_mask.png).
  2. For every colour region the annotator gives seed boxes (hand-picked flat patches, several per region to cover lit
     and shaded parts) and optionally a zone polygon where the region may appear.
  3. Every figure pixel is assigned the region with the nearest seed colour (CIE Lab, Euclidean) among the regions
     whose zone contains it. A 5x5 majority filter removes speckle.
  4. Each region's connected components (holes filled, >= min_px pixels) are traced and simplified
     (Douglas-Peucker, 0.5 px) into polygons. Hand polygons from the hints (e.g. eyes, glasses) are copied as given.
  5. skin is split at the annotated chin line: skin_face above, skin_limbs below (the render side uses the same rule).
The annotator then reviews the preview overlay and corrects seeds/zones/hand polygons until the overlay is right.
The written polygons are the annotation; this helper is only provenance and is never run by the fidelity tool."""
import argparse
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import analysis as A  # noqa: E402
import metrics as M  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))


def poly_mask(shape, polys):
    return A.poly_mask((shape[1], shape[0]), polys)


def components(mask):
    """4-connected components (list of boolean masks), deterministic scan order."""
    lab = np.zeros(mask.shape, np.int32)
    out = []
    h, w = mask.shape
    n = 0
    for y0, x0 in zip(*np.nonzero(mask)):
        if lab[y0, x0]:
            continue
        n += 1
        stack = [(y0, x0)]
        lab[y0, x0] = n
        pts = []
        while stack:
            y, x = stack.pop()
            pts.append((y, x))
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                yy, xx = y + dy, x + dx
                if 0 <= yy < h and 0 <= xx < w and mask[yy, xx] and not lab[yy, xx]:
                    lab[yy, xx] = n
                    stack.append((yy, xx))
        m = np.zeros_like(mask)
        ys, xs = zip(*pts)
        m[list(ys), list(xs)] = True
        out.append(m)
    return out


def fill_holes(m):
    h, w = m.shape
    pad = np.zeros((h + 2, w + 2), bool)
    pad[1:-1, 1:-1] = m
    outside = components(~pad)
    keep = next(c for c in outside if c[0, 0])
    return ~keep[1:-1, 1:-1]


def trace(m):
    """Outer boundary of a single filled component as a closed list of pixel-corner points (Moore tracing on the
    pixel-corner grid, x right / y down)."""
    h, w = m.shape
    pad = np.zeros((h + 2, w + 2), bool)
    pad[1:-1, 1:-1] = m
    ys, xs = np.nonzero(pad)
    y0, x0 = ys.min(), xs[ys == ys.min()].min()
    # walk along pixel edges keeping the region on the right-hand side
    start = (x0, y0)  # corner (top-left of the first pixel), in padded coords
    pts = [start]
    d = 0  # 0 right, 1 down, 2 left, 3 up
    x, y = start
    dirs = [(1, 0), (0, 1), (-1, 0), (0, -1)]

    def filled(px, py):
        return 0 <= py < pad.shape[0] and 0 <= px < pad.shape[1] and pad[py, px]
    for _ in range(4 * pad.size):
        # pixel to the right-hand side / left-hand side of edge in direction d from corner (x, y)
        for turn in (1, 0, 3, 2):  # prefer turning right, then straight, left, back
            nd = (d + turn) % 4
            dx, dy = dirs[nd]
            # the pixel on the right of moving along nd from corner (x,y)
            if nd == 0:
                r, l = (x, y), (x, y - 1)
            elif nd == 1:
                r, l = (x - 1, y), (x, y)
            elif nd == 2:
                r, l = (x - 1, y - 1), (x - 1, y)
            else:
                r, l = (x, y - 1), (x - 1, y - 1)
            if filled(*r) and not filled(*l):
                d = nd
                x, y = x + dx, y + dy
                break
        if (x, y) == start:
            break
        pts.append((x, y))
    return [(px - 1, py - 1) for px, py in pts]


def simplify(pts, eps=0.5):
    pts = np.asarray(pts, float)
    if len(pts) < 4:
        return pts.tolist()

    def dp(a):
        if len(a) < 3:
            return a
        s, e = a[0], a[-1]
        v = e - s
        n = np.hypot(*v)
        if n == 0:
            dist = np.hypot(*(a - s).T)
        else:
            dist = np.abs(v[0] * (a[:, 1] - s[1]) - v[1] * (a[:, 0] - s[0])) / n
        i = int(np.argmax(dist))
        if dist[i] > eps:
            return np.vstack([dp(a[:i + 1])[:-1], dp(a[i:])])
        return np.vstack([s, e])
    # split the closed ring at the farthest point from the start
    i = int(np.argmax(np.hypot(*(pts - pts[0]).T)))
    out = np.vstack([dp(pts[:i + 1])[:-1], dp(np.vstack([pts[i:], pts[:1]]))[:-1]])
    return [[round(float(x), 1), round(float(y), 1)] for x, y in out]


def hand_polygon(p):
    """A hand-drawn polygon [[x, y], ...] or {"ellipse": [cx, cy, rx, ry]} (24 vertices)."""
    if isinstance(p, dict):
        cx, cy, rx, ry = p["ellipse"]
        return [(cx + rx * np.cos(2 * np.pi * i / 24), cy + ry * np.sin(2 * np.pi * i / 24)) for i in range(24)]
    return p


def annotate(hints, view):
    h = hints["views"][view]
    ref_dir = os.path.join(ROOT, hints["reference_dir"])
    img = np.asarray(Image.open(os.path.join(ref_dir, view + ".png")).convert("RGB"))
    fig = np.asarray(Image.open(os.path.join(ref_dir, view + "_mask.png")).convert("L")) > 127
    lab = M.srgb_to_lab(img.reshape(-1, 3)).reshape(img.shape)
    names = sorted(h["colour_regions"])
    best = np.full(fig.shape, np.inf)
    label = np.full(fig.shape, -1, np.int32)
    for i, name in enumerate(names):
        r = h["colour_regions"][name]
        zone = poly_mask(fig.shape, r["zones"]) if r.get("zones") else np.ones(fig.shape, bool)
        for (x0, y0, x1, y1) in r["seeds"]:
            proto = np.median(lab[y0:y1, x0:x1].reshape(-1, 3), axis=0)
            dist = np.linalg.norm(lab - proto, axis=2)
            better = fig & zone & (dist < best)
            best[better] = dist[better]
            label[better] = i
    lim = Image.fromarray((label + 1).astype(np.uint8)).filter(ImageFilter.ModeFilter(5))
    label = np.asarray(lim).astype(np.int32) - 1
    label[~fig] = -1
    regions = {}
    min_px = h.get("min_px", 15)
    chin = h.get("chin_line_y")
    for i, name in enumerate(names):
        m = label == i
        parts = {name: m}
        if name == "skin" and chin is not None:
            top = np.zeros_like(m)
            top[:int(round(chin)), :] = True
            parts = {"skin_face": m & top, "skin_limbs": m & ~top}
        for pname, pm in parts.items():
            polys = []
            for c in components(pm):
                if c.sum() < min_px:
                    continue
                polys.append(simplify(trace(fill_holes(c))))
            if polys:
                regions[pname] = polys
    for name, polys in h.get("hand_regions", {}).items():
        regions[name] = [[[round(float(x), 1), round(float(y), 1)] for x, y in hand_polygon(p)] for p in polys]
    return img, fig, regions


def preview(img, regions, landmarks, path, palette=None):
    base = Image.fromarray(img).convert("RGB")
    over = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(over)
    pal = [(230, 25, 75), (60, 180, 75), (255, 225, 25), (0, 130, 200), (245, 130, 48), (145, 30, 180),
           (70, 240, 240), (240, 50, 230), (210, 245, 60), (250, 190, 212), (0, 128, 128), (220, 190, 255)]
    order = sorted(regions, key=lambda n: (n in ("eyes", "glasses"), n))
    for name in order:
        c = pal[sorted(regions).index(name) % len(pal)]
        for p in regions[name]:
            fill = None if name in ("eyes", "glasses") else c + (90,)
            d.polygon([tuple(q) for q in p], fill=fill, outline=c + (255,))
    for k, (x, y) in (landmarks or {}).items():
        d.ellipse([x - 1.5, y - 1.5, x + 1.5, y + 1.5], outline=(0, 255, 0, 255))
    out = Image.alpha_composite(base.convert("RGBA"), over).convert("RGB")
    out = out.resize((out.width * 3, out.height * 3), Image.NEAREST)
    d2 = ImageDraw.Draw(out)
    for i, name in enumerate(sorted(regions)):
        d2.rectangle([4, 4 + 14 * i, 14, 14 + 14 * i], fill=pal[i % len(pal)])
        d2.text((18, 4 + 14 * i), name, fill=(255, 255, 255))
    out.save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("hints")
    ap.add_argument("view")
    ap.add_argument("--write", default="")
    ap.add_argument("--preview", default="")
    a = ap.parse_args()
    hints = json.load(open(a.hints))
    img, fig, regions = annotate(hints, a.view)
    lms = {}
    if a.write and os.path.exists(a.write):
        lms = json.load(open(a.write)).get("landmarks", {})
    if a.preview:
        preview(img, regions, lms, a.preview)
    if a.write:
        doc = json.load(open(a.write)) if os.path.exists(a.write) else {}
        doc["regions"] = regions
        with open(a.write, "w") as f:
            f.write(M.dumps(doc))
    print(json.dumps({k: len(v) for k, v in regions.items()}))


if __name__ == "__main__":
    main()
