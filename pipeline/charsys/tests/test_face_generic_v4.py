"""T-216: face_generic/4 (pipeline/charsys/face_generic_v4.py, face_v4/knobs.py, face_v4/chains.py).

    python3 pipeline/charsys/tests/test_face_generic_v4.py [--blender <exe>]

Checks (each line PASS/FAIL; exit code 1 on any FAIL):
  plain    (no Blender, no numpy) face_generic/4 is registered and face_generic/1-3 still resolve to their own
           modules; the knob spec validator accepts WARP / HOOK / LATTICE and refuses unknown types, anchors, bad
           radii / scales, mirror on a midline anchor and a moved lattice border point; chain_stops / gaps find a
           base key without its stops and leave a partial chain alone; the v4 module names no character.
  blender  (--blender; synthetic meshes, about 10 s, no character asset) on a UV sphere with one shape key:
           each knob type moves the skin only inside its falloff radius / lattice box (0 outside), the key's delta
           is unchanged after the fold (dependent keys follow), Basis equals the mesh, and no modifier, empty,
           lattice or vertex group is left (knob-free); a mirrored knob is symmetric; complete() adds linear
           stop keys only where a chain has none, once per shared Key datablock.
"""
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CHARSYS = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(CHARSYS, "..", ".."))
sys.path.insert(0, CHARSYS)
RESULTS = []


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def check(name, ok, detail=None):
    RESULTS.append(bool(ok))
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + ("" if ok or detail is None else f"  ({detail})"))


def refused(fn):
    from face_v4 import knobs as K
    try:
        fn()
    except K.KnobError:
        return True
    return False


def plain():
    import versions as V
    from face_v4 import chains as CH
    from face_v4 import knobs as K
    e = V.REGISTRY.entry("face", "face_generic/4")
    check("face_generic/4 registered -> face_generic_v4", e["module"] == "face_generic_v4" and e["status"] == "released")
    check("face_generic/1-3 unchanged modules",
          [V.REGISTRY.entry("face", f"face_generic/{n}")["module"] for n in (1, 2, 3)]
          == ["face_generic", "face_generic", "face_generic_v3"])
    src = open(os.path.join(CHARSYS, "face_generic_v4.py"), encoding="utf-8").read()
    check("v4 declares GENERATOR_VERSIONS face_generic/4", 'GENERATOR_VERSIONS = ("face_generic/4",)' in src)
    ok = K.validate([{"type": "WARP", "at": "chin", "radius_m": 0.05, "move_m": [0, 0, -0.01]},
                     {"type": "HOOK", "at": {"front": 0.5}, "radius_m": 0.04, "move_m": [0.004, 0, 0]},
                     {"type": "LATTICE", "at": {"profile": 0.5}, "size_m": [0.1, 0.1, 0.1], "points": [3, 3, 3],
                      "offsets": {"1_1_1": [0, 0.004, 0]}}])
    ml = K.validate([{"type": "LATTICE", "at": "chin", "size_m": [.1, .1, .1], "points": [5, 3, 3], "mirror": True,
                      "offsets": {"3_1_1": [0.004, 0, 0]}}])[0]
    check("a midline LATTICE may mirror its own points", ml["mirror_points"] and ml["mirror"])
    check("valid knobs accepted; per-side anchors mirror by default",
          [k["mirror"] for k in ok] == [False, True, False] and ok[2]["offsets"] == {(1, 1, 1): (0.0, 0.004, 0.0)})
    bad = [
        ("unknown type", [{"type": "SMOOTH", "at": "chin", "radius_m": 0.05}]),
        ("unknown anchor", [{"type": "WARP", "at": "forehead", "radius_m": 0.05}]),
        ("zero radius", [{"type": "WARP", "at": "chin", "radius_m": 0}]),
        ("bad scale", [{"type": "HOOK", "at": "chin", "radius_m": 0.05, "scale": [1, 0, 1]}]),
        ("mirror on midline (Warp)", [{"type": "WARP", "at": "chin", "radius_m": 0.05, "mirror": True}]),
        ("bad falloff", [{"type": "WARP", "at": "chin", "radius_m": 0.05, "falloff": "WOBBLE"}]),
        ("lattice border moved", [{"type": "LATTICE", "at": "chin", "size_m": [.1, .1, .1], "points": [3, 3, 3],
                                   "offsets": {"0_1_1": [0, 0, 0.01]}}]),
        ("lattice 2 points", [{"type": "LATTICE", "at": "chin", "size_m": [.1, .1, .1], "points": [2, 3, 3]}]),
        ("not a list", {"type": "WARP"}),
    ]
    for name, knobs in bad:
        check(f"validator refuses: {name}", refused(lambda k=knobs: K.validate(k)))
    names = {"skin": {"Basis", "Laugh", "Blink", "Blink@75"}, "lid": {"Basis", "Laugh", "Laugh@25", "Laugh@50",
                                                                       "Blink@25", "Blink@75", "Blink"}}
    stops = CH.chain_stops(names.values())
    check("chain stops: union per base", stops == {"Laugh": [25, 50], "Blink": [25, 75]}, stops)
    check("gaps: base without any stop only", CH.gaps(names, stops) == [("skin", "Laugh")], CH.gaps(names, stops))
    lint = re.compile(r"auburn|girl_|boy_|white_hair|yellow_hoodie", re.I)
    files = ["face_generic_v4.py", "face_v4/knobs.py", "face_v4/chains.py", "face_v4/__init__.py"]
    hits = [f for f in files if lint.search(open(os.path.join(CHARSYS, f), encoding="utf-8").read())]
    check("no character named in face_generic/4 code", not hits, hits)


