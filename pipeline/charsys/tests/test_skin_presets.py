"""Plain-Python checks for the T-066 presets/2 skin family (pipeline/charsys/materials/skin_presets.json).

    python3 pipeline/charsys/tests/test_skin_presets.py

1. the skin library validates (schema, family presets/2, kind skin, the skin-section rules);
2. its ids never shadow a presets/1 id, and every presets/1 id resolves exactly as before (no family tag, same
   values as presets.json defaults + preset);
3. the family is non-emissive and matte (the T-066 look rules: no glowing creases, no glossy skin);
4. opt-in only: the approved character versions (fidelity_baseline.json: spec + current overrides) name no
   presets/2 id, and the T-066 candidate overrides do and validate through spec.load.
The Blender-side graph checks are in test_skin_material.py.
"""
import copy
import glob
import json
import os
import sys


HERE = os.path.dirname(os.path.abspath(__file__))
CHARSYS = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(CHARSYS, "..", ".."))
sys.path.insert(0, CHARSYS)

import spec as SPEC  # noqa: E402
import versions as V  # noqa: E402
from materials import builder as MATERIALS  # noqa: E402

RESULTS = []
CANDIDATES = os.path.join(ROOT, "docs", "evaluation", "characters", "T-066", "candidates")


def check(name, ok, detail=None):
    RESULTS.append(bool(ok))
    suffix = "" if detail is None else f" {detail}"
    print(f"[test_skin_presets] {'PASS' if ok else 'FAIL'} {name}{suffix}")


def preset_ids(spec):
    return {slot: cfg.get("preset") for slot, cfg in ((spec.get("materials") or {}).get("assignments") or {}).items()}


def main():
    skin = MATERIALS.load_skin_library()
    v1 = MATERIALS.load_library()
    check("skin library validates", MATERIALS.validate_skin_library(skin) == [])
    check("schema / family", skin["schema"] == MATERIALS.SKIN_SCHEMA and skin["family"] == "presets/2")
    check("ids disjoint from presets/1", not set(skin["presets"]) & set(v1["presets"]), sorted(skin["presets"]))
    check("skin-felt/2 present", "skin-felt/2" in skin["presets"])

    # presets/1 resolution unchanged
    same = True
    for name in v1["presets"]:
        expect = MATERIALS.deep_merge(v1["defaults"], v1["presets"][name])
        expect["name"] = name
        got = MATERIALS.resolve_preset(name)
        same &= got == expect and "family" not in got and MATERIALS.library_for(name) is not None
        same &= not MATERIALS.is_skin_preset(name)
    check("presets/1 ids resolve exactly as before", same)

    for name in skin["presets"]:
        p = MATERIALS.resolve_preset(name)
        check(f"{name}: family tag", p.get("family") == "presets/2")
        check(f"{name}: non-emissive", p["skin"]["emission"] is False)
        check(f"{name}: matte (roughness >= 0.6, specular <= 0.35)",
              p["surface"]["roughness"] >= 0.6 and p["surface"]["specular_ior_level"] <= 0.35,
              (p["surface"]["roughness"], p["surface"]["specular_ior_level"]))
        check(f"{name}: soft subsurface", 0.2 <= p["surface"]["subsurface_weight"] <= 0.6)
        check(f"{name}: gentle rim sheen", p["silhouette"]["enabled"] and p["silhouette"]["weight"] <= 0.8)
        check(f"{name}: no generated fibre curves on skin", p["fibres"]["enabled"] is False)
        tint = p["skin"]["crease"]["tint_srgb"]
        check(f"{name}: crease tint is warm (R >= G >= B)", tint[0] >= tint[1] >= tint[2], tint)
        check(f"{name}: skin fuzz target below 3/255", p["targets"]["fuzz_rms_y255"]["range"][1] <= 3.0)

    # validation rules reject a glowing or out-of-range skin
    bad = copy.deepcopy(skin)
    bad["presets"]["skin-felt/2"]["skin"]["emission"] = True
    bad["presets"]["skin-felt/2"]["skin"]["flock"] = {"enabled": True, "scale_per_reference": 700.0, "albedo": 0.5}
    errs = MATERIALS.validate_skin_library(bad)
    check("validator rejects emission and loud flock", any("emission" in e for e in errs) and any("flock" in e for e in errs), errs)
    clash = copy.deepcopy(skin)
    clash["presets"]["skin-felt"] = clash["presets"]["skin-felt/2"]
    check("validator rejects a presets/1 id", any("reuse a presets/1 id" in e for e in MATERIALS.validate_skin_library(clash)))

    # assignments: opt-in by id
    asg = {"assignments": {"skin": {"preset": "skin-felt/2", "base_color_srgb": [236, 196, 172]}}}
    check("assignment with a skin id validates", MATERIALS.validate_assignments(asg) == [])
    asg["assignments"]["skin"]["preset"] = "skin-felt/9"
    check("unknown id still rejected", MATERIALS.validate_assignments(asg) != [])

    # approved versions unchanged: they name no presets/2 id
    baseline = json.load(open(os.path.join(ROOT, "docs", "evaluation", "characters", "fidelity_baseline.json")))
    for cid, entry in baseline["characters"].items():
        spec, _ = SPEC.load(os.path.join(ROOT, entry["build"]), [os.path.join(ROOT, p) for p in entry.get("overrides", [])])
        ids = preset_ids(spec)
        pins, _ = V.resolve_pins(spec)  # presets/2 skin ids only with an explicit generators.materials presets/2 pin
        check(f"{cid} approved version names presets/2 ids only with the presets/2 pin",
              pins["materials"] == "presets/2" or not any(MATERIALS.is_skin_preset(v) for v in ids.values()), ids)

    # candidates opt in and validate
    found = sorted(glob.glob(os.path.join(CANDIDATES, "*.override.json")))
    check("T-066 candidate overrides exist", len(found) >= 2, [os.path.basename(p) for p in found])
    for path in found:
        data = json.load(open(path))
        cid = data["character_id"]
        entry = baseline["characters"][cid]
        overrides = [os.path.join(ROOT, p) for p in entry.get("overrides", [])] + [path]
        spec, _ = SPEC.load(os.path.join(ROOT, entry["build"]), overrides)
        ids = preset_ids(spec)
        check(f"{os.path.basename(path)}: skin slot uses presets/2", MATERIALS.is_skin_preset(ids.get("skin")), ids.get("skin"))
        check(f"{os.path.basename(path)}: assignments validate", MATERIALS.validate_assignments(spec["materials"]) == [])

    ok = all(RESULTS)
    print(f"[test_skin_presets] {'PASS' if ok else 'FAIL'} {sum(RESULTS)}/{len(RESULTS)}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
