"""Writes the T-097-girl solo acting shot episodes/e908_girl_acting/shots/s010/shot.scene.json (python3).

    python3 episodes/e908_girl_acting/make_shot.py

The girl (cast "current": girl_auburn_bun_glasses 0.11.0) alone at a small table with a felt cup, in the watertable
spirit (docs/references/video_watertable.mp4; T-106 measurements, docs/evaluation/animation/T-106/). Explicit
The reactions come from the scene `events` (T-097D: each event is planned by the reaction planner from the girl's
profile, content/personality/girl_auburn_bun_glasses.json reaction.events, and played as a look, a blended emotion and
her preferred gesture clip). Authored here only what the planner cannot produce: the opening look off to her left, the
sustained watch of the cup while she points (a planned look lasts at most its reaction), and the glance up to the
camera at the success (a scene event without a source plays no look). The cup is a prop and the planner looks only at
characters and scene objects, so the event's source is `cup_spot`, a small box standing inside the cup (hidden by
its wall).

Beats (scene frames @24, frame 1 = t 0; also written into the shot as x_t097_girl.beats):
  E1  object_appears (the cup)      the event she notices
  notice   E1 + 4.5    planned: look at the cup (head follows), emotion girl_wonder (eyes wide, brows up, rounded mouth),
                       gesture girl_wonder_point (the hand rises to the chin); delay = mid reaction.delay_frames x
                       tempo_scale, never under delay_frames[0]; WT [0, 15) hand at chin, eyes wide, mouth rounded
  gesture              leaves the chin (WT [15, 22)), leans in and points down at the cup (WT [22, 39)), holds the point
                       (WT [39, 61)); the rounded mouth closes during the hold (WT f039-f061)
  E2  success (the cup "works")     during the point hold
  delighted E2 + 4.5   planned: the acting-beat open "delighted" smile (emotion girl_delighted: the model's open Smile preset; the
                       rest face stays the modelled closed smile and returns after the beat)
  look up  E2 + 6      a quick glance up to the camera, sharing the delight, while she still points (invented: WT keeps
                       the eye line low until f081); she straightens into the higher, forward head pose (WT [81, 96))
  end hold             upright, arms down (WT [96, 121), 25 f); the open smile releases into the closed rest smile
Clip timing: girl_wonder_point is authored at WT durations x 1.1 and plays at her tempo 1.1 (make_girl_clips.py)."""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import girl_beats as GB  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "episodes", "e908_girl_acting", "shots", "s010", "shot.scene.json")
TEMPO = GB.TEMPO

# staging (engine axes: metres, +Y up, she faces +Z; her right is -X)
TABLE = {"min": [-0.15, 0.0, 0.12], "max": [0.15, 0.40, 0.52]}  # top at 0.40 m: below her elbows (hips 0.30 m)
CUP = [-0.06, 0.40, 0.31]  # where her right index points: replaced by clip_calibration.json "cup" (calibrate_clips.py)
_cal = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clip_calibration.json")
if os.path.isfile(_cal) and "cup" in json.load(open(_cal)):
    CUP = json.load(open(_cal))["cup"]
CAMERA_AZ, CAMERA_ELEV, CAMERA_DIST = 24.0, 7.0, 1.45  # from her left front, a little above (WT three-quarter): the pointing arm is in front of her, the face stays readable when she leans in
CAMERA_TARGET = [-0.02, 0.62, 0.10]
FOCAL = 40.0
BLINK_S = math.floor(40 / 24 * 1e4) / 1e4  # T-106 watertable girl: 35.7 blinks per visible minute = one per 40 f (inside limits.blink_interval_frames)

PROFILE = json.load(open(os.path.join(ROOT, "content", "personality", "girl_auburn_bun_glasses.json")))
_r = PROFILE["reaction"]
# the planned notice delay (frames@24): mid delay_frames x tempo_scale, never under delay_frames[0] (T-097D)
DELAY = max(sum(_r["delay_frames"]["value"]) / 2 * _r.get("tempo_scale", {}).get("value", 1.0), _r["delay_frames"]["value"][0])

