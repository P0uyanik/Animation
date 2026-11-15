"""Writes the T-002 clip test shot episodes/e901_clip_test/shots/s010/shot.scene.json (python3).

    python3 pipeline/clips/make_test_shot.py --boy-package <pkg dir> --girl-package <pkg dir>

Both characters use the shared clips (no per-character clip data): base idle_relaxed for the whole shot, wave (the
girl mirrored to her left arm), point, the boy walking while waving and looking at the camera, the girl reaching for
a cup with her right hand while her right-arm point clip is active (IK keeps priority), sit_down onto a box and
stand_up. Seat boxes: top height = the sit_down clip's seat contact ratio (clip data) x each character's leg length
(its package retarget data); placed under the seated root offset (clip root motion x leg length). The numbers are
written into the shot file (a shot is data); this script only documents how they were derived."""
import argparse
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "episodes", "e901_clip_test", "shots", "s010", "shot.scene.json")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--boy-package", required=True)
    ap.add_argument("--girl-package", required=True)
    a = ap.parse_args()
    sit = json.load(open(os.path.join(ROOT, "content", "clips", "sit_down.clip.json")))
    seat = next(c for c in sit["contacts"] if c["type"] == "seat")
    rk = sit["root"]["translation"]["keys"][-1]  # seated root offset (x, y, z) / leg length
    leg = {n: json.load(open(os.path.join(p, "character.json")))["retarget"]["leg_length"]
           for n, p in (("boy", a.boy_package), ("girl", a.girl_package))}
    place = {"boy": (-0.36, 0.0), "girl": (0.34, 0.0)}
    objects = [{"name": "floor", "kind": "box", "min": [-4, -0.05, -3], "max": [4, 0, 4], "material": "floor_mat"},
               {"name": "wall", "kind": "box", "min": [-4, 0, -1.4], "max": [4, 3, -1.3], "material": "wall_mat"}]
    derived = {}
    for n in ("boy", "girl"):
        x, z = place[n]
        top = seat["height_ratio"] * leg[n]
        zc = z + rk[3] * leg[n]  # seated pelvis position (behind the standing position)
        objects.append({"name": f"seat_{n}", "kind": "box", "min": [round(x - 0.1, 4), 0.0, round(zc - 0.09, 4)],
                        "max": [round(x + 0.1, 4), round(top, 4), round(zc + 0.05, 4)], "material": "seat_mat"})
        derived[n] = {"leg_length": leg[n], "seat_top": round(top, 4), "seat_centre_z": round(zc, 4)}
    # a cup on a pedestal within the girl's right-hand reach (boxes are static in bake v1: the reach uses no lift)
    objects.append({"name": "pedestal", "kind": "box", "min": [0.17, 0.0, 0.1], "max": [0.25, 0.4, 0.18], "material": "seat_mat"})
    objects.append({"name": "cup", "kind": "box", "min": [0.2, 0.4, 0.13], "max": [0.225, 0.43, 0.155], "material": "cup_mat",
                    "position": [0.2125, 0.415, 0.1425]})
    shot = {
        "format": "plush.scene", "version": 1,
        "name": "e901_clip_test s010: shared clips on two characters (technical validation)",
        "frameRate": [30, 1], "frameStart": 1, "frameEnd": 440,
        "render": {"width": 640, "height": 360, "spp": 32, "maxDepth": 8, "exposureEV": 0.3, "denoise": True, "denoiseBlend": 0.85, "clamp": 12},
        "camera": {"position": [0.0, 0.55, 2.3], "target": [0.0, 0.38, 0.0], "focalMm": 32, "fStop": 0, "focusDistance": -1},
        "materials": [{"name": "floor_mat", "type": "standard", "baseColor": [0.46, 0.44, 0.42], "roughness": 0.85, "specular": 0.3},
                      {"name": "wall_mat", "type": "standard", "baseColor": [0.62, 0.6, 0.55], "roughness": 0.9, "specular": 0.3},
                      {"name": "seat_mat", "type": "standard", "baseColor": [0.35, 0.5, 0.62], "roughness": 0.7, "specular": 0.3},
                      {"name": "cup_mat", "type": "standard", "baseColor": [0.85, 0.3, 0.25], "roughness": 0.5, "specular": 0.4}],
        "lights": [{"type": "rect", "corner": [-2.0, 1.0, 2.0], "edgeU": [1.2, 0, 0.6], "edgeV": [0, 1.4, 0], "color": [1.0, 0.95, 0.88], "intensity": 3.0},
                   {"type": "sun", "direction": [0.3, -0.6, -0.7], "angleDeg": 4, "color": [1.0, 0.92, 0.82], "intensity": 1.4},
                   {"type": "sky", "color": [0.6, 0.62, 0.66], "intensity": 0.4}],
        "objects": objects,
        "characters": [{"name": "boy", "asset": "(set by run_shot)", "position": [-0.75, 0.0, 0.0], "yawDeg": 0, "life": True},
                       {"name": "girl", "asset": "(set by run_shot)", "position": [place["girl"][0], 0.0, place["girl"][1]], "yawDeg": 0, "life": True}],
        "actions": [
            {"type": "clip", "character": "boy", "clip": "idle_relaxed", "base": True},
            {"type": "clip", "character": "girl", "clip": "idle_relaxed", "base": True},
            {"type": "clip", "character": "boy", "clip": "wave", "start": 10, "blendIn": 8, "blendOut": 8},
            {"type": "clip", "character": "girl", "clip": "wave", "start": 10, "mirror": True, "blendIn": 8, "blendOut": 8},
            {"type": "clip", "character": "boy", "clip": "point", "start": 120, "blendIn": 8, "blendOut": 8},
            {"type": "clip", "character": "girl", "clip": "point", "start": 120, "blendIn": 8, "blendOut": 8},
            {"type": "look", "character": "boy", "start": 220, "end": 300, "camera": True},
            {"type": "walk", "character": "boy", "start": 220, "end": 290, "to": [place["boy"][0], place["boy"][1]], "face": 0},
            {"type": "clip", "character": "boy", "clip": "wave", "start": 230, "blendIn": 8, "blendOut": 8},
            {"type": "clip", "character": "girl", "clip": "point", "start": 215, "blendIn": 8, "blendOut": 8},
            {"type": "reach", "character": "girl", "hand": "R", "object": "cup", "start": 225, "contact": 245, "liftEnd": 255,
             "place": 270, "release": 274, "end": 290, "lift": 0.0},
            {"type": "clip", "character": "boy", "clip": "sit_down", "start": 320, "blendIn": 8, "blendOut": 0, "end": 398},
            {"type": "clip", "character": "girl", "clip": "sit_down", "start": 320, "blendIn": 8, "blendOut": 0, "end": 398},
            {"type": "clip", "character": "boy", "clip": "stand_up", "start": 390, "blendIn": 8, "blendOut": 8},
            {"type": "clip", "character": "girl", "clip": "stand_up", "start": 390, "blendIn": 8, "blendOut": 8}],
        # the camera moves to a three-quarter view before the sit (seated thighs point at a front camera)
        "animation": {"camera.position": [[1, [0.0, 0.55, 2.3], "smooth"], [300, [0.0, 0.55, 2.3], "smooth"], [316, [1.7, 0.55, 1.5], "smooth"]],
                      "camera.target": [[1, [0.0, 0.38, 0.0], "smooth"], [300, [0.0, 0.38, 0.0], "smooth"], [316, [0.0, 0.3, -0.05], "smooth"]]},
        "production": {"cast": {"boy": {"version_dir": "assets/characters/boy_yellow_hoodie/versions/1.0.0"},
                                "girl": {"spec": "assets/characters/girl_auburn_bun_glasses/spec/girl_auburn_bun_glasses.spec.json"}},
                       "profile": "pipeline/charsys/rig_profiles/humanoid_rigify.json",
                       "render": {"resolution": [320, 180], "samples": 16, "light_scale": 1.0}},
        "x_t002_derivation": {"seat": "top = sit_down seat contact height_ratio x leg_length; centre z = clip seated root z x leg_length",
                              "height_ratio": seat["height_ratio"], "seated_root_per_leg": rk[1:], "characters": derived}}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(shot, open(OUT, "w"), indent=1)
    print(OUT, json.dumps(derived))


main()
