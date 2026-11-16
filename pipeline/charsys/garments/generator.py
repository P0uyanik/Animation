"""Shared, character-independent garment construction for ``body_generic/1``.

Coordinates and dimensions come only from the generic body parameters and the
garment spec. The character faces -Y, +Z is up, and +X is its left.
"""
import json
import math
import re

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

from . import drape as cloth


GENERATOR = "garment/1"
ITEM_TYPES = {"top", "shirt", "vest", "shorts", "trousers", "dress", "skirt", "shoes", "boots"}
COLLARS = {"none", "crew", "rib", "shirt", "point", "v", "v-neck", "round"}
EMBROIDERY_STYLES = {"flower", "sprig", "bouquet"}
BUTTON_PLACEMENTS = {"centre", "edge", "waistband", "pockets", "positions"}
CROTCH_TYPES = {"none", "gusset"}
EDGE_STYLES = ("rolled", "piped")

# T-025, proportion-relative distances. Every ease, offset, mask margin and collision distance in a spec (and every
# internal margin that used to be a fraction of the height) is defined on the neutral body_generic proportions at
# 1.0 m (the synthetic test body, ``pipeline/clips/mannequin.json``) and is scaled by the ratio of the local body
# measure to this reference: limb thickness for sleeves, legs and footwear, torso depth for the torso, head height
# for collars. Ratios are rounded to 1e-4, so a body with the reference measures reproduces the T-024 geometry.
REFERENCE_BODY_M = {"arm_root_radius": 0.030, "thigh_radius": 0.045, "torso_depth": 0.125143, "head_height": 0.290}
# T-025, armholes from body measurements. Depth below the shoulder line = (2/pi) x the arm-root circumference
# (ARMHOLE_DEPTH_ROOT_RADII = 4 arm-root radii, the same length); the side cut keeps ARMHOLE_SIDE_SHARE of the local torso half width, but never closer than
# ARMHOLE_ROOT_CLEARANCE arm-root radii to the shoulder joint, so the arm root always passes through the opening.
ARMHOLE_DEPTH_ROOT_RADII = 4.0
ARMHOLE_SIDE_SHARE = 0.58
ARMHOLE_ROOT_CLEARANCE = 1.25
MATERIAL_PRESETS = {
    "felt", "wool yarn", "fleece", "cotton knit", "woven cotton", "denim", "felt hair",
    "buttons/plastic", "glasses/acrylic", "skin-felt", "boot fleece",
}
# T-028: every garment piece whose material preset enables surface fibres gets the shared fibre group
# (materials.builder.add_fibres_geometry, "PS Shared Surface Fibres/1") at clothing.fibres_lod (default "close";
# "off" builds none). The fibre object is a child of its piece, so it follows the rig and the post-skinning collision,
# and is hidden with it when the item is not worn. Fibres are Curves objects: never in the returned garment list.
FIBRE_LODS = ("close", "wide", "off")
FIBRES_PROP = "ps_fibres_source"
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
    if "drape" in defaults:
        cloth.validate(defaults["drape"], "clothing.defaults.drape")
    if defaults.get("edge_finish", "flat") not in cloth.EDGE_FINISHES:
        raise ValueError(f"clothing.defaults.edge_finish must be one of {list(cloth.EDGE_FINISHES)}")
    if clothing.get("fibres_lod", "close") not in FIBRE_LODS:
        raise ValueError(f"clothing.fibres_lod must be one of {list(FIBRE_LODS)}")
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
        for key in ("sleeve_puff_m", "puff_m"):
            if key in raw:
                _number(raw[key], f"garment {name}.{key}", 0.0, 0.1)
        for key in ("sleeve_puff_peak", "puff_inner"):
            if key in raw:
                _number(raw[key], f"garment {name}.{key}", 0.0, 1.0)
        if isinstance(raw.get("collar"), dict):
            for key in ("width_m", "gap_m", "slope", "tip_round", "lift_m"):
                if key in raw["collar"]:
                    _number(raw["collar"][key], f"garment {name}.collar.{key}", 0.0, 1.0)
        bands = raw.get("bands")
        if isinstance(bands, dict) and "cuff_radius_m" in bands:
            _number(bands["cuff_radius_m"], f"garment {name}.bands.cuff_radius_m", 0.0, 0.05)
        if isinstance(bands, dict) and "edge_roll_m" in bands:
            if raw["type"] == "skirt":
                raise ValueError(f"garment {name}.bands.edge_roll_m is not supported on skirts (lofted, no shell)")
            _number(bands["edge_roll_m"], f"garment {name}.bands.edge_roll_m", 0.0, 0.03)
        if isinstance(bands, dict) and bands.get("edge_style", "rolled") not in EDGE_STYLES:
            raise ValueError(f"garment {name}.bands.edge_style must be one of {list(EDGE_STYLES)}")
        if "drape" in raw:
            cloth.validate(raw["drape"], f"garment {name}.drape")
        if raw.get("edge_finish", "flat") not in cloth.EDGE_FINISHES:
            raise ValueError(f"garment {name}.edge_finish must be one of {list(cloth.EDGE_FINISHES)}")
        if "shoulder_width" in raw:
            if raw["type"] not in ("top", "shirt", "vest", "dress"):
                raise ValueError(f"garment {name}.shoulder_width is supported on tops, vests and dresses")
            _number(raw["shoulder_width"], f"garment {name}.shoulder_width", 0.0, 1.0)
        if "crotch" in raw:
            _validate_crotch(raw, name)
        if raw.get("buttons") not in (None, 0) and not isinstance(raw.get("buttons"), int):
            _validate_buttons(raw, name)
        for key in ("shaft_width_m", "toe_volume_m"):
            if key in raw:
                if raw["type"] not in ("shoes", "boots"):
                    raise ValueError(f"garment {name}.{key} is supported on shoes and boots")
                _number(raw[key], f"garment {name}.{key}", 0.0, 0.1)
        if isinstance(raw.get("sole"), dict) and "width_m" in raw["sole"]:
            _number(raw["sole"]["width_m"], f"garment {name}.sole.width_m", 0.0, 0.05)
        if "embroidery" in raw:
            _validate_embroidery(raw, name)
        for part in raw.get("materials", {}):
            _assignment(raw, part)
    return clothing


def _validate_crotch(raw, name):
    crotch = raw["crotch"]
    crotch = {"type": crotch} if isinstance(crotch, str) else crotch
    if raw["type"] not in ("shorts", "trousers"):
        raise ValueError(f"garment {name}.crotch is supported on shorts and trousers")
    if not isinstance(crotch, dict) or crotch.get("type", "gusset") not in CROTCH_TYPES:
        raise ValueError(f"garment {name}.crotch.type must be one of {sorted(CROTCH_TYPES)}")
    for key in ("depth", "width"):
        if key in crotch:
            _number(crotch[key], f"garment {name}.crotch.{key}", 0.0, 1.0)


def _validate_buttons(raw, name):
    b = raw["buttons"]
    if not isinstance(b, dict):
        raise ValueError(f"garment {name}.buttons must be an integer or an object")
    placement = b.get("placement", "centre")
    if placement not in BUTTON_PLACEMENTS:
        raise ValueError(f"garment {name}.buttons.placement must be one of {sorted(BUTTON_PLACEMENTS)}")
    allowed = {"centre": ("top", "shirt", "vest", "dress"), "edge": ("top", "shirt", "vest", "dress"),
               "waistband": ("shorts", "trousers", "skirt"), "pockets": ("vest",),
               "positions": ("top", "shirt", "vest", "dress", "shorts", "trousers")}[placement]
    if raw["type"] not in allowed:
        raise ValueError(f"garment {name}.buttons.placement {placement} is supported on {', '.join(allowed)}")
    if "count" in b and (not isinstance(b["count"], int) or not 0 <= b["count"] <= 16):
        raise ValueError(f"garment {name}.buttons.count must be an integer in [0, 16]")
    if b.get("side", "both") not in ("both", "left", "right"):
        raise ValueError(f"garment {name}.buttons.side must be both, left or right")
    for key in ("radius_m", "inset_m", "drop_m"):
        if key in b:
            _number(b[key], f"garment {name}.buttons.{key}", 0.0, 0.1)
    for key in ("spread", "v0", "v1"):
        if key in b:
            _number(b[key], f"garment {name}.buttons.{key}", 0.0, 1.0)
    if placement == "positions":
        if not isinstance(b.get("positions"), list) or not b["positions"]:
            raise ValueError(f"garment {name}.buttons.positions must be a non-empty list")
        for i, m in enumerate(b["positions"]):
            _number(m.get("u", 0.0), f"garment {name}.buttons.positions[{i}].u", -1.0, 1.0)
            _number(m.get("v", 0.5), f"garment {name}.buttons.positions[{i}].v", 0.0, 1.0)
            if m.get("face", "front") not in ("front", "back"):
                raise ValueError(f"garment {name}.buttons.positions[{i}].face must be front or back")


EMBROIDERY_TARGETS = {
    "top": ("main",), "shirt": ("main",), "vest": ("main", "pocket.L", "pocket.R"),
    "dress": ("main",), "shorts": ("main",), "trousers": ("main",), "skirt": ("main",),
    "shoes": ("main.L", "main.R"), "boots": ("main.L", "main.R"),
}


