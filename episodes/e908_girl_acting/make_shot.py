"""Writes the T-097-girl solo acting shot episodes/e908_girl_acting/shots/s010/shot.scene.json (python3).

    python3 episodes/e908_girl_acting/make_shot.py

The girl (cast "current": girl_auburn_bun_glasses 0.11.0) alone at a small table with a felt cup, in the watertable
spirit (docs/references/video_watertable.mp4; T-106 measurements, docs/evaluation/animation/T-106/). Explicit
emotion / clip / look actions (T-097D, which schedules reaction plans from scene `events`, is not used yet); the
`events` list is read by tools/animcheck/acting.py (the engine ignores the key).

Beats (scene frames @24, frame 1 = t 0; also written into the shot as x_t097_girl.beats):
  E1  object_appears (the cup)      the event she notices
  notice   E1 + 4      eyes go to the cup (quick 3-frame saccade, head follows): reaction.delay_frames low end
  reaction notice + 2  wonder: emotion girl_wonder (eyes wide, brows up, rounded mouth) and the hand rises to the chin
                       (girl_wonder_point starts); WT [0, 15) hand at chin, eyes wide, mouth rounded
  gesture              leaves the chin (WT [15, 22)), leans in and points down at the cup (WT [22, 39)), holds the point
                       (WT [39, 61)); the rounded mouth closes during the hold (WT f039-f061)
  E2  success (the cup "works")     during the point hold
  delighted E2 + 4     the acting-beat open "delighted" smile (emotion girl_delighted: the model's open Smile preset; the
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

# beats (scene frames)
E1 = 13
NOTICE = E1 + 4
REACT = NOTICE + 2
CLIP = REACT  # girl_wonder_point start
clip_t = lambda c: CLIP + c / TEMPO  # noqa: E731  clip frame -> scene frame
# clip beats (clip frames, girl_beats.py): t1 chin, t2 leave, t3 off, t4 point, t5 hold end, t6 drawn back, t7 straight
T = dict(zip(("t1", "t2", "t3", "t4", "t5", "t6", "t7"), GB.wonder_clip_frames()))
B = {k: round(clip_t(v), 1) for k, v in T.items()}
E2 = int(round(B["t4"] + 12))  # the event arrives during the point hold
DELIGHT = E2 + 4
LOOK_UP = E2 + 6  # a quick glance up to the camera, sharing the delight (invented: WT keeps the eye line low until f081)
END = int(round(B["t7"])) + 25  # WT end hold [96, 121)


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
             "material": "table_mat"}],
        "props": [{"name": "cup", "id": "prop.felt_cup",
                   "transform": {"translation": CUP, "rotationDeg": [0, 0, 0], "scale": [1, 1, 1]}}],
        "characters": [{"name": "girl", "asset": "(set by run_shot)", "position": [0.0, 0.0, 0.0], "yawDeg": 0.0,
                        "personality": "girl_auburn_bun_glasses",
                        # eyes do most of the looking down (WT: eye line low, head only slightly inclined)
                        "life": {"blinkInterval": BLINK_S, "headFollow": 0.35, "gaze": {"assistPitchDeg": 5.0, "assistBodyYawDeg": 0.0}}}],
        "events": [{"time": round((E1 - 1) / 24, 4), "name": "object_appears", "source": "cup"},
                   {"time": round((E2 - 1) / 24, 4), "name": "success", "source": "cup"}],
        "actions": [
            {"type": "clip", "character": "girl", "clip": "idle_relaxed", "base": True},
            # alert, before the event: looking off to her left at eye height
            {"type": "look", "character": "girl", "start": 1, "end": NOTICE - 1, "target": [0.9, 0.72, 1.2]},
            # notice: a quick glance to the cup; the eye line stays low through the point (WT f022-f081)
            {"type": "look", "character": "girl", "start": NOTICE, "end": LOOK_UP - 1, "target": cup_top},
            {"type": "emotion", "character": "girl", "name": "girl_wonder", "start": REACT, "end": int(round(B["t3"])),
             "intensity": 0.7},
            {"type": "clip", "character": "girl", "clip": "girl_wonder_point", "start": CLIP},
            {"type": "emotion", "character": "girl", "name": "girl_delighted", "start": DELIGHT, "end": END - 20, "intensity": 0.9},
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
                                  "E2_success": E2, "delighted": DELIGHT, "look_up": LOOK_UP, "end": END},
                        "reference": "T-106 watertable girl acting beats (docs/evaluation/animation/T-106/performance.csv)"},
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(scene, f, indent=1)
        f.write("\n")
    print(OUT, scene["x_t097_girl"]["beats"])


if __name__ == "__main__":
    main()
