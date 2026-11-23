"""Dev: render chosen frames of a shot.blend (Cycles) at a given size and sample count. args: <blend> <out dir> <w> <h> <samples> <frames...>"""
import os, sys, bpy
a = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.open_mainfile(filepath=a[0])
sc = bpy.context.scene; r = sc.render
out, w, h, spp = a[1], int(a[2]), int(a[3]), int(a[4])
os.makedirs(out, exist_ok=True)
r.engine = "CYCLES"; sc.cycles.samples = spp; r.resolution_x, r.resolution_y, r.resolution_percentage = w, h, 100
for f in map(int, a[5:]):
    sc.frame_set(f); r.filepath = os.path.join(out, f"frame_{f:04d}.png")
    bpy.ops.render.render(write_still=True)
