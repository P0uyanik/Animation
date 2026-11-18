"""Render the T-015 sphere/patch swatch sheet in Cycles or EEVEE.

blender -b --factory-startup -P pipeline/charsys/materials/render_swatches.py -- \
  --out docs/evaluation/materials/T-015/swatch_sheet.png \
  --metadata docs/evaluation/materials/T-015/swatches.json
"""
import argparse
import binascii
import json
import math
import os
import struct
import sys
import time
import zlib

import bpy
import numpy as np
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
import render_calibration as RC  # noqa: E402
import render_engine  # noqa: E402


def parse():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--metadata", required=True)
    parser.add_argument("--width", type=int, default=480)
    parser.add_argument("--height", type=int, default=576,
                        help="height of each render; the evidence sheet stacks all ten renders")
    parser.add_argument("--samples", type=int, default=16)
    parser.add_argument("--engine", choices=("cycles", "eevee"), default="cycles")
    parser.add_argument("--exposure", type=float, default=0.0)
    parser.add_argument("--view-transform", default="AgX")
    parser.add_argument("--save-blend", default="")
    parser.add_argument("--lighting", default="harness",
                        help="'harness' (compare_harness.studio_lighting + AgX, the T-015 setup) or a render_calibration profile")
    parser.add_argument("--fibres-lod", choices=("close", "wide", "off"), default="close")
    parser.add_argument("--presets", default="", help="optional comma-separated subset for calibration probes")
    parser.add_argument("--denoiser", choices=("oidn", "off"), default="oidn",
                        help="'off' renders without a denoiser (use enough --samples to keep Monte Carlo noise "
                             "below the fuzz floor)")
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


def fibre_patch_surface(name, location):
    """Front-face-only source for flat-patch fibre measurement."""
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=2, y_subdivisions=2, size=2.0,
                                    location=(location[0], -0.026, location[2]),
                                    rotation=(math.pi / 2.0, 0.0, 0.0))
    obj = bpy.context.object
    obj.name = "fibre_source_" + name.replace("/", "_").replace(" ", "_")
    obj.scale = (0.217, 0.107, 1.0)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.hide_render = True
    return obj


def roi(scene, camera, obj, width, height, fraction=0.5, offset=(0.0, 0.0)):
    points = [world_to_camera_view(scene, camera, obj.matrix_world @ Vector(corner)) for corner in obj.bound_box]
    x0, x1 = min(p.x for p in points) * width, max(p.x for p in points) * width
    y0, y1 = (1 - max(p.y for p in points)) * height, (1 - min(p.y for p in points)) * height
    # Measure a square, flat central crop.  At the 480 px evidence width this
    # is about 100 px square and the 0.256 m reference spans about 205 px, so
    # the VISUAL_TARGET fibre checks remain above their H >= 180 px validity
    # floor.  The old two-column layout only provided 60 x 32 px crops.
    side = min(x1 - x0, y1 - y0) * fraction
    cx = (x0 + x1) * 0.5 + (x1 - x0) * offset[0]
    cy = (y0 + y1) * 0.5 + (y1 - y0) * offset[1]
    return [round(cx - side * 0.5), round(cy - side * 0.5),
            round(cx + side * 0.5), round(cy + side * 0.5)]


def square_roi(scene, camera, obj, width, height, side_px, offset_m):
    """Square ROI of ``side_px`` centred at the object's projected centre plus ``offset_m`` (screen x right, y up)."""
    centre = obj.matrix_world.translation
    point = world_to_camera_view(scene, camera, centre + Vector((offset_m[0], 0.0, offset_m[1])))
    cx, cy = point.x * width, (1 - point.y) * height
    return [round(cx - side_px * 0.5), round(cy - side_px * 0.5),
            round(cx + side_px * 0.5), round(cy + side_px * 0.5)]


# VISUAL_TARGET "Common measurement setup" step 3: three unobstructed patches, report the median. Fuzz uses 64 x 64 px
# flat-lit patches at H = 256 (left / centre / right of the flat swatch). Sheen needs form shading for its 31 px
# form-removal blur, so its patches sit fully inside the key-lit side of the sphere (upper-left, left, top; centres at
# 0.55 R so every corner stays on the surface - the T-019 single ROI reached past the silhouette into the backdrop).
FUZZ_PATCH_OFFSETS_M = ((-0.13, 0.0), (0.0, 0.0), (0.13, 0.0))
SHEEN_PATCH_ANGLES_DEG = (135.0, 180.0, 90.0)
SHEEN_PATCH_RADIUS_FRACTION = 0.55
FUZZ_PATCH_PX_AT_H256 = 64
SHEEN_PATCH_PX_AT_H256 = 72


def _png_chunk(kind, payload):
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", binascii.crc32(kind + payload) & 0xffffffff)


