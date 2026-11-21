"""T-189 throwaway: a kindergarten corner assembled ONLY from reused parts, in two looks.

blender -b --factory-startup -P vignette.py -- --dl <scratch>/dl --out <png> --look raw|house [--px 768 --spp 64]
Parts: CC0 Poly Haven models (scaled to child size), Poly Haven laminate_floor_02 + oak_veneer_01, ambientCG Carpet016,
Poly Haven HDRI lebombo, built-in Principled BSDF + Cycles Bevel node. Nothing is authored except placement.
raw   = models keep their own scanned textures.
house = owner rule "tint/scale/mapping only": wood parts -> oak_veneer_01 (box mapping), painted parts -> built-in
        Principled in one T-170 palette colour, Bevel node r 4 mm for soft edges; rug = Carpet016 tinted sage.
"""
import bpy, math, os, sys
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
arg = lambda n, d: argv[argv.index(n) + 1] if n in argv else d
DL, OUT, LOOK = arg("--dl", ""), arg("--out", ""), arg("--look", "house")
PX, SPP = int(arg("--px", 768)), int(arg("--spp", 64))
TEX = os.path.join(DL, "tex")


def lin(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c] + [1]


PAL = {"sage": "#A19558", "coral": "#C7755C", "blue": "#7E9CC0", "cream": "#E4D4C0", "rose": "#C99A9A", "yellow": "#E2B85A"}
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; sc.render.engine = "CYCLES"; sc.cycles.samples = SPP; sc.cycles.use_denoising = True; sc.cycles.seed = 0
sc.render.resolution_x, sc.render.resolution_y = PX, PX * 2 // 3
sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "AgX - Medium High Contrast"
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True; wn = w.node_tree.nodes
e = wn.new("ShaderNodeTexEnvironment"); e.image = bpy.data.images.load(os.path.join(TEX, "hdri_lebombo", "lebombo_1k.hdr"))
w.node_tree.links.new(e.outputs[0], wn["Background"].inputs[0]); wn["Background"].inputs[1].default_value = 0.5


def image_mat(name, folder, scale, tint=None, contrast=1.0, normal=0.6, rough_add=0.0):
    """Ready-made image set, box-projected in object space; only scale / tint / mapping changed."""
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; N, L = nt.nodes, nt.links
    b = N["Principled BSDF"]; tc = N.new("ShaderNodeTexCoord"); mp = N.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1 / scale,) * 3; L.new(tc.outputs["Object"], mp.inputs[0])

    def tex(f, data):
        t = N.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(os.path.join(TEX, folder, f))
        t.projection = "BOX"; t.projection_blend = 0.2
        if data:
            t.image.colorspace_settings.name = "Non-Color"
        L.new(mp.outputs[0], t.inputs[0]); return t
    c = tex("diff.jpg", False); src = c.outputs[0]
    if contrast != 1.0:
        bc = N.new("ShaderNodeBrightContrast"); bc.inputs["Contrast"].default_value = (contrast - 1) * 100 / 100
        L.new(src, bc.inputs[0]); src = bc.outputs[0]
    if tint:
        mx = N.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.blend_type = "MULTIPLY"; mx.inputs["Factor"].default_value = 1
        L.new(src, mx.inputs[6]); mx.inputs[7].default_value = tint; src = mx.outputs[2]
    L.new(src, b.inputs["Base Color"])
    r = tex("rough.jpg", True)
    if rough_add:
        ma = N.new("ShaderNodeMath"); ma.operation = "ADD"; ma.inputs[1].default_value = rough_add; L.new(r.outputs[0], ma.inputs[0]); L.new(ma.outputs[0], b.inputs["Roughness"])
    else:
        L.new(r.outputs[0], b.inputs["Roughness"])
    bv = N.new("ShaderNodeBevel"); bv.inputs["Radius"].default_value = 0.004; L.new(bv.outputs[0], b.inputs["Normal"])
    return m


def flat(name, hexc, rough=0.5):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = lin(hexc); b.inputs["Roughness"].default_value = rough
    bv = nt.nodes.new("ShaderNodeBevel"); bv.inputs["Radius"].default_value = 0.004; nt.links.new(bv.outputs[0], b.inputs["Normal"])
    return m


OAK = image_mat("oak", "ph_oak_veneer_01", 0.6, tint=[0.95, 0.85, 0.7, 1], contrast=0.7)
FLOOR = image_mat("floor", "ph_laminate_floor_02", 1.0)
RUG = image_mat("rug", "acg_Carpet016", 0.85, tint=[0.27 * 2.0, 0.20 * 2.6, 0.06 * 5.5, 1], rough_add=0.2)
WALL = flat("wall", "#E9DCC8", 0.9)


