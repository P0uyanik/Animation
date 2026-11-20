"""T-124: finds still-camera spans and identical hold frames in an engine shot bake (plush.shot_bake/1).

    python3 tools/render_bench/holds.py <bake.json> [--eps 1e-6]

A frame is a hold of the previous one only if *everything* in the bake is equal within eps: camera, lights, props
and every character's skinning matrices and morph/control weights. Only such frames may reuse a rendered image."""
import json
import sys


def flat(x, out):
    if isinstance(x, dict):
        for k in sorted(x):
            if k != "frame":
                flat(x[k], out)
    elif isinstance(x, list):
        for v in x:
            flat(v, out)
    elif isinstance(x, (int, float)) and not isinstance(x, bool):
        out.append(float(x))
    return out


def main():
    bake = json.load(open(sys.argv[1]))
    eps = float(sys.argv[sys.argv.index("--eps") + 1]) if "--eps" in sys.argv else 1e-6
    fds = sorted(bake["frame_data"], key=lambda f: f["frame"])
    cam = [flat(f["camera"], []) for f in fds]
    full = [flat(f, []) for f in fds]
    still_cam = all(max(abs(a - b) for a, b in zip(cam[0], c)) <= eps for c in cam)
    holds, spans, cur = [], [], None
    for i in range(1, len(fds)):
        d = max(abs(a - b) for a, b in zip(full[i - 1], full[i])) if len(full[i]) == len(full[i - 1]) else float("inf")
        if d <= eps:
            holds.append(fds[i]["frame"])
            cur = cur or [fds[i - 1]["frame"], fds[i]["frame"]]
            cur[1] = fds[i]["frame"]
        elif cur:
            spans.append(cur)
            cur = None
    if cur:
        spans.append(cur)
    print(json.dumps({"frames": [fds[0]["frame"], fds[-1]["frame"]], "camera_still": still_cam, "eps": eps,
                      "identical_hold_frames": len(holds), "hold_spans": spans}, indent=1))


if __name__ == "__main__":
    main()
