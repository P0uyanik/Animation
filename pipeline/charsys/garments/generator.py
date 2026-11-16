"""Shared, character-independent garment construction for ``body_generic/1``.

Coordinates and dimensions come only from the generic body parameters and the
garment spec. The character faces -Y, +Z is up, and +X is its left.
"""
import math
import re

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree


GENERATOR = "garment/1"
ITEM_TYPES = {"top", "shirt", "vest", "shorts", "trousers", "dress", "skirt", "shoes", "boots"}
COLLARS = {"none", "crew", "rib", "shirt", "point", "v", "v-neck"}
MATERIAL_PRESETS = {
    "felt", "wool yarn", "fleece", "cotton knit", "woven cotton", "denim", "felt hair",
    "buttons/plastic", "glasses/acrylic", "skin-felt",
}
DEFAULT_COLOURS = {
    "cotton knit": (196, 189, 181), "woven cotton": (202, 194, 184), "denim": (74, 91, 112),
    "felt": (118, 101, 90), "fleece": (151, 132, 116), "buttons/plastic": (118, 88, 64),
}


def _number(value, label, low=None, high=None):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{label} must be a number")
    value = float(value)
    if low is not None and value < low or high is not None and value > high:
        raise ValueError(f"{label} must be in [{low}, {high}]")
    return value


def _assignment(cfg, part="main"):
    value = cfg.get("materials", {}).get(part)
    if value is None and part in ("bodice", "skirt"):
        value = cfg.get("materials", {}).get("main")
    if value is None:
        value = cfg.get("material") or cfg.get("material_preset")
    if isinstance(value, str):
        value = {"preset": value}
    if not isinstance(value, dict) or not value.get("preset"):
        raise ValueError(f"garment {cfg.get('name', cfg.get('type'))}.{part} needs a material preset")
    if value["preset"] not in MATERIAL_PRESETS:
        raise ValueError(f"unknown garment material preset: {value['preset']}")
    color = value.get("base_color_srgb", cfg.get("base_color_srgb"))
    if color is not None and (not isinstance(color, list) or len(color) != 3 or
                              any(not isinstance(c, (int, float)) or c < 0 or c > 255 for c in color)):
        raise ValueError(f"garment {cfg.get('name', cfg.get('type'))}.{part}.base_color_srgb must be 3 values in [0, 255]")
    return {**value, "base_color_srgb": color or list(DEFAULT_COLOURS.get(value["preset"], (150, 130, 115)))}


def validate(clothing):
    """Validate and return a shallow-normalized ``garment/1`` clothing block."""
    if not isinstance(clothing, dict) or clothing.get("generator") != GENERATOR:
        raise ValueError(f"clothing.generator must be {GENERATOR}")
    items = clothing.get("garments")
    if not isinstance(items, list) or not items:
        raise ValueError("clothing.garments must be a non-empty list")
    defaults = clothing.get("defaults", {})
    if "max_influences" in clothing and (not isinstance(clothing["max_influences"], int) or
                                          not 1 <= clothing["max_influences"] <= 4):
        raise ValueError("clothing.max_influences must be an integer in [1, 4]")
    collision = clothing.get("collision", {})
    if not isinstance(collision, dict):
        raise ValueError("clothing.collision must be an object")
    if "enabled" in collision and not isinstance(collision["enabled"], bool):
        raise ValueError("clothing.collision.enabled must be a boolean")
    if "mask_margin_m" in clothing:
        _number(clothing["mask_margin_m"], "clothing.mask_margin_m", 0.0, 0.2)
    for key in ("offset_m", "radius_m", "falloff_m"):
        if key in collision:
            _number(collision[key], f"clothing.collision.{key}", 0.0, 0.2)
    if "passes" in collision and (not isinstance(collision["passes"], int) or not 1 <= collision["passes"] <= 4):
        raise ValueError("clothing.collision.passes must be an integer in [1, 4]")
    if "hide_body_faces" in clothing and not isinstance(clothing["hide_body_faces"], bool):
        raise ValueError("clothing.hide_body_faces must be a boolean")
    for key in ("thickness_m", "ease_m", "offset_m", "seam_radius_m", "collision_clearance_m",
                "articulation_allowance_m", "front_articulation_rise_m", "front_centre_ease_m"):
        if key in defaults:
            _number(defaults[key], f"clothing.defaults.{key}", 0.0, 0.1)
    names = set()
    for i, raw in enumerate(items):
        if not isinstance(raw, dict) or raw.get("type") not in ITEM_TYPES:
            raise ValueError(f"clothing.garments[{i}].type must be one of {sorted(ITEM_TYPES)}")
        name = raw.get("name", raw["type"])
        if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", name):
            raise ValueError(f"clothing.garments[{i}].name must be lower_snake_case")
        if name in names:
            raise ValueError(f"duplicate garment name: {name}")
        names.add(name)
        _assignment(raw)
        if "mask_body" in raw and not isinstance(raw["mask_body"], bool):
            raise ValueError(f"garment {name}.mask_body must be a boolean")
        for key in ("sleeve_length", "length", "height", "flare"):
            if key in raw:
                _number(raw[key], f"garment {name}.{key}", 0.0, 1.0)
        for key in ("thickness_m", "ease_m", "offset_m", "seam_radius_m", "collision_clearance_m",
                    "articulation_allowance_m", "front_articulation_rise_m", "front_centre_ease_m", "length_m", "height_m", "flare_m"):
            if key in raw:
                _number(raw[key], f"garment {name}.{key}", 0.0, 1.0)
        collar = raw.get("collar", "none")
        collar = collar.get("type", "none") if isinstance(collar, dict) else collar
        if collar not in COLLARS:
            raise ValueError(f"garment {name}.collar must be one of {sorted(COLLARS)}")
        for part in raw.get("materials", {}):
            _assignment(raw, part)
    return clothing


def _merge(defaults, item):
    out = dict(defaults or {})
    out.update(item)
    out["name"] = item.get("name", item["type"])
    out["ease_m"] = float(out.get("ease_m", out.get("offset_m", 0.008)))
    out["thickness_m"] = float(out.get("thickness_m", 0.002))
    out["seam_radius_m"] = float(out.get("seam_radius_m", max(0.0008, out["thickness_m"] * 0.55)))
    return out


