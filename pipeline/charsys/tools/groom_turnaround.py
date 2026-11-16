"""Turnaround and close-up renders of a built character master for groom evaluation (headless Blender; read-only).

    blender -b --factory-startup -P pipeline/charsys/tools/groom_turnaround.py -- <master.blend> <reference_index.json> <out_dir>
        [--views id,id,...] [--height 640] [--samples 32] [--exposure -1.0] [--closeup "<name>:<yaw>:<elev>:<x>,<y>,<z>:<width_m>"]

Cameras: yaw/elevation/focal of each reference view (reference_index.json), framed on the character's bounding box
(compare_harness.place_camera, 90% of the height), under compare_harness.studio_lighting. A close-up camera looks at a
world point from yaw/elevation with an orthographic width. Character-agnostic: everything comes from the arguments.
Writes <view>.png per view and timings.json."""
import argparse
import json
import math
import os
import sys
import time

import bpy
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "pipeline", "blender"))
import compare_harness as CH  # noqa: E402


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("master")
    ap.add_argument("index")
    ap.add_argument("out")
    ap.add_argument("--views", default="")
    ap.add_argument("--height", type=int, default=640)
    ap.add_argument("--samples", type=int, default=32)
    ap.add_argument("--closeup", action="append", default=[])
    ap.add_argument("--exposure", type=float, default=-1.0,
                    help="view exposure (stops); the harness lights are set for silhouettes and overexpose albedo by ~1 stop")
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    t0 = time.time()
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(a.master))
    sc = bpy.context.scene
    for o in list(sc.objects):
        if o.type in ("LIGHT", "CAMERA"):
            bpy.data.objects.remove(o, do_unlink=True)
    CH.studio_lighting()
    sc.render.engine = "CYCLES"
    sc.cycles.samples = a.samples
    sc.cycles.device = "CPU"
    try:
        sc.cycles.use_denoising = True
        sc.cycles.denoiser = "OPENIMAGEDENOISE"
    except Exception:
        pass
    sc.render.film_transparent = False
    names = [v.identifier for v in sc.view_settings.bl_rna.properties["view_transform"].enum_items]
    sc.view_settings.view_transform = "AgX" if "AgX" in names else "Filmic"  # as compare_harness
    sc.view_settings.exposure = a.exposure
    root = next((c for c in bpy.data.collections if "ps_character_id" in c.keys()), None)
    pool = root.all_objects if root else sc.objects
    meshes = [o for o in pool if o.type == "MESH" and not o.hide_render and not o.name.startswith("WGT")]
    deps = bpy.context.evaluated_depsgraph_get()
    lo, hi = Vector((1e9,) * 3), Vector((-1e9,) * 3)
    for o in meshes:
        ev = o.evaluated_get(deps)
        for c in ev.bound_box:
            w = ev.matrix_world @ Vector(c)
            lo = Vector(map(min, lo, w))
            hi = Vector(map(max, hi, w))
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    idx = json.load(open(a.index))
    want = [v for v in a.views.split(",") if v]
    views = [v for v in idx["views"] if not want or v["id"] in want]
    times = {"open_s": round(time.time() - t0, 2), "views": {}}
    sc.render.resolution_x, sc.render.resolution_y = a.height // 2, a.height
    target = (lo + hi) / 2
    for v in views:
        t = time.time()
        cam.data.type = "PERSP"
        CH.place_camera(cam, target, v["yaw_deg"], v["elevation_deg"], v["focal_mm_estimate"], lo, hi, 0.5, 0.9)
        sc.render.filepath = os.path.join(a.out, v["id"] + ".png")
        bpy.ops.render.render(write_still=True)
        times["views"][v["id"]] = round(time.time() - t, 2)
    for spec in a.closeup:
        name, yaw, elev, xyz, width = spec.split(":")
        p = Vector(tuple(float(c) for c in xyz.split(",")))
        yaw, elev = float(yaw), float(elev)
        d = Vector((math.sin(math.radians(yaw)) * math.cos(math.radians(elev)),
                    -math.cos(math.radians(yaw)) * math.cos(math.radians(elev)), math.sin(math.radians(elev))))
        cam.data.type = "ORTHO"
        cam.data.ortho_scale = float(width)
        cam.location = p + d * 1.5
        cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        sc.render.resolution_x = sc.render.resolution_y = a.height
        t = time.time()
        sc.render.filepath = os.path.join(a.out, name + ".png")
        bpy.ops.render.render(write_still=True)
        times["views"][name] = round(time.time() - t, 2)
        sc.render.resolution_x, sc.render.resolution_y = a.height // 2, a.height
    times["samples"] = a.samples
    times["total_s"] = round(time.time() - t0, 2)
    json.dump(times, open(os.path.join(a.out, "timings.json"), "w"), indent=1)
    print(json.dumps(times))


main()
