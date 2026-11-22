"""T-183 round 3: frames where the body animation itself jumps (before secondary motion would matter).

    python3 snaps.py <bake.json> [--deg=45] [--mm=100] [--bones=head,chest,upperArm.L,...] [--json]

Per character, the frames f at which one of the listed bones turns more than --deg degrees or its pivot travels more
than --mm millimetres from frame f-1 to f (one frame = 1/24 s: 45 degrees per frame is 1080 degrees per second, 100 mm
per frame is 2.4 m/s; a quick hand gesture of e909, hand to the temple, reaches 41 degrees / 68 mm). The bones are body bones (not chain bones), so the numbers are those of the source animation.
snap_frames(bake) -> {character: {frame: [(bone, degrees, mm), ...]}} for the other tools (r5_table.py)."""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "..", "tools", "motion_checks"))
import shot as S  # noqa: E402

BONES = ["head", "chest", "upperArm.L", "upperArm.R", "forearm.L", "forearm.R", "hand.L", "hand.R"]


def snap_frames(bake, deg=45.0, mm=100.0, bones=BONES):
    sh = S.Shot(bake) if isinstance(bake, str) else bake
    out = {}
    for c in sh.characters:
        idx = {b: i for i, b in enumerate(c.bones)}
        piv = c.pivots()
        rows = {}
        for bn in bones:
            if bn not in idx:
                continue
            R = c.M[:, idx[bn], :3, :3]
            tr = np.einsum("fji,fjk->fik", R[:-1], R[1:]).trace(axis1=1, axis2=2)
            ang = np.degrees(np.arccos(np.clip((tr - 1) / 2, -1, 1)))
            d = np.linalg.norm(np.diff(piv[:, idx[bn]], axis=0), axis=1) * 1000
            for i in np.nonzero((ang > deg) | (d > mm))[0]:
                rows.setdefault(int(sh.frames[i + 1]), []).append((bn, round(float(ang[i])), round(float(d[i]))))
        out[c.name] = rows
    return out


if __name__ == "__main__":
    o = {a.split("=", 1)[0][2:]: a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--") and "=" in a}
    res = snap_frames([a for a in sys.argv[1:] if not a.startswith("--")][0], float(o.get("deg", 45)), float(o.get("mm", 100)),
                      o["bones"].split(",") if "bones" in o else BONES)
    if "--json" in sys.argv:
        print(json.dumps({c: {str(f): r for f, r in rows.items()} for c, rows in res.items()}))
    else:
        for c, rows in res.items():
            print(c, "-" if not rows else "")
            for f in sorted(rows):
                print(f"  f{f}: " + ", ".join(f"{b} {a} deg / {d} mm" for b, a, d in rows[f]))
