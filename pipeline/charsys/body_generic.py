"""charsys generic body generator (`body_generic/1`): body mesh, joint set, metarig fitting and skinning for any
humanoid character, entirely from its spec. No character's dimensions live in this module.

Spec (`spec.body`): {"generator": "body_generic/1", "height_m": <sole to top of skull>, "params": {...}} with every
length a FRACTION OF height_m (angles in degrees):
  head:     centre_z, half_width, half_depth, half_height, chin_taper (0..1), forward
            optional face shape (absent = the plain ellipsoid, unchanged): lower_half_height (centre to chin; the
            lower face length), lower_roundness (superellipse exponent of the front outline below the centre: 2 =
            ellipse, 3-4 = full round cheeks and a wide jaw / broad short chin), lower_depth_roundness (the same for
            the side profile: fuller cheeks at 3/4)
            optional profile_levels [[z, centre_x, centre_y, half_width, front_depth, back_depth], ...] and
            profile_exponent: an asymmetric head loft that replaces the ellipsoid (absent = unchanged)
            body_generic/2 (T-065) head fitted to reference outlines: optional `outline` {eye_z, unit, chin_t,
            front: [[t, half_width], ...], side: [[t, forward], ...]} (eye_z and unit = the eye spacing as fractions
            of height_m; t = depth below the eye line and the values in units of the eye spacing, as measured on the
            character's front / side reference views). The lower head is scaled so the chin sits chin_t below the
            eye line, every horizontal slice of the lower face takes the front half width, and the face front takes
            the side profile (the back of the head stays); the remesh then smooths it (absent = unchanged).
            With front_eye_width (the reference's half width at the eye line, same units) the widths are taken
            relative to it, so the head keeps its own width at the eye line and takes the reference's shape below.
            The side profile is applied below mid-face only, relative to it (the chin's set-back from the mouth
            and cheeks); above it the reference silhouette is cheek volume and the eye, made by the face options
  neck:     base_z, top_z, radius, optional top_radius (thicker top blending into the jaw; default radius)
  torso:    levels: [[z, half_width, half_depth_front, half_depth_back], ...]  (bottom to top)
  shoulder: z, joint_x, clavicle_x
  arm:      angle_deg (below horizontal), upper_len, fore_len, radii [shoulder, elbow, wrist]
  hand:     palm_len, palm_half_width, palm_half_thick, finger_len [index, middle, ring, pinky], finger_radius,
            thumb_len, thumb_radius, finger_curl (0..0.4)
  leg:      hip_x, hip_z, knee_z, ankle_z, radii [thigh, knee, ankle]; optional ankle_x (feet set wider than the
            hips, an A-stance; the knee follows linearly; default hip_x = straight vertical legs, unchanged)
  foot:     length, half_width, height, heel_back
  eyes:     x, z, y                      (eye bones for gaze; the eye meshes belong to the face, M3)
Optional `spec.rig.joints`: {joint name: [x, y, z] in metres} overrides any derived joint.
Weight rules (`spec.rig.weight_rules`) are keyed by part ROLE ("skin", "hand"), never by object name.
Coordinates: metres, +Z up, the character faces -Y, her/his left is +X (as the legacy builder)."""
import json
import math
import os

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
import geom as G  # noqa: E402  (same helpers as the legacy builder)

SIDES = ((1, "L"), (-1, "R"))
GENERATOR_VERSIONS = ("body_generic/1", "body_generic/2")  # versions implemented here (versions.py; released = immutable)


def _p(P, H, key, *names):
    """Value(s) of P[key][name] scaled by the body height (missing keys raise: no hidden character defaults)."""
    d = P[key]
    vals = [d[n] for n in names]
    out = [[x * H for x in v] if isinstance(v, list) else v * H for v in vals]
    return out[0] if len(out) == 1 else out


