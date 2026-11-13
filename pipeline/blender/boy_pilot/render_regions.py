"""Renders a pilot .blend from harness cameras twice: the normal look (beauty) and a flat region-ID image (each
material region drawn in a unique emission colour, no shading). Used for colour calibration and region metrics.

    blender -b -P pipeline/blender/boy_pilot/render_regions.py -- <subject.blend> <reference_index.json> <out_dir> \
        [views=val27_front,val27_side_right,val27_back] [samples=24]

Writes <view>_beauty.png and <view>_id.png (360x720, same camera placement as compare_harness.py)."""
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import compare_harness as H  # noqa: E402

REGIONS = {  # material name -> region id colour (sRGB 0-1)
    "M_hair_felt": (1, 0, 0), "M_hair_fur": (1, 0, 0),
    "M_skin": (0, 1, 0),
    "M_hoodie_fleece": (0, 0, 1), "M_hoodie_fur": (0, 0, 1),
    "M_trousers_fleece": (1, 1, 0), "M_trousers_fur": (1, 1, 0),
    "M_shoe_felt": (1, 0, 1), "M_shoe_fur": (1, 0, 1),
    "M_sole": (0, 1, 1),
    "M_backpack_felt": (1, 0.5, 0), "M_webbing": (1, 0.5, 0),
    "M_eye": (0.5, 0, 1),
}


def emission(name, rgb):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = (*rgb, 1)
    o = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(e.outputs[0], o.inputs[0])
    return m


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    subject, index_path, out = map(os.path.abspath, argv[:3])
    views = (argv[3] if len(argv) > 3 else "val27_front,val27_side_right,val27_back").split(",")
    samples = int(argv[4]) if len(argv) > 4 else 24
    os.makedirs(out, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    objs = H.import_subject(subject, "backdrop", keep_materials=True)
    bpy.context.view_layer.update()
    lo, hi = H.bbox(objs)
    target = (lo + hi) * 0.5
    H.studio_lighting()
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.render.film_transparent = True
    sc.render.resolution_x, sc.render.resolution_y = 360, 720
    sc.render.image_settings.color_mode = "RGBA"
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    import json
    index = {v["id"]: v for v in json.load(open(index_path))["views"]}
    # Material swap tables for the ID pass.
    ids = {}
    black = emission("ID_other", (0, 0, 0))
    owners = [o for o in bpy.data.objects if o.type in ("MESH", "CURVES") and o.data is not None]
    original = {o.name: [s.material for s in o.material_slots] for o in owners}
    for vid in views:
        v = index[vid]
        for o in bpy.data.objects:
            o.hide_render = any(o.name.startswith(p) for p in v.get("hide_objects_prefix", []))
        H.place_camera(cam, target, v["yaw_deg"], v["elevation_deg"], v["focal_mm_estimate"], lo, hi, 0.5, 0.94)
        # beauty
        for o in owners:
            for s, m in zip(o.material_slots, original[o.name]):
                s.material = m
        sc.cycles.samples, sc.cycles.use_denoising = samples, True
        sc.view_settings.view_transform = "AgX"
        sc.render.filter_size = 1.5
        sc.render.filepath = os.path.join(out, f"{vid}_beauty.png")
        bpy.ops.render.render(write_still=True)
        # region ID
        for o in owners:
            for s, m in zip(o.material_slots, original[o.name]):
                rgb = REGIONS.get(m.name if m else "", None)
                if rgb is None:
                    s.material = black
                else:
                    if rgb not in ids:
                        ids[rgb] = emission(f"ID_{len(ids)}", rgb)
                    s.material = ids[rgb]
        sc.cycles.samples, sc.cycles.use_denoising = 4, False
        sc.view_settings.view_transform = "Standard"
        sc.render.filter_size = 0.01
        sc.render.filepath = os.path.join(out, f"{vid}_id.png")
        bpy.ops.render.render(write_still=True)
        print("[regions]", vid, flush=True)


main()
