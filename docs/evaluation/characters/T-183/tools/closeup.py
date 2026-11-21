"""Close-up cameras for a shot bake (T-183 round 2): writes a copy of a plush.shot_bake/1 whose camera is one of the
fixed close-up views of the girl in e909 s010, for pipeline/charsys/shot_render.py (same lights, same animation).

    python3 closeup.py <bake.json> <out_bake.json> <view> [--frames=A-B]

Views (world space, fixed for the whole shot so that only the figure moves; the girl sits at x = -0.28, faces +Z):
  side      her right side, level with the head                       back      straight from behind
  shoulder  over her right shoulder, from behind and above            arm       front three-quarter on her right (the
  side_l    front three-quarter on her left (the boy's side)                    hand that goes to the temple, f24-27)
--frames keeps only those frames in the copy (a smaller file; shot_render.py takes --frames as well)."""
import json
import sys

VIEWS = {  # position, target, focal length (mm)
    "side": ([-1.22, 0.74, 0.02], [-0.28, 0.64, 0.0], 32.0),
    "back": ([-0.33, 0.80, -0.98], [-0.28, 0.62, 0.0], 32.0),
    "shoulder": ([-0.78, 0.98, -0.62], [-0.27, 0.62, 0.02], 32.0),
    "arm": ([-0.80, 0.80, 0.72], [-0.29, 0.62, 0.0], 32.0),
    "side_l": ([0.02, 0.86, 0.80], [-0.27, 0.62, 0.0], 32.0),
}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    src, dst, view = args
    pos, target, focal = VIEWS[view]
    fr = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--frames=")), None)
    b = json.load(open(src))
    if fr:
        lo, hi = (int(x) for x in fr.split("-"))
        b["frame_data"] = [fd for fd in b["frame_data"] if lo <= fd["frame"] <= hi]
        b["frames"] = [lo, hi]
    for fd in b["frame_data"]:
        fd["camera"].update(position=pos, target=target, focalMm=focal, fStop=0.0)
    b["scene"] = f"{b.get('scene', '')} [close-up: {view}]"
    json.dump(b, open(dst, "w"))


if __name__ == "__main__":
    main()
