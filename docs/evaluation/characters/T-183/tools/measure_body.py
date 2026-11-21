"""T-183 round 2 measurement: every hair vertex of a character against every body and garment surface, every frame.

Skins the package meshes with a plush.shot_bake/1 (tools/motion_checks/shot.py) and reports, per frame and per pair
(hair part > solid part), how deep hair vertices are behind the solid's surface (signed distance to the nearest
face, bpy BVH; negative = behind the face = inside). A vertex counts when it is deeper than --limit-mm (default 1).

    python3 measure_body.py <bake.json> [--out=out.json] [--character=girl] [--limit-mm=1] [--frames=A-B] [--step=N]
                            [--skip=pattern,pattern] [--roots=<mm>] [--rest]

--skip     solid parts left out (name patterns; default: the parts no hair should be tested against, see SKIP).
--roots    a hair vertex that is inside a solid in the rest pose AND is carried by the same bone as the surface it is
           in is a root (the scalp end of a lock, the inner side of the cap): it cannot move against that surface.
           Roots deeper at rest than this many mm are listed apart ("roots") and not counted (default 0 = count all).
--rest     measure the package's rest pose only (frame 0 of the table = rest).
Needs the bpy module (mathutils)."""
import fnmatch
import json
import os
import sys

import bpy  # noqa: F401 (makes mathutils importable)
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "..", "tools", "motion_checks"))
import shot as S  # noqa: E402

# solids that are not body or garment surfaces for this measure: face features that lie in the head's surface, and
# what the hair carries itself
SKIP = ["eye*", "brow*", "lash*", "lid*", "iris*", "pupil*", "mouth*", "teeth*", "tongue*", "nose*", "glasses*", "blush*",
        "cheek*", "freckle*"]
REACH = 0.08  # m: search distance for the nearest face


def opt(name, default=None):
    return next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith(f"--{name}=")), default)


def skinner(ch, mi):
    P, _, J, Wt = ch.rest(mi)
    J = ch._joint_map()[J]

    def at(M):  # M: (B, 4, 4)
        A = np.einsum("nk,nkij->nij", Wt, M[J])
        return np.einsum("nij,nj->ni", A[:, :3, :3], P) + A[:, :3, 3]
    return P, J, Wt, at


def tree_of(P, T):
    return BVHTree.FromPolygons([Vector(p) for p in P], T)