def _material(G, name, assignment, reference_size):
    try:
        from materials import builder as material_builder
        return material_builder.build_material(name, assignment["preset"], assignment["base_color_srgb"],
                                               assignment.get("reference_size_m", reference_size),
                                               assignment.get("overrides"))
    except ImportError:
        mat = G.material(name, tuple(assignment["base_color_srgb"]), roughness=0.74,
                         sheen=0.12 if assignment["preset"] in ("cotton knit", "woven cotton", "denim") else 0.04)
        mat["ps_material_preset"] = assignment["preset"]
        mat["ps_material_reference_size_m"] = float(assignment.get("reference_size_m", reference_size))
        return mat


def _tag(ob, cfg, part, material):
    ob["ps_garment_generator"] = GENERATOR
    ob["ps_garment_item"] = cfg["name"]
    ob["ps_garment_type"] = cfg["type"]
    ob["ps_garment_part"] = part
    ob["ps_material_preset"] = material.get("ps_material_preset", "")
    ob["ps_collision_clearance_m"] = float(cfg.get(
        "collision_clearance_m", max(0.003, cfg["thickness_m"] * 1.5)))
    return ob


def _mat_for(G, cfg, part, H):
    assignment = _assignment(cfg, part)
    return _material(G, f"M_garment.{cfg['name']}.{part}", assignment, H)


def _interp(rows, z):
    rows = sorted(rows, key=lambda r: r[0])
    z = max(rows[0][0], min(rows[-1][0], z))
    for a, b in zip(rows, rows[1:]):
        if a[0] <= z <= b[0]:
            t = (z - a[0]) / max(1e-9, b[0] - a[0])
            return tuple(x + (y - x) * t for x, y in zip(a[1:], b[1:]))
    return tuple(rows[-1][1:])


def _torso_dims(P, H, z):
    rows = [[r[0] * H, *(x * H for x in r[1:])] for r in P["torso"]["levels"]]
    return _interp(rows, z)  # half width, front (-Y), back (+Y)


def _leg_radius(P, H, t):
    a, b, c = (x * H for x in P["leg"]["radii"])
    if t <= 0.5:
        return a + (b - a) * (t * 2)
    return b + (c - b) * ((t - 0.5) * 2)


def _arm_radius(P, H, t):
    a, b, c = (x * H for x in P["arm"]["radii"])
    elbow = P["arm"]["upper_len"] / (P["arm"]["upper_len"] + P["arm"]["fore_len"])
    if t <= elbow:
        return a + (b - a) * (t / max(elbow, 1e-9))
    return b + (c - b) * ((t - elbow) / max(1 - elbow, 1e-9))


def _segment(p, a, b):
    d = b - a
    t = max(0.0, min(1.0, (p - a).dot(d) / max(d.length_squared, 1e-12)))
    return t, (p - (a + d * t)).length


def _face_centroid(body, poly):
    return sum((body.data.vertices[i].co for i in poly.vertices), Vector()) / len(poly.vertices)


def _shell(body, name, selector, ease, thickness, C, G):
    selected = [p for p in body.data.polygons if selector(_face_centroid(body, p))]
    if not selected:
        raise ValueError(f"garment region {name} selected no body faces")
    source = sorted({i for p in selected for i in p.vertices})
    remap = {old: new for new, old in enumerate(source)}
    verts = [body.data.vertices[i].co + body.data.vertices[i].normal * ease for i in source]
    # Concave body areas (especially an armpit) can point an ordinary normal offset toward another part of the
    # surface. Project those vertices to the exterior clearance envelope; the source index still owns its skinning.
    body_bvh = BVHTree.FromPolygons([v.co.copy() for v in body.data.vertices],
                                    [tuple(p.vertices) for p in body.data.polygons], all_triangles=False)
    for k, point in enumerate(verts):
        point = point.copy()
        for _ in range(4):
            location, normal, _, _ = body_bvh.find_nearest(point)
            signed = (point - location).dot(normal)
            if signed >= ease - 1e-6:
                break
            point += normal * (ease - signed + 1e-5)
        verts[k] = tuple(point)
    faces = [tuple(remap[i] for i in p.vertices) for p in selected]
    ob = G.new_object(name, verts, faces, C)
    source_attr = ob.data.attributes.new("ps_body_vertex", "INT", "POINT")
    for datum, index in zip(source_attr.data, source):
        datum.value = index
    if thickness > 0:
        mod = ob.modifiers.new("garment_thickness", "SOLIDIFY")
        mod.thickness = thickness
        mod.offset = 1.0
        bpy.context.view_layer.objects.active = ob
        ob.select_set(True)
        bpy.ops.object.modifier_apply(modifier=mod.name)
        ob.select_set(False)
    return ob, {p.index for p in selected}


def _ensure_clearance(body, ob, clearance):
    """Move a procedural piece onto the body's exterior clearance envelope in rest pose."""
    bvh = BVHTree.FromPolygons([v.co.copy() for v in body.data.vertices],
                               [tuple(p.vertices) for p in body.data.polygons], all_triangles=False)
    changed = False
    for vertex in ob.data.vertices:
        point = ob.matrix_world @ vertex.co
        for _ in range(5):
            location, normal, _, _ = bvh.find_nearest(point)
            signed = (point - location).dot(normal)
            if signed >= clearance - 1e-6:
                break
            point += normal * (clearance - signed + 1e-5)
            changed = True
        vertex.co = ob.matrix_world.inverted() @ point
    if changed:
        ob.data.update()


def _front_articulation_rise(ob, centre_z, half_span, rise, upper_only=False):
    """Raise the lower front articulation band so flexed thighs remain below the garment."""
    if rise <= 0:
        return
    for vertex in ob.data.vertices:
        dz = vertex.co.z - centre_z
        factor = 1.0 - (max(0.0, dz) if upper_only else abs(dz)) / max(half_span, 1e-9)
        front = min(1.0, max(0.0, -vertex.co.y / 0.04))
        if factor <= 0 or front <= 0 or upper_only and dz < -0.01:
            continue
        vertex.co.z += rise * min(1.0, factor) * front
    ob.data.update()


