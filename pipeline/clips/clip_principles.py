"""Shared acting helpers for script-made clips (T-027): animation principles on the shared skeleton roles.

Pure Python (no bpy): used by make_clips.py and make_emotion_clips.py, and testable without Blender. Character-
independent: poses are {role: L} with L the role's reference-space rotation relative to its semantic parent (the
plush.clip/1 convention, docs/ANIMATION_CLIPS.md section 1); root offsets are in leg lengths (engine axes: +X the
character's left, +Y up, +Z forward). Nothing here names a character.

Principles provided (all parameterised):
- spacing: ease() profiles (linear, in, out, in-out with a power) instead of uniform spacing;
- anticipation, overshoot and settle: move() is a 0 -> 1 transition curve with a small counter-move before the
  main move (s < 0), an overshoot past the target (s > 1) and a damped settle; every phase joins with zero velocity
  (C1, no pops);
- successive breaking / overlap: perform() plays key poses ("beats") per role with a per-role delay along the chain
  (spine, chest, shoulder, elbow, wrist, fingers: chain_delays()), so the proximal joint leads and the distal ones
  follow. Shoulder, elbow and wrist no longer rotate in sync, which turns straight hand paths into arcs; distal
  joints get more overshoot (follow-through);
- whole-body support: support() adds hip and spine counter-rotation and a weight shift towards the action side;
  plant_legs() keeps both feet planted under a hips rotation and root offset (two-bone IK in reference space);
- loops: periodic() / wave() helpers with per-role phase lags (overlap in idles).

Quaternion convention: (w, x, y, z), Hamilton product, q1 . q2 applies q2 first (retarget.py)."""
import math

import retarget as RT

ID = [1.0, 0.0, 0.0, 0.0]
SIDES = ("L", "R")
FINGERS = ("thumbA", "thumbB", "f0a", "f0b", "f1a", "f1b", "f2a", "f2b", "f3a", "f3b")


# ------------------------------------------------------------------ quaternion helpers
def rot(axis, deg):
    a = math.radians(deg) / 2
    n = RT.normalize(axis)
    return [math.cos(a), n[0] * math.sin(a), n[1] * math.sin(a), n[2] * math.sin(a)]


def rx(d):
    return rot([1, 0, 0], d)


def ry(d):
    return rot([0, 1, 0], d)


def rz(d):
    return rot([0, 0, 1], d)


def seq(*qs):
    """Applies rotations in order (first argument first), in the role's reference axes."""
    out = ID
    for q in qs:
        out = RT.qmul(q, out)
    return out


def qlog(q):
    """Rotation vector / 2 (axis * half angle) of a unit quaternion, shortest arc."""
    q = RT.qnorm(q)
    if q[0] < 0:
        q = [-c for c in q]
    s = math.sqrt(q[1] ** 2 + q[2] ** 2 + q[3] ** 2)
    if s < 1e-12:
        return [0.0, 0.0, 0.0]
    a = math.atan2(s, q[0])
    return [q[1] / s * a, q[2] / s * a, q[3] / s * a]


def qexp(v):
    a = math.sqrt(sum(c * c for c in v))
    if a < 1e-12:
        return list(ID)
    s = math.sin(a) / a
    return [math.cos(a), v[0] * s, v[1] * s, v[2] * s]


def qpow(q, s):
    return qexp([c * s for c in qlog(q)])


def interp(a, b, s):
    """a . (a^-1 b)^s: slerp from a to b for s in [0, 1]; extrapolates for s < 0 (counter-move) and s > 1
    (overshoot) along the same great arc."""
    return RT.qnorm(RT.qmul(a, qpow(RT.qmul(RT.qconj(a), b), s)))


def mirror_q(q):
    """Reflection across x = 0 (the clip format's mirror rule)."""
    return [q[0], q[1], -q[2], -q[3]]


def mirror_role(r):
    if r.endswith(".L"):
        return r[:-2] + ".R"
    if r.endswith(".R"):
        return r[:-2] + ".L"
    return r


