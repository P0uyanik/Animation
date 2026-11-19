"""T-125 motion checks: flicker / shimmer, popping and interpenetration over time on a baked (and rendered) shot.
Not part of the gate (tools/check_all.py does not run it). README.md has the method and the thresholds.

    python3 tools/motion_checks/run.py --bake <run>/bake.json [--scene <shot>/build/shot.resolved.scene.json] \
        [--trace trace.json] [--frames <npz dir>] --out <dir> [--strips N] [--root <repo>] [--check]

--trace: collision_trace.cpp output for the same scene (interpenetration on the engine's collision bodies).
--frames: render_passes.py output (flicker; rendered crops in every evidence strip).
Writes <out>/motion_checks.json and <out>/strips/*.jpg (the N worst issues per check, default 4).
--check: exit 1 when any issue (fast-by-design channels excluded) is found."""
import argparse
import json
import os
import sys

import numpy as np


def _load(path):
    with open(path) as f:
        return json.load(f)

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import evidence as EV  # noqa: E402
import flicker  # noqa: E402
import frames as FR  # noqa: E402
import penetration as PEN  # noqa: E402
import popping  # noqa: E402
import shot as SH  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))


def load_thresholds(path=None):
    return _load(path or os.path.join(HERE, "thresholds.json"))


def char(shot, name):
    return next((c for c in shot.characters if c.name == name), None)


def pivot(shot, cname, bone, f):
    c = char(shot, cname)
    if c is None or bone not in c.bones:
        return None
    i = list(shot.frames).index(f)
    return c.pivots()[i, c.bones.index(bone)]


def point_of(shot, issue, thr):
    """World point an issue is about (for the rendered crops), or None."""
    f, kind, owner, ch = issue["peak_frame"], issue["kind"], issue.get("owner"), issue.get("channel", "")
    i = list(shot.frames).index(f)
    if issue["check"] == "popping":
        if kind in ("joint", "rotation"):
            return pivot(shot, owner, ch, f)
        if kind == "morph":
            return pivot(shot, owner, "head", f)
        if kind.startswith("prop"):
            return shot.props[ch][i, :3, 3]
        if kind == "mesh":
            c = char(shot, owner)
            mi = c.mesh_index(ch)
            v = issue["vertex_sample"] * thr["popping"].get("mesh_stride", 16)
            return c.skin(mi, np.array([v]))[0][i, 0]
    if kind == "arm":
        return pivot(shot, owner, "hand." + ch.split(".")[-1], f)
    if kind == "head":
        a, b = owner.split("+")
        pa, pb = pivot(shot, a, "head", f), pivot(shot, b, "head", f)
        return None if pa is None or pb is None else (pa + pb) / 2 + np.array([0, 0.1, 0])
    if kind == "limb":
        cname, bone = ch.split(".", 1)
        return pivot(shot, cname, bone, f)
    if kind in ("hand_prop", "prop_body", "prop_room"):
        return shot.props[owner][i, :3, 3] if owner in shot.props else None
    if kind == "garment":
        c = char(shot, owner)
        mi = c.mesh_index(ch)
        v = issue["vertex_sample"] * thr["interpenetration"]["garment_stride"]
        return c.skin(mi, np.array([v]), with_morphs=False)[0][i, 0]
    return None


def series_of(issue, ctx):
    """(values per bake frame, limit, label) for an issue's plot."""
    k, ch, owner = issue["kind"], issue.get("channel"), issue.get("owner")
    if issue["check"] == "popping":
        for o, names, A, P in ctx["chan"][k]:
            if o == owner and ch in names:
                j = names.index(ch)
                a = A[j].max(axis=1) if k == "mesh" else A[:, j]
                return a, issue.get("limit", ctx["thr"]["popping"][k]["abs_min"]), f"{owner} {ch} |a| {issue['unit']}"
    if issue["check"] == "interpenetration":
        tr = ctx.get("trace")
        if k == "arm":
            c = next(c for c in tr["characters"] if c["name"] == owner)
            v = c["arm"][ch.split(".")[1]]["gap"]
        elif k == "head":
            v = next(p for p in tr["pairs"] if f"{p['a']}+{p['b']}" == owner)["head_gap"]
        elif k == "limb":
            v = next(p for p in tr["pairs"] if f"{p['a']}+{p['b']}" == owner)["limb"][ch]
        elif k in ("hand_prop", "prop_body"):
            v = next(p for p in tr["props"] if p["name"] == owner)["hand" if k == "hand_prop" else "body"][ch]
        else:
            return None
        return np.asarray(v) * 1000, issue["limit_mm"], f"{owner} {ch} gap mm"
    if issue["check"] == "flicker":
        meas, key = ctx["flicker_meas"], issue["kind"]
        vals = []
        for f in ctx["shot"].frames:
            r = meas.get(int(f), {}).get("regions", {}).get(issue["region"])
            if r is None:
                vals.append(np.nan)
            elif key == "tile_flip_share":
                tm = meas[int(f)]["tiles"][issue["region"]]
                vals.append(float(np.nanmax(tm)) if np.isfinite(tm).any() else np.nan)
            else:
                vals.append(r["denoised"].get("noise" if key == "held_noise" else "flip_share", np.nan))
        return np.array(vals), issue["limit"], f"{issue['region']} {key}"
    return None