def _front_centre_ease(ob, centre_z, half_span, depth, centre_width):
    """Add a front pleat over the hip centre without widening the side silhouette."""
    if depth <= 0:
        return
    for vertex in ob.data.vertices:
        z_factor = 1.0 - abs(vertex.co.z - centre_z) / max(half_span, 1e-9)
        x_factor = 1.0 - abs(vertex.co.x) / max(centre_width, 1e-9)
        if vertex.co.y < 0 and z_factor > 0 and x_factor > 0:
            vertex.co.y -= depth * min(1.0, z_factor) * min(1.0, x_factor)
    ob.data.update()


def _closed_tube(G, C, name, points, radius):
    pts = [Vector(p) for p in points]
    if (pts[0] - pts[-1]).length > 1e-8:
        pts.append(pts[0])
    return G.tube(name, pts, [radius] * len(pts), [radius] * len(pts), C, up_hint=(0, 0, 1),
                  seg=8, cap_start=None, cap_end=None)


def _torso_ring(G, C, name, P, H, z, ease, radius):
    w, front, back = _torso_dims(P, H, z)
    ring = G.superellipse_ring(0, 0, z, w + ease, front + ease, back + ease, 2.4, 48)
    return _closed_tube(G, C, name, ring, radius)


def _limb_ring(G, C, name, centre, direction, body_radius, ease, seam_radius):
    d = Vector(direction).normalized()
    front = Vector((0, -1, 0))
    front = (front - d * front.dot(d)).normalized()
    side = d.cross(front).normalized()
    r = body_radius + ease
    points = [Vector(centre) + side * (math.cos(2 * math.pi * k / 32) * r) +
              front * (math.sin(2 * math.pi * k / 32) * r) for k in range(32)]
    return _closed_tube(G, C, name, points, seam_radius)


def _feature(objects, ob, cfg, part, mat, G):
    G.assign(ob, mat)
    _tag(ob, cfg, part, mat)
    objects.append(ob)
    return ob


