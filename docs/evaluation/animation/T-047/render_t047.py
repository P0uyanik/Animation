"""T-047 evidence renders (not part of the pipeline): stills of one character from a shot.blend written by
pipeline/charsys/shot_render.py --blend-only, from a camera placed in front of the character (or 45 degrees to its
right), the other characters hidden so nothing stands in the way.

    blender -b --factory-startup -P docs/evaluation/animation/T-047/render_t047.py -- \
        --blend shot.blend --character <character_id> --facing <yaw deg in the engine scene> \
        --frames 42[,43...] --view front|q34 --engine cycles|workbench [--samples 32] [--res W H] --out <dir> --tag <name>

Writes <out>/<tag>_f####.png. The camera frames the character's evaluated meshes (bounding box at the first listed
frame), so planned and unplanned renders of the same frame use the same camera when given the same frame list.
"""
import argparse
import math
import os
import sys

import bpy
from mathutils import Vector


def args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blend", required=True)
    ap.add_argument("--character", required=True)
    ap.add_argument("--facing", type=float, required=True)
    ap.add_argument("--frames", required=True)
    ap.add_argument("--view", choices=("front", "q34"), default="front")
    ap.add_argument("--engine", choices=("cycles", "workbench"), default="cycles")
    ap.add_argument("--samples", type=int, default=32)
    ap.add_argument("--res", type=int, nargs=2, default=(640, 800))
    ap.add_argument("--out", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--camera-from", default="", help="reuse the camera box of this frame (default: first frame)")
    ap.add_argument("--hide", default="", help="comma-separated scene objects to hide (e.g. a table in front)")
    return ap.parse_args(sys.argv[sys.argv.index("--") + 1:])


def main():
    a = args()
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(a.blend))
    scene = bpy.context.scene
    frames = [int(f) for f in a.frames.split(",")]
    # the shot's own (library-override) character collections, not the linked library ones
    roots = {c.name: c for c in bpy.data.collections if c.get("ps_character_id") and c.library is None}
    root = roots.get(a.character)
    if root is None:
        raise SystemExit(f"collection {a.character} not found: {sorted(roots)}")
    # Other characters are excluded from the view layer (a library override ignores object hide flags); lights,
    # camera and props stay.
    def layer_of(lc, coll):
        if lc.collection == coll:
            return lc
        for ch in lc.children:
            found = layer_of(ch, coll)
            if found:
                return found
        return None
    for name, other in roots.items():
        if name != a.character:
            lc = layer_of(bpy.context.view_layer.layer_collection, other)
            if lc is None:
                raise SystemExit(f"{name}: not in the view layer")
            lc.exclude = True
    for name in filter(None, a.hide.split(",")):  # set objects in the way, by name (reported with the renders)
        if name in scene.objects:
            scene.objects[name].hide_render = True
    scene.frame_set(int(a.camera_from) if a.camera_from else frames[0])
    dg = bpy.context.evaluated_depsgraph_get()
    lo, hi = Vector((1e9, 1e9, 1e9)), Vector((-1e9, -1e9, -1e9))
    for o in root.all_objects:
        if o is None or o.type != "MESH" or o.hide_render:
            continue
        e = o.evaluated_get(dg)
        for c in e.bound_box:
            w = e.matrix_world @ Vector(c)
            lo = Vector(map(min, lo, w))
            hi = Vector(map(max, hi, w))
    centre = (lo + hi) / 2
    height = hi.z - lo.z
    # engine forward (sin yaw, 0, cos yaw) -> Blender (x, -z, y)
    yaw = math.radians(a.facing + (45.0 if a.view == "q34" else 0.0))
    fwd = Vector((math.sin(yaw), -math.cos(yaw), 0.0))
    cam_data = bpy.data.cameras.new("t047_cam")
    cam_data.lens = 50
    cam = bpy.data.objects.new("t047_cam", cam_data)
    scene.collection.objects.link(cam)
    sensor_h = cam_data.sensor_width * a.res[1] / a.res[0]
    dist = 1.25 * height * cam_data.lens / sensor_h
    cam.location = centre + fwd * dist + Vector((0, 0, 0.05 * height))
    look = centre - cam.location
    cam.rotation_euler = look.to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam
    r = scene.render
    r.resolution_x, r.resolution_y, r.resolution_percentage = a.res[0], a.res[1], 100
    r.film_transparent = False
    if a.engine == "cycles":
        r.engine = "CYCLES"
        scene.cycles.samples = a.samples
        scene.cycles.device = "CPU"
        try:
            scene.cycles.use_denoising = True
            scene.cycles.denoiser = "OPENIMAGEDENOISE"
        except Exception:  # noqa: BLE001
            scene.cycles.use_denoising = False
    else:
        r.engine = "BLENDER_WORKBENCH"
        scene.display.shading.light = "STUDIO"
        scene.display.shading.color_type = "MATERIAL"
    r.image_settings.file_format = "PNG"
    os.makedirs(a.out, exist_ok=True)
    for f in frames:
        scene.frame_set(f)
        r.filepath = os.path.join(os.path.abspath(a.out), f"{a.tag}_f{f:04d}.png")
        bpy.ops.render.render(write_still=True)
        print(f"[render_t047] {r.filepath}")


main()
