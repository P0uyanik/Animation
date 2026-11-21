"""Writes the T-114 two-character acting shot episodes/e909_two_char_acting/shots/s010/shot.scene.json (python3).

    python3 episodes/e909_two_char_acting/make_shot.py [--candidate]

About 10 s at 24 fps, cast "current", calibrated timing default (no "timing" key, T-104d). The boy and the girl stand
side by side at the small table of e907 (staging, camera, set and hand-over point are read from
episodes/e907_exchange/shots/s010_verbs/shot.scene.json; derivation in episodes/e907_exchange/make_shot.py). The story
uses the T-112 verbs (finger bands, T-112c) and the T-097D scene events; the reactions come from the two personality
profiles:

1. she notices the felt cup on the table (event object_appears, source the table top: a prop is no event source; her profile: girl_wonder + wonder gesture; T-106 WT [0, 39));
2. she picks it up with her inner (left) hand by its far handle (pick_up, set b) and holds it out to him (carry);
3. he is bored: he looks off to his side while she offers; when the pass starts (react: partner_acts) he answers
   late (his profile: 16-26 f notice, boy_interested + boy_reluctant_shrug; T-106 WT [60, 81) late blink + head lift),
   then reaches and takes it by its near handle (pass to his right hand, socket grip);
4. a shared hold long enough for both faces to read (T-116 note), then he holds the cup up and looks at it (carry,
   held look at the object) and sets it down on the table (place);
5. both react: a success event for him (his profile: boy_interested) and her delight beat, then a held look at each
   other (T-116 notes: one clear delight beat, legible gaze).

Current-cast-safe faces (T-113 open point 1: the published masters have no SmileOpen / Pout): her delight is the shared
`happy` (smile) at the place, not girl_delighted, and he is never given boy_reluctant (pout). The girl's success
reaction would play girl_delighted, so the place does not react for her on the current cast: the success event lists
the boy only and her delight is authored. --candidate writes s010_t113 with the T-113 candidate overrides pinned in the
cast (evaluation only) and lets her react to the success event with girl_delighted (SmileOpen).

Gaze (T-113 open point 3, the e908 look drove the eyes past gaze_range during blinks): both characters' eye limits are
set just inside their specs' gaze_range_deg (EYE_YAW, EYE_PITCH); the neck assist takes part of the excess (kept small as in
e907 so the heads stay apart and the faces read) and a far look stops short at the range. The eyes stay inside the
range the lids were fitted for (measured by measure_beats.py, pinned by the test).

Cup grasp (T-188, owner pick 2026-11-21 of T-171 round 3 "fixed, thumb up", variant r3, as T-185 put it on e910): her
pick-up carries the opt-in "fingerClose" R3 below (the same keys as episodes/e910_showcase/make_shot.py R3; T-186's
"r3pick"). Only her pick-up: on the pass and the place the boy's hand goes 22.9 mm through the cup as it opens after the
place (T-185). The cup stays the released content/assets one: T-171's proposed site moves side_a (the boy's side, set
a); her set b is not changed by it (T-185: r3site = r3pick on her rows)."""
import argparse
import copy
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BASE = os.path.join(ROOT, "episodes", "e907_exchange", "shots", "s010_verbs", "shot.scene.json")
OUT = os.path.join(ROOT, "episodes", "e909_two_char_acting", "shots", "{}", "shot.scene.json")
FPS = 24

# Gaze (T-113 open point 3): the eyes stay inside both specs' gaze_range_deg [16 yaw, 8 pitch] (life.gaze max*Deg; the
# engine default is 30 / 25, so e908 drove the eyes 25 deg down during blinks); the neck assist takes the excess.
SPEC_GAZE_RANGE = (16.0, 8.0)  # boy 2.1.0 and girl 0.12.0: face.eyes.gaze_range_deg [yaw, pitch]
SOFT_MARGIN = 1.5  # the engine's eye limit is soft (overshoots up to 1.1 deg here): the limits sit this far inside the range
EYE_YAW, EYE_PITCH = SPEC_GAZE_RANGE[0] - SOFT_MARGIN, SPEC_GAZE_RANGE[1] - SOFT_MARGIN
NECK_YAW = 15.0  # life.gaze.assistYawDeg as e907: more turns the heads into each other (hair touching)
GIRL_NECK_PITCH = 20.0  # life.gaze.assistPitchDeg (e907 10); 35 hid her face at the notice
BOY_NECK_PITCH = 15.0  # looking down at the cup in his hand: more pitch hides his face under his hair
HEAD_FOLLOW = 0.3  # life.headFollow as e907 (0.5 leaned the heads together)
SHARED = 30  # frames of the shared hold (pass release - contact): long enough for his glance up at her (T-116)
END = 286  # 11.9 s
DELIGHT = 0.85  # her `happy` (Smile) at his acceptance, held to the end
BORED = 0.18  # boy_unimpressed: its lid (blink 0.5) stays under personality.py's 0.1 blink run threshold

