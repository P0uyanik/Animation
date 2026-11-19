"""Flicker / shimmer: temporal luminance noise per region on rendered frames (render_passes.py npz frames), the
denoised image and the noisy image before the denoiser.

Motion is separated from noise with a held-pose baseline per pixel: a pixel counts at frame t only while its geometry
holds still over t-1, t, t+1 (the same region index, depth change below depth_tol of the depth, normal turn below
normal_tol_deg, from the render's own passes). On those pixels the image should not change either, so the temporal
second difference of the luminance
    r_t = L_t - (L_{t-1} + L_{t+1}) / 2,   relative: r_t / (mean of the three + eps)
is noise or flicker (a smooth light change, e.g. a slowly moving shadow, is linear in time and drops out). For
independent noise of standard deviation s per frame, r has the deviation s * sqrt(1.5), so
    noise = 1.4826 * median|r_rel| / sqrt(1.5)
estimates the relative temporal noise of the held pixels.

Hair and fibres are thinner than a pixel: any motion, breathing included, changes their coverage-averaged depth and
normal passes, so they are almost never held. For them (and every region) the second measure is motion tolerant:
temporal sign flips. A pixel flips at t when its relative luminance change from t-1 to t and from t to t+1 have
opposite signs and both are at least flip_min (in the same region over the three frames). Motion moves a pixel's
luminance one way for a frame or more (an edge passing, a slowly turning surface); noise, denoiser instability and
aliasing of thin fibres (a fibre that blinks in and out) turn it back the next frame. flip share = flipped pixels /
region pixels, per region and per 16 x 16 tile (at least min_tile_pixels region pixels).

Motion compensation: with the render's motion vectors (Cycles Vector pass, render_passes.py), L_{t-1} and L_{t+1}
are first warped onto frame t (bilinear, from where each pixel was / will be: x + X, y - Y and x - Z, y + W in image
rows), and a pixel counts only where the warped region index is the pixel's own (no disocclusion). What then still
turns back is noise, denoiser instability or strand aliasing, not motion (a moving hand or a hair swing is followed).
Without vectors, solid regions (solid_regions) count only nearly held pixels (near_depth_tol, near_normal_tol_deg)
and strands every pixel of their region (motion then adds to their flips; the report says which mode was used).

Issues (denoised image; the noisy image is measured and reported next to it, the denoiser gain is noisy / denoised):
frames where a region's held noise, its flip share, or a tile's flip share reaches thresholds.json."""
import numpy as np

REGION_NAMES = {0: "background", 1: "hair", 2: "fibres", 3: "skin", 4: "cloth"}
TILE = 16


def held_mask(idx, depth, normal, t, thr, depth_tol=None, normal_tol=None):
    """Pixels whose geometry holds still over t-1..t+1 (within depth_tol of the depth and normal_tol degrees)."""
    i = (idx[t - 1] == idx[t]) & (idx[t + 1] == idx[t])
    d0, d1, d2 = (depth[k].astype(np.float32) for k in (t - 1, t, t + 1))
    with np.errstate(invalid="ignore", divide="ignore"):
        dd = np.maximum(np.abs(d1 - d0), np.abs(d2 - d1)) / np.maximum(d1, 1e-3)
    far = ~np.isfinite(d1) | (d1 > 1e3)  # world misses: always held
    ok_d = far | (dd < (thr["depth_tol"] if depth_tol is None else depth_tol))
    n0, n1, n2 = (unit(normal[k]) for k in (t - 1, t, t + 1))
    c = np.cos(np.radians(thr["normal_tol_deg"] if normal_tol is None else normal_tol))
    ok_n = far | ((np.sum(n0 * n1, -1) > c) & (np.sum(n2 * n1, -1) > c))
    return i & ok_d & ok_n


def unit(n):
    n = n.astype(np.float32)
    return n / np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-6)


def flips(L, t, eps, flip_min):
    a, b, c = (L[k].astype(np.float32) for k in (t - 1, t, t + 1))
    m = (a + b + c) / 3 + eps
    d1, d2 = (b - a) / m, (c - b) / m
    return (d1 * d2 < 0) & (np.minimum(np.abs(d1), np.abs(d2)) >= flip_min)


