"""Regression helper (headless Blender, read-only): where is the character's head?

    blender -b --factory-startup -P tools/regression/probe_head.py -- <master.blend> <out.json>

Character-independent: the head bone comes from the embedded spec (rig.head_bone); without one, the deform bone
with the highest head point is used. Writes {"center": [x, y, z], "length_m": L, "bone": name} in world space.
"""
import json
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.open_mainfile(filepath=argv[0])
root = next((c for c in bpy.data.collections if "ps_character_id" in c.keys()), None)
spec = {}
text = bpy.data.texts.get("ps_character_spec.json")
if text is not None:
    spec = json.loads(text.as_string())
pool = root.all_objects if root else bpy.data.objects
rigs = sorted((o for o in pool if o.type == "ARMATURE"), key=lambda o: o.name)
if not rigs:
    raise SystemExit("no armature in the character")
rig = rigs[0]
name = spec.get("rig", {}).get("head_bone", "")
bone = rig.data.bones.get(name) if name else None
if bone is None:
    deform = [b for b in rig.data.bones if b.use_deform] or list(rig.data.bones)
    bone = max(deform, key=lambda b: (rig.matrix_world @ b.head_local).z)
head = rig.matrix_world @ bone.head_local
tail = rig.matrix_world @ bone.tail_local
# The head bone runs from the neck joint up; the face centre is near its middle.
center = (head + tail) / 2
length = max((tail - head).length, 0.05)
json.dump({"bone": bone.name, "center": [round(c, 6) for c in center], "length_m": round(length, 6)},
          open(argv[1], "w"), indent=1)
