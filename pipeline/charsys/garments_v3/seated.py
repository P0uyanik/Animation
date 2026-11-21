"""``garment/3`` ``seated`` (``shorts`` / ``trousers``, T-184): the item stays over the legs when the hips bend
(sitting, a walk's forward swing).

Two faults of the ``garment/1`` binding show at a deep hip bend; ``seated`` corrects both at bind time, after the
``garment/2`` binding. Without the field nothing here runs and the item is bound exactly as before.

``leg_weights``: a shell vertex is bound with the weights of the body vertex it was extruded from. Puff, leg split,
cuff gather and drape then move it, so part of a leg tube ends up over the thigh while it is still carried by the
pelvis: it stays behind when the thigh bends and the thigh comes through it. Every vertex of the item's shell pieces
(the pieces that carry their source vertex; bands, gussets and rigid pieces keep their weights) takes the weights of
the skin under it instead: the nearest point of the body surface, looked for on its own side's leg and on the skin
carried by the bones the item already uses (never the other leg, an arm or a hand). The new weights are blended in
  - by how much of that skin is carried by the thigh or by a bone above the leg (hems and shins keep their weights:
    a hem that rests on a shoe must not turn with the foot), and
  - from 0 at the centre plane to 1 at ``centre_m`` from it, so the crotch seam stays in one piece when the legs
    move apart.

``collision``: the ``garment/1`` post-skinning collision (shrinkwrap to the outside of the posed body) is weighted by
the rest distance to visible skin, so a front panel far from bare skin at rest is not corrected when a bare thigh is
bent up through it. With both thighs bent forward by each of ``hip_deg`` (FK, about the rig's side axis), a vertex
within ``radius_m`` of visible skin gets full collision weight, fading to none over ``falloff_m``; the larger of this
and the rest weight is kept. No modifier, shape key or driver is added. The weights are rebuilt by the ``garment/1``
rule whenever the worn items are switched (``set_active_items``); ``bind`` must then be run again.

  {"leg_weights": {"centre_m": 0.012}, "collision": {"hip_deg": [45, 90, 110], "radius_m": 0.03, "falloff_m": 0.03},
   "leg_bone": "DEF-thigh.{side}", "fk_bone": "thigh_fk.{side}"}
``true`` is the block above; ``"leg_weights": false`` or ``"collision": false`` switches one part off.
The engine package carries the weights (``leg_weights``); the collision is a Blender modifier and is not exported.
Character-agnostic: bones by configured name, sides by the rig's X axis, everything else from the body and the rig."""
import math

from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
from mathutils.interpolate import poly_3d_calc

from garments import generator as GEN
from garments_v2 import correctives as CORR

SEATED = {"leg_weights": True, "collision": True, "leg_bone": "DEF-thigh.{side}", "fk_bone": "thigh_fk.{side}"}
LEG_WEIGHTS = {"centre_m": 0.012}
COLLISION = {"hip_deg": [45.0, 90.0, 110.0], "radius_m": 0.03, "falloff_m": 0.03}
RANGES = {"centre_m": (0.0, 0.05), "radius_m": (0.0, 0.15), "falloff_m": (0.001, 0.15)}
SOURCE_ATTR = "ps_body_vertex"  # garment/1: the body vertex a shell vertex was extruded from
REPORT_PROP = "ps_garment3_seated"
MIN_CHANGE = 0.01  # a vertex whose weights would change by less than this share keeps its weights untouched


def validate(v, name):
    if v is True:
        return
    if not isinstance(v, dict):
        raise ValueError(f"garment {name}.seated must be true or an object")
    for key in v:
        if key not in SEATED:
            raise ValueError(f"garment {name}.seated.{key}: unknown field (known: {sorted(SEATED)})")
    for key in ("leg_bone", "fk_bone"):
        if key in v and (not isinstance(v[key], str) or "{side}" not in v[key]):
            raise ValueError(f"garment {name}.seated.{key} must contain '{{side}}'")
    for part, known in (("leg_weights", LEG_WEIGHTS), ("collision", COLLISION)):
        cfg = v.get(part, True)
        if isinstance(cfg, bool):
            continue
        if not isinstance(cfg, dict):
            raise ValueError(f"garment {name}.seated.{part} must be true, false or an object")
        for key in cfg:
            if key not in known:
                raise ValueError(f"garment {name}.seated.{part}.{key}: unknown field (known: {sorted(known)})")
            if key in RANGES:
                GEN._number(cfg[key], f"garment {name}.seated.{part}.{key}", *RANGES[key])
        if "hip_deg" in cfg:
            degs = cfg["hip_deg"]
            if not isinstance(degs, list) or not degs or len(degs) > 8:
                raise ValueError(f"garment {name}.seated.collision.hip_deg must be a list of 1 to 8 angles")
            for d in degs:
                GEN._number(d, f"garment {name}.seated.collision.hip_deg", 5.0, 150.0)
    if v.get("leg_weights", True) is False and v.get("collision", True) is False:
        raise ValueError(f"garment {name}.seated: leg_weights and collision are both off")


