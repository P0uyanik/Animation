"""Hand mesh round 2 (T-121): separated fingers with a readable gap and rounded tips. Opt-in.

body_generic builds each hand as a palm plus four finger tubes and a thumb, then voxel-remeshes them together. The
finger spacing (0.55 x palm half-width) is smaller than a finger's diameter, so the remesh fuses the fingers into a
mitten and single fingertips do not read in a grasp (T-116). This module lays the fingers out so that neighbours keep a
gap (a fixed fraction of the spacing at the knuckles, widening towards the tips through a small fan spread), gives
them rounded, slightly full plush tips, and remeshes with a voxel small enough to keep the gaps open.

Opt-in: spec `body.hands = "hands_r2/1"` (usually from an override file). Without it, nothing here runs and the build
is unchanged. The bone names are the same (palm.*, f_<finger>.01-.03, thumb.01-.03 per side): the finger points of the
hand frames are replaced by this layout before the rig is fitted, so the finger bones follow the separated fingers
and the usual role "hand" heat weights apply.

The layout and the grasp check are plain Python (no bpy), so tests/test_hands_r2.py runs without Blender.
"""
import math

GENERATOR_VERSIONS = ("hands_r2/1",)
FINGERS = (("f_index", -1.5, 0), ("f_middle", -0.5, 1), ("f_ring", 0.5, 2), ("f_pinky", 1.5, 3))
SEGMENTS = (0.40, 0.72, 1.0)  # joint fractions root -> tip, the same split as body_generic.fit_metarig_from_joints
DEFAULTS = {
    "spacing": 0.64,      # finger spacing / palm half-width (body_generic: 0.55); wider so fingers stay chubby
    "gap": 0.14,          # gap between neighbouring fingers at the knuckles / spacing
    "spread_deg": 4.0,    # fan angle per finger step from the middle line (tips separate more than roots)
    "radius_max": 0.92,   # finger radius at most this x spec finger_radius (plush fingers stay chubby)
    "tip_fullness": 1.04, # fingertip pad radius / finger radius (rounded, slightly full tip)
    "voxel_gap": 0.30,    # remesh voxel / knuckle gap (keeps the gap open through the remesh)
}
TARGET_VERTICES = 8000  # per hand after the remesh (body_generic's hand: about 1.2k; the gaps need more)
# Full grasp for the clearance check: per joint curl (deg) of each finger and of the thumb (flexion, opposition).
FULL_GRASP = {"finger_curl_deg": (40.0, 50.0, 35.0), "thumb_flex_deg": (25.0, 25.0), "thumb_oppose_deg": 30.0}


# ---- tiny vector helpers on tuples ----
def _add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _mul(a, k):
    return (a[0] * k, a[1] * k, a[2] * k)


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _norm(a):
    n = math.sqrt(_dot(a, a))
    return _mul(a, 1.0 / n)


def _rot(v, axis, deg):
    """Rodrigues rotation of v about the unit axis."""
    t = math.radians(deg)
    c, s = math.cos(t), math.sin(t)
    return _add(_add(_mul(v, c), _mul(_cross(axis, v), s)), _mul(axis, _dot(axis, v) * (1 - c)))


def params(hand_spec):
    """Round-2 options: DEFAULTS, overridden by spec body.params.hand.r2 (optional)."""
    return {**DEFAULTS, **((hand_spec or {}).get("r2") or {})}


def layout(frame, hp, H):
    """Finger and thumb chains for one hand.

    frame: {"wrist", "d", "palm_n", "side_v", "sx", "thumb": (t0, troot, ttip)} as tuples (the body_generic hand frame;
    the thumb is kept as body_generic lays it out). hp: spec body.params.hand. Returns
    {"fingers": {name: {"palm": point, "joints": [root, j1, j2, tip], "radius", "tip_radius"}},
     "thumb": {"joints": [t0, troot, tmid, ttip], "radius", "tip_radius"}, "gap", "voxel", "radius"}."""
    o = params(hp)
    W, d, pn, sv, sx = frame["wrist"], frame["d"], frame["palm_n"], frame["side_v"], frame["sx"]
    pl, pw = hp["palm_len"] * H, hp["palm_half_width"] * H
    spacing = pw * o["spacing"]
    gap = spacing * o["gap"]
    r = min(hp["finger_radius"] * H * o["radius_max"], (spacing - gap) / 2.0)
    base = _add(W, _mul(d, 0.15 * pl))
    fingers = {}
    for name, off, k in FINGERS:
        across = _mul(sv, off * spacing * sx)
        root = _add(_add(W, _mul(d, 0.95 * pl)), across)
        L = hp["finger_len"][k] * H
        direction = _norm(_add(d, _mul(pn, hp["finger_curl"])))  # body_generic's rest curl, kept
        direction = _rot(direction, pn, -o["spread_deg"] * off * sx)  # fan: outer fingers lean outwards
        if _dot(_sub(_add(root, direction), root), _mul(sv, off * sx)) < 0:  # spread sign follows the side
            direction = _rot(direction, pn, 2 * o["spread_deg"] * off * sx)
        tip = _add(root, _mul(direction, L * math.sqrt(1 + hp["finger_curl"] ** 2)))
        joints = [root] + [_add(root, _mul(_sub(tip, root), f)) for f in SEGMENTS]
        fingers[name] = {"palm": _add(base, across), "joints": joints, "radius": r, "tip_radius": r * o["tip_fullness"]}
    t0, troot, ttip = frame["thumb"]
    tr = hp["thumb_radius"] * H * o["radius_max"]
    thumb = {"joints": [t0, troot, _add(troot, _mul(_sub(ttip, troot), 0.5)), ttip], "radius": tr,
             "tip_radius": tr * o["tip_fullness"]}
    return {"fingers": fingers, "thumb": thumb, "gap": gap, "radius": r, "voxel": gap * o["voxel_gap"]}


