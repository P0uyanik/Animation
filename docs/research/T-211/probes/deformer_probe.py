"""T-211 probe B (read-only on the master; nothing is saved): Blender built-in deformers as regional face "knobs".

    blender -b --factory-startup -P deformer_probe.py -- <master.blend> <out.json>

On body_skin (Armature and Mask modifiers removed, rest pose) it measures for Warp (radius falloff), Lattice (3x3x3
on a head vertex group), Hook (radius falloff) and a Geometry Nodes Set Position knob: off-region motion, time per
re-evaluation after a knob change, and determinism. Then: expression keys evaluated through the knob stack (do they
stay local?), baking the stack into Basis + every key (what the engine export would read), apply-as-shape-key,
edit-mode Basis propagation to dependent keys, and Surface Deform keeping a brow on a re-shaped skin."""
import hashlib, json, sys, time
import bmesh, bpy
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.open_mainfile(filepath=argv[0])
R = {}
skin = bpy.data.objects["body_skin"]
R["skin_drivers"] = sorted({f.driver.type for f in skin.data.shape_keys.animation_data.drivers})
for m in list(skin.modifiers):
    skin.modifiers.remove(m)
for o in bpy.data.objects:  # keep only skin, landmarks and one brow (fast depsgraph)
    if o is not skin and not o.name.startswith("LM_") and o.name != "brow.L":
        bpy.data.objects.remove(o)
brow = bpy.data.objects["brow.L"]
for m in list(brow.modifiers):
    brow.modifiers.remove(m)
sc = bpy.context.scene
lm = {o.name[3:]: Vector(o.matrix_world.translation) for o in bpy.data.objects if o.name.startswith("LM_")}
n = len(skin.data.vertices)
keys = skin.data.shape_keys.key_blocks
mw = np.array(skin.matrix_world)


def ev(ob=skin):
    dg = bpy.context.evaluated_depsgraph_get()
    e = ob.evaluated_get(dg)
    me = e.to_mesh()
    a = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", a)
    e.to_mesh_clear()
    a = a.reshape(-1, 3)
    m = np.array(ob.matrix_world)
    return a @ m[:3, :3].T + m[:3, 3]


def h(a):
    return hashlib.sha1(np.round(a, 7).tobytes()).hexdigest()[:12]


base = ev()
chin_z, eye_z = lm["chin"].z, 0.5 * (lm["eye_L"].z + lm["eye_R"].z)
head = base[:, 2] > chin_z - 0.01
guess = np.array((lm["mouth"].x + 0.045, lm["mouth"].y, 0.5 * (eye_z + lm["mouth"].z)))  # left cheek, snapped to the skin
front = head & (base[:, 1] < lm["mouth"].y + 0.03)
cheek = Vector(base[np.nonzero(front)[0][np.argmin(np.linalg.norm(base[front] - guess, axis=1))]])
d_cheek = np.linalg.norm(base - np.array(cheek), axis=1)
R["mesh"] = {"vertices": n, "keys": len(keys) - 1, "head_vertices": int(head.sum())}


def knob(label, setup, change, radius=None, region=None):
    t0 = time.perf_counter(); setup(); bpy.context.view_layer.update(); a0 = ev(); t_set = time.perf_counter() - t0
    times = []
    for s in (1.0, 0.5, 1.0, 0.0, 1.0):
        change(s); t = time.perf_counter(); a = ev(); times.append(time.perf_counter() - t)
    change(1.0); a1 = ev(); a2 = ev()
    d = np.linalg.norm(a1 - base, axis=1) * 1000
    out = {"max_mm": round(float(d.max()), 2), "setup_s": round(t_set, 3),
           "eval_ms_median": round(1000 * float(np.median(times)), 1), "deterministic": h(a1) == h(a2)}
    if radius is not None:
        out["outside_radius_max_mm"] = round(float(d[d_cheek > radius].max()), 4)
    if region is not None:
        out["outside_region_max_mm"] = round(float(d[~region].max()), 4)
    out["far_neck_body_max_mm"] = round(float(d[~head].max()), 4)
    R[label] = out
    return a1


def clear():
    for m in list(skin.modifiers):
        skin.modifiers.remove(m)


