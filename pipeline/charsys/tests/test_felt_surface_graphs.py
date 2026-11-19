"""Blender-side checks of the T-110 felt surface (presets/4) and its shared fibre halo (headless; bpy or Blender 5.3).

    blender -b --factory-startup -P pipeline/charsys/tests/test_felt_surface_graphs.py

1. default output unchanged (and 1b: the build's add_missing_halos call adds nothing and changes no datablock in a
   scene built only from presets/1..3 ids): every presets/1, presets/2 and presets/3 id builds node for node and value for value as
   on the input SHA (fresh material, preset applied over a linked colour graph, generated fibre object) - golden
   digests in pipeline/charsys/materials/felt_frozen_graphs.json, written once from the input SHA's builder with
   --write-golden; a presets/1..3 build creates no halo group, no halo material and no halo property;
2. the opt-in path: a /4 fabric id adds the one shared group PS Felt Halo/1 to its surface-fibre object (same object,
   second material slot); a /4 id whose base has no fibres (skin) gets a halo-only fibre object; repeated fibre calls
   for one surface (groom layers) add one halo; LOD off adds none, wide lowers the density;
3. the skin pass (add_missing_halos): one halo per mesh with a halo material, restricted to that material's faces on a
   multi-material mesh, garment pieces skipped, idempotent; the evaluated halo has curves with the per-curve root
   normal and tone attributes and the halo material;
4. felt skin/4 keeps the skin layers (non-emissive, crease, flock, warmth) and the blush link.
Exit code 1 on any failure.

    blender -b --factory-startup -P pipeline/charsys/tests/test_felt_surface_graphs.py -- \
        --write-golden <out.json> --charsys <input-SHA checkout>/pipeline/charsys --sha <input sha>
"""
import argparse
import hashlib
import importlib.util
import json
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
CHARSYS = os.path.abspath(os.path.join(HERE, ".."))
GOLDEN = os.path.join(CHARSYS, "materials", "felt_frozen_graphs.json")
HALO_GROUP = "PS Felt Halo/1"
RESULTS = []

_spec = importlib.util.spec_from_file_location("_r2graphs", os.path.join(HERE, "test_materials_r2_graphs.py"))
R2 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(R2)  # digest helpers only (its main() runs under __main__)


def check(name, ok, detail=None):
    RESULTS.append(bool(ok))
    print(f"[test_felt_surface_graphs] {'PASS' if ok else 'FAIL'} {name}" + ("" if detail is None else f" {detail}"))


def parse():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--write-golden", default="")
    p.add_argument("--charsys", default=CHARSYS)
    p.add_argument("--sha", default="")
    return p.parse_args(argv)


def frozen_ids(M):
    return list(M.load_library()["presets"]) + list(M.load_skin_library()["presets"]) + list(M.load_r2_library()["presets"])


def write_golden(args):
    M = R2.import_builder(os.path.abspath(args.charsys))
    out = {"schema": "plush-studio.material-graph-golden/1", "task": "T-110",
           "note": "Node-graph digests of every presets/1, presets/2 and presets/3 id (test_materials_r2_graphs.digest_id), "
                   "written from the input SHA's builder (test_felt_surface_graphs.py --write-golden). Never regenerate "
                   "from a branch that changes them.",
           "input_sha": args.sha, "blender": bpy.app.version_string, "ids": {}}
    for name in frozen_ids(M):
        out["ids"][name] = R2.digest_id(M, name)[0]
    with open(args.write_golden, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print(f"[test_felt_surface_graphs] wrote {len(out['ids'])} digests to {args.write_golden}")


def halo_mods(ob):
    return [m for m in ob.modifiers if m.type == "NODES" and m.node_group and m.node_group.name == HALO_GROUP]


def mod_input(mod, name):
    group = mod.node_group
    ident = next(i.identifier for i in group.interface.items_tree
                 if i.item_type == "SOCKET" and i.in_out == "INPUT" and i.name == name)
    return getattr(mod.properties.inputs, ident).value


def sphere(name, radius=0.06):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=radius)
    ob = bpy.context.object
    ob.name = name
    return ob


