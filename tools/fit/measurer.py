"""T-214 render-side T-204 face measurer.

Renders a head-only build of a character blend with flat Workbench object-ID passes (tools/fit/render.py,
measure_views), derives the T-204 trace points from the masks, projections and depth, and evaluates them with
T-204's own definitions (docs/evaluation/characters/T-204/measure.py `values`). Commands:

    python tools/fit/measurer.py measure  --character auburn --out build/t214/auburn [--blend B] [--spec S] [--px 512]
    python tools/fit/measurer.py validate --character auburn --out build/t214/val-auburn

`measure` scores the 8 yaws plus the reference yaws against the T-204 targets, with the matched expression of each
reference view (views.json). `validate` renders the neutral T-202 cameras at 1024 px and compares every measure with
T-204's hand traces of the same renders (measures.csv `current`), within the T-204 tolerance.
Point coordinates follow T-204: 400 units per square tile, x right, y down."""
import argparse
import csv
import importlib.util
import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
T204 = ROOT / "docs/evaluation/characters/T-204"
CONFIG = ROOT / "docs/evaluation/characters/T-214/views.json"
N = 400
CLASSES = ("background", "skin", "lid", "lash", "eye_L", "eye_R", "brow", "ear", "mouth", "cavity", "glasses",
           "hair", "bun", "hair_acc", "other")
C = {n: i for i, n in enumerate(CLASSES)}
FACE_SURFACE = [C[k] for k in ("skin", "lid", "lash", "eye_L", "eye_R", "brow", "mouth", "cavity")]
HAIR = [C["hair"], C["bun"]]
# Measures whose value depends on hair landmarks (fitted separately from the face, T-212). Every H-normalised
# measure also depends on the main-hair crown through H.
HAIR_MEASURES = {"hair_width", "hair_height", "forehead_covered", "fringe_eye", "crown_above_skull",
                 "hair_cheek_width", "bun_width", "exposed_cheek", "profile_depth"}
COLOUR_MEASURES = {"cheek_L", "cheek_a", "cheek_b", "forehead_L", "forehead_a", "forehead_b", "bow_L", "bow_a",
                   "bow_b", "blush_da"}
DEPTH_JUMP_M = 0.008   # face-to-neck occlusion step; a surface at 80 deg moves < 4 mm per 1024 px pixel here
NOSE_RELIEF = 0.25     # nose box = connected skin standing above the local cheek plane by > 25 % of its peak


def t204():
    spec = importlib.util.spec_from_file_location("t204_measure", T204 / "measure.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n", encoding="utf-8")


# ------------------------------------------------------------------------------------------------ mask helpers
def flood(mask, seed):
    """4-connected component of `mask` containing seed (u, v); empty if the seed is outside the mask."""
    u, v = int(seed[0]), int(seed[1])
    h, w = mask.shape
    if not (0 <= u < w and 0 <= v < h) or not mask[v, u]:
        return np.zeros_like(mask)
    im = Image.fromarray(mask.astype(np.uint8) * 100).copy()  # a fromarray image shares a read-only buffer
    ImageDraw.floodfill(im, (u, v), 200)
    return np.asarray(im) == 200


def nearest_in(mask, point, radius):
    """Pixel of mask closest to point within radius, or None."""
    v, u = np.nonzero(mask)
    if not len(u):
        return None
    d = (u + .5 - point[0]) ** 2 + (v + .5 - point[1]) ** 2
    i = int(np.argmin(d))
    return (u[i], v[i]) if d[i] <= radius * radius else None


def open3(mask):
    """Binary opening with a 3x3 square: removes isolated fibre pixels before taking extremes."""
    def erode(m):
        p = np.pad(m, 1)
        return np.logical_and.reduce([p[1 + dy:p.shape[0] - 1 + dy, 1 + dx:p.shape[1] - 1 + dx]
                                      for dy in (-1, 0, 1) for dx in (-1, 0, 1)])

    def dilate(m):
        p = np.pad(m, 1)
        return np.logical_or.reduce([p[1 + dy:p.shape[0] - 1 + dy, 1 + dx:p.shape[1] - 1 + dx]
                                     for dy in (-1, 0, 1) for dx in (-1, 0, 1)])
    return dilate(erode(mask))


def bbox(mask):
    v, u = np.nonzero(mask)
    return None if not len(u) else (u.min(), v.min(), u.max() + 1, v.max() + 1)


def occluding_edges(region, depth, lateral=True):
    """Region pixels whose lower (and with `lateral`, left or right) neighbour lies farther by a step: the chin and
    jaw over the neck. A background neighbour is not an occluded surface."""
    e = np.zeros_like(region)
    d = np.where(np.isfinite(depth), depth, -np.inf)
    with np.errstate(invalid="ignore"):
        e[:-1] |= region[:-1] & ((d[1:] - d[:-1]) > DEPTH_JUMP_M)
        if lateral:
            e[:, :-1] |= region[:, :-1] & ((d[:, 1:] - d[:, :-1]) > DEPTH_JUMP_M)
            e[:, 1:] |= region[:, 1:] & ((d[:, :-1] - d[:, 1:]) > DEPTH_JUMP_M)
    return e


