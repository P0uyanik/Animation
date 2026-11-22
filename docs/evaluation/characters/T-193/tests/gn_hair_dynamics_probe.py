"""T-193 feasibility probe: Blender 5.3 bundled GN "Hair Dynamics" (XPBD, Physics (Experimental) mode).

Run (headless bpy 5.3):
  python3 tools/bpy_blender.py -b --factory-startup -P <this> -- OUT.json [--mode=guide|ringlet] [--sub=N] [--cs=N]
          [--edge] [--margin=M] [--png=OUT.png]
Scene (metres, Z up): a skinned torso cylinder (r 0.12, 3-bone armature) that bends forward over a table
(top z 0.70, front edge y 0.30; the bent chest stays >= 4 cm above it), a head sphere (r 0.09) on the head bone, eight locks rooted on the head
(4 front/side that fall onto the table in the lean, 4 back that lie on the bent back).
  guide:   each lock is a 16-point centre line (the T-183-like "chain"), 0.32 m.
  ringlet: each lock is a 48-point helix (r 15 mm, 5 turns), 0.32 m tall (arc 0.55 m).
Colliders: torso (Deforming, evaluated armature mesh), table box; the head is the hair surface (Surface Collision).
Measures per frame: hair points > 1 mm inside the torso mesh (BVH closest point + normal side), below the table
top inside its footprint, inside the head sphere; max stretch; a SHA-256 of all positions (determinism).
Throwaway research code; not part of the pipeline.
"""
import hashlib
import json
import math
import sys
import time

import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

ASSETS = bpy.utils.system_resource("DATAFILES") + "/assets/nodes/"
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else "probe.json"
opt = {a[2:].split("=")[0]: (a.split("=")[1] if "=" in a else True) for a in argv[1:]}
MODE = opt.get("mode", "guide")
SUB, CS = int(opt.get("sub", 10)), int(opt.get("cs", 15))
EDGE = bool(opt.get("edge", False))
MARGIN = float(opt.get("margin", 0.004))
PNG = opt.get("png")
PF = [int(x) for x in opt.get("pf", "20,50,72,110").split(",")]
FRAMES = 120
TABLE_Z, TABLE_Y0, TABLE_Y1 = 0.70, 0.30, 0.94

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.frame_start, sc.frame_end = 1, FRAMES
sc.render.fps = 24
for blend, names in (("geometry_nodes_dynamics_assets.blend", ["Hair Dynamics", "Collider"]),
                     ("procedural_hair_node_assets.blend", ["Attach Hair Curves to Surface"])):
    with bpy.data.libraries.load(ASSETS + blend) as (_s, d):
        d.node_groups = list(names)
HD, COL, ATT = (bpy.data.node_groups[n] for n in ("Hair Dynamics", "Collider", "Attach Hair Curves to Surface"))


def one_node_gn(obj, group, inputs):
    tree = bpy.data.node_groups.new(obj.name + "_gn", "GeometryNodeTree")
    tree.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    tree.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    gi, go = tree.nodes.new("NodeGroupInput"), tree.nodes.new("NodeGroupOutput")
    n = tree.nodes.new("GeometryNodeGroup")
    n.node_tree = group
    tree.links.new(gi.outputs[0], n.inputs[0])
    tree.links.new(n.outputs[0], go.inputs[0])
    for k, v in inputs.items():
        n.inputs[k].default_value = v
    obj.modifiers.new("gn", "NODES").node_group = tree


# --- armature + skinned torso -----------------------------------------------------------------------
arm_data = bpy.data.armatures.new("rig")
rig = bpy.data.objects.new("rig", arm_data)
sc.collection.objects.link(rig)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode="EDIT")
bones = {}
for name, h, t, par in (("spine", 0.50, 0.80, None), ("chest", 0.80, 1.08, "spine"), ("head", 1.08, 1.30, "chest")):
    b = arm_data.edit_bones.new(name)
    b.head, b.tail = (0, 0, h), (0, 0, t)
    if par:
        b.parent = bones[par]
        b.use_connect = True
    bones[name] = b
bpy.ops.object.mode_set(mode="OBJECT")

bpy.ops.mesh.primitive_cylinder_add(radius=0.12, depth=0.56, location=(0, 0, 0.78), vertices=40)
torso = bpy.context.object
torso.name = "torso"
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.mesh.subdivide(number_cuts=14)  # rings so it can bend
bpy.ops.object.mode_set(mode="OBJECT")
vs, vc = torso.vertex_groups.new(name="spine"), torso.vertex_groups.new(name="chest")
for v in torso.data.vertices:
    w = min(1.0, max(0.0, (v.co.z + 0.78 - 0.68) / 0.24))
    vs.add([v.index], 1 - w, "REPLACE")
    vc.add([v.index], w, "REPLACE")
torso.modifiers.new("arm", "ARMATURE").object = rig

