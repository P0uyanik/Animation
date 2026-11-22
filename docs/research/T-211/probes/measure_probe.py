"""T-211 probe C (read-only on the master; nothing saved): Blender built-ins for measuring a face without a detector.

    blender -b --factory-startup -P measure_probe.py -- <master.blend> <out.json> <scratch dir>

1. Render-free blink-closure check: from a camera at 5 yaws, rays (scene.ray_cast on the evaluated scene) towards
   points of the eyeball; an eyeball point is "visible" if the first hit is the eyeball. Blink 0 vs face_Blink = 1.
2. Landmark projection (world_to_camera_view) + occlusion (ray_cast) at 8 yaws.
3. Mask passes at 256 x 256 on the head: Workbench object colour (what tools/fit uses), Cycles 1 sample with
   Object Index + Cryptomatte, EEVEE; time and read-back of the files (bpy.data.images.load) and of the Viewer node.
4. BVH: closed-lid clearance to the eyeball (find_nearest) at Blink = 1."""
import json, math, os, sys, time
import bpy, numpy as np
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector
from mathutils.bvhtree import BVHTree

argv = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.open_mainfile(filepath=argv[0]); OUT, TMP = argv[1], argv[2]
os.makedirs(TMP, exist_ok=True)
R = {}
sc = bpy.context.scene
rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
lm = {o.name[3:]: o.matrix_world.translation.copy() for o in bpy.data.objects if o.name.startswith("LM_")}
centre = (lm["eye_L"] + lm["eye_R"]) / 2 * 0.5 + lm["mouth"] * 0.5
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.lens = 85