def mirror_pose(p):
    return {mirror_role(r): mirror_q(q) for r, q in p.items()}


def mirror_root(v):
    return [-v[0], v[1], v[2]]


def depth_of(role):
    """Position of a role along its limb chain (0 trunk ... 5 fingers): drives overlap and follow-through."""
    base = role.split(".")[0]
    return {"hips": 0, "spine": 0, "chest": 1, "neck": 2, "head": 3, "upperArm": 2, "forearm": 3, "hand": 4,
            "thigh": 1, "shin": 2, "foot": 3}.get(base, 5 if base in FINGERS else 0)


# ------------------------------------------------------------------ spacing
def smooth(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def ease(u, kind="inout", power=2.0):
    """Spacing profile on u in [0, 1]: 'linear', 'in' (slow start), 'out' (slow end), 'inout' (slow both ends,
    power > 1 sharpens it; 2 is close to smoothstep). Zero end velocity where the profile eases."""
    u = min(1.0, max(0.0, u))
    if kind == "linear":
        return u
    if kind == "in":
        return u ** power
    if kind == "out":
        return 1 - (1 - u) ** power
    a, b = u ** power, (1 - u) ** power
    return a / (a + b)


def move(u, anticipation=0.0, ant=0.15, overshoot=0.0, settle=0.25, power=2.0, bounce=True):
    """Transition curve s(u), u in [0, 1] -> s from 0 to 1, with
    - anticipation: s dips to -anticipation over the first `ant` of the time (a counter-move);
    - main move: eased (power) from -anticipation to 1 + overshoot;
    - settle: back from 1 + overshoot to 1 over the last `settle` of the time, with one small damped undershoot
      when `bounce`. Every phase starts and ends with zero velocity, so the curve is C1 and has no pops.
    The main move gets 1 - ant - settle of the time: give a beat enough frames for its anticipation and settle (the
    peak speed of the main move is about power x its average speed)."""
    u = min(1.0, max(0.0, u))
    ua = ant if anticipation > 0 else 0.0
    us = settle if overshoot > 0 else 0.0
    if u < ua:
        return -anticipation * smooth(u / ua)
    if u <= 1 - us:
        x = (u - ua) / max(1e-9, 1 - ua - us)
        return -anticipation + (1 + overshoot + anticipation) * ease(x, "inout", power)
    v = (u - (1 - us)) / us
    return 1 + overshoot * (1 - smooth(v)) * (math.cos(math.pi * v) if bounce else 1.0)


# ------------------------------------------------------------------ successive breaking / overlap
def chain_delays(step=2.0, trunk=0.0, roles=None):
    """Per-role delay in frames: depth along the chain x step (spine leads, fingers follow last)."""
    out = {}
    for r in roles or ():
        out[r] = trunk + step * depth_of(r)
    return out


class Beat:
    """A key pose at a clip frame, and the motion parameters of the transition that LEAVES it towards the next beat
    (anticipation, overshoot, power, settle, ant, bounce: see move(); per_role={role: {...}} overrides them for single
    roles). Roles missing from a pose keep the previous beat's rotation (identity before they are first named)."""

    def __init__(self, frame, pose, **motion):
        self.frame = float(frame)
        self.pose = dict(pose)
        self.motion = motion


def perform(beats, n, delay=None, follow=0.5, lead_anticipation=True):
    """Plays beats per role with successive breaking: role r reaches beat i at frame beat_i + delay[r]. Each
    transition uses move() with the leaving beat's parameters; overshoot grows along the limb past the shoulder
    (follow-through, x (1 + follow * (depth - 2)) for elbow, wrist, fingers, head), a beat's per_role dict overrides
    the parameters of single roles (after scaling), anticipation is strongest on the leading (proximal) joints when lead_anticipation.
    Returns {frame: pose} for frames 0 .. n-1."""
    delay = delay or {}
    roles = []
    for b in beats:
        for r in b.pose:
            if r not in roles:
                roles.append(r)
    # every beat names every role: a role missing from a beat keeps the previous beat's rotation (identity, the
    # reference, before the first beat that names it)
    full = []
    prev = {r: ID for r in roles}
    for b in beats:
        cur = dict(prev)
        cur.update(b.pose)
        full.append(cur)
        prev = cur
    out = {}
    for f in range(n):
        p = {}
        for r in roles:
            t = f - delay.get(r, 0.0)
            if t <= beats[0].frame:
                p[r] = full[0][r]
                continue
            if t >= beats[-1].frame:
                p[r] = full[-1][r]
                continue
            i = max(k for k in range(len(beats) - 1) if beats[k].frame <= t)
            a, b = beats[i], beats[i + 1]
            m = dict(a.motion)
            per_role = m.pop("per_role", {})
            d = depth_of(r)
            if m.get("overshoot"):
                m["overshoot"] = m["overshoot"] * (1 + follow * max(0, d - 2))
            m.update(per_role.get(r, {}))
            if m.get("anticipation") and lead_anticipation:
                m["anticipation"] = m["anticipation"] * max(0.3, 1 - 0.15 * d)
            s = move((t - a.frame) / (b.frame - a.frame), **m)
            p[r] = interp(full[i][r], full[i + 1][r], s)
        out[f] = p
    return out


def scalar_track(beats, f):
    """A scalar timeline [(frame, value, motion dict)] evaluated with move() (anticipation / overshoot allowed)."""
    if f <= beats[0][0]:
        return beats[0][1]
    if f >= beats[-1][0]:
        return beats[-1][1]
    i = max(k for k in range(len(beats) - 1) if beats[k][0] <= f)
    (f0, v0, m), (f1, v1, _) = beats[i], beats[i + 1]
    return v0 + (v1 - v0) * move((f - f0) / (f1 - f0), **(m or {}))


# ------------------------------------------------------------------ loops
def periodic(t, terms):
    """Sum of harmonics: terms = [(amplitude, cycles per loop, phase in turns)], t = loop phase in turns."""
    return sum(a * math.sin(2 * math.pi * (k * t + ph)) for a, k, ph in terms)


def lagged(fn, t, role, lag_turns):
    """fn(t) evaluated with a phase lag that grows with the role's chain depth (overlap in loops)."""
    return fn(t - lag_turns * depth_of(role))


# ------------------------------------------------------------------ whole-body support
class Body:
    """Leg geometry of the authoring rig in leg lengths (reference space): hip joints relative to the hips role and
    thigh / shin lengths. Measured from the rig, so the IK matches the authoring mannequin; on characters with other
    proportions the root offset scales with their leg length (clip format)."""

    def __init__(self, hip_l, hip_r, thigh, shin):
        self.hip = {"L": list(hip_l), "R": list(hip_r)}
        self.thigh, self.shin = float(thigh), float(shin)

    @staticmethod
    def from_heads(heads, leg):
        """heads: {role: engine-axes position} of the authoring rig; leg: its leg length."""
        h = heads["hips"]
        off = {s: [(heads["thigh." + s][i] - h[i]) / leg for i in range(3)] for s in SIDES}
        th = math.dist(heads["thigh.L"], heads["shin.L"]) / leg
        sh = math.dist(heads["shin.L"], heads["foot.L"]) / leg
        return Body(off["L"], off["R"], th, sh)


def _swing_frame(d, hint):
    """Global (reference-relative) rotation taking the leg's reference frame (dir -Y, twist +Z) to (d, hint)."""
    return RT.qnorm(RT.qmul(RT.frame(d, hint), RT.qconj(RT.frame([0, -1, 0], [0, 0, 1]))))


def plant_legs(pose, root, body, knee_dir=(0.0, 0.0, 1.0)):
    """Sets thigh / shin / foot of both sides so each foot stays at its reference position, flat and forward,
    under the pose's hips rotation and the root offset (leg lengths). A leg that cannot reach lowers the root (the
    returned root); the knee bends towards knee_dir. Feet are planted in the semantic hierarchy (reference space)."""
    root = list(root)
    G_h = pose.get("hips", ID)
    leg = body.thigh + body.shin
    hips_at = {s: [root[i] + RT.qrot(G_h, body.hip[s])[i] for i in range(3)] for s in SIDES}
    feet = {s: [body.hip[s][0], body.hip[s][1] - leg, body.hip[s][2]] for s in SIDES}
    over = max(math.dist(hips_at[s], feet[s]) - leg for s in SIDES)
    if over > 1e-12:  # the supporting leg is straight: the pelvis sinks until it reaches
        root[1] -= over
        hips_at = {s: [hips_at[s][0], hips_at[s][1] - over, hips_at[s][2]] for s in SIDES}
    for s in SIDES:
        D = RT.sub(feet[s], hips_at[s])
        dl = RT.length(D)
        Dn = RT.normalize(D)
        n = RT.perpendicular(Dn, list(knee_dir))
        cos_a = (body.thigh ** 2 + dl ** 2 - body.shin ** 2) / (2 * body.thigh * dl)
        a = math.acos(max(-1.0, min(1.0, cos_a)))
        u = [math.cos(a) * Dn[i] + math.sin(a) * n[i] for i in range(3)]
        knee = [hips_at[s][i] + body.thigh * u[i] for i in range(3)]
        w = RT.normalize(RT.sub(feet[s], knee))
        G_t = _swing_frame(u, RT.perpendicular(u, [0, 0, 1]))
        G_s = _swing_frame(w, RT.perpendicular(w, [0, 0, 1]))
        pose["thigh." + s] = RT.qnorm(RT.qmul(RT.qconj(G_h), G_t))
        pose["shin." + s] = RT.qnorm(RT.qmul(RT.qconj(G_t), G_s))
        pose["foot." + s] = RT.qnorm(RT.qconj(G_s))  # global identity: flat, pointing forward
    return root


def support(pose, side, k, tilt=2.5, counter=0.9, chest=0.6, yaw=0.0, lean=0.0, shift=0.025):
    """Whole-body support for an action on `side` ('L' or 'R') with weight k in [0, 1] (may overshoot):
    - weight shift: the pelvis moves towards the action side by shift x k leg lengths and its action-side hip
      hikes by tilt x k degrees (the supporting hip rises);
    - counter-rotation: spine and chest tilt back by counter / chest x the pelvis tilt (shoulders stay near level),
      the trunk turns by yaw x k degrees (+ = towards the action side; 40 % spine, 60 % chest) and the spine leans
      forward by lean x k degrees.
    Composes onto the pose's existing hips / spine / chest rotations; returns the root offset (leg lengths) to add.
    The legs are not set here (plant_legs, or the layer underneath)."""
    sg = 1.0 if side == "L" else -1.0
    t = tilt * k * sg
    pose["hips"] = RT.qnorm(RT.qmul(pose.get("hips", ID), rz(t)))
    pose["spine"] = RT.qnorm(RT.qmul(pose.get("spine", ID), seq(rz(-counter * t), ry(0.4 * yaw * k * sg), rx(lean * k))))
    pose["chest"] = RT.qnorm(RT.qmul(pose.get("chest", ID), seq(rz(-chest * t), ry(0.6 * yaw * k * sg))))
    return [shift * k * sg, 0.0, 0.0]


# ------------------------------------------------------------------ helpers for poses
def side_pose(pose, role, q_left, s):
    """Left-side definition q_left applied to side s (mirrored for R)."""
    pose[f"{role}.{s}"] = q_left if s == "L" else mirror_q(q_left)


def blend_pose(a, b, t):
    out = {}
    for k in set(a) | set(b):
        out[k] = interp(a.get(k, ID), b.get(k, ID), t)
    return out
