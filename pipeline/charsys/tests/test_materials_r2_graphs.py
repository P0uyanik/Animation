"""Blender-side checks of the T-092 presets/3 family (headless; bpy or Blender 5.3).

    blender -b --factory-startup -P pipeline/charsys/tests/test_materials_r2_graphs.py

1. every presets/1 and presets/2 id builds exactly as on the input SHA: the shader graph of a fresh material, the
   graph after applying the preset onto a material with a linked colour graph (preserve_base_color), the generated
   fibre object (shared node group, modifier inputs, fibre material graph) are compared, node for node and value for
   value, with the golden digests in pipeline/charsys/materials/r2_frozen_graphs.json (written once from the input
   SHA's builder with --write-golden). Same Blender + identical graphs = identical swatch renders;
2. every presets/3 fabric id gets exactly one uniform fibre halo through the existing shared Geometry Nodes group
   (PS Shared Surface Fibres/1): one fibre object per surface, no second node group, a family tag presets/3;
3. skin-felt/3: non-emissive, the presets/2 skin layers plus the occlusion warmth node, family tag, idempotent.
Exit code 1 on any failure.

    blender -b --factory-startup -P pipeline/charsys/tests/test_materials_r2_graphs.py -- \
        --write-golden <out.json> --charsys <checkout>/pipeline/charsys --sha <input sha>
"""
import argparse
import hashlib
import json
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
CHARSYS = os.path.abspath(os.path.join(HERE, ".."))
GOLDEN = os.path.join(CHARSYS, "materials", "r2_frozen_graphs.json")
SHARED_GROUP = "PS Shared Surface Fibres/1"

RESULTS = []


def check(name, ok, detail=None):
    RESULTS.append(bool(ok))
    print(f"[test_materials_r2_graphs] {'PASS' if ok else 'FAIL'} {name}" + ("" if detail is None else f" {detail}"))


def parse():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--write-golden", default="")
    p.add_argument("--charsys", default=CHARSYS)
    p.add_argument("--sha", default="")
    return p.parse_args(argv)


def _value(v):
    if isinstance(v, bool) or v is None or isinstance(v, (int, str)):
        return v
    if isinstance(v, float):
        return round(v, 6)
    if hasattr(v, "name") and hasattr(v, "bl_rna") and not hasattr(v, "__len__"):
        return "<id:" + v.name + ">"
    try:
        return [_value(x) for x in v]
    except TypeError:
        return str(v)


NODE_PROPS = ("operation", "blend_type", "clamp", "use_clamp", "interpolation_type", "data_type", "noise_dimensions",
              "noise_type", "musgrave_dimensions", "wave_type", "bands_direction", "rings_direction", "wave_profile",
              "feature", "distance", "voronoi_dimensions", "samples", "only_local", "inside", "attribute_type",
              "attribute_name", "uv_map", "parametrization", "model", "distribution", "subsurface_method",
              "transform_space", "distribute_method", "mode", "vector_type", "normalize", "domain")


def tree_digest(tree):
    nodes = []
    for n in sorted(tree.nodes, key=lambda n: n.name):
        props = {k: _value(getattr(n, k)) for k in NODE_PROPS if hasattr(n, k)}
        custom = {k: _value(n[k]) for k in n.keys()}
        inputs = {}
        for i, s in enumerate(n.inputs):
            if hasattr(s, "default_value") and not s.is_linked:
                inputs[f"{i}:{s.identifier}"] = _value(s.default_value)
        nodes.append({"name": n.name, "type": n.bl_idname, "label": n.label, "props": props, "custom": custom,
                      "inputs": inputs})
    links = sorted(f"{l.from_node.name}.{l.from_socket.identifier}->{l.to_node.name}.{l.to_socket.identifier}"
                   for l in tree.links)
    return {"nodes": nodes, "links": links}


def material_digest(m):
    return {"tree": tree_digest(m.node_tree), "custom": {k: _value(m[k]) for k in m.keys()},
            "surface_render_method": getattr(m, "surface_render_method", None)}


