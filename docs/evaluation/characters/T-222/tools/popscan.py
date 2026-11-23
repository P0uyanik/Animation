"""Dev: T-194 pop rule for garments over every frame: per character, frames where the push-out adds > 5 mm to the
largest garment vertex move (f-1 -> f). Evaluates garments with the push-out on and off."""
import json, sys, time, numpy as np, bpy
sys.path.insert(0, "/home/user/Animation/pipeline/production")
import contact_audit as CA
a = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.open_mainfile(filepath=a[0]); fa, fb = map(int, a[1].split("-"))
for o in bpy.context.scene.objects:  # only garments, their proxies and the solids are needed
    if o.type == "MESH" and o.name.startswith("hair_"):
        o.hide_viewport = True
C = CA.characters(bpy, "/home/user/Animation/pipeline/charsys/rig_profiles/humanoid_rigify.json")
prev, pops, maxadd, t0 = {}, [], {}, time.time()
for f in range(fa, fb + 1):
    bpy.context.scene.frame_set(f)
    for on in (True, False):
        for c in C.values():
            for o in c["garment"]:
                m = o.modifiers.get("ps_garment_pushout")
                if m: m.show_viewport = on
        deps = bpy.context.evaluated_depsgraph_get()
        for n, c in C.items():
            P = CA.points(c["garment"], deps)
            key = (n, on)
            if key in prev:
                j = max(float(np.linalg.norm(x - y, axis=1).max()) for x, y in zip(P, prev[key]) if len(x))
                prev[(n, on, "j")] = j
            prev[key] = P
    for n in C:
        if (n, True, "j") in prev:
            add = (prev[(n, True, "j")] - prev[(n, False, "j")]) * 1e3
            maxadd[n] = max(maxadd.get(n, 0.0), add)
            if add > 5.0:
                pops.append((f, n, round(add, 1)))
print("POPSCAN", json.dumps({"frames": [fa, fb], "pops": len(pops), "per_char": {n: sum(1 for p in pops if p[1] == n) for n in C},
                             "max_added_mm": {n: round(v, 1) for n, v in maxadd.items()}, "list": pops[:40], "s": round(time.time() - t0)}))
