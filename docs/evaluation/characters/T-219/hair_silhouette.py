"""T-219 H2: hair silhouette of renders vs the ORIGINAL turnaround references (plain Python: numpy + Pillow).

    python3 docs/evaluation/characters/T-219/hair_silhouette.py <character> <masks dir> <label> [--json out.json]

Per view (front, 3/4, side, back; equal weights) the figure mask of the reference (the stored <view>_mask.png, else
the sheet's grey background removed) is compared with the render's alpha (render_masks.py). Scale: one per character,
hair-independent: the sole-to-eye height of the front view (reference eye line from the annotation / table below, render
eye line projected from the eye landmarks). The render is scaled, its sole row put on the reference sole row and
shifted (+-12 px x, +-3 px y) to the best figure IoU below the shoulder line. The HEAD ZONE is every row above the
shoulder line (eye line + 0.2 x sole-to-eye height): head, hair and buns. Reported per view: IoU of the head zone,
area ratio (render / reference), width ratio and top ratio (height of the top above the eye line, render / reference).
"""
import json
import os
import sys

import numpy as np
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
# reference views (original turnaround sheets), render yaw, and the front view's eye line (pixels, y down):
# auburn from references/annotations/sheet30_front.json (eye_L/eye_R y = 140); white read on a 4x gridded zoom of
# s02_front (iris centres y = 77.5, +-1 px)
REFS = {
    "girl_auburn_bun_glasses": {"views": [("sheet30_front", 0), ("sheet30_front_left", -45), ("sheet30_left", 90),
                                          ("sheet30_back", 180)], "eye_y": 140.0, "ext": ".png"},
    "girl_white_hair_blue_dress": {"views": [("s02_front", 0), ("s02_front_left", -30), ("s02_left", 90),
                                             ("s02_back", 180)], "eye_y": 77.5, "ext": ".jpg"},
}
SHOULDER = 0.2


def ref_mask(character, view, ext):
    d = os.path.join(ROOT, "assets", "characters", character, "references", "views")
    mp = os.path.join(d, view + "_mask.png")
    if os.path.isfile(mp):
        return np.asarray(Image.open(mp).convert("L")) > 127
    a = np.asarray(Image.open(os.path.join(d, view + ext)).convert("RGB")).astype(int)
    border = np.concatenate([a[:4].reshape(-1, 3), a[:, :3].reshape(-1, 3), a[:, -3:].reshape(-1, 3)])
    bg = np.median(border, axis=0)
    m = np.abs(a - bg).sum(-1) > 36
    return fill(largest(m))


def largest(m):
    from collections import deque
    lab = np.zeros(m.shape, int)
    best, bestn, n = 0, 0, 0
    for y, x in zip(*np.nonzero(m)):
        if lab[y, x]:
            continue
        n += 1
        q, cnt = deque([(y, x)]), 0
        lab[y, x] = n
        while q:
            cy, cx = q.popleft()
            cnt += 1
            for ny, nx in ((cy + 1, cx), (cy - 1, cx), (cy, cx + 1), (cy, cx - 1)):
                if 0 <= ny < m.shape[0] and 0 <= nx < m.shape[1] and m[ny, nx] and not lab[ny, nx]:
                    lab[ny, nx] = n
                    q.append((ny, nx))
        if cnt > bestn:
            best, bestn = n, cnt
    return lab == best


def fill(m):
    """Holes (background not connected to the border) filled."""
    from collections import deque
    out = ~m
    seen = np.zeros(m.shape, bool)
    q = deque([(y, x) for y in range(m.shape[0]) for x in (0, m.shape[1] - 1) if out[y, x]]
              + [(y, x) for x in range(m.shape[1]) for y in (0, m.shape[0] - 1) if out[y, x]])
    for y, x in q:
        seen[y, x] = True
    while q:
        cy, cx = q.popleft()
        for ny, nx in ((cy + 1, cx), (cy - 1, cx), (cy, cx + 1), (cy, cx - 1)):
            if 0 <= ny < m.shape[0] and 0 <= nx < m.shape[1] and out[ny, nx] and not seen[ny, nx]:
                seen[ny, nx] = True
                q.append((ny, nx))
    return ~seen


