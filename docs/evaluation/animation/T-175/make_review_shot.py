"""T-175 style-review shot: the CMU mocap clips (walk loop, sit down, stand up) on the current boy and auburn girl.

    python3 docs/evaluation/animation/T-175/make_review_shot.py [--no-lock] [--out <dir>]

Writes <out>/shot.scene.json (default: docs/evaluation/animation/T-175/shots/review). One shot, two parts with a hard
camera cut, so the cast is built once:
  frames   1..96   walk: both characters walk left to right past floor stripes (a fixed side-on camera);
  frames 101..230  sit down on a stool, hold, stand up with a small step (3/4 camera).
--no-lock writes the comparison shot: the same clips with the foot-lock switched off (copies of the clips next to the
shot, "style.foot_lock": false), for the before / after numbers.
The seat height comes from each clip's seat contact (height_ratio x the character's leg length, see LEG below)."""
import argparse
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
CLIPS = os.path.join(ROOT, "content", "clips", "mocap")
# Leg lengths (thigh + shin, metres) of the current packages, from their retarget blocks (boy 2.2.0, girl 0.13.0).
LEG = {"boy": 0.2503, "girl": 0.2341}
WALK = (1, 96)
SIT = (104, 230)
STAGE2 = 7.0
CAST = {"boy": "boy_yellow_hoodie", "girl": "girl_auburn_bun_glasses"}


