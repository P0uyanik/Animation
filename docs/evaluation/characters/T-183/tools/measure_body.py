"""T-183 round 2 measurement: every hair vertex of a character against its body and garment surfaces, every frame.

Skins the package meshes with a plush.shot_bake/1 (tools/motion_checks/shot.py). The solid figure is every non-hair
mesh of the character (skin, ears, hands, garments; see SKIP). The depth of a hair vertex is its exit distance: how far
it has to move, in the best direction, until nothing of the figure lies beyond it (0 = it can be seen from outside in
that direction). This is the same for closed meshes, cloth shells with a thickness, open or inverted trims, and for
the space between cloth and skin (a vertex that went through the cloth is as deep as the cloth's outer face is far).
Directions: towards / away from the nearest surface point first (exact when that ray leaves the figure), then 26
fixed directions. A vertex counts when it is deeper than --limit-mm (default 1).

Roots: a hair vertex that is inside the figure in the rest pose (the scalp side of the cap, the embedded end of a lock,
the inner half of a felt volume) counts only by what it is deeper than at rest; the rest depths are listed apart.

    python3 measure_body.py <bake.json> [--out=out.json] [--character=girl] [--limit-mm=1] [--frames=A-B] [--step=N]
                            [--jobs=N] [--skip=pattern,pattern] [--rest]

--rest   the package's rest pose only (no root allowance: everything inside is listed).
Needs the bpy module (mathutils)."""
import fnmatch
import json
import multiprocessing
import os
import sys

import bpy  # noqa: F401 (makes mathutils importable)
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "..", "tools", "motion_checks"))
import shot as S  # noqa: E402

# not body or garment surfaces for this measure: face features that lie in the head's surface, glasses
SKIP = ["eye*", "brow*", "lash*", "lid*", "mouth*", "glasses*"]
REACH = 0.05  # m: hair farther than this from every surface is not tested (it is outside, or the rays say so anyway)
CAP = 0.6     # m: a ray that meets nothing within this distance has left the figure
EPS = 2e-5
DIRS = [Vector(d).normalized() for d in
        [(x, y, z) for x in (-1, 0, 1) for y in (-1, 0, 1) for z in (-1, 0, 1) if (x, y, z) != (0, 0, 0)]]


def opt(name, default=None):
    return next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith(f"--{name}=")), default)


def skinner(ch, mi):
    P, _, J, Wt = ch.rest(mi)
    J = ch._joint_map()[J]

    def at(M):  # M: (B, 4, 4) or None (rest)
        if M is None:
            return P
        A = np.einsum("nk,nkij->nij", Wt, M[J])
        return np.einsum("nij,nj->ni", A[:, :3, :3], P) + A[:, :3, 3]
    return at


def exit_along(tree, p, d, best):
    """Distance from p along d to the last surface the ray meets (0 = none), given up once it reaches `best`."""
    t, last = 0.0, 0.0
    while True:
        hit = tree.ray_cast(p + d * (t + EPS), d, CAP - t)
        if hit[0] is None:
            return last
        t += EPS + hit[3]
        last = t
        if last >= best:
            return last


def depth_of(tree, p):
    """(exit distance of point p in metres, index of the nearest face or -1)."""
    loc, nrm, idx, dist = tree.find_nearest(p, REACH)
    if loc is None:
        return 0.0, -1
    off = p - loc
    if dist > 1e-7:
        if off.dot(nrm) >= 0:  # in front of the nearest face: usually outside
            if tree.ray_cast(p, off / dist, CAP)[0] is None:
                return 0.0, idx
        else:  # behind it: the shortest way out is through that face, if nothing lies beyond it
            d = -off / dist
            if tree.ray_cast(loc + d * EPS, d, CAP)[0] is None:
                return dist, idx
    best = CAP
    for d in DIRS:
        best = min(best, exit_along(tree, p, d, best))
        if best <= 0.0:
            return 0.0, idx
    return best, idx


class Figure:
    def __init__(self, ch, skip):
        self.ch = ch
        parts = [m["part"] for m in ch.doc["meshes"]]
        self.parts = parts
        self.hair = [i for i, p in enumerate(parts) if p.startswith("hair_")]
        self.solid = [i for i, p in enumerate(parts) if not p.startswith("hair_") and not any(fnmatch.fnmatchcase(p, s) for s in skip)]
        self.sk = {i: skinner(ch, i) for i in self.hair + self.solid}
        tris, owner, base = [], [], 0
        for i in self.solid:
            T = ch.array(ch.doc["meshes"][i]["indices"], 3).astype(np.int64)
            tris.append(T + base)
            owner.append(np.full(len(T), i))
            base += ch.doc["meshes"][i]["vertices"]
        self.tris = np.concatenate(tris).tolist()
        self.owner = np.concatenate(owner)

    def measure(self, M):
        """{hair mesh index: (depth per vertex in metres, nearest solid mesh index per vertex)} for one pose."""
        P = np.concatenate([self.sk[i](M) for i in self.solid])
        tree = BVHTree.FromPolygons(P.tolist(), self.tris)
        lo, hi = P.min(0) - 0.002, P.max(0) + 0.002
        out = {}
        for h in self.hair:
            Ph = self.sk[h](M)
            depth = np.zeros(len(Ph))
            near = np.full(len(Ph), -1, dtype=np.int64)
            for k in np.nonzero(np.all((Ph >= lo) & (Ph <= hi), axis=1))[0]:
                d, idx = depth_of(tree, Vector(Ph[k]))
                depth[k] = d
                if idx >= 0:
                    near[k] = self.owner[idx]
            out[h] = (depth, near)
        return out


