"""Dev: apply the garment push-out to a copy of a keyed shot.blend (same rest data as shot_render builds it)."""
import json, sys, time, types
import bpy
sys.path.insert(0, "/home/user/Animation/pipeline/charsys")
import garment_pushout as GP
a = sys.argv[sys.argv.index("--") + 1:]
src, dst, spec = a[0], a[1], (a[2] if len(a) > 2 else "on")
bpy.ops.wm.open_mainfile(filepath=src)
sc = bpy.context.scene
objs = [o for o in sc.objects if o.library is None]
states = {}
for rig in [o for o in objs if o.type == "ARMATURE"]:
    kids = [o for o in objs if o.type == "MESH" and any(m.type == "ARMATURE" and m.object == rig for m in o.modifiers)]
    if kids:
        states[rig.name[4:] if rig.name.startswith("rig_") else rig.name] = {"rig": rig, "ov": types.SimpleNamespace(all_objects=kids)}
t = time.time()
gp = GP.GarmentPushOut(sc, GP.load_spec(spec), states)
t1 = time.time()
gp.install()
t2 = time.time()
gp.bake()
rep = {**gp.report, "timing": {"setup_s": round(t1 - t, 2), "install_s": round(t2 - t1, 2), "bake_s": round(time.time() - t2, 2)}}
print("[apply_gpush]", json.dumps(rep)[:3000])
bpy.ops.wm.save_as_mainfile(filepath=dst, relative_remap=True)
