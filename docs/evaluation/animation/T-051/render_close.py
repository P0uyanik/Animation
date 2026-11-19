"""T-051 evidence: renders chosen frames of a shot.blend (run_shot --blend-only) through extra close-up cameras (not
part of the pipeline). Same as docs/evaluation/animation/T-082/render_frames.py, but the camera keeps world up (+Z in
Blender) (an explicit level look-at) so a side view is not rolled, and several cameras render in one Blender run:

    blender -b --factory-startup -P docs/evaluation/animation/T-051/render_close.py -- --blend shot.blend --frames 48 \
        --out <dir> --tag <name> [--samples 8] [--res W H] --view <name> <cx cy cz> <tx ty tz> <lens> [--view ...]
    (engine coordinates: +Y up)
"""
import argparse
import os
import sys

import bpy  # type: ignore
from mathutils import Matrix, Vector  # type: ignore


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blend", required=True)
    ap.add_argument("--frames", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--samples", type=int, default=8)
    ap.add_argument("--res", type=int, nargs=2, default=(240, 180))
    ap.add_argument("--view", nargs=8, action="append", required=True, metavar=("NAME", "CX", "CY", "CZ", "TX", "TY", "TZ", "LENS"))
    a = ap.parse_args(sys.argv[sys.argv.index("--") + 1:])
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(a.blend))
    scene = bpy.context.scene
    r = scene.render
    r.resolution_x, r.resolution_y, r.resolution_percentage = a.res[0], a.res[1], 100
    r.engine = "CYCLES"
    scene.cycles.samples = a.samples
    scene.cycles.device = "CPU"
    r.image_settings.file_format = "PNG"
    os.makedirs(a.out, exist_ok=True)
    b = lambda v: Vector((v[0], -v[2], v[1]))  # noqa: E731  engine (x, y up, z) -> Blender (x, -z, y)
    for name, cx, cy, cz, tx, ty, tz, lens in a.view:
        cd = bpy.data.cameras.new("t051_" + name)
        cd.lens = float(lens)
        cd.clip_start = 0.01
        cam = bpy.data.objects.new("t051_" + name, cd)
        scene.collection.objects.link(cam)
        cam.location = b((float(cx), float(cy), float(cz)))
        target = b((float(tx), float(ty), float(tz)))
        fwd = (target - cam.location).normalized()  # level look-at: camera -Z forward, +Y up, +X right
        right = fwd.cross(Vector((0.0, 0.0, 1.0))).normalized()
        up = right.cross(fwd)
        cam.rotation_euler = Matrix((right, up, -fwd)).transposed().to_euler()
        scene.camera = cam
        for f in (int(x) for x in a.frames.split(",")):
            scene.frame_set(f)
            r.filepath = os.path.join(os.path.abspath(a.out), f"{a.tag}_{name}_f{f:04d}.png")
            bpy.ops.render.render(write_still=True)
            print("[render_close]", r.filepath)


main()
