"""T-095 evidence (copy of T-082 render_frames.py): renders chosen frames of a shot.blend (pipeline/charsys/shot_render.py --blend-only) with the
shot's own camera (not part of the pipeline):

    blender -b --factory-startup -P docs/evaluation/animation/T-095/render_frames.py -- \
        --blend shot.blend --frames 17,42,56 --out <dir> --tag <name> [--engine cycles|workbench] [--samples 16] [--res W H]
        [--camera x y z --target x y z [--lens mm]]   (engine coordinates: +Y up; default: the shot's own camera)
"""
import argparse
import os
import sys

import bpy  # type: ignore


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blend", required=True)
    ap.add_argument("--frames", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--engine", choices=("cycles", "workbench"), default="cycles")
    ap.add_argument("--samples", type=int, default=16)
    ap.add_argument("--res", type=int, nargs=2, default=(640, 360))
    ap.add_argument("--camera", type=float, nargs=3)
    ap.add_argument("--target", type=float, nargs=3)
    ap.add_argument("--lens", type=float, default=35.0)
    a = ap.parse_args(sys.argv[sys.argv.index("--") + 1:])
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(a.blend))
    scene = bpy.context.scene
    if a.camera and a.target:
        from mathutils import Vector  # type: ignore
        b = lambda v: Vector((v[0], -v[2], v[1]))  # noqa: E731  engine (x, y up, z) -> Blender (x, -z, y)
        cd = bpy.data.cameras.new("t082_cam")
        cd.lens = a.lens
        cam = bpy.data.objects.new("t082_cam", cd)
        scene.collection.objects.link(cam)
        cam.location = b(a.camera)
        cam.rotation_euler = (b(a.target) - cam.location).to_track_quat("-Z", "Y").to_euler()
        scene.camera = cam
    r = scene.render
    r.resolution_x, r.resolution_y, r.resolution_percentage = a.res[0], a.res[1], 100
    if a.engine == "cycles":
        r.engine = "CYCLES"
        scene.cycles.samples = a.samples
        scene.cycles.device = "CPU"
    else:
        r.engine = "BLENDER_WORKBENCH"
        scene.display.shading.color_type = "MATERIAL"
    r.image_settings.file_format = "PNG"
    os.makedirs(a.out, exist_ok=True)
    for f in (int(x) for x in a.frames.split(",")):
        scene.frame_set(f)
        r.filepath = os.path.join(os.path.abspath(a.out), f"{a.tag}_f{f:04d}.png")
        bpy.ops.render.render(write_still=True)
        print("[render_frames]", r.filepath)


main()