def _validate_embroidery(raw, name):
    emb = raw["embroidery"]
    targets = EMBROIDERY_TARGETS[raw["type"]]
    if not isinstance(emb, dict) or not isinstance(emb.get("motifs"), list) or not emb["motifs"]:
        raise ValueError(f"garment {name}.embroidery.motifs must be a non-empty list")
    for i, m in enumerate(emb["motifs"]):
        label = f"garment {name}.embroidery.motifs[{i}]"
        if not isinstance(m, dict):
            raise ValueError(f"{label} must be an object")
        _number(m.get("u", 0.0), f"{label}.u", -1.0, 1.0)
        _number(m.get("v", 0.5), f"{label}.v", 0.0, 1.0)
        if m.get("face", "front") not in ("front", "back"):
            raise ValueError(f"{label}.face must be front or back")
        default_target = targets[0]
        if m.get("target", default_target) not in targets:
            raise ValueError(f"{label}.target must be one of {list(targets)} for a {raw['type']}")
        if m.get("style", emb.get("style", "flower")) not in EMBROIDERY_STYLES:
            raise ValueError(f"{label}.style must be one of {sorted(EMBROIDERY_STYLES)}")
        for key in ("size_m", "relief_m"):
            if key in m:
                _number(m[key], f"{label}.{key}", 0.0, 0.2)
    for key in ("size_m", "relief_m"):
        if key in emb:
            _number(emb[key], f"garment {name}.embroidery.{key}", 0.0, 0.2)
    for part in ("embroidery", "embroidery_accent"):
        if part in raw.get("materials", {}):
            continue
        if part == "embroidery" and "material" in emb:
            _assignment({"name": name, "materials": {part: emb["material"]}}, part)
        if part == "embroidery_accent" and "accent_material" in emb:
            _assignment({"name": name, "materials": {part: emb["accent_material"]}}, part)


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
        mat = material_builder.build_material(name, assignment["preset"], assignment["base_color_srgb"],
                                              assignment.get("reference_size_m", reference_size),
                                              assignment.get("overrides"))
        mat["ps_material_assignment"] = json.dumps(
            {**assignment, "reference_size_m": float(assignment.get("reference_size_m", reference_size))},
            sort_keys=True)
        return mat
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


class BodyFit:
    """Local body measures of a ``body_generic/1`` body and the distance scales derived from them (T-025).

    ``arm``, ``leg``, ``torso`` and ``head`` are the ratios of this body's arm-root radius, thigh radius, mean torso
    depth and head height to ``REFERENCE_BODY_M``; ``body`` is the geometric mean of the limb and torso ratios
    (whole-body distances: mask margin, collision). ``at(point)`` gives the ratio of the region a rest-pose point
    belongs to (sleeve, leg/foot or torso)."""

    def __init__(self, P, H, J):
        self.P, self.H, self.J = P, H, J
        levels = P["torso"]["levels"]
        self.measures = {
            "arm_root_radius": P["arm"]["radii"][0] * H,
            "thigh_radius": P["leg"]["radii"][0] * H,
            "torso_depth": sum(f + b for _, _, f, b in levels) / len(levels) * H,
            "head_height": 2.0 * P["head"]["half_height"] * H,
        }
        ratio = {k: round(v / REFERENCE_BODY_M[k], 4) for k, v in self.measures.items()}
        self.arm, self.leg, self.torso, self.head = (ratio["arm_root_radius"], ratio["thigh_radius"],
                                                     ratio["torso_depth"], ratio["head_height"])
        self.body = round((self.arm * self.leg * self.torso) ** (1.0 / 3.0), 4)
        self.hip_z = P["leg"]["hip_z"] * H
        self.arm_root = self.measures["arm_root_radius"]
        self.segments = [(J[f"shoulder.{s}"], J[f"wrist.{s}"]) for s in ("L", "R")]

    def in_sleeve(self, c, t0=0.10, t1=1.0, margin=None):
        margin = 0.012 * self.arm if margin is None else margin
        for a, b in self.segments:
            t, d = _segment(c, a, b)
            if t0 <= t <= t1 and d <= _arm_radius(self.P, self.H, t) + margin:
                return True
        return False

    def at(self, c):
        if self.in_sleeve(c):
            return self.arm
        if c.z < self.hip_z:
            return self.leg
        return self.torso

    def report(self):
        return {"measures_m": {k: round(v, 6) for k, v in self.measures.items()},
                "scale": {"arm": self.arm, "leg": self.leg, "torso": self.torso, "head": self.head, "body": self.body}}


def _face_centroid(body, poly):
    return sum((body.data.vertices[i].co for i in poly.vertices), Vector()) / len(poly.vertices)


def _boundary_loops(faces):
    """Closed boundary loops (vertex index lists) of a face list; edges used by exactly one face."""
    count, nxt = {}, {}
    for f in faces:
        for a, b in zip(f, f[1:] + f[:1]):
            key = (min(a, b), max(a, b))
            count[key] = count.get(key, 0) + 1
    for (a, b), n in count.items():
        if n == 1:
            nxt.setdefault(a, []).append(b)
            nxt.setdefault(b, []).append(a)
    loops, seen = [], set()
    for start in sorted(nxt):
        if start in seen:
            continue
        loop, prev, cur = [start], None, start
        seen.add(start)
        while True:
            options = [v for v in nxt[cur] if v != prev and (v not in seen or v == start)]
            if not options:
                break
            prev, cur = cur, options[0]
            if cur == start:
                break
            loop.append(cur)
            seen.add(cur)
        if len(loop) >= 6:
            loops.append(loop)
    return loops


def _shell(body, name, selector, ease, thickness, C, G, extra=None, scale=None, loops_out=None):
    """Offset body shell. ``extra(co, normal) -> metres`` adds a per-vertex volume (puffed sleeves, bloomers) on top
    of the ease, along the body normal. ``scale(co)`` (T-025) multiplies ease and volume by the local body-measure
    ratio. ``loops_out`` receives the open edges as [(points, normals)] loops (rolled edges)."""
    selected = [p for p in body.data.polygons if selector(_face_centroid(body, p))]
    if not selected:
        raise ValueError(f"garment region {name} selected no body faces")
    source = sorted({i for p in selected for i in p.vertices})
    remap = {old: new for new, old in enumerate(source)}
    verts, eases = [], []
    for i in source:
        v = body.data.vertices[i]
        add = extra(v.co, v.normal) if extra is not None else 0.0
        k = scale(v.co) if scale is not None else 1.0
        e = ease * k if scale is not None else ease
        verts.append(v.co + v.normal * (ease + add) if scale is None else v.co + v.normal * ((ease + add) * k))
        eases.append(e)
    # Concave body areas (especially an armpit) can point an ordinary normal offset toward another part of the
    # surface. Project those vertices to the exterior clearance envelope; the source index still owns its skinning.
    body_bvh = BVHTree.FromPolygons([v.co.copy() for v in body.data.vertices],
                                    [tuple(p.vertices) for p in body.data.polygons], all_triangles=False)
    for k, point in enumerate(verts):
        point = point.copy()
        e = eases[k]
        for _ in range(4):
            location, normal, _, _ = body_bvh.find_nearest(point)
            signed = (point - location).dot(normal)
            if signed >= e - 1e-6:
                break
            point += normal * (e - signed + 1e-5)
        verts[k] = tuple(point)
    faces = [tuple(remap[i] for i in p.vertices) for p in selected]
    if loops_out is not None:
        for loop in _boundary_loops(faces):
            loops_out.append(([Vector(verts[i]) for i in loop], [body.data.vertices[source[i]].normal.copy()
                                                                  for i in loop]))
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
        cloth.register_shell(ob, len(verts), thickness)
    else:
        cloth.register_shell(ob, len(verts), 0.0)
    return ob, {p.index for p in selected}


def _ensure_clearance(body, ob, clearance):
    """Move a procedural piece onto the body's exterior clearance envelope in rest pose. ``clearance`` is metres or
    a function of the rest-pose point (proportion-relative ease)."""
    bvh = BVHTree.FromPolygons([v.co.copy() for v in body.data.vertices],
                               [tuple(p.vertices) for p in body.data.polygons], all_triangles=False)
    changed = False
    for vertex in ob.data.vertices:
        point = ob.matrix_world @ vertex.co
        need = clearance(point) if callable(clearance) else clearance
        for _ in range(5):
            location, normal, _, _ = bvh.find_nearest(point)
            signed = (point - location).dot(normal)
            if signed >= need - 1e-6:
                break
            point += normal * (need - signed + 1e-5)
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


def _bump(s, peak):
    """Smooth 0 -> 1 -> 0 volume profile over s in [0, 1] with its maximum at ``peak``."""
    s = max(0.0, min(1.0, s))
    peak = max(0.05, min(0.95, peak))
    if s <= peak:
        return math.sin(0.5 * math.pi * s / peak)
    return math.cos(0.5 * math.pi * (s - peak) / (1.0 - peak))


