"""T-132 100% crops: current against candidate, same camera, light and pose per row (T-119 pose_shots.py conventions).

    blender -b --factory-startup -P docs/evaluation/characters/T-132/crops.py -- <out dir> <boy|girl> \
        <label>=<master.blend> ... [--samples 16] [--px 400]

A shot camera target is either [x, y, z] or an object name (its world bounding-box centre after posing, for hands).
Writes <out>/<label>/<shot>.png and <out>/shots.json; compose_crops.py lays them out unscaled (100%)."""
import json
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "pipeline", "charsys"))
import render_calibration as RC  # noqa: E402
import render_engine  # noqa: E402

AD = [("upper_arm_fk.{s}", "Y", 35.0, "LR", True)]
HALF = AD + [("upper_arm_fk.{s}", "X", -37.5, "L", False)]
FULL = AD + [("upper_arm_fk.{s}", "X", -75.0, "L", False)]
SIDE_COLLAR = ((0.0, -0.01, 0.60), 0.24, 90.0, 6.0)
SHOTS = {
    "boy": [
        ("crown_back", "crown / whorl, back-top", AD, ((0.0, 0.03, 0.93), 0.30, 180.0, 40.0), ()),
        ("crown_3q", "crown petals, 3/4 front", AD, ((0.0, 0.0, 0.95), 0.26, -35.0, 20.0), ()),
        ("ankle_rest", "ankle notch, rest, side", AD, ((0.07, -0.02, 0.085), 0.20, 90.0, 3.0), ()),
        ("ankle_up", "ankle notch, toes up 25", AD + [("foot_fk.{s}", "X", 25.0, "LR", False)],
         ((0.07, -0.02, 0.085), 0.20, 90.0, 3.0), ()),
        ("ankle_down", "ankle notch, toes down 30", AD + [("foot_fk.{s}", "X", -30.0, "LR", False)],
         ((0.07, -0.02, 0.085), 0.20, 90.0, 3.0), ()),
        ("hand_L", "hand.L, rest, side", AD, ("hand.L", 0.16, 90.0, 5.0), ()),
    ],
    "girl": [
        ("sweeps_front", "sweeps over the forehead, front", AD, ((0.0, 0.0, 0.87), 0.30, 0.0, 8.0), ()),
        ("curl_ends_back", "curl ends, back", AD, ((0.0, 0.0, 0.70), 0.34, 180.0, 5.0), ()),
        ("flower", "flower on the bun, 3/4 front", AD, ((0.0, 0.05, 1.02), 0.24, 35.0, 15.0), ()),
        ("collar_rest", "collar, rest, side (hair hidden)", AD, SIDE_COLLAR, ("hair",)),
        ("collar_half", "collar, half reach 37.5", HALF, SIDE_COLLAR, ("hair",)),
        ("collar_full", "collar, full reach 75", FULL, SIDE_COLLAR, ("hair",)),
        ("bloomers_front", "bloomer cuffs, front", AD, ((0.0, 0.0, 0.33), 0.26, 0.0, 3.0), ()),
        ("bloomers_back", "bloomer cuffs, 3/4 back", AD, ((0.0, 0.0, 0.33), 0.26, 150.0, 3.0), ()),
        ("hand_L", "hand.L, rest, side", AD, ("hand.L", 0.16, 90.0, 5.0), ()),
    ],
}


def pose(rig, steps):
    """As T-119 pose_shots.py: FK (IK_FK 1), each step rotates a bone about a world axis through its head."""
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="POSE")
    for pb in rig.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
        if "IK_FK" in pb.keys():
            pb["IK_FK"] = 1.0
    bpy.context.view_layer.update()
    for pattern, axis, deg, sides, mirror in steps:
        for s in sides:
            pb = rig.pose.bones[pattern.format(s=s)]
            a = -deg if (mirror and s == "R") else deg
            hw = rig.matrix_world @ pb.head
            rm = Matrix.Translation(hw) @ Matrix.Rotation(math.radians(a), 4, axis) @ Matrix.Translation(-hw)
            pb.matrix = rig.matrix_world.inverted() @ rm @ rig.matrix_world @ pb.matrix
            bpy.context.view_layer.update()
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.context.view_layer.update()


def bbox_centre(name):
    o = bpy.data.objects[name]
    dg = bpy.context.evaluated_depsgraph_get()
    m = o.evaluated_get(dg).to_mesh()
    vs = [o.matrix_world @ v.co for v in m.vertices]
    lo = Vector([min(v[i] for v in vs) for i in range(3)])
    hi = Vector([max(v[i] for v in vs) for i in range(3)])
    return (lo + hi) / 2


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    out, which = os.path.abspath(argv[0]), argv[1]
    opt = {k: argv[argv.index(k) + 1] for k in ("--samples", "--px") if k in argv}
    spp, px = int(opt.get("--samples", 16)), int(opt.get("--px", 400))
    cols = [a.split("=", 1) for a in argv[2:] if "=" in a and not a.startswith("--")]
    rec = {"set": which, "samples": spp, "px": px, "light": "character_neutral/1", "lens_mm": 70.0,
           "blender": bpy.app.version_string, "columns": [], "shots": [
               {"name": n, "label": l, "pose": [list(p) for p in ps], "camera": list(c), "hidden_prefixes": list(h)}
               for n, l, ps, c, h in SHOTS[which]]}
    for label, blend in cols:
        bpy.ops.wm.open_mainfile(filepath=os.path.abspath(blend))
        sc = bpy.context.scene
        rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
        for k in [k for k in rig.keys() if k.startswith("face_")]:
            rig[k] = 0.0
        for o in list(sc.objects):
            if o.type in ("LIGHT", "CAMERA"):
                bpy.data.objects.remove(o, do_unlink=True)
        lrig = RC.apply(sc, RC.load(RC.DEFAULT))
        render_engine.configure(sc, "cycles", spp, cycles_device="CPU", cycles_denoiser="OPENIMAGEDENOISE")
        sc.cycles.seed = 0
        cam = bpy.data.objects.new("ShotCam", bpy.data.cameras.new("ShotCam"))
        sc.collection.objects.link(cam)
        sc.camera = cam
        cam.data.lens, cam.data.sensor_fit, cam.data.sensor_height = 70.0, "VERTICAL", 36.0
        fov = 2 * math.atan(18.0 / 70.0)
        before = {o.name: o.hide_render for o in bpy.data.objects}
        for name, _, steps, (target, fh, yaw, elev), hide in SHOTS[which]:
            pose(rig, steps)
            for o in bpy.data.objects:
                o.hide_render = before[o.name] or any(o.name.startswith(p) for p in hide)
            t = bbox_centre(target) if isinstance(target, str) else Vector(target)
            a, el = math.radians(yaw), math.radians(elev)
            d = Vector((math.sin(a) * math.cos(el), -math.cos(a) * math.cos(el), math.sin(el)))
            cam.location = t + d * (fh / 2 / math.tan(fov / 2))
            cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
            RC.orient(lrig, d)
            sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = px, px, 100
            sc.render.image_settings.file_format = "PNG"
            sc.render.filepath = os.path.join(out, label, name + ".png")
            bpy.ops.render.render(write_still=True)
        rec["columns"].append({"label": label, "blend": os.path.relpath(os.path.abspath(blend), ROOT)})
    os.makedirs(out, exist_ok=True)
    json.dump(rec, open(os.path.join(out, "shots.json"), "w"), indent=1)


main()
