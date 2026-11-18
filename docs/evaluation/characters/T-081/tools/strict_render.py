"""T-081 strict comparison: renders several masters in ONE run with identical cameras, lights, world, exposure,
samples and resolution (headless Blender; read-only on the inputs).

    blender -b --factory-startup -P docs/evaluation/characters/T-081/tools/strict_render.py -- <out_dir>
        <tag>=<master.blend> [<tag>=<master.blend> ...] [--spp 16] [--px 360]

Cameras are fixed constants, not framed per model, so every version is seen from exactly the same place:
perspective 70 mm (sensor fit vertical, 36 mm), elevation 5 deg, yaws from the girl's reference_index.json
(yaw convention: 0 = camera in front, +90 = camera on the character's left):
  body_front 0, body_34 -45 (sheet30_front_left), body_side 90 (sheet30_left), body_back 180 -> target (0, 0, 0.56),
  frame height 1.26 m, image px x 1.6 px;
  face_front 0, face_34 -45 (ref_30 front-left) -> target (0, 0, 0.735), frame height 0.36 m, image px x px.
Lighting: the shared calibration character_neutral/1 (render_calibration.json), re-aimed per camera direction
exactly as every other evaluation render; the calibration's world and exposure. Rest pose (A-pose), every face
control 0 (the version's own neutral). Cycles CPU + OIDN. Writes <out_dir>/<tag>/<view>.png and cameras.json."""
import json
import math
import os
import sys

import bpy
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "pipeline", "charsys"))
import render_calibration as RC  # noqa: E402
import render_engine  # noqa: E402

LENS, SENSOR, ELEV = 70.0, 36.0, 5.0
BODY = {"target": (0.0, 0.0, 0.56), "height": 1.26, "aspect": 1.6}
FACE = {"target": (0.0, 0.0, 0.735), "height": 0.36, "aspect": 1.0}
VIEWS = [("body_front", 0, BODY), ("body_34", -45, BODY), ("body_side", 90, BODY), ("body_back", 180, BODY),
         ("face_front", 0, FACE), ("face_34", -45, FACE)]


def arg(argv, name, default):
    return argv[argv.index(name) + 1] if name in argv else default


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    out = os.path.abspath(argv[0])
    masters = [a.split("=", 1) for a in argv[1:] if "=" in a and not a.startswith("--")]
    spp, px = int(arg(argv, "--spp", 16)), int(arg(argv, "--px", 360))
    fov = 2 * math.atan(SENSOR / 2 / LENS)
    cams = {}
    for tag, path in masters:
        bpy.ops.wm.open_mainfile(filepath=os.path.abspath(path))
        sc = bpy.context.scene
        for o in list(sc.objects):
            if o.type in ("LIGHT", "CAMERA"):
                bpy.data.objects.remove(o, do_unlink=True)
        lrig = RC.apply(sc, RC.load(RC.DEFAULT))
        render_engine.configure(sc, "cycles", spp, cycles_device="CPU", cycles_denoiser="OPENIMAGEDENOISE")
        sc.cycles.seed = 0
        rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
        for k in [k for k in rig.keys() if k.startswith("face_")]:
            rig[k] = 0.0
        rig.update_tag()
        cam = bpy.data.objects.new("StrictCam", bpy.data.cameras.new("StrictCam"))
        sc.collection.objects.link(cam)
        sc.camera = cam
        cam.data.type = "PERSP"
        cam.data.lens = LENS
        cam.data.sensor_fit = "VERTICAL"
        cam.data.sensor_height = SENSOR
        cam.data.clip_start = 0.01
        os.makedirs(os.path.join(out, tag), exist_ok=True)
        for name, yaw, fr in VIEWS:
            a, el = math.radians(yaw), math.radians(ELEV)
            d = Vector((math.sin(a) * math.cos(el), -math.cos(a) * math.cos(el), math.sin(el)))
            dist = fr["height"] / 2 / math.tan(fov / 2)
            target = Vector(fr["target"])
            cam.location = target + d * dist
            cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
            RC.orient(lrig, d)
            sc.render.resolution_y = int(px * fr["aspect"])
            sc.render.resolution_x = px
            sc.render.resolution_percentage = 100
            sc.frame_set(sc.frame_current)
            sc.render.filepath = os.path.join(out, tag, name + ".png")
            bpy.ops.render.render(write_still=True)
            cams[name] = {"yaw_deg": yaw, "elevation_deg": ELEV, "lens_mm": LENS, "target": list(fr["target"]),
                          "distance_m": round(dist, 4), "frame_height_m": fr["height"],
                          "resolution": [sc.render.resolution_x, sc.render.resolution_y], "samples": spp}
            print("rendered", tag, name)
    json.dump({"masters": dict(masters), "lighting": RC.DEFAULT, "views": cams}, open(os.path.join(out, "cameras.json"), "w"), indent=1)


main()
