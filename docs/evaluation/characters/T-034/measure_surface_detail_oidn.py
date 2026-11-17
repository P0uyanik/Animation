"""T-034: does the shared surface-detail layer survive OIDN?

Renders a gently curved panel with each cloth preset twice (surface_detail on/off), 32 spp + OIDN (albedo and normal
guides, as the turnaround renders), character_neutral-like key light, and measures the band-pass contrast at the
layer's scale (difference of Gaussians, sigma 2 px - 24 px, on luminance, 0..255). It also renders without a
denoiser at 512 spp as a noise-free reference, so "survives" means: the OIDN contrast gain matches the noise-free gain.

    blender -b --factory-startup -P docs/evaluation/characters/T-034/measure_surface_detail_oidn.py -- <out.json> [<png dir>]
"""
import json
import math
import os
import sys

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "pipeline", "charsys"))
from materials import builder as MB  # noqa: E402

PRESETS = [("felt", (144, 104, 104)), ("woven cotton", (214, 210, 210)), ("boot fleece", (132, 88, 68)),
           ("skin-felt", (226, 186, 168))]
SIZE = 256


def scene_setup():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.render.resolution_x = sc.render.resolution_y = SIZE
    sc.render.film_transparent = False
    sc.view_settings.view_transform = "Standard"
    world = bpy.data.worlds.new("w")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.05, 0.05, 0.055, 1)
    sc.world = world
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=96, y_subdivisions=96, size=0.2)
    panel = bpy.context.object
    for v in panel.data.vertices:  # a gentle cylinder bend, like a sleeve or a vest panel
        v.co.z = -2.0 * v.co.x ** 2
    panel.data.shade_smooth()
    panel.rotation_euler = (math.radians(90), 0, 0)
    bpy.ops.object.camera_add(location=(0, -0.42, 0))
    cam = bpy.context.object
    cam.rotation_euler = (math.radians(90), 0, 0)
    cam.data.lens = 85
    sc.camera = cam
    bpy.ops.object.light_add(type="AREA", location=(0.25, -0.3, 0.25))
    key = bpy.context.object
    key.data.energy = 1.5
    key.data.size = 0.25
    key.rotation_euler = (math.radians(55), 0, math.radians(40))
    return sc, panel


def render(sc, path, samples, denoise):
    sc.cycles.samples = samples
    sc.cycles.use_denoising = denoise
    if denoise:
        sc.cycles.denoiser = "OPENIMAGEDENOISE"
        sc.cycles.denoising_input_passes = "RGB_ALBEDO_NORMAL"
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(path)
    px = np.array(img.pixels[:]).reshape(SIZE, SIZE, 4)[..., :3]
    bpy.data.images.remove(img)
    return px


def lum(px):
    return ((0.2126 * px[..., 0] + 0.7152 * px[..., 1] + 0.0722 * px[..., 2]) * 255.0)[64:192, 64:192]


def band_contrast(px):
    from numpy.fft import fft2, ifft2
    y = (0.2126 * px[..., 0] + 0.7152 * px[..., 1] + 0.0722 * px[..., 2]) * 255.0
    c = y[64:192, 64:192]

    def blur(a, s):
        k = np.fft.fftfreq(a.shape[0])
        g = np.exp(-2 * (np.pi * s) ** 2 * (k[:, None] ** 2 + k[None, :] ** 2))
        return np.real(ifft2(fft2(a) * g))
    return float(np.std(blur(c, 2.0) - blur(c, 24.0)))


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    out = argv[0]
    png_dir = argv[1] if len(argv) > 1 else os.path.join(os.path.dirname(out), "oidn_swatches")
    os.makedirs(png_dir, exist_ok=True)
    sc, panel = scene_setup()
    rows = {}
    for name, colour in PRESETS:
        row, arrays = {}, {}
        for state in ("off", "on"):
            mat = MB.build_material(f"M_{name}_{state}", name, colour, 0.3,
                                    {"surface_detail": {"enabled": state == "on"}})
            panel.data.materials.clear()
            panel.data.materials.append(mat)
            slug = name.replace(" ", "_").replace("/", "_")
            for label, samples, denoise in (("oidn32", 32, True), ("ref512", 512, False)):
                px = render(sc, os.path.join(png_dir, f"{slug}_{state}_{label}.png"), samples, denoise)
                arrays[f"{state}_{label}"] = px
                row[f"{state}_{label}"] = round(band_contrast(px), 3)
        # The layer's own signal: luminance of (on - off), noise-free vs OIDN, and how well OIDN keeps it.
        d_ref = lum(arrays["on_ref512"]) - lum(arrays["off_ref512"])
        d_oidn = lum(arrays["on_oidn32"]) - lum(arrays["off_oidn32"])
        row["detail_signal_std_ref512"] = round(float(np.std(d_ref)), 3)
        row["detail_signal_std_oidn32"] = round(float(np.std(d_oidn)), 3)
        row["oidn_vs_noise_free_correlation"] = round(float(np.corrcoef(d_ref.ravel(), d_oidn.ravel())[0, 1]), 3)
        rows[name] = row
        print(name, row, flush=True)
    json.dump({"detail_signal": "std of the on-minus-off luminance (0..255), centre 128 px; correlation of that "
                                "difference between OIDN 32 spp and noise-free 512 spp",
               "metric": "band-pass luminance std (DoG 2-24 px, 0..255), centre 128 px",
               "presets": rows}, open(out, "w"), indent=1)


main()
