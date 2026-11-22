"""T-183 round 3 measurement: every hair vertex of a character against the scene around it, every frame.

Surfaces, each counted apart:
  object:<name>     a box object of the scene (table top, legs, stools, floor, wall; world space, from the bake)
  prop:<name>       a prop at its baked transform of the frame; shape = the asset's mesh primitive (box centred,
                    sphere centred, cylinder standing on its base, axis y), scaled by the asset's scale
  <character>       the solid figure of another character (measure_body.py's Figure and exit distance; its hair is
                    not part of it), with --others
The depth of a hair vertex inside a box, sphere or cylinder is exact: the shortest way out. A vertex counts when it is
deeper than --limit-mm (default 1). The hair of the measured character is skinned from the package meshes with the
bake (tools/motion_checks/shot.py), as in measure_body.py.

    python3 measure_props.py <bake.json> --character=<name> [--out=out.json] [--limit-mm=1] [--frames=A-B] [--step=N]
                             [--jobs=N] [--others] [--skip-objects=pattern,pattern]

Needs the bpy module (mathutils) only with --others."""
import fnmatch
import glob
import json
import multiprocessing
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "motion_checks"))
import shot as S  # noqa: E402


def opt(name, default=None):
    return next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith(f"--{name}=")), default)


def skinner(ch, mi):
    P, _, J, Wt = ch.rest(mi)
    J = ch._joint_map()[J]

    def at(M):
        A = np.einsum("nk,nkij->nij", Wt, M[J])
        return np.einsum("nij,nj->ni", A[:, :3, :3], P) + A[:, :3, 3]
    return at


def box_depth(P, lo, hi):
    """Shortest way out of the box per point (0 outside)."""
    d = np.minimum(P - lo, hi - P).min(1)
    return np.maximum(d, 0.0)


def prop_assets(scene_path):
    """{prop id: asset json} from content/assets of the repository and of the scene's episode."""
    dirs = [os.path.join(ROOT, "content", "assets")]
    d = os.path.dirname(os.path.abspath(scene_path))
    while len(d) > len(ROOT):
        dirs.append(os.path.join(d, "content", "assets"))
        d = os.path.dirname(d)
    out = {}
    for a in dirs:
        for f in glob.glob(os.path.join(a, "**", "*.asset.json"), recursive=True):
            try:
                j = json.load(open(f))
            except ValueError:
                continue
            if isinstance(j, dict) and "id" in j:
                out[j["id"]] = j
    return out


def prop_shape(asset):
    m, s = asset.get("mesh", {}), float(asset.get("scale", 1.0))
    p = m.get("primitive")
    if p == "box":
        h = 0.5 * s * np.array(m["size"], dtype=float)
        return ("box", -h, h)
    if p == "sphere":
        return ("sphere", s * float(m["radius"]))
    if p == "cylinder":
        return ("cylinder", s * float(m["radius"]), s * float(m["height"]))
    return None


def prop_depth(P, M, shape):
    """Depth of world points P inside a prop with world matrix M (rigid, uniform scale)."""
    R, t = M[:3, :3], M[:3, 3]
    sc = float(np.cbrt(abs(np.linalg.det(R))))
    L = (P - t) @ np.linalg.inv(R).T  # prop space
    if shape[0] == "box":
        d = box_depth(L, shape[1], shape[2])
    elif shape[0] == "sphere":
        d = np.maximum(shape[1] - np.linalg.norm(L, axis=1), 0.0)
    else:
        r = np.hypot(L[:, 0], L[:, 2])
        d = np.maximum(np.minimum(shape[1] - r, np.minimum(L[:, 1], shape[2] - L[:, 1])), 0.0)
    return d * sc


_G = {}


