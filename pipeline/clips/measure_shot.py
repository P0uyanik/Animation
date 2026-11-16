"""Shot checks from an engine bake (T-010): eye angles relative to the head (T-006 gaze limits) and pop detection
with the T-002 smoothness limits (reuses measure_clips.Baked / per_frame_change). No character-specific code.

    python3 pipeline/clips/measure_shot.py --scene <shot build>/shot.resolved.scene.json --bake <run>/bake.json \
        --out <dir> [--engine build/apps/render-cli/plush-render]
    python3 pipeline/clips/measure_shot.py --clips-before <dir> --clips-after <dir> --package boy=<pkg dir> \
        --package girl=<pkg dir> --out <dir> [--clips idle_relaxed,wave,...]

Gaze: per frame, character and eye bone ("eye.*"), the eye's rest +Z axis expressed in the head bone's frame
(R_head^T * R_eye * +Z, from the baked skinning matrices; rest frames are axis aligned), as yaw (+ = character
left) and pitch (+ = up) in degrees, plus the angle to the camera. The maxima are compared with the limits the engine
uses: the scene's life.gaze override, else the GazeLimits defaults parsed from engine/anim/animation.h.

Smoothness (T-002 C4 rule): inside blend / emotion-ramp boundary windows the per-frame rotation change of every limb
role is <= min(12 deg, 1.25 x the largest interior per-frame maximum of the sources active at that frame); at every
other frame it is <= 1.25 x that maximum (no pop beyond what the sources do on their own). A source's interior maximum is measured on a bake of
the shot with only that source (plus the base clips and look actions, which are under everything); keyed tracks
("animation") are one source. Frames where no non-base source is active use the base-only bake as the source.

Acting principles (T-027, principles_check.json; per character and limb chain, measured on the bake, no thresholds):
  chains: arm.L / arm.R (upperArm -> forearm -> hand; effector = wrist, relative to the shoulder) and trunk (hips ->
  head; effector = head pivot, relative to the hips pivot). The effector path is cut into moves at deep speed minima
  and at direction reversals.
  - ease_ratio: per move (>= 6 frames), mean effector speed in its first and last 20 % / mean speed in its middle
    20 % (1 = uniform spacing, lower = eased in and out); median over the moves. joint_ease_ratio: the same on each
    chain role's angular speed over the major moves (the spacing of the joints themselves; overlap between joints
    spreads the effector's speed towards the ends of a move, so both are reported);
  - arc_curvature: per move with a chord >= 20 % of the chain length, the largest distance of the path from the
    straight chord / chord length (0 = straight line); median and max;
  - anticipation: in joint space, per major move of the effector: a chain role first turns against the move's own
    rotation axis (2-40 % of the move, >= 0.3 deg) in the 6 frames before it or early in it, and that counter-turn is
    the role's motion there (so an oscillation such as a preceding wave does not count); "present" = any;
  - overshoot_settle: a chain role goes past its final value along the move's axis (2-40 %, >= 0.3 deg) near the
    end of the move or in the 6 frames after it, and comes back;
  - symmetry_index (per character): 1 - mean angle between each left arm role direction and the mirrored right one
    (character frame) / 90 deg, 1 = mirror-symmetric; plus the mean lateral tilt of hips / chest / head;
  - micro_motion: per chain, mean over its roles of the RMS rotation (deg) about the role's mean rotation, and the
    effector position RMS (mm), over the frames given (default: the frames where only base layers act).
Before / after for clip files (--clips-before DIR --clips-after DIR --package NAME=PKG ...): each clip is played on
every package (life off, no automatic idle; a gesture over its own version's idle_relaxed as the base, an idle alone),
baked and measured; writes clip_principles_before_after.json."""
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
import clip_principles as CP  # noqa: E402
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
        life = chars[name].get("life")
        lim = dict(lim0, **(((life if isinstance(life, dict) else {}).get("gaze")) or {}))  # "life": true has no overrides
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
    v["actions"] = [a for i, a in enumerate(scene["actions"]) if a.get("base") or a["type"] in ("look", "expression") or i in keep]
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


