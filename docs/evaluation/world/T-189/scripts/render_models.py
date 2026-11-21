"""T-189 throwaway: import CC0 Poly Haven glTF models headless and render each in three looks.

blender -b --factory-startup -P render_models.py -- --dl <scratch>/dl --out <scratch>/renders [--px 256 --spp 32]
raw   = model as downloaded (its own scanned PBR textures)
tint  = own textures, multiplied by one palette colour (owner rule: tint/scale/mapping only)
flat  = all materials replaced by one built-in Principled BSDF in a palette colour (+ Cycles Bevel normal)
Writes <out>/<id>_<look>.png and <out>/stats.json (dims, tris, materials, images, import time).
"""
import bpy, json, math, os, sys, time
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
arg = lambda n, d: argv[argv.index(n) + 1] if n in argv else d
DL, OUT = arg("--dl", ""), arg("--out", ""); PX, SPP = int(arg("--px", 256)), int(arg("--spp", 32))
IDS = arg("--ids", "").split(",") if "--ids" in argv else sorted(d for d in os.listdir(os.path.join(DL, "ph")) if os.path.isdir(os.path.join(DL, "ph", d)))
os.makedirs(OUT, exist_ok=True)
HDRI = os.path.join(DL, "tex", "hdri_lebombo", "lebombo_1k.hdr")
# T-170 measured pastel palette (03_palette_measured.png): sage, coral, powder blue, cream, honey oak
PAL = {"sage": "#A19558", "coral": "#C7755C", "blue": "#7E9CC0", "cream": "#E4D4C0", "oak": "#C8A47C"}
PICK = {"painted_wooden_chair_01": "coral", "painted_wooden_stool": "blue", "painted_wooden_table": "oak",
        "painted_wooden_shelves": "cream", "painted_wooden_cabinet_02": "sage", "SchoolChair_01": "sage",
        "SchoolDesk_01": "oak", "Shelf_01": "oak", "potted_plant_01": "sage", "rubber_duck_toy": "oak",
        "stationery_supplies": "blue", "wicker_basket_01": "coral", "plastic_crate_02": "blue",
        "ceramic_vase_01": "cream", "folding_wooden_stool": "coral", "wooden_bowl_02": "oak"}


def lin(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c] + [1]


def scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene; sc.render.engine = "CYCLES"; sc.cycles.samples = SPP; sc.cycles.use_denoising = True
    sc.cycles.seed = 0; sc.render.resolution_x = sc.render.resolution_y = PX
    sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "AgX - Medium High Contrast"
    w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True; n = w.node_tree.nodes
    e = n.new("ShaderNodeTexEnvironment"); e.image = bpy.data.images.load(HDRI)
    w.node_tree.links.new(e.outputs[0], n["Background"].inputs[0]); n["Background"].inputs[1].default_value = 0.6
    return sc


def area(loc, target, energy, size, color):
    d = bpy.data.lights.new("l", "AREA"); d.energy = energy; d.size = size; d.color = color
    o = bpy.data.objects.new("l", d); o.location = loc; bpy.context.collection.objects.link(o)
    o.rotation_euler = (Vector(target) - o.location).to_track_quat("-Z", "Y").to_euler()


def import_model(mid):
    folder = os.path.join(DL, "ph", mid); g = [f for f in os.listdir(folder) if f.endswith(".gltf")][0]
    t0 = time.time(); before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(folder, g))
    objs = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
    return objs, time.time() - t0


def bounds(objs):
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    lo = Vector([min(p[i] for p in pts) for i in range(3)]); hi = Vector([max(p[i] for p in pts) for i in range(3)])
    return lo, hi


def restyle(objs, look, colour):
    if look == "raw":
        return
    if look == "flat":
        m = bpy.data.materials.new("flat"); m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = lin(colour); b.inputs["Roughness"].default_value = 0.55
        bv = nt.nodes.new("ShaderNodeBevel"); bv.inputs["Radius"].default_value = 0.006
        nt.links.new(bv.outputs[0], b.inputs["Normal"])
        for o in objs:
            o.data.materials.clear(); o.data.materials.append(m)
        return
    for m in {s.material for o in objs for s in o.material_slots if s.material}:  # tint: multiply own colour map
        nt = m.node_tree; b = next(x for x in nt.nodes if x.type == "BSDF_PRINCIPLED"); s = b.inputs["Base Color"]
        mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "MULTIPLY"
        mix.inputs["Factor"].default_value = 1.0; mix.inputs[7].default_value = [min(1, 2.2 * x) for x in lin(colour)[:3]] + [1]
        if s.is_linked:
            src = s.links[0].from_socket; nt.links.new(src, mix.inputs[6])
        else:
            mix.inputs[6].default_value = s.default_value
        nt.links.new(mix.outputs[2], s)


def frame(objs):
    lo, hi = bounds(objs); c = (lo + hi) / 2; r = max((hi - lo).length / 2, 0.05)
    bpy.ops.mesh.primitive_plane_add(size=60 * r, location=(c.x, c.y, lo.z))
    gm = bpy.data.materials.new("g"); gm.use_nodes = True
    gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = lin("#D8CBBB")
    bpy.context.object.data.materials.append(gm)
    cd = bpy.data.cameras.new("c"); cd.lens = 50; cam = bpy.data.objects.new("c", cd); bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam; d = r / math.tan(math.atan(18 / 50)) * 1.15
    cam.location = c + Vector((d * 0.62, -d * 0.72, d * 0.38)); cam.rotation_euler = (c - cam.location).to_track_quat("-Z", "Y").to_euler()
    area(c + Vector((-3 * r, -1.5 * r, 3 * r)), c, 40 * r * r, 3 * r, (1, 0.95, 0.88))
    area(c + Vector((3 * r, -2 * r, 1 * r)), c, 6 * r * r, 4 * r, (1, 0.86, 0.72))


stats = {}
for mid in IDS:
    for look in ("raw", "tint", "flat"):
        scene(); objs, dt = import_model(mid); restyle(objs, look, PAL[PICK.get(mid, "cream")]); frame(objs)
        if look == "raw":
            lo, hi = bounds(objs)
            imgs = {i.name: list(i.size) for i in bpy.data.images if i.filepath and "lebombo" not in i.filepath}
            stats[mid] = dict(dims_m=[round(x, 3) for x in (hi - lo)], tris=sum(len(p.vertices) - 2 for o in objs for p in o.data.polygons),
                              objects=len(objs), materials=len({s.material.name for o in objs for s in o.material_slots if s.material}),
                              images=imgs, import_s=round(dt, 2), palette=PICK.get(mid, "cream"))
        t0 = time.time(); bpy.context.scene.render.filepath = os.path.join(OUT, "%s_%s.png" % (mid, look))
        bpy.ops.render.render(write_still=True); stats.setdefault(mid, {})["render_s_" + look] = round(time.time() - t0, 1)
        print(mid, look, stats[mid]["render_s_" + look], flush=True)
json.dump(stats, open(os.path.join(OUT, "stats.json"), "w"), indent=1)
