"""T-222 garment push-out (pipeline/charsys/garment_pushout.py): synthetic scene, no assets.

    blender -b --factory-startup -P pipeline/charsys/tests/test_garment_pushout.py
    python3 tools/bpy_blender.py -b --factory-startup -P pipeline/charsys/tests/test_garment_pushout.py

A two-bone limb: a closed collision proxy (`ps_collision_proxy`), a masked rendered skin (not a solid) and three
garment sleeves over the joint (inner, outer, and one embedded in the body at rest), skinned to the lower bone only,
so bending the upper bone drives the body through the sleeves (the T-184 weight fault). Checks: spec parsing, roles,
rest pose unchanged, nothing inside after the push in the bent pose (and many inside before), layer order kept,
embedded vertices only back to their rest depth, the move fade, the modifier's place in the stack, determinism."""
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import garment_pushout as GP  # noqa: E402

FAILS = []
BEND = 30.0  # degrees: penetrations from 0 to the full limb


def check(cond, msg):
    print(("ok   " if cond else "FAIL ") + msg)
    if not cond:
        FAILS.append(msg)


def tube(name, r, z0, z1, seg=48, rings=40, caps=False):
    vs, fs = [], []
    for k in range(rings + 1):
        z = z0 + (z1 - z0) * k / rings
        for i in range(seg):
            a = 2 * math.pi * i / seg
            vs.append((r * math.cos(a), r * math.sin(a), z))
    for k in range(rings):
        for i in range(seg):
            a, b = k * seg + i, k * seg + (i + 1) % seg
            fs.append((a, b, b + seg, a + seg))
    if caps:
        vs += [(0, 0, z0), (0, 0, z1)]
        c0, c1 = len(vs) - 2, len(vs) - 1
        for i in range(seg):
            fs.append((c0, (i + 1) % seg, i))
            fs.append((c1, rings * seg + i, rings * seg + (i + 1) % seg))
    me = bpy.data.meshes.new(name)
    me.from_pydata(vs, [], fs)
    me.update()
    return bpy.data.objects.new(name, me)


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    col = bpy.data.collections.new("char")
    sc.collection.children.link(col)
    arm = bpy.data.armatures.new("rig")
    rig = bpy.data.objects.new("rig_x", arm)
    col.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    lo = arm.edit_bones.new("lower")
    lo.head, lo.tail = (0, 0, 0), (0, 0, 0.5)
    up = arm.edit_bones.new("upper")
    up.head, up.tail, up.parent = (0, 0, 0.5), (0, 0, 1.0), lo
    bpy.ops.object.mode_set(mode="OBJECT")

    def skin(o, rule):
        col.objects.link(o)
        o.parent = rig
        g1, g2 = o.vertex_groups.new(name="lower"), o.vertex_groups.new(name="upper")
        for v in o.data.vertices:
            w = rule(v.co.z)
            if w < 1:
                g1.add([v.index], 1 - w, "REPLACE")
            if w > 0:
                g2.add([v.index], w, "REPLACE")
        m = o.modifiers.new("Armature", "ARMATURE")
        m.object = rig
        return o
    body_rule = lambda z: min(1.0, max(0.0, (z - 0.45) / 0.1))  # noqa: E731
    proxy = skin(tube("garment.collider.body_skin", 0.05, 0.0, 1.0, caps=True), body_rule)
    proxy["ps_collision_proxy"] = True
    proxy.hide_render = True
    sk = skin(tube("body_skin", 0.05, 0.0, 1.0, caps=True), body_rule)
    sk.modifiers.new("garment_body_mask", "MASK")
    out = {"rig": rig, "col": col, "proxy": proxy}
    for nm, r in (("garment.shirt.inner", 0.052), ("garment.shirt.outer", 0.058), ("garment.shirt.embedded", 0.047)):
        g = skin(tube(nm, r, 0.3, 0.75), lambda z: 0.0)  # the lower bone only: the bent body goes through it
        g["ps_garment_item"] = "shirt"
        sw = g.modifiers.new("body_collision", "SHRINKWRAP")  # like the garment builds: after the armature
        sw.target, sw.wrap_method, sw.wrap_mode, sw.offset = proxy, "NEAREST_SURFACEPOINT", "OUTSIDE", 0.002
        sw.show_viewport = sw.show_render = False  # off here: the test measures the push-out alone
        out[nm.split(".")[-1]] = g
    return out


def world(o):
    deps = bpy.context.evaluated_depsgraph_get()
    e = o.evaluated_get(deps)
    me = e.to_mesh()
    co = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", co)
    e.to_mesh_clear()
    M = np.array(o.matrix_world)
    return co.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3]