def _cuff_radius(cfg, bands, default):
    return float(bands.get("cuff_radius_m", default)) if isinstance(bands, dict) else default


def _round_collar(G, C, body, cfg, P, H, top_z, fit):
    """Flat collar lying on the shoulders, split at the front with rounded tips (round/Peter Pan collar)."""
    collar = cfg.get("collar") if isinstance(cfg.get("collar"), dict) else {}
    ease, thick = cfg["ease_m"] * fit.torso, cfg["thickness_m"]
    width = float(collar.get("width_m", 0.035 * fit.head))
    slope = float(collar.get("slope", 0.55))
    tip = float(collar.get("tip_round", 0.35))  # fraction of each half (by angle) that is rounded
    r_in = P["neck"]["radius"] * H + ease + thick + cfg["seam_radius_m"]
    gap = min(math.pi * 0.4, float(collar.get("gap_m", 0.008 * fit.head)) / max(r_in, 1e-6))
    z0 = top_z + ease * 0.35
    cols, rows = 72, 6
    verts, faces = [], []
    half = math.pi - gap
    for i in range(cols + 1):
        phi = gap + (2 * math.pi - 2 * gap) * i / cols  # 0 = front centre, increasing towards the character's left
        from_tip = min(phi - gap, 2 * math.pi - gap - phi) / max(half, 1e-9)
        q = min(1.0, from_tip / max(tip, 1e-6))
        w = width * math.sqrt(max(0.0, 1.0 - (1.0 - q) ** 2)) if tip > 0 else width
        w = max(w, width * 0.08)
        d = Vector((math.sin(phi), -math.cos(phi), 0.0))
        for k in range(rows + 1):
            r = r_in + w * k / rows
            verts.append(tuple(d * r + Vector((0, 0, z0 - slope * w * k / rows))))
    for i in range(cols):
        for k in range(rows):
            a = i * (rows + 1) + k
            faces.append((a, a + 1, a + rows + 2, a + rows + 1))
    ob = G.new_object(f"garment.{cfg['name']}.collar", verts, faces, C)
    # lift_m: extra clearance so the collar lies out over outer layers (a vest or jacket worn on top).
    _ensure_clearance(body, ob, ease + thick + cfg["seam_radius_m"] + float(collar.get("lift_m", 0.0)) * fit.torso)
    mod = ob.modifiers.new("garment_thickness", "SOLIDIFY")
    mod.thickness, mod.offset = max(thick, 0.0015), 1.0
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.modifier_apply(modifier=mod.name)
    ob.select_set(False)
    return ob


_UNIT_SPHERE = None


def _unit_sphere():
    global _UNIT_SPHERE
    if _UNIT_SPHERE is None:
        import bmesh
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=6, radius=1.0)
        _UNIT_SPHERE = ([v.co.copy() for v in bm.verts], [tuple(v.index for v in f.verts) for f in bm.faces])
        bm.free()
    return _UNIT_SPHERE


def _surface_frame(bvh, x, z, face, what):
    """Ray-cast a front/back placement (x, z) onto a garment piece; returns (point, tangent, bitangent, normal)."""
    sign = -1.0 if face == "front" else 1.0
    hit = bvh.ray_cast(Vector((x, sign * 2.0, z)), Vector((0, -sign, 0)))
    if hit[0] is None:
        raise ValueError(f"{what} misses the garment")
    n = hit[1].normalized()
    if n.y * sign < 0:
        n = -n
    up = Vector((0, 0, 1))
    t = up.cross(n).normalized() if abs(n.z) < 0.95 else Vector((1, 0, 0))
    b = n.cross(t).normalized()
    return hit[0], t, b, n


def _bbox_world(ob):
    pts = [ob.matrix_world @ v.co for v in ob.data.vertices]
    return (Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))),
            Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))))


def _embroidery(G, C, cfg, targets, z_range, P, H):
    """Raised embroidery motifs on the outside of garment pieces. ``targets`` maps a target name (``main``,
    ``pocket.L``, ``main.L``, ...) to its object. On a torso or bottoms ``main`` each motif sits at (u, v): u is the
    signed fraction of the local half width (+ = the character's left), v the fraction between the hem and the top.
    On any other target (pockets, boot shells, skirts) u and v are fractions of the piece's rest bounding box.
    Styles: ``flower`` (petals around a centre knot), ``sprig`` (leaves along a short stem) and ``bouquet`` (three
    flowers with leaves, dense enough to read at 640 px). Returns two meshes: main stitches (part ``embroidery``) and
    accents (part ``embroidery_accent``)."""
    emb = cfg["embroidery"]
    sv, sf = _unit_sphere()
    deps = bpy.context.evaluated_depsgraph_get()
    bvhs = {}
    z_lo, z_hi = z_range
    main_v, main_f, acc_v, acc_f = [], [], [], []

    def blob(vs, fs, centre, t, b, n, sx, sy, sz):
        base = len(vs)
        for p in sv:
            vs.append(tuple(centre + t * (p.x * sx) + b * (p.y * sy) + n * (p.z * sz)))
        fs.extend(tuple(base + i for i in f) for f in sf)

    def flower(c, t, b, n, r, relief, petals, leaves, leaf_dir=-0.5 * math.pi):
        for k in range(petals):
            a = 2 * math.pi * k / petals
            d = t * math.cos(a) + b * math.sin(a)
            e = d.cross(n).normalized()
            blob(main_v, main_f, c + d * (r * 0.55), d, e, n, r * 0.45, r * 0.24, relief)
        blob(acc_v, acc_f, c + n * (relief * 0.4), t, b, n, r * 0.22, r * 0.22, relief * 1.1)
        for k in range(leaves):
            a = leaf_dir + (k - 0.5 * (leaves - 1)) * 0.9
            d = t * math.cos(a) + b * math.sin(a)
            blob(acc_v, acc_f, c + d * (r * 1.15), d, d.cross(n).normalized(), n, r * 0.38, r * 0.15, relief * 0.8)

    placed = []
    for m in emb["motifs"]:
        size = float(m.get("size_m", emb.get("size_m", 0.03 * H)))
        relief = float(m.get("relief_m", emb.get("relief_m", 0.0015)))
        style = m.get("style", emb.get("style", "flower"))
        petals = int(m.get("petals", emb.get("petals", 5)))
        face = m.get("face", "front")
        target = m.get("target", next(iter(targets)))
        if target not in targets:
            raise ValueError(f"garment {cfg['name']}: embroidery target {target} does not exist")
        shell = targets[target]
        if target not in bvhs:
            bvhs[target] = BVHTree.FromObject(shell, deps)
        bvh = bvhs[target]
        if target == "main" and cfg["type"] not in ("shoes", "boots", "skirt"):
            z = z_lo + (z_hi - z_lo) * float(m.get("v", 0.5))
            w, _, _ = _torso_dims(P, H, z)
            x = float(m.get("u", 0.0)) * w
        else:
            lo, hi = _bbox_world(shell)
            x = (lo.x + hi.x) * 0.5 + float(m.get("u", 0.0)) * (hi.x - lo.x) * 0.5
            z = lo.z + (hi.z - lo.z) * float(m.get("v", 0.5))
        point, t, b, n = _surface_frame(bvh, x, z, face, f"garment {cfg['name']}: embroidery motif at "
                                                         f"u={m.get('u')} v={m.get('v')} ({target})")
        rot = math.radians(float(m.get("rotation_deg", 0.0)))
        t, b = t * math.cos(rot) + b * math.sin(rot), b * math.cos(rot) - t * math.sin(rot)
        c = point + n * (relief * 0.6)
        r = size * 0.5
        leaves = int(m.get("leaves", emb.get("leaves", 2)))
        if style == "flower":
            flower(c, t, b, n, r, relief, petals, leaves)
        elif style == "bouquet":
            # Three flowers in a tight cluster, leaves fanning out below and to the sides, a stem knot in the gaps.
            for dx, dy, k, lead in ((0.0, 0.30, 0.48, 0), (-0.42, -0.12, 0.40, 1), (0.42, -0.12, 0.40, 2)):
                fc = c + t * (dx * r) + b * (dy * r)
                flower(fc, t, b, n, r * k, relief, petals, 0)
            for k in range(max(2, leaves)):
                a = -0.5 * math.pi + (k - 0.5 * (max(2, leaves) - 1)) * 0.75
                d = t * math.cos(a) + b * math.sin(a)
                blob(acc_v if k % 2 else main_v, acc_f if k % 2 else main_f, c + d * (r * 0.72) - b * (r * 0.15),
                     d, d.cross(n).normalized(), n, r * 0.30, r * 0.12, relief * 0.8)
            blob(main_v, main_f, c - b * (r * 0.05), t, b, n, r * 0.12, r * 0.12, relief * 0.9)
        else:  # sprig: a short stem with leaves alternating along it
            leaves = max(2, int(m.get("leaves", emb.get("leaves", 4))))
            blob(main_v, main_f, c, b, t, n, r, r * 0.07, relief * 0.6)
            for k in range(leaves):
                s = -0.8 + 1.6 * k / (leaves - 1)
                side = 1 if k % 2 else -1
                d = (b * 0.6 + t * side).normalized()
                blob(acc_v if k % 2 else main_v, acc_f if k % 2 else main_f, c + b * (s * r) + d * (r * 0.28),
                     d, d.cross(n).normalized(), n, r * 0.30, r * 0.13, relief * 0.8)
        entry = {"u": m.get("u", 0.0), "v": m.get("v", 0.5), "face": face, "style": style,
                 "at_m": [round(v, 4) for v in point]}
        if "target" in m:
            entry["target"] = target
        placed.append(entry)
    out = []
    if main_v:
        out.append(("embroidery", G.new_object(f"garment.{cfg['name']}.embroidery", main_v, main_f, C)))
    if acc_v:
        out.append(("embroidery_accent", G.new_object(f"garment.{cfg['name']}.embroidery_accent", acc_v, acc_f, C)))
    return out, placed


