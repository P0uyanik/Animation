import sys, numpy as np, bpy
from mathutils import Vector
sys.path.insert(0, "/home/user/Animation/pipeline/charsys"); sys.path.insert(0, "/home/user/Animation/pipeline/production")
import garment_pushout as GP, hair_pushout as HP, contact_audit as CA
a = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.open_mainfile(filepath=a[0]); f = int(a[1])
sc = bpy.context.scene; sc.frame_set(f)
for o in bpy.data.objects:
    m = o.modifiers.get("ps_garment_pushout")
    if m: m.show_viewport = False
bpy.context.view_layer.update(); deps = bpy.context.evaluated_depsgraph_get()
C = CA.characters(bpy, "/home/user/Animation/pipeline/charsys/rig_profiles/humanoid_rigify.json")
for spec in a[2:]:
    nm, vi = spec.split(":"); vi = int(vi)
    o = bpy.data.objects[nm]
    ch = next(n for n, c in C.items() if o in c["garment"])
    tree = HP.bvh_of(*HP.world_triangles(C[ch]["solid"], deps))
    P = CA.points([o], deps)[0][vi]
    B = CA.points([bpy.data.objects["ps_garment_pushout.base." + nm]], deps)[0][vi]
    T = CA.points([bpy.data.objects["ps_garment_pushout.tip." + nm]], deps)[0][vi]
    d = (T - B) / np.linalg.norm(T - B)
    print(nm, vi, "P", np.round(P, 3), "d", np.round(d, 2), "base-P mm", round(np.linalg.norm(B - P) * 1e3, 1))
    for sgn in (1, -1):
        t, hits = 0.0, []
        for _ in range(6):
            h = tree.ray_cast(Vector(P + sgn * d * (t + 1e-5)), Vector(sgn * d), 0.5 - t)
            if h[0] is None: break
            t += 1e-5 + h[3]; hits.append(("B" if h[1].dot(Vector(sgn * d)) > 0 else "F", round(t * 1e3, 1)))
        print("   dir", sgn, hits)
    loc, nrm, _, dist = tree.find_nearest(Vector(P)); print("   nearest", round(dist*1e3,1), "dot(n, P-loc)", round(np.dot(np.array(nrm), P-np.array(loc))*1e3,2))
    print("   wind", GP.winding_exit(tree, Vector(P), Vector(d), 0.5, 4))
