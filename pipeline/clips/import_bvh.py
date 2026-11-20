"""Mocap -> plush.clip/1 importer (T-175; plan docs/evaluation/animation/T-174/README.md section 5).

Pure Python (no Blender): reads CMU motion capture, either the official ASF/AMC files from mocap.cs.cmu.edu or a BVH
conversion, and writes a plush.clip/1 file with the SAME retarget math as the rest of the clip system
(pipeline/clips/retarget.py, docs/ANIMATION_CLIPS.md section 8 "future mocap conversion"):

    C_r  rest direction / twist per role from the source rest pivots (retarget.derive)
    A_r  = Fref_r . C_r^-1
    G_r  = R_r(frame) . R_r(rest)^-1             (global rotation relative to rest, engine axes)
    L_r  = A_p . G_p^-1 . G_r . A_r^-1           (the clip sample, reference space)

What it adds over the T-174 feasibility test:
- the CMU role maps (ASF/AMC joint names and the cgspeed BVH names);
- folding of the extra spine / neck joints (CMU lowerback, lowerneck + upperneck; BVH LowerBack, Neck1): the folded
  role keeps its own joint's twist and gets the swing that points it exactly at its child pivot (0 deg direction error);
- heading normalisation (the take faces / travels along engine +Z), ground correction (the planted ankle lands at the
  character's rest ankle height), resampling to 24 fps (slerp), optional seamless loop extraction;
- licence + attribution in every clip (CMU only; ATTRIBUTION.md next to the clips);
- contacts.foot_plant from the source ankle height and speed;
- an optional chibi "style" block (read by engine/scene/clip_layers.cpp; see STYLE_PRESETS).

    python3 pipeline/clips/import_bvh.py --asf 07.asf --amc 07_01.amc --name cmu_walk_07_01 --out content/clips/mocap \
        [--frames A:B] [--loop auto|A:B] [--style walk|sit|none] [--source-id 07_01] [--description ...]
    python3 pipeline/clips/import_bvh.py --bvh 07_01.bvh [--rest-frame 1] ...
Deterministic: same inputs, same bytes."""
import argparse
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import retarget as RT  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
PROFILE = os.path.join(ROOT, "pipeline", "charsys", "rig_profiles", "humanoid_rigify.json")
TARGET_FPS = 24.0
SEAT_PELVIS = 0.2  # estimate: the seat top is this many leg lengths under the seated hip pivot
CMU_LICENSE = "CMU-Mocap"
CMU_ATTRIBUTION = ("The data used in this project was obtained from mocap.cs.cmu.edu. "
                   "The database was created with funding from NSF EIA-0196217.")

# Role maps: role -> (joint, fold). A joint's pivot is where its segment starts and its rotation turns that segment.
# fold = True: the source has extra joints between this role's pivot and its child role's pivot; the role is
# aligned to point at the child pivot (swing) on top of its own joint's rotation.
CMU_ASF_ROLES = {"hips": ("root", True), "spine": ("upperback", False), "chest": ("thorax", False),
                 "neck": ("lowerneck", True), "head": ("head", False),
                 "upperArm.L": ("lhumerus", False), "forearm.L": ("lradius", False), "hand.L": ("lhand", False),
                 "thigh.L": ("lfemur", False), "shin.L": ("ltibia", False), "foot.L": ("lfoot", False)}
# The hand's pivot is the wrist (start of lwrist), its rotation the hand's; the toe point is used for contacts only.
CMU_ASF_PIVOT = {"hand.L": "lwrist"}
CMU_ASF_TOE = {"foot.L": "ltoes"}
CMU_BVH_ROLES = {"hips": ("Hips", True), "spine": ("Spine", False), "chest": ("Spine1", False),
                 "neck": ("Neck", True), "head": ("Head", False),
                 "upperArm.L": ("LeftArm", False), "forearm.L": ("LeftForeArm", False), "hand.L": ("LeftHand", False),
                 "thigh.L": ("LeftUpLeg", False), "shin.L": ("LeftLeg", False), "foot.L": ("LeftFoot", False)}
CMU_BVH_PIVOT = {}
CMU_BVH_TOE = {"foot.L": "LeftToeBase"}

