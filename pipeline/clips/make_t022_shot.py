"""Writes the T-022 hand-prop test shot episodes/e905_props_test/shots/s010/shot.scene.json (python3).

    python3 pipeline/clips/make_t022_shot.py [--boy-package <pkg dir> --girl-package <pkg dir>]

3 s at 24 fps: the boy picks a felt cup (content/assets/felt_cup.asset.json) up from a small table with his right
hand, lifts it, hands it to the girl, who takes it with her right hand at the cup's other grip socket and draws it
towards herself. Everything is shared interaction actions (scene/interaction.h): grasp, hold, handover, hold.

Placement is derived from data, not tuned per character: the cup's grip socket sits at a fixed fraction of the boy's
arm length in front of and below his right shoulder (his package skeleton), the table top is under the cup, and the
cup is turned so its "grip" socket faces the boy's right side and "grip_b" the girl's right side. The derived numbers
are written into the shot file (a shot is data); this script documents how they were derived. Without packages it
uses the T-022 defaults measured on boy 1.1.0 / girl (current spec) packages."""
import argparse
import json
import math
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "episodes", "e905_props_test", "shots", "s010", "shot.scene.json")
SPEC = "assets/characters/boy_yellow_hoodie/spec/boy_yellow_hoodie.spec.json"
OVERRIDE = "assets/characters/boy_yellow_hoodie/spec/boy_yellow_hoodie.1.1.0.override.json"
GIRL_SPEC = "assets/characters/girl_auburn_bun_glasses/spec/girl_auburn_bun_glasses.spec.json"

BOY_POS, BOY_YAW = (-0.19, 0.0, 0.0), 68.0
GIRL_POS, GIRL_YAW = (0.19, 0.0, 0.0), -68.0
# grip socket from the right shoulder: forward, down, outward, in arm lengths. T-030: 0.85 forward / 0.45 down (0.96 arm
# from the shoulder); T-022 used 0.5 / 0.66, which put the grip at the belly surface, so the forearm had to enter the
# body at the grasp (the engine's arm-body clearance reports such a contact).
REACH = (0.85, -0.45, 0.06)
CUP = json.load(open(os.path.join(ROOT, "content", "assets", "felt_cup.asset.json")))
CUP_GRIP = tuple(CUP["sockets"]["grip"]["translation"])  # felt_cup "grip" socket (local)


def yaw_rot(deg, v):
    """Engine yaw (degrees about +Y): local +Z (forward) -> (sin, 0, cos)."""
    a = math.radians(deg)
    x, y, z = v
    return (x * math.cos(a) + z * math.sin(a), y, -x * math.sin(a) + z * math.cos(a))


