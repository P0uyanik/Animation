"""Writes the T-117 cup-exchange showcase episodes/e910_showcase/shots/s010/shot.scene.json (python3).

    python3 episodes/e910_showcase/make_shot.py

8 s at 24 fps (192 frames). The boy and the girl stand at the small table of e907 with the felt cup. Staging, set,
camera, the hand-over point, the verbs' grasp sets and the calibrated timing are the e907 s010_verbs ones (read at
run time); the eye/neck limits, the shared-hold length and the delight timing reuse the T-114 (e909) lessons.

Beats (docs/tasks/T-117.md; scene frames):
  0-2 s   f1-48     the cup on the table. He is slouched and bored (profile posture, boy_unimpressed), fidgets: he
                    looks off, back at the cup and off again (fidget look_away_and_back). She has her hand at her chin, looking at the cup (girl_chin_think).
  2-4 s   f49-96    she glances at him (partner_acts, source girl); he notices after his own delay (profile 16-26 f:
                    boy_interested), reaches, picks the cup up (pick_up, set a, right hand) and carries it up.
  4-6 s   f97-144   she reacts with wonder (girl_wonder, eyes on the cup); the pass to her left hand, a shared hold
                    long enough for both faces to read (T-116 note 1), release.
  6-8 s   f145-192  her delight (success event: her profile plays girl_delighted = SmileOpen on the candidate face),
                    and his late, reluctant answer (partner_acts: boy_interested, head lift) and a look away.

Cast: the current versions stay boy 2.1.0 / girl 0.12.0 (cast not "current" here: shot-level overrides, evaluation
only). Each character is built from the published CANDIDATE spec (boy 2.2.0 = 2.1.0 + T-109 face r4 + T-113 closed
fit; girl 0.13.0 = 0.12.0 + T-109 face r4 + T-113 closed fit + SmileOpen + T-115) plus the T-118 hair round 5
(groom/4) and the T-121 hands_r2 overrides. Verbs with T-051 / T-112c finger grasps (on with a timing profile).

Gaze (T-120): scene "gazeLegibility" {"rangeDeg": [16, 8]} (both specs' face.eyes.gaze_range_deg), the boy
{"headPitchDeg": 10}; every authored look lasts >= MIN_LOOK frames (lead 3 + turn 8, T-120 open point 2).

Cup grasp (T-185, owner pick 2026-11-21 of T-171 round 3 "fixed, thumb up", variant r3): the pick-up and the pass carry
the opt-in "fingerClose" R3 below, exactly as T-171 measured it (docs/evaluation/interaction/T-171/make_variants.py), on
T-171's proposed cup site: this episode's own copy of the felt cup, episodes/e910_showcase/content/assets (socket grip
at 50 mm, side_a band 0-100 mm; written here from content/assets/felt_cup.asset.json, which is unchanged). The engine
and shot_render.py take the nearest content/assets above the scene, so every e910 shot uses the copy. The same keys go
into the derived shots s010_e1 (T-134) and s010_e23 (T-136): `--derived` patches them in place."""
import copy
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BASE = os.path.join(ROOT, "episodes", "e907_exchange", "shots", "s010_verbs", "shot.scene.json")
OUT = os.path.join(ROOT, "episodes", "e910_showcase", "shots", "s010", "shot.scene.json")
FPS = 24
END = 192
MIN_LOOK = 11  # T-120: leadFrames 3 + turnFrames 8; shorter looks end before the head arrives

CAST = {
    "boy": {"spec": "assets/characters/boy_yellow_hoodie/spec/boy_yellow_hoodie.2.2.0.spec.json",
            "overrides": ["docs/evaluation/characters/T-118/candidates/boy_yellow_hoodie.hair_r5.override.json",
                          "docs/evaluation/characters/T-121/hands_r2.override.json"]},
    "girl": {"spec": "assets/characters/girl_auburn_bun_glasses/spec/girl_auburn_bun_glasses.0.13.0.spec.json",
             "overrides": ["docs/evaluation/characters/T-118/candidates/girl_auburn_bun_glasses.hair_r5.override.json",
                           "docs/evaluation/characters/T-121/hands_r2.override.json"]},
}
GAZE_SCENE = {"rangeDeg": [16, 8]}  # T-120 README "For T-114 (e909) and T-117 (e910)"
GAZE_BOY = {"headPitchDeg": 10}
BORED = 0.18  # boy_unimpressed: its lid stays under personality.py's blink-run threshold (T-114 section 2)
WONDER = 0.7  # her girl_wonder at the lift (profile object_appears intensity)

