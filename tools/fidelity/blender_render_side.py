"""Fidelity tool, render side (headless Blender; read-only on the .blend). Character-independent.

    blender -b --factory-startup -P tools/fidelity/blender_render_side.py -- <in.blend> <reference_index.json> <out_dir>
        --views id,id,... [--height 640] [--region-map <json>] [--prepare-only <out.blend> --hide p1,p2]

For every requested reference view it places the camera exactly as pipeline/charsys/tools/groom_turnaround.py does
(same bounding box of the renderable character meshes, compare_harness.place_camera with fill 0.9, aspect 0.5) and writes
  <view>_regions.png   flat region colours (Cycles, 1 sample, emission stand-ins, minimal pixel filter, transparent
                       background), rendered without glasses; <view>_regions_glasses.png with them (glasses mask)
  <view>_landmarks.json  2D landmarks in render pixels (x right, y down) projected from bones, landmark empties and
                         mesh vertices, with a visibility flag (ray cast from the camera; glasses are see-through)
  regions.json         region name -> sRGB id colour
With --prepare-only it instead saves a copy of <in.blend> whose objects matching the --hide prefixes are excluded from
rendering (used for reference views that hide parts, e.g. "hide_objects_prefix" in reference_index.json) and exits.

Regions (shared rules; a per-character region map can add [glob, region] rules that win):
  hair collection: the dominant material -> hair, other materials -> hair_accessory
  clothing: garment.<item>.* -> garment:<item> (garment/1); other names -> garment:<first token>
  body, ears, lids -> skin (split later in 2D into skin_face above the projected chin and skin_limbs below)
  eye.* -> eyes; lash/brow/mouth -> face_detail; accessories glasses* -> glasses, others -> accessory:<first token>
  fur curves fur_<token> -> the region whose name ends with <token>, else hair if token == hair
Nothing is written back to the .blend."""
import argparse
import fnmatch
import json
import math
import os
import re
import sys

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "pipeline", "blender"))
import compare_harness as CH  # noqa: E402

PALETTE = [(230, 25, 75), (60, 180, 75), (255, 225, 25), (0, 130, 200), (245, 130, 48), (145, 30, 180),
           (70, 240, 240), (240, 50, 230), (210, 245, 60), (250, 190, 212), (0, 128, 128), (220, 190, 255),
           (170, 110, 40), (255, 250, 200), (128, 0, 0), (170, 255, 195), (128, 128, 0), (255, 215, 180),
           (0, 0, 128), (128, 128, 128)]


def srgb_to_linear(c):
    out = []
    for v in c:
        v = v / 255.0
        out.append(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4)
    return out


def token(name):
    return re.split(r"[._]", name)[0]


def character_root():
    return next((c for c in bpy.data.collections if "ps_character_id" in c.keys()), None)


def component_of(obj, root):
    for c in obj.users_collection:
        comp = c.get("ps_component")
        if comp:
            return comp
    return ""


def renderable(root, sc):
    pool = root.all_objects if root else sc.objects
    return [o for o in pool if o.type in ("MESH", "CURVES") and not o.hide_render and not o.name.startswith("WGT")]


