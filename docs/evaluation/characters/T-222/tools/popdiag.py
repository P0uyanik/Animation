"""Dev: for frames f-1 -> f, the garment vertices whose move gains most with the push-out (on - off)."""
import sys, numpy as np, bpy
sys.path.insert(0, "/home/user/Animation/pipeline/production")
import contact_audit as CA
a = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.open_mainfile(filepath=a[0]); ch, f = a[1], int(a[2])
C = CA.characters(bpy, "/home/user/Animation/pipeline/charsys/rig_profiles/humanoid_rigify.json")
G = C[ch]["garment"]
def ev(frame, on):
    for o in G:
        m = o.modifiers.get("ps_garment_pushout")
        if m: m.show_viewport = on
    bpy.context.scene.frame_set(frame); return CA.points(G, bpy.context.evaluated_depsgraph_get())
P = {(fr, on): ev(fr, on) for fr in (f - 1, f) for on in (False, True)}
best = []
for k, o in enumerate(G):
    jon = np.linalg.norm(P[(f, True)][k] - P[(f - 1, True)][k], axis=1)
    joff = np.linalg.norm(P[(f, False)][k] - P[(f - 1, False)][k], axis=1)
    i = int(np.argmax(jon - joff))
    m0 = np.linalg.norm(P[(f - 1, True)][k][i] - P[(f - 1, False)][k][i]); m1 = np.linalg.norm(P[(f, True)][k][i] - P[(f, False)][k][i])
    best.append((jon[i] - joff[i], o.name, i, m0, m1, int(((jon - joff) > 0.005).sum())))
for b in sorted(best, reverse=True)[:6]:
    print("POP %.1f mm %s v%d push %.1f -> %.1f mm, vertices >5mm: %d" % (b[0]*1e3, b[1], b[2], b[3]*1e3, b[4]*1e3, b[5]))
