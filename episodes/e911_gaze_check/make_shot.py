"""Writes the T-120 gaze-legibility eval shots (python3):

    python3 episodes/e911_gaze_check/make_shot.py

Both are the T-095 exchange episodes/e907_exchange/shots/s010/shot.scene.json (read, not changed): same cast
("current"), staging, actions, camera and timing, so its cup looks and partner looks are checked in the shot camera.
- shots/s010_default/shot.scene.json: the scene as it is (no "gazeLegibility": the engine's default gaze).
- shots/s010_legible/shot.scene.json: plus the scene key GAZE below (T-120, scene.h GazeLegibility). rangeDeg is both
  characters' spec face.eyes.gaze_range_deg; the head caps stay the shot's own life.gaze assistYawDeg / assistPitchDeg
  unless HEAD overrides them per character.
"""
import copy
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SOURCE = os.path.join(ROOT, "episodes", "e907_exchange", "shots", "s010", "shot.scene.json")
OUT = os.path.join(ROOT, "episodes", "e911_gaze_check", "shots")
GAZE = {"rangeDeg": [16, 8]}
HEAD = {"boy": {"headPitchDeg": 10}}  # per character: extra "gazeLegibility" fields (his fringe hides a head-down glance)


def main():
    with open(SOURCE, encoding="utf-8") as f:
        base = json.load(f)
    for name, legible in (("s010_default", False), ("s010_legible", True)):
        s = copy.deepcopy(base)
        s["name"] = "e911_gaze_check %s: T-120 eval copy of e907_exchange s010 (%s)" % (
            name, "gazeLegibility on" if legible else "engine default gaze")
        if legible:
            s["gazeLegibility"] = GAZE
            for c in s["characters"]:
                if c["name"] in HEAD:
                    c["gazeLegibility"] = HEAD[c["name"]]
        s["x_t120"] = {"source": "episodes/e907_exchange/shots/s010/shot.scene.json", "gazeLegibility": legible}
        path = os.path.join(OUT, name, "shot.scene.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(s, f, indent=1)
            f.write("\n")
        print("wrote", os.path.relpath(path, ROOT))


if __name__ == "__main__":
    main()
