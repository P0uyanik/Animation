"""Blender worker. One flat Workbench object-colour pass per reference camera."""
import sys
from pathlib import Path

import bpy
from bpy_extras.object_utils import world_to_camera_view

sys.path.insert(0, str(Path(__file__).resolve().parent))
from core import ROOT, child, read, write

sys.path.insert(0, str(ROOT / "pipeline/blender"))
import compare_harness as cameras


def main(job_path):
    job = read(job_path)
    out = Path(job_path).resolve().parent
    bpy.ops.wm.open_mainfile(filepath=str(child(out, job["blend"])))
    scene = bpy.context.scene
    root = next(c for c in bpy.data.collections if c.get("ps_character_id"))
    objects = [o for o in root.all_objects if o.type in ("MESH", "CURVES")
               and not o.hide_render and not o.name.startswith("WGT")]
    colours = {"eye.L": (1, 0, 0), "eye.R": (0, 1, 0),
               "brow.L": (0, 0, 1), "brow.R": (1, 1, 0)}
    for o in objects:
        o.color = (*colours.get(o.name, (1, 1, 1)), 1)
    cam = bpy.data.objects.new("Fit camera", bpy.data.cameras.new("Fit camera"))
    scene.collection.objects.link(cam)
    scene.camera = cam
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.resolution_y = job["height"]
    scene.render.resolution_x = job["height"] // 2
    scene.render.resolution_percentage = 100
    scene.display.render_aa = "OFF"
    shading = scene.display.shading
    shading.light = "FLAT"
    shading.color_type = "OBJECT"
    shading.show_shadows = shading.show_cavity = shading.show_specular_highlight = False
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0
    scene.view_settings.gamma = 1
    empties = {o.name[3:]: o for o in root.all_objects if o.name.startswith("LM_")}
    for i, view in enumerate(job["views"]):
        prefixes = tuple(view.get("hide_objects_prefix", ()))
        for o in objects:
            o.hide_render = (o.name == "glasses_lens" or
                             (o.name.startswith(prefixes) and not o.name.startswith("garment.")))
        lo, hi = cameras.bbox([o for o in objects if not o.hide_render])
        cameras.place_camera(cam, (lo + hi) / 2, view["yaw_deg"], view["elevation_deg"],
                             view["focal_mm_estimate"], lo, hi,
                             scene.render.resolution_x / scene.render.resolution_y, 0.9)
        bpy.context.view_layer.update()
        points = {}
        for name, obj in empties.items():
            p = world_to_camera_view(scene, cam, obj.matrix_world.translation)
            points[name] = [p.x * scene.render.resolution_x, (1 - p.y) * scene.render.resolution_y]
        name = f"pass-{i:03d}"
        write(child(out, name + ".json"), points)
        scene.render.filepath = str(child(out, name + ".png"))
        bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main(sys.argv[sys.argv.index("--") + 1])