def head_region(cls, depth, seed):
    """Face surface connected to the seed without crossing an occlusion step (chin over neck, jaw over neck).
    The farther pixel of each step leaves the mask, so the near (head) side keeps its full edge."""
    m = np.isin(cls, FACE_SURFACE) & np.isfinite(depth)
    far = np.zeros_like(m)
    for axis in (0, 1):
        a = np.swapaxes(depth, 0, axis)
        with np.errstate(invalid="ignore"):
            d = a[1:] - a[:-1]
        f = np.zeros(a.shape, bool)
        f[1:] |= d > DEPTH_JUMP_M      # lower/right pixel farther
        f[:-1] |= -d > DEPTH_JUMP_M    # upper/left pixel farther
        far |= np.swapaxes(f, 0, axis)
    return flood(m & ~far, seed)


# ------------------------------------------------------------------------------------------------ geometry
class Camera:
    def __init__(self, rec, px):
        self.m = np.array(rec["camera"]["matrix_world"])
        self.inv = np.linalg.inv(self.m)
        self.f = rec["camera"]["lens"] / rec["camera"]["sensor"] * px
        self.px = px

    def project(self, p):
        c = self.inv @ np.append(p, 1)
        return np.array([self.px / 2 + self.f * c[0] / -c[2], self.px / 2 - self.f * c[1] / -c[2], -c[2]])

    def unproject(self, u, v, z):
        c = np.array([(u - self.px / 2) / self.f * z, -(v - self.px / 2) / self.f * z, -z, 1])
        return (self.m @ c)[:3]


