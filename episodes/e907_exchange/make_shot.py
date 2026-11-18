"""Writes the T-095 two-person exchange shot episodes/e907_exchange/shots/s010/shot.scene.json (python3).

    python3 episodes/e907_exchange/make_shot.py [--boy-package <pkg dir> --girl-package <pkg dir>]

2.75 s at 24 fps, cast "current" (boy 2.0.0, girl 0.11.0 today). The boy and the girl stand side by side behind a
small table, both opened towards the camera as in the references (PB f12/157/272, WT f24: the children stand next to
each other at a table and the camera sees both faces). He picks a felt cup up from the table with his inner (right)
hand and offers it; she takes it with her inner (left) hand at the cup's other handle. Shared interaction actions
only (scene/interaction.h: grasp, hold, handover, hold) plus look and emotion actions.

Beats (scene frames; "who notices, who acts, who reacts"):
- f1    she is busy with the table in front of her; he looks at the cup.
- f6    he acts: reaches for the cup (contact f18) and lifts it towards her (hold f20..f30), still looking at it.
- f22   she notices: her eyes go to the offered cup (the observer glances first) ...
- f30   ... and only then her hand answers: her reach starts eight frames after the glance (contact f44).
- f30   he looks up at her face while he holds the cup out ("here").
- f44..f50 both hands share the cup (her contact f44, his release f50); she is pleased (happy from f42) and looks up
        at his face at f48; the accepted frame is f47.
- f50.. he lets go and draws his hand back, glances at her, then looks off to the side (impatient, low-key; boy
        REFERENCE_BEHAVIOUR); she draws the cup towards herself (hold f52..f64).

Staging (derived from the two current rigs, not tuned per character). Natural hand as in e905 (T-082): an easy,
almost straight arm held forward and a little down (ARM_REACH of the arm length, ARM_DROP below horizontal), from the
package skeleton's shoulder of the inner arm.
- Both turn TURN degrees from facing the camera towards each other (references: three-quarter faces, never profiles;
  at 68 degrees, e905, her near eye went behind her hair and glasses).
- He stands on the camera's right, she on its left, so each one's inner hand is the hand nearer the other: his
  right, her left. The cup's grip handle (local +x) faces him, grip_b (-x) faces her.
- Her natural hand is across the cup from his (cup width + HANDOVER_GAP); her position follows from that. This
  sets the shoulder spacing from the two arm lengths and shoulder widths.
- The cup stands on the table under his natural hand (PICKUP forward of it) and is only lifted (LIFT).
- Camera: in front, CAMERA_ELEV degrees above the target, the target between the heads' and the cup's heights; the
  distance frames the two heads and the cup with FRAME_MARGIN (16:9, 32 mm on a 36 mm film width).
The derived numbers are written into the shot (x_t095_staging): a shot is data, this script is the derivation.
Without packages it uses defaults measured on the current packages (boy 2.0.0, girl 0.11.0)."""
import argparse
import array
import json
import math
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "episodes", "e907_exchange", "shots", "s010", "shot.scene.json")
CAST = {"boy": "boy_yellow_hoodie", "girl": "girl_auburn_bun_glasses"}

TURN = 25.0  # degrees each one turns from facing the camera towards the other
ARM_REACH, ARM_DROP = 0.93, 0.35  # natural hand (T-082): 0.93 of the arm length, 20 deg below horizontal
ARM_IN = 50.0  # degrees: the offering / taking arm points this far towards the partner (keeps the heads apart)
PICKUP_FWD = 0.0  # the cup's grip this far in front of his natural hand when it stands on the table
LIFT = 0.01
OFFER = 0.35  # his offer (hold) carries the cup this share of the way to the hand-over point before she reaches
CUP_YAW = -75.0  # degrees about +Y; grip (local +x) turned towards him and the camera, grip_b towards her and back
GIRL_NECK_PITCH = 10.0  # life.gaze.assistPitchDeg (default 35, e905 20): she looks down at the cup mostly with her eyes; her hair stays off his
HEAD_FOLLOW = 0.3  # life.headFollow (default 0.55): the head takes this share of a gaze turn; the eyes do the rest
BODY_YAW = 0.0  # life.gaze.assistBodyYawDeg (default 35): no chest twist towards the look target
NECK_YAW = 15.0  # life.gaze.assistYawDeg (default 70): looking at each other is mostly eyes, so the heads stay apart
FOCAL, FILM_W, ASPECT = 32.0, 36.0, 16.0 / 9.0
CAMERA_ELEV = 12.0  # degrees: the references look at the children from slightly above
FRAME_MARGIN = 1.15
CUP = json.load(open(os.path.join(ROOT, "content", "assets", "felt_cup.asset.json")))
CUP_GRIP = tuple(CUP["sockets"]["grip"]["translation"])
CUP_GRIP_B = tuple(CUP["sockets"]["grip_b"]["translation"])
CUP_HEIGHT = CUP["mesh"]["height"]