# beats (scene frames); the verb phases in between are the calibrated profile's
B = {
    "notice_event": 12,      # object_appears; her notice = + her delay (4-6 f)
    "pick_up": 36,           # after the wonder rise and hold (T-106 WT [0, 39) wonder, the reach [22, 39))
    "offer": None,           # carry chains on the pick-up
    "his_glance": 58,        # he glances at the offered cup ...
    "his_look_off": 72,      # ... and looks away again (bored)
    "pass": 88,              # she holds it out to him: the pass starts (his partner_acts event)
    "inspect_hold": 16,      # frames he holds the cup up and looks at it (T-106 PB [125, 132) + 0.79 s hold)
    # read back from the bake (measure_beats.py) and pinned by tests/acting/test_e909_beats.py:
    "his_contact": 133,      # his hand on the grip (pass contact): her delight starts 2 f before (as e907)
    "her_release": 163,      # end of the shared hold (SHARED)
    "place_contact": 221,    # the cup back on the table
    # authored after those:
    "her_look_cup": 192,     # she follows the cup down to the table
    "success": 221,          # success event (the boy reacts: look at the cup on the table, boy_interested)
    "her_look_back": 230,    # then she looks up at him again ...
    "his_look_her": 262,     # ... and he answers with a held look at her (T-116: legible gaze, shared beat)
}
OFFER_AT_DELTA = [0.035, 0.035, 0.03]  # from the hand-over point towards him, up and to the camera: the offered cup
INSPECT_BY = [0.0, 0.1, 0.04]  # his hold: the cup up and a little towards the camera, under his look
# T-188: T-171 round 3 r3 = episodes/e910_showcase/make_shot.py R3, key for key. rest = the separated rest hand; wrap =
# the joint-by-joint finger wrap; grip natural = thumb up; clear = the way in keeps 6 mm off the cup.
R3_REST = {"curl": 0.25, "thumb": 0.12, "spread": 0.6,
           "fingers": {"index": {"curl": 0.14, "spread": 0.9}, "middle": {"curl": 0.22, "spread": 0.6},
                       "ring": {"curl": 0.29, "spread": 0.6}, "little": {"curl": 0.35, "spread": 0.9}}}
R3 = {"rest": R3_REST, "wrap": True, "grip": "natural", "clear": 0.006}
X_T188 = {"task": "T-188", "fingerClose": R3, "on": "girl pick_up only",
          "measured_by": "docs/evaluation/interaction/T-188/README.md"}


def r4(v):
    return [round(x, 4) for x in v]


