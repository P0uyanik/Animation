"""``garment/2`` pose correctives (T-093): shape keys that keep a torso garment on the torso when an arm reaches.

With nearest-body weight transfer, panel vertices near the armhole carry some upper-arm weight; when the arm swings
forward they are dragged forward with it and the panel flares off the chest (the vest flare in reach). For every side,
``correctives.reach`` adds the shape key ``corrective.reach.<side>`` to every piece of the item: for the configured
reach (a rotation of the arm chain about the shoulder joint) each vertex is pulled back to where the torso alone would
put it, by ``strength`` x a falloff of its arm weight: full below ``arm_lo``, fading towards 0 at ``arm_hi`` (an
``arm_hi`` above 1 keeps part of the correction even on vertices carried entirely by the arm, e.g. a vest panel whose
nearest skin is the arm root; 1 - smoothstep((1 - lo) / (hi - lo)) of the arm motion is then removed there). The delta is solved through the vertex's own linear-blend skinning matrix, so the
posed result is exact in the reach pose; the shared post-skinning collision still keeps the piece off the arm.

The key is driven by the arm's forward swing: a TRANSFORMS driver variable on the upper-arm deform bone in local
space (swing-twist about the bone's length axis, the swing channel the reach moves), mapped to 0 below ``gate`` x the
reach swing and 1 at the reach swing. A sideways swing (arms down, T-pose) moves the other channel and leaves the key
at 0. Rigid pieces on the item move with it unchanged (pockets, embroidery, buttons all get the same correction).

``correctives.arm_weights`` (T-093 round 2): {"cap": 0.3, "prefixes": [arm bone prefixes], "to": "DEF-shoulder.{side}"}
caps the arm bones' share of every vertex weight at ``cap`` before the reach keys are solved, so a sleeveless panel
is carried by the shoulder and torso, not by the arm, in every arm pose (the reach key then corrects the rest).

``correctives.reach.over`` (round 2): item names of the inner layer (e.g. ["blouse"]); in the reach pose the piece is
also kept outside that layer's posed main piece (``over_gap_m``, at most ``over_max_m`` of push), so the sleeve does
not show through the vest at the shoulder.

``correctives`` (item field of a top, shirt, vest, hoodie or dress):
  {"reach": {"deg": -75 (rotation of the arm about axis, degrees), "axis": [1, 0, 0] (world axis; the default swings
   the arm forward), "strength": 1.0, "arm_lo": 0.35, "arm_hi": 0.95, "gate": 0.3, "sides": ["L", "R"],
   "arm_bone": "DEF-upper_arm.{side}"}}
Character-agnostic: the bones come from the rig through the configured name pattern, the shoulder joint from the bone.
"""
import math

from mathutils import Matrix, Vector

from garments import generator as GEN

ARM_WEIGHTS = {"cap": 0.3, "prefixes": ["DEF-upper_arm", "DEF-forearm", "DEF-hand", "DEF-f_", "DEF-thumb", "DEF-palm"],
               "to": "DEF-shoulder.{side}"}
REACH = {"deg": -75.0, "axis": [1.0, 0.0, 0.0], "strength": 1.0, "arm_lo": 0.35, "arm_hi": 0.95, "gate": 0.3,
         "sides": ["L", "R"], "arm_bone": "DEF-upper_arm.{side}", "over": [], "over_gap_m": 0.003,
         "over_max_m": 0.03}
KEY = "corrective.reach.{side}"