def trace(rec, arrays, px, chin3d=None):
    """T-204 trace points (400-unit tile) for one rendered view. Returns (points, estimated, extra)."""
    s = N / px
    full, face, hairm, depth = arrays["full_cls"], arrays["face_cls"], arrays["hair_cls"], arrays["face_depth"]
    cam = Camera(rec, px)
    yaw = rec["yaw"]
    side_view = 60 <= abs(yaw) <= 120
    back_view = abs(yaw) > 120
    est, extra = set(), {}

    def P(u, v):
        return [round(float(u) * s, 2), round(float(v) * s, 2)]

    lm = {k: np.array(v[:3]) for k, v in rec["landmarks"].items()}
    surf = rec["surface"]
    # Eyes: near = image-left in front, otherwise the one closer to the camera.
    eyes = {}
    for k in ("eye_L", "eye_R"):
        if k in rec["iris"]:
            ring = np.array(rec["iris"][k]["ring"])
            inside = np.clip(ring.astype(int), 0, px - 1)
            eyes[k] = dict(ring=ring, depth=rec["iris"][k]["centre"][2],
                           vis_full=float(np.mean(full[inside[:, 1], inside[:, 0]] == C[k])),
                           face_px=int((face == C[k]).sum()))
    pts = {}
    order = sorted(eyes, key=lambda k: (eyes[k]["ring"][:, 0].mean() if abs(yaw) < 10 else eyes[k]["depth"]))
    near = order[0] if order and eyes[order[0]]["face_px"] and not back_view else None
    far = order[1] if len(order) > 1 and not side_view and not back_view and eyes[order[1]]["face_px"] else None
    # Opening box (inside lash; lids, lash and hair excluded): connected eyeball pixels of the face pass at the iris.
    eye_box = None
    if near:
        ring = eyes[near]["ring"]
        c = ring.mean(0)
        mask = face == C[near]
        seed = nearest_in(mask, c, 0.04 * px)
        if seed is not None:
            comp = flood(mask, seed)
            eye_box = bbox(comp)
            vis_full = ((full == C[near]) & comp).sum() / max(1, comp.sum())
            if vis_full < 0.8:
                est.add("eye")
        # iris extremes of the iris disc the lids leave visible (face pass: hair and rims do not count);
        # the centre height is the ring's (inferred where a lid covers it)
        disc = Image.new("L", (px, px), 0)
        ImageDraw.Draw(disc).polygon([tuple(p) for p in ring], fill=1)
        disc = np.asarray(disc).astype(bool)
        seen = disc & (face == C[near])
        if seen.sum() < 0.95 * disc.sum():
            est.add("iris")
        cols = np.nonzero(seen.any(0))[0]
        iris = ([cols.min(), ring[:, 1].mean(), cols.max() + 1] if len(cols) >= 2 else
                [ring[:, 0].min(), ring[:, 1].mean(), ring[:, 0].max()])
        pts["iris"] = [round(iris[0] * s, 2), round(iris[1] * s, 2), round(iris[2] * s, 2)]
        if eye_box:
            pts["eye"] = [round(x * s, 2) for x in eye_box]
        if side_view:  # profile eye level: the opening's centre (the iris is seen edge-on)
            pts["eye_y"] = round(((eye_box[1] + eye_box[3]) / 2 if eye_box else iris[1]) * s, 2)
    if far:
        fr = eyes[far]["ring"]
        pts["far"] = P(*fr.mean(0))
        if eyes[far]["vis_full"] < 0.3:
            est.add("far")
    # Head region and chin.
    nose = np.array(surf["nose_tip"][:2]) if "nose_tip" in surf else lm["nose"][:2]
    seed = nearest_in(np.isin(face, FACE_SURFACE), nose, 0.05 * px)
    region = head_region(face, depth, seed) if seed is not None else np.zeros_like(face, bool)
    chin = None
    mouth_v = lm["mouth"][1] if "mouth" in lm else nose[1]
    edges = occluding_edges(region, depth)
    edges[:int(mouth_v)] = False
    ev, eu = np.nonzero(edges)
    if len(ev):  # the neck lies under the chin/jaw occluding edge: cut it column by column
        low = np.full(px, -1)
        np.maximum.at(low, eu, ev)
        rows_idx = np.arange(px)[:, None]
        region &= ~((low[None, :] >= 0) & (rows_idx > low[None, :]))
    if not back_view and len(ev) and not side_view:
        down = occluding_edges(region, depth, lateral=False)
        down[:int(mouth_v)] = False
        dv, du = np.nonzero(down)
        vb = (dv if len(dv) else ev).max()  # lowest point of the chin over the neck (a downward step)
        us = (du if len(dv) else eu)[(dv if len(dv) else ev) == vb]
        chin = (us.mean() + .5, vb + 1.0)
        region[vb + 1:] = False
        if yaw == 0:
            extra["chin3d"] = cam.unproject(chin[0], chin[1] - 0.5, float(depth[vb, int(us.mean())])).tolist()
    elif not back_view and len(ev) and chin3d is not None:
        # profile: the occluding-edge pixel nearest the front view's 3D chin (the throat is a smooth surface)
        cu, cv, _ = cam.project(np.array(chin3d))
        d2 = (eu + .5 - cu) ** 2 + (ev + 1 - cv) ** 2
        i = int(np.argmin(d2))
        if d2[i] <= (0.04 * px) ** 2:
            chin = (eu[i] + .5, ev[i] + 1.0)
        else:
            chin = (cu, cv)
            est.add("chin")
        region[int(chin[1]):] = False
    elif chin3d is not None:
        u, v, _ = cam.project(np.array(chin3d))
        chin = (u, v)
        est.add("chin")
    if chin:
        pts["chin"] = P(*chin)
    # Crown (scoring): the highest VISIBLE main-hair point, at the bun junction where a bun sits on the hair -
    # the 2nd percentile of the per-column top of the visible main hair, so stray strands do not count.
    # Report: the geometric main-hair top from the hair-only pass, behind the bun where it hides it.
    hm = open3(hairm == C["hair"])
    hr = np.nonzero(hm.sum(1) >= 2)[0]
    if len(hr):
        v0 = hr.min()
        extra["crown_geometric"] = P(np.nonzero(hm[v0])[0].mean() + .5, v0)
    hv = open3(full == C["hair"])
    tops = np.array([(np.argmax(hv[:, u]), u) for u in np.nonzero(hv.any(0))[0]])
    if len(tops):
        v1 = np.percentile(tops[:, 0], 2)
        near_top = tops[tops[:, 0] <= v1]
        pts["crown"] = P(near_top[:, 1].mean() + .5, v1)
    elif "crown_geometric" in extra:
        pts["crown"] = extra["crown_geometric"]
        est.add("crown")
    hair_all = open3(np.isin(full, HAIR))
    hrows = np.nonzero(hair_all.any(1))[0]
    pts["crest"] = None if not len(hrows) or hrows.min() == 0 else P(np.nonzero(hair_all[hrows.min()])[0].mean() + .5,
                                                                      hrows.min())
    if not back_view:  # back views keep the hair silhouette measures only
        # Contours: from the opening top (or iris level) down to the chin, per 400-unit row.
        if chin and region.any() and not side_view:
            # start between the opening top and the iris centre: above iris level, below the temple bulge on turns
            top = ((eye_box[1] + iris[1]) / 2 if eye_box else (iris[1] if near else lm["eye_L"][1]))
            # and not above the ear tops: higher up the outline is the skull side, not the cheek
            ear_rows = np.nonzero((face == C["ear"]).any(1))[0]
            if len(ear_rows) and ear_rows.min() < chin[1]:
                top = max(top, ear_rows.min())
            left, right = [], []
            for y in np.arange(math.ceil(top * s), chin[1] * s, 1.0 if px >= 800 else 2.0):
                r = int(y / s)
                us = np.nonzero(region[r])[0]
                if len(us):
                    left.append([round(us.min() * s, 2), round(float(y), 2)])
                    right.append([round((us.max() + 1) * s, 2), round(float(y), 2)])
            left.append(pts["chin"])
            right.append(pts["chin"])
            pts["left"], pts["right"] = left, right
            vis = np.isin(full, FACE_SURFACE)
            for key, pl in (("left", left), ("right", right)):
                hidden = sum(not vis[min(px - 1, int(p[1] / s)), min(px - 1, int(p[0] / s) + (1 if key == "left" else -1))]
                             for p in pl)
                if hidden > 0.1 * len(pl):
                    est.add(key)
        # Brow: lower edge above the near pupil (face pass, no hair over it).
        if near and eye_box:
            bm = face == C["brow"]
            cu = int((iris[0] + iris[2]) / 2)
            lo_u, hi_u = eye_box[0] - 0.02 * px, eye_box[2] + 0.02 * px
            cols = [cu] + [cu + d * k for k in range(1, int(0.03 * px)) for d in (-1, 1)]
            for c in cols:
                if lo_u <= c <= hi_u:
                    vs = np.nonzero(bm[:eye_box[1], c])[0]
                    if len(vs):
                        pts["brow"] = P(c + .5, vs.max() + 1)
                        if not (full[vs.max(), c] == C["brow"]):
                            est.add("brow")
                        break
        # Mouth box (lips and cavity) and nose box.
        mm = np.isin(full, [C["mouth"], C["cavity"]])
        if "mouth" in lm:
            sd = nearest_in(mm, lm["mouth"][:2], 0.05 * px)
            if sd is not None:
                box = bbox(flood(mm, sd) | (open3(mm) & (np.hypot(*np.meshgrid(np.arange(px) - sd[0], np.arange(px) - sd[1]))
                                                           < 0.06 * px)))
                pts["mouth"] = [round(x * s, 2) for x in box]
        if "nose" in lm and not side_view:
            nb = nose_box(face, depth, lm["nose"], rec.get("nose_size_m", 0.016) * cam.f / lm["nose"][2], px)
            if nb:
                pts["nose"] = [round(x * s, 2) for x in nb]
                if "nose_tip" in surf and not surf["nose_tip"][4]:
                    est.add("nose")
        # Ears: near (front: image-left) ear box; on turns the T-204 ear_turn projection.
        em = full == C["ear"]  # visible ear (T-204 traces the visible rim to root; hidden parts omitted)
        ears = [k for k in ("ear_L", "ear_R") if k in lm]
        if ears and em.any():
            key = min(ears, key=lambda k: lm[k][0] if abs(yaw) < 10 else lm[k][2])
            sd = nearest_in(em, lm[key][:2], 0.08 * px)
            if sd is not None:
                comp = flood(em, sd)
                b = bbox(comp)
                whole = flood(face == C["ear"], sd)
                if abs(yaw) < 10 or not side_view:
                    pts["ear"] = [round(x * s, 2) for x in b]
                    if comp.sum() < 0.8 * whole.sum():
                        est.add("ear")
                if 10 <= abs(yaw) < 60 and "left" in pts:
                    b = bbox(whole)  # projection check: the whole near ear, under hair too
                    ym = (b[1] + b[3]) / 2
                    us = np.nonzero(whole[int(ym)])[0]
                    cont = pts["left"] if lm[key][0] < nose[0] else pts["right"]
                    ys = np.array([p[1] for p in cont])
                    cx = float(np.interp(ym * s, ys, [p[0] for p in cont]))
                    rim = us.min() if lm[key][0] < nose[0] else us.max() + 1
                    pts["ear_turn"] = [P(rim, ym), [round(cx, 2), round(ym * s, 2)]]
    # Hair: cap above eye level, outer span at cheek level, bun span, fringe/skull/midbrow on the midline.
    eye_v = (pts["eye_y"] / s if "eye_y" in pts else iris[1]) if near else lm["eye_L"][1]
    mouth_v = ((pts["mouth"][1] + pts["mouth"][3]) / 2 / s) if "mouth" in pts else lm["mouth"][1]
    hm2 = open3(np.isin(full, HAIR))
    above = hm2[:int(eye_v)]
    if above.any():
        v, u = np.nonzero(above)
        i, j = np.argmin(u), np.argmax(u)
        pts["cap"] = [P(u[i], v[i]), P(u[j] + 1, v[j])]
    ych = int((eye_v + mouth_v) / 2)
    us = np.nonzero(hm2[ych])[0]
    if len(us):
        pts["hair_at_cheek"] = [P(us.min(), ych), P(us.max() + 1, ych)]
    else:
        pts["no_cheek_hair"] = True
    bm = open3(full == C["bun"])
    if bm.any():
        # twin buns: the image-left bun (T-204 cap_crest_bun)
        parts = []
        rest = bm.copy()
        while rest.any() and len(parts) < 6:
            v, u = np.nonzero(rest)
            comp = flood(rest, (u[0], v[0]))
            rest &= ~comp
            if comp.sum() >= 0.1 * bm.sum():
                parts.append(comp)
        if len(parts) > 1 and "bun_twin" in rec.get("flags", ()):
            bm = min(parts, key=lambda c: np.nonzero(c)[1].mean())
        v, u = np.nonzero(bm)
        i, j = np.argmin(u), np.argmax(u)
        pts["bun_span"] = [P(u[i], v[i]), P(u[j] + 1, v[j])]
        pts["no_bun"] = False
    elif "bun" not in rec.get("classes_present", ["bun"]):  # no bun in the build: visibly absent
        pts["no_bun"] = True
    if not side_view and not back_view:
        mid_u = int(nose[0])
        skin_col = np.nonzero(region[:, mid_u])[0]
        if len(skin_col):
            pts["skull"] = P(mid_u + .5, skin_col.min())
            est.add("skull")
        brows = np.nonzero(face == C["brow"])
        if len(brows[0]):
            pts["midbrow"] = P(mid_u + .5, brows[0].mean() + .5)
            col = full[:int(eye_box[1] if eye_box else eye_v), mid_u]  # the fringe may hang below the brows
            hv = np.nonzero(np.isin(col, HAIR))[0]
            if len(hv):
                pts["fringe"] = P(mid_u + .5, hv.max() + 1)
    elif side_view:
        prof = profile(face, full, pts, chin, eye_v, nose, rec, cam, s, px, est)
        pts.update(prof)
    # Visible opening (scoring): the lid overhang and lid line shade the top of the eyeball in Cycles; the opening
    # top moves down by the character's calibrated shadow band (views.json lid_shadow_h, in H). Report: geometric.
    if pts.get("eye") and pts.get("crown") and pts.get("chin"):
        extra["eye_geometric"] = list(pts["eye"])
        band = float(rec.get("lid_shadow_h", 0.0)) * (pts["chin"][1] - pts["crown"][1])
        e = pts["eye"]
        pts["eye"] = [e[0], round(min(e[1] + band, e[3] - 1), 2), e[2], e[3]]
    return pts, sorted(est), extra


