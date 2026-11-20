"""T-170 throwaway swatch renderer (planning evidence only; NOT pipeline code).

blender -b --factory-startup -P docs/evaluation/world/T-170/scripts/render_swatches.py -- [--only name,name] [--px 320] [--spp 64]
Writes docs/evaluation/world/T-170/swatches/<name>.png. Existing fibre presets come from pipeline/charsys/materials
(read-only import); the world materials below are prototypes of the parameter ranges proposed in the README.
"""
import math, os, sys
import bpy, bmesh
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "pipeline", "charsys"))
from materials import builder as MATERIALS  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
def arg(name, default):
    return argv[argv.index(name) + 1] if name in argv else default
ONLY = [s for s in arg("--only", "").split(",") if s]
PX, SPP = int(arg("--px", 320)), int(arg("--spp", 64))
OUT = os.path.join(HERE, "..", "swatches")

def lin(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c] + [1.0]

def principled(name, base, rough, **kw):
    m = bpy.data.materials.new(name); m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = lin(base); p.inputs["Roughness"].default_value = rough
    for k, v in kw.items():
        p.inputs[k].default_value = v
    return m, m.node_tree.nodes, m.node_tree.links, p

def coords(nodes, links, scale):
    tc = nodes.new("ShaderNodeTexCoord"); mp = nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = scale; links.new(tc.outputs["Object"], mp.inputs["Vector"])
    return mp.outputs["Vector"]

def bump(nodes, links, p, height, strength, distance):
    b = nodes.new("ShaderNodeBump"); b.inputs["Strength"].default_value = strength
    b.inputs["Distance"].default_value = distance
    links.new(height, b.inputs["Height"]); links.new(b.outputs["Normal"], p.inputs["Normal"])

def wood(name, light, dark, rough, grain_contrast, coat, wear=0.0):
    """Grained wood: stretched noise rings (grain along local X), ramp light->dark, satin coat, optional scuff wear."""
    m, n, l, p = principled(name, light, rough, **{"Coat Weight": coat, "Coat Roughness": 0.25})
    v = coords(n, l, (2.0, 22.0, 22.0))
    nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 3.0; nz.inputs["Detail"].default_value = 6.0
    nz.inputs["Distortion"].default_value = 1.2; l.new(v, nz.inputs["Vector"])
    fine = n.new("ShaderNodeTexNoise"); fine.inputs["Scale"].default_value = 40.0; l.new(coords(n, l, (1.5, 60, 60)), fine.inputs["Vector"])
    mx = n.new("ShaderNodeMath"); mx.operation = "MULTIPLY_ADD"; mx.inputs[1].default_value = 0.35; l.new(fine.outputs["Fac"], mx.inputs[0]); l.new(nz.outputs["Fac"], mx.inputs[2])
    ramp = n.new("ShaderNodeValToRGB"); e = ramp.color_ramp.elements
    e[0].position = 0.5 - 0.3 * grain_contrast; e[0].color = lin(dark); e[1].position = 0.75; e[1].color = lin(light)
    l.new(mx.outputs[0], ramp.inputs["Fac"])
    col = ramp.outputs["Color"]
    if wear > 0:
        sc = n.new("ShaderNodeTexNoise"); sc.inputs["Scale"].default_value = 9.0; sc.inputs["Detail"].default_value = 10.0
        l.new(coords(n, l, (1, 14, 1)), sc.inputs["Vector"])
        thr = n.new("ShaderNodeMapRange"); thr.inputs["From Min"].default_value = 0.56; thr.inputs["From Max"].default_value = 0.66
        l.new(sc.outputs["Fac"], thr.inputs["Value"])
        mixc = n.new("ShaderNodeMixRGB"); mixc.inputs["Color2"].default_value = lin("#C9B49A")
        wf = n.new("ShaderNodeMath"); wf.operation = "MULTIPLY"; wf.inputs[1].default_value = wear
        l.new(thr.outputs["Result"], wf.inputs[0]); l.new(wf.outputs[0], mixc.inputs["Fac"]); l.new(col, mixc.inputs["Color1"])
        col = mixc.outputs["Color"]
        rr = n.new("ShaderNodeMapRange"); rr.inputs["To Min"].default_value = rough; rr.inputs["To Max"].default_value = min(1.0, rough + 0.25)
        l.new(wf.outputs[0], rr.inputs["Value"]); l.new(rr.outputs["Result"], p.inputs["Roughness"])
    l.new(col, p.inputs["Base Color"])
    bump(n, l, p, mx.outputs[0], 0.25, 0.0004)
    return m

def simple(name, base, rough, noise_scale=0.0, bump_strength=0.0, distance=0.0003, **kw):
    m, n, l, p = principled(name, base, rough, **kw)
    if noise_scale:
        nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = noise_scale; nz.inputs["Detail"].default_value = 8.0
        l.new(coords(n, l, (1, 1, 1)), nz.inputs["Vector"]); bump(n, l, p, nz.outputs["Fac"], bump_strength, distance)
    return m

