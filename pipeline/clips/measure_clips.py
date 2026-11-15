"""T-002 measurements C2, C3, C4 from engine bakes (python3; runs plush-render --bake).

    python3 pipeline/clips/measure_clips.py --boy <pkg dir> --girl <pkg dir> --mannequin <pkg dir> \
        --blender-poses <measure_blender.json> --out <dir> [--engine build/apps/render-cli/plush-render]

Scenes (generated into <out>/scenes, life layer off so only clip motion is compared):
  clip_<name>: boy, girl and the mannequin side by side (yaw 0), each playing the clip from frame 1 (no blending);
               the loop clip plays two cycles (seam).
  blend_<who>: base idle_relaxed + wave (blend 8/8) + point mirrored to the left arm + a walk with a wave during it
               + sit_down / stand_up; and the same scene without the clip actions (underlying pose).
C2: per role and sampled frame, the world direction (and twist reference) of boy vs girl; limits 2.0 / 5.0 degrees.
C3: engine mannequin vs the Blender mannequin (measure_blender.py), per role; limits 1.0 / 3.0 degrees.
C4: interior per-frame maxima per role (reference values), blend-in/out and layering boundaries (<= 1.25 x the larger
    neighbouring interior maximum and <= 12 deg per frame), root position at boundaries (<= 1.25 x interior max root
    speed), loop seam (<= 1.25 x interior maximum; root continuous), entry/exit frames vs the underlying pose."""
import argparse
import json
import math
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
import retarget as RT  # noqa: E402

LIMB_ROLES = ["upperArm.L", "forearm.L", "upperArm.R", "forearm.R", "thigh.L", "shin.L", "thigh.R", "shin.R",
              "hips", "spine", "chest", "neck", "head"]
TWIST_ROLES = LIMB_ROLES  # every one of these has a twist reference (profile twist hints)
CLIPS = ["idle_relaxed", "wave", "point", "sit_down", "stand_up", "dense_test"]


def ang(a, b):
    return math.degrees(math.atan2(RT.length(RT.cross(a, b)), RT.dot(a, b)))


def scene(chars, actions, frame_end, objects=()):
    return {"format": "plush.scene", "version": 1, "name": "T-002 measurement", "frameRate": [30, 1], "frameStart": 1,
            "frameEnd": frame_end, "render": {"width": 320, "height": 180, "spp": 4, "exposureEV": 0},
            "camera": {"position": [0, 0.8, 3.5], "target": [0, 0.5, 0], "focalMm": 35},
            "materials": [{"name": "m", "type": "standard", "baseColor": [0.5, 0.5, 0.5]}],
            "lights": [{"type": "sky", "color": [1, 1, 1], "intensity": 1}], "objects": list(objects),
            "characters": chars, "actions": actions}


def bake(engine, path, out):
    r = subprocess.run([engine, path, "--bake", out], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"bake failed for {path}:\n{r.stdout[-2000:]}{r.stderr[-2000:]}")
    return json.load(open(out))


class Baked:
    """Per character: role -> per frame (global rotation quaternion, direction, twist) and hips position."""

    def __init__(self, bake, pkgs):
        self.frames = [fd["frame"] for fd in bake["frame_data"]]
        self.data = {}
        for ch in bake["characters"]:
            man = json.load(open(pkgs[ch["name"]]))
            rt = man["retarget"]
            heads = {b["name"]: b["head"] for b in man["skeleton"]}
            idx = {n: i for i, n in enumerate(ch["bones"])}
            per = {}
            for fd in bake["frame_data"]:
                s = fd["characters"][ch["name"]]["skin"]
                roles = {}
                for r, d in rt["roles"].items():
                    b = idx[r]
                    m = [[s[16 * b + c * 4 + rr] for c in range(3)] for rr in range(3)]
                    q = RT.quat_from_matrix(m)
                    h = heads[r]
                    pos = [sum(m[rr][c] * h[c] for c in range(3)) + s[16 * b + 12 + rr] for rr in range(3)]
                    roles[r] = (q, RT.qrot(q, d["dir"]), RT.qrot(q, d["twist"]), pos)
                per[fd["frame"]] = roles
            self.data[ch["name"]] = per


