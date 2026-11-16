"""Shared build-time cloth rest shape for ``garment/1`` (T-034).

A garment item with ``drape.enabled`` has its offset shells settled once with Blender's cloth solver, against the
rest-pose body as a collider, under gravity. The settled shape becomes the shell's rest shape; skinning, masks and
post-skinning collision then work exactly as before. Everything here is character-independent: the pins, the gather
and the fabric come from the spec and the garment's own geometry.

Pins (``pin``, any of):
- ``edges``: open edges (cuffs, waist, leg openings, neckline, hem) stay where the band/edge finish holds them;
- ``volume``: shell areas at the plain ease (no puff/bloomer volume) stay fitted; only added volume drapes;
- ``top``: the item's top band (shoulders and neck for tops, the waist for bottoms) carries the weight.

``gather`` grows the free (unpinned) cloth by that share before it settles, as fabric gathered into a shorter band:
it cannot fit back onto the volume it came from, so it buckles into folds. A tiny seeded jitter breaks the symmetry
so folds form deterministically. The solver runs a fixed number of frames in a private scene (nothing else is
evaluated) and without self-collision, so a build is bit-reproducible.

Thickness: the shell's solidified outer layer is rebuilt from the settled inner layer along its new normals, so the
cloth keeps an even thickness through the folds. ``edge_finish: "rounded"`` rounds the solidified rim (any shell,
draped or not).
"""
import random
import time
import zlib

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

# Fabric presets in Blender cloth units (calibrated at the 1.0 m reference body, metres). ``thickness_m`` is the
# cloth collision distance; ``mass`` per vertex (kg); stiffness values are Blender's spring stiffnesses.
FABRICS = {
    "cotton": {"mass": 0.15, "tension": 15.0, "compression": 15.0, "shear": 5.0, "bending": 0.5,
               "air_damping": 2.0, "thickness_m": 0.0015, "friction": 5.0},
    "knit": {"mass": 0.2, "tension": 6.0, "compression": 6.0, "shear": 3.0, "bending": 0.15,
             "air_damping": 2.0, "thickness_m": 0.002, "friction": 8.0},
    "felt": {"mass": 0.3, "tension": 40.0, "compression": 40.0, "shear": 20.0, "bending": 8.0,
             "air_damping": 2.0, "thickness_m": 0.0025, "friction": 10.0},
    "denim": {"mass": 0.4, "tension": 40.0, "compression": 40.0, "shear": 30.0, "bending": 12.0,
              "air_damping": 2.0, "thickness_m": 0.002, "friction": 6.0},
}
FABRIC_FIELDS = ("mass", "tension", "compression", "shear", "bending", "air_damping", "thickness_m", "friction")
PINS = ("edges", "volume", "top")
EDGE_FINISHES = ("flat", "rounded")
DRAPE_PARTS = ("main", "bodice")
DEFAULTS = {"enabled": False, "fabric": "cotton", "frames": 30, "quality": 6, "seed": 0, "gather": 0.0,
            "pin": ["edges", "volume"], "edge_band_m": 0.012, "volume_band_m": 0.006, "top_band_m": 0.03,
            "jitter_m": 0.0004, "smooth": 1, "gravity": 1.0, "collider_reach_m": 0.06}

COLLIDER_SKIN_M = 0.001
# Shell layer bookkeeping, filled by generator._shell: mesh pointer -> (single-layer vertex count, thickness).
SHELL_LAYERS = {}


def _num(value, label, low, high):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not low <= float(value) <= high:
        raise ValueError(f"{label} must be a number in [{low}, {high}]")


