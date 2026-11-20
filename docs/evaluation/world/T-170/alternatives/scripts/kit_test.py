"""T-170b throwaway test (NOT pipeline code): build a desk vignette from data using only built-in Blender
primitives + stock modifiers (Bevel, Solidify, Weighted Normal), no custom mesh code, and compare geometric rounding
(Bevel modifier) with render-time rounding (Cycles Bevel shader node on a sharp cube).

blender -b --factory-startup -P docs/evaluation/world/T-170/alternatives/scripts/kit_test.py -- [--px 640] [--spp 64]
Materials are the T-170 prototypes, imported read-only from ../../scripts/render_swatches.py.
"""
import os, sys, time
import bpy, bmesh
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
PX = int(argv[argv.index("--px") + 1]) if "--px" in argv else 640
SPP = int(argv[argv.index("--spp") + 1]) if "--spp" in argv else 64
sys.argv = ["blender", "--", "--only", "__none__"]          # import the T-170 material prototypes without rendering
sys.path.insert(0, os.path.join(HERE, "..", "..", "scripts"))
import render_swatches as T170  # noqa: E402

# ---- the whole "construction system" under test: rounding classes + 4 stock primitive kinds -------------------
ROUND = {"crisp": (0.0004, 0.0004, 1), "soft": (0.08, 0.0015, 0.012), "chunky": (0.16, 0.003, 0.020)}  # frac, min, max

def rounding(o, cls, smallest, segs=4):
    frac, lo, hi = ROUND[cls]
    w = lo if cls == "crisp" else max(lo, min(hi, frac * smallest))
    b = o.modifiers.new("round", "BEVEL"); b.width = w; b.segments = segs; b.limit_method = "NONE"; b.harden_normals = False
    o.modifiers.new("wn", "WEIGHTED_NORMAL").keep_sharp = True
    for p in o.data.polygons:
        p.use_smooth = True

def part(kind, size, loc, mat, cls="soft", wall=0.0, rot=(0, 0, 0)):
    bm = bmesh.new()
    if kind in ("box", "shell"):
        bmesh.ops.create_cube(bm, size=1.0)
    elif kind in ("cyl", "cup"):
        bmesh.ops.create_cone(bm, cap_ends=True, segments=32, radius1=0.5, radius2=0.5, depth=1.0)
    elif kind == "sheet":
        bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5)
    for v in bm.verts:
        v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
    if kind in ("shell", "cup"):                       # open top: delete the face with the highest centre
        top = max(bm.faces, key=lambda f: f.calc_center_median().z); bmesh.ops.delete(bm, geom=[top], context="FACES")
    me = bpy.data.meshes.new(kind); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(kind, me); o.location = loc; o.rotation_euler = rot; bpy.context.collection.objects.link(o)
    if kind in ("shell", "cup", "sheet"):
        s = o.modifiers.new("wall", "SOLIDIFY"); s.thickness = wall; s.offset = -1 if kind != "sheet" else 0
    rounding(o, cls, min(x for x in size if x > 0) if kind != "sheet" else wall)
    o.data.materials.append(mat)
    return o

# ---- data: a child desk vignette (would be JSON in the pipeline) -----------------------------------------------
def build():
    wood = T170.wood("wood", "#B08560", "#6B4630", 0.62, 1.0, 0.0, wear=0.8)
    oak = T170.wood("oak", "#D9B88F", "#A8794B", 0.42, 0.7, 0.25)
    blue = T170.SW["plastic_semigloss"](); paper = T170.SW["paper"](); cup = T170.SW["ceramic_matte"]()
    crayon = T170.SW["wax_crayon"](); toy = T170.SW["wood_painted_toy"]()
    T, H = 0.032, 0.52                                                  # top thickness, table height (m)
    part("box", (1.00, 0.62, T), (0, 0, H - T / 2), wood)               # top
    for sx in (-1, 1):
        for sy in (-1, 1):
            part("box", (0.055, 0.055, H - T), (sx * 0.44, sy * 0.25, (H - T) / 2), oak)   # legs
    part("box", (0.84, 0.022, 0.07), (0, -0.27, H - T - 0.035), oak)    # apron front
    part("shell", (0.34, 0.24, 0.06), (0.22, 0.08, H + 0.03), blue, "chunky", wall=0.008)   # water tray
    part("cup", (0.075, 0.075, 0.10), (-0.30, 0.16, H + 0.05), cup, "soft", wall=0.006)
    part("sheet", (0.21, 0.297, 0), (-0.12, -0.08, H + 0.0004), paper, "crisp", wall=0.0003, rot=(0, 0, 0.25))
    part("cyl", (0.011, 0.011, 0.09), (-0.02, -0.17, H + 0.0055), crayon, "soft", rot=(1.5708, 0, 1.1))
    part("box", (0.05, 0.05, 0.05), (-0.36, -0.12, H + 0.025), toy, "soft")              # block, geometric rounding
    sharp = part("box", (0.05, 0.05, 0.05), (-0.28, -0.20, H + 0.025), toy, "soft")      # block, shader rounding
    sharp.modifiers.remove(sharp.modifiers["round"])
    m2 = toy.copy(); sharp.data.materials[0] = m2; n = m2.node_tree.nodes
    bv = n.new("ShaderNodeBevel"); bv.inputs["Radius"].default_value = 0.004; bv.samples = 8
    m2.node_tree.links.new(bv.outputs["Normal"], n["Principled BSDF"].inputs["Normal"])

def render():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene; sc.render.engine = "CYCLES"; sc.cycles.samples = SPP; sc.cycles.use_denoising = True
    sc.cycles.seed = 0; sc.render.resolution_x, sc.render.resolution_y = PX, PX * 10 // 16
    sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "AgX - Medium High Contrast"
    w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.95, 0.80, 0.66, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 0.5
    t0 = time.time(); build(); t_build = time.time() - t0
    bpy.ops.mesh.primitive_plane_add(size=8); bpy.context.object.data.materials.append(T170.simple("floor", "#D8CBBB", 0.8))
    for loc, e, s, c in (((-1.6, 1.0, 1.6), 380, 1.6, (1.0, 0.95, 0.88)), ((1.4, -1.4, 0.9), 60, 2.0, (1.0, 0.86, 0.72))):
        d = bpy.data.lights.new("l", "AREA"); d.energy = e; d.size = s; d.color = c
        o = bpy.data.objects.new("l", d); o.location = loc; bpy.context.collection.objects.link(o)
        o.rotation_euler = (Vector((0, 0, 0.5)) - o.location).to_track_quat("-Z", "Y").to_euler()
    cd = bpy.data.cameras.new("c"); cd.lens = 50; cd.dof.use_dof = True; cd.dof.aperture_fstop = 4.0
    cam = bpy.data.objects.new("c", cd); bpy.context.collection.objects.link(cam); sc.camera = cam
    tgt = Vector((-0.12, -0.05, 0.54)); cam.location = (0.05, -1.05, 0.95)
    cam.rotation_euler = (tgt - cam.location).to_track_quat("-Z", "Y").to_euler(); cd.dof.focus_distance = (tgt - cam.location).length
    sc.render.filepath = os.path.join(HERE, "..", "evidence", "kit_desk_vignette.png")
    t1 = time.time(); bpy.ops.render.render(write_still=True)
    print("KIT build %.2fs render %.1fs objects %d" % (t_build, time.time() - t1, len(bpy.data.objects)))

render()
