"""Render the T-015 sphere/patch swatch sheet in Cycles.

blender -b --factory-startup -P pipeline/charsys/materials/render_swatches.py -- \
  --out docs/evaluation/materials/T-015/swatch_sheet.png \
  --metadata docs/evaluation/materials/T-015/swatches.json
"""
import argparse
import json
import math
import os
import sys
import time

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector


HERE = os.path.dirname(os.path.abspath(__file__))
CHARSYS = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(CHARSYS, "..", ".."))
sys.path.insert(0, CHARSYS)
sys.path.insert(0, os.path.join(ROOT, "pipeline", "blender"))

from materials import builder as MATERIALS  # noqa: E402
import compare_harness as HARNESS  # noqa: E402
import geom as G  # noqa: E402


def parse():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--metadata", required=True)
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=960)
    parser.add_argument("--samples", type=int, default=64)
    parser.add_argument("--exposure", type=float, default=0.0)
    parser.add_argument("--view-transform", default="AgX")
    parser.add_argument("--save-blend", default="")
    return parser.parse_args(argv)


def look_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def label(text, location, material):
    curve = bpy.data.curves.new("label", "FONT")
    curve.body = text
    curve.align_x = "CENTER"
    curve.align_y = "CENTER"
    curve.size = 0.047
    curve.extrude = 0.0002
    obj = bpy.data.objects.new("label_" + text.replace("/", "_"), curve)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler.x = math.radians(90)
    obj.data.materials.append(material)
    return obj


def patch(name, location, material):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = "patch_" + name.replace("/", "_").replace(" ", "_")
    obj.scale = (0.235, 0.025, 0.125)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bevel = obj.modifiers.new("Soft fabric edge", "BEVEL")
    bevel.width = 0.018
    bevel.segments = 5
    G.assign(obj, material)
    return obj


def roi(scene, camera, obj, width, height):
    points = [world_to_camera_view(scene, camera, obj.matrix_world @ Vector(corner)) for corner in obj.bound_box]
    x0, x1 = min(p.x for p in points) * width, max(p.x for p in points) * width
    y0, y1 = (1 - max(p.y for p in points)) * height, (1 - min(p.y for p in points)) * height
    dx, dy = (x1 - x0) * 0.25, (y1 - y0) * 0.25
    return [round(x0 + dx), round(y0 + dy), round(x1 - dx), round(y1 - dy)]


def main():
    args = parse()
    started = time.time()
    out = os.path.abspath(args.out)
    metadata_path = os.path.abspath(args.metadata)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    os.makedirs(os.path.dirname(metadata_path), exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    HARNESS.studio_lighting()

    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = args.samples
    scene.cycles.use_denoising = True
    scene.render.resolution_x = args.width
    scene.render.resolution_y = args.height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.film_transparent = False
    requested_transform = args.view_transform
    try:
        scene.view_settings.view_transform = requested_transform
    except TypeError:
        requested_transform = scene.view_settings.view_transform
    scene.view_settings.exposure = args.exposure

    camera_data = bpy.data.cameras.new("SwatchCamera")
    camera = bpy.data.objects.new("SwatchCamera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.location = (0.0, -6.0, 0.5)
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 2.8
    look_at(camera, (0.0, 0.0, 0.5))

    text_material = G.material("M_swatch_labels", (32, 29, 28), roughness=0.9)
    library = MATERIALS.load_library()
    entries = []
    for index, name in enumerate(library["presets"]):
        row, column = divmod(index, 2)
        x = -0.55 if column == 0 else 0.55
        z = 1.62 - row * 0.56
        preset = library["presets"][name]
        material = MATERIALS.build_material("M_swatch_" + name, name, preset["swatch_srgb"],
                                            library["reference_size_m"])
        bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=0.125,
                                             location=(x - 0.235, 0.0, z))
        sphere = bpy.context.object
        sphere.name = "sphere_" + name.replace("/", "_").replace(" ", "_")
        bpy.ops.object.shade_smooth()
        G.assign(sphere, material)
        fabric = patch(name, (x + 0.145, 0.0, z), material)
        label(name, (x, -0.17, z - 0.19), text_material)
        entries.append({"preset": name, "base_color_srgb": preset["swatch_srgb"], "patch": fabric})

    bpy.context.view_layer.update()
    metadata = {
        "schema": "plush-studio.material-swatches/1",
        "blender": bpy.app.version_string,
        "image": os.path.relpath(out, ROOT).replace("\\", "/"),
        "width": args.width,
        "height": args.height,
        "samples": args.samples,
        "exposure": args.exposure,
        "view_transform": requested_transform,
        "render_engine": "CYCLES",
        "studio_light": "pipeline/blender/compare_harness.py:studio_lighting",
        "reference_size_m": library["reference_size_m"],
        "swatches": [],
    }
    for entry in entries:
        metadata["swatches"].append({
            "preset": entry["preset"],
            "base_color_srgb": entry["base_color_srgb"],
            "patch_roi_px": roi(scene, camera, entry["patch"], args.width, args.height),
        })

    scene.render.filepath = out
    render_started = time.time()
    bpy.ops.render.render(write_still=True)
    metadata["render_s"] = round(time.time() - render_started, 2)
    metadata["total_s"] = round(time.time() - started, 2)
    with open(metadata_path, "w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2)
        handle.write("\n")
    if args.save_blend:
        blend_path = os.path.abspath(args.save_blend)
        os.makedirs(os.path.dirname(blend_path), exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print(f"[render_swatches] {out} ({args.width}x{args.height}, {len(entries)} presets)")


if __name__ == "__main__":
    main()