# beats (scene frames)
E1 = 13
NOTICE = E1 + DELAY
REACT = NOTICE  # the planned emotion and gesture start with the look
CLIP = REACT  # girl_wonder_point start (the profile's preferred object_appears gesture)
clip_t = lambda c: CLIP + c / TEMPO  # noqa: E731  clip frame -> scene frame
# clip beats (clip frames, girl_beats.py): t1 chin, t2 leave, t3 off, t4 point, t5 hold end, t6 drawn back, t7 straight
T = dict(zip(("t1", "t2", "t3", "t4", "t5", "t6", "t7"), GB.wonder_clip_frames()))
B = {k: round(clip_t(v), 1) for k, v in T.items()}
E2 = int(round(B["t4"] + 12))  # the event arrives during the point hold
DELIGHT = E2 + DELAY
LOOK_UP = E2 + 6  # a quick glance up to the camera, sharing the delight (invented: WT keeps the eye line low until f081)
END = math.ceil(B["t7"]) + 25  # WT end hold [96, 121)
WATCH = int(B["t2"])  # the authored watch takes over from the planned look as she leaves the chin


def planned_reactions(events):
    """The actions T-097D plays for the girl's events (engine/scene/actions.cpp planReactionActions, her profile, salience
    1): a look at an object source held gaze_shift x the reaction length, the blended emotion released after the length
    plus the emotion's decay, the first preferred gesture. Recorded in the shot (x_t097_girl.planned_reactions) so tools
    that read scene actions (tools/animcheck, tests/acting) can check the scene as it plays; the engine computes its own."""
    out = []
    tempo, hold = _r.get("tempo_scale", {}).get("value", 1.0), _r.get("hold_scale", {}).get("value", 1.0)
    for e in events:
        p = _r["events"]["value"][e["kind"]]
        start = 1 + (e["time"] + DELAY / 24) * 24
        length = p["duration_s"] * tempo * hold * 24
        if e["source"]:
            out.append({"type": "look", "character": "girl", "start": round(start, 3),
                        "end": round(start + max(3.0, p["gaze_shift"] * length), 3), "back": True, "object": e["source"]})
        emo = json.load(open(os.path.join(ROOT, "content", "emotions", p["emotion"] + ".emotion.json")))
        decay = emo.get("blend", {}).get("decay", emo["timing"]["release"])
        out.append({"type": "emotion", "character": "girl", "name": p["emotion"], "start": round(start, 3),
                    "end": round(start + length + decay * 24, 3), "intensity": p["intensity"], "blend": True})
        if p.get("gestures"):
            out.append({"type": "clip", "character": "girl", "clip": p["gestures"][0], "start": round(start, 3)})
    return out


def camera():
    a, e = math.radians(CAMERA_AZ), math.radians(CAMERA_ELEV)
    d = [math.sin(a) * math.cos(e), math.sin(e), math.cos(a) * math.cos(e)]
    return {"position": [round(CAMERA_TARGET[i] + CAMERA_DIST * d[i], 4) for i in range(3)], "target": CAMERA_TARGET,
            "focalMm": FOCAL, "fStop": 0, "focusDistance": -1}


