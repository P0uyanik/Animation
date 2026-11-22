"""Hair push-out (T-194, hair_pushout.py) test (headless Blender; no rendering, writes only <out.json>).

    blender -b --factory-startup -P pipeline/charsys/tests/test_hair_pushout.py -- <out.json>

SYNTHETIC scenes only (no character data). Checks:
  1. push_chain (stage A geometry): a chain through a closed box, an open quad and an inside-out quad ends with no
     segment crossing anything and every segment length kept (1e-6 m); a chain that goes down through the opening
     of a hollow box (no face crossed) ends with no joint enclosed; a chain 75 mm deep in a box comes out on the
     side it came from; a chain that crosses nothing is returned bit for bit; applying it twice = once; the same
     result on a second run; a root embedded at rest (rest allowance) is not pushed.
  2. Scene (a rig with a head bone, a torso that moves, a fold plate, a four-bone DYN chain with a lock tube around
     it, a static cap, an open-top cup prop): stage A re-keys the chain bones in the frame where the lock is in the
     torso and leaves the keys of a free frame exactly as baked; stage B: no hair vertex inside the torso box or
     behind the fold plate after the push-out (some before); vertices that were outside do not move; the cup gets a
     closing cap that is a collider and is not rendered; two evaluations give the same hash.
  3. load_spec: defaults, inline JSON, unknown keys refused.
Exit code 1 on any failure."""
import hashlib
import json
import os
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import hair_pushout as HP  # noqa: E402

out = sys.argv[sys.argv.index("--") + 1]
R = {"checks": {}}
ok = True


def check(name, cond, **info):
    global ok
    R["checks"][name] = {"ok": bool(cond), **info}
    ok &= bool(cond)
    print(("PASS " if cond else "FAIL ") + name, json.dumps(info) if info else "")


def tree_of(V, F):
    from mathutils.bvhtree import BVHTree
    return BVHTree.FromPolygons([tuple(v) for v in V], F)


def box(lo, hi, flip=False):
    (x0, y0, z0), (x1, y1, z1) = lo, hi
    V = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    F = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    return V, [tuple(reversed(f)) for f in F] if flip else F


def crossings(tree, P):
    n = 0
    for k in range(1, len(P)):
        d = P[k] - P[k - 1]
        L = float(np.linalg.norm(d))
        if L > 0 and tree.ray_cast(Vector(P[k - 1]), Vector(d / L), L)[0] is not None:
            n += 1
    return n


def lengths(P):
    return np.linalg.norm(np.diff(P, axis=0), axis=1)


# 1. stage A geometry ----------------------------------------------------------------------------------------------
J = np.array([[0.0, 0.0, 1.0], [0.0, 0.0, 0.92], [0.0, 0.0, 0.84], [0.0, 0.0, 0.76], [0.0, 0.0, 0.68]])
CL = 0.014
cases = {
    "closed_box": tree_of(*box((-0.1, -0.1, 0.70), (0.1, 0.1, 0.80))),
    "open_quad": tree_of([(-0.2, -0.2, 0.89), (0.2, -0.2, 0.89), (0.2, 0.2, 0.87), (-0.2, 0.2, 0.87)], [(0, 1, 2, 3)]),
    "inside_out_quad": tree_of([(-0.2, -0.2, 0.89), (-0.2, 0.2, 0.87), (0.2, 0.2, 0.87), (0.2, -0.2, 0.89)], [(0, 1, 2, 3)]),
}
for name, t in cases.items():
    P, info = HP.push_chain(t, J, [0.0] * 4, CL)
    P2, info2 = HP.push_chain(t, P, [0.0] * 4, CL)
    P3, _ = HP.push_chain(t, J, [0.0] * 4, CL)
    check(f"A.{name}.no_crossing", crossings(t, J) > 0 and crossings(t, P) == 0, before=crossings(t, J), after=crossings(t, P))
    check(f"A.{name}.lengths", np.abs(lengths(P) - lengths(J)).max() < 1e-6 and info["shortened"] == 0,
          max_err=float(np.abs(lengths(P) - lengths(J)).max()))
    check(f"A.{name}.idempotent", info2["moved"] is None and np.array_equal(P2, P))
    check(f"A.{name}.deterministic", np.array_equal(P3, P))