def place(yaw_deg, dist=1.0):  # yaw 0 = front (the face looks along -Y); + = towards the character's left
    a = math.radians(yaw_deg)
    cam.location = centre + Vector((math.sin(a) * dist, -math.cos(a) * dist, 0.0))
    cam.rotation_euler = (centre - cam.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.view_layer.update()


def eye_points(name):
    e = bpy.data.objects[name]
    return [e.matrix_world @ v.co for v in e.data.vertices]


def visible_fraction(name, yaw):
    place(yaw)
    dg = bpy.context.evaluated_depsgraph_get()
    pts = eye_points(name)
    o = cam.location
    facing = [p for p in pts if (p - o).dot(p - bpy.data.objects[name].matrix_world.translation) < 0]
    vis = 0
    for p in facing:
        d = (p - o); dist = d.length; d.normalize()
        hit, loc, nrm, idx, ob, _ = sc.ray_cast(dg, o, d, distance=dist + 1e-3)
        if hit and ob.original.name == name and (loc - p).length < 2e-3:
            vis += 1
    return vis, len(facing)


for nm in ("glasses", "glasses_lens"):  # the transparent lens is a ray hit too; tools/fit also omits it
    if nm in bpy.data.objects:
        bpy.data.objects[nm].hide_viewport = True
yaws = [-90, -45, 0, 45, 90]
t0 = time.perf_counter()
blink = {}
for val in (0.0, 1.0):
    rig["face_Blink"] = val; rig.update_tag(); bpy.context.view_layer.update()
    blink[str(val)] = {str(y): {s: "%d/%d" % visible_fraction(f"eye.{s}", y) for s in "LR"} for y in yaws}
R["blink_closure_raycast"] = {"visible_eyeball_points": blink, "s": round(time.perf_counter() - t0, 2)}

# BVH clearance of the closed upper lid to the eyeball
dg = bpy.context.evaluated_depsgraph_get()
def bvh(name):
    e = bpy.data.objects[name].evaluated_get(dg); me = e.to_mesh()
    t = BVHTree.FromPolygons([e.matrix_world @ v.co for v in me.vertices], [p.vertices[:] for p in me.polygons])
    vs = [e.matrix_world @ v.co for v in me.vertices]; e.to_mesh_clear(); return t, vs
eye_t, _ = bvh("eye.L"); _, lid_v = bvh("lid_upper.L")
gaps = [eye_t.find_nearest(v)[3] for v in lid_v]
R["closed_lid_to_eyeball_mm"] = {"min": round(1000 * min(gaps), 2), "median": round(1000 * float(np.median(gaps)), 2)}
rig["face_Blink"] = 0.0; rig.update_tag(); bpy.context.view_layer.update()

# Landmark projection + occlusion at 8 yaws
proj = {}
for y in (0, 45, 90, 135, 180, -135, -90, -45):
    place(y); dg = bpy.context.evaluated_depsgraph_get(); row = {}
    for k, p in lm.items():
        u = world_to_camera_view(sc, cam, p)
        d = p - cam.location; L = d.length; d.normalize()
        hit, loc, *_ = sc.ray_cast(dg, cam.location, d, distance=L - 2e-3)
        row[k] = [round(u.x, 3), round(u.y, 3), "occluded" if hit else "visible"]
    proj[str(y)] = row
for nm in ("glasses", "glasses_lens"):
    if nm in bpy.data.objects:
        bpy.data.objects[nm].hide_viewport = False
R["landmarks_projected"] = {k: proj[k] for k in ("0", "45", "90", "180")}

# Mask passes on a 256 px head crop
place(30, 0.9); sc.render.resolution_x = sc.render.resolution_y = 256; sc.render.resolution_percentage = 100
cam.data.lens = 120
sc.render.image_settings.file_format = "PNG"
names = {"body_skin": 1, "eye.L": 2, "eye.R": 3, "lid_upper.L": 4, "lid_upper.R": 4, "brow.L": 5, "brow.R": 5, "glasses": 6}
for o in bpy.data.objects:
    o.pass_index = names.get(o.name, 0)
rend = {}
def run(label, engine, setup):
    sc.render.engine = engine; setup()
    path = os.path.join(TMP, label + ".png"); sc.render.filepath = path
    t = time.perf_counter()
    try:
        bpy.ops.render.render(write_still=True)
        dt = time.perf_counter() - t
        img = bpy.data.images.load(path); px = np.array(img.pixels[:]).reshape(256, 256, -1)
        rend[label] = {"s": round(dt, 2), "readback_shape": list(px.shape), "nonzero_px": int((px[..., :3].sum(-1) > 0).sum())}
    except Exception as e:
        rend[label] = {"error": str(e)[:200], "s": round(time.perf_counter() - t, 2)}
def wb():
    d = sc.display; d.shading.light = "FLAT"; d.shading.color_type = "OBJECT"; d.render_aa = "OFF"
    for o in bpy.data.objects:
        o.color = (o.pass_index / 6, 0.5, 1 - o.pass_index / 6, 1)
run("workbench_object_colour", "BLENDER_WORKBENCH", wb)
def cy():
    sc.cycles.device = "CPU"; sc.cycles.samples = 1; sc.cycles.use_denoising = False
    vl = sc.view_layers[0]; vl.use_pass_object_index = True; vl.use_pass_cryptomatte_object = True
run("cycles_1spp_index_crypto", "CYCLES", cy)
def ee():
    sc.eevee.taa_render_samples = 1
if not os.environ.get("T211_SKIP_EEVEE"):
    run("eevee_1spp", "BLENDER_EEVEE", ee)
# Compositor: object-index mask through ID Mask -> File Output; Viewer node read-back in background mode
sc.render.engine = "CYCLES"
try:
    tree = bpy.data.node_groups.new("t211_comp", "CompositorNodeTree"); sc.compositing_node_group = tree
    N = tree.nodes; rl = N.new("CompositorNodeRLayers"); idm = N.new("CompositorNodeIDMask")
    if hasattr(idm, "index"):
        idm.index = 2
    else:
        idm.inputs["Index"].default_value = 2
    vw = N.new("CompositorNodeViewer")
    out_ = tree.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    go = N.new("NodeGroupOutput")
    tree.links.new(rl.outputs["IndexOB"], idm.inputs[0]); tree.links.new(idm.outputs[0], vw.inputs[0]); tree.links.new(idm.outputs[0], go.inputs[0])
    sc.render.filepath = os.path.join(TMP, "comp_idmask.png")
    t = time.perf_counter(); bpy.ops.render.render(write_still=True); dt = time.perf_counter() - t
    v = bpy.data.images.get("Viewer Node")
    vpx = len(v.pixels) if v else 0
    img = bpy.data.images.load(sc.render.filepath); px = np.array(img.pixels[:]).reshape(256, 256, -1)
    rend["compositor_idmask_eye.L"] = {"s": round(dt, 2), "viewer_node_pixels": vpx, "file_mask_px": int((px[..., 0] > 0.5).sum())}
except Exception as e:
    rend["compositor_idmask_eye.L"] = {"error": repr(e)[:240]}
R["mask_passes_256px"] = rend
json.dump(R, open(OUT, "w"), indent=1)
print(json.dumps(R, indent=1))
