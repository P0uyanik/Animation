"""Contact audit (T-218, pipeline/production/contact_audit.py) test. Headless Blender, SYNTHETIC scenes only (no
character data, no assets, no engine); writes only into a temporary folder.

    blender -b --factory-startup -P pipeline/production/tests/test_contact_audit.py

Scene: two rigged "characters" (a, b) of boxes, a prop box and a floor box, frames 1-3.
  a: body box; a hair triangle above it that is keyed 0 / 20 / 3 mm into the body; a garment triangle keyed 10 mm
     into the body at f2; a hand box off the body axis (hand bone + a finger bone below it) keyed 8 mm into the prop
     at f2; glasses.
  b: a masked rendered body plus a hidden collision proxy (the solid); b's body overlaps a's by 50 mm and goes 5 mm
     into the floor at every frame.
Checks:
  1. Roles from metadata: hair, garment, body, solid (proxy, not the masked body), glasses, hand vertices (the hand
     bone and its child), props and set boxes (from the bake's objects).
  2. Depths per class and frame (0.1 mm): hair_own 20 / 3, garment_body 10 (a lining inside a closed hollow cage,
     outside the solid but with no free direction, is not counted: closed-solid rule), hand_prop 8,
     body_body 50 (a in b only),
     body_set 5 (b only); nothing in frames where nothing is inside; depth pops of hair_own = 2 (0 -> 20 -> 3).
  3. The largest hair vertex move per frame (70 / 17 mm) and `compare` (jump pops of a run against itself = 0).
  4. Determinism: two runs give the same rows and SHA-256; --jobs 2 (frame chunks with a warm-up frame) gives the
     same rows, vertex moves and SHA-256 as --jobs 1; --step 2 measures f1 and f3 only.
  5. Pure Python: staging (hair deeper than --staging-mm in another character's body is apart), known rules move
     entries apart, the summary's calm / snap split and the markdown.
Exit code 1 on any failure."""
import json
import os
import shutil
import subprocess
import sys
import tempfile

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(HERE, ".."))
import contact_audit as CA  # noqa: E402

FAILS = []


def check(cond, msg):
    print(("ok   " if cond else "FAIL ") + msg, flush=True)
    if not cond:
        FAILS.append(msg)


def near(a, b, tol=0.1):
    return a is not None and abs(a - b) <= tol


def box_mesh(name, centre, half):
    import bmesh
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = [c + h * 2 * x for c, h, x in zip(centre, half, v.co)]
    bm.to_mesh(me)
    bm.free()
    return me


def cage_mesh(name, centre, outer, inner):
    """A closed hollow box: outer shell, inner shell facing into the cavity (a point in the cavity is outside the
    solid but no ray of the 26 directions gets out: the T-183 "enclosed" case)."""
    import bmesh
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    for h, flip in ((outer, False), (inner, True)):
        r = bmesh.ops.create_cube(bm, size=2 * h)
        for v in r["verts"]:
            v.co = [c + x for c, x in zip(centre, v.co)]
        if flip:
            bmesh.ops.reverse_faces(bm, faces=list({f for v in r["verts"] for f in v.link_faces}))
    bm.to_mesh(me)
    bm.free()
    return me


def tri_mesh(name, centre, size=0.002, axis="z"):
    me = bpy.data.meshes.new(name)
    x, y, z = centre
    if axis == "z":
        vs = [(x - size, y - size, z), (x + size, y - size, z), (x, y + size, z)]
    else:
        vs = [(x, y - size, z - size), (x, y + size, z - size), (x, y, z + size)]
    me.from_pydata(vs, [], [(0, 1, 2)])
    return me


def rigged(name, me, rig, groups, scene):
    """groups: [(bone, vertex indices or None for all)]"""
    ob = bpy.data.objects.new(name, me)
    scene.collection.objects.link(ob)
    ob.parent = rig
    for bone, idx in groups:
        g = ob.vertex_groups.new(name=bone)
        g.add(list(range(len(me.vertices))) if idx is None else idx, 1.0, "REPLACE")
    m = ob.modifiers.new("Armature", "ARMATURE")
    m.object = rig
    return ob


def make_rig(name, bones, scene):
    arm = bpy.data.armatures.new(name)
    rig = bpy.data.objects.new(name, arm)
    scene.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    made = {}
    for bn, head, tail, parent in bones:
        eb = arm.edit_bones.new(bn)
        eb.head, eb.tail = head, tail
        if parent:
            eb.parent = made[parent]
        made[bn] = eb
    bpy.ops.object.mode_set(mode="OBJECT")
    return rig


def key(rig, bone, frame, y):
    pb = rig.pose.bones[bone]
    pb.location = (0.0, y, 0.0)  # local Y = along the bone
    pb.keyframe_insert("location", frame=frame)


