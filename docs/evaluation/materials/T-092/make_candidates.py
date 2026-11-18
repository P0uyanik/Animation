"""Write the T-092 candidate overrides (evaluation only; never an approved version).

    python3 docs/evaluation/materials/T-092/make_candidates.py

Each override sits on top of the character's current approved spec (docs/evaluation/characters/fidelity_baseline.json)
and changes only material assignments: materials.assignments.<slot> and the material / materials.<part> entries of
garments. clothing.garments is a list (lists are replaced, not merged), so the override carries the approved list with
every non-material key copied unchanged; T-094 can combine it with T-093 field by field. No generator pin, version or
*.spec.json is changed.
"""
import copy
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))

# slot -> new assignment fields (merged over the approved assignment)
PLAN = {
    "boy_yellow_hoodie": {
        "note": "boy 2.0.0 + T-092 presets/3: soft hoodie fleece, quiet trouser pile, warm skin (skin-felt/3).",
        "assignments": {"skin": {"preset": "skin-felt/3"}},
        "garments": {"hoodie": {"material": {"preset": "hoodie fleece/3"}},
                     "trousers": {"material": {"preset": "trouser pile/3"}}},
    },
    "girl_auburn_bun_glasses": {
        "note": "girl 0.11.0 + T-092 presets/3: dense smooth vest felt, quiet brushed-cotton blouse and shorts, cream "
                "fleece boot cuffs (G08, owner-accepted), warm skin (skin-felt/3).",
        "assignments": {"skin": {"preset": "skin-felt/3"}},
        "garments": {"vest": {"material": {"preset": "vest felt/3", "base_color_srgb": [118, 82, 80]}},
                     "blouse": {"material": {"preset": "brushed cotton/3"}},
                     "shorts": {"material": {"preset": "brushed cotton/3"}},
                     "boots": {"materials": {"band": {"preset": "cuff fleece/3", "base_color_srgb": [240, 222, 196],
                                                      "reference_size_m": 0.15, "overrides": None}}}},
    },
}


def merged(old, new):
    out = copy.deepcopy(old)
    for k, v in new.items():
        if v is None:
            out.pop(k, None)
        else:
            out[k] = copy.deepcopy(v)
    return out


def main():
    sys_path = os.path.join(ROOT, "pipeline", "charsys")
    import sys
    sys.path.insert(0, sys_path)
    import spec as SPEC
    baseline = json.load(open(os.path.join(ROOT, "docs", "evaluation", "characters", "fidelity_baseline.json")))
    for cid, plan in PLAN.items():
        entry = baseline["characters"][cid]
        spec, _ = SPEC.load(os.path.join(ROOT, entry["build"]),
                            [os.path.join(ROOT, p) for p in entry.get("overrides", [])])
        assignments = {slot: merged(spec["materials"]["assignments"][slot], new)
                       for slot, new in plan["assignments"].items()}
        garments = copy.deepcopy(spec["clothing"]["garments"])
        for g in garments:
            change = plan["garments"].get(g["name"])
            if not change:
                continue
            if "material" in change:
                g["material"] = merged(g["material"], change["material"])
            for part, new in change.get("materials", {}).items():
                g["materials"][part] = merged(g["materials"][part], new)
        override = {"materials": {"assignments": assignments}, "clothing": {"garments": garments}}
        data = {"character_id": cid, "task": "T-092",
                "base": entry["build"],
                "note": "T-092 candidate (path B, evaluation only; never an approved version): " + plan["note"] +
                        " Changes only material assignments (materials.assignments and garment material entries); "
                        "the garments list is the approved one with only material keys changed. The materials pin "
                        "stays as approved (T-094 sets generators.materials = presets/3 at the version bump).",
                "override": override}
        out = os.path.join(ROOT, "assets", "characters", cid, "spec", "candidates", "T-092",
                           f"{cid}.materials_r2.override.json")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(data, fh, indent=1)
            fh.write("\n")
        print("wrote", os.path.relpath(out, ROOT))


if __name__ == "__main__":
    main()