# Chibi style presets (docs/evaluation/animation/T-175/README.md). lean: share of the source trunk lean kept (hips,
# spine, chest, neck swing; yaw is kept); stride: horizontal root scale; arm_swing: arm swing around the clip's mean
# arm pose; tempo: clock multiplier (short legs step quicker); foot_lock: two-bone leg IK pin on foot_plant frames.
STYLE_PRESETS = {
    "walk": {"lean": 0.6, "stride": 1.0, "arm_swing": 0.85, "tempo": 1.15, "foot_lock": True},
    "sit": {"lean": 0.55, "stride": 1.0, "arm_swing": 1.0, "tempo": 1.1, "foot_lock": True, "foot_lead": 5,
            "foot_release": 10},
}


# ------------------------------------------------------------------ 3x3 matrices (row lists)
def mmul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def mT(a):
    return [[a[j][i] for j in range(3)] for i in range(3)]


def mvec(a, v):
    return [a[0][0] * v[0] + a[0][1] * v[1] + a[0][2] * v[2], a[1][0] * v[0] + a[1][1] * v[1] + a[1][2] * v[2],
            a[2][0] * v[0] + a[2][1] * v[1] + a[2][2] * v[2]]


def rot_axis(axis, deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    if axis == "x":
        return [[1, 0, 0], [0, c, -s], [0, s, c]]
    if axis == "y":
        return [[c, 0, s], [0, 1, 0], [-s, 0, c]]
    return [[c, -s, 0], [s, c, 0], [0, 0, 1]]


IDENT = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]


def euler(order, degs):
    """Rotation for angles applied in `order` (e.g. 'xyz': first x, then y, then z, all about fixed axes)."""
    m = IDENT
    for ax, d in zip(order, degs):
        m = mmul(rot_axis(ax, d), m)
    return m


