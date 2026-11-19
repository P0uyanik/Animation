"""T-119 evidence renders: current against candidate in the poses of the task (same cameras and lights per row).

    blender -b --factory-startup -P docs/evaluation/characters/T-119/pose_shots.py -- <out dir> <girl|boy>
        <label>=<master.blend> ... [--samples 16] [--px 360] [--engine cycles|workbench] [--only shot,shot]

Each column opens one A-pose master and renders every shot of the set. A shot is a pose (FK bones rotated about a
world axis through the bone's head, applied in order on the rest pose), a camera (target, frame height, yaw,
elevation) and the object-name prefixes hidden in that shot only (the girl's curls cover the collar from the side,
so hair is hidden in the collar rows and nowhere else). Writes <out>/<label>/<shot>.png and <out>/shots.json;
``compose_sheet.py`` lays the tiles out as the strict sheet."""
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

ARMS_DOWN = [("upper_arm_fk.{s}", "Y", 35.0, "LR", True)]
# (bone pattern, world axis, degrees, sides, mirror the angle on the right side)
SHOTS = {
    "girl": [
        {"name": "rest_side", "label": "rest | side, collar", "pose": ARMS_DOWN,
         "cam": ((0.0, -0.01, 0.60), 0.24, 90.0, 6.0), "hide": ("hair",)},
        {"name": "half_reach_side", "label": "half reach (one arm, 37.5 deg) | side", "hide": ("hair",),
         "pose": ARMS_DOWN + [("upper_arm_fk.{s}", "X", -37.5, "L", False)], "cam": ((0.0, -0.01, 0.60), 0.24, 90.0, 6.0)},
        {"name": "full_reach_side", "label": "full reach (one arm, 75 deg) | side", "hide": ("hair",),
         "pose": ARMS_DOWN + [("upper_arm_fk.{s}", "X", -75.0, "L", False)], "cam": ((0.0, -0.01, 0.60), 0.24, 90.0, 6.0)},
        {"name": "full_reach_front", "label": "full reach (one arm, 75 deg) | 3/4 front", "hide": ("hair",),
         "pose": ARMS_DOWN + [("upper_arm_fk.{s}", "X", -75.0, "L", False)], "cam": ((0.0, -0.02, 0.57), 0.34, 35.0, 8.0)},
        {"name": "bloomers_front", "label": "rest | bloomer cuffs, front", "pose": ARMS_DOWN,
         "cam": ((0.0, 0.0, 0.33), 0.34, 0.0, 3.0)},
        {"name": "bloomers_back", "label": "rest | bloomer cuffs, 3/4 back", "pose": ARMS_DOWN,
         "cam": ((0.0, 0.0, 0.33), 0.34, 150.0, 3.0)},
    ],
    "boy": [
        {"name": "ankle_rest", "label": "rest | ankle, side", "pose": ARMS_DOWN,
         "cam": ((0.07, -0.02, 0.085), 0.24, 90.0, 3.0)},
        {"name": "ankle_up", "label": "ankle flexion, toes up 25 deg | side",
         "pose": ARMS_DOWN + [("foot_fk.{s}", "X", 25.0, "LR", False)], "cam": ((0.07, -0.02, 0.085), 0.24, 90.0, 3.0)},
        {"name": "ankle_down", "label": "ankle flexion, toes down 30 deg | side",
         "pose": ARMS_DOWN + [("foot_fk.{s}", "X", -30.0, "LR", False)], "cam": ((0.07, -0.02, 0.085), 0.24, 90.0, 3.0)},
        {"name": "ankle_front", "label": "ankle flexion, toes down 30 deg | 3/4 front",
         "pose": ARMS_DOWN + [("foot_fk.{s}", "X", -30.0, "LR", False)], "cam": ((0.0, -0.02, 0.085), 0.26, 35.0, 10.0)},
        {"name": "pickup", "label": "pickup close-up | hand, cheek, cuff",
         "pose": ARMS_DOWN + [("upper_arm_fk.{s}", "X", -60.0, "L", False), ("forearm_fk.{s}", "X", -70.0, "L", False)],
         "cam": ((0.09, -0.12, 0.66), 0.40, 40.0, 5.0)},
        {"name": "figure_front", "label": "rest | figure, front", "pose": ARMS_DOWN,
         "cam": ((0.0, 0.0, 0.5), 1.1, 0.0, 5.0)},
    ],
}


def pose(rig, steps):
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


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    out, which = os.path.abspath(argv[0]), argv[1]
    opt = {k: argv[argv.index(k) + 1] for k in ("--samples", "--px", "--engine", "--only") if k in argv}
    spp, px, engine = int(opt.get("--samples", 16)), int(opt.get("--px", 360)), opt.get("--engine", "cycles")
    only = set(opt["--only"].split(",")) if "--only" in opt else None
    cols = [a.split("=", 1) for a in argv[2:] if "=" in a and not a.startswith("--")]
    shots = [s for s in SHOTS[which] if only is None or s["name"] in only]
    record = {"set": which, "engine": engine, "samples": spp, "px": px, "light": "character_neutral/1 (render_calibration)",
              "lens_mm": 70.0, "blender": bpy.app.version_string, "columns": [], "shots": [
                  {"name": s["name"], "label": s["label"], "pose": [list(p) for p in s["pose"]],
                   "camera": {"target": s["cam"][0], "frame_height_m": s["cam"][1], "yaw_deg": s["cam"][2],
                              "elevation_deg": s["cam"][3]}, "hidden_prefixes": list(s.get("hide", ()))} for s in shots]}
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
        if engine == "cycles":
            render_engine.configure(sc, "cycles", spp, cycles_device="CPU", cycles_denoiser="OPENIMAGEDENOISE")
            sc.cycles.seed = 0
        else:
            sc.render.engine = "BLENDER_WORKBENCH"
            sc.display.shading.light, sc.display.shading.color_type = "STUDIO", "MATERIAL"
            sc.display.shading.show_cavity = True
        cam = bpy.data.objects.new("ShotCam", bpy.data.cameras.new("ShotCam"))
        sc.collection.objects.link(cam)
        sc.camera = cam
        cam.data.lens, cam.data.sensor_fit, cam.data.sensor_height = 70.0, "VERTICAL", 36.0
        fov = 2 * math.atan(18.0 / 70.0)
        hidden_before = {o.name: o.hide_render for o in bpy.data.objects}
        for s in shots:
            pose(rig, s["pose"])
            for o in bpy.data.objects:
                o.hide_render = hidden_before[o.name] or any(o.name.startswith(p) for p in s.get("hide", ()))
            target, frame_h, yaw, elev = s["cam"]
            a, el = math.radians(yaw), math.radians(elev)
            d = Vector((math.sin(a) * math.cos(el), -math.cos(a) * math.cos(el), math.sin(el)))
            cam.location = Vector(target) + d * (frame_h / 2 / math.tan(fov / 2))
            cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
            RC.orient(lrig, d)
            sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = px, px, 100
            sc.render.image_settings.file_format = "PNG"
            sc.render.filepath = os.path.join(out, label, s["name"] + ".png")
            bpy.ops.render.render(write_still=True)
        record["columns"].append({"label": label, "blend": os.path.basename(blend)})
    os.makedirs(out, exist_ok=True)
    json.dump(record, open(os.path.join(out, "shots.json"), "w"), indent=1)


main()
