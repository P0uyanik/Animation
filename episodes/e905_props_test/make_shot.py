"""Writes the T-022 hand-prop test shot episodes/e905_props_test/shots/s010/shot.scene.json (python3).

    python3 episodes/e905_props_test/make_shot.py [--boy-package <pkg dir> --girl-package <pkg dir>]

3 s at 24 fps: the boy picks a felt cup (content/assets/felt_cup.asset.json) up from a small table with his right
hand, holds it out low, and the girl takes it with her right hand at the cup's other grip socket and draws it
towards herself. Everything is shared interaction actions (scene/interaction.h): grasp, hold, handover, hold.

Staging (T-082, owner decision 2026-11-18: natural, reference-matching motion). It is derived from each character's
natural hand position, not tuned per character. That position is an easy, almost straight arm held forward and a
little down (ARM_REACH of the arm length, ARM_DROP below horizontal): for these short-armed plush characters this
keeps the cup low, the elbow down and the heads apart.
- The boy's references show low, practical hands and elbows in (docs/characters/boy_yellow_hoodie/REFERENCE_BEHAVIOUR.md).
- The cup stands on the table where his hand naturally is, so he picks it up and holds it out without lifting it to
  his face.
- The girl stands so her natural hand is across the cup from his (HANDOVER_GAP beyond the cup's width). The two
  stand offset, so their right hands line up without crossing their own bodies.
- Both keep T-022's 22 degree cheat towards the camera.
- The camera looks at the pair from the side where the hands meet, perpendicular to the line between them.
- Her neck follows her eyes only up to 20 degrees (life.gaze), so looking down at the cup does not put her head
  into his.
The derived numbers are written into the shot file (a shot is data); this script documents how they were derived.
Without packages it uses the defaults measured on boy 1.1.0 / girl (current spec) packages.

T-022/T-030 staging (replaced): the cup 0.85 arm forward and 0.45 down from his shoulder, a 10 cm lift, and a hand-over
point between the shoulders "0.4 arm lower", measured from the cup's base, not its grip. That carried his hand to
shoulder height in front of his face, where no arm pose looks natural (T-047 wing elbow, T-082 report)."""
import argparse
import json
import math
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "episodes", "e905_props_test", "shots", "s010", "shot.scene.json")
SPEC = "assets/characters/boy_yellow_hoodie/spec/boy_yellow_hoodie.spec.json"
OVERRIDE = "assets/characters/boy_yellow_hoodie/spec/boy_yellow_hoodie.1.1.0.override.json"
GIRL_SPEC = "assets/characters/girl_auburn_bun_glasses/spec/girl_auburn_bun_glasses.spec.json"

CHEAT = 22.0  # both turned this far from facing each other towards the camera (T-022's yaw +-68)
ARM_REACH, ARM_DROP = 0.93, 0.35  # natural hand: 0.93 of the arm length, 0.35 rad (20 deg) below horizontal
HANDOVER_GAP = 0.03  # metres between the two natural hands beyond the cup's width
CUP_WIDTH = 0.08
PICKUP = (-0.03, 0.03)  # the cup's grip from his natural hand, in his frame: outward (to his right), forward
LIFT = 0.01  # the cup is only lifted off the table
GIRL_NECK_PITCH = 20.0  # life.gaze.assistPitchDeg: her neck's share of looking down (default 35)
CAMERA_DIST, CAMERA_HEIGHT, CAMERA_TARGET_Y = 1.75, 0.9, 0.5
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