def _emb_assignment(cfg, part):
    """Embroidery materials: materials.<part>, else embroidery.material / accent_material, else the garment's band."""
    emb = cfg.get("embroidery", {})
    if part in cfg.get("materials", {}):
        return cfg
    src = emb.get("material") if part == "embroidery" else emb.get("accent_material", emb.get("material"))
    if src is None:
        return cfg
    return {**cfg, "materials": {**cfg.get("materials", {}), part: src}}


def _add_embroidery(objects, G, C, cfg, targets, z_range, P, H):
    if not cfg.get("embroidery"):
        return
    if not isinstance(targets, dict):
        targets = {"main": targets}
    pieces, placed = _embroidery(G, C, cfg, targets, z_range, P, H)
    for part, ob in pieces:
        ob["ps_embroidery_motifs"] = len(placed)
        _feature(objects, ob, cfg, part, _mat_for(G, _emb_assignment(cfg, part), part, H), G)
    cfg["_embroidery_report"] = placed


_UNIT_BUTTON = None


def _button(G, C, name, point, t, b, n, radius):
    """Flattened button oriented on the garment surface (local frame t, b, n)."""
    global _UNIT_BUTTON
    if _UNIT_BUTTON is None:
        import bmesh
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=8, radius=1.0)
        _UNIT_BUTTON = ([v.co.copy() for v in bm.verts], [tuple(v.index for v in f.verts) for f in bm.faces])
        bm.free()
    sv, sf = _UNIT_BUTTON
    centre = point + n * (radius * 0.45 * 0.8)
    verts = [tuple(centre + t * (p.x * radius) + b * (p.z * radius) + n * (p.y * radius * 0.45)) for p in sv]
    return G.new_object(name, verts, sf, C)


def _placed_buttons(objects, G, C, cfg, H, fit, bvh_main, points, what):
    """Buttons at explicit (x, z, face, bvh) placements, each projected onto its garment piece."""
    buttons = cfg["buttons"]
    bm = _mat_for(G, cfg, "buttons", H)
    radius = float(buttons.get("radius_m", 0.006 * fit.torso))
    report = []
    for k, (x, z, face, bvh) in enumerate(points):
        point, t, b, n = _surface_frame(bvh or bvh_main, x, z, face, f"garment {cfg['name']}: {what} button {k + 1}")
        ob = _button(G, C, f"garment.{cfg['name']}.button.{k + 1}", point, t, b, n, radius)
        ob["ps_weight_anchor"] = tuple(point - n * (cfg["ease_m"] + cfg["thickness_m"]))
        _feature(objects, ob, cfg, "buttons", bm, G)
        report.append([round(v, 4) for v in point])
    cfg["_buttons_report"] = {"placement": buttons.get("placement", "centre"), "at_m": report}


def _spread(count, lo, hi):
    return [(lo + hi) * 0.5] if count == 1 else [lo + (hi - lo) * k / (count - 1) for k in range(count)]


def _smooth_loop(points, iterations):
    pts = [p.copy() for p in points]
    n = len(pts)
    for _ in range(iterations):
        pts = [pts[i] * 0.5 + (pts[i - 1] + pts[(i + 1) % n]) * 0.25 for i in range(n)]
    out = [pts[0]]
    for p in pts[1:]:
        if (p - out[-1]).length > 1e-4:
            out.append(p)
    return out


def _armhole_edge(fit, cfg, shoulder_z, arm_bottom, neck_r):
    """Side cut x(z, w) of a torso shell's armhole (T-025): ARMHOLE_SIDE_SHARE of the local half width, kept clear
    of the arm root; ``shoulder_width`` (0-1) widens the strap towards the shoulder joint at the shoulder line."""
    joint_x = fit.P["shoulder"]["joint_x"] * fit.H
    root_x = joint_x - ARMHOLE_ROOT_CLEARANCE * fit.arm_root
    sw = cfg.get("shoulder_width")
    strap_x = None if sw is None else neck_r + float(sw) * (joint_x - neck_r)

    def edge(z, w):
        base = min(ARMHOLE_SIDE_SHARE * w, root_x)
        if strap_x is None or strap_x <= base:
            return base
        u = max(0.0, min(1.0, (z - arm_bottom) / max(shoulder_z - arm_bottom, 1e-9)))
        return base + (strap_x - base) * u * u * (3 - 2 * u)
    return edge


def _edge_rolls(objects, G, C, cfg, H, loops, thick, bands, prefix="edge"):
    """Rolled edge or piping along every open edge of a shell (neckline, front opening, hem, armholes, sleeve ends,
    waist, leg openings, boot tops). ``rolled`` (default, T-025): the cloth turned over, a soft tube centred just
    outside the panel edge. ``piped`` (T-034): a cord sewn onto the edge, centred on the rim (material part
    ``piping``, else ``edge``/``band``/``main``)."""
    roll = float(bands.get("edge_roll_m", 0.0)) if isinstance(bands, dict) else 0.0
    if roll <= 0 or not loops:
        return
    style = bands.get("edge_style", "rolled")
    mats = cfg.get("materials", {})
    order = (("piping",) if style == "piped" else ()) + ("edge", "band")
    part = next((p for p in order if p in mats), "main")
    edge_mat = _mat_for(G, cfg, part, H)
    lift = thick * 0.5 + roll * (0.6 if style == "rolled" else 0.0)
    for k, (pts, normals) in enumerate(sorted(loops, key=lambda lp: -len(lp[0]))):
        path = _smooth_loop([p + n * lift for p, n in zip(pts, normals)], 6)
        if len(path) < 6:
            continue
        ob = _closed_tube(G, C, f"garment.{cfg['name']}.{prefix}.{k + 1}", path, roll)
        _feature(objects, ob, cfg, "edge", edge_mat, G)