def joints(P, H, overrides=None):
    """Generic joint set derived from the body parameters (one definition for mesh and skeleton)."""
    J = {}
    hip_z = P["leg"]["hip_z"] * H
    sh_z = P["shoulder"]["z"] * H
    neck_top = P["neck"]["top_z"] * H
    J["spine_0"] = Vector((0, 0, hip_z))
    for k in range(1, 5):  # spine_1..spine_4: evenly from the hips to the shoulder line
        J[f"spine_{k}"] = Vector((0, 0, hip_z + (sh_z - hip_z) * k / 4))
    J["spine_5"] = Vector((0, 0, (sh_z + neck_top) / 2))
    J["neck_top"] = Vector((0, 0, neck_top))
    J["head_top"] = Vector((0, P["head"]["forward"] * H, (P["head"]["centre_z"] + P["head"]["half_height"]) * H))
    a = math.radians(P["arm"]["angle_deg"])
    for sx, s in SIDES:
        S = Vector((sx * P["shoulder"]["joint_x"] * H, 0, sh_z))
        d = Vector((sx * math.cos(a), 0, -math.sin(a)))
        E = S + d * P["arm"]["upper_len"] * H
        W = E + d * P["arm"]["fore_len"] * H
        J[f"clavicle.{s}"] = Vector((sx * P["shoulder"]["clavicle_x"] * H, 0, sh_z))
        J[f"shoulder.{s}"], J[f"elbow.{s}"], J[f"wrist.{s}"] = S, E, W
        J[f"hand_end.{s}"] = W + d * P["hand"]["palm_len"] * H
        hx = sx * P["leg"]["hip_x"] * H
        J[f"pelvis.{s}"] = Vector((hx, -0.3 * P["leg"]["hip_x"] * H, hip_z + 0.5 * (sh_z - hip_z) * 0.3))
        J[f"hip.{s}"] = Vector((hx, 0, hip_z))
        ax = sx * P["leg"].get("ankle_x", P["leg"]["hip_x"]) * H  # optional A-stance (default: vertical legs)
        kt = (hip_z - P["leg"]["knee_z"] * H) / max(1e-9, hip_z - P["leg"]["ankle_z"] * H)
        J[f"knee.{s}"] = Vector((hx + (ax - hx) * kt, -0.004 * H, P["leg"]["knee_z"] * H))
        J[f"ankle.{s}"] = Vector((ax, 0, P["leg"]["ankle_z"] * H))
        hx = ax  # the foot joints sit under the ankle
        fl, fh = P["foot"]["length"] * H, P["foot"]["height"] * H
        J[f"toe.{s}"] = Vector((hx, -0.55 * fl, 0.35 * fh))
        J[f"toe_tip.{s}"] = Vector((hx, -0.95 * fl, 0.35 * fh))
        hw = P["foot"]["half_width"] * H
        J[f"heel_in.{s}"] = Vector((hx - sx * hw, P["foot"]["heel_back"] * H, 0))
        J[f"heel_out.{s}"] = Vector((hx + sx * hw, P["foot"]["heel_back"] * H, 0))
    for k, v in (overrides or {}).items():
        J[k] = Vector(v)
    return J


def hand_frames(P, H, J):
    """Per side: the hand frame and the palm, finger and thumb points shared by the hand mesh and the finger bones."""
    hp = P["hand"]
    a = math.radians(P["arm"]["angle_deg"])
    out = {}
    for sx, s in SIDES:
        W = J[f"wrist.{s}"]
        d = (J[f"hand_end.{s}"] - W).normalized()
        palm_n = Vector((-sx * math.sin(a), 0, -math.cos(a))).normalized()  # palm faces down and in, towards the body
        side_v = d.cross(palm_n).normalized()  # across the knuckles
        pl, pw = hp["palm_len"] * H, hp["palm_half_width"] * H
        base = W + d * 0.15 * pl
        spacing = pw * 0.55
        fingers = {}
        for name, off, L in (("f_index", -1.5, hp["finger_len"][0]), ("f_middle", -0.5, hp["finger_len"][1]),
                             ("f_ring", 0.5, hp["finger_len"][2]), ("f_pinky", 1.5, hp["finger_len"][3])):
            root = W + d * 0.95 * pl + side_v * (off * spacing * sx)
            tip = root + d * (L * H) + palm_n * (hp["finger_curl"] * L * H)
            fingers[name] = (base + side_v * (off * spacing * sx), root, tip)
        tl = hp["thumb_len"] * H
        troot = W + d * 0.35 * pl + side_v * (-(pw * 1.05) * sx) + palm_n * (0.25 * pw)
        ttip = troot + d * (0.75 * tl) + side_v * (-0.3 * tl * sx) + palm_n * (0.45 * tl)
        out[s] = {"d": d, "palm_n": palm_n, "side_v": side_v, "base": base, "fingers": fingers,
                  "thumb": (W + d * 0.1 * pl + side_v * (-(pw * 0.5) * sx), troot, ttip)}
    return out


