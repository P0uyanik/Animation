"""Blender-side checks of the T-066 presets/2 skin graph (headless; bpy or Blender 5.3).

    blender -b --factory-startup -P pipeline/charsys/tests/test_skin_material.py

1. a presets/1 material (skin-felt) gets no presets/2 node and no family tag (opt-in only);
2. skin-felt/2 on a face-like material that has an emissive "light bleed" link and a linked colour graph:
   the emission is disconnected and zero (no glowing creases), the original colour graph is still the root of the
   albedo chain (blush preserved), the crease and flock layers are present, the subsurface radius is warm;
3. re-applying the preset does not stack generated nodes (same node count).
Exit code 1 on any failure.
"""
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..")))
from materials import builder as MATERIALS  # noqa: E402

RESULTS = []


def check(name, ok, detail=None):
    RESULTS.append(bool(ok))
    print(f"[test_skin_material] {'PASS' if ok else 'FAIL'} {name}" + ("" if detail is None else f" {detail}"))


def face_like(name):
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
    links.new(ao.outputs["AO"], p.inputs["Emission Strength"])
    links.new(mix.outputs["Result"], p.inputs["Emission Color"])
    return m, p


def root_of(socket):
    """Follow the first colour input of each generated mix back to the first non-library node."""
    node = socket.links[0].from_node if socket.links else None
    seen = 0
    while node is not None and node.get("ps_material_library") and seen < 50:
        seen += 1
        nxt = None
        for inp in node.inputs:
            if inp.links and inp.type == "RGBA":
                nxt = inp.links[0].from_node
                break
        node = nxt
    return node


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    v1 = MATERIALS.build_material("M_v1", "skin-felt", (202, 176, 169))
    names = [n.name for n in v1.node_tree.nodes]
    check("presets/1: no skin-family nodes", not any(n.startswith("PS Skin") for n in names))
    check("presets/1: no family tag", "ps_material_family" not in v1.keys())

    m, p = face_like("M_face")
    MATERIALS.apply_preset(m, "skin-felt/2", (232, 194, 176), 0.29, preserve_base_color=True)
    check("family tag", m.get("ps_material_family") == "presets/2")
    check("emission disconnected", not p.inputs["Emission Strength"].links and not p.inputs["Emission Color"].links)
    check("emission strength zero", p.inputs["Emission Strength"].default_value == 0.0)
    nodes = {n.name for n in m.node_tree.nodes}
    check("crease + flock layers", {"PS Skin Crease Occlusion", "PS Skin Crease Warmth", "PS Skin Flock"} <= nodes)
    root = root_of(p.inputs["Base Color"])
    check("blush graph preserved at the root of the albedo chain", root is not None and root.name == "blush",
          None if root is None else root.name)
    radius = tuple(round(v, 3) for v in p.inputs["Subsurface Radius"].default_value)
    check("warm subsurface radius (red leads)", radius[0] > radius[1] > radius[2], radius)
    check("matte", p.inputs["Roughness"].default_value >= 0.6 or p.inputs["Roughness"].links)
    before = len(m.node_tree.nodes)
    MATERIALS.apply_preset(m, "skin-felt/2", (232, 194, 176), 0.29, preserve_base_color=True)
    check("re-apply is idempotent", len(m.node_tree.nodes) == before, (before, len(m.node_tree.nodes)))

    ok = all(RESULTS)
    print(f"[test_skin_material] {'PASS' if ok else 'FAIL'} {sum(RESULTS)}/{len(RESULTS)}")
    sys.exit(0 if ok else 1)


main()