def _top(C, body, cfg, P, H, J, G, fit, vest=False):
    ease, thick = cfg["ease_m"], cfg["thickness_m"]
    shell_ease = ease + float(cfg.get("articulation_allowance_m", 0.0))
    front_rise = float(cfg.get("front_articulation_rise_m", 0.0)) * fit.torso
    levels = P["torso"]["levels"]
    hem_z = float(cfg.get("hem_z_m", levels[2][0] * H))
    top_z = max(P["neck"]["base_z"], P["torso"]["levels"][-1][0]) * H
    sleeve = 0.0 if vest else float(cfg.get("sleeve_length", 0.45))
    arm_segments = fit.segments
    opening = float(cfg.get("open_front_m", 0.022 if vest else 0.0)) * fit.torso
    shoulder_z = P["shoulder"]["z"] * H
    arm_bottom = shoulder_z - ARMHOLE_DEPTH_ROOT_RADII * fit.arm_root
    edge = _armhole_edge(fit, cfg, shoulder_z, arm_bottom, P["neck"]["radius"] * H)
    torso_margin = 0.015 * fit.torso

    def selector(c):
        torso = hem_z <= c.z <= top_z
        if torso:
            w, front, back = _torso_dims(P, H, c.z)
            torso = abs(c.x) <= w + torso_margin and -front - torso_margin <= c.y <= back + torso_margin
            # Leave an actual armhole. A shell copied from the underarm concavity is trapped when the arm lowers.
            if c.z > arm_bottom and abs(c.x) > edge(c.z, w):
                torso = False
            if vest and torso and c.y < -front * 0.35 and abs(c.x) < opening:
                torso = False
        return torso or (sleeve > 0 and fit.in_sleeve(c, 0.10, sleeve))

    puff = float(cfg.get("sleeve_puff_m", 0.0)) if sleeve > 0 else 0.0
    peak = float(cfg.get("sleeve_puff_peak", 0.6))
    start = 0.10

    def sleeve_volume(c, normal):
        if puff <= 0:
            return 0.0
        best = 0.0
        for a, b in arm_segments:
            t, d = _segment(c, a, b)
            if start <= t <= sleeve and d <= _arm_radius(P, H, t) + 0.012 * fit.arm:
                best = max(best, puff * _bump((t - start) / max(sleeve - start, 1e-6), peak))
        return best

    bands = cfg.get("bands", {})
    if bands is True:
        bands = {"hem": True, "cuff": True}
    roll = float(bands.get("edge_roll_m", 0.0))
    loops = [] if roll > 0 else None
    main, covered = _shell(body, f"garment.{cfg['name']}.main", selector, shell_ease, thick, C, G,
                           extra=sleeve_volume if puff > 0 else None, scale=fit.at, loops_out=loops)
    _front_articulation_rise(main, hem_z, 0.20 * fit.torso, front_rise, upper_only=True)
    objects = []
    main_mat = _mat_for(G, cfg, "main", H)
    _feature(objects, main, cfg, "main", main_mat, G)
    seam_mat = _mat_for(G, cfg, "seam", H)
    te, ae = ease * fit.torso, ease * fit.arm
    if bands.get("hem"):
        hem_band = _torso_ring(G, C, f"garment.{cfg['name']}.band.hem", P, H, hem_z, te + thick + 0.004 * fit.torso,
                               cfg["seam_radius_m"] * 1.25)
        _front_articulation_rise(hem_band, hem_z, 0.10 * fit.torso, front_rise, upper_only=True)
        _feature(objects, hem_band, cfg, "band", _mat_for(G, cfg, "band", H), G)
    ridges = int(bands.get("rib_ridges", 0))
    for k in range(ridges):
        z = hem_z + (k + 1) * cfg["seam_radius_m"] * 2.2
        ridge = _torso_ring(G, C, f"garment.{cfg['name']}.rib.hem_{k + 1}", P, H, z, te + thick + 0.004 * fit.torso,
                            cfg["seam_radius_m"] * 0.65)
        _front_articulation_rise(ridge, hem_z, 0.10 * fit.torso, front_rise, upper_only=True)
        _feature(objects, ridge, cfg, "band", _mat_for(G, cfg, "band", H), G)
    if sleeve > 0 and bands.get("cuff"):
        for side in ("L", "R"):
            a, b = J[f"shoulder.{side}"], J[f"wrist.{side}"]
            centre = a.lerp(b, sleeve)
            cr = _cuff_radius(cfg, bands, cfg["seam_radius_m"] * 1.25)
            ob = _limb_ring(G, C, f"garment.{cfg['name']}.band.cuff.{side}", centre, b - a,
                            _arm_radius(P, H, sleeve), ae + thick + max(0.0, cr - cfg["seam_radius_m"] * 1.25), cr)
            _feature(objects, ob, cfg, "band", _mat_for(G, cfg, "band", H), G)
    _edge_rolls(objects, G, C, cfg, H, loops, thick, bands)
    if cfg.get("seam_lines"):
        seam_top_z = min(top_z, arm_bottom)
        for sx, side in ((1, "L"), (-1, "R")):
            path = []
            for k in range(9):
                z = hem_z + (seam_top_z - hem_z) * k / 8
                w, _, _ = _torso_dims(P, H, z)
                path.append(Vector((sx * (w + te + thick), 0, z)))
            ob = G.tube(f"garment.{cfg['name']}.seam.side.{side}", path,
                        [cfg["seam_radius_m"]] * len(path), [cfg["seam_radius_m"]] * len(path), C,
                        up_hint=(0, -1, 0), seg=7, cap_start="round", cap_end="round")
            _feature(objects, ob, cfg, "seam", seam_mat, G)
    collar = cfg.get("collar", "none")
    collar = collar.get("type", "none") if isinstance(collar, dict) else collar
    if collar in ("crew", "rib"):
        r = P["neck"]["radius"] * H + te + thick + cfg["seam_radius_m"]
        collar_z = top_z + te * 0.35
        pts = [Vector((math.cos(2 * math.pi * k / 48) * r, math.sin(2 * math.pi * k / 48) * r, collar_z)) for k in range(48)]
        _feature(objects, _closed_tube(G, C, f"garment.{cfg['name']}.collar", pts, cfg["seam_radius_m"] * 1.4),
                 cfg, "band", _mat_for(G, cfg, "band", H), G)
    elif collar == "round":
        _feature(objects, _round_collar(G, C, body, cfg, P, H, top_z, fit), cfg, "collar",
                 _mat_for(G, cfg, "collar" if "collar" in cfg.get("materials", {}) else "main", H), G)
    elif collar in ("v", "v-neck", "shirt", "point"):
        r = P["neck"]["radius"] * H + te + thick
        drop = float(cfg.get("collar_drop_m", (0.045 if collar in ("v", "v-neck") else 0.032) * fit.torso))
        collar_z = top_z + te * 0.2
        _, front_top, _ = _torso_dims(P, H, top_z)
        _, front_low, _ = _torso_dims(P, H, top_z - drop)
        y_top = -(max(r, front_top) + te + thick + cfg["seam_radius_m"] * 2)
        y_low = -(front_low + te + thick + cfg["seam_radius_m"] * 2)
        pts = [Vector((-r, y_top, collar_z)), Vector((0, y_low, top_z - drop)), Vector((r, y_top, collar_z))]
        ob = G.tube(f"garment.{cfg['name']}.collar", pts, [cfg["seam_radius_m"] * 1.5] * 3,
                    [cfg["seam_radius_m"] * 1.5] * 3, C, up_hint=(0, -1, 0), seg=8)
        _feature(objects, ob, cfg, "band", _mat_for(G, cfg, "band", H), G)
    buttons = cfg.get("buttons", 0)
    buttons = {"count": buttons} if isinstance(buttons, int) else (buttons or {})
    cfg["buttons"] = buttons
    count = int(buttons.get("count", 0))
    placement = buttons.get("placement", "centre")
    if count and placement == "centre":
        bm = _mat_for(G, cfg, "buttons", H)
        radius = float(buttons.get("radius_m", 0.006 * fit.torso))
        z0, z1 = hem_z + 0.07 * fit.torso, top_z - 0.07 * fit.torso
        for k in range(count):
            z = (z0 + z1) * 0.5 if count == 1 else z0 + (z1 - z0) * k / (count - 1)
            _, front, _ = _torso_dims(P, H, z)
            ob = G.uv_sphere(f"garment.{cfg['name']}.button.{k + 1}", (0, -front - te - thick - radius, z),
                             1.0, C, 16, 8, (radius, radius * 0.45, radius))
            ob["ps_weight_anchor"] = (0, -front, z)
            _feature(objects, ob, cfg, "buttons", bm, G)
    pockets = {}
    if vest and cfg.get("pockets", True):
        pm = _mat_for(G, cfg, "pockets", H)
        pc = cfg.get("pockets") if isinstance(cfg.get("pockets"), dict) else {}
        pw, ph, pd = (float(pc.get("width_m", 0.035 * fit.torso)), float(pc.get("height_m", 0.032 * fit.torso)),
                      float(pc.get("depth_m", 0.004 * fit.torso)))
        z = hem_z + float(pc.get("above_hem_m", 0.055)) * fit.torso
        w, front, _ = _torso_dims(P, H, z)
        for sx, side in ((1, "L"), (-1, "R")):
            centre = (sx * min(w * 0.5, w - pw), -front - te - thick - pd, z)
            ob = G.uv_sphere(f"garment.{cfg['name']}.pocket.{side}", centre, 1.0, C, 20, 10,
                             (pw, pd, ph))
            ob["ps_weight_anchor"] = (centre[0], -front, centre[2])
            _feature(objects, ob, cfg, "pockets", pm, G)
            pockets[f"pocket.{side}"] = ob
    if count and placement != "centre":
        deps = bpy.context.evaluated_depsgraph_get()
        bvh = BVHTree.FromObject(main, deps)
        side = buttons.get("side", "both")
        sides = [s for s, name in ((1, "left"), (-1, "right")) if side in ("both", name)]
        if placement == "edge":
            # Along the front edge(s) of an open garment, inset from the opening.
            radius = float(buttons.get("radius_m", 0.006 * fit.torso))
            inset = float(buttons.get("inset_m", 1.8 * radius / fit.torso)) * fit.torso
            z_lo = hem_z + float(buttons.get("v0", 0.18)) * (arm_bottom - hem_z)
            z_hi = hem_z + float(buttons.get("v1", 0.95)) * (arm_bottom - hem_z)
            points = [(sx * (max(opening, 0.0) + inset), z, "front", None)
                      for sx in sides for z in reversed(_spread(count, z_lo, z_hi))]
        elif placement == "pockets":
            points = []
            for s in sides:
                ob = pockets.get("pocket.L" if s > 0 else "pocket.R")
                if ob is None:
                    continue
                lo, hi = _bbox_world(ob)
                pb = BVHTree.FromObject(ob, deps)
                for x in _spread(count, lo.x + (hi.x - lo.x) * 0.3, hi.x - (hi.x - lo.x) * 0.3):
                    points.append((x, lo.z + (hi.z - lo.z) * float(buttons.get("v1", 0.78)), "front", pb))
        else:  # positions
            points = []
            for m in buttons["positions"]:
                z = hem_z + (top_z - hem_z) * float(m.get("v", 0.5))
                points.append((float(m.get("u", 0.0)) * _torso_dims(P, H, z)[0], z, m.get("face", "front"), None))
        _placed_buttons(objects, G, C, cfg, H, fit, bvh, points, placement)
    _add_embroidery(objects, G, C, cfg, {"main": main, **pockets}, (hem_z, top_z), P, H)
    return objects, covered


