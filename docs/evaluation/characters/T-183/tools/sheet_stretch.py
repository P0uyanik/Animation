"""T-183: how much a hair part is stretched or sheared in a bake: the length of every mesh edge in each frame against
its rest length (1 = as modelled). A sheet that tears between its chains shows as edges far from 1.

    python3 sheet_stretch.py <bake.json> [--part=hair_curtain] [--character=girl] [--step=N]

Prints per measured frame set: the worst and the 99.9th / 99th percentile ratio (long and short), and the worst frame."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "..", "tools", "motion_checks"))
import shot as S  # noqa: E402


def opt(name, default=None):
    return next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith(f"--{name}=")), default)


def main():
    sh = S.Shot([a for a in sys.argv[1:] if not a.startswith("--")][0])
    ch = next(c for c in sh.characters if c.name == opt("character", "girl"))
    mi = [m["part"] for m in ch.doc["meshes"]].index(opt("part", "hair_curtain"))
    P, _, J, W = ch.rest(mi)
    J = ch._joint_map()[J]
    T = ch.array(ch.doc["meshes"][mi]["indices"], 3).astype(np.int64)
    E = np.unique(np.sort(np.concatenate([T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]]), axis=1), axis=0)
    L0 = np.linalg.norm(P[E[:, 0]] - P[E[:, 1]], axis=1)
    E, L0 = E[L0 > 1e-5], L0[L0 > 1e-5]
    worst = (1.0, 1.0, 0, 0)
    hi99, lo99, hi999 = [], [], []
    for f in range(0, len(sh.frames), int(opt("step", "1"))):
        A = np.einsum("nk,nkij->nij", W, ch.M[f][J])
        Q = np.einsum("nij,nj->ni", A[:, :3, :3], P) + A[:, :3, 3]
        r = np.linalg.norm(Q[E[:, 0]] - Q[E[:, 1]], axis=1) / L0
        hi99.append(np.percentile(r, 99))
        hi999.append(np.percentile(r, 99.9))
        lo99.append(np.percentile(r, 1))
        if r.max() > worst[0]:
            worst = (float(r.max()), worst[1], int(sh.frames[f]), worst[3])
        if r.min() < worst[1]:
            worst = (worst[0], float(r.min()), worst[2], int(sh.frames[f]))
    print(f"{opt('part', 'hair_curtain')}: {len(E)} edges; longest {worst[0]:.2f} x rest (f{worst[2]}), shortest {worst[1]:.2f} x (f{worst[3]}); "
          f"over the frames: 99.9 % of edges under {max(hi999):.2f} x, 99 % under {max(hi99):.2f} x, 1 % under {min(lo99):.2f} x")


if __name__ == "__main__":
    main()
