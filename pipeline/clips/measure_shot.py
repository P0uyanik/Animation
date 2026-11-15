"""Shot checks from an engine bake (T-010): eye angles relative to the head (T-006 gaze limits) and pop detection
with the T-002 smoothness limits (reuses measure_clips.Baked / per_frame_change). No character-specific code.

    python3 pipeline/clips/measure_shot.py --scene <shot build>/shot.resolved.scene.json --bake <run>/bake.json \
        --out <dir> [--engine build/apps/render-cli/plush-render]

Gaze: per frame, character and eye bone ("eye.*"), the eye's rest +Z axis expressed in the head bone's frame
(R_head^T * R_eye * +Z, from the baked skinning matrices; rest frames are axis aligned), as yaw (+ = character
left) and pitch (+ = up) in degrees, plus the angle to the camera. The maxima are compared with the limits the engine
uses: the scene's life.gaze override, else the GazeLimits defaults parsed from engine/anim/animation.h.

Smoothness (T-002 C4 rule): inside blend / emotion-ramp boundary windows the per-frame rotation change of every limb
role is <= min(12 deg, 1.25 x the largest interior per-frame maximum of the sources active at that frame); at every
other frame it is <= 1.25 x that maximum (no pop beyond what the sources do on their own). A source's interior maximum is measured on a bake of
the shot with only that source (plus the base clips and look actions, which are under everything); keyed tracks
("animation") are one source. Frames where no non-base source is active use the base-only bake as the source."""
import argparse
import copy
import json
import math
import os
import re
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
import measure_clips as MC  # noqa: E402
import retarget as RT  # noqa: E402


def gaze_defaults():
    src = open(os.path.join(ROOT, "engine", "anim", "animation.h")).read()
    body = re.search(r"struct GazeLimits \{(.*?)\};", src, re.S).group(1)
    return {k: float(v) for k, v in re.findall(r"float (\w+) = ([0-9.]+)f;", body)}


def mat3(s, b):
    return [[s[16 * b + c * 4 + r] for c in range(3)] for r in range(3)]


def mul_t(a, v):  # a^T v
    return [sum(a[r][c] * v[r] for r in range(3)) for c in range(3)]


def mul(a, v):
    return [sum(a[r][c] * v[c] for c in range(3)) for r in range(3)]


def gaze(scene, bake):
    lim0 = gaze_defaults()
    chars = {c["name"]: c for c in scene["characters"]}
    out = {"limits_source": "engine/anim/animation.h GazeLimits (scene life.gaze overrides applied)", "characters": {}}
    for ch in bake["characters"]:
        name = ch["name"]
        lim = dict(lim0, **((chars[name].get("life") or {}).get("gaze") or {}))
        idx = {n: i for i, n in enumerate(ch["bones"])}
        eyes = sorted(n for n in ch["bones"] if n.startswith("eye."))
        head = idx["head"]
        rows, mx = [], {e: {"up": 0.0, "down": 0.0, "left": 0.0, "right": 0.0} for e in eyes}
        for fd in bake["frame_data"]:
            s = fd["characters"][name]["skin"]
            H = mat3(s, head)
            row = {"frame": fd["frame"]}
            hf = mul(H, [0, 0, 1])
            row["head_pitch_world_deg"] = math.degrees(math.atan2(hf[1], math.hypot(hf[0], hf[2])))
            for e in eyes:
                b = idx[e]
                E = mat3(s, b)
                d = mul_t(H, mul(E, [0, 0, 1]))
                yaw = math.degrees(math.atan2(d[0], d[2]))
                pitch = math.degrees(math.atan2(d[1], math.hypot(d[0], d[2])))
                # eye pivot in world: skin * head position (skin = world * global * translate(-head))
                wdir = mul(E, [0, 0, 1])
                row[e] = {"yaw_deg": round(yaw, 4), "pitch_deg": round(pitch, 4)}
                m = mx[e]
                m["up"], m["down"] = max(m["up"], pitch), max(m["down"], -pitch)
                m["left"], m["right"] = max(m["left"], yaw), max(m["right"], -yaw)
                row[e]["_wdir"] = wdir
            rows.append(row)
        out["characters"][name] = {"limits_deg": lim, "eyes": eyes, "max_deg": mx, "frames": rows}
        out["characters"][name]["within_limits"] = all(
            mx[e]["up"] <= lim["maxUpDeg"] + 1e-3 and mx[e]["down"] <= lim["maxDownDeg"] + 1e-3
            and mx[e]["left"] <= lim["maxLeftDeg"] + 1e-3 and mx[e]["right"] <= lim["maxRightDeg"] + 1e-3 for e in eyes)
    return out