def pose(lay, frame, curl_deg=(0.0, 0.0, 0.0), thumb_flex_deg=(0.0, 0.0), thumb_oppose_deg=0.0):
    """Forward kinematics on the layout: each finger joint curls towards the palm about the finger's own knuckle axis
    (the .01/.02/.03 bones); the thumb flexes about the hand axis at .02/.03 and opposes about the palm normal at .01.
    Returns {name: [points]} including "thumb"."""
    pn = frame["palm_n"]
    out = {}
    for name, f in lay["fingers"].items():
        pts = [tuple(p) for p in f["joints"]]
        axis = _norm(_cross(_sub(pts[-1], pts[0]), pn))  # positive rotation moves the tip towards the palm side
        if _dot(_rot(_sub(pts[1], pts[0]), axis, 10.0), pn) < _dot(_sub(pts[1], pts[0]), pn):
            axis = _mul(axis, -1.0)
        for j, ang in enumerate(curl_deg):  # rotate the rest of the chain about joint j
            pivot = pts[j]
            for i in range(j + 1, len(pts)):
                pts[i] = _add(pivot, _rot(_sub(pts[i], pivot), axis, ang))
        out[name] = pts
    pts = [tuple(p) for p in lay["thumb"]["joints"]]
    pivot = pts[1]
    for i in range(2, len(pts)):  # opposition at the thumb root (.01 -> .02 joint), about the palm normal
        pts[i] = _add(pivot, _rot(_sub(pts[i], pivot), pn, thumb_oppose_deg * -frame["sx"]))
    d = frame["d"]
    axis = _norm(_cross(_sub(pts[-1], pts[1]), d)) if abs(_dot(_norm(_sub(pts[-1], pts[1])), d)) < 0.99 else frame["side_v"]
    if _dot(_rot(_sub(pts[-1], pts[1]), axis, 10.0), pn) < _dot(_sub(pts[-1], pts[1]), pn):
        axis = _mul(axis, -1.0)
    for j, ang in zip((1, 2), thumb_flex_deg):
        pivot = pts[j]
        for i in range(j + 1, len(pts)):
            pts[i] = _add(pivot, _rot(_sub(pts[i], pivot), axis, ang))
    out["thumb"] = pts
    return out


def _seg_dist(p1, q1, p2, q2):
    """Closest distance between segments p1q1 and p2q2 (Ericson, Real-Time Collision Detection 5.1.9)."""
    d1, d2, r = _sub(q1, p1), _sub(q2, p2), _sub(p1, p2)
    a, e, f = _dot(d1, d1), _dot(d2, d2), _dot(d2, r)
    c, b = _dot(d1, r), _dot(d1, d2)
    den = a * e - b * b
    s = min(max((b * f - c * e) / den, 0.0), 1.0) if den > 1e-18 else 0.0
    t = (b * s + f) / e
    if t < 0.0:
        t, s = 0.0, min(max(-c / a, 0.0), 1.0)
    elif t > 1.0:
        t, s = 1.0, min(max((b - c) / a, 0.0), 1.0)
    c1, c2 = _add(p1, _mul(d1, s)), _add(p2, _mul(d2, t))
    x = _sub(c1, c2)
    return math.sqrt(_dot(x, x))


def clearances(lay, posed):
    """Surface clearance (m) between every pair of digits, each digit a chain of capsules with its full radius
    (the tip pad radius on the last segment). Negative = the fingers intersect. Returns {(a, b): metres}."""
    rad = {n: (f["radius"], f["tip_radius"]) for n, f in lay["fingers"].items()}
    rad["thumb"] = (lay["thumb"]["radius"], lay["thumb"]["tip_radius"])
    names = sorted(posed)
    out = {}
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            pa, pb = posed[a], posed[b]
            best = 1e9
            for ia in range(len(pa) - 1):
                if a == "thumb" and ia == 0:  # the thumb's .01 segment lies inside the palm
                    continue
                for ib in range(len(pb) - 1):
                    if b == "thumb" and ib == 0:
                        continue
                    ra = rad[a][1] if ia == len(pa) - 2 else rad[a][0]
                    rb = rad[b][1] if ib == len(pb) - 2 else rad[b][0]
                    best = min(best, _seg_dist(pa[ia], pa[ia + 1], pb[ib], pb[ib + 1]) - ra - rb)
            out[(a, b)] = best
    return out


