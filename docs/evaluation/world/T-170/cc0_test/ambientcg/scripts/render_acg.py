"""T-170d throwaway (copy of T-170c render_cc0.py, ambientCG folders, optional per-candidate src/target): Cycles swatches of CC0 image sets (research evidence only; NOT pipeline code).

blender -b --factory-startup -P render_acg.py -- --tex <scratch> --out <dir> --mode raw|tweak [--only a,b] [--px 320] [--spp 64]
raw   = maps as downloaded at real-world scale, no colour change.
tweak = candidates.json "tweak" (scale, contrast, saturation, normal strength, roughness, coat/sheen) plus a linear RGB
        gain fitted in 3 low-sample passes so the lit top face lands on the T-170 reference patch colour.
Rig = T-170 swatch rig (window key screen-left 26 W, warm bounce, AgX medium-high contrast, 70 mm f/2.8) scaled with
the slab, plus the indoor HDRI as world (fill + reflections). Slab has UVs in metres (needed for tangent normal maps).
"""
import json, math, os, sys
import bpy, bmesh
import numpy as np
from mathutils import Vector
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
def arg(n, d):
    return argv[argv.index(n) + 1] if n in argv else d
TEX, OUT, MODE = arg("--tex", ""), arg("--out", ""), arg("--mode", "raw")
ONLY = [s for s in arg("--only", "").split(",") if s]; PX, SPP = int(arg("--px", 320)), int(arg("--spp", 64))
HDRI = arg("--hdri", "lebombo")
C = json.load(open(os.path.join(HERE, "candidates.json")))
REF = json.load(open(os.path.join(HERE, "..", "..", "..", "measurements.json")))["patches"]

def s2l(c):
    c = np.asarray(c, float) / 255; return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
def l2hex(c):
    c = np.clip(c, 0, 1); c = np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)
    return "#%02X%02X%02X" % tuple(int(round(x * 255)) for x in c)
def hexrgb(h):
    return [int(h[i:i + 2], 16) for i in (1, 3, 5)]

def img(path, data=False):
    i = bpy.data.images.load(path)
    if data:
        i.colorspace_settings.name = "Non-Color"
    return i

def material(name, t, gain):
    c = C["candidates"][name]; d = os.path.join(TEX, "acg_" + c.get("src", name))
    mean = s2l(np.asarray(Image.open(os.path.join(d, "diff.jpg")).convert("RGB")).reshape(-1, 3)).mean(0)
    m = bpy.data.materials.new(name); m.use_nodes = True; n, l = m.node_tree.nodes, m.node_tree.links; p = n["Principled BSDF"]
    uv = n.new("ShaderNodeUVMap"); mp = n.new("ShaderNodeMapping"); s = 1.0 / (c["dim"] * t.get("scale", 1.0))
    mp.inputs["Scale"].default_value = (s, s, s); mp.inputs["Rotation"].default_value = (0, 0, math.pi / 2 * c["rot"])
    l.new(uv.outputs[0], mp.inputs[0])
    def tex(f, data):
        x = n.new("ShaderNodeTexImage"); x.image = img(os.path.join(d, f), data); l.new(mp.outputs[0], x.inputs[0]); return x
    col = tex("diff.jpg", False).outputs["Color"]
    mix = n.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.inputs["Factor"].default_value = t.get("contrast", 1.0)
    mix.inputs["A"].default_value = list(mean) + [1]; l.new(col, mix.inputs["B"])
    hs = n.new("ShaderNodeHueSaturation"); hs.inputs["Saturation"].default_value = t.get("sat", 1.0); l.new(mix.outputs["Result"], hs.inputs["Color"])
    g = n.new("ShaderNodeVectorMath"); g.operation = "MULTIPLY"; g.inputs[1].default_value = list(gain); l.new(hs.outputs[0], g.inputs[0])
    l.new(g.outputs[0], p.inputs["Base Color"])
    r = n.new("ShaderNodeMath"); r.operation = "MULTIPLY_ADD"; r.use_clamp = True
    r.inputs[1].default_value = t.get("rough_mul", 1.0); r.inputs[2].default_value = t.get("rough_add", 0.0)
    l.new(tex("rough.jpg", True).outputs["Color"], r.inputs[0]); l.new(r.outputs[0], p.inputs["Roughness"])
    nm = n.new("ShaderNodeNormalMap"); nm.inputs["Strength"].default_value = t.get("normal", 1.0)
    l.new(tex("nor_gl.jpg", True).outputs["Color"], nm.inputs["Color"]); l.new(nm.outputs[0], p.inputs["Normal"])
    p.inputs["Coat Weight"].default_value = t.get("coat", 0.0); p.inputs["Coat Roughness"].default_value = 0.25
    p.inputs["Sheen Weight"].default_value = t.get("sheen", 0.0); p.inputs["Sheen Roughness"].default_value = 0.6
    return m, mean

def slab(size, radius, loc):
    me = bpy.data.meshes.new("b"); bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
    lay = bm.loops.layers.uv.new("uv")
    for f in bm.faces:                                   # box projection in metres
        a = max(range(3), key=lambda i: abs(f.normal[i])); u, v = [i for i in range(3) if i != a]
        for lp in f.loops:
            lp[lay].uv = (lp.vert.co[u], lp.vert.co[v])
    bmesh.ops.bevel(bm, geom=bm.edges[:], offset=radius, segments=6, profile=0.5, affect="EDGES")
    for f in bm.faces:
        f.smooth = True
    bm.to_mesh(me); bm.free(); o = bpy.data.objects.new("b", me); o.location = loc; bpy.context.collection.objects.link(o)
    o.modifiers.new("wn", "WEIGHTED_NORMAL"); return o

