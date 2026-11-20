"""T-163: rendered contact sheet of the 13 felt props (Blender 5.3, Cycles, low samples).
Uses the pipeline's own prop mesh builder and the 'felt' material preset (shot_render.prop_mesh, materials.builder).
  blender -b --factory-startup -P tests/props/render_sheet.py -- <out.png> [samples]
then tests/props/label_sheet.py adds the captions (PIL)."""
import json, math, os, sys
import bpy
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "pipeline", "charsys"))
import shot_render as SR  # noqa: E402
from materials import builder as MATERIALS  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:]
OUT = args[0]
SAMPLES = int(args[1]) if len(args) > 1 else 32
NAMES = ["cup", "bowl", "plate", "spoon", "book", "ball", "box", "box_lid", "toy", "apple", "pencil", "block", "basket"]
COLS, CELL = 5, 0.26

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "CYCLES"
sc.cycles.samples = SAMPLES
sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y = 1500, 900
sc.view_settings.view_transform = "Standard"
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.93, 0.91, 0.87, 1)
w.node_tree.nodes["Background"].inputs[1].default_value = 1.0

rows = (len(NAMES) + COLS - 1) // COLS
for i, n in enumerate(NAMES):
    a = json.load(open(os.path.join(ROOT, f"content/assets/felt_{n}.asset.json")))
    me, _ = SR.prop_mesh(n, a)
    ob = bpy.data.objects.new(n, me)
    sc.collection.objects.link(ob)
    m = a["mesh"]
    if m["primitive"] == "cylinder" and m.get("open_top"):
        s = ob.modifiers.new("wall", "SOLIDIFY"); s.thickness = m.get("wall", 0.004); s.offset = -1.0
    me.materials.append(MATERIALS.build_material(f"M_{n}", a["material_presets"][0]))
    r, c = divmod(i, COLS)
    z = 0.0 if m["primitive"] == "cylinder" else (m["radius"] if m["primitive"] == "sphere" else m["size"][1] / 2)
    ob.location = ((c - (COLS - 1) / 2) * CELL, (rows - 1 - r) * CELL * 0.9, z)
    ob.rotation_euler = (0, 0, math.radians(-30))

bpy.ops.mesh.primitive_plane_add(size=3, location=(0, 0, 0))
g = bpy.context.object
gm = bpy.data.materials.new("floor"); gm.use_nodes = True
gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.82, 0.78, 0.72, 1)
g.data.materials.append(gm)

for loc, e in (((0.4, -1.2, 1.2), 40), ((-0.8, 0.5, 1.0), 12)):
    L = bpy.data.lights.new("l", "AREA"); L.energy = e; L.size = 1.2
    lo = bpy.data.objects.new("l", L); sc.collection.objects.link(lo); lo.location = loc
    lo.rotation_euler = (Vector((0, -0.1, 0.0)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()

cam = bpy.data.cameras.new("c"); cam.lens = 50
co = bpy.data.objects.new("c", cam); sc.collection.objects.link(co); sc.camera = co
ctr = Vector((0, (rows - 1) * CELL * 0.45, 0.02))
co.location = ctr + Vector((0, -1.5, 1.35))
co.rotation_euler = (ctr - co.location).to_track_quat("-Z", "Y").to_euler()
sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print("rendered", OUT)