def build(path, bake_path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.frame_start, sc.frame_end = 1, 3
    a = make_rig("rig_a", [("root", (0, 0, 0), (0, 0, 0.1), None),
                           ("hairb", (0, 0, 0.75), (0, 0, 0.85), "root"),       # along +Z
                           ("garm", (0.25, 0, 0.5), (0.35, 0, 0.5), "root"),    # along +X
                           ("DEF-hand.L", (0.6, 0.3, 0.5), (0.7, 0.3, 0.5), "root"),
                           ("DEF-f.L", (0.7, 0.3, 0.5), (0.75, 0.3, 0.5), "DEF-hand.L"),
                           ("lin", (-0.75, 0, 0.5), (-0.65, 0, 0.5), "root")], sc)                # along +X
    rigged("body_skin", box_mesh("body_a", (0, 0, 0.5), (0.2, 0.2, 0.2)), a, [("root", None)], sc)
    rigged("hair_a", tri_mesh("hair_a", (0, 0, 0.75)), a, [("hairb", None)], sc)
    g = rigged("garment.shirt", tri_mesh("garm_a", (0.25, 0, 0.5), axis="x"), a, [("garm", None)], sc)
    g["ps_garment_item"] = "shirt"
    hand = rigged("hand.L", box_mesh("hand_a", (0.6, 0.3, 0.5), (0.01, 0.01, 0.01)), a, [], sc)
    gh, gf = hand.vertex_groups.new(name="DEF-hand.L"), hand.vertex_groups.new(name="DEF-f.L")
    xs = [v.co.x for v in hand.data.vertices]
    gh.add([i for i, x in enumerate(xs) if x < 0.6], 1.0, "REPLACE")
    gf.add([i for i, x in enumerate(xs) if x > 0.6], 1.0, "REPLACE")
    cage = rigged("arm.cage", cage_mesh("cage_a", (-0.6, 0, 0.5), 0.05, 0.03), a, [("root", None)], sc)
    lin = rigged("garment.lining", tri_mesh("lining_a", (-0.68, 0, 0.5), axis="x"), a, [("lin", None)], sc)
    lin["ps_garment_item"] = "lining"
    rigged("glasses", tri_mesh("glasses_a", (0, -0.25, 0.6), axis="x"), a, [("root", None)], sc)
    for f, y in ((1, 0.0), (2, -0.07), (3, -0.053)):
        key(a, "hairb", f, y)
    for f, y in ((1, 0.0), (2, -0.06), (3, 0.0)):
        key(a, "garm", f, y)
    for f, y in ((1, 0.0), (2, 0.018), (3, 0.0)):
        key(a, "DEF-hand.L", f, y)
    for f, y in ((1, 0.0), (2, 0.1), (3, 0.0)):  # the lining is outside the cage at rest, in its cavity at f2
        key(a, "lin", f, y)
    b = make_rig("rig_b", [("root", (0.35, 0, 0), (0.35, 0, 0.1), None)], sc)
    bb = rigged("body_skin", box_mesh("body_b", (0.35, 0, 0.195), (0.2, 0.25, 0.2)), b, [("root", None)], sc)
    keep = bb.vertex_groups.new(name="keep")
    keep.add(list(range(8)), 1.0, "REPLACE")
    mk = bb.modifiers.new("mask", "MASK")
    mk.vertex_group = "keep"
    px = rigged("garment.collider.body_skin", box_mesh("proxy_b", (0.35, 0, 0.195), (0.2, 0.25, 0.2)), b,
                [("root", None)], sc)
    px["ps_collision_proxy"] = 1
    px.hide_render = True
    for n, c, h in (("prop.box", (0.65, 0.3, 0.5), (0.03, 0.03, 0.03)), ("prop.floor", (0, 0, -0.05), (2, 2, 0.05))):
        ob = bpy.data.objects.new(n, box_mesh(n, c, h))
        sc.collection.objects.link(ob)
    bpy.ops.wm.save_as_mainfile(filepath=path)
    json.dump({"objects": [{"name": "floor", "kind": "box"}], "characters": []}, open(bake_path, "w"))


def audit(blend, bake, out, *extra):
    cmd = [sys.executable if os.path.basename(sys.executable).startswith("python") else "python3",
           os.path.join(ROOT, "pipeline", "production", "contact_audit.py"), "audit", "--blend", blend, "--bake", bake,
           "--out", out, "--md", out + ".md", "--profile", PROFILE, "--blender", BLENDER, *extra]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-3000:], r.stderr[-3000:])
    check(r.returncode == 0, f"audit {' '.join(extra) or '(defaults)'} exits 0")
    return json.load(open(out)) if r.returncode == 0 else None


def depth(doc, frame, cls, char):
    r = next((r for r in doc["rows"] if r["frame"] == frame), None)
    e = (r or {}).get("classes", {}).get(cls, {}).get(char, {})
    return max((v[1] for v in e.values()), default=None)


