#!/usr/bin/env python3
"""T-053 evidence shots: the personality regression shot (tools/animcheck/make_shots.py personality_scene) on the
CURRENT approved character versions (run_shot cast "current", T-062: boy 1.1.0, girl 0.10.0), with profiles (after)
and without (before). Same idle + gesture timing in both.

    python3 docs/evaluation/animation/T-053/make_evidence.py
    python3 pipeline/production/run_shot.py --shot docs/evaluation/animation/T-053/shots/<after|before>/shot.scene.json \\
        --blender <blender> --stages prepare,bake
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "tools/animcheck"))
import make_shots  # noqa: E402

PRODUCTION = {
    "cast": {"boy": {"character_id": "boy_yellow_hoodie", "version": "current"},
             "girl": {"character_id": "girl_auburn_bun_glasses", "version": "current"}},
    "profile": "pipeline/charsys/rig_profiles/humanoid_rigify.json",
    "render": {"resolution": [640, 360], "samples": 16, "light_scale": 1.0},
}


def main():
    for name, profiles in (("after", True), ("before", False)):
        scene = make_shots.personality_scene(profiles)
        scene["name"] = f"T-053 evidence ({name}): " + scene["name"].split(": ", 1)[1]
        for ch in scene["characters"]:
            ch["asset"] = "(set by run_shot)"
        scene["production"] = PRODUCTION
        out = HERE / "shots" / name / "shot.scene.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(scene, indent=1) + "\n")
        print("wrote", out.relative_to(ROOT))


if __name__ == "__main__":
    main()
