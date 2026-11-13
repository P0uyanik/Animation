"""Camera-matched comparison harness (runs inside Blender, headless).

    blender -b --factory-startup -P pipeline/blender/compare_harness.py -- \
        --subject renders/compare/it4_boy/it4_boy.obj --index assets/characters/boy_yellow_hoodie/references/reference_index.json \
        --out renders/compare/it4_boy/blender [--width 360 --height 720 --samples 48] [--save-blend path.blend]

For every view in the reference index it places a camera at the view's yaw, elevation and lens estimate around
the subject, frames the subject's full height (90% of the image), renders a colour image with a transparent
background (the alpha is the silhouette) under fixed neutral studio lighting, and writes cameras.json (Blender and
Plush coordinates) so the same cameras can be rendered by Plush Studio.

Conventions: the subject stands at the origin facing the front camera. Imported OBJ files are Y-up (Plush) and are
converted to Blender's Z-up by the importer; the character then faces -Y. yaw 0 = camera in front (-Y),
+90 = camera on the character's left (+X), 180 = behind.
Evaluation tool only: it does not modify the subject file or any Plush data."""
import argparse
import json
import math
import os
import sys
import time

import bpy
from mathutils import Vector


def parse():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", required=True)
    ap.add_argument("--index", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--width", type=int, default=360)
    ap.add_argument("--height", type=int, default=720)
    ap.add_argument("--samples", type=int, default=48)
    ap.add_argument("--fill", type=float, default=0.9, help="fraction of the image height the subject fills")
    ap.add_argument("--views", default="", help="comma-separated view ids (default: all)")
    ap.add_argument("--drop-material", default="backdrop", help="objects using a material containing this are removed")
    ap.add_argument("--save-blend", default="")
    return ap.parse_args(argv)


def import_subject(path, drop):
    before = set(bpy.data.objects)
    ext = os.path.splitext(path)[1].lower()
    if ext == ".obj":
        bpy.ops.wm.obj_import(filepath=path, forward_axis="NEGATIVE_Z", up_axis="Y")
    elif ext in (".glb", ".gltf"):
        bpy.ops.import_scene.gltf(filepath=path)
    else:
        raise SystemExit(f"unsupported subject format: {ext}")
    objs = [o for o in bpy.data.objects if o not in before]
    for o in list(objs):
        mats = [s.material.name for s in o.material_slots if s.material]
        if drop and any(drop in m for m in mats):
            bpy.data.objects.remove(o, do_unlink=True)
            objs.remove(o)
    for o in objs:  # neutral, slightly rough materials: the harness compares shape and colour, not look development
        for s in o.material_slots:
            if s.material and s.material.use_nodes:
                p = s.material.node_tree.nodes.get("Principled BSDF")
                if p:
                    p.inputs["Roughness"].default_value = 0.8
                    p.inputs["Specular IOR Level"].default_value = 0.3
    return objs


def bbox(objs):
    lo = Vector((1e9, 1e9, 1e9)); hi = Vector((-1e9, -1e9, -1e9))
    for o in objs:
        if o.type != "MESH":
            continue
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
    return lo, hi


def studio_lighting():
    world = bpy.data.worlds.new("Neutral") if not bpy.context.scene.world else bpy.context.scene.world
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (0.5, 0.5, 0.5, 1)
    bg.inputs["Strength"].default_value = 0.6
    for name, loc, energy, size in (("Key", (-1.6, -2.2, 2.4), 260, 1.6), ("Fill", (2.0, -1.8, 1.2), 90, 2.0),
                                    ("Rim", (0.6, 2.2, 2.0), 160, 1.2)):
        light = bpy.data.lights.new(name, "AREA")
        light.energy, light.size = energy, size
        ob = bpy.data.objects.new(name, light)
        bpy.context.scene.collection.objects.link(ob)
        ob.location = loc
        direction = Vector((0, 0, 0.5)) - Vector(loc)
        ob.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def place_camera(cam, target, yaw, elev, focal, lo, hi, aspect, fill):
    cam.data.lens = focal
    cam.data.sensor_fit = "HORIZONTAL"
    cam.data.sensor_width = 36.0
    d = Vector((math.sin(math.radians(yaw)) * math.cos(math.radians(elev)),
                -math.cos(math.radians(yaw)) * math.cos(math.radians(elev)),
                math.sin(math.radians(elev))))
    corners = [Vector((x, y, z)) for x in (lo.x, hi.x) for y in (lo.y, hi.y) for z in (lo.z, hi.z)]
    # Vertical field of view from the horizontal sensor and the image aspect (width / height).
    half_v = math.atan(18.0 / focal / aspect)
    dist = 1.0
    for _ in range(40):  # distance so that the projected bbox height fills `fill` of the frame
        cam.location = target + d * dist
        cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        bpy.context.view_layer.update()
        inv = cam.matrix_world.inverted()
        ys = []
        for c in corners:
            p = inv @ c
            ys.append(p.y / -p.z)
        span = (max(ys) - min(ys)) / (2 * math.tan(half_v))
        dist *= span / fill
        if abs(span - fill) < 1e-4:
            break
    return d, dist


def main():
    a = parse()
    t0 = time.time()
    os.makedirs(a.out, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    objs = import_subject(os.path.abspath(a.subject), a.drop_material)
    lo, hi = bbox(objs)
    target = (lo + hi) * 0.5
    studio_lighting()
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = a.samples
    scene.cycles.use_denoising = True
    scene.render.film_transparent = True
    scene.render.resolution_x, scene.render.resolution_y = a.width, a.height
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.view_settings.view_transform = "AgX" if "AgX" in [v.identifier for v in scene.view_settings.bl_rna.properties["view_transform"].enum_items] else "Filmic"
    cam = bpy.data.objects.new("CompareCam", bpy.data.cameras.new("CompareCam"))
    scene.collection.objects.link(cam)
    scene.camera = cam
    index = json.load(open(a.index))
    wanted = set(filter(None, a.views.split(",")))
    cams = {"blender": bpy.app.version_string, "subject": a.subject, "width": a.width, "height": a.height,
            "subject_bbox_blender": [list(lo), list(hi)], "views": []}
    for v in index["views"]:
        if wanted and v["id"] not in wanted:
            continue
        d, dist = place_camera(cam, target, v["yaw_deg"], v["elevation_deg"], v["focal_mm_estimate"], lo, hi,
                               a.width / a.height, a.fill)
        scene.render.filepath = os.path.join(os.path.abspath(a.out), v["id"] + ".png")
        t = time.time()
        bpy.ops.render.render(write_still=True)
        cl, tg = cam.location, target
        cams["views"].append({
            "id": v["id"], "yaw_deg": v["yaw_deg"], "elevation_deg": v["elevation_deg"], "focal_mm": v["focal_mm_estimate"],
            "distance": dist, "camera_blender": list(cl), "target_blender": list(tg),
            # Plush is Y-up with the character facing +Z: (x, y, z)_plush = (x, z, -y)_blender
            "camera_plush": [cl.x, cl.z, -cl.y], "target_plush": [tg.x, tg.z, -tg.y], "render_s": round(time.time() - t, 2)})
        print(f"[harness] {v['id']}: yaw {v['yaw_deg']}, elev {v['elevation_deg']}, {v['focal_mm_estimate']} mm, "
              f"distance {dist:.2f} m, {time.time() - t:.1f} s", flush=True)
    cams["total_s"] = round(time.time() - t0, 1)
    json.dump(cams, open(os.path.join(a.out, "cameras.json"), "w"), indent=1)
    if a.save_blend:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(a.save_blend))
    print(f"[harness] done: {len(cams['views'])} views in {cams['total_s']} s (Blender {bpy.app.version_string})", flush=True)


main()
