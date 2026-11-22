"""T-209 probe (read-only): how far each face shape key moves the parts of the head that carry identity.

    blender -b --factory-startup -P docs/research/T-209/probes/identity_drift_probe.py -- <master.blend> <out.json> [<eye radius m>]

For the skin mesh (body_skin) and every shape key relative to Basis it reports, in millimetres:
  mouth_max    largest move within MZ (45 mm) of LM_mouth (expected motion)
  eye_max      largest move within EZ of either LM_eye centre, EZ = 1.35 x eyeball radius (lid skin; expected motion)
  ident_max    largest move of head vertices outside those zones and outside 20 mm of LM_nose
               (forehead, brow ridge, outer cheek, jaw outline, ears, cranium) -> drift candidates
  ident_p95    95th percentile of the same set
  far_max      largest move further than 2 eye radii from both eyes and 90 mm from the mouth (cranium, back of
               head, ears, neck): must be 0 for an expression
  nose_max     largest move within 8 mm of LM_nose
  width_eye / width_cheek   change of the head's front-projected width (x range) in a 6 mm band at eye
               height / halfway eye-to-chin
Opens the master read-only; writes only <out.json>."""
import json
import sys

import bpy
import numpy as np

argv = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.open_mainfile(filepath=argv[0])
out = argv[1]
EYE_R = float(argv[2]) if len(argv) > 2 else 0.048   # eyeball radius from spec.face.eyes.radius_m
EZ, MZ = 1.35 * EYE_R, 0.045

lm = {o.name[3:]: np.array(o.matrix_world.translation) for o in bpy.data.objects if o.name.startswith("LM_")}
skin = bpy.data.objects["body_skin"]
mw = np.array(skin.matrix_world)
keys = skin.data.shape_keys.key_blocks
n = len(skin.data.vertices)


def co(kb):
    a = np.empty(n * 3)
    kb.data.foreach_get("co", a)
    a = a.reshape(n, 3)
    return a @ mw[:3, :3].T + mw[:3, 3]


base = co(keys[0])
chin_z = lm["chin"][2]
eye_z = 0.5 * (lm["eye_L"][2] + lm["eye_R"][2])
head = base[:, 2] > chin_z - 0.01
d_mouth = np.linalg.norm(base - lm["mouth"], axis=1)
d_eye = np.minimum(np.linalg.norm(base - lm["eye_L"], axis=1), np.linalg.norm(base - lm["eye_R"], axis=1))
d_nose = np.linalg.norm(base - lm["nose"], axis=1)
ident = head & (d_mouth > MZ) & (d_eye > EZ) & (d_nose > 0.020)
far = head & (d_mouth > 0.090) & (d_eye > 2 * EYE_R)
band_eye = head & (np.abs(base[:, 2] - eye_z) < 0.003)
cheek_z = 0.5 * (eye_z + chin_z)
band_cheek = head & (np.abs(base[:, 2] - cheek_z) < 0.003)


def width(c, sel):
    return float(c[sel, 0].max() - c[sel, 0].min()) if sel.any() else None


rows = {}
for kb in keys[1:]:
    c = co(kb)
    d = np.linalg.norm(c - base, axis=1) * 1000.0
    rows[kb.name] = {
        "mouth_max": round(float(d[head & (d_mouth <= MZ)].max()), 2),
        "eye_max": round(float(d[head & (d_eye <= EZ)].max()), 2),
        "far_max": round(float(d[far].max()), 3),
        "nose_max": round(float(d[d_nose <= 0.008].max()), 2),
        "ident_max": round(float(d[ident].max()), 2),
        "ident_p95": round(float(np.percentile(d[ident], 95)), 3),
        "width_eye": round((width(c, band_eye) - width(base, band_eye)) * 1000.0, 2),
        "width_cheek": round((width(c, band_cheek) - width(base, band_cheek)) * 1000.0, 2),
    }
res = {"blend": argv[0], "skin_vertices": n, "head_vertices": int(head.sum()), "identity_vertices": int(ident.sum()), "far_vertices": int(far.sum()), "eye_radius_m": EYE_R,
       "head_width_eye_mm": round(width(base, band_eye) * 1000, 1), "keys": rows}
json.dump(res, open(out, "w"), indent=1)
print("T209 wrote", out, len(rows), "keys")
