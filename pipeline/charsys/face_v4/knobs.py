"""face.knobs: built-in Blender deform modifiers as regional face-shape knobs (face_generic/4, T-216; T-211 / T-212).

Each knob is one Blender deform modifier with a compact falloff on the head skin, anchored on a face point:

    {"type": "WARP" | "HOOK", "at": <anchor>, "offset_m": [x, y, z], "radius_m": r, "falloff": "SMOOTH",
     "move_m": [dx, dy, dz], "scale": [sx, sy, sz], "mirror": true, "floor_m": f, "floor_fade_m": 0.01}
    {"type": "LATTICE", "at": <anchor>, "offset_m": [...], "size_m": [w, d, h], "points": [nu, nv, nw],
     "offsets": {"i_j_k": [dx, dy, dz]}, "mirror": true}

Anchors (face frame: +x = the character's left, -y = forward, +z = up; t runs from the eye line (0) to the spec chin
(1)): "chin", "mouth", "eye" (per side), {"front": t} (the front-view outline point at that height: the widest skin
point of the row, per side), {"profile": t} (the profile outline point on the midline: the most forward skin point).
`offset_m` shifts the anchor; on a per-side anchor x points outward. `move_m` / `scale` move / scale the Warp target
or the Hook empty about the anchor (x outward per side). `mirror` (default: true for per-side anchors) builds the
knob on both sides, mirrored. `floor_m` limits the knob to skin above anchor z - floor_m (a smooth fade of
floor_fade_m below), e.g. to keep the neck still. LATTICE: a box of size_m centred on the anchor with nu x nv x nw
points (linear interpolation); `offsets` moves points by index "i_j_k" (i along x, j along y, k along z); its
border points stay fixed, so the skin outside the box is unchanged; mirrored offsets go to index nu-1-i, x negated.

apply_knobs() builds the modifiers, applies each one as a shape key (modifier_apply_as_shapekey) and folds that key
into Basis: every key block moves by the same offset, so keys built before stay relative and unchanged, and every
key built later is built on the fitted rest face. All helpers (modifiers, empties, lattices, vertex groups) are
removed: the master is knob-free (face_parity.knob_free). Off-region motion is reported per knob (outside the
falloff radius / lattice box, and below the floor), so the compact-falloff claim is checked on every build.

Character-independent: every position and size is spec data or derived from the face context."""
import math

TYPES = ("WARP", "HOOK", "LATTICE")
FALLOFFS = ("SMOOTH", "SPHERE", "ROOT", "SHARP", "LINEAR", "CONSTANT", "INVERSE_SQUARE")
MIDLINE = ("chin", "mouth")
EPS_MOVED_M = 1e-6


class KnobError(ValueError):
    pass


def _vec3(v, name, default=(0.0, 0.0, 0.0)):
    v = default if v is None else v
    if not isinstance(v, (list, tuple)) or len(v) != 3:
        raise KnobError(f"{name} must be [x, y, z], got {v!r}")
    return tuple(float(c) for c in v)


def validate(knobs):
    """Plain checks of the spec list (no bpy). Returns the normalised list; raises KnobError."""
    if not isinstance(knobs, list):
        raise KnobError("face.knobs must be a list")
    out = []
    for i, k in enumerate(knobs):
        if not isinstance(k, dict):
            raise KnobError(f"face.knobs.{i} must be an object")
        t = k.get("type")
        if t not in TYPES:
            raise KnobError(f"face.knobs.{i}.type {t!r}: one of {TYPES}")
        at = k.get("at")
        side = per_side(at)
        n = dict(k, index=i, per_side=side, mirror=bool(k.get("mirror", side)),
                 offset_m=_vec3(k.get("offset_m"), f"face.knobs.{i}.offset_m"))
        if n["mirror"] and not side:
            raise KnobError(f"face.knobs.{i}: mirror needs a per-side anchor (eye / front)")
        if t in ("WARP", "HOOK"):
            r = float(k.get("radius_m", 0.0))
            if not r > 0:
                raise KnobError(f"face.knobs.{i}.radius_m must be > 0")
            if k.get("falloff", "SMOOTH") not in FALLOFFS:
                raise KnobError(f"face.knobs.{i}.falloff: one of {FALLOFFS}")
            n["move_m"] = _vec3(k.get("move_m"), f"face.knobs.{i}.move_m")
            n["scale"] = _vec3(k.get("scale"), f"face.knobs.{i}.scale", (1.0, 1.0, 1.0))
            if min(n["scale"]) <= 0:
                raise KnobError(f"face.knobs.{i}.scale must be > 0")
        else:
            n["size_m"] = _vec3(k.get("size_m"), f"face.knobs.{i}.size_m")
            if min(n["size_m"]) <= 0:
                raise KnobError(f"face.knobs.{i}.size_m must be > 0")
            pts = k.get("points", [3, 3, 3])
            if len(pts) != 3 or any(int(p) < 3 for p in pts):
                raise KnobError(f"face.knobs.{i}.points: three counts >= 3 (border points stay fixed)")
            n["points"] = [int(p) for p in pts]
            offs = {}
            for key, d in (k.get("offsets") or {}).items():
                idx = lattice_index(key, n["points"])
                if any(j in (0, p - 1) for j, p in zip(idx, n["points"])):
                    raise KnobError(f"face.knobs.{i}.offsets.{key}: border points stay fixed (compact knob)")
                offs[idx] = _vec3(d, f"face.knobs.{i}.offsets.{key}")
            n["offsets"] = offs
        out.append(n)
    return out