def validate(raw, label):
    """Validate a ``drape`` block (item level or ``parts.<part>``)."""
    if not isinstance(raw, dict):
        raise ValueError(f"{label} must be an object")
    known = set(DEFAULTS) | {"overrides", "parts"}
    for key in raw:
        if key not in known:
            raise ValueError(f"{label}.{key} is not a drape field")
    if "enabled" in raw and not isinstance(raw["enabled"], bool):
        raise ValueError(f"{label}.enabled must be a boolean")
    if raw.get("fabric", "cotton") not in FABRICS:
        raise ValueError(f"{label}.fabric must be one of {sorted(FABRICS)}")
    for key, low, high in (("frames", 1, 200), ("quality", 1, 20), ("seed", 0, 2 ** 31 - 1), ("smooth", 0, 10)):
        if key in raw and (isinstance(raw[key], bool) or not isinstance(raw[key], int) or not low <= raw[key] <= high):
            raise ValueError(f"{label}.{key} must be an integer in [{low}, {high}]")
    _num(raw.get("gather", 0.0), f"{label}.gather", 0.0, 0.5)
    _num(raw.get("gravity", 1.0), f"{label}.gravity", 0.0, 1.0)
    _num(raw.get("collider_reach_m", 0.06), f"{label}.collider_reach_m", 0.01, 0.5)
    for key in ("edge_band_m", "volume_band_m", "top_band_m", "jitter_m"):
        if key in raw:
            _num(raw[key], f"{label}.{key}", 0.0, 0.2)
    pins = raw.get("pin", DEFAULTS["pin"])
    if not isinstance(pins, list) or any(p not in PINS for p in pins):
        raise ValueError(f"{label}.pin must be a list of {list(PINS)}")
    overrides = raw.get("overrides", {})
    if not isinstance(overrides, dict):
        raise ValueError(f"{label}.overrides must be an object")
    for key, value in overrides.items():
        if key not in FABRIC_FIELDS:
            raise ValueError(f"{label}.overrides.{key} must be one of {list(FABRIC_FIELDS)}")
        _num(value, f"{label}.overrides.{key}", 0.0, 1000.0)
    parts = raw.get("parts", {})
    if not isinstance(parts, dict):
        raise ValueError(f"{label}.parts must be an object")
    for part, sub in parts.items():
        if part not in DRAPE_PARTS:
            raise ValueError(f"{label}.parts.{part}: drape parts are {list(DRAPE_PARTS)}")
        if "parts" in sub:
            raise ValueError(f"{label}.parts.{part} cannot nest parts")
        validate(sub, f"{label}.parts.{part}")


def settings_for(drape, part):
    """Resolved drape settings for one garment part (item block merged with ``parts.<part>``)."""
    out = dict(DEFAULTS)
    out.update({k: v for k, v in (drape or {}).items() if k != "parts"})
    out.update((drape or {}).get("parts", {}).get(part, {}))
    fabric = dict(FABRICS[out["fabric"]])
    fabric.update(out.get("overrides", {}))
    out["fabric_settings"] = fabric
    return out


def register_shell(ob, layer_vertices, thickness):
    SHELL_LAYERS[ob.data.as_pointer()] = (int(layer_vertices), float(thickness), ob.data.name, len(ob.data.vertices))


def shell_layers(ob):
    """(single-layer vertex count, thickness) of a shell registered in this build, else None. The mesh name and
    vertex count must still match, so a recycled pointer can never alias another mesh."""
    entry = SHELL_LAYERS.get(ob.data.as_pointer())
    if entry is None or entry[2] != ob.data.name or entry[3] != len(ob.data.vertices):
        return None
    return entry[0], entry[1]


def reset():
    SHELL_LAYERS.clear()


def _smoothstep(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3.0 - 2.0 * x)


def _layer_faces(me, n):
    return [tuple(p.vertices) for p in me.polygons if all(v < n for v in p.vertices)]


def _boundary_vertices(faces):
    count = {}
    for f in faces:
        for a, b in zip(f, f[1:] + f[:1]):
            key = (min(a, b), max(a, b))
            count[key] = count.get(key, 0) + 1
    return sorted({v for e, c in count.items() if c == 1 for v in e})


def pin_weights(points, faces, body_bvh, ease_at, settings):
    """Per-vertex pin weight (1 = held) from the spec's pins; pure geometry, no character data."""
    pins = settings["pin"]
    weights = [0.0] * len(points)
    if "edges" in pins and settings["edge_band_m"] > 0:
        edge = [points[i] for i in _boundary_vertices(faces)]
        if edge:
            kd = KDTree(len(edge))
            for i, p in enumerate(edge):
                kd.insert(p, i)
            kd.balance()
            band = settings["edge_band_m"]
            for i, p in enumerate(points):
                d = kd.find(p)[2]
                weights[i] = max(weights[i], 1.0 - _smoothstep(d / band))
    if "volume" in pins and settings["volume_band_m"] > 0:
        band = settings["volume_band_m"]
        for i, p in enumerate(points):
            location, normal, _, _ = body_bvh.find_nearest(p)
            extra = (p - location).dot(normal) - ease_at(p)
            weights[i] = max(weights[i], 1.0 - _smoothstep(extra / band))
    if "top" in pins and settings["top_band_m"] > 0:
        top = max(p.z for p in points)
        band = settings["top_band_m"]
        for i, p in enumerate(points):
            weights[i] = max(weights[i], 1.0 - _smoothstep((top - p.z) / band))
    return weights


