"""Writes episodes/e910_showcase/shots/s010_e1/shot.scene.json (T-134): the T-117 showcase shot s010, unchanged, plus
the opt-in scene key "reachMechanics". Usage: python3 make_e1_shot.py ['<json value of reachMechanics>']"""
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
SRC = os.path.join(ROOT, "episodes", "e910_showcase", "shots", "s010", "shot.scene.json")
OUT = os.path.join(ROOT, "episodes", "e910_showcase", "shots", "s010_e1", "shot.scene.json")

with open(SRC, encoding="utf-8") as f:
    scene = json.load(f)
scene["reachMechanics"] = json.loads(sys.argv[1]) if len(sys.argv) > 1 else True
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8", newline="\n") as f:
    json.dump(scene, f, indent=1)
    f.write("\n")
print(os.path.relpath(OUT, ROOT), "reachMechanics =", json.dumps(scene["reachMechanics"]))