def mat(name, rgb, rough=0.85):
    return {"name": name, "type": "standard", "baseColor": rgb, "roughness": rough, "specular": 0.3}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-lock", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args()
    out = a.out or os.path.join(HERE, "shots", "review_nolock" if a.no_lock else "review")
    os.makedirs(out, exist_ok=True)
    clips = {n: json.load(open(os.path.join(CLIPS, f"{n}.clip.json"))) for n in ("cmu_walk", "cmu_sit_down", "cmu_stand_up")}

    def clip_ref(n):
        if not a.no_lock:
            return {"clip": f"mocap/{n}"}
        c = json.loads(json.dumps(clips[n]))
        c["style"]["foot_lock"] = False
        json.dump(c, open(os.path.join(out, f"{n}_nolock.clip.json"), "w"))
        return {"file": f"../{n}_nolock.clip.json"}  # relative to <shot>/build/shot.resolved.scene.json

    seat_ratio = next(c["height_ratio"] for c in clips["cmu_sit_down"]["contacts"] if c["type"] == "seat")
    sit_root = clips["cmu_sit_down"]["root"]["translation"]["samples"][-1]
    sit_frames = clips["cmu_sit_down"]["frame_count"]
    sit_tempo = clips["cmu_sit_down"]["style"]["tempo"]
    stand_start = SIT[0] + 62
    # Two stages on one floor: the walk at z = 0 (camera at z = 3.4 looking back), the stools at z = STAGE2 behind
    # that camera with their own back wall, so neither part sees the other.
    objects = [{"name": "floor", "kind": "box", "min": [-5, -0.05, -3], "max": [5, 0, STAGE2 + 4], "material": "floor_mat"},
               {"name": "wall", "kind": "box", "min": [-5, 0, -1.6], "max": [5, 3, -1.5], "material": "wall_mat"},
               {"name": "wall2", "kind": "box", "min": [-5, 0, STAGE2 - 1.6], "max": [5, 3, STAGE2 - 1.5], "material": "wall_mat"}]
    for k in range(-12, 13):  # floor stripes every 20 cm: a fixed reference for foot slide
        objects.append({"name": f"stripe{k + 12:02d}", "kind": "box", "min": [k * 0.2 - 0.01, 0.0, -1.2], "max": [k * 0.2 + 0.01, 0.002, 1.0],
                        "material": "stripe_mat"})
    # Part 1 (walk): the characters face +X (yaw 90) and start at the left. Part 2: they stand at x = +-0.45 facing
    # the camera side; position and yaw are keyed with a step at the cut.
    walk_pos = {"boy": [-1.55, 0.0, 0.35], "girl": [-0.75, 0.0, -0.45]}
    sit_pos = {"boy": [-0.45, 0.0, STAGE2], "girl": [0.45, 0.0, STAGE2]}
    sit_yaw = {"boy": 25.0, "girl": -25.0}
    characters, actions, anim = [], [], {}
    import math
    for who in ("boy", "girl"):
        characters.append({"name": who, "asset": "(set by run_shot)", "position": walk_pos[who], "yawDeg": 90, "life": False,
                           "autoIdle": False})
        anim[f"{who}.position"] = [[1, walk_pos[who], "step"], [SIT[0] - 3, sit_pos[who], "step"]]
        anim[f"{who}.yaw"] = [[1, [90, 90, 90], "step"], [SIT[0] - 3, [sit_yaw[who]] * 3, "step"]]
        actions.append({"type": "clip", "character": who, **clip_ref("cmu_walk"), "start": WALK[0], "end": WALK[1] + 4, "blendIn": 0,
                        "blendOut": 0})
        actions.append({"type": "clip", "character": who, "clip": "idle_relaxed", "start": SIT[0] - 3, "end": SIT[0] + 6, "blendIn": 0,
                        "blendOut": 6})
        # The seated clip stays at full weight (no blend-out) until the stand-up above it has blended in: a layer that
        # fades out lets the root rise towards the standing pose before the next one takes over.
        actions.append({"type": "clip", "character": who, **clip_ref("cmu_sit_down"), "start": SIT[0], "end": stand_start + 6,
                        "blendIn": 6, "blendOut": 0})
        actions.append({"type": "clip", "character": who, **clip_ref("cmu_stand_up"), "start": stand_start, "end": SIT[1] + 1,
                        "blendIn": 6, "blendOut": 0})
        # the stool under the seated hips: the clip's last root offset (leg lengths, character space) turned by the yaw
        y = math.radians(sit_yaw[who])
        dx, dz = sit_root[0] * LEG[who], sit_root[2] * LEG[who]
        cx = sit_pos[who][0] + dx * math.cos(y) + dz * math.sin(y)
        cz = sit_pos[who][2] - dx * math.sin(y) + dz * math.cos(y)
        h = seat_ratio * LEG[who]
        objects.append({"name": f"stool_{who}", "kind": "box", "min": [cx - 0.085, 0.0, cz - 0.085], "max": [cx + 0.085, round(h, 4), cz + 0.085],
                        "material": "seat_mat"})
    cam_walk = ([-0.55, 0.45, 3.0], [-0.55, 0.27, 0.0])  # centred on the three cycles the review clip shows
    cam_sit = ([0.75, 0.55, STAGE2 + 2.7], [0.0, 0.3, STAGE2 - 0.05])
    anim["camera.position"] = [[1, cam_walk[0], "step"], [SIT[0] - 3, cam_sit[0], "step"]]
    anim["camera.target"] = [[1, cam_walk[1], "step"], [SIT[0] - 3, cam_sit[1], "step"]]
    scene = {"format": "plush.scene", "version": 1,
             "name": "T-175 review: CMU mocap walk / sit / stand on boy + auburn girl" + (" (foot-lock off)" if a.no_lock else ""),
             "frameRate": [24, 1], "frameStart": 1, "frameEnd": SIT[1],
             # plain clip clock and blends, so measure_feet.py can map scene frames to clip frames exactly
             "animPrinciples": False,
             "render": {"width": 640, "height": 360, "spp": 32, "maxDepth": 8, "exposureEV": 0.3, "denoise": True, "denoiseBlend": 0.85,
                        "clamp": 12},
             "camera": {"position": cam_walk[0], "target": cam_walk[1], "focalMm": 32, "fStop": 0, "focusDistance": -1},
             "materials": [mat("floor_mat", [0.46, 0.44, 0.42]), mat("wall_mat", [0.62, 0.6, 0.55], 0.9),
                           mat("seat_mat", [0.35, 0.5, 0.62], 0.7), mat("stripe_mat", [0.2, 0.2, 0.22], 0.8)],
             "lights": [{"type": "rect", "corner": [-2.0, 1.0, 2.0], "edgeU": [1.2, 0, 0.6], "edgeV": [0, 1.4, 0], "color": [1.0, 0.95, 0.88],
                         "intensity": 3.0},
                        {"type": "rect", "corner": [-2.0, 1.0, STAGE2 + 2.0], "edgeU": [1.2, 0, 0.6], "edgeV": [0, 1.4, 0],
                         "color": [1.0, 0.95, 0.88], "intensity": 3.0},
                        {"type": "sun", "direction": [0.3, -0.6, -0.7], "angleDeg": 4, "color": [1.0, 0.92, 0.82], "intensity": 1.4},
                        {"type": "sky", "color": [0.6, 0.62, 0.66], "intensity": 0.4}],
             "objects": objects, "characters": characters, "actions": actions, "animation": anim,
             "production": {"cast": {w: {"character_id": cid, "version": "current"} for w, cid in CAST.items()},
                            "profile": "pipeline/charsys/rig_profiles/humanoid_rigify.json",
                            "render": {"resolution": [640, 360], "samples": 16, "light_scale": 1.0}},
             "x_t175": {"walk_frames": list(WALK), "sit_frames": list(SIT), "stand_start": stand_start, "foot_lock": not a.no_lock,
                        "sit_clip_scene_frames": round((sit_frames - 1) / sit_tempo, 1)}}
    json.dump(scene, open(os.path.join(out, "shot.scene.json"), "w"), indent=1)
    print(os.path.relpath(os.path.join(out, "shot.scene.json"), ROOT))


main()