def blender_exe():
    exe = os.environ.get("BLENDER")
    if exe:
        return exe
    if os.path.basename(sys.executable).startswith("python"):  # the bpy module: the same adapter the gate uses
        return f"{sys.executable} {os.path.join(ROOT, 'tools', 'bpy_blender.py')}"
    return bpy.app.binary_path or "blender"


tmp = tempfile.mkdtemp(prefix="t218_test_")
PROFILE = os.path.join(tmp, "profile.json")
json.dump({"roles": {"hand.L": "DEF-hand.L", "hand.R": "DEF-hand.R"}}, open(PROFILE, "w"))
BLENDER = blender_exe()
blend, bake = os.path.join(tmp, "scene.blend"), os.path.join(tmp, "bake.json")
build(blend, bake)

d1 = audit(blend, bake, os.path.join(tmp, "a1.json"))
if d1:
    R = d1["roles"]
    check(R["a"]["hair"] == ["hair_a"] and R["a"]["garment"] == ["garment.lining", "garment.shirt"],
          "roles: hair and garment")
    check(sorted(R["a"]["body"]) == ["arm.cage", "body_skin", "hand.L"],
          f"roles: a's body = skin, cage, hand ({R['a']['body']})")
    check(R["b"]["solid"] == ["garment.collider.body_skin"] and R["b"]["body"] == ["body_skin.001"],
          f"roles: b's solid is the hidden proxy, the masked skin is body only ({R['b']['solid']}, {R['b']['body']})")
    check(R["a"]["glasses"] == ["glasses"] and "glasses" not in R["a"]["body"], "roles: glasses apart from the body")
    check(R["a"]["hands"] == {"hand.L": 8}, f"roles: hand vertices = hand bone + its finger ({R['a']['hands']})")
    check(R["props"] == ["prop.box"] and R["set"] == ["prop.floor"], "roles: props vs set boxes from the bake")
    check(d1["characters"] == ["a", "b"], "characters from the rigs (rig_ stripped)")
    check(depth(d1, 1, "hair_own", "a") is None and near(depth(d1, 2, "hair_own", "a"), 20.0)
          and near(depth(d1, 3, "hair_own", "a"), 3.0), "hair_own: none / 20 / 3 mm")
    check(depth(d1, 1, "garment_body", "a") is None and near(depth(d1, 2, "garment_body", "a"), 10.0)
          and depth(d1, 3, "garment_body", "a") is None, "garment_body: 10 mm at f2 only")
    gl = [k for r in d1["rows"] for k in r["classes"].get("garment_body", {}).get("a", {}) if "lining" in k]
    check(gl == [], f"garment_body (closed solid rule): a lining in a closed cavity is outside, not enclosed ({gl})")
    check(near(depth(d1, 2, "hand_prop", "a"), 8.0) and depth(d1, 1, "hand_prop", "a") is None,
          "hand_prop: 8 mm at f2 only")
    check(all(near(depth(d1, f, "body_body", "a"), 50.0) and depth(d1, f, "body_body", "b") is None for f in (1, 2, 3)),
          "body_body: a in b 50 mm every frame, b in a none")
    check(all(near(depth(d1, f, "body_set", "b"), 5.0) and depth(d1, f, "body_set", "a") is None for f in (1, 2, 3)),
          "body_set: b 5 mm in the floor every frame")
    check(all(depth(d1, f, c, ch) is None for f in (1, 2, 3) for c in ("hair_other", "hair_set", "hair_prop")
              for ch in ("a", "b")), "no false entries in the other hair classes")
    s = d1["summary"]
    check(s["hair_own"]["pops"]["count"] == 2 and near(s["hair_own"]["pops"]["max_mm"], 20.0),
          f"hair_own depth pops 0 -> 20 -> 3: 2, max 20 ({s['hair_own']['pops']['count']})")
    check(s["body_body"]["pops"]["count"] == 0 and s["body_body"]["cols"]["all"]["over"] == 3,
          "body_body: 3 entries, no pops")
    check(s["hair"]["max_mm"] == s["hair_own"]["max_mm"] and s["hair"]["cols"]["all"]["over"] == 2,
          "hair aggregate = worst hair class")
    check(s["hair_own"]["worst"]["frame"] == 2, "worst frame")
    j = {r["frame"]: r["jump_mm"]["a"].get("hair") for r in d1["rows"]}
    check(j[1] is None and near(j[2], 70.0) and near(j[3], 17.0), f"largest hair vertex move 70 / 17 mm ({j})")
    cmp = CA.compare(d1, d1)
    check(cmp["pops_b_vs_a"]["count"] == 0 and cmp["new_keys_b"] == {}, "compare: a run against itself")
    md = os.path.join(tmp, "a1.json.md")
    check(os.path.isfile(md) and "| hair_own |" in open(md).read(),
          "markdown summary written")

    d2 = audit(blend, bake, os.path.join(tmp, "a2.json"))
    d3 = audit(blend, bake, os.path.join(tmp, "a3.json"), "--jobs", "2")
    d4 = audit(blend, bake, os.path.join(tmp, "a4.json"), "--step", "2")
    if d2 and d3 and d4:
        check(d2["rows"] == d1["rows"] and d2["sha256"] == d1["sha256"], "deterministic: two runs equal")
        check(d3["rows"] == d1["rows"] and d3["sha256"] == d1["sha256"],
              "--jobs 2 = --jobs 1 (rows, vertex moves, sha256)")
        check([r["frame"] for r in d4["rows"]] == [1, 3], "--step 2 measures f1, f3")

