"""T-187 paper-boat test scene (low-quality preview, not for publication). Writes the two scene files of e912:

    python3 episodes/e912_paper_boat/make_shots.py [--stage measure|full]

  shots/s010/shot.scene.json   scene A = shots 1-2 (the paper sheet)
  shots/s020/shot.scene.json   scene B = shots 3-5 (the boat; the cut between the two scenes replaces the sheet with
                               the boat, so no prop has to pop inside one scene)

Both scenes start with a hidden pre-roll: the cast stands at its stools and sits down (T-175 cmu_sit_down, foot-lock
+ foot_home), the rendered range starts seated (RENDER_A / RENDER_B). Everything is existing systems only: T-175
mocap clips (sit / stand / walk), the verbs (pick_up, carry, pass) with T-185's r3 fingerClose, touch, look, emotion,
the calibrated T-106 timing. Staging measured from a first bake (staging.json, written by measure_staging.py) places
the stools under the seated hips and the table under the seated hands.

Cast (owner: the current released characters): boy_yellow_hoodie 2.3.0 and girl_auburn_bun_glasses 0.14.0 ("current"),
girl_white_hair_blue_dress 0.1.0 (published version dir; she is not in the fidelity baseline that "current" reads).
Seating, camera left to right: white-hair girl ("white") | auburn girl ("auburn") | boy, facing the camera (+Z)."""
import argparse
import copy
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
CLIPS = os.path.join(ROOT, "content", "clips", "mocap")
STAGING = os.path.join(HERE, "staging.json")

CAST = {"white": {"version_dir": "assets/characters/girl_white_hair_blue_dress/versions/0.1.0"},
        "auburn": {"character_id": "girl_auburn_bun_glasses", "version": "current"},
        "boy": {"character_id": "boy_yellow_hoodie", "version": "current"}}
PERSONALITY = {"white": "girl_white_hair_blue_dress", "auburn": "girl_auburn_bun_glasses", "boy": "boy_yellow_hoodie"}
# Lowest rest vertex of the shoes under the character origin (m): boy / auburn from T-175 (make_review_shot.py SOLE),
# white measured from her 0.1.0 package (measure_staging.py --sole).
SOLE = {"boy": 0.0271, "auburn": 0.0295, "white": 0.0238}
X = {"white": -0.43, "auburn": 0.0, "boy": 0.4}
YAW = {"white": 18.0, "auburn": 0.0, "boy": -18.0}
ORDER = ("white", "auburn", "boy")

SIT_START = 6  # the pre-roll: idle 1..SIT_START+8, sit-down from SIT_START (28 scene frames)


def r4(v):
    return [round(float(x), 4) for x in v]


def mat(name, rgb, rough=0.85):
    return {"name": name, "type": "standard", "baseColor": rgb, "roughness": rough, "specular": 0.3}


def staging():
    if os.path.isfile(STAGING):
        return json.load(open(STAGING, encoding="utf-8"))
    return {}


