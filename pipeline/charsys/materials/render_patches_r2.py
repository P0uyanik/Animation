"""T-092 material patches: per material a macro patch and a shot-size patch, before and after, under fixed lights.

    blender -b --factory-startup -P pipeline/charsys/materials/render_patches_r2.py -- \
        --plan docs/evaluation/materials/T-092/patches.plan.json --out <dir> [--samples 16] [--only label,...]

Every tile is the same stand-in form (a sphere of radius ``form_radius_m``) with the slot's material assignment and
its generated surface fibres (the shared group, ``close`` LOD), rendered in Cycles with OIDN on the CPU:

- shot-size: the strict-sheet body-row camera (70 mm, 36 mm vertical sensor, frame height 1.26 m: camera distance
  2.45 m, ~457 px per metre at 576 px height); the tile keeps that distance and pixel density and narrows the field
  (a longer lens) to a 0.35 m crop around the form, so the material reads at exactly the size it has on the sheet;
- macro: a 0.06 m field on the lit upper-left of the form and its silhouette (surface relief and fibre halo).

Lights: the plan's rigs, each loaded from pipeline/charsys/render_calibration.json (read-only) or this task's
pipeline/charsys/materials/r2_lights.json, aimed camera-relative as in every review render. Writes
<out>/tiles/<label>/<variant>_<rig>_<scale>.png and <out>/patches_render.json (the seconds of every tile).
"""
import argparse
import json
import math
import os
import sys
import time

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
CHARSYS = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(CHARSYS, "..", ".."))
sys.path.insert(0, CHARSYS)

from materials import builder as MATERIALS  # noqa: E402
import render_calibration as RC  # noqa: E402
import render_engine  # noqa: E402

LIGHT_FILES = {"render_calibration.json": RC.PATH, "r2_lights.json": os.path.join(HERE, "r2_lights.json")}
SHEET_LENS_MM, SHEET_SENSOR_MM, SHEET_FRAME_M, SHEET_HEIGHT_PX = 70.0, 36.0, 1.26, 576


def parse():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--plan", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--samples", type=int, default=16)
    p.add_argument("--only", default="", help="comma-separated material labels")
    p.add_argument("--preview", action="store_true", help="2 samples, shot-size only, neutral only (a cheap check)")
    return p.parse_args(argv)


def camera_for(scale, form_r, centre):
    fov = 2 * math.atan(SHEET_SENSOR_MM / 2 / SHEET_LENS_MM)
    distance = SHEET_FRAME_M / 2 / math.tan(fov / 2)
    if scale == "shot":
        frame = 0.35
        px = int(round(frame / SHEET_FRAME_M * SHEET_HEIGHT_PX))
        lens = SHEET_LENS_MM * SHEET_FRAME_M / frame
        target = Vector(centre)
    else:
        frame, px = 0.06, 360
        distance = 0.25
        lens = SHEET_SENSOR_MM / 2 / (frame / 2 / distance)
        target = Vector(centre) + Vector((-0.62, 0.0, 0.62)) * form_r  # lit upper-left, across the silhouette
    return {"frame_m": frame, "px": px, "lens_mm": round(lens, 3), "distance_m": round(distance, 4),
            "target": [round(v, 4) for v in target], "px_per_m": round(px / frame, 2)}


def clear_lights(scene):
    for ob in list(scene.objects):
        if ob.type == "LIGHT":
            bpy.data.objects.remove(ob, do_unlink=True)


def main():
    args = parse()
    plan = json.load(open(args.plan, encoding="utf-8"))
    out = os.path.abspath(args.out)
    os.makedirs(out, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    samples = 2 if args.preview else args.samples
    engine = render_engine.configure(scene, "cycles", samples, cycles_device="CPU", cycles_denoiser="OPENIMAGEDENOISE")
    scene.cycles.seed = 0
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.resolution_percentage = 100
    form_r = float(plan.get("form_radius_m", 0.06))
    centre = (0.0, 0.0, 0.0)
    only = {s.strip() for s in args.only.split(",") if s.strip()}
    materials = [m for m in plan["materials"] if not only or m["label"] in only]

    entries = []
    for m in materials:
        for variant in ("before", "after"):
            asg = m[variant]
            bpy.ops.mesh.primitive_uv_sphere_add(segments=96, ring_count=48, radius=form_r, location=centre)
            ob = bpy.context.object
            ob.name = f"form_{m['label']}_{variant}"
            bpy.ops.object.shade_smooth()
            mat = MATERIALS.build_from_assignment(f"M_{m['label']}_{variant}", asg)
            ob.data.materials.append(mat)
            fb = MATERIALS.add_fibres_from_assignment(ob, asg, lod="close")
            objs = [ob] + ([fb] if fb is not None else [])
            for o in objs:
                o.hide_render = True
            entries.append({"label": m["label"], "variant": variant, "objects": objs, "preset": asg["preset"],
                            "family": MATERIALS.preset_family(asg["preset"]), "fibres": fb is not None})

    cam = bpy.data.objects.new("PatchCam", bpy.data.cameras.new("PatchCam"))
    scene.collection.objects.link(cam)
    scene.camera = cam
    cam.data.sensor_fit = "VERTICAL"
    cam.data.sensor_height = SHEET_SENSOR_MM
    cam.data.clip_start = 0.005
    rigs = plan["lights"][:1] if args.preview else plan["lights"]
    scales = ("shot",) if args.preview else ("macro", "shot")
    result = {"schema": "plush-studio.material-patches/1", "task": "T-092", "blender": bpy.app.version_string,
              "engine": engine, "samples": samples, "denoiser": "OPENIMAGEDENOISE", "device": "CPU",
              "threads": scene.render.threads, "form_radius_m": form_r, "cameras": {}, "tiles": []}
    elevation = math.radians(float(plan.get("elevation_deg", 6.0)))
    d = Vector((0.0, -math.cos(elevation), math.sin(elevation)))
    for rig_ref in rigs:
        clear_lights(scene)
        prof = RC.load(rig_ref["name"], LIGHT_FILES[rig_ref["file"]])
        rig = RC.apply(scene, prof)
        RC.orient(rig, d)
        for scale in scales:
            c = camera_for(scale, form_r, centre)
            result["cameras"][scale] = c
            cam.data.lens = c["lens_mm"]
            cam.location = Vector(c["target"]) + d * c["distance_m"]
            cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
            scene.render.resolution_x = scene.render.resolution_y = c["px"]
            for e in entries:
                for o in e["objects"]:
                    o.hide_render = False
                path = os.path.join(out, "tiles", e["label"], f"{e['variant']}_{rig_ref['tag']}_{scale}.png")
                os.makedirs(os.path.dirname(path), exist_ok=True)
                scene.render.filepath = path
                t0 = time.time()
                bpy.ops.render.render(write_still=True)
                seconds = round(time.time() - t0, 2)
                for o in e["objects"]:
                    o.hide_render = True
                result["tiles"].append({"label": e["label"], "variant": e["variant"], "preset": e["preset"],
                                        "family": e["family"], "fibres": e["fibres"], "light": rig_ref["name"],
                                        "light_tag": rig_ref["tag"], "scale": scale,
                                        "file": os.path.relpath(path, out).replace("\\", "/"), "seconds": seconds})
                print(f"[render_patches_r2] {e['label']} {e['variant']} {rig_ref['tag']} {scale} {seconds}s",
                      flush=True)
    with open(os.path.join(out, "patches_render.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(result, fh, indent=1)
        fh.write("\n")


if __name__ == "__main__":
    main()
