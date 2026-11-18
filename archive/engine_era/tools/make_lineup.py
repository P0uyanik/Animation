"""Lineup / turnaround test scene for the three characters (front, three-quarter, side, back).
Run from the repository root: python3 tools/make_lineup.py"""
import json
chars = [("girlA", "girl_white_hair", -0.42), ("girlB", "girl_brown_glasses", 0.0), ("boyC", "boy_dark_hair", 0.42)]
s = {"format": "plush.scene", "version": 1, "name": "Test - character lineup", "frameRate": [30, 1], "frameStart": 1, "frameEnd": 4,
     "render": {"width": 960, "height": 720, "spp": 64, "maxDepth": 8, "exposureEV": 0.4, "denoise": True, "denoiseBlend": 0.85, "clamp": 12},
     "camera": {"position": [0, 0.62, 3.0], "target": [0, 0.52, 0], "focalMm": 50, "fStop": 5.6, "focusDistance": -1},
     "materials": [{"name": "backdrop", "type": "standard", "baseColor": [0.55, 0.52, 0.49], "roughness": 0.9, "specular": 0.3}],
     "lights": [
         {"type": "rect", "corner": [-2.2, 1.0, 2.0], "edgeU": [1.2, 0, 0.6], "edgeV": [0, 1.4, 0], "color": [1.0, 0.95, 0.88], "intensity": 3.2},
         {"type": "rect", "corner": [1.2, 0.6, 2.2], "edgeU": [0.9, 0, -0.5], "edgeV": [0, 1.2, 0], "color": [0.9, 0.93, 1.0], "intensity": 1.2},
         {"type": "sun", "direction": [0.4, -0.6, -0.7], "angleDeg": 4, "color": [1.0, 0.9, 0.8], "intensity": 1.5},
         {"type": "sky", "color": [0.6, 0.6, 0.62], "intensity": 0.35}],
     "objects": [{"name": "floor", "kind": "box", "min": [-4, -0.05, -3], "max": [4, 0, 4], "material": "backdrop"},
                 {"name": "wall", "kind": "box", "min": [-4, 0, -1.6], "max": [4, 3, -1.5], "material": "backdrop"}],
     "characters": [{"name": n, "asset": f"../characters/{a}.character.json", "position": [x, 0.012, 0], "yawDeg": 0} for n, a, x in chars],
     "animation": {}}
for n, _, _ in chars:
    s["animation"][f"{n}.yaw"] = [[1, 0, "step"], [2, -35, "step"], [3, -90, "step"], [4, 180, "step"]]  # frame 4: back
    s["animation"][f"{n}/lookAt"] = [[1, [0, 0.62, 3.0], "step"]]
json.dump(s, open("content/scenes/test_lineup.scene.json", "w"), indent=1)
print("wrote content/scenes/test_lineup.scene.json")