# Warp: move a 30 mm region of the cheek 4 mm outward (x) with smooth falloff
e_from = bpy.data.objects.new("warp_from", None); sc.collection.objects.link(e_from); e_from.location = cheek
e_to = bpy.data.objects.new("warp_to", None); sc.collection.objects.link(e_to); e_to.location = cheek
def warp_setup():
    m = skin.modifiers.new("knob_cheek", "WARP"); m.object_from, m.object_to = e_from, e_to
    m.falloff_type, m.falloff_radius, m.use_volume_preserve = "SMOOTH", 0.030, False
def warp_change(s):
    e_to.location = cheek + Vector((0.004 * s, 0, 0))
knob("warp", warp_setup, warp_change, radius=0.030)
clear()

# Hook with radius falloff on the head vertices (needs a vertex set)
vg = skin.vertex_groups.new(name="t211_head"); vg.add([int(i) for i in np.nonzero(head)[0]], 1.0, "REPLACE")
e_hook = bpy.data.objects.new("hook", None); sc.collection.objects.link(e_hook); e_hook.location = cheek
def hook_setup():
    bpy.context.view_layer.update()  # matrix_world of the new empty must be current before the inverse is taken
    m = skin.modifiers.new("knob_hook", "HOOK"); m.object, m.vertex_group = e_hook, vg.name
    m.falloff_type, m.falloff_radius = "SMOOTH", 0.030
    m.center = skin.matrix_world.inverted() @ cheek
    m.matrix_inverse = (skin.matrix_world.inverted() @ e_hook.matrix_world).inverted()
def hook_change(s):
    e_hook.location = cheek + Vector((0.004 * s, 0, 0))
knob("hook", hook_setup, hook_change, radius=0.030)
clear()

# Lattice 3x3x3 around the head, restricted to the head group; move the lower-front-left point outward
hb = base[head]; lo, hi = hb.min(0), hb.max(0)
lat = bpy.data.lattices.new("t211_lat"); lat.points_u = lat.points_v = lat.points_w = 3
lob = bpy.data.objects.new("t211_lat", lat); sc.collection.objects.link(lob)
lob.location = Vector((lo + hi) / 2); lob.scale = Vector(hi - lo) * 1.02
pt = lat.points[0 + 0 * 3 + 0 * 9]  # (u, v, w) = (-x, -y, -z): lower jaw corner, front
p0 = pt.co_deform.copy()
def lat_setup():
    m = skin.modifiers.new("knob_lattice", "LATTICE"); m.object, m.vertex_group = lob, vg.name
def lat_change(s):
    pt.co_deform = p0 + Vector((-0.15 * s, 0, 0)); lob.update_tag()
knob("lattice_3x3x3", lat_setup, lat_change, region=head)
clear()

# Geometry Nodes knob: offset * smooth falloff(distance to centre, radius), inputs exposed on the modifier
ng = bpy.data.node_groups.new("t211_knob", "GeometryNodeTree")
ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
for nm, st in (("Centre", "NodeSocketVector"), ("Offset", "NodeSocketVector"), ("Radius", "NodeSocketFloat")):
    ng.interface.new_socket(nm, in_out="INPUT", socket_type=st)
N, L = ng.nodes, ng.links
gi, go = N.new("NodeGroupInput"), N.new("NodeGroupOutput")
pos, sp = N.new("GeometryNodeInputPosition"), N.new("GeometryNodeSetPosition")
dist = N.new("ShaderNodeVectorMath"); dist.operation = "DISTANCE"
mr = N.new("ShaderNodeMapRange"); mr.interpolation_type = "SMOOTHSTEP"; mr.inputs["To Min"].default_value, mr.inputs["To Max"].default_value = 1.0, 0.0
sc_ = N.new("ShaderNodeVectorMath"); sc_.operation = "SCALE"
L.new(pos.outputs[0], dist.inputs[0]); L.new(gi.outputs["Centre"], dist.inputs[1])
L.new(dist.outputs["Value"], mr.inputs["Value"]); L.new(gi.outputs["Radius"], mr.inputs["From Max"])
L.new(gi.outputs["Offset"], sc_.inputs[0]); L.new(mr.outputs["Result"], sc_.inputs["Scale"])
L.new(gi.outputs["Geometry"], sp.inputs["Geometry"]); L.new(sc_.outputs[0], sp.inputs["Offset"]); L.new(sp.outputs[0], go.inputs[0])
def ids(m):
    return {it.name: it.identifier for it in ng.interface.items_tree if it.item_type == "SOCKET" and it.in_out == "INPUT"}
