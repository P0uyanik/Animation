"""Milestone 03: three characters at a water table; B folds a paper boat and sets it on the water.
Run from the repository root: python3 tools/make_milestone03.py"""
import json, random
s = json.load(open("content/scenes/milestone01_classroom.scene.json"))
s["name"] = "Milestone 03 - the paper boat on the water table"
s["frameStart"], s["frameEnd"] = 1, 72
s["render"].update(width=960, height=540, spp=64, adaptiveThreshold=0.1, exposureEV=0.35)
s["objects"] = [o for o in s["objects"] if o["name"] not in ("boat", "rug")]
s["materials"] += [
    {"name": "water", "type": "glass", "baseColor": [0.82, 0.93, 0.94], "ior": 1.33, "thin": False, "castsShadow": False},
    {"name": "basin_paint", "type": "standard", "baseColor": [0.35, 0.62, 0.68], "roughness": 0.5},
    {"name": "pebble_a", "type": "standard", "baseColor": [0.75, 0.45, 0.4], "roughness": 0.3, "coat": 0.6},
    {"name": "pebble_b", "type": "standard", "baseColor": [0.4, 0.6, 0.4], "roughness": 0.3, "coat": 0.6},
    {"name": "pebble_c", "type": "standard", "baseColor": [0.55, 0.5, 0.75], "roughness": 0.3, "coat": 0.6},
    {"name": "cushion", "type": "plush", "baseColor": [0.75, 0.42, 0.45], "sheen": 0.8},
    {"name": "cushion2", "type": "plush", "baseColor": [0.45, 0.55, 0.7], "sheen": 0.8},
    {"name": "cushion_fiber", "type": "fiber", "baseColor": [0.8, 0.5, 0.5], "betaM": 0.4, "betaN": 0.8},
    {"name": "book_red", "type": "standard", "baseColor": [0.6, 0.12, 0.1], "roughness": 0.5},
    {"name": "book_green", "type": "standard", "baseColor": [0.2, 0.42, 0.25], "roughness": 0.5},
    {"name": "book_yellow", "type": "standard", "baseColor": [0.8, 0.62, 0.2], "roughness": 0.5},
    {"name": "drawing", "type": "standard", "baseColor": [0.9, 0.88, 0.82], "roughness": 0.8,
     "texture": {"type": "noise", "color2": [0.9, 0.55, 0.3], "scale": 18, "amount": 0.55}},
    {"name": "drawing2", "type": "standard", "baseColor": [0.9, 0.88, 0.82], "roughness": 0.8,
     "texture": {"type": "noise", "color2": [0.35, 0.55, 0.85], "scale": 14, "amount": 0.55}},
]
T = [0.0, 0.0, 0.42]  # water table centre on the floor
legs = [{"type": "capsule", "a": [x, 0.0, z], "b": [x, 0.42, z], "r": 0.022} for x in (-0.28, 0.28) for z in (-0.18, 0.18)]
s["objects"] += [
    {"name": "waterTable", "kind": "sdf", "material": "wood_light", "position": T, "part": {"voxelSize": 0.003, "prims": [
        {"type": "roundBox", "center": [0, 0.45, 0], "halfSize": [0.33, 0.055, 0.23], "rounding": 0.02},
        {"type": "roundBox", "center": [0, 0.48, 0], "halfSize": [0.295, 0.06, 0.195], "rounding": 0.01, "blend": 0.006, "subtract": True}] + legs}},
    {"name": "basinBottom", "kind": "sdf", "material": "basin_paint", "position": T, "part": {"voxelSize": 0.004, "prims": [
        {"type": "roundBox", "center": [0, 0.423, 0], "halfSize": [0.294, 0.004, 0.194], "rounding": 0.002}]}},
    {"name": "water", "kind": "water", "material": "water", "position": [T[0], 0.475, T[2]],
     "water": {"halfSize": [0.292, 0, 0.192], "resolution": 110, "ripples": [[0.04, -0.02, 46, 0.0035], [0.06, 0.0, 53, 0.002]]}},
]
rng = random.Random(5)
for k in range(14):
    s["objects"].append({"name": f"pebble{k}", "kind": "sdf", "material": rng.choice(["pebble_a", "pebble_b", "pebble_c"]),
                         "position": [T[0] + rng.uniform(-0.26, 0.26), 0.428, T[2] + rng.uniform(-0.16, 0.16)], "yawDeg": rng.uniform(0, 180),
                         "part": {"voxelSize": 0.0015, "prims": [{"type": "ellipsoid", "center": [0, 0.004, 0], "radii": [0.012, 0.006, 0.009]}]}})