_FIG = _REST = _SHOT = None


def _frame(f):
    fig, limit = _FIG, _REST["limit"]
    res = fig.measure(_SHOT.characters[_REST["ci"]].M[f])
    row = {"frame": int(_SHOT.frames[f]), "worst_mm": 0.0, "n": 0, "by_pair": {}}
    for h, (depth, near) in res.items():
        over = depth - _REST["depth"][h]  # roots count by what they are deeper than at rest
        ins = over > limit
        if not ins.any():
            continue
        for s in np.unique(near[ins]):
            sel = ins & (near == s)
            w = float(over[sel].max()) * 1000
            row["by_pair"][f"{fig.parts[h]}>{fig.parts[s]}"] = [round(w, 1), int(sel.sum())]
            row["worst_mm"] = max(row["worst_mm"], w)
            row["n"] += int(sel.sum())
    return row


def main():
    global _FIG, _REST, _SHOT
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    sh = S.Shot(args[0])
    name = opt("character", "girl")
    ci = next((i for i, c in enumerate(sh.characters) if c.name == name), 0)
    ch = sh.characters[ci]
    limit = float(opt("limit-mm", "1")) / 1000.0
    fig = Figure(ch, SKIP + [p for p in (opt("skip", "") or "").split(",") if p])
    rest = fig.measure(None)
    rest_rows = {}
    for h, (depth, near) in rest.items():
        ins = depth > limit
        for s in np.unique(near[ins]):
            sel = ins & (near == s)
            rest_rows[f"{fig.parts[h]}>{fig.parts[s]}"] = [round(float(depth[sel].max()) * 1000, 1), int(sel.sum())]
    print("rest pose, hair inside the figure (max mm, vertices):")
    for k, v in sorted(rest_rows.items(), key=lambda kv: -kv[1][0]):
        print(f"  {k:48s} {v[0]:5.1f} mm, {v[1]} vertices")
    res = {"bake": args[0], "character": ch.name, "limit_mm": limit * 1000, "metric": "exit distance",
           "hair_vertices": int(sum(len(v[0]) for v in rest.values())), "hair_parts": [fig.parts[i] for i in fig.hair],
           "solid_parts": [fig.parts[i] for i in fig.solid], "rest": rest_rows, "frames": []}
    frames = [] if "--rest" in sys.argv else list(range(0, len(sh.frames), int(opt("step", "1"))))
    if opt("frames"):
        a, b = (int(x) for x in opt("frames").split("-"))
        frames = [f for f in frames if a <= int(sh.frames[f]) <= b]
    _FIG, _SHOT = fig, sh
    _REST = {"limit": limit, "ci": ci, "depth": {h: v[0] for h, v in rest.items()}}
    jobs = int(opt("jobs", str(min(4, os.cpu_count() or 1))))
    if jobs > 1 and len(frames) > 1:
        with multiprocessing.get_context("fork").Pool(jobs) as pool:
            rows = pool.imap(_frame, frames, chunksize=1)
            rows = [(print(f"f{r['frame']:4d} worst {r['worst_mm']:5.1f} mm n={r['n']:5d} "
                           f"{sorted(r['by_pair'].items(), key=lambda kv: -kv[1][0])[:3]}", flush=True), r)[1] for r in rows]
    else:
        rows = []
        for f in frames:
            r = _frame(f)
            print(f"f{r['frame']:4d} worst {r['worst_mm']:5.1f} mm n={r['n']:5d} {sorted(r['by_pair'].items(), key=lambda kv: -kv[1][0])[:3]}", flush=True)
            rows.append(r)
    res["frames"] = rows
    pair = {}
    for r in rows:
        for key, (w, n) in r["by_pair"].items():
            p = pair.setdefault(key, {"max_mm": 0.0, "frames": 0, "worst_frame": 0, "max_vertices": 0})
            p["frames"] += 1
            p["max_vertices"] = max(p["max_vertices"], n)
            if w > p["max_mm"]:
                p["max_mm"], p["worst_frame"] = w, r["frame"]
    res["summary"] = {"frames_measured": len(rows), "frames_deeper_than_limit": sum(1 for r in rows if r["n"]),
                      "max_depth_mm": round(max((r["worst_mm"] for r in rows), default=0.0), 1),
                      "max_vertices": max((r["n"] for r in rows), default=0), "pairs": pair}
    print("summary:", json.dumps({k: v for k, v in res["summary"].items() if k != "pairs"}))
    for k, v in sorted(pair.items(), key=lambda kv: -kv[1]["max_mm"]):
        print(f"  {k:48s} max {v['max_mm']:5.1f} mm (f{v['worst_frame']}), {v['frames']} frames, up to {v['max_vertices']} vertices")
    out = opt("out")
    if out:
        json.dump(res, open(out, "w"))


if __name__ == "__main__":
    main()