def rug(name, base):
    m, n, l, p = principled(name, base, 1.0, **{"Sheen Weight": 0.6, "Sheen Roughness": 0.6})
    w = n.new("ShaderNodeTexWave"); w.inputs["Scale"].default_value = 260.0; w.inputs["Distortion"].default_value = 3.0
    w.inputs["Detail"].default_value = 2.0; w.inputs["Detail Scale"].default_value = 6.0
    l.new(coords(n, l, (1, 1, 1)), w.inputs["Vector"])
    v = n.new("ShaderNodeTexVoronoi"); v.inputs["Scale"].default_value = 700.0; l.new(coords(n, l, (1, 1, 1)), v.inputs["Vector"])
    mx = n.new("ShaderNodeMath"); mx.operation = "MULTIPLY"; l.new(w.outputs["Fac"], mx.inputs[0]); l.new(v.outputs["Distance"], mx.inputs[1])
    bump(n, l, p, mx.outputs[0], 1.0, 0.002)
    mixc = n.new("ShaderNodeMixRGB"); mixc.blend_type = "MULTIPLY"; mixc.inputs["Color1"].default_value = lin(base)
    mixc.inputs["Color2"].default_value = (0.45, 0.45, 0.45, 1); l.new(w.outputs["Fac"], mixc.inputs["Fac"]); l.new(mixc.outputs["Color"], p.inputs["Base Color"])
    return m

def water(name):
    m = bpy.data.materials.new(name); m.use_nodes = True; n, l = m.node_tree.nodes, m.node_tree.links
    n.remove(n["Principled BSDF"]); out = n["Material Output"]
    g = n.new("ShaderNodeBsdfGlass"); g.inputs["IOR"].default_value = 1.333; g.inputs["Roughness"].default_value = 0.0
    g.inputs["Color"].default_value = (0.93, 0.97, 1.0, 1)
    tc = n.new("ShaderNodeTexCoord"); w = n.new("ShaderNodeTexWave"); w.wave_type = "RINGS"; w.rings_direction = "SPHERICAL"
    w.inputs["Scale"].default_value = 22.0; w.inputs["Distortion"].default_value = 0.15; l.new(tc.outputs["Object"], w.inputs["Vector"])
    b = n.new("ShaderNodeBump"); b.inputs["Strength"].default_value = 0.2; b.inputs["Distance"].default_value = 0.0015
    l.new(w.outputs["Fac"], b.inputs["Height"]); l.new(b.outputs["Normal"], g.inputs["Normal"])
    lp = n.new("ShaderNodeLightPath"); tr = n.new("ShaderNodeBsdfTransparent"); mix = n.new("ShaderNodeMixShader")
    l.new(lp.outputs["Is Shadow Ray"], mix.inputs["Fac"]); l.new(g.outputs[0], mix.inputs[1]); l.new(tr.outputs[0], mix.inputs[2])
    l.new(mix.outputs[0], out.inputs["Surface"])
    return m