def _top(C, body, cfg, P, H, J, G, vest=False):
    ease, thick = cfg["ease_m"], cfg["thickness_m"]
    shell_ease = ease + float(cfg.get("articulation_allowance_m", 0.0))
    front_rise = float(cfg.get("front_articulation_rise_m", 0.0))
    levels = P["torso"]["levels"]
    hem_z = float(cfg.get("hem_z_m", levels[2][0] * H))
    top_z = max(P["neck"]["base_z"], P["torso"]["levels"][-1][0]) * H
    sleeve = 0.0 if vest else float(cfg.get("sleeve_length", 0.45))
    arm_segments = [(J[f"shoulder.{s}"], J[f"wrist.{s}"]) for s in ("L", "R")]
    opening = float(cfg.get("open_front_m", 0.022 * H if vest else 0.0))

    def selector(c):
        torso = hem_z <= c.z <= top_z
        if torso:
            w, front, back = _torso_dims(P, H, c.z)
            torso = abs(c.x) <= w + 0.015 * H and -front - 0.015 * H <= c.y <= back + 0.015 * H
            # Leave an actual armhole. A shell copied from the underarm concavity is trapped when the arm lowers.
            if c.z > P["shoulder"]["z"] * H - 0.12 * H and abs(c.x) > w * 0.58:
                torso = False
            if vest and torso and c.y < -front * 0.35 and abs(c.x) < opening:
                torso = False
        arm = False
        if sleeve > 0:
            for a, b in arm_segments:
                t, d = _segment(c, a, b)
                arm |= 0.10 <= t <= sleeve and d <= _arm_radius(P, H, t) + 0.012 * H
        return torso or arm

    main, covered = _shell(body, f"garment.{cfg['name']}.main", selector, shell_ease, thick, C, G)
    _front_articulation_rise(main, hem_z, 0.20 * H, front_rise, upper_only=True)
    objects = []
    main_mat = _mat_for(G, cfg, "main", H)
    _feature(objects, main, cfg, "main", main_mat, G)
    seam_mat = _mat_for(G, cfg, "seam", H)
    bands = cfg.get("bands", {})
    if bands is True:
        bands = {"hem": True, "cuff": True}
    if bands.get("hem"):
        hem_band = _torso_ring(G, C, f"garment.{cfg['name']}.band.hem", P, H, hem_z, ease + thick + 0.004,
                               cfg["seam_radius_m"] * 1.25)
        _front_articulation_rise(hem_band, hem_z, 0.10 * H, front_rise, upper_only=True)
        _feature(objects, hem_band, cfg, "band", _mat_for(G, cfg, "band", H), G)
    ridges = int(bands.get("rib_ridges", 0))
    for k in range(ridges):
        z = hem_z + (k + 1) * cfg["seam_radius_m"] * 2.2
        ridge = _torso_ring(G, C, f"garment.{cfg['name']}.rib.hem_{k + 1}", P, H, z, ease + thick + 0.004,
                            cfg["seam_radius_m"] * 0.65)
        _front_articulation_rise(ridge, hem_z, 0.10 * H, front_rise, upper_only=True)
        _feature(objects, ridge, cfg, "band", _mat_for(G, cfg, "band", H), G)
    if sleeve > 0 and bands.get("cuff"):
        for side in ("L", "R"):
            a, b = J[f"shoulder.{side}"], J[f"wrist.{side}"]
            centre = a.lerp(b, sleeve)
            ob = _limb_ring(G, C, f"garment.{cfg['name']}.band.cuff.{side}", centre, b - a,
                            _arm_radius(P, H, sleeve), ease + thick, cfg["seam_radius_m"] * 1.25)
            _feature(objects, ob, cfg, "band", _mat_for(G, cfg, "band", H), G)
    if cfg.get("seam_lines"):
        seam_top_z = min(top_z, P["shoulder"]["z"] * H - 0.12 * H)
        for sx, side in ((1, "L"), (-1, "R")):
            path = []
            for k in range(9):
                z = hem_z + (seam_top_z - hem_z) * k / 8
                w, _, _ = _torso_dims(P, H, z)
                path.append(Vector((sx * (w + ease + thick), 0, z)))
            ob = G.tube(f"garment.{cfg['name']}.seam.side.{side}", path,
                        [cfg["seam_radius_m"]] * len(path), [cfg["seam_radius_m"]] * len(path), C,
                        up_hint=(0, -1, 0), seg=7, cap_start="round", cap_end="round")
            _feature(objects, ob, cfg, "seam", seam_mat, G)
    collar = cfg.get("collar", "none")
    collar = collar.get("type", "none") if isinstance(collar, dict) else collar
    if collar in ("crew", "rib"):
        r = P["neck"]["radius"] * H + ease + thick + cfg["seam_radius_m"]
        collar_z = top_z + ease * 0.35
        pts = [Vector((math.cos(2 * math.pi * k / 48) * r, math.sin(2 * math.pi * k / 48) * r, collar_z)) for k in range(48)]
        _feature(objects, _closed_tube(G, C, f"garment.{cfg['name']}.collar", pts, cfg["seam_radius_m"] * 1.4),
                 cfg, "band", _mat_for(G, cfg, "band", H), G)
    elif collar in ("v", "v-neck", "shirt", "point"):
        r = P["neck"]["radius"] * H + ease + thick
        drop = float(cfg.get("collar_drop_m", 0.045 * H if collar in ("v", "v-neck") else 0.032 * H))
        collar_z = top_z + ease * 0.2
        _, front_top, _ = _torso_dims(P, H, top_z)
        _, front_low, _ = _torso_dims(P, H, top_z - drop)
        y_top = -(max(r, front_top) + ease + thick + cfg["seam_radius_m"] * 2)
        y_low = -(front_low + ease + thick + cfg["seam_radius_m"] * 2)
        pts = [Vector((-r, y_top, collar_z)), Vector((0, y_low, top_z - drop)), Vector((r, y_top, collar_z))]
        ob = G.tube(f"garment.{cfg['name']}.collar", pts, [cfg["seam_radius_m"] * 1.5] * 3,
                    [cfg["seam_radius_m"] * 1.5] * 3, C, up_hint=(0, -1, 0), seg=8)
        _feature(objects, ob, cfg, "band", _mat_for(G, cfg, "band", H), G)
    buttons = cfg.get("buttons", 0)
    buttons = {"count": buttons} if isinstance(buttons, int) else (buttons or {})
    count = int(buttons.get("count", 0))
    if count:
        bm = _mat_for(G, cfg, "buttons", H)
        radius = float(buttons.get("radius_m", 0.006 * H))
        z0, z1 = hem_z + 0.07 * H, top_z - 0.07 * H
        for k in range(count):
            z = (z0 + z1) * 0.5 if count == 1 else z0 + (z1 - z0) * k / (count - 1)
            _, front, _ = _torso_dims(P, H, z)
            ob = G.uv_sphere(f"garment.{cfg['name']}.button.{k + 1}", (0, -front - ease - thick - radius, z),
                             1.0, C, 16, 8, (radius, radius * 0.45, radius))
            ob["ps_weight_anchor"] = (0, -front, z)
            _feature(objects, ob, cfg, "buttons", bm, G)
    if vest and cfg.get("pockets", True):
        pm = _mat_for(G, cfg, "pockets", H)
        pc = cfg.get("pockets") if isinstance(cfg.get("pockets"), dict) else {}
        pw, ph, pd = (float(pc.get("width_m", 0.035 * H)), float(pc.get("height_m", 0.032 * H)),
                      float(pc.get("depth_m", 0.004 * H)))
        z = hem_z + float(pc.get("above_hem_m", 0.055 * H))
        w, front, _ = _torso_dims(P, H, z)
        for sx, side in ((1, "L"), (-1, "R")):
            centre = (sx * min(w * 0.5, w - pw), -front - ease - thick - pd, z)
            ob = G.uv_sphere(f"garment.{cfg['name']}.pocket.{side}", centre, 1.0, C, 20, 10,
                             (pw, pd, ph))
            ob["ps_weight_anchor"] = (centre[0], -front, centre[2])
            _feature(objects, ob, cfg, "pockets", pm, G)
    return objects, covered


