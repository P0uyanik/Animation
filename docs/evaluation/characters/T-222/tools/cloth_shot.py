"""Dev (part-B evaluation): the cloth_sim skirt prototype driven by a real shot's keyed motion inside its shot.blend.
args: <shot.blend> <out dir> <frames A-B> [--save]   (the tagged ps_cloth_sim piece of the shot; seat = the set boxes)"""
import hashlib, json, os, struct, sys, time
import numpy as np
import bpy
sys.path.insert(0, "/home/user/Animation/pipeline/charsys/cloth_sim")
import skirt as S
# evaluation only: in a shot the character's collections are library overrides (cannot link into them); the
# prototype's helpers link into the scene collection instead (same code otherwise)
_src = open(S.__file__).read().replace("piece.users_collection[0].objects.link", "bpy.context.scene.collection.objects.link")
_src = _src.replace("body.users_collection[0].objects.link", "bpy.context.scene.collection.objects.link")
exec(compile(_src, S.__file__, "exec"), S.__dict__)
_comp = S.companions
S.companions = lambda piece: [o for o in _comp(piece) if o.library is None]  # not the linked originals
a = sys.argv[sys.argv.index("--") + 1:]
blend, out, (fa, fb) = a[0], a[1], map(int, a[2].split("-"))
os.makedirs(out, exist_ok=True)
t0 = time.time()
bpy.ops.wm.open_mainfile(filepath=blend)
sc = bpy.context.scene
local = [o for o in sc.objects if o.library is None]
pieces = [o for o in local if o.type == "MESH" and o.get(S.PROP)]
assert len(pieces) == 1, [p.name for p in pieces]
piece = pieces[0]
rig = next(m.object for m in piece.modifiers if m.type == "ARMATURE")
kids = [o for o in local if o.type == "MESH" and any(m.type == "ARMATURE" and m.object == rig for m in o.modifiers)]
body = next(o for o in kids if o.name.split(".")[0] == piece["ps_weight_source"] and not o.get("ps_collision_proxy"))
st = S.settings({})
# proxy and binding at rest (action off), then the shot's keys drive the rig
ad = rig.animation_data; act, slot = ad.action, ad.action_slot
ad.action = None
saved = [(pb, pb.matrix_basis.copy()) for pb in rig.pose.bones]
for pb in rig.pose.bones: pb.matrix_basis.identity()
bpy.context.view_layer.update()
proxy = S.make_proxy(piece, st, 126)
for o in [piece] + S.companions(piece):  # shot objects are system overrides: operators need user-editable ones
    if o.override_library is not None:
        o.override_library.is_system_override = False
    if o.data.library is not None:  # linked mesh data: the bind operator refuses it; a local copy (same data)
        o.data = o.data.copy()
followers = S.bind(piece, proxy)
col = S.collider(rig, body, st["body_thickness_m"], st["friction"])
for pb, m in saved: pb.matrix_basis = m
ad.action = act; ad.action_slot = slot
boxes = [o for o in local if o.type == "MESH" and o.name.startswith("prop.") and not any(m.type == "ARMATURE" for m in o.modifiers)
         and len(o.data.vertices) == 8]
for b in boxes:
    if not any(m.type == "COLLISION" for m in b.modifiers):
        b.modifiers.new("Collision", "COLLISION")
    b.collision.cloth_friction = 20.0
keep = {rig, piece, proxy, col, *boxes}
hidden = []
for o in sc.objects:
    if o not in keep and not o.hide_viewport:
        o.hide_viewport = True; hidden.append(o)
t1 = time.time()
sc.frame_start, sc.frame_end = fa, fb
cloth = S.add_cloth(proxy, st)
cloth.point_cache.frame_start, cloth.point_cache.frame_end = fa, fb
samples = []
for f in range(fa, fb + 1):
    sc.frame_set(f)
    samples.append(S._points(proxy))
data = np.stack(samples)
pc2 = os.path.join(out, "skirt.pc2")
with open(pc2, "wb") as fh:
    fh.write(struct.pack("<12siiffi", b"POINTCACHE2\0", 1, data.shape[1], float(fa), 1.0, data.shape[0]))
    fh.write(data.astype("<f4").tobytes())
t2 = time.time()
proxy.modifiers.remove(cloth)
mc = S.replay(proxy, pc2); mc.frame_start = float(fa)
for o in hidden: o.hide_viewport = False
pen = {}
for f in sorted({fa, (fa + fb) // 2, fb, *[int(x) for x in a[3:] if x.isdigit()]}):
    sc.frame_set(f); row = {}
    for label, sim in (("cloth", True), ("skinned", False)):
        S.show(followers, sim); bpy.context.view_layer.update()
        row[label] = {k: v for k, v in S.penetration(piece, col).items() if k in ("inside_skin", "max_depth_mm", "p95_depth_mm", "hem_rise_mm")}
    S.show(followers, True)
    pen[f] = row
rep = {"blend": blend, "piece": piece.name, "frames": [fa, fb], "proxy_vertices": int(data.shape[1]),
       "boxes": [b.name for b in boxes], "sha256": hashlib.sha256(open(pc2, "rb").read()).hexdigest(),
       "seconds": {"setup": round(t1 - t0, 1), "simulate": round(t2 - t1, 1), "per_frame": round((t2 - t1) / (fb - fa + 1), 2)},
       "penetration": pen}
json.dump(rep, open(os.path.join(out, "cloth_shot.json"), "w"), indent=1)
print("[cloth_shot]", json.dumps(rep))
if "--save" in a:
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out, "shot_cloth.blend"), relative_remap=True)
