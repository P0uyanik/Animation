"""T-184 evidence: lower garments against the skin in a rendered shot, and hip crops of every character.

    blender -b --factory-startup -P seated_probe.py -- --shot <shot.blend> --out <dir> [--frames 1,2]
        [--size 512] [--samples 16] [--no-render]

<shot.blend> is what pipeline/charsys/shot_render.py writes (masters linked, deform bones keyed from an engine bake).
Per frame and character, as Blender evaluates the shot (armature, then the garment collision):
  * every vertex of the lower garments (shorts, trousers, tights, skirt) against the posed body: depth under the
    surface (signed along the nearest face normal) and whether that face is visible skin or skin the garment mask
    hides. "under visible skin" is what a render shows as skin through cloth;
  * two crops from fixed cameras aimed between the hips and the knees: "front" (level with the shot camera's side of
    the character) and "lap" (from 40 degrees to the side and above, looking down at the thighs).
Writes <out>/measure.json and <out>/frame_NNNN.png, numbered row by row as listed in measure.json["tiles"]
(tools/review/shot_sheet.py reads them as frames). Nothing character-specific: bones by the rig profile's names."""
import argparse
import json
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

LOWER = ("shorts", "trousers", "tights", "skirt")
VIEWS = (("front", 0.0, 0.12, 0.95), ("lap", 40.0, 0.55, 0.9))  # name, yaw from the shot camera side, height, distance

ap = argparse.ArgumentParser()
ap.add_argument("--shot", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--frames", default="")
ap.add_argument("--size", type=int, default=512)
ap.add_argument("--samples", type=int, default=16)
ap.add_argument("--no-render", action="store_true")
a = ap.parse_args(sys.argv[sys.argv.index("--") + 1:])
os.makedirs(a.out, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=a.shot)
sc = bpy.context.scene
frames = [int(f) for f in a.frames.split(",")] if a.frames else list(range(sc.frame_start, sc.frame_end + 1))
shot_cam = sc.camera
rigs = sorted((o for o in sc.objects if o.type == "ARMATURE"), key=lambda o: o.name)
report = {"shot": os.path.basename(a.shot), "frames": {}, "tiles": []}
tile = 0
for frame in frames:
    sc.frame_set(frame)
    dg = bpy.context.evaluated_depsgraph_get()
    per_frame = {}
    for rig in rigs:
        kids = [o for o in sc.objects if o.parent == rig and o.type == "MESH"]
        proxy = next((o for o in kids if o.get("ps_collision_proxy")), None)
        body = next((o for o in kids if o.name.startswith("body_skin")), None)
        if proxy is None or body is None:
            continue
        mask = body.vertex_groups.get("ps_garment_mask")
        hidden = {v.index for v in body.data.vertices
                  if mask is not None and any(g.group == mask.index and g.weight > 0 for g in v.groups)}
        e = proxy.evaluated_get(dg)
        m = e.to_mesh()
        pts = [e.matrix_world @ v.co for v in m.vertices]
        faces = [tuple(p.vertices) for p in m.polygons]
        e.to_mesh_clear()
        face_hidden = [any(v in hidden for v in f) for f in faces]
        bvh = BVHTree.FromPolygons(pts, faces)
        pieces = {}
        for o in sorted(kids, key=lambda o: o.name):
            if o.get("ps_garment_item") not in LOWER:
                continue
            ee = o.evaluated_get(dg)
            mm = ee.to_mesh()
            depth, visible = [], []
            for v in mm.vertices:
                p = ee.matrix_world @ v.co
                loc, nrm, fi, dist = bvh.find_nearest(p)
                depth.append(dist if (p - loc).dot(nrm) >= 0 else -dist)
                visible.append(not face_hidden[fi])
            ee.to_mesh_clear()
            d, vis = np.array(depth) * 1000, np.array(visible)
            under = d < -1.0
            pieces[o.name.split(".0")[0] if o.name[-4:-3] == "." and o.name[-3:].isdigit() else o.name] = {
                "vertices": len(d),
                "under_visible_skin": int((under & vis).sum()),
                "worst_under_visible_skin_mm": round(float(d[under & vis].min()), 1) if (under & vis).any() else 0.0,
                "under_hidden_skin": int((under & ~vis).sum()),
                "worst_under_hidden_skin_mm": round(float(d[under & ~vis].min()), 1) if (under & ~vis).any() else 0.0}
        per_frame[rig.name] = pieces
        if a.no_render:
            continue
        hips = rig.matrix_world @ rig.pose.bones["DEF-spine"].head
        knees = (rig.matrix_world @ rig.pose.bones["DEF-shin.L"].head
                 + rig.matrix_world @ rig.pose.bones["DEF-shin.R"].head) / 2
        target = (hips + knees) / 2
        towards = shot_cam.matrix_world.translation - target
        towards.z = 0
        towards.normalize()
        for view, yaw, up, dist in VIEWS:
            tile += 1
            cam = bpy.data.objects.new(f"t184_{tile}", bpy.data.cameras.new(f"t184_{tile}"))
            sc.collection.objects.link(cam)
            cam.data.lens = 70
            cam.location = target + (Matrix.Rotation(math.radians(yaw), 3, "Z") @ towards) * dist + Vector((0, 0, up))
            cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
            sc.camera = cam
            sc.render.resolution_x = sc.render.resolution_y = a.size
            sc.render.resolution_percentage = 100
            if sc.render.engine == "CYCLES":
                sc.cycles.samples = a.samples
            sc.render.filepath = os.path.join(a.out, f"frame_{tile:04d}.png")
            bpy.ops.render.render(write_still=True)
            report["tiles"].append({"file": f"frame_{tile:04d}.png", "frame": frame, "character": rig.name,
                                    "view": view})
        sc.camera = shot_cam
    report["frames"][str(frame)] = per_frame
json.dump(report, open(os.path.join(a.out, "measure.json"), "w"), indent=1)
print(json.dumps(report["frames"], indent=1))
