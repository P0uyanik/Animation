"""Iteration 4 benchmark: the water table, described with actions instead of bone keys, filmed by the director.
C walks in; B lifts the floating paper boat (fingers close on it), looks at it, puts it back (ripples); A is
surprised, then touches the water with a fingertip (ripples); everyone breathes and blinks on their own.
Run from the repository root: python3 tools/make_watertable_v4.py"""
import json, math, random

s = json.load(open("content/scenes/milestone03_watertable.scene.json"))
s["name"] = "Water table v4 - actions and automatic camera"
s["frameRate"] = [30, 1]
s["frameStart"], s["frameEnd"] = 1, 180
s["render"].update(width=1280, height=720, spp=96, adaptiveThreshold=0.1, exposureEV=0.35)
T = [0.0, 0.0, 0.42]
WATER_Y = 0.475

# The boat floats on the water from the start (no folding in this shot).
for o in s["objects"]:
    if o["name"] == "boat":
        o["position"] = [0.07, WATER_Y + 0.004, 0.30]
        o["yawDeg"] = 70
        o["scale"] = 0.45  # hand-sized, as in the reference video
        o.pop("attach", None)
        o["float"] = {"on": "water", "frame": 1}
    if o["name"] == "water":
        o["water"]["ripples"] = []

# Modest set dressing: bunting across the back wall, a low toy shelf with plush toys and blocks, a round rug.
s["materials"] += [
    {"name": "flag_a", "type": "plush", "baseColor": [0.85, 0.45, 0.4], "sheen": 0.6},
    {"name": "flag_b", "type": "plush", "baseColor": [0.95, 0.8, 0.45], "sheen": 0.6},
    {"name": "flag_c", "type": "plush", "baseColor": [0.45, 0.65, 0.8], "sheen": 0.6},
    {"name": "string", "type": "standard", "baseColor": [0.9, 0.88, 0.8], "roughness": 0.8},
    {"name": "toy_bear", "type": "plush", "baseColor": [0.62, 0.45, 0.3], "sheen": 0.8},
    {"name": "toy_bunny", "type": "plush", "baseColor": [0.9, 0.86, 0.8], "sheen": 0.8},
    {"name": "toy_fiber", "type": "fiber", "baseColor": [0.7, 0.55, 0.4], "betaM": 0.4, "betaN": 0.8},
    {"name": "block_a", "type": "standard", "baseColor": [0.8, 0.3, 0.25], "roughness": 0.45},
    {"name": "block_b", "type": "standard", "baseColor": [0.3, 0.55, 0.8], "roughness": 0.45},
    {"name": "block_c", "type": "standard", "baseColor": [0.9, 0.75, 0.3], "roughness": 0.45},
    {"name": "rug", "type": "plush", "baseColor": [0.55, 0.62, 0.55], "sheen": 0.7},
    {"name": "rug_fiber", "type": "fiber", "baseColor": [0.6, 0.68, 0.6], "betaM": 0.4, "betaN": 0.8},
]
wall_z = -1.5
for k in range(13):
    x = -1.3 + 0.2 * k
    sag = 0.06 * math.sin(math.pi * (k / 12.0))
    s["objects"].append({"name": f"flag{k}", "kind": "sdf", "material": ["flag_a", "flag_b", "flag_c"][k % 3],
                         "position": [x, 1.62 - sag, wall_z + 0.04], "yawDeg": 0,
                         "part": {"voxelSize": 0.002, "prims": [
                             {"type": "roundCone", "a": [0, 0.0, 0], "b": [0, -0.09, 0], "r1": 0.045, "r2": 0.006}]}})
s["objects"].append({"name": "buntingString", "kind": "sdf", "material": "string", "position": [0, 0, wall_z + 0.04],
                     "part": {"voxelSize": 0.002, "prims": [
                         {"type": "capsule", "a": [-1.4, 1.63, 0], "b": [0.0, 1.565, 0], "r": 0.004},
                         {"type": "capsule", "a": [0.0, 1.565, 0], "b": [1.2, 1.63, 0], "r": 0.004, "blend": 0.004}]}})
SH = [-1.15, 0, -1.2]  # toy shelf
s["objects"].append({"name": "toyShelf", "kind": "sdf", "material": "wood_light", "position": SH, "part": {"voxelSize": 0.004, "prims": [
    {"type": "roundBox", "center": [0, 0.2, 0], "halfSize": [0.35, 0.2, 0.15], "rounding": 0.015},
    {"type": "roundBox", "center": [0, 0.21, 0.04], "halfSize": [0.32, 0.075, 0.14], "rounding": 0.008, "subtract": True, "blend": 0.004}]}})
