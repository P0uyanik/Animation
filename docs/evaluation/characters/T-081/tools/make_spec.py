"""T-081: writes assets/characters/girl_auburn_bun_glasses/spec/girl_auburn_bun_glasses.0.11.0.spec.json.

    python3 docs/evaluation/characters/T-081/tools/make_spec.py

0.11.0 = the frozen base spec + the approved 0.10.0 override + the owner-approved candidates, in this order (later
wins): T-065 face v2 + fitted head, T-066 skin presets/2, T-068 vest details, T-070 hair v3 round 2 (groom/2), then
the T-081 choices below. A complete spec file instead of an override: an override can only add keys, and groom/2
needs the groom/1 hair keys (structure names in hair.dynamics, yarn, scalp offset) removed."""
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "pipeline", "charsys"))
from spec import deep_merge  # noqa: E402

G = "assets/characters/girl_auburn_bun_glasses/spec/"
E = "docs/evaluation/characters/"
OUT = G + "girl_auburn_bun_glasses.0.11.0.spec.json"


def ov(path):
    d = json.load(open(os.path.join(ROOT, path)))
    d = d.get("override", d.get("overrides", d))
    d.pop("metadata", None)
    return d


T081 = {
    "face": {
        "eyes": {"socket": {"wall_smooth_iterations": 10,
                            "note": "T-081: relaxes the socket wall (face_generic/2 opt-in): the sharp folds at the eye corners and below the eye rims (dark specks under skin-felt/2) go from max 92 deg to 40 deg"}},
        "mouth": {"half_width_m": 0.0205, "lip_height_m": 0.0034, "lip_srgb": [222, 142, 140],
                  "fullness": {"upper": 1.45, "lower": 1.8, "forward_m": 0.0014, "lower_forward": 1.3},
                  "note": "T-081 (0.11.0): neutral = closed gentle smile with lifted cheeks (owner decisions 2026-11-17/18, ref_34 Neutral): face_generic/2 rest_shape soft_smile (MouthSmile 0.35 + CheekRaise 0.8 baked, lips closed, no teeth or tongue at rest); open smile with teeth and tongue only from MouthWide/JawOpen (Smile, Laugh, Surprise, MouthOpen, talking). Lips a little wider, fuller and pinker than the T-065 candidate (ref_34 mouth tiles, T-059)."},
        "ears": {"radii_m": [0.013, 0.025, 0.034]},
    },
    "body": {"params": {"neck": {"radius": 0.054, "top_radius": 0.061,
                                 "note": "T-081: wider neck (was 0.04639 / 0.055) so the neck reads less like a stalk under the broad chin (sheet30 front); its length is unchanged"}}},
    "animation": {"personality": {"profile": "girl_auburn_bun_glasses", "profile_version": "1.0.0",
                                  "path": "content/personality/girl_auburn_bun_glasses.json",
                                  "note": "T-053 personality profile referenced by this version (scenes opt in with \"personality\": \"girl_auburn_bun_glasses\")"}},
}

HISTORY = ("0.11.0 (T-081, complete spec girl_auburn_bun_glasses.0.11.0.spec.json; base spec + 0.10.0 + the approved "
           "candidates): face_generic/2 + body_generic/2 fitted head (T-065) with the closed gentle smile + lifted cheeks "
           "at rest (soft_smile) and brown eyes kept; skin-felt/2 porcelain-peach skin, warmer lower blush (T-066); "
           "hair v3 groom/2 round 2 (T-070); vest patch pockets + cross-stitch decals (T-068); personality profile 1.0.0 "
           "(T-053); socket-wall smoothing (cheek/eye-corner folds fixed), fuller wider lips, larger ears, wider neck "
           "(T-081, T-059 targets); unpublished, awaiting owner visual approval; not the current version")


def main():
    base = json.load(open(os.path.join(ROOT, G + "girl_auburn_bun_glasses.spec.json")))
    o = ov(G + "girl_auburn_bun_glasses.0.10.0.override.json")
    for p in (E + "T-065/candidates/girl_next_face2.override.json",
              E + "T-066/candidates/girl_auburn_bun_glasses.skin2.override.json",
              E + "T-068/candidates/girl.vest_details.override.json",
              E + "T-070/candidates/girl.hair_v3.json"):
        o = deep_merge(o, ov(p))
    o = deep_merge(o, T081)
    hair = o.pop("hair")
    s = deep_merge(base, o)
    hair["components"] = base["hair"]["components"]
    hair["provenance"] = "T-070 hair v3 round 2 (groom/2) candidate data, docs/evaluation/characters/T-070/candidates/girl.hair_v3.json"
    s["hair"] = hair
    md = s["metadata"]
    md["history"] = json.load(open(os.path.join(ROOT, G + "girl_auburn_bun_glasses.0.10.0.override.json")))["override"]["metadata"]["history"]
    md["spec_version"] = "0.11.0"
    md["status"] = "T-081: all approved improvements in one girl version; unpublished, awaiting owner visual approval (not current)"
    md["history"] = list(md.get("history", [])) + [HISTORY]
    with open(os.path.join(ROOT, OUT), "w") as f:
        json.dump(s, f, indent=1)
        f.write("\n")
    print("wrote", OUT)


main()