def _superellipse_gain(t, n, cap=2.6):
    """Width of a superellipse |u|^n + |t|^n = 1 relative to the ellipse (n = 2) at the normalised height t (0..1):
    n > 2 gives a fuller, rounder lower face (cheeks carried down to a broad, short chin)."""
    if n == 2.0:
        return 1.0
    t = min(t, 0.999)
    return min(cap, (1.0 - t ** n) ** (1.0 / n) / math.sqrt(1.0 - t * t))


def _dense_profile(levels, steps):
    """Resample profile rows [z, values...] at `steps` + 1 evenly spaced heights with a Catmull-Rom curve through the
    rows, so the loft (which samples exactly these heights) is smooth across the keys instead of terracing at each
    one. Used only by the optional head profile loft."""
    zs = [r[0] for r in levels]
    out = []
    for k in range(steps + 1):
        z = zs[0] + (zs[-1] - zs[0]) * k / steps
        i = max(0, min(len(levels) - 2, max(j for j in range(len(zs)) if zs[j] <= z) if z > zs[0] else 0))
        t = (z - zs[i]) / max(1e-9, zs[i + 1] - zs[i])
        p0, p1, p2, p3 = (levels[max(0, i - 1)], levels[i], levels[i + 1], levels[min(len(levels) - 1, i + 2)])
        row = [z]
        for c in range(1, len(p1)):
            # non-uniform key spacing: tangents scaled to the local segment (finite differences over the neighbours)
            h = zs[i + 1] - zs[i]
            m1 = (p2[c] - p0[c]) / max(1e-9, p2[0] - p0[0]) * h
            m2 = (p3[c] - p1[c]) / max(1e-9, p3[0] - p1[0]) * h
            t2, t3 = t * t, t * t * t
            v = ((2 * t3 - 3 * t2 + 1) * p1[c] + (t3 - 2 * t2 + t) * m1 + (-2 * t3 + 3 * t2) * p2[c]
                 + (t3 - t2) * m2)
            row.append(v if c < 3 else max(v, 1e-4))  # widths and depths stay positive
        out.append(row)
    return out


def _interp(rows, t):
    if t <= rows[0][0]:
        return rows[0][1]
    for (t0, v0), (t1, v1) in zip(rows, rows[1:]):
        if t <= t1:
            return v0 + (v1 - v0) * (t - t0) / max(1e-9, t1 - t0)
    return rows[-1][1]


