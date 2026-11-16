"""Shared, character-independent garment construction for ``body_generic/1``.

Coordinates and dimensions come only from the generic body parameters and the
garment spec. The character faces -Y, +Z is up, and +X is its left.
"""
import math
import re

import bmesh
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
    for key in ("thickness_m", "ease_m", "offset_m", "seam_radius_m"):
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
        for key in ("sleeve_length", "length", "height", "flare"):
            if key in raw:
                _number(raw[key], f"garment {name}.{key}", 0.0, 1.0)
        for key in ("thickness_m", "ease_m", "offset_m", "seam_radius_m", "length_m", "height_m", "flare_m"):
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

    main, covered = _shell(body, f"garment.{cfg['name']}.main", selector, ease, thick, C, G)
    objects = []
    main_mat = _mat_for(G, cfg, "main", H)
    _feature(objects, main, cfg, "main", main_mat, G)
    seam_mat = _mat_for(G, cfg, "seam", H)
    bands = cfg.get("bands", {})
    if bands is True:
        bands = {"hem": True, "cuff": True}
    if bands.get("hem"):
        _feature(objects, _torso_ring(G, C, f"garment.{cfg['name']}.band.hem", P, H, hem_z, ease + thick,
                                     cfg["seam_radius_m"] * 1.25), cfg, "band", _mat_for(G, cfg, "band", H), G)
    ridges = int(bands.get("rib_ridges", 0))
    for k in range(ridges):
        z = hem_z + (k + 1) * cfg["seam_radius_m"] * 2.2
        _feature(objects, _torso_ring(G, C, f"garment.{cfg['name']}.rib.hem_{k + 1}", P, H, z, ease + thick,
                                     cfg["seam_radius_m"] * 0.65), cfg, "band", _mat_for(G, cfg, "band", H), G)
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
        r = _leg_radius(P, H, t) + 0.012 * H
        return any((Vector((c.x, c.y, c.z)) - Vector((J[f"hip.{s}"].x, 0, c.z))).length <= r for s in ("L", "R"))

    main, covered = _shell(body, f"garment.{cfg['name']}.main", selector, ease, thick, C, G)
    objects = []
    _feature(objects, main, cfg, "main", _mat_for(G, cfg, "main", H), G)
    bands = cfg.get("bands", {})
    if bands is True:
        bands = {"waist": True, "cuff": True}
    if bands.get("waist"):
        _feature(objects, _torso_ring(G, C, f"garment.{cfg['name']}.band.waist", P, H, waist_z,
                                     ease + thick, cfg["seam_radius_m"] * 1.3),
                 cfg, "band", _mat_for(G, cfg, "band", H), G)
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
        rings.append(G.superellipse_ring(0, 0, z, w + add, front + add, back + add, 2.4, 48))
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
            path = [Vector(rings[k][0 if sx > 0 else 24]) for k in range(len(rings))]
            ob = G.tube(f"garment.{cfg['name']}.seam.side.{side}", path,
                        [cfg["seam_radius_m"]] * len(path), [cfg["seam_radius_m"]] * len(path), C,
                        up_hint=(0, -1, 0), seg=7)
            _feature(objects, ob, cfg, "seam", sm, G)
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


def _delete_body_faces(body, indices):
    if not indices:
        return 0
    bm = bmesh.new()
    bm.from_mesh(body.data)
    bm.faces.ensure_lookup_table()
    doomed = [bm.faces[i] for i in sorted(indices) if i < len(bm.faces)]
    bmesh.ops.delete(bm, geom=doomed, context="FACES")
    loose = [v for v in bm.verts if not v.link_faces]
    if loose:
        bmesh.ops.delete(bm, geom=loose, context="VERTS")
    bm.to_mesh(body.data)
    bm.free()
    body.data.update()
    return len(doomed)


def build(C, body, clothing, P, H, J, G):
    """Build garments before rigging. Returns ``(objects, JSON-safe report)``."""
    validate(clothing)
    objects, coverage, item_report = [], set(), []
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
        item_report.append({"name": cfg["name"], "type": cfg["type"], "objects": [o.name for o in objects[before:]],
                            "material_presets": sorted({o.get("ps_material_preset", "") for o in objects[before:]})})
    hidden = _delete_body_faces(body, coverage) if clothing.get("hide_body_faces", False) else 0
    return objects, {"generator": GENERATOR, "items": item_report, "objects": len(objects),
                     "covered_body_faces": len(coverage), "hidden_body_faces": hidden,
                     "hide_body_faces": bool(clothing.get("hide_body_faces", False))}


def bind_to_body(rig, body, garments, neighbours=1, max_influences=4):
    """Copy normalized nearby body weights to all garment pieces and add their Armature modifiers."""
    if not garments:
        return {"method": "nearest_body_weights/1", "objects": 0, "vertices": 0, "max_source_distance_m": 0.0}
    source_groups = {g.index: g.name for g in body.vertex_groups}
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
        ob["ps_weight_transfer"] = "nearest_body_weights/1"
        ob["ps_weight_source"] = body.name
        ob["ps_weight_neighbours"] = int(neighbours)
        total += len(ob.data.vertices)
        per_object[ob.name] = {"vertices": len(ob.data.vertices), "nearest_source_vertices": len(set(source_hits))}
    return {"method": "nearest_body_weights/1", "objects": len(garments), "vertices": total,
            "max_source_distance_m": round(max_dist, 6), "per_object": per_object}