def write_rgb8_png(path, pixels):
    """Write an exact RGB8 PNG; used only to stack already-rendered frames."""
    height, width, channels = pixels.shape
    if channels != 3 or pixels.dtype != np.uint8:
        raise ValueError("write_rgb8_png expects an HxWx3 uint8 array")
    scanlines = b"".join(b"\0" + pixels[y].tobytes() for y in range(height))
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    with open(path, "wb") as handle:
        handle.write(b"\x89PNG\r\n\x1a\n")
        handle.write(_png_chunk(b"IHDR", ihdr))
        handle.write(_png_chunk(b"IDAT", zlib.compress(scanlines, 9)))
        handle.write(_png_chunk(b"IEND", b""))


def stack_frames(paths, out):
    # Import the exact display-PNG decoder used by the metric script.  No
    # colour transform is applied while composing the vertical evidence sheet.
    from materials.measure_swatches import load_display_rgb
    frames = []
    width = None
    for path in paths:
        rgb, frame_width, _frame_height = load_display_rgb(path)
        if width is not None and frame_width != width:
            raise ValueError("swatch frame widths do not match")
        width = frame_width
        frames.append(np.rint(rgb * 255.0).astype(np.uint8))
    write_rgb8_png(out, np.concatenate(frames, axis=0))


