"""T-185: the "before" scene of a shot that now carries the r3 cup grasp: run_shot's resolved scene with every
"fingerClose" and "x_t185" removed, written under <repo>/build/t185/<name>/ so the engine and shot_render.py find the
shared content/assets (the released cup) instead of the episode's copy. Character package paths are made absolute.
    python3 docs/evaluation/interaction/T-185/before_scene.py <shot.resolved.scene.json> <name>"""
import json, os, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
src, name = sys.argv[1], sys.argv[2]
s = json.load(open(src))
for a in s["actions"]:
    a.pop("fingerClose", None)
s.pop("x_t185", None)
for c in s["characters"]:
    if not os.path.isabs(c["asset"]):
        c["asset"] = os.path.abspath(os.path.join(os.path.dirname(src), c["asset"]))
out = os.path.join(ROOT, "build", "t185", name, "before.scene.json")
os.makedirs(os.path.dirname(out), exist_ok=True)
json.dump(s, open(out, "w"), indent=1)
print(out)
