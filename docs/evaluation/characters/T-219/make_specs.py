"""T-219: composes the candidate specs (plain Python).

    python3 docs/evaluation/characters/T-219/make_specs.py [--out-root <dir>]

For each girl: the CURRENT published spec (assets/characters/<id>/versions/<current>/spec.json, face untouched: D6)
+ hair.flock = T-207 options/V1.json (owner pick 2026-11-23 ~06:58 CET) + hair.cap_contour and the H2 volume values
from h2/<id>.json. h2 patches name structures by "name"; a dict merges into the structure (nested dicts merge, a dict
whose keys are list indices patches those list items, anything else replaces). Writes
assets/characters/<id>/spec/candidates/T-219/<id>.<version>.spec.json (or under --out-root)."""
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
V1 = os.path.join(ROOT, "docs", "evaluation", "characters", "T-207", "options", "V1.json")
CHARS = {"girl_auburn_bun_glasses": ("0.14.0", "0.15.0"), "girl_white_hair_blue_dress": ("0.1.0", "0.2.0")}
DECISION = ("docs/process/OWNER_DECISIONS.md 2026-11-23 ~06:58 CET: T-207 hair look V1 for the auburn and the "
            "white-haired girl (boy unchanged), new character versions as sheets for approval before CURRENT; fix the "
            "forehead stair-step with H2")


def merge(dst, patch):
    for k, v in patch.items():
        if isinstance(v, dict) and isinstance(dst.get(k), list) and all(x.isdigit() for x in v):
            for i, item in v.items():
                if isinstance(item, dict) and isinstance(dst[k][int(i)], dict):
                    merge(dst[k][int(i)], item)
                else:
                    dst[k][int(i)] = copy.deepcopy(item)
        elif isinstance(v, dict) and isinstance(dst.get(k), dict):
            merge(dst[k], v)
        else:
            dst[k] = copy.deepcopy(v)
    return dst


def compose(cid, cur, new):
    spec = json.load(open(os.path.join(ROOT, "assets", "characters", cid, "versions", cur, "spec.json")))
    h2 = json.load(open(os.path.join(HERE, "h2", cid + ".json")))
    hair = spec["hair"]
    by_name = {s["name"]: s for s in hair["structures"]}
    for name, patch in (h2.get("structures") or {}).items():
        merge(by_name[name], patch)
    merge(hair, h2.get("hair") or {})
    hair["flock"] = json.load(open(V1))
    md = spec["metadata"]
    spec["metadata"] = {
        "spec_version": new, "parent_versions": [cur],
        "status": f"T-219: candidate (hair release: T-207 V1 flock + H2 volume + cap border); NOT approved, not current",
        "sources": {"derived_from": f"assets/characters/{cid}/versions/{cur}/spec.json",
                    "layers": ["docs/evaluation/characters/T-207/options/V1.json (hair.flock)",
                               f"docs/evaluation/characters/T-219/h2/{cid}.json (H2 volume, hair.cap_contour)"],
                    "composed_by": "docs/evaluation/characters/T-219/make_specs.py"},
        "owner_decisions": DECISION, "parent_metadata": md}
    return spec


def main(argv):
    out_root = argv[argv.index("--out-root") + 1] if "--out-root" in argv else ROOT
    for cid, (cur, new) in CHARS.items():
        d = os.path.join(out_root, "assets", "characters", cid, "spec", "candidates", "T-219")
        os.makedirs(d, exist_ok=True)
        p = os.path.join(d, f"{cid}.{new}.spec.json")
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(compose(cid, cur, new), fh, indent=1, ensure_ascii=False)
            fh.write("\n")
        print(p)


if __name__ == "__main__":
    main(sys.argv[1:])
