"""Write the T-110 felt-surface candidate overrides (evaluation only; never an approved version).

    python3 docs/evaluation/characters/T-110/make_candidates.py [--specs-root <checkout with the base specs>] [--check]

Base: boy 2.1.0 and girl 0.12.0 (T-094, the versions about to become current). Each override changes only material
preset ids to their presets/4 counterparts (same colour, reference size and overrides) and pins
generators.materials = presets/4. clothing.garments is a list (lists are replaced, not merged), so the override
carries the base list with every non-material key unchanged.
"""
import argparse
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
BASES = {"boy_yellow_hoodie": "assets/characters/boy_yellow_hoodie/spec/boy_yellow_hoodie.2.1.0.spec.json",
         "girl_auburn_bun_glasses": "assets/characters/girl_auburn_bun_glasses/spec/girl_auburn_bun_glasses.0.12.0.spec.json"}
# presets/1..3 id -> presets/4 id (pipeline/charsys/materials/presets_felt.json)
FELT = {"skin-felt/3": "felt skin/4", "hoodie fleece/3": "hoodie fleece/4", "trouser pile/3": "trouser pile/4",
        "felt": "felt/4", "felt hair": "felt hair/4", "vest felt/3": "vest felt/4",
        "brushed cotton/3": "brushed cotton/4", "cuff fleece/3": "cuff fleece/4", "boot fleece": "boot fleece/4"}


def swap(node, changed, path):
    if isinstance(node, dict):
        if isinstance(node.get("preset"), str) and node["preset"] in FELT:
            changed.append(f"{path}: {node['preset']} -> {FELT[node['preset']]}")
            node["preset"] = FELT[node["preset"]]
        for k, v in node.items():
            swap(v, changed, f"{path}.{k}" if path else k)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            swap(v, changed, f"{path}[{i}]")


def build(cid, specs_root):
    base_rel = BASES[cid]
    spec = json.load(open(os.path.join(specs_root, base_rel), encoding="utf-8"))
    materials = copy.deepcopy({"assignments": spec["materials"]["assignments"]})
    garments = copy.deepcopy(spec["clothing"]["garments"])
    changed = []
    swap(materials, changed, "materials")
    swap(garments, changed, "clothing.garments")
    return {"character_id": cid, "task": "T-110", "base": base_rel,
            "note": "T-110 candidate (path B, evaluation only; never an approved version): the base spec with every "
                    "felt-surface preset id swapped to its presets/4 counterpart (shared GN fibre halo; felt skin "
                    "felt skin/4) and generators.materials = presets/4. Colours, reference sizes, overrides and every "
                    "non-material key unchanged. The skin halo is added by the post-build pass "
                    "(materials/felt_halo.add_missing_halos; apply_felt_halo.py for evaluation builds).",
            "changed": changed,
            "override": {"generators": {"materials": "presets/4"}, "materials": materials,
                         "clothing": {"garments": garments}}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--specs-root", default=ROOT)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    bad = 0
    for cid in BASES:
        doc = build(cid, a.specs_root)
        path = os.path.join(ROOT, "assets", "characters", cid, "spec", "candidates", "T-110", f"{cid}.felt_surface.override.json")
        text = json.dumps(doc, indent=1) + "\n"
        if a.check:
            same = os.path.exists(path) and open(path, encoding="utf-8").read() == text
            print(("OK " if same else "DIFF ") + path)
            bad += not same
        else:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            open(path, "w", encoding="utf-8", newline="\n").write(text)
            print(path, len(doc["changed"]), "presets swapped")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
