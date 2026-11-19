"""T-119 measures on built masters (current against candidate), used by the README and test_garments_r3.py.

    blender -b --factory-startup -P docs/evaluation/characters/T-119/measure.py -- <out.json> <girl|boy>
        <label>=<master.blend> ...

girl  collar: per pose (rest = arms down, half reach, full one-arm reach): distance of the collar's vertices to the
      posed layers under it (body, blouse and vest main pieces), m (p50 / p95 / max: how far it stands off); how far
      the collar moved from its rest place (max, m); its deform bones. bloomers: the gap between the two cuff bands
      on the centre line (negative = they overlap) and how far the shell hangs below the bands.
boy   ankle: per pose (rest, toes up 25 deg, toes down 30 deg): area of visible skin (the evaluated body, i.e. after
      the garment mask) between 3 cm below and 6 cm above the trouser hem that a horizontal ray leaving the leg does
      not find covered by a garment piece, cm2. hands: the material and preset on hand.L."""
import json
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

ARMS_DOWN = [("upper_arm_fk.{s}", "Y", 35.0, "LR", True)]
POSES = {"girl": {"rest": ARMS_DOWN, "half_reach": ARMS_DOWN + [("upper_arm_fk.{s}", "X", -37.5, "L", False)],
                  "full_reach": ARMS_DOWN + [("upper_arm_fk.{s}", "X", -75.0, "L", False)]},
         "boy": {"rest": ARMS_DOWN, "toes_up": ARMS_DOWN + [("foot_fk.{s}", "X", 25.0, "LR", False)],
                 "toes_down": ARMS_DOWN + [("foot_fk.{s}", "X", -30.0, "LR", False)]}}


def pose(rig, steps):
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="POSE")
    for pb in rig.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
        if "IK_FK" in pb.keys():
            pb["IK_FK"] = 1.0
    bpy.context.view_layer.update()
    for pattern, axis, deg, sides, mirror in steps:
        for s in sides:
            pb = rig.pose.bones[pattern.format(s=s)]
            a = -deg if (mirror and s == "R") else deg
            hw = rig.matrix_world @ pb.head
            rm = Matrix.Translation(hw) @ Matrix.Rotation(math.radians(a), 4, axis) @ Matrix.Translation(-hw)
            pb.matrix = rig.matrix_world.inverted() @ rm @ rig.matrix_world @ pb.matrix
            bpy.context.view_layer.update()
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.context.view_layer.update()


def evaluated(ob):
    e = ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
    m = e.to_mesh()
    pts = [e.matrix_world @ v.co for v in m.vertices]
    faces = [tuple(p.vertices) for p in m.polygons]
    areas = [p.area for p in m.polygons]
    e.to_mesh_clear()
    return pts, faces, areas


def bvh_of(objects):
    verts, faces = [], []
    for ob in objects:
        pts, fs, _ = evaluated(ob)
        base = len(verts)
        verts += pts
        faces += [tuple(base + i for i in f) for f in fs]
    return BVHTree.FromPolygons(verts, faces, all_triangles=False)


def pieces(item=None, part=None):
    return [o for o in bpy.data.objects if o.type == "MESH" and o.get("ps_garment_item")
            and (item is None or o["ps_garment_item"] == item) and (part is None or o.get("ps_garment_part") == part)]


def quantiles(values):
    v = sorted(values)
    return {"p50": round(v[len(v) // 2], 5), "p95": round(v[int(0.95 * (len(v) - 1))], 5), "max": round(v[-1], 5)}


def girl(rig):
    collar = pieces("blouse", "collar")[0]
    collider = bpy.data.objects["garment.collider.body_skin"]  # the whole posed body (body_skin itself is masked)
    under = [collider] + pieces("blouse", "main") + pieces("vest", "main")
    out = {"collar_bones": sorted(g.name for g in collar.vertex_groups if not g.name.startswith("ps_")
                                  and any(g.index == x.group and x.weight > 1e-4 for v in collar.data.vertices
                                          for x in v.groups)), "poses": {}}
    rest = None
    for name, steps in POSES["girl"].items():
        pose(rig, steps)
        pts = evaluated(collar)[0]
        tree = bvh_of(under)
        dist = [tree.find_nearest(p)[3] for p in pts]
        rest = pts if rest is None else rest
        out["poses"][name] = {"stand_off_m": quantiles(dist),
                              "moved_from_rest_max_m": round(max((a - b).length for a, b in zip(pts, rest)), 5)}
    pose(rig, [])
    bands = {}
    for s in ("L", "R"):
        band = bpy.data.objects[f"garment.shorts.band.cuff.{s}"]
        bands[s] = [band.matrix_world @ v.co for v in band.data.vertices]
    shell = [o.matrix_world @ v.co for o in pieces("shorts", "main") for v in o.data.vertices]
    band_low = min(p.z for ps in bands.values() for p in ps)
    out["bloomers"] = {"band_gap_m": round(min(p.x for p in bands["L"]) - max(p.x for p in bands["R"]), 4),
                       "shell_below_bands_m": round(max(0.0, band_low - min(p.z for p in shell)), 4)}
    return out


def boy(rig):
    body = bpy.data.objects["body_skin"]
    garments = pieces()
    main = bpy.data.objects["garment.trousers.main"]
    hem = min((main.matrix_world @ v.co).z for v in main.data.vertices)
    hand = bpy.data.objects["hand.L"]
    mat = hand.data.materials[0]
    out = {"hand_material": mat.name, "hand_preset": mat.get("ps_material_preset"), "trouser_hem_z_m": round(hem, 4),
           "poses": {}}
    for name, steps in POSES["boy"].items():
        pose(rig, steps)
        pts, faces, areas = evaluated(body)
        cover = bvh_of(garments)
        seen, total = 0.0, 0.0
        for f, area in zip(faces, areas):
            c = sum((pts[i] for i in f), Vector((0.0, 0.0, 0.0))) / len(f)
            if not hem - 0.03 <= c.z <= hem + 0.06:
                continue
            n = (pts[f[1]] - pts[f[0]]).cross(pts[f[2]] - pts[f[0]])
            d = Vector((n.x, n.y, 0.0))
            if d.length < 1e-12:
                continue
            total += area
            if cover.ray_cast(c + d.normalized() * 1e-4, d.normalized(), 0.4)[0] is None:
                seen += area
        out["poses"][name] = {"visible_skin_cm2": round(total * 1e4, 2), "uncovered_skin_cm2": round(seen * 1e4, 2)}
    return out


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    out, which = argv[0], argv[1]
    res = {"set": which, "blender": bpy.app.version_string, "columns": {}}
    for a in argv[2:]:
        label, blend = a.split("=", 1)
        bpy.ops.wm.open_mainfile(filepath=os.path.abspath(blend))
        rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
        res["columns"][label] = girl(rig) if which == "girl" else boy(rig)
    json.dump(res, open(out, "w"), indent=1)
    print("MEASURE", json.dumps(res))


main()
