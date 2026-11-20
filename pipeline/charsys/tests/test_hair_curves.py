"""Tests for the T-141 opt-in hair-curves experiment (pipeline/charsys/groom/hair_curves.py).

    python3 pipeline/charsys/tests/test_hair_curves.py [--blender <exe>]

Plain part (no Blender): the groom/ folder is a namespace directory (no __init__.py) and `import groom` still resolves
to groom.py; no shared code imports the experiment (opt-in only); the committed T-141 option files parse.
Blender part (synthetic tube with a two-bone armature; no character is built or read): options validation and layer
resolution; guides follow the mesh's "ps_fibre" V direction, lie on the surface and overhang the open end; the build
is deterministic; the built-in hair node groups are appended and stacked in order; the source mesh keeps its
vertices, UV maps and active UV; a rigid bone rotation moves every strand point with the surface; under a bend the
strand set (curve and point counts) is identical and stays on the surface; felt-fibre layers are hidden only when
asked; the command line refuses to overwrite its input or write into assets/characters."""
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
MODULE = os.path.join(CHARSYS, "groom", "hair_curves.py")
TAG = "[test_hair_curves]"
RESULTS = []


def check(name, ok, detail=None):
    RESULTS.append(bool(ok))
    print(f"{TAG} {'PASS' if ok else 'FAIL'} {name}{'' if detail is None else ' ' + str(detail)}", flush=True)


def load_module():
    spec = importlib.util.spec_from_file_location("ps_hair_curves", MODULE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ------------------------------------------------------------------------------------------------ plain checks
def plain():
    gdir = os.path.join(CHARSYS, "groom")
    check("groom/ is a namespace directory (no __init__.py)", not os.path.exists(os.path.join(gdir, "__init__.py")))
    check("groom/ holds only the experiment module",
          sorted(f for f in os.listdir(gdir) if not f.startswith("__")) == ["hair_curves.py"], os.listdir(gdir))
    out = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, sys.argv[1]); import importlib.util;"
                          "print(importlib.util.find_spec('groom').origin)", CHARSYS], capture_output=True, text=True)
    check("`import groom` still resolves to groom.py", out.stdout.strip() == os.path.join(CHARSYS, "groom.py"),
          out.stdout.strip() or out.stderr.strip()[-200:])
    users = []
    for base in ("pipeline", "tools", "engine", "apps"):
        for dp, _, files in os.walk(os.path.join(ROOT, base)):
            for f in files:
                p = os.path.join(dp, f)
                if f.endswith(".py") and p not in (MODULE, os.path.abspath(__file__)):
                    if re.search(r"groom[/.\\]+hair_curves|import hair_curves|ps_hair_curves",
                                 open(p, encoding="utf-8", errors="replace").read()):
                        users.append(os.path.relpath(p, ROOT))
    check("no shared code references the experiment (opt-in only)", not users, users[:5])
    odir = os.path.join(ROOT, "docs", "evaluation", "characters", "T-141", "options")
    files = sorted(f for f in os.listdir(odir) if f.endswith(".json")) if os.path.isdir(odir) else []
    ok = bool(files) and all(json.load(open(os.path.join(odir, f))).get("schema") == "plush-studio.hair-curves/1"
                             for f in files)
    check("committed T-141 option files carry the schema", ok, files)
    return files


