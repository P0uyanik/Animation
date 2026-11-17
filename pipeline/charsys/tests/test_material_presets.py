"""Plain-Python validation for the T-015 material library and character opt-ins."""
import json
import os
import sys


HERE = os.path.dirname(os.path.abspath(__file__))
CHARSYS = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(CHARSYS, "..", ".."))
sys.path.insert(0, CHARSYS)

import spec as SPEC  # noqa: E402
from materials import builder as MATERIALS  # noqa: E402


EXPECTED = {
    "felt", "wool yarn", "fleece", "cotton knit", "woven cotton", "denim", "felt hair",
    "boot fleece", "buttons/plastic", "glasses/acrylic", "skin-felt",
}
FIBRE_ENABLED = {"felt", "wool yarn", "fleece", "cotton knit", "felt hair", "boot fleece"}
FIBRE_FIELDS = {"enabled", "density_per_cm2", "length_mm", "curl", "lean", "lod",
                "color_variation", "lean_variation", "root_transparency", "tip_transparency"}  # T-026 look fields
RESULTS = []


def check(name, ok, detail=None):
    RESULTS.append(bool(ok))
    suffix = "" if detail is None else f" {detail}"
    print(f"[test_material_presets] {'PASS' if ok else 'FAIL'} {name}{suffix}")


def main():
    library = MATERIALS.load_library()
    check("preset names", set(library["presets"]) == EXPECTED, sorted(library["presets"]))
    check("library validates", MATERIALS.validate_library(library) == [])
    for name in EXPECTED:
        preset = MATERIALS.resolve_preset(name, library=library)
        check(f"{name}: reference-scaled bump", preset["fibre"]["distance_fraction"] >= 0 and
              preset["fibre"]["scale_per_reference"] > 0)
        check(f"{name}: fibre schema", set(preset["fibres"]) == FIBRE_FIELDS)
        check(f"{name}: fibre enable", preset["fibres"]["enabled"] is (name in FIBRE_ENABLED))
        check(f"{name}: wide LOD is quarter density", preset["fibres"]["lod"] == 0.25)
    check("non-fibrous surfaces disable fibres", all(not library["presets"][name].get("fibres", {}).get("enabled", False)
                                                      for name in ("skin-felt", "buttons/plastic", "glasses/acrylic")))

    girl_path = os.path.join(ROOT, "assets", "characters", "girl_auburn_bun_glasses", "spec",
                             "girl_auburn_bun_glasses.spec.json")
    girl, _ = SPEC.load(girl_path)
    assignments = girl["materials"]["assignments"]
    check("girl opts into only requested slots", set(assignments) == {"skin", "glasses", "glasses_lens", "hair", "hair_band",
                                                                "hair_flower", "hair_flower_centre"},  # T-016 groom slots
          sorted(assignments))
    check("girl skin preset", assignments["skin"]["preset"] == "skin-felt")
    check("girl glasses presets", assignments["glasses"]["preset"] == "buttons/plastic" and
          assignments["glasses_lens"]["preset"] == "glasses/acrylic")
    check("girl hair preset (T-033: felted hair, was wool yarn in T-016)", assignments["hair"]["preset"] == "felt hair")

    boy_path = os.path.join(ROOT, "assets", "characters", "boy_yellow_hoodie", "spec",
                            "boy_yellow_hoodie.spec.json")
    boy = json.load(open(boy_path))
    check("boy has no material preset opt-in", "assignments" not in boy.get("materials", {}))

    override_path = os.path.join(ROOT, "docs", "evaluation", "materials", "T-015", "legacy_materials.override.json")
    before, _ = SPEC.load(girl_path, (override_path,))
    check("before override disables all opt-ins", before["materials"]["assignments"] is None)

    invalid = json.loads(json.dumps(girl))
    invalid["materials"]["assignments"]["skin"]["preset"] = "not-a-preset"
    try:
        SPEC.validate(invalid)
        rejected = False
    except ValueError:
        rejected = True
    check("unknown preset rejected", rejected)

    ok = all(RESULTS)
    print(f"[test_material_presets] {'ALL PASS' if ok else 'FAILURES'} ({sum(RESULTS)}/{len(RESULTS)})")
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
