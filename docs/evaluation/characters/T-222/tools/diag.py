"""Dev: per-vertex off/on depths at one frame for chosen garment objects (contact_audit Surfaces, solid role)."""
import sys, json
import numpy as np
import bpy
sys.path.insert(0, "/home/user/Animation/pipeline/production"); sys.path.insert(0, "/home/user/Animation/pipeline/charsys")
import contact_audit as CA
a = sys.argv[sys.argv.index("--") + 1:]
blend, frame, names = a[0], int(a[1]), a[2].split(",")
bpy.ops.wm.open_mainfile(filepath=blend)
C = CA.characters(bpy, "/home/user/Animation/pipeline/charsys/rig_profiles/humanoid_rigify.json")
res = {}
def run(tag):
    sc = bpy.context.scene; sc.frame_set(frame); deps = bpy.context.evaluated_depsgraph_get()
    for n, c in C.items():
        S = CA.Surfaces([(f"{n}:body:{o.name}", o) for o in c["solid"]], deps, closed=True)
        for o, P in zip(c["garment"], CA.points(c["garment"], deps)):
            if o.name not in names: continue
            d = np.zeros(len(P)); lab = [None]*len(P)
            for i in S.near(P):
                d[i], lab[i], _ = S.depth(P[i])
            res.setdefault(o.name, {})[tag] = (P, d, lab)
run("on")
for o in bpy.data.objects:
    m = o.modifiers.get("ps_garment_pushout")
    if m: m.show_viewport = False
run("off")
for nm, r in res.items():
    Pn, dn, ln = r["on"]; Pf, df, lf = r["off"]
    mv = np.linalg.norm(Pn - Pf, axis=1)
    print(nm, "inside>1mm off", int((df > 1e-3).sum()), "on", int((dn > 1e-3).sum()), "moved", int((mv > 1e-4).sum()), "max move mm", round(mv.max()*1e3,1))
    bo = bpy.data.objects.get("ps_garment_pushout.base." + nm)
    c0 = np.zeros(len(Pn))
    if bo: bo.data.attributes["ps_rest_clearance"].data.foreach_get("value", c0) if len(bo.data.vertices) == len(c0) else None
    worst = np.argsort(-dn)[:6]
    for i in worst:
        print("   v", i, "off %.1f on %.1f move %.1f" % (df[i]*1e3, dn[i]*1e3, mv[i]*1e3), "c0 %.1f" % (c0[i]*1e3))
    newin = np.nonzero((dn > 1e-3) & (df <= 1e-3))[0]
    print("   new inside", len(newin), "their moves mm", np.round(np.sort(mv[newin])[-5:]*1e3,1))
