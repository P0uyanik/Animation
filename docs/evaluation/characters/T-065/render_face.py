"""T-065 face close-ups: renders a list of shots of a built master (headless Blender; read-only on the input).

    blender -b --factory-startup -P docs/evaluation/characters/T-065/render_face.py -- <master.blend> <out_dir>
        --shots "Neutral@0,Neutral@35,Smile@0" [--engine CYCLES|WORKBENCH] [--tile 384] [--samples 16] [--width 0.27]
        [--set "face_Blink.L=0.5;face_MouthSmile=0.3"] [--dx 0] [--dz 0]

A shot is <preset>@<yaw degrees>; <preset> "Neutral" = every face control at 0; "A+B" adds presets; "A*0.5" scales.
Framing and lighting as pipeline/charsys/tests/face_expression_sheet.py (orthographic, framed on LM_eye_*/LM_chin,
shared calibration character_neutral/1). Writes <out_dir>/<preset>_<yaw>.png."""
import math
import os
import sys

import bpy
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "pipeline", "charsys"))
import render_calibration as RC  # noqa: E402


def arg(argv, name, default):
    return argv[argv.index(name) + 1] if name in argv else default


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    src, out = os.path.abspath(argv[0]), os.path.abspath(argv[1])
    os.makedirs(out, exist_ok=True)
    shots = arg(argv, "--shots", "Neutral@0").split(",")
    engine = arg(argv, "--engine", "CYCLES")
    tile, width = int(arg(argv, "--tile", 384)), float(arg(argv, "--width", 0.27))
    extra = [kv.split("=") for kv in arg(argv, "--set", "").split(";") if "=" in kv]
    bpy.ops.wm.open_mainfile(filepath=src)
    sc = bpy.context.scene
    for o in list(sc.objects):
        if o.type in ("LIGHT", "CAMERA"):
            bpy.data.objects.remove(o, do_unlink=True)
    rig_l = RC.apply(sc, RC.load())
    for o in sc.objects:  # --only <name prefixes>: debug views of single parts
        if "--only" in argv and o.type == "MESH" and not o.name.startswith(tuple(arg(argv, "--only", "").split(","))):
            o.hide_render = True
    if engine == "WORKBENCH":
        sc.render.engine = "BLENDER_WORKBENCH"
        sc.display.shading.light = "STUDIO"
        sc.display.shading.color_type = "MATERIAL"
        sc.display.shading.show_cavity = True
    else:
        sc.render.engine = "CYCLES"
        sc.cycles.samples = int(arg(argv, "--samples", 16))
        sc.cycles.device = "CPU"
        sc.cycles.use_denoising = True
    sc.render.resolution_x = sc.render.resolution_y = tile
    rig = next(o for o in bpy.data.objects if o.type == "ARMATURE" and "ps_face_parts" in o.keys())
    lm = {o.name[3:]: o.matrix_world.translation.copy() for o in bpy.data.objects if o.name.startswith("LM_")}
    centre = (lm["eye_L"] + lm["eye_R"]) / 2 * 0.62 + lm["chin"] * 0.38
    centre.z += float(arg(argv, "--dz", 0.0))
    centre.x += float(arg(argv, "--dx", 0.0))
    centre.y = min(lm["eye_L"].y, lm["chin"].y)
    cam = bpy.data.objects.new("SheetCam", bpy.data.cameras.new("SheetCam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = width
    controls = [k for k in rig.keys() if k.startswith("face_")]
    for shot in shots:
        preset, yaw = shot.split("@") if "@" in shot else (shot, "0")
        d = Vector((math.sin(math.radians(float(yaw))), -math.cos(math.radians(float(yaw))), 0.05)).normalized()
        cam.location = centre + d * 1.5
        cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        RC.orient(rig_l, d)
        for k in controls:
            rig[k] = 0.0
        for part in preset.split("+"):
            name, w = (part.split("*") + ["1"])[:2]
            if name != "Neutral":
                if f"face_{name}" not in rig.keys():
                    raise SystemExit(f"no control face_{name}")
                rig[f"face_{name}"] = float(w)
        for k, v in extra:
            rig[k] = float(v)
        rig.update_tag()
        sc.frame_set(sc.frame_current)
        sc.render.filepath = os.path.join(out, f"{preset.replace('*', 'x')}_{yaw}.png")
        bpy.ops.render.render(write_still=True)
        print("rendered", sc.render.filepath)


main()