# deep: the lock enters a box from above and its tip is 75 mm inside; it must stay above (the side it came from)
deep = tree_of(*box((-0.3, -0.3, 0.0), (0.3, 0.3, 0.815)))
P, info = HP.push_chain(deep, J, [0.0] * 4, CL)
check("A.deep.same_side", crossings(deep, P) == 0 and P[:, 2].min() > 0.815, min_z=float(P[:, 2].min()))
# opening: a hollow box (no top face, like a blouse over a masked torso); the lock goes down through the opening
hv, hf = box((-0.1, -0.1, 0.40), (0.1, 0.1, 0.86))
hollow = tree_of(hv, hf[:1] + hf[2:])  # face 1 is the top
P, info = HP.push_chain(hollow, J, [0.0] * 4, CL)
inside_before = sum(HP.enclosed(hollow, j) for j in J[1:])
inside_after = sum(HP.enclosed(hollow, p) for p in P[1:])
check("A.opening.enclosed_pushed", inside_before > 0 and inside_after == 0 and info["enclosed"] > 0
      and np.abs(lengths(P) - lengths(J)).max() < 1e-6, before=int(inside_before), after=int(inside_after),
      enclosed=info["enclosed"], left=info["enclosed_left"])
# nothing crossed: bit for bit
far = tree_of(*box((1.0, 1.0, 0.0), (1.2, 1.2, 0.2)))
P, info = HP.push_chain(far, J, [0.0] * 4, CL)
check("A.free_chain_bit_identical", info["moved"] is None and np.array_equal(P, J) and P is not J)
# root embedded at rest: the head (a box around the root) is crossed by segment 0 at rest; allowed
head = tree_of(*box((-0.05, -0.05, 0.95), (0.05, 0.05, 1.05)))
allow = HP.rest_allowance(head, J)
P, info = HP.push_chain(head, J, allow, CL)
check("A.rest_allowance", allow[0] > 0.04 and allow[1] == 0.0 and info["moved"] is None, allow=allow)

# 2. scene --------------------------------------------------------------------------------------------------------
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
arm = bpy.data.armatures.new("rig")
rig = bpy.data.objects.new("rig", arm)
sc.collection.objects.link(rig)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode="EDIT")
eb = arm.edit_bones
hb = eb.new("head")
hb.head, hb.tail = (0, 0, 1.0), (0, 0, 1.2)
tb = eb.new("torso")
tb.head, tb.tail = (0, 0, 0.0), (0, 0, 0.1)
fb = eb.new("fold")
fb.head, fb.tail = (0, 0, 0.0), (0, 0, 0.1)
prev = hb
names = []
for k in range(4):
    b = eb.new(f"DYN-lock.{k}")
    b.head, b.tail = (0.0, 0.0, 1.0 - 0.08 * k), (0.0, 0.0, 0.92 - 0.08 * k)
    b.parent = prev
    b.use_connect = k > 0
    prev = b
    names.append(b.name)
bpy.ops.object.mode_set(mode="OBJECT")
rig["ps_dynamics"] = json.dumps({"chains": [{"name": "lock", "bones": names}], "colliders": []})


def skinned(name, V, F, groups):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in V], [], F)
    o = bpy.data.objects.new(name, me)
    sc.collection.objects.link(o)
    o.parent = rig
    for g, (idx, w) in groups.items():
        vg = o.vertex_groups.get(g) or o.vertex_groups.new(name=g)
        for i, wi in zip(idx, w):
            vg.add([int(i)], float(wi), "REPLACE")
    m = o.modifiers.new("Armature", "ARMATURE")
    m.object = rig
    return o


