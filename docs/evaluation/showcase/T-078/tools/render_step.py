"""T-078: render every Nth frame of a run_shot shot.blend (render settings as run_shot saved them).

    blender -b --factory-startup -P docs/evaluation/showcase/T-078/tools/render_step.py -- <shot.blend> <out dir> A B N"""
import os
import sys
import time

import bpy

blend, out, fa, fb, n = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.open_mainfile(filepath=blend)
sc = bpy.context.scene
os.makedirs(out, exist_ok=True)
for f in range(int(fa), int(fb) + 1, int(n)):
    p = os.path.join(out, f"frame_{f:04d}.png")
    if os.path.exists(p):
        continue
    t = time.time()
    sc.frame_set(f)
    sc.render.filepath = p
    bpy.ops.render.render(write_still=True)
    print(f"FRAME {f} {time.time() - t:.1f}s", flush=True)
