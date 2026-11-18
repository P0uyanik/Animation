"""T-093b: garment region score for a finished `tools/fit/run.py` output (read-only use of tools/fit).

    python3 docs/evaluation/characters/T-093b/garment_score.py --fit <fit out dir> --blender <exe> \
        --garments blouse,shorts [--hem shorts]

For every trial, a second flat Workbench pass (same camera placement and visibility as tools/fit/render.py) labels the
objects under `garment.<name>.` per requested garment. The trial's recorded registration (scale, ox, oy in
score.json) places each label mask in reference crop coordinates, where it is compared with the annotated
`garment:<name>` region (IoU). The garment score of a view is the mean of its garment IoUs (x100); the trial score is
the mean over views (equal weight). Optional `--hem <name>`: lowest visible edge (image y) error in px against the
reference region's lowest pixel. Writes <fit>/garment_scores.json and prints one line per trial.

As T-090b's garment selection: the stock fit score (silhouette, eyes, chin/nose) stays in scores.json; this adds
the garment term the stock objective lacks."""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
COLOURS = [(1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 0)]


def worker(job_path):
    import bpy
    sys.path[:0] = [str(ROOT / "pipeline/blender"), str(ROOT / "tools/fit")]
    import compare_harness as cameras
    job = json.load(open(job_path))
    bpy.ops.wm.open_mainfile(filepath=job["blend"])
    scene = bpy.context.scene
    root = next(c for c in bpy.data.collections if c.get("ps_character_id"))
    objects = [o for o in root.all_objects if o.type in ("MESH", "CURVES")
               and not o.hide_render and not o.name.startswith("WGT")]
    names = job["garments"]
    for o in objects:
        c = (1, 1, 1)
        for i, g in enumerate(names):
            if o.name.startswith(f"garment.{g}."):
                c = COLOURS[i]
        o.color = (*c, 1)
    cam = bpy.data.objects.new("Fit camera", bpy.data.cameras.new("Fit camera"))
    scene.collection.objects.link(cam)
    scene.camera = cam
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.resolution_y = job["height"]
    scene.render.resolution_x = job["height"] // 2
    scene.render.resolution_percentage = 100
    scene.display.render_aa = "OFF"
    sh = scene.display.shading
    sh.light, sh.color_type = "FLAT", "OBJECT"
    sh.show_shadows = sh.show_cavity = sh.show_specular_highlight = False
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    for i, view in enumerate(job["views"]):
        prefixes = tuple(view.get("hide_objects_prefix", ()))
        for o in objects:
            o.hide_render = (o.name == "glasses_lens" or
                             (o.name.startswith(prefixes) and not o.name.startswith("garment.")))
        lo, hi = cameras.bbox([o for o in objects if not o.hide_render])
        cameras.place_camera(cam, (lo + hi) / 2, view["yaw_deg"], view["elevation_deg"], view["focal_mm_estimate"],
                             lo, hi, scene.render.resolution_x / scene.render.resolution_y, 0.9)
        bpy.context.view_layer.update()
        scene.render.filepath = str(Path(job["out"]) / f"garment-{i:03d}.png")
        bpy.ops.render.render(write_still=True)


def drive(args):
    import numpy as np
    from PIL import Image
    sys.path[:0] = [str(ROOT / "tools/fidelity")]
    import analysis as fidelity
    import metrics
    fit = Path(args.fit).resolve()
    scores = json.load(open(fit / "scores.json"))
    names = args.garments.split(",")
    out = {"garments": names, "trials": []}
    for it in scores["iterations"]:
        work = fit / f"trial-{it['trial']:03d}"
        job = json.load(open(work / "render-job.json"))
        gj = {"blend": str((work / job["blend"]).resolve()), "views": job["views"], "height": job["height"],
              "garments": names, "out": str(work)}
        jp = work / "garment-job.json"
        json.dump(gj, open(jp, "w"))
        if not all((work / f"garment-{i:03d}.png").is_file() for i in range(len(job["views"]))):
            subprocess.run([args.blender, "-b", "--factory-startup", "-P", __file__, "--", "--worker", str(jp)],
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        views = {}
        for i, view in enumerate(job["views"]):
            vid = view["id"]
            al = it["views"][vid]["alignment"]
            rgba = np.asarray(Image.open(work / f"garment-{i:03d}.png").convert("RGBA")).astype(np.int16)
            fig = rgba[:, :, 3] > 127
            ref_ann = json.load(open(args.annotations / f"{vid}.json"))
            size = tuple(ref_ann["size"])
            v = {}
            for k, g in enumerate(names):
                lab = fig & (np.abs(rgba[:, :, :3] - np.array(COLOURS[k]) * 255).max(axis=2) < 40)
                m = fidelity.place(lab, al["scale"], al["ox"], al["oy"], (size[1], size[0]))
                ref = fidelity.poly_mask(size, ref_ann["regions"].get(f"garment:{g}", []))
                v[g] = {"iou": metrics.iou(ref, m) or 0.0}
                if g == args.hem and m.any() and ref.any():
                    v[g]["hem_err_px"] = float(abs(np.nonzero(m)[0].max() - np.nonzero(ref)[0].max()))
            v["score"] = float(np.mean([v[g]["iou"] for g in names]) * 100)
            views[vid] = v
        rec = {"trial": it["trial"], "parameters": it["parameters"], "fit_score": it["score"],
               "garment_score": float(np.mean([v["score"] for v in views.values()])), "views": views}
        out["trials"].append(rec)
        print(f"trial {it['trial']}: garment {rec['garment_score']:.2f} fit {it['score']:.2f} "
              + " ".join(f"{vid}:" + ",".join(f"{g}={v[g]['iou']:.3f}" for g in names) for vid, v in views.items()))
    best = max(out["trials"], key=lambda r: (r["garment_score"], -r["trial"]))
    out["best"] = best["trial"]
    json.dump(out, open(fit / "garment_scores.json", "w"), indent=1)
    print("best trial", best["trial"])


if __name__ == "__main__":
    if "--worker" in sys.argv:
        worker(sys.argv[sys.argv.index("--worker") + 1])
    else:
        ap = argparse.ArgumentParser(description=__doc__)
        ap.add_argument("--fit", required=True)
        ap.add_argument("--blender", default="blender")
        ap.add_argument("--garments", required=True)
        ap.add_argument("--hem", default="")
        ap.add_argument("--annotations", type=Path, required=True)
        drive(ap.parse_args())
