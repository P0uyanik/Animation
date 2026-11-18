"""Blender test for T-079's scalp-cap weight fix (groom_hybrid.drop_stale_weights; bug found in T-078).

    blender -b --factory-startup -P pipeline/charsys/tests/test_hair_v3_r3_weights.py

The groom/2 scalp cap is cut from the head mesh and inherited the head's deform weights without its vertex groups;
on a generic head (many groups) the stale group indices made export_engine fail with IndexError. Checks: stale
entries are removed, valid entries (and their weights) are kept, a mesh without stale entries is left untouched, and
groom_hybrid.build calls the fix on the scalp cap. Without bpy (plain Python) the test reports SKIP."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CHARSYS = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, CHARSYS)
RESULTS = []


def check(name, ok, detail=None):
    RESULTS.append(bool(ok))
    print(f"[test_hair_v3_r3_weights] {'PASS' if ok else 'FAIL'} {name}{'' if detail is None else ' ' + str(detail)}")


def grid(name, groups, weights):
    """A 4-vertex mesh object with the given vertex groups and per-vertex {group index: weight} entries; entries
    with an index >= len(groups) are written through bmesh (as a bmesh copy of a head would carry them)."""
    import bmesh
    import bpy
    me = bpy.data.meshes.new(name)
    me.from_pydata([(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)], [], [(0, 1, 2, 3)])
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    bm = bmesh.new()
    bm.from_mesh(me)
    dl = bm.verts.layers.deform.verify()
    bm.verts.ensure_lookup_table()
    for v, w in zip(bm.verts, weights):
        for k, x in w.items():
            v[dl][k] = x
    bm.to_mesh(me)
    bm.free()
    for g in groups:
        ob.vertex_groups.new(name=g)
    return ob


def main():
    try:
        import bpy  # noqa: F401
    except ImportError:
        print("[test_hair_v3_r3_weights] SKIP (needs Blender)")
        return 0
    import groom_hybrid as GH
    ob = grid("stale", ["head", "neck"], [{0: 1.0, 7: 0.5}, {1: 0.25, 40: 1.0}, {12: 1.0}, {}])
    n = len(ob.vertex_groups)
    check("fixture has stale entries", any(g.group >= n for v in ob.data.vertices for g in v.groups))
    removed = GH.drop_stale_weights(ob)
    check("3 stale entries removed", removed == 3, removed)
    check("no stale entries left", not any(g.group >= n for v in ob.data.vertices for g in v.groups))
    kept = sorted((v.index, g.group, round(g.weight, 4)) for v in ob.data.vertices for g in v.groups)
    check("valid entries and weights kept", kept == [(0, 0, 1.0), (1, 1, 0.25)], kept)
    clean = grid("clean", ["head"], [{0: 1.0}, {0: 0.5}, {}, {}])
    before = [(v.index, g.group, g.weight) for v in clean.data.vertices for g in v.groups]
    check("clean mesh untouched", GH.drop_stale_weights(clean) == 0
          and before == [(v.index, g.group, g.weight) for v in clean.data.vertices for g in v.groups])
    src = open(GH.__file__).read()
    check("build() strips the scalp cap's stale weights", "drop_stale_weights(ob)" in src.split("def build(")[1])
    ok = all(RESULTS)
    print(f"[test_hair_v3_r3_weights] {'ALL PASS' if ok else 'FAILED'} ({sum(RESULTS)}/{len(RESULTS)})")
    return 0 if ok else 1


if __name__ == "__main__":
    code = main()
    if code:
        raise SystemExit(code)
