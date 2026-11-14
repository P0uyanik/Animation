"""Measures a built body against spec targets (headless Blender, read-only):
    blender -b --factory-startup -P pipeline/charsys/tests/body_measure.py -- <master.blend> <out.json>
Crown height, eye-bone height, leg width between knee and ankle, hand tip height, hip and shoulder joint heights."""
import json
import sys

import bpy
import numpy as np

src, out = sys.argv[sys.argv.index("--") + 1:][:2]
bpy.ops.wm.open_mainfile(filepath=src)
rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
skin = bpy.data.objects.get("body_skin")
co = np.array([skin.matrix_world @ v.co for v in skin.data.vertices])
B = {b.name: (rig.matrix_world @ b.head_local, rig.matrix_world @ b.tail_local) for b in rig.data.bones}
hands = [o for o in bpy.data.objects if o.name.startswith("hand.")]
hz = min(min((o.matrix_world @ v.co).z for v in o.data.vertices) for o in hands)
knee, ankle = B["DEF-shin.L"][0].z, B["DEF-foot.L"][0].z
mid = (knee + ankle) / 2
legs = co[(np.abs(co[:, 2] - mid) < 0.004) & (co[:, 0] > 0.0)]
r = {"crown_m": round(float(co[:, 2].max()), 4), "eye_bone_z_m": round(float(B["DEF-eye.L"][0].z), 4),
     "eye_bone_x_m": round(float(B["DEF-eye.L"][0].x), 4), "hand_tip_z_m": round(float(hz), 4),
     "leg_width_m": round(float(legs[:, 0].max() - legs[:, 0].min()), 4), "leg_centre_x_m": round(float((legs[:, 0].max() + legs[:, 0].min()) / 2), 4),
     "shoulder_joint_z_m": round(float(B["DEF-upper_arm.L"][0].z), 4), "hip_joint_z_m": round(float(B["DEF-thigh.L"][0].z), 4),
     "knee_z_m": round(float(knee), 4), "ankle_z_m": round(float(ankle), 4), "head_width_m": round(float(np.ptp(co[co[:, 2] > B["DEF-eye.L"][0].z - 0.05][:, 0])), 4)}
json.dump(r, open(out, "w"), indent=1)
print("[body_measure]", json.dumps(r))
