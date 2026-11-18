"""T-081 owner-sheet views of a built girl master (headless Blender; read-only on the input).

    blender -b --factory-startup -P docs/evaluation/characters/T-081/tools/render_views.py -- <master.blend> <out_dir>
        [--views "body@0,body@35,body@90,body@180,face@0"] [--engine CYCLES|WORKBENCH] [--px 400] [--spp 16]
        [--set "face_MouthSmile=0.3"] [--tag name]

A view is <framing>@<yaw deg> (yaw 0 = front, + = camera towards the character's left). Framing "body" = whole
character (orthographic, 1.15 x height), "head" = head and hair (0.5 m), "face" = face close-up framed on the
LM_eye_*/LM_chin landmarks (0.34 m, as T-065's render_face.py). Shared calibration character_neutral/1, Cycles CPU
+ OIDN. Writes <out_dir>/<tag><framing>_<yaw>.png."""
import math
import os
import sys

import bpy
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "pipeline", "charsys"))
import render_calibration as RC  # noqa: E402
import render_engine  # noqa: E402


def arg(argv, name, default):
    return argv[argv.index(name) + 1] if name in argv else default


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    src, out = os.path.abspath(argv[0]), os.path.abspath(argv[1])
    os.makedirs(out, exist_ok=True)
    views = arg(argv, "--views", "body@0,body@35,body@90,body@180,face@0").split(",")
    engine, px, spp = arg(argv, "--engine", "CYCLES"), int(arg(argv, "--px", 400)), int(arg(argv, "--spp", 16))
    tag = arg(argv, "--tag", "")
    extra = [kv.split("=") for kv in arg(argv, "--set", "").split(";") if "=" in kv]
    bpy.ops.wm.open_mainfile(filepath=src)
    sc = bpy.context.scene
    for o in list(sc.objects):
        if o.type in ("LIGHT", "CAMERA"):
            bpy.data.objects.remove(o, do_unlink=True)
    lrig = RC.apply(sc, RC.load(RC.DEFAULT))
    if engine == "WORKBENCH":
        sc.render.engine = "BLENDER_WORKBENCH"
        sc.display.shading.light = "STUDIO"
        sc.display.shading.color_type = "MATERIAL"
        sc.display.shading.show_cavity = True
    else:
        render_engine.configure(sc, "cycles", spp, cycles_device="CPU", cycles_denoiser="OPENIMAGEDENOISE")
    rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    for k, v in extra:
        rig[k] = float(v)
    rig.update_tag()
    sc.frame_set(sc.frame_current)
    lm = {o.name[3:]: o.matrix_world.translation.copy() for o in bpy.data.objects if o.name.startswith("LM_")}
    zs = [(o.matrix_world @ Vector(c)).z for o in sc.objects if o.type == "MESH" and not o.hide_render
          for c in o.bound_box]
    top, bottom = max(zs), min(zs)
    cam = bpy.data.objects.new("T081Cam", bpy.data.cameras.new("T081Cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.data.type = "ORTHO"
    for view in views:
        framing, yaw = view.split("@")
        if framing == "body":
            centre, width, tall = Vector((0, 0, (top + bottom) / 2)), (top - bottom) * 1.06, 1.0
        elif framing == "head":
            centre, width, tall = Vector((0, 0, lm["eye_L"].z + 0.03)), 0.5, 1.0
        else:
            centre = (lm["eye_L"] + lm["eye_R"]) / 2 * 0.62 + lm["chin"] * 0.38
            centre.y = 0
            width, tall = 0.34, 1.0
        cam.data.ortho_scale = width
        sc.render.resolution_x, sc.render.resolution_y = px, int(px * tall)
        sc.render.resolution_percentage = 100
        a, el = math.radians(float(yaw)), math.radians(2.0)
        d = Vector((math.sin(a) * math.cos(el), -math.cos(a) * math.cos(el), math.sin(el))).normalized()
        cam.location = centre + d * 3.0
        cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        RC.orient(lrig, d)
        sc.render.filepath = os.path.join(out, f"{tag}{framing}_{yaw}.png")
        bpy.ops.render.render(write_still=True)
        print("rendered", sc.render.filepath)


main()
