"""T-155: mesh measures of third-character builds against her reference fractions (references/measurements.json,
fractions from the bun top, w01): hem, eye line, chin, boot top, figure height (03 lineup ~1.069 m) and the
eye-centre spacing / ear-centre spacing ratio (landmarks: 0.421). Used to decide whether the T-133 proposal still
improves on top of T-137 F1b (owner 2026-11-20 ~07:00Z: proposal only if it improves).

    blender -b --factory-startup -P docs/evaluation/characters/T-155/third_measure.py -- <out.json> <label>=<master.blend> ...
"""
import json
import sys

import bpy

TARGET = {"height_m": 1.069, "hem": 0.736, "eye_line": 0.282, "chin": 0.376, "boot_top": 0.859, "eye_ear_ratio": 0.421}


def zr(names):
    dg = bpy.context.evaluated_depsgraph_get()
    zs = []
    for n in names:
        o = bpy.data.objects.get(n)
        if o is None or o.type != "MESH":
            continue
        m = o.evaluated_get(dg).to_mesh()
        zs += [(o.matrix_world @ v.co).z for v in m.vertices]
    return min(zs), max(zs)


argv = sys.argv[sys.argv.index("--") + 1:]
out, res = argv[0], {"target": TARGET}
for arg in argv[1:]:
    label, blend = arg.split("=", 1)
    bpy.ops.wm.open_mainfile(filepath=blend)
    meshes = [o.name for o in bpy.data.objects if o.type == "MESH" and not o.hide_render and "collider" not in o.name]
    lo, hi = zr(meshes)
    H = hi - lo
    frac = lambda z: (hi - z) / H  # noqa: E731
    w = lambda n: bpy.data.objects[n].matrix_world.translation  # noqa: E731
    r = {"height_m": H,
         "hem": frac(zr(["garment.dress.skirt", "garment.dress.band.hem_rib"])[0]),
         "eye_line": frac((w("LM_eye_L").z + w("LM_eye_R").z) / 2),
         "chin": frac(w("LM_chin").z),
         "boot_top": frac(zr(["garment.boots.cuff.L"])[1]),
         "eye_ear_ratio": (w("LM_eye_L") - w("LM_eye_R")).length / (w("LM_ear_L") - w("LM_ear_R")).length}
    r["abs_error"] = {k: abs(r[k] - TARGET[k]) for k in TARGET}
    r["sum_fraction_error"] = sum(r["abs_error"][k] for k in ("hem", "eye_line", "chin", "boot_top", "eye_ear_ratio"))
    res[label] = r
json.dump(res, open(out, "w"), indent=1)
print(json.dumps(res, indent=1))