def main():
    base = json.load(open(os.path.join(ROOT, "episodes", "e907_exchange", "shots", "s010", "shot.scene.json")))
    cup_top = [CUP[0], CUP[1] + 0.05, CUP[2]]
    scene = {
        "format": "plush.scene", "version": 1,
        "name": "e908_girl_acting s010: T-097-girl solo acting - notice, wonder (hand to chin), point, delighted hold",
        "frameRate": [24, 1], "frameStart": 1, "frameEnd": END,
        "render": base["render"], "camera": camera(),
        "materials": base["materials"], "lights": base["lights"],
        "objects": [o for o in base["objects"] if o["name"] in ("floor", "wall")] + [
            {"name": "table_top", "kind": "box", "min": [TABLE["min"][0], TABLE["max"][1] - 0.03, TABLE["min"][2]],
             "max": TABLE["max"], "material": "table_mat"},
            {"name": "table_leg", "kind": "box", "min": [-0.02, 0.0, 0.30], "max": [0.02, TABLE["max"][1] - 0.03, 0.34],
             "material": "table_mat"},
            # the event source for the planned look: a small box inside the cup, on its floor (hidden by the felt wall)
            {"name": "cup_spot", "kind": "box", "min": [CUP[0] - 0.015, CUP[1] + 0.002, CUP[2] - 0.015],
             "max": [CUP[0] + 0.015, CUP[1] + 0.032, CUP[2] + 0.015], "material": "table_mat"}],
        "props": [{"name": "cup", "id": "prop.felt_cup",
                   "transform": {"translation": CUP, "rotationDeg": [0, 0, 0], "scale": [1, 1, 1]}}],
        "characters": [{"name": "girl", "asset": "(set by run_shot)", "position": [0.0, 0.0, 0.0], "yawDeg": 0.0,
                        "personality": "girl_auburn_bun_glasses",
                        # eyes do most of the looking down (WT: eye line low, head only slightly inclined)
                        "life": {"blinkInterval": BLINK_S, "headFollow": 0.35, "gaze": {"assistPitchDeg": 5.0, "assistBodyYawDeg": 0.0}}}],
        "events": [{"time": round((E1 - 1) / 24, 4), "kind": "object_appears", "name": "object_appears", "source": "cup_spot",
                    "characters": ["girl"]},
                   {"time": round((E2 - 1) / 24, 4), "kind": "success", "name": "success", "source": "", "characters": ["girl"]}],
        "actions": [
            {"type": "clip", "character": "girl", "clip": "idle_relaxed", "base": True},
            # alert, before the event: looking off to her left at eye height
            {"type": "look", "character": "girl", "start": 1, "end": NOTICE - 1, "target": [0.9, 0.72, 1.2]},
            # (the notice look, girl_wonder and girl_wonder_point are planned from the object_appears event)
            # the eye line stays low on the cup while she points (WT f022-f081), after the planned look
            {"type": "look", "character": "girl", "start": WATCH, "end": LOOK_UP - 1, "target": cup_top},
            # (girl_delighted is planned from the success event)
            # a quick glance up, sharing the delight; she straightens into the higher, forward head pose (WT [81, 96))
            {"type": "look", "character": "girl", "start": LOOK_UP, "end": END, "camera": True},
        ],
        "production": {"cast": {"girl": {"character_id": "girl_auburn_bun_glasses", "version": "current"}},
                       "profile": "pipeline/charsys/rig_profiles/humanoid_rigify.json",
                       "render": {"resolution": [640, 360], "samples": 16, "light_scale": 1.0}},
        "x_t097_girl": {"generator": "episodes/e908_girl_acting/make_shot.py",
                        "beats": {"E1_object_appears": E1, "notice": NOTICE, "reaction": REACT, "clip_start": CLIP,
                                  "chin": B["t1"], "leave_chin": B["t2"], "point_start": B["t3"], "point": B["t4"],
                                  "point_hold_end": B["t5"], "drawn_back": B["t6"], "straight": B["t7"],
                                  "E2_success": E2, "delighted": DELIGHT, "watch": WATCH, "look_up": LOOK_UP, "end": END},
                        "planned_reactions": None,
                        "reference": "T-106 watertable girl acting beats (docs/evaluation/animation/T-106/performance.csv)"},
    }
    scene["x_t097_girl"]["planned_reactions"] = planned_reactions(scene["events"])
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(scene, f, indent=1)
        f.write("\n")
    print(OUT, scene["x_t097_girl"]["beats"])


if __name__ == "__main__":
    main()
