"""T-187: staging from a bake of shots/measure (the cast seated, no furniture). Writes episodes/e912_paper_boat/staging.json.

    python3 episodes/e912_paper_boat/measure_staging.py <bake.json> [--frame 50]

- sole: the depth of each character's shoe soles under its origin (lowest rest vertex carried by a foot bone or its
  children, the T-175 SOLE rule), for characters whose scene position does not already compensate it (y == 0).
- stools: per character a box under the seated hips (T-175 make_review_shot.py seat_boxes, copied: its top is the 2nd
  percentile height of the vertices the pelvis carries, body and garments; from behind the pelvis to in front of it).
- table: one long table in front of the cast: its top 30 mm above the highest knee point (the knees go under it),
  its near edge 30 mm in front of the most forward chest point, 0.26 m deep, across the cast plus 0.25 m.
- hands: the seated wrist pivots and the shoulder heights (informative, for the touch / pass targets)."""
import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "motion_checks"))
import shot as SHOT  # noqa: E402

def carried_by(ch, bones, rest_only=True):
    """Rest vertices (all meshes) whose strongest joint is one of `bones`: [(mesh index, vertex indices)]."""
    names = [b["name"] for b in ch.doc["skeleton"]]
    ids = [names.index(b) for b in bones if b in names]
    out = []
    for mi in range(len(ch.doc["meshes"])):
        P, N, J, W = ch.rest(mi)
        sel = np.nonzero(np.isin(J[np.arange(len(J)), W.argmax(1)], ids))[0]
        if len(sel):
            out.append((mi, sel))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bake")
    ap.add_argument("--frame", type=int, default=50)
    a = ap.parse_args()
    sh = SHOT.Shot(a.bake)
    i = list(sh.frames).index(a.frame)
    scene = json.load(open(sh.scene_path))
    pos = {c["name"]: c["position"] for c in scene["characters"]}
    st = {"from_bake": os.path.relpath(a.bake, ROOT), "frame": a.frame, "sole": {}, "stools": {}, "hands": {}}
    knee_top, chest_front, xs = [], [], []
    for ch in sh.characters:
        names = [b["name"] for b in ch.doc["skeleton"]]
        # sole depth at rest (character space; the package origin is the character origin)
        feet = [n for n in names if "foot." in n or "toe." in n]
        low = min(float(ch.rest(mi, sel)[0][:, 1].min()) for mi, sel in carried_by(ch, feet))
        st["sole"][ch.name] = round(-low, 4) if abs(pos[ch.name][1]) < 1e-6 else None
        piv = ch.pivots()[i]
        b = ch.bones
        hp = piv[b.index("hips")]
        pts = np.concatenate([ch.skin(mi, sel, with_morphs=False)[0][i] for mi, sel in carried_by(ch, ["hips"])])
        knees = [piv[b.index(f"shin.{s}")] for s in "LR"]
        fwd = (knees[0] + knees[1]) / 2 - hp
        fwd[1] = 0
        fwd /= np.linalg.norm(fwd)
        side = np.array([fwd[2], 0, -fwd[0]])
        half = float(np.abs((pts - hp) @ side).max()) + 0.03
        back = float(((pts - hp) @ fwd).min()) - 0.02
        front = float(((knees[0] + knees[1]) / 2 - hp) @ fwd) - 0.04
        top = float(np.percentile(pts[:, 1], 2))
        c = [hp + fwd * u + side * v for u in (back, front) for v in (-half, half)]
        st["stools"][ch.name] = [[round(min(p[0] for p in c), 4), 0.0, round(min(p[2] for p in c), 4)],
                                 [round(max(p[0] for p in c), 4), round(top, 4), round(max(p[2] for p in c), 4)]]
        legs = np.concatenate([ch.skin(mi, sel, with_morphs=False)[0][i]
                               for mi, sel in carried_by(ch, [n for n in names if "thigh." in n or "shin." in n])])
        knee_top.append(float(np.percentile(legs[:, 1], 99.5)))
        torso = np.concatenate([ch.skin(mi, sel, with_morphs=False)[0][i]
                                for mi, sel in carried_by(ch, [n for n in names if n in ("spine", "chest", "DEF-spine.002")])])
        chest_front.append(float(np.percentile(torso[:, 2], 99)))
        xs.append(float(hp[0]))
        st["hands"][ch.name] = {"wrist_L": [round(float(v), 4) for v in piv[b.index("hand.L")]],
                                "wrist_R": [round(float(v), 4) for v in piv[b.index("hand.R")]],
                                "shoulder_y": round(float(piv[b.index("upperArm.L")][1]), 4),
                                "hips": [round(float(v), 4) for v in hp], "knee_top_y": round(knee_top[-1], 4),
                                "chest_front_z": round(chest_front[-1], 4)}
    z0 = max(chest_front) + 0.03
    st["table"] = {"min": [round(min(xs) - 0.42, 4), 0.0, round(z0, 4)],
                   "max": [round(max(xs) + 0.42, 4), round(max(knee_top) + 0.03, 4), round(z0 + 0.26, 4)]}
    out = os.path.join(HERE, "staging.json")
    json.dump(st, open(out, "w"), indent=1)
    print(json.dumps(st, indent=1))


if __name__ == "__main__":
    main()
