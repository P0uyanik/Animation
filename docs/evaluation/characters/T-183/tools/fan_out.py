"""T-183 round 2: how wide and how untidy the hair is while she leans (numbers beside the close-up frames).

    python3 fan_out.py <label>=<bake.json> [<label>=<bake.json> ...] [--frames=24-132] [--step=4] [--chains=ringlets*]
                       [--out=<json>]

Per bake, over the frames (shot frame numbers), for the girl:
  area back / side   the hair's silhouette seen straight from behind and from her right side (the directions of the
                     close-up views `back` and `side` of closeup.py, parallel projection, 3 mm cells), cm2
  out back / side    the part of it that is not in front of or behind the figure (hair beyond the body's outline), cm2
  crossings          pairs of lock chains whose centre lines cross in the back view (the rest pose is listed first)
  kink               the sharpest bend between two neighbouring segments of a lock chain, degrees more than at rest
  tips               mean distance of the lock chains' tips from where they are in the first bake given (mm)
The first bake is the reference for `tips` (give the released bake first)."""
import fnmatch
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "..", "..", "tools", "motion_checks"))
import shot as S  # noqa: E402
from closeup import VIEWS  # noqa: E402

CELL = 0.003


def opt(name, default=None):
    return next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith(f"--{name}=")), default)


def basis(view):
    pos, target, _ = VIEWS[view]
    d = np.array(target, float) - np.array(pos, float)
    d[1] = 0.0  # level: the silhouette's height stays the height
    d /= np.linalg.norm(d)
    u = np.cross([0.0, 1.0, 0.0], d)
    return np.stack([u / np.linalg.norm(u), [0.0, 1.0, 0.0]])  # (2, 3): right, up


def cells(P, B):
    """The cells a point set covers in a view, as sorted int64 keys, with one cell of spread (the vertices of a lock
    are 2-4 mm apart)."""
    q = np.floor(P @ B.T / CELL).astype(np.int64) + 50000
    k = np.unique(q[:, 0] * 100000 + q[:, 1])
    return np.unique(np.concatenate([k + dx * 100000 + dy for dx in (-1, 0, 1) for dy in (-1, 0, 1)]))


def tri_points(P, T, n=3):
    a, b, c = P[T[:, 0]], P[T[:, 1]], P[T[:, 2]]
    pts = [P]
    for i in range(n + 1):
        for j in range(n + 1 - i):
            pts.append(a + (b - a) * (i / n) + (c - a) * (j / n))
    return np.concatenate(pts)


def skinner(ch, mi):
    P, _, J, Wt = ch.rest(mi)
    J = ch._joint_map()[J]

    def at(M):
        if M is None:
            return P
        A = np.einsum("nk,nkij->nij", Wt, M[J])
        return np.einsum("nij,nj->ni", A[:, :3, :3], P) + A[:, :3, 3]
    return at


