"""T-089b face strip renderer (headless Blender; read-only on the inputs). Character-independent.

    blender -b --factory-startup -P docs/evaluation/characters/T-089b/face_strip.py -- <job.json>

job.json: {"out": dir, "engine": "cycles"|"workbench", "samples": N, "px": W, "frame": "eyes"|"face",
           "states": ["neutral", "blink50", "blink100", "glance"], "views": {"front": 0, "threequarter": -35},
           "hide": ["hair", ...] (object-name substrings hidden; default: hair, groom, garment, clothing, hood, acc, glasses),
           "columns": [{"tag": "...", "blend": "..."}], "render_only": [tags] (optional: resume; the other columns only
           set the shared camera target)}
Renders <out>/<tag>/<state>_<view>.png with the T-087 light rig (character_neutral/1), 70 mm lens, 6 deg elevation,
face controls zeroed except the state's (blink = face_Blink.L/R at 0.5 / 1.0; glance = both eye bones 15 deg towards
screen-left, as T-089's measure_eyes.py). One camera per frame/view for every column (target from the first column's
eye centres). compose.py lays the PNGs out as a labelled grid."""
import json
import math
import os
import sys
import time

import bpy
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "pipeline", "charsys"))
import render_calibration as RC  # noqa: E402
import render_engine  # noqa: E402

HIDE = ("hair", "groom", "garment", "clothing", "hood", "acc", "glasses", "fur")
FRAMES = {"eyes": (0.12, 0.5, 0.005), "face": (0.32, 1.0, -0.04)}  # vertical frame height m, aspect (h/w), target dz


def eye_bones(rig):
    names = [b.name for b in rig.pose.bones]
    for pat in ("eye.{s}", "MCH-eye.{s}", "DEF-eye.{s}"):
        if all(pat.format(s=s) in names for s in ("L", "R")):
            return [rig.pose.bones[pat.format(s=s)] for s in ("L", "R")]
    return []


def main():
    job = json.load(open(sys.argv[sys.argv.index("--") + 1]))
    out = os.path.abspath(job["out"])
    hide = tuple(job.get("hide", HIDE))
    fh, aspect, dz = FRAMES[job.get("frame", "eyes")]
    fov = 2 * math.atan(36.0 / 2 / 70.0)
    target = None
    result = {"job": job, "blender": bpy.app.version_string, "columns": {}}
    for col in job["columns"]:
        t0 = time.time()
        bpy.ops.wm.open_mainfile(filepath=os.path.abspath(col["blend"]))
        sc = bpy.context.scene
        for o in list(sc.objects):
            if o.type in ("LIGHT", "CAMERA"):
                bpy.data.objects.remove(o, do_unlink=True)
        for o in sc.objects:
            if any(t in o.name.lower() for t in hide):
                o.hide_render = True
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
            target = Vector((0.0, c.y, c.z + dz))  # the eye midpoint (front of the face)
        if job.get("render_only") and col["tag"] not in job["render_only"]:
            continue  # resume: this column only sets the shared camera target (already rendered)
        cam = bpy.data.objects.new("StripCam", bpy.data.cameras.new("StripCam"))
        sc.collection.objects.link(cam)
        sc.camera = cam
        cam.data.lens, cam.data.sensor_fit, cam.data.sensor_height, cam.data.clip_start = 70.0, "VERTICAL", 36.0, 0.01
        sc.render.resolution_x = int(job.get("px", 320))
        sc.render.resolution_y = int(round(sc.render.resolution_x * aspect))
        sc.render.resolution_percentage = 100
        sc.render.image_settings.file_format = "PNG"
        os.makedirs(os.path.join(out, col["tag"]), exist_ok=True)
        for state in job.get("states", ["neutral"]):
            for k in [k for k in rig.keys() if k.startswith("face_")]:
                rig[k] = 0.0
            for k in ("face_Blink.L", "face_Blink.R"):
                if k in rig.keys():
                    rig[k] = {"blink50": 0.5, "blink100": 1.0}.get(state, 0.0)
            for b in eye_bones(rig):
                b.rotation_mode = "XYZ"
                b.rotation_euler = (0, 0, math.radians(-15) if state == "glance" else 0.0)
            rig.update_tag()
            bpy.context.view_layer.update()
            for vn, yaw in job.get("views", {"front": 0.0, "threequarter": -35.0}).items():
                a, el = math.radians(yaw), math.radians(6.0)
                d = Vector((math.sin(a) * math.cos(el), -math.cos(a) * math.cos(el), math.sin(el)))
                cam.location = target + d * (fh / 2 / math.tan(fov / 2))
                cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
                RC.orient(lrig, d)
                sc.frame_set(sc.frame_current)
                sc.render.filepath = os.path.join(out, col["tag"], f"{state}_{vn}.png")
                bpy.ops.render.render(write_still=True)
                print("rendered", col["tag"], state, vn, flush=True)
        result["columns"][col["tag"]] = {"blend": col["blend"], "seconds": round(time.time() - t0, 1)}
    result["target"] = list(target)
    json.dump(result, open(os.path.join(out, "strip_result.json"), "w"), indent=1)


main()