def classify(objs, root, rules):
    """object name -> region (string)."""
    hair_counts = {}
    for o in objs:
        if o.type == "MESH" and component_of(o, root) == "hair":
            for p in o.data.polygons:
                m = o.data.materials[p.material_index] if o.data.materials else None
                if m:
                    hair_counts[m.name] = hair_counts.get(m.name, 0) + 1
    hair_main = max(sorted(hair_counts), key=lambda k: hair_counts[k]) if hair_counts else None
    out = {}
    for o in objs:
        n = o.name
        hit = next((r for g, r in rules if fnmatch.fnmatchcase(n, g)), None)
        if hit:
            out[n] = hit
            continue
        comp = component_of(o, root)
        if comp == "hair":
            mats = [m.name for m in o.data.materials if m] if o.type == "MESH" else []
            out[n] = "hair" if (not mats or hair_main in mats) else "hair_accessory"
        elif comp == "clothing":
            m = re.match(r"garment\.([^.]+)\.", n)
            out[n] = "garment:" + (m.group(1) if m else token(n))
        elif comp == "body":
            out[n] = "skin"
        elif comp == "face":
            if n.startswith("eye."):
                out[n] = "eyes"
            elif n.startswith(("lid_", "ear.")):
                out[n] = "skin"
            else:
                out[n] = "face_detail"
        elif comp == "accessories":
            out[n] = "glasses" if n.startswith("glasses") else "accessory:" + token(n)
        elif comp == "fur":
            t = n[4:] if n.startswith("fur_") else n
            out[n] = t  # resolved below
        else:
            out[n] = "other"
    names = set(v for k, v in out.items() if component_of(bpy.data.objects[k], root) != "fur")
    for k, v in list(out.items()):
        if component_of(bpy.data.objects[k], root) == "fur" and not any(fnmatch.fnmatchcase(k, g) for g, _ in rules):
            cand = sorted(r for r in names if r == v or r.endswith(":" + v) or r.endswith(":" + v.rstrip("s")))
            out[k] = cand[0] if cand else ("hair" if v == "hair" else "other")
    return out


def region_colours(regions):
    names = sorted(set(regions.values()))
    return {r: PALETTE[i % len(PALETTE)] for i, r in enumerate(names)}


def render_regions(sc, path, objs, regions, colours, hide=()):
    """Flat region colours (RGBA, transparent background): every material slot is swapped for an emission stand-in
    (restored afterwards). Objects named in `hide` are left out of this pass."""
    keep = (sc.cycles.samples, sc.cycles.use_denoising, sc.render.filter_size, sc.view_settings.view_transform,
            sc.view_settings.look, sc.view_settings.exposure, sc.view_settings.gamma, sc.world,
            sc.render.film_transparent, sc.render.image_settings.color_mode)
    hidden = [o for o in objs if o.name in hide and not o.hide_render]
    for o in hidden:
        o.hide_render = True
    flat = {}
    for r, col in colours.items():
        e = bpy.data.materials.new("_fid_" + r)
        if hasattr(e, "use_nodes") and not e.use_nodes:
            e.use_nodes = True
        nt = e.node_tree
        for nd in list(nt.nodes):
            nt.nodes.remove(nd)
        em = nt.nodes.new("ShaderNodeEmission")
        em.inputs["Color"].default_value = (*srgb_to_linear(col), 1)
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        nt.links.new(em.outputs[0], out.inputs["Surface"])
        flat[r] = e
    saved = []
    for o in objs:
        mat = flat[regions[o.name]]
        if len(o.material_slots) == 0:
            o.data.materials.append(mat)
            saved.append(("appended", o))
            continue
        for slot in o.material_slots:
            saved.append((slot, slot.material))
            slot.material = mat
    world = bpy.data.worlds.new("_fid_world")
    world.color = (0, 0, 0)
    sc.world = world
    sc.cycles.samples, sc.cycles.use_denoising, sc.render.filter_size = 1, False, 0.01
    sc.render.film_transparent = True
    sc.render.image_settings.color_mode = "RGBA"
    sc.view_settings.view_transform = "Standard"
    try:
        sc.view_settings.look = "None"
    except Exception:
        pass
    sc.view_settings.exposure, sc.view_settings.gamma = 0.0, 1.0
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    for a, b in saved:
        if a == "appended":
            b.data.materials.pop(index=len(b.data.materials) - 1)
        else:
            a.material = b
    (sc.cycles.samples, sc.cycles.use_denoising, sc.render.filter_size, sc.view_settings.view_transform,
     sc.view_settings.look, sc.view_settings.exposure, sc.view_settings.gamma, sc.world,
     sc.render.film_transparent, sc.render.image_settings.color_mode) = keep
    for o in hidden:
        o.hide_render = False
    for e in flat.values():
        bpy.data.materials.remove(e)
    bpy.data.worlds.remove(world)


