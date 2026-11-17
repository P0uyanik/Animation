"""Blender integration checks for the T-020 shared renderer selector.

Run with:
  blender -b --factory-startup -P pipeline/charsys/tests/test_render_engine.py
"""
import os
import sys

import bpy

CHARSYS = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, CHARSYS)
import render_engine  # noqa: E402


scene = bpy.context.scene
cycles = render_engine.configure(scene, "cycles", 7)
assert scene.render.engine == "CYCLES"
assert scene.cycles.samples == 7
assert scene.cycles.use_denoising
assert cycles["engine"] == "cycles"

bpy.ops.object.light_add(type="AREA")
eevee = render_engine.configure(scene, "eevee", 9)
assert scene.render.engine == "BLENDER_EEVEE"
assert scene.eevee.taa_render_samples == 9
assert scene.eevee.use_shadows and scene.eevee.shadow_ray_count == 4
assert scene.eevee.use_fast_gi and scene.eevee.fast_gi_method == "AMBIENT_OCCLUSION_ONLY"
assert bpy.context.object.data.use_shadow_jitter
assert eevee["soft_shadows"] and eevee["ambient_occlusion"] and not eevee["bloom"]
print("[test_render_engine] ALL PASS")