def box(name, size, loc, mat):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc); o = bpy.context.object; o.name = name; o.scale = size
    bpy.ops.object.transform_apply(scale=True); o.data.materials.append(mat); return o


def model(mid, loc, rot_z=0.0, size=None, scale=None, mat=None):
    """Import CC0 glTF; fit to target size (x,y,z metres) or uniform scale; floor at loc.z."""
    g = [f for f in os.listdir(os.path.join(DL, "ph", mid)) if f.endswith(".gltf")][0]
    before = set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath=os.path.join(DL, "ph", mid, g))
    new = [o for o in bpy.data.objects if o not in before]; roots = [o for o in new if o.parent is None]
    meshes = [o for o in new if o.type == "MESH"]
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
    lo = Vector([min(p[i] for p in pts) for i in range(3)]); hi = Vector([max(p[i] for p in pts) for i in range(3)])
    dim = hi - lo; s = Vector(scale) if scale else Vector([size[i] / dim[i] for i in range(3)])
    piv = bpy.data.objects.new(mid, None); bpy.context.collection.objects.link(piv)
    for r in roots:
        r.parent = piv; r.location -= Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))
    piv.scale = s; piv.location = loc; piv.rotation_euler = (0, 0, math.radians(rot_z))
    if LOOK == "house" and mat is not None:
        for o in meshes:
            o.data.materials.clear(); o.data.materials.append(mat)
    return piv


# room: floor, two walls, rug
box("floor", (6, 6, 0.02), (0, 0, -0.01), FLOOR)
box("wall_back", (6, 0.1, 3), (0, 1.6, 1.5), WALL); box("wall_left", (0.1, 6, 3), (-2.2, 0, 1.5), WALL)
box("rug", (1.9, 1.3, 0.012), (0.1, -0.05, 0.006), RUG if LOOK == "house" else flat("rug_flat", "#A49069", 1.0))
# furniture (child scale: table top ~0.52 m, seats ~0.30 m)
model("painted_wooden_table", (0.1, 0.0, 0.012), size=(1.2, 0.62, 0.52), mat=OAK)
model("painted_wooden_chair_01", (-0.25, -0.5, 0.012), 15, scale=(0.6,) * 3, mat=flat("c1", PAL["coral"]))
model("painted_wooden_chair_01", (0.5, -0.52, 0.012), -10, scale=(0.6,) * 3, mat=flat("c2", PAL["blue"]))
model("painted_wooden_stool", (0.95, 0.15, 0.012), 30, scale=(0.6,) * 3, mat=flat("c3", PAL["sage"]))
model("painted_wooden_shelves", (-1.1, 1.3, 0), 0, scale=(1.2, 1.0, 0.9), mat=OAK)
model("plastic_crate_02", (-0.25, 1.3, 0), 0, scale=(0.8,) * 3, mat=flat("bin", PAL["sage"], 0.6))
model("wicker_basket_01", (0.35, 1.32, 0), 5, scale=(0.9,) * 3, mat=flat("bin2", PAL["coral"], 0.8))
# props on the table (top at 0.532)
model("rubber_duck_toy", (0.42, 0.05, 0.532), -30, scale=(0.35,) * 3, mat=flat("duck", PAL["yellow"], 0.35))
model("wooden_bowl_02", (-0.15, 0.08, 0.532), 0, scale=(1.0,) * 3, mat=flat("bowl", PAL["blue"], 0.4))
model("ceramic_vase_01", (-1.05, 1.32, 0.95), 0, scale=(0.5,) * 3, mat=flat("vase", PAL["rose"], 0.6))


def area(loc, target, energy, size, colour):
    d = bpy.data.lights.new("l", "AREA"); d.energy = energy; d.size = size; d.color = colour
    o = bpy.data.objects.new("l", d); o.location = loc; bpy.context.collection.objects.link(o)
    o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()


area((-2.0, -0.6, 1.8), (0.1, 0.3, 0.5), 650, 1.6, (1, 0.95, 0.88))  # window key from the left
area((1.8, -2.2, 1.2), (0.1, 0.3, 0.5), 120, 2.5, (1, 0.86, 0.72))   # warm bounce
cd = bpy.data.cameras.new("c"); cd.lens = 40; cd.dof.use_dof = True; cd.dof.aperture_fstop = 4.0
cam = bpy.data.objects.new("c", cd); bpy.context.collection.objects.link(cam); sc.camera = cam
cam.location = (1.35, -2.45, 1.05); tgt = Vector((-0.15, 0.35, 0.45))
cam.rotation_euler = (tgt - cam.location).to_track_quat("-Z", "Y").to_euler(); cd.dof.focus_distance = (tgt - cam.location).length
sc.render.filepath = OUT; bpy.ops.render.render(write_still=True)