def _bottoms(C, body, cfg, P, H, J, G):
    ease, thick = cfg["ease_m"], cfg["thickness_m"]
    shell_ease = ease + float(cfg.get("articulation_allowance_m", 0.0))
    front_rise = float(cfg.get("front_articulation_rise_m", 0.0))
    is_short = cfg["type"] == "shorts"
    length = float(cfg.get("length", 0.36 if is_short else 0.92))
    hip_z, ankle_z = P["leg"]["hip_z"] * H, P["leg"]["ankle_z"] * H
    bottom_z = float(cfg.get("length_m", length * (hip_z - ankle_z)))
    bottom_z = hip_z - bottom_z if "length_m" in cfg else hip_z - length * (hip_z - ankle_z)
    waist_z = float(cfg.get("waist_z_m", P["torso"]["levels"][2][0] * H))

    def selector(c):
        if not bottom_z <= c.z <= waist_z:
            return False
        if c.z >= hip_z:
            w, front, back = _torso_dims(P, H, c.z)
            return abs(c.x) <= w + 0.012 * H and -front - 0.012 * H <= c.y <= back + 0.012 * H
        t = (hip_z - c.z) / max(hip_z - ankle_z, 1e-9)
        if t > length + 0.04:
            return False
        # Crotch bridge: the merged body surface between the legs just below the hip line.
        if c.z >= hip_z - _leg_radius(P, H, 0.0) and abs(c.x) <= abs(J["hip.L"].x):
            _, front, back = _torso_dims(P, H, hip_z)
            if -front - 0.012 * H <= c.y <= back + 0.012 * H:
                return True
        r = _leg_radius(P, H, t) + 0.012 * H
        return any((Vector((c.x, c.y, c.z)) - Vector((J[f"hip.{s}"].x, 0, c.z))).length <= r for s in ("L", "R"))

    main, covered = _shell(body, f"garment.{cfg['name']}.main", selector, shell_ease, thick, C, G)
    _front_articulation_rise(main, hip_z, 0.20 * H, front_rise)
    _front_centre_ease(main, hip_z, 0.12 * H, float(cfg.get("front_centre_ease_m", 0.0)), abs(J["hip.L"].x) * 0.75)
    objects = []
    _feature(objects, main, cfg, "main", _mat_for(G, cfg, "main", H), G)
    bands = cfg.get("bands", {})
    if bands is True:
        bands = {"waist": True, "cuff": True}
    if bands.get("waist"):
        waist_band = _torso_ring(G, C, f"garment.{cfg['name']}.band.waist", P, H, waist_z,
                                  ease + thick + 0.004, cfg["seam_radius_m"] * 1.3)
        _front_articulation_rise(waist_band, hip_z, 0.10 * H, front_rise)
        _feature(objects, waist_band, cfg, "band", _mat_for(G, cfg, "band", H), G)
    if cfg.get("cuff") or bands.get("cuff"):
        t = max(0.0, min(1.0, (hip_z - bottom_z) / max(hip_z - ankle_z, 1e-9)))
        for side in ("L", "R"):
            centre = Vector((J[f"hip.{side}"].x, 0, bottom_z))
            ob = _limb_ring(G, C, f"garment.{cfg['name']}.band.cuff.{side}", centre, (0, 0, -1),
                            _leg_radius(P, H, t), ease + thick, cfg["seam_radius_m"] * 1.35)
            _feature(objects, ob, cfg, "band", _mat_for(G, cfg, "band", H), G)
    if cfg.get("seam_lines"):
        sm = _mat_for(G, cfg, "seam", H)
        for sx, side in ((1, "L"), (-1, "R")):
            path = []
            for k in range(9):
                z = bottom_z + (waist_z - bottom_z) * k / 8
                if z < hip_z:
                    t = (hip_z - z) / max(hip_z - ankle_z, 1e-9)
                    x = abs(J[f"hip.{side}"].x) + _leg_radius(P, H, t) + ease + thick
                else:
                    x = _torso_dims(P, H, z)[0] + ease + thick
                path.append(Vector((sx * x, 0, z)))
            ob = G.tube(f"garment.{cfg['name']}.seam.side.{side}", path,
                        [cfg["seam_radius_m"]] * len(path), [cfg["seam_radius_m"]] * len(path), C,
                        up_hint=(0, -1, 0), seg=7)
            _feature(objects, ob, cfg, "seam", sm, G)
    return objects, covered


def _skirt_ring(z, width, front, back):
    """Eight-sided ring rotated off the inter-leg axes for a stable unified skirt silhouette."""
    points = []
    for k in range(8):
        angle = 2 * math.pi * (k + 0.5) / 8
        c, s = math.cos(angle), math.sin(angle)
        x = width * math.copysign(abs(c) ** (2 / 2.4), c)
        y_extent = back if s > 0 else front
        y = y_extent * math.copysign(abs(s) ** (2 / 2.4), s)
        points.append((x, y, z))
    return points


def _skirt(C, cfg, P, H, J, G, part="main"):
    ease, thick = cfg["ease_m"], cfg["thickness_m"]
    hip_z, ankle_z = P["leg"]["hip_z"] * H, P["leg"]["ankle_z"] * H
    waist_z = float(cfg.get("waist_z_m", P["torso"]["levels"][2][0] * H))
    length = float(cfg.get("length", 0.66))
    bottom_z = waist_z - (float(cfg["length_m"]) if "length_m" in cfg else length * (waist_z - ankle_z))
    flare = float(cfg.get("flare_m", float(cfg.get("flare", 0.08)) * H))
    rings = []
    for k in range(17):
        t = k / 16
        z = bottom_z + (waist_z - bottom_z) * t
        down = 1 - t
        if z >= hip_z:
            w, front, back = _torso_dims(P, H, z)
        else:
            lt = (hip_z - z) / max(hip_z - ankle_z, 1e-9)
            lr = _leg_radius(P, H, lt)
            w = abs(J["hip.L"].x) + lr
            front = back = lr
        add = ease + thick + flare * down
        rings.append(_skirt_ring(z, w + add, front + add, back + add))
    ob = G.loft(f"garment.{cfg['name']}.{part}", rings, C, cap_bottom=False, cap_top=False)
    if thick > 0:
        mod = ob.modifiers.new("garment_thickness", "SOLIDIFY")
        mod.thickness, mod.offset = thick, 1.0
        bpy.context.view_layer.objects.active = ob
        ob.select_set(True)
        bpy.ops.object.modifier_apply(modifier=mod.name)
        ob.select_set(False)
    objects = []
    _feature(objects, ob, cfg, part, _mat_for(G, cfg, part, H), G)
    bands = cfg.get("bands", {})
    if bands is True:
        bands = {"waist": True, "hem": True}
    bm = _mat_for(G, cfg, "band", H)
    if bands.get("waist"):
        _feature(objects, _torso_ring(G, C, f"garment.{cfg['name']}.band.waist", P, H, waist_z,
                                     ease + thick, cfg["seam_radius_m"] * 1.3), cfg, "band", bm, G)
    if bands.get("hem"):
        ring = rings[0]
        _feature(objects, _closed_tube(G, C, f"garment.{cfg['name']}.band.hem", ring,
                                      cfg["seam_radius_m"] * 1.35), cfg, "band", bm, G)
    if cfg.get("seam_lines"):
        sm = _mat_for(G, cfg, "seam", H)
        for sx, side in ((1, "L"), (-1, "R")):
            path = [Vector((sx * max(abs(point[0]) for point in ring), 0.0, ring[0][2])) for ring in rings]
            ob = G.tube(f"garment.{cfg['name']}.seam.side.{side}", path,
                        [cfg["seam_radius_m"]] * len(path), [cfg["seam_radius_m"]] * len(path), C,
                        up_hint=(0, -1, 0), seg=7)
            _feature(objects, ob, cfg, "seam", sm, G)
    anchor = (0.0, 0.0, waist_z)
    for piece in objects:
        piece["ps_weight_anchor"] = anchor
    return objects