def add_camera_error(g, bake, pkgs):
    """Angle between each eye's axis and the direction from its pivot to the camera (limit engaged when > 0)."""
    for ch in bake["characters"]:
        name = ch["name"]
        man = json.load(open(pkgs[name]))
        heads = {b["name"]: b["head"] for b in man["skeleton"]}
        idx = {n: i for i, n in enumerate(ch["bones"])}
        G = g["characters"][name]
        worst = 0.0
        for fd, row in zip(bake["frame_data"], G["frames"]):
            s = fd["characters"][name]["skin"]
            cam = fd["camera"]["position"]
            for e in G["eyes"]:
                b = idx[e]
                m = mat3(s, b)
                piv = [sum(m[r][c] * heads[e][c] for c in range(3)) + s[16 * b + 12 + r] for r in range(3)]
                to = RT.normalize([cam[i] - piv[i] for i in range(3)])
                wd = row[e].pop("_wdir")
                a = math.degrees(math.acos(max(-1.0, min(1.0, RT.dot(RT.normalize(wd), to)))))
                row[e]["off_camera_deg"] = round(a, 4)
                worst = max(worst, a)
        G["max_off_camera_deg"] = worst


def variant(scene, keep, keys):
    v = copy.deepcopy(scene)
    v["actions"] = [a for i, a in enumerate(scene["actions"]) if a.get("base") or a["type"] == "look" or i in keep]
    if not keys:
        v.pop("animation", None)
    return v


def merge(a, b):
    if not isinstance(b, dict):
        return b
    out = dict(a) if isinstance(a, dict) else {}
    for k, v in b.items():
        if v is None:
            out.pop(k, None)
        else:
            out[k] = merge(out.get(k), v)
    return out


def ramps(a, fps):
    """(start, end, ramp-in frames, ramp-out frames) of a clip or emotion action, in scene frames."""
    start = float(a.get("start", 1))
    if a["type"] == "clip":
        c = json.load(open(os.path.join(ROOT, "content", "clips", a["clip"] + ".clip.json")))
        end = float(a.get("end", start + c["frame_count"] / c["fps"] * fps / float(a.get("speed", 1.0))))
        return start, end, float(a.get("blendIn", 0)), float(a.get("blendOut", 0))
    name, _, var = a["name"].partition("/")
    e = json.load(open(os.path.join(ROOT, "content", "emotions", name + ".emotion.json")))
    if var:
        e = merge(e, e["variants"][var])
    t = e["timing"]
    end = float(a.get("end", start + (t["onset"] + t["hold"] + t["release"]) * fps))
    # crossfades can stretch an emotion's ramps by the neighbour's ramp: the windows take onset + release both ways
    w = (t["onset"] + t["release"]) * fps
    return start, end, w, w


