import sys, bpy, numpy as np
argv = sys.argv[sys.argv.index("--") + 1:]
blend, f0, who = argv[0], int(argv[1]), argv[2]
bpy.ops.wm.open_mainfile(filepath=blend)
sc = bpy.context.scene
hair = [o for o in sc.objects if o.type == "MESH" and o.name.startswith("hair_") and any(m.type == "ARMATURE" and who in m.object.name for m in o.modifiers)]
def pts():
    deps = bpy.context.evaluated_depsgraph_get(); out = {}
    for o in hair:
        e = o.evaluated_get(deps); me = e.to_mesh(); co = np.empty(len(me.vertices)*3); me.vertices.foreach_get("co", co)
        M = np.array(e.matrix_world); out[o.name] = co.reshape(-1,3) @ M[:3,:3].T + M[:3,3]; e.to_mesh_clear()
    return out
sc.frame_set(f0); a = pts(); sc.frame_set(f0 + 1); b = pts()
r = sorted(((float(np.linalg.norm(a[k]-b[k],axis=1).max())*1e3, k, int(np.linalg.norm(a[k]-b[k],axis=1).argmax())) for k in a), reverse=True)[:4]
print("JUMP", blend.split("/")[-2], [(round(x,1), k, i) for x, k, i in r])