s["objects"].append({"name": "toyBear", "kind": "sdf", "material": "toy_bear", "position": [SH[0] - 0.15, 0.4, SH[2]], "yawDeg": 20,
                     "part": {"voxelSize": 0.002, "prims": [
                         {"type": "ellipsoid", "center": [0, 0.06, 0], "radii": [0.06, 0.065, 0.055]},
                         {"type": "ellipsoid", "center": [0, 0.15, 0.005], "radii": [0.048, 0.045, 0.045], "blend": 0.015},
                         {"type": "ellipsoid", "center": [0.035, 0.19, 0], "radii": [0.018, 0.018, 0.012], "blend": 0.006, "mirror": True}]},
                     "fuzz": {"material": "toy_fiber", "density": 60, "length": 0.004, "radius": 3e-5, "tilt": 0.5, "curl": 0.4, "segments": 3, "seed": 141}})
s["objects"].append({"name": "toyBunny", "kind": "sdf", "material": "toy_bunny", "position": [SH[0] + 0.15, 0.4, SH[2]], "yawDeg": -15,
                     "part": {"voxelSize": 0.002, "prims": [
                         {"type": "ellipsoid", "center": [0, 0.055, 0], "radii": [0.05, 0.058, 0.048]},
                         {"type": "ellipsoid", "center": [0, 0.13, 0.005], "radii": [0.04, 0.04, 0.038], "blend": 0.012},
                         {"type": "capsule", "a": [0.015, 0.16, 0], "b": [0.02, 0.23, -0.005], "r": 0.012, "blend": 0.005, "mirror": True}]}})
for k, (dx, dz, m, h) in enumerate([(-0.2, 0.0, "block_a", 0.0), (-0.13, 0.03, "block_b", 0.0), (-0.165, 0.015, "block_c", 0.06)]):
    s["objects"].append({"name": f"block{k}", "kind": "sdf", "material": m, "position": [SH[0] + dx, 0.07 + h, SH[2] + 0.17 + dz],
                         "yawDeg": 12 * k, "part": {"voxelSize": 0.0015, "prims": [
                             {"type": "roundBox", "center": [0, 0.03, 0], "halfSize": [0.03, 0.03, 0.03], "rounding": 0.006}]}})
s["objects"].append({"name": "rug", "kind": "sdf", "material": "rug", "position": [0, 0, 0.42], "part": {"voxelSize": 0.006, "prims": [
    {"type": "disc", "center": [0, 0.004, 0], "halfSize": [0.95, 0.95, 0.004], "rounding": 0.003, "rotationDeg": [90, 0, 0]}]},
                     "fuzz": {"material": "rug_fiber", "density": 18, "length": 0.004, "radius": 3e-5, "tilt": 0.3, "curl": 0.5, "segments": 3, "seed": 142}})

# Characters at the rim of the table: B behind it, A at its right end; C walks in from the left.
s["characters"] = [
    {"name": "C", "asset": "../characters/boy_dark_hair.character.json", "position": [-0.82, 0.012, 0.86], "yawDeg": 120, "life": True},
    {"name": "B", "asset": "../characters/girl_brown_glasses.character.json", "position": [0.0, 0.012, 0.1], "yawDeg": 0, "life": True},
    {"name": "A", "asset": "../characters/girl_white_hair.character.json", "position": [0.38, 0.012, 0.15], "yawDeg": -25, "life": True},
]
s["camera"].update(position=[0.5, 1.28, 2.25], target=[-0.04, 0.58, 0.36], focalMm=32, fStop=4.0, focusDistance=-1)
s["animation"] = {}  # nothing keyed by hand: everything below comes from actions, life and the director
s["actions"] = [
    {"type": "look", "character": "A", "start": 1, "object": "boat", "end": 180},
    {"type": "look", "character": "B", "start": 1, "object": "boat", "end": 40},
    {"type": "walk", "character": "C", "start": 1, "end": 54, "to": [-0.45, 0.4], "face": 75},
    {"type": "look", "character": "C", "start": 30, "object": "boat", "end": 180},
    {"type": "reach", "character": "B", "hand": "L", "object": "boat", "start": 40, "contact": 56, "liftEnd": 72,
     "place": 116, "placeAt": [0.02, WATER_Y + 0.004, 0.34], "release": 120, "end": 136, "graspRadius": 0.014, "lift": 0.11},
    {"type": "expression", "character": "B", "name": "surprise", "start": 74, "end": 104, "weight": 0.8},
    {"type": "expression", "character": "A", "name": "surprise", "start": 78, "end": 108, "weight": 1.0},
    {"type": "touch", "character": "A", "hand": "R", "start": 128, "contact": 144, "end": 166, "target": [0.22, WATER_Y + 0.001, 0.34]},
    {"type": "expression", "character": "C", "name": "smile", "start": 150, "end": 200, "weight": 1.0},
]
s["director"] = {"minShot": 36}
json.dump(s, open("content/scenes/watertable_v4.scene.json", "w"), indent=1)
print("wrote content/scenes/watertable_v4.scene.json")
