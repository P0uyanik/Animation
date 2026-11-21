"""T-184: cut a few frames out of an engine bake (plush.shot_bake/1) so the evidence can be rebuilt without the
branch that baked it.

    python3 make_excerpt.py --bake <bake.json> --frames 24,150 --source "<branch@sha, shot>" --out bake_excerpt.json

The kept frames are renumbered 1..N (shot_render.py keys every frame of the range); "x_t184" records the source and
the original frame numbers. Package and scene paths are replaced by notes: shot_render.py takes the masters from its
--cast file and does not read them."""
import argparse
import json

ap = argparse.ArgumentParser()
ap.add_argument("--bake", required=True)
ap.add_argument("--frames", required=True)
ap.add_argument("--source", required=True)
ap.add_argument("--out", required=True)
a = ap.parse_args()
bake = json.load(open(a.bake))
want = [int(f) for f in a.frames.split(",")]
by_frame = {fd["frame"]: fd for fd in bake["frame_data"]}
data = []
for k, f in enumerate(want, 1):
    data.append(dict(by_frame[f], frame=k))
bake["frame_data"], bake["frames"] = data, [1, len(want)]
for c in bake["characters"]:
    c["package"] = f"(not stored: the engine package of {c['name']})"
bake["scene_path"] = "(not stored)"
bake["x_t184"] = {"source": a.source, "source_frames": {str(k): f for k, f in enumerate(want, 1)}}
json.dump(bake, open(a.out, "w"), separators=(",", ":"))
print(a.out, len(data), "frames")
