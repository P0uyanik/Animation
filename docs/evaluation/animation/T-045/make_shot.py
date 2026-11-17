#!/usr/bin/env python3
"""Writes the T-045 evidence shots: both characters idle -> reach (fingertip touch) -> wave, 5.5 s at 24 fps.

shot_before/shot.scene.json: body mechanics off (as every shot before T-045).
shot_after/shot.scene.json:  body mechanics on, tuned by each character's personality draft profile.
Everything else is identical, so the two renders differ only by the layer.
"""
import copy
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
T046 = HERE.parent / "T-046" / "shot" / "shot.scene.json"


def local_to_world(pos, yaw_deg, p):
    """Engine character transform: rotation about +y by yaw, then translation."""
    c, s = math.cos(math.radians(yaw_deg)), math.sin(math.radians(yaw_deg))
    x, y, z = p
    return [round(pos[0] + x * c + z * s, 4), round(pos[1] + y, 4), round(pos[2] - x * s + z * c, 4)]


def main():
    base = json.loads(T046.read_text())
    cast = {
        # name: position, yaw, touch target (character space, at the right hand), timeline offset, personality, wave
        "boy": ([-0.28, 0.0, 0.0], 12, [-0.17, 0.46, 0.18], 0, "boy_yellow_hoodie", {"weight": 0.75, "mirror": False}),
        "girl": ([0.28, 0.0, 0.0], -12, [-0.16, 0.43, 0.165], 4, "girl_auburn_bun_glasses", {"weight": 1.0, "mirror": False}),
    }
    scene = {
        "format": "plush.scene", "version": 1,
        "name": "T-045 body mechanics: idle -> reach (touch) -> wave",
        "frameRate": [24, 1], "frameStart": 1, "frameEnd": 132,
        "render": base["render"],
        "camera": {"position": [0.0, 0.56, 2.3], "target": [0.0, 0.46, 0.0], "focalMm": 35, "fStop": 0, "focusDistance": -1},
        "materials": base["materials"] + [{"name": "plinth_mat", "type": "standard", "baseColor": [0.55, 0.42, 0.3],
                                             "roughness": 0.8, "specular": 0.3}],
        "lights": base["lights"],
        "objects": [o for o in base.get("objects", [])],
        "characters": [], "actions": [],
        "production": {
            "cast": {"boy": {"version_dir": "assets/characters/boy_yellow_hoodie/versions/1.0.0"},
                     "girl": {"spec": "assets/characters/girl_auburn_bun_glasses/spec/girl_auburn_bun_glasses.spec.json"}},
            "profile": "pipeline/charsys/rig_profiles/humanoid_rigify.json",
            "render": {"resolution": [640, 360], "samples": 16, "light_scale": 1.0},
        },
    }
    for name, (pos, yaw, target_local, off, personality, wave) in cast.items():
        target = local_to_world(pos, yaw, target_local)
        h = 0.035
        scene["objects"].append({"name": f"plinth_{name}", "kind": "box", "material": "plinth_mat",
                                 "min": [target[0] - h, 0.0, target[2] - h], "max": [target[0] + h, target[1], target[2] + h]})
        scene["characters"].append({"name": name, "asset": "(set by run_shot)", "position": pos, "yawDeg": yaw,
                                    "life": True, "x_personality": personality})
        scene["actions"] += [
            {"type": "look", "character": name, "start": 1, "end": 22 + off, "camera": True},
            {"type": "touch", "character": name, "hand": "R", "object": f"plinth_{name}", "target": target,
             "start": 24 + off, "contact": 40 + off, "end": 62 + off},
            {"type": "look", "character": name, "start": 64 + off, "end": 132, "camera": True},
            {"type": "clip", "character": name, "clip": "wave", "start": 66 + off, "speed": 1.5, "blendIn": 4,
             "blendOut": 8, **wave},
        ]
    for variant, on in (("shot_before", False), ("shot_after", True)):
        s = copy.deepcopy(scene)
        for ch in s["characters"]:
            p = ch.pop("x_personality")
            if on:
                ch["bodyMechanics"] = {"personality": p}
        s["name"] += " (" + ("body mechanics on" if on else "body mechanics off") + ")"
        out = HERE / variant / "shot.scene.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(s, indent=1) + "\n")
        print("wrote", out.relative_to(HERE.parents[3]))


if __name__ == "__main__":
    main()