def ramps(a, fps, base_dir=None):
    """(start, end, ramp-in frames, ramp-out frames) of a clip or emotion action, in scene frames."""
    start = float(a.get("start", a.get("frame", 1)))
    if a["type"] not in ("clip", "emotion"):  # walk, reach, ...: their own span, 4-frame ownership ramps
        end = float(a.get("end", start))
        if a["type"] == "walk":  # the engine walk owns the legs from start - 4 to end + 10 (4-frame ownership ramps
            start, end = start - 4.0, end + 10.0  # around start .. end + 6) and turns to "face" until end + 8
        return start, end, 4.0, 4.0
    if a["type"] == "clip":
        path = a["file"] if "file" in a else os.path.join(ROOT, "content", "clips", a["clip"] + ".clip.json")
        if not os.path.isabs(path):
            path = os.path.join(base_dir or ROOT, path)  # "file" is relative to the scene file
        c = json.load(open(path))
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
        if a.get("base") or a["type"] in ("look", "expression"):  # expressions move morphs (and the jaw), not limb roles
            continue
        srcs[f"{i}_{a['type']}_{a.get('clip') or a.get('name')}".replace("/", "-")] = (variant(scene, {i}, False), (a["character"], *ramps(a, fps, base_dir)[:2]))
        if a["type"] not in ("clip", "emotion"):  # generated actions (walk, reach): sources only; their own steps can
            continue  # exceed 12 deg/frame (walk boundaries are T-002 C4 in measure_clips.py)
        st, en, ri, ro = ramps(a, fps, base_dir)
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


# ------------------------------------------------------------------ acting principles (T-027)
CHAINS = {"arm.L": (["upperArm.L", "forearm.L", "hand.L"], "hand.L", "upperArm.L"),
          "arm.R": (["upperArm.R", "forearm.R", "hand.R"], "hand.R", "upperArm.R"),
          "trunk": (["hips", "spine", "chest", "neck", "head"], "head", "hips")}


def _yaw_frame(yaw_deg):
    """World -> character frame (x left, y up, z forward) for a character turned by yaw (degrees about +Y)."""
    c, s = math.cos(math.radians(yaw_deg)), math.sin(math.radians(yaw_deg))
    return lambda v: [c * v[0] - s * v[2], v[1], s * v[0] + c * v[2]]


def _moves(path, min_len=3):
    """Cuts a path (list of points, one per frame) into moves at speed minima: [(i0, i1)] index ranges."""
    n = len(path)
    if n < 3:
        return []
    v = [0.0] + [math.dist(path[i], path[i - 1]) for i in range(1, n)]
    vmax = max(v)
    if vmax < 1e-7:
        return []
    thr = max(0.02 * vmax, 2e-5)
    stops = [0]
    rev = set()
    for i in range(1, n - 1):
        d0, d1 = RT.sub(path[i], path[i - 1]), RT.sub(path[i + 1], path[i])
        if RT.dot(d0, d1) < 0 and v[i] > thr and v[i + 1] > thr:  # a direction reversal always ends a move
            rev.add(i)
        if (v[i] <= v[i - 1] and v[i] <= v[i + 1]) or i in rev:
            stops.append(i)
    stops.append(n - 1)
    keep = [stops[0]]
    for k in range(1, len(stops) - 1):  # a minimum is a stop when it is deep relative to the peaks around it
        i = stops[k]
        left = max(v[keep[-1]:i + 1])
        right = max(v[i:stops[k + 1] + 1])
        if i in rev or v[i] < thr or v[i] < 0.35 * min(left, right):
            keep.append(i)
    keep.append(stops[-1])
    out = []
    for a, b in zip(keep, keep[1:]):
        if b - a >= min_len and max(v[a + 1:b + 1]) > thr:
            out.append((a, b))
    return out


