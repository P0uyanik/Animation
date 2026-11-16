"""Render a version-to-version eyelid/gaze strip from two character masters.

    blender -b --factory-startup -P pipeline/charsys/tests/eye_pitch_strip.py -- \
        --old <1.0.0 master.blend> --new <1.1.0 master.blend> --out <dir>

The input files are read-only.  Each cell is a 320 px square close-up (below the requested 400 px maximum), and the
combined eye_strip.png has versions as rows and eye pitch relative to the head as columns.  Positive pitch means up,
matching the engine/T-010 convention.
"""
import argparse
import json
import math
import os
import sys

import bpy
from mathutils import Vector


def parse():
    argv = sys.argv[sys.argv.index("--") + 1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", required=True)
    ap.add_argument("--new", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--pitches", type=float, nargs="+", default=[-15, -5, 0, 5, 10, 15])
    ap.add_argument("--samples", type=int, default=16)
    return ap.parse_args(argv)


def eye_visibility(scene, rig, eyes):
    """Front-grid shares whose first hit is eyeball surface / the procedural iris disc.

    The iris is defined in undeformed eye-local coordinates.  Undoing the rigid eye-bone deformation at each ray
    hit therefore measures actual iris exposure rather than merely exposed sclera.
    """
    deps = bpy.context.evaluated_depsgraph_get()
    surface = iris = total = 0
    for side, eye in zip(("L", "R"), eyes):
        pb = rig.pose.bones[f"DEF-eye.{side}"]
        deform = rig.matrix_world @ pb.matrix @ pb.bone.matrix_local.inverted() @ rig.matrix_world.inverted()
        undeform = eye.matrix_world.inverted() @ deform.inverted()
        c = eye.matrix_world.translation
        r = eye.dimensions.x / 2
        for ix in range(-6, 7):
            for iz in range(-6, 7):
                dx, dz = ix / 6 * r * 0.8, iz / 6 * r * 0.8
                if dx * dx + dz * dz > (0.8 * r) ** 2:
                    continue
                ok, loc, _nrm, _idx, ob, _mat = scene.ray_cast(
                    deps, Vector((c.x + dx, c.y - 0.5, c.z + dz)), Vector((0, 1, 0)))
                total += 1
                hit_eye = bool(ok and ob is not None and ob.name == eye.name)
                surface += hit_eye
                if hit_eye:
                    local = undeform @ loc
                    iris += local.y < 0 and math.hypot(local.x, local.z) <= 0.023
    return round(100.0 * surface / total, 1), round(100.0 * iris / total, 1)


def setup(master, samples):
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(master))
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.render.resolution_x = scene.render.resolution_y = 320
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.resolution_percentage = 100
    if scene.world is None:
        scene.world = bpy.data.worlds.new("t014_world")
    scene.world.color = (0.16, 0.16, 0.16)
    for ob in bpy.data.objects:
        if ob.name.startswith(("WGT-", "fur_")):
            ob.hide_render = True
    rig = next(ob for ob in bpy.data.objects if ob.type == "ARMATURE" and ob.name.startswith("rig_"))
    for key in rig.keys():
        if key.startswith("face_"):
            rig[key] = 0.0
    eyes = [bpy.data.objects[f"eye.{side}"] for side in ("L", "R")]
    centre = sum((ob.matrix_world.translation for ob in eyes), Vector()) / 2
    camera = bpy.data.objects.new("t014_eye_camera", bpy.data.cameras.new("t014_eye_camera"))
    camera.data.lens = 92
    camera.location = centre + Vector((0, -0.58, 0.004))
    camera.rotation_euler = (centre - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(camera)
    scene.camera = camera
    key = bpy.data.objects.new("t014_key", bpy.data.lights.new("t014_key", "AREA"))
    key.data.energy = 650
    key.data.shape = "DISK"
    key.data.size = 0.55
    key.location = centre + Vector((-0.35, -0.45, 0.42))
    key.rotation_euler = (centre - key.location).to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(key)
    fill = bpy.data.objects.new("t014_fill", bpy.data.lights.new("t014_fill", "AREA"))
    fill.data.energy = 300
    fill.data.size = 0.4
    fill.location = centre + Vector((0.38, -0.30, 0.05))
    fill.rotation_euler = (centre - fill.location).to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(fill)
    return scene, rig, eyes


def pose_pitch(rig, pitch):
    for side in ("L", "R"):
        pb = rig.pose.bones[f"DEF-eye.{side}"]
        for constraint in pb.constraints:
            constraint.mute = True
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = (math.radians(pitch), 0, 0)  # engine +pitch (up) == this Rigify deform bone's local +X
    rig.update_tag()
    bpy.context.view_layer.update()


def main():
    a = parse()
    a.old = os.path.abspath(a.old)
    a.new = os.path.abspath(a.new)
    a.out = os.path.abspath(a.out)
    os.makedirs(a.out, exist_ok=True)
    rows = []
    metrics = {"cell_px": 320, "pitches_deg": a.pitches, "versions": {}}
    for label, master in (("1.0.0", a.old), ("1.1.0", a.new)):
        scene, rig, eyes = setup(master, a.samples)
        row = []
        metrics["versions"][label] = []
        for pitch in a.pitches:
            pose_pitch(rig, pitch)
            tag = f"{pitch:+g}".replace("+", "p").replace("-", "m")
            path = os.path.join(a.out, f"eye_{label}_{tag}.png")
            scene.render.filepath = path
            bpy.ops.render.render(write_still=True)
            surface, iris = eye_visibility(scene, rig, eyes)
            metrics["versions"][label].append({"pitch_deg": pitch, "eye_surface_visible_pct": surface,
                                                 "iris_visible_grid_pct": iris,
                                                 "render": os.path.basename(path)})
            row.append(path)
        rows.append((label, row))
    try:
        from PIL import Image, ImageDraw
        cell = 320
        strip = Image.new("RGB", (cell * len(a.pitches), cell * len(rows)), (0, 0, 0))
        draw = ImageDraw.Draw(strip)
        for iy, (label, paths) in enumerate(rows):
            for ix, (pitch, path) in enumerate(zip(a.pitches, paths)):
                strip.paste(Image.open(path).convert("RGB"), (ix * cell, iy * cell))
                draw.rectangle((ix * cell, iy * cell, ix * cell + 150, iy * cell + 22), fill=(0, 0, 0))
                draw.text((ix * cell + 5, iy * cell + 5), f"{label}  eye {pitch:+g} deg", fill=(255, 255, 255))
        strip.save(os.path.join(a.out, "eye_strip.png"))
    except ImportError:
        metrics["warning"] = "Pillow unavailable in Blender Python; individual 320 px renders were kept"
    metrics["blender"] = bpy.app.version_string
    with open(os.path.join(a.out, "eye_pitch_metrics.json"), "w") as f:
        json.dump(metrics, f, indent=1)
    print("[eye_pitch_strip] ->", a.out)


if __name__ == "__main__":
    main()
