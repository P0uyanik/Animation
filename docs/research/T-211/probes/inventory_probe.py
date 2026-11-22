"""T-211 probe A: which built-in Blender 5.3 features used by the face plan exist and run headless (factory startup).
blender -b --factory-startup -P inventory_probe.py -- out.json"""
import json, sys, time, addon_utils, bpy
out = {"version": bpy.app.version_string, "autoexec": bpy.app.autoexec_fail is not None and not bpy.context.preferences.filepaths.use_scripts_auto_execute}
def has(path):
    mod, _, name = path.rpartition(".")
    try:
        return hasattr(eval("bpy.ops." + mod), name) and bool(getattr(eval("bpy.ops." + mod), name).get_rna_type())
    except Exception:
        return False
ops = ["object.modifier_apply_as_shapekey", "object.shape_key_add", "object.shape_key_mirror", "object.shape_key_transfer",
       "object.join_shapes", "object.surfacedeform_bind", "object.meshdeform_bind", "object.correctivesmooth_bind",
       "object.geometry_nodes_input_attribute_toggle", "object.geometry_node_bake_single", "geometry.execute_node_group",
       "grease_pencil.trace_image", "gpencil.trace_image", "image.import_as_mesh_planes", "import_image.to_plane",
       "poselib.create_pose_asset", "poselib.apply_pose_asset", "poselib.blend_pose_asset", "object.make_override_library",
       "clip.solve_camera", "clip.track_markers", "import_fspy.import_project", "pose.rigify_generate", "object.data_transfer",
       "object.vertex_group_normalize_all", "paint.weight_from_bones", "object.shape_key_lock", "object.shape_key_make_basis",
       "object.blend_from_shape", "mesh.blend_from_shape"]
out["ops"] = {o: has(o) for o in ops}
mods = {}
for name in ("rigify", "pose_library", "io_import_images_as_planes"):
    try:
        mods[name] = {"enable": bool(addon_utils.enable(name, default_set=True))}
    except Exception as e:
        mods[name] = {"error": repr(e)[:120]}
out["addons"] = mods
out["ops_after_rigify"] = {o: has(o) for o in ("pose.rigify_generate",)}
try:
    import rigify.rig_lists as rl
    names = sorted(rl.rigs.keys())
    out["rigify_face_rigs"] = [n for n in names if n.startswith(("face", "faces", "skin"))]
except Exception as e:
    out["rigify_face_rigs"] = repr(e)[:150]
bpy.ops.wm.read_factory_settings(use_empty=True)
out["ops_after_reset"] = {o: has(o) for o in ("poselib.create_pose_asset", "grease_pencil.trace_image")}
# drivers: simple expressions run without Python auto-exec
sc = bpy.context.scene
ob = bpy.data.objects.new("e", None); sc.collection.objects.link(ob)
ob["a"], ob["b"] = 0.6, 0.5
res = {}
for i, expr in enumerate(["a*b", "min(a, b)", "clamp((a - 0.2) / 0.6) * b", "smoothstep(0.0, 1.0, a) * b", "pow(a, 2.0)*b"]):
    ob[f"r{i}"] = 0.0
    d = ob.driver_add(f'["r{i}"]').driver
    d.type = "SCRIPTED"
    for v in "ab":
        var = d.variables.new(); var.name = v; var.type = "SINGLE_PROP"
        var.targets[0].id = ob; var.targets[0].data_path = f'["{v}"]'
    d.expression = expr
    bpy.context.view_layer.update(); sc.frame_set(1)
    res[expr] = {"simple": d.is_simple_expression, "valid": d.is_valid, "value": round(ob[f"r{i}"], 4)}
out["drivers_autoexec_off"] = res
out["use_scripts_auto_execute"] = bpy.context.preferences.filepaths.use_scripts_auto_execute
# render engines available
out["engines"] = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
out["cryptomatte_props"] = [p for p in ("use_pass_cryptomatte_object", "use_pass_cryptomatte_material", "use_pass_object_index") if hasattr(bpy.context.view_layer, p)]
json.dump(out, open(sys.argv[sys.argv.index("--") + 1], "w"), indent=1)
print(json.dumps(out, indent=1))
