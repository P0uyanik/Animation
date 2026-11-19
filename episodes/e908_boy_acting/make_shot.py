"""Writes the T-097-boy solo acting shot episodes/e908_boy_acting/shots/s010/shot.scene.json (python3).

    python3 episodes/e908_boy_acting/make_shot.py

7.5 s at 24 fps, cast "current" (boy_yellow_hoodie 2.0.0 today), personality profile on. The boy stands at a small
table and watches a felt cup on it, bored (heavy lids, head down; T-106 PB [0, 32), WT [0, 27)). An off-screen partner
points at the cup (scene `events`: partner_acts). He keeps the same watch for a long beat and only then answers:
a blink and a short sidelong glance with the eyes, his lids lift and his head comes up a little with a small roll
(boy_interested), then a small, slow, reluctant shrug, and he holds the raised head to the end. Calibrated on T-106
WT (docs/evaluation/animation/T-106/performance.csv, boy rows), the moment the girl points beside him:

  WT (frames)          what he does                                   here (scene frames)
  [0, 27)              leans, brows low, mouth nearly closed          f1 .. EVENT: bored hold
  f39                  the girl's point arrives (reach [22, 39))      EVENT (partner_acts)
  [27, 60)             holds the same sidelong watch (33 f)           EVENT .. NOTICE (DELAY = 21 f)
  [60, 68) blink, [60, 81) head lifts 29 px, 5 deg roll (21 f)        NOTICE: blink, glance, boy_interested rise 21 f
  [81, 87) blink during the settle                                    (life blinks)
  [87, 121) holds the raised head, small closed mouth (34 f)          end hold after the shrug (END_HOLD = 34 f)
  (no gesture shown)                                                  GESTURE: boy_reluctant_shrug (extrapolation)

The reaction is generated from the scene `events` (T-097D): the planner reads the profile (reaction.delay_frames
middle 21 f, events.partner_acts: boy_interested at 0.7 x intensity_scale 0.6, duration, boy_reluctant_shrug, whose
rest lead holds the reluctant beat). The event has no source (the partner is off screen, so there is nothing to look
at); the blink and the short sidelong glance at the notice are authored, as the reference shows them."""
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "episodes", "e908_boy_acting", "shots", "s010", "shot.scene.json")
PROFILE = json.load(open(os.path.join(ROOT, "content", "personality", "boy_yellow_hoodie.json")))
REACTION = PROFILE["reaction"]
PARTNER = REACTION["events"]["value"]["partner_acts"]
SHRUG = json.load(open(os.path.join(ROOT, "content", "clips", "boy_reluctant_shrug.clip.json")))
CUP = json.load(open(os.path.join(ROOT, "content", "assets", "felt_cup.asset.json")))

FPS = 24
F0 = 1
EVENT = 30          # partner_acts: the off-screen point arrives
DELAY = 21          # T-106 WT f39 -> f60
NOTICE = EVENT + DELAY
BLINK_F = 5         # explicit blink at the notice (T-106 WT [60, 68) envelope 8 f incl. partly closed frames; engine 5-6 f)
GLANCE_F = 11       # sidelong glance, eyes only, <= 12 f (REFERENCE_BEHAVIOUR.md section 7)
RISE_F = 21         # boy_interested onset 0.875 s (T-106 WT [60, 81))
SETTLE_F = 10       # head lift settles before the gesture (T-104 settle 8-18 f)
GESTURE = NOTICE + RISE_F + SETTLE_F  # the arm leaves rest here (the shrug clip's rest lead, make_clips.py LEAD_F)
GESTURE_BLEND_OUT = 6  # the generated clip action's default blend
END_HOLD = 34       # T-106 WT [87, 121)
MOTION_END = NOTICE + SHRUG["frame_count"] - SHRUG.get("x_rest_tail_frames", 0)  # the arm is back at rest
END = MOTION_END + GESTURE_BLEND_OUT + END_HOLD

TABLE_TOP = 0.4695
TABLE = {"min": [-0.12, 0.4395, 0.2], "max": [0.16, TABLE_TOP, 0.44]}
CUP_POS = [0.05, TABLE_TOP, 0.32]            # in front of him, a little to his left (+x is his left)
PARTNER_HEAD = [-1.3, 0.85, 0.55]            # off screen, beside him on the camera side
HEAD = [0.0, 0.7, 0.0]                        # head bone of the current package (e907 DEFAULT_RIG)


def lerp(a, b, t):
    return [round(x + (y - x) * t, 4) for x, y in zip(a, b)]


