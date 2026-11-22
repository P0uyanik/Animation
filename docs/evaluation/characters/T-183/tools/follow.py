"""T-183 measurement: hair follow. Tip of every hair chain in a bake against the same shot baked with the character's
dynamics off (scene character "dynamics": false = the body-anchored pose): distance in mm (max, rms), relative speed.

    python3 follow.py <bake.json> <dynamics-off bake.json> [character name]"""
import json
import os
import sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "..", "tools", "motion_checks"))
import shot as S
dyn, sta = S.Shot(sys.argv[1]), S.Shot(sys.argv[2])
name = sys.argv[3] if len(sys.argv) > 3 else "girl"
cd = next(c for c in dyn.characters if c.name == name); cs = next(c for c in sta.characters if c.name == name)
idx = {b: i for i, b in enumerate(cd.bones)}
fps = dyn.fps
def carried(c, bone, p):
    M = c.M[:, idx[bone]]
    return np.einsum("fij,j->fi", M[:, :3, :3], p) + M[:, :3, 3]
head_rest = {b["name"]: np.array(b["head"]) for b in cd.doc["skeleton"]}
hp = carried(cs, "head", head_rest["head"]) 
hv = np.linalg.norm(np.diff(hp, axis=0), axis=1) * 1000 * fps  # mm/s
import signal; signal.signal(signal.SIGPIPE, signal.SIG_DFL)
print(f"head pivot speed mm/s: max {hv.max():.0f} mean {hv.mean():.0f}")
rows = {}
for ch in cd.doc["dynamics"]["chains"]:
    tip = np.array(ch["tip"]); last = ch["bones"][-1]
    td, ts = carried(cd, last, tip), carried(cs, last, tip)
    d = (td - ts) * 1000
    dn = np.linalg.norm(d, axis=1)
    vt = np.linalg.norm(np.diff(ts, axis=0), axis=1) * 1000 * fps   # target tip speed
    vr = np.linalg.norm(np.diff(d, axis=0), axis=1) * fps            # relative speed mm/s
    quiet = vt < 20
    # oscillation: sign changes of the relative velocity along the principal axis of d
    u, s_, vT = np.linalg.svd(d - d.mean(0), full_matrices=False)
    x = (d - d.mean(0)) @ vT[0]
    zc = int(np.sum(np.diff(np.sign(np.diff(x))) != 0))
    rows.setdefault(ch["group"], []).append((dn.max(), np.sqrt((dn**2).mean()), vr.max(), vr[quiet].mean() if quiet.any() else 0, vt.max(), zc, quiet.mean()))
import signal; signal.signal(signal.SIGPIPE, signal.SIG_DFL)
print("group                n  maxDisp rmsDisp  maxRelSpd  relSpdQuiet  maxTargetSpd  reversals quietShare")
for g, r in rows.items():
    a = np.array(r)
    print(f"{g:20s} {len(r):2d} {a[:,0].max():7.1f} {a[:,1].mean():7.1f} {a[:,2].max():9.0f} {a[:,3].mean():11.1f} {a[:,4].max():12.0f} {a[:,5].mean():9.1f} {a[:,6].mean():8.2f}")
