"""T-206 wool-hair probe (scratch only). blender -b --factory-startup -P hair_probe.py -- <out> <blend> <variant> [px] [spp]
variants: base | lowvol | yarn | combed (combed = blend already processed by groom/hair_curves.py; lowvol applied too)"""
import math, os, sys, time, json, hashlib
import bpy, numpy as np
from mathutils import Vector
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "pipeline", "charsys"))
import render_calibration as RC, render_engine
a = sys.argv[sys.argv.index("--") + 1:]
out, blend, variant = a[0], a[1], a[2]
px = int(a[3]) if len(a) > 3 else 640; spp = int(a[4]) if len(a) > 4 else 16
bpy.ops.wm.open_mainfile(filepath=blend)
sc = bpy.context.scene
rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
for k in [k for k in rig.keys() if k.startswith("face_")]:
    rig[k] = 0.0
def set_in(m, name, fn):
    g = m.node_group
    s = next(i for i in g.interface.items_tree if i.item_type == "SOCKET" and i.in_out == "INPUT" and i.name == name)
    p = getattr(m.properties.inputs, s.identifier); old = p.value; p.value = fn(old); return old, p.value
log = {"variant": variant}
if variant in ("lowvol", "yarn", "combed"):
    ch = []
    for o in bpy.data.objects:
        if o.type == "CURVES" and o.name.startswith("hair_") and ".fibres" in o.name and o.modifiers and o.modifiers[0].type == "NODES" and o.modifiers[0].node_group and "Surface Fibres" in o.modifiers[0].node_group.name:
            m = o.modifiers[0]
            L = getattr(m.properties.inputs, next(i for i in m.node_group.interface.items_tree if i.item_type=="SOCKET" and i.in_out=="INPUT" and i.name=="Length").identifier).value
            if L > 0.006:   # flyaway layer
                ch.append((o.name, "fly", set_in(m, "Density", lambda v: v * 0.2)))
            else:           # felt layer: shorter, a bit sparser
                ch.append((o.name, "felt", set_in(m, "Length", lambda v: v * 0.5), set_in(m, "Density", lambda v: v * 0.7)))
    log["fibre_changes"] = len(ch)
if variant == "yarn":
    # striations along the plied rope: bands across U of the ps_fibre UV (V runs along the rope), wobbled by noise
    mat = bpy.data.materials["M_hair"]; nt = mat.node_tree
    bump = next(n for n in nt.nodes if n.bl_idname == "ShaderNodeBump")
    uv = nt.nodes.new("ShaderNodeUVMap"); uv.uv_map = "ps_fibre"
    sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(uv.outputs[0], sep.inputs[0])
    noi = nt.nodes.new("ShaderNodeTexNoise"); noi.inputs["Scale"].default_value = 40.0
    nt.links.new(uv.outputs[0], noi.inputs["Vector"])
    mul = nt.nodes.new("ShaderNodeMath"); mul.operation = "MULTIPLY_ADD"
    nt.links.new(sep.outputs[0], mul.inputs[0]); mul.inputs[1].default_value = 1.0
    nt.links.new(noi.outputs["Fac"], mul.inputs[2])
    sin = nt.nodes.new("ShaderNodeMath"); sin.operation = "SINE"
    sc2 = nt.nodes.new("ShaderNodeMath"); sc2.operation = "MULTIPLY"; sc2.inputs[1].default_value = 2 * math.pi * float(os.environ.get("YARN_FREQ", "600"))
    nt.links.new(mul.outputs[0], sc2.inputs[0]); nt.links.new(sc2.outputs[0], sin.inputs[0])
    b2 = nt.nodes.new("ShaderNodeBump"); b2.inputs["Strength"].default_value = float(os.environ.get("YARN_STRENGTH", "0.6")); b2.inputs["Distance"].default_value = 0.0006
    nt.links.new(sin.outputs[0], b2.inputs["Height"])
    if bump.inputs["Normal"].is_linked:
        nt.links.new(bump.inputs["Normal"].links[0].from_socket, b2.inputs["Normal"])
    nt.links.new(b2.outputs["Normal"], bump.inputs["Normal"])
    log["yarn"] = {"freq_per_uv": os.environ.get("YARN_FREQ", "600"), "strength": os.environ.get("YARN_STRENGTH", "0.6")}
# camera + light as T-202 face_views.py
for o in list(sc.objects):
    if o.type in ("LIGHT", "CAMERA"):
        bpy.data.objects.remove(o, do_unlink=True)
lrig = RC.apply(sc, RC.load(RC.DEFAULT))
render_engine.configure(sc, "cycles", spp, cycles_device="CPU", cycles_denoiser="OPENIMAGEDENOISE")
sc.cycles.seed = 0; sc.render.threads_mode = "AUTO"
cam = bpy.data.objects.new("C", bpy.data.cameras.new("C")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.lens, cam.data.sensor_fit, cam.data.sensor_height = 70.0, "VERTICAL", 36.0
fov = 2 * math.atan(18.0 / 70.0); target = Vector((0, 0, 0.84)); fh = 0.66
# strand census (evaluated) + hash of hair_curves points (determinism of the strand set)
dg = bpy.context.evaluated_depsgraph_get(); n = 0; h = hashlib.sha256()
for o in sorted(bpy.data.objects, key=lambda o: o.name):
    if o.type == "CURVES" and o.name.startswith("hair_"):
        e = o.evaluated_get(dg); n += len(e.data.curves)
        if ".hair_curves" in o.name:
            p = np.empty(len(e.data.points) * 3, np.float32); e.data.points.foreach_get("position", p); h.update(p.tobytes())
log["hair_strands_eval"] = n; log["hair_curves_sha"] = h.hexdigest()[:16]
os.makedirs(out, exist_ok=True); log["renders"] = {}
for yaw, elev in ((0, 5), (-45, 5)):
    ya, el = math.radians(yaw), math.radians(elev)
    d = Vector((math.sin(ya) * math.cos(el), -math.cos(ya) * math.cos(el), math.sin(el)))
    cam.location = target + d * (fh / 2 / math.tan(fov / 2)); cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    RC.orient(lrig, d)
    sc.render.resolution_x = sc.render.resolution_y = px; sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.filepath = os.path.join(out, "%s%s_%+04d.png" % (variant, os.environ.get("TAG", ""), yaw))
    t = time.time(); bpy.ops.render.render(write_still=True); log["renders"][yaw] = round(time.time() - t, 1)
json.dump(log, open(os.path.join(out, variant + os.environ.get("TAG", "") + ".json"), "w"), indent=1)
print("PROBE", json.dumps(log))
