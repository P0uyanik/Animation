"""Joint deformation test for any charsys master with a Rigify rig (headless Blender; read-only on the input).

    blender -b --factory-startup -P pipeline/charsys/tests/deform_test.py -- <master.blend> <out_dir>

Poses (FK controls, defined by intent; the rotation sign is chosen by measuring the effect, so no character's
bone-axis convention is assumed): shoulder raise 70 deg, shoulder forward 60, elbow 90, wrist 60, hip forward 80,
knee 90, ankle 30, finger curl 70 (all finger segments and thumb), on the left side. Per pose, over every mesh with
an Armature modifier: max and 99th-percentile edge stretch, min and 1st-percentile edge compression (posed / rest
length). Writes deform_test.json and deform_sheet.png (workbench renders)."""
import json
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Vector

src, OUT = sys.argv[sys.argv.index("--") + 1:][:2]
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=os.path.abspath(src))
rig = next(o for o in bpy.data.objects if o.type == "ARMATURE" and not o.name.startswith("WGT"))
meshes = [o for o in bpy.data.objects if o.type == "MESH" and any(m.type == "ARMATURE" for m in o.modifiers) and not o.name.startswith("WGT")]
for pb in rig.pose.bones:
    if "IK_FK" in pb.keys():
        pb["IK_FK"] = 1.0
deps = bpy.context.evaluated_depsgraph_get


def world_pts(ob):
    ev = ob.evaluated_get(deps())
    me = ev.to_mesh()
    c = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", c)
    ev.to_mesh_clear()
    c = c.reshape(-1, 3)
    M = np.array(ob.matrix_world)
    return c @ M[:3, :3].T + M[:3, 3]


def reset():
    for pb in rig.pose.bones:
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = (0, 0, 0)
    bpy.context.view_layer.update()


def bone_head(name):
    return rig.matrix_world @ rig.pose.bones[name].head


def bone_tail(name):
    return rig.matrix_world @ rig.pose.bones[name].tail


reset()
REST = {o.name: world_pts(o) for o in meshes}
EDGES = {o.name: np.array([e.vertices[:] for e in o.data.edges]) for o in meshes}
FINGERS = [f"{f}.0{k}.L" for f in ("f_index", "f_middle", "f_ring", "f_pinky", "thumb") for k in (1, 2, 3)]
# (pose name, controls, axis, angle, measure(), goal sign): goal > 0 means the measure should increase
POSES = [("shoulder_raise", ["upper_arm_fk.L"], 2, 70, lambda: bone_tail("forearm_fk.L").z, +1),
         ("shoulder_forward", ["upper_arm_fk.L"], 0, 60, lambda: -bone_tail("forearm_fk.L").y, +1),
         ("elbow_90", ["forearm_fk.L"], 0, 90, lambda: -bone_tail("forearm_fk.L").y, +1),
         ("wrist_60", ["hand_fk.L"], 0, 60, lambda: -bone_tail("hand_fk.L").y, +1),
         ("hip_forward_80", ["thigh_fk.L"], 0, 80, lambda: -bone_tail("thigh_fk.L").y, +1),
         ("knee_90", ["shin_fk.L"], 0, 90, lambda: bone_tail("shin_fk.L").y, +1),
         ("ankle_30", ["foot_fk.L"], 0, 30, lambda: bone_tail("foot_fk.L").z, +1),
         ("fingers_curl_70", [f for f in FINGERS], 0, 70, lambda: -sum((bone_tail(f) - bone_head("hand_fk.L")).length for f in FINGERS if f in rig.pose.bones), +1)]
R = {"source": os.path.basename(src), "rig": rig.name, "poses": {}, "missing_controls": []}
tiles = []
for name, ctrls, axis, ang, measure, goal in POSES:
    ctrls = [c for c in ctrls if c in rig.pose.bones]
    if not ctrls:
        R["missing_controls"].append(name)
        continue
    reset()
    m0 = measure()
    best = None
    for sign in (1, -1):
        reset()
        for c in ctrls:
            e = [0.0, 0.0, 0.0]
            e[axis] = math.radians(sign * ang)
            rig.pose.bones[c].rotation_euler = e
        bpy.context.view_layer.update()
        dm = (measure() - m0) * goal
        if best is None or dm > best[0]:
            best = (dm, sign)
    reset()
    for c in ctrls:
        e = [0.0, 0.0, 0.0]
        e[axis] = math.radians(best[1] * ang)
        rig.pose.bones[c].rotation_euler = e
    bpy.context.view_layer.update()
    st = []
    for o in meshes:
        P1, P0, E = world_pts(o), REST[o.name], EDGES[o.name]
        if len(E) == 0 or len(P1) != len(P0):
            continue
        l0 = np.linalg.norm(P0[E[:, 0]] - P0[E[:, 1]], axis=1)
        l1 = np.linalg.norm(P1[E[:, 0]] - P1[E[:, 1]], axis=1)
        ok = l0 > 1e-4
        st.append(l1[ok] / l0[ok])
    r = np.concatenate(st) if st else np.array([1.0])
    R["poses"][name] = {"sign": best[1], "effect": round(best[0], 4), "max_stretch": round(float(r.max()), 3),
                        "p99_stretch": round(float(np.percentile(r, 99)), 3), "min_compress": round(float(r.min()), 3),
                        "p01_compress": round(float(np.percentile(r, 1)), 3)}
    tiles.append(name)
    # render the pose (workbench, three-quarter front)
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.render.resolution_x, sc.render.resolution_y = 240, 320
    if "pt_cam" not in bpy.data.objects:
        cam = bpy.data.objects.new("pt_cam", bpy.data.cameras.new("pt_cam"))
        cam.data.type = "ORTHO"
        cam.data.ortho_scale = 1.25
        sc.collection.objects.link(cam)
        sc.camera = cam
        t = Vector((0.05, 0, 0.52))
        cam.location = t + Vector((1.6, -2.6, 0.5))
        cam.rotation_euler = (t - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = os.path.join(OUT, f"_{name}.png")
    bpy.ops.render.render(write_still=True)
json.dump(R, open(os.path.join(OUT, "deform_test.json"), "w"), indent=1)
for k, v in R["poses"].items():
    print("[deform_test]", k, v)
print("[deform_test] missing:", R["missing_controls"])
