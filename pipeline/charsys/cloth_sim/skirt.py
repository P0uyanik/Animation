"""Skirt cloth simulation on a built master (Blender cloth, baked to a PC2 point cache). See README.md.

Pipeline for one tagged piece (``ps_cloth_sim`` + the ``ps_cloth_pin`` attribute written by ``garment/3``):
  1. ``make_proxy``: a single-layer quad grid resampled from the piece at rest (rows x columns about the piece's own
     vertical axis, lightly smoothed, moved by a seeded sub-millimetre jitter), skinned like the nearest vertices of
     the piece and pinned where the piece is pinned.
  2. ``bind``: the piece and its companion pieces (the same item's bands below the pin line) follow the proxy
     through a Surface Deform modifier; their own skinning and collision modifiers are switched off while the
     simulation is shown (``show(False)`` switches back: the build's skinned skirt, untouched).
  3. ``simulate``: a Cloth modifier on the proxy, colliding with an unmasked copy of the body (and optional static
     props: a seat), stepped frame by frame through a motion; every frame's proxy points are written to a PC2 file.
  4. ``replay``: the Cloth modifier is replaced by a Mesh Cache modifier reading that file (the bake).
``penetration`` measures the piece against the posed body."""
import json
import math
import struct

import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

PROP, PIN = "ps_cloth_sim", "ps_cloth_pin"
PARITY_DIR = Vector((0.2672612, 0.5345225, 0.8017837))
DEFAULTS = {
    "rows": 30, "columns": 120, "smooth": 2, "jitter_m": 0.0001,
    # a doll-sized knitted skirt is a stiff shell that holds its flare: at the solver's default-like vertex mass a
    # low bending stiffness lets the cone collapse inwards by a third of its radius at rest (README, "Settings")
    "quality": 14, "vertex_mass": 0.01, "tension": 40.0, "compression": 40.0, "shear": 5.0, "bending": 40.0,
    "tension_damping": 6.0, "bending_damping": 0.6, "air_damping": 2.0,
    "collision_quality": 6, "distance_m": 0.004, "body_thickness_m": 0.0045, "friction": 12.0,
    "self_collision": False, "pin_stiffness": 1.0,
}


def tagged(objects=None):
    return [o for o in (objects or bpy.data.objects) if o.type == "MESH" and o.get(PROP)]


def _apply_pose(rig, steps):
    """FK pose on the rest pose: (bone pattern, world axis, degrees, sides) turned about the bone's head, in order."""
    for pb in rig.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
        if "IK_FK" in pb.keys():
            pb["IK_FK"] = 1.0
    bpy.context.view_layer.update()
    for pattern, axis, deg, sides in steps:
        for s in sides:
            pb = rig.pose.bones[pattern.format(s=s)]
            hw = rig.matrix_world @ pb.head
            rm = Matrix.Translation(hw) @ Matrix.Rotation(math.radians(deg), 4, axis) @ Matrix.Translation(-hw)
            pb.matrix = rig.matrix_world.inverted() @ rm @ rig.matrix_world @ pb.matrix
            bpy.context.view_layer.update()


