"""T-187: cheap preview frames of an e912 scene bake (one Blender run for a list of frames; low samples).

    python3 episodes/e912_paper_boat/preview.py <shot> <run-id> <frame,frame,...> [--samples 4] [--out <dir>]

Writes a copy of <shot>/build/runs/<run-id>/bake.json holding only the listed frames (renumbered 1..n, the scene is
unchanged), renders it with pipeline/charsys/shot_render.py (640x360, review profile, --samples) and copies the frames
to <out>/<shot>_f<frame>.png (default docs/evaluation/video/T-187/preview)."""
import argparse
import json
import os
import shutil
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("shot")
    ap.add_argument("run")
    ap.add_argument("frames")
    ap.add_argument("--samples", type=int, default=4)
    ap.add_argument("--out", default=os.path.join(ROOT, "docs", "evaluation", "video", "T-187", "preview"))
    ap.add_argument("--blender", default="/usr/local/bin/blender")
    a = ap.parse_args()
    build = os.path.join(HERE, "shots", a.shot, "build")
    run = os.path.join(build, "runs", a.run)
    want = [int(f) for f in a.frames.split(",")]
    bake = json.load(open(os.path.join(run, "bake.json")))
    by = {fd["frame"]: fd for fd in bake["frame_data"]}
    sub = []
    for k, f in enumerate(want, 1):
        fd = dict(by[f])
        fd["frame"] = k
        sub.append(fd)
    bake["frame_data"], bake["frames"] = sub, [1, len(sub)]
    pdir = os.path.join(run, "preview")
    os.makedirs(pdir, exist_ok=True)
    path = os.path.join(pdir, "bake.json")
    json.dump(bake, open(path, "w"))
    cmd = [a.blender, "-b", "--factory-startup", "-P", os.path.join(ROOT, "pipeline", "charsys", "shot_render.py"), "--",
           "--bake", path, "--cast", os.path.join(build, "cast.json"), "--out", os.path.join(pdir, "render"),
           "--profile", "review", "--samples", str(a.samples), "--resolution", "640", "360"]
    with open(os.path.join(pdir, "render.log"), "w") as log:
        subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, check=True)
    os.makedirs(a.out, exist_ok=True)
    for k, f in enumerate(want, 1):
        dst = os.path.join(a.out, f"{a.shot}_f{f:03d}.png")
        shutil.copy(os.path.join(pdir, "render", f"frame_{k:04d}.png"), dst)
        print(os.path.relpath(dst, ROOT))


if __name__ == "__main__":
    main()
