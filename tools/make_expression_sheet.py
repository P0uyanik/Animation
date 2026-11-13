"""Ten-expression test for one character (frames 1-10). Run from the repository root:
python3 tools/make_expression_sheet.py [character_file_stem]"""
import json, sys
asset = sys.argv[1] if len(sys.argv) > 1 else "girl_white_hair"
s = json.load(open("content/scenes/test_lineup.scene.json"))
s["name"] = f"Test - expressions ({asset})"
s["frameStart"], s["frameEnd"] = 1, 10
s["characters"] = [{"name": "ch", "asset": f"../characters/{asset}.character.json", "position": [0, 0.012, 0], "yawDeg": 0}]
cam = [0.0, 0.85, 0.78]
s["camera"].update(position=cam, target=[0.0, 0.8, 0.1], focalMm=60, fStop=0, focusDistance=-1)
labels = ["neutral", "happy", "surprised", "sad", "annoyed", "blink", "look left", "look right", "look down", "look at camera"]
# Per frame: smile, mouthOpen, frown, brow X (raise <0), brow tilt Z (sad <0, angry >0), lid rotation, look-at target
F = [
    (0, 0, 0, 0, 0, 0, cam),
    (1, 0.08, 0, -3, 0, 12, cam),
    (0, 1, 0, -8, 0, -4, cam),
    (0, 0, 1, -4, -9, 20, [0.0, 0.5, 0.6]),
    (0, 0, 0.6, 5, 9, 30, cam),
    (0, 0, 0, 0, 0, 86, cam),
    (0, 0, 0, 0, 0, 0, [0.7, 0.8, 0.45]),
    (0, 0, 0, 0, 0, 0, [-0.7, 0.8, 0.45]),
    (0, 0, 0, 0, 0, 8, [0.0, 0.25, 0.55]),
    (0.4, 0.1, 0, -2, 0, 0, cam),
]
step = lambda vals: [[i + 1, v, "step"] for i, v in enumerate(vals)]
s["animation"] = {
    "ch/expr.smile": step([f[0] for f in F]),
    "ch/expr.mouthOpen": step([f[1] for f in F]),
    "ch/expr.frown": step([f[2] for f in F]),
    "ch/brow.L.rot": step([[f[3], 0, f[4]] for f in F]),
    "ch/brow.R.rot": step([[f[3], 0, -f[4]] for f in F]),
    "ch/lid.L.rot": step([[f[5], 0, 0] for f in F]),
    "ch/lid.R.rot": step([[f[5], 0, 0] for f in F]),
    "ch/lookAt": step([f[6] for f in F]),
}
s["labels"] = labels
out = f"content/scenes/test_expressions_{asset}.scene.json"
json.dump(s, open(out, "w"), indent=1)
print("wrote", out)
