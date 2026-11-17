"""Writes the untracked "old clips" comparison shot for e906 (T-027) and its clip copies (python3).

    python3 episodes/e906_acting_test/make_old_variant.py [--ref e94f3bc]

Source: episodes/e906_acting_test/shots/s010/shot.scene.json. Output (untracked, inside the shot's build folder):
  shots/s010/build/old_variant/shot.scene.json and shots/s010/build/old_variant/clips/<name>.clip.json
The variant is the same shot as the repository had it before T-027: the clips of git revision --ref (the main commit
this branch started from) and no automatic base idle ("autoIdle": false; that engine had none). Each clip action plays
the old file with its speed scaled so it lasts as long as the new clip in the shot (old wave 105 frames, new 90), so
both renders show the full motion over the same frames. Everything else (cast, camera, looks, expressions, life layer
with the default blinks) is identical."""
import argparse
import json
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SHOT = os.path.join(HERE, "shots", "s010", "shot.scene.json")
OUT = os.path.join(HERE, "shots", "s010", "build", "old_variant")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", default="e94f3bc")
    a = ap.parse_args()
    shot = json.load(open(SHOT))
    os.makedirs(os.path.join(OUT, "clips"), exist_ok=True)
    for act in shot["actions"]:
        if act["type"] != "clip":
            continue
        name = act["clip"]
        old = subprocess.run(["git", "show", f"{a.ref}:content/clips/{name}.clip.json"], cwd=ROOT, check=True,
                             capture_output=True, text=True).stdout
        path = os.path.join(OUT, "clips", name + ".clip.json")
        open(path, "w").write(old)
        new = json.load(open(os.path.join(ROOT, "content", "clips", name + ".clip.json")))
        oldc = json.loads(old)
        dur_new = (new["frame_count"] - 1) / new["fps"] / act.get("speed", 1.0)
        act["speed"] = round((oldc["frame_count"] - 1) / oldc["fps"] / dur_new, 4)
        act["file"] = path  # absolute: run_shot bakes a resolved copy of the scene from its build folder
        del act["clip"]
    for c in shot["characters"]:
        c["autoIdle"] = False
    shot["name"] += " / OLD CLIPS (pre-T-027, no automatic idle; untracked comparison variant)"
    json.dump(shot, open(os.path.join(OUT, "shot.scene.json"), "w"), indent=1)
    print(f"[make_old_variant] {os.path.relpath(os.path.join(OUT, 'shot.scene.json'), ROOT)}")


if __name__ == "__main__":
    main()
