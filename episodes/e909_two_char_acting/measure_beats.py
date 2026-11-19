"""Measures the key beats of an e909 bake (python3; T-114). Used by tests/acting/test_e909_beats.py.

    python3 episodes/e909_two_char_acting/measure_beats.py [--bake <bake.json>] [--json out.json]

From the bake only (the verbs and reactions are expanded inside the engine, so their frames are read back from the
motion):
- holds: per hand (girl L at the cup's grip_b, boy R at grip), the runs of frames in which the hand bone stays fixed in
  the cup's frame (frame-to-frame change < HOLD_MM) while close to its socket (< NEAR_M). Run start = contact, run end =
  release (the last held frame).
- cup: the first frame the cup leaves its table pose, and the first frame it is back on the table (place).
- faces: per character, the frames where the named morphs peak (girl Smile = delight, girl WideOpen = wonder,
  boy EyeWide = interest) and their peak values.
- eyes: per character, the largest eye-bone turn from the head's rest direction, sideways and down (degrees), so the
  look stays inside the spec's gaze range (T-113 open point 3).
"""
import argparse
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
DEFAULT_BAKE = os.path.join(HERE, "shots", "s010", "build", "bake.json")
with open(os.path.join(ROOT, "content", "assets", "felt_cup.asset.json")) as _f:
    CUP = json.load(_f)
SOCKET = {s: CUP["sockets"][s]["translation"] for s in ("grip", "grip_b")}
HANDS = {"girl": ("hand.L", "grip_b"), "boy": ("hand.R", "grip")}
HOLD_MM, NEAR_M, MIN_RUN = 0.5, 0.08, 6
FACES = {"girl": ("Smile", "WideOpen", "SmileOpen"), "boy": ("EyeWide", "BrowDown", "Pout")}


def pivot(m, head):
    return [m[r] * head[0] + m[4 + r] * head[1] + m[8 + r] * head[2] + m[12 + r] for r in range(3)]


def to_local(m, p):
    """World point -> the cup's frame (m column-major, rigid)."""
    d = [p[i] - m[12 + i] for i in range(3)]
    return [sum(m[4 * c + r] * d[r] for r in range(3)) for c in range(3)]


def runs(flags, frames):
    out, s = [], None
    for i, f in enumerate(flags + [False]):
        if f and s is None:
            s = i
        elif not f and s is not None:
            if i - s >= MIN_RUN:
                out.append([frames[s], frames[i - 1]])
            s = None
    return out


def measure(bake_path):
    with open(bake_path) as fh:
        bake = json.load(fh)
    fd = bake["frame_data"]
    frames = [f["frame"] for f in fd]
    chars = {}
    for c in bake["characters"]:
        with open(c["package"]) as fh:
            doc = json.load(fh)
        heads = {b["name"]: b["head"] for b in doc["skeleton"]}
        chars[c["name"]] = (c, doc, {n: i for i, n in enumerate(c["bones"])}, heads)
    res = {"bake": os.path.relpath(bake_path, ROOT), "frames": [frames[0], frames[-1]], "holds": {}, "faces": {},
           "eyes": {}}
    cups = [f["props"]["cup"] for f in fd]
    for who, (bone, sock) in HANDS.items():
        c, doc, idx, heads = chars[who]
        i = idx[bone]
        loc = [to_local(cups[k], pivot(fd[k]["characters"][who]["skin"][16 * i:16 * i + 16], heads[bone]))
               for k in range(len(fd))]
        flags = [False]
        for k in range(1, len(fd)):
            near = math.dist(loc[k], SOCKET[sock]) < NEAR_M
            flags.append(near and math.dist(loc[k], loc[k - 1]) * 1000 < HOLD_MM)
        res["holds"][who] = {"hand": bone, "socket": sock, "runs": runs(flags, frames)}
    t0 = cups[0][12:15]
    moved = [k for k in range(len(fd)) if math.dist(cups[k][12:15], t0) > 0.001]
    res["cup"] = {"table": [round(x, 4) for x in t0], "leaves": frames[moved[0]] if moved else None,
                  "back": next((frames[k] for k in range(moved[-1] + 1, len(fd))), None) if moved else None,
                  "end_offset_mm": round(math.dist(cups[-1][12:15], t0) * 1000, 3)}
    for who, names in FACES.items():
        c, doc, idx, heads = chars[who]
        mn = c["morphs"]
        res["faces"][who] = {}
        for n in names:
            ks = [j for j, m in enumerate(mn) if m == n]
            if not ks:
                res["faces"][who][n] = None
                continue
            series = [max(f["characters"][who]["morphs"][j] for j in ks) for f in fd]
            pk = max(range(len(series)), key=series.__getitem__)
            above = [frames[k] for k, v in enumerate(series) if v > 0.5 * series[pk] > 0]
            res["faces"][who][n] = {"peak": round(series[pk], 3), "peak_frame": frames[pk],
                                    "half_window": [above[0], above[-1]] if above else None}
    for who in ("girl", "boy"):
        c, doc, idx, heads = chars[who]
        bl = [j for j, m in enumerate(c["morphs"]) if m == "Blink"]
        worst = {"all": [0.0, 0.0, None], "blink": [0.0, 0.0, None]}
        for k, f in enumerate(fd):
            sk = f["characters"][who]["skin"]
            h = sk[16 * idx["head"]:16 * idx["head"] + 16]
            for eye in ("eye.L", "eye.R"):
                e = sk[16 * idx[eye]:16 * idx[eye] + 16]
                # rest gaze +Z; the eye's posed +Z expressed in the head's rest frame: R_head^T R_eye e_z
                ez = [e[8], e[9], e[10]]
                v = [sum(h[4 * c_ + r] * ez[r] for r in range(3)) for c_ in range(3)]
                yaw, pitch = abs(math.degrees(math.atan2(v[0], v[2]))), abs(math.degrees(math.asin(max(-1, min(1, v[1])))))
                keys = ["all"] + (["blink"] if bl and f["characters"][who]["morphs"][bl[0]] > 0.5 else [])
                for key in keys:
                    w = worst[key]
                    if yaw > w[0]:
                        w[0], w[2] = yaw, frames[k]
                    w[1] = max(w[1], pitch)
        res["eyes"][who] = {k: {"yaw_deg": round(v[0], 2), "pitch_deg": round(v[1], 2), "yaw_frame": v[2]}
                            for k, v in worst.items()}
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bake", default=DEFAULT_BAKE)
    ap.add_argument("--json", default="")
    a = ap.parse_args()
    res = measure(a.bake)
    txt = json.dumps(res, indent=1)
    if a.json:
        open(a.json, "w").write(txt + "\n")
    print(txt)


if __name__ == "__main__":
    main()
