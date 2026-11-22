"""Blender prelude for the T-197 settings and per-frame timing."""
import os
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True

import bpy

sys.path.insert(0, str(Path.cwd() / "code/pipeline/charsys"))
import render_engine

original = render_engine.configure


def configure(scene, engine, samples):
    result = original(scene, engine, samples)
    if engine == "eevee":
        scene.eevee.shadow_pool_size = "128"
        scene.eevee.use_raytracing = True
        scene.eevee.ray_tracing_method = "SCREEN"
        scene.eevee.ray_tracing_options.resolution_scale = "4"
    else:
        scene.cycles.device = "CPU"
        scene.cycles.denoiser = "OPENIMAGEDENOISE"
        scene.cycles.denoising_use_gpu = False
    return result


render_engine.configure = configure


@bpy.app.handlers.persistent
def start(scene, *_):
    global frame_start
    frame_start = time.time()


@bpy.app.handlers.persistent
def written(scene, *_):
    with open(os.environ["T208_TIMES"], "a", encoding="utf-8") as f:
        print(scene.frame_current, frame_start, time.time(), sep=",", file=f)


bpy.app.handlers.render_pre.append(start)
bpy.app.handlers.render_write.append(written)