def _frame(f):
    g = _G
    M = g["ch"].M[f]
    row = {"frame": int(g["shot"].frames[f]), "worst_mm": 0.0, "n": 0, "by_pair": {}}

    def note(part, surf, depth):
        ins = depth > g["limit"]
        if ins.any():
            w = float(depth[ins].max()) * 1000
            row["by_pair"][f"{part}>{surf}"] = [round(w, 1), int(ins.sum())]
            row["worst_mm"] = max(row["worst_mm"], w)
            row["n"] += int(ins.sum())

    hair = {part: sk(M) for part, sk in g["hair"].items()}
    lo = np.min([p.min(0) for p in hair.values()], axis=0)
    hi = np.max([p.max(0) for p in hair.values()], axis=0)
    for name, blo, bhi in g["boxes"]:
        if np.any(bhi < lo) or np.any(blo > hi):
            continue
        for part, P in hair.items():
            note(part, f"object:{name}", box_depth(P, blo, bhi))
    for name, shape in g["props"].items():
        Mp = g["shot"].props[name][f]
        for part, P in hair.items():
            note(part, f"prop:{name}", prop_depth(P, Mp, shape))
    for oname, (fig, och, mb) in g["others"].items():
        from mathutils import Vector
        from mathutils.bvhtree import BVHTree
        Mo = och.M[f]
        Ps = np.concatenate([fig.sk[i](Mo) for i in fig.solid])
        slo, shi = Ps.min(0) - 0.002, Ps.max(0) + 0.002
        if np.any(shi < lo) or np.any(slo > hi):
            continue
        tree = None
        for part, P in hair.items():
            idx = np.nonzero(np.all((P >= slo) & (P <= shi), axis=1))[0]
            if not len(idx):
                continue
            if tree is None:
                tree = BVHTree.FromPolygons(Ps.tolist(), fig.tris)
            depth = np.zeros(len(P))
            near = np.full(len(P), -1, dtype=np.int64)
            for k in idx:
                d, fi, _ = mb.depth_of(tree, Vector(P[k]))
                depth[k] = d
                if fi >= 0:
                    near[k] = fig.owner[fi]
            for s in np.unique(near[depth > g["limit"]]):
                note(part, f"{oname}:{fig.parts[s]}", np.where(near == s, depth, 0.0))
    return row


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    sh = S.Shot(args[0])
    name = opt("character")
    ch = next((c for c in sh.characters if c.name == name), None)
    if ch is None:
        raise SystemExit(f"--character: one of {[c.name for c in sh.characters]}")
    limit = float(opt("limit-mm", "1")) / 1000.0
    skip = [p for p in (opt("skip-objects", "") or "").split(",") if p]
    parts = [m["part"] for m in ch.doc["meshes"]]
    hair = {p: skinner(ch, i) for i, p in enumerate(parts) if p.startswith("hair_")}
    boxes = [(o["name"], np.array(o["min"], dtype=float), np.array(o["max"], dtype=float)) for o in sh.objects
             if o.get("kind") == "box" and not any(fnmatch.fnmatchcase(o["name"], s) for s in skip)]
    scene = json.load(open(sh.scene_path if os.path.isabs(sh.scene_path) else os.path.join(ROOT, sh.scene_path))) if sh.scene_path else {}
    assets = prop_assets(sh.scene_path or args[0])
    props, no_shape = {}, []
    for p in scene.get("props", []):
        shape = prop_shape(assets.get(p.get("id"), {}))
        if shape is not None and p["name"] in sh.props:
            props[p["name"]] = shape
        else:
            no_shape.append(p["name"])
    others = {}
    if "--others" in sys.argv:
        sys.argv = [a for a in sys.argv if a != "--legacy"]
        sys.path.insert(0, HERE)
        import measure_body as mb
        for oc in sh.characters:
            if oc.name != ch.name:
                others[oc.name] = (mb.Figure(oc, mb.SKIP), oc, mb)
    _G.update(shot=sh, ch=ch, limit=limit, hair=hair, boxes=boxes, props=props, others=others)
    frames = list(range(0, len(sh.frames), int(opt("step", "1"))))
    if opt("frames"):
        a, b = (int(x) for x in opt("frames").split("-"))
        frames = [f for f in frames if a <= int(sh.frames[f]) <= b]
    jobs = int(opt("jobs", str(min(4, os.cpu_count() or 1))))
    if jobs > 1 and len(frames) > 1:
        with multiprocessing.get_context("fork").Pool(jobs) as pool:
            rows = list(pool.imap(_frame, frames, chunksize=4))
    else:
        rows = [_frame(f) for f in frames]
    pair = {}
    for r in rows:
        for key, (w, n) in r["by_pair"].items():
            p = pair.setdefault(key, {"max_mm": 0.0, "frames": 0, "worst_frame": 0, "max_vertices": 0, "first": r["frame"], "last": r["frame"]})
            p["frames"] += 1
            p["last"] = r["frame"]
            p["max_vertices"] = max(p["max_vertices"], n)
            if w > p["max_mm"]:
                p["max_mm"], p["worst_frame"] = w, r["frame"]
    surf = {}
    for key, v in pair.items():
        s = surf.setdefault(key.split(">", 1)[1], {"max_mm": 0.0, "worst_frame": 0})
        if v["max_mm"] > s["max_mm"]:
            s["max_mm"], s["worst_frame"] = v["max_mm"], v["worst_frame"]
    for s in surf:
        surf[s]["frames"] = sum(1 for r in rows if any(k.split(">", 1)[1] == s for k in r["by_pair"]))
        surf[s]["max_vertices"] = max(sum(n for k, (_, n) in r["by_pair"].items() if k.split(">", 1)[1] == s) for r in rows)
    res = {"bake": args[0], "character": ch.name, "limit_mm": limit * 1000,
           "hair_vertices": int(sum(ch.doc["meshes"][i]["vertices"] for i, p in enumerate(parts) if p.startswith("hair_"))),
           "objects": [b[0] for b in boxes], "props": {k: v[0] for k, v in props.items()}, "props_without_shape": no_shape,
           "others": list(others), "frames": rows,
           "summary": {"frames_measured": len(rows), "frames_deeper_than_limit": sum(1 for r in rows if r["n"]),
                       "max_depth_mm": round(max((r["worst_mm"] for r in rows), default=0.0), 1),
                       "max_vertices": max((r["n"] for r in rows), default=0), "surfaces": surf, "pairs": pair}}
    print(f"{ch.name}: {res['hair_vertices']} hair vertices; objects {res['objects']}; props {res['props']}"
          f"{' (no shape: ' + ', '.join(no_shape) + ')' if no_shape else ''}; others {res['others']}")
    print("summary:", json.dumps({k: v for k, v in res["summary"].items() if k not in ("pairs", "surfaces")}))
    for k, v in sorted(surf.items(), key=lambda kv: -kv[1]["max_mm"]):
        print(f"  {k:36s} max {v['max_mm']:5.1f} mm (f{v['worst_frame']}), {v['frames']} frames, up to {v['max_vertices']} vertices")
    for k, v in sorted(pair.items(), key=lambda kv: -kv[1]["max_mm"]):
        print(f"    {k:60s} max {v['max_mm']:5.1f} mm (f{v['worst_frame']}), {v['frames']} frames f{v['first']}-{v['last']}, up to {v['max_vertices']} vertices")
    out = opt("out")
    if out:
        json.dump(res, open(out, "w"))


if __name__ == "__main__":
    main()
