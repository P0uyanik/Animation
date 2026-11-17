"""Writes the shared animation evaluation shots (T-062) into content/scenes/eval/<shot>/shot.scene.json.

    python3 content/scenes/eval/make_eval_shots.py [--check]

Every evaluation shot is derived from an existing, reviewed shot (its staging, actions and camera are kept as they
are), and its cast is replaced by "current" references: {"character_id": <id>, "version": "current"}, which
run_shot resolves to the character's current approved version from docs/evaluation/characters/fidelity_baseline.json.
So an evaluation never pins a character version, and a newly approved version is used without editing any shot.
Animation tasks render their evidence from these shots (or from copies that keep the "current" cast).

--check: exits 1 when a written shot differs from what this script would write (the files are generated)."""
import argparse
import copy
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
HERE = os.path.dirname(os.path.abspath(__file__))

# shot name -> (source shot, purpose, optional changes to the derived scene)
SHOTS = {
    "idle": ("episodes/e906_acting_test/shots/s010/shot.scene.json",
             "Idle and life layer: both characters stand, the automatic base idle (idle_relaxed) and blinks run, each "
             "looks at the other; no gesture. Staging and camera from e906.", "idle"),
    "walk": ("episodes/e000_pilot/shots/s010/shot.scene.json",
             "Walk: the girl walks in and stops beside the boy; gaze hand-off and expressions on arrival (e000).", None),
    "reach_touch_wave": ("docs/evaluation/animation/T-045/shot_after/shot.scene.json",
                         "Reach + touch then wave, both characters, body mechanics on (T-045 'after' shot).", None),
    "wave": ("episodes/e906_acting_test/shots/s010/shot.scene.json",
             "Wave and reaction: the girl waves, the boy reacts and waves back (e906 acting test).", None),
    "handover": ("episodes/e905_props_test/shots/s010/shot.scene.json",
                 "Hand-over: the boy picks up a cup and hands it to the girl (e905 props test).", None),
    "emotions": ("episodes/e902_emotion_test/shots/s010/shot.scene.json",
                 "Emotion sequence: every shared emotion and its variants on both characters (e902).", None),
}


def character_ids(cast: dict) -> dict:
    """Scene character name -> character id of the source shot's explicit cast entry."""
    ids = {}
    for name, src in cast.items():
        if "character_id" in src:
            ids[name] = src["character_id"]
        elif "version_dir" in src:
            ids[name] = json.load(open(os.path.join(ROOT, src["version_dir"], "manifest.json")))["character_id"]
        else:
            ids[name] = json.load(open(os.path.join(ROOT, src["spec"])))["identity"]["id"]
    return ids


def derive(name: str) -> dict:
    source, purpose, variant = SHOTS[name]
    shot = copy.deepcopy(json.load(open(os.path.join(ROOT, source))))
    prod = shot["production"]
    ids = character_ids(prod["cast"])
    prod["cast"] = {n: {"character_id": ids[n], "version": "current"} for n in prod["cast"]}
    if variant == "idle":
        shot["frameEnd"] = 60
        shot["actions"] = [a for a in shot["actions"] if a["type"] == "look"]
        for a in shot["actions"]:
            a["start"], a["end"] = 1, 60
    shot["name"] = f"eval/{name}: {purpose}"
    for key in [k for k in shot if k.startswith("x_")]:
        del shot[key]
    shot["x_eval"] = {"task": "T-062", "derived_from": source, "generator": "content/scenes/eval/make_eval_shots.py",
                      "cast": "current: resolved by run_shot from docs/evaluation/characters/fidelity_baseline.json"}
    return shot


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    stale = []
    for name in SHOTS:
        text = json.dumps(derive(name), indent=1) + "\n"
        path = os.path.join(HERE, name, "shot.scene.json")
        if a.check:
            if not os.path.isfile(path) or open(path, encoding="utf-8").read() != text:
                stale.append(os.path.relpath(path, ROOT))
            continue
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "w", encoding="utf-8", newline="\n").write(text)
        print(os.path.relpath(path, ROOT))
    if stale:
        print("stale evaluation shots (run content/scenes/eval/make_eval_shots.py):", ", ".join(stale))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