def write_strips(issues, ctx, out, n):
    os.makedirs(os.path.join(out, "strips"), exist_ok=True)
    shot, data, fr = ctx["shot"], ctx.get("frames_data"), ctx.get("frames_list")
    done = {}
    for iss in issues:
        if iss.get("by_design"):
            continue
        c = iss["check"]
        if done.get(c, 0) >= n:
            continue
        done[c] = done.get(c, 0) + 1
        name = f"{c}_{done[c]:02d}_{iss['kind']}_f{iss['peak_frame']}.jpg"
        panels = []
        if data is not None:
            if c == "flicker" and "bbox_px" in iss:
                x0, y0, x1, y1 = iss["bbox_px"]
                cx, cy = (iss["worst_tile_px"][0] + 8, iss["worst_tile_px"][1] + 8)
                t = fr.index(iss["peak_frame"])
                ft = ctx["thr"]["flicker"]
                if "vector" in data:  # the motion-compensated flips the check counted
                    w = flicker.compensated(data, t)
                    fmap = flicker.flips(w["denoised"], 1, ft["eps"], ft["flip_min"]) & w["same"]
                else:
                    fmap = flicker.flips(data["denoised"], t, ft["eps"], ft["flip_min"])
                fmap = (fmap * 255).astype(np.uint8)
                panels += EV.frame_crops(data["denoised"], fr, iss["peak_frame"], cx, cy, fmap)
            else:
                p = point_of(shot, iss, ctx["thr"])
                if p is not None:
                    H, W = data["denoised"].shape[1:]
                    xy = SH.project(shot.cameras[list(shot.frames).index(iss["peak_frame"])], p, W, H)
                    if xy is not None:
                        panels += EV.frame_crops(data["denoised"], fr, iss["peak_frame"], *xy)
        s = series_of(iss, ctx)
        if s is not None:
            panels.append(EV.plot(s[0], list(shot.frames), iss["peak_frame"], s[1], iss["frames"][0], iss["frames"][1], s[2]))
        if panels:
            EV.strip(os.path.join(out, "strips", name), panels)
            iss["strip"] = f"strips/{name}"


def run(a):
    thr = load_thresholds(a.thresholds)
    shot = SH.Shot(a.bake)
    rep = {"format": "plush.motion_checks", "version": 1,
           "inputs": {"bake": os.path.relpath(a.bake, a.root), "scene": a.scene and os.path.relpath(a.scene, a.root),
                      "trace": a.trace and os.path.relpath(a.trace, a.root), "frames": a.frames and os.path.relpath(a.frames, a.root),
                      "bake_frames": [int(shot.frames[0]), int(shot.frames[-1])]},
           "thresholds": thr, "stats": {}, "issues": []}
    ctx = {"shot": shot, "thr": thr}
    # popping
    ctx["chan"] = popping.channels(shot, thr["popping"].get("mesh_stride", 16))
    iss, st = popping.find(shot, thr["popping"], chan=ctx["chan"])
    rep["stats"]["popping"] = st
    rep["issues"] += iss
    # interpenetration
    pt = thr["interpenetration"]
    rep["stats"]["interpenetration"] = {}
    if a.trace:
        ctx["trace"] = _load(a.trace)
        iss, st = PEN.from_trace(ctx["trace"], pt)
        rep["stats"]["interpenetration"]["trace"] = st
        rep["issues"] += iss
    iss, st = PEN.garment(shot, pt)
    rep["stats"]["interpenetration"]["garment"] = st
    rep["issues"] += iss
    if a.scene:
        assets = PEN.load_assets(a.root, _load(a.scene))
        iss, st = PEN.prop_room(shot, assets, pt)
        rep["stats"]["interpenetration"]["prop_room"] = st
        rep["issues"] += iss
    # flicker
    if a.frames:
        fr, data = FR.load_dir(a.frames)
        ctx["frames_list"], ctx["frames_data"] = fr, data
        meas = flicker.measure(fr, data, thr["flicker"])
        ctx["flicker_meas"] = meas
        iss, st = flicker.find(fr, data, thr["flicker"], meas=meas)
        rep["stats"]["flicker"] = st
        rep["inputs"]["rendered_frames"] = [fr[0], fr[-1], len(fr)]
        rep["issues"] += iss
    os.makedirs(a.out, exist_ok=True)
    write_strips(rep["issues"], ctx, a.out, a.strips)
    counted = [i for i in rep["issues"] if not i.get("by_design")]
    rep["counts"] = {c: sum(1 for i in counted if i["check"] == c) for c in ("flicker", "popping", "interpenetration")}
    rep["counts"]["by_design"] = len(rep["issues"]) - len(counted)
    with open(os.path.join(a.out, "motion_checks.json"), "w") as f:
        json.dump(rep, f, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))
    return rep


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--bake", required=True)
    ap.add_argument("--scene", default="")
    ap.add_argument("--trace", default="")
    ap.add_argument("--frames", default="")
    ap.add_argument("--out", required=True)
    ap.add_argument("--thresholds", default="")
    ap.add_argument("--strips", type=int, default=4)
    ap.add_argument("--root", default=ROOT)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    rep = run(a)
    print(json.dumps({"counts": rep["counts"], "out": a.out}))
    return 1 if a.check and any(rep["counts"][c] for c in ("flicker", "popping", "interpenetration")) else 0


if __name__ == "__main__":
    sys.exit(main())