def base_scene(name, frame_end, st, table=None):
    sole = dict(SOLE)
    chars = []
    for who in ORDER:
        chars.append({"name": who, "asset": "(set by run_shot)", "position": [X[who], sole[who], 0.0], "yawDeg": YAW[who],
                      "life": {"sway": 0, "headFollow": 0.35}, "autoIdle": False,
                      "personality": PERSONALITY[who]})
    objects = [{"name": "floor", "kind": "box", "min": [-6, -0.05, -4], "max": [6, 0, 6], "material": "floor_mat"},
               {"name": "wall", "kind": "box", "min": [-6, 0, -1.3], "max": [6, 3, -1.2], "material": "wall_mat"},
               {"name": "board", "kind": "box", "min": [-0.9, 0.55, -1.2], "max": [0.9, 1.15, -1.18], "material": "board_mat"},
               {"name": "board_frame", "kind": "box", "min": [-0.94, 0.51, -1.21], "max": [0.94, 1.19, -1.195],
                "material": "frame_mat"}]
    for who in ORDER:
        if who in st.get("stools", {}):
            lo, hi = st["stools"][who]
            objects.append({"name": f"stool_{who}", "kind": "box", "min": r4(lo), "max": r4(hi), "material": "seat_mat"})
    if table:
        lo, hi = table
        objects.append({"name": "table_top", "kind": "box", "min": r4([lo[0], hi[1] - 0.025, lo[2]]), "max": r4(hi),
                        "material": "table_mat"})
        for i, (x, z) in enumerate([(lo[0] + 0.03, lo[2] + 0.03), (hi[0] - 0.03, lo[2] + 0.03), (lo[0] + 0.03, hi[2] - 0.03),
                                    (hi[0] - 0.03, hi[2] - 0.03)]):
            objects.append({"name": f"table_leg{i}", "kind": "box", "min": r4([x - 0.015, 0, z - 0.015]),
                            "max": r4([x + 0.015, hi[1] - 0.025, z + 0.015]), "material": "table_mat"})
    return {"format": "plush.scene", "version": 1, "name": name, "frameRate": [24, 1], "frameStart": 1, "frameEnd": frame_end,
            "timing": "calibrated",
            "render": {"width": 640, "height": 360, "spp": 16, "maxDepth": 8, "exposureEV": 0.3, "denoise": True, "denoiseBlend": 0.85,
                       "clamp": 12},
            "camera": {"position": [0.0, 0.75, 2.6], "target": [0.0, 0.35, 0.0], "focalMm": 32, "fStop": 0, "focusDistance": -1},
            "materials": [mat("floor_mat", [0.5, 0.44, 0.36]), mat("wall_mat", [0.72, 0.68, 0.58], 0.9),
                          mat("board_mat", [0.12, 0.22, 0.17], 0.8), mat("frame_mat", [0.45, 0.32, 0.2], 0.7),
                          mat("seat_mat", [0.35, 0.5, 0.62], 0.7), mat("table_mat", [0.62, 0.46, 0.3], 0.7)],
            "lights": [{"type": "rect", "corner": [-1.6, 1.4, 1.8], "edgeU": [1.4, 0, 0.4], "edgeV": [0, 0.9, 0.3],
                        "color": [1.0, 0.95, 0.88], "intensity": 3.0},
                       {"type": "sun", "direction": [0.3, -0.6, -0.7], "angleDeg": 4, "color": [1.0, 0.92, 0.82], "intensity": 1.4},
                       {"type": "sky", "color": [0.6, 0.62, 0.66], "intensity": 0.45}],
            "objects": objects, "characters": chars, "props": [], "actions": [], "animation": {}, "events": [],
            "production": {"cast": copy.deepcopy(CAST), "profile": "pipeline/charsys/rig_profiles/humanoid_rigify.json",
                           "render": {"resolution": [640, 360], "samples": 16, "light_scale": 1.0}}}


def sit_actions(who, hold_end):
    """Pre-roll: stand (idle), sit down, stay seated until hold_end (the clip holds its last, seated frame)."""
    return [{"type": "clip", "character": who, "clip": "idle_relaxed", "start": 1, "end": SIT_START + 8, "blendIn": 0, "blendOut": 8},
            {"type": "clip", "character": who, "clip": "mocap/cmu_sit_down", "start": SIT_START, "end": hold_end,
             "blendIn": 8, "blendOut": 0}]


