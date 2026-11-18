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

``correctives`` (item field of a top, shirt, vest, hoodie or dress):
  {"reach": {"deg": -75 (rotation of the arm about axis, degrees), "axis": [1, 0, 0] (world axis; the default swings
   the arm forward), "strength": 1.0, "arm_lo": 0.35, "arm_hi": 0.95, "gate": 0.3, "sides": ["L", "R"],
   "arm_bone": "DEF-upper_arm.{side}"}}
Character-agnostic: the bones come from the rig through the configured name pattern, the shoulder joint from the bone.
"""
import math

from mathutils import Matrix, Vector

from garments import generator as GEN

REACH = {"deg": -75.0, "axis": [1.0, 0.0, 0.0], "strength": 1.0, "arm_lo": 0.35, "arm_hi": 0.95, "gate": 0.3,
         "sides": ["L", "R"], "arm_bone": "DEF-upper_arm.{side}"}
KEY = "corrective.reach.{side}"


def validate(v, name):
    if not isinstance(v, dict) or not v:
        raise ValueError(f"garment {name}.correctives must be a non-empty object")
    for kind, cfg in v.items():
        if kind != "reach":
            raise ValueError(f"garment {name}.correctives.{kind}: unknown corrective (known: ['reach'])")
        if not isinstance(cfg, dict):
            raise ValueError(f"garment {name}.correctives.reach must be an object")
        for key in cfg:
            if key not in REACH:
                raise ValueError(f"garment {name}.correctives.reach.{key}: unknown field (known: {sorted(REACH)})")
        for key, lo, hi in (("deg", -150.0, 150.0), ("strength", 0.0, 1.5), ("arm_lo", 0.0, 1.0), ("arm_hi", 0.0, 3.0),
                            ("gate", 0.0, 0.95)):
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


def solve_deltas(ob, share, R, joint, s):
    """Object-space shape key deltas of one side (see the module docstring) and the largest posed correction."""
    mw = ob.matrix_world
    inv3 = mw.to_3x3().inverted()
    lo, hi, strength = float(s["arm_lo"]), float(s["arm_hi"]), float(s["strength"])
    deltas, biggest = [], 0.0
    I = Matrix.Identity(3)
    for v, wa in zip(ob.data.vertices, share):
        if wa <= 1e-4:
            deltas.append(None)
            continue
        k = strength * (1.0 - _smooth((wa - lo) / (hi - lo)))
        if k <= 0:
            deltas.append(None)
            continue
        p = mw @ v.co
        posed = p + wa * ((R @ (p - joint) + joint) - p)
        want = k * (p - posed)
        M = I * (1.0 - wa) + R * wa
        try:
            d = M.inverted() @ want
        except ValueError:
            deltas.append(None)
            continue
        deltas.append(inv3 @ d)
        biggest = max(biggest, want.length)
    return deltas, biggest


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


def add(rig, objects, cfg):
    """Adds the reach correctives to the item's pieces. Returns a JSON-safe report."""
    report = {}
    for kind, raw in sorted(cfg.items()):
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
            for ob in sorted(objects, key=lambda o: o.name):
                if ob.type != "MESH":
                    continue
                share = arm_weight_share(ob, arm)
                deltas, big = solve_deltas(ob, share, R, joint, s)
                if not any(d is not None for d in deltas):
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
                expr = _drive(key, rig, bone.name, channel, sign, lo, hi)
                keyed.append(ob.name)
                biggest, verts = max(biggest, big), verts + n
            sides[side] = {"bone": bone.name, "channel": channel, "reach_swing_rad": round(value, 5),
                           "gate_rad": round(lo, 5), "arms_down_swing_rad": round(down_v, 5),
                           "arms_down_value": round(min(max((down_v - lo) / (hi - lo), 0.0), 1.0), 4),
                           "objects": keyed, "vertices": verts, "max_correction_m": round(biggest, 5),
                           "expression": expr if keyed else None}
        report[kind] = {"deg": float(s["deg"]), "axis": list(s["axis"]), "strength": float(s["strength"]),
                        "sides": sides}
    return report
