"""T-126c renders of the dress build (same calibrated light and lens as the T-119 pose shots).

    blender -b --factory-startup -P docs/evaluation/characters/T-126/dress/shots.py -- <out dir> <preview|sheet|crops>
        <master.blend> [--samples 16] [--px 480] [--only shot,shot] [--hide prefix,prefix] [--no-fibres]

A shot is a pose (FK bones turned about a world axis through the bone's head, on the rest pose), a camera (target,
frame height, yaw, elevation) and object-name prefixes hidden in that shot. ``--no-fibres`` hides the generated surface
fibres (geometry and shader only). Writes <out>/<shot>.png and
<out>/shots.json. ``compose.py`` lays the tiles out next to her references."""
import json
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "pipeline", "charsys"))
import render_calibration as RC  # noqa: E402
import render_engine  # noqa: E402

DOWN = [("upper_arm_fk.{s}", "Y", 35.0, "LR", True)]  # arms lowered from the A-pose, as in 16
A_POSE = []
FIGURE = [
    {"name": "figure_front", "label": "A-pose | front (09 panel 01)", "pose": A_POSE, "cam": ((0.0, 0.0, 0.33), 0.72, 0.0, 4.0)},
    {"name": "figure_side", "label": "A-pose | side (09 panel 01)", "pose": A_POSE, "cam": ((0.0, 0.0, 0.33), 0.72, 90.0, 4.0)},
    {"name": "figure_34", "label": "arms down | 3/4 front", "pose": DOWN, "cam": ((0.0, 0.0, 0.33), 0.72, 35.0, 8.0)},
]
SHOTS = {
    "preview": FIGURE,
    "sheet": FIGURE + [
        {"name": "figure_back", "label": "arms down | 3/4 back", "pose": DOWN, "cam": ((0.0, 0.0, 0.33), 0.72, 145.0, 8.0),
         "hide": ("hair",)},
        {"name": "w05", "label": "arms down | the 16 (W05) framing", "pose": DOWN, "cam": ((0.03, 0.0, 0.42), 0.50, -18.0, 2.0),
         "hide": ("hair",)},
    ],
    "crops": [
        {"name": "collar", "label": "collar | front", "pose": DOWN, "cam": ((0.0, -0.02, 0.645), 0.20, 0.0, 6.0), "hide": ("hair",)},
        {"name": "collar_34", "label": "collar | 3/4", "pose": DOWN, "cam": ((0.0, -0.02, 0.645), 0.20, 45.0, 10.0), "hide": ("hair",)},
        {"name": "cuff", "label": "sleeve and rib cuff (A-pose)", "pose": A_POSE, "cam": ((0.17, 0.0, 0.47), 0.17, 15.0, 6.0)},
        {"name": "hem", "label": "skirt pattern and rib hem", "pose": DOWN, "cam": ((0.0, -0.08, 0.35), 0.26, -15.0, 2.0)},
        {"name": "boots", "label": "boots and tights | 3/4", "pose": DOWN, "cam": ((0.0, -0.02, 0.07), 0.30, 40.0, 8.0)},
        {"name": "boots_side", "label": "boot | side, sole stitch", "pose": DOWN, "cam": ((0.06, -0.03, 0.06), 0.24, 90.0, 4.0)},
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


def setup(sc, spp):
    """Calibrated light, Cycles CPU + OIDN, a 70 mm camera. Returns (camera, light rig, vertical fov)."""
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
    return cam, lrig, 2 * math.atan(18.0 / 70.0)


def aim(cam, lrig, fov, shot_cam):
    target, frame_h, yaw, elev = shot_cam
    a, el = math.radians(yaw), math.radians(elev)
    d = Vector((math.sin(a) * math.cos(el), -math.cos(a) * math.cos(el), math.sin(el)))
    cam.location = Vector(target) + d * (frame_h / 2 / math.tan(fov / 2))
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    RC.orient(lrig, d)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    out, which, blend = os.path.abspath(argv[0]), argv[1], argv[2]
    opt = {k: argv[argv.index(k) + 1] for k in ("--samples", "--px", "--only", "--hide") if k in argv}
    spp, px = int(opt.get("--samples", 16)), int(opt.get("--px", 480))
    only = set(opt["--only"].split(",")) if "--only" in opt else None
    always = tuple(opt["--hide"].split(",")) if "--hide" in opt else ()
    no_fibres = "--no-fibres" in argv
    shots = [s for s in SHOTS[which] if only is None or s["name"] in only]
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(blend))
    sc = bpy.context.scene
    rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    for k in [k for k in rig.keys() if k.startswith("face_")]:
        rig[k] = 0.0
    cam, lrig, fov = setup(sc, spp)
    hidden_before = {o.name: o.hide_render for o in bpy.data.objects}
    for s in shots:
        pose(rig, s["pose"])
        hide = tuple(s.get("hide", ())) + always
        for o in bpy.data.objects:
            o.hide_render = hidden_before[o.name] or any(o.name.startswith(p) for p in hide) or (
                no_fibres and o.name.endswith(".fibres"))
        aim(cam, lrig, fov, s["cam"])
        sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = px, px, 100
        sc.render.image_settings.file_format = "PNG"
        sc.render.filepath = os.path.join(out, s["name"] + ".png")
        bpy.ops.render.render(write_still=True)
    os.makedirs(out, exist_ok=True)
    json.dump({"set": which, "blend": os.path.basename(blend), "engine": "cycles", "samples": spp, "px": px,
               "light": "character_neutral/1 (render_calibration)", "lens_mm": 70.0, "blender": bpy.app.version_string,
               "hidden_always": list(always), "fibres": not no_fibres,
               "shots": [{"name": s["name"], "label": s["label"], "pose": [list(p) for p in s["pose"]],
                          "camera": {"target": s["cam"][0], "frame_height_m": s["cam"][1], "yaw_deg": s["cam"][2],
                                     "elevation_deg": s["cam"][3]}, "hidden_prefixes": list(s.get("hide", ()))}
                         for s in shots]}, open(os.path.join(out, f"shots_{which}.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
