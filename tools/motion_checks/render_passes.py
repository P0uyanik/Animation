"""T-125: renders a shot.blend (from pipeline/charsys/shot_render.py --blend-only) with the passes the flicker check
needs, one uncompressed multilayer EXR per frame (Blender, or tools/bpy_blender.py with the pinned bpy wheel):

    blender -b --factory-startup -P tools/motion_checks/render_passes.py -- --blend shot.blend --out <dir> \
        [--frames A-B] [--samples N] [--resolution W H] [--vectors-only]

Each <dir>/NNNN.exr holds the denoised image (ViewLayer.Combined), the noisy image before the denoiser
(ViewLayer.Noisy Image, Cycles denoising data) and the object index (ViewLayer.IndexOB) of the region class set
below, and the motion vectors (ViewLayer.Vector: pixels to the previous / next frame; motion blur stays off, as in
production). --vectors-only renders 1 sample without the denoiser and keeps only the vectors (NNNN_vec.npz), to add
motion compensation to frames rendered before. Only this in-memory copy is changed (pass indices, output settings); the .blend file is not saved.

Region classes (object index): 1 hair (object or material name starts with / contains "hair"), 2 fibres (other
curves: garment and felt fibres), 3 skin (a material with "skin" in its name), 4 cloth and props (other character /
prop geometry), 0 background (world, room objects: wall, floor, table).

With --npz (default) each EXR is reduced right after its render to <dir>/NNNN.npz (luminance of both images, object
index, depth, normal; float16 / uint8, about 2.5 MB) and the EXR is removed (--keep-exr keeps it)."""
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import frames as FR  # noqa: E402

REGIONS = {"background": 0, "hair": 1, "fibres": 2, "skin": 3, "cloth": 4}
ROOM = ("floor", "wall", "table", "world", "backdrop")


def region_of(o):
    mats = [s.material.name.lower() for s in getattr(o, "material_slots", []) if s.material]
    name = o.name.lower()
    if any(name.removeprefix("prop.").startswith(r) for r in ROOM):  # shot_render names room objects prop.<name>
        return "background"
    if "hair" in name or any("hair" in m for m in mats):
        return "hair"
    if o.type == "CURVES":
        return "fibres"
    if any("skin" in m for m in mats):
        return "skin"
    return "cloth"


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    opt = {"--frames": "", "--samples": "", "--resolution": None, "--keep-exr": False, "--vectors-only": False}
    i = 0
    while i < len(argv):
        k = argv[i]
        if k in ("--keep-exr", "--vectors-only"):
            opt[k] = True
            i += 1
        elif k == "--resolution":
            opt[k] = (int(argv[i + 1]), int(argv[i + 2]))
            i += 3
        else:
            opt[k] = argv[i + 1]
            i += 2
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(opt["--blend"]))
    sc = bpy.context.scene
    counts = {}
    for o in sc.objects:
        if o.type in ("MESH", "CURVES", "CURVE", "SURFACE"):
            r = region_of(o)
            o.pass_index = REGIONS[r]
            counts[r] = counts.get(r, 0) + 1
    if opt["--samples"]:
        sc.cycles.samples = int(opt["--samples"])
    if opt["--resolution"]:
        sc.render.resolution_x, sc.render.resolution_y = opt["--resolution"]
        sc.render.resolution_percentage = 100
    vl = sc.view_layers[0]
    vl.use_pass_vector = True
    sc.render.use_motion_blur = False
    if opt["--vectors-only"]:
        sc.cycles.samples = 1
        sc.cycles.use_denoising = False
    else:
        sc.cycles.use_denoising = True
        vl.cycles.denoising_store_passes = True
        vl.use_pass_object_index = True
    st = sc.render.image_settings
    st.media_type = "MULTI_LAYER_IMAGE"
    st.file_format = "OPEN_EXR_MULTILAYER"
    st.color_depth = "32"
    st.exr_codec = "NONE"
    if opt["--frames"]:
        a, _, b = opt["--frames"].partition("-")
        sc.frame_start, sc.frame_end = int(a), int(b or a)
    out = os.path.abspath(opt["--out"])
    os.makedirs(out, exist_ok=True)
    print(f"[render_passes] regions {counts} frames {sc.frame_start}-{sc.frame_end} samples {sc.cycles.samples} "
          f"seed {sc.cycles.seed} animated_seed {sc.cycles.use_animated_seed} denoiser {sc.cycles.denoiser}")
    for f in range(sc.frame_start, sc.frame_end + 1):
        path = os.path.join(out, f"{f:04d}.exr")
        npz = path[:-4] + ("_vec.npz" if opt["--vectors-only"] else ".npz")
        if os.path.exists(npz) or os.path.exists(path):
            continue
        sc.frame_set(f)
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        FR.exr_to_npz(path, npz, vectors_only=opt["--vectors-only"])
        if not opt["--keep-exr"]:
            os.remove(path)


main()