def nose_box(face, depth, centre, radius_px, px):
    """Nose bump: skin connected to LM_nose standing above the surrounding face by more than NOSE_RELIEF of the peak
    relief. The face is a quadratic fitted on a ring just outside the bump (1.1-1.6 x the projected bump radius;
    the sector towards the mouth is left out: the lips sit in a recess)."""
    u0, v0 = centre[0], centre[1]
    r2 = 1.6 * radius_px
    v_lo, v_hi = int(max(0, v0 - r2 - 1)), int(min(px, v0 + r2 + 2))
    u_lo, u_hi = int(max(0, u0 - r2 - 1)), int(min(px, u0 + r2 + 2))
    vv, uu = np.mgrid[v_lo:v_hi, u_lo:u_hi]
    dz = depth[v_lo:v_hi, u_lo:u_hi]
    x, y = (uu + .5 - u0) / radius_px, (vv + .5 - v0) / radius_px
    d2 = x * x + y * y
    ok = (face[v_lo:v_hi, u_lo:u_hi] == C["skin"]) & np.isfinite(dz)
    ring = ok & (d2 >= 1.21) & (d2 <= 2.56) & ~((y > 0.6) & (np.abs(x) < 1.0))
    if ring.sum() < 30:
        return None
    basis = np.stack([np.ones_like(x), x, y, x * x, x * y, y * y])
    coef, *_ = np.linalg.lstsq(basis[:, ring].T, dz[ring], rcond=None)
    relief = np.where(ok & (d2 <= 2.56), np.tensordot(coef, basis, 1) - dz, -1)
    disk = ok & (d2 <= 0.5)
    if not disk.any():
        return None
    peak = relief[disk].max()
    if peak <= 0:
        return None
    seed = np.unravel_index(np.argmax(np.where(disk, relief, -1)), relief.shape)
    comp = flood(relief > NOSE_RELIEF * peak, (seed[1], seed[0]))
    b = bbox(comp)
    return None if b is None else (b[0] + u_lo, b[1] + v_lo, b[2] + u_lo, b[3] + v_lo)


