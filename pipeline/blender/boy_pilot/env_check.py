"""Checks a Blender installation for the pilot scripts (headless): version, Python, numpy, Rigify, required APIs.
    blender -b --factory-startup -P pipeline/blender/boy_pilot/env_check.py -- <out.json>"""
import json
import sys

import bpy

out = sys.argv[sys.argv.index("--") + 1]
r = {"blender": bpy.app.version_string, "version": list(bpy.app.version), "background": bpy.app.background,
     "python": sys.version.split()[0], "build_platform": str(bpy.app.build_platform)}
try:
    import numpy
    r["numpy"] = numpy.__version__
except Exception as e:  # pragma: no cover
    r["numpy"] = f"missing: {e}"
try:
    import addon_utils
    addon_utils.enable("rigify", default_set=True)
    r["rigify"] = "rigify" in bpy.context.preferences.addons
except Exception as e:
    r["rigify"] = f"error: {e}"
checks = {  # APIs the pilot scripts use
    "Mesh.shade_smooth (4.1+)": hasattr(bpy.types.Mesh, "shade_smooth"),
    "hair curves": hasattr(bpy.data, "hair_curves"),
    "OBJ importer": hasattr(bpy.ops.wm, "obj_import"),
    "glTF exporter": hasattr(bpy.ops.export_scene, "gltf"),
}


def try_set(obj, attr, value):
    try:
        setattr(obj, attr, value)
        return getattr(obj, attr) == value
    except Exception:
        return False


checks["Cycles"] = try_set(bpy.context.scene.render, "engine", "CYCLES")  # engine and view enums are dynamic
checks["AgX view transform"] = try_set(bpy.context.scene.view_settings, "view_transform", "AgX")
m = bpy.data.materials.new("check")
m.use_nodes = True
p = m.node_tree.nodes.get("Principled BSDF")
for name in ("Specular IOR Level", "Sheen Weight", "Subsurface Weight", "Subsurface Scale", "Coat Weight"):
    checks[f"Principled input '{name}' (4.0+)"] = p is not None and name in p.inputs
r["checks"] = checks
r["ok"] = r["background"] and r["rigify"] is True and all(checks.values()) and not str(r["numpy"]).startswith("missing")
json.dump(r, open(out, "w"), indent=1)
print("[env_check]", json.dumps(r))
