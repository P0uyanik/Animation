"""T-087 review recipe, render side (headless Blender; read-only on the inputs). Character-independent.

    blender -b --factory-startup -P tools/review/blender_render.py -- <job.json>

job.json (written by tools/review/recipe.py, never by hand):
  {"out": dir, "engine": "cycles"|"workbench", "samples": n, "px": n, "lens_mm": f, "sensor_mm": f,
   "calibration": "character_neutral/1",
   "columns": [{"tag": str, "blend": path, "comparison_pose": {"upper_arm_fk_rotation_y_deg": f} | null}],
   "views": [{"name": str, "yaw_deg": f, "elevation_deg": f, "target": [x, y, z], "frame_height_m": f, "aspect": f}
             | {"name": str, ..., "fit": "head", "margin": f, "aspect": f}]}
A view with "fit": "head" is framed on the head bounds (the lowest LM_chin to the highest renderable top, plus
margin x that height above and margin_below (default 0.15) below), measured over ALL columns first, so every column still gets the same camera.

Every column is rendered in this ONE run with the same fixed cameras (not framed per model), the same light rig (the
shared calibration, re-aimed per camera direction like every other evaluation render), world, exposure, samples and
resolution. Face controls are zeroed (each version's own neutral). With comparison_pose the arms are lowered through
the rig exactly as build_character.py makes <id>_compare.blend. A pose probe records the upper-arm angle from
straight down (DEF-upper_arm.*) so the caller can refuse A-pose renders. Writes <out>/<tag>/<view>.png and
<out>/render_result.json. Nothing is written back to the inputs."""
import json
import math
import os
import sys
import time

import bpy
from mathutils import Matrix, Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "pipeline", "charsys"))
import render_calibration as RC  # noqa: E402
import render_engine  # noqa: E402


def apply_comparison_pose(rig, deg):
    """Same transform as build_character.py (compare variant): IK/FK switched to FK, upper_arm_fk rotated about the
    world Y axis through the shoulder by +deg (L) / -deg (R)."""
    bpy.context.view_layer.objects.active = rig
    for pb in rig.pose.bones:
        if "IK_FK" in pb.keys():
            pb["IK_FK"] = 1.0
    bpy.ops.object.mode_set(mode="POSE")
    for s, sx in (("L", 1), ("R", -1)):
        pb = rig.pose.bones.get(f"upper_arm_fk.{s}")
        if pb is None:
            continue
        head_w = rig.matrix_world @ pb.head
        rm = Matrix.Translation(head_w) @ Matrix.Rotation(math.radians(sx * deg), 4, "Y") @ Matrix.Translation(-head_w)
        pb.matrix = rig.matrix_world.inverted() @ rm @ rig.matrix_world @ pb.matrix
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.context.view_layer.update()


def arm_probe(rig):
    """Upper-arm angle from straight down, degrees, per side (evaluated pose). ~0 = arms down; A-pose is far larger."""
    out = {}
    for s in ("L", "R"):
        pb = rig.pose.bones.get(f"DEF-upper_arm.{s}")
        if pb is None:
            continue
        d = (rig.matrix_world @ pb.tail) - (rig.matrix_world @ pb.head)
        if d.length == 0:
            continue
        out[s] = round(math.degrees(d.angle(Vector((0, 0, -1)))), 2)
    return out


def open_column(col):
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(col["blend"]))
    rig = next((o for o in bpy.data.objects if o.type == "ARMATURE"), None)
    if rig is not None and col.get("comparison_pose"):
        apply_comparison_pose(rig, float(col["comparison_pose"]["upper_arm_fk_rotation_y_deg"]))
    return bpy.context.scene, rig


def head_bounds(sc):
    """(chin z, top z) of the opened character: LM_chin (the builder's face landmark) and the highest point of the
    renderable meshes/curves (evaluated bounding boxes, rig widgets excluded)."""
    chin = bpy.data.objects.get("LM_chin")
    if chin is None:
        raise SystemExit("head framing needs the LM_chin landmark empty")
    deps = bpy.context.evaluated_depsgraph_get()
    top = max((o.evaluated_get(deps).matrix_world @ Vector(c)).z for o in sc.objects
              if o.type in ("MESH", "CURVES") and not o.hide_render and not o.name.startswith("WGT")
              for c in o.evaluated_get(deps).bound_box)
    return chin.matrix_world.translation.z, top