def fit_head_outline(head, ol, H):
    """body_generic/2: fits the lower face of the head primitive to front and side outlines measured on the
    references (see the module docstring, head.outline). Works in place on the head mesh before the body remesh."""
    ze, u = float(ol["eye_z"]) * H, float(ol["unit"]) * H
    chin_t = float(ol["chin_t"])
    me = head.data
    vs = me.vertices
    ys = [v.co.y for v in vs]
    yc = 0.5 * (min(ys) + max(ys))
    # 1. chin height: the lower head is scaled vertically so its front-most bottom point sits chin_t below the eyes
    front_low = [v.co.z for v in vs if abs(v.co.x) < 0.15 * u and v.co.y < yc]
    z_now = min(front_low)
    z_tgt = ze - chin_t * u
    k = (ze - z_tgt) / max(1e-9, ze - z_now)
    for v in vs:
        if v.co.z < ze:
            v.co.z = ze - (ze - v.co.z) * k
    # slice statistics after the vertical fit
    nb = 64
    bins = [[] for _ in range(nb + 1)]
    for v in vs:
        if z_tgt - 1e-6 <= v.co.z <= ze:
            bins[int(round((ze - v.co.z) / max(1e-9, ze - z_tgt) * nb))].append(v)
    eye_band = [v for v in vs if abs(v.co.z - ze) < 0.04 * u]  # the head at the eye line (reference for both fits)
    w0 = max((abs(v.co.x) for v in eye_band), default=None)
    f0 = min((v.co.y for v in eye_band), default=None)
    rel = (w0 / (float(ol["front_eye_width"]) * u)) if (w0 and ol.get("front_eye_width")) else 1.0  # keep the
    # cranium's width: the outline's widths relative to the reference face width at the eye line
    front = ([[0.0, w0 / u]] + [[r[0], r[1] * rel] for r in ol.get("front", []) if r[0] > 0]) if w0 else ol.get("front", [])
    side = [[0.0, 0.0]] + [r for r in ol.get("side", []) if r[0] > 0]
    # the side profile is used below mid-face only, relative to it (the chin's set-back from the cheeks and mouth):
    # above, the reference silhouette is the cheek volume and the eye, which the face options make
    t_m = 0.5 * chin_t
    i_m = int(round(t_m / chin_t * nb))
    ds = [None] * len(bins)
    for i, b in enumerate(bins):
        if not b:
            continue
        t = i / nb * chin_t
        # 2. front outline: the slice keeps its own shape, scaled to the outline's half width
        if front:
            wcur = max(abs(v.co.x) for v in b)
            s = max(0.35, min(1.6, _interp(front, t) * u / max(1e-6, wcur)))
            for v in b:
                v.co.x *= s
    base_i = next((j for j in range(i_m, len(bins)) if bins[j]), None)
    if ol.get("side") and base_i is not None:
        base_y = min(v.co.y for v in bins[base_i])
        off_m = _interp(side, t_m)
        for i, b in enumerate(bins):
            if not b or i < base_i:
                continue
            t = i / nb * chin_t
            q = max(0.0, min(1.0, (t - t_m) / (0.15 * chin_t)))
            ds[i] = ((base_y - (_interp(side, t) - off_m) * u) - min(v.co.y for v in b)) * q * q * (3 - 2 * q)
    # 3. side profile: offsets smoothed between slices (no ridges), applied with a broad lateral falloff; the back
    # half of the head stays
    if any(d is not None for d in ds):
        idx = [i for i, d in enumerate(ds) if d is not None]
        for i in idx:
            near = [ds[j] for j in idx if abs(j - i) <= 3]
            dsm = sum(near) / len(near)
            b = bins[i]
            fcur = min(v.co.y for v in b)
            wcur = max(max(abs(v.co.x) for v in b), 1e-6)
            for v in b:
                w = max(0.0, min(1.0, (yc - v.co.y) / max(1e-6, yc - fcur))) * (1.0 - min(1.0, abs(v.co.x) / wcur) ** 4)
                v.co.y += dsm * w
    me.update()