def smoothness(scene_path, bake_path, out, engine, pkgs):
    scene = json.load(open(scene_path))
    f_end = scene["frameEnd"]
    fps = scene["frameRate"][0] / scene["frameRate"][1]
    sd = tempfile.mkdtemp(prefix="measure_shot_")  # variant bakes are scratch data
    base_dir = os.path.dirname(os.path.abspath(scene_path))

    def run(name, sc):
        p = os.path.join(base_dir, f"_measure_{name}.scene.json")  # next to the shot: clips/emotions resolve upward
        json.dump(sc, open(p, "w"), indent=1)
        try:
            return MC.Baked(MC.bake(engine, p, os.path.join(sd, f"{name}.bake.json")), pkgs).data
        finally:
            os.remove(p)

    shot = MC.Baked(json.load(open(bake_path)), pkgs).data
    roles = MC.LIMB_ROLES
    res = {"limits": {"boundary_factor": 1.25, "max_deg_per_frame": 12.0}, "sources": {}, "characters": {}}
    srcs = {"base": (variant(scene, set(), False), None)}
    windows = []  # (character, first frame, last frame): blend / emotion ramp boundaries (12 deg cap applies)
    for i, a in enumerate(scene["actions"]):
        if a.get("base") or a["type"] == "look":
            continue
        srcs[f"{i}_{a['type']}_{a.get('clip') or a.get('name')}".replace("/", "-")] = (variant(scene, {i}, False), (a["character"], *ramps(a, fps)[:2]))
        st, en, ri, ro = ramps(a, fps)
        windows.append((a["character"], st - 1, st + ri + 1))
        if en <= f_end:
            windows.append((a["character"], en - ro - 1, en + 1))
    if scene.get("animation"):
        for track, keys in scene["animation"].items():
            who = track.split("/")[0]
            srcs[f"keys_{track.replace('/', '-')}"] = (variant(scene, set(), True), (who, float(keys[0][0]), float(keys[-1][0])))
    interior = {}
    for name, (sc, sp) in srcs.items():
        data = run(name, sc)
        interior[name] = {}
        for who, per in data.items():
            frames = sorted(per)
            if sp is not None and sp[0] != who:
                continue
            fr = [f for f in frames if sp is None or sp[1] - 1 <= f <= sp[2] + 1]
            chg, _ = MC.per_frame_change(per, roles, fr)
            interior[name][who] = {r: max(v.values(), default=0.0) for r, v in chg.items()}
        res["sources"][name] = {"character_span": sp, "interior_max_deg": interior[name]}
    ok_all = True
    for who, per in shot.items():
        frames = sorted(per)
        chg, _ = MC.per_frame_change(per, roles, frames)
        worst = {"ratio": 0.0}
        overall = 0.0
        fails = []
        for f in frames[1:]:
            active = [n for n, (_, sp) in srcs.items() if sp is not None and sp[0] == who and sp[1] - 1 <= f <= sp[2] + 1]
            in_window = any(w[0] == who and w[1] <= f <= w[2] for w in windows)
            for r in roles:
                v = chg[r].get(f, 0.0)
                overall = max(overall, v)
                lim = 1.25 * max([interior["base"][who].get(r, 0.0)] + [interior[n][who].get(r, 0.0) for n in active])
                if in_window:
                    lim = min(12.0, lim)
                ratio = v / lim if lim > 1e-9 else (0.0 if v < 1e-4 else float("inf"))
                if ratio > worst["ratio"]:
                    worst = {"ratio": ratio, "frame": f, "role": r, "change_deg": v, "limit_deg": lim, "boundary_window": in_window,
                             "sources": ["base"] + active}
                if v > lim + 1e-4:
                    fails.append({"frame": f, "role": r, "change_deg": v, "limit_deg": lim, "boundary_window": in_window})
        ok = not fails
        ok_all &= ok
        res["characters"][who] = {"max_deg_per_frame": overall, "worst": worst, "failures": fails, "pass": ok}
    shutil.rmtree(sd, ignore_errors=True)
    res["boundary_windows"] = windows
    res["pass"] = ok_all
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", required=True)
    ap.add_argument("--bake", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--engine", default=os.path.join(ROOT, "build", "apps", "render-cli", "plush-render"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    scene = json.load(open(a.scene))
    bake = json.load(open(a.bake))
    pkgs = {c["name"]: c["package"] for c in bake["characters"]}  # the bake names each package's character.json
    g = gaze(scene, bake)
    add_camera_error(g, bake, pkgs)
    g["pass"] = all(c["within_limits"] for c in g["characters"].values())
    json.dump(g, open(os.path.join(a.out, "gaze_check.json"), "w"), indent=1)
    s = smoothness(a.scene, a.bake, a.out, a.engine, pkgs)
    json.dump(s, open(os.path.join(a.out, "smoothness_check.json"), "w"), indent=1)
    for who, c in g["characters"].items():
        print(f"gaze {who}: limits {c['limits_deg']} max {json.dumps({e: {k: round(v, 2) for k, v in m.items()} for e, m in c['max_deg'].items()})} "
              f"off-camera max {c['max_off_camera_deg']:.2f} -> {'PASS' if c['within_limits'] else 'FAIL'}")
        hp = [r["head_pitch_world_deg"] for r in c["frames"]]
        print(f"     head pitch (world) min {min(hp):.2f} max {max(hp):.2f}")
    for who, c in s["characters"].items():
        print(f"smooth {who}: max {c['max_deg_per_frame']:.2f} deg/frame, worst {json.dumps(c['worst'])} -> {'PASS' if c['pass'] else 'FAIL'}")
    print(json.dumps({"gaze": g["pass"], "smoothness": s["pass"]}))


if __name__ == "__main__":
    main()
