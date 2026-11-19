"""T-109 face probe renderer (headless Blender; read-only on the inputs). Character-independent.

    blender -b --factory-startup -P docs/evaluation/characters/T-109/face_probe.py -- <job.json>

job.json: {"out": dir, "engine": "cycles"|"workbench", "samples": N, "px": W, "frame": "eyes"|"face",
           "views": {"front": 0, "threequarter": -35}, "columns": [{"tag", "blend", "hide": [substr...],
           "controls": {"face_X": w}}]}
Like T-089b's face_strip.py, but each column names its own hidden objects (substring match) and face controls, so one
master can be rendered with and without glasses, lens or lids. T-087 light rig (character_neutral/1), 70 mm lens,
6 deg elevation; one camera per frame/view for every column (target from the first column's eye centres)."""
import json
import math
import os
import sys

import bpy
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "pipeline", "charsys"))
import render_calibration as RC  # noqa: E402
import render_engine  # noqa: E402

FRAMES = {"eyes": (0.12, 0.5, 0.005), "face": (0.32, 1.0, -0.04), "lower": (0.26, 1.0, -0.06)}


def main():
    job = json.load(open(sys.argv[sys.argv.index("--") + 1]))
    out = os.path.abspath(job["out"])
    fh, aspect, dz = FRAMES[job.get("frame", "face")]
    fov = 2 * math.atan(36.0 / 2 / 70.0)
    target = None
    loaded = None
    for col in job["columns"]:
        if loaded != col["blend"]:
            bpy.ops.wm.open_mainfile(filepath=os.path.abspath(col["blend"]))
            loaded = col["blend"]
        sc = bpy.context.scene
        for o in list(sc.objects):
            if o.type in ("LIGHT", "CAMERA"):
                bpy.data.objects.remove(o, do_unlink=True)
        hide = tuple(col.get("hide", job.get("hide", ["fur"])))
        for o in sc.objects:
            o.hide_render = any(t in o.name.lower() for t in hide) or o.name.startswith(("WGT", "garment.collider"))
        lrig = RC.apply(sc, RC.load(RC.DEFAULT))
        if job.get("engine") == "workbench":
            sc.render.engine = "BLENDER_WORKBENCH"
            sc.display.shading.light = "STUDIO"
            sc.display.shading.color_type = "MATERIAL"
        else:
            render_engine.configure(sc, "cycles", int(job.get("samples", 8)), cycles_device="CPU",
                                    cycles_denoiser="OPENIMAGEDENOISE")
            sc.cycles.seed = 0
        rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
        if target is None:
            c = sum((bpy.data.objects[f"eye.{s}"].matrix_world.translation for s in ("L", "R")), Vector()) / 2
            target = Vector((0.0, c.y, c.z + dz))
        for k in [k for k in rig.keys() if k.startswith("face_")]:
            rig[k] = 0.0
        for k, v in (col.get("controls") or {}).items():
            rig[k] = float(v)
        rig.update_tag()
        bpy.context.view_layer.update()
        cam = bpy.data.objects.new("ProbeCam", bpy.data.cameras.new("ProbeCam"))
        sc.collection.objects.link(cam)
        sc.camera = cam
        cam.data.lens, cam.data.sensor_fit, cam.data.sensor_height, cam.data.clip_start = 70.0, "VERTICAL", 36.0, 0.01
        sc.render.resolution_x = int(job.get("px", 320))
        sc.render.resolution_y = int(round(sc.render.resolution_x * aspect))
        sc.render.resolution_percentage = 100
        sc.render.image_settings.file_format = "PNG"
        os.makedirs(os.path.join(out, col["tag"]), exist_ok=True)
        for vn, yaw in job.get("views", {"front": 0.0, "threequarter": -35.0}).items():
            a, el = math.radians(yaw), math.radians(6.0)
            d = Vector((math.sin(a) * math.cos(el), -math.cos(a) * math.cos(el), math.sin(el)))
            cam.location = target + d * (fh / 2 / math.tan(fov / 2))
            cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
            RC.orient(lrig, d)
            sc.frame_set(sc.frame_current)
            sc.render.filepath = os.path.join(out, col["tag"], f"{vn}.png")
            bpy.ops.render.render(write_still=True)
            print("rendered", col["tag"], vn, flush=True)
        bpy.data.objects.remove(cam, do_unlink=True)


main()