def render(name, t, gain, px, spp, path):
    bpy.ops.wm.read_factory_settings(use_empty=True); k = C["groups"][C["candidates"][name]["group"]]["view"] / 0.09
    sc = bpy.context.scene; sc.render.engine = "CYCLES"; sc.cycles.samples = spp; sc.cycles.use_denoising = True
    sc.render.resolution_x = sc.render.resolution_y = px; sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "AgX - Medium High Contrast"
    w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True; wn, wl = w.node_tree.nodes, w.node_tree.links
    e = wn.new("ShaderNodeTexEnvironment"); e.image = img(os.path.join(TEX, "hdri_" + HDRI, HDRI + "_1k.hdr"))
    tc = wn.new("ShaderNodeTexCoord"); mp = wn.new("ShaderNodeMapping"); mp.inputs["Rotation"].default_value = (0, 0, math.radians(float(arg("--hdri-rot", 150))))
    wl.new(tc.outputs["Generated"], mp.inputs[0]); wl.new(mp.outputs[0], e.inputs[0]); wl.new(e.outputs[0], wn["Background"].inputs[0])
    wn["Background"].inputs[1].default_value = float(arg("--hdri-strength", 0.45))
    m, mean = material(name, t, gain)
    bpy.ops.mesh.primitive_plane_add(size=3 * k); gm = bpy.data.materials.new("g"); gm.use_nodes = True
    gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = list(s2l(hexrgb("#D8CBBB"))) + [1]
    gm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.8; bpy.context.object.data.materials.append(gm)
    b = slab((0.09 * k, 0.06 * k, 0.025 * k), 0.002 * k, (-0.012 * k, 0, 0.0125 * k)); b.data.materials.append(m)
    r = 0.022 * k; bpy.ops.mesh.primitive_uv_sphere_add(radius=r, segments=48, ring_count=24, location=(0.062 * k, -0.028 * k, r))
    s = bpy.context.object; bpy.ops.object.shade_smooth(); s.data.materials.append(m)
    for lp in s.data.uv_layers[0].data:
        lp.uv = (lp.uv[0] * 2 * math.pi * r, lp.uv[1] * math.pi * r)
    def area(loc, energy, size, color):
        d = bpy.data.lights.new("l", "AREA"); d.energy = energy * k * k; d.size = size * k; d.color = color
        o = bpy.data.objects.new("l", d); o.location = Vector(loc) * k; bpy.context.collection.objects.link(o)
        o.rotation_euler = (Vector((0, 0, 0.03 * k)) - o.location).to_track_quat("-Z", "Y").to_euler()
    area((-0.55, 0.35, 0.45), 26, 0.45, (1.0, 0.95, 0.88)); area((0.5, -0.5, 0.25), 3.5, 0.6, (1.0, 0.86, 0.72))
    target = Vector((-0.012 * k, 0, 0.025 * k)); cd = bpy.data.cameras.new("c"); cd.lens = 70; cd.dof.use_dof = True
    cam = bpy.data.objects.new("c", cd); bpy.context.collection.objects.link(cam); sc.camera = cam
    cam.location = target + Vector((0.10, -0.82, 0.50)).normalized() * 0.30 * 0.95 * k
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler(); cd.dof.focus_distance = (target - cam.location).length
    cd.dof.aperture_fstop = 2.8 * k                       # same blur in image space at every slab size
    sc.render.filepath = path; bpy.ops.render.render(write_still=True)
    a = np.asarray(Image.open(path).convert("RGB"), float); q = px // 8
    box = a[px // 2 - q:px // 2 + q // 2, px // 2 - 2 * q:px // 2 + q]            # lit top face around the camera target
    med = np.median(box.reshape(-1, 3), 0); Y = box @ np.array([.2126, .7152, .0722])
    S = float(np.median((box.max(2) - box.min(2)) / np.maximum(box.max(2), 1)))
    return med, S, float(np.std(Y)), mean

os.makedirs(OUT, exist_ok=True); RES = os.path.join(OUT, "results_%s.json" % MODE)
res = json.load(open(RES)) if os.path.exists(RES) else {}
for name, c in C["candidates"].items():
    if (ONLY and name not in ONLY) or (MODE == "raw" and "src" in c):
        continue
    t = c["tweak"] if MODE == "tweak" else {}; gain = np.ones(3); tgt = REF[c.get("target") or C["groups"][c["group"]]["target"]]["hex"]
    if MODE == "tweak":
        for _ in range(3):
            med, _, _, mean = render(name, t, gain, 128, 16, os.path.join(OUT, "_fit.png"))
            gain = gain * s2l(hexrgb(tgt)) / np.maximum(s2l(med), 1e-4); gain = gain * min(1.0, 0.92 / float((gain * mean).max()))
    med, S, sd, mean = render(name, t, gain, PX, SPP, os.path.join(OUT, "%s__%s.png" % (name, MODE)))
    res[name] = {"target_hex": tgt, "display_hex": "#%02X%02X%02X" % tuple(int(x) for x in med), "S50": round(S, 3), "luma_sd": round(sd, 2),
                 "texture_mean_hex": l2hex(mean), "albedo_after_hex": l2hex(mean * gain), "gain_linear_rgb": [round(float(x), 3) for x in gain], "tweak": t}
    print(name, res[name]); json.dump(res, open(RES, "w"), indent=1)
if os.path.exists(os.path.join(OUT, "_fit.png")):
    os.remove(os.path.join(OUT, "_fit.png"))