def build(candidate):
    base = json.load(open(BASE, encoding="utf-8"))
    st = base["x_t112b_verbs"]
    pass_act = next(a for a in base["actions"] if a["type"] == "pass")
    meet = pass_act["at"]
    cup0 = base["props"][0]["transform"]["translation"]
    boy_pos = next(c for c in base["characters"] if c["name"] == "boy")["position"]
    offered = r4([meet[i] + OFFER_AT_DELTA[i] for i in range(3)])
    off_side = r4([boy_pos[0] + 1.2, 0.6, boy_pos[2] + 1.0])  # his bored look: away from her (e907)
    name = "s010_t113" if candidate else "s010"
    shot = {k: copy.deepcopy(base[k]) for k in ("format", "version", "frameRate", "render", "camera", "materials",
                                                 "lights", "objects", "props")}
    shot["name"] = (f"e909_two_char_acting {name}: T-114 two-character acting - she notices the cup, picks it up and "
                    "offers it, he answers late and reluctantly, takes it, looks at it, sets it down; both react")
    shot["frameStart"], shot["frameEnd"] = 1, END
    chars = copy.deepcopy(base["characters"])
    for c in chars:
        c["life"]["headFollow"] = HEAD_FOLLOW
        c["life"]["gaze"].update({"maxLeftDeg": EYE_YAW, "maxRightDeg": EYE_YAW, "maxUpDeg": EYE_PITCH,
                                  "maxDownDeg": EYE_PITCH, "assistYawDeg": NECK_YAW,
                                  "assistPitchDeg": BOY_NECK_PITCH if c["name"] == "boy" else GIRL_NECK_PITCH})
    shot["characters"] = chars
    t = lambda f: round((f - 1) / FPS, 5)  # noqa: E731  (scene frame -> event time)
    shot["events"] = [
        {"time": t(B["notice_event"]), "kind": "object_appears", "name": "she notices the cup", "source": "table_top",
         "characters": ["girl"]},
        {"time": t(B["success"]), "kind": "success", "name": "the cup is back on the table", "source": "table_top",
         "characters": ["boy", "girl"] if candidate else ["boy"]},
    ]
    a = [
        {"type": "clip", "character": "boy", "clip": "idle_relaxed", "base": True},
        {"type": "clip", "character": "girl", "clip": "idle_relaxed", "base": True},
        # he is bored before anything happens: looking off to his side (T-106 PB [0, 32) heavy lids)
        {"type": "look", "character": "boy", "start": 1, "end": B["his_glance"] - 1, "target": off_side},
        {"type": "emotion", "character": "boy", "name": "boy_unimpressed", "start": 1, "end": B["pass"] + 20,
         "intensity": BORED},
        # she: notice (event) -> pick up -> offer -> pass
        {"type": "pick_up", "character": "girl", "hand": "L", "prop": "cup", "set": "b", "start": B["pick_up"],
         "fingerClose": copy.deepcopy(R3)},
        {"type": "carry", "character": "girl", "hand": "L", "at": offered},
        {"type": "look", "character": "girl", "start": B["his_glance"], "end": B["pass"] - 1, "atCharacter": "boy"},
        # he glances at the offer and away again (reluctant)
        {"type": "look", "character": "boy", "start": B["his_glance"], "end": B["his_look_off"] - 1, "target": offered},
        {"type": "look", "character": "boy", "start": B["his_look_off"], "end": B["pass"] - 1, "target": off_side},
        {"type": "pass", "character": "girl", "hand": "L", "to": "boy", "toHand": "R", "toSocket": "grip",
         "start": B["pass"], "at": meet, "react": True,
         "release": B["his_contact"] + SHARED},
        # he holds it up and looks at it, then sets it down where it stood
        {"type": "carry", "character": "boy", "hand": "R", "by": INSPECT_BY, "settle": B["inspect_hold"]},
        {"type": "place", "verb": True, "character": "boy", "hand": "R", "at": r4(cup0), "socket": "place",
         "react": False},
        # her delight beat: he takes it (T-106 PB [255, 289) open smile; current cast: the shared smile, `happy`)
        {"type": "emotion", "character": "girl", "name": "happy", "start": B["his_contact"] - 2, "end": END + 24,
         "intensity": DELIGHT},
        {"type": "look", "character": "girl", "start": B["his_contact"] + 4, "end": B["her_look_cup"] - 1,
         "atCharacter": "boy"},
        # the shared hold: he glances up at her (both faces read, T-116), then back to the cup in his hand
        {"type": "look", "character": "boy", "start": B["his_contact"] + 10, "end": B["his_contact"] + SHARED - 2,
         "atCharacter": "girl"},
        {"type": "look", "character": "girl", "start": B["her_look_cup"], "end": B["her_look_back"] - 1,
         "target": r4(cup0)},
        {"type": "look", "character": "girl", "start": B["her_look_back"], "end": END, "atCharacter": "boy"},
        {"type": "look", "character": "boy", "start": B["his_look_her"], "end": END, "atCharacter": "girl"},
    ]
    shot["actions"] = a
    shot["production"] = copy.deepcopy(base["production"])
    if candidate:  # the girl's current spec + the T-113 candidate override (SmileOpen); the boy stays current
        shot["production"]["cast"]["girl"] = {
            "spec": "assets/characters/girl_auburn_bun_glasses/spec/girl_auburn_bun_glasses.0.12.0.spec.json",
            "overrides": ["docs/evaluation/characters/T-113/candidates/girl_t113.override.json"]}
    shot["x_t114"] = {
        "task": "T-114", "derived_from": os.path.relpath(BASE, ROOT).replace(os.sep, "/"),
        "staging_from": st.get("derived_from", ""), "beats_authored": B, "offered_at": offered,
        "handover_point": meet, "cup_table": cup0, "eye_range_deg": [EYE_YAW, EYE_PITCH],
        "neck_yaw_deg": NECK_YAW, "girl_neck_pitch_deg": GIRL_NECK_PITCH, "boy_neck_pitch_deg": BOY_NECK_PITCH,
        "head_follow": HEAD_FOLLOW, "shared_hold": SHARED, "candidate": candidate,
    }
    shot["x_t188"] = copy.deepcopy(X_T188)
    return name, shot


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate", action="store_true", help="write s010_t113 (T-113 candidate overrides, evaluation)")
    a = ap.parse_args()
    name, shot = build(a.candidate)
    out = OUT.format(name)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(shot, f, indent=1)
        f.write("\n")
    print(os.path.relpath(out, ROOT))


main()