def settings(raw):
    st = dict(SEATED, **(raw if isinstance(raw, dict) else {}))
    for part, defaults in (("leg_weights", LEG_WEIGHTS), ("collision", COLLISION)):
        cfg = st[part]
        st[part] = None if cfg is False else dict(defaults, **(cfg if isinstance(cfg, dict) else {}))
    return st


def _smooth(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def _deform_weights(ob):
    """Per vertex {bone name: weight} of an object's deform groups (no ``ps_`` groups)."""
    names = {g.index: g.name for g in ob.vertex_groups if not g.name.startswith("ps_")}
    return [{names[g.group]: g.weight for g in v.groups if g.group in names and g.weight > 0} for v in ob.data.vertices]


def _legs(rig, st, name):
    """Per side: (bones of the leg chain, the thigh's own segments)."""
    out = {}
    for side in ("L", "R"):
        bone = rig.data.bones.get(st["leg_bone"].format(side=side))
        if bone is None:
            raise ValueError(f"garment {name}.seated: rig has no bone {st['leg_bone'].format(side=side)!r}")
        chain = {bone.name} | {b.name for b in bone.children_recursive}
        out[side] = (chain, {b for b in chain if b.startswith(bone.name)})
    return out


def follow_skin(rig, body, pieces, st, name, max_influences=4):
    """``leg_weights``: see the module docstring. Returns a JSON-safe report."""
    cfg = st["leg_weights"]
    centre = float(cfg["centre_m"])
    legs = _legs(rig, st, name)
    skin = _deform_weights(body)
    dominant = [max(sorted(w), key=w.get) if w else None for w in skin]
    shells = [(ob, _deform_weights(ob)) for ob in pieces if ob.data.attributes.get(SOURCE_ATTR) is not None]
    used = {b for _, ws in shells for w in ws for b in w}
    points = [body.matrix_world @ v.co for v in body.data.vertices]
    faces, bvh = {}, {}
    for side, other in (("L", "R"), ("R", "L")):
        allowed = (used - legs[other][0]) | legs[side][0]
        faces[side] = [p for p in body.data.polygons if all(dominant[i] in allowed for i in p.vertices)]
        bvh[side] = BVHTree.FromPolygons(points, [tuple(p.vertices) for p in faces[side]]) if faces[side] else None
    to_rig = rig.matrix_world.inverted()
    per_object, total, changed, biggest = {}, 0, 0, 0.0
    for ob, weights in shells:
        groups = {g.name: g for g in ob.vertex_groups}
        n = 0
        for v, old in zip(ob.data.vertices, weights):
            old_total = sum(old.values())
            if old_total <= 0:
                continue
            total += 1
            p = ob.matrix_world @ v.co
            x = (to_rig @ p).x
            side = "L" if x >= 0 else "R"
            if bvh[side] is None:
                continue
            loc, _, fi, _ = bvh[side].find_nearest(p)
            if loc is None:
                continue
            poly = faces[side][fi]
            under = {}
            for share, i in zip(poly_3d_calc([points[k] for k in poly.vertices], loc), poly.vertices):
                for b, w in skin[i].items():
                    under[b] = under.get(b, 0.0) + share * w
            under_total = sum(under.values())
            if under_total <= 0:
                continue
            chain, thigh = legs[side]
            below = sum(w for b, w in under.items() if b in chain and b not in thigh) / under_total
            t = (1.0 - below) * (_smooth(abs(x) / centre) if centre > 0 else 1.0)
            if t <= 1e-4:
                continue
            mix = {b: (1.0 - t) * w / old_total for b, w in old.items()}
            for b, w in under.items():
                mix[b] = mix.get(b, 0.0) + t * w / under_total
            keep = sorted(mix.items(), key=lambda kv: (-kv[1], kv[0]))[:max_influences]
            norm = sum(w for _, w in keep)
            new = {b: w / norm for b, w in keep if w / norm > 1e-6}
            diff = 0.5 * sum(abs(new.get(b, 0.0) - old.get(b, 0.0) / old_total) for b in set(new) | set(old))
            if diff < MIN_CHANGE:
                continue
            for b in old:
                groups[b].remove([v.index])
            for b, w in sorted(new.items()):
                group = groups.get(b)
                if group is None:
                    group = groups[b] = ob.vertex_groups.new(name=b)
                group.add([v.index], w, "REPLACE")
            n += 1
            biggest = max(biggest, diff)
        per_object[ob.name] = n
        changed += n
    return {"centre_m": centre, "objects": per_object, "vertices": total, "vertices_changed": changed,
            "max_weight_change": round(biggest, 4)}


def _evaluated_points(ob):
    import bpy
    e = ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
    m = e.to_mesh()
    pts = [e.matrix_world @ v.co for v in m.vertices]
    e.to_mesh_clear()
    return pts


def sweep_collision(rig, body, pieces, st, name):
    """``collision``: see the module docstring. Returns a JSON-safe report."""
    import bpy
    cfg = st["collision"]
    radius, falloff = float(cfg["radius_m"]), max(float(cfg["falloff_m"]), 1e-9)
    targets = [ob for ob in pieces if ob.vertex_groups.get(GEN.COLLISION_GROUP) is not None
               and ob.modifiers.get(GEN.COLLISION_MODIFIER) is not None]
    proxy = next((m.target for ob in targets for m in ob.modifiers if m.type == "SHRINKWRAP" and m.target), None)
    report = {"hip_deg": [float(d) for d in cfg["hip_deg"]], "radius_m": radius, "falloff_m": falloff,
              "objects": {}, "vertices_raised": 0}
    if proxy is None:
        return report
    mask = body.vertex_groups.get(GEN.MASK_GROUP)
    hidden = set()
    if mask is not None:
        hidden = {v.index for v in body.data.vertices if any(g.group == mask.index and g.weight > 0 for g in v.groups)}
    visible = [tuple(p.vertices) for p in body.data.polygons if not any(i in hidden for i in p.vertices)]
    if not visible:
        return report
    wanted = {ob.name: [0.0] * len(ob.data.vertices) for ob in targets}
    off = [m for ob in targets for m in ob.modifiers if m.type == "SHRINKWRAP" and m.show_viewport]
    for m in off:
        m.show_viewport = False
    side_axis = (rig.matrix_world.to_3x3() @ Vector((1.0, 0.0, 0.0))).normalized()
    for side in ("L", "R"):
        if rig.pose.bones.get(st["fk_bone"].format(side=side)) is None:
            raise ValueError(f"garment {name}.seated.collision: rig has no {st['fk_bone'].format(side=side)!r}")
    try:
        for deg in cfg["hip_deg"]:
            R = Matrix.Rotation(math.radians(-float(deg)), 3, side_axis)  # the rig faces -Y: this bends forward
            restore = [CORR._pose_fk(rig, side, R, st["fk_bone"]) for side in ("L", "R")]
            try:
                skin = _evaluated_points(proxy)
                if len(skin) != len(body.data.vertices):
                    raise ValueError(f"garment {name}.seated.collision: the collision body changes its vertex count")
                bvh = BVHTree.FromPolygons(skin, visible)
                for ob in targets:
                    pts = _evaluated_points(ob)
                    if len(pts) != len(ob.data.vertices):
                        raise ValueError(f"garment {name}.seated.collision: {ob.name} changes its vertex count")
                    w = wanted[ob.name]
                    for i, p in enumerate(pts):
                        hit = bvh.find_nearest(p, radius + falloff)
                        if hit[0] is None:
                            continue
                        w[i] = max(w[i], 1.0 if hit[3] <= radius else 1.0 - (hit[3] - radius) / falloff)
            finally:
                for undo in reversed(restore):
                    undo()
    finally:
        for m in off:
            m.show_viewport = True
        bpy.context.view_layer.update()
    for ob in targets:
        group = ob.vertex_groups[GEN.COLLISION_GROUP]
        by_weight = {}
        for v, w in zip(ob.data.vertices, wanted[ob.name]):
            now = next((g.weight for g in v.groups if g.group == group.index), 0.0)
            if w > now + 1e-4:
                by_weight.setdefault(round(w, 4), []).append(v.index)
        for w, idx in sorted(by_weight.items()):
            group.add(idx, w, "REPLACE")
        report["objects"][ob.name] = sum(len(i) for i in by_weight.values())
    report["vertices_raised"] = sum(report["objects"].values())
    return report


def bind(rig, body, garments, name, raw, max_influences=4, worn=None):
    """Applies one item's ``seated`` block after the ``garment/2`` binding. Returns a JSON-safe report."""
    st = settings(raw)
    pieces = sorted((o for o in garments if o.type == "MESH" and o.get("ps_garment_item") == name
                     and "ps_weight_anchor" not in o), key=lambda o: o.name)
    out = {}
    if st["leg_weights"] is not None:
        out["leg_weights"] = follow_skin(rig, body, pieces, st, name, max_influences)
    if st["collision"] is not None and (worn is None or name in set(worn)):
        out["collision"] = sweep_collision(rig, body, pieces, st, name)
    for ob in pieces:
        ob[REPORT_PROP] = True
    return out