# ---- Blender side ----
def _frame_tuple(F, wrist, sx):
    return {"wrist": tuple(wrist), "d": tuple(F["d"]), "palm_n": tuple(F["palm_n"]), "side_v": tuple(F["side_v"]),
            "sx": sx, "thumb": tuple(tuple(p) for p in F["thumb"])}


def apply_to_frames(frames, P, H, J):
    """Replaces the finger points of body_generic's hand frames by the round-2 layout (in place), so the finger bones
    fitted from the frames follow the separated fingers. Returns {side: layout}."""
    from mathutils import Vector
    hp = P["hand"]
    lays = {}
    for s, sx in (("L", 1), ("R", -1)):
        F = frames[s]
        lay = layout(_frame_tuple(F, J[f"wrist.{s}"], sx), hp, H)
        F["fingers"] = {n: (Vector(f["palm"]), Vector(f["joints"][0]), Vector(f["joints"][-1]))
                        for n, f in lay["fingers"].items()}
        lays[s] = lay
    return lays


def build(C, M, P, H, J, frames, lays, G):
    """The two hand meshes (hand.L, hand.R; role 'hand'): body_generic's palm, the round-2 fingers with rounded tips,
    the thumb, remeshed with a voxel that keeps the gaps open. Returns ([(object, 'hand')], report)."""
    from mathutils import Matrix, Vector
    hpp = P["hand"]
    out, report = [], {"generator": GENERATOR_VERSIONS[0]}
    for s in ("L", "R"):
        F, lay = frames[s], lays[s]
        d, pn, sv = F["d"], F["palm_n"], F["side_v"]
        centre = J[f"wrist.{s}"] + d * 0.5 * hpp["palm_len"] * H
        palm = G.uv_sphere(f"_palm.{s}", centre, 1.0, C, 48, 24, (1, 1, 1))  # finer than body_generic: no facets
        Rm = Matrix((sv, pn, d)).transposed()
        for v in palm.data.vertices:  # the body_generic palm (oriented soft box: across, thickness, along)
            loc = v.co - centre
            v.co = centre + Rm @ Vector((loc.x * hpp["palm_half_width"] * H, loc.y * hpp["palm_half_thick"] * H,
                                         loc.z * 0.6 * hpp["palm_len"] * H))
        pieces = [palm]
        for name, f in lay["fingers"].items():
            root, tip = Vector(f["joints"][0]), Vector(f["joints"][-1])
            r, rt = f["radius"], f["tip_radius"]
            ax = (tip - root).normalized()
            mid = root + (tip - root) * 0.55
            pieces.append(G.tube(f"_{name}.{s}", [root - ax * 0.6 * r, mid, tip], [r, r * 0.96, r * 0.94],
                                 [r * 0.94, r * 0.90, r * 0.88], C, up_hint=tuple(pn), seg=16, cap_end=None))
            pieces.append(G.uv_sphere(f"_{name}_tip.{s}", tip, 1.0, C, 16, 8, (rt, rt * 0.94, rt)))  # rounded pad
        th = lay["thumb"]
        t0, troot, tmid, ttip = (Vector(p) for p in th["joints"])
        tr, trt = th["radius"], th["tip_radius"]
        pieces.append(G.tube(f"_thumb.{s}", [t0, troot, ttip], [tr * 1.1, tr, tr * 0.94], [tr, tr * 0.95, tr * 0.88], C,
                             up_hint=tuple(pn), seg=16, cap_end=None))
        pieces.append(G.uv_sphere(f"_thumb_tip.{s}", ttip, 1.0, C, 16, 8, (trt, trt * 0.94, trt)))
        hand = G.join(pieces, f"hand.{s}")
        G.voxel_remesh(hand, lay["voxel"], smooth_iter=3)
        G.add_mod(hand, "DECIMATE", ratio=min(1.0, TARGET_VERTICES / max(1, len(hand.data.vertices))))
        G.apply_mods(hand)  # collapse only merges along existing edges, so the gaps stay open
        hand.data.shade_smooth()
        G.assign(hand, M["skin"])
        out.append((hand, "hand"))
        report[s] = {"finger_radius_mm": round(lay["radius"] * 1000, 2), "gap_mm": round(lay["gap"] * 1000, 2),
                     "voxel_mm": round(lay["voxel"] * 1000, 3), "vertices": len(hand.data.vertices)}
    return out, report


def replace_hands(C, M, parts, P, H, J, frames, G):
    """Opt-in hook for build_character.main_generic: drops body_generic's hands from parts, lays out the round-2
    fingers into the frames (bones follow) and builds the new hands. Returns (parts, report)."""
    import bpy
    for ob, role in parts:
        if role == "hand":
            bpy.data.objects.remove(ob, do_unlink=True)
    lays = apply_to_frames(frames, P, H, J)
    hands, report = build(C, M, P, H, J, frames, lays, G)
    return [p for p in parts if p[1] != "hand"] + hands, report