def _gusset(G, C, cfg, P, H, J, fit, bottom_z, hip_z, ankle_z, puff, inner):
    """Crotch gusset (T-025): a hammock panel between the leg panels, from just above the crotch down to ``depth``
    of the leg opening, so no gap shows between the legs from the front or back. Its sides are buried in the leg
    panels; ``width`` is its front/back reach as a share of the leg panel radius."""
    crotch = cfg["crotch"] if isinstance(cfg["crotch"], dict) else {"type": cfg["crotch"]}
    r0 = _leg_radius(P, H, 0.0)
    crotch_z = hip_z - r0
    depth = float(crotch.get("depth", 0.6)) * max(0.0, crotch_z - bottom_z)
    t = (hip_z - crotch_z) / max(hip_z - ankle_z, 1e-9)
    leg_r = _leg_radius(P, H, t)
    ease = cfg["ease_m"] * fit.leg
    reach = float(crotch.get("width", 0.85)) * (leg_r + ease + puff * inner * fit.leg)
    hip_x = abs(J["hip.L"].x)
    xe = max(1e-3, hip_x - leg_r + 0.6 * leg_r)
    z_top = crotch_z + 0.25 * r0
    z_bottom = crotch_z - depth
    nx, nphi = 16, 18
    verts, faces = [], []
    for i in range(nx + 1):
        x = -xe + 2 * xe * i / nx
        for j in range(nphi + 1):
            phi = math.pi * j / nphi
            verts.append((x, -reach * math.cos(phi), z_top - (z_top - z_bottom) * math.sin(phi)))
    for i in range(nx):
        for j in range(nphi):
            a = i * (nphi + 1) + j
            faces.append((a, a + nphi + 1, a + nphi + 2, a + 1))
    ob = G.new_object(f"garment.{cfg['name']}.gusset", verts, faces, C)
    if cfg["thickness_m"] > 0:
        mod = ob.modifiers.new("garment_thickness", "SOLIDIFY")
        mod.thickness, mod.offset = cfg["thickness_m"], 1.0
        bpy.context.view_layer.objects.active = ob
        ob.select_set(True)
        bpy.ops.object.modifier_apply(modifier=mod.name)
        ob.select_set(False)
    cfg["_gusset_report"] = {"crotch_z_m": round(crotch_z, 4), "bottom_z_m": round(z_bottom, 4),
                             "reach_m": round(reach, 4), "half_width_m": round(xe, 4)}
    return ob


def _bottoms(C, body, cfg, P, H, J, G, fit):
    ease, thick = cfg["ease_m"], cfg["thickness_m"]
    shell_ease = ease + float(cfg.get("articulation_allowance_m", 0.0))
    front_rise = float(cfg.get("front_articulation_rise_m", 0.0)) * fit.torso
    is_short = cfg["type"] == "shorts"
    length = float(cfg.get("length", 0.36 if is_short else 0.92))
    hip_z, ankle_z = P["leg"]["hip_z"] * H, P["leg"]["ankle_z"] * H
    bottom_z = float(cfg.get("length_m", length * (hip_z - ankle_z)))
    bottom_z = hip_z - bottom_z if "length_m" in cfg else hip_z - length * (hip_z - ankle_z)
    waist_z = float(cfg.get("waist_z_m", P["torso"]["levels"][2][0] * H))
    tm, lm = 0.012 * fit.torso, 0.012 * fit.leg

    def selector(c):
        if not bottom_z <= c.z <= waist_z:
            return False
        if c.z >= hip_z:
            w, front, back = _torso_dims(P, H, c.z)
            return abs(c.x) <= w + tm and -front - tm <= c.y <= back + tm
        t = (hip_z - c.z) / max(hip_z - ankle_z, 1e-9)
        if t > length + 0.04:
            return False
        # Hip band (T-025): the merged body surface below the hip line, one thigh radius deep, across the whole hip
        # (crotch bridge and the hip front/back/sides). Selecting only between the leg centres left holes at the
        # front and back of the hip, where the hip is deeper than a thigh radius; volume (bloomers) opened them.
        if c.z >= hip_z - _leg_radius(P, H, 0.0):
            w, front, back = _torso_dims(P, H, hip_z)
            if abs(c.x) <= w + tm and -front - tm <= c.y <= back + tm:
                return True
        r = _leg_radius(P, H, t) + lm
        return any((Vector((c.x, c.y, c.z)) - Vector((J[f"hip.{s}"].x, 0, c.z))).length <= r for s in ("L", "R"))

    puff = float(cfg.get("puff_m", 0.0))
    inner = float(cfg.get("puff_inner", 0.35))
    at_hip = math.sin(0.25 * math.pi)

    def bloomer_volume(c, normal):
        """Bloomers: volume grows from the waist to the seat, peaks in the upper leg and gathers to 0 at the cuff;
        surfaces facing the other leg get ``puff_inner`` of it."""
        if c.z >= hip_z:
            f = at_hip * max(0.0, min(1.0, (waist_z - c.z) / max(waist_z - hip_z, 1e-9)))
        else:
            s = (hip_z - c.z) / max(hip_z - bottom_z, 1e-9)
            f = math.sin(math.pi * (0.25 + 0.75 * max(0.0, min(1.0, s))))
        facing_in = max(0.0, -normal.x * math.copysign(1.0, c.x)) if abs(c.x) > 1e-6 else 0.0
        return puff * f * (1.0 - (1.0 - inner) * facing_in)

    roll_loops = [] if float((cfg.get("bands") or {}).get("edge_roll_m", 0.0) if isinstance(cfg.get("bands"), dict)
                             else 0.0) > 0 else None
    main, covered = _shell(body, f"garment.{cfg['name']}.main", selector, shell_ease, thick, C, G,
                           extra=bloomer_volume if puff > 0 else None, scale=fit.at, loops_out=roll_loops)
    _front_articulation_rise(main, hip_z, 0.20 * fit.torso, front_rise)
    _front_centre_ease(main, hip_z, 0.12 * fit.torso, float(cfg.get("front_centre_ease_m", 0.0)) * fit.torso,
                       abs(J["hip.L"].x) * 0.75)
    objects = []
    _feature(objects, main, cfg, "main", _mat_for(G, cfg, "main", H), G)
    te, le = ease * fit.torso, ease * fit.leg
    bands = cfg.get("bands", {})
    if bands is True:
        bands = {"waist": True, "cuff": True}
    crotch = cfg.get("crotch", "none")
    if (crotch.get("type", "gusset") if isinstance(crotch, dict) else crotch) == "gusset":
        gusset = _gusset(G, C, cfg, P, H, J, fit, bottom_z, hip_z, ankle_z, puff, inner)
        _feature(objects, gusset, cfg, "gusset", _mat_for(G, cfg, "gusset", H), G)
    if bands.get("waist"):
        waist_band = _torso_ring(G, C, f"garment.{cfg['name']}.band.waist", P, H, waist_z,
                                 te + thick + 0.004 * fit.torso, cfg["seam_radius_m"] * 1.3)
        _front_articulation_rise(waist_band, hip_z, 0.10 * fit.torso, front_rise)
        _feature(objects, waist_band, cfg, "band", _mat_for(G, cfg, "band", H), G)
    if cfg.get("cuff") or bands.get("cuff"):
        t = max(0.0, min(1.0, (hip_z - bottom_z) / max(hip_z - ankle_z, 1e-9)))
        for side in ("L", "R"):
            centre = Vector((J[f"hip.{side}"].x, 0, bottom_z))
            cr = _cuff_radius(cfg, bands, cfg["seam_radius_m"] * 1.35)
            ob = _limb_ring(G, C, f"garment.{cfg['name']}.band.cuff.{side}", centre, (0, 0, -1),
                            _leg_radius(P, H, t), le + thick + max(0.0, cr - cfg["seam_radius_m"] * 1.35), cr)
            _feature(objects, ob, cfg, "band", _mat_for(G, cfg, "band", H), G)
    if cfg.get("seam_lines"):
        sm = _mat_for(G, cfg, "seam", H)
        for sx, side in ((1, "L"), (-1, "R")):
            path = []
            for k in range(9):
                z = bottom_z + (waist_z - bottom_z) * k / 8
                if z < hip_z:
                    t = (hip_z - z) / max(hip_z - ankle_z, 1e-9)
                    x = abs(J[f"hip.{side}"].x) + _leg_radius(P, H, t) + le + thick
                else:
                    x = _torso_dims(P, H, z)[0] + te + thick
                path.append(Vector((sx * x, 0, z)))
            ob = G.tube(f"garment.{cfg['name']}.seam.side.{side}", path,
                        [cfg["seam_radius_m"]] * len(path), [cfg["seam_radius_m"]] * len(path), C,
                        up_hint=(0, -1, 0), seg=7)
            _feature(objects, ob, cfg, "seam", sm, G)
    buttons = cfg.get("buttons", 0)
    buttons = {"count": buttons, "placement": "waistband"} if isinstance(buttons, int) else (buttons or {})
    cfg["buttons"] = buttons
    count = int(buttons.get("count", 0))
    if count:
        bvh = BVHTree.FromObject(main, bpy.context.evaluated_depsgraph_get())
        radius = float(buttons.get("radius_m", 0.006 * fit.torso))
        if buttons.get("placement", "waistband") == "waistband":
            # Across the front of the waistband, just below its top edge.
            drop = float(buttons.get("drop_m", 1.7 * radius / fit.torso)) * fit.torso
            spread = float(buttons.get("spread", 0.5))
            w = _torso_dims(P, H, waist_z - drop)[0]
            points = [(u * w, waist_z - drop, "front", None) for u in _spread(count, -spread, spread)]
        else:
            points = []
            for m in buttons["positions"]:
                z = bottom_z + (waist_z - bottom_z) * float(m.get("v", 0.5))
                points.append((float(m.get("u", 0.0)) * _torso_dims(P, H, z)[0], z, m.get("face", "front"), None))
        _placed_buttons(objects, G, C, cfg, H, fit, bvh, points, buttons.get("placement", "waistband"))
    _edge_rolls(objects, G, C, cfg, H, roll_loops, thick, cfg.get("bands"))
    _add_embroidery(objects, G, C, cfg, main, (bottom_z, waist_z), P, H)
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