def gnset(m, ident, value):  # Blender 5.x: modifier inputs live in m.properties.inputs.<identifier>.value
    getattr(m.properties.inputs, ident).value = value
def gn_setup():
    m = skin.modifiers.new("knob_gn", "NODES"); m.node_group = ng; i = ids(m)
    gnset(m, i["Centre"], tuple(cheek - Vector(skin.matrix_world.translation))); gnset(m, i["Radius"], 0.030)
def gn_change(s):
    m = skin.modifiers["knob_gn"]; gnset(m, ids(m)["Offset"], (0.004 * s, 0.0, 0.0)); skin.update_tag()
knob("geometry_nodes_set_position", gn_setup, gn_change, radius=0.030)

# Expressions through the knob stack (GN knob still on): does a key stay local, and how much does it change?
far = head & (np.linalg.norm(base - np.array(lm["mouth"]), axis=1) > 0.090) & (
    np.minimum(np.linalg.norm(base - np.array(lm["eye_L"]), axis=1), np.linalg.norm(base - np.array(lm["eye_R"]), axis=1)) > 0.096)
fitted = ev()
raw = {}
for k in keys[1:]:
    a = np.empty(n * 3); k.data.foreach_get("co", a); raw[k.name] = a.reshape(n, 3) @ mw[:3, :3].T
b0 = raw_basis = np.empty(n * 3); keys[0].data.foreach_get("co", b0); raw_basis = b0.reshape(n, 3) @ mw[:3, :3].T
expr = {}
t0 = time.perf_counter()
baked = {}
for k in keys[1:]:
    k.value = 1.0; k.slider_max = max(k.slider_max, 1.0)
    skin.data.shape_keys.animation_data.drivers.find(f'key_blocks["{k.name}"].value').mute = True
for k in keys[1:]:
    k.value = 0.0
for k in keys[1:]:
    k.value = 1.0; skin.update_tag(); a = ev(); k.value = 0.0
    d_stack = a - fitted; d_raw = raw[k.name] - raw_basis
    baked[k.name] = d_stack
    dd = np.linalg.norm(d_stack - d_raw, axis=1) * 1000
    expr[k.name] = {"far_max_mm": round(float(np.linalg.norm(d_stack[far], axis=1).max() * 1000), 3),
                    "delta_change_max_mm": round(float(dd.max()), 3)}
t_bake = time.perf_counter() - t0
R["keys_through_stack"] = {"bake_all_keys_s": round(t_bake, 2), "per_key": expr}

# Built-in alternatives for writing the result back as keys
res = {}
for mname in ("knob_gn", "knob_cheek"):
    if mname == "knob_cheek":
        warp_setup(); warp_change(1.0)
    t0 = time.perf_counter()
    try:
        with bpy.context.temp_override(object=skin, active_object=skin, selected_objects=[skin]):
            r1 = bpy.ops.object.modifier_apply_as_shapekey(modifier=mname, keep_modifier=True)
        res[mname] = {"result": sorted(r1), "s": round(time.perf_counter() - t0, 2), "new_key": keys[-1].name,
                      "vertex_count_same": len(keys[-1].data) == n}
        skin.shape_key_remove(keys[-1])
    except RuntimeError as e:
        res[mname] = {"error": str(e).strip()}
R["modifier_apply_as_shapekey"] = res
clear()

# Edit-mode Basis change: Blender propagates the Basis offset to keys relative to it
smile_before = np.empty(n * 3); keys["MouthSmile"].data.foreach_get("co", smile_before)
basis_before = np.empty(n * 3); keys[0].data.foreach_get("co", basis_before)
skin.active_shape_key_index = 0
bpy.context.view_layer.objects.active = skin
with bpy.context.temp_override(object=skin, active_object=skin):
    bpy.ops.object.mode_set(mode="EDIT")
    bm = bmesh.from_edit_mesh(skin.data)
    sel = [i for i in np.nonzero(d_cheek < 0.030)[0]]
    bm.verts.ensure_lookup_table()
    for i in sel:
        bm.verts[int(i)].co.x += 0.004
    bmesh.update_edit_mesh(skin.data)
    bpy.ops.object.mode_set(mode="OBJECT")