def quat_to_matrix(q):
    w, x, y, z = q
    return [[1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
            [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
            [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)]]


def swing(a, b):
    """Shortest rotation (quaternion) taking unit vector a to unit vector b."""
    a, b = RT.normalize(a), RT.normalize(b)
    d = RT.dot(a, b)
    if d < -0.999999:
        ax = RT.perpendicular(a, [0, 0, 1])
        return [0.0, ax[0], ax[1], ax[2]]
    c = RT.cross(a, b)
    return RT.qnorm([1.0 + d, c[0], c[1], c[2]])


def slerp(a, b, t):
    d = sum(x * y for x, y in zip(a, b))
    if d < 0:
        b, d = [-c for c in b], -d
    if d > 0.9995:
        return RT.qnorm([x + (y - x) * t for x, y in zip(a, b)])
    th = math.acos(min(1.0, d))
    s = math.sin(th)
    return [(math.sin((1 - t) * th) * x + math.sin(t * th) * y) / s for x, y in zip(a, b)]


# ------------------------------------------------------------------ source skeletons
class Source:
    """A posed source skeleton: rest + per frame {joint: (pivot [x,y,z], global rotation 3x3)} in engine axes
    (+Y up, the character faces +Z, its left is +X)."""

    def __init__(self, rest, frames, fps, roles, pivots, toes):
        self.rest, self.frames, self.fps = rest, frames, fps
        self.roles, self.pivots, self.toes = roles, pivots, toes


def parse_asf(path):
    bones, hier, units = {}, {}, {"length": 1.0}
    section, cur = None, None
    root = {"order": "xyz", "axis": "xyz", "position": [0.0, 0.0, 0.0], "orientation": [0.0, 0.0, 0.0]}
    for raw in open(path, encoding="latin-1"):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith(":"):
            section = line.split()[0][1:]
            continue
        t = line.split()
        if section == "units" and t[0] == "length":
            units["length"] = float(t[1])
        elif section == "root":
            if t[0] == "order":
                root["order"] = "".join(x[1].lower() for x in t[1:] if x.upper().startswith("R"))
                root["tr"] = [x.upper() for x in t[1:]]
            elif t[0] == "axis":
                root["axis"] = t[1].lower()
            elif t[0] == "position":
                root["position"] = [float(x) for x in t[1:4]]
            elif t[0] == "orientation":
                root["orientation"] = [float(x) for x in t[1:4]]
        elif section == "bonedata":
            if t[0] == "begin":
                cur = {"dof": [], "axis": [0.0, 0.0, 0.0], "axis_order": "xyz"}
            elif t[0] == "end":
                bones[cur["name"]] = cur
                cur = None
            elif t[0] == "name":
                cur["name"] = t[1]
            elif t[0] == "direction":
                cur["direction"] = [float(x) for x in t[1:4]]
            elif t[0] == "length":
                cur["length"] = float(t[1])
            elif t[0] == "axis":
                cur["axis"] = [float(x) for x in t[1:4]]
                cur["axis_order"] = t[4].lower() if len(t) > 4 else "xyz"
            elif t[0] == "dof":
                cur["dof"] = [x.lower() for x in t[1:]]
        elif section == "hierarchy":
            if t[0] in ("begin", "end"):
                continue
            hier[t[0]] = t[1:]
    parent = {}
    for p, cs in hier.items():
        for c in cs:
            parent[c] = p
    order, todo = [], ["root"]
    while todo:
        n = todo.pop(0)
        order.append(n)
        todo.extend(hier.get(n, []))
    for b in bones.values():
        b["C"] = euler(b["axis_order"], b["axis"])
    return {"bones": bones, "parent": parent, "order": order, "root": root}


def parse_amc(path, asf):
    frames, cur = [], None
    for raw in open(path, encoding="latin-1"):
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith(":"):
            continue
        t = line.split()
        if len(t) == 1 and t[0].isdigit():
            cur = {}
            frames.append(cur)
            continue
        if cur is not None:
            cur[t[0]] = [float(x) for x in t[1:]]
    return frames


def asf_pose(asf, values):
    """Forward kinematics of one AMC frame (values None = the ASF rest pose). Returns {joint: (pivot, rotation)}
    where a bone's pivot is its start (the parent's end) and the root's pivot is the root position."""
    root = asf["root"]
    C0 = euler(root["axis"], root["orientation"])
    out = {}
    if values is None:
        pos, Mr = list(root["position"]), C0
    else:
        v = values.get("root", [0.0] * 6)
        tr = root.get("tr", ["TX", "TY", "TZ", "RX", "RY", "RZ"])
        ch = dict(zip(tr, v))
        pos = [ch.get("TX", 0.0), ch.get("TY", 0.0), ch.get("TZ", 0.0)]
        Mr = mmul(mmul(C0, euler(root["order"], [ch.get("R" + a.upper(), 0.0) for a in root["order"]])), mT(C0))
    out["root"] = (pos, Mr)
    ends = {"root": pos}
    for n in asf["order"][1:]:
        b = asf["bones"][n]
        p = asf["parent"][n]
        Mp = out[p][1]
        if values is None or not b["dof"]:
            M = Mp
        else:
            v = values.get(n, [0.0] * len(b["dof"]))
            ang = {d: x for d, x in zip(b["dof"], v)}
            Mm = euler("xyz", [ang.get("rx", 0.0), ang.get("ry", 0.0), ang.get("rz", 0.0)])
            M = mmul(mmul(mmul(Mp, b["C"]), Mm), mT(b["C"]))
        start = ends[p]
        d = mvec(M, b["direction"])
        ends[n] = [start[i] + b["length"] * d[i] for i in range(3)]
        out[n] = (start, M)
    return out


def load_asf_amc(asf_path, amc_path, fps=120.0):
    asf = parse_asf(asf_path)
    raw = parse_amc(amc_path, asf)
    rest = asf_pose(asf, None)
    frames = [asf_pose(asf, v) for v in raw]
    # CMU ASF axes are already engine axes (+Y up, +X the subject's left, feet point +Z in the rest pose).
    return Source(rest, frames, fps, CMU_ASF_ROLES, CMU_ASF_PIVOT, CMU_ASF_TOE)


def parse_bvh(path):
    tok = open(path, encoding="latin-1").read().split()
    i = 0
    joints, order, stack = {}, [], []
    fps, motion = 120.0, []
    while i < len(tok):
        t = tok[i]
        if t in ("ROOT", "JOINT"):
            name = tok[i + 1]
            joints[name] = {"parent": stack[-1] if stack else None, "offset": [0.0] * 3, "channels": []}
            order.append(name)
            stack.append(name)
            i += 2
        elif t == "End":
            stack.append(None)
            i += 2
        elif t == "OFFSET":
            if stack[-1] is not None:
                joints[stack[-1]]["offset"] = [float(x) for x in tok[i + 1:i + 4]]
            i += 4
        elif t == "CHANNELS":
            n = int(tok[i + 1])
            joints[stack[-1]]["channels"] = tok[i + 2:i + 2 + n]
            i += 2 + n
        elif t == "}":
            stack.pop()
            i += 1
        elif t == "MOTION":
            nf = int(tok[i + 2])
            ft = float(tok[i + 5])
            fps = 1.0 / ft
            i += 6
            nc = sum(len(j["channels"]) for j in joints.values())
            for _ in range(nf):
                motion.append([float(x) for x in tok[i:i + nc]])
                i += nc
        else:
            i += 1
    return joints, order, fps, motion


def bvh_pose(joints, order, values):
    out, k = {}, 0
    for n in order:
        j = joints[n]
        loc, M = [0.0, 0.0, 0.0], IDENT
        for ch in j["channels"]:
            v = values[k] if values is not None else 0.0
            k += 1
            c = ch.lower()
            if c.endswith("position"):
                loc["xyz".index(c[0])] = v
            elif c.endswith("rotation"):
                M = mmul(M, rot_axis(c[0], v))  # BVH: intrinsic, channel order left to right
        if j["parent"] is None:
            pos = [j["offset"][i] + loc[i] for i in range(3)]
            G = M
        else:
            pp, Gp = out[j["parent"]]
            o = mvec(Gp, j["offset"])
            pos = [pp[i] + o[i] for i in range(3)]
            G = mmul(Gp, M)
        out[n] = (pos, G)
    return out


def load_bvh(path, rest_frame=0):
    """rest_frame 0 = the zero-channel pose; N >= 1 = that motion frame (cgspeed CMU: frame 1 is a T-pose)."""
    joints, order, fps, motion = parse_bvh(path)
    rest = bvh_pose(joints, order, motion[rest_frame - 1] if rest_frame > 0 else None)
    frames = [bvh_pose(joints, order, v) for v in motion]
    # BVH convention (cgspeed CMU): +Y up, the subject faces +Z, its left is +X: engine axes.
    return Source(rest, frames, fps, CMU_BVH_ROLES, CMU_BVH_PIVOT, CMU_BVH_TOE)


# ------------------------------------------------------------------ conversion
def full_roles(m):
    out = dict(m)
    for r, v in m.items():
        if r.endswith(".L"):
            out[r[:-2] + ".R"] = (mirror_name(v[0]),) + tuple(v[1:])
    return out


def mirror_name(n):
    for a, b in (("Left", "Right"), ("left", "right")):
        if n.startswith(a):
            return b + n[len(a):]
    if n[:1] == "l" and len(n) > 1:
        return "r" + n[1:]
    return n


def full_side(m):
    out = dict(m)
    for r, v in m.items():
        if r.endswith(".L"):
            out[r[:-2] + ".R"] = mirror_name(v)
    return out


def detect_plants(ankles, fps, leg, h_tol=0.02, v_tol=0.35, min_frames=3):
    """Frames where an ankle is down (within h_tol leg lengths of its lowest height) and nearly still (horizontal
    speed < v_tol leg lengths per second). Returns [[a, b], ...] (inclusive), runs of >= min_frames, 1-frame gaps
    closed."""
    n = len(ankles)
    lo = min(p[1] for p in ankles)
    down = []
    for k in range(n):
        a = ankles[max(0, k - 1)]
        b = ankles[min(n - 1, k + 1)]
        span = (min(n - 1, k + 1) - max(0, k - 1)) or 1
        v = math.hypot(b[0] - a[0], b[2] - a[2]) / span * fps / leg
        down.append(ankles[k][1] - lo <= h_tol * leg and v <= v_tol)
    for k in range(1, n - 1):
        if not down[k] and down[k - 1] and down[k + 1]:
            down[k] = True
    runs, k = [], 0
    while k < n:
        if down[k]:
            j = k
            while j + 1 < n and down[j + 1]:
                j += 1
            if j - k + 1 >= min_frames:
                runs.append([k, j])
            k = j + 1
        else:
            k += 1
    return runs


def convert(src, name, frames=None, loop=None, style=None, source_id="", description="", profile_path=PROFILE,
            fps_out=TARGET_FPS, face="auto", origin_frame=None, seat=None):
    prof = json.load(open(profile_path))
    ref = RT.reference_pose(prof["reference_pose"])
    roles = full_roles(src.roles)
    pivots = full_side(src.pivots)
    toes = full_side(src.toes)
    roles = {r: v for r, v in roles.items() if v[0] in src.rest}

    def pivot(pose, r):
        return pose[pivots.get(r, roles[r][0])][0]

    heads0 = {r: pivot(src.rest, r) for r in roles}
    data = RT.derive(heads0, ref)
    order = [x for x in ref if x["name"] in data["roles"]]
    child = {}
    for x in order:  # the child role a folded role points at (its reference "end")
        if roles.get(x["name"], (None, False))[1] and x["end"] in roles:
            child[x["name"]] = x["end"]
    A, parent = {}, {}
    for x in order:
        c = data["roles"][x["name"]]
        A[x["name"]] = RT.qmul(RT.frame(x["ref_dir"], x["ref_twist"]), RT.qconj(RT.frame(c["dir"], c["twist"])))
        p = x["parent"]
        while p and p not in data["roles"]:
            p = next((y["parent"] for y in ref if y["name"] == p), "")
        parent[x["name"]] = p
    leg = data["leg_length"]

    # frame range at the source rate, then the time samples at fps_out
    f0, f1 = 0, len(src.frames) - 1
    if frames:
        a, b = frames
        f0, f1 = max(0, a), min(len(src.frames) - 1, b)

    def global_q(pose, r):
        j = roles[r][0]
        M = mmul(pose[j][1], mT(src.rest[j][1]))
        q = RT.quat_from_matrix(M)
        if r in child:  # fold: swing the role so it points at its child pivot
            d0 = RT.sub(heads0[child[r]], heads0[r])
            d_pred = RT.qrot(q, d0)
            d_act = RT.sub(pivot(pose, child[r]), pivot(pose, r))
            if RT.length(d_act) > 1e-9:
                q = RT.qnorm(RT.qmul(swing(d_pred, d_act), q))
        return q

    def toe_point(pose, r):
        t = toes.get(r)
        return pose[t][0] if t and t in pose else pivot(pose, r)

    per_src = {}

    def src_sample(k):
        if k not in per_src:
            pose = src.frames[k]
            per_src[k] = ({r: global_q(pose, r) for r in data["roles"] if r in roles},
                          {r: pivot(pose, r) for r in roles}, {r: toe_point(pose, r) for r in ("foot.L", "foot.R") if r in roles})
        return per_src[k]

    def sample_at(t):
        """Source time t (seconds from f0): interpolated globals, pivots, toes."""
        x = f0 + t * src.fps
        k = min(int(math.floor(x)), f1)
        u = x - k
        g0, p0, t0 = src_sample(k)
        if u < 1e-9 or k >= f1:
            return g0, p0, t0
        g1, p1, t1 = src_sample(k + 1)
        G = {r: slerp(g0[r], g1[r], u) for r in g0}
        P = {r: [a + (b - a) * u for a, b in zip(p0[r], p1[r])] for r in p0}
        T = {r: [a + (b - a) * u for a, b in zip(t0[r], t1[r])] for r in t0}
        return G, P, T

    dur = (f1 - f0) / src.fps
    n = int(math.floor(dur * fps_out + 1e-6)) + 1
    seq = [sample_at(i / fps_out) for i in range(n)]

    # optional loop: [a, a + P) in output frames with pose(a + P) ~ pose(a)
    loop_range = None
    if loop == "auto":
        loop_range = find_cycle(seq, fps_out)
    elif loop:
        loop_range = loop
    if loop_range:
        a, b = loop_range  # b = a + period (exclusive end, the frame that matches a)
        seq = seq[a:b + 1]
        n = len(seq) - 1  # frames in the clip; seq[n] is the seam frame (frame 0 of the next cycle)
    else:
        n = len(seq)

    # heading: the take faces (or, for a loop, travels along) +Z
    hip = [s[1]["hips"] for s in seq]
    if face == "auto":
        face = "travel" if loop_range else "first"
    yaw = 0.0
    if face == "travel" and math.hypot(hip[-1][0] - hip[0][0], hip[-1][2] - hip[0][2]) > 0.05 * leg:
        yaw = math.atan2(hip[-1][0] - hip[0][0], hip[-1][2] - hip[0][2])
    elif face in ("first", "travel"):
        fwd = RT.qrot(seq[0][0]["hips"], [0.0, 0.0, 1.0])
        yaw = math.atan2(fwd[0], fwd[2])
    origin = None
    if origin_frame is not None:  # heading and x/z origin from another source frame (clips cut from one take line up)
        Go, Po, _ = src_sample(max(0, min(len(src.frames) - 1, origin_frame)))
        fwd = RT.qrot(Go["hips"], [0.0, 0.0, 1.0])
        yaw = math.atan2(fwd[0], fwd[2])
        origin = Po["hips"]
    Ry = RT.qnorm([math.cos(-yaw / 2), 0.0, math.sin(-yaw / 2), 0.0])

    def ry(v):
        return RT.qrot(Ry, v)

    samples, ankles = [], {"foot.L": [], "foot.R": []}
    hips_pos = []
    for G, P, T in seq:
        Gy = {r: RT.qnorm(RT.qmul(Ry, q)) for r, q in G.items()}
        L = {}
        for x in order:
            r = x["name"]
            if r not in Gy:
                continue
            p = parent[r]
            Gp = Gy[p] if p else [1.0, 0.0, 0.0, 0.0]
            Ap = A[p] if p else [1.0, 0.0, 0.0, 0.0]
            q = RT.qnorm(RT.qmul(RT.qmul(RT.qmul(Ap, RT.qconj(Gp)), Gy[r]), RT.qconj(A[r])))
            L[r] = [-c for c in q] if q[0] < 0 else q
        samples.append(L)
        hips_pos.append(ry(P["hips"]))
        for f in ankles:
            if f in P:
                ankles[f].append(ry(P[f]))

    # ground: the lowest ankle over the take is the planted ankle height; the root's height is the hips' height above
    # it minus the rest hips-above-ankle height, so a planted (straight-ish) leg lands at the rest ankle height
    feet = [f for f in ankles if ankles[f]]
    ground = min(p[1] for f in feet for p in ankles[f])
    rest_ank = min(heads0[f][1] for f in feet)
    rest_h = heads0["hips"][1] - rest_ank
    x0, z0 = hips_pos[0][0], hips_pos[0][2]
    if origin is not None:
        x0, z0 = ry(origin)[0], ry(origin)[2]
    roots = [[(h[0] - x0) / leg, (h[1] - ground - rest_h) / leg, (h[2] - z0) / leg] for h in hips_pos]

    clip_meta_extra = {}
    if loop_range:
        # seamless: spread the seam mismatch over the cycle (rotations and root height), cycle_offset = travel
        last = samples[n]
        for r in samples[0]:
            delta = RT.qmul(last[r], RT.qconj(samples[0][r]))
            inv = RT.qconj(delta)
            for k in range(n + 1):
                q = RT.qnorm(RT.qmul(slerp([1.0, 0.0, 0.0, 0.0], inv, k / n), samples[k][r]))
                samples[k][r] = [-c for c in q] if q[0] < 0 else q
        dy = roots[n][1] - roots[0][1]
        for k in range(n + 1):
            roots[k][1] -= dy * k / n
        cyc = [roots[n][0] - roots[0][0], 0.0, roots[n][2] - roots[0][2]]
        clip_meta_extra["cycle_offset"] = [round(c, 7) for c in cyc]
        samples, roots = samples[:n], roots[:n]
        for f in feet:
            ankles[f] = ankles[f][:n + 1]

    contacts, plant_heights = [], []  # heights: mean planted ankle height above the ground, leg lengths
    for f in ("foot.L", "foot.R"):
        if f not in ankles or not ankles[f]:
            continue
        runs = [[a, min(b, n - 1)] for a, b in detect_plants(ankles[f], fps_out, leg) if a <= n - 1]
        if loop_range and len(runs) > 1 and runs[-1][1] == n - 1 and runs[0][0] == 0:
            # a plant across the loop seam: one contact whose end runs past the last frame (frames wrap)
            runs = runs[1:-1] + [[runs[-1][0], runs[0][1] + n]]
        for a, b in runs:
            contacts.append({"type": "foot_plant", "role": f, "frames": [a, b]})
            hs = [ankles[f][k % len(ankles[f])][1] for k in range(a, b + 1)]
            plant_heights.append(round((sum(hs) / len(hs) - ground) / leg, 4))
    if seat:  # seated frames A:B (clip frames): seat top = height_ratio x leg length (docs/ANIMATION_CLIPS.md)
        a, b = seat
        hip_h = min(hips_pos[k][1] for k in range(a, min(b, n - 1) + 1)) - ground + rest_ank - min(
            src.rest[j][0][1] for j in src.rest)
        contacts.append({"type": "seat", "frames": [a, min(b, n - 1)], "height_ratio": round((hip_h - SEAT_PELVIS * leg) / leg, 4)})
    contacts.sort(key=lambda c: (c["frames"][0], c.get("role", "")))

    meta = {"source": "mocap", "license": CMU_LICENSE, "attribution": CMU_ATTRIBUTION, "loop": bool(loop_range),
            "description": description or f"CMU motion capture {source_id} (mocap.cs.cmu.edu), imported by T-175",
            "mask": [x["name"] for x in order if x["name"] in samples[0]], "contacts": contacts,
            "mirror_note": "mirrorable (mocap, left/right mapped by role)"}
    clip = write_clip(name, fps_out, samples, roots, meta, prof["reference_pose"])
    if loop_range:
        clip["root"]["cycle_offset"] = clip_meta_extra["cycle_offset"]
    clip["x_mocap"] = {"importer": "pipeline/clips/import_bvh.py", "source_id": source_id, "source_fps": src.fps,
                       "source_frames": [f0, f1], "loop_frames": list(loop_range) if loop_range else None,
                       "source_leg": round(leg, 5), "heading_deg": round(math.degrees(yaw), 3),
                       "folded": sorted(child),
                       # a spread above ~0.03 means the take is not on level ground (reject it for a loop)
                       "plant_height_spread": round(max(plant_heights) - min(plant_heights), 4) if plant_heights else 0.0}
    if style:
        clip["style"] = make_style(style, samples)
    return clip


def find_cycle(seq, fps, lo_s=0.7, hi_s=1.6):
    """Best gait cycle: frames (a, a + P) with the smallest pose difference on the legs, P in [lo_s, hi_s] seconds."""
    n = len(seq)
    roles = [r for r in ("thigh.L", "shin.L", "thigh.R", "shin.R", "hips") if r in seq[0][0]]
    best = None
    for P in range(int(lo_s * fps), int(hi_s * fps) + 1):
        for a in range(0, n - P):
            d = 0.0
            for r in roles:
                # compare leg rotations relative to the hips (heading independent)
                qa = RT.qmul(RT.qconj(seq[a][0]["hips"]), seq[a][0][r])
                qb = RT.qmul(RT.qconj(seq[a + P][0]["hips"]), seq[a + P][0][r])
                d += RT.qangle_deg(qa, qb)
            if best is None or d < best[0] - 1e-9:
                best = (d, a, a + P)
    if best is None:
        raise SystemExit("loop auto: the take is too short for a gait cycle")
    return best[1], best[2]


def mean_quat(qs):
    s = [0.0, 0.0, 0.0, 0.0]
    for q in qs:
        sg = -1.0 if sum(a * b for a, b in zip(q, qs[0])) < 0 else 1.0
        s = [a + sg * b for a, b in zip(s, q)]
    q = RT.qnorm(s)
    return q if q[0] >= 0 else [-c for c in q]


def make_style(preset, samples):
    st = dict(STYLE_PRESETS[preset]) if isinstance(preset, str) else dict(preset)
    st = {"version": 1, "preset": preset if isinstance(preset, str) else "custom", **st}
    if st.get("arm_swing", 1.0) != 1.0:
        st["arm_center"] = {r: [round(c, 7) for c in mean_quat([s[r] for s in samples])]
                            for r in ("upperArm.L", "forearm.L", "upperArm.R", "forearm.R") if r in samples[0]}
    return st


def write_clip(name, fps, samples, roots, meta, ref_block):
    """Dense plush.clip/1 (the same layout as clip_tools.write_clip with dense=True, without Blender)."""
    n = len(samples)
    roles = [r for r in samples[0] if r in meta["mask"]]
    tracks = {r: {"samples": [[round(c, 7) for c in s[r]] for s in samples]} for r in roles}
    clip = {"format": "plush.clip", "version": 1, "name": name, "fps": fps, "frame_count": n,
            "loop": bool(meta.get("loop", False)), "source": meta["source"], "license": meta["license"],
            "attribution": meta["attribution"], "description": meta["description"], "mask": meta["mask"],
            "mirror": {"suffix": [".L", ".R"], "axis": "x", "note": meta["mirror_note"]},
            "contacts": meta["contacts"], "tracks": tracks, "reference_pose": ref_block}
    clip["root"] = {"translation": {"samples": [[round(c, 7) for c in r] for r in roots]}, "scale": "leg_length",
                    "space": "character, engine axes"}
    return clip


def save(clip, path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(clip, f, indent=1)
        f.write("\n")


def _range(s):
    a, b = s.split(":")
    return int(a), int(b)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--asf")
    ap.add_argument("--amc")
    ap.add_argument("--bvh")
    ap.add_argument("--rest-frame", type=int, default=0, help="BVH: motion frame used as rest (1-based; 0 = offsets)")
    ap.add_argument("--fps", type=float, default=120.0, help="AMC frame rate (CMU: 120)")
    ap.add_argument("--name", required=True)
    ap.add_argument("--out", required=True, help="output folder (or a .clip.json path)")
    ap.add_argument("--frames", type=_range, help="source frame range A:B (0-based, inclusive)")
    ap.add_argument("--loop", help="'auto' or A:B in output frames (B = A + period)")
    ap.add_argument("--style", choices=sorted(STYLE_PRESETS) + ["none"], default="none")
    ap.add_argument("--face", choices=["auto", "first", "travel", "none"], default="auto")
    ap.add_argument("--origin-frame", type=int, help="source frame that defines heading and the x/z origin")
    ap.add_argument("--seat", type=_range, help="seated clip frames A:B: adds a seat contact (estimated height_ratio)")
    ap.add_argument("--source-id", default="")
    ap.add_argument("--description", default="")
    a = ap.parse_args(argv)
    if a.bvh:
        src = load_bvh(a.bvh, a.rest_frame)
    elif a.asf and a.amc:
        src = load_asf_amc(a.asf, a.amc, a.fps)
    else:
        ap.error("give --asf and --amc, or --bvh")
    loop = None
    if a.loop:
        loop = "auto" if a.loop == "auto" else _range(a.loop)
    clip = convert(src, a.name, frames=a.frames, loop=loop, style=None if a.style == "none" else a.style,
                   source_id=a.source_id, description=a.description, face=a.face, origin_frame=a.origin_frame,
                   seat=a.seat)
    path = a.out if a.out.endswith(".clip.json") else os.path.join(a.out, f"{a.name}.clip.json")
    save(clip, path)
    print(json.dumps({"clip": os.path.relpath(path, ROOT), "frames": clip["frame_count"], "loop": clip["loop"],
                      "contacts": len(clip["contacts"]), "x_mocap": clip["x_mocap"]}))


if __name__ == "__main__":
    main()
