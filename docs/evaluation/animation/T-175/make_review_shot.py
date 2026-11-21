"""T-175 style-review shot: the CMU mocap clips (walk loop, sit down, stand up) on the current boy and auburn girl.

    python3 docs/evaluation/animation/T-175/make_review_shot.py [--no-lock] [--out <dir>] [--seat-from <bake.json>]

Writes <out>/shot.scene.json (default: docs/evaluation/animation/T-175/shots/review). One shot, two parts with a hard
camera cut, so the cast is built once:
  frames   1..96   walk: both characters walk left to right past floor stripes (a fixed side-on camera);
  frames 101..230  stand, sit down on a stool, hold, stand up on the spot, stand (3/4 camera).
--no-lock writes the comparison shot: the same clips with the foot-lock switched off (copies of the clips next to the
shot, "style.foot_lock": false), for the before / after numbers.
--seat-from: an engine bake of this shot; the stools are then placed under the seated hips at the height of the lowest
seated point of the pelvis (body and garments). Without it the seat height is the clip's seat contact estimate
(height_ratio x the character's leg length, see LEG below).
The characters stand ON the floor: their scene position is raised by SOLE, the depth of their shoe soles under the
character origin in the rest pose (the current packages rest 27 / 30 mm under their origin)."""
import argparse
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
CLIPS = os.path.join(ROOT, "content", "clips", "mocap")
# Leg lengths (thigh + shin, metres) of the current packages, from their retarget blocks (boy 2.2.0, girl 0.13.0).
LEG = {"boy": 0.2503, "girl": 0.2341}
# Lowest rest vertex of the shoes under the character origin (metres), current packages (boy 2.3.0, girl 0.14.0).
SOLE = {"boy": 0.0271, "girl": 0.0295}
WALK = (1, 96)
SIT = (104, 230)
STAGE2 = 7.0
CAST = {"boy": "boy_yellow_hoodie", "girl": "girl_auburn_bun_glasses"}


def mat(name, rgb, rough=0.85):
    return {"name": name, "type": "standard", "baseColor": rgb, "roughness": rough, "specular": 0.3}


def seat_boxes(bake_path, frame):
    """{character: (min, max)} of a stool under each seated character at `frame` of an engine bake: its top is the
    lowest point of the vertices the pelvis carries (body and garments), it reaches from behind the pelvis to just
    behind the heels and is as wide as the pelvis plus a hand on each side."""
    import numpy as np
    sys.path.insert(0, os.path.join(ROOT, "tools", "motion_checks"))
    import shot as SHOT
    sh = SHOT.Shot(bake_path)
    i = list(sh.frames).index(frame)
    out = {}
    for ch in sh.characters:
        names = [b["name"] for b in ch.doc["skeleton"]]
        hips = names.index("hips")
        pts = []
        for mi in range(len(ch.doc["meshes"])):
            P, N, J, W = ch.rest(mi)
            sel = np.nonzero(J[np.arange(len(J)), W.argmax(1)] == hips)[0]
            if len(sel):
                pts.append(ch.skin(mi, sel, with_morphs=False)[0][i])
        pts = np.concatenate(pts)
        piv = ch.pivots()[i]
        hp = piv[ch.bones.index("hips")]
        knees = [piv[ch.bones.index(f"shin.{s}")] for s in "LR"]
        fwd = (knees[0] + knees[1]) / 2 - hp
        fwd[1] = 0
        fwd /= np.linalg.norm(fwd)
        side = np.array([fwd[2], 0, -fwd[0]])
        half = float(np.abs((pts - hp) @ side).max()) + 0.05
        back = float(((pts - hp) @ fwd).min()) - 0.02
        # the lower legs are tucked back under the knees: the seat ends behind the heels
        heels = min(float((piv[ch.bones.index(f"foot.{s}")] - hp) @ fwd) for s in "LR")
        front = min(float(((knees[0] + knees[1]) / 2 - hp) @ fwd) - 0.035, heels - 0.075)
        top = float(np.percentile(pts[:, 1], 2))
        c = [hp + fwd * u + side * v for u in (back, front) for v in (-half, half)]
        lo = [min(p[0] for p in c), 0.0, min(p[2] for p in c)]
        hi = [max(p[0] for p in c), top, max(p[2] for p in c)]
        out[ch.name] = (lo, hi)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-lock", action="store_true")
    ap.add_argument("--out")
    ap.add_argument("--seat-from")
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
    stand_frames = clips["cmu_stand_up"]["frame_count"]
    stood = stand_start + int(math.ceil((stand_frames - 1) / clips["cmu_stand_up"]["style"]["tempo"])) + 2
    seats = seat_boxes(a.seat_from, SIT[0] + 45) if a.seat_from else {}
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
    walk_pos = {"boy": [-1.55, SOLE["boy"], 0.35], "girl": [-0.75, SOLE["girl"], -0.45]}
    sit_pos = {"boy": [-0.45, SOLE["boy"], STAGE2], "girl": [0.45, SOLE["girl"], STAGE2]}
    sit_yaw = {"boy": 25.0, "girl": -25.0}
    characters, actions, anim = [], [], {}
    for who in ("boy", "girl"):
        characters.append({"name": who, "asset": "(set by run_shot)", "position": walk_pos[who], "yawDeg": 90, "life": False,
                           "autoIdle": False})
        anim[f"{who}.position"] = [[1, walk_pos[who], "step"], [SIT[0] - 3, sit_pos[who], "step"]]
        anim[f"{who}.yaw"] = [[1, [90, 90, 90], "step"], [SIT[0] - 3, [sit_yaw[who]] * 3, "step"]]
        actions.append({"type": "clip", "character": who, **clip_ref("cmu_walk"), "start": WALK[0], "end": WALK[1] + 4, "blendIn": 0,
                        "blendOut": 0})
        # Stand (idle), sit down, hold, stand up, stand (idle). The feet stay where they stand ("foot_home"). The
        # seated clip stays at full weight (no blend-out) until the stand-up above it has blended in; the stand-up
        # starts on the sit-down's last pose (the same frames played backwards).
        actions.append({"type": "clip", "character": who, "clip": "idle_relaxed", "start": SIT[0] - 3, "end": SIT[0] + 8, "blendIn": 0,
                        "blendOut": 8})
        actions.append({"type": "clip", "character": who, **clip_ref("cmu_sit_down"), "start": SIT[0], "end": stand_start + 6,
                        "blendIn": 8, "blendOut": 0})
        actions.append({"type": "clip", "character": who, **clip_ref("cmu_stand_up"), "start": stand_start, "end": SIT[1] + 1,
                        "blendIn": 6, "blendOut": 0})
        actions.append({"type": "clip", "character": who, "clip": "idle_relaxed", "start": stood, "end": SIT[1] + 1, "blendIn": 10,
                        "blendOut": 0})
        if who in seats:
            lo, hi = seats[who]
        else:  # the clip's last root offset (leg lengths, character space) turned by the yaw; an estimated height
            y = math.radians(sit_yaw[who])
            dx, dz = sit_root[0] * LEG[who], sit_root[2] * LEG[who]
            cx = sit_pos[who][0] + dx * math.cos(y) + dz * math.sin(y)
            cz = sit_pos[who][2] - dx * math.sin(y) + dz * math.cos(y)
            lo, hi = [cx - 0.1, 0.0, cz - 0.1], [cx + 0.1, seat_ratio * LEG[who], cz + 0.1]
        objects.append({"name": f"stool_{who}", "kind": "box", "min": [round(v, 4) for v in lo], "max": [round(v, 4) for v in hi],
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