def validate(v, name):
    if not isinstance(v, dict) or not v:
        raise ValueError(f"garment {name}.correctives must be a non-empty object")
    for kind, cfg in v.items():
        if kind not in ("reach", "arm_weights"):
            raise ValueError(f"garment {name}.correctives.{kind}: unknown corrective (known: ['arm_weights', 'reach'])")
        if not isinstance(cfg, dict):
            raise ValueError(f"garment {name}.correctives.{kind} must be an object")
        if kind == "arm_weights":
            for key in cfg:
                if key not in ARM_WEIGHTS:
                    raise ValueError(f"garment {name}.correctives.arm_weights.{key}: unknown field "
                                     f"(known: {sorted(ARM_WEIGHTS)})")
            if "cap" in cfg:
                GEN._number(cfg["cap"], f"garment {name}.correctives.arm_weights.cap", 0.0, 1.0)
            pre = cfg.get("prefixes", ARM_WEIGHTS["prefixes"])
            if not isinstance(pre, list) or not pre or any(not isinstance(x, str) or not x for x in pre):
                raise ValueError(f"garment {name}.correctives.arm_weights.prefixes must be a list of bone prefixes")
            if not isinstance(cfg.get("to", ARM_WEIGHTS["to"]), str) or "{side}" not in cfg.get("to", ARM_WEIGHTS["to"]):
                raise ValueError(f"garment {name}.correctives.arm_weights.to must contain '{{side}}'")
            continue
        for key in cfg:
            if key not in REACH:
                raise ValueError(f"garment {name}.correctives.reach.{key}: unknown field (known: {sorted(REACH)})")
        for key, lo, hi in (("deg", -150.0, 150.0), ("strength", 0.0, 1.5), ("arm_lo", 0.0, 1.0), ("arm_hi", 0.0, 3.0),
                            ("gate", 0.0, 0.95), ("over_gap_m", 0.0, 0.02), ("over_max_m", 0.001, 0.08)):
            if key in cfg:
                GEN._number(cfg[key], f"garment {name}.correctives.reach.{key}", lo, hi)
        s = dict(REACH, **cfg)
        if s["arm_hi"] <= s["arm_lo"]:
            raise ValueError(f"garment {name}.correctives.reach: arm_hi must be greater than arm_lo")
        ax = s["axis"]
        if (not isinstance(ax, list) or len(ax) != 3 or any(not isinstance(a, (int, float)) for a in ax)
                or Vector(ax).length < 1e-6):
            raise ValueError(f"garment {name}.correctives.reach.axis must be a non-zero [x, y, z]")
        if not isinstance(s["sides"], list) or not s["sides"] or any(x not in ("L", "R") for x in s["sides"]):
            raise ValueError(f"garment {name}.correctives.reach.sides must be a list of 'L' / 'R'")
        if not isinstance(s["over"], list) or any(not isinstance(x, str) for x in s["over"]):
            raise ValueError(f"garment {name}.correctives.reach.over must be a list of item names")
        if not isinstance(s["arm_bone"], str) or "{side}" not in s["arm_bone"]:
            raise ValueError(f"garment {name}.correctives.reach.arm_bone must contain '{{side}}'")


