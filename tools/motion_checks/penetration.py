"""Interpenetration over time.

From the collision trace (collision_trace.cpp: the engine's own collision bodies, per frame; metres, negative =
inside), thresholds in mm:
  arm          body-body / body-garment: a character's forearm (wrist half) and hand capsules, sleeve included,
               against its own torso + garment shell (counted from the rest allowance, so the rest pose is 0 deep)
  head         character-character: the two head and hair shells (T-096 volumes; negative = overlapping)
  limb         character-character: one character's limb capsules against the other's torso shell
  hand_prop    hand-prop: a hand capsule against a prop's collision proxy. The hand capsule covers palm and fingers,
               so a grip puts the handle inside it: only depth beyond the measured grip depth counts
  prop_body    prop-body: the prop proxy's surface samples against each torso shell
From the bake and the packages (mesh level):
  garment      body-garment: sampled garment vertices against the nearest body-skin vertex at rest carried by the
               same dominant bone (skin normal direction), both skinned with the bake. A garment vertex that goes deeper under the skin than at rest by more
               than the threshold, and is under it, means skin shows through or the cloth sinks into the body
  prop_room    prop against the room's box objects (table top, floor, wall): proxy axis samples to the box surface
Each issue: the frame range below the threshold, the worst frame and depth."""
import json

import numpy as np


def _load(path):
    with open(path) as f:
        return json.load(f)



def runs(values, frames, limit_mm, what, extra):
    """Issues for each run of frames whose value (metres) is below limit_mm."""
    v = np.asarray(values, dtype=np.float64) * 1000
    hit = v < limit_mm
    out = []
    if not hit.any():
        return out
    idx = np.nonzero(hit)[0]
    for r in np.split(idx, np.nonzero(np.diff(idx) > 1)[0] + 1):
        k = r[np.argmin(v[r])]
        out.append({"check": "interpenetration", "kind": what, **extra, "frames": [int(frames[r[0]]), int(frames[r[-1]])],
                    "peak_frame": int(frames[k]), "value_mm": round(float(v[k]), 2), "limit_mm": limit_mm})
    return out


def from_trace(trace, thr):
    fr = trace["frames"]
    out, stats = [], {}

    def note(kind, name, vals):
        m = float(np.min(vals)) * 1000
        s = stats.setdefault(kind, {"min_mm": 1e9, "at": None})
        if m < s["min_mm"]:
            s.update(min_mm=round(m, 2), at=f"{name} f{fr[int(np.argmin(vals))]}")

    for c in trace["characters"]:
        for side, a in c.get("arm", {}).items():
            note("arm", f"{c['name']}.{side}", a["gap"])
            for i in runs(a["gap"], fr, thr["arm_mm"], "arm", {"owner": c["name"], "channel": f"arm.{side}"}):
                k = fr.index(i["peak_frame"])
                i["part"], i["against"] = a["part"][k], a["against"][k]
                out.append(i)
    for p in trace["pairs"]:
        pair = f"{p['a']}+{p['b']}"
        if "head_gap" in p and min(p["head_gap"]) < 1e8:
            note("head", pair, p["head_gap"])
            out += runs(p["head_gap"], fr, thr["head_mm"], "head", {"owner": pair, "channel": "head/hair shells"})
        for name, v in p.get("limb", {}).items():
            note("limb", name, v)
            out += runs(v, fr, thr["limb_mm"], "limb", {"owner": pair, "channel": name})
    for p in trace["props"]:
        for name, v in p.get("hand", {}).items():
            note("hand_prop", f"{p['name']}/{name}", v)
            out += runs(v, fr, thr["hand_prop_mm"], "hand_prop", {"owner": p["name"], "channel": name})
        for name, v in p.get("body", {}).items():
            note("prop_body", f"{p['name']}/{name}", v)
            out += runs(v, fr, thr["prop_body_mm"], "prop_body", {"owner": p["name"], "channel": name})
    return out, stats


# --- mesh level: body-garment ---------------------------------------------------------------------------------------
def skin_meshes(c):
    return [i for i, m in enumerate(c.doc["meshes"]) if m["part"] in ("body_skin",) or m["part"].startswith("hand.")]


def garment_meshes(c):
    return [i for i, m in enumerate(c.doc["meshes"]) if m["part"].startswith("garment.")]


def nearest(src, dst, chunk=2048):
    """Index into dst of the nearest point for every src point (brute force in chunks) and the distance."""
    idx = np.empty(len(src), dtype=np.int64)
    dist = np.empty(len(src))
    d2 = (dst ** 2).sum(1)
    for s in range(0, len(src), chunk):
        a = src[s:s + chunk]
        D = (a ** 2).sum(1)[:, None] - 2 * a @ dst.T + d2[None]
        k = np.argmin(D, 1)
        idx[s:s + chunk] = k
        dist[s:s + chunk] = np.sqrt(np.maximum(D[np.arange(len(a)), k], 0))
    return idx, dist


