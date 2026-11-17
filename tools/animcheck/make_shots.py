#!/usr/bin/env python3
"""Writes the animation regression shots of tools/animcheck (T-061).

`shots/wave_touch.scene.json` is the T-045 evidence shot (docs/evaluation/animation/T-045/make_shot.py, body mechanics
on) on the engine test packages (tests/data/imported): boy 1.0.0 and girl m3, idle -> touch (IK point gesture) -> wave
clip (speed 1.5, blendIn 4, weight 0.75 / 1.0). It is engine-only (no Blender), so the gate can bake it in seconds.
`shots/clip_gestures.scene.json`: library gesture clips at their default blends and at speed 1 / 1.5 / 0.8 (point,
wave mirrored, shrug) on both packages, so retiming and blending are checked away from the T-045 timing too.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
T045 = ROOT / "docs/evaluation/animation/T-045/shot_after/shot.scene.json"
PACKAGES = {"boy": "../../../tests/data/imported/boy_yellow_hoodie_1.0.0/character.json",
            "girl": "../../../tests/data/imported/girl_auburn_bun_glasses_m3/character.json"}


def base_scene(name, frame_end):
    src = json.loads(T045.read_text())
    scene = {k: src[k] for k in ("format", "version", "frameRate", "render", "camera", "materials", "lights")}
    scene.update({"name": name, "frameStart": 1, "frameEnd": frame_end})
    scene["objects"] = [o for o in src["objects"]]
    scene["characters"] = []
    for ch in src["characters"]:
        ch = dict(ch)
        ch["asset"] = PACKAGES[ch["name"]]
        scene["characters"].append(ch)
    return src, scene


def main():
    src, scene = base_scene("animcheck: T-045 idle -> touch -> wave (body mechanics on, test packages)", 132)
    scene["actions"] = src["actions"]
    write("wave_touch", scene)

    _, scene = base_scene("animcheck: library gesture clips at three speeds", 250)
    scene["objects"] = [o for o in scene["objects"] if not o["name"].startswith("plinth")]
    scene["actions"] = []
    for name, off in (("boy", 0), ("girl", 3)):
        scene["actions"] += [
            {"type": "look", "character": name, "start": 1, "end": 250, "camera": True},
            {"type": "clip", "character": name, "clip": "point", "start": 6 + off, "speed": 1.0},
            {"type": "clip", "character": name, "clip": "wave", "start": 100 + off, "speed": 1.5, "mirror": True},
            {"type": "clip", "character": name, "clip": "gest_shrug", "start": 176 + off, "speed": 0.8},
        ]
    write("clip_gestures", scene)


def write(name, scene):
    out = HERE / "shots" / f"{name}.scene.json"
    out.write_text(json.dumps(scene, indent=1) + "\n")
    print("wrote", out.relative_to(ROOT))


if __name__ == "__main__":
    main()