def profile(face, full, pts, chin, eye_v, nose, rec, cam, s, px, est):
    """Side view: anterior skin points at eye level, 50 % and 85 % of the eye-to-chin fall; exposed skin window on
    the 50 % line; head/hair silhouette span at eye height; resolved nose tip."""
    out = {}
    if not chin:
        return out
    facing = -1 if nose[0] < px / 2 else 1  # face points image-left when the nose is left of centre
    out["facing"] = facing
    skin = face == C["skin"]
    prof = []
    for frac in (0.0, 0.5, 0.85):
        y = eye_v + frac * (chin[1] - eye_v)
        us = np.nonzero(skin[int(y)])[0]
        if not len(us):
            prof.append(None)
            continue
        u = us.min() if facing < 0 else us.max() + 1
        prof.append(P2(u, y, s))
        if not np.isin(full[int(y), min(px - 1, int(u) if facing < 0 else int(u) - 1)], FACE_SURFACE):
            est.add("profile")
    out["profile"] = prof
    if prof[1]:
        y = int(eye_v + 0.5 * (chin[1] - eye_v))
        # the most anterior uninterrupted visible skin run on the 50 % line (a lock may cover the anterior edge);
        # runs under 1 % of the frame are slivers between strands
        row = np.r_[False, full[y] == C["skin"], False]
        edges = np.flatnonzero(np.diff(row.astype(np.int8)))
        runs = [r for r in zip(edges[::2], edges[1::2]) if r[1] - r[0] >= 0.01 * px]
        if runs:
            a, b = min(runs, key=lambda r: r[0]) if facing < 0 else max(runs, key=lambda r: r[1])
            out["exposed"] = [P2(b, y, s), P2(a, y, s)] if facing < 0 else [P2(a, y, s), P2(b, y, s)]
    row = int(eye_v)
    sil = np.nonzero((full[row] != 0) & (full[row] != C["glasses"]))[0]
    if len(sil):
        out["profile_span"] = [P2(sil.min(), eye_v, s), P2(sil.max() + 1, eye_v, s)]
    tip = rec["surface"].get("nose_tip")
    out["nose_tip"] = P2(tip[0], tip[1], s) if tip and tip[4] else None
    return out