def proxy_tree(proxy):
    deps = bpy.context.evaluated_depsgraph_get()
    e = proxy.evaluated_get(deps)
    me = e.to_mesh()
    M = e.matrix_world
    V = [M @ v.co for v in me.vertices]
    F = [tuple(p.vertices) for p in me.polygons]
    e.to_mesh_clear()
    return BVHTree.FromPolygons(V, F)


def inside(tree, p):
    odd = 0
    for d in ((0.31, 0.83, 0.46), (-0.72, 0.21, 0.66), (0.58, -0.61, 0.54), (-0.13, -0.42, -0.9), (0.9, 0.3, -0.31)):
        d = Vector(d).normalized()
        k, o = 0, Vector(p)
        while True:
            h = tree.ray_cast(o, d, 2.0)
            if h[0] is None:
                break
            k += 1
            o = h[0] + d * 1e-6
        odd += k % 2
    return odd >= 3


def depth(tree, p):
    """Signed distance to the proxy surface (negative inside)."""
    loc, _n, _i, d = tree.find_nearest(Vector(p))
    return -d if inside(tree, p) else d


def bend(rig, deg):
    pb = rig.pose.bones["upper"]
    pb.rotation_mode = "XYZ"
    pb.rotation_euler = (math.radians(deg), 0, 0)
    bpy.context.view_layer.update()


def remove_pushout(sc, names):
    for o in list(bpy.data.objects):
        if o.name.startswith(GP.PREFIX):
            bpy.data.objects.remove(o)
    for k in names:
        m = sc[k].modifiers.get(GP.PREFIX)
        if m:
            sc[k].modifiers.remove(m)


def rate_limit(sc, col, rig, names):
    """The default rate limit: a keyed bend 0 -> BEND over frames 1-10, held to 24, baked and packed."""
    import tempfile
    remove_pushout(sc, names)
    bend(rig, 0.0)
    scn = bpy.context.scene
    scn.frame_start, scn.frame_end = 1, 24
    pb = rig.pose.bones["upper"]
    for f, deg in ((1, 0.0), (10, BEND), (24, BEND)):
        pb.rotation_euler = (math.radians(deg), 0, 0)
        pb.keyframe_insert("rotation_euler", frame=f)
    gp = GP.GarmentPushOut(scn, GP.load_spec("on"), {"x": {"ov": col, "rig": rig}})
    gp.install()
    rep = gp.bake()
    check(rep is not None and rep["objects"] == 3, f"bake: {rep}")
    step = GP.DEFAULTS["max_step_m"]

    def offsets(f):
        scn.frame_set(f)
        on = {k: world(sc[k]) for k in names}
        for k in names:
            sc[k].modifiers[GP.PREFIX].show_viewport = False
        off = {k: world(sc[k]) for k in names}
        for k in names:
            sc[k].modifiers[GP.PREFIX].show_viewport = True
        return {k: on[k] - off[k] for k in names}
    seq = [offsets(f) for f in range(1, 25)]
    dmax = max(float(np.linalg.norm(b[k] - a[k], axis=1).max()) for a, b in zip(seq, seq[1:]) for k in names)
    check(dmax <= step + 1e-6, f"rate limit: largest frame-to-frame change of the push {dmax * 1e3:.3f} mm "
                               f"(step {step * 1e3} mm)")
    grown = max(float(np.linalg.norm(seq[-1][k], axis=1).max()) for k in names)
    check(grown > 5 * step, f"the push grows over the frames ({grown * 1e3:.1f} mm at frame 24)")
    path = os.path.join(tempfile.mkdtemp(), "rate.blend")
    bpy.ops.wm.save_as_mainfile(filepath=path)
    bpy.ops.wm.open_mainfile(filepath=path)
    o = bpy.data.objects["garment.shirt.inner"]
    bpy.context.scene.frame_set(17)  # a jump: only the packed bake can give the sequential state
    a = world(o)
    o.modifiers[GP.PREFIX].show_viewport = False
    b = world(o)
    d = float(np.abs((a - b) - seq[16]["inner"]).max())
    check(d < 1e-6, f"packed bake after reload, frame 17 out of order: {d * 1e3:.6f} mm from the sequential push")


