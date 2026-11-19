"""Blender test for hair round 4 (T-091, groom/3 = groom_r4.py) on a synthetic head (no character data).

    blender -b --factory-startup -P pipeline/charsys/tests/test_hair_r4_build.py

Checks: masses and a scrunchie build; each mass mesh carries the ps_comb direction (unit vectors, one per vertex);
a mass aimed into the face is held out of the face keep-out (0 violations, clamp reported); the build is
deterministic; groom/2 structures built through groom/3 are vertex-identical to groom/2's own build (groom/3 reuses
groom/2 unchanged); the directional-fibre flag adds the comb modifier only when enabled. Without bpy: SKIP."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..")))
RESULTS = []


def check(name, ok, detail=None):
    RESULTS.append(bool(ok))
    print(f"[test_hair_r4_build] {'PASS' if ok else 'FAIL'} {name}{'' if detail is None else ' ' + str(detail)}")


SPEC = {
    "generator": "groom/3", "seed": 5, "face_keepout": {"az": 34, "el_min": -5},
    "structures": [
        {"type": "bun", "name": "bun", "buns": [{"az": 180, "el": 82, "radius": 0.06, "height": 0.08, "ropes": 3,
                                                 "rope_thick": 0.02, "turns": 0.8}]},
        {"type": "clumps", "name": "clumps", "rows": [{"count": 4, "az": [100, 160], "el": [10, 30],
                                                      "flow": "down", "len_deg": [20, 30], "width": [0.04, 0.05],
                                                      "thick": [0.02, 0.025]}]},
        {"type": "masses", "name": "masses", "rows": [{"count": 5, "az": [-180, 180], "el": [55, 65],
                                                      "pole": {"az": 180, "el": 80}, "len_deg": [40, 50],
                                                      "width": [0.07, 0.08], "depth": 0.6}],
         "items": [{"root": [0, 60], "tip": [0, -40], "width": 0.08, "depth": 0.6},
                   {"root": [40, 70], "tip": [60, 20], "width": 0.06, "lift": [0.0, 0.05], "lift_power": 1.8}]},
        {"type": "scrunchie", "name": "band", "bun": 0, "gathers": 8},
    ]}


def head_object():
    import bpy
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=0.15, location=(0, 0, 1.0))
    ob = bpy.context.active_object
    ob.name = "head"
    return ob


def build(mod, spec, head, fibres=None):
    import bpy
    coll = bpy.data.collections.new("hair_test")
    bpy.context.scene.collection.children.link(coll)
    mats = {}

    def material(slot):
        return mats.setdefault(slot, bpy.data.materials.new(f"M_{slot}"))

    frame = {"centre": (0, 0, 1.0), "radii": (0.15, 0.15, 0.15)}
    objs, rep = mod.build(coll, head, frame, spec, material, lambda h, x, z: -0.15, fibres)
    return objs, rep


def verts(ob):
    return [tuple(round(c, 6) for c in v.co) for v in ob.data.vertices]


def main():
    try:
        import bpy
    except ImportError:
        print("[test_hair_r4_build] SKIP (needs Blender)")
        return 0
    import groom_hybrid as GH
    import groom_r4 as G4
    bpy.ops.wm.read_factory_settings(use_empty=True)
    head = head_object()
    objs, rep = build(G4, SPEC, head)
    names = {o.name: o for o in objs}
    m = names.get("hair_masses")
    check("masses built", m is not None and rep["structures"]["masses"]["masses"] == 7, rep["structures"].get("masses"))
    check("scrunchie built", "hair_band" in names and rep["structures"]["band"]["gathers"] == 8)
    a = m.data.attributes.get(G4.COMB_ATTR) if m else None
    vals = [tuple(x.vector) for x in a.data] if a else []
    check("ps_comb on every mass vertex", a is not None and len(vals) == len(m.data.vertices))
    check("ps_comb is unit length", vals and all(abs(sum(c * c for c in v) ** 0.5 - 1) < 1e-3 for v in vals))
    check("clumps (groom/2 type) carry no ps_comb", G4.COMB_ATTR not in names["hair_clumps"].data.attributes)
    check("mass aimed into the face is clamped", rep["structures"]["masses"]["keepout_clamped"] >= 1)
    check("face keep-out: 0 violations", rep["keepout"]["violations"] == 0, rep["keepout"])
    v1 = {n: verts(o) for n, o in names.items()}
    for o in objs:
        bpy.data.objects.remove(o, do_unlink=True)
    objs2, _ = build(G4, SPEC, head)
    check("deterministic (same vertices on a rebuild)", {o.name: verts(o) for o in objs2} == v1)
    for o in objs2:
        bpy.data.objects.remove(o, do_unlink=True)
    v2_spec = dict(SPEC, generator="groom/2", structures=[s for s in SPEC["structures"]
                                                          if s["type"] not in ("masses", "scrunchie")])
    objs3, _ = build(GH, v2_spec, head)
    v3 = {o.name: verts(o) for o in objs3}
    for o in objs3:
        bpy.data.objects.remove(o, do_unlink=True)
    objs4, _ = build(G4, dict(v2_spec, generator="groom/3"), head)
    check("groom/2 structures identical through groom/3", {o.name: verts(o) for o in objs4} == v3)
    for o in objs4:
        bpy.data.objects.remove(o, do_unlink=True)

    def fake_fibres(ob, slot, overrides):  # a curves object standing in for the shared surface fibres
        fo = bpy.data.objects.new(ob.name + "_fibres", bpy.data.hair_curves.new(ob.name + "_fc"))
        bpy.context.scene.collection.objects.link(fo)
        return fo

    for enabled in (False, True):
        sp = dict(SPEC, fibres={"slots": ["hair"], "layers": [{"name": "felt"}],
                                "directional": {"enabled": enabled, "strength": 0.9}})
        objs5, rep5 = build(G4, sp, head, fake_fibres)
        combed = [o for o in bpy.data.objects if o.type == "CURVES" and any(md.name == "PS Fibre Comb"
                                                                           for md in o.modifiers)]
        check(f"directional {'on' if enabled else 'off'}: comb modifier on mass fibres only"
              if enabled else "directional off: no comb modifier",
              (len(combed) == 1 and combed[0].name.startswith("hair_masses")) if enabled else not combed,
              [o.name for o in combed])
        check(f"directional {'on' if enabled else 'off'}: reported", rep5["fibres"]["directional"] == (0.9 if enabled else 0.0))
        for o in [o for o in bpy.data.objects if o.name.startswith("hair_")]:
            bpy.data.objects.remove(o, do_unlink=True)
    ok = all(RESULTS)
    print(f"[test_hair_r4_build] {'ALL PASS' if ok else 'FAILED'} ({sum(RESULTS)}/{len(RESULTS)})")
    return 0 if ok else 1


if __name__ == "__main__":
    code = main()
    if code:
        raise SystemExit(code)