# Set dressing: books on the shelf, cushions, drawings on the wall.
for k, (m, h) in enumerate([("book_red", 0.17), ("book_green", 0.15), ("book_yellow", 0.18), ("book_red", 0.14), ("book_green", 0.16)]):
    s["objects"].append({"name": f"book{k}", "kind": "sdf", "material": m, "position": [0.55 + 0.035 * k, 0.5, -1.47], "yawDeg": 0,
                         "part": {"voxelSize": 0.002, "prims": [{"type": "roundBox", "center": [0, h / 2, 0], "halfSize": [0.014, h / 2, 0.06], "rounding": 0.003}]}})
for k, (x, z, m) in enumerate([(-1.2, -0.8, "cushion"), (-0.95, -1.1, "cushion2")]):
    s["objects"].append({"name": f"cushion{k}", "kind": "sdf", "material": m, "position": [x, 0, z], "yawDeg": 20 * k,
                         "part": {"voxelSize": 0.004, "prims": [{"type": "roundBox", "center": [0, 0.06, 0], "halfSize": [0.2, 0.06, 0.2], "rounding": 0.05}]},
                         "fuzz": {"material": "cushion_fiber", "density": 25, "length": 0.004, "radius": 3e-5, "tilt": 0.4, "curl": 0.4, "segments": 3, "seed": 90 + k}})
for k, (x, y, m) in enumerate([(-1.45, 1.35, "drawing"), (-1.1, 1.45, "drawing2"), (0.6, 1.4, "drawing"), (1.0, 1.3, "drawing2")]):
    s["objects"].append({"name": f"drawing{k}", "kind": "box", "min": [x - 0.13, y - 0.1, -1.6], "max": [x + 0.13, y + 0.1, -1.595], "material": m})
s["objects"].append({"name": "boat", "kind": "paperBoat", "material": "paper", "position": [0.075, 0.545, 0.2], "yawDeg": 90,
                     "attach": {"to": "B/hand.L", "frame": 1, "release": 46}, "float": {"on": "water", "frame": 46}})