# ---------------------------------------------------------------------------------------------- Blender checks
def make_scene(bpy, np, with_fibres=False):
    """An open tube along -Z (radius 0.03, z 0.3 .. 0), "ps_fibre" V = metres from the top, two-bone armature."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    seg, rings, r, h = 16, 31, 0.03, 0.3
    verts, faces, uvs = [], [], []
    for j in range(rings):
        z = h * (1 - j / (rings - 1))
        for i in range(seg):
            a = 2 * np.pi * i / seg
            verts.append((r * np.cos(a), r * np.sin(a), z))
    for j in range(rings - 1):
        for i in range(seg):
            a, b = j * seg + i, j * seg + (i + 1) % seg
            faces.append((a, a + seg, b + seg, b))  # outward normals
            v0, v1 = h * j / (rings - 1), h * (j + 1) / (rings - 1)
            u0, u1 = i / seg * 0.19, (i + 1) / seg * 0.19
            uvs += [(u0, v0), (u0, v1), (u1, v1), (u1, v0)]
    me = bpy.data.meshes.new("hair_test_tube")
    me.from_pydata(verts, [], faces)
    me.uv_layers.new(name="UVMap")
    fib = me.uv_layers.new(name="ps_fibre")
    fib.data.foreach_set("uv", np.asarray(uvs, dtype=np.float32).ravel())
    ob = bpy.data.objects.new("hair_test_tube", me)
    bpy.context.scene.collection.objects.link(ob)
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
        w = min(max((h * 0.6 - v[2]) / (h * 0.2), 0.0), 1.0)  # blend zone z 0.18 .. 0.12
        gt.add([i], 1.0 - w, "REPLACE")
        gl.add([i], w, "REPLACE")
    ob.parent = rig
    mod = ob.modifiers.new("Armature", "ARMATURE")
    mod.object = rig
    if with_fibres:
        for layer in ("fibres", "halo"):
            fo = bpy.data.objects.new(f"{ob.name}.{layer}", bpy.data.hair_curves.new(f"{ob.name}.{layer}"))
            fo["ps_groom_fibres"] = layer
            fo.parent = ob
            bpy.context.scene.collection.objects.link(fo)
    return ob, rig


def positions(bpy, np, obj, evaluated=True):
    data = obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).data if evaluated else obj.data
    p = np.zeros(len(data.points) * 3, dtype=np.float32)
    data.attributes["position"].data.foreach_get("vector", p)
    return p.reshape(-1, 3), len(data.curves)


def inner(tmp):
    import bpy
    import numpy as np
    from mathutils import Matrix
    HC = load_module()
    base = {"schema": HC.SCHEMA, "seed": 3, "structures": [{"match": "hair_test_*", "density_per_m2": 4000}]}

    check("valid options pass", HC.validate(base) == [], HC.validate(base))
    bad = [({}, "no schema"), ({**base, "structures": []}, "empty structures"),
           ({**base, "structures": [{"density_per_m2": 1}]}, "no match"),
           ({**base, "structures": [{"match": "x", "flow": "sideways"}]}, "bad flow"),
           ({**base, "structures": [{"match": "x", "points": 2}]}, "points < 3"),
           ({**base, "structures": [{"match": "x", "clump": {"nope": 1}}]}, "unknown clump key"),
           ({**base, "structures": [{"match": "x", "length_m": -1}]}, "negative length"),
           ({**base, "structures": [{"match": "x", "wobble": 1}]}, "unknown setting"),
           ({**base, "hide_fibre_layers": "yes"}, "bad hide"), ({**base, "extra": 1}, "unknown key")]
    fails = [label for o, label in bad if not HC.validate(o)]
    check(f"{len(bad)} malformed option sets are refused", not fails, fails)
    lay = HC.settings_for("hair_a", {"structures": [
        {"match": "hair_bow*", "skip": True}, {"match": "hair_*", "length_m": 0.02, "clump": {"factor": 0.1}},
        {"match": "hair_*", "length_m": 0.09}, {"match": "hair_*", "layer": "fly", "interpolate": None}]})
    check("layers: first match wins per layer, sub-settings merge with the defaults",
          sorted(lay) == ["", "fly"] and lay[""]["length_m"] == 0.02 and lay[""]["clump"]["factor"] == 0.1
          and lay[""]["clump"]["shape"] == HC.DEFAULTS["clump"]["shape"] and lay["fly"]["interpolate"] is None)
    check("skip excludes a mesh; unmatched meshes get nothing",
          HC.settings_for("hair_bow", {"structures": [{"match": "hair_bow*", "skip": True}, {"match": "hair_*"}]}) == {}
          and HC.settings_for("head", {"structures": [{"match": "hair_*"}]}) == {})

    ob, rig = make_scene(bpy, np)
    me = ob.data
    co0 = np.zeros(len(me.vertices) * 3)
    me.vertices.foreach_get("co", co0)
    uv_names0, active0 = [u.name for u in me.uv_layers], me.uv_layers.active.name
    rep = HC.apply(base)
    obj = bpy.data.objects.get("hair_test_tube.hair_curves")
    st = rep["objects"].get("hair_test_tube.hair_curves", {})
    area = 2 * np.pi * 0.03 * 0.3
    check("one curves object per matched mesh, parented to it", obj is not None and obj.parent is ob
          and obj.type == "CURVES" and len(rep["objects"]) == 1)
    check("guide count = density x area (2%)", abs(st.get("guides", 0) - 4000 * area) < 0.02 * 4000 * area + 2,
          (st.get("guides"), round(4000 * area, 1)))
    check("flow comes from the ps_fibre UV map", st.get("flow") == "uv", st.get("flow"))
    g, n = positions(bpy, np, obj, evaluated=False)
    g = g.reshape(n, -1, 3)
    d = g[:, -1] - g[:, 0]
    check("guides run along increasing V (down the tube)", float((d[:, 2] < 0).mean()) > 0.99,
          round(float((d[:, 2] < 0).mean()), 4))
    on = g[g[:, :, 2] > 0.0]
    rad = np.linalg.norm(on[:, :2], axis=1)
    lim = HC.DEFAULTS["lift_m"] * 1.5 + HC.DEFAULTS["tip_lift_m"]
    check("guide points over the tube lie on its surface (lift only)",
          float(rad.min()) > 0.03 * np.cos(np.pi / 16) - 1e-4 and float(rad.max()) < 0.03 + lim + 1e-4,
          (round(float(rad.min()), 5), round(float(rad.max()), 5)))
    check("strands that reach the open end overhang it", st.get("overhang_points", 0) > 0
          and float(g[:, :, 2].min()) < -0.005, (st.get("overhang_points"), round(float(g[:, :, 2].min()), 4)))
    step = np.linalg.norm(np.diff(g, axis=1), axis=2)
    check("strand length within length_m", float(step.sum(axis=1).max()) <= HC.DEFAULTS["length_m"] * 1.15,
          round(float(step.sum(axis=1).max()), 4))
    mods = [(m.name, m.node_group.name) for m in obj.modifiers]
    want = ["Interpolate Hair Curves", "Clump Hair Curves", "Frizz Hair Curves", "Set Hair Curve Profile",
            HC.FOLLOW_GROUP]
    check("modifier stack: built-in hair groups in order, then follow-surface", [m[1] for m in mods][:5] == want, mods)
    check("built-in groups are appended (local data, file is self-contained)",
          all(bpy.data.node_groups[n].library is None for n in want))
    co1 = np.zeros(len(me.vertices) * 3)
    me.vertices.foreach_get("co", co1)
    check("source mesh: vertices unchanged, UV maps kept, one atlas map added, active UV unchanged",
          np.array_equal(co0, co1) and [u.name for u in me.uv_layers] == uv_names0 + [HC.UV_ATLAS]
          and me.uv_layers.active.name == active0)
    meta = json.loads(obj["ps_hair_curves"])
    check("settings and seed are recorded on the object", meta["seed"] == 3 and meta["settings"]["points"] == 10)
    try:
        HC.apply(base)
        again = False
    except RuntimeError:
        again = True
    check("applying twice to the same file is refused", again)

    rest, ncur = positions(bpy, np, obj)
    check("children are generated (more curves than guides)", ncur > n, (n, ncur))
    rr = np.linalg.norm(rest[rest[:, 2] > 0.005][:, :2], axis=1)
    check("rest: no evaluated strand point is below the surface (min_height_m) or far above it",
          float(rr.min()) > 0.03 * np.cos(np.pi / 16) and float(rr.max()) < 0.045,
          (round(float(rr.min()), 4), round(float(rr.max()), 4)))
    rig.pose.bones["top"].rotation_mode = "XYZ"
    rig.pose.bones["top"].rotation_euler = (0.0, np.radians(70.0), 0.0)  # the bone axis is world -Z
    bpy.context.view_layer.update()
    rigid, ncur_r = positions(bpy, np, obj)
    rot = np.array(Matrix.Rotation(np.radians(-70.0), 3, "Z"))
    err = float(np.abs(rigid - rest @ rot.T).max())
    check("rigid rotation: every strand point turns with the surface (< 0.1 mm)", ncur_r == ncur and err < 1e-4, err)
    rig.pose.bones["top"].rotation_euler = (0.0, 0.0, 0.0)
    rig.pose.bones["low"].rotation_mode = "XYZ"
    rig.pose.bones["low"].rotation_euler = (np.radians(40.0), 0.0, 0.0)
    bpy.context.view_layer.update()
    bent, ncur_b = positions(bpy, np, obj)
    dg = bpy.context.evaluated_depsgraph_get()
    em = ob.evaluated_get(dg).to_mesh()
    from mathutils.bvhtree import BVHTree
    bvh = BVHTree.FromPolygons([tuple(v.co) for v in em.vertices], [tuple(p.vertices) for p in em.polygons])
    sel = np.flatnonzero(rest[:, 2] > 0.01)[::7]
    dist = np.array([bvh.find_nearest(tuple(bent[i]))[3] for i in sel])
    rdist = np.abs(np.linalg.norm(rest[sel][:, :2], axis=1) - 0.03)
    moved = float(np.linalg.norm(bent - rest, axis=1).max())
    check("bend: same strand set (curve and point counts)", ncur_b == ncur and len(bent) == len(rest))
    check("bend: strands move with the lower bone", moved > 0.05, round(moved, 4))
    check("bend: strands stay on the deformed surface (rest distance + 2 mm)",
          float((dist - rdist).max()) < 0.002, round(float((dist - rdist).max()), 5))
    rig.pose.bones["low"].rotation_euler = (0.0, 0.0, 0.0)
    bpy.context.view_layer.update()
    back, _ = positions(bpy, np, obj)
    check("back to rest: identical strands (no state, no drift)", np.array_equal(back, rest))

    make_scene(bpy, np)
    HC.apply(base)
    g2, _ = positions(bpy, np, bpy.data.objects["hair_test_tube.hair_curves"], evaluated=False)
    e2, _ = positions(bpy, np, bpy.data.objects["hair_test_tube.hair_curves"])
    check("deterministic: a second build gives identical guides and strands",
          np.array_equal(g2.reshape(g.shape), g) and np.array_equal(e2, rest))
    make_scene(bpy, np)
    HC.apply({**base, "seed": 4})
    g3, _ = positions(bpy, np, bpy.data.objects["hair_test_tube.hair_curves"], evaluated=False)
    check("another seed gives other guides", g3.shape != g.reshape(-1, 3).shape or not np.array_equal(g3, g.reshape(-1, 3)))

    ob, _ = make_scene(bpy, np, with_fibres=True)
    HC.apply({**base, "structures": base["structures"] + [
        {"match": "hair_test_*", "layer": "fly", "density_per_m2": 500, "interpolate": None, "clump": None,
         "curl": {"radius": 0.002, "frequency": 40}}]})
    fly = bpy.data.objects.get("hair_test_tube.hair_curves.fly")
    check("second layer builds its own object with Curl and without Interpolate/Clump", fly is not None
          and [m.node_group.name for m in fly.modifiers][:2] == ["Curl Hair Curves", "Frizz Hair Curves"])
    check("felt-fibre layers stay visible by default",
          not any(c.hide_render for c in ob.children if "ps_groom_fibres" in c))
    ob, _ = make_scene(bpy, np, with_fibres=True)
    rep = HC.apply({**base, "hide_fibre_layers": ["halo"]})
    hidden = sorted(c["ps_groom_fibres"] for c in ob.children if "ps_groom_fibres" in c and c.hide_render)
    check("hide_fibre_layers hides only the named layers", hidden == ["halo"] and len(rep["hidden_fibre_objects"]) == 1,
          hidden)

    ob, _ = make_scene(bpy, np)
    ob.data.uv_layers.remove(ob.data.uv_layers["ps_fibre"])
    ob["ps_dyn"] = json.dumps({"chains": [{"joints": [[0, 0, 0.3], [0, 0, 0.15], [0, 0, 0.0]]}]})
    rep = HC.apply(base)
    check("flow falls back to the dynamics chain without a fibre UV",
          rep["objects"]["hair_test_tube.hair_curves"]["flow"] == "chain")
    ob, _ = make_scene(bpy, np)
    ob.data.uv_layers.remove(ob.data.uv_layers["ps_fibre"])
    rep = HC.apply(base)
    check("flow falls back to gravity without UV and chains",
          rep["objects"]["hair_test_tube.hair_curves"]["flow"] == "down")

    src = os.path.join(tmp, "in.blend")
    make_scene(bpy, np)
    bpy.ops.wm.save_as_mainfile(filepath=src)
    opt = os.path.join(tmp, "o.json")
    json.dump(base, open(opt, "w"))
    refused = []
    for out in (src, os.path.join(tmp, "assets", "characters", "x", "out.blend")):
        try:
            HC.main(["--blend", src, "--out", out, "--options", opt])
            refused.append(False)
        except SystemExit as e:
            refused.append(bool(e.code))
    check("command line refuses to overwrite the input or write into assets/characters", refused == [True, True])
    size0 = os.path.getsize(src)
    out = os.path.join(tmp, "out.blend")
    HC.main(["--blend", src, "--out", out, "--options", opt, "--report", os.path.join(tmp, "r.json")])
    r = json.load(open(os.path.join(tmp, "r.json")))
    check("command line writes a new file and a report; the input file is untouched",
          os.path.exists(out) and os.path.getsize(src) == size0 and r["curves_total"] > r["guides_total"] > 0, )
    json.dump(RESULTS, open(os.path.join(tmp, "inner.json"), "w"))


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
