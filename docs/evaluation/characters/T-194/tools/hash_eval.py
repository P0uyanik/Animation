"""T-194: evaluated-geometry hashes and the stage B cost of a shot.blend (shot_render.py, with or without
--hair-pushout). No rendering.

    python3 tools/bpy_blender.py -b --factory-startup -P hash_eval.py -- <shot.blend> <out.json> --frames=a,b,c [--time]

Per frame: SHA-256 over the evaluated world-space vertex positions (float32) of every mesh object, in name order
("all"), and of the hair objects only ("hair"). Also the sorted object names and the pose of every bone (so "no flag =
identical" compares objects, keys and geometry). --time: per frame, the seconds to evaluate every hair object with
the push-out modifier (stage B) and with it disabled (median of 3), so the stage B cost per frame is the difference."""
import hashlib
import json
import statistics
import sys
import time

import bpy
import numpy as np

argv = sys.argv[sys.argv.index("--") + 1:]
BLEND, OUT = argv[0], argv[1]
opts = dict(a[2:].split("=", 1) if "=" in a else (a[2:], "1") for a in argv[2:])
frames = [int(x) for x in opts.get("frames", "1").split(",")]
bpy.ops.wm.open_mainfile(filepath=BLEND)
sc = bpy.context.scene
meshes = sorted((o for o in sc.objects if o.type == "MESH"), key=lambda o: o.name)
hair = [o for o in meshes if o.name.startswith("hair_")]
rigs = sorted((o for o in sc.objects if o.type == "ARMATURE"), key=lambda o: o.name)


def digest(objs, deps):
    h = hashlib.sha256()
    for o in objs:
        e = o.evaluated_get(deps)
        me = e.to_mesh()
        co = np.empty(len(me.vertices) * 3)
        me.vertices.foreach_get("co", co)
        M = np.array(e.matrix_world)
        h.update(o.name.encode())
        h.update((co.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3]).astype(np.float32).tobytes())
        e.to_mesh_clear()
    return h.hexdigest()


def eval_hair():
    """Seconds for Blender to re-evaluate every hair object (armature + modifiers) at the current frame."""
    for o in hair:
        o.update_tag()
    t = time.perf_counter()
    bpy.context.view_layer.update()
    return time.perf_counter() - t


out = {"blend": BLEND, "objects": [o.name for o in sorted(sc.objects, key=lambda o: o.name)], "frames": {}}
mods = [m for o in hair for m in o.modifiers if m.name.startswith("ps_pushout")]
for f in frames:
    sc.frame_set(f)
    deps = bpy.context.evaluated_depsgraph_get()
    hp = hashlib.sha256()
    for r in rigs:
        for pb in r.pose.bones:
            hp.update(np.array(pb.matrix, dtype=np.float32).tobytes())
    row = {"all": digest(meshes, deps), "hair": digest(hair, deps), "pose": hp.hexdigest()}
    if "time" in opts:
        res = {}
        for label, on in (("with_stage_b", True), ("without_stage_b", False)):
            for m in mods:
                m.show_viewport = on
            ts = []
            bpy.context.view_layer.update()
            for _ in range(3):
                ts.append(eval_hair())
            res[label] = round(statistics.median(ts), 3)
        for m in mods:
            m.show_viewport = True
        row["hair_eval_s"] = res
    out["frames"][f] = row
    print("[hash_eval]", f, json.dumps(row), flush=True)
json.dump(out, open(OUT, "w"), indent=1)
