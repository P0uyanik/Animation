"""Make an untracked T-010 derivative whose boy cast entry uses the unpublished T-014 1.1.0 spec override."""
import argparse
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SOURCE = os.path.join(ROOT, "episodes", "e903_test_video", "shots", "s010", "shot.scene.json")
SPEC = "assets/characters/boy_yellow_hoodie/spec/boy_yellow_hoodie.spec.json"
OVERRIDE = "assets/characters/boy_yellow_hoodie/spec/boy_yellow_hoodie.1.1.0.override.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    shot = json.load(open(SOURCE))
    shot["name"] += " / T-014 unpublished boy 1.1.0 candidate"
    shot["production"]["cast"]["boy"] = {"spec": SPEC, "overrides": [OVERRIDE]}
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w") as f:
        json.dump(shot, f, indent=1)
    print(f"[make_t014_shot] {SOURCE} -> {os.path.abspath(a.out)}")


if __name__ == "__main__":
    main()