def main():
    args = parse()
    started = time.time()
    out = os.path.abspath(args.out)
    metadata_path = os.path.abspath(args.metadata)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    os.makedirs(os.path.dirname(metadata_path), exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    rig = None
    if args.lighting == "harness":
        HARNESS.studio_lighting()
    else:
        rig = RC.apply(scene, RC.load(args.lighting))

    engine_settings = render_engine.configure(scene, args.engine, args.samples, cycles_device="CPU",
                                               cycles_denoiser="OPENIMAGEDENOISE")
    if args.engine == "cycles":
        # T-034: --denoiser off renders the raw Cycles estimate (OIDN survival metrics).
        scene.cycles.use_denoising = args.denoiser == "oidn"
        engine_settings["denoising"] = scene.cycles.use_denoising
    if max(args.width, args.height) > 640:
        raise SystemExit("each swatch render must be <=640 px in both dimensions")
    scene.render.resolution_x = args.width
    scene.render.resolution_y = args.height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.film_transparent = False
    if rig is None:
        requested_transform = args.view_transform
        try:
            scene.view_settings.view_transform = requested_transform
        except TypeError:
            requested_transform = scene.view_settings.view_transform
        scene.view_settings.exposure = args.exposure
    else:
        requested_transform = scene.view_settings.view_transform

    camera_data = bpy.data.cameras.new("SwatchCamera")
    camera = bpy.data.objects.new("SwatchCamera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.location = (0.0, -6.0, 0.0)
    camera.data.type = "ORTHO"
    # Each preset is rendered independently at <=640 px, then its exact PNG
    # bytes are stacked.  Keep the horizontal field at 0.6 m: the 0.256 m
    # reference therefore projects to 204.8 px at the default 480 px width.
    camera.data.ortho_scale = 0.6 * args.height / args.width
    look_at(camera, (0.0, 0.0, 0.0))
    if rig:
        RC.orient(rig, (0.0, -1.0, 0.0))

    text_material = G.material("M_swatch_labels", (32, 29, 28), roughness=0.9)
    neutral_material = G.material("M_swatch_neutral", (128, 128, 128), roughness=1.0, specular=0.0)
    library = MATERIALS.load_library()
    selected = [item.strip() for item in args.presets.split(",") if item.strip()] or list(library["presets"])
    # presets/1 ids by default; ids of the presets/2 skin family (T-066, skin_presets.json) only when named
    unknown = [name for name in selected if name not in library["presets"] and not MATERIALS.is_skin_preset(name)]
    if unknown:
        raise SystemExit(f"unknown presets: {unknown}")
    entries = []
    for index, name in enumerate(selected):
        x = 0.0
        preset_library = MATERIALS.library_for(name, library)
        preset = preset_library["presets"][name]
        material = MATERIALS.build_material("M_swatch_" + name, name, preset["swatch_srgb"],
                                            preset_library["reference_size_m"])
        bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=0.125,
                                             location=(x, 0.0, 0.18))
        sphere = bpy.context.object
        sphere.name = "sphere_" + name.replace("/", "_").replace(" ", "_")
        bpy.ops.object.shade_smooth()
        G.assign(sphere, material)
        fabric = patch(name, (x, 0.0, -0.10), material)
        fabric_fibre_source = fibre_patch_surface(name, (x, 0.0, -0.10))
        caption = label(name, (x, -0.17, -0.305), text_material)
        bpy.ops.mesh.primitive_cube_add(location=(0.215, 0.0, 0.285), scale=(0.035, 0.025, 0.035))
        neutral = bpy.context.object
        neutral.name = "neutral_" + name.replace("/", "_").replace(" ", "_")
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        G.assign(neutral, neutral_material)
        generated_fibres = [MATERIALS.add_fibres_geometry(surface, name, preset["swatch_srgb"],
                                                            preset_library["reference_size_m"], lod=args.fibres_lod)
                            for surface in (sphere, fabric_fibre_source)]
        objects = [sphere, fabric, caption, neutral] + [item for item in generated_fibres if item is not None]
        for obj in objects:
            obj.hide_render = True
        entries.append({"preset": name, "base_color_srgb": preset["swatch_srgb"], "sphere": sphere, "patch": fabric,
                        "neutral": neutral, "objects": objects, "fibre_source": fabric_fibre_source})

    bpy.context.view_layer.update()
    metadata = {
        "schema": "plush-studio.material-swatches/1",
        "blender": bpy.app.version_string,
        "image": os.path.relpath(out, ROOT).replace("\\", "/"),
        "width": args.width,
        "height": args.height * len(entries),
        "render_width": args.width,
        "render_height": args.height,
        ("max_cycles_render_dimension_px" if args.engine == "cycles" else
         "max_eevee_render_dimension_px"): max(args.width, args.height),
        "samples": args.samples,
        "exposure": scene.view_settings.exposure,
        "view_transform": requested_transform,
        "render_engine": engine_settings["blender_engine"],
        "engine_settings": engine_settings,
        "device": "CPU" if args.engine == "cycles" else "N/A",
        "denoiser": (("OPENIMAGEDENOISE" if args.denoiser == "oidn" else "none")
                     if args.engine == "cycles" else "OFF"),
        "studio_light": ("pipeline/blender/compare_harness.py:studio_lighting" if rig is None else
                         "pipeline/charsys/render_calibration.json:" + args.lighting),
        "reference_size_m": library["reference_size_m"],
        "projected_reference_px": round(library["reference_size_m"] / 0.6 * args.width, 4),
        "fibres_lod": args.fibres_lod,
        "swatches": [],
    }
    frame_dir = os.path.join(os.path.dirname(out), "." + os.path.splitext(os.path.basename(out))[0] + "_frames")
    os.makedirs(frame_dir, exist_ok=True)
    frame_paths = []
    render_total = 0.0
    for index, entry in enumerate(entries):
        for obj in entry["objects"]:
            obj.hide_render = False
        bpy.context.view_layer.update()
        patch_roi = roi(scene, camera, entry["patch"], args.width, args.height)
        sheen_roi = roi(scene, camera, entry["sphere"], args.width, args.height, 0.4, (-0.22, -0.22))
        neutral_roi = roi(scene, camera, entry["neutral"], args.width, args.height, 0.72)
        px_per_m = args.width / 0.6
        h_px = library["reference_size_m"] * px_per_m
        fuzz_side = FUZZ_PATCH_PX_AT_H256 * h_px / 256.0
        sheen_side = SHEEN_PATCH_PX_AT_H256 * h_px / 256.0
        sphere_r = 0.125
        fuzz_rois = [square_roi(scene, camera, entry["patch"], args.width, args.height, fuzz_side, off)
                     for off in FUZZ_PATCH_OFFSETS_M]
        sheen_rois = [square_roi(scene, camera, entry["sphere"], args.width, args.height, sheen_side,
                                 (math.cos(math.radians(a)) * SHEEN_PATCH_RADIUS_FRACTION * sphere_r,
                                  math.sin(math.radians(a)) * SHEEN_PATCH_RADIUS_FRACTION * sphere_r))
                      for a in SHEEN_PATCH_ANGLES_DEG]
        sheet_offset = index * args.height
        frame_path = os.path.join(frame_dir, f"{index:02d}_{entry['preset'].replace('/', '_').replace(' ', '_')}.png")
        scene.render.filepath = frame_path
        one_started = time.time()
        bpy.ops.render.render(write_still=True)
        render_total += time.time() - one_started
        frame_paths.append(frame_path)
        metadata["swatches"].append({
            "preset": entry["preset"],
            "base_color_srgb": entry["base_color_srgb"],
            "patch_roi_px": [patch_roi[0], patch_roi[1] + sheet_offset,
                             patch_roi[2], patch_roi[3] + sheet_offset],
            "sheen_roi_px": [sheen_roi[0], sheen_roi[1] + sheet_offset,
                             sheen_roi[2], sheen_roi[3] + sheet_offset],
            "neutral_roi_px": [neutral_roi[0], neutral_roi[1] + sheet_offset,
                               neutral_roi[2], neutral_roi[3] + sheet_offset],
            "fuzz_rois_px": [[r[0], r[1] + sheet_offset, r[2], r[3] + sheet_offset] for r in fuzz_rois],
            "sheen_rois_px": [[r[0], r[1] + sheet_offset, r[2], r[3] + sheet_offset] for r in sheen_rois],
            "projected_reference_px": metadata["projected_reference_px"],
        })
        for obj in entry["objects"]:
            obj.hide_render = True

    stack_frames(frame_paths, out)
    for frame_path in frame_paths:
        os.remove(frame_path)
    os.rmdir(frame_dir)
    metadata["render_s"] = round(render_total, 2)
    metadata["total_s"] = round(time.time() - started, 2)
    with open(metadata_path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(metadata, handle, indent=2)
        handle.write("\n")
    if args.save_blend:
        blend_path = os.path.abspath(args.save_blend)
        os.makedirs(os.path.dirname(blend_path), exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print(f"[render_swatches] {out} ({args.width}x{args.height * len(entries)} sheet; "
          f"{len(entries)} renders at {args.width}x{args.height})")


if __name__ == "__main__":
    main()