def _footwear(C, body, cfg, P, H, J, G):
    ease, thick = cfg["ease_m"], cfg["thickness_m"]
    ankle_z, knee_z = P["leg"]["ankle_z"] * H, P["leg"]["knee_z"] * H
    height = float(cfg.get("height", 0.18 if cfg["type"] == "shoes" else 0.64))
    top_z = ankle_z + (float(cfg["height_m"]) if "height_m" in cfg else height * (knee_z - ankle_z))
    fw, fl = P["foot"]["half_width"] * H, P["foot"]["length"] * H
    max_r = max(x * H for x in P["leg"]["radii"])
    objects, covered = [], set()
    for side in ("L", "R"):
        hx = J[f"ankle.{side}"].x

        def selector(c, hx=hx):
            return (-0.01 * H <= c.z <= top_z and abs(c.x - hx) <= max(fw, max_r) + 0.015 * H and
                    -1.05 * fl <= c.y <= max_r + 0.02 * H)
        ob, cov = _shell(body, f"garment.{cfg['name']}.main.{side}", selector, ease, thick, C, G)
        covered |= cov
        _feature(objects, ob, cfg, "main", _mat_for(G, cfg, "main", H), G)
        bands = cfg.get("bands", {})
        bands = {"cuff": True} if bands is True else bands
        if cfg.get("cuff") or bands.get("cuff"):
            t = max(0.0, min(1.0, (knee_z - top_z) / max(knee_z - ankle_z, 1e-9)))
            lr = _leg_radius(P, H, 1 - t)
            ring = _limb_ring(G, C, f"garment.{cfg['name']}.band.cuff.{side}", (hx, 0, top_z), (0, 0, -1),
                              lr, ease + thick, cfg["seam_radius_m"] * 1.4)
            _feature(objects, ring, cfg, "band", _mat_for(G, cfg, "band", H), G)
        sole = cfg.get("sole", {})
        if sole is not False:
            sole = sole if isinstance(sole, dict) else {}
            st = float(sole.get("thickness_m", max(0.003, thick * 2)))
            ob = G.uv_sphere(f"garment.{cfg['name']}.sole.{side}",
                             (hx, -0.30 * fl, -ease - st * 0.5), 1.0, C, 28, 12,
                             (fw + ease + thick, 0.60 * fl + ease + thick, st * 0.5))
            _feature(objects, ob, cfg, "sole", _mat_for(G, cfg, "sole", H), G)
    return objects, covered


MASK_PREFIX = "ps_mask."
MASK_GROUP = "ps_garment_mask"
MASK_MODIFIER = "garment_body_mask"
COLLISION_GROUP = "ps_collision"
COLLISION_MODIFIER = "body_collision"
COVER_ATTR = "ps_cover."


def _store_cover(body, item, faces):
    """Record the body faces an item's shell covers as a FACE boolean attribute (survives rigging)."""
    name = COVER_ATTR + item
    if name in body.data.attributes:
        body.data.attributes.remove(body.data.attributes[name])
    attr = body.data.attributes.new(name, "BOOLEAN", "FACE")
    values = [False] * len(body.data.polygons)
    for index in faces:
        values[index] = True
    attr.data.foreach_set("value", values)


def _covered_faces(body, items):
    covered = set()
    for item in items:
        attr = body.data.attributes.get(COVER_ATTR + item)
        if attr is None:
            continue
        values = [False] * len(body.data.polygons)
        attr.data.foreach_get("value", values)
        covered.update(i for i, v in enumerate(values) if v)
    return covered


def _fully_covered_vertices(body, faces):
    """Vertices whose every incident face is covered. Masking them removes only fully covered faces."""
    touched, open_verts = set(), set()
    for poly in body.data.polygons:
        target = touched if poly.index in faces else open_verts
        target.update(poly.vertices)
    return touched - open_verts


def _mask_margin(body, hidden, margin):
    """Keep skin within ``margin`` (geodesic, rest pose) of any visible skin, so a camera looking past a hem, cuff or
    collar sees skin under the opening instead of the hollow inside of the masked body."""
    if not hidden or margin <= 0:
        return hidden
    import heapq
    co = [v.co for v in body.data.vertices]
    adjacent = {}
    for edge in body.data.edges:
        a, b = edge.vertices
        if a in hidden or b in hidden:
            length = (co[a] - co[b]).length
            adjacent.setdefault(a, []).append((b, length))
            adjacent.setdefault(b, []).append((a, length))
    dist = {}
    heap = []
    for index in hidden:
        for other, length in adjacent.get(index, ()):
            if other not in hidden and length < dist.get(index, margin):
                dist[index] = length
    heap = [(d, i) for i, d in dist.items()]
    heapq.heapify(heap)
    while heap:
        d, index = heapq.heappop(heap)
        if d > dist.get(index, margin):
            continue
        for other, length in adjacent.get(index, ()):
            nd = d + length
            if other in hidden and nd < dist.get(other, margin):
                dist[other] = nd
                heapq.heappush(heap, (nd, other))
    return {i for i in hidden if dist.get(i, margin) >= margin}


def masked_items(body):
    return list(body.get("ps_garment_mask_items", []))