def iou(a, b):
    u = (a | b).sum()
    return float((a & b).sum() / u) if u else None


def place(mask, s, ox, oy, shape):
    h, w = mask.shape
    nw, nh = max(1, int(round(w * s))), max(1, int(round(h * s)))
    m = np.asarray(Image.fromarray(mask.astype(np.uint8) * 255).resize((nw, nh), Image.BILINEAR)) > 127
    out = np.zeros(shape, bool)
    xa, ya, xb, yb = max(0, ox), max(0, oy), min(shape[1], ox + nw), min(shape[0], oy + nh)
    if xb > xa and yb > ya:
        out[ya:yb, xa:xb] = m[ya - oy:yb - oy, xa - ox:xb - ox]
    return out


def rows(m):
    r = np.nonzero(m.any(1))[0]
    return int(r.min()), int(r.max())


def measure(character, masks_dir, label):
    cfg = REFS[character]
    meta = json.load(open(os.path.join(masks_dir, label + ".json")))
    views = []
    refs = [(v, yaw, ref_mask(character, v, cfg["ext"])) for v, yaw in cfg["views"]]
    ref_sole = rows(refs[0][2])[1]
    E = ref_sole - cfg["eye_y"]
    ren0 = np.asarray(Image.open(os.path.join(masks_dir, meta["views"]["0"]["png"])))[..., 3] > 127
    ren_E = rows(ren0)[1] - meta["views"]["0"]["eye_px"][1]
    s = E / ren_E
    for v, yaw, R in refs:
        N = np.asarray(Image.open(os.path.join(masks_dir, meta["views"][str(int(yaw))]["png"])))[..., 3] > 127
        r_top, r_sole = rows(R)
        eye_y = r_sole - E
        cut = int(round(eye_y + SHOULDER * E))
        n_top, n_sole = rows(N)
        cols = np.nonzero(N.any(0))[0]
        rcols = np.nonzero(R.any(0))[0]
        ox0 = int(round((rcols.min() + rcols.max()) / 2 - (cols.min() + cols.max()) / 2 * s))
        oy0 = int(round(r_sole - n_sole * s))
        best = None
        for dy in range(-3, 4):
            for dx in range(-12, 13):
                P = place(N, s, ox0 + dx, oy0 + dy, R.shape)
                k = (round(iou(R[cut:], P[cut:]) or 0, 6), -abs(dx) - abs(dy))
                if best is None or k > best[0]:
                    best = (k, P)
        P = best[1]
        Rh, Ph = R.copy(), P.copy()
        Rh[cut:], Ph[cut:] = False, False
        rc, pc = np.nonzero(Rh.any(0))[0], np.nonzero(Ph.any(0))[0]
        views.append({"view": v, "yaw": yaw, "iou_head": round(iou(Rh, Ph), 4),
                      "area_ratio": round(float(Ph.sum() / Rh.sum()), 4),
                      "width_ratio": round(float((pc.max() - pc.min() + 1) / (rc.max() - rc.min() + 1)), 4),
                      "top_ratio": round(float((eye_y - rows(Ph)[0]) / (eye_y - rows(Rh)[0])), 4),
                      "iou_body": best[0][0]})
    mean = {k: round(float(np.mean([x[k] for x in views])), 4) for k in ("iou_head", "area_ratio", "width_ratio",
                                                                          "top_ratio", "iou_body")}
    return {"character": character, "label": label, "scale": round(s, 5), "views": views, "mean": mean}


if __name__ == "__main__":
    a = sys.argv[1:]
    res = measure(a[0], a[1], a[2])
    if "--json" in a:
        json.dump(res, open(a[a.index("--json") + 1], "w"), indent=1)
    for v in res["views"]:
        print(f"{v['view']:20s} iou {v['iou_head']:.3f} area {v['area_ratio']:.3f} width {v['width_ratio']:.3f} "
              f"top {v['top_ratio']:.3f} (body iou {v['iou_body']:.3f})")
    print("MEAN", json.dumps(res["mean"]), "scale", res["scale"])
