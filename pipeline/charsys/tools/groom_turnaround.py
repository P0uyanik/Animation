"""Turnaround and close-up renders of a built character master for groom evaluation (headless Blender; read-only).

    blender -b --factory-startup -P pipeline/charsys/tools/groom_turnaround.py -- <master.blend> <reference_index.json> <out_dir>
        [--views id,id,...] [--height 640] [--samples 32] [--lighting character_neutral/1|harness] [--exposure E]
        [--closeup "<name>:<yaw>:<elev>:<x>,<y>,<z>:<width_m>"] [--ids]

Cameras: yaw/elevation/focal of each reference view (reference_index.json), framed on the character's bounding box
(compare_harness.place_camera, 90% of the height). Lighting: the shared character-render calibration
(render_calibration.json, lights re-aimed relative to every camera) or, with --lighting harness, the round-1 setup
(compare_harness.studio_lighting, AgX, exposure -1). A close-up camera looks at a world point from yaw/elevation with
an orthographic width. --ids also writes <view>_ids.png: flat material-slot colours (Workbench, no anti-aliasing) and
ids.json (slot -> colour) for colour measurements. Character-agnostic: everything comes from the arguments.
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
sys.path.insert(0, os.path.join(ROOT, "pipeline", "charsys"))
import render_calibration as RC  # noqa: E402

ID_COLOURS = [(230, 25, 75), (60, 180, 75), (255, 225, 25), (0, 130, 200), (245, 130, 48), (145, 30, 180),
              (70, 240, 240), (240, 50, 230), (210, 245, 60), (250, 190, 212), (0, 128, 128), (220, 190, 255),
              (170, 110, 40), (255, 250, 200), (128, 0, 0), (170, 255, 195), (128, 128, 0), (255, 215, 180),
              (0, 0, 128), (128, 128, 128)]


def render_ids(sc, path, materials):
    """Flat material colours (sRGB ids) through Workbench without anti-aliasing; restores the scene afterwards."""
    keep = (sc.render.engine, sc.view_settings.view_transform, sc.view_settings.exposure, sc.view_settings.gamma)
    old = {m.name: tuple(m.diffuse_color) for m in materials}
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.light = "FLAT"
    sc.display.shading.color_type = "MATERIAL"
    sc.display.render_aa = "OFF"
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.exposure, sc.view_settings.gamma = 0.0, 1.0
    for i, m in enumerate(materials):
        m.diffuse_color = (*RC.srgb_to_linear(ID_COLOURS[i % len(ID_COLOURS)]), 1)
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    for m in materials:
        m.diffuse_color = old[m.name]
    sc.render.engine, sc.view_settings.view_transform, sc.view_settings.exposure, sc.view_settings.gamma = keep


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
    ap.add_argument("--lighting", default=RC.DEFAULT,
                    help="a render_calibration.json profile, or 'harness' for compare_harness.studio_lighting (round 1)")
    ap.add_argument("--exposure", type=float, default=None,
                    help="override the view exposure (stops); harness default -1, calibrated profiles use their own")
    ap.add_argument("--ids", action="store_true", help="also write <view>_ids.png material-slot masks")
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    t0 = time.time()
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(a.master))
    sc = bpy.context.scene
    for o in list(sc.objects):
        if o.type in ("LIGHT", "CAMERA"):
            bpy.data.objects.remove(o, do_unlink=True)
    rig = None
    if a.lighting == "harness":
        CH.studio_lighting()
    else:
        rig = RC.apply(sc, RC.load(a.lighting))
    sc.render.engine = "CYCLES"
    sc.cycles.samples = a.samples
    sc.cycles.device = "CPU"
    try:
        sc.cycles.use_denoising = True
        sc.cycles.denoiser = "OPENIMAGEDENOISE"
    except Exception:
        pass
    sc.render.film_transparent = False
    if rig is None:
        names = [v.identifier for v in sc.view_settings.bl_rna.properties["view_transform"].enum_items]
        sc.view_settings.view_transform = "AgX" if "AgX" in names else "Filmic"  # as compare_harness
        sc.view_settings.exposure = -1.0
    if a.exposure is not None:
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
    times = {"open_s": round(time.time() - t0, 2), "views": {}, "lighting": a.lighting,
             "view_transform": sc.view_settings.view_transform, "exposure": sc.view_settings.exposure}
    mats = sorted({m for o in meshes for m in o.data.materials if m}, key=lambda m: m.name)
    if a.ids:
        json.dump({m.name: ID_COLOURS[i % len(ID_COLOURS)] for i, m in enumerate(mats)},
                  open(os.path.join(a.out, "ids.json"), "w"), indent=1)
    sc.render.resolution_x, sc.render.resolution_y = a.height // 2, a.height
    target = (lo + hi) / 2
    for v in views:
        t = time.time()
        cam.data.type = "PERSP"
        d, _ = CH.place_camera(cam, target, v["yaw_deg"], v["elevation_deg"], v["focal_mm_estimate"], lo, hi, 0.5, 0.9)
        if rig:
            RC.orient(rig, d)
        sc.render.filepath = os.path.join(a.out, v["id"] + ".png")
        bpy.ops.render.render(write_still=True)
        times["views"][v["id"]] = round(time.time() - t, 2)
        if a.ids:
            render_ids(sc, os.path.join(a.out, v["id"] + "_ids.png"), mats)
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
        if rig:
            RC.orient(rig, d)
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