def P2(u, v, s):
    return [round(float(u) * s, 2), round(float(v) * s, 2)]


# ------------------------------------------------------------------------------------------------ evaluation
def evaluate(points, estimated, view, character, db, m204, reference_targets=True):
    """T-204 values for the traced points; rows against the targets of `view` when given."""
    vals = m204.values(points)
    rows = []
    targets = db["characters"][character]["targets"].get(view, {}) if view else {}
    for key in sorted(set(vals) | set(targets)):
        if key in COLOUR_MEASURES:
            continue
        spec = db["metrics"].get(key, {"depends": [], "unit": ""})
        t = targets.get(key)
        cur = vals.get(key)
        gap = cur - t["value"] if (t and cur is not None and t.get("value") is not None) else None
        rows.append(dict(measure=key, unit=spec["unit"], group="hair" if key in HAIR_MEASURES else "face",
                         current=None if cur is None else round(cur, 5),
                         mark=("E" if set(estimated) & set(spec["depends"]) else "M") if cur is not None else "",
                         reference=t["value"] if t else None, tolerance=t["tolerance"] if t else None,
                         gap=None if gap is None else round(gap, 5),
                         z=None if gap is None else round(gap / t["tolerance"], 3),
                         result="" if not t else ("unscored" if gap is None else
                                                  ("within" if abs(gap) <= t["tolerance"] else "outside"))))
    return rows


def blender_cmd():
    exe = os.environ.get("BLENDER")
    if exe:
        return [exe]
    return [sys.executable, str(ROOT / "tools/bpy_blender.py")]