def _run_cloth(points, faces, pins, gather, settings, collider_mesh, collider_matrix, clearance, seed_key):
    """Settle one single-layer sheet; returns the settled points (world space)."""
    fabric = settings["fabric_settings"]
    rng = random.Random((int(settings["seed"]) * 1000003) ^ zlib.crc32(seed_key.encode()))
    me = bpy.data.meshes.new("ps_drape.sheet")
    me.from_pydata([tuple(p) for p in points], [], faces)
    me.validate()
    me.update()
    jitter = float(settings["jitter_m"])
    for v, w in zip(me.vertices, pins):
        if jitter > 0 and w < 0.999:
            v.co += v.normal * (jitter * (1.0 - w) * (2.0 * rng.random() - 1.0))
    scene = bpy.data.scenes.new("ps_drape")
    scene.frame_start, scene.frame_end = 1, int(settings["frames"]) + 1
    scene.render.fps = 24
    scene.gravity = (0.0, 0.0, -9.81 * float(settings["gravity"]))
    scene.use_gravity = True
    sheet = bpy.data.objects.new("ps_drape.sheet", me)
    scene.collection.objects.link(sheet)
    pin_group = sheet.vertex_groups.new(name="pin")
    gather_group = sheet.vertex_groups.new(name="gather")
    for i, w in enumerate(pins):
        pin_group.add([i], float(w), "REPLACE")
        gather_group.add([i], float(1.0 - w), "REPLACE")
    collider = bpy.data.objects.new("ps_drape.collider", collider_mesh)
    collider.matrix_world = collider_matrix
    scene.collection.objects.link(collider)
    collider.modifiers.new("Collision", "COLLISION")
    collider.collision.thickness_outer = COLLIDER_SKIN_M
    collider.collision.cloth_friction = float(fabric["friction"])
    collider.collision.damping = 1.0
    mod = sheet.modifiers.new("cloth", "CLOTH")
    s = mod.settings
    s.quality = int(settings["quality"])
    s.mass = float(fabric["mass"])
    s.tension_stiffness, s.compression_stiffness = float(fabric["tension"]), float(fabric["compression"])
    s.shear_stiffness, s.bending_stiffness = float(fabric["shear"]), float(fabric["bending"])
    s.air_damping = float(fabric["air_damping"])
    s.vertex_group_mass = "pin"
    s.pin_stiffness = 1.0
    if gather > 0:
        s.vertex_group_shrink = "gather"
        s.shrink_min = 0.0
        s.shrink_max = -float(gather)
    cs = mod.collision_settings
    cs.use_collision = True
    cs.use_self_collision = False
    cs.distance_min = float(fabric["thickness_m"])
    cs.collision_quality = 3
    mod.point_cache.frame_start, mod.point_cache.frame_end = 1, int(settings["frames"]) + 1
    for frame in range(1, int(settings["frames"]) + 2):
        scene.frame_set(frame)
    deps = scene.view_layers[0].depsgraph
    evaluated = sheet.evaluated_get(deps)
    settled = [sheet.matrix_world @ v.co for v in evaluated.to_mesh().vertices]
    evaluated.to_mesh_clear()
    bpy.data.objects.remove(sheet)
    bpy.data.objects.remove(collider)
    bpy.data.meshes.remove(me)
    bpy.data.scenes.remove(scene)
    return settled


def _smooth_free(points, faces, pins, iterations):
    """Light Laplacian relax of free vertices only (removes solver jitter, keeps the folds)."""
    if iterations <= 0:
        return points
    neighbours = [set() for _ in points]
    for f in faces:
        for a, b in zip(f, f[1:] + f[:1]):
            neighbours[a].add(b)
            neighbours[b].add(a)
    pts = [p.copy() for p in points]
    for _ in range(iterations):
        nxt = []
        for i, p in enumerate(pts):
            if not neighbours[i] or pins[i] >= 0.999:
                nxt.append(p)
                continue
            avg = sum((pts[j] for j in neighbours[i]), Vector()) / len(neighbours[i])
            nxt.append(p.lerp(avg, 0.5 * (1.0 - pins[i])))
        pts = nxt
    return pts


def _collider_mesh(body, points, reach, inflate=0.0):
    """The rest-pose body faces within ``reach`` of the sheet (the rest of the body cannot be touched in one
    settle); a much smaller collider keeps the solve fast. Body-space copy, inflated along the vertex normals by
    ``inflate`` (the item's clearance) so the solver can use a thin collision shell: a thick collision distance
    makes every cloth vertex test hundreds of faces."""
    kd = KDTree(len(points))
    for i, p in enumerate(points):
        kd.insert(p, i)
    kd.balance()
    mw = body.matrix_world
    me = body.data
    near = [False] * len(me.vertices)
    for v in me.vertices:
        near[v.index] = kd.find(mw @ v.co)[2] <= reach
    polys = [tuple(p.vertices) for p in me.polygons if any(near[i] for i in p.vertices)]
    used = sorted({i for f in polys for i in f})
    remap = {old: new for new, old in enumerate(used)}
    out = bpy.data.meshes.new("ps_drape.collider")
    out.from_pydata([tuple(me.vertices[i].co + me.vertices[i].normal * inflate) for i in used], [],
                    [tuple(remap[i] for i in f) for f in polys])
    out.validate()
    return out