def main():
    args = parse()
    if args.write_golden:
        write_golden(args)
        return
    M = R2.import_builder(CHARSYS)
    from materials import felt_halo as FH
    golden = json.load(open(GOLDEN, encoding="utf-8"))
    ids = frozen_ids(M)
    check("golden covers every presets/1..3 id", sorted(golden["ids"]) == sorted(ids), sorted(set(ids) ^ set(golden["ids"])))
    for name in ids:
        digest, _ = R2.digest_id(M, name)
        check(f"{name}: graph unchanged vs input {golden.get('input_sha')}", golden["ids"].get(name) == digest)
        mats = [m for m in bpy.data.materials if m.get(FH.HALO_MATERIAL_PROP) or m.get("ps_felt_halo_material")]
        check(f"{name}: no halo group, material or property", bpy.data.node_groups.get(HALO_GROUP) is None and not mats)

    # 1b. the build's halo call (build_character.main_generic -> add_missing_halos) is a no-op without presets/4
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for name in ids:
        library = M.library_for(name)
        ob = sphere("noop_" + name.replace("/", "_").replace(" ", "_"), 0.05)
        ob.data.materials.append(M.build_material("M_" + name, name, library["presets"][name]["swatch_srgb"],
                                                  library["reference_size_m"]))
        M.add_fibres_geometry(ob, name, library["presets"][name]["swatch_srgb"], library["reference_size_m"])

    def snapshot():
        out = {}
        for coll in ("objects", "materials", "node_groups", "hair_curves", "meshes", "collections"):
            out[coll] = sorted(x.name for x in getattr(bpy.data, coll))
        out["digests"] = {m.name: json.dumps(R2.material_digest(m), sort_keys=True) for m in bpy.data.materials}
        out["modifiers"] = {o.name: [m.name for m in o.modifiers] for o in bpy.data.objects}
        out["children"] = {o.name: sorted(c.name for c in o.children) for o in bpy.data.objects}
        return out
    before = snapshot()
    made = FH.add_missing_halos(list(bpy.context.scene.objects))
    check("build halo call without presets/4: adds nothing", made == [], [o.name for o in made])
    check("build halo call without presets/4: every datablock, graph and modifier unchanged", snapshot() == before)
    check("build halo call without presets/4: no halo group created", bpy.data.node_groups.get(HALO_GROUP) is None)
    src = open(os.path.join(CHARSYS, "build_character.py"), encoding="utf-8").read()
    check("build_character calls the pass once, after organise and before the master is stamped",
          src.count("MATERIALS_HALO.add_missing_halos(") == 1 and
          src.index("subs, unassigned = organise(C, cid, components)") < src.index("MATERIALS_HALO.add_missing_halos(") <
          src.index('stamp(C, spec, info, "master")', src.index("def main_generic")))
    gen = open(os.path.join(CHARSYS, "garments", "generator.py"), encoding="utf-8").read()
    check("garment generator accepts later preset families through is_known_preset",
          "material_builder.is_known_preset(name)" in gen)

    # 2. opt-in through the fibre path
    bpy.ops.wm.read_factory_settings(use_empty=True)
    lib = M.load_felt_library()
    fabric = [n for n, p in lib["presets"].items() if p["fibres"]["enabled"]]
    for name in fabric:
        ob = sphere("src_" + name.replace("/", "_").replace(" ", "_"))
        mat = M.build_material("M_" + name, name, lib["presets"][name]["swatch_srgb"], 0.256)
        ob.data.materials.append(mat)
        check(f"{name}: material tagged presets/4 with its halo assignment",
              mat.get("ps_material_family") == "presets/4" and json.loads(mat[FH.HALO_MATERIAL_PROP])["preset"] == name)
        fb = M.add_fibres_geometry(ob, name, lib["presets"][name]["swatch_srgb"], 0.256)
        mods = [m for m in fb.modifiers if m.type == "NODES"]
        check(f"{name}: surface fibres + one shared halo on the same object",
              [m.node_group.name for m in mods] == ["PS Shared Surface Fibres/1", HALO_GROUP] and
              len(fb.data.materials) == 2 and fb.get(FH.HALO_OBJECT_PROP) == ob.name)
        again = M.add_fibres_geometry(ob, name, lib["presets"][name]["swatch_srgb"], 0.256)
        check(f"{name}: a second fibre layer on the same surface adds no second halo", not halo_mods(again))
    groups = sorted(g.name for g in bpy.data.node_groups if g.bl_idname == "GeometryNodeTree")
    check("one shared halo group for every surface", groups == sorted(["PS Shared Surface Fibres/1", HALO_GROUP]), groups)
    skin_src = sphere("src_skin4_fibre_path")
    only = M.add_fibres_geometry(skin_src, "felt skin/4", [236, 190, 166], 0.29)
    check("felt skin/4 through the fibre path: a halo-only object",
          only is not None and [m.node_group.name for m in only.modifiers] == [HALO_GROUP])
    check("LOD off: no fibres, no halo", M.add_fibres_geometry(sphere("src_off"), "felt/4", lod="off") is None)
    wide = M.add_fibres_geometry(sphere("src_wide"), "felt/4", lod="wide")
    close = M.add_fibres_geometry(sphere("src_close"), "felt/4", lod="close")
    check("wide LOD lowers the halo density",
          mod_input(halo_mods(wide)[0], "Density") < mod_input(halo_mods(close)[0], "Density"))
    hoodie = halo_mods(bpy.data.objects["src_hoodie_fleece_4.fibres"])[0]
    trousers = halo_mods(bpy.data.objects["src_trouser_pile_4.fibres"])[0]
    check("per-preset density and length", (mod_input(hoodie, "Density"), mod_input(hoodie, "Length")) !=
          (mod_input(trousers, "Density"), mod_input(trousers, "Length")))

    # 3. skin pass
    bpy.ops.wm.read_factory_settings(use_empty=True)
    body = sphere("body_skin", 0.1)
    skin = R2.face_like("M_skin4")
    M.apply_preset(skin, "felt skin/4", [236, 190, 166], 0.29, preserve_base_color=True)
    lips = bpy.data.materials.new("M_lips")
    body.data.materials.append(skin)
    body.data.materials.append(lips)
    for i, poly in enumerate(body.data.polygons):
        poly.material_index = 1 if poly.center.z < -0.05 else 0
    plain = sphere("plain_old_preset", 0.05)
    plain.data.materials.append(M.build_material("M_felt1", "felt", [200, 100, 80], 0.2))
    garment = sphere("garment.piece", 0.05)
    garment["ps_garment_item"] = "hoodie"
    garment.data.materials.append(M.build_material("M_g4", "felt/4", [200, 100, 80], 0.2))
    made = FH.add_missing_halos(list(bpy.context.scene.objects))
    check("skin pass: one halo, on the skin mesh only", [o[FH.HALO_OBJECT_PROP] for o in made] == ["body_skin"],
          [o.name for o in made])
    mod = halo_mods(made[0])[0] if made else None
    check("skin pass: restricted to the skin material's faces on a multi-material mesh",
          mod is not None and mod_input(mod, "Use Selection") is True and mod_input(mod, "Selection Material") == skin)
    check("skin pass: parented to the mesh with an identity transform",
          made and made[0].parent == body and made[0].matrix_basis == made[0].matrix_basis.Identity(4))
    check("skin pass: idempotent", FH.add_missing_halos(list(bpy.context.scene.objects)) == [])
    deps = bpy.context.evaluated_depsgraph_get()
    ev = made[0].evaluated_get(deps)
    curves = ev.data
    n = len(curves.curves)
    sel_z = [curves.points[c.first_point_index].position.z for c in curves.curves]
    check("halo evaluates to curves", n > 100, n)
    check("halo fibres only on the skin faces", n and min(sel_z) > -0.07, round(min(sel_z), 4) if n else None)
    attrs = {a.name: a.domain for a in curves.attributes}
    check("per-curve root normal and tone attributes",
          attrs.get(FH.HALO_NORMAL_ATTRIBUTE) == "CURVE" and attrs.get(FH.HALO_TONE_ATTRIBUTE) == "CURVE", attrs)
    lengths = []
    for c in list(curves.curves)[:200]:
        a, b = curves.points[c.first_point_index].position, curves.points[c.first_point_index + c.points_length - 1].position
        lengths.append((b - a).length)
    hl = lib["presets"]["felt skin/4"]["halo"]["length_mm"] / 1000 * 0.29 / 0.256
    check("halo fibre length follows the preset (x reference scale)", hl * 0.4 < sum(lengths) / len(lengths) < hl * 1.6,
          (round(sum(lengths) / len(lengths), 5), round(hl, 5)))
    hm = [m for m in made[0].data.materials if m]
    check("halo material: silhouette weight and tip fade",
          len(hm) == 1 and hm[0].get("ps_felt_halo_material") and
          any(n.type == "ATTRIBUTE" and n.attribute_name == FH.HALO_NORMAL_ATTRIBUTE for n in hm[0].node_tree.nodes))

    # 4. felt skin/4 layers
    nodes = skin.node_tree.nodes
    p = next(n for n in nodes if n.type == "BSDF_PRINCIPLED" and not n.name.startswith("PS "))
    check("felt skin/4: emission disconnected and zero",
          not p.inputs["Emission Strength"].links and p.inputs["Emission Strength"].default_value == 0.0)
    for label in ("Skin Crease Occlusion", "Skin Flock", "Skin Warmth Occlusion", "Skin Warmth Mix"):
        check(f"felt skin/4: {label} node", nodes.get("PS " + label) is not None)
    check("felt skin/4: blush graph still feeds the albedo", nodes.get("blush").outputs["Result"].links)
    check("felt skin/4: roughness from the patch", abs(p.inputs["Roughness"].default_value -
                                                       lib["presets"]["felt skin/4"]["surface"]["roughness"]) < 1e-6)
    count = len(nodes)
    M.apply_preset(skin, "felt skin/4", [236, 190, 166], 0.29, preserve_base_color=True)
    check("felt skin/4: re-apply is idempotent", len(skin.node_tree.nodes) == count)

    print(f"[test_felt_surface_graphs] {'ALL PASS' if all(RESULTS) else 'FAIL'} ({sum(RESULTS)}/{len(RESULTS)})")
    sys.exit(0 if all(RESULTS) else 1)


if __name__ == "__main__":
    main()