bpy.ops.mesh.primitive_uv_sphere_add(radius=0.09, location=(0, 0, 1.20), segments=48, ring_count=24)
head = bpy.context.object
head.name = "head"
head.parent, head.parent_type, head.parent_bone = rig, "BONE", "head"
head.matrix_world = Matrix.Translation((0, 0, 1.20))

# lean forward (towards +Y): f1-24 still, f24-56 lean, f56-88 hold, f88-120 back up
pb = rig.pose.bones
for b in pb:
    b.rotation_mode = "XYZ"
for f, sp, ch, hd_ in ((1, 0, 0, 0), (24, 0, 0, 0), (56, 18, 30, 10), (88, 18, 30, 10), (120, 0, 0, 0)):
    for name, deg in (("spine", sp), ("chest", ch), ("head", hd_)):
        pb[name].rotation_euler = (math.radians(-deg), 0, 0)
        pb[name].keyframe_insert("rotation_euler", frame=f)

bpy.ops.mesh.primitive_cube_add(size=1, location=(0, (TABLE_Y0 + TABLE_Y1) / 2, TABLE_Z / 2))
table = bpy.context.object
table.name = "table"
table.scale = (1.2, TABLE_Y1 - TABLE_Y0, TABLE_Z)
bpy.ops.object.transform_apply(scale=True)

coll = bpy.data.collections.new("colliders")
sc.collection.children.link(coll)
for o, deform in ((torso, True), (table, False)):
    sc.collection.objects.unlink(o)
    coll.objects.link(o)
    one_node_gn(o, COL, {"Margin": MARGIN, "Friction": 0.3, "Edge Contacts": EDGE, "Deforming": deform})

# --- locks ---------------------------------------------------------------------------------------------
NPT = 16 if MODE == "guide" else 48
LEN, HR, TURNS = float(opt.get("len", 0.32)), 0.015, 5.0
angles = [-30, 30, -75, 75, 150, 180, 210, 180]  # degrees from +Y (front) around Z
pos = []
for i, a in enumerate(angles):
    a = math.radians(a)
    rz = 1.20 - (0.03 if i < 7 else 0.06)
    rr = math.sqrt(0.09 ** 2 - (rz - 1.20) ** 2) * 0.98
    r = Vector((rr * math.sin(a), rr * math.cos(a), rz))
    out = Vector((r.x, r.y, 0)).normalized()
    for k in range(NPT):
        t = k / (NPT - 1)
        off = out * (0.05 * min(1, t * 5))  # leave the head sideways, then hang
        if MODE == "ringlet":
            ang = 2 * math.pi * TURNS * t
            off += Vector((math.cos(ang), math.sin(ang), 0)) * HR * min(1, t * 4)
        pos.append((r.x + off.x, r.y + off.y, r.z - LEN * t))
hc = bpy.data.hair_curves.new("locks")
hc.add_curves([NPT] * len(angles))
hc.position_data.foreach_set("vector", np.array(pos, dtype=np.float32).ravel())
hair = bpy.data.objects.new("hair", hc)
sc.collection.objects.link(hair)
hair.parent = head  # hair object follows the head, simulation runs in world space
hair.matrix_parent_inverse = head.matrix_world.inverted()
hc.surface, hc.surface_uv_map = head, "UVMap"

tree = bpy.data.node_groups.new("hair_sim", "GeometryNodeTree")
tree.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
tree.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
gi, go = tree.nodes.new("NodeGroupInput"), tree.nodes.new("NodeGroupOutput")
att = tree.nodes.new("GeometryNodeGroup")
att.node_tree = ATT
att.inputs["Surface Object"].default_value = head
uvn = tree.nodes.new("GeometryNodeInputNamedAttribute")
uvn.data_type = "FLOAT_VECTOR"
uvn.inputs["Name"].default_value = "UVMap"
tree.links.new(uvn.outputs["Attribute"], att.inputs["Surface UV Map"])
hd = tree.nodes.new("GeometryNodeGroup")
hd.node_tree = HD
tree.links.new(gi.outputs[0], att.inputs[0])
tree.links.new(att.outputs[0], hd.inputs["Hair"])
tree.links.new(hd.outputs["Hair"], go.inputs[0])
for k, v in {"Mode": "Physics (Experimental)", "Substeps": SUB, "Constraint Steps": CS, "Effectors Collection": coll,
             "Bendiness": 0.3, "Edge Contacts": EDGE, "Deforming": False, "Surface Collision": True}.items():
    hd.inputs[k].default_value = v
hair.modifiers.new("sim", "NODES").node_group = tree