def _skirt(C, cfg, P, H, J, G, fit, part="main"):
    ease, thick = cfg["ease_m"], cfg["thickness_m"]
    hip_z, ankle_z = P["leg"]["hip_z"] * H, P["leg"]["ankle_z"] * H
    waist_z = float(cfg.get("waist_z_m", P["torso"]["levels"][2][0] * H))
    length = float(cfg.get("length", 0.66))
    bottom_z = waist_z - (float(cfg["length_m"]) if "length_m" in cfg else length * (waist_z - ankle_z))
    flare = float(cfg.get("flare_m", float(cfg.get("flare", 0.08)) * fit.leg))
    rings = []
    for k in range(17):
        t = k / 16
        z = bottom_z + (waist_z - bottom_z) * t
        down = 1 - t
        if z >= hip_z:
            w, front, back = _torso_dims(P, H, z)
            s = fit.torso
        else:
            lt = (hip_z - z) / max(hip_z - ankle_z, 1e-9)
            lr = _leg_radius(P, H, lt)
            w = abs(J["hip.L"].x) + lr
            front = back = lr
            s = fit.leg
        add = ease * s + thick + flare * down
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
                                     ease * fit.torso + thick, cfg["seam_radius_m"] * 1.3), cfg, "band", bm, G)
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
    if part == "main" and cfg.get("embroidery"):
        _add_embroidery(objects, G, C, cfg, {"main": ob}, (bottom_z, waist_z), P, H)
    return objects


def _smoothstep(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)



def _section_radii(body, centre_xy, z, count, half_band, max_r, fallback):
    """Per-angle outer radius of the body cross-section around ``centre_xy`` in the band ``|co.z - z| <= half_band``
    (``count`` equal sectors starting at +X, counter-clockwise). Vertices further than ``max_r`` (another limb) are
    ignored; empty sectors are filled from their neighbours, or ``fallback`` when nothing was found."""
    cx, cy = centre_xy
    radii = [None] * count
    for v in body.data.vertices:
        co = v.co
        if abs(co.z - z) > half_band:
            continue
        dx, dy = co.x - cx, co.y - cy
        r = math.hypot(dx, dy)
        if r > max_r:
            continue
        k = int(round((math.atan2(dy, dx) % (2 * math.pi)) / (2 * math.pi) * count)) % count
        radii[k] = r if radii[k] is None else max(radii[k], r)
    known = [k for k, r in enumerate(radii) if r is not None]
    if not known:
        return [fallback] * count
    out = []
    for k in range(count):
        if radii[k] is not None:
            out.append(radii[k])
            continue
        prev = max((j for j in known if j < k), default=known[-1])
        nxt = min((j for j in known if j > k), default=known[0])
        span = (nxt - prev) % count or count
        f = ((k - prev) % count) / span
        out.append(radii[prev] * (1 - f) + radii[nxt] * f)
    return out


def _footwear(C, body, cfg, P, H, J, G, fit):
    ease, thick = cfg["ease_m"], cfg["thickness_m"]
    ankle_z, knee_z = P["leg"]["ankle_z"] * H, P["leg"]["knee_z"] * H
    height = float(cfg.get("height", 0.18 if cfg["type"] == "shoes" else 0.64))
    top_z = ankle_z + (float(cfg["height_m"]) if "height_m" in cfg else height * (knee_z - ankle_z))
    fw, fl = P["foot"]["half_width"] * H, P["foot"]["length"] * H
    max_r = max(x * H for x in P["leg"]["radii"])
    # Chunky proportions (T-025): extra shaft width (full above the lower third of the shaft) and toe volume (over
    # the front half of the foot, mostly on its top and front).
    shaft, toe = float(cfg.get("shaft_width_m", 0.0)), float(cfg.get("toe_volume_m", 0.0))

    def volume(c, normal):
        v = 0.0
        if shaft > 0 and c.z > ankle_z:
            v += shaft * _smoothstep((c.z - ankle_z) / max(0.35 * (top_z - ankle_z), 1e-9))
        if toe > 0:
            front = _smoothstep((-c.y - 0.15 * fl) / (0.55 * fl))
            facing = max(0.0, normal.z, -normal.y) + 0.3 * max(0.0, 1.0 - abs(normal.z))
            v += toe * front * min(1.0, facing) * (normal.z > -0.5)
        return v

    objects, covered = [], set()
    shell_parts = {}
    lm = fit.leg
    for side in ("L", "R"):
        hx = J[f"ankle.{side}"].x

        def selector(c, hx=hx):
            return (-0.01 * lm <= c.z <= top_z and abs(c.x - hx) <= max(fw, max_r) + 0.015 * lm and
                    -1.05 * fl <= c.y <= max_r + 0.02 * lm)
        bands = cfg.get("bands", {})
        bands = {"cuff": True} if bands is True else bands
        roll_loops = [] if float(bands.get("edge_roll_m", 0.0)) > 0 else None
        ob, cov = _shell(body, f"garment.{cfg['name']}.main.{side}", selector, ease, thick, C, G,
                         extra=volume if shaft > 0 or toe > 0 else None, scale=lambda c: lm, loops_out=roll_loops)
        covered |= cov
        _feature(objects, ob, cfg, "main", _mat_for(G, cfg, "main", H), G)
        shell_parts[f"main.{side}"] = ob
        _edge_rolls(objects, G, C, cfg, H, roll_loops, thick, bands, prefix=f"edge.{side}")
        if cfg.get("cuff") or bands.get("cuff"):
            t = max(0.0, min(1.0, (knee_z - top_z) / max(knee_z - ankle_z, 1e-9)))
            lr = _leg_radius(P, H, 1 - t)
            cr = _cuff_radius(cfg, bands, cfg["seam_radius_m"] * 1.4)
            ring = _limb_ring(G, C, f"garment.{cfg['name']}.band.cuff.{side}", (hx, 0, top_z), (0, 0, -1),
                              lr, (ease + shaft) * lm + thick + max(0.0, cr - cfg["seam_radius_m"] * 1.4), cr)
            _feature(objects, ring, cfg, "band", _mat_for(G, cfg, "band", H), G)
        if shaft > 0:
            # Lining closing the opening between the leg and a widened shaft (seen from above). T-026: its inner
            # edge follows the measured leg cross-section (the _leg_radius estimate can sit centimetres outside a
            # slim leg, leaving a dark gap and a separate visible ring), and with a cuff its outer edge ends under
            # the cuff tube's centre line instead of poking out between the shaft wall and the tube.
            t = max(0.0, min(1.0, (knee_z - top_z) / max(knee_z - ankle_z, 1e-9)))
            lr = _leg_radius(P, H, 1 - t)
            r_leg = _section_radii(body, (hx, 0.0), top_z - 0.002 * lm, 48, 0.004 * lm, abs(hx) * 0.95, lr)
            # The lining closes onto the leg, so it keeps only the collision clearance, not the garment ease that
            # build() enforces on every piece (that pushed its inner edge 2 cm off the leg: the dark gap + ring).
            clearance = float(cfg.get("collision_clearance_m", max(0.003, thick * 1.5)))
            # Seat the lining on the shaft's top rim (the solidified shell edge stands above top_z once the shell
            # has its ease clearance); a lining below that rim leaves the rim visible as a separate ring.
            _ensure_clearance(body, ob, lambda point: ease * fit.at(point))
            rim = [(ob.matrix_world @ v.co).z for v in ob.data.vertices]
            lining_z = max([top_z - 0.002 * lm] + rim) + 0.0005 * lm
            r_shell = lr + (ease + shaft) * lm + thick
            r_cuff = (lr + (ease + shaft) * lm + thick + max(0.0, cr - cfg["seam_radius_m"] * 1.4)
                      if cfg.get("cuff") or bands.get("cuff") else None)
            verts, faces = [], []
            for k in range(48):
                a = 2 * math.pi * k / 48
                d = Vector((math.cos(a), math.sin(a), 0.0))
                r_in = r_leg[k] + clearance
                r_out = max(r_cuff if r_cuff is not None else r_shell, r_in + 0.002 * lm)
                verts += [tuple(Vector((hx, 0, lining_z)) + d * r_in),
                          tuple(Vector((hx, 0, lining_z)) + d * r_out)]
            for k in range(48):
                a, b = 2 * k, 2 * ((k + 1) % 48)
                faces.append((a, b, b + 1, a + 1))
            lining = G.new_object(f"garment.{cfg['name']}.lining.{side}", verts, faces, C)
            lining[CLEARANCE_PROP] = clearance
            mod = lining.modifiers.new("garment_thickness", "SOLIDIFY")
            mod.thickness, mod.offset = max(thick, 0.0015), -1.0
            bpy.context.view_layer.objects.active = lining
            lining.select_set(True)
            bpy.ops.object.modifier_apply(modifier=mod.name)
            lining.select_set(False)
            _feature(objects, lining, cfg, "lining", _mat_for(G, cfg, "lining" if "lining" in cfg.get("materials", {})
                                                              else "band", H), G)
        sole = cfg.get("sole", {})
        if sole is not False:
            sole = sole if isinstance(sole, dict) else {}
            st = float(sole.get("thickness_m", max(0.003, thick * 2)))
            extra_w = float(sole.get("width_m", 0.0)) + 0.5 * toe
            e = ease * lm
            ob = G.uv_sphere(f"garment.{cfg['name']}.sole.{side}",
                             (hx, -0.30 * fl - 0.5 * toe * lm, -e - st * 0.5), 1.0, C, 28, 12,
                             (fw + e + thick + extra_w * lm, 0.60 * fl + e + thick + extra_w * lm, st * 0.5))
            _feature(objects, ob, cfg, "sole", _mat_for(G, cfg, "sole", H), G)
    _add_embroidery(objects, G, C, cfg, shell_parts, (0.0, top_z), P, H)
    return objects, covered