class Projector:
    def __init__(self, sc, cam, deps, see_through):
        self.sc, self.cam, self.deps, self.see_through = sc, cam, deps, see_through
        self.W, self.H = sc.render.resolution_x, sc.render.resolution_y

    def px(self, p):
        v = world_to_camera_view(self.sc, self.cam, p)
        return [round(v.x * self.W, 2), round((1 - v.y) * self.H, 2)]

    def visible(self, p, eps=0.004):
        o = self.cam.matrix_world.translation.copy()
        d = p - o
        dist = d.length
        d.normalize()
        start = o
        travelled = 0.0
        for _ in range(8):
            hit, loc, _n, _i, ob, _m = self.sc.ray_cast(self.deps, start, d, distance=dist - travelled - eps)
            if not hit:
                return True
            if ob is not None and ob.name in self.see_through:
                step = (loc - start).length + 1e-4
                travelled += step
                start = start + d * step
                continue
            return False
        return False


def world_verts(o, deps):
    ev = o.evaluated_get(deps)
    me = ev.to_mesh()
    mw = ev.matrix_world
    pts = [mw @ v.co for v in me.vertices]
    ev.to_mesh_clear()
    return pts


def first_visible(cands, proj, eps=0.004):
    """First visible candidate as (point, False); if none is visible, the first candidate as (point, True) so the
    landmark is reported as hidden (surface point, visibility tested again) instead of being dropped."""
    for p in cands:
        if proj.visible(p, eps):
            return p, False
    return (cands[0], True) if cands else None