# beats (scene frames)
B = {
    "chin": 1,            # girl_chin_think: hand at the chin ~f15-30, lowered by ~f63
    "fidget_back": 12,    # he looks back at the cup ...
    "fidget_off": 23,     # ... and off again
    "her_glance": 24,     # she looks up at him (partner_acts for him, salience below his gesture threshold)
    "pick_up": 47,        # after his notice (event + his delay, ~f47); the verb's look phase comes first
    "wonder": 64,         # her wonder as the cup comes up
    "pass": 100,          # he holds it out: the pass starts
    "contact": 114,       # her hand on the cup (pass "contact")
    "release": 136,       # end of the shared hold (22 f)
    "success": 142,       # the cup is hers: her success reaction (girl_delighted)
    "his_answer": 146,    # partner_acts for him: he answers her delight late (his delay)
    "look_away": 176,     # he looks away (reluctant), to the end
}
# No shrug clip (tried mirrored, left arm, at f1 and f126/f144): animcheck measures a clip gesture on the wrist that
# travels furthest in its window, here always his right hand in the pick-up / release verbs, and failed it there
# (onset/stop step). His reluctant answer is the head lift of boy_interested (his late partner_acts reaction).
PICK_SETTLE = 5  # e907 s010_verbs
HER_REACH = 10  # timing.py reference: handover reach >= 10 f (the default start gave 9 f)
CUP_YAW = -45.0  # e907: -75 (see build())

# T-185: T-171 round 3 variant r3 (make_variants.py SEP + R3), key for key. rest = the separated rest hand; wrap = the
# joint-by-joint finger wrap with the measured skin and the seated palm; grip natural = thumb up (the grasp point turns
# about the cup's axis, the elbow is keyed); clear = the way in keeps 6 mm off the cup.
R3_REST = {"curl": 0.25, "thumb": 0.12, "spread": 0.6,
           "fingers": {"index": {"curl": 0.14, "spread": 0.9}, "middle": {"curl": 0.22, "spread": 0.6},
                       "ring": {"curl": 0.29, "spread": 0.6}, "little": {"curl": 0.35, "spread": 0.9}}}
R3 = {"rest": R3_REST, "wrap": True, "grip": "natural", "clear": 0.006}
R3_VERBS = ("pick_up", "pass", "place")  # make_variants.py: every verb of the shot gets the key
CUP_SRC = os.path.join(ROOT, "content", "assets", "felt_cup.asset.json")
CUP_OUT = os.path.join(ROOT, "episodes", "e910_showcase", "content", "assets", "felt_cup.asset.json")
CUP_SITE = {"grip_y": 0.05, "side_a_band": [0.0, 0.1]}  # T-171 proposed site (make_variants.py site_variant)
DERIVED = [os.path.join(ROOT, "episodes", "e910_showcase", "shots", n, "shot.scene.json") for n in ("s010_e1", "s010_e23")]
X_T185 = {"task": "T-185", "fingerClose": R3, "cup_site": CUP_SITE,
          "cup_asset": "episodes/e910_showcase/content/assets/felt_cup.asset.json",
          "measured_by": "docs/evaluation/interaction/T-171/README.md Round 3 (variant r3)"}


def r4(v):
    return [round(x, 4) for x in v]


def apply_r3(shot):
    """T-185: the r3 cup grasp on every verb of the shot (in place)."""
    for x in shot["actions"]:
        if x.get("type") in R3_VERBS:
            x["fingerClose"] = copy.deepcopy(R3)
    shot["x_t185"] = copy.deepcopy(X_T185)
    return shot


