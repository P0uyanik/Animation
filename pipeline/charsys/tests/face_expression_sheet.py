"""Expression sheet of chosen presets for any face_generic/1 master (headless Blender; read-only on the input).

    blender -b --factory-startup -P pipeline/charsys/tests/face_expression_sheet.py -- <master.blend> <out.png>
        [--presets Neutral,SmileClosed,Smile,Surprise,Sadness,Thinking] [--yaw 0] [--tile 384] [--width 0.27]
        [--samples 32] [--cols 3]

Each preset is driven through its rig control (face_<preset>; "Neutral" = every control at 0), rendered as an
orthographic close-up framed on the face landmarks (LM_eye_*, LM_chin) with the shared render calibration
(character_neutral/1), and tiled left to right, top to bottom in the order given. Writes <out.png> and the tiles
next to it (<out>_<preset>.png). Character-agnostic: the parts come from the rig and the landmarks."""
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..")))
import render_calibration as RC  # noqa: E402


def arg(argv, name, default):
    return argv[argv.index(name) + 1] if name in argv else default


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    src, out = os.path.abspath(argv[0]), os.path.abspath(argv[1])
    presets = arg(argv, "--presets", "Neutral,SmileClosed,Smile,Surprise,Sadness,Thinking").split(",")
    yaw, tile, width = float(arg(argv, "--yaw", 0)), int(arg(argv, "--tile", 384)), float(arg(argv, "--width", 0.27))
    cols = int(arg(argv, "--cols", 3))
    bpy.ops.wm.open_mainfile(filepath=src)
    sc = bpy.context.scene
    for o in list(sc.objects):
        if o.type in ("LIGHT", "CAMERA"):
            bpy.data.objects.remove(o, do_unlink=True)
    rig_l = RC.apply(sc, RC.load())
    sc.render.engine = "CYCLES"
    sc.cycles.samples = int(arg(argv, "--samples", 32))
    sc.cycles.device = "CPU"
    sc.cycles.use_denoising = True
    sc.render.resolution_x = sc.render.resolution_y = tile
    rig = next(o for o in bpy.data.objects if o.type == "ARMATURE" and "ps_face_parts" in o.keys())
    lm = {o.name[3:]: o.matrix_world.translation.copy() for o in bpy.data.objects if o.name.startswith("LM_")}
    centre = (lm["eye_L"] + lm["eye_R"]) / 2 * 0.7 + lm["chin"] * 0.3
    centre.y = min(lm["eye_L"].y, lm["chin"].y)
    d = Vector((math.sin(math.radians(yaw)), -math.cos(math.radians(yaw)), 0.05)).normalized()
    cam = bpy.data.objects.new("SheetCam", bpy.data.cameras.new("SheetCam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = width
    cam.location = centre + d * 1.5
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    RC.orient(rig_l, d)
    controls = [k for k in rig.keys() if k.startswith("face_")]
    tiles = []
    for p in presets:
        for k in controls:
            rig[k] = 0.0
        if p != "Neutral":
            if f"face_{p}" not in rig.keys():
                raise SystemExit(f"preset {p} has no control face_{p} on this master")
            rig[f"face_{p}"] = 1.0
        rig.update_tag()
        sc.frame_set(sc.frame_current)
        path = os.path.splitext(out)[0] + f"_{p}.png"
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        img = bpy.data.images.load(path)
        a = np.array(img.pixels[:], dtype=np.float32).reshape(tile, tile, 4)
        tiles.append(a)
        bpy.data.images.remove(img)
    rows = math.ceil(len(tiles) / cols)
    sheet = np.ones((rows * tile, cols * tile, 4), dtype=np.float32)
    for i, a in enumerate(tiles):
        r, c = divmod(i, cols)
        y0 = (rows - 1 - r) * tile  # image pixels start at the bottom row
        sheet[y0:y0 + tile, c * tile:(c + 1) * tile] = a
    im = bpy.data.images.new("sheet", cols * tile, rows * tile, alpha=True)
    im.pixels = sheet.ravel()
    im.filepath_raw = out
    im.file_format = "PNG"
    im.save()
    print("expression sheet:", out, presets)


main()