def render(blend, views, px, iris, out):
    out.mkdir(parents=True, exist_ok=True)
    job = out / "measure-job.json"
    write(job, {"kind": "face_measure", "blend": str(Path(blend).resolve()), "px": px, "views": views,
                "iris_radius": iris})
    cmd = [*blender_cmd(), "-b", "--factory-startup", "-P", str(HERE / "render.py"), "--", str(job)]
    log = out / "blender.log"
    with log.open("w", encoding="utf-8") as stream:
        r = subprocess.run(cmd, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
    if r.returncode or not (out / "measure-views.json").is_file():
        raise RuntimeError(f"measure render failed, see {log}")
    return read(out / "measure-views.json")


def iris_radius(spec_path):
    """Visible iris edge in the eye shader's unit-sphere radius: the layered/felt ramp holds the dark limbal ring to
    radius - 0.35 limbal_width, then blends to sclera by radius + 0.012; in sRGB the edge reads at the ring's outer
    edge (T-202 front render: 28.5 units across vs 28.6 predicted, 30.2 at the nominal radius)."""
    eyes = read(spec_path)["face"]["eyes"]
    iris = eyes.get("iris", {})
    rho = float(iris.get("radius", 0.55))
    if eyes.get("shader") in ("layered/1", "felt/1"):
        rho -= 0.35 * float(iris.get("limbal_width", 0.06))
    return {"eye_L": rho, "eye_R": rho}


def measure_all(rendered, out, character, db, m204, view_names, nose_size=0.016, flags=(), lid_shadow_h=0.0):
    """Trace and evaluate every rendered view (front first: its chin anchors the profile and back views)."""
    px = rendered["px"]
    recs = sorted(rendered["views"], key=lambda r: (abs(r["yaw"]), bool(r["expression"])))  # neutral front first
    chin3d, results = None, []
    for rec in recs:
        with np.load(out / rec["arrays"]) as z:
            arrays = {k: z[k] for k in z.files}
        rec["nose_size_m"] = nose_size
        rec["flags"] = list(flags)
        rec["lid_shadow_h"] = lid_shadow_h
        rec["classes_present"] = rendered.get("classes_present", ["bun"])
        pts, est, extra = trace(rec, arrays, px, chin3d)
        if rec["yaw"] == 0 and "chin3d" in extra:
            chin3d = extra["chin3d"]
        view = view_names.get(rec["name"])
        try:
            rows = evaluate(pts, est, view, character, db, m204)
            error = None
            geo = dict(pts)
            for k in ("crown", "eye"):
                if f"{k}_geometric" in extra:
                    geo[k] = extra[f"{k}_geometric"]
            try:
                gv = m204.values(geo)
            except ValueError:
                gv = {}
            for row in rows:
                g = gv.get(row["measure"])
                row["geometric"] = None if g is None else round(g, 5)
        except ValueError as exc:
            rows, error = [], str(exc)
        results.append(dict(name=rec["name"], yaw=rec["yaw"], view=view, expression=rec["expression"],
                            points=pts, geometric={k: v for k, v in extra.items() if k.endswith("_geometric")},
                            estimated=est, rows=rows, error=error))
        overlay_view(arrays, pts, out / f"{rec['name']}-overlay.png", px)
    return results


def overlay_view(arrays, pts, path, px):
    pal = np.array([[34, 38, 44], [236, 205, 178], [214, 150, 120], [40, 30, 30], [70, 160, 255], [40, 110, 230],
                    [110, 70, 30], [245, 160, 160], [210, 40, 50], [100, 20, 30], [250, 230, 60], [150, 100, 60],
                    [110, 75, 45], [240, 80, 220], [120, 200, 120]], np.uint8)
    im = Image.fromarray(pal[arrays["full_cls"]]).resize((800, 800), Image.Resampling.NEAREST)
    d = ImageDraw.Draw(im)
    k = 2.0

    def xy(p):
        return (p[0] * k, p[1] * k)
    for key in ("left", "right"):
        if pts.get(key):
            d.line([xy(p) for p in pts[key]], fill="#00ffff", width=2)
    for key in ("eye", "mouth", "nose", "ear"):
        b = pts.get(key)
        if b:
            d.rectangle([b[0] * k, b[1] * k, b[2] * k, b[3] * k], outline="#ff00ff", width=2)
    for key in ("crown", "chin", "crest", "brow", "far", "skull", "fringe", "midbrow", "nose_tip"):
        p = pts.get(key)
        if p:
            d.ellipse([p[0] * k - 4, p[1] * k - 4, p[0] * k + 4, p[1] * k + 4], outline="#ffffff", width=2)
    for key in ("cap", "hair_at_cheek", "bun_span", "ear_turn", "exposed", "profile_span"):
        if pts.get(key):
            d.line([xy(p) for p in pts[key]], fill="#ffff00", width=2)
    if pts.get("profile"):
        for p in pts["profile"]:
            if p:
                d.ellipse([p[0] * k - 4, p[1] * k - 4, p[0] * k + 4, p[1] * k + 4], outline="#00ff00", width=2)
    if pts.get("iris"):
        l, y, r = pts["iris"]
        d.line([(l * k, y * k), (r * k, y * k)], fill="#00ffff", width=2)
    im.save(path)


def views_for(cfg, ch, yaws, neutral):
    """Render list: the 8 yaws (neutral) plus each reference view at its yaw with the matched expression."""
    c = cfg["characters"][ch]
    base = dict(target=c["target"], frame_h=c["frame_h"], elev=c["elev"])
    out, names = [], {}
    for v, spec in c["views"].items():
        expr = {} if neutral else spec.get("expression", {})
        name = f"ref-{v}"
        out.append(dict(base, name=name, yaw=spec["yaw"], expression=expr))
        names[name] = v
    for y in yaws:
        out.append(dict(base, name=f"y{y:+04d}", yaw=y, expression={}))
    return out, names


def summary(results, holdout):
    by = {}
    for r in results:
        if not r["view"]:
            continue
        scored = [x for x in r["rows"] if x["result"] in ("within", "outside")]
        for g in ("face", "hair"):
            sub = [x for x in scored if x["group"] == g]
            by[f"{r['view']}/{g}"] = dict(scored=len(sub), within=sum(x["result"] == "within" for x in sub),
                                          mean_abs_z=round(float(np.mean([abs(x["z"]) for x in sub])), 3)
                                          if sub else None, holdout=r["view"] == holdout)
    return by


def cmd_measure(args, validate=False):
    cfg = read(CONFIG)
    ch = cfg["characters"][args.character]
    db = read(T204 / "targets.json")
    m204 = t204()
    blend = args.blend or ROOT / f"assets/characters/{ch['id']}/versions/{ch['version']}/{ch['id']}_master.blend"
    spec = args.spec or Path(blend).parent / "spec.resolved.json"
    out = Path(args.out).resolve()
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"output must be empty: {out}")
    if out.is_relative_to((ROOT / "assets").resolve()):
        raise SystemExit("refusing output under assets/")
    t0 = time.perf_counter()
    views, names = views_for(cfg, args.character, [] if validate else cfg["yaws"], neutral=validate)
    rendered = render(blend, views, args.px, iris_radius(spec), out)
    t1 = time.perf_counter()
    nose = read(spec)["face"].get("nose", {})
    results = measure_all(rendered, out, args.character, db, m204, names,
                          float(nose.get("size_m", nose.get("radius_m", 0.016))), ch.get("flags", ()),
                          0.0 if args.geometric else float(ch.get("lid_shadow_h", 0.0)))
    t2 = time.perf_counter()
    report = dict(character=args.character, blend=str(blend), px=args.px, holdout=ch.get("holdout"),
                  timings=dict(render_s=round(t1 - t0, 2), measure_s=round(t2 - t1, 2),
                               blender=rendered["timings"]), views=results)
    if validate:
        report["validation"] = validation(results, args.character, db, m204)
        evidence(results, args.character, db, m204, out / "evidence.jpg")
    else:
        report["summary"] = summary(results, ch.get("holdout"))
    write(out / "measures.json", report)
    rows = [dict(view=r["name"], yaw=r["yaw"], target_view=r["view"] or "", **x) for r in results for x in r["rows"]]
    if rows:
        with (out / "measures.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=rows[0].keys(), lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
    print(json.dumps(report.get("validation", {}).get("summary") or report.get("summary"), indent=1))
    print(f"render {t1 - t0:.1f} s, measure {t2 - t1:.1f} s -> {out}")
    return report


def validation(results, character, db, m204):
    """Agreement of the measurer with T-204's hand traces of the same neutral T-202 renders. `with_hand_h` repeats
    each measure with the hand crown and chin (H) to separate a normalisation difference from a feature difference."""
    hand = {}
    with (T204 / "measures.csv").open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["character"] == character and r["current"] != "":
                hand[(r["view"], r["measure"])] = (float(r["current"]), float(r["tolerance"]), r["current_mark"])
    rows = []
    for r in results:
        mine = {x["measure"]: x for x in r["rows"]}
        hp = db["characters"][character]["views"][r["view"]]["current"]["points"]
        pts = dict(r["points"], crown=hp["crown"], chin=hp["chin"])
        for key in ("left", "right"):  # contours end at the chin
            if pts.get(key):
                pts[key] = [p for p in pts[key][:-1] if p[1] < hp["chin"][1]] + [hp["chin"]]
        try:
            alt = m204.values(pts)
        except ValueError:
            alt = {}
        for (view, key), (cur, tol, mark) in sorted(hand.items()):
            if view != r["view"] or key in COLOUR_MEASURES:
                continue
            m = mine.get(key, {}).get("current")
            diff = None if m is None else round(m - cur, 5)
            rows.append(dict(view=view, measure=key, group="hair" if key in HAIR_MEASURES else "face",
                             hand=cur, hand_mark=mark, measurer=m, measurer_mark=mine.get(key, {}).get("mark", ""),
                             geometric=mine.get(key, {}).get("geometric"),
                             diff=diff, tolerance=tol,
                             agree=None if diff is None else abs(diff) <= tol,
                             with_hand_h=None if key not in alt else round(alt[key], 5),
                             agree_with_hand_h=None if key not in alt else abs(alt[key] - cur) <= tol))
    n = [x for x in rows if x["agree"] is not None]
    return dict(rows=rows, summary=dict(compared=len(n), agree=sum(x["agree"] for x in n),
                                        agree_with_hand_h=sum(bool(x["agree_with_hand_h"]) for x in n),
                                        missing=[f"{x['view']}/{x['measure']}" for x in rows if x["agree"] is None],
                                        disagree=[f"{x['view']}/{x['measure']}" for x in n if not x["agree"]]))


def evidence(results, character, db, m204, path):
    """T-202 render tile per view with T-204's hand trace (cyan) and the measurer's points (yellow)."""
    base = T204.parent / "T-202"
    if not (base / "sheets").is_dir():
        base = ROOT / "build/in/docs/evaluation/characters/T-202"
    if not (base / "sheets").is_dir():
        return False
    tiles = []
    for r in results:
        trace_hand = db["characters"][character]["views"][r["view"]]["current"]
        tile = m204.source_image(base, trace_hand, "current").resize((600, 600), Image.Resampling.LANCZOS)
        d = ImageDraw.Draw(tile)
        k = 600 / N
        for pts, col in ((trace_hand["points"], "#45e6ed"), (r["points"], "#ffd36a")):
            for key in ("left", "right", "profile", "exposed", "ear_turn", "cap", "hair_at_cheek", "bun_span",
                        "profile_span"):
                line = pts.get(key)
                if line and all(p is not None for p in line):
                    d.line([(p[0] * k, p[1] * k) for p in line], fill=col, width=2)
            for key in ("eye", "mouth", "nose", "ear"):
                b = pts.get(key)
                if b:
                    d.rectangle([b[0] * k, b[1] * k, b[2] * k, b[3] * k], outline=col, width=2)
            for key in ("crown", "chin", "brow", "far", "fringe", "skull", "midbrow", "nose_tip"):
                p = pts.get(key)
                if p:
                    d.ellipse([p[0] * k - 5, p[1] * k - 5, p[0] * k + 5, p[1] * k + 5], outline=col, width=2)
            if pts.get("iris"):
                l, y, rr = pts["iris"]
                d.line([(l * k, y * k), (rr * k, y * k)], fill=col, width=2)
        d.text((8, 6), f"{r['view']}  yaw {r['yaw']}   cyan T-204 hand   yellow T-214 measurer", fill="white")
        tiles.append(tile)
    sheet = Image.new("RGB", (600 * len(tiles), 600))
    for i, t in enumerate(tiles):
        sheet.paste(t, (600 * i, 0))
    sheet.save(path, quality=88)
    return True


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("measure", "validate"):
        q = sub.add_parser(name)
        q.add_argument("--character", required=True, choices=sorted(read(CONFIG)["characters"]))
        q.add_argument("--out", required=True)
        q.add_argument("--blend", type=Path, help="default: the configured release master")
        q.add_argument("--spec", type=Path, help="resolved spec for the iris radius; default beside the blend")
        q.add_argument("--px", type=int, default=1024 if name == "validate" else 512)
        q.add_argument("--geometric", action="store_true", help="no lid-shadow band (calibration runs)")
    args = p.parse_args()
    cmd_measure(args, validate=args.cmd == "validate")


if __name__ == "__main__":
    main()
