"""T-183 measurement: the girl's hand vertices inside her hair meshes and hair vertices inside her ear meshes, per frame
(skinned from a plush.shot_bake/1 with tools/motion_checks/shot.py; signed distance to the nearest face, bpy BVH).

    python3 measure_contact.py <bake.json> [--out=out.json]   (needs the bpy module for mathutils)
"""
import json
import os
import sys

import bpy  # noqa: F401 (makes mathutils importable)
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "..", "tools", "motion_checks"))
import shot as S  # noqa: E402


def skin_frame(ch, mi, f):
    P, N, J, Wt = ch.rest(mi)
    J = ch._joint_map()[J]
    A = np.einsum("nk,nkij->nij", Wt, ch.M[f][J])
    return np.einsum("nij,nj->ni", A[:, :3, :3], P) + A[:, :3, 3]


def tris(ch, mi):
    m = ch.doc["meshes"][mi]
    a = m["indices"]
    return ch.array(a, 3).astype(np.int64)


def bvh(P, T):
    return BVHTree.FromPolygons([Vector(p) for p in P], [tuple(int(i) for i in t) for t in T])


def depth_inside(tree, Q):
    """Signed distance of points Q to the surface (negative = behind the nearest face = inside), metres."""
    out = np.full(len(Q), 1.0)
    for i, q in enumerate(Q):
        loc, nrm, _, dist = tree.find_nearest(Vector(q), 0.05)
        if loc is None:
            continue
        out[i] = dist if (Vector(q) - loc).dot(nrm) >= 0 else -dist
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    sh = S.Shot(args[0])
    ch = next(c for c in sh.characters if c.name == "girl") if len(sh.characters) > 1 else sh.characters[0]
    parts = [m["part"] for m in ch.doc["meshes"]]
    hair = [i for i, p in enumerate(parts) if p.startswith("hair_")]
    ears = [i for i, p in enumerate(parts) if p.startswith("ear.")]
    hands = [i for i, p in enumerate(parts) if p.startswith("hand.")]
    F = len(sh.frames)
    T = {i: tris(ch, i) for i in hair + ears + hands}
    res = {"frames": [int(x) for x in sh.frames], "hand_hair": [], "hair_ear": [], "parts": {}}
    step = 1
    hand_sel = {i: np.arange(0, ch.doc["meshes"][i]["vertices"], 3) for i in hands}
    for f in range(0, F, step):
        Hd = {i: skin_frame(ch, i, f) for i in hands}
        Er = {i: skin_frame(ch, i, f) for i in ears}
        row_h = {"frame": int(sh.frames[f]), "worst_mm": 0.0, "n": 0, "by_part": {}}
        row_e = {"frame": int(sh.frames[f]), "worst_mm": 0.0, "n": 0, "by_part": {}}
        ear_tree = {i: bvh(Er[i], T[i]) for i in ears}
        ear_box = {i: (Er[i].min(0) - 0.01, Er[i].max(0) + 0.01) for i in ears}
        for hi in hair:
            Ph = None
            # hand vertices inside hair
            for i in hands:
                Q = Hd[i][hand_sel[i]]
                if Ph is None:
                    Ph = skin_frame(ch, hi, f)
                lo, hi_ = Ph.min(0) - 0.01, Ph.max(0) + 0.01
                near = np.all((Q >= lo) & (Q <= hi_), axis=1)
                if not near.any():
                    continue
                tree = bvh(Ph, T[hi])
                d = depth_inside(tree, Q[near])
                ins = d < -0.001
                if ins.any():
                    key = f"{parts[i]}>{parts[hi]}"
                    row_h["by_part"][key] = [round(float(-d.min()) * 1000, 1), int(ins.sum())]
                    row_h["worst_mm"] = max(row_h["worst_mm"], float(-d.min()) * 1000)
                    row_h["n"] += int(ins.sum())
            # hair vertices inside the ear
            if Ph is None:
                Ph = skin_frame(ch, hi, f)
            for i in ears:
                lo, hi_ = ear_box[i]
                near = np.all((Ph >= lo) & (Ph <= hi_), axis=1)
                if not near.any():
                    continue
                idx = np.nonzero(near)[0][::2]
                d = depth_inside(ear_tree[i], Ph[idx])
                ins = d < -0.001
                if ins.any():
                    key = f"{parts[hi]}>{parts[i]}"
                    row_e["by_part"][key] = [round(float(-d.min()) * 1000, 1), int(ins.sum()) * 2]
                    row_e["worst_mm"] = max(row_e["worst_mm"], float(-d.min()) * 1000)
                    row_e["n"] += int(ins.sum()) * 2
        res["hand_hair"].append(row_h)
        res["hair_ear"].append(row_e)
        print(f"f{row_h['frame']:4d} hand>hair {row_h['worst_mm']:5.1f} mm n={row_h['n']:4d} {row_h['by_part']} | hair>ear {row_e['worst_mm']:5.1f} mm n={row_e['n']} "
              f"{ {k: v for k, v in row_e['by_part'].items()} }", flush=True)
    out = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--out=")), None)
    if out:
        json.dump(res, open(out, "w"))


if __name__ == "__main__":
    main()