INNER = r'''
import json, sys
sys.path.insert(0, sys.argv[sys.argv.index("--") + 1])
import bpy, numpy as np
from face_v4 import knobs as K, chains as CH
out = {}
bpy.ops.wm.read_factory_settings(use_empty=True)
C = bpy.data.collections.new("t"); bpy.context.scene.collection.children.link(C)
bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=48, radius=0.15, location=(0, 0, 0.8))
head = bpy.context.active_object
for c in list(head.users_collection): c.objects.unlink(head)
C.objects.link(head)
head.shape_key_add(name="Basis")
k = head.shape_key_add(name="Smile")
n = len(head.data.vertices)
co0 = np.array([v.co[:] for v in head.data.vertices])
d0 = np.zeros((n, 3)); d0[:, 2] = 0.002 * (co0[:, 1] < 0)
k.data.foreach_set("co", (co0 + d0).ravel())

class Ctx:  # the duck-typed face context: ray casts on the current head mesh
    def invalidate(self): self._t = None
    def tree(self):
        from mathutils.bvhtree import BVHTree
        if getattr(self, "_t", None) is None:
            me = head.data
            self._t = BVHTree.FromPolygons([head.matrix_world @ v.co for v in me.vertices], [p.vertices[:] for p in me.polygons])
        return self._t
    def face_y(self, h, x, z):
        from mathutils import Vector
        return self.tree().ray_cast(Vector((x, -5, z)), Vector((0, 1, 0)), 10)[0].y

ez, zc = 0.82, 0.70
ctx = Ctx()
res = K.anchors(ctx, 0.05, ez, 0.74, zc)
out["front_anchor"] = list(res({"front": 0.5}, 1)); out["cheek_anchor"] = list(res({"cheek": 0.6}, -1))
knobs = [{"type": "WARP", "at": "chin", "radius_m": 0.04, "move_m": [0, 0, -0.01], "scale": [1.2, 1, 1]},
         {"type": "HOOK", "at": {"front": 0.5}, "radius_m": 0.03, "move_m": [0.005, 0, 0]},
         {"type": "WARP", "at": {"cheek": 0.6}, "radius_m": 0.02, "move_m": [0, 0.003, 0], "mirror": False},
         {"type": "LATTICE", "at": {"profile": 0.3}, "size_m": [0.12, 0.06, 0.06], "points": [5, 3, 3],
          "offsets": {"3_1_1": [0.005, -0.006, 0]}, "mirror": True}]
rep = K.apply_knobs(C, head, ctx, knobs, res, z_chin=zc)
out["report"] = rep
kb = head.data.shape_keys.key_blocks
b = np.empty(3 * n); s = np.empty(3 * n); m = np.empty(3 * n)
kb["Basis"].data.foreach_get("co", b); kb["Smile"].data.foreach_get("co", s); head.data.vertices.foreach_get("co", m)
out["delta_err"] = float(np.abs((s - b).reshape(-1, 3) - d0).max())
out["basis_eq_mesh"] = float(np.abs(b - m).max())
out["moved_max"] = float(np.linalg.norm(m.reshape(-1, 3) - co0, axis=1).max())
L = [e for e in rep["knobs"] if e["tag"].endswith(".L")][0]; R = [e for e in rep["knobs"] if e["tag"].endswith(".R")][0]
out["mirror"] = [L["anchor_m"][0] + R["anchor_m"][0], L["max_mm"] - R["max_mm"], L["moved_vertices"] - R["moved_vertices"]]
sym = m.reshape(-1, 3) - co0  # the mirrored lattice: x displacement antisymmetric about x = 0 near the profile anchor
box = (np.abs(co0[:, 0]) < 0.06) & (co0[:, 1] < -0.1) & (np.abs(co0[:, 2] + 0.8 - 0.784) < 0.03)  # object at z 0.8
out["lattice_sym"] = float(np.abs(sym[box, 0].sum())) / max(1, int(box.sum())) if box.any() else None
out["lattice_dx"] = float(np.abs(sym[box, 0]).max()) if box.any() else None
out["left"] = {"modifiers": [md.type for md in head.modifiers], "groups": len(head.vertex_groups),
               "objects": sorted(o.name for o in bpy.data.objects if o is not head), "lattices": len(bpy.data.lattices),
               "keys": [k.name for k in kb]}
# chains: a shared Key datablock (one mesh, two objects), a gap object, a partial chain
def mesh(name, keys, data=None):
    me = data or bpy.data.meshes.new(name)
    if data is None:
        me.from_pydata([(0, 0, 0), (1, 0, 0), (0, 1, 0)], [], [(0, 1, 2)])
    ob = bpy.data.objects.new(name, me); C.objects.link(ob)
    if data is None:
        ob.shape_key_add(name="Basis")
        for kname in keys:
            kk = ob.shape_key_add(name=kname)
            kk.data[0].co = (0, 0, 0.01)
    return ob
a = mesh("a", ["Laugh", "Laugh@25", "Laugh@50"])
g = mesh("g", ["Laugh"])
g2 = mesh("g2", [], data=g.data)
p = mesh("p", ["Laugh", "Laugh@50"])
done = CH.complete([a, g, g2, p])
out["chains"] = done
gk = g.data.shape_keys.key_blocks
out["g_keys"] = [k.name for k in gk]
out["g_stop25_z"] = gk["Laugh@25"].data[0].co.z if "Laugh@25" in gk else None
out["p_keys"] = [k.name for k in p.data.shape_keys.key_blocks]
json.dump(out, open(sys.argv[-1], "w"))
'''