def write(rel, scene):
    path = os.path.join(HERE, rel, "shot.scene.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(scene, f, indent=1)
        f.write("\n")
    print(os.path.relpath(path, ROOT))


# --- staging (metres, engine axes; staging.json from measure_staging.py) -------------------------------------------
# The girls' arms are short (shoulder to wrist 0.18 m, hand 0.05 m; boy 0.27 + 0.08): the table is high (top TABLE_Y,
# 8 cm under the auburn girl's seated shoulders) and its near edge just in front of the seated chests (TABLE_Z0), so
# her hands reach the sheet and the boat. Standing, the chests come 0.08-0.13 m forward: s030 (stand up) moves the
# table back by TABLE_BACK_S030 (nobody touches it there; across the cut the move is not visible in the wide shot).
TABLE_Y = 0.45
TABLE_Z0 = 0.055
TABLE_DEPTH = 0.27
TABLE_BACK_S030 = 0.11
SHEET = "prop.e912_origami_sheet"   # 15 cm square, 1.2 mm
BOAT = "prop.e912_paper_boat"       # hull 100 x 26 x 42 mm; sail + two flared ends are child props
BOAT_H = 0.026

# T-185: T-171 round 3 variant r3 (episodes/e910_showcase/make_shot.py R3), key for key, on every verb.
R3_REST = {"curl": 0.25, "thumb": 0.12, "spread": 0.6,
           "fingers": {"index": {"curl": 0.14, "spread": 0.9}, "middle": {"curl": 0.22, "spread": 0.6},
                       "ring": {"curl": 0.29, "spread": 0.6}, "little": {"curl": 0.35, "spread": 0.9}}}
R3 = {"rest": R3_REST, "wrap": True, "grip": "natural", "clear": 0.006}
BOAT_IN_HAND = ([0.0154, -0.0757, 0.0], [-91.63, 0.0, 135.0])  # boy hand.R -> boat (s020 bake f205, after the pass)


def table_box(dz=0.0):
    return ([-0.66, 0.0, TABLE_Z0 + dz], [0.66, TABLE_Y, TABLE_Z0 + dz + TABLE_DEPTH])


def boat_props(at, yaw=0.0, parent=None):
    """The boat: the hull (the prop the hands hold) + sail + two flared ends parented to its sockets."""
    hull = {"name": "boat", "id": BOAT, "transform": {"translation": r4(at), "rotationDeg": [0, yaw, 0], "scale": [1, 1, 1]}}
    if parent:
        hull["parent"] = parent
    kids = [{"name": "boat_sail", "id": "prop.e912_paper_boat_sail",
             "transform": {"translation": [0, 0.01, 0], "rotationDeg": [0, 0, 45], "scale": [1, 1, 1]},
             "parent": {"kind": "prop", "name": "boat", "socket": "sail"}}]
    for side, s in (("a", 1), ("b", -1)):
        kids.append({"name": f"boat_end_{side}", "id": "prop.e912_paper_boat_end",
                     "transform": {"translation": [s * 0.004, 0.004, 0], "rotationDeg": [0, 0, -s * 38], "scale": [1, 1, 1]},
                     "parent": {"kind": "prop", "name": "boat", "socket": f"end_{side}"}})
    return [hull] + kids


def cams(sc, cuts):
    """cuts: [(frame, position, target, focal)] -> hard cuts (step keys) on camera.position / .target / .lens."""
    f0, p0, t0, l0 = cuts[0]
    sc["camera"].update({"position": r4(p0), "target": r4(t0), "focalMm": l0})
    sc["animation"]["camera.position"] = [[f, r4(p), "step"] for f, p, t, l in cuts]
    sc["animation"]["camera.target"] = [[f, r4(t), "step"] for f, p, t, l in cuts]
    sc["animation"]["camera.lens"] = [[f, [l, 0, -1], "step"] for f, p, t, l in cuts]


def look(who, start, end, **tgt):
    return {"type": "look", "character": who, "start": start, "end": end, **tgt}


def emo(who, name, start, end, k):
    return {"type": "emotion", "character": who, "name": name, "start": start, "end": end, "intensity": k}


def touch(who, hand, contact, at):
    return {"type": "touch", "character": who, "hand": hand, "start": contact - 10, "contact": contact, "end": contact + 9,
            "target": r4(at)}


# Wide and medium cameras (all scenes): the cast spans x -0.5..0.5, seated heads at y ~0.6.
WIDE = ([0.0, 0.92, 1.75], [0.0, 0.47, 0.0], 32)
ALL3 = ([0.05, 1.2, 1.85], [0.0, 0.5, 0.05], 45)


def measure_scene():
    """The cast sits down and stays seated (no props, no table): for measure_staging.py."""
    sc = base_scene("e912 measure: the cast sits down", 60, {})
    for who in ORDER:
        sc["actions"] += sit_actions(who, 61)
    return sc


def scene_s010(st):
    """Shots 1-2: the wide (all seated, the sheet in front of her), then her hands on the sheet + her face."""
    END = 184
    S1, S2 = 41, 101
    sc = base_scene("e912 s010: shots 1-2 - the three sit at the table; she works a paper sheet, the others watch", END, st,
                    table_box())
    sheet = [0.0, TABLE_Y + 0.0006, TABLE_Z0 + 0.078]
    sc["props"] = [{"name": "sheet", "id": SHEET, "transform": {"translation": r4(sheet), "rotationDeg": [0, 12, 0],
                                                                "scale": [1, 1, 1]}}]
    A = sc["actions"]
    for who in ORDER:
        A += sit_actions(who, END + 1)
    y = TABLE_Y + 0.001
    # shot 1: she looks at the sheet, the others at her; she starts on it at the end of the wide
    A += [look("auburn", 20, S2 + 2, atProp="sheet"), look("boy", 20, 70, atCharacter="auburn"), look("boy", 71, END, atProp="sheet"),
          look("white", 20, 58, atProp="sheet"), look("white", 59, 80, atCharacter="auburn"), look("white", 81, END, atProp="sheet"),
          emo("auburn", "girl_eager", 48, END, 0.6),
          touch("auburn", "L", 88, [0.07, y, TABLE_Z0 + 0.025])]
    # shot 2: her hands alternate on the sheet's near corners, in front of each shoulder (targets nearer the middle
    # are pushed out by the arm-body clearance: her wide torso; T-030) (folding is faked by the framing: no finger animation); she looks
    # down at it the whole time; the boy is curious, the white-hair girl too
    for k, (hand, at) in enumerate([("R", [-0.07, y, TABLE_Z0 + 0.03]), ("L", [0.065, y, TABLE_Z0 + 0.03]),
                                    ("R", [-0.06, y, TABLE_Z0 + 0.04]), ("L", [0.075, y, TABLE_Z0 + 0.025]),
                                    ("R", [-0.075, y, TABLE_Z0 + 0.025])]):
        A.append(touch("auburn", hand, 110 + 15 * k, at))
    A += [look("auburn", S2 + 3, END, target=r4([0.0, y, TABLE_Z0 + 0.12])),
          emo("boy", "boy_focused", 112, END, 0.6), emo("white", "curious", 120, END, 0.6)]
    cams(sc, [(1, *WIDE), (S2, [0.03, 0.78, 0.95], [0.0, 0.5, 0.06], 45)])
    sc["x_t187"] = {"shots": [{"shot": 1, "frames": [S1, S2 - 1], "camera": "wide"},
                              {"shot": 2, "frames": [S2, END], "camera": "medium on her (hands + face)"}],
                    "render_frames": [S1, END]}
    return sc


def scene_s020(st):
    """Shots 3-4: the boat is there; she picks it up and shows it, the others are surprised; she hands it to the boy."""
    END = 208
    S3, S4 = 41, 125
    sc = base_scene("e912 s020: shots 3-4 - the boat: she shows it, the others are surprised; she gives it to the boy", END, st,
                    table_box())
    # the boat on the table where the sheet was, its grip_b end (local -x) towards her left hand
    sc["props"] = boat_props([0.13, TABLE_Y + BOAT_H / 2, TABLE_Z0 + 0.028])
    A = sc["actions"]
    for who in ORDER:
        A += sit_actions(who, END + 1)
    show = [0.14, 0.5, 0.02]
    meet = [0.2, 0.52, TABLE_Z0 + 0.02]
    A += [
        # shot 3: she lifts the boat and shows it; both others surprised (eyes on the boat); she is delighted
        {"type": "pick_up", "character": "auburn", "hand": "L", "prop": "boat", "set": "b", "start": S3 - 6, "settle": 4,
         "fingerClose": copy.deepcopy(R3)},
        {"type": "carry", "character": "auburn", "hand": "L", "at": r4(show)},
        look("boy", 20, S3 + 10, atCharacter="auburn"), look("boy", S3 + 11, S4 + 4, atProp="boat"),
        look("white", 20, S3 + 14, atCharacter="auburn"), look("white", S3 + 15, END, atProp="boat"),
        emo("boy", "surprised", S3 + 18, S4 + 10, 0.9), emo("white", "surprised", S3 + 22, S4 + 20, 0.9),
        look("auburn", S3 + 34, S3 + 60, atCharacter="boy"), look("auburn", S3 + 61, S4 + 2, atCharacter="white"),
        emo("auburn", "girl_delighted", S3 + 30, END, 0.8),
        # shot 4: the hand-over (T-112b pass: her left hand to his right), a shared hold, his delight
        {"type": "pass", "character": "auburn", "hand": "L", "to": "boy", "toHand": "R", "toSet": "a", "at": r4(meet), "start": S4 + 4,
         "receiverStart": S4 + 10, "contact": S4 + 22, "release": S4 + 42, "fingerClose": copy.deepcopy(R3)},
        look("auburn", S4 + 3, S4 + 30, atProp="boat"), look("auburn", S4 + 31, END, atCharacter="boy"),
        look("boy", S4 + 5, S4 + 40, atProp="boat"), look("boy", S4 + 41, S4 + 60, atCharacter="auburn"),
        look("boy", S4 + 61, END, atProp="boat"),
        {"type": "carry", "character": "boy", "hand": "R", "by": [0.0, 0.03, 0.02]},
        emo("boy", "happy", S4 + 46, END, 0.8),
    ]
    cams(sc, [(1, *ALL3), (S4, [0.4, 0.92, 0.9], [0.17, 0.55, 0.03], 40)])
    sc["x_t187"] = {"shots": [{"shot": 3, "frames": [S3, S4 - 1], "camera": "medium wide, all three"},
                              {"shot": 4, "frames": [S4, END], "camera": "two-shot, her and the boy"}],
                    "render_frames": [S3, END]}
    return sc


def scene_s030(st):
    """Shot 5: all three stand up together (wide), cut, they walk off (side camera); the boy has the boat in his hand."""
    END = 166
    S5, S5B = 45, 93
    STAND = 50
    sc = base_scene("e912 s030: shot 5 - they stand up together and walk off", END, st, table_box(TABLE_BACK_S030))
    # the boat rides in his right hand from the start (no hold IK: a hold target is a world point and the arm-body
    # clearance pushed it across his body while he stood up). The offset is his hand -> boat at the end of s020's
    # pass (s020 bake frame 205, measured by hand_offset() in this file's history: translation / XYZ degrees).
    sc["props"] = boat_props(BOAT_IN_HAND[0], parent={"kind": "character", "name": "boy", "socket": "hand.R"})
    sc["props"][0]["transform"]["rotationDeg"] = BOAT_IN_HAND[1]
    A = sc["actions"]
    stand_frames = json.load(open(os.path.join(CLIPS, "cmu_stand_up.clip.json")))["frame_count"]
    stood = STAND + int(math.ceil((stand_frames - 1) / 1.1)) + 2
    sole = dict(SOLE)
    # the walk: single file along +X in front of the table, staggered in depth; position / yaw step at the cut
    lane = {"boy": (-0.45, 0.7), "auburn": (-0.97, 0.95), "white": (-1.5, 1.2)}
    for who in ORDER:
        A += [{"type": "clip", "character": who, "clip": "idle_relaxed", "start": 1, "end": SIT_START + 8, "blendIn": 0, "blendOut": 8},
              {"type": "clip", "character": who, "clip": "mocap/cmu_sit_down", "start": SIT_START, "end": STAND + 6, "blendIn": 8,
               "blendOut": 0},
              {"type": "clip", "character": who, "clip": "mocap/cmu_stand_up", "start": STAND, "end": S5B, "blendIn": 6, "blendOut": 0},
              {"type": "clip", "character": who, "clip": "idle_relaxed", "start": stood, "end": S5B, "blendIn": 10, "blendOut": 0},
              {"type": "clip", "character": who, "clip": "mocap/cmu_walk", "start": S5B, "end": END + 1, "blendIn": 0, "blendOut": 0}]
        x0, z0 = lane[who]
        sc["animation"][f"{who}.position"] = [[1, [X[who], sole[who], 0.0], "step"], [S5B, [x0, sole[who], z0], "step"]]
        sc["animation"][f"{who}.yaw"] = [[1, [YAW[who]] * 3, "step"], [S5B, [90, 90, 90], "step"]]
    A += [
          look("boy", 30, STAND, atProp="boat"), look("boy", STAND + 1, S5B - 1, atCharacter="auburn"),
          look("auburn", 20, S5B - 1, atCharacter="boy"), look("white", 20, S5B - 1, atCharacter="auburn"),
          emo("boy", "happy", 20, END, 0.6), emo("auburn", "girl_content", 20, END, 0.7), emo("white", "girl_content", 30, END, 0.6)]
    cams(sc, [(1, *WIDE), (S5B, [0.2, 0.62, 3.3], [0.2, 0.38, 0.9], 32)])
    sc["x_t187"] = {"shots": [{"shot": "5a", "frames": [S5, S5B - 1], "camera": "wide"},
                              {"shot": "5b", "frames": [S5B, END], "camera": "side-on, they walk off to the right"}],
                    "render_frames": [S5, END], "table_moved_back_m": TABLE_BACK_S030}
    return sc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="full", choices=["measure", "full"])
    a = ap.parse_args()
    if a.stage == "measure":
        write("shots/measure", measure_scene())
        return
    st = staging()
    write("shots/s010", scene_s010(st))
    write("shots/s020", scene_s020(st))
    write("shots/s030", scene_s030(st))


if __name__ == "__main__":
    main()