def _move_stats(path, a, b):
    seg = path[a:b + 1]
    chord = RT.sub(seg[-1], seg[0])
    cl = RT.length(chord)
    d = RT.normalize(chord) if cl > 1e-9 else [0.0, 0.0, 0.0]
    dev = 0.0
    dip = 0.0
    for p in seg:
        w = RT.sub(p, seg[0])
        t = RT.dot(w, d)
        dev = max(dev, RT.length([w[i] - t * d[i] for i in range(3)]))
        dip = min(dip, t)
    sp = [math.dist(seg[i], seg[i - 1]) for i in range(1, len(seg))]
    m = len(sp)
    ease = None
    if m >= 6:
        k = max(1, int(round(0.2 * m)))
        mid = sp[(m - k) // 2:(m - k) // 2 + k]
        ends = sp[:k] + sp[-k:]
        mm = sum(mid) / len(mid)
        ease = (sum(ends) / len(ends)) / mm if mm > 1e-9 else None
    return {"frames": [a, b], "chord_m": cl, "dir": d, "arc_curvature": dev / cl if cl > 1e-9 else 0.0,
            "start_dip_ratio": -dip / cl if cl > 1e-9 else 0.0, "ease_ratio": ease}


def _median(xs):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    n = len(xs)
    return xs[n // 2] if n % 2 else 0.5 * (xs[n // 2 - 1] + xs[n // 2])


def _qmean(qs):
    ref = qs[0]
    acc = [0.0] * 4
    for q in qs:
        s = 1.0 if sum(x * y for x, y in zip(q, ref)) >= 0 else -1.0
        acc = [acc[i] + s * q[i] for i in range(4)]
    return RT.qnorm(acc)


LOOK = 6  # frames before / after a major move searched for its counter-move (anticipation) and its settle


def _joint_principles(per, frames, roles, a, b):
    """Anticipation and overshoot / settle of one major move [a, b] (frame indices) in joint space. Per chain role, the
    progress of its rotation along the move's own axis (from the pose LOOK frames before the move to its end):
    - anticipation: before / early in the move the role first turns AGAINST the move by 2-40 % of the move (>= 0.3
      deg; a counter-move as large as the move is an oscillation, not anticipation), and that counter-turn is the
      role's motion there (its rotation path <= 3 x the counter-turn);
    - overshoot / settle: near / after the end the role goes PAST its final value by 2-40 % of the move (>= 0.3 deg)
      and comes back, and that return is its motion there.
    Roles that turn less than 5 deg in the move are ignored. Returns (anticipating roles, settling roles, joint ease
    ratios: per role, its angular speed in the first and last 20 % of the move / in the middle 20 %)."""
    n = len(frames)
    ws, we = max(0, a - LOOK), min(n - 1, b + LOOK)
    ra, rs, ease = [], [], []
    for r in roles:
        q = [per[frames[i]][r][0] for i in range(ws, we + 1)]
        main = CP.qlog(RT.qmul(RT.qconj(q[0]), q[b - ws]))
        ang = RT.length(main)  # half-angle (rad)
        if ang < math.radians(5) / 2:
            continue
        ax = [c / ang for c in main]
        sp = [RT.qangle_deg(q[i], q[i + 1]) for i in range(a - ws, b - ws)]
        if len(sp) >= 6:
            kk = max(1, int(round(0.2 * len(sp))))
            mid = sp[(len(sp) - kk) // 2:(len(sp) - kk) // 2 + kk]
            if sum(mid) > 1e-9:
                ease.append((sum(sp[:kk]) + sum(sp[-kk:])) / (2 * kk) / (sum(mid) / kk))
        prog = [RT.dot(CP.qlog(RT.qmul(RT.qconj(q[0]), x)), ax) for x in q]
        step = [RT.qangle_deg(q[i], q[i + 1]) / 2 for i in range(len(q) - 1)]
        thr = max(0.02 * ang, math.radians(0.3) / 2)
        early = range(0, (a - ws) + int(0.35 * (b - a)) + 1)
        imin = min(early, key=lambda i: prog[i])
        if thr <= -prog[imin] <= 0.4 * ang and math.radians(sum(step[:imin])) <= 3 * -prog[imin] + 1e-9:
            ra.append(r)
        late = range((b - ws) - int(0.35 * (b - a)), len(q))
        imax = max(late, key=lambda i: prog[i])
        back = prog[imax] - prog[-1]
        if thr <= back <= 0.4 * ang and math.radians(sum(step[imax:])) <= 3 * back + 1e-9:
            rs.append(r)
    return ra, rs, ease


def principles(per, frames, yaw_deg=0.0, micro_frames=None):
    """Acting-principle measurements of one character's baked data (measure_clips.Baked().data[name])."""
    to_c = _yaw_frame(yaw_deg)
    frames = sorted(f for f in frames if f in per)
    out = {"frames": [frames[0], frames[-1]] if frames else [], "chains": {}}
    for name, (roles, eff, base) in CHAINS.items():
        if not all(r in per[frames[0]] for r in roles):
            continue
        path = [to_c(RT.sub(per[f][eff][3], per[f][base][3])) for f in frames]
        length = sum(math.dist(per[frames[0]][roles[i]][3], per[frames[0]][roles[i + 1]][3]) for i in range(len(roles) - 1))
        moves = [_move_stats(path, a, b) for a, b in _moves(path)]
        major = [k for k, m in enumerate(moves) if m["chord_m"] >= 0.2 * length]
        antic, settle, antic_roles, settle_roles, jease = [], [], set(), set(), []
        for k in major:
            a, b = moves[k]["frames"]
            ra, rs, je = _joint_principles(per, frames, roles, a, b)
            jease += je
            antic.append(bool(ra))
            settle.append(bool(rs))
            antic_roles |= set(ra)
            settle_roles |= set(rs)
        mf = sorted(f for f in (frames if micro_frames is None else micro_frames) if f in per)
        rms = []
        if not mf:  # no quiet frames: micro-motion is not measured
            mf = None
        prms = None
        for r in roles if mf else ():
            qs = [per[f][r][0] for f in mf]
            mean = _qmean(qs)
            rms.append(math.sqrt(sum(RT.qangle_deg(q, mean) ** 2 for q in qs) / len(qs)))
        if mf:
            ep = [to_c(RT.sub(per[f][eff][3], per[f][base][3])) for f in mf]
            c = [sum(p[i] for p in ep) / len(ep) for i in range(3)]
            prms = math.sqrt(sum(math.dist(p, c) ** 2 for p in ep) / len(ep))
        out["chains"][name] = {
            "chain_length_m": length, "moves": len(moves), "major_moves": len(major),
            "ease_ratio_median": _median(m["ease_ratio"] for m in moves),
            "joint_ease_ratio_median": _median(jease),
            "arc_curvature_median": _median(moves[k]["arc_curvature"] for k in major),
            "arc_curvature_max": max((moves[k]["arc_curvature"] for k in major), default=None),
            "anticipation_present": any(antic), "anticipated_major_moves": sum(antic), "anticipation_roles": sorted(antic_roles),
            "overshoot_settle_present": any(settle), "settled_major_moves": sum(settle), "overshoot_settle_roles": sorted(settle_roles),
            "micro_motion_rms_deg": sum(rms) / len(rms) if rms else None,
            "micro_motion_effector_rms_mm": None if prms is None else prms * 1000,
            "move_list": [{k2: (round(v, 5) if isinstance(v, float) else v) for k2, v in m.items() if k2 != "dir"} for m in moves]}
    # left / right symmetry of the arms (character frame) and lateral trunk tilt
    angs, tilt = [], []
    for f in frames:
        for r in ("upperArm", "forearm", "hand"):
            if f"{r}.L" in per[f] and f"{r}.R" in per[f]:
                dl = to_c(per[f][f"{r}.L"][1])
                dr = to_c(per[f][f"{r}.R"][1])
                angs.append(MC.ang(dl, [-dr[0], dr[1], dr[2]]))
        for r in ("hips", "chest", "head"):
            if r in per[f]:
                up = to_c(RT.qrot(per[f][r][0], [0, 1, 0]))
                tilt.append(abs(math.degrees(math.atan2(up[0], up[1]))))
    if angs:
        ma = sum(angs) / len(angs)
        out["symmetry_index"] = max(0.0, 1 - ma / 90.0)
        out["arm_mirror_difference_mean_deg"] = ma
    if tilt:
        out["trunk_lateral_tilt_mean_deg"] = sum(tilt) / len(tilt)
    return out


def principles_shot(scene, bake, pkgs):
    """Principles per character for a shot bake; micro-motion over the frames where only base layers act."""
    data = MC.Baked(bake, pkgs).data
    fps = scene["frameRate"][0] / scene["frameRate"][1]
    res = {"characters": {}}
    for ch in scene["characters"]:
        who = ch["name"]
        if who not in data:
            continue
        frames = sorted(data[who])
        busy = set()
        for a in scene.get("actions", []):
            if a.get("character") != who or a.get("base") or a["type"] in ("look", "expression"):
                continue
            if a["type"] in ("clip", "emotion"):
                try:
                    st, en, _, _ = ramps(a, fps)
                except (OSError, KeyError):
                    st, en = float(a.get("start", 1)), float(a.get("end", frames[-1]))
            else:
                st, en = float(a.get("start", a.get("frame", 1))), float(a.get("end", frames[-1]))
            busy.update(f for f in frames if st - 1 <= f <= en + 1)
        quiet = [f for f in frames if f not in busy]
        res["characters"][who] = principles(data[who], frames, float(ch.get("yawDeg", 0)), quiet if len(quiet) >= 10 else [])
        res["characters"][who]["micro_motion_frames"] = (f"{len(quiet)} base-only frames" if len(quiet) >= 10
                                                         else "not measured (fewer than 10 base-only frames)")
    return res


def clips_before_after(before, after, packages, out, engine, clips=None):
    """Plays each clip of two clip folders on the packages and measures the principles (see the module doc)."""
    names = clips or sorted({f[:-len(".clip.json")] for f in os.listdir(after) if f.endswith(".clip.json")} &
                            {f[:-len(".clip.json")] for f in os.listdir(before) if f.endswith(".clip.json")})
    sd = os.path.join(out, "scenes")
    os.makedirs(sd, exist_ok=True)
    pk = {n: os.path.join(os.path.abspath(p), "character.json") for n, p in packages.items()}
    res = {"before": os.path.abspath(before), "after": os.path.abspath(after), "clips": {}}
    for c in names:
        res["clips"][c] = {}
        for tag, d in (("before", before), ("after", after)):
            cl = json.load(open(os.path.join(d, c + ".clip.json")))
            n = int(math.ceil((cl["frame_count"] - (0 if cl["loop"] else 1)) * 30.0 / cl["fps"])) + 1
            chars = [{"name": who, "asset": os.path.relpath(pk[who], sd), "position": [0.8 * i, 0, 0], "yawDeg": 0, "life": False,
                      "autoIdle": False} for i, who in enumerate(sorted(pk))]
            acts = []
            for who in sorted(pk):
                if c != "idle_relaxed":
                    acts.append({"type": "clip", "character": who, "file": os.path.relpath(os.path.join(d, "idle_relaxed.clip.json"), sd),
                                 "base": True})
                acts.append({"type": "clip", "character": who, "file": os.path.relpath(os.path.join(d, c + ".clip.json"), sd),
                             "start": 1, "blendIn": 0, "blendOut": 0, **({"base": True} if c == "idle_relaxed" else {})})
            p = os.path.join(sd, f"{tag}_{c}.scene.json")
            json.dump(MC.scene(chars, acts, n), open(p, "w"), indent=1)
            data = MC.Baked(MC.bake(engine, p, os.path.join(sd, f"{tag}_{c}.bake.json")), pk).data
            res["clips"][c][tag] = {who: principles(data[who], sorted(data[who])) for who in sorted(pk)}
    json.dump(res, open(os.path.join(out, "clip_principles_before_after.json"), "w"), indent=1)
    return res


def _fmt(v, nd=2):
    return "-" if v is None else (("yes" if v else "no") if isinstance(v, bool) else f"{v:.{nd}f}")


def print_before_after(res, who):
    print(f"{'clip':13s} {'chain':6s} | {'ease ratio':>15s} | {'joint ease':>15s} | {'arc curvature':>15s} | {'anticip.':>9s} | "
          f"{'settle':>9s} | {'micro rms deg':>15s} | {'symmetry idx':>14s}")
    for c, v in res["clips"].items():
        b, a = v["before"][who], v["after"][who]
        for ch in ("arm.L", "arm.R", "trunk"):
            if ch not in a["chains"]:
                continue
            x, y = b["chains"][ch], a["chains"][ch]
            sym = f"{_fmt(b.get('symmetry_index'))} -> {_fmt(a.get('symmetry_index'))}" if ch == "arm.L" else ""
            print(f"{c:13s} {ch:6s} | {_fmt(x['ease_ratio_median']):>6s} -> {_fmt(y['ease_ratio_median']):>6s} | "
                  f"{_fmt(x['joint_ease_ratio_median']):>6s} -> {_fmt(y['joint_ease_ratio_median']):>6s} | "
                  f"{_fmt(x['arc_curvature_median'], 3):>6s} -> {_fmt(y['arc_curvature_median'], 3):>6s} | "
                  f"{_fmt(x['anticipation_present']):>3s} -> {_fmt(y['anticipation_present']):>3s} | "
                  f"{_fmt(x['overshoot_settle_present']):>3s} -> {_fmt(y['overshoot_settle_present']):>3s} | "
                  f"{_fmt(x['micro_motion_rms_deg']):>6s} -> {_fmt(y['micro_motion_rms_deg']):>6s} | {sym:>14s}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene")
    ap.add_argument("--bake")
    ap.add_argument("--out", required=True)
    ap.add_argument("--engine", default=os.path.join(ROOT, "build", "apps", "render-cli", "plush-render"))
    ap.add_argument("--clips-before")
    ap.add_argument("--clips-after")
    ap.add_argument("--package", action="append", default=[], help="NAME=<package dir> (clip before / after mode)")
    ap.add_argument("--clips", default="", help="comma-separated clip names (default: every clip in both folders)")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    if a.clips_before or a.clips_after:
        pk = dict(x.split("=", 1) for x in a.package)
        res = clips_before_after(a.clips_before, a.clips_after, pk, a.out, a.engine, [c for c in a.clips.split(",") if c] or None)
        for who in sorted(pk):
            print(f"== {who}")
            print_before_after(res, who)
        return
    if not (a.scene and a.bake):
        ap.error("--scene and --bake are required (or --clips-before / --clips-after)")
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
    pr = principles_shot(scene, bake, pkgs)
    json.dump(pr, open(os.path.join(a.out, "principles_check.json"), "w"), indent=1)
    for who, c in pr["characters"].items():
        for ch, v in c["chains"].items():
            print(f"principles {who} {ch}: ease {_fmt(v['ease_ratio_median'])} joint ease {_fmt(v['joint_ease_ratio_median'])} arc {_fmt(v['arc_curvature_median'], 3)} "
                  f"anticipation {_fmt(v['anticipation_present'])} settle {_fmt(v['overshoot_settle_present'])} "
                  f"micro {_fmt(v['micro_motion_rms_deg'])} deg / {_fmt(v['micro_motion_effector_rms_mm'])} mm")
        print(f"principles {who}: symmetry index {_fmt(c.get('symmetry_index'), 3)}, trunk lateral tilt {_fmt(c.get('trunk_lateral_tilt_mean_deg'))} deg")
    print(json.dumps({"gaze": g["pass"], "smoothness": s["pass"]}))


if __name__ == "__main__":
    main()
