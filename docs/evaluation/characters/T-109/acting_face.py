"""T-109 acting-frame face crops (headless Blender; read-only on the inputs). Character-independent.

    blender -b --factory-startup -P docs/evaluation/characters/T-109/acting_face.py -- <job.json>

job.json: {"blend": <run_shot shot.blend>, "frame": N, "out": dir, "samples": 16, "px": 360, "yaw_deg": 0,
           "variants": [{"tag": "as_played"}, {"tag": "SmileOpen", "swap": {"Smile": "SmileOpen"}}]}
Renders the shot's own frame (its lights, world and the baked animation) through a face camera: 70 mm, aimed at the
eye midpoint along the face's forward direction (the eyes' -y axes), yaw_deg turned about the vertical. A variant's
"swap" moves the baked weight of one preset shape key to another at that frame on every face mesh (both keys' F-curves
are muted, the source and its in-betweens set to 0, the target to the source's weight), to show a library preset in
the same acting pose (the jaw bone keeps its baked angle); "set": {key: weight} sets a preset key's weight instead. Hair stays; fur is hidden as in the review renders."""
import json
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector


def _fcurves(idb):
    ad = idb.animation_data
    if not ad or not ad.action:
        return []
    fcs = list(getattr(ad.action, "fcurves", []) or [])
    for layer in getattr(ad.action, "layers", []) or []:  # slotted actions (Blender 4.4+)
        for strip in layer.strips:
            for bag in strip.channelbags:
                fcs += list(bag.fcurves)
    return fcs


def swap_keys(objs, src, dst):
    """Moves the evaluated weight of shape key src to dst on every mesh that has both. Returns the weight moved."""
    moved = 0.0
    for o in objs:
        sk = o.data.shape_keys if o.type == "MESH" else None
        if sk is None or src not in sk.key_blocks or dst not in sk.key_blocks:
            continue
        v = sk.key_blocks[src].value
        names = [k.name for k in sk.key_blocks if k.name == src or k.name.startswith(src + "@")
                 or k.name == dst or k.name.startswith(dst + "@")]
        for fc in _fcurves(sk):
            if any(fc.data_path == f'key_blocks["{n}"].value' for n in names):
                fc.mute = True
        for n in names:
            sk.key_blocks[n].value = 0.0
        sk.key_blocks[dst].value = v
        moved = max(moved, v)
    return moved


def main():
    job = json.load(open(sys.argv[sys.argv.index("--") + 1]))
    out = os.path.abspath(job["out"])
    os.makedirs(out, exist_ok=True)
    result = {"job": job, "blender": bpy.app.version_string, "variants": {}}
    for var in job.get("variants", [{"tag": "as_played"}]):
        bpy.ops.wm.open_mainfile(filepath=os.path.abspath(job["blend"]))
        sc = bpy.context.scene
        frame = int(job["frame"])
        sc.frame_set(frame)
        for o in sc.objects:
            if "fur" in o.name.lower():
                o.hide_render = True
        swaps = {}
        for src, dst in (var.get("swap") or {}).items():
            swaps[f"{src}->{dst}"] = round(float(swap_keys(list(sc.objects), src, dst)), 4)
        for key, w in (var.get("set") or {}).items():  # a preset weight added on top of the baked frame
            for o in sc.objects:
                sk = o.data.shape_keys if o.type == "MESH" else None
                if sk is not None and key in sk.key_blocks:
                    for fc in _fcurves(sk):
                        if fc.data_path == f'key_blocks["{key}"].value':
                            fc.mute = True
                    sk.key_blocks[key].value = float(w)
            swaps[f"set {key}"] = float(w)
        bpy.context.view_layer.update()
        eyes = [o for o in sc.objects if o.type == "MESH" and o.name.split(".")[0].endswith("eye") and o.name[-2:] in (".L", ".R")]
        eyes = [o for o in eyes if not o.name.startswith("WGT")][:2]
        dg = bpy.context.evaluated_depsgraph_get()
        mids = [o.evaluated_get(dg).matrix_world.translation for o in eyes]
        c = sum(mids, Vector()) / len(mids)
        fwd = sum(((o.evaluated_get(dg).matrix_world.to_3x3() @ Vector((0, -1, 0))).normalized() for o in eyes), Vector())
        if job.get("follow_pitch"):  # aim along the head bone's forward (its rest axis that points to the face)
            rig = next(o for o in sc.objects if o.type == "ARMATURE" and job.get("head_bone", "DEF-spine.006") in o.pose.bones)
            pb = rig.pose.bones[job.get("head_bone", "DEF-spine.006")]
            ax = max((Vector(v) for v in ((1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1))),
                     key=lambda v: -(pb.bone.matrix_local.to_3x3() @ v).y)  # rest: the face looks along -y
            fwd = (rig.matrix_world.to_3x3() @ pb.matrix.to_3x3() @ ax).normalized()
        else:  # level camera
            fwd.z = 0.0
        fwd.normalize()
        d = Matrix.Rotation(math.radians(job.get("yaw_deg", 0.0)), 3, "Z") @ fwd
        d = (d + Vector((0, 0, math.sin(math.radians(6.0))))).normalized()
        if job.get("follow_pitch"):
            target = c + (Matrix.Rotation(0, 3, "Z") @ Vector((0, 0, -0.04)))
        fh = float(job.get("frame_height_m", 0.3))
        cam = bpy.data.objects.new("T109FaceCam", bpy.data.cameras.new("T109FaceCam"))
        sc.collection.objects.link(cam)
        cam.data.lens, cam.data.sensor_fit, cam.data.sensor_height, cam.data.clip_start = 70.0, "VERTICAL", 36.0, 0.01
        fov = 2 * math.atan(18.0 / 70.0)
        target = target if job.get("follow_pitch") else c + Vector((0, 0, -0.04))
        cam.location = target + d * (fh / 2 / math.tan(fov / 2))
        cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        sc.camera = cam
        sc.render.engine = "CYCLES"
        sc.cycles.samples = int(job.get("samples", 16))
        sc.cycles.device = "CPU"
        sc.cycles.seed = 0
        sc.render.resolution_x = sc.render.resolution_y = int(job.get("px", 360))
        sc.render.resolution_percentage = 100
        sc.render.image_settings.file_format = "PNG"
        sc.render.filepath = os.path.join(out, f"{var['tag']}.png")
        bpy.ops.render.render(write_still=True)
        result["variants"][var["tag"]] = {"swaps": swaps, "eye_mid": [round(v, 4) for v in c]}
        print("rendered", var["tag"], swaps, flush=True)
    json.dump(result, open(os.path.join(out, "acting_face.json"), "w"), indent=1)


main()