def set_active_items(body, garments, items, collision=None):
    """Select which garment items are worn: rebuilds the body mask (union of the worn items' masks) and the
    per-garment collision weights against the body regions that stay visible. Deterministic; no simulation."""
    items = set(items)
    if collision is None:
        collision = dict(body.get("ps_garment_collision", {}))
    radius = float(collision.get("radius_m", 0.08))
    falloff = float(collision.get("falloff_m", 0.02))
    mask_items = sorted(items & set(masked_items(body)))
    hidden_faces = _covered_faces(body, mask_items)
    hidden_verts = _mask_margin(body, _fully_covered_vertices(body, hidden_faces),
                                float(body.get("ps_garment_mask_margin_m", 0.015)))
    group = body.vertex_groups.get(MASK_GROUP) or body.vertex_groups.new(name=MASK_GROUP)
    group.remove(list(range(len(body.data.vertices))))
    if hidden_verts:
        group.add(sorted(hidden_verts), 1.0, "REPLACE")
    mod = body.modifiers.get(MASK_MODIFIER)
    if mod is None:
        mod = body.modifiers.new(MASK_MODIFIER, "MASK")
    mod.mode, mod.vertex_group, mod.invert_vertex_group = "VERTEX_GROUP", MASK_GROUP, True
    mod.show_viewport = mod.show_render = bool(hidden_verts)
    # Faces actually removed by the mask: any face with a hidden vertex.
    removed = {p.index for p in body.data.polygons if any(v in hidden_verts for v in p.vertices)}
    visible = [p for p in body.data.polygons if p.index not in removed]
    body_points = [body.matrix_world @ v.co for v in body.data.vertices]
    full = BVHTree.FromPolygons(body_points, [tuple(p.vertices) for p in body.data.polygons], all_triangles=False)
    bvh = None
    if visible:
        bvh = BVHTree.FromPolygons(body_points, [tuple(p.vertices) for p in visible], all_triangles=False)
    weighted = 0
    for ob in garments:
        worn = ob.get("ps_garment_item") in items
        ob.hide_render = not worn
        cgroup = ob.vertex_groups.get(COLLISION_GROUP)
        if cgroup is None or ob.modifiers.get(COLLISION_MODIFIER) is None:
            continue
        cgroup.remove(list(range(len(ob.data.vertices))))
        if not worn or bvh is None:
            continue
        # Rest-pose distance to the visible body decides how much of the post-skinning correction applies:
        # full weight near hems, cuffs, collars and open garments; zero over masked (hidden) skin.
        by_weight = {}
        for v in ob.data.vertices:
            point = ob.matrix_world @ v.co
            over = full.find_nearest(point)[2]
            if over is not None and over not in removed:
                w = 1.0  # hangs over visible skin (skirts, sleeve openings, hems)
            else:
                hit = bvh.find_nearest(point)
                if hit[0] is None:
                    continue
                d = hit[3]
                w = 1.0 if d <= radius else max(0.0, 1.0 - (d - radius) / max(falloff, 1e-9))
            if w > 0:
                by_weight.setdefault(round(w, 4), []).append(v.index)
        for w, idx in sorted(by_weight.items()):
            cgroup.add(idx, w, "REPLACE")
            weighted += len(idx)
    return {"worn": sorted(items), "masked_items": mask_items, "hidden_body_vertices": len(hidden_verts),
            "hidden_body_faces": len(removed), "visible_body_faces": len(visible),
            "collision_weighted_vertices": weighted}


def visible_face_flags(body):
    """Per-polygon visibility of the body under its current garment mask (True = visible)."""
    group = body.vertex_groups.get(MASK_GROUP)
    mod = body.modifiers.get(MASK_MODIFIER)
    if group is None or mod is None or not mod.show_render:
        return [True] * len(body.data.polygons)
    hidden = set()
    gi = group.index
    for v in body.data.vertices:
        if any(g.group == gi and g.weight > 0 for g in v.groups):
            hidden.add(v.index)
    return [not any(i in hidden for i in p.vertices) for p in body.data.polygons]


def build(C, body, clothing, P, H, J, G):
    """Build garments before rigging. Returns ``(objects, JSON-safe report)``."""
    validate(clothing)
    objects, coverage, item_report, masked = [], set(), [], []
    hide_default = bool(clothing.get("hide_body_faces", False))
    for raw in clothing["garments"]:
        cfg = _merge(clothing.get("defaults"), raw)
        before = len(objects)
        if cfg["type"] in ("top", "shirt"):
            made, cov = _top(C, body, cfg, P, H, J, G)
        elif cfg["type"] == "vest":
            made, cov = _top(C, body, cfg, P, H, J, G, vest=True)
        elif cfg["type"] in ("shorts", "trousers"):
            made, cov = _bottoms(C, body, cfg, P, H, J, G)
        elif cfg["type"] == "skirt":
            made, cov = _skirt(C, cfg, P, H, J, G), set()
        elif cfg["type"] == "dress":
            bodice_cfg = dict(cfg)
            bodice_cfg["type"] = "dress"
            bodice_cfg.setdefault("sleeve_length", 0.18)
            bodice_cfg["hem_z_m"] = float(cfg.get("waist_z_m", P["torso"]["levels"][2][0] * H))
            made, cov = _top(C, body, bodice_cfg, P, H, J, G)
            made[0].name = f"garment.{cfg['name']}.bodice"
            made[0]["ps_garment_part"] = "bodice"
            if "bodice" in cfg.get("materials", {}):
                mat = _mat_for(G, cfg, "bodice", H)
                made[0].data.materials.clear()
                G.assign(made[0], mat)
                _tag(made[0], cfg, "bodice", mat)
            made += _skirt(C, cfg, P, H, J, G, part="skirt")
        else:
            made, cov = _footwear(C, body, cfg, P, H, J, G)
        for ob in made:
            _ensure_clearance(body, ob, cfg["ease_m"])
        objects += made
        coverage |= cov
        mask = bool(cfg.get("mask_body", hide_default)) and bool(cov)
        if mask:
            _store_cover(body, cfg["name"], cov)
            masked.append(cfg["name"])
        item_report.append({"name": cfg["name"], "type": cfg["type"], "objects": [o.name for o in objects[before:]],
                            "covered_body_faces": len(cov), "mask_body": mask,
                            "material_presets": sorted({o.get("ps_material_preset", "") for o in objects[before:]})})
    body["ps_garment_mask_items"] = masked
    body["ps_garment_mask_margin_m"] = float(clothing.get("mask_margin_m", 0.015))
    collision = {"enabled": True, "offset_m": 0.002, "radius_m": 0.08, "falloff_m": 0.02, "passes": 3}
    collision.update(clothing.get("collision", {}))
    body["ps_garment_collision"] = collision
    return objects, {"generator": GENERATOR, "items": item_report, "objects": len(objects),
                     "covered_body_faces": len(coverage), "masked_items": masked,
                     "mask_margin_m": body["ps_garment_mask_margin_m"],
                     "hide_body_faces": hide_default, "collision": collision}


