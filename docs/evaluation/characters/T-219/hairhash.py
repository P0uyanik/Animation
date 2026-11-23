"""Open a master .blend; hash hair objects: rest (original) mesh verts + curves points, and evaluated points."""
import bpy, sys, json, hashlib, numpy as np
a = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.open_mainfile(filepath=a[0])
dg = bpy.context.evaluated_depsgraph_get()
rest, ev, allm = hashlib.sha256(), hashlib.sha256(), hashlib.sha256()
n = {"mesh": 0, "curves": 0, "points": 0, "ev_points": 0}
for o in sorted(bpy.data.objects, key=lambda o: o.name):
    if o.type == "MESH":
        p = np.zeros(len(o.data.vertices) * 3, np.float32); o.data.vertices.foreach_get("co", p)
        allm.update(o.name.encode() + p.tobytes())
    if not o.name.startswith("hair_") and o.type != "CURVES":
        continue
    if o.type == "MESH":
        rest.update(o.name.encode() + p.tobytes()); n["mesh"] += 1
    if o.type == "CURVES":
        d = o.data; p = np.zeros(len(d.points) * 3, np.float32); d.points.foreach_get("position", p)
        rest.update(o.name.encode() + p.tobytes()); n["curves"] += len(d.curves); n["points"] += len(d.points)
    e = o.evaluated_get(dg).data
    if o.type == "CURVES":
        p = np.zeros(len(e.points) * 3, np.float32); e.points.foreach_get("position", p); n["ev_points"] += len(e.points)
    elif o.type == "MESH":
        p = np.zeros(len(e.vertices) * 3, np.float32); e.vertices.foreach_get("co", p)
    ev.update(o.name.encode() + p.tobytes())
out = dict(n, rest_sha=rest.hexdigest()[:16], eval_sha=ev.hexdigest()[:16], all_mesh_sha=allm.hexdigest()[:16])
print("HAIRHASH", json.dumps(out))
if len(a) > 1: json.dump(out, open(a[1], "w"), indent=1)
