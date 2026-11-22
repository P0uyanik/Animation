"""Tests for the T-207 opt-in velvet / flock hair finish (pipeline/charsys/groom/flock.py).

    python3 pipeline/charsys/tests/test_hair_flock.py [--blender <exe>]

Plain part (no Blender): no shared code imports the module (opt-in only); the committed T-207 option files parse.
Blender part (synthetic tube with a two-bone armature, a felt-fibre child and a lock material; no character is built or
read): options validation; the build hook is a no-op without the "flock" key (every mesh, curve, material and modifier
value bit-identical) and null blocks change nothing; flock and edge layers are deterministic over two runs; strands
start on the surface, lean along the flow and stay short; faces under another mesh get no strands; convexity matches
1/R on a sphere and the edge mask ignores the camera; felt-fibre layers are hidden or scaled only as asked; velvet
edits the named nodes and reports missing ones; a bone rotation moves the strands with the surface (same counts); the
command line refuses to overwrite its input or write into assets/characters."""
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CHARSYS = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(CHARSYS, "..", ".."))
MODULE = os.path.join(CHARSYS, "groom", "flock.py")
OPTIONS = os.path.join(ROOT, "docs", "evaluation", "characters", "T-207", "options")
TAG = "[test_hair_flock]"
RESULTS = []


def check(name, ok, detail=None):
    RESULTS.append(bool(ok))
    print(f"{TAG} {'PASS' if ok else 'FAIL'} {name}{'' if detail is None else ' ' + str(detail)}", flush=True)


