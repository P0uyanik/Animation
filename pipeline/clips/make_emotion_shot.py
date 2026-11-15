"""Writes the T-003 emotion test shot episodes/e902_emotion_test/shots/s010/shot.scene.json (python3).

    python3 pipeline/clips/make_emotion_shot.py

Both characters (boy: published 1.0.0, 4 facial morphs; girl: unpublished spec build, full face library) play the
same shared emotions from content/emotions/ in sequence, each starting at the previous one's release (the engine
crossfades them), on the base clip idle_relaxed, looking at the camera. A final segment layers emotions with walk, look and a wave clip.
The peak frame of every emotion (middle of its full-weight hold, outside its gesture) is written into the shot's
"x_t003" block for the contact sheet; a shot is data, this script only documents how it was derived."""
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "episodes", "e902_emotion_test", "shots", "s010", "shot.scene.json")
EMOTIONS = ["happy", "happy/laugh", "sad", "sad/cry", "angry", "surprised", "confused", "afraid", "sleepy", "curious"]
FPS = 30
LIFE = {"blinkInterval": 100}  # life layer on; no automatic blink during the shot (faces are judged at the peaks)


def load(full):
    name, _, variant = full.partition("/")
    j = json.load(open(os.path.join(ROOT, "content", "emotions", name + ".emotion.json")))
    if variant:  # JSON merge patch (only the fields used here)
        p = j["variants"][variant]
        j = dict(j, timing=dict(j["timing"], **p.get("timing", {})), gesture=p.get("gesture", j.get("gesture")))
    return j


def main():
    acts = [{"type": "clip", "character": n, "clip": "idle_relaxed", "base": True} for n in ("boy", "girl")]
    t, prev_release, peaks = 12.0, 0.0, []
    for i, n in enumerate(EMOTIONS):
        e = load(n)
        tm = e["timing"]
        on, hold, rel = tm["onset"] * FPS, tm["hold"] * FPS, tm["release"] * FPS
        onset = on + (prev_release if i else 0.0)  # crossfade: the previous release + this onset
        a, b = t + onset, t + onset + hold  # full weight
        g = e.get("gesture")
        if g:
            cl = json.load(open(os.path.join(ROOT, "content", "clips", g["clip"] + ".clip.json")))
            g0 = t + g.get("offset", 0) * FPS
            g1 = g0 + (cl["frame_count"] - 1) / cl["fps"] * FPS
            a = max(a, g1 + 1)
        peaks.append({"emotion": n, "start": t, "peak": int(round((a + b) / 2))})
        for c in ("boy", "girl"):
            acts.append({"type": "emotion", "character": c, "name": n, "start": t})
        t, prev_release = b, rel  # the next starts where this one's release begins
    last_end = t + prev_release
    # layering segment: emotion + walk + look + wave clip (girl), emotion + walk + look (boy)
    s = int(last_end) + 20
    # both keep their gaze on the camera through the sequence (look keeps priority over the emotion's head pose)
    acts += [{"type": "look", "character": n, "start": 1, "end": s - 1, "camera": True} for n in ("boy", "girl")]
    acts += [{"type": "emotion", "character": "girl", "name": "happy", "start": s, "end": s + 150},
             {"type": "emotion", "character": "boy", "name": "curious", "start": s, "end": s + 150},
             {"type": "walk", "character": "girl", "start": s + 20, "end": s + 90, "to": [0.42, 0.12], "face": 0},
             {"type": "walk", "character": "boy", "start": s + 20, "end": s + 90, "to": [-0.42, 0.12], "face": 0},
             {"type": "look", "character": "girl", "start": s + 10, "end": s + 150, "camera": True},
             {"type": "look", "character": "boy", "start": s + 10, "end": s + 150, "camera": True},
             {"type": "clip", "character": "girl", "clip": "wave", "start": s + 40, "blendIn": 8, "blendOut": 8}]
    frame_end = s + 160
    shot = {
        "format": "plush.scene", "version": 1,
        "name": "e902_emotion_test s010: shared emotions on two characters (technical validation)",
        "frameRate": [FPS, 1], "frameStart": 1, "frameEnd": frame_end,
        "render": {"width": 640, "height": 360, "spp": 32, "maxDepth": 8, "exposureEV": 0.3, "denoise": True, "denoiseBlend": 0.85, "clamp": 12},
        "camera": {"position": [0.0, 0.55, 2.2], "target": [0.0, 0.52, 0.0], "focalMm": 40, "fStop": 0, "focusDistance": -1},
        "materials": [{"name": "floor_mat", "type": "standard", "baseColor": [0.46, 0.44, 0.42], "roughness": 0.85, "specular": 0.3},
                      {"name": "wall_mat", "type": "standard", "baseColor": [0.62, 0.6, 0.55], "roughness": 0.9, "specular": 0.3}],
        "lights": [{"type": "rect", "corner": [-2.0, 1.0, 2.0], "edgeU": [1.2, 0, 0.6], "edgeV": [0, 1.4, 0], "color": [1.0, 0.95, 0.88], "intensity": 3.0},
                   {"type": "sun", "direction": [0.3, -0.6, -0.7], "angleDeg": 4, "color": [1.0, 0.92, 0.82], "intensity": 1.4},
                   {"type": "sky", "color": [0.6, 0.62, 0.66], "intensity": 0.4}],
        "objects": [{"name": "floor", "kind": "box", "min": [-4, -0.05, -3], "max": [4, 0, 4], "material": "floor_mat"},
                    {"name": "wall", "kind": "box", "min": [-4, 0, -1.4], "max": [4, 3, -1.3], "material": "wall_mat"}],
        "characters": [{"name": "boy", "asset": "(set by run_shot)", "position": [-0.24, 0.0, 0.0], "yawDeg": 0, "life": LIFE},
                       {"name": "girl", "asset": "(set by run_shot)", "position": [0.24, 0.0, 0.0], "yawDeg": 0, "life": LIFE}],
        "actions": acts,
        "production": {"cast": {"boy": {"version_dir": "assets/characters/boy_yellow_hoodie/versions/1.0.0"},
                                "girl": {"spec": "assets/characters/girl_auburn_bun_glasses/spec/girl_auburn_bun_glasses.spec.json"}},
                       "profile": "pipeline/charsys/rig_profiles/humanoid_rigify.json",
                       "render": {"resolution": [320, 180], "samples": 16, "light_scale": 1.0}},
        "x_t003": {"peaks": peaks, "layering_segment": [s, s + 150],
                   "note": "peak = middle of the full-weight hold outside the gesture; emotions crossfade (previous release + onset)"}}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(shot, open(OUT, "w"), indent=1)
    print(OUT, json.dumps(peaks))


main()