def garment_depths(c, thr):
    """{garment part: ((F, n) signed offset (m) of sampled garment vertices from their paired skin vertex along its
    normal, (n,) the rest offset)}. A garment vertex is paired at rest with the nearest skin vertex carried by the
    same dominant bone (largest skinning weight) within garment_pair_max_m, so the pair moves together and the
    offset changes only where the skinning of cloth and body differ."""
    gs, ss = thr["garment_stride"], thr["skin_stride"]
    sm = skin_meshes(c)
    sels = [np.arange(0, c.doc["meshes"][mi]["vertices"], ss) for mi in sm]
    rest = [c.rest(mi, sel) for mi, sel in zip(sm, sels)]
    rest_skin = np.concatenate([r[0] for r in rest])
    rest_nrm = np.concatenate([r[1] for r in rest])
    skin_dom = np.concatenate([r[2][np.arange(len(r[2])), np.argmax(r[3], 1)] for r in rest])
    posed = [c.skin(mi, sel, with_morphs=False) for mi, sel in zip(sm, sels)]
    SP, SN = np.concatenate([p for p, _ in posed], 1), np.concatenate([n for _, n in posed], 1)
    out = {}
    for mi in garment_meshes(c):
        m = c.doc["meshes"][mi]
        sel = np.arange(0, m["vertices"], gs)
        if len(sel) == 0:
            continue
        rg, _, gj, gw = c.rest(mi, sel)
        gdom = gj[np.arange(len(gj)), np.argmax(gw, 1)]
        k = np.full(len(sel), -1)
        dist = np.full(len(sel), np.inf)
        for j in np.unique(gdom):
            cand = np.nonzero(skin_dom == j)[0]
            mine = np.nonzero(gdom == j)[0]
            if len(cand) == 0:
                continue
            kk, dd = nearest(rg[mine], rest_skin[cand])
            k[mine], dist[mine] = cand[kk], dd
        near = dist < thr["garment_pair_max_m"]
        if not near.any():
            continue
        sel, k, rg = sel[near], k[near], rg[near]
        d_rest = np.einsum("ni,ni->n", rg - rest_skin[k], rest_nrm[k])
        GP, _ = c.skin(mi, sel, with_morphs=False)
        d = np.einsum("fni,fni->fn", GP - SP[:, k], SN[:, k])
        out[m["part"]] = (d, d_rest)
    return out


def garment(shot, thr):
    out, stats = [], {}
    for c in shot.characters:
        for part, (d, d_rest) in garment_depths(c, thr).items():
            sink = d_rest[None] - d  # how much deeper than at rest (m)
            bad = (d < 0) & (sink * 1000 > thr["garment_mm"])
            per = np.where(d < 0, sink, 0).max(1) * 1000  # worst per frame
            s = stats.setdefault(c.name, {"max_sink_mm": 0, "at": None})
            if per.max() > s["max_sink_mm"]:
                s.update(max_sink_mm=round(float(per.max()), 2), at=f"{part} f{shot.frames[int(np.argmax(per))]}")
            hitf = bad.any(1)
            if not hitf.any():
                continue
            idx = np.nonzero(hitf)[0]
            for r in np.split(idx, np.nonzero(np.diff(idx) > 1)[0] + 1):
                k = r[np.argmax(per[r])]
                out.append({"check": "interpenetration", "kind": "garment", "owner": c.name, "channel": part,
                            "frames": [int(shot.frames[r[0]]), int(shot.frames[r[-1]])], "peak_frame": int(shot.frames[k]),
                            "value_mm": round(-float(per[k]), 2), "limit_mm": -thr["garment_mm"],
                            "vertices": int(bad[k].sum()), "vertex_sample": int(np.argmax(np.where(bad[k], sink[k], -1)))})
    return out, stats


# --- props against the room ------------------------------------------------------------------------------------------
def prop_proxy(asset):
    """(axis a, axis b, radius) in prop-local metres from a plush.asset collision block (capsule / sphere / box)."""
    col = asset.get("collision") or {}
    k = asset.get("scaleMetres", 1.0)
    if col.get("type") == "capsule":
        r, h = col["radius"] * k, col["height"] * k
        return np.array([0, r, 0.0]), np.array([0, h - r, 0.0]), r
    if col.get("type") == "sphere":
        r = col["radius"] * k
        return np.zeros(3), np.zeros(3), r
    mesh = asset.get("mesh", {})
    r = mesh.get("radius", 0.05) * k
    h = mesh.get("height", 2 * r / k) * k
    return np.array([0, min(r, h / 2), 0.0]), np.array([0, max(h - r, h / 2), 0.0]), min(r, h / 2)


def box_gap(p, lo, hi):
    """Signed distance of points p (n, 3) to an axis-aligned box (negative inside)."""
    q = np.maximum(lo - p, p - hi)
    outside = np.linalg.norm(np.maximum(q, 0), axis=1)
    inside = np.minimum(q.max(1), 0)
    return outside + inside


def prop_room(shot, assets, thr):
    """assets: {prop name: plush.asset dict}."""
    out, stats = [], {}
    for name, M in shot.props.items():
        if name not in assets:
            continue
        a, b, r = prop_proxy(assets[name])
        ts = np.linspace(0, 1, 9)
        local = np.concatenate([a[None] * (1 - ts[:, None]) + b[None] * ts[:, None], np.ones((9, 1))], 1)
        P = np.einsum("fij,nj->fni", M, local)[..., :3]
        for o in shot.objects:
            if o.get("kind") != "box":
                continue
            lo, hi = np.array(o["min"]), np.array(o["max"])
            g = np.array([box_gap(P[f], lo, hi).min() - r for f in range(len(P))])
            key = f"{name}/{o['name']}"
            stats[key] = {"min_mm": round(float(g.min() * 1000), 2), "at": int(shot.frames[int(np.argmin(g))])}
            out += runs(g, list(shot.frames), thr["prop_room_mm"], "prop_room", {"owner": name, "channel": o["name"]})
    return out, stats


def load_assets(root, scene):
    """{prop name: asset json} for the scene's props (content/assets/*.asset.json by id)."""
    import glob
    import os
    by_id = {}
    for p in glob.glob(os.path.join(root, "content", "assets", "*.asset.json")):
        try:
            d = _load(p)
            by_id[d.get("id")] = d
        except (OSError, ValueError):
            pass
    return {p["name"]: by_id[p["id"]] for p in scene.get("props", []) if p.get("id") in by_id}
