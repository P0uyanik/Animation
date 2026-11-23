"""T-219 step 6: writes the two s030 comparison shots into <out dir> (never into the repository's evaluation shots:
they cast explicit, non-current versions on purpose, and the white girl has no fidelity_baseline current entry).

    python3 docs/evaluation/characters/T-219/make_pushout_shots.py <out dir>
    python3 pipeline/production/run_shot.py --shot <out dir>/s030_current/shot.scene.json --blender <exe> \
        --frames 1-80 --blend-only --run-dir cur        (likewise s030_candidate, run-dir cand2)

Copies episodes/e912_paper_boat/shots/s030 with the girls cast explicitly (current = version_dir 0.14.0 / 0.1.0,
candidate = the T-219 candidate specs), the boy current, hair push-out on (T-194 defaults), plus the episode's
content/assets next to them (run_shot looks for props in content/assets above the shot)."""
import json
import os
import shutil
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
SRC = "episodes/e912_paper_boat/shots/s030/shot.scene.json"
CAST = {
    "current": {"auburn": {"version_dir": "assets/characters/girl_auburn_bun_glasses/versions/0.14.0"},
                "white": {"version_dir": "assets/characters/girl_white_hair_blue_dress/versions/0.1.0"}},
    "candidate": {"auburn": {"spec": "assets/characters/girl_auburn_bun_glasses/spec/candidates/T-219/"
                                     "girl_auburn_bun_glasses.0.15.0.spec.json"},
                  "white": {"spec": "assets/characters/girl_white_hair_blue_dress/spec/candidates/T-219/"
                                    "girl_white_hair_blue_dress.0.2.0.spec.json"}},
}


def main(out):
    out = os.path.abspath(out)
    if out.startswith(os.path.join(ROOT, "docs")) or out.startswith(os.path.join(ROOT, "assets")):
        raise SystemExit("write the comparison shots outside docs/ and assets/")
    shutil.copytree(os.path.join(ROOT, "episodes/e912_paper_boat/content"), os.path.join(out, "content"),
                    dirs_exist_ok=True)
    for tag, cast in CAST.items():
        d = json.load(open(os.path.join(ROOT, SRC)))
        d["production"]["cast"].update(cast)
        d["production"].setdefault("render", {})["hair_pushout"] = True
        d["x_t219"] = f"T-219 step 6: copy of {SRC}, girls cast explicitly ({tag}); hair push-out on (T-194 defaults)"
        p = os.path.join(out, f"s030_{tag}", "shot.scene.json")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        json.dump(d, open(p, "w"), indent=1)
        print(p)


if __name__ == "__main__":
    main(sys.argv[1])
