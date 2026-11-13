"""Builds content/scenes/milestone02_classroom.scene.json from the frozen milestone-01 scene.
Run from the repository root: python3 tools/make_milestone02.py"""
import json
s = json.load(open("content/scenes/milestone01_classroom.scene.json"))
s["name"] = "Milestone 02 - picking up the paper boat"
s["frameEnd"] = 72
s["characters"][0]["asset"] = "../characters/girl_white_hair.character.json"
s["objects"] = [o for o in s["objects"] if o["name"] != "boat"]
legs = [{"type": "capsule", "a": [x, 0.0, z], "b": [x, 0.44, z], "r": 0.016, "blend": 0.0}
        for x in (-0.18, 0.18) for z in (-0.115, 0.115)]
s["objects"].append({"name": "table", "kind": "sdf", "material": "wood_light", "position": [0.1, 0.0, 0.33],
                     "part": {"voxelSize": 0.003, "prims": [
                         {"type": "roundBox", "center": [0, 0.436, 0], "halfSize": [0.21, 0.014, 0.14], "rounding": 0.008}] + legs}})
s["objects"].append({"name": "boat", "kind": "paperBoat", "material": "paper", "position": [0.1, 0.446, 0.23], "yawDeg": 25,
                     "attach": {"to": "girl/hand.L", "frame": 34}})
cam_start, cam_end = [0.32, 0.93, 1.62], [0.27, 0.88, 1.42]
s["camera"].update(position=cam_start, target=[0.06, 0.6, 0.16], focusDistance=-1, fStop=2.0)
rest_wrist = [0.155, 0.442, 0.015]
s["animation"] = {
    "camera.position": [[1, cam_start], [72, cam_end]],
    "girl/lookAt": [[1, cam_start], [8, cam_start], [14, [0.1, 0.47, 0.23]], [34, [0.1, 0.47, 0.23]], [54, [0.07, 0.6, 0.21]], [72, [0.07, 0.6, 0.21]]],
    "girl/head.rot": [[1, [0, 0, 0]], [10, [0, 0, 0]], [26, [16, 12, 4]], [36, [17, 12, 4]], [54, [6, 8, 3]], [72, [5, 9, 6]]],
    "girl/neck.rot": [[1, [0, 0, 0]], [12, [0, 0, 0]], [26, [6, 4, 0]], [54, [2, 3, 0]], [72, [2, 3, 0]]],
    "girl/spine.rot": [[1, [0, 0, 0]], [14, [0, 0, 0]], [30, [10, 4, 0]], [38, [10, 4, 0]], [56, [2, 2, 0]], [72, [2, 2, 0]]],
    "girl/chest.rot": [[1, [0, 0, 0]], [14, [0, 0, 0]], [30, [14, 5, 0]], [38, [14, 5, 0]], [56, [4, 3, 0]], [72, [4, 3, 0]]],
    "girl/ik.hand.L": [[1, rest_wrist], [16, rest_wrist], [31, [0.095, 0.505, 0.205]], [36, [0.095, 0.505, 0.205]], [54, [0.075, 0.6, 0.19]], [72, [0.075, 0.605, 0.19]]],
    "girl/brow.L.rot": [[1, [0, 0, 0]], [11, [0, 0, 0]], [17, [-5, 0, 0]], [30, [-5, 0, 0]], [40, [0, 0, 0]], [58, [-2, 0, 0]]],
    "girl/brow.R.rot": [[1, [0, 0, 0]], [11, [0, 0, 0]], [17, [-5, 0, 0]], [30, [-5, 0, 0]], [40, [0, 0, 0]], [58, [-2, 0, 0]]],
    "girl/expr.mouthOpen": [[1, 0], [12, 0], [18, 0.75], [26, 0.6], [34, 0]],
    "girl/expr.smile": [[1, 0], [48, 0], [60, 1.0], [72, 1.0]],
}
for lid in ("girl/lid.L.rot", "girl/lid.R.rot"):
    s["animation"][lid] = [[1, [0, 0, 0]], [40, [0, 0, 0]], [42, [86, 0, 0]], [45, [0, 0, 0]], [63, [0, 0, 0]], [65, [86, 0, 0]], [68, [0, 0, 0]]]
json.dump(s, open("content/scenes/milestone02_classroom.scene.json", "w"), indent=1)
print("wrote content/scenes/milestone02_classroom.scene.json")
