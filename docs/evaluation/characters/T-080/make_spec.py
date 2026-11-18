"""T-080: compose the boy's 2.0.0 spec from the 2.0.0-dev spec and the approved-improvement candidates.

    python3 docs/evaluation/characters/T-080/make_spec.py [--check]

Inputs (read only):
  base   assets/characters/boy_yellow_hoodie/spec/boy_yellow_hoodie.2.0.0-dev.spec.json (generic path)
  face   docs/evaluation/characters/T-065/candidates/boy_2.0-dev_face2.override.json  (face_generic/2 + body_generic/2)
  skin   docs/evaluation/characters/T-066/candidates/boy_yellow_hoodie.skin2.override.json (skin-felt/2, presets/2)
  hair   docs/evaluation/characters/T-079/candidates/boy.hair_v3.json (groom/2 round 3; Supervisor 2026-11-18:
         round 3 instead of round 2)
  outfit docs/evaluation/characters/T-068/candidates/boy_2.0.0-dev.garment_details.override.json
  personality content/personality/boy_yellow_hoodie.json (profile 1.0.0, T-053)

Output: assets/characters/boy_yellow_hoodie/spec/boy_yellow_hoodie.2.0.0.spec.json (one self-contained spec; the
approved 1.0.0 / 1.1.0 files and the 2.0.0-dev spec are not touched). --check only verifies the file is up to date.
Every conflict between candidates is resolved here, in data, and listed in CHOICES (copied into the spec metadata).
"""
import copy
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "pipeline", "charsys"))
import spec as SPEC  # noqa: E402

SPEC_DIR = "assets/characters/boy_yellow_hoodie/spec"
BASE = f"{SPEC_DIR}/boy_yellow_hoodie.2.0.0-dev.spec.json"
OUT = f"{SPEC_DIR}/boy_yellow_hoodie.2.0.0.spec.json"
FACE = "docs/evaluation/characters/T-065/candidates/boy_2.0-dev_face2.override.json"
SKIN = "docs/evaluation/characters/T-066/candidates/boy_yellow_hoodie.skin2.override.json"
HAIR = "docs/evaluation/characters/T-079/candidates/boy.hair_v3.json"  # hair v3 round 3 (T-079, merged)
OUTFIT = "docs/evaluation/characters/T-068/candidates/boy_2.0.0-dev.garment_details.override.json"
PERSONALITY = "content/personality/boy_yellow_hoodie.json"

CHOICES = [
    "face/head: T-065 boy face v2 candidate taken unchanged (face_generic/2 layout, cheeks, eyes, lids, socket, "
    "flat-stroke brows; body_generic/2 head outline fitted to the reference outlines).",
    "skin: T-066 skin-felt/2 (presets/2) with the porcelain-peach colour 236/190/166 for the skin slot and the face "
    "albedo, blush 226/128/112 (T-066's legacy blush colour, now in face.blush.srgb); T-065's dev blush placement kept.",
    "face skin occlusion: T-065's lift 0.35 kept; bleed 0 instead of T-065's 0.2 (conflict): presets/2 is "
    "non-emissive by rule and removes the bleed anyway; the references (upload 01, canon29) show no glowing creases.",
    "hair: T-079 round-3 groom/2 data unchanged (top whorl, upright crown, no horn tufts; Supervisor 2026-11-18: "
    "round 3 instead of round 2) and its hair material (felt hair 25/22/21); the 2.0.0-dev hair_clumps/1 section "
    "is replaced as a whole. Hair frame = the generic path's head frame from the body params (centre/radii within "
    "2 mm of the T-070/T-079 frame).",
    "outfit: T-068 clothing taken as a whole (hood volume, closed armholes, trousers length 0.985, sneakers type, "
    "backpack garment); accessories stay none (the backpack is a garment type, T-068).",
    "materials pin presets/2 (registered in versions.py by T-080); exporter export/4 kept (as 2.0.0-dev and the "
    "girl 0.10.0).",
    "personality: profile boy_yellow_hoodie 1.0.0 referenced from animation.personality (data only; the engine "
    "reads content/personality/<id>.json through the scene's \"personality\" field).",
]


def load(rel):
    return json.load(open(os.path.join(ROOT, rel)))


def compose():
    base = load(BASE)
    face = load(FACE)["override"]
    skin = load(SKIN)
    hair = load(HAIR)
    outfit = load(OUTFIT)["override"]
    pers = load(PERSONALITY)
    s = SPEC.deep_merge(base, face)  # face v2 + fitted head (generators face/body pinned there)
    # outfit (whole clothing section; T-068 also pins accessories none)
    s["clothing"] = copy.deepcopy(outfit["clothing"])
    s["generators"].update(outfit.get("generators", {}))
    s["accessories"] = {"generator": "none", "items": [],
                        "note": "T-068/T-080: the backpack is built as a garment type (clothing.garments[backpack])"}
    # hair v3 round 3 (whole hair section) + its material assignment
    s["hair"] = copy.deepcopy(hair["overrides"]["hair"])
    s["generators"].update(hair["overrides"]["generators"])
    s["materials"] = SPEC.deep_merge(s["materials"], hair["overrides"].get("materials", {}))
    # skin presets/2
    skin_asg = copy.deepcopy(skin["override"]["materials"]["assignments"]["skin"])
    rgb = skin_asg["base_color_srgb"]
    s["materials"]["assignments"]["skin"] = skin_asg
    s["materials"]["albedo_srgb"]["skin"] = list(rgb)
    s["face"]["blush"]["srgb"] = list(skin["legacy_post_build"]["blush_srgb"])
    s["face"]["skin"]["occlusion"]["bleed"] = 0.0
    s["generators"]["materials"] = "presets/2"
    # personality reference
    s["animation"]["personality"] = {"profile": pers["character"], "profile_version": pers["profile_version"],
                                     "path": PERSONALITY, "owner_brief": pers["owner_brief"]}
    s["identity"]["identity_lock"] = ("Successor to frozen 1.0.0 and 1.1.0; current approved version (owner, "
                                      "docs/process/OWNER_DECISIONS.md 2026-11-18)")
    s["metadata"] = {
        "spec_version": "2.0.0",
        "status": "approved (current); published to the asset store as 2.0.0 by T-080",
        "scope": "generic path: body_generic/2 fitted head, face_generic/2, skin-felt/2 (presets/2), groom/2 hair v3 "
                 "round 3, garment/1 hoodie (hood volume, closed armholes), joggers, sneakers, backpack; personality "
                 "profile 1.0.0",
        "parent_versions": ["1.0.0", "1.1.0", "2.0.0-dev"],
        "sources": {"base": BASE, "face": FACE, "skin": SKIN, "hair": HAIR, "outfit": OUTFIT,
                    "personality": PERSONALITY},
        "choices": CHOICES,
        "approval": {"by": "owner", "date": "2026-11-18",
                     "record": "docs/process/OWNER_DECISIONS.md 2026-11-18: \"I approve Boy 2.0.0 as the new "
                               "current version.\""},
    }
    s["generators"] = {k: s["generators"][k] for k in
                       ("body", "face", "groom", "garment", "accessories", "rig", "materials", "exporter")}
    SPEC.validate(s)
    return s


def main():
    s = compose()
    text = json.dumps(s, indent=1, ensure_ascii=False) + "\n"
    path = os.path.join(ROOT, OUT)
    if "--check" in sys.argv:
        ok = os.path.exists(path) and open(path).read() == text
        print("up to date" if ok else "STALE")
        return 0 if ok else 1
    open(path, "w").write(text)
    print(OUT, SPEC.sha256(s), json.dumps(s["generators"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
