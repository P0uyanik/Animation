"""T-066 evaluation helper (headless Blender): apply a candidate's presets/2 skin assignment to a built master whose
build path does not read materials.assignments.skin (the frozen legacy body_v6/1 path of the boy).

    blender -b --factory-startup -P docs/evaluation/characters/T-066/apply_skin_candidate.py -- \
        <master.blend> <candidate.override.json> <out.blend>

For every material named in the candidate's ``legacy_post_build.materials`` the skin assignment is applied with the
shared builder (materials/builder.apply_from_assignment, the same call the generic path makes). A linked base-colour
graph (the legacy blush mix) keeps its shape: its skin input is set to the assignment's base colour and its blush
input to ``legacy_post_build.blush_srgb``. Evidence only; the master in assets/ is never touched.
"""
import json
import os
import sys

import bpy

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "pipeline", "charsys"))
from materials import builder as MATERIALS  # noqa: E402
from geom import srgb_to_linear  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:]
master, candidate, out = argv[:3]
if os.path.commonpath([os.path.abspath(out), os.path.join(ROOT, "assets")]) == os.path.join(ROOT, "assets"):
    raise SystemExit("refusing to write into assets/")
data = json.load(open(candidate))
assignment = data["override"]["materials"]["assignments"]["skin"]
post = data.get("legacy_post_build") or {}
bpy.ops.wm.open_mainfile(filepath=master)
done = []
for name in post.get("materials", []):
    material = bpy.data.materials.get(name)
    if material is None:
        raise SystemExit(f"material {name} not in {master}")
    principled = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    base = principled.inputs["Base Color"]
    mix = next((l.from_node for l in base.links if l.from_node.type == "MIX"), None)
    if mix is not None:  # legacy blush graph: skin -> blush by distance to the blush spots
        mix.inputs["A"].default_value = (*srgb_to_linear(tuple(assignment["base_color_srgb"])), 1)
        if post.get("blush_srgb"):
            mix.inputs["B"].default_value = (*srgb_to_linear(tuple(post["blush_srgb"])), 1)
    MATERIALS.apply_from_assignment(material, assignment, preserve_base_color=True)
    done.append(name)
bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(out), compress=True)
print(json.dumps({"applied": done, "preset": assignment["preset"]}))
