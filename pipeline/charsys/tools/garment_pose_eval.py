"""Garment clearance and posed renders of a built character master (headless Blender; read-only on the master).

    blender -b --factory-startup -P pipeline/charsys/tools/garment_pose_eval.py -- <master.blend> <out_dir>
        [--poses auto | idle_relaxed:45,wave:52,...]
        [--render-pose sit_down:50] [--index <reference_index.json> --views id,id,...] [--height 640] [--samples 32]
        [--lighting character_neutral/1]

Finds the garment/1 pieces (``ps_garment_generator``), the body that carries the garment mask and the rig in the
master, converts the rig to the semantic FK deform rig the repository clips are authored on (garments.evaluate), and
measures the signed garment-to-visible-body clearance at rest (floor 0.5 mm) and in every pose (floor 0). With
--render-pose it renders that pose from the reference views' yaw/elevation/focal under the shared character-render
calibration. ``--poses auto`` (default, T-025) evaluates the legacy six samples plus one sampled extreme per
``content/clips/*.clip.json`` (garments.evaluate.test_poses), so new clips become new test poses. Character-agnostic: everything comes from the master and the arguments. The master is never saved.
Writes garment_pose_eval.json and <pose>_<view>.png."""
import argparse
import json
import os
import sys
import time

import bpy
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "pipeline", "charsys"))
sys.path.insert(0, os.path.join(ROOT, "pipeline", "clips"))
sys.path.insert(0, os.path.join(ROOT, "pipeline", "blender"))
from garments import evaluate as EV  # noqa: E402
from garments import generator as GEN  # noqa: E402

DEFAULT_POSES = "auto"


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("master")
    ap.add_argument("out")
    ap.add_argument("--poses", default=DEFAULT_POSES)
    ap.add_argument("--render-pose", default="")
    ap.add_argument("--index", default="")
    ap.add_argument("--views", default="")
    ap.add_argument("--height", type=int, default=640)
    ap.add_argument("--samples", type=int, default=32)
    ap.add_argument("--lighting", default="")
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    t0 = time.time()
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(a.master))
    garments = [o for o in bpy.data.objects if o.get("ps_garment_generator") == GEN.GENERATOR]
    body = next(o for o in bpy.data.objects if o.type == "MESH" and o.modifiers.get(GEN.MASK_MODIFIER) is not None)
    rig = next(m.object for m in body.modifiers if m.type == "ARMATURE")
    worn = sorted({o["ps_garment_item"] for o in garments if not o.hide_render})
    objects = [o for o in garments if o["ps_garment_item"] in worn]
    floor = 0.0005
    gap = EV.SKIN_CONTACT_TOLERANCE_M
    player = EV.ClipPlayer(rig, EV.semantic_fk_rig(rig, ROOT), os.path.join(ROOT, "content", "clips"))
    player.reset()
    rest_positions = {o.name: EV.world_mesh(o)[0] for o in objects}
    result = {"blender": bpy.app.version_string, "master": os.path.basename(a.master), "worn": worn,
              "garment_objects": len(objects), "mask": GEN.set_active_items(body, garments, worn),
              "rest": EV.clearance(body, objects, floor, gap), "poses": {}}
    motion = {}
    worst = None
    clips_dir = os.path.join(ROOT, "content", "clips")
    specs = ([f"{n}:{f}" for n, f in EV.test_poses(clips_dir)] if a.poses == "auto"
             else [p for p in a.poses.split(",") if p])
    for spec in specs:
        name, frame = spec.split(":")
        meta = player.apply(name, int(frame))
        entry = {"source": meta, **EV.clearance(body, objects, 0.0, gap, contact_floor=floor)}
        result["poses"][spec] = entry
        if worst is None or entry["min_clearance_m"] < result["poses"][worst]["min_clearance_m"]:
            worst = spec
        for o in objects:
            motion[o.name] = max(motion.get(o.name, 0.0), EV.rms_motion(EV.world_mesh(o)[0], rest_positions[o.name]))
    result["worst_pose"] = {"pose": worst, **{k: result["poses"][worst][k] for k in
                                              ("min_clearance_m", "closest_object", "vertices_inside_visible_body")}} \
        if worst else None
    result["min_rms_motion_m"] = round(min(motion.values()), 6) if motion else None
    result["pass"] = result["rest"]["pass"] and all(p["pass"] for p in result["poses"].values())
    result["measure_s"] = round(time.time() - t0, 1)

    if a.render_pose:
        import compare_harness as CH
        import render_calibration as RC
        name, frame = a.render_pose.split(":")
        player.apply(name, int(frame))
        sc = bpy.context.scene
        for o in list(sc.objects):
            if o.type in ("LIGHT", "CAMERA"):
                bpy.data.objects.remove(o, do_unlink=True)
        light_rig = RC.apply(sc, RC.load(a.lighting or RC.DEFAULT))
        sc.render.engine = "CYCLES"
        sc.cycles.samples = a.samples
        sc.cycles.device = "CPU"
        sc.cycles.use_denoising = True
        sc.cycles.denoiser = "OPENIMAGEDENOISE"
        sc.render.film_transparent = False
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
        cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
        sc.collection.objects.link(cam)
        sc.camera = cam
        views = json.load(open(a.index))["views"]
        want = [v for v in a.views.split(",") if v]
        views = [v for v in views if not want or v["id"] in want]
        sc.render.resolution_x, sc.render.resolution_y = a.height // 2, a.height
        renders = {}
        for v in views:
            t = time.time()
            d, _ = CH.place_camera(cam, (lo + hi) / 2, v["yaw_deg"], v["elevation_deg"], v["focal_mm_estimate"],
                                   lo, hi, 0.5, 0.9)
            RC.orient(light_rig, d)
            path = os.path.join(a.out, f"{name}_{frame}_{v['id']}.png")
            sc.render.filepath = path
            bpy.ops.render.render(write_still=True)
            renders[v["id"]] = {"file": os.path.basename(path), "s": round(time.time() - t, 2)}
        result["render"] = {"pose": a.render_pose, "samples": a.samples, "height_px": a.height,
                            "lighting": a.lighting or RC.DEFAULT, "views": renders}
    result["total_s"] = round(time.time() - t0, 1)
    json.dump(result, open(os.path.join(a.out, "garment_pose_eval.json"), "w"), indent=1)
    print(json.dumps({k: result[k] for k in ("pass", "worst_pose", "total_s")}))


main()