def main():
    cup_top = [CUP_POS[0], CUP_POS[1] + 0.05, CUP_POS[2]]
    glance = lerp(cup_top, PARTNER_HEAD, PARTNER["gaze_shift"] if "gaze_shift" in PARTNER else 0.3)
    t_event = (EVENT - F0) / FPS
    scene = {
        "format": "plush.scene", "version": 1,
        "name": "e908_boy_acting s010: T-097-boy solo acting - bored watch, late interest, reluctant shrug, hold",
        "frameRate": [FPS, 1], "frameStart": F0, "frameEnd": END,
        "render": {"width": 640, "height": 360, "spp": 32, "maxDepth": 8, "exposureEV": 0.3, "denoise": True,
                   "denoiseBlend": 0.85, "clamp": 12},
        "camera": {"position": [-0.42, 0.86, 1.75], "target": [0.0, 0.7, 0.12], "focalMm": 40.0, "fStop": 0,
                   "focusDistance": -1},
        "materials": [
            {"name": "floor_mat", "type": "standard", "baseColor": [0.46, 0.44, 0.42], "roughness": 0.85, "specular": 0.3},
            {"name": "wall_mat", "type": "standard", "baseColor": [0.62, 0.6, 0.55], "roughness": 0.9, "specular": 0.3},
            {"name": "table_mat", "type": "standard", "baseColor": [0.42, 0.3, 0.2], "roughness": 0.7, "specular": 0.3}],
        "lights": [
            {"type": "rect", "corner": [-2.0, 1.0, 2.0], "edgeU": [1.2, 0, 0.6], "edgeV": [0, 1.4, 0],
             "color": [1.0, 0.95, 0.88], "intensity": 3.0},
            {"type": "sun", "direction": [0.3, -0.6, -0.7], "angleDeg": 4, "color": [1.0, 0.92, 0.82], "intensity": 1.4},
            {"type": "sky", "color": [0.6, 0.62, 0.66], "intensity": 0.4}],
        "objects": [
            {"name": "floor", "kind": "box", "min": [-4, -0.05, -3], "max": [4, 0, 4], "material": "floor_mat"},
            {"name": "wall", "kind": "box", "min": [-4, 0, -1.4], "max": [4, 3, -1.3], "material": "wall_mat"},
            {"name": "table_top", "kind": "box", "min": TABLE["min"], "max": TABLE["max"], "material": "table_mat"},
            {"name": "table_leg", "kind": "box", "min": [0.0, 0.0, 0.3], "max": [0.04, 0.4395, 0.34],
             "material": "table_mat"}],
        "props": [{"name": "cup", "id": CUP["id"],
                   "transform": {"translation": CUP_POS, "rotationDeg": [0, -30.0, 0], "scale": [1, 1, 1]}}],
        "characters": [{"name": "boy", "asset": "(set by run_shot)", "position": [0.0, 0.0, 0.0], "yawDeg": -12.0,
                        "personality": "boy_yellow_hoodie",
                        "life": {"headFollow": 0.3, "gaze": {"assistYawDeg": 15.0, "assistBodyYawDeg": 0.0}}}],
        "events": [{"time": round(t_event, 5), "kind": "partner_acts", "name": "partner points (off screen)", "source": ""}],
        "actions": [
            {"type": "clip", "character": "boy", "clip": "idle_relaxed", "base": True},
            {"type": "look", "character": "boy", "start": F0, "end": NOTICE - 1, "target": cup_top},
            {"type": "expression", "character": "boy", "name": "blink", "start": NOTICE, "end": NOTICE + BLINK_F,
             "weight": 1.0, "ramp": 2},
            {"type": "look", "character": "boy", "start": NOTICE, "end": NOTICE + GLANCE_F, "target": glance},
            {"type": "look", "character": "boy", "start": NOTICE + GLANCE_F + 1, "end": END, "target": cup_top}],
        "production": {"cast": {"boy": {"character_id": "boy_yellow_hoodie", "version": "current"}},
                       "profile": "pipeline/charsys/rig_profiles/humanoid_rigify.json",
                       "render": {"resolution": [640, 360], "samples": 16, "light_scale": 1.0}},
        "x_t097boy_staging": {
            "beats": {"event": EVENT, "notice": NOTICE, "delay_frames": DELAY, "blink": [NOTICE, NOTICE + BLINK_F],
                      "glance": [NOTICE, NOTICE + GLANCE_F], "rise_end": NOTICE + RISE_F, "gesture": GESTURE,
                      "gesture_end": MOTION_END, "end_hold": [END - END_HOLD, END], "end": END},
            "reference": "docs/evaluation/animation/T-106/performance.csv (watertable, boy rows)",
            "reaction": "generated from events (T-097D) with profile reaction.events.partner_acts; blink and glance authored"},
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(scene, f, indent=1)
        f.write("\n")
    print("wrote", os.path.relpath(OUT, ROOT), "frames", F0, "-", END, scene["x_t097boy_staging"]["beats"])


if __name__ == "__main__":
    main()
