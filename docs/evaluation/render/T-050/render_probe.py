"""T-050 render-cost probe (scratch tool; read-only on the master, never saves a .blend).

    blender -b --factory-startup -P docs/evaluation/render/T-050/render_probe.py -- <master.blend> <out.json>
        [--png out.png] [--res W H] [--engine cycles|eevee] [--samples N] [--adaptive T] [--no-denoise]
        [--cast 1|2] [--frames N] [--persistent] [--yaw 35]

Opens a published character master, lights it with the shared render calibration (character_neutral/1), frames a
16:9 camera on it (optionally adds a second instance of the character for a two-shot proxy) and renders the same
still `--frames` times, recording wall time per render (first render includes BVH build / kernel or shader warm-up;
later ones show the steady per-frame cost, with or without Cycles persistent data)."""
import argparse
import json
import os
import sys
import time

import bpy
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "pipeline", "blender"))
import compare_harness as CH  # noqa: E402
sys.path.insert(0, os.path.join(ROOT, "pipeline", "charsys"))
import render_calibration as RC  # noqa: E402
import render_engine  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("master")
    ap.add_argument("out")
    ap.add_argument("--png")
    ap.add_argument("--res", type=int, nargs=2, default=[640, 360])
    ap.add_argument("--engine", choices=("cycles", "eevee"), default="cycles")
    ap.add_argument("--samples", type=int, default=16)
    ap.add_argument("--adaptive", type=float, default=None, help="Cycles adaptive threshold; 0 disables adaptive")
    ap.add_argument("--no-denoise", action="store_true")
    ap.add_argument("--cast", type=int, default=1)
    ap.add_argument("--frames", type=int, default=1)
    ap.add_argument("--persistent", action="store_true")
    ap.add_argument("--yaw", type=float, default=35.0)
    a = ap.parse_args(sys.argv[sys.argv.index("--") + 1:])
    t0 = time.time()
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(a.master))
    sc = bpy.context.scene
    for o in list(sc.objects):
        if o.type in ("LIGHT", "CAMERA"):
            bpy.data.objects.remove(o, do_unlink=True)
    rig = RC.apply(sc, RC.load(RC.DEFAULT))
    settings = render_engine.configure(sc, a.engine, a.samples, cycles_device="CPU", cycles_denoiser="OPENIMAGEDENOISE")
    if a.engine == "cycles":
        if a.adaptive is not None:
            sc.cycles.use_adaptive_sampling = a.adaptive > 0
            if a.adaptive > 0:
                sc.cycles.adaptive_threshold = a.adaptive
        sc.cycles.use_denoising = not a.no_denoise
        sc.render.use_persistent_data = a.persistent
        settings.update(adaptive=sc.cycles.use_adaptive_sampling, adaptive_threshold=sc.cycles.adaptive_threshold,
                        denoising=sc.cycles.use_denoising, persistent_data=a.persistent,
                        max_bounces=sc.cycles.max_bounces, threads=sc.render.threads)
    root = next((c for c in bpy.data.collections if "ps_character_id" in c.keys()), None)
    pool = root.all_objects if root else sc.objects
    meshes = [o for o in pool if o.type == "MESH" and not o.hide_render and not o.name.startswith("WGT")]
    deps = bpy.context.evaluated_depsgraph_get()
    lo, hi = Vector((1e9,) * 3), Vector((-1e9,) * 3)
    for o in meshes:
        ev = o.evaluated_get(deps)
        for c in ev.bound_box:
            w = ev.matrix_world @ Vector(c)
            lo, hi = Vector(map(min, lo, w)), Vector(map(max, hi, w))
    if a.cast == 2 and root is not None:  # two-shot proxy: a second instance of the same character beside the first
        dx = (hi.x - lo.x) * 1.25
        inst = bpy.data.objects.new("T050_second", None)
        inst.instance_type, inst.instance_collection = "COLLECTION", root
        inst.location = (dx, 0, 0)
        inst.rotation_euler = (0, 0, 0.5)
        sc.collection.objects.link(inst)
        hi = Vector((hi.x + dx, hi.y, hi.z))
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    w, h = a.res
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = w, h, 100
    sc.render.film_transparent = False
    d, _ = CH.place_camera(cam, (lo + hi) / 2, a.yaw, 6, 50, lo, hi, w / h, 0.8)
    RC.orient(rig, d)
    rep = {"master": os.path.relpath(a.master, ROOT), "blender": bpy.app.version_string, "cpu_threads": os.cpu_count(),
           "resolution": [w, h], "cast": a.cast, "engine_settings": settings, "open_s": round(time.time() - t0, 2),
           "renders_s": []}
    for i in range(a.frames):
        sc.frame_set(sc.frame_current)  # same still each time; persistent data may reuse the BVH
        t = time.time()
        if a.png and i == a.frames - 1:
            sc.render.filepath = os.path.abspath(a.png)
            bpy.ops.render.render(write_still=True)
        else:
            bpy.ops.render.render()
        rep["renders_s"].append(round(time.time() - t, 2))
    rep["total_s"] = round(time.time() - t0, 2)
    json.dump(rep, open(a.out, "w"), indent=1)
    print("T050", json.dumps(rep))


main()