def per_frame_change(per, roles, frames):
    """{role: {frame: angle between frame-1 and frame}} and root (hips position) change."""
    ch = {r: {} for r in roles}
    root = {}
    for f in frames[1:]:
        for r in roles:
            if r in per[f]:
                ch[r][f] = RT.qangle_deg(per[f - 1][r][0], per[f][r][0])
        root[f] = math.dist(per[f - 1]["hips"][3], per[f]["hips"][3])
    return ch, root


def main():
    ap = argparse.ArgumentParser()
    for k in ("boy", "girl", "mannequin"):
        ap.add_argument("--" + k, required=True)
    ap.add_argument("--blender-poses", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--engine", default=os.path.join(ROOT, "build", "apps", "render-cli", "plush-render"))
    a = ap.parse_args()
    out = os.path.abspath(a.out)
    sd = os.path.join(out, "scenes")
    os.makedirs(sd, exist_ok=True)
    pk = {k: os.path.join(os.path.abspath(getattr(a, k)), "character.json") for k in ("boy", "girl", "mannequin")}
    clips = {c: json.load(open(os.path.join(ROOT, "content", "clips", c + ".clip.json"))) for c in CLIPS}
    blender = json.load(open(a.blender_poses))
    res = {"limits": {"C2_dir_deg": 2.0, "C2_twist_deg": 5.0, "C3_dir_deg": 1.0, "C3_twist_deg": 3.0,
                      "C4_boundary_factor": 1.25, "C4_max_deg_per_frame": 12.0},
           "life_layer": "off (clip motion only)", "C2": {}, "C3": {}, "C4": {"interior": {}, "boundaries": [], "seam": {}, "entry_exit": []}}
    interior = {}  # who -> source -> role -> max deg/frame ; root speed
    # ---------------------------------------------------------------- per-clip scenes (C2, C3, interior maxima)
    for c in CLIPS:
        cl = clips[c]
        nframes = int(math.floor((cl["frame_count"] if cl["loop"] else cl["frame_count"] - 1) / cl["fps"] * 30 + 1e-9)) + 1
        if cl["loop"]:
            nframes = 2 * nframes + 1
        masked = [r for r in LIMB_ROLES if r in cl["mask"]]  # roles the clip drives (others keep each character's pose)
        chars = [{"name": n, "asset": os.path.relpath(pk[n], sd), "position": [x, 0, 0], "yawDeg": 0, "life": False}
                 for n, x in (("boy", -0.8), ("girl", 0.0), ("mannequin", 0.8))]
        acts = [{"type": "clip", "character": n, "clip": c, "start": 1, "blendIn": 0, "blendOut": 0} for n in ("boy", "girl", "mannequin")]
        p = os.path.join(sd, f"clip_{c}.scene.json")
        json.dump(scene(chars, acts, nframes), open(p, "w"), indent=1)
        B = Baked(bake(a.engine, p, os.path.join(sd, f"clip_{c}.bake.json")), pk)
        bo, gi, ma = B.data["boy"], B.data["girl"], B.data["mannequin"]
        frames = B.frames
        # C2
        worst = {"dir": 0.0, "twist": 0.0}
        per_role = {}
        for f in frames:
            for r in masked:
                d, t = ang(bo[f][r][1], gi[f][r][1]), ang(bo[f][r][2], gi[f][r][2])
                pr = per_role.setdefault(r, [0.0, 0.0])
                pr[0], pr[1] = max(pr[0], d), max(pr[1], t)
                worst["dir"], worst["twist"] = max(worst["dir"], d), max(worst["twist"], t)
        res["C2"][c] = {"frames": len(frames), "roles_compared": masked, "max_dir_deg": worst["dir"], "max_twist_deg": worst["twist"],
                        "per_role_max": per_role, "pass": worst["dir"] <= 2.0 and worst["twist"] <= 5.0}
        # C3: engine mannequin at scene frame 1 + clip frame * 30 / fps vs the Blender pose at that clip frame
        bp = blender[c]
        step = cl["fps"] / 30.0
        w3 = {"dir": 0.0, "twist": 0.0}
        pr3 = {}
        n3 = 0
        for f in frames:
            cf = (f - 1) * step
            if abs(cf - round(cf)) > 1e-9 or str(int(round(cf))) not in bp["frames"]:
                continue
            bl = bp["frames"][str(int(round(cf)))]
            n3 += 1
            for r, v in bl.items():
                if r not in ma[f] or r not in cl["mask"]:
                    continue
                d, t = ang(ma[f][r][1], v["dir"]), ang(ma[f][r][2], v["twist"])
                x = pr3.setdefault(r, [0.0, 0.0])
                x[0], x[1] = max(x[0], d), max(x[1], t)
                w3["dir"], w3["twist"] = max(w3["dir"], d), max(w3["twist"], t)
        res["C3"][c] = {"frames_compared": n3, "roles": len(pr3), "max_dir_deg": w3["dir"], "max_twist_deg": w3["twist"],
                        "per_role_max": pr3, "pass": n3 > 0 and w3["dir"] <= 1.0 and w3["twist"] <= 3.0}
        # interior maxima (per character) and the loop seam
        n_int = len(frames) if not cl["loop"] else (len(frames) - 1) // 2 + 1
        for who, per in (("boy", bo), ("girl", gi)):
            chg, root = per_frame_change(per, LIMB_ROLES + ["hand.L", "hand.R"], frames[:n_int])
            interior.setdefault(who, {})[c] = {r: max(v.values(), default=0.0) for r, v in chg.items()}
            interior[who][c]["__root"] = max(root.values(), default=0.0)
            if cl["loop"]:
                seam_f = 1 + int(round(cl["frame_count"] / step))  # scene frame of clip frame N (= 0 of cycle 2)
                chg2, root2 = per_frame_change(per, LIMB_ROLES, [seam_f - 1, seam_f])
                seam = {r: chg2[r][seam_f] for r in LIMB_ROLES}
                lim = {r: 1.25 * interior[who][c][r] for r in LIMB_ROLES}
                res["C4"]["seam"].setdefault(c, {})[who] = {
                    "seam_frame": seam_f, "max_seam_change_deg": max(seam.values()),
                    "worst_ratio_to_interior_max": max(seam[r] / max(1e-9, interior[who][c][r]) for r in LIMB_ROLES if interior[who][c][r] > 1e-6),
                    "root_seam_change_m": root2[seam_f], "pass": all(seam[r] <= lim[r] + 1e-6 for r in LIMB_ROLES)}
    res["C4"]["interior"] = interior
    # ---------------------------------------------------------------- blending and layering scenes (C4)
    W0, W1 = 250, 380
    L = {c: (clips[c]["frame_count"] - 1) * 30.0 / clips[c]["fps"] for c in CLIPS}  # clip length in scene frames
    T = {"wave": 30, "point": 140, "wave_walk": 260, "sit": 420}
    T["stand"] = T["sit"] + int(L["sit_down"]) + 20
    for who in ("boy", "girl"):
        leg = json.load(open(pk[who]))["retarget"]["leg_length"]
        clip_acts = [
            {"type": "clip", "character": who, "clip": "idle_relaxed", "base": True},
            {"type": "clip", "character": who, "clip": "wave", "start": T["wave"], "blendIn": 8, "blendOut": 8},
            {"type": "clip", "character": who, "clip": "point", "start": T["point"], "mirror": True, "blendIn": 8, "blendOut": 8},
            {"type": "clip", "character": who, "clip": "wave", "start": T["wave_walk"], "blendIn": 8, "blendOut": 8},
            {"type": "clip", "character": who, "clip": "sit_down", "start": T["sit"], "blendIn": 8, "blendOut": 0, "end": T["stand"] + 8},
            {"type": "clip", "character": who, "clip": "stand_up", "start": T["stand"], "blendIn": 8, "blendOut": 8}]
        walk = {"type": "walk", "character": who, "start": W0, "end": W1, "to": [0.0, 0.8 * leg / 0.26]}
        chars = [{"name": who, "asset": os.path.relpath(pk[who], sd), "position": [0, 0, 0], "yawDeg": 0, "life": False}]
        n_end = int(T["stand"] + L["stand_up"] + 30)
        p = os.path.join(sd, f"blend_{who}.scene.json")
        json.dump(scene(chars, clip_acts + [walk], n_end), open(p, "w"), indent=1)
        p0 = os.path.join(sd, f"blend_{who}_underlying.scene.json")
        json.dump(scene(chars, [clip_acts[0], walk], n_end), open(p0, "w"), indent=1)
        pw = os.path.join(sd, f"walk_{who}.scene.json")  # the engine's walk alone (unchanged code path)
        json.dump(scene(chars, [walk], n_end), open(pw, "w"), indent=1)
        B = Baked(bake(a.engine, p, os.path.join(sd, f"blend_{who}.bake.json")), pk).data[who]
        U = Baked(bake(a.engine, p0, os.path.join(sd, f"blend_{who}_underlying.bake.json")), pk).data[who]
        Wk = Baked(bake(a.engine, pw, os.path.join(sd, f"walk_{who}.bake.json")), pk).data[who]
        frames = sorted(B)
        chg, root = per_frame_change(B, LIMB_ROLES, frames)
        # walk interior: the whole walk (start to its end ramp) of the engine walk without clips
        wchg, wroot = per_frame_change(Wk, LIMB_ROLES, list(range(W0 - 1, W1 + 9)))
        interior[who]["walk"] = {r: max(v.values(), default=0.0) for r, v in wchg.items()}
        interior[who]["walk"]["__root"] = max(wroot.values(), default=0.0)
        it = interior[who]
        mir = lambda r: r[:-2] + (".L" if r.endswith(".R") else ".R") if r[-2:] in (".L", ".R") else r
        e = {k: T[k] + L[c] for k, c in (("wave", "wave"), ("point", "point"), ("wave_walk", "wave"), ("stand", "stand_up"))}
        windows = [  # (name, first frame, last frame, sources, mirror the second source's roles)
            ("wave blend-in (base idle -> wave)", T["wave"], T["wave"] + 10, ("idle_relaxed", "wave"), False),  # the base idle is under every window
            ("wave blend-out (wave -> base idle)", e["wave"] - 9, e["wave"] + 1, ("idle_relaxed", "wave"), False),
            ("point (mirrored) blend-in", T["point"], T["point"] + 10, ("idle_relaxed", "point"), True),
            ("point (mirrored) blend-out", e["point"] - 9, e["point"] + 1, ("idle_relaxed", "point"), True),
            ("walk start (base idle -> walk)", W0 - 6, W0 + 6, ("idle_relaxed", "walk"), False),
            ("wave during walk: blend-in", T["wave_walk"], T["wave_walk"] + 10, ("idle_relaxed", "walk", "wave"), False),
            ("wave during walk: blend-out", e["wave_walk"] - 9, e["wave_walk"] + 1, ("idle_relaxed", "walk", "wave"), False),
            ("walk end (walk -> base idle)", W1 - 2, W1 + 14, ("idle_relaxed", "walk"), False),
            ("sit_down blend-in (base idle -> sit_down)", T["sit"], T["sit"] + 10, ("idle_relaxed", "sit_down"), False),
            ("sit_down -> stand_up hand-over", T["stand"] - 2, T["stand"] + 10, ("idle_relaxed", "sit_down", "stand_up"), False),
            ("stand_up end (stand_up -> base idle)", e["stand"] - 9, e["stand"] + 1, ("idle_relaxed", "stand_up"), False)]
        for name, f0, f1, srcs, m2 in windows:
            f0, f1 = int(f0), int(f1)
            worst = {"role": None, "change": 0.0, "limit": 0.0, "ratio": 0.0}
            ok = True
            for f in range(max(f0, frames[1]), f1 + 1):
                for r in LIMB_ROLES:
                    lim = min(12.0, 1.25 * max(it[x].get(mir(r) if (m2 and x == srcs[-1]) else r, 0.0) for x in srcs))
                    v = chg[r].get(f, 0.0)
                    if v > lim + 1e-4:
                        ok = False
                    ratio = v / lim if lim > 1e-9 else (0.0 if v < 1e-4 else float("inf"))
                    if ratio > worst["ratio"]:
                        worst = {"role": r, "frame": f, "change": v, "limit": lim, "ratio": ratio}
            rlim = 1.25 * max(it[x]["__root"] for x in srcs)
            rmax = max(root.get(f, 0.0) for f in range(max(f0, frames[1]), f1 + 1))
            rok = rmax <= rlim + 1e-7
            res["C4"]["boundaries"].append({"character": who, "boundary": name, "frames": [f0, f1], "worst": worst,
                                            "root_max_change_m": rmax, "root_limit_m": rlim, "pass": ok and rok})
        # entry / exit: weight 0 at the start frame and the frame after the end equals the underlying pose
        for name, f in (("wave start", T["wave"]), ("wave end+1", e["wave"] + 1), ("point start", T["point"]),
                        ("point end+1", e["point"] + 1), ("wave (walking) start", T["wave_walk"]),
                        ("wave (walking) end+1", e["wave_walk"] + 1), ("sit_down start", T["sit"]), ("stand_up end+1", e["stand"] + 1)):
            f = int(f)
            d = max(RT.qangle_deg(B[f][r][0], U[f][r][0]) for r in LIMB_ROLES)
            res["C4"]["entry_exit"].append({"character": who, "event": name, "frame": f, "max_diff_vs_underlying_deg": d, "pass": d <= 1e-3})
    res["pass"] = {"C2": all(v["pass"] for v in res["C2"].values()), "C3": all(v["pass"] for v in res["C3"].values()),
                   "C4": all(b["pass"] for b in res["C4"]["boundaries"]) and all(e["pass"] for e in res["C4"]["entry_exit"])
                   and all(s["pass"] for v in res["C4"]["seam"].values() for s in v.values())}
    json.dump(res, open(os.path.join(out, "clip_measurements.json"), "w"), indent=1)
    print(json.dumps(res["pass"]))
    for c in CLIPS:
        print(f"{c:13s} C2 dir {res['C2'][c]['max_dir_deg']:.4f} twist {res['C2'][c]['max_twist_deg']:.4f} | "
              f"C3 dir {res['C3'][c]['max_dir_deg']:.4f} twist {res['C3'][c]['max_twist_deg']:.4f} ({res['C3'][c]['frames_compared']} frames)")
    for b in res["C4"]["boundaries"]:
        w = b["worst"]
        print(f"{b['character']:4s} {b['boundary']:45s} worst {w['role']} {w['change']:.2f}/{w['limit']:.2f} deg "
              f"root {b['root_max_change_m'] * 1000:.1f}/{b['root_limit_m'] * 1000:.1f} mm {'PASS' if b['pass'] else 'FAIL'}")
    for c, v in res["C4"]["seam"].items():
        for who, s in v.items():
            print(f"seam {c} {who}: max {s['max_seam_change_deg']:.3f} deg, ratio {s['worst_ratio_to_interior_max']:.2f} {'PASS' if s['pass'] else 'FAIL'}")
    print("entry/exit max", max(e["max_diff_vs_underlying_deg"] for e in res["C4"]["entry_exit"]))


if __name__ == "__main__":
    main()