def preset(name, preset_name, base):
    c = [int(base[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return MATERIALS.build_material(name, preset_name, base_color_srgb=c)

SW = {
    "wood_oak_satin": lambda: wood("m", "#D9B88F", "#A8794B", 0.42, 0.7, 0.25),
    "wood_worn": lambda: wood("m", "#B08560", "#6B4630", 0.62, 1.0, 0.0, wear=0.8),
    "wood_painted_toy": lambda: simple("m", "#C8402A", 0.28, **{"Coat Weight": 0.6, "Coat Roughness": 0.12}),
    "plastic_semigloss": lambda: simple("m", "#5F86AE", 0.30, 220.0, 0.03, **{"Coat Weight": 0.3, "Coat Roughness": 0.2}),
    "plastic_gloss": lambda: simple("m", "#E2B21C", 0.16),
    "paper": lambda: simple("m", "#F1EEE8", 0.72, 900.0, 0.12, 0.0002, **{"Subsurface Weight": 0.15, "Subsurface Scale": 0.002}),
    "wax_crayon": lambda: simple("m", "#3E9A4B", 0.42, 300.0, 0.08, **{"Subsurface Weight": 0.3, "Subsurface Scale": 0.003}),
    "ceramic_matte": lambda: simple("m", "#C8A888", 0.55, 120.0, 0.05),
    "wall_plaster": lambda: simple("m", "#EFE3D0", 0.9, 160.0, 0.2, 0.0006),
    "metal_wire": lambda: simple("m", "#B4744A", 0.3, **{"Metallic": 1.0}),
    "rug_loop_pile": lambda: rug("m", "#7FA39A"),
    "water_tray": None,
    "felt (existing)": lambda: preset("m", "felt", "#E7A9A0"),
    "fleece (existing)": lambda: preset("m", "fleece", "#D9B24A"),
    "wool yarn (existing)": lambda: preset("m", "wool yarn", "#6E4630"),
    "woven cotton (existing)": lambda: preset("m", "woven cotton", "#A9B77A"),
    "skin-flock/3 (existing)": lambda: preset("m", "skin-flock/3", "#F0C9B4"),
}
# bevel rule sheet: radius as a fraction of the smallest dimension of the part
for f in (0.0, 0.03, 0.08, 0.16):
    SW["bevel_%02d" % round(f * 100)] = (lambda f=f: (wood("m", "#D9B88F", "#A8794B", 0.42, 0.7, 0.25), f))

def block(size, radius, loc):
    me = bpy.data.meshes.new("b"); bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
    if radius > 0:
        bmesh.ops.bevel(bm, geom=bm.edges[:], offset=radius, segments=6, profile=0.5, affect="EDGES")
    for f in bm.faces:
        f.smooth = radius > 0
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("b", me); o.location = loc; bpy.context.collection.objects.link(o)
    o.modifiers.new("wn", "WEIGHTED_NORMAL")
    return o

def scene(name):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene; sc.render.engine = "CYCLES"; sc.cycles.samples = SPP; sc.cycles.use_denoising = True
    sc.render.resolution_x = sc.render.resolution_y = PX; sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "AgX - Medium High Contrast"
    w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.95, 0.80, 0.66, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 0.45
    made = SW[name]() if SW[name] else None
    frac = 0.08
    if isinstance(made, tuple):
        made, frac = made
    bpy.ops.mesh.primitive_plane_add(size=3); g = bpy.context.object
    g.data.materials.append(simple("ground", "#D8CBBB", 0.8))
    if name == "water_tray":
        tray = block((0.20, 0.14, 0.035), 0.012, (0, 0, 0.0175)); tray.data.materials.append(SW["plastic_semigloss"]())
        cut = block((0.176, 0.116, 0.04), 0.008, (0, 0, 0.030)); cut.hide_render = True; cut.display_type = "WIRE"
        b = tray.modifiers.new("cut", "BOOLEAN"); b.object = cut; b.operation = "DIFFERENCE"
        wat = block((0.1755, 0.1155, 0.016), 0.0, (0, 0, 0.0185)); wat.data.materials.append(water("water"))
        boat = block((0.05, 0.02, 0.012), 0.002, (0.02, 0.01, 0.031)); boat.data.materials.append(SW["paper"]())
        target, dist = Vector((0, 0, 0.02)), 0.34
    else:
        blk = block((0.09, 0.06, 0.06), frac * 0.06, (-0.012, 0, 0.03)); blk.data.materials.append(made)
        if not name.startswith("bevel"):
            bpy.ops.mesh.primitive_uv_sphere_add(radius=0.026, segments=48, ring_count=24, location=(0.062, -0.028, 0.026))
            s = bpy.context.object; bpy.ops.object.shade_smooth(); s.data.materials.append(made)
        target, dist = Vector((0.01, 0, 0.028)), 0.30
        if "existing" in name:
            for o in [o for o in bpy.context.scene.objects if o.type == "MESH" and o is not g]:
                try:
                    MATERIALS.add_fibres_geometry(o, name.split(" (")[0], base_color_srgb=None)
                except Exception as exc:  # fibres are optional evidence; the surface preset still renders
                    print("fibres skipped:", name, exc)
    def area(loc, energy, size, color):
        d = bpy.data.lights.new("l", "AREA"); d.energy = energy; d.size = size; d.color = color
        o = bpy.data.objects.new("l", d); o.location = loc; bpy.context.collection.objects.link(o)
        o.rotation_euler = (Vector((0, 0, 0.03)) - o.location).to_track_quat("-Z", "Y").to_euler()
    area((-0.55, 0.35, 0.45), 26, 0.45, (1.0, 0.95, 0.88))   # window key: screen-left, back, ~40 deg up, large
    area((0.5, -0.5, 0.25), 3.5, 0.6, (1.0, 0.86, 0.72))     # warm room bounce
    cd = bpy.data.cameras.new("c"); cd.lens = 70; cd.dof.use_dof = True; cd.dof.aperture_fstop = 2.8
    cam = bpy.data.objects.new("c", cd); bpy.context.collection.objects.link(cam); sc.camera = cam
    cam.location = target + Vector((0.10, -0.82, 0.50)).normalized() * dist * 1.25
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler(); cd.dof.focus_distance = (target - cam.location).length
    os.makedirs(OUT, exist_ok=True)
    sc.render.filepath = os.path.join(OUT, name.replace(" (existing)", "__existing").replace(" ", "_").replace("/", "-") + ".png")
    bpy.ops.render.render(write_still=True)

for nm in SW:
    if not ONLY or nm in ONLY or nm.split(" (")[0] in ONLY:
        scene(nm)