smile_after = np.empty(n * 3); keys["MouthSmile"].data.foreach_get("co", smile_after)
basis_after = np.empty(n * 3); keys[0].data.foreach_get("co", basis_after)
db = (basis_after - basis_before).reshape(n, 3); ds = (smile_after - smile_before).reshape(n, 3)
R["editmode_basis_propagation"] = {"moved_vertices": len(sel), "basis_move_mm": round(float(np.abs(db).max() * 1000), 3),
                                   "key_followed_max_err_mm": round(float(np.abs(ds - db).max() * 1000), 4)}

# Surface Deform: brow bound to the skin follows a later skin knob. Bind on the skin itself, then on a triangulated
# copy (same vertices) because Surface Deform refuses targets with concave polygons.
brow.parent = None
for m in list(skin.modifiers):
    skin.modifiers.remove(m)
tri = skin.copy(); tri.data = skin.data.copy(); tri.name = "skin_tri"; sc.collection.objects.link(tri)
tri.shape_key_clear()
bm = bmesh.new(); bm.from_mesh(tri.data); bmesh.ops.triangulate(bm, faces=bm.faces[:]); bm.to_mesh(tri.data); bm.free()
b_before = ev(brow); bc = Vector(b_before.mean(0))
e2f = bpy.data.objects.new("w2f", None); e2t = bpy.data.objects.new("w2t", None)
sc.collection.objects.link(e2f); sc.collection.objects.link(e2t); e2f.location = e2t.location = bc
sd = {}
for target in (skin, tri):
    for m in list(brow.modifiers):
        brow.modifiers.remove(m)
    e2t.location = bc
    m = brow.modifiers.new("sd", "SURFACE_DEFORM"); m.target = target
    bpy.context.view_layer.update()
    t0 = time.perf_counter()
    with bpy.context.temp_override(object=brow, active_object=brow):
        rb = bpy.ops.object.surfacedeform_bind(modifier="sd")
    t_bind = time.perf_counter() - t0
    bound = m.is_bound
    w = target.modifiers.new("knob_brow", "WARP"); w.object_from, w.object_to, w.falloff_type, w.falloff_radius = e2f, e2t, "SMOOTH", 0.05
    bpy.context.view_layer.update(); t_rest = ev(target); b0 = ev(brow)
    e2t.location = bc + Vector((0, 0, 0.003)); bpy.context.view_layer.update()
    b1 = ev(brow); t1 = ev(target)
    from mathutils.kdtree import KDTree
    kd = KDTree(len(t_rest))
    for i, c in enumerate(t_rest):
        kd.insert(c, i)
    kd.balance()
    near = [kd.find(c)[1] for c in b0]
    skin_move = (t1 - t_rest)[near]; brow_move = b1 - b0
    sd["skin" if target is skin else "triangulated_copy"] = {
        "is_bound": bound, "bind_s": round(t_bind, 2), "brow_vertices": len(b0),
        "skin_move_under_brow_mean_mm": round(float(np.linalg.norm(skin_move, axis=1).mean() * 1000), 3),
        "brow_move_mean_mm": round(float(np.linalg.norm(brow_move, axis=1).mean() * 1000), 3),
        "follow_err_max_mm": round(float(np.linalg.norm(brow_move - skin_move, axis=1).max() * 1000), 3)}
    target.modifiers.remove(w)
R["surface_deform"] = sd
R["skin_concave_or_ngon_faces"] = sum(1 for p in skin.data.polygons if len(p.vertices) > 4)
json.dump(R, open(argv[1], "w"), indent=1)
print(json.dumps({k: v for k, v in R.items() if k != "keys_through_stack"}, indent=1))
print("KEYS", R["keys_through_stack"]["bake_all_keys_s"], max(v["far_max_mm"] for v in expr.values()), max(v["delta_change_max_mm"] for v in expr.values()))