def collision_proxy(rig, body):
    """Hidden, never-rendered object sharing the body mesh and deform weights, deformed by the same rig but without
    the garment mask. Collision targets this so hidden (masked) skin still pushes garments outward."""
    name = f"garment.collider.{body.name}"
    proxy = bpy.data.objects.get(name)
    if proxy is None:
        proxy = bpy.data.objects.new(name, body.data)
        for collection in body.users_collection:
            collection.objects.link(proxy)
        proxy.parent = rig
        proxy.matrix_world = body.matrix_world.copy()
        source = next((m for m in body.modifiers if m.type == "ARMATURE"), None)
        mod = proxy.modifiers.new("Armature", "ARMATURE")
        mod.object = rig
        if source is not None:
            mod.use_deform_preserve_volume = source.use_deform_preserve_volume
            mod.use_vertex_groups, mod.use_bone_envelopes = source.use_vertex_groups, source.use_bone_envelopes
    proxy["ps_collision_proxy"] = True
    proxy["ps_collision_source"] = body.name
    proxy.hide_render = True
    proxy.visible_camera = proxy.visible_shadow = False
    proxy.display_type = "WIRE"
    try:
        proxy.hide_set(True)
    except RuntimeError:
        pass
    return proxy


def bind_to_body(rig, body, garments, neighbours=1, max_influences=4, worn=None):
    """Copy normalized nearby body weights to all garment pieces and add their Armature modifiers."""
    if not garments:
        return {"method": "nearest_body_weights/1", "objects": 0, "vertices": 0, "max_source_distance_m": 0.0}
    source_groups = {g.index: g.name for g in body.vertex_groups if not g.name.startswith("ps_")}
    if not source_groups:
        raise ValueError("body must be rigged before garment weight transfer")
    tree = KDTree(len(body.data.vertices))
    world = body.matrix_world
    for v in body.data.vertices:
        tree.insert(world @ v.co, v.index)
    tree.balance()
    max_dist = 0.0
    total = 0
    per_object = {}
    collision_cfg = dict(body.get("ps_garment_collision", {"enabled": True}))
    proxy = collision_proxy(rig, body) if collision_cfg.get("enabled", True) else None
    for ob in garments:
        groups = {name: ob.vertex_groups.new(name=name) for name in source_groups.values()}
        source_hits = []
        source_attr = ob.data.attributes.get("ps_body_vertex")
        anchor = ob.get("ps_weight_anchor")
        anchor_near = tree.find(Vector(anchor))[1] if anchor is not None else None
        for v in ob.data.vertices:
            explicit = source_attr.data[v.index].value if source_attr is not None else None
            if explicit is not None and 0 <= explicit < len(body.data.vertices):
                point = world @ body.data.vertices[explicit].co
                near = [(point, explicit, (ob.matrix_world @ v.co - point).length)]
            elif anchor_near is not None:
                point = world @ body.data.vertices[anchor_near].co
                near = [(point, anchor_near, (ob.matrix_world @ v.co - point).length)]
            else:
                near = tree.find_n(ob.matrix_world @ v.co, min(neighbours, len(body.data.vertices)))
            accum = {}
            nearest = near[0][1]
            max_dist = max(max_dist, near[0][2])
            source_hits.append(nearest)
            for _, index, dist in near:
                factor = 1.0 / max(dist, 1e-6) ** 2
                for g in body.data.vertices[index].groups:
                    if g.group in source_groups:
                        accum[g.group] = accum.get(g.group, 0.0) + factor * g.weight
            chosen = sorted(accum.items(), key=lambda x: x[1], reverse=True)[:max_influences]
            denom = sum(w for _, w in chosen)
            if denom <= 0:
                raise ValueError(f"body vertex near {ob.name}[{v.index}] has no transferable weights")
            for gi, weight in chosen:
                groups[source_groups[gi]].add([v.index], weight / denom, "REPLACE")
        ob.parent = rig
        ob.matrix_parent_inverse = rig.matrix_world.inverted()
        mod = ob.modifiers.new("Armature", "ARMATURE")
        mod.object = rig
        if collision_cfg.get("enabled", True):
            # Post-skinning collision correction: after the Armature modifier, project only the vertex-group
            # weighted vertices (those near visible skin) to the outside of the posed, masked body.
            # A second pass resolves vertices that the first projection moved into an adjacent body part in deep
            # creases (thigh against belly, arm against ribs).
            ob.vertex_groups.new(name=COLLISION_GROUP)
            for k in range(int(collision_cfg.get("passes", 3))):
                collision = ob.modifiers.new(COLLISION_MODIFIER if k == 0 else f"{COLLISION_MODIFIER}.{k + 1}",
                                             "SHRINKWRAP")
                collision.target = proxy
                collision.wrap_method = "NEAREST_SURFACEPOINT"
                collision.wrap_mode = "OUTSIDE"
                collision.offset = float(collision_cfg.get("offset_m", 0.002))
                collision.vertex_group = COLLISION_GROUP
        ob["ps_weight_transfer"] = "nearest_body_weights/1"
        ob["ps_weight_source"] = body.name
        ob["ps_weight_neighbours"] = int(neighbours)
        total += len(ob.data.vertices)
        per_object[ob.name] = {"vertices": len(ob.data.vertices), "nearest_source_vertices": len(set(source_hits))}
    items = sorted({ob.get("ps_garment_item") for ob in garments} if worn is None else set(worn))
    active = set_active_items(body, garments, items, collision_cfg)
    return {"method": "nearest_body_weights/1", "objects": len(garments), "vertices": total,
            "max_source_distance_m": round(max_dist, 6), "collision_proxy": proxy.name if proxy else None,
            "collision": {"method": "shrinkwrap_outside_after_armature/1", **{
                k: (round(v, 6) if isinstance(v, float) else v) for k, v in collision_cfg.items()}},
            "mask": active, "per_object": per_object}