def arm(pkg, side="R"):
    sk = {b["name"]: b for b in json.load(open(os.path.join(pkg, "character.json")))["skeleton"]}
    d = lambda a, b: math.dist(sk[a]["head"], sk[b]["head"])  # noqa: E731
    return sk[f"upperArm.{side}"]["head"], d(f"upperArm.{side}", f"forearm.{side}") + d(f"forearm.{side}", f"hand.{side}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--boy-package")
    ap.add_argument("--girl-package")
    a = ap.parse_args()
    if a.boy_package:
        shoulder, arm_len = arm(a.boy_package)
    else:
        shoulder, arm_len = [-0.118, 0.618, 0.0], 0.233
    if a.girl_package:
        g_shoulder, g_arm = arm(a.girl_package)
    else:
        g_shoulder, g_arm = [-0.098, 0.585, 0.0], 0.181
    # boy-local: forward +Z, his right is -X; the right shoulder rest head is at shoulder (package skeleton)
    local = (shoulder[0] - REACH[2] * arm_len, shoulder[1] + REACH[1] * arm_len, shoulder[2] + REACH[0] * arm_len)
    w = yaw_rot(BOY_YAW, local)
    grip = [round(BOY_POS[i] + w[i], 4) for i in range(3)]
    cup_yaw = BOY_YAW + 180.0  # local +x (grip) -> the boy's right side; grip_b (-x) -> the girl's right side
    g = yaw_rot(cup_yaw, CUP_GRIP)
    cup = [round(grip[i] - g[i], 4) for i in range(3)]
    top = cup[1]
    # a small round-cornered side table: a 3 cm top under the cup on a single leg
    table = [{"name": "table_top", "kind": "box", "min": [round(cup[0] - 0.1, 4), round(top - 0.03, 4), round(cup[2] - 0.09, 4)],
              "max": [round(cup[0] + 0.08, 4), round(top, 4), round(cup[2] + 0.07, 4)], "material": "table_mat"},
             {"name": "table_leg", "kind": "box", "min": [round(cup[0] - 0.035, 4), 0.0, round(cup[2] - 0.045, 4)],
              "max": [round(cup[0] + 0.015, 4), round(top - 0.03, 4), round(cup[2] + 0.005, 4)], "material": "table_mat"}]
    # hand-over point: between the two right shoulders, 0.4 x the shorter arm below them (the cup's origin)
    bs = [BOY_POS[i] + yaw_rot(BOY_YAW, shoulder)[i] for i in range(3)]
    gs = [GIRL_POS[i] + yaw_rot(GIRL_YAW, g_shoulder)[i] for i in range(3)]
    meet = [round(0.5 * (bs[i] + gs[i]) - (0.4 * min(arm_len, g_arm) if i == 1 else 0.0), 4) for i in range(3)]
    shot = {
        "format": "plush.scene", "version": 1,
        "name": "e905_props_test s010: T-022 hand interaction - boy picks up a cup and hands it to the girl",
        "frameRate": [24, 1], "frameStart": 1, "frameEnd": 72,
        "render": {"width": 640, "height": 360, "spp": 32, "maxDepth": 8, "exposureEV": 0.3, "denoise": True,
                   "denoiseBlend": 0.85, "clamp": 12},
        "camera": {"position": [0.1, 0.98, 1.6], "target": [0.0, 0.6, 0.0], "focalMm": 32, "fStop": 0, "focusDistance": -1},
        "materials": [{"name": "floor_mat", "type": "standard", "baseColor": [0.46, 0.44, 0.42], "roughness": 0.85, "specular": 0.3},
                      {"name": "wall_mat", "type": "standard", "baseColor": [0.62, 0.6, 0.55], "roughness": 0.9, "specular": 0.3},
                      {"name": "table_mat", "type": "standard", "baseColor": [0.42, 0.3, 0.2], "roughness": 0.7, "specular": 0.3}],
        "lights": [{"type": "rect", "corner": [-2.0, 1.0, 2.0], "edgeU": [1.2, 0, 0.6], "edgeV": [0, 1.4, 0],
                    "color": [1.0, 0.95, 0.88], "intensity": 3.0},
                   {"type": "sun", "direction": [0.3, -0.6, -0.7], "angleDeg": 4, "color": [1.0, 0.92, 0.82], "intensity": 1.4},
                   {"type": "sky", "color": [0.6, 0.62, 0.66], "intensity": 0.4}],
        "objects": [{"name": "floor", "kind": "box", "min": [-4, -0.05, -3], "max": [4, 0, 4], "material": "floor_mat"},
                    {"name": "wall", "kind": "box", "min": [-4, 0, -1.4], "max": [4, 3, -1.3], "material": "wall_mat"},
                    *table],
        "props": [{"name": "cup", "id": "prop.felt_cup",
                   "transform": {"translation": cup, "rotationDeg": [0, cup_yaw, 0], "scale": [1, 1, 1]}}],
        "characters": [{"name": "boy", "asset": "(set by run_shot)", "position": list(BOY_POS), "yawDeg": BOY_YAW,
                        "life": {"blinkInterval": 2.2}},
                       {"name": "girl", "asset": "(set by run_shot)", "position": list(GIRL_POS), "yawDeg": GIRL_YAW,
                        "life": {"blinkInterval": 2.6}}],
        "actions": [
            {"type": "clip", "character": "boy", "clip": "idle_relaxed", "base": True},
            {"type": "clip", "character": "girl", "clip": "idle_relaxed", "base": True},
            {"type": "grasp", "character": "boy", "hand": "R", "prop": "cup", "socket": "grip", "start": 3, "contact": 17},
            {"type": "hold", "character": "boy", "hand": "R", "start": 19, "end": 30, "by": [0.03, 0.1, -0.01]},
            {"type": "handover", "character": "boy", "hand": "R", "to": "girl", "toHand": "R", "toSocket": "grip_b",
             "start": 30, "receiverStart": 30, "contact": 46, "release": 51, "end": 63, "at": meet},
            {"type": "hold", "character": "girl", "hand": "R", "start": 52, "end": 68, "by": [0.03, 0.03, -0.02]},
            {"type": "look", "character": "girl", "start": 1, "end": 26, "target": [BOY_POS[0], 0.78, BOY_POS[2]]},
            {"type": "emotion", "character": "girl", "name": "happy", "start": 44, "end": 90, "intensity": 0.7}],
        "production": {"cast": {"boy": {"spec": SPEC, "overrides": [OVERRIDE]}, "girl": {"spec": GIRL_SPEC}},
                       "profile": "pipeline/charsys/rig_profiles/humanoid_rigify.json",
                       "render": {"resolution": [640, 360], "samples": 16, "light_scale": 1.0}},
        "x_t022_derivation": {"grip_from_right_shoulder_in_arm_lengths": REACH, "boy_arm_length": round(arm_len, 4),
                              "boy_right_shoulder_rest": shoulder, "grip_socket_world": grip,
                              "cup_yaw": "boy yaw + 180: grip (local +x) faces his right, grip_b faces the girl's right",
                              "table_top": "cup base height", "handover_at": "midpoint of the two right shoulders, 0.4 x the shorter arm lower",
                              "girl_arm_length": round(g_arm, 4), "handover_point": meet}}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(shot, open(OUT, "w"), indent=1)
    print(OUT, json.dumps(shot["x_t022_derivation"]))


main()
