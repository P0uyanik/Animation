"""T-113 expression sheet renderer (headless Blender; read-only on the inputs). Character-independent.

    blender -b --factory-startup -P docs/evaluation/characters/T-113/expr_sheet.py -- <job.json>

job.json: {"out": dir, "samples": N, "px": W, "frame": "face"|"eyes", "frame_h": m, "dz": m, "yaw": deg, "elev": deg,
           "columns": [{"tag", "blend"}], "rows": [{"tag", "controls": {"face_X": w}, "gaze_deg": [yaw, pitch]}]}
Every row is rendered for every column (same camera per row: the first column's eye centres). The T-087 light rig
(character_neutral/1, render_calibration), 70 mm lens, Cycles CPU with OIDN, seed 0. A control the master lacks is
skipped and listed in <out>/missing.json (what the engine would skip too). gaze_deg turns both eye controls
(eye.L / eye.R about Z and X, as test_face_v3b turns them; engine signs: + yaw = the character's left, + pitch = up) for the emotions' gaze bias."""
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

FRAMES = {"eyes": (0.12, 0.5, 0.005), "face": (0.30, 1.0, -0.035)}


def main():
    job = json.load(open(sys.argv[sys.argv.index("--") + 1]))
    out = os.path.abspath(job["out"])
    fh, aspect, dz = FRAMES[job.get("frame", "face")]
    fh, dz = float(job.get("frame_h", fh)), float(job.get("dz", dz))  # per character: head size differs
    fov = 2 * math.atan(36.0 / 2 / 70.0)
    missing = {}
    targets = {}
    for col in job["columns"]:
        bpy.ops.wm.open_mainfile(filepath=os.path.abspath(col["blend"]))
        sc = bpy.context.scene
        for o in list(sc.objects):
            if o.type in ("LIGHT", "CAMERA"):
                bpy.data.objects.remove(o, do_unlink=True)
        for o in sc.objects:
            o.hide_render = "fur" in o.name.lower() or o.name.startswith(("WGT", "garment.collider"))
        lrig = RC.apply(sc, RC.load(RC.DEFAULT))
        render_engine.configure(sc, "cycles", int(job.get("samples", 8)), cycles_device="CPU",
                                cycles_denoiser="OPENIMAGEDENOISE")
        sc.cycles.seed = 0
        rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
        cam = bpy.data.objects.new("SheetCam", bpy.data.cameras.new("SheetCam"))
        sc.collection.objects.link(cam)
        sc.camera = cam
        cam.data.lens, cam.data.sensor_fit, cam.data.sensor_height, cam.data.clip_start = 70.0, "VERTICAL", 36.0, 0.01
        sc.render.resolution_x = int(job.get("px", 320))
        sc.render.resolution_y = int(round(sc.render.resolution_x * aspect))
        sc.render.resolution_percentage = 100
        sc.render.image_settings.file_format = "PNG"
        for row in job["rows"]:
            for k in [k for k in rig.keys() if k.startswith("face_")]:
                rig[k] = 0.0
            for k, v in (row.get("controls") or {}).items():
                if k in rig.keys():
                    rig[k] = float(v)
                else:
                    missing.setdefault(col["tag"], {}).setdefault(row["tag"], []).append(k)
            gy, gp = row.get("gaze_deg", [0.0, 0.0])
            for s in "LR":
                b = rig.pose.bones.get(f"eye.{s}")
                if b is not None:
                    b.rotation_mode = "XYZ"
                    b.rotation_euler = (math.radians(-gp), 0.0, math.radians(-gy))  # engine: + yaw = left, + pitch = up
            rig.update_tag()
            bpy.context.view_layer.update()
            if row["tag"] not in targets:
                c = sum((bpy.data.objects[f"eye.{s}"].matrix_world.translation for s in ("L", "R")), Vector()) / 2
                targets[row["tag"]] = Vector((0.0, c.y, c.z + dz))
            target = targets[row["tag"]]
            a, el = math.radians(job.get("yaw", -30.0)), math.radians(job.get("elev", 6.0))
            d = Vector((math.sin(a) * math.cos(el), -math.cos(a) * math.cos(el), math.sin(el)))
            cam.location = target + d * (fh / 2 / math.tan(fov / 2))
            cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
            RC.orient(lrig, d)
            sc.frame_set(sc.frame_current)
            os.makedirs(os.path.join(out, row["tag"]), exist_ok=True)
            sc.render.filepath = os.path.join(out, row["tag"], f"{col['tag']}.png")
            bpy.ops.render.render(write_still=True)
            print("rendered", col["tag"], row["tag"], flush=True)
    json.dump(missing, open(os.path.join(out, "missing.json"), "w"), indent=1)


main()