def make_proxy(piece, st, seed):
    me = piece.data
    pts = [v.co.copy() for v in me.vertices]
    cx, cy = sum(p.x for p in pts) / len(pts), sum(p.y for p in pts) / len(pts)
    z0, z1 = min(p.z for p in pts), max(p.z for p in pts)
    bvh = BVHTree.FromPolygons(pts, [tuple(p.vertices) for p in me.polygons])
    rows, cols = int(st["rows"]), int(st["columns"])
    reach = 4.0 * max(math.hypot(p.x - cx, p.y - cy) for p in pts)
    radius = [[0.0] * cols for _ in range(rows)]
    for j in range(rows):
        z = z0 + (z1 - z0) * (0.004 + 0.992 * j / (rows - 1))
        for k in range(cols):
            a = 2 * math.pi * k / cols
            d = Vector((math.cos(a), math.sin(a), 0.0))
            hit = bvh.ray_cast(Vector((cx, cy, z)) + d * reach, -d)  # from outside: the outer wall
            if hit[0] is None:
                raise ValueError(f"cloth_sim: {piece.name} is not a closed tube about its axis at z = {z:.3f}")
            radius[j][k] = math.hypot(hit[0].x - cx, hit[0].y - cy)
    for _ in range(int(st["smooth"])):  # the relief of a knitted pattern is not cloth shape
        radius = [[(radius[j][k - 1] + 2 * radius[j][k] + radius[j][(k + 1) % cols] + radius[max(j - 1, 0)][k]
                    + radius[min(j + 1, rows - 1)][k]) / 6.0 for k in range(cols)] for j in range(rows)]
    rng = np.random.RandomState(int(seed))
    jit = rng.uniform(-1.0, 1.0, (rows, cols)) * float(st["jitter_m"])
    verts, faces = [], []
    for j in range(rows):
        z = z0 + (z1 - z0) * j / (rows - 1)
        for k in range(cols):
            a = 2 * math.pi * k / cols
            r = radius[j][k] + jit[j][k]
            verts.append((cx + math.cos(a) * r, cy + math.sin(a) * r, z))
    for j in range(rows - 1):
        for k in range(cols):
            a, b = j * cols + k, j * cols + (k + 1) % cols
            faces.append((a, b, b + cols, a + cols))
    pm = bpy.data.meshes.new(piece.name + ".sim")
    pm.from_pydata(verts, [], faces)
    proxy = bpy.data.objects.new(piece.name + ".sim", pm)
    piece.users_collection[0].objects.link(proxy)
    proxy.parent, proxy.matrix_world = piece.parent, piece.matrix_world.copy()
    proxy.hide_render = True
    proxy.display_type = "WIRE"
    # skinning and pin weights of the nearest vertex of the piece
    tree = KDTree(len(pts))
    for i, p in enumerate(pts):
        tree.insert(p, i)
    tree.balance()
    pin_attr = me.attributes[PIN].data
    names = {g.index: g.name for g in piece.vertex_groups if not g.name.startswith("ps_")}
    groups = {}
    pin = proxy.vertex_groups.new(name=PIN)
    for i, co in enumerate(verts):
        _, src, _ = tree.find(Vector(co))
        for g in me.vertices[src].groups:
            if g.group in names and g.weight > 0:
                name = names[g.group]
                if name not in groups:
                    groups[name] = proxy.vertex_groups.new(name=name)
                groups[name].add([i], g.weight, "REPLACE")
        w = pin_attr[src].value
        if w > 0.0:
            pin.add([i], w, "REPLACE")
    arm = next((m for m in piece.modifiers if m.type == "ARMATURE"), None)
    if arm is None:
        raise ValueError(f"cloth_sim: {piece.name} is not bound to a rig")
    mod = proxy.modifiers.new("Armature", "ARMATURE")
    mod.object = arm.object
    proxy["ps_cloth_proxy_of"] = piece.name
    proxy["ps_cloth_seed"] = int(seed)
    return proxy


def companions(piece):
    """Pieces of the same item that hang on the simulated piece: every band below the pin line that runs round the
    piece's own axis (a hem band; not a sleeve cuff that happens to hang at skirt height)."""
    zs = [v.co.z for v in piece.data.vertices]
    cx = sum(v.co.x for v in piece.data.vertices) / len(zs)
    cy = sum(v.co.y for v in piece.data.vertices) / len(zs)
    pin = piece.data.attributes[PIN].data
    free_top = max((z for z, p in zip(zs, pin) if p.value <= 0.0), default=min(zs))
    out = []
    for o in bpy.data.objects:
        if o is piece or o.type != "MESH" or o.get("ps_garment_item") != piece.get("ps_garment_item"):
            continue
        if o.name.endswith(".sim") or not o.data.vertices:
            continue
        xs, ys = [v.co.x for v in o.data.vertices], [v.co.y for v in o.data.vertices]
        round_axis = min(xs) < cx < max(xs) and min(ys) < cy < max(ys)
        if (round_axis and max(v.co.z for v in o.data.vertices) < free_top
                and str(o.get("ps_garment_part", "")).startswith("band")):
            out.append(o)
    return out