def crossing(a, b):
    """True when two 2D polylines cross."""
    def ccw(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    for i in range(len(a) - 1):
        for j in range(len(b) - 1):
            p, q, r, s = a[i], a[i + 1], b[j], b[j + 1]
            if ccw(p, q, r) * ccw(p, q, s) < 0 and ccw(r, s, p) * ccw(r, s, q) < 0:
                return True
    return False


def bends(X):
    """Angles (degrees) between neighbouring segments of a polyline (K, 3)."""
    d = np.diff(X, axis=0)
    d /= np.maximum(np.linalg.norm(d, axis=1, keepdims=True), 1e-12)
    return np.degrees(np.arccos(np.clip((d[:-1] * d[1:]).sum(1), -1, 1)))


def measure(path, frames, pattern):
    sh = S.Shot(path)
    ch = next(c for c in sh.characters if c.name == "girl")
    parts = [m["part"] for m in ch.doc["meshes"]]
    hair = [i for i, p in enumerate(parts) if p.startswith("hair_")]
    skip = ["eye*", "brow*", "lash*", "lid*", "mouth*", "glasses*"]
    solid = [i for i, p in enumerate(parts) if not p.startswith("hair_") and not any(fnmatch.fnmatchcase(p, s) for s in skip)]
    sk = {i: skinner(ch, i) for i in hair + solid}
    tris = {i: ch.array(ch.doc["meshes"][i]["indices"], 3).astype(np.int64) for i in solid}
    idx = {b: i for i, b in enumerate(ch.bones)}
    hd = {b["name"]: np.array(b["head"]) for b in ch.doc["skeleton"]}
    chains = [c for c in ch.doc["dynamics"]["chains"] if fnmatch.fnmatchcase(c["name"], pattern)]
    pts = [[(idx[b], hd[b]) for b in c["bones"]] + [(idx[c["bones"][-1]], np.array(c["tip"]))] for c in chains]

    def joints(M):
        if M is None:
            return [np.stack([p for _, p in c]) for c in pts]
        return [np.stack([M[b][:3, :3] @ p + M[b][:3, 3] for b, p in c]) for c in pts]

    views = {v: basis(v) for v in ("back", "side")}
    rest = joints(None)
    rest_bend = [bends(X) for X in rest]

    def ncross(J):
        B = views["back"]
        L = [X @ B.T for X in J]
        return sum(crossing(L[i], L[j]) for i in range(len(L)) for j in range(i + 1, len(L)))

    rows = []
    fno = {int(f): k for k, f in enumerate(sh.frames)}
    for f in frames:
        M = ch.M[fno[f]]
        H = np.concatenate([sk[i](M) for i in hair])
        Fg = np.concatenate([tri_points(sk[i](M), tris[i]) for i in solid])
        J = joints(M)
        row = {"frame": f, "tips": np.stack([X[-1] for X in J]).tolist(), "crossings": ncross(J),
               "kink": max(float((bends(X) - r).max()) for X, r in zip(J, rest_bend) if len(r))}
        for v, B in views.items():
            hc = cells(H, B)
            row[f"area_{v}"] = len(hc) * CELL * CELL * 1e4
            row[f"out_{v}"] = len(np.setdiff1d(hc, cells(Fg, B), assume_unique=True)) * CELL * CELL * 1e4
        rows.append(row)
    return {"chains": len(chains), "rest_crossings": ncross(rest), "rows": rows}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    a, b = (int(x) for x in opt("frames", "24-132").split("-"))
    frames = list(range(a, b + 1, int(opt("step", "4"))))
    res, ref = {}, None
    for arg in args:
        label, path = arg.split("=", 1)
        r = measure(path, frames, opt("chains", "ringlets*"))
        if ref is None:
            ref = [np.array(x["tips"]) for x in r["rows"]]
        for x, t in zip(r["rows"], ref):
            tips = np.array(x.pop("tips"))
            x["tips_mm"] = float(np.linalg.norm(tips - t, axis=1).mean() * 1000) if tips.shape == t.shape else -1.0
        res[label] = r
        R = r["rows"]
        mean = {k: float(np.mean([x[k] for x in R])) for k in R[0] if k != "frame"}
        peak = {k: float(np.max([x[k] for x in R])) for k in R[0] if k != "frame"}
        r["mean"], r["max"] = mean, peak
        print(f"{label}: {r['chains']} chains, {r['rest_crossings']} crossings at rest, frames {a}-{b} step {frames[1] - frames[0] if len(frames) > 1 else 1}")
        print("  frame  area back  out back  area side  out side  crossings  kink deg  tips mm")
        for x in R + [dict(mean, frame="mean"), dict(peak, frame="max")]:
            print(f"  {str(x['frame']):>5s}  {x['area_back']:9.0f}  {x['out_back']:8.0f}  {x['area_side']:9.0f}  {x['out_side']:8.0f}"
                  f"  {x['crossings']:9.1f}  {x['kink']:8.1f}  {x['tips_mm']:7.1f}")
    if opt("out"):
        json.dump(res, open(opt("out"), "w"), indent=1)


if __name__ == "__main__":
    main()
