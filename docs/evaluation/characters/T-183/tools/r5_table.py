"""T-183 round 3: per-surface numbers of one measured bake, split by the frames where the body animation jumps.

    python3 r5_table.py <bake.json> <character> <props measure.json> <body measure.json> [--pad=1] [--min-mm=1]

For every pair hair part > surface of the two measure JSONs (measure_props.py, measure_body.py; per-frame rows):
worst depth, frames and vertices over all frames, and the same over the frames that are NOT snap frames. A snap frame
is one where a body bone of the measured character or of the character whose surface it is turns > 45 degrees or
travels > 100 mm within that one frame (tools/snaps.py), widened by --pad frames to each side. Prints a JSON."""
import json
import sys

from snaps import snap_frames

args = [a for a in sys.argv[1:] if not a.startswith("--")]
o = {a.split("=", 1)[0][2:]: a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--") and "=" in a}
pad = int(o.get("pad", 1))
bake, who = args[0], args[1]
snaps = snap_frames(bake)


def snapset(names):
    s = set()
    for n in names:
        for f in snaps.get(n, {}):
            s.update(range(f - pad, f + pad + 1))
    return s


out = {"bake": bake, "character": who, "snap_frames": {c: sorted(r) for c, r in snaps.items() if r}, "pad": pad, "pairs": {}}
for path in args[2:]:
    d = json.load(open(path))
    for row in d["frames"]:
        for pair, (mm, n) in row.get("by_pair", {}).items():
            surf = pair.split(">", 1)[1]
            other = surf.split(":", 1)[0] if ":" in surf and not surf.startswith(("object:", "prop:")) else None
            sn = snapset([who] + ([other] if other else []))
            p = out["pairs"].setdefault(pair, {"all": [0.0, 0, 0, []], "calm": [0.0, 0, 0, []]})
            for key in ("all",) + (("calm",) if row["frame"] not in sn else ()):
                q = p[key]
                q[0], q[1], q[2] = max(q[0], mm), q[1] + 1, max(q[2], n)
                q[3].append(row["frame"])
for p in out["pairs"].values():
    for key in ("all", "calm"):
        mm, fr, n, frames = p[key]
        p[key] = {"max_mm": mm, "frames": fr, "max_vertices": n, "first": min(frames) if frames else None, "last": max(frames) if frames else None,
                  "list": frames if len(frames) <= 12 else None}
print(json.dumps(out, indent=1))