def load_module():
    spec = importlib.util.spec_from_file_location("ps_hair_flock", MODULE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def plain():
    users = []
    for base in ("pipeline", "tools", "engine", "apps"):
        for dp, _, files in os.walk(os.path.join(ROOT, base)):
            for f in files:
                p = os.path.join(dp, f)
                if f.endswith(".py") and p not in (MODULE, os.path.abspath(__file__)) and \
                        os.path.dirname(p) != os.path.join(CHARSYS, "groom"):
                    if re.search(r"groom[/.\\]+flock|import flock|ps_hair_flock",
                                 open(p, encoding="utf-8", errors="replace").read()):
                        users.append(os.path.relpath(p, ROOT))
    check("no shared code references the module (opt-in only)", not users, users[:5])
    files = sorted(f for f in os.listdir(OPTIONS) if f.endswith(".json")) if os.path.isdir(OPTIONS) else []
    ok = bool(files) and all(json.load(open(os.path.join(OPTIONS, f))).get("schema") == "plush-studio.hair-flock/1"
                             for f in files)
    check("committed T-207 option files carry the schema", ok, files)


# ---------------------------------------------------------------------------------------------- Blender checks
def make_scene(bpy, np):
    """Open tube along -Z (radius 0.03, z 0.3 .. 0) with "ps_fibre" V = metres from the top, a two-bone armature,
    a felt-fibre child with a stand-in "PS Shared Surface Fibres/1" modifier, and a lock material with PS nodes."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    seg, rings, r, h = 24, 31, 0.03, 0.3
    verts, faces, uvs = [], [], []
    for j in range(rings):
        z = h * (1 - j / (rings - 1))
        for i in range(seg):
            a = 2 * np.pi * i / seg
            verts.append((r * np.cos(a), r * np.sin(a), z))
    for j in range(rings - 1):
        for i in range(seg):
            a, b = j * seg + i, j * seg + (i + 1) % seg
            faces.append((a, a + seg, b + seg, b))
            v0, v1 = h * j / (rings - 1), h * (j + 1) / (rings - 1)
            u0, u1 = i / seg * 0.19, (i + 1) / seg * 0.19
            uvs += [(u0, v0), (u0, v1), (u1, v1), (u1, v0)]
    me = bpy.data.meshes.new("hair_test_tube")
    me.from_pydata(verts, [], faces)
    fib = me.uv_layers.new(name="ps_fibre")
    fib.data.foreach_set("uv", np.asarray(uvs, dtype=np.float32).ravel())
    ob = bpy.data.objects.new("hair_test_tube", me)
    bpy.context.scene.collection.objects.link(ob)
    mat = bpy.data.materials.new("M_hair_test")
    try:
        mat.use_nodes = True
    except AttributeError:
        pass
    nt = mat.node_tree
    av = nt.nodes.new("ShaderNodeMapRange")
    av.name = "PS Fibre Albedo Variation"
    av.inputs["To Min"].default_value, av.inputs["To Max"].default_value = 0.1, 1.9
    rim = nt.nodes.new("ShaderNodeBsdfPrincipled")
    rim.name = "PS Rim Sheen"
    me.materials.append(mat)
    arm = bpy.data.armatures.new("rig_test")
    rig = bpy.data.objects.new("rig_test", arm)
    bpy.context.scene.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    top = arm.edit_bones.new("top")
    top.head, top.tail = (0, 0, h), (0, 0, h / 2)
    low = arm.edit_bones.new("low")
    low.head, low.tail, low.parent = (0, 0, h / 2), (0, 0, 0), top
    bpy.ops.object.mode_set(mode="OBJECT")
    gt, gl = ob.vertex_groups.new(name="top"), ob.vertex_groups.new(name="low")
    for i, v in enumerate(verts):
        w = min(max((h * 0.6 - v[2]) / (h * 0.2), 0.0), 1.0)
        gt.add([i], 1.0 - w, "REPLACE")
        gl.add([i], w, "REPLACE")
    ob.parent = rig
    mod = ob.modifiers.new("Armature", "ARMATURE")
    mod.object = rig
    g = bpy.data.node_groups.new("PS Shared Surface Fibres/1", "GeometryNodeTree")
    g.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    g.interface.new_socket("Density", in_out="INPUT", socket_type="NodeSocketFloat")
    g.interface.new_socket("Length", in_out="INPUT", socket_type="NodeSocketFloat")
    g.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    gi, go = g.nodes.new("NodeGroupInput"), g.nodes.new("NodeGroupOutput")
    g.links.new(gi.outputs[0], go.inputs[0])
    fmat = bpy.data.materials.new("M_fibres_test")
    for layer, length in (("felt", 0.0015), ("halo", 0.004)):
        fo = bpy.data.objects.new(f"{ob.name}.{layer}", bpy.data.hair_curves.new(f"{ob.name}.{layer}"))
        fo["ps_groom_fibres"] = layer
        fo.data.materials.append(fmat)
        fo.parent = ob
        bpy.context.scene.collection.objects.link(fo)
        m = fo.modifiers.new("Fibres", "NODES")
        m.node_group = g
        for it in g.interface.items_tree:
            if it.item_type == "SOCKET" and it.in_out == "INPUT" and it.name in ("Density", "Length"):
                getattr(m.properties.inputs, it.identifier).value = 100000.0 if it.name == "Density" else length
    return ob, rig


def scene_hash(bpy, np):
    """Everything the hook could touch: objects, mesh data, curves data, modifier inputs, material node inputs."""
    h = hashlib.sha256()
    for o in sorted(bpy.data.objects, key=lambda o: o.name):
        h.update(f"{o.name}|{o.type}|{o.hide_render}|{o.hide_viewport}|{sorted(o.keys())}".encode())
        if o.type == "MESH":
            co = np.zeros(len(o.data.vertices) * 3, dtype=np.float32)
            o.data.vertices.foreach_get("co", co)
            h.update(co.tobytes() + str(sorted(a.name for a in o.data.attributes)).encode())
            h.update(f"{o.add_rest_position_attribute}".encode())
        if o.type == "CURVES":
            h.update(f"{len(o.data.curves)}|{len(o.data.points)}".encode())
        for m in o.modifiers:
            h.update(m.name.encode())
            if m.type == "NODES" and m.node_group:
                for it in m.node_group.interface.items_tree:
                    if it.item_type == "SOCKET" and it.in_out == "INPUT":
                        p = getattr(m.properties.inputs, it.identifier, None)
                        h.update(repr(getattr(p, "value", None)).encode())
    for mat in sorted(bpy.data.materials, key=lambda m: m.name):
        if mat.node_tree:
            for n in sorted(mat.node_tree.nodes, key=lambda n: n.name):
                for s in n.inputs:
                    v = getattr(s, "default_value", None)
                    try:
                        v = tuple(v)
                    except TypeError:
                        pass
                    h.update(f"{n.name}.{s.identifier}={v!r}".encode())
    h.update(str(sorted(g.name for g in bpy.data.node_groups)).encode())
    return h.hexdigest()


def inner(tmp):
    import bpy
    import numpy as np
    from mathutils import Vector
    F = load_module()
    out = []

    def ck(name, ok, detail=None):
        out.append(bool(ok))
        print(f"{TAG} {'PASS' if ok else 'FAIL'} {name}{'' if detail is None else ' ' + str(detail)}", flush=True)

    full = {"schema": F.SCHEMA, "seed": 3, "look": "test", "match": ["hair_*"],
            "velvet": {"albedo_variation": [0.8, 1.2], "sheen": [0.5, 0.7], "sheen_lighten": 0.4},
            "fibres": {"felt": {"length": 0.5, "density": 0.25}, "halo": "hide"},
            "flock": {"density_per_m2": 150000, "length_m": 0.003, "lean_deg": 25, "lean_variation_deg": 0},
            "edge": {"density_per_m2": 20000, "length_m": 0.006, "mask": {"convex": [0, 50], "base": 0.1},
                     "frizz": {"distance": 0.0005, "shape": 0.5, "factor": 1.0}}}
    ck("valid options pass", F.validate(full) == [], F.validate(full))
    bad = F.validate({"schema": F.SCHEMA, "bogus": 1, "flock": {"length_m": -1, "points": 40, "x": 0},
                      "edge": {"mask": {"convex": [1]}}, "fibres": {"felt": "drop"}, "velvet": {"sheen": 2}})
    ck("bad options are reported", len(bad) >= 7, bad)
    ck("wrong schema is reported", F.validate({"schema": "x"}) != [])
    for f in sorted(os.listdir(OPTIONS)):
        if f.endswith(".json"):
            ck(f"options/{f} validates", F.validate(json.load(open(os.path.join(OPTIONS, f)))) == [])

    # --- absent key = bit-identical; null blocks change nothing
    make_scene(bpy, np)
    h0 = scene_hash(bpy, np)
    spec = {"schema": "groom/5", "structures": []}
    r = F.apply_spec(spec, list(bpy.data.objects))
    ck("build hook without the key returns None", r is None)
    ck("build hook without the key leaves everything bit-identical", scene_hash(bpy, np) == h0)
    ck("strip_spec returns the same object without the key", F.strip_spec(spec) is spec)
    ck("strip_spec drops only the key", F.strip_spec(dict(spec, flock=full)) == spec)
    r = F.apply({"schema": F.SCHEMA, "velvet": None, "fibres": None, "flock": None, "edge": None})
    ck("all-null options change nothing", scene_hash(bpy, np) == h0 and r["strands_total"] == 0)

    # --- full build, twice
    def build(camera_at=None):
        ob, rig = make_scene(bpy, np)
        if camera_at is not None:
            cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
            bpy.context.scene.collection.objects.link(cam)
            cam.location = camera_at
            bpy.context.scene.camera = cam
        rep = F.apply(full)
        return ob, rig, rep

    ob, rig, r1 = build()
    ev1 = F.evaluated_hash()
    _, _, r2 = build()
    ev2 = F.evaluated_hash()
    ck("two runs give the same strand hash", r1["strand_sha"] == r2["strand_sha"], (r1["strand_sha"], r2["strand_sha"]))
    ck("two runs give the same evaluated hash", ev1 == ev2, (ev1, ev2))
    _, _, r3 = build(camera_at=(0.5, -1.0, 0.2))
    _, _, r4 = build(camera_at=(-1.0, 0.3, 0.9))
    ck("strands do not depend on the camera", r3["strand_sha"] == r4["strand_sha"] == r1["strand_sha"])
    full2 = json.loads(json.dumps(full))
    full2["seed"] = 4
    make_scene(bpy, np)
    ck("another seed gives other strands", F.apply(full2)["strand_sha"] != r1["strand_sha"])

    ob, rig, rep = build()
    fl = bpy.data.objects.get("hair_test_tube.flock")
    ed = bpy.data.objects.get("hair_test_tube.flock.edge")
    ck("flock and edge objects exist, parented to the mesh", fl is not None and ed is not None and fl.parent == ob
       and ed.parent == ob)
    n = len(fl.data.curves)
    area = 2 * np.pi * 0.03 * 0.3
    ck("flock strand count = density x area", abs(n - 150000 * area) < 0.02 * 150000 * area, (n, 150000 * area))
    p = np.zeros(len(fl.data.points) * 3, dtype=np.float32)
    fl.data.points.foreach_get("position", p)
    p = p.reshape(n, -1, 3)
    rad0 = np.linalg.norm(p[:, 0, :2], axis=1)
    ck("roots lie on the surface (+ lift)", np.all(np.abs(rad0 - 0.03 - 0.0002) < 6e-4), float(np.abs(rad0 - 0.03).max()))
    seg = p[:, -1] - p[:, 0]
    ln = np.linalg.norm(seg, axis=1)
    ck("strands are short (<= length_m)", ln.max() <= 0.003 + 1e-6 and ln.min() > 0.0005, (ln.min(), ln.max()))
    down = -seg[:, 2] / ln
    ck("strands lean along the flow (down the lock)", np.median(down) > 0.6, float(np.median(down)))
    rise = np.linalg.norm(p[:, -1, :2], axis=1) - rad0
    ck("strands rise off the surface", np.all(rise > 0), float(rise.min()))
    ck("fibre tone attribute for the fibre material", "ps_fibre_tone" in fl.data.attributes)
    names = [m.name for m in ed.modifiers]
    ck("edge modifiers: Frizz, Profile, Follow Surface, Material", names == ["Frizz", "Profile", "Follow Surface",
                                                                             "Material"], names)
    felt, halo = bpy.data.objects["hair_test_tube.felt"], bpy.data.objects["hair_test_tube.halo"]
    ck("halo layer hidden, felt layer not", halo.hide_render and not felt.hide_render)
    vals = {it.name: getattr(felt.modifiers[0].properties.inputs, it.identifier).value
            for it in felt.modifiers[0].node_group.interface.items_tree
            if it.item_type == "SOCKET" and it.in_out == "INPUT" and it.name in ("Density", "Length")}
    ck("felt layer scaled (length x0.5, density x0.25)", abs(vals["Length"] - 0.00075) < 1e-9
       and abs(vals["Density"] - 25000.0) < 1e-3, vals)
    av = bpy.data.materials["M_hair_test"].node_tree.nodes["PS Fibre Albedo Variation"]
    ck("velvet sets named nodes", abs(av.inputs["To Min"].default_value - 0.8) < 1e-6
       and abs(av.inputs["To Max"].default_value - 1.2) < 1e-6)
    vlog = rep["velvet"]["M_hair_test"]
    ck("velvet reports nodes the material lacks", "sheen.lo" in vlog.get("missing", []), vlog)

    # --- motion: rotate the lower bone; same strand set, strands move with the surface
    before = F.evaluated_hash()
    bpy.context.view_layer.objects.active = rig
    rig.pose.bones["low"].rotation_mode = "XYZ"
    rig.pose.bones["low"].rotation_euler = (0.6, 0.0, 0.0)
    bpy.context.view_layer.update()
    after = F.evaluated_hash()
    ck("bend keeps the strand set (curves, points)", before[:2] == after[:2], (before, after))
    ck("bend moves the strands", before[2] != after[2])
    dg = bpy.context.evaluated_depsgraph_get()
    mev = ob.evaluated_get(dg).to_mesh()
    from mathutils.bvhtree import BVHTree
    bvh = BVHTree.FromPolygons([v.co.copy() for v in mev.vertices], [tuple(pl.vertices) for pl in mev.polygons])
    fe = fl.evaluated_get(dg).data
    q = np.zeros(len(fe.points) * 3, dtype=np.float32)
    fe.points.foreach_get("position", q)
    roots = q.reshape(n, -1, 3)[:, 0]
    dist = np.array([bvh.find_nearest(Vector(x))[3] for x in roots[::50]])
    ob.evaluated_get(dg).to_mesh_clear()
    ck("roots stay on the bent surface", dist.max() < 1e-3, float(dist.max()))

    # --- hidden-face cull: a sleeve over z 0.2 .. 0.3 hides that part of the tube
    ob, rig = make_scene(bpy, np)
    seg_, verts, faces = 24, [], []
    for j, z in enumerate((0.31, 0.2)):
        for i in range(seg_):
            a = 2 * np.pi * i / seg_
            verts.append((0.032 * np.cos(a), 0.032 * np.sin(a), z))
    for i in range(seg_):
        a, b = i, (i + 1) % seg_
        faces.append((a, a + seg_, b + seg_, b))
    sm = bpy.data.meshes.new("sleeve")
    sm.from_pydata(verts, [], faces)
    sl = bpy.data.objects.new("sleeve", sm)
    bpy.context.scene.collection.objects.link(sl)
    rep = F.apply({"schema": F.SCHEMA, "flock": {"density_per_m2": 100000, "cull_m": 0.004}})
    fl = bpy.data.objects["hair_test_tube.flock"]
    p = np.zeros(len(fl.data.points) * 3, dtype=np.float32)
    fl.data.points.foreach_get("position", p)
    z0 = p.reshape(len(fl.data.curves), -1, 3)[:, 0, 2]
    ck("no strands under the sleeve", z0.max() < 0.205, float(z0.max()))
    ck("hidden area reported (~1/3)", abs(rep["layers"]["hair_test_tube.flock"]["hidden_area_m2"] - area / 3) < 0.15 * area / 3,
       rep["layers"]["hair_test_tube.flock"])

    # --- convexity = 1/R on a sphere; plane = 0
    bpy.ops.wm.read_factory_settings(use_empty=True)
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=48, v_segments=24, radius=0.01)
    sme = bpy.data.meshes.new("sph")
    bm.to_mesh(sme)
    bm.free()
    HC = F.hair_curves()
    co, vn, tv, tl = HC._mesh_arrays(sme)
    c = F.convexity(co, vn, F._edges(sme))
    ck("convexity of a 10 mm sphere ~ 100 /m", abs(np.median(c) - 100.0) < 10.0, float(np.median(c)))
    w = F.edge_weight(sme, co, vn, {"convex": [40, 80], "boundary": 1.0, "base": 0.0})
    ck("edge weight 1 on a tight convex surface", np.median(w) > 0.99, float(np.median(w)))
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=10, y_segments=10, size=0.1)
    pme = bpy.data.meshes.new("pl")
    bm.to_mesh(pme)
    bm.free()
    co, vn, tv, tl = HC._mesh_arrays(pme)
    w = F.edge_weight(pme, co, vn, {"convex": [40, 80], "boundary": 1.0, "base": 0.0})
    bnd = F.boundary_vertices(pme, F._edges(pme))
    ck("edge weight: 0 inside a plane, 1 on its open border", np.all(w[~bnd] == 0.0) and np.all(w[bnd] == 1.0))

    # --- command line guards
    mod_path = MODULE
    src = os.path.join(tmp, "in.blend")
    bpy.ops.wm.save_as_mainfile(filepath=src)
    opt = os.path.join(tmp, "o.json")
    json.dump({"schema": F.SCHEMA}, open(opt, "w"))
    for dst, label in ((src, "input"), (os.path.join(ROOT, "assets", "characters", "x", "y.blend"), "assets")):
        try:
            F.main(["--blend", src, "--out", dst, "--options", opt])
            ck(f"command line refuses {label}", False)
        except SystemExit as e:
            ck(f"command line refuses {label}", "flock:" in str(e), str(e))
    del mod_path
    json.dump(out, open(os.path.join(tmp, "inner.json"), "w"))


def main():
    if "--inner" in sys.argv:
        inner(sys.argv[sys.argv.index("--inner") + 1])
        return 0
    blender = sys.argv[sys.argv.index("--blender") + 1] if "--blender" in sys.argv else "blender"
    plain()
    with tempfile.TemporaryDirectory() as tmp:
        p = subprocess.run([blender, "-b", "--factory-startup", "-P", os.path.abspath(__file__), "--", "--inner", tmp],
                           capture_output=True, text=True)
        lines = [ln for ln in p.stdout.splitlines() if ln.startswith(TAG)]
        print("\n".join(lines))
        try:
            RESULTS.extend(json.load(open(os.path.join(tmp, "inner.json"))))
        except OSError:
            check("Blender part ran to the end", False, (p.stdout + p.stderr)[-1500:])
    print(f"{TAG} {sum(RESULTS)}/{len(RESULTS)} passed")
    return 0 if all(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