def _smooth(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def reach_rotation(rig, bone, s):
    """(world rotation matrix 3x3, world shoulder joint) of the reach of one side."""
    R = Matrix.Rotation(math.radians(float(s["deg"])), 3, Vector(s["axis"]).normalized())
    return R, rig.matrix_world @ bone.head_local


def swing_values(rig, bone, R):
    """Driver values (2 asin of the swing quaternion's x and z, what a SWING_TWIST_Y TRANSFORMS variable reads in
    LOCAL_SPACE) of the bone rotated by the world rotation R about its head, its parent unchanged."""
    M = (rig.matrix_world.to_3x3() @ bone.matrix_local.to_3x3()).normalized()
    q = (M.inverted() @ R @ M).to_quaternion()
    sw, _ = q.to_swing_twist("Y")
    if sw.w < 0:
        sw = -sw
    return 2.0 * math.asin(max(-1.0, min(1.0, sw.x))), 2.0 * math.asin(max(-1.0, min(1.0, sw.z)))


def arm_weight_share(ob, arm_names):
    """Per vertex: the share of its deform weight carried by the bones in ``arm_names``."""
    names = {g.index: g.name for g in ob.vertex_groups}
    out = []
    for v in ob.data.vertices:
        tot = arm = 0.0
        for g in v.groups:
            n = names.get(g.group, "")
            if n.startswith("ps_") or g.weight <= 0:
                continue
            tot += g.weight
            if n in arm_names:
                arm += g.weight
        out.append(arm / tot if tot > 0 else 0.0)
    return out


def solve_deltas(ob, share, R, joint, s, layer=None):
    """Object-space shape key deltas of one side (see the module docstring) and the largest posed correction.
    ``layer`` = (BVH of the posed inner layer, gap, max push): in the reach pose, vertices that would lie inside the
    inner layer (or closer than gap) are moved back out over it."""
    mw = ob.matrix_world
    inv3 = mw.to_3x3().inverted()
    lo, hi, strength = float(s["arm_lo"]), float(s["arm_hi"]), float(s["strength"])
    deltas, biggest = [], 0.0
    I = Matrix.Identity(3)
    for v, wa in zip(ob.data.vertices, share):
        p = mw @ v.co
        posed = p + wa * ((R @ (p - joint) + joint) - p)
        k = strength * (1.0 - _smooth((wa - lo) / (hi - lo))) if wa > 1e-4 else 0.0
        target = posed + k * (p - posed)
        if layer is not None:
            bvh, gap, cap = layer
            loc, nrm, _, _ = bvh.find_nearest(target, cap + gap)
            if loc is not None:
                nrm = nrm.normalized()
                side = (target - loc).dot(nrm)
                if side < gap and gap - side <= cap:
                    target = target + nrm * (gap - side)
        want = target - posed
        if want.length < 1e-7:
            deltas.append(None)
            continue
        M = I * (1.0 - wa) + R * wa
        try:
            d = M.inverted() @ want
        except ValueError:
            deltas.append(None)
            continue
        deltas.append(inv3 @ d)
        biggest = max(biggest, want.length)
    return deltas, biggest


def _skin_linear(ob, share, R):
    """Per vertex: the linear part of its skinning in the analytic reach (arm chain rotated by R)."""
    I = Matrix.Identity(3)
    return [I * (1.0 - wa) + R * wa for wa in share]


def _pose_fk(rig, side, R, fk_bone):
    """Rotates one FK upper arm by the world rotation R about its head (IK/FK switched to FK). Returns a restore
    function that puts back the exact previous pose and switch values."""
    import bpy
    saved = {pb.name: (pb.matrix_basis.copy(), {k: pb[k] for k in pb.keys() if k == "IK_FK"}) for pb in rig.pose.bones}
    for pb in rig.pose.bones:
        if "IK_FK" in pb.keys():
            pb["IK_FK"] = 1.0
    pb = rig.pose.bones.get(fk_bone.format(side=side))
    if pb is None:
        raise ValueError(f"correctives.reach.over: rig has no {fk_bone.format(side=side)!r}")
    bpy.context.view_layer.update()
    hw = rig.matrix_world @ pb.head
    rm = Matrix.Translation(hw) @ R.to_4x4() @ Matrix.Translation(-hw)
    pb.matrix = rig.matrix_world.inverted() @ rm @ rig.matrix_world @ pb.matrix
    bpy.context.view_layer.update()

    def restore():
        for b in rig.pose.bones:
            mb, props = saved[b.name]
            b.matrix_basis = mb
            for k, v in props.items():
                b[k] = v
        bpy.context.view_layer.update()
    return restore


def _evaluated(ob):
    import bpy
    dg = bpy.context.evaluated_depsgraph_get()
    e = ob.evaluated_get(dg)
    m = e.to_mesh()
    pts = [e.matrix_world @ v.co for v in m.vertices]
    faces = [tuple(p.vertices) for p in m.polygons]
    e.to_mesh_clear()
    return pts, faces


def solve_layer_evaluated(rig, objects, inner, arm, R, side, s, keys):
    """Layer-order correction on the evaluated reach pose: with the side's FK arm rotated, vertices of ``objects``
    inside (or closer than ``over_gap_m`` to) the evaluated inner layer are pushed back out over it; the posed push is
    mapped to rest space through each vertex's skinning and accumulated on ``keys`` (ob -> shape key, value 1 while
    solving). Two passes (the second corrects the residual). Restores the rig. Returns the largest push."""
    from mathutils.bvhtree import BVHTree
    gap, cap = float(s["over_gap_m"]), float(s["over_max_m"])
    restore = _pose_fk(rig, side, R, s.get("fk_bone", "upper_arm_fk.{side}"))
    biggest = 0.0
    try:
        for _ in range(2):
            verts, faces = [], []
            for ob in inner:
                pts, fs = _evaluated(ob)
                base = len(verts)
                verts += pts
                faces += [tuple(base + i for i in f) for f in fs]
            bvh = BVHTree.FromPolygons(verts, faces, all_triangles=False)
            for ob in objects:
                key = keys.get(ob.name)
                if key is None:
                    continue
                pts, _ = _evaluated(ob)
                if len(pts) != len(ob.data.vertices):
                    continue
                Ms = _skin_linear(ob, arm_weight_share(ob, arm), R)
                inv3 = ob.matrix_world.to_3x3().inverted()
                for i, p in enumerate(pts):
                    loc, nrm, _, _ = bvh.find_nearest(p, cap + gap)
                    if loc is None:
                        continue
                    nrm = nrm.normalized()
                    side_d = (p - loc).dot(nrm)
                    if side_d < gap and gap - side_d <= cap:
                        push = nrm * (gap - side_d)
                        try:
                            d = inv3 @ (Ms[i].inverted() @ push)
                        except ValueError:
                            continue
                        key.data[i].co = key.data[i].co + d
                        biggest = max(biggest, push.length)
                ob.data.update()
    finally:
        restore()
    return biggest


def posed_layer(objects, arm, R, joint, parts=("main",)):
    """BVH of the listed pieces (inner layer) in the reach pose of one side: linear-blend skinning of the arm chain
    ``arm`` rotated by R about the joint, every other bone at rest."""
    from mathutils.bvhtree import BVHTree
    verts, faces = [], []
    for ob in objects:
        if ob.type != "MESH" or ob.get("ps_garment_part") not in parts:
            continue
        share = arm_weight_share(ob, arm)
        mw = ob.matrix_world
        base = len(verts)
        for v, wa in zip(ob.data.vertices, share):
            p = mw @ v.co
            verts.append(p + wa * ((R @ (p - joint) + joint) - p))
        faces += [tuple(base + i for i in poly.vertices) for poly in ob.data.polygons]
    return BVHTree.FromPolygons(verts, faces, all_triangles=False) if faces else None


def _drive(key, rig, bone_name, channel, sign, lo, hi):
    key.driver_remove("value")
    d = key.driver_add("value").driver
    d.type = "SCRIPTED"
    var = d.variables.new()
    var.name = "swing"
    var.type = "TRANSFORMS"
    t = var.targets[0]
    t.id = rig
    t.bone_target = bone_name
    t.transform_type = channel
    t.rotation_mode = "SWING_TWIST_Y"
    t.transform_space = "LOCAL_SPACE"
    d.expression = f"min(max(({sign:+.1f} * swing - {lo:.5f}) / {hi - lo:.5f}, 0.0), 1.0)"
    return d.expression


def cap_arm_weights(rig, objects, raw, max_influences=4):
    """Caps the arm bones' share of every vertex's weight at ``cap`` (a sleeveless torso garment should not be carried
    by the arm); the rest goes to the vertex's other bones, or to ``to`` (the side's shoulder bone) when it has none.
    Keeps at most ``max_influences`` influences, normalized. Returns a JSON-safe report."""
    s = dict(ARM_WEIGHTS, **raw)
    cap, prefixes = float(s["cap"]), tuple(s["prefixes"])
    capped, total = 0, 0
    for ob in objects:
        if ob.type != "MESH":
            continue
        names = {g.index: g.name for g in ob.vertex_groups}
        groups = {g.name: g for g in ob.vertex_groups}
        mw = ob.matrix_world
        for v in ob.data.vertices:
            ws = {names[g.group]: g.weight for g in v.groups if not names[g.group].startswith("ps_") and g.weight > 0}
            tot = sum(ws.values())
            if tot <= 0:
                continue
            total += 1
            arm = {k: w for k, w in ws.items() if k.startswith(prefixes)}
            a = sum(arm.values()) / tot
            if a <= cap + 1e-6:
                continue
            rest = {k: w for k, w in ws.items() if k not in arm}
            if not rest:
                side = "L" if (mw @ v.co).x >= 0 else "R"
                target = s["to"].format(side=side)
                if target not in groups or rig.data.bones.get(target) is None:
                    raise ValueError(f"correctives.arm_weights: no bone/group {target!r}")
                rest = {target: 1.0}
            ra = sum(arm.values())
            rr = sum(rest.values())
            new = {k: cap * w / ra for k, w in arm.items()}
            for k, w in rest.items():
                new[k] = new.get(k, 0.0) + (1.0 - cap) * w / rr
            keep = sorted(new.items(), key=lambda kv: -kv[1])[:max_influences]
            norm = sum(w for _, w in keep)
            for k in ws:
                groups[k].remove([v.index])
            for k, w in keep:
                groups[k].add([v.index], w / norm, "REPLACE")
            capped += 1
    return {"cap": cap, "vertices_capped": capped, "vertices": total}


def add(rig, objects, cfg, max_influences=4, others=()):
    """Adds the item's correctives: first the arm-weight cap (if any), then the reach shape keys (solved on the
    capped weights). Returns a JSON-safe report."""
    report = {}
    if "arm_weights" in cfg:
        report["arm_weights"] = cap_arm_weights(rig, objects, cfg["arm_weights"], max_influences)
    for kind, raw in sorted(cfg.items()):
        if kind != "reach":
            continue
        s = dict(REACH, **raw)
        sides = {}
        for side in s["sides"]:
            bone = rig.data.bones.get(s["arm_bone"].format(side=side))
            if bone is None:
                raise ValueError(f"correctives.{kind}: rig has no bone {s['arm_bone'].format(side=side)!r}")
            arm = {bone.name} | {b.name for b in bone.children_recursive}
            R, joint = reach_rotation(rig, bone, s)
            vx, vz = swing_values(rig, bone, R)
            channel, value = ("ROT_X", vx) if abs(vx) >= abs(vz) else ("ROT_Z", vz)
            sign = 1.0 if value >= 0 else -1.0
            lo, hi = float(s["gate"]) * abs(value), abs(value)
            # sideways check: the compare-variant arms-down rotation (about world Y) seen on the chosen channel
            down = Matrix.Rotation(math.radians(35.0 if side == "L" else -35.0), 3, "Y")
            dvx, dvz = swing_values(rig, bone, down)
            down_v = sign * (dvx if channel == "ROT_X" else dvz)
            keyed, biggest, verts = [], 0.0, 0
            inner = [o for o in others if o.get("ps_garment_item") in set(s["over"]) and o.type == "MESH"
                     and o.get("ps_garment_part") == "main"]
            keys = {}
            for ob in sorted(objects, key=lambda o: o.name):
                if ob.type != "MESH":
                    continue
                share = arm_weight_share(ob, arm)
                deltas, big = solve_deltas(ob, share, R, joint, s)
                if not any(d is not None for d in deltas) and not inner:
                    continue
                if ob.data.shape_keys is None:
                    ob.shape_key_add(name="Basis", from_mix=False)
                key = ob.shape_key_add(name=KEY.format(side=side), from_mix=False)
                n = 0
                for i, d in enumerate(deltas):
                    if d is not None:
                        key.data[i].co = ob.data.vertices[i].co + d
                        n += 1
                key.slider_min, key.slider_max = 0.0, 1.0
                keys[ob.name] = key
                biggest, verts = max(biggest, big), verts + n
            layer_push = 0.0
            if inner and keys:
                for k in keys.values():
                    k.value = 1.0
                layer_push = solve_layer_evaluated(rig, [o for o in objects if o.name in keys], inner, arm, R, side,
                                                   s, keys)
            expr = None
            for name_, key in sorted(keys.items()):
                ob = next(o for o in objects if o.name == name_)
                basis = ob.data.shape_keys.key_blocks[0]
                if all((a.co - b.co).length < 1e-7 for a, b in zip(key.data, basis.data)):
                    ob.shape_key_remove(key)  # nothing to correct on this piece
                    if len(ob.data.shape_keys.key_blocks) == 1:
                        ob.shape_key_clear()
                    continue
                expr = _drive(key, rig, bone.name, channel, sign, lo, hi)
                keyed.append(ob.name)
            sides[side] = {"bone": bone.name, "channel": channel, "reach_swing_rad": round(value, 5),
                           "gate_rad": round(lo, 5), "arms_down_swing_rad": round(down_v, 5),
                           "arms_down_value": round(min(max((down_v - lo) / (hi - lo), 0.0), 1.0), 4),
                           "objects": keyed, "vertices": verts, "max_correction_m": round(biggest, 5),
                           "layer_over": sorted({o.get("ps_garment_item") for o in inner}) if inner else [],
                           "max_layer_push_m": round(layer_push, 5),
                           "expression": expr if keyed else None}
        report[kind] = {"deg": float(s["deg"]), "axis": list(s["axis"]), "strength": float(s["strength"]),
                        "sides": sides}
    return report
