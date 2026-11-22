"""Which colliders a chain joint touches, per frame (T-183 round 2: tracing tip noise).
usage: near_colliders.py <exp dir with bake.json> <chain name> <joint index | -1 = tip> <A-B frames> [slack mm]
                          [--character=girl]
Prints, per frame, the joint position (mm) and every collider of the package whose surface is nearer to the joint
than the joint's contact radius plus the slack (default 3 mm): name, bone, gap = distance - (collider radius + joint
radius) in mm (negative = the joint is inside the contact distance)."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "..", "tools", "motion_checks"))
import shot as S  # noqa: E402

who = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--character=")), "girl")
sys.argv = [a for a in sys.argv if not a.startswith("--character=")]
out, chain, joint, (fa, fb) = sys.argv[1], sys.argv[2], int(sys.argv[3]), (int(x) for x in sys.argv[4].split("-"))
slack = float(sys.argv[5]) / 1000 if len(sys.argv) > 5 else 0.003
sh = S.Shot(out + "/bake.json")
c = next(c for c in sh.characters if c.name == who)
idx = {b: i for i, b in enumerate(c.bones)}
head = {b["name"]: np.array(b["head"]) for b in c.doc["skeleton"]}
dyn = c.doc["dynamics"]
ch = next(x for x in dyn["chains"] if x["name"] == chain)
pts = [(b, head[b]) for b in ch["bones"]] + [(ch["bones"][-1], np.array(ch["tip"]))]
bone, p = pts[joint]
radii = ch.get("contact", {}).get("radii")
jr = radii[joint] if radii else ch.get("radius", 0.01)


def carried(b, q, f):
    M = c.M[f, idx[b]]
    return M[:3, :3] @ q + M[:3, 3]


for f in range(fa - 1, fb):
    x = carried(bone, p, f)
    rows = []
    for col in dyn["colliders"]:
        a = np.array(col.get("a", col.get("centre")))
        b = np.array(col.get("b", col.get("centre")))
        A, B = carried(col["bone"], a, f), carried(col["bone"], b, f)
        ab = B - A
        l2 = ab @ ab
        t = np.clip(((x - A) @ ab) / l2, 0, 1) if l2 > 1e-12 else 0.0
        gap = np.linalg.norm(x - (A + t * ab)) - col["radius"] - jr
        if gap < slack:
            rows.append((gap, col["name"], col["bone"]))
    rows.sort()
    print(f"f{f + 1:3d} x {x[0] * 1000:7.1f} {x[1] * 1000:7.1f} {x[2] * 1000:7.1f} r {jr * 1000:.1f} | "
          + "; ".join(f"{n} [{b}] {g * 1000:+.1f}" for g, n, b in rows[:8]))