def drape_shell(ob, body, ease_at, settings, clearance):
    """Settle shell ``ob`` (garment/1 offset shell). Returns (old_inner_points, new_inner_points, faces, report)."""
    layers = shell_layers(ob)
    me = ob.data
    n, thick = layers if layers else (len(me.vertices), 0.0)
    mw = ob.matrix_world
    points = [mw @ me.vertices[i].co for i in range(n)]
    faces = _layer_faces(me, n)
    body_bvh = BVHTree.FromPolygons([body.matrix_world @ v.co for v in body.data.vertices],
                                    [tuple(p.vertices) for p in body.data.polygons], all_triangles=False)
    # Blender's solidify (offset +1) puts the offset (outer) copy first: vertices [0, n) are the outer layer with the
    # original face orientation, [n, 2n) the original (inner) layer. The outer layer is settled; its distance to the
    # body includes the thickness.
    pins = pin_weights(points, faces, body_bvh, lambda p: ease_at(p) + thick, settings)
    started = time.perf_counter()
    shell_gap = settings["fabric_settings"]["thickness_m"] + COLLIDER_SKIN_M
    collider = _collider_mesh(body, points, float(settings["collider_reach_m"]) + clearance,
                              max(0.0, clearance - shell_gap))
    settled = _run_cloth(points, faces, pins, float(settings["gather"]), settings, collider,
                         body.matrix_world.copy(), clearance, ob.name)
    n_collider = len(collider.polygons)
    bpy.data.meshes.remove(collider)
    settled = _smooth_free(settled, faces, pins, int(settings["smooth"]))
    # New outer layer, then the inner layer back along the settled normals (even thickness through the folds).
    inv = mw.inverted()
    for i in range(n):
        me.vertices[i].co = inv @ settled[i]
    if thick > 0 and len(me.vertices) >= 2 * n:
        sheet = bmesh.new()
        verts = [sheet.verts.new(p) for p in settled]
        for f in faces:
            try:
                sheet.faces.new([verts[i] for i in f])
            except ValueError:
                pass
        sheet.normal_update()
        for i, v in enumerate(sheet.verts):
            me.vertices[n + i].co = inv @ (v.co - v.normal * thick)
        sheet.free()
    me.update()
    moved = [(a - b).length for a, b in zip(points, settled)]
    free = sum(1 for w in pins if w < 0.5)
    return points, settled, faces, {"object": ob.name, "vertices": n, "free_vertices": free,
                                    "max_move_m": round(max(moved) if moved else 0.0, 5),
                                    "mean_move_m": round(sum(moved) / max(len(moved), 1), 5),
                                    "collider_faces": n_collider, "seconds": round(time.perf_counter() - started, 2)}


def follow(objects, old_points, new_points, faces):
    """Carry the drape displacement onto an item's other pieces (bands, buttons, pockets, edge rolls, embroidery):
    each vertex takes the inverse-distance blend of the displacement of the nearest shell face's corners."""
    bvh = BVHTree.FromPolygons([tuple(p) for p in old_points], faces, all_triangles=False)
    delta = [b - a for a, b in zip(old_points, new_points)]
    for ob in objects:
        mw = ob.matrix_world
        inv = mw.inverted()
        changed = False
        for v in ob.data.vertices:
            p = mw @ v.co
            location, _, index, _ = bvh.find_nearest(p)
            if index is None:
                continue
            corners = faces[index]
            ws = [1.0 / max((old_points[c] - location).length, 1e-6) for c in corners]
            total = sum(ws)
            d = sum((delta[c] * (w / total) for c, w in zip(corners, ws)), Vector())
            if d.length > 1e-9:
                v.co = inv @ (p + d)
                changed = True
        if changed:
            ob.data.update()


def round_rim(ob, segments=2):
    """Round the solidified rim of a shell: bevel the edges where the rim meets the inner and outer layers."""
    layers = shell_layers(ob)
    if not layers or layers[1] <= 0:
        return 0
    n, thick = layers
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.verts.ensure_lookup_table()
    edges = set()
    for f in bm.faces:
        idx = [v.index for v in f.verts]
        if any(i < n for i in idx) and any(i >= n for i in idx):  # rim face
            for e in f.edges:
                a, b = (v.index for v in e.verts)
                if (a < n) == (b < n):
                    edges.add(e)
    if edges:
        bmesh.ops.bevel(bm, geom=list(edges), offset=thick * 0.48, offset_type="OFFSET", segments=int(segments),
                        profile=0.5, affect="EDGES", clamp_overlap=True)
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    SHELL_LAYERS.pop(ob.data.as_pointer(), None)  # topology changed: layers no longer index-aligned
    return len(edges)
