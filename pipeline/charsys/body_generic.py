"""charsys generic body generator (`body_generic/1`): body mesh, joint set, metarig fitting and skinning for any
humanoid character, entirely from its spec. No character's dimensions live in this module.

Spec (`spec.body`): {"generator": "body_generic/1", "height_m": <sole to top of skull>, "params": {...}} with every
length a FRACTION OF height_m (angles in degrees):
  head:     centre_z, half_width, half_depth, half_height, chin_taper (0..1), forward
  neck:     base_z, top_z, radius
  torso:    levels: [[z, half_width, half_depth_front, half_depth_back], ...]  (bottom to top)
  shoulder: z, joint_x, clavicle_x
  arm:      angle_deg (below horizontal), upper_len, fore_len, radii [shoulder, elbow, wrist]
  hand:     palm_len, palm_half_width, palm_half_thick, finger_len [index, middle, ring, pinky], finger_radius,
            thumb_len, thumb_radius, finger_curl (0..0.4)
  leg:      hip_x, hip_z, knee_z, ankle_z, radii [thigh, knee, ankle]
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
        J[f"knee.{s}"] = Vector((hx, -0.004 * H, P["leg"]["knee_z"] * H))
        J[f"ankle.{s}"] = Vector((hx, 0, P["leg"]["ankle_z"] * H))
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


def build_body(C, M, P, H, J, frames):
    """Body skin (head, neck, torso, arms, legs, feet; one remeshed surface) and the two hands. Returns
    [(object, role)] with roles 'skin' and 'hand'."""
    hp = P["head"]
    head = G.uv_sphere("_head", (0, hp["forward"] * H, hp["centre_z"] * H), 1.0, C, 48, 24,
                       (hp["half_width"] * H, hp["half_depth"] * H, hp["half_height"] * H))
    cz, hh = hp["centre_z"] * H, hp["half_height"] * H
    for v in head.data.vertices:  # rounder cranium, tapered jaw
        t = max(0.0, (cz - v.co.z) / hh)
        k = 1 - hp["chin_taper"] * t * t
        v.co.x *= k
        v.co.y = hp["forward"] * H + (v.co.y - hp["forward"] * H) * k
    neck = G.tube("_neck", [Vector((0, 0, P["neck"]["base_z"] * H)), Vector((0, 0, P["neck"]["top_z"] * H)),
                            Vector((0, hp["forward"] * H * 0.5, cz))], [P["neck"]["radius"] * H] * 3,
                  [P["neck"]["radius"] * H] * 3, C, up_hint=(0, -1, 0))
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
    (nearest weighted neighbour fill, 4 influences, normalise) and the nearest-bone fallback. B = body_v6 module
    (only its generic weight helpers are used)."""
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