def lattice_index(key, points):
    parts = str(key).split("_")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        raise KnobError(f"lattice offset key {key!r}: 'i_j_k'")
    idx = tuple(int(p) for p in parts)
    if any(j >= p for j, p in zip(idx, points)):
        raise KnobError(f"lattice offset key {key!r} outside {points}")
    return idx


def per_side(at):
    if at in MIDLINE or (isinstance(at, dict) and "profile" in at):
        return False
    if at == "eye" or (isinstance(at, dict) and "front" in at):
        return True
    raise KnobError(f"unknown knob anchor {at!r} (chin, mouth, eye, {{'front': t}}, {{'profile': t}})")


def mirrored(v, sx):
    """Per-side vector (x outward) -> face frame for side sx (+1 left, -1 right)."""
    return (sx * v[0], v[1], v[2])


def anchors(ctx, ex, ez, z_mouth, z_chin, y_centre):
    """Anchor resolver: (at, sx) -> (x, y, z) on the current skin (ctx ray casts; call after ctx.invalidate())."""

    def row_z(t):
        return ez - float(t) * (ez - z_chin)

    def front(sx, z):
        best = None
        for i in range(25):  # widest skin point of the row: the front-view outline
            y = y_centre - 0.12 + 0.17 * i / 24
            x = ctx.side_x(sx, y, z)
            if x is not None and (best is None or sx * x > sx * best[0]):
                best = (x, y)
        if best is None:
            raise KnobError(f"no skin outline at z={z:.4f}")
        return (best[0], best[1], z)

    def resolve(at, sx=1):
        if at == "chin":
            return (0.0, ctx.face_y(None, 0.0, z_chin), z_chin)
        if at == "mouth":
            return (0.0, ctx.face_y(None, 0.0, z_mouth), z_mouth)
        if at == "eye":
            return (sx * ex, ctx.face_y(None, sx * ex, ez), ez)
        if isinstance(at, dict) and "profile" in at:
            z = row_z(at["profile"])
            return (0.0, ctx.face_y(None, 0.0, z), z)
        if isinstance(at, dict) and "front" in at:
            return front(sx, row_z(at["front"]))
        raise KnobError(f"unknown knob anchor {at!r}")

    return resolve


