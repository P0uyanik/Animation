"""Renders the harness cameras (cameras.json from pipeline/blender/compare_harness.py) with Plush Studio's own
renderer, so every comparison view also shows the subject with its full Plush look (fibres, procedural textures).

    python3 pipeline/plush_views.py --scene content/scenes/compare_it4_boy.scene.json \
        --cameras renders/compare/it4_boy/blender/cameras.json --out renders/compare/it4_boy/plush [--spp 48]

Writes a temporary scene with one frame per view (step-keyed camera position, target and lens) next to the output
and renders it in one run (the character is built once). Uses the existing plush-render; no engine changes."""
import argparse
import json
import os
import subprocess


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", required=True)
    ap.add_argument("--cameras", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--spp", type=int, default=48)
    ap.add_argument("--render", default="build/apps/render-cli/plush-render")
    a = ap.parse_args()
    cams = json.load(open(a.cameras))
    s = json.load(open(a.scene))
    scene_dir = os.path.dirname(os.path.abspath(a.scene))
    for c in s["characters"]:  # absolute asset paths: the generated scene lives elsewhere
        c["asset"] = os.path.normpath(os.path.join(scene_dir, c["asset"]))
    views = cams["views"]
    s["frameStart"], s["frameEnd"] = 1, len(views)
    step = lambda vals: [[i + 1, v, "step"] for i, v in enumerate(vals)]
    s["animation"] = {
        "camera.position": step([v["camera_plush"] for v in views]),
        "camera.target": step([v["target_plush"] for v in views]),
        "camera.lens": step([[v["focal_mm"], 0.0, -1.0] for v in views]),
    }
    os.makedirs(a.out, exist_ok=True)
    gen = os.path.join(a.out, "views.scene.json")
    json.dump(s, open(gen, "w"), indent=1)
    subprocess.run([a.render, gen, "--frames", f"1-{len(views)}", "--outdir", a.out, "--width", str(cams["width"]),
                    "--height", str(cams["height"]), "--spp", str(a.spp), "--adaptive", "0.1"], check=True)
    for i, v in enumerate(views):  # frame_0001.png -> <view id>.png
        src = os.path.join(a.out, f"frame_{i + 1:04d}.png")
        if os.path.exists(src):
            os.replace(src, os.path.join(a.out, v["id"] + ".png"))
    print("plush views:", len(views))


if __name__ == "__main__":
    main()