s["characters"] = [
    {"name": "C", "asset": "../characters/boy_dark_hair.character.json", "position": [-0.38, 0.012, 0.02], "yawDeg": 22},
    {"name": "B", "asset": "../characters/girl_brown_glasses.character.json", "position": [0.0, 0.012, -0.02], "yawDeg": 0},
    {"name": "A", "asset": "../characters/girl_white_hair.character.json", "position": [0.38, 0.012, 0.02], "yawDeg": -22},
]
boat_on_water = [T[0] + 0.045, 0.49, T[2] - 0.02]
hand_rest = [0.155, 0.442, 0.0]
s["camera"].update(position=[0.0, 1.22, 2.0], target=[0.0, 0.63, 0.2], focalMm=35, fStop=2.4, focusDistance=-1)
s["animation"] = {
    "camera.position": [[1, [0.0, 1.22, 2.0]], [72, [0.06, 1.15, 1.8]]],
    "boat.fold": [[1, 0.0], [6, 0.0], [30, 1.0]],
    # B: folds the paper at chest height, reaches over the water and lets go, then smiles.
    "B/ik.hand.L": [[1, [0.06, 0.58, 0.15]], [30, [0.06, 0.58, 0.15]], [44, [0.05, 0.53, 0.37]], [48, [0.05, 0.53, 0.37]], [62, hand_rest], [72, hand_rest]],
    "B/lookAt": [[1, [0.07, 0.56, 0.2]], [30, [0.07, 0.56, 0.2]], [44, boat_on_water], [72, boat_on_water]],
    "B/head.rot": [[1, [16, 4, 0]], [30, [16, 4, 0]], [44, [20, 2, 0]], [60, [14, 0, 3]], [72, [12, 0, 3]]],
    "B/chest.rot": [[1, [4, 0, 0]], [30, [4, 0, 0]], [44, [16, 4, 0]], [56, [8, 2, 0]], [72, [6, 2, 0]]],
    "B/expr.mouthOpen": [[1, 0.2], [44, 0.2], [50, 0.9], [60, 0.3]],
    "B/expr.smile": [[1, 0.6], [44, 0.6], [56, 1.0], [72, 1.0]],
    # A: watches the folding, follows the boat, delighted when it floats.
    "A/lookAt": [[1, [0.07, 0.56, 0.2]], [30, [0.07, 0.56, 0.2]], [46, boat_on_water], [72, boat_on_water]],
    "A/head.rot": [[1, [10, 0, -4]], [30, [10, 0, -4]], [46, [18, 0, -2]], [72, [16, 0, 4]]],
    "A/chest.rot": [[1, [4, 0, 0]], [40, [4, 0, 0]], [52, [12, 0, 0]], [72, [10, 0, 0]]],
    "A/expr.mouthOpen": [[1, 0], [46, 0], [52, 0.8], [62, 0.2]],
    "A/expr.smile": [[1, 0.2], [50, 0.2], [60, 1.0], [72, 1.0]],
    "A/lid.L.rot": [[1, [0, 0, 0]], [24, [0, 0, 0]], [26, [86, 0, 0]], [29, [0, 0, 0]]],
    "A/lid.R.rot": [[1, [0, 0, 0]], [24, [0, 0, 0]], [26, [86, 0, 0]], [29, [0, 0, 0]]],
    # C: sleepy at first, then the boat on the water catches his interest.
    "C/lookAt": [[1, [0.0, 0.7, 1.2]], [20, [0.0, 0.7, 1.2]], [30, [0.07, 0.56, 0.2]], [46, boat_on_water], [72, boat_on_water]],
    "C/head.rot": [[1, [4, 0, 0]], [22, [4, 0, 0]], [34, [14, -6, 0]], [50, [20, -4, 0]], [72, [18, -4, 0]]],
    "C/chest.rot": [[1, [0, 0, 0]], [40, [0, 0, 0]], [52, [10, -4, 0]], [72, [8, -4, 0]]],
    "C/lid.L.rot": [[1, [34, 0, 0]], [40, [34, 0, 0]], [50, [14, 0, 0]], [72, [16, 0, 0]]],
    "C/lid.R.rot": [[1, [34, 0, 0]], [40, [34, 0, 0]], [50, [14, 0, 0]], [72, [16, 0, 0]]],
    "C/brow.L.rot": [[1, [3, 0, 0]], [44, [3, 0, 0]], [52, [-3, 0, 0]], [72, [-2, 0, 0]]],
    "C/brow.R.rot": [[1, [3, 0, 0]], [44, [3, 0, 0]], [52, [-3, 0, 0]], [72, [-2, 0, 0]]],
    "C/expr.frown": [[1, 0.35], [44, 0.35], [56, 0.0]],
    "C/expr.smile": [[1, 0.0], [52, 0.0], [64, 0.45]],
}
json.dump(s, open("content/scenes/milestone03_watertable.scene.json", "w"), indent=1)
print("wrote content/scenes/milestone03_watertable.scene.json")