def write_cup():
    """This episode's copy of the felt cup with T-171's proposed grasp site. A text copy of the source with the two
    values replaced (so a diff of the two files shows only them), checked against the parsed JSON."""
    text = open(CUP_SRC, encoding="utf-8").read()
    for a, b in (('"translation": [0.04, 0.066, 0.0]', f'"translation": [0.04, {CUP_SITE["grip_y"]}, 0.0]'),
                 ('"band": [0.045, 0.09]', '"band": [{}, {}]'.format(*CUP_SITE["side_a_band"]))):
        if text.count(a) != 1:
            raise SystemExit(f"{CUP_SRC}: expected '{a}' once (the source cup changed: re-check T-171's site)")
        text = text.replace(a, b)
    want = json.load(open(CUP_SRC, encoding="utf-8"))
    want["sockets"]["grip"]["translation"][1] = CUP_SITE["grip_y"]
    next(g for g in want["affordances"]["grasp_sites"] if g["id"] == "side_a")["fingers"]["band"] = CUP_SITE["side_a_band"]
    if json.loads(text) != want:
        raise SystemExit("cup copy: text replacement does not give the intended asset")
    os.makedirs(os.path.dirname(CUP_OUT), exist_ok=True)
    with open(CUP_OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return CUP_OUT


def write(path, shot):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(shot, f, indent=1)
        f.write("\n")
    print(os.path.relpath(path, ROOT))


def build():
    base = json.load(open(BASE, encoding="utf-8"))
    acts = base["actions"]
    pick = next(a for a in acts if a["type"] == "pick_up")
    pass_act = next(a for a in acts if a["type"] == "pass")
    meet = pass_act["at"]
    cup0 = base["props"][0]["transform"]["translation"]
    boy_pos = next(c for c in base["characters"] if c["name"] == "boy")["position"]
    off_side = r4([boy_pos[0] + 1.2, 0.6, boy_pos[2] + 1.0])  # his bored look: away from her (e907 / e909)
    lifted = r4([meet[0] + 0.03, meet[1] + 0.06, meet[2] + 0.03])  # he carries the cup up before holding it out

    shot = {k: copy.deepcopy(base[k]) for k in ("format", "version", "frameRate", "render", "camera", "materials",
                                                 "lights", "objects", "props", "timing")}
    shot["name"] = ("e910_showcase s010: T-117 8 s cup-exchange showcase - he is bored, notices late, picks up the cup "
                    "and passes it; she wonders, takes it and is delighted; he answers late and looks away")
    shot["frameStart"], shot["frameEnd"] = 1, END
    # T-107 note (cup wall visible at the shared hold): at e907's yaw -75 the two grips point at and away from the
    # camera, so his front hand covers the cup; turned to CUP_YAW they spread across the frame
    shot["props"][0]["transform"]["rotationDeg"] = [0, CUP_YAW, 0]
    shot["gazeLegibility"] = GAZE_SCENE
    chars = copy.deepcopy(base["characters"])
    for c in chars:
        if c["name"] == "boy":
            c["gazeLegibility"] = GAZE_BOY
    shot["characters"] = chars
    t = lambda f: round((f - 1) / FPS, 5)  # noqa: E731  (scene frame -> event time)
    shot["events"] = [
        # her look up at him: he notices late (profile delay), interest without a gesture (salience 0.9: 0.7 x 0.9 x
        # his intensity_scale 0.6 = 0.38 < his gesture_min_intensity 0.4)
        {"time": t(B["her_glance"]), "kind": "partner_acts", "name": "she looks at him and the cup", "source": "girl",
         "characters": ["boy"], "salience": 0.9},
        # the cup is hers: her delight (profile success: girl_delighted, SmileOpen)
        {"time": t(B["success"]), "kind": "success", "name": "the cup is passed", "source": "table_top",
         "characters": ["girl"]},
        # her delight: he answers late (profile partner_acts: boy_interested, head lift)
        {"time": t(B["his_answer"]), "kind": "partner_acts", "name": "she is delighted", "source": "girl",
         "characters": ["boy"], "salience": 0.9},
    ]
    a = [
        {"type": "clip", "character": "boy", "clip": "idle_relaxed", "base": True},
        {"type": "clip", "character": "girl", "clip": "idle_relaxed", "base": True},
        # 0-2 s: he is bored, with fidgets; she has her hand at her chin, looking at the cup
        {"type": "emotion", "character": "boy", "name": "boy_unimpressed", "start": 1, "end": B["pick_up"],
         "intensity": BORED},
        {"type": "look", "character": "boy", "start": 1, "end": B["fidget_back"] - 1, "target": off_side},
        {"type": "look", "character": "boy", "start": B["fidget_back"], "end": B["fidget_off"] - 1, "target": r4(cup0)},
        {"type": "look", "character": "boy", "start": B["fidget_off"], "end": B["pick_up"] - 10, "target": off_side},
        {"type": "clip", "character": "girl", "clip": "girl_chin_think", "start": B["chin"]},
        {"type": "look", "character": "girl", "start": 1, "end": B["her_glance"] - 1, "target": r4(cup0)},
        {"type": "look", "character": "girl", "start": B["her_glance"], "end": B["pick_up"] + 4, "atCharacter": "boy"},
        # 2-4 s: his pick-up (verb look, reach, grasp) and carry up
        dict(pick, start=B["pick_up"], settle=PICK_SETTLE),
        {"type": "carry", "character": "boy", "hand": "R", "at": lifted},
        {"type": "look", "character": "girl", "start": B["pick_up"] + 5, "end": B["pass"] - 1, "atProp": "cup"},
        # 4-6 s: her wonder; the pass with a shared hold (both faces read), release
        {"type": "emotion", "character": "girl", "name": "girl_wonder", "start": B["wonder"], "end": B["success"] + 6,
         "intensity": WONDER},
        {"type": "pass", "character": "boy", "hand": "R", "to": "girl", "toHand": "L", "at": meet,
         "start": B["pass"], "receiverStart": B["contact"] - HER_REACH, "contact": B["contact"],
         "release": B["release"]},
        {"type": "look", "character": "boy", "start": B["pass"], "end": B["contact"] + 2, "atProp": "cup"},
        {"type": "look", "character": "boy", "start": B["contact"] + 3, "end": B["release"] + 2, "atCharacter": "girl"},
        {"type": "look", "character": "girl", "start": B["contact"] + 4, "end": B["release"] - 4, "atCharacter": "boy"},
        {"type": "carry", "character": "girl", "hand": "L", "by": [-0.03, 0.03, -0.02]},
        {"type": "look", "character": "girl", "start": B["release"] - 3, "end": B["success"] + 10, "atProp": "cup"},
        # 6-8 s: her delight looking at him; his late reluctant answer (reaction above) and a look away
        {"type": "look", "character": "girl", "start": B["success"] + 11, "end": END, "atCharacter": "boy"},
        {"type": "look", "character": "boy", "start": B["release"] + 3, "end": B["look_away"] - 1, "atProp": "cup"},
        {"type": "look", "character": "boy", "start": B["look_away"], "end": END, "target": off_side},
    ]
    shot["actions"] = a
    shot["production"] = copy.deepcopy(base["production"])
    shot["production"]["cast"] = copy.deepcopy(CAST)
    apply_r3(shot)
    shot["x_t117"] = {
        "task": "T-117", "derived_from": os.path.relpath(BASE, ROOT).replace(os.sep, "/"),
        "staging_from": base["x_t112b_verbs"].get("derived_from", ""), "beats_authored": B, "handover_point": meet,
        "lifted_at": lifted, "cup_table": cup0, "cup_yaw_deg": CUP_YAW, "gaze_legibility": {"scene": GAZE_SCENE, "boy": GAZE_BOY},
        "min_look_frames": MIN_LOOK, "current_versions_unchanged": {"boy": "2.1.0", "girl": "0.12.0"},
        "shot_level_overrides": CAST,
    }
    looks = [x for x in a if x["type"] == "look"]
    short = [x for x in looks if x["end"] - x["start"] + 1 < MIN_LOOK]
    if short:
        raise SystemExit(f"looks shorter than {MIN_LOOK} f: {short}")
    return shot


def main():
    import sys
    print(os.path.relpath(write_cup(), ROOT))
    write(OUT, build())
    if "--derived" in sys.argv:  # s010_e1 / s010_e23: their own keys stay, the r3 grasp is added
        for p in DERIVED:
            write(p, apply_r3(json.load(open(p, encoding="utf-8"))))


main()