def _smooth(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def _floor_weights(co, z0, floor, fade):
    """Weights 1 above z0 - floor, smooth fade to 0 over `fade` below it."""
    import numpy as np
    zf = z0 - floor
    t = (co[:, 2] - (zf - fade)) / max(fade, 1e-9)
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


def _instances(k, resolve):
    sides = (1, -1) if k["mirror"] else (1,)
    out = []
    for sx in sides:
        a = resolve(k["at"], sx)
        o = mirrored(k["offset_m"], sx) if k["per_side"] else k["offset_m"]
        out.append((sx, tuple(a[i] + o[i] for i in range(3))))
    return out


def _add_group(head, name, weights):
    vg = head.vertex_groups.new(name=name)
    import numpy as np
    for w in np.unique(np.round(weights[weights > 0], 6)):
        idx = np.nonzero(np.abs(np.round(weights, 6) - w) < 1e-12)[0]
        vg.add([int(i) for i in idx], float(w), "REPLACE")
    return vg


def _build(C, head, k, sx, anchor, co, tag):
    """One modifier (and its helpers) on head. Returns (modifier, helpers, region test(co) -> bool array)."""
    import bpy
    import numpy as np
    from mathutils import Matrix, Vector
    helpers = []
    A = Vector(anchor)
    if k["type"] in ("WARP", "HOOK"):
        r = float(k["radius_m"])
        mv = mirrored(k["move_m"], sx) if k["per_side"] else k["move_m"]
        target = Matrix.Translation(A + Vector(mv)) @ Matrix.Diagonal((*k["scale"], 1.0))
        group = None
        floor = k.get("floor_m")
        d = np.linalg.norm(co - np.array(anchor), axis=1)
        w = (d <= r * 1.001).astype(float)
        if floor is not None:
            w = w * _floor_weights(co, anchor[2], float(floor), float(k.get("floor_fade_m", 0.01)))
        if k["type"] == "HOOK" or floor is not None:
            group = _add_group(head, f"{tag}_w", w)
            helpers.append(("group", group.name))
        if k["type"] == "WARP":
            e0 = bpy.data.objects.new(f"{tag}_from", None)
            e1 = bpy.data.objects.new(f"{tag}_to", None)
            for e in (e0, e1):
                C.objects.link(e)
                helpers.append(("object", e.name))
            e0.matrix_world = Matrix.Translation(A)
            e1.matrix_world = target
            m = head.modifiers.new(tag, "WARP")
            m.object_from, m.object_to = e0, e1
            m.falloff_type = k.get("falloff", "SMOOTH")
            m.falloff_radius = r
            m.use_volume_preserve = False
            m.strength = 1.0
        else:
            e = bpy.data.objects.new(f"{tag}_hook", None)
            C.objects.link(e)
            helpers.append(("object", e.name))
            e.matrix_world = Matrix.Translation(A)
            m = head.modifiers.new(tag, "HOOK")
            m.object = e
            m.center = head.matrix_world.inverted() @ A
            m.falloff_type = k.get("falloff", "SMOOTH")
            m.falloff_radius = r
            m.strength = 1.0
            bpy.context.view_layer.update()
            m.matrix_inverse = (e.matrix_world.inverted() @ head.matrix_world)
            e.matrix_world = target
        if group is not None:
            m.vertex_group = group.name
        region = (lambda c, A=np.array(anchor), r=r: np.linalg.norm(c - A, axis=1) <= r * 1.001)
        return m, helpers, region
    size = np.array(k["size_m"])
    lat = bpy.data.lattices.new(f"{tag}_lat")
    lat.points_u, lat.points_v, lat.points_w = k["points"]
    for ax in ("u", "v", "w"):
        setattr(lat, f"interpolation_type_{ax}", "KEY_LINEAR")
    lat.use_outside = False
    lo = bpy.data.objects.new(f"{tag}_lattice", lat)
    C.objects.link(lo)
    helpers.append(("object", lo.name))
    helpers.append(("lattice", lat.name))
    lo.matrix_world = Matrix.Translation(A) @ Matrix.Diagonal((*size, 1.0))
    nu, nv, nw = k["points"]
    for (i, j, l), d in k["offsets"].items():
        if k["per_side"] and sx < 0:  # mirror: index along x and the x offset
            i, d = nu - 1 - i, (-d[0], d[1], d[2])
        p = lat.points[i + nu * (j + nv * l)]
        p.co_deform = p.co + Vector((d[0] / size[0], d[1] / size[1], d[2] / size[2]))
    half = size / 2
    inside = np.all(np.abs(co - np.array(anchor)) <= half * 1.0001, axis=1)
    group = _add_group(head, f"{tag}_w", inside.astype(float))
    helpers.append(("group", group.name))
    m = head.modifiers.new(tag, "LATTICE")
    m.object = lo
    m.vertex_group = group.name
    m.strength = 1.0
    region = (lambda c, A=np.array(anchor), h=half: np.all(np.abs(c - A) <= h * 1.0001, axis=1))
    return m, helpers, region


def _coords(me):
    import numpy as np
    a = np.empty(3 * len(me.vertices))
    me.vertices.foreach_get("co", a)
    return a.reshape(-1, 3)


def _bake(head, mod_name):
    """Applies the modifier as a shape key and folds the key into Basis (every key block moves by its delta).
    Returns the per-vertex displacement (n x 3)."""
    import bpy
    import numpy as np
    me = head.data
    had_keys = me.shape_keys is not None
    idx = list(head.modifiers).index(head.modifiers[mod_name])
    with bpy.context.temp_override(object=head, active_object=head, selected_objects=[head]):
        if idx:
            bpy.ops.object.modifier_move_to_index(modifier=mod_name, index=0)
        bpy.ops.object.modifier_apply_as_shapekey(modifier=mod_name, keep_modifier=False)
    kbs = me.shape_keys.key_blocks
    key = kbs[mod_name]
    basis = me.shape_keys.reference_key
    n = len(me.vertices)
    a = np.empty(3 * n)
    b = np.empty(3 * n)
    basis.data.foreach_get("co", a)
    key.data.foreach_get("co", b)
    delta = b - a
    head.shape_key_remove(key)
    if not had_keys:
        head.shape_key_clear()
        v = np.empty(3 * n)
        me.vertices.foreach_get("co", v)
        me.vertices.foreach_set("co", v + delta)
    else:
        for kb in me.shape_keys.key_blocks:  # Basis and every key relative to it follow by the same offset
            c = np.empty(3 * n)
            kb.data.foreach_get("co", c)
            kb.data.foreach_set("co", c + delta)
        v = np.empty(3 * n)
        me.vertices.foreach_get("co", v)
        me.vertices.foreach_set("co", v + delta)
    me.update()
    return delta.reshape(-1, 3)


def _cleanup(head, helpers):
    import bpy
    for kind, name in helpers:
        if kind == "group" and head.vertex_groups.get(name) is not None:
            head.vertex_groups.remove(head.vertex_groups[name])
        elif kind == "object" and bpy.data.objects.get(name) is not None:
            bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
    for kind, name in helpers:
        if kind == "lattice" and bpy.data.lattices.get(name) is not None:
            bpy.data.lattices.remove(bpy.data.lattices[name])


def apply_knobs(C, head, ctx, knobs, resolve, body_below_m=0.04, z_chin=None):
    """Builds, bakes and removes every knob (module docstring). Anchors are resolved on the skin as it is when the
    knob is reached (knobs apply in list order). Returns the report."""
    import numpy as np
    ks = validate(knobs)
    rep = {"count": 0, "knobs": []}
    total = np.zeros((len(head.data.vertices), 3))
    for k in ks:
        ctx.invalidate()
        for sx, anchor in _instances(k, resolve):
            tag = f"knob_{k['index']:02d}" + ("" if not k["mirror"] else (".L" if sx > 0 else ".R"))
            co = _coords(head.data) @ np.array(head.matrix_world.to_3x3()).T + np.array(head.matrix_world.translation)
            m, helpers, region = _build(C, head, k, sx, anchor, co, tag)
            try:
                d = _bake(head, m.name)
            finally:
                _cleanup(head, helpers)
            mag = np.linalg.norm(d, axis=1)
            moved = mag > EPS_MOVED_M
            out = ~region(co)
            entry = {"name": k.get("name", tag), "tag": tag, "type": k["type"],
                     "anchor_m": [round(float(c), 5) for c in anchor],
                     "moved_vertices": int(moved.sum()), "max_mm": round(float(mag.max()) * 1000, 4),
                     "outside_region_max_mm": round(float(mag[out].max()) * 1000 if out.any() else 0.0, 6)}
            if k.get("floor_m") is not None:
                below = co[:, 2] < anchor[2] - float(k["floor_m"]) - float(k.get("floor_fade_m", 0.01))
                entry["below_floor_max_mm"] = round(float(mag[below].max()) * 1000 if below.any() else 0.0, 6)
            rep["knobs"].append(entry)
            rep["count"] += 1
            total += d
    ctx.invalidate()
    mag = np.linalg.norm(total, axis=1)
    rep["max_mm"] = round(float(mag.max()) * 1000, 4) if len(mag) else 0.0
    if z_chin is not None:
        co = _coords(head.data)
        body = co[:, 2] < z_chin - body_below_m
        rep["body_below_chin_max_mm"] = round(float(mag[body].max()) * 1000 if body.any() else 0.0, 6)
    return rep