# torso: a closed box far below at rest; the "torso" bone lifts it to z 0.70-0.80 in frame 1
tv, tf = box((-0.1, -0.1, -0.60), (0.1, 0.1, -0.50))
torso = skinned("body_torso", tv, tf, {"torso": (range(8), [1.0] * 8)})
# fold: an open plate behind the cap at rest (x = -0.15); the "fold" bone moves it to x = -0.075 in frame 1
fv = [(-0.15, -0.1, 1.02), (-0.15, 0.1, 1.02), (-0.15, 0.1, 1.12), (-0.15, -0.1, 1.12)]
fold = skinned("body_fold", fv, [(0, 1, 2, 3)], {"fold": (range(4), [1.0] * 4)})
# lock tube: rings of 8 vertices, radius 20 mm, along the chain; weights on the bone of the ring's segment
rings, F, wts = [], [], {n: ([], []) for n in names}
for r in range(17):
    z = 1.0 - 0.32 * r / 16
    for s in range(8):
        a = 2 * np.pi * s / 8
        rings.append((0.02 * np.cos(a), 0.02 * np.sin(a), z))
        b = min(3, int((1.0 - z) / 0.08 + 1e-9)) if r > 0 else 0
        wts[names[b]][0].append(len(rings) - 1)
        wts[names[b]][1].append(1.0)
for r in range(16):
    for s in range(8):
        a0, a1 = r * 8 + s, r * 8 + (s + 1) % 8
        F.append((a0, a1, a1 + 8, a0 + 8))
lock = skinned("hair_lock", rings, F, wts)
# head: a closed box weighted to the head bone (x -0.06 .. 0.06); cap: a static patch on its back (x -0.065 .. -0.105)
hv, hf = box((-0.06, -0.08, 0.99), (0.06, 0.08, 1.18))
headm = skinned("body_head", hv, hf, {"head": (range(8), [1.0] * 8)})
cv = [(-0.065 - 0.01 * i, -0.04 + 0.02 * j, 1.04 + 0.02 * k) for i in range(5) for j in range(5) for k in range(4)]
cap = skinned("hair_cap", cv, [], {"head": (range(len(cv)), [1.0] * len(cv))})
# cup prop: open-top cylinder with a solidify wall
bpy.ops.mesh.primitive_cylinder_add(radius=0.04, depth=0.1, location=(0.5, 0, 0.05))
cup = bpy.context.object
cup.name = "prop.cup"
import bmesh  # noqa: E402
bm = bmesh.new()
bm.from_mesh(cup.data)
bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.normal.z > 0.9], context="FACES_ONLY")
bm.to_mesh(cup.data)
bm.free()
cup.modifiers.new("wall", "SOLIDIFY").thickness = 0.004

coll = bpy.data.collections.new("ch")
for o in (rig, torso, fold, lock, cap, headm):
    coll.objects.link(o)
pbs = {pb.name: pb for pb in rig.pose.bones}
for pb in pbs.values():
    pb.rotation_mode = "QUATERNION"
states = {"ch": {"rig": rig, "bones": [(i, pbs[n]) for i, n in enumerate(["head", "torso", "fold"] + names)],
                 "ov": coll, "head_bone": "head"}}


def key_bone(pb, P, Pp, frame):  # as shot_render._key_bone
    if pb.parent is None:
        basis = pb.bone.matrix_local.inverted() @ P
    else:
        basis = (pb.parent.bone.matrix_local.inverted() @ pb.bone.matrix_local).inverted() @ Pp.inverted() @ P
    loc, rot, sca = basis.decompose()
    pb.location, pb.rotation_quaternion, pb.scale = loc, rot, sca
    for path in ("location", "rotation_quaternion", "scale"):
        pb.keyframe_insert(path, frame=frame, group=pb.name)


po = HP.PushOut(sc, HP.load_spec("on"), states, {"cup": cup}, [])
check("B.cup_cap", len(po.caps) == 1 and po.caps[0].hide_render and po.caps[0] in po.colliders,
      caps=[c.name for c in po.caps])