def bind(piece, proxy):
    """Surface Deform on the piece and its companions (bound at rest). Returns the followers."""
    followers = [piece] + companions(piece)
    for ob in followers:
        sd = ob.modifiers.new("cloth_follow", "SURFACE_DEFORM")
        sd.target = proxy
        sd.falloff = 4.0
        ob.hide_set(False)
        with bpy.context.temp_override(object=ob, active_object=ob, selected_objects=[ob]):
            bpy.ops.object.surfacedeform_bind(modifier=sd.name)
        if not sd.is_bound:
            raise RuntimeError(f"cloth_sim: could not bind {ob.name} to {proxy.name}")
    show(followers, True)
    return followers


def show(followers, sim):
    """Switch the followers between the simulated skirt (Surface Deform) and the build's skinned skirt."""
    for ob in followers:
        for m in ob.modifiers:
            if m.name == "cloth_follow":
                m.show_viewport = m.show_render = sim
            elif m.type in ("ARMATURE", "SHRINKWRAP"):
                m.show_viewport = m.show_render = not sim


def collider(rig, body, thickness, friction):
    """An unmasked, rig-deformed copy of the body that the cloth collides with (never rendered)."""
    name = f"cloth.collider.{body.name}"
    ob = bpy.data.objects.get(name)
    if ob is None:
        ob = bpy.data.objects.new(name, body.data)
        body.users_collection[0].objects.link(ob)
        ob.parent, ob.matrix_world = rig, body.matrix_world.copy()
        src = next((m for m in body.modifiers if m.type == "ARMATURE"), None)
        mod = ob.modifiers.new("Armature", "ARMATURE")
        mod.object = rig
        if src is not None:
            mod.use_deform_preserve_volume = src.use_deform_preserve_volume
        ob.hide_render = True
        ob.display_type = "WIRE"
        col = ob.modifiers.new("Collision", "COLLISION")
        del col
    ob.collision.thickness_outer = float(thickness)
    ob.collision.thickness_inner = 0.01
    ob.collision.cloth_friction = float(friction)
    return ob