def build_body(C, M, P, H, J, frames):
    """Body skin (head, neck, torso, arms, legs, feet; one remeshed surface) and the two hands. Returns
    [(object, role)] with roles 'skin' and 'hand'."""
    hp = P["head"]
    if hp.get("profile_levels"):  # optional asymmetric head loft (absent = the ellipsoid below, unchanged)
        profile = _dense_profile([[x * H for x in level] for level in hp["profile_levels"]],
                                 int(hp.get("profile_steps", 56)))
        head = G.profile_loft("_head", profile, C, n=float(hp.get("profile_exponent", 2.25)),
                              seg=int(hp.get("profile_segments", 64)), steps=int(hp.get("profile_steps", 56)))
        cz = hp["centre_z"] * H
    else:
        seg, rings = (96, 64) if hp.get("outline") else (48, 24)  # body_generic/2: a denser head for the outline fit
        head = G.uv_sphere("_head", (0, hp["forward"] * H, hp["centre_z"] * H), 1.0, C, seg, rings,
                           (hp["half_width"] * H, hp["half_depth"] * H, hp["half_height"] * H))
        cz, hh = hp["centre_z"] * H, hp["half_height"] * H
        lhh = hp.get("lower_half_height", hp["half_height"]) * H  # optional head-shape options (defaults: unchanged)
        nx, ny = float(hp.get("lower_roundness", 2.0)), float(hp.get("lower_depth_roundness", 2.0))
        fy0 = hp["forward"] * H
        for v in head.data.vertices:  # rounder cranium, tapered jaw
            if v.co.z < cz and lhh != hh:
                v.co.z = cz + (v.co.z - cz) * lhh / hh
            t = max(0.0, (cz - v.co.z) / (lhh if v.co.z < cz else hh))
            if t > 0 and (nx != 2.0 or ny != 2.0):
                v.co.x *= _superellipse_gain(t, nx)
                v.co.y = fy0 + (v.co.y - fy0) * _superellipse_gain(t, ny)
            k = 1 - hp["chin_taper"] * t * t
            v.co.x *= k
            v.co.y = fy0 + (v.co.y - fy0) * k
    if hp.get("outline"):  # body_generic/2 head: lower face fitted to the reference outlines (absent = unchanged)
        fit_head_outline(head, hp["outline"], H)
    nr = P["neck"]["radius"] * H
    ntr = P["neck"].get("top_radius", P["neck"]["radius"]) * H
    tip = ntr * 0.5 if hp.get("outline") else ntr  # body_generic/2: the neck narrows inside the fitted head, so it
    # does not show through the receded jaw and chin
    neck = G.tube("_neck", [Vector((0, 0, P["neck"]["base_z"] * H)), Vector((0, 0, P["neck"]["top_z"] * H)),
                            Vector((0, hp["forward"] * H * 0.5, cz))], [nr, ntr, tip], [nr, ntr, tip], C,
                  up_hint=(0, -1, 0))
    rings = [G.superellipse_ring(0, 0, z * H, w * H, f * H, b * H, 2.4, 48) for z, w, f, b in P["torso"]["levels"]]
    torso = G.loft("_torso", rings, C)
    parts = [head, neck, torso]
    r = P["arm"]["radii"]
    for sx, s in SIDES:
        S, E, W = J[f"shoulder.{s}"], J[f"elbow.{s}"], J[f"wrist.{s}"]
        rr = [x * H for x in r]
        parts.append(G.tube(f"_arm.{s}", [S, E, W], rr, rr, C, up_hint=(0, -1, 0)))
        lr = [x * H for x in P["leg"]["radii"]]
        parts.append(G.tube(f"_leg.{s}", [J[f"hip.{s}"], J[f"knee.{s}"], J[f"ankle.{s}"]], lr, lr, C, up_hint=(0, -1, 0)))
        fl, fw, fh = P["foot"]["length"] * H, P["foot"]["half_width"] * H, P["foot"]["height"] * H
        a = J[f"ankle.{s}"]
        parts.append(G.uv_sphere(f"_foot.{s}", (a.x, -0.3 * fl, 0.5 * fh), 1.0, C, 32, 16, (fw, 0.6 * fl, 0.5 * fh)))
    skin = G.join(parts, "body_skin")
    G.voxel_remesh(skin, P.get("voxel", 0.004) * H, smooth_iter=4)
    G.assign(skin, M["skin"])
    out = [(skin, "skin")]
    hpp = P["hand"]
    for sx, s in SIDES:
        F = frames[s]
        d, pn, sv = F["d"], F["palm_n"], F["side_v"]
        centre = J[f"wrist.{s}"] + d * 0.5 * hpp["palm_len"] * H
        palm = G.uv_sphere(f"_palm.{s}", centre, 1.0, C, 24, 12, (1, 1, 1))
        Rm = Matrix((sv, pn, d)).transposed()
        for v in palm.data.vertices:  # oriented soft box: across, thickness, along
            loc = v.co - centre
            v.co = centre + Rm @ Vector((loc.x * hpp["palm_half_width"] * H, loc.y * hpp["palm_half_thick"] * H,
                                         loc.z * 0.6 * hpp["palm_len"] * H))
        pieces = [palm]
        fr = hpp["finger_radius"] * H
        for name, (pr, root, tip) in F["fingers"].items():
            pieces.append(G.tube(f"_{name}.{s}", [root - d * 0.3 * fr, (root + tip) / 2, tip], [fr, fr * 0.97, fr * 0.9],
                                 [fr * 0.95, fr * 0.92, fr * 0.86], C, up_hint=tuple(pn)))
        tr = hpp["thumb_radius"] * H
        t0, troot, ttip = F["thumb"]
        pieces.append(G.tube(f"_thumb.{s}", [t0, troot, ttip], [tr * 1.1, tr, tr * 0.9], [tr, tr * 0.95, tr * 0.85], C,
                             up_hint=tuple(pn)))
        hand = G.join(pieces, f"hand.{s}")
        G.voxel_remesh(hand, hpp["finger_radius"] * H * 0.45, smooth_iter=4)
        G.assign(hand, M["skin"])
        out.append((hand, "hand"))
    return out