# frame 1: torso up into the lock, fold onto the cap; frame 2: everything at rest
for f, (tz, fx) in ((1, (1.30, 0.07)), (2, (0.0, 0.0))):
    for pb in pbs.values():
        pb.location, pb.rotation_quaternion, pb.scale = (0, 0, 0), (1, 0, 0, 0), (1, 1, 1)
    pbs["torso"].location = (0, tz, 0)  # bone local Y = world Z for a bone pointing up
    pbs["fold"].location = (fx, 0, 0)  # bone local X = world X
    for pb in pbs.values():
        for path in ("location", "rotation_quaternion", "scale"):
            pb.keyframe_insert(path, frame=f)
baked = {}
before = {}
for f in (1, 2):
    sc.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get()
    e = lock.evaluated_get(dg)
    before[f] = np.array([e.matrix_world @ v.co for v in e.to_mesh().vertices])
    e.to_mesh_clear()
    baked[f] = {n: tuple(pbs[n].rotation_quaternion) for n in names}
    rk = po.frame(f, key_bone)
    if f == 1:
        check("A.scene.rekeyed_in_contact", len(rk) > 0 and po.report["frames"][1]["ch"]["chains_pushed"] == 1,
              report=po.report["frames"][1]["ch"])
    else:
        sc.frame_set(2)
        after = {n: tuple(pbs[n].rotation_quaternion) for n in names}
        check("A.scene.free_frame_untouched", len(rk) == 0 and after == baked[2])
po.install()
check("B.installed", all(any(m.type == "NODES" for m in o.modifiers) for o in (lock, cap))
      and all(px.hide_render for _o, px in states["ch"]["proxies"]))


def eval_points(o, f):
    sc.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get()
    e = o.evaluated_get(dg)
    me = e.to_mesh()
    P = np.array([e.matrix_world @ v.co for v in me.vertices])
    e.to_mesh_clear()
    return P


def inside_box(P, lo, hi, m=0.0):
    return int(np.all((P > np.array(lo) + m) & (P < np.array(hi) - m), axis=1).sum())


TLO, THI = (-0.1, -0.1, 0.70), (0.1, 0.1, 0.80)
L1 = eval_points(lock, 1)
C1 = eval_points(cap, 1)
cap_rest = np.array([tuple(v) for v in cv])
check("B.lock_out_of_torso", inside_box(before[1], TLO, THI) > 0 and inside_box(L1, TLO, THI, -0.0005) == 0,
      before=inside_box(before[1], TLO, THI), after=inside_box(L1, TLO, THI, -0.0005))
behind = lambda P: int(((P[:, 0] > -0.0805) & (P[:, 0] < -0.06) & (np.abs(P[:, 1]) < 0.1) & (P[:, 2] > 1.02) & (P[:, 2] < 1.12)).sum())  # noqa: E731
check("B.cap_out_of_fold", behind(cap_rest) > 0 and behind(C1) == 0, before=behind(cap_rest), after=behind(C1))
C2 = eval_points(cap, 2)
L2 = eval_points(lock, 2)
check("B.outside_untouched", np.allclose(C2, cap_rest, atol=1e-6) and np.allclose(L2, before[2], atol=1e-6),
      cap_max=float(np.abs(C2 - cap_rest).max()), lock_max=float(np.abs(L2 - before[2]).max()))
h1 = hashlib.sha256(np.round(eval_points(lock, 1), 7).tobytes() + np.round(eval_points(cap, 1), 7).tobytes()).hexdigest()
eval_points(lock, 2)
h2 = hashlib.sha256(np.round(eval_points(lock, 1), 7).tobytes() + np.round(eval_points(cap, 1), 7).tobytes()).hexdigest()
check("B.deterministic", h1 == h2, sha256=h1)

# 3. spec ---------------------------------------------------------------------------------------------------------
check("spec.defaults", HP.load_spec("on") == HP.DEFAULTS and HP.load_spec(None) == HP.DEFAULTS)
check("spec.inline", HP.load_spec('{"margin_m": 0.004}')["margin_m"] == 0.004)
try:
    HP.load_spec('{"margin": 1}')
    check("spec.unknown_refused", False)
except ValueError:
    check("spec.unknown_refused", True)

R["ok"] = ok
json.dump(R, open(out, "w"), indent=1)
print("hair push-out test:", "OK" if ok else "FAILED")
sys.exit(0 if ok else 1)