# beats (scene frames)
F = {"end": 66, "grasp": 4, "his_contact": 18, "offer": (20, 28), "her_glance": 20, "her_reach": 27, "his_look_up": 29,
     "her_contact": 45, "her_happy": 43, "her_look_up": 49, "accept": 48, "his_release": 51, "his_end": 61,
     "his_look_off": 59, "her_draw": (53, 65)}

# defaults: measured on the current packages (boy 2.0.0, girl 0.11.0), see --boy-package / --girl-package
DEFAULT_RIG = {"boy": {"shoulder": {"R": [-0.1105, 0.6206, 0.0], "L": [0.1105, 0.6206, 0.0]}, "arm": 0.2667,
                       "head": [0.0, 0.7, 0.0], "top": 1.1132, "head_half_width": 0.2312},
               "girl": {"shoulder": {"R": [-0.098, 0.6141, 0.0], "L": [0.098, 0.6141, 0.0]}, "arm": 0.18,
                        "head": [0.0, 0.69, 0.0], "top": 1.1715, "head_half_width": 0.2405}}


def yaw_rot(deg, v):
    """Engine yaw (degrees about +Y): local +Z (forward) -> (sin, 0, cos)."""
    a = math.radians(deg)
    x, y, z = v
    return (x * math.cos(a) + z * math.sin(a), y, -x * math.sin(a) + z * math.cos(a))


def rig(pkg):
    """Inner-arm shoulders, arm length, head bone and the head's extent (top, half width; every mesh vertex above the
    head bone, hair included) from an engine package."""
    char = json.load(open(os.path.join(pkg, "character.json")))
    sk = {b["name"]: b for b in char["skeleton"]}
    d = lambda a, b: math.dist(sk[a]["head"], sk[b]["head"])  # noqa: E731
    head = sk["head"]["head"]
    geo = open(os.path.join(pkg, "geometry.bin"), "rb").read()
    top, half = head[1], 0.0
    for m in char["meshes"]:
        pos = array.array("f", geo[m["positions"]["offset"]:m["positions"]["offset"] + 4 * m["positions"]["count"]])
        for i in range(0, len(pos), 3):
            if pos[i + 1] > head[1]:
                top, half = max(top, pos[i + 1]), max(half, abs(pos[i]))
    return {"shoulder": {s: sk[f"upperArm.{s}"]["head"] for s in "LR"},
            "arm": d("upperArm.R", "forearm.R") + d("forearm.R", "hand.R"), "head": head,
            "top": round(top, 4), "head_half_width": round(half, 4)}


def natural_hand(pos, yaw, shoulder, arm_len):
    """World position of a character's natural hand (the arm whose shoulder is given), see ARM_REACH / ARM_DROP; the
    arm points ARM_IN towards its own side (the partner's side for the inner arm)."""
    L = ARM_REACH * arm_len
    out = math.copysign(math.sin(math.radians(ARM_IN)), shoulder[0])
    fwd = math.cos(math.radians(ARM_IN))
    h = L * math.cos(ARM_DROP)
    local = (shoulder[0] + h * out, shoulder[1] - L * math.sin(ARM_DROP), shoulder[2] + h * fwd)
    w = yaw_rot(yaw, local)
    return [pos[i] + w[i] for i in range(3)]