def fit_metarig_from_joints(meta, J, frames, P, H, profile):
    """Generic replacement for the legacy fit_metarig: every bone from the joint set via the rig profile (data)."""
    bpy.context.view_layer.objects.active = meta
    bpy.ops.object.mode_set(mode="EDIT")
    eb = meta.data.edit_bones
    for name in profile.get("remove", []):
        b = eb.get(name)
        if b is not None:
            for c in [b] + list(b.children_recursive):
                eb.remove(c)

    def put(name, h, t):
        b = eb[name]
        b.head, b.tail = Vector(h), Vector(t)
    for bone, (jh, jt) in profile["bones"].items():
        for sx, s in SIDES if "{s}" in bone else ((0, ""),):
            put(bone.format(s=s), J[jh.format(s=s)], J[jt.format(s=s)])
    for sx, s in SIDES:
        F = frames[s]
        for palm, fing in profile["fingers"].items():
            pr, root, tip = F["fingers"][fing]
            put(f"{palm}.{s}", pr, root)
            put(f"{fing}.01.{s}", root, root + (tip - root) * 0.40)
            put(f"{fing}.02.{s}", root + (tip - root) * 0.40, root + (tip - root) * 0.72)
            put(f"{fing}.03.{s}", root + (tip - root) * 0.72, tip)
        t0, troot, ttip = F["thumb"]
        put(f"thumb.01.{s}", t0, troot)
        put(f"thumb.02.{s}", troot, troot + (ttip - troot) * 0.5)
        put(f"thumb.03.{s}", troot + (ttip - troot) * 0.5, ttip)
        if profile.get("eye_bones"):
            e = eb.new(f"eye.{s}")
            e.head = Vector((sx * P["eyes"]["x"] * H, P["eyes"]["y"] * H, P["eyes"]["z"] * H))
            e.tail = e.head + Vector((0, -0.03 * H, 0))
            e.parent = eb["spine.006"]
    bpy.ops.object.mode_set(mode="OBJECT")
    if profile.get("eye_bones"):
        for s in ("L", "R"):
            pb = meta.pose.bones[f"eye.{s}"]
            pb.rigify_type = "basic.super_copy"
            try:
                pb.rigify_parameters.make_deform = True
            except AttributeError:
                pass