def natural_hand(pos, yaw, shoulder, arm_len):
    """World position of a character's natural hand (right arm), see ARM_REACH / ARM_DROP."""
    L = ARM_REACH * arm_len
    local = (shoulder[0], shoulder[1] - L * math.sin(ARM_DROP), shoulder[2] + L * math.cos(ARM_DROP))
    w = yaw_rot(yaw, local)
    return [pos[i] + w[i] for i in range(3)]


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
    # Layout around the boy at the origin, then centred so the two characters stand symmetric about x = 0.
    byaw, gyaw = 90.0 - CHEAT, -90.0 + CHEAT
    bh = natural_hand((0, 0, 0), byaw, shoulder, arm_len)
    gh0 = natural_hand((0, 0, 0), gyaw, g_shoulder, g_arm)
    fwd = yaw_rot(byaw, (0, 0, 1))
    across = [bh[i] + fwd[i] * (CUP_WIDTH + HANDOVER_GAP) for i in range(3)]  # her natural hand
    gpos = [across[0] - gh0[0], 0.0, across[2] - gh0[2]]
    mid = [gpos[0] / 2, 0.0, gpos[2] / 2]
    shift = lambda v: [round(v[0] - mid[0], 4), round(v[1], 4), round(v[2] - mid[2], 4)]  # noqa: E731
    boy_pos, girl_pos = shift([0, 0, 0]), shift(gpos)
    bh, gh = shift(bh), shift(across)
    # pickup: the cup's grip a little outward of and in front of his natural hand; the table top under the cup
    off = yaw_rot(byaw, (-PICKUP[0], 0.0, PICKUP[1]))  # his right is local -X
    grip = [round(bh[i] + off[i], 4) for i in range(3)]
    cup_yaw = byaw + 180.0  # local +x (grip) -> the boy's right side; grip_b (-x) -> the girl's right side
    g = yaw_rot(cup_yaw, CUP_GRIP)
    cup = [round(grip[i] - g[i], 4) for i in range(3)]
    top = cup[1]
    table = [{"name": "table_top", "kind": "box", "min": [round(cup[0] - 0.08, 4), round(top - 0.03, 4), round(cup[2] - 0.08, 4)],
              "max": [round(cup[0] + 0.08, 4), round(top, 4), round(cup[2] + 0.08, 4)], "material": "table_mat"},
             {"name": "table_leg", "kind": "box", "min": [round(cup[0] - 0.025, 4), 0.0, round(cup[2] - 0.025, 4)],
              "max": [round(cup[0] + 0.025, 4), round(top - 0.03, 4), round(cup[2] + 0.025, 4)], "material": "table_mat"}]
    # hand-over point (the cup's origin): between the two natural hands, his grip at his natural hand height
    meet = [round(0.5 * (bh[i] + gh[i]), 4) for i in range(3)]
    meet[1] = round(bh[1] - CUP_GRIP[1] + LIFT, 4)
    hold_by = [round(0.4 * (meet[0] - cup[0]), 4), LIFT, round(0.4 * (meet[2] - cup[2]), 4)]
    # camera: perpendicular to the line between the two, on the side where the hands meet
    line = [girl_pos[0] - boy_pos[0], girl_pos[2] - boy_pos[2]]
    n = math.hypot(*line)
    perp = [-line[1] / n, line[0] / n]
    if perp[0] * (meet[0]) + perp[1] * (meet[2]) < 0:
        perp = [-perp[0], -perp[1]]
    cam = [round(perp[0] * CAMERA_DIST, 3), CAMERA_HEIGHT, round(perp[1] * CAMERA_DIST, 3)]
    shot = {
        "format": "plush.scene", "version": 1,
        "name": "e905_props_test s010: T-022 hand interaction - boy picks up a cup and hands it to the girl",
        "frameRate": [24, 1], "frameStart": 1, "frameEnd": 72,
        "render": {"width": 640, "height": 360, "spp": 32, "maxDepth": 8, "exposureEV": 0.3, "denoise": True,
                   "denoiseBlend": 0.85, "clamp": 12},
        "camera": {"position": cam, "target": [0.0, CAMERA_TARGET_Y, 0.0], "focalMm": 32, "fStop": 0, "focusDistance": -1},
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
        "characters": [{"name": "boy", "asset": "(set by run_shot)", "position": boy_pos, "yawDeg": byaw,
                        "life": {"blinkInterval": 2.2}},
                       {"name": "girl", "asset": "(set by run_shot)", "position": girl_pos, "yawDeg": gyaw,
                        "life": {"blinkInterval": 2.6, "gaze": {"assistPitchDeg": GIRL_NECK_PITCH}}}],
        "actions": [
            {"type": "clip", "character": "boy", "clip": "idle_relaxed", "base": True},
            {"type": "clip", "character": "girl", "clip": "idle_relaxed", "base": True},
            {"type": "grasp", "character": "boy", "hand": "R", "prop": "cup", "socket": "grip", "start": 3, "contact": 17},
            {"type": "hold", "character": "boy", "hand": "R", "start": 19, "end": 30, "by": hold_by},
            {"type": "handover", "character": "boy", "hand": "R", "to": "girl", "toHand": "R", "toSocket": "grip_b",
             "start": 30, "receiverStart": 30, "contact": 46, "release": 51, "end": 63, "at": meet},
            {"type": "hold", "character": "girl", "hand": "R", "start": 52, "end": 68, "by": [0.03, 0.03, -0.02]},
            {"type": "look", "character": "girl", "start": 1, "end": 26, "target": [boy_pos[0], 0.78, boy_pos[2]]},
            {"type": "emotion", "character": "girl", "name": "happy", "start": 44, "end": 90, "intensity": 0.7}],
        "production": {"cast": {"boy": {"spec": SPEC, "overrides": [OVERRIDE]}, "girl": {"spec": GIRL_SPEC}},
                       "profile": "pipeline/charsys/rig_profiles/humanoid_rigify.json",
                       "render": {"resolution": [640, 360], "samples": 16, "light_scale": 1.0}},
        "x_t082_staging": {"rule": "natural hands: an easy arm, ARM_REACH of its length, ARM_DROP below horizontal; "
                                    "the cup at his, hers across the cup; offset so the right hands line up",
                           "arm_reach": ARM_REACH, "arm_drop_rad": ARM_DROP, "handover_gap": HANDOVER_GAP, "cheat_deg": CHEAT,
                           "boy_arm_length": round(arm_len, 4), "girl_arm_length": round(g_arm, 4),
                           "boy_right_shoulder_rest": shoulder, "girl_right_shoulder_rest": g_shoulder,
                           "boy_natural_hand": bh, "girl_natural_hand": gh, "grip_socket_world": grip,
                           "handover_point": meet, "girl_neck_pitch_deg": GIRL_NECK_PITCH,
                           "cup_yaw": "boy yaw + 180: grip (local +x) faces his right, grip_b faces the girl's right"}}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(shot, open(OUT, "w"), indent=1)
    print(OUT, json.dumps(shot["x_t082_staging"]))


main()