# --- step and measure ------------------------------------------------------------------------------------
rest_len = np.linalg.norm(np.diff(np.array(pos).reshape(len(angles), NPT, 3), axis=1), axis=2).sum(1)
rows, h, frames_xy = [], hashlib.sha256(), {}
t0 = time.time()
for f in range(1, FRAMES + 1):
    sc.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get()
    he = hair.evaluated_get(dg)
    p = np.zeros(len(he.data.points) * 3, dtype=np.float32)
    he.data.attributes["position"].data.foreach_get("vector", p)
    mw = np.array(he.matrix_world)
    w = p.reshape(-1, 3) @ mw[:3, :3].T + mw[:3, 3]
    h.update(w.astype(np.float32).tobytes())
    te = torso.evaluated_get(dg)
    tm = te.to_mesh()
    tw = np.array(te.matrix_world)
    tv = [Vector(tw[:3, :3] @ np.array(v.co) + tw[:3, 3]) for v in tm.vertices]
    bvh = BVHTree.FromPolygons(tv, [tuple(pl.vertices) for pl in tm.polygons])
    depth_t = []
    for q in w:
        co, nrm, _i, dist = bvh.find_nearest(Vector(q))
        depth_t.append(dist if (Vector(q) - co).dot(nrm) < 0 else 0.0)
    te.to_mesh_clear()
    depth_t = np.array(depth_t)
    in_fp = (np.abs(w[:, 0]) < 0.6) & (w[:, 1] > TABLE_Y0) & (w[:, 1] < TABLE_Y1)
    depth_tab = np.where(in_fp, TABLE_Z - w[:, 2], 0)
    hcw = np.array(head.evaluated_get(dg).matrix_world.translation)
    depth_h = 0.09 - np.linalg.norm(w - hcw, axis=1)
    L = np.linalg.norm(np.diff(w.reshape(len(angles), NPT, 3), axis=1), axis=2).sum(1)
    rows.append({"frame": f, "torso_n": int((depth_t > 0.001).sum()), "torso_mm": round(float(depth_t.max()) * 1e3, 2),
                 "table_n": int((depth_tab > 0.001).sum()), "table_mm": round(float(max(0, depth_tab.max())) * 1e3, 2),
                 "head_n": int((depth_h > 0.001).sum()), "head_mm": round(float(max(0, depth_h.max())) * 1e3, 2),
                 "stretch_max": round(float((L / rest_len).max()), 3)})
    if PNG and f in PF:
        frames_xy[f] = (w.copy(), np.array(tv), hcw)
el = time.time() - t0


def summ_key(k):
    return {"frames": sum(r[k + "_n"] > 0 for r in rows), "worst_mm": max(r[k + "_mm"] for r in rows),
            "most_points": max(r[k + "_n"] for r in rows)}


summ = {"blender": bpy.app.version_string, "mode": MODE, "locks": len(angles), "points": int(len(w)), "frames": FRAMES,
        "substeps": SUB, "constraint_steps": CS, "edge_contacts": EDGE, "margin_m": MARGIN,
        "seconds_incl_measure": round(el, 2), "sha256": h.hexdigest(),
        "torso": summ_key("torso"), "table": summ_key("table"), "head": summ_key("head"),
        "stretch_max": max(r["stretch_max"] for r in rows)}
json.dump({"summary": summ, "rows": rows}, open(OUT, "w"), indent=1)
print(json.dumps(summ))

if PNG:  # side view (Y right, Z up): torso vertices grey, table, head circle, locks coloured
    from PIL import Image, ImageDraw
    S, W, H = 250 / 1.05, 250, 300
    img = Image.new("RGB", (W * 4, H + 20), "white")
    dr = ImageDraw.Draw(img)

    def px(y, z, ox):
        return (ox + (y + 0.30) * S, H - (z - 0.35) * S)

    cols = ["#d62728", "#ff7f0e", "#2ca02c", "#17becf", "#1f77b4", "#9467bd", "#8c564b", "#e377c2"]
    for i, (f, (w, tv, hcw)) in enumerate(sorted(frames_xy.items())):
        ox = i * W
        x0, y0 = px(TABLE_Y0, TABLE_Z, ox)
        x1, y1 = px(TABLE_Y1, 0.35, ox)
        dr.rectangle([x0, y0, min(x1, ox + W - 2), y1], fill="#d9c9a8")
        for v in tv[::3]:
            dr.point(px(v[1], v[2], ox), fill="#aaaaaa")
        c = px(hcw[1], hcw[2], ox)
        dr.ellipse([c[0] - 0.09 * S, c[1] - 0.09 * S, c[0] + 0.09 * S, c[1] + 0.09 * S], outline="#555555")
        for k in range(len(angles)):
            seg = w.reshape(len(angles), NPT, 3)[k]
            dr.line([px(q[1], q[2], ox) for q in seg], fill=cols[k], width=2)
        dr.text((ox + 6, H + 4), f"f{f}  {MODE} sub{SUB} cs{CS} edge{int(EDGE)}", fill="black")
        dr.line([ox + W - 1, 0, ox + W - 1, H + 20], fill="#cccccc")
    img.save(PNG)