def face_like(name):
    """A material with a linked colour graph and an emissive bleed, as face_generic builds before apply."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nodes, links = m.node_tree.nodes, m.node_tree.links
    p = nodes.get("Principled BSDF")
    mix = nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.name = "blush"
    mix.inputs["A"].default_value = (0.8, 0.55, 0.45, 1)
    mix.inputs["B"].default_value = (0.8, 0.2, 0.2, 1)
    links.new(mix.outputs["Result"], p.inputs["Base Color"])
    ao = nodes.new("ShaderNodeAmbientOcclusion")
    ao.name = "bleed"
    links.new(ao.outputs["AO"], p.inputs["Emission Strength"])
    return m


def surface(name):
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=4, y_subdivisions=4, size=0.1)
    ob = bpy.context.object
    ob.name = name
    return ob


def fibre_digest(fb):
    if fb is None:
        return None
    mod = fb.modifiers["PS Surface Fibres"]
    group = mod.node_group
    inputs = {}
    for item in group.interface.items_tree:
        if item.item_type == "SOCKET" and item.in_out == "INPUT":
            inputs[item.name] = _value(getattr(mod.properties.inputs, item.identifier).value)
    mats = [material_digest(m) for m in fb.data.materials if m]
    return {"group": group.name, "group_tree": hashlib.sha256(json.dumps(tree_digest(group), sort_keys=True)
                                                              .encode()).hexdigest(),
            "inputs": inputs, "materials": mats, "custom": {k: _value(fb[k]) for k in fb.keys()}}


def digest_id(M, name):
    library = M.library_for(name)
    preset = library["presets"][name]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    fresh = M.build_material("M_" + name, name, preset["swatch_srgb"], library["reference_size_m"])
    linked = face_like("M_linked_" + name)
    M.apply_preset(linked, name, preset["swatch_srgb"], library["reference_size_m"], preserve_base_color=True)
    ob = surface("src_" + name.replace("/", "_"))
    fb = M.add_fibres_geometry(ob, name, preset["swatch_srgb"], library["reference_size_m"])
    data = {"fresh": material_digest(fresh), "linked": material_digest(linked), "fibres": fibre_digest(fb)}
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest(), data


def import_builder(charsys):
    sys.path.insert(0, charsys)
    from materials import builder as M
    return M


def frozen_ids(M):
    ids = list(M.load_library()["presets"])
    ids += list(M.load_skin_library()["presets"])
    return ids


def write_golden(args):
    M = import_builder(os.path.abspath(args.charsys))
    out = {"schema": "plush-studio.material-graph-golden/1", "task": "T-092",
           "note": "Node-graph digests (ids) and resolved-preset digests (resolved) of every presets/1 and presets/2 id, written from the input SHA's builder "
                   "(test_materials_r2_graphs.py --write-golden). Never regenerate from a branch that changes them.",
           "input_sha": args.sha, "blender": bpy.app.version_string, "ids": {}}
    out["resolved"] = {}
    for name in frozen_ids(M):
        out["ids"][name] = digest_id(M, name)[0]
        out["resolved"][name] = hashlib.sha256(json.dumps(M.resolve_preset(name), sort_keys=True).encode()).hexdigest()
    with open(args.write_golden, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print(f"[test_materials_r2_graphs] wrote {len(out['ids'])} digests to {args.write_golden}")


def main():
    args = parse()
    if args.write_golden:
        write_golden(args)
        return
    M = import_builder(CHARSYS)
    golden = json.load(open(GOLDEN, encoding="utf-8"))
    ids = frozen_ids(M)
    check("golden covers every presets/1 and presets/2 id", sorted(golden["ids"]) == sorted(ids),
          sorted(set(ids) ^ set(golden["ids"])))
    for name in ids:
        digest, _ = digest_id(M, name)
        check(f"{name}: graph unchanged vs input {golden.get('input_sha')}", golden["ids"].get(name) == digest)
        check(f"{name}: no presets/3 family tag", M.resolve_preset(name).get("family") != M.R2_FAMILY)

    r2 = M.load_r2_library()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    fabric = [n for n, p in r2["presets"].items() if "skin" not in p]
    fibre_objects = []
    for name in fabric:
        preset = r2["presets"][name]
        mat = M.build_material("M_" + name, name, preset["swatch_srgb"], r2["reference_size_m"])
        check(f"{name}: family tag presets/3", mat.get("ps_material_family") == M.R2_FAMILY)
        ob = surface("src_" + name.replace("/", "_"))
        fb = M.add_fibres_geometry(ob, name, preset["swatch_srgb"], r2["reference_size_m"])
        check(f"{name}: one fibre halo object", fb is not None and fb["ps_fibres_source"] == ob.name)
        if fb is None:
            continue
        mod = [m for m in fb.modifiers if m.type == "NODES"]
        check(f"{name}: through the shared group {SHARED_GROUP}",
              len(mod) == 1 and mod[0].node_group.name == SHARED_GROUP, [m.node_group.name for m in mod])
        fibre_objects.append(fb)
    groups = [g.name for g in bpy.data.node_groups if g.bl_idname == "GeometryNodeTree"]
    check("no new fibre system (a single Geometry Nodes group)", groups == [SHARED_GROUP], groups)
    check("one fibre object per fabric surface", len(fibre_objects) == len(fabric) and
          len({f["ps_fibres_source"] for f in fibre_objects}) == len(fabric))

    skin = face_like("M_skin3")
    M.apply_preset(skin, "skin-felt/3", [236, 196, 172], 0.29, preserve_base_color=True)
    nodes = skin.node_tree.nodes
    p = next(n for n in nodes if n.type == "BSDF_PRINCIPLED" and not n.name.startswith("PS "))
    check("skin-felt/3: emission disconnected and zero",
          not p.inputs["Emission Strength"].links and p.inputs["Emission Strength"].default_value == 0.0)
    for label in ("Skin Crease Occlusion", "Skin Flock", "Skin Warmth Occlusion", "Skin Warmth Mix"):
        check(f"skin-felt/3: {label} node", nodes.get("PS " + label) is not None)
    check("skin-felt/3: family tag presets/3", skin.get("ps_material_family") == M.R2_FAMILY)
    check("skin-felt/3: blush graph still feeds the albedo", nodes.get("blush").outputs["Result"].links)
    count = len(nodes)
    M.apply_preset(skin, "skin-felt/3", [236, 196, 172], 0.29, preserve_base_color=True)
    check("skin-felt/3: re-apply is idempotent", len(skin.node_tree.nodes) == count, (count, len(skin.node_tree.nodes)))
    radius = tuple(round(v, 3) for v in p.inputs["Subsurface Radius"].default_value)
    check("skin-felt/3: red-led subsurface radius", radius[0] > radius[1] > radius[2], radius)
    check("skin-felt/3: no fibre object (skin halo is the rim sheen)",
          M.add_fibres_geometry(surface("src_skin3"), "skin-felt/3") is None)

    print(f"[test_materials_r2_graphs] {'PASS' if all(RESULTS) else 'FAIL'} {sum(RESULTS)}/{len(RESULTS)}")
    sys.exit(0 if all(RESULTS) else 1)


if __name__ == "__main__":
    main()