def bilinear(img, x, y):
    H, W = img.shape[:2]
    x = np.clip(x, 0, W - 1.001)
    y = np.clip(y, 0, H - 1.001)
    x0, y0 = np.floor(x).astype(np.int64), np.floor(y).astype(np.int64)
    fx, fy = x - x0, y - y0
    if img.ndim == 3:
        fx, fy = fx[..., None], fy[..., None]
    return (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x0 + 1] * fx * (1 - fy)
            + img[y0 + 1, x0] * (1 - fx) * fy + img[y0 + 1, x0 + 1] * fx * fy)


def compensated(data, t):
    """{"denoised", "noisy": (3, H, W) the frames t-1, t, t+1 warped onto t; "same": pixels whose warped region
    index matches} from the Vector pass of frame t."""
    v = data["vector"][t].astype(np.float32)
    H, W = v.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    px, py = xx + v[..., 0], yy - v[..., 1]
    nx, ny = xx - v[..., 2], yy + v[..., 3]
    idx = data["index"]
    near = lambda a, x, y: a[np.clip(np.rint(y).astype(np.int64), 0, H - 1), np.clip(np.rint(x).astype(np.int64), 0, W - 1)]
    out = {"same": (near(idx[t - 1], px, py) == idx[t]) & (near(idx[t + 1], nx, ny) == idx[t])}
    for k in ("denoised", "noisy"):
        L = data[k]
        out[k] = np.stack([bilinear(L[t - 1].astype(np.float32), px, py), L[t].astype(np.float32),
                           bilinear(L[t + 1].astype(np.float32), nx, ny)])
    return out


def residual(L, t, eps):
    a, b, c = (L[k].astype(np.float32) for k in (t - 1, t, t + 1))
    return (b - (a + c) / 2) / ((a + b + c) / 3 + eps)


def tile_share(flip, mask, min_px):
    """(h, w) share of flipped pixels among the mask's pixels per tile (nan below min_px mask pixels)."""
    H, W = flip.shape
    h, w = H // TILE, W // TILE
    f = (flip & mask)[:h * TILE, :w * TILE].reshape(h, TILE, w, TILE).sum((1, 3)).astype(np.float64)
    n = mask[:h * TILE, :w * TILE].reshape(h, TILE, w, TILE).sum((1, 3))
    with np.errstate(all="ignore"):
        out = f / n
    out[n < min_px] = np.nan
    return out


def measure(frames, data, thr):
    """Per-frame measurements: {frame: {"held": share, "regions": {name: {...}}, "tiles": {region: (h, w) medians}}}."""
    idx, depth, normal = data["index"], data["depth"], data["normal"]
    out = {}
    for t in range(1, len(frames) - 1):
        if frames[t + 1] - frames[t - 1] != 2:
            continue  # needs consecutive frames
        held = held_mask(idx, depth, normal, t, thr)
        near = held_mask(idx, depth, normal, t, thr, thr["near_depth_tol"], thr["near_normal_tol_deg"])
        rec = {"held": round(float(held.mean()), 4), "regions": {}, "tiles": {}}
        res = {k: residual(data[k], t, thr["eps"]) for k in ("denoised", "noisy")}
        mc = "vector" in data
        if mc:
            w = compensated(data, t)
            same = w["same"]
            fl = {k: flips(w[k], 1, thr["eps"], thr["flip_min"]) for k in ("denoised", "noisy")}
        else:
            same = (idx[t - 1] == idx[t]) & (idx[t + 1] == idx[t])
            fl = {k: flips(data[k], t, thr["eps"], thr["flip_min"]) for k in ("denoised", "noisy")}
        rec["motion_compensated"] = mc
        for rid, name in REGION_NAMES.items():
            reg = same & (idx[t] == rid)
            m = held & reg
            if name in thr["solid_regions"] and not mc:
                reg = reg & near  # a solid surface moving through the pixel is motion, not flicker
            if reg.sum() < thr["min_region_pixels"]:
                continue
            r = {"pixels": int(reg.sum()), "held_pixels": int(m.sum())}
            for k in ("denoised", "noisy"):
                r[k] = {"flip_share": round(float(fl[k][reg].mean()), 5)}
                if m.sum() >= thr["min_region_pixels"]:
                    a = np.abs(res[k][m])
                    r[k]["noise"] = round(float(1.4826 * np.median(a) / np.sqrt(1.5)), 5)
            if "noise" in r["denoised"]:
                r["denoiser_gain"] = round(r["noisy"]["noise"] / max(r["denoised"]["noise"], 1e-6), 2)
            r["denoiser_flip_gain"] = round(r["noisy"]["flip_share"] / max(r["denoised"]["flip_share"], 1e-6), 2)
            rec["regions"][name] = r
            rec["tiles"][name] = tile_share(fl["denoised"], reg, thr["min_tile_pixels"])
        out[int(frames[t])] = rec
    return out


