"""Rig, expression and export tests for a pilot master .blend (headless).

    blender -b -P pipeline/blender/boy_pilot/rig_tests.py -- <master.blend> <glb> <out_dir>

1. Expressions: face renders with each shape key at 1 (Blink, BrowDown, Smile, JawOpen).
2. Deformation poses through the Rigify controls (FK): arms raised, elbows bent 90°, head turned, knee/hip bent,
   eye gaze; full-body renders (no fur: fur curves in the pilot are static and do not follow the rig).
3. Gaze: eye bones rotate the eyeballs.
4. glTF round trip: re-import the exported .glb and count joints, skinned meshes and morph targets.
Writes rig_tests.json and PNGs."""
import json
import math
import os
import sys

import bpy
from mathutils import Euler, Vector

argv = sys.argv[sys.argv.index("--") + 1:]
master, glb, out = map(os.path.abspath, argv[:3])
os.makedirs(out, exist_ok=True)
R = {}


def setup_render(res, samples=20):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = res
    if not sc.world:
        sc.world = bpy.data.worlds.new("W")
    sc.world.use_nodes = True
    sc.world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.5, 0.5, 0.5, 1)
    sc.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6
    for name, loc, energy, size in (("Key", (-1.6, -2.2, 2.4), 260, 1.6), ("Fill", (2.0, -1.8, 1.2), 90, 2.0),
                                    ("Rim", (0.6, 2.2, 2.0), 160, 1.2)):
        if name in bpy.data.objects:
            continue
        lt = bpy.data.lights.new(name, "AREA")
        lt.energy, lt.size = energy, size
        ob = bpy.data.objects.new(name, lt)
        sc.collection.objects.link(ob)
        ob.location = loc
        ob.rotation_euler = (Vector((0, 0, 0.5)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    if "TestCam" not in bpy.data.objects:
        cam = bpy.data.objects.new("TestCam", bpy.data.cameras.new("TestCam"))
        sc.collection.objects.link(cam)
        sc.camera = cam
    return bpy.data.objects["TestCam"]


def look(cam, target, yaw, el, dist, focal):
    d = Vector((math.sin(math.radians(yaw)) * math.cos(math.radians(el)), -math.cos(math.radians(yaw)) * math.cos(math.radians(el)),
                math.sin(math.radians(el))))
    cam.location = Vector(target) + d * dist
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = focal


def render(path):
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


bpy.ops.wm.open_mainfile(filepath=master)
for o in list(bpy.data.objects):  # widgets are never rendered; hide them from the test renders as well
    if o.name.startswith("WGT-"):
        o.hide_render = True
rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
R["rig"] = {"bones": len(rig.data.bones), "deform_bones": sum(b.use_deform for b in rig.data.bones),
            "controls": sorted(b.name for b in rig.pose.bones if not b.name.startswith(("DEF-", "ORG-", "MCH-")))[:80]}
cam = setup_render((600, 600))

# 1. expressions
keys = []
for o in bpy.data.objects:
    if o.type == "MESH" and o.data.shape_keys:
        for kb in o.data.shape_keys.key_blocks[1:]:
            keys.append((o.name, kb.name))
R["shape_keys"] = keys
look(cam, (0, -0.05, 0.80), 0, 4, 0.95, 70)
render(os.path.join(out, "expr_neutral.png"))
for name in sorted({k for _, k in keys}):
    for o in bpy.data.objects:
        if o.type == "MESH" and o.data.shape_keys and name in o.data.shape_keys.key_blocks:
            o.data.shape_keys.key_blocks[name].value = 1.0
    render(os.path.join(out, f"expr_{name}.png"))
    for o in bpy.data.objects:
        if o.type == "MESH" and o.data.shape_keys and name in o.data.shape_keys.key_blocks:
            o.data.shape_keys.key_blocks[name].value = 0.0

# 2. poses through Rigify FK controls
for pb in rig.pose.bones:
    if "IK_FK" in pb.keys():
        pb["IK_FK"] = 1.0
pb = rig.pose.bones
POSES = {
    "arms_up": {"upper_arm_fk.L": (0, 0, 0), "upper_arm_fk.R": (0, 0, 0)},
}


def set_rot(name, euler_deg):
    b = pb.get(name)
    if b is None:
        return False
    b.rotation_mode = "XYZ"
    b.rotation_euler = Euler([math.radians(a) for a in euler_deg])
    return True


def reset():
    for b in pb:
        b.rotation_mode = "XYZ" if b.rotation_mode == "QUATERNION" else b.rotation_mode
        b.rotation_euler = (0, 0, 0)
        b.location = (0, 0, 0)


def pose_and_render(name, rots, views):
    reset()
    ok = {k: set_rot(k, v) for k, v in rots.items()}
    bpy.context.view_layer.update()
    for vname, (yaw, el, tgt, dist) in views.items():
        look(cam, tgt, yaw, el, dist, 60)
        render(os.path.join(out, f"pose_{name}_{vname}.png"))
    return ok


bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y = 600, 900
FULL = {"front": (0, 6, (0, 0, 0.56), 2.6), "side": (-90, 6, (0, 0, 0.56), 2.6)}
# Rotation axes in each bone's local frame (Rigify FK controls: X bends, Z rolls); sign checked by the renders.
R["poses"] = {
    "a_pose": pose_and_render("a_pose", {}, FULL),
    "arms_raised": pose_and_render("arms_raised", {"upper_arm_fk.L": (0, 0, 70), "upper_arm_fk.R": (0, 0, -70)}, FULL),
    "elbows_90": pose_and_render("elbows_90", {"forearm_fk.L": (90, 0, 0), "forearm_fk.R": (90, 0, 0),
                                               "upper_arm_fk.L": (-30, 0, 0), "upper_arm_fk.R": (-30, 0, 0)}, FULL),
    "knee_hip": pose_and_render("knee_hip", {"thigh_fk.L": (-60, 0, 0), "shin_fk.L": (80, 0, 0)}, FULL),
    "head_turn_tilt": pose_and_render("head_turn_tilt", {"head": (10, 30, 8)}, FULL),
}
# 3. gaze: rotate the eye controls (eye bones were added as basic.super_copy controls)
reset()
eye_ctrl = [n for n in ("eye.L", "eye.R") if n in pb]
for n in eye_ctrl:
    set_rot(n, (0, 0, 25))
bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y = 600, 600
look(cam, (0, -0.05, 0.80), 0, 4, 0.95, 70)
render(os.path.join(out, "gaze_side.png"))
R["gaze_controls"] = eye_ctrl
reset()

# 4. glTF round trip
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
meshes = [o for o in bpy.data.objects if o.type == "MESH"]
R["gltf_roundtrip"] = {
    "file_mb": round(os.path.getsize(glb) / 1e6, 1), "armatures": len(arms), "joints": [len(a.data.bones) for a in arms],
    "meshes": len(meshes), "skinned_meshes": sum(1 for o in meshes if any(m.type == "ARMATURE" for m in o.modifiers)),
    "morph_targets": sorted({kb.name for o in meshes if o.data.shape_keys for kb in o.data.shape_keys.key_blocks[1:]}),
    "materials": len(bpy.data.materials),
}
json.dump(R, open(os.path.join(out, "rig_tests.json"), "w"), indent=1)
print(json.dumps({k: v for k, v in R.items() if k != "rig"}, indent=1))
print("controls sample:", R["rig"]["controls"][:40])