# in process: the closed-solid rule (garment_body, body_body) on a deep point and next to a sharp edge
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
big = bpy.data.objects.new("big", box_mesh("big", (0, 0, 0), (0.3, 0.3, 0.3)))
me = bpy.data.meshes.new("wedge")  # a thin wedge along Y, sharp edge at x = 1.2, half-angle ~7 deg
me.from_pydata([(1.0, -0.2, -0.025), (1.0, -0.2, 0.025), (1.2, -0.2, 0.0), (1.0, 0.2, -0.025), (1.0, 0.2, 0.025),
                (1.2, 0.2, 0.0)], [], [(0, 2, 1), (3, 4, 5), (0, 1, 4, 3), (1, 2, 5, 4), (2, 0, 3, 5)])
me.validate()
me.update()
wedge = bpy.data.objects.new("wedge", me)
for o in (big, wedge):
    sc.collection.objects.link(o)
deps = bpy.context.evaluated_depsgraph_get()
T = CA.Surfaces([("x:body:big", big), ("x:body:wedge", wedge)], deps, closed=True)
d_deep = T.depth(np.array((0.0, 0.0, 0.22)))[0]
check(abs(d_deep - 0.08) < 1e-4, f"closed rule: 80 mm deep is 80 mm (no 50 mm search cut-off; {d_deep * 1e3:.1f})")
check(T.depth(np.array((0.0, 0.0, 0.0)))[0] > 0.29, "closed rule: the centre of a 0.6 m box is 300 mm deep")
outs = [np.array((1.2 + 0.03 * np.cos(a), 0.0, 0.03 * np.sin(a))) for a in np.radians(np.arange(-80, 81, 10))]
res = [(T.depth(q)[0], T.depth(q)[2]) for q in outs]
check(all(r[0] == 0.0 for r in res), "closed rule: points 30 mm beyond a sharp edge are outside")
check(any(r[1] < 0 for r in res), "precondition: the nearest face's sign says inside for some of them "
      f"({sorted({round(r[1] * 1e3, 1) for r in res})} mm)")
check(T.depth(np.array((1.05, 0.0, 0.0)))[0] > 0, "closed rule: a point inside the wedge is inside")

# pure Python: staging, known rules, snaps split
rows = [{"frame": f, "jump_mm": {}, "sha256": "", "classes": {"hair_other": {"x": {
    "hair_q > y:body:body_skin": [3, mm], "hair_q > y:garment:garment.coat": [1, 9.0]}}}} for f, mm in
    ((1, 2.0), (2, 9.0), (3, 2.0))]
doc = {"rows": rows, "limit_mm": 1.0, "characters": ["x", "y"], "snap_frames": [2]}
s = CA.summarise(doc, [], 4.0, 5.0)
check(s["staging_hair"]["cols"]["all"]["over"] == 1 and s["staging_hair"]["max_mm"] == 9.0,
      "staging: > 4 mm in another character's body is apart")
check(s["hair_other"]["cols"]["all"]["over"] == 3 and s["hair_other"]["cols"]["calm"]["entries"] == 0,
      "garment of another character stays in hair_other; f1-3 are the snap window of f2 (no calm entries)")
known = [{"label": "accepted", "class": "hair_other", "character": "x", "surface": "y:garment:*"}]
s = CA.summarise(doc, known, 4.0, 5.0)
check(s["known:accepted"]["cols"]["all"]["over"] == 3 and s["hair_other"]["cols"]["all"]["over"] == 2,
      "known rule moves the matching entries apart")
s = CA.summarise(doc, [], 4.0, 1.0)
check(s["hair_other"]["pops"]["count"] == 2 and s["staging_hair"]["pops"]["count"] == 2,
      "depth pops split with the class (2 -> 0 key moves to staging and back)")

shutil.rmtree(tmp, ignore_errors=True)
print(f"\n{len(FAILS)} failure(s)" if FAILS else "\nall passed")
sys.exit(1 if FAILS else 0)