# Per-object rest clearance override for pieces that close onto the body (boot lining), read by build().
CLEARANCE_PROP = "ps_garment_rest_clearance_m"
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
        for fibres in fibre_children(ob):
            fibres.hide_render = not worn
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


def add_fibres(ob, lod="close"):
    """Attach the shared surface-fibre group to one garment piece through its material preset. Returns the fibre
    object or None (preset without fibres, LOD off, or the isolated-test material fallback)."""
    if lod == "off" or ob.type != "MESH" or not ob.data.materials or ob.data.materials[0] is None:
        return None
    raw = ob.data.materials[0].get("ps_material_assignment")
    if not raw:
        return None
    try:
        from materials import builder as material_builder
    except ImportError:
        return None
    fibres = material_builder.add_fibres_from_assignment(ob, json.loads(raw), lod)
    if fibres is None:
        return None
    fibres.parent = ob
    fibres.matrix_parent_inverse.identity()
    fibres.matrix_basis.identity()
    fibres.hide_render = ob.hide_render
    fibres["ps_garment_item"] = ob.get("ps_garment_item", "")
    fibres["ps_garment_part"] = ob.get("ps_garment_part", "")
    return fibres


def fibre_children(ob):
    return [child for child in ob.children if child.get(FIBRES_PROP) == ob.name]


def build(C, body, clothing, P, H, J, G):
    """Build garments before rigging. Returns ``(objects, JSON-safe report)``."""
    validate(clothing)
    cloth.reset()
    fit = BodyFit(P, H, J)
    objects, coverage, item_report, masked = [], set(), [], []
    item_report_drape = {}
    hide_default = bool(clothing.get("hide_body_faces", False))
    for raw in clothing["garments"]:
        cfg = _merge(clothing.get("defaults"), raw)
        before = len(objects)
        if cfg["type"] in ("top", "shirt"):
            made, cov = _top(C, body, cfg, P, H, J, G, fit)
        elif cfg["type"] == "vest":
            made, cov = _top(C, body, cfg, P, H, J, G, fit, vest=True)
        elif cfg["type"] in ("shorts", "trousers"):
            made, cov = _bottoms(C, body, cfg, P, H, J, G, fit)
        elif cfg["type"] == "skirt":
            made, cov = _skirt(C, cfg, P, H, J, G, fit), set()
        elif cfg["type"] == "dress":
            bodice_cfg = dict(cfg)
            bodice_cfg["type"] = "dress"
            bodice_cfg.setdefault("sleeve_length", 0.18)
            bodice_cfg["hem_z_m"] = float(cfg.get("waist_z_m", P["torso"]["levels"][2][0] * H))
            made, cov = _top(C, body, bodice_cfg, P, H, J, G, fit)
            for key in ("_embroidery_report", "_buttons_report"):
                if key in bodice_cfg:
                    cfg[key] = bodice_cfg[key]
            made[0].name = f"garment.{cfg['name']}.bodice"
            made[0]["ps_garment_part"] = "bodice"
            if "bodice" in cfg.get("materials", {}):
                mat = _mat_for(G, cfg, "bodice", H)
                made[0].data.materials.clear()
                G.assign(made[0], mat)
                _tag(made[0], cfg, "bodice", mat)
            skirt_cfg = {k: v for k, v in cfg.items() if k != "embroidery"}
            made += _skirt(C, skirt_cfg, P, H, J, G, fit, part="skirt")
        else:
            made, cov = _footwear(C, body, cfg, P, H, J, G, fit)
        ease = cfg["ease_m"]
        drape_report = _drape_and_finish(body, made, cfg, fit)
        if drape_report:
            item_report_drape[cfg["name"]] = drape_report
        for ob in made:
            _ensure_clearance(body, ob, ob[CLEARANCE_PROP] if CLEARANCE_PROP in ob else
                              (lambda point, ease=ease: ease * fit.at(point)))
        objects += made
        coverage |= cov
        fibre_objects = [f for f in (add_fibres(ob, clothing.get("fibres_lod", "close")) for ob in made) if f]
        mask = bool(cfg.get("mask_body", hide_default)) and bool(cov)
        if mask:
            _store_cover(body, cfg["name"], cov)
            masked.append(cfg["name"])
        item_report_extra = {}
        if cfg.get("_embroidery_report"):
            item_report_extra["embroidery_motifs"] = cfg["_embroidery_report"]
        if cfg.get("_buttons_report"):
            item_report_extra["buttons"] = cfg["_buttons_report"]
        if cfg.get("_gusset_report"):
            item_report_extra["gusset"] = cfg["_gusset_report"]
        if cfg["name"] in item_report_drape:
            item_report_extra["drape"] = item_report_drape[cfg["name"]]
        item_report.append({**item_report_extra, "name": cfg["name"], "type": cfg["type"], "objects": [o.name for o in objects[before:]],
                            "covered_body_faces": len(cov), "mask_body": mask,
                            "material_presets": sorted({o.get("ps_material_preset", "") for o in objects[before:]}),
                            "fibres": [{"object": f.name, "source": f[FIBRES_PROP], "preset": f["ps_material_preset"],
                                        "lod": f["ps_fibres_lod"]} for f in fibre_objects]})
    body["ps_garment_mask_items"] = masked
    body["ps_garment_mask_margin_m"] = float(clothing.get("mask_margin_m", 0.015)) * fit.body
    collision = {"enabled": True, "offset_m": 0.002, "radius_m": 0.08, "falloff_m": 0.02, "passes": 3}
    collision.update(clothing.get("collision", {}))
    for key in ("offset_m", "radius_m", "falloff_m"):
        collision[key] = float(collision[key]) * fit.body
    body["ps_garment_collision"] = collision
    return objects, {"generator": GENERATOR, "items": item_report, "objects": len(objects),
                     "fibres_lod": clothing.get("fibres_lod", "close"),
                     "covered_body_faces": len(coverage), "masked_items": masked,
                     "mask_margin_m": body["ps_garment_mask_margin_m"],
                     "hide_body_faces": hide_default, "collision": collision, "body_fit": fit.report()}


def _drape_and_finish(body, made, cfg, fit):
    """T-034: optional cloth rest shape for the item's shells (``drape``), the displacement carried onto its other
    pieces, then the optional rounded rim (``edge_finish``). Returns a JSON-safe report or None."""
    drape = cfg.get("drape") or {}
    shells = [ob for ob in made if cloth.shell_layers(ob) is not None]
    report = []
    old_all, new_all, faces_all = [], [], []
    ease = cfg["ease_m"]
    for ob in shells:
        part = ob.get("ps_garment_part", "main")
        settings = cloth.settings_for(drape, part if part in cloth.DRAPE_PARTS else "main")
        if not settings["enabled"]:
            continue
        old, new, faces, info = cloth.drape_shell(
            ob, body, lambda p: ease * fit.at(p), settings, ease * fit.body)
        info.update({"part": part, "fabric": settings["fabric"], "frames": settings["frames"],
                     "gather": settings["gather"], "seed": settings["seed"], "pin": list(settings["pin"])})
        report.append(info)
        offset = len(old_all)
        old_all += old
        new_all += new
        faces_all += [tuple(i + offset for i in f) for f in faces]
    if report:
        cloth.follow([ob for ob in made if ob not in shells], old_all, new_all, faces_all)
    if cfg.get("edge_finish", "flat") == "rounded":
        for ob in shells:
            cloth.round_rim(ob)
    return report or None


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
