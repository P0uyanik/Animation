"""R6 equivalence (T-001): compares two runs of the same shot, frames and settings, e.g. a command-line run and a
Plush Studio run. Runs inside Blender (it opens both shot.blend files):

    blender -b --factory-startup -P pipeline/production/tests/compare_runs.py -- --a <run A dir> --b <run B dir>
        [--label-a cli] [--label-b studio] --out <result.json>

A run dir holds bake.json and render/ (frames, shot.blend, shot_render.json): <shot>/build for a default
command-line run, <shot>/build/runs/<id> for a Studio run. Compared: the bake (camera per frame, skinning matrices,
morph control weights), the bone reconstruction report, camera transforms in the Blender scene, frame count and
numbers, render settings (resolution, samples, exposure, light_scale via light energies), and pixels."""
import hashlib
import json
import os
import sys

import bpy

TOL = 1e-6


def args():
    a = sys.argv[sys.argv.index("--") + 1:]
    get = lambda n, d=None: a[a.index(n) + 1] if n in a else d
    return get("--a"), get("--b"), get("--label-a", "a"), get("--label-b", "b"), get("--out")


def maxdiff(x, y):
    if len(x) != len(y):
        return float("inf")
    return max((abs(p - q) for p, q in zip(x, y)), default=0.0)


def compare_bakes(pa, pb):
    A, B = json.load(open(pa)), json.load(open(pb))
    fa = {f["frame"]: f for f in A["frame_data"]}
    fb = {f["frame"]: f for f in B["frame_data"]}
    cam = skin = morph = 0.0
    for f in fa:
        if f not in fb:
            return {"frames_equal": False}
        ca, cb = fa[f]["camera"], fb[f]["camera"]
        for k in ("position", "target", "up"):
            cam = max(cam, maxdiff(ca[k], cb[k]))
        for k in ("focalMm", "sensorWidthMm", "fStop", "focusDistance"):
            cam = max(cam, abs(ca[k] - cb[k]))
        for n in fa[f]["characters"]:
            skin = max(skin, maxdiff(fa[f]["characters"][n]["skin"], fb[f]["characters"][n]["skin"]))
            morph = max(morph, maxdiff(fa[f]["characters"][n]["morphs"], fb[f]["characters"][n]["morphs"]))
    static_keys = [k for k in A if k not in ("frame_data",)]
    static_equal = {k: A[k] == B.get(k) for k in static_keys}
    sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
    return {"byte_identical": sha(pa) == sha(pb), "frames": sorted(fa), "frames_equal": sorted(fa) == sorted(fb),
            "camera_max_abs_diff": cam, "skin_matrix_max_abs_diff": skin, "morph_weight_max_abs_diff": morph,
            "static_fields_equal": static_equal,
            "pass": sorted(fa) == sorted(fb) and cam <= TOL and skin <= TOL and morph <= TOL and all(static_equal.values())}


def blend_info(path, frames):
    bpy.ops.wm.open_mainfile(filepath=path)
    sc = bpy.context.scene
    cam = sc.camera
    mats, lens = {}, {}
    for f in frames:
        sc.frame_set(f)
        mats[f] = [v for row in cam.matrix_world for v in row]
        lens[f] = cam.data.lens
    lights = sorted((o.name, o.data.type, round(o.data.energy, 9), list(o.data.color)) for o in sc.objects if o.type == "LIGHT")
    world = sc.world.node_tree.nodes.get("Background").inputs["Strength"].default_value if sc.world and sc.world.use_nodes else None
    return {"camera_world": mats, "lens": lens,
            "settings": {"resolution": [sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage],
                         "engine": sc.render.engine, "samples": sc.cycles.samples, "denoise": sc.cycles.use_denoising,
                         "exposure": round(sc.view_settings.exposure, 9), "view_transform": sc.view_settings.view_transform,
                         "frame_range": [sc.frame_start, sc.frame_end], "fps": [sc.render.fps, sc.render.fps_base],
                         "lights": lights, "world_strength": world}}


def pixels(path):
    img = bpy.data.images.load(path, check_existing=False)
    px = list(img.pixels)
    size = list(img.size)
    bpy.data.images.remove(img)
    return size, px


def main():
    A, B, la, lb, out = args()
    res = {"labels": [la, lb], "runs": [A, B], "tolerance": TOL}
    res["bake"] = compare_bakes(os.path.join(A, "bake.json"), os.path.join(B, "bake.json"))
    ra = json.load(open(os.path.join(A, "render", "shot_render.json")))
    rb = json.load(open(os.path.join(B, "render", "shot_render.json")))
    strip = lambda c: {k: v for k, v in c.items() if k != "master"}
    res["bone_reconstruction"] = {la: {n: strip(c) for n, c in ra["characters"].items()},
                                  lb: {n: strip(c) for n, c in rb["characters"].items()}}
    res["bone_reconstruction"]["pass"] = res["bone_reconstruction"][la] == res["bone_reconstruction"][lb]
    fr_a = sorted(f for f in os.listdir(os.path.join(A, "render")) if f.startswith("frame_") and f.endswith(".png"))
    fr_b = sorted(f for f in os.listdir(os.path.join(B, "render")) if f.startswith("frame_") and f.endswith(".png"))
    res["frames"] = {la: fr_a, lb: fr_b, "count": [len(fr_a), len(fr_b)], "pass": fr_a == fr_b,
                     "report_frames": [ra["frames"], rb["frames"]]}
    frames = list(range(ra["frames"][0], ra["frames"][1] + 1))
    ia = blend_info(os.path.join(A, "render", "shot.blend"), frames)
    ib = blend_info(os.path.join(B, "render", "shot.blend"), frames)
    cm = max(maxdiff(ia["camera_world"][f], ib["camera_world"][f]) for f in frames)
    lm = max(abs(ia["lens"][f] - ib["lens"][f]) for f in frames)
    res["blender_camera"] = {"matrix_world_max_abs_diff": cm, "lens_max_abs_diff": lm, "frames": frames, "pass": cm <= TOL and lm <= TOL}
    res["render_settings"] = {la: ia["settings"], lb: ib["settings"], "report": {la: [ra["resolution"], ra["samples"]], lb: [rb["resolution"], rb["samples"]]},
                              "pass": ia["settings"] == ib["settings"] and ra["resolution"] == rb["resolution"] and ra["samples"] == rb["samples"]}
    px = {}
    ok = fr_a == fr_b
    for f in fr_a if ok else []:
        sa, pa = pixels(os.path.join(A, "render", f))
        sb, pb = pixels(os.path.join(B, "render", f))
        if sa != sb:
            px[f] = {"size": [sa, sb]}
            ok = False
            continue
        d = [abs(p - q) for p, q in zip(pa, pb)]
        n = sum(1 for i in range(0, len(d), 4) if max(d[i:i + 4]) > 0)
        px[f] = {"size": sa, "max_abs_diff_8bit": round(max(d) * 255), "differing_pixels": n}
        ok &= max(d) == 0
    res["pixels"] = {"per_frame": px, "identical": ok, "pass": ok}
    res["pass"] = all(res[k]["pass"] for k in ("bake", "bone_reconstruction", "frames", "blender_camera", "render_settings", "pixels"))
    json.dump(res, open(out, "w"), indent=1)
    print("[compare_runs]", "PASS" if res["pass"] else "FAIL", json.dumps({k: res[k].get("pass") for k in
          ("bake", "bone_reconstruction", "frames", "blender_camera", "render_settings", "pixels")}))


main()
