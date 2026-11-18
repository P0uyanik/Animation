"""T-095 evidence: head-to-head clearance and cup-hold drift of an exchange shot, from its engine bake (python3, numpy).

    python3 docs/evaluation/animation/T-095/measure_t095.py --bake <shot>/build/bake.json --scene <shot>/shot.scene.json \
        [--json out.json]

Head clearance: every package vertex above the neck bone (head, face, hair, glasses, buns; skinned with the bake's
skinning matrices, every 8th vertex) of one character against the other's, per frame: the smallest distance (metres;
values >= 0.12 mean nothing is closer than 12 cm). Also the head-bone pivot distance.
Cup-hold drift: on the shared-cup interval (the receiver's contact .. the giver's release, from the shot's handover
action), the cup's origin expressed in each holding hand's bone frame, relative to that frame at the receiver's
contact: the largest displacement (mm) and rotation (deg). A rigidly held cup drifts 0. Also over each hand's own
holding span (grasp contact .. release / shot end). Not part of the build or the gate."""
import argparse
import json
import math

import numpy as np


def mat(m):
    return np.array(m, dtype=np.float64).reshape(4, 4).T  # column-major 16 floats -> 4x4


class Char:
    def __init__(self, entry):
        self.name = entry["name"]
        self.bones = entry["bones"]
        pkg = entry["package"]
        doc = json.load(open(pkg))
        geo = open(pkg.replace("character.json", "geometry.bin"), "rb").read()
        sk = {b["name"]: b for b in doc["skeleton"]}
        self.index = {n: i for i, n in enumerate(self.bones)}
        self.heads = {n: np.array(sk[n]["head"]) for n in self.bones if n in sk}
        neck_y = sk["neck"]["head"][1]
        pos, jnt, wgt = [], [], []
        for m in doc["meshes"]:
            p = np.frombuffer(geo, np.float32, m["positions"]["count"], m["positions"]["offset"]).reshape(-1, 3)
            j = np.frombuffer(geo, np.uint16, m["joints"]["count"], m["joints"]["offset"]).reshape(-1, 4)
            w = np.frombuffer(geo, np.float32, m["weights"]["count"], m["weights"]["offset"]).reshape(-1, 4)
            keep = np.nonzero(p[:, 1] > neck_y)[0][::8]
            pos.append(p[keep]), jnt.append(j[keep]), wgt.append(w[keep])
        self.pos = np.concatenate(pos).astype(np.float64)
        self.jnt = np.concatenate(jnt).astype(np.int64)
        self.wgt = np.concatenate(wgt).astype(np.float64)

    def skin(self, fd):
        S = np.array(fd["characters"][self.name]["skin"], dtype=np.float64).reshape(-1, 4, 4).transpose(0, 2, 1)
        h = np.concatenate([self.pos, np.ones((len(self.pos), 1))], 1)
        out = np.zeros((len(self.pos), 3))
        for k in range(4):
            out += self.wgt[:, k:k + 1] * np.einsum("nij,nj->ni", S[self.jnt[:, k]], h)[:, :3]
        return out

    def bone(self, fd, name):
        """World frame of a bone (skin matrix * translate(head))."""
        i = self.index[name]
        S = mat(fd["characters"][self.name]["skin"][16 * i:16 * i + 16])
        T = np.eye(4)
        T[:3, 3] = self.heads[name]
        return S @ T


def min_dist(a, b, chunk=1024, reach=0.12):
    """Smallest distance between two point sets; only points within `reach` of the other set's bounding box count
    (returns >= reach when nothing is that close)."""
    def near(p, q):
        lo, hi = q.min(0) - reach, q.max(0) + reach
        return p[np.all((p >= lo) & (p <= hi), axis=1)]
    a, b = near(a, b), near(b, a)
    if len(a) == 0 or len(b) == 0:
        return reach
    best = math.inf
    for i in range(0, len(a), chunk):
        d = ((a[i:i + chunk, None, :] - b[None, :, :]) ** 2).sum(-1)
        best = min(best, float(d.min()))
    return math.sqrt(best)


def rot_deg(R):
    return math.degrees(math.acos(max(-1.0, min(1.0, (np.trace(R) - 1) / 2))))


def drift(frames, ch, hand, f0, f1):
    """Cup origin in the hand bone's frame, relative to frame f0: largest displacement (mm) and rotation (deg)."""
    def rel(f):
        H = ch.bone(frames[f], hand)
        H[:3, :3] /= np.linalg.norm(H[:3, :3], axis=0)  # pivots carry no scale; normalise anyway
        return np.linalg.inv(H) @ mat(frames[f]["props"]["cup"])
    r0 = rel(f0)
    dmm = max(1000 * float(np.linalg.norm(rel(f)[:3, 3] - r0[:3, 3])) for f in range(f0, f1 + 1))
    ddeg = max(rot_deg(r0[:3, :3].T @ rel(f)[:3, :3]) for f in range(f0, f1 + 1))
    return {"frames": [f0, f1], "max_mm": round(dmm, 4), "max_deg": round(ddeg, 4)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bake", required=True)
    ap.add_argument("--scene", required=True)
    ap.add_argument("--json")
    a = ap.parse_args()
    bake = json.load(open(a.bake))
    scene = json.load(open(a.scene))
    frames = {fd["frame"]: fd for fd in bake["frame_data"]}
    chars = {c["name"]: Char(c) for c in bake["characters"]}
    names = list(chars)
    A, B = chars[names[0]], chars[names[1]]
    heads = []
    for f in sorted(frames):
        fd = frames[f]
        pa, pb = A.bone(fd, "head")[:3, 3], B.bone(fd, "head")[:3, 3]
        heads.append({"frame": f, "surface_m": round(min_dist(A.skin(fd), B.skin(fd)), 4),
                      "pivot_m": round(float(np.linalg.norm(pa - pb)), 4)})
    closest = min(heads, key=lambda h: h["surface_m"])
    ho = next(x for x in scene["actions"] if x["type"] == "handover")
    grasp = next(x for x in scene["actions"] if x["type"] in ("grasp", "reach") and x.get("prop") == "cup")
    giver, receiver = chars[ho["character"]], chars[ho["to"]]
    ghand, rhand = "hand." + ho.get("hand", "R"), "hand." + ho.get("toHand", "R")
    c0, c1 = int(ho["contact"]), int(ho["release"])
    last = max(frames)
    shared = {"interval": [c0, c1], "giver": drift(frames, giver, ghand, c0, c1),
              "receiver": drift(frames, receiver, rhand, c0, c1)}
    spans = {"giver_hold": drift(frames, giver, ghand, int(grasp["contact"]), c1),
             "receiver_hold": drift(frames, receiver, rhand, c0, last)}
    shared_heads = [h for h in heads if c0 <= h["frame"] <= c1]
    out = {"bake": a.bake, "head_clearance": {"closest": closest,
                                               "shared_cup_min_surface_m": min(h["surface_m"] for h in shared_heads),
                                               "shared_cup_min_pivot_m": min(h["pivot_m"] for h in shared_heads),
                                               "per_frame": heads},
           "cup_hold_drift_shared": shared, "cup_hold_drift_spans": spans}
    text = json.dumps(out, indent=1)
    if a.json:
        open(a.json, "w").write(text + "\n")
    print(json.dumps({k: v for k, v in out["head_clearance"].items() if k != "per_frame"}))
    print(json.dumps(shared))
    print(json.dumps(spans))


if __name__ == "__main__":
    main()