def signed(tree, Q):
    """Signed distance of points Q to the surface (negative = behind the nearest face), and the face index."""
    d = np.full(len(Q), 1.0)
    fi = np.full(len(Q), -1, dtype=np.int64)
    for i, q in enumerate(Q):
        v = Vector(q)
        loc, nrm, idx, dist = tree.find_nearest(v, REACH)
        if loc is None:
            continue
        d[i] = dist if (v - loc).dot(nrm) >= 0 else -dist
        fi[i] = idx
    return d, fi


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    sh = S.Shot(args[0])
    name = opt("character", "girl")
    ch = next((c for c in sh.characters if c.name == name), sh.characters[0])
    limit = float(opt("limit-mm", "1")) / 1000.0
    root_mm = float(opt("roots", "0"))
    step = int(opt("step", "1"))
    skip = SKIP + [p for p in (opt("skip", "") or "").split(",") if p]
    parts = [m["part"] for m in ch.doc["meshes"]]
    hair = [i for i, p in enumerate(parts) if p.startswith("hair_")]
    solid = [i for i, p in enumerate(parts) if not p.startswith("hair_") and not any(fnmatch.fnmatchcase(p, s) for s in skip)]
    sk = {i: skinner(ch, i) for i in hair + solid}
    tris = {i: [tuple(int(x) for x in t) for t in ch.array(ch.doc["meshes"][i]["indices"], 3)] for i in solid}
    dom = {i: sk[i][1][np.arange(len(sk[i][1])), np.argmax(sk[i][2], axis=1)] for i in hair + solid}  # dominant bone
    frames = list(range(0, len(sh.frames), step))
    if opt("frames"):
        a, b = (int(x) for x in opt("frames").split("-"))
        frames = [f for f in frames if a <= int(sh.frames[f]) <= b]

    # rest pose: which hair vertices are roots (inside a solid at rest, carried by the bone that carries that surface)
    roots = {}
    rest_rows = {}
    for si in solid:
        Ps = sk[si][0]
        tree = tree_of(Ps, tris[si])
        lo, hi = Ps.min(0), Ps.max(0)
        T = np.asarray(tris[si])
        for hi_ in hair:
            Ph = sk[hi_][0]
            near = np.nonzero(np.all((Ph >= lo) & (Ph <= hi), axis=1))[0]
            if not len(near):
                continue
            d, fi = signed(tree, Ph[near])
            ins = d < -limit
            if ins.any():
                rest_rows[f"{parts[hi_]}>{parts[si]}"] = [round(float(-d.min()) * 1000, 1), int(ins.sum())]
            if root_mm > 0:
                deep = d < -root_mm / 1000.0
                same = np.zeros(len(near), dtype=bool)
                ok = fi >= 0
                same[ok] = dom[si][T[fi[ok], 0]] == dom[hi_][near[ok]]
                r = near[deep & same]
                if len(r):
                    roots.setdefault(hi_, {})[si] = set(int(x) for x in r)
    print("rest pose, hair inside solids (mm, vertices):", json.dumps(rest_rows, indent=1))
    if root_mm > 0:
        print("roots (not counted):", {f"{parts[h]}>{parts[s]}": len(v) for h, d in roots.items() for s, v in d.items()})
    res = {"bake": args[0], "character": ch.name, "limit_mm": limit * 1000, "hair_vertices": int(sum(len(sk[i][0]) for i in hair)),
           "hair_parts": [parts[i] for i in hair], "solid_parts": [parts[i] for i in solid], "rest": rest_rows,
           "roots": {f"{parts[h]}>{parts[s]}": len(v) for h, d in roots.items() for s, v in d.items()}, "frames": []}
    if "--rest" in sys.argv:
        frames = []
    pair = {}
    for f in frames:
        M = ch.M[f]
        H = {i: sk[i][3](M) for i in hair}
        row = {"frame": int(sh.frames[f]), "worst_mm": 0.0, "n": 0, "by_pair": {}}
        for si in solid:
            Ps = sk[si][3](M)
            lo, hi = Ps.min(0), Ps.max(0)
            tree = None
            for hi_ in hair:
                Ph = H[hi_]
                near = np.nonzero(np.all((Ph >= lo) & (Ph <= hi), axis=1))[0]
                if hi_ in roots and si in roots[hi_]:
                    near = np.array([i for i in near if int(i) not in roots[hi_][si]], dtype=np.int64)
                if not len(near):
                    continue
                if tree is None:
                    tree = tree_of(Ps, tris[si])
                d, _ = signed(tree, Ph[near])
                ins = d < -limit
                if ins.any():
                    key = f"{parts[hi_]}>{parts[si]}"
                    w = float(-d.min()) * 1000
                    row["by_pair"][key] = [round(w, 1), int(ins.sum())]
                    row["worst_mm"] = max(row["worst_mm"], w)
                    row["n"] += int(ins.sum())
                    p = pair.setdefault(key, {"max_mm": 0.0, "frames": 0, "worst_frame": 0, "max_vertices": 0})
                    p["frames"] += 1
                    p["max_vertices"] = max(p["max_vertices"], int(ins.sum()))
                    if w > p["max_mm"]:
                        p["max_mm"], p["worst_frame"] = round(w, 1), int(sh.frames[f])
        res["frames"].append(row)
        top = sorted(row["by_pair"].items(), key=lambda kv: -kv[1][0])[:4]
        print(f"f{row['frame']:4d} worst {row['worst_mm']:5.1f} mm n={row['n']:5d} {top}", flush=True)
    bad = [r for r in res["frames"] if r["n"]]
    res["summary"] = {"frames_measured": len(res["frames"]), "frames_deeper_than_limit": len(bad),
                      "max_depth_mm": round(max((r["worst_mm"] for r in res["frames"]), default=0.0), 1),
                      "max_vertices": max((r["n"] for r in res["frames"]), default=0), "pairs": pair}
    print("summary:", json.dumps({k: v for k, v in res["summary"].items() if k != "pairs"}))
    for k, v in sorted(pair.items(), key=lambda kv: -kv[1]["max_mm"]):
        print(f"  {k:48s} max {v['max_mm']:5.1f} mm (f{v['worst_frame']}), {v['frames']} frames, up to {v['max_vertices']} vertices")
    out = opt("out")
    if out:
        json.dump(res, open(out, "w"))


if __name__ == "__main__":
    main()