def main():
    # spec
    s = GP.load_spec("on")
    check(s == GP.DEFAULTS, "load_spec('on') gives the defaults")
    try:
        GP.load_spec('{"bogus": 1}')
        check(False, "unknown spec key refused")
    except ValueError:
        check(True, "unknown spec key refused")
    check(GP.load_spec('{"margin_m": 0.003}')["margin_m"] == 0.003, "inline JSON spec")

    sc = build()
    rig, col = sc["rig"], sc["col"]
    objs = list(col.all_objects)
    check([o.name for o in GP.solids(objs, rig)] == ["garment.collider.body_skin"],
          "solids: the proxy only (masked skin and garments are not solids)")
    check([o.name for o in GP.garments(objs, rig)] == ["garment.shirt.embedded", "garment.shirt.inner",
                                                        "garment.shirt.outer"], "garments: every ps_garment_item mesh")
    check(GP.garments(objs, rig, ["pants"]) == [], "items filter")

    names = ("inner", "outer", "embedded")
    bend(rig, 0.0)
    rest0 = {k: world(sc[k]) for k in names}
    bend(rig, BEND)
    before = {k: world(sc[k]) for k in names}
    bend(rig, 0.0)

    gp = GP.GarmentPushOut(bpy.context.scene, GP.load_spec('{"max_step_m": 0}'), {"x": {"ov": col, "rig": rig}})
    gp.install()
    rep = gp.report["characters"]["x"]
    check(rep["objects"] == 3 and rep["inside_at_rest"] > 0, f"report: 3 objects, embedded vertices found ({rep})")
    for k in names:
        mods = [m.type for m in sc[k].modifiers]
        check(mods == ["ARMATURE", "SHRINKWRAP", "NODES"], f"{k}: push-out last in the stack")

    bpy.context.view_layer.update()
    for k in names:
        d = float(np.abs(world(sc[k]) - rest0[k]).max())
        check(d < 1e-6, f"rest pose unchanged: {k} max {d * 1e3:.6f} mm")

    bend(rig, BEND)
    tree = proxy_tree(sc["proxy"])
    after = {k: world(sc[k]) for k in names}
    again = {k: world(sc[k]) for k in names}
    check(all(np.array_equal(after[k], again[k]) for k in names), "deterministic: two evaluations identical")
    for k in ("inner", "outer"):
        db = np.array([depth(tree, p) for p in before[k]])
        da = np.array([depth(tree, p) for p in after[k]])
        nb, na = int((db < -0.001).sum()), int((da < -0.001).sum())
        check(nb > 100 and na <= 0.3 * nb, f"{k}: vertices > 1 mm inside the bent body {nb} -> {na}")
        shallow = (db < -0.001) & (db > -0.015)
        check(shallow.sum() > 20 and not (da[shallow] < -0.001).any(),
              f"{k}: every vertex 1-15 mm inside is out ({int(shallow.sum())})")
        # what is left is deep (past the limb's axis from the garment's side: the short way out would put the
        # cloth on the far side, which the push-out refuses)
        check(not (da < -0.001).any() or float(db[da < -0.001].max()) < -0.015, f"{k}: only deep cases left")
    mv = max(float(np.linalg.norm(after[k] - before[k], axis=1).max()) for k in names)
    check(mv <= GP.DEFAULTS["move_fade_m"][1] + 1e-6, f"no move beyond the fade end ({mv * 1e3:.1f} mm)")
    # layer order: where both sleeves were pushed, the outer one stays outside the inner one
    si = np.array([depth(tree, p) for p in after["inner"]])
    so = np.array([depth(tree, p) for p in after["outer"]])
    moved = (np.linalg.norm(after["inner"] - before["inner"], axis=1) > 1e-4) & \
            (np.linalg.norm(after["outer"] - before["outer"], axis=1) > 1e-4)
    bad = int((so[moved] < si[moved] - 1e-4).sum())
    check(moved.sum() > 50 and bad <= 0.02 * moved.sum(),
          f"layer order kept on {int(moved.sum())} pushed pairs ({bad} swapped)")
    # embedded at rest (3 mm inside): never pushed further out than its rest depth
    se = np.array([depth(tree, p) for p in after["embedded"]])
    me_ = np.linalg.norm(after["embedded"] - before["embedded"], axis=1) > 1e-4
    check(me_.sum() > 0 and float(se[me_].max()) < 0.0,
          f"embedded sleeve: {int(me_.sum())} pushed, all still embedded (max {se[me_].max() * 1e3:.2f} mm)")

    # move fade: with a tiny fade window the deep vertices are left as baked
    bend(rig, 0.0)
    remove_pushout(sc, names)
    gp2 = GP.GarmentPushOut(bpy.context.scene, GP.load_spec('{"move_fade_m": [0.002, 0.004], "max_step_m": 0}'),
                            {"x": {"ov": col, "rig": rig}})
    gp2.install()
    bend(rig, BEND)
    a2 = world(sc["inner"])
    mv2 = float(np.linalg.norm(a2 - before["inner"], axis=1).max())
    check(mv2 <= 0.004 + 1e-6, f"move fade [2, 4] mm: largest move {mv2 * 1e3:.2f} mm")
    rate_limit(sc, col, rig, names)
    print(f"test_garment_pushout: {'FAIL ' + str(len(FAILS)) if FAILS else 'PASS'}")
    sys.exit(1 if FAILS else 0)


main()
