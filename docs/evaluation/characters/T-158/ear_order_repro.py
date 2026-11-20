"""T-158 investigation: rebuild a published master's ears (face_generic.build_ears steps, location/rotation read
from the master) from create_uvsphere with a chosen edge/face order, and report Y/n for a match with the published
ear at the 0.1 mm / 0.01 mm / 1e-7 m grids. Variants: natural (live order), rebuild, rebuild_desc, pydata, sortonly,
lowhigh, highlow (canonical orders, all miss boy 2.2.0 at 0.01 mm), table<k> (replay a recorded natural run).

    blender -b --factory-startup -P ear_order_repro.py -- <master.blend> <variant> <rx,ry,rz>
"""
import sys, math, hashlib; import os as _os; sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..', '..', '..', 'pipeline', 'charsys'))
import bpy, bmesh, numpy as np
import os
S = os.environ.get('T158_SCRATCH', '.')  # folder with n3216_<k>.json recordings (variant table<k>)
from mathutils import Vector
import geom as G
args=sys.argv[sys.argv.index('--')+1:]; pub, variant = args[0], args[1]
bpy.ops.wm.open_mainfile(filepath=pub)
P={n:bpy.data.objects[n] for n in ("ear.L","ear.R")}
pubco={n:np.array([tuple(v.co) for v in o.data.vertices]) for n,o in P.items()}
loc={n:(tuple(o.location),tuple(o.rotation_euler)) for n,o in P.items()}
rad=tuple(float(x) for x in args[2].split(','))
C=bpy.context.scene.collection
def sphere(name):
    bm=bmesh.new(); bmesh.ops.create_uvsphere(bm,u_segments=32,v_segments=16,radius=1.0)
    for v in bm.verts: v.co=Vector((v.co.x*rad[0],v.co.y*rad[1],v.co.z*rad[2]))
    bm.verts.index_update()
    if variant=="rebuild":
        co=[v.co.copy() for v in bm.verts]; faces=sorted(tuple(v.index for v in f.verts) for f in bm.faces); bm.free(); bm=bmesh.new(); vs=[bm.verts.new(c) for c in co]
        for f in faces: bm.faces.new([vs[i] for i in f])
    elif variant=="rebuild_desc":
        co=[v.co.copy() for v in bm.verts]; faces=sorted((tuple(v.index for v in f.verts) for f in bm.faces), reverse=True); bm.free(); bm=bmesh.new(); vs=[bm.verts.new(c) for c in co]
        for f in faces: bm.faces.new([vs[i] for i in f])
    elif variant in ("sortonly","lowhigh","highlow"):
        n=len(bm.verts)
        def key(e):
            k=0
            for i in sorted(v.index for v in e.verts): k=k*n+i
            return k
        if variant=="sortonly":
            bm.edges.sort(key=key); bm.faces.sort(key=key)
        else:
            co=[v.co.copy() for v in bm.verts]; faces=sorted(tuple(v.index for v in f.verts) for f in bm.faces)
            edges=sorted(tuple(sorted(v.index for v in e.verts)) for e in bm.edges); bm.free(); bm=bmesh.new(); vs=[bm.verts.new(c) for c in co]
            for a,b in edges: bm.edges.new((vs[a],vs[b]) if variant=="lowhigh" else (vs[b],vs[a]))
            for f in faces: bm.faces.new([vs[i] for i in f])
    elif variant.startswith("table"):
        import json
        T=json.load(open(S+"/n3216_%s.json"%variant[5:]))
        co=[v.co.copy() for v in bm.verts]; bm.free(); bm=bmesh.new(); vs=[bm.verts.new(c) for c in co]
        for a,b in T["E"]: bm.edges.new((vs[a],vs[b]))
        for f in T["F"]: bm.faces.new([vs[i] for i in f])
    elif variant=="pydata":
        co=[v.co.copy() for v in bm.verts]; faces=sorted(tuple(v.index for v in f.verts) for f in bm.faces); bm.free()
        me=bpy.data.meshes.new(name); me.from_pydata(co,[],faces); me.shade_smooth(); ob=bpy.data.objects.new(name,me); C.objects.link(ob); return ob
    me=bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); me.shade_smooth(); ob=bpy.data.objects.new(name,me); C.objects.link(ob); return ob
res=[]
for n,sx in (("ear.L",1),("ear.R",-1)):
    e=sphere("x"+n); (x,y,z),rot=loc[n]; e.location=(x,y,z); e.rotation_euler=rot; bpy.context.view_layer.update()
    bowl=Vector((x+sx*rad[0]*0.9, y-rad[1]*0.25, z)); G.brush(e,bowl,rad[2]*0.7,(-sx*rad[0]*0.5, rad[1]*0.12, 0))
    G.add_mod(e,"SUBSURF",levels=1,render_levels=2); G.apply_mods(e)
    co=np.array([tuple(v.co) for v in e.data.vertices])
    def q(c,g): s=c/g; q=(np.sign(s)*np.floor(np.abs(s)+0.5)).astype(np.int64); return q[np.lexsort(q.T[::-1])]
    m=[bool(np.array_equal(q(co,g),q(pubco[n],g))) for g in (1e-4,1e-5,1e-7)]
    res.append(f"{n}:{''.join('Y' if v else 'n' for v in m)}")
print("RES",variant," ".join(res))