def rule_predicate(rule, part_name):
    """Allowed-bone test from a spec rule (by role): allow_prefixes, deny_prefixes, sided (same side as the part)."""
    if not rule:
        return None
    side = part_name.rsplit(".", 1)[-1] if part_name.endswith((".L", ".R")) else None
    allow, deny = tuple(rule.get("allow_prefixes", ())), tuple(rule.get("deny_prefixes", ()))

    def ok(b):
        if allow and not b.startswith(allow):
            return False
        if deny and b.startswith(deny):
            return False
        if rule.get("sided") and side and b[-2:] in (".L", ".R") and not b.endswith(side):
            return False
        return True
    return ok


def rig_generic(C, rig_name, parts, P, H, J, frames, rules, B, smooth=None):
    """Rigify rig fitted from the joint set, then heat weights filtered by the role rules, the legacy cleanup
    (nearest weighted neighbour fill, 4 influences, normalise) and the nearest-bone fallback. B = the module with the
    generic weight helpers cleanup_weights / bind_to_nearest_bone (body_helpers; identical copies of body_v6's)."""
    import time

    import addon_utils
    addon_utils.enable("rigify", default_set=True)
    profile = json.load(open(os.path.join(HERE, "rig_profiles", "rigify_human_metarig.json")))
    bpy.ops.object.armature_human_metarig_add()
    meta = bpy.context.object
    meta.name = "metarig"
    fit_metarig_from_joints(meta, J, frames, P, H, profile)
    t = time.time()
    bpy.ops.pose.rigify_generate()
    rig = bpy.context.object
    rig.name = rig_name
    for coll in list(rig.users_collection):
        coll.objects.unlink(rig)
    C.objects.link(rig)
    rules = {**profile.get("default_weight_rules", {}), **(rules or {})}  # profile defaults, spec per role on top
    report = {"rigify_bones": len(rig.data.bones), "deform_bones": sum(1 for b in rig.data.bones if b.use_deform),
              "generate_s": round(time.time() - t, 1), "fit_profile": profile["profile"]}
    bpy.data.objects.remove(meta, do_unlink=True)
    unweighted_before = unweighted_after = total = 0
    fallback = []
    for ob, role in parts:
        bpy.ops.object.select_all(action="DESELECT")
        ob.select_set(True)
        rig.select_set(True)
        bpy.context.view_layer.objects.active = rig
        bpy.ops.object.parent_set(type="ARMATURE_AUTO")
        allowed = rule_predicate(rules.get(role), ob.name)
        if allowed:
            for vg in list(ob.vertex_groups):
                if not allowed(vg.name):
                    ob.vertex_groups.remove(vg)
        ub, ua = B.cleanup_weights(ob)
        if ua:
            ua = B.bind_to_nearest_bone(ob, rig, allowed)
            fallback.append(ob.name)
        sm = (smooth or {}).get(role)
        if sm:  # optional per-role weight smoothing (spec.rig.weight_smooth), then the 4-influence limit again
            bpy.ops.object.select_all(action="DESELECT")
            ob.select_set(True)
            bpy.context.view_layer.objects.active = ob
            bpy.ops.object.mode_set(mode="WEIGHT_PAINT")  # the smoothing operator needs weight-paint mode
            bpy.ops.object.vertex_group_smooth(group_select_mode="ALL", factor=float(sm.get("factor", 0.5)), repeat=int(sm.get("repeat", 4)))
            bpy.ops.object.mode_set(mode="OBJECT")
            bpy.ops.object.vertex_group_limit_total(group_select_mode="ALL", limit=4)
            bpy.ops.object.vertex_group_normalize_all(group_select_mode="ALL", lock_active=False)
        unweighted_before += ub
        unweighted_after += ua
        total += len(ob.data.vertices)
    report.update({"weighted_objects": len(parts), "vertices": total, "unweighted_after_heat": unweighted_before,
                   "unweighted_after_cleanup": unweighted_after, "nearest_bone_fallback": fallback})
    return rig, report