def find(frames, data, thr, meas=None):
    meas = meas if meas is not None else measure(frames, data, thr)
    raw = []
    for f, rec in meas.items():
        for name, r in rec["regions"].items():
            lim = thr["held_noise"].get(name, thr["held_noise"]["default"])
            if r["denoised"].get("noise", 0) >= lim:
                raw.append({"kind": "held_noise", "region": name, "frame": f, "value": r["denoised"]["noise"],
                            "noisy": r["noisy"]["noise"], "limit": lim})
            lim = thr["flip_share"].get(name, thr["flip_share"]["default"])
            if r["denoised"]["flip_share"] >= lim:
                raw.append({"kind": "flip_share", "region": name, "frame": f, "value": r["denoised"]["flip_share"],
                            "noisy": r["noisy"]["flip_share"], "limit": lim})
            tm = rec["tiles"][name]
            tl = thr["tile_flip_share"].get(name, thr["tile_flip_share"]["default"])
            hit = np.argwhere(np.nan_to_num(tm, nan=0) >= tl)
            if len(hit):
                k = np.nanargmax(np.where(np.isnan(tm), -1, tm))
                ky, kx = np.unravel_index(k, tm.shape)
                y0, x0 = hit.min(0)
                y1, x1 = hit.max(0)
                raw.append({"kind": "tile_flip_share", "region": name, "frame": f, "value": round(float(tm[ky, kx]), 5),
                            "limit": tl, "tiles": int(len(hit)),
                            "bbox_px": [int(x0 * TILE), int(y0 * TILE), int((x1 + 1) * TILE), int((y1 + 1) * TILE)],
                            "worst_tile_px": [int(kx * TILE), int(ky * TILE)]})
    return merge(raw, min_run=thr.get("tile_min_run", 1)), summary(meas)


def merge(raw, gap=1, min_run=1):
    """Runs of frames per (kind, region); tile runs shorter than min_run frames are dropped (a blink or a saccade
    turns a pixel back for one or two frames; shimmer persists)."""
    out = []
    for key in sorted({(i["kind"], i["region"]) for i in raw}):
        g = sorted((i for i in raw if (i["kind"], i["region"]) == key), key=lambda i: i["frame"])
        runs, cur = [], [g[0]]
        for i in g[1:]:
            if i["frame"] <= cur[-1]["frame"] + gap + 1:
                cur.append(i)
            else:
                runs.append(cur)
                cur = [i]
        runs.append(cur)
        for r in runs:
            if key[0] == "tile_flip_share" and r[-1]["frame"] - r[0]["frame"] + 1 < min_run:
                continue
            w = max(r, key=lambda i: i["value"])
            e = {"check": "flicker", **{k: v for k, v in w.items() if k != "frame"},
                 "frames": [r[0]["frame"], r[-1]["frame"]], "peak_frame": w["frame"]}
            if "bbox_px" in w:
                e["bbox_px"] = [min(i["bbox_px"][0] for i in r), min(i["bbox_px"][1] for i in r),
                                max(i["bbox_px"][2] for i in r), max(i["bbox_px"][3] for i in r)]
            out.append(e)
    out.sort(key=lambda i: -i["value"] / i["limit"])
    return out


def summary(meas):
    """Per region over the shot: median and max of the per-frame noise (denoised, noisy), the largest tile median."""
    out = {}
    for name in REGION_NAMES.values():
        rows = [rec["regions"][name] for rec in meas.values() if name in rec["regions"]]
        if not rows:
            continue
        tiles = [np.nanmax(rec["tiles"][name]) for rec in meas.values()
                 if name in rec["tiles"] and np.isfinite(rec["tiles"][name]).any()]
        o = {"frames": len(rows), "motion_compensated": all(rec.get("motion_compensated") for rec in meas.values()),
             "held_share": round(float(np.mean([r["held_pixels"] / r["pixels"] for r in rows])), 3)}
        for k in ("denoised", "noisy"):
            for m in ("noise", "flip_share"):
                v = np.array([r[k][m] for r in rows if m in r[k]])
                if len(v):
                    o[f"{k}_{m}_median"] = round(float(np.median(v)), 5)
                    o[f"{k}_{m}_max"] = round(float(v.max()), 5)
        o["tile_flip_share_max"] = round(float(max(tiles)), 4) if tiles else None
        out[name] = o
    return out