def r4(v):
    return [round(x, 4) for x in v]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--boy-package")
    ap.add_argument("--girl-package")
    a = ap.parse_args()
    B = rig(a.boy_package) if a.boy_package else DEFAULT_RIG["boy"]
    G = rig(a.girl_package) if a.girl_package else DEFAULT_RIG["girl"]
    byaw, gyaw = -TURN, TURN  # he stands at +x (camera right) and turns to -x; she the mirror
    bh = natural_hand((0, 0, 0), byaw, B["shoulder"]["R"], B["arm"])
    gh0 = natural_hand((0, 0, 0), gyaw, G["shoulder"]["L"], G["arm"])
    g_off, gb_off = yaw_rot(CUP_YAW, CUP_GRIP), yaw_rot(CUP_YAW, CUP_GRIP_B)
    # her natural hand where the cup's other handle is when his handle is at his natural hand (raised by LIFT)
    across = [bh[0] - g_off[0] + gb_off[0], gh0[1], bh[2] - g_off[2] + gb_off[2]]
    gpos = [across[0] - gh0[0], 0.0, across[2] - gh0[2]]
    mid = [gpos[0] / 2, 0.0, gpos[2] / 2]
    shift = lambda v: r4([v[0] - mid[0], v[1], v[2] - mid[2]])  # noqa: E731
    boy_pos, girl_pos = shift([0, 0, 0]), shift(gpos)
    bh, gh = shift(bh), shift(across)
    # the cup on the table: grip (local +x, towards him) just in front of his natural hand
    grip = r4([bh[0], bh[1], bh[2] + PICKUP_FWD])
    cup = r4([grip[i] - g_off[i] for i in range(3)])
    top = cup[1]
    table = [{"name": "table_top", "kind": "box", "min": r4([cup[0] - 0.09, top - 0.03, cup[2] - 0.07]),
              "max": r4([cup[0] + 0.09, top, cup[2] + 0.07]), "material": "table_mat"},
             {"name": "table_leg", "kind": "box", "min": r4([cup[0] - 0.025, 0.0, cup[2] - 0.025]),
              "max": r4([cup[0] + 0.025, top - 0.03, cup[2] + 0.025]), "material": "table_mat"}]
    # hand-over point (cup origin): each handle as near its holder's natural hand as the rigid cup allows (the mean of
    # the two cup positions that put one handle exactly at one natural hand); the planner refines it (T-030 grid)
    # height: her handle at her natural hand (her 18 cm arm has no slack; his longer arm takes the difference)
    meet = r4([bh[0] - g_off[0], gh[1] - gb_off[1] + LIFT, bh[2] - g_off[2]])
    his_reach = math.dist([meet[i] + g_off[i] for i in range(3)], shift(yaw_rot(byaw, B["shoulder"]["R"])))
    her_reach = math.dist([meet[i] + gb_off[i] for i in range(3)], shift([gpos[i] + yaw_rot(gyaw, G["shoulder"]["L"])[i] for i in range(3)]))
    offer_by = r4([OFFER * (meet[0] - cup[0]), LIFT, OFFER * (meet[2] - cup[2])])
    # heads (skeleton head bone, rest) and the camera
    bhead = [boy_pos[0] + yaw_rot(byaw, B["head"])[0], B["head"][1], boy_pos[2] + yaw_rot(byaw, B["head"])[2]]
    ghead = [girl_pos[0] + yaw_rot(gyaw, G["head"])[0], G["head"][1], girl_pos[2] + yaw_rot(gyaw, G["head"])[2]]
    head_dist = math.dist(bhead, ghead)
    head_top = max(B["top"], G["top"])
    low = cup[1] - 0.12  # the table under the cup
    target = [0.0, round(0.5 * (low + head_top), 3), round(0.5 * (bhead[2] + ghead[2]) * 0.5 + 0.5 * meet[2], 3)]
    vfov = 2 * math.atan(FILM_W / 2 / FOCAL / ASPECT)
    hfov = 2 * math.atan(FILM_W / 2 / FOCAL)
    width = abs(boy_pos[0] - girl_pos[0]) + B["head_half_width"] + G["head_half_width"]  # both heads
    dist = FRAME_MARGIN * max((head_top - low) / 2 / math.tan(vfov / 2), width / 2 / math.tan(hfov / 2))
    el = math.radians(CAMERA_ELEV)
    cam = [0.0, round(target[1] + dist * math.sin(el), 3), round(target[2] + dist * math.cos(el), 3)]
    boy_face = [round(bhead[0], 3), round(bhead[1] + 0.1, 3), round(bhead[2], 3)]
    girl_face = [round(ghead[0], 3), round(ghead[1] + 0.1, 3), round(ghead[2], 3)]
    her_task = r4([girl_pos[0] + yaw_rot(gyaw, (0, 0, 0.35))[0], cup[1], girl_pos[2] + yaw_rot(gyaw, (0, 0, 0.35))[2]])
    off_side = r4([boy_pos[0] + 1.2, 0.6, boy_pos[2] + 1.0])  # his "bored" glance: away from her, to his left
    offered = r4([cup[0] + offer_by[0], cup[1] + 0.05, cup[2] + offer_by[2]])
    shot = {
        "format": "plush.scene", "version": 1,
        "name": "e907_exchange s010: T-095 readable two-person exchange - he offers a cup, she notices, takes it",
        "frameRate": [24, 1], "frameStart": 1, "frameEnd": F["end"],
        "render": {"width": 640, "height": 360, "spp": 32, "maxDepth": 8, "exposureEV": 0.3, "denoise": True,
                   "denoiseBlend": 0.85, "clamp": 12},
        "camera": {"position": cam, "target": target, "focalMm": FOCAL, "fStop": 0, "focusDistance": -1},
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
        "props": [{"name": "cup", "id": "prop.felt_cup", "transform": {"translation": cup, "rotationDeg": [0, CUP_YAW, 0], "scale": [1, 1, 1]}}],
        "characters": [{"name": "boy", "asset": "(set by run_shot)", "position": boy_pos, "yawDeg": byaw,
                        "life": {"blinkInterval": 2.2, "headFollow": HEAD_FOLLOW, "gaze": {"assistYawDeg": NECK_YAW, "assistBodyYawDeg": BODY_YAW}}},
                       {"name": "girl", "asset": "(set by run_shot)", "position": girl_pos, "yawDeg": gyaw,
                        "life": {"blinkInterval": 2.6, "headFollow": HEAD_FOLLOW, "gaze": {"assistPitchDeg": GIRL_NECK_PITCH, "assistYawDeg": NECK_YAW, "assistBodyYawDeg": BODY_YAW}}}],
        "actions": [
            {"type": "clip", "character": "boy", "clip": "idle_relaxed", "base": True},
            {"type": "clip", "character": "girl", "clip": "idle_relaxed", "base": True},
            {"type": "look", "character": "girl", "start": 1, "end": F["her_glance"] - 1, "target": her_task},
            {"type": "grasp", "character": "boy", "hand": "R", "prop": "cup", "socket": "grip", "start": F["grasp"],
             "contact": F["his_contact"]},
            {"type": "hold", "character": "boy", "hand": "R", "start": F["offer"][0], "end": F["offer"][1], "by": offer_by},
            {"type": "look", "character": "girl", "start": F["her_glance"], "end": F["her_reach"], "target": offered},
            {"type": "handover", "character": "boy", "hand": "R", "to": "girl", "toHand": "L", "toSocket": "grip_b",
             "start": F["offer"][1], "receiverStart": F["her_reach"], "contact": F["her_contact"],
             "release": F["his_release"], "end": F["his_end"], "at": meet},
            {"type": "look", "character": "boy", "start": F["his_look_up"], "end": F["her_contact"] - 2, "target": girl_face},
            {"type": "look", "character": "boy", "start": F["her_contact"] - 1, "end": F["his_release"], "target": offered},
            {"type": "hold", "character": "girl", "hand": "L", "start": F["her_draw"][0], "end": F["her_draw"][1],
             "by": [-0.03, 0.03, -0.02]},
            {"type": "look", "character": "girl", "start": F["her_look_up"], "end": F["end"], "target": boy_face},
            {"type": "look", "character": "boy", "start": F["his_release"] + 2, "end": F["his_look_off"] - 1, "target": girl_face},
            {"type": "look", "character": "boy", "start": F["his_look_off"], "end": F["end"], "target": off_side},
            {"type": "emotion", "character": "girl", "name": "happy", "start": F["her_happy"], "end": 90, "intensity": 0.7}],
        "production": {"cast": {n: {"character_id": cid, "version": "current"} for n, cid in CAST.items()},
                       "profile": "pipeline/charsys/rig_profiles/humanoid_rigify.json",
                       "render": {"resolution": [640, 360], "samples": 16, "light_scale": 1.0}},
        "x_t095_staging": {
            "rule": "side by side behind a table, both turned TURN from the camera towards each other; natural inner "
                    "hands (ARM_REACH, ARM_DROP), hers across the cup from his; camera in front, CAMERA_ELEV above",
            "beats": F, "turn_deg": TURN, "arm_in_deg": ARM_IN, "arm_reach": ARM_REACH, "arm_drop_rad": ARM_DROP,
            "boy_arm_length": round(B["arm"], 4), "girl_arm_length": round(G["arm"], 4),
            "boy_right_shoulder_rest": r4(B["shoulder"]["R"]), "girl_left_shoulder_rest": r4(G["shoulder"]["L"]),
            "boy_natural_hand": bh, "girl_natural_hand": gh, "grip_socket_world": grip, "handover_point": meet,
            "boy_reach_at_handover": round(his_reach / B["arm"], 3), "girl_reach_at_handover": round(her_reach / G["arm"], 3),
            "shoulder_spacing": round(abs(boy_pos[0] - girl_pos[0]), 4), "head_bone_distance_rest": round(head_dist, 4),
            "camera_distance": round(dist, 3), "girl_neck_pitch_deg": GIRL_NECK_PITCH, "neck_yaw_assist_deg": NECK_YAW, "head_follow": HEAD_FOLLOW, "body_yaw_assist_deg": BODY_YAW,
            "cup_yaw_deg": CUP_YAW}}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(shot, f, indent=1)
        f.write("\n")
    print(os.path.relpath(OUT, ROOT), json.dumps(shot["x_t095_staging"]))


main()
