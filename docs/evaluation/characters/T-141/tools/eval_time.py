"""T-141: seconds Blender needs to re-evaluate a master after a pose change (viewport depsgraph; the felt fibres and
the hair curves are regenerated). blender -b --factory-startup -P eval_time.py -- <blend> [<blend> ...]"""
import json
import sys
import time

import bpy

out = {}
for path in sys.argv[sys.argv.index("--") + 1:]:
    bpy.ops.wm.open_mainfile(filepath=path)
    rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    bpy.context.view_layer.update()
    times = []
    for i in range(3):
        rig.location.z = 0.001 * (i + 1)  # every child is re-evaluated
        t = time.time()
        bpy.context.view_layer.update()
        times.append(round(time.time() - t, 2))
    out[path] = times
print("EVAL", json.dumps(out))