def landmarks_3d(objs, regions, rig, deps, sc, proj, view_dir):
    """Named 3D points with a 'surface' flag (surface points get a visibility test; skeletal points do not)."""
    lm = {}
    by = {o.name: o for o in objs}
    empties = {o.name[3:]: o.matrix_world.translation.copy() for o in bpy.data.objects
               if o.type == "EMPTY" and o.name.startswith("LM_")}
    bones = {}
    if rig is not None:
        for pb in rig.pose.bones:
            bones[pb.name] = (rig.matrix_world @ pb.head, rig.matrix_world @ pb.tail)
    fwd = Vector((0, -1, 0))
    facing = view_dir.dot(fwd)  # >0: camera in front of the character
    side = {"L": 1.0, "R": -1.0}
    mid_x = 0.0
    if "eye_L" in empties and "eye_R" in empties:
        mid_x = (empties["eye_L"].x + empties["eye_R"].x) / 2
    for k in ("eye_L", "eye_R", "nose", "mouth", "chin"):
        if k in empties:
            lm[k] = (empties[k], True)
    # eyes: iris (front-most point of the eyeball) and corners (extremes of the visible eyeball)
    for s in ("L", "R"):
        eo = by.get("eye." + s)
        if not eo:
            continue
        pts = world_verts(eo, deps)
        c = sum(pts, Vector()) / len(pts)
        front = sorted(pts, key=lambda p: -(p - c).dot(fwd))
        lm["iris_" + s] = (front[0], True)
        if facing > -0.2:
            vis = [p for p in pts if (p - c).dot(fwd) > 0 and proj.visible(p, 0.003)]
            if len(vis) >= 3:
                lat = sorted(vis, key=lambda p: abs(p.x - mid_x))
                lm["eye_inner_" + s] = (lat[0], False)
                lm["eye_outer_" + s] = (lat[-1], False)
        bo = by.get("brow." + s)
        if bo and facing > -0.2:
            bp = sorted(world_verts(bo, deps), key=lambda p: abs(p.x - mid_x))
            pi = first_visible(bp[:40], proj)
            po = first_visible(list(reversed(bp))[:40], proj)
            if pi:
                lm["brow_inner_" + s] = pi
            if po:
                lm["brow_outer_" + s] = po
        ear = by.get("ear." + s)
        if ear:
            ep = sorted(world_verts(ear, deps), key=lambda p: -p.z)
            pt = first_visible(ep[:60], proj)
            if pt:
                lm["ear_top_" + s] = pt
    mo = by.get("mouth")
    if mo and facing > 0.2:
        mp = world_verts(mo, deps)
        for s in ("L", "R"):
            cand = sorted(mp, key=lambda p: -side[s] * (p.x - mid_x))
            pt = first_visible(cand[:60], proj)
            if pt:
                lm["mouth_corner_" + s] = pt
    # hairline: lowest visible hair point on the face midline, in front of the head, above the eyes
    if facing > 0.3 and "eye_L" in empties:
        spacing = abs(empties["eye_L"].x - empties["eye_R"].x)
        eye_z = empties["eye_L"].z
        cand = []
        for o in objs:
            if regions.get(o.name) == "hair" and o.type == "MESH":
                cand += [p for p in world_verts(o, deps)
                         if abs(p.x - mid_x) < 0.12 * spacing and p.y < empties["eye_L"].y + 0.02 and p.z > eye_z]
        cand.sort(key=lambda p: p.z)
        pt = first_visible(cand[:200], proj, 0.006)
        if pt and not pt[1]:
            lm["hairline"] = pt
    # skeleton (Rigify deform names, shared rig generator)
    def bone(n):
        return bones.get(n)
    if bone("DEF-spine.004"):
        lm["neck"] = (bone("DEF-spine.004")[0], False)
    for s in ("L", "R"):
        if bone(f"DEF-upper_arm.{s}"):
            lm["shoulder_" + s] = (bone(f"DEF-upper_arm.{s}")[0], False)
        if bone(f"DEF-hand.{s}"):
            h, t = bone(f"DEF-hand.{s}")
            lm["hand_" + s] = ((h + t) / 2, False)
    meshes = [o for o in objs if o.type == "MESH"]
    zmin = min(p.z for o in meshes for p in world_verts(o, deps)) if meshes else 0.0
    for s in ("L", "R"):
        if bone(f"DEF-foot.{s}"):
            h = bone(f"DEF-foot.{s}")[0]
            lm["foot_" + s] = (Vector((h.x, h.y, zmin)), False)
    # hems: lowest visible point of each garment inside the torso band (|x| < 0.6 shoulder half-width)
    if bone("DEF-upper_arm.L") and bone("DEF-upper_arm.R"):
        sx = (bone("DEF-upper_arm.L")[0].x, bone("DEF-upper_arm.R")[0].x)
        cx, half = (sx[0] + sx[1]) / 2, abs(sx[0] - sx[1]) / 2
        items = {}
        for o in meshes:
            r = regions.get(o.name, "")
            if r.startswith("garment:"):
                items.setdefault(r[8:], []).append(o)
        for item, obs in sorted(items.items()):
            main = [o for o in obs if ".main" in o.name] or obs
            pts = [p for o in main for p in world_verts(o, deps) if abs(p.x - cx) < 0.6 * half]
            if not pts or min(p.z for p in pts) < zmin + 0.02:
                continue  # footwear / ground contact: covered by feet
            pts.sort(key=lambda p: p.z)
            pt = first_visible(pts[:400], proj, 0.006)
            if pt and not pt[1]:
                lm["hem_" + item] = (Vector((cx, pt[0].y, pt[0].z)), False)
    return lm


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("blend")
    ap.add_argument("index")
    ap.add_argument("out")
    ap.add_argument("--views", default="")
    ap.add_argument("--height", type=int, default=640)
    ap.add_argument("--region-map", default="")
    ap.add_argument("--prepare-only", default="")
    ap.add_argument("--hide", default="")
    a = ap.parse_args(argv)
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(a.blend))
    sc = bpy.context.scene
    if a.prepare_only:
        prefixes = [p for p in a.hide.split(",") if p]
        hidden = []
        for o in sc.objects:
            if any(o.name.startswith(p) for p in prefixes):
                o.hide_render = True
                hidden.append(o.name)
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(a.prepare_only), copy=True)
        print(json.dumps({"prepared": a.prepare_only, "hidden": hidden}))
        return
    os.makedirs(a.out, exist_ok=True)
    for o in list(sc.objects):
        if o.type in ("LIGHT", "CAMERA"):
            bpy.data.objects.remove(o, do_unlink=True)
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    root = character_root()
    pool = root.all_objects if root else sc.objects
    meshes = [o for o in pool if o.type == "MESH" and not o.hide_render and not o.name.startswith("WGT")]
    objs = renderable(root, sc)
    rules = []
    if a.region_map:
        rules = [tuple(r) for r in json.load(open(a.region_map)).get("rules", [])]
    regions = classify(objs, root, rules)
    colours = region_colours(regions)
    deps = bpy.context.evaluated_depsgraph_get()
    lo, hi = Vector((1e9,) * 3), Vector((-1e9,) * 3)
    for o in meshes:  # identical to groom_turnaround.py
        ev = o.evaluated_get(deps)
        for c in ev.bound_box:
            w = ev.matrix_world @ Vector(c)
            lo = Vector(map(min, lo, w))
            hi = Vector(map(max, hi, w))
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    idx = json.load(open(a.index))
    want = [v for v in a.views.split(",") if v]
    views = [v for v in idx["views"] if not want or v["id"] in want]
    sc.render.resolution_x, sc.render.resolution_y = a.height // 2, a.height
    sc.render.resolution_percentage = 100
    target = (lo + hi) / 2
    rig = next((o for o in pool if o.type == "ARMATURE"), None) or next(
        (o for o in sc.objects if o.type == "ARMATURE"), None)
    see_through = {o.name for o in objs if regions.get(o.name) == "glasses"}
    json.dump({"colours": {r: list(c) for r, c in sorted(colours.items())},
               "objects": dict(sorted(regions.items())),
               "skin_split": "skin pixels above the projected chin (LM_chin) -> skin_face, below -> skin_limbs"},
              open(os.path.join(a.out, "regions.json"), "w"), indent=1)
    for v in views:
        cam.data.type = "PERSP"
        d, _ = CH.place_camera(cam, target, v["yaw_deg"], v["elevation_deg"], v["focal_mm_estimate"], lo, hi, 0.5, 0.9)
        bpy.context.view_layer.update()
        deps = bpy.context.evaluated_depsgraph_get()
        proj = Projector(sc, cam, deps, see_through)
        lm3 = landmarks_3d(objs, regions, rig, deps, sc, proj, d)
        out = {}
        for k, (p, surface) in sorted(lm3.items()):
            vis = proj.visible(p) if surface else True
            out[k] = {"xy": proj.px(p), "visible": bool(vis), "world": [round(c, 5) for c in p]}
        chin = lm3.get("chin")
        info = {"view": v["id"], "camera_dir": [round(c, 5) for c in d],
                "resolution": [sc.render.resolution_x, sc.render.resolution_y],
                "chin_y_px": proj.px(chin[0])[1] if chin else None, "landmarks": out}
        json.dump(info, open(os.path.join(a.out, v["id"] + "_landmarks.json"), "w"), indent=1)
        # pass 1 without glasses (eyes and skin seen through the lenses); pass 2 with them (filled glasses mask)
        render_regions(sc, os.path.join(a.out, v["id"] + "_regions.png"), objs, regions, colours, see_through)
        if see_through:
            render_regions(sc, os.path.join(a.out, v["id"] + "_regions_glasses.png"), objs, regions, colours)
    print(json.dumps({"views": [v["id"] for v in views], "regions": sorted(colours)}))


main()