def box(name, lo, hi, friction=20.0):
    """A static box prop the cloth collides with (a seat). Not rendered."""
    (x0, y0, z0), (x1, y1, z1) = lo, hi
    v = [(x, y, z) for z in (z0, z1) for y in (y0, y1) for x in (x0, x1)]
    f = [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(v, [], f)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.hide_render = True
    ob.display_type = "WIRE"
    ob.modifiers.new("Collision", "COLLISION")
    ob.collision.thickness_outer = 0.002
    ob.collision.cloth_friction = friction
    return ob


def add_cloth(proxy, st):
    mod = proxy.modifiers.new("Cloth", "CLOTH")
    s, c = mod.settings, mod.collision_settings
    s.quality = int(st["quality"])
    s.mass = float(st["vertex_mass"])
    s.tension_stiffness, s.compression_stiffness = float(st["tension"]), float(st["compression"])
    s.shear_stiffness, s.bending_stiffness = float(st["shear"]), float(st["bending"])
    s.tension_damping = s.compression_damping = s.shear_damping = float(st["tension_damping"])
    s.bending_damping, s.air_damping = float(st["bending_damping"]), float(st["air_damping"])
    s.vertex_group_mass = PIN
    s.pin_stiffness = float(st["pin_stiffness"])
    c.use_collision = True
    c.collision_quality = int(st["collision_quality"])
    c.distance_min = float(st["distance_m"])
    c.use_self_collision = bool(st["self_collision"])
    return mod


def _points(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    out = np.empty(len(me.vertices) * 3, dtype=np.float32)
    me.vertices.foreach_get("co", out)
    ev.to_mesh_clear()
    return out.reshape(-1, 3)


def simulate(rig, proxy, motion, st, path):
    """Step the motion from frame 1 and write every frame's proxy points (object space) to ``path`` (PC2)."""
    sc = bpy.context.scene
    frames = int(motion["frames"])
    sc.frame_start, sc.frame_end = 1, frames
    cloth = add_cloth(proxy, st)
    cloth.point_cache.frame_start, cloth.point_cache.frame_end = 1, frames
    samples = []
    for f in range(1, frames + 1):
        _apply_pose(rig, motion["pose"](f))
        sc.frame_set(f)
        samples.append(_points(proxy))
    data = np.stack(samples)
    with open(path, "wb") as fh:
        fh.write(struct.pack("<12siiffi", b"POINTCACHE2\0", 1, data.shape[1], 1.0, 1.0, data.shape[0]))
        fh.write(data.astype("<f4").tobytes())
    proxy.modifiers.remove(cloth)
    return data


def replay(proxy, path):
    """The bake: the proxy plays the PC2 file (no Cloth modifier, no rig on the proxy)."""
    for m in list(proxy.modifiers):
        proxy.modifiers.remove(m)
    mc = proxy.modifiers.new("cloth_bake", "MESH_CACHE")
    mc.cache_format, mc.filepath = "PC2", path
    mc.frame_start, mc.frame_scale, mc.play_mode = 1.0, 1.0, "SCENE"
    mc.deform_mode, mc.interpolation = "OVERWRITE", "NONE"
    return mc


def penetration(piece, body_collider, layer_m=0.0):
    """How far the evaluated piece is inside the posed body skin. ``layer_m``: also count vertices closer to the skin
    than a layer worn under the piece (tights)."""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = body_collider.evaluated_get(dg)
    bme = ev.to_mesh()
    mw = body_collider.matrix_world
    bvh = BVHTree.FromPolygons([mw @ v.co for v in bme.vertices], [tuple(p.vertices) for p in bme.polygons])
    ev.to_mesh_clear()
    pts = _points(piece)
    pw = piece.matrix_world
    depth, under = [], 0
    rest_z = [v.co.z for v in piece.data.vertices]
    z0, span = min(rest_z), max(max(rest_z) - min(rest_z), 1e-9)
    thirds = [0, 0, 0]  # inside-skin vertices by rest height: hem third, middle, waist third
    for p, rz in zip(pts, rest_z):
        w = pw @ Vector(p)
        loc, normal, _, dist = bvh.find_nearest(w)
        signed = dist if (w - loc).dot(normal) >= 0 else -dist
        if signed < 0:  # a bent limb folds the skin over itself and fools the normal test: confirm by ray parity
            hits, origin = 0, w
            for _ in range(64):
                hit = bvh.ray_cast(origin, PARITY_DIR)
                if hit[0] is None:
                    break
                hits += 1
                origin = hit[0] + PARITY_DIR * 1e-5
            if hits % 2 == 0:
                signed = dist
        if signed < 0:
            depth.append(-signed)
            thirds[min(2, int(3 * (rz - z0) / span))] += 1
        if signed < layer_m:
            under += 1
    depth.sort()
    n = len(pts)
    hem = [i for i, rz in enumerate(rest_z) if rz - z0 < span / 3]
    rise = sum((pw @ Vector(pts[i])).z - (pw @ piece.data.vertices[i].co).z for i in hem) / max(len(hem), 1)
    return {"vertices": n, "hem_rise_mm": round(1000 * rise, 1), "inside_by_third_hem_mid_waist": thirds, "inside_skin": len(depth), "inside_skin_share": round(len(depth) / n, 5),
            "max_depth_mm": round(1000 * depth[-1], 2) if depth else 0.0,
            "p95_depth_mm": round(1000 * depth[int(0.95 * (len(depth) - 1))], 2) if depth else 0.0,
            "under_layer": under, "under_layer_share": round(under / n, 5), "layer_mm": round(1000 * layer_m, 2)}


def settings(overrides=None):
    return dict(DEFAULTS, **(overrides or {}))


def describe(st, seed):
    return json.dumps({"seed": seed, **st}, sort_keys=True)
