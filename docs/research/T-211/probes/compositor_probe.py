"""T-211 probe D: compositor object-index mask in background mode (Cycles CPU, 1 sample, 64 px cube scene).
blender -b --factory-startup -P compositor_probe.py -- <scratch dir>"""
import json, os, sys, time
import bpy, numpy as np
tmp = sys.argv[sys.argv.index("--") + 1]; os.makedirs(tmp, exist_ok=True)
sc = bpy.context.scene
bpy.data.objects["Cube"].pass_index = 2
sc.render.engine = "CYCLES"; sc.cycles.samples = 1; sc.cycles.device = "CPU"
sc.render.resolution_x = sc.render.resolution_y = 64
vl = sc.view_layers[0]; vl.use_pass_object_index = True
tree = bpy.data.node_groups.new("comp", "CompositorNodeTree"); sc.compositing_node_group = tree
N = tree.nodes; rl = N.new("CompositorNodeRLayers")
out = {"rlayer_outputs": [o.name for o in rl.outputs if o.enabled]}
idm = N.new("CompositorNodeIDMask"); out["idmask_inputs"] = [i.name for i in idm.inputs]
idx = next(o for o in rl.outputs if o.name in ("IndexOB", "Object Index"))
tree.links.new(idx, idm.inputs[0])
if "Index" in idm.inputs:
    idm.inputs["Index"].default_value = 2
else:
    idm.index = 2
vw = N.new("CompositorNodeViewer"); tree.links.new(idm.outputs[0], vw.inputs[0])
tree.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
go = N.new("NodeGroupOutput"); tree.links.new(idm.outputs[0], go.inputs[0])
sc.render.filepath = os.path.join(tmp, "idmask.png")
t = time.perf_counter(); bpy.ops.render.render(write_still=True); out["render_s"] = round(time.perf_counter() - t, 2)
v = bpy.data.images.get("Viewer Node")
out["viewer_node_pixels_in_background"] = len(v.pixels) if v else None
px = np.array(bpy.data.images.load(sc.render.filepath).pixels[:]).reshape(64, 64, -1)
out["file_mask_px"] = int((px[..., 0] > 0.5).sum())
rr = bpy.data.images.get("Render Result"); out["render_result_pixels"] = len(rr.pixels) if rr else None
print("OUT", json.dumps(out))