def blender(exe):
    with tempfile.TemporaryDirectory() as t:
        sc, res = os.path.join(t, "inner.py"), os.path.join(t, "out.json")
        open(sc, "w").write(INNER)
        r = subprocess.run([exe, "-b", "--factory-startup", "--python-exit-code", "1", "-P", sc, "--", CHARSYS, res],
                           capture_output=True, text=True)
        check("synthetic Blender run", r.returncode == 0 and os.path.isfile(res), (r.stdout + r.stderr)[-600:])
        if not os.path.isfile(res):
            return
        o = json.load(open(res))
    rep = o["report"]
    check("5 knob instances (WARP, HOOK x2 mirrored, WARP one side, LATTICE)", rep["count"] == 5 and
          [k["type"] for k in rep["knobs"]] == ["WARP", "HOOK", "HOOK", "WARP", "LATTICE"], rep["count"])
    import math
    fa, ca = o["front_anchor"], o["cheek_anchor"]
    # sphere r 0.15 at z 0.8: front row z = 0.76 -> silhouette radius sqrt(.15^2 - .04^2) at y ~ 0 (no occluding edge)
    check("front anchor = the row's front-view outline", abs(fa[0] - math.sqrt(0.15 ** 2 - 0.04 ** 2)) < 0.002
          and abs(fa[1]) < 0.02, fa)
    check("cheek anchor = most forward skin point of the row on that side (x < 0, near the midline on a sphere)",
          -0.002 < ca[0] < 0 and ca[1] < -0.13, ca)
    check("every knob moved skin", all(k["moved_vertices"] > 0 and k["max_mm"] > 0.5 for k in rep["knobs"]),
          [k["max_mm"] for k in rep["knobs"]])
    check("0 mm outside every falloff radius / lattice box",
          all(k["outside_region_max_mm"] == 0.0 for k in rep["knobs"]), [k["outside_region_max_mm"] for k in rep["knobs"]])
    check("dependent key delta unchanged by the fold (< 1e-6 m)", o["delta_err"] < 1e-6, o["delta_err"])
    check("Basis equals the mesh after the fold", o["basis_eq_mesh"] < 1e-9, o["basis_eq_mesh"])
    check("mirrored knob is symmetric", abs(o["mirror"][0]) < 1e-6 and abs(o["mirror"][1]) < 0.1
          and abs(o["mirror"][2]) <= 4, o["mirror"])  # UV-sphere vertices at the falloff edge: float noise
    check("midline lattice: symmetric outward motion", o["lattice_dx"] and o["lattice_dx"] > 5e-4
          and o["lattice_sym"] < 2e-5, (o["lattice_dx"], o["lattice_sym"]))
    lf = o["left"]
    check("knob-free: no modifier, vertex group, empty or lattice left; keys unchanged",
          lf["modifiers"] == [] and lf["groups"] == 0 and lf["objects"] == [] and lf["lattices"] == 0
          and lf["keys"] == ["Basis", "Smile"], lf)
    check("chains: gap mesh completed once (shared Key), partial chain untouched",
          o["chains"] == {"Laugh": ["g"]} and o["g_keys"] == ["Basis", "Laugh", "Laugh@25", "Laugh@50"]
          and o["p_keys"] == ["Basis", "Laugh", "Laugh@50"], o)
    check("stop key is linear (25 % of the base delta)", o["g_stop25_z"] is not None and
          abs(o["g_stop25_z"] - 0.0025) < 1e-7, o["g_stop25_z"])


def main():
    plain()
    exe = arg("--blender")
    if exe:
        blender(exe)
    print(f"[test_face_generic_v4] {sum(RESULTS)}/{len(RESULTS)} passed")
    return 0 if all(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
