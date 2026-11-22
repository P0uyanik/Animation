"""T-211 probe E (read-only): are all drivers in a master Blender "simple expressions" (they then evaluate with Python
auto-exec off, as in our headless --factory-startup runs), and do L/R key vertex groups work as a split?
blender -b --factory-startup -P driver_probe.py -- <master.blend>"""
import json, sys, bpy, numpy as np
bpy.ops.wm.open_mainfile(filepath=sys.argv[sys.argv.index("--") + 1])
kinds, bad = {}, []
for idb in list(bpy.data.objects) + list(bpy.data.shape_keys):
    ad = idb.animation_data
    for f in (ad.drivers if ad else []):
        d = f.driver
        k = d.type if d.type != "SCRIPTED" else ("SCRIPTED_simple" if d.is_simple_expression else "SCRIPTED_python")
        kinds[k] = kinds.get(k, 0) + 1
        if k == "SCRIPTED_python":
            bad.append(d.expression[:60])
out = {"driver_kinds": kinds, "python_expressions": bad[:5]}
# key_block.vertex_group: MouthSmile limited to the left side by a vertex group, then "new shape from mix"
skin = bpy.data.objects["body_skin"]; kb = skin.data.shape_keys.key_blocks
n = len(skin.data.vertices); co = np.empty(n * 3); skin.data.vertices.foreach_get("co", co); x = co[0::3]
vg = skin.vertex_groups.new(name="t211_side_L")
w = np.clip(0.5 + x / 0.02, 0, 1)  # +-10 mm midline blend
for i in np.nonzero(w > 0)[0]:
    vg.add([int(i)], float(w[i]), "REPLACE")
skin.shape_key_add(name="t211_check")  # dummy to keep indices
for k in kb:
    k.mute = False
smile = kb["MouthSmile"]; smile.vertex_group = vg.name
ad = skin.data.shape_keys.animation_data
for f in ad.drivers:
    f.mute = True
for k in kb[1:]:
    k.value = 0.0
smile.value = 1.0
newk = skin.shape_key_add(name="MouthSmile.L_from_mix", from_mix=True)
a = np.empty(n * 3); newk.data.foreach_get("co", a); b = np.empty(n * 3); kb[0].data.foreach_get("co", b)
s = np.empty(n * 3); smile.data.foreach_get("co", s)
d_new = (a - b).reshape(n, 3); d_full = (s - b).reshape(n, 3)
right = x < -0.01
out["vertex_group_split"] = {"left_share_of_motion": round(float(np.abs(d_new).sum() / max(np.abs(d_full).sum(), 1e-12)), 3),
                             "right_side_max_mm": round(float(np.abs(d_new[right]).max() * 1000), 4),
                             "exact_vs_weight_max_err_mm": round(float(np.abs(d_new - d_full * w[:, None]).max() * 1000), 5)}
print("OUT", json.dumps(out))