def fit_views(job):
    """Resolves "fit": "head" views to one fixed target/frame height shared by every column."""
    fits = [v for v in job["views"] if v.get("fit") == "head"]
    if not fits:
        return None
    lo, hi = 1e9, -1e9
    for col in job["columns"]:
        sc, _ = open_column(col)
        c, t = head_bounds(sc)
        lo, hi = min(lo, c), max(hi, t)
    for v in fits:
        h = hi - lo
        # LM_chin sits on the underside of the jaw, above the lowest visible chin/jaw line: more room below
        bottom = lo - h * float(v.get("margin_below", 0.15))
        top = hi + h * float(v.get("margin", 0.05))
        v["target"] = [0.0, 0.0, round((bottom + top) / 2, 4)]
        v["frame_height_m"] = round(top - bottom, 4)
    return {"chin_z": round(lo, 4), "top_z": round(hi, 4)}


def main():
    job = json.load(open(sys.argv[sys.argv.index("--") + 1]))
    out = os.path.abspath(job["out"])
    os.makedirs(out, exist_ok=True)
    lens, sensor = float(job.get("lens_mm", 70.0)), float(job.get("sensor_mm", 36.0))
    fov = 2 * math.atan(sensor / 2 / lens)
    engine, spp, px = job["engine"], int(job["samples"]), int(job["px"])
    result = {"engine": engine, "samples": spp, "px": px, "lens_mm": lens, "sensor_mm": sensor,
              "calibration": job.get("calibration"), "blender": bpy.app.version_string, "columns": {}, "views": {}}
    result["head_bounds"] = fit_views(job)
    for col in job["columns"]:
        t0 = time.time()
        bpy.ops.wm.open_mainfile(filepath=os.path.abspath(col["blend"]))
        sc = bpy.context.scene
        for o in list(sc.objects):
            if o.type in ("LIGHT", "CAMERA"):
                bpy.data.objects.remove(o, do_unlink=True)
        lrig = RC.apply(sc, RC.load(job.get("calibration") or RC.DEFAULT))
        if engine == "workbench":
            sc.render.engine = "BLENDER_WORKBENCH"
            sc.display.shading.light = "STUDIO"
            sc.display.shading.color_type = "MATERIAL"
            sc.display.render_aa = "8"
        else:
            render_engine.configure(sc, "cycles", spp, cycles_device="CPU", cycles_denoiser="OPENIMAGEDENOISE")
            sc.cycles.seed = 0
        rig = next((o for o in bpy.data.objects if o.type == "ARMATURE"), None)
        info = {"blend": col["blend"], "comparison_pose": col.get("comparison_pose")}
        if rig is not None:
            for k in [k for k in rig.keys() if k.startswith("face_")]:
                rig[k] = 0.0
            rig.update_tag()
            if col.get("comparison_pose"):
                apply_comparison_pose(rig, float(col["comparison_pose"]["upper_arm_fk_rotation_y_deg"]))
            bpy.context.view_layer.update()
            info["arm_angle_from_down_deg"] = arm_probe(rig)
        cam = bpy.data.objects.new("ReviewCam", bpy.data.cameras.new("ReviewCam"))
        sc.collection.objects.link(cam)
        sc.camera = cam
        cam.data.type = "PERSP"
        cam.data.lens = lens
        cam.data.sensor_fit = "VERTICAL"
        cam.data.sensor_height = sensor
        cam.data.clip_start = 0.01
        os.makedirs(os.path.join(out, col["tag"]), exist_ok=True)
        for v in job["views"]:
            a, el = math.radians(v["yaw_deg"]), math.radians(v["elevation_deg"])
            d = Vector((math.sin(a) * math.cos(el), -math.cos(a) * math.cos(el), math.sin(el)))
            dist = v["frame_height_m"] / 2 / math.tan(fov / 2)
            target = Vector(v["target"])
            cam.location = target + d * dist
            cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
            RC.orient(lrig, d)
            sc.render.resolution_x = px
            sc.render.resolution_y = int(round(px * v["aspect"]))
            sc.render.resolution_percentage = 100
            sc.frame_set(sc.frame_current)
            sc.render.image_settings.file_format = "PNG"
            sc.render.filepath = os.path.join(out, col["tag"], v["name"] + ".png")
            bpy.ops.render.render(write_still=True)
            result["views"][v["name"]] = {"yaw_deg": v["yaw_deg"], "elevation_deg": v["elevation_deg"],
                                          "target": list(v["target"]), "distance_m": round(dist, 4),
                                          "frame_height_m": v["frame_height_m"],
                                          "resolution": [sc.render.resolution_x, sc.render.resolution_y]}
            print("rendered", col["tag"], v["name"], flush=True)
        info["seconds"] = round(time.time() - t0, 1)
        result["columns"][col["tag"]] = info
    json.dump(result, open(os.path.join(out, "render_result.json"), "w"), indent=1)


main()
