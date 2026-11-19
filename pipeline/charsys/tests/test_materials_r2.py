"""Plain-Python checks for the T-092 presets/3 family (pipeline/charsys/materials/presets_r2.json).

    python3 pipeline/charsys/tests/test_materials_r2.py

1. the library validates (schema, family presets/3, the presets/1 rules, the skin and warmth rules), every id ends in
   /3 and none reuses a presets/1 or presets/2 id; the six T-092 ids exist;
2. presets/1 and presets/2 resolve exactly as on the input SHA: every id's resolved preset (defaults merged) hashes to
   the digest in materials/r2_frozen_graphs.json's "resolved" section, its family is unchanged and library_for still
   returns its own file; presets.json and skin_presets.json carry no presets/3 id;
3. one uniform fibre halo per fabric preset: fibres enabled with a uniform look (colour variation <= 0.2, lean
   variation <= 0.6, root and tip fade), quiet clumps (nap value gain <= 0.15) and quiet albedo breakup
   (micro-relief colour <= 0.15) - the noisy/speckled audit findings; the skin has no fibre curves;
4. skin-felt/3: non-emissive, warm crease and warmth tints, a red-led subsurface radius, the warmth stronger and wider
   than the crease, and the validator rejects a glowing, cold or over-strong warmth;
5. the light rigs: character_warm_indoor/1 lives in this task's r2_lights.json, loads with render_calibration.load,
   has the neutral rig's directions and keeps its front-facing luminance; render_calibration.json is untouched;
6. the T-092 candidate overrides validate through spec.load on top of their base specs and differ from them
   only in material keys (materials.assignments.* and garment material / materials.* entries); every presets/3 id
   they name resolves; no generator pin is changed.
"""
import copy
import glob
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CHARSYS = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(CHARSYS, "..", ".."))
sys.path.insert(0, CHARSYS)

import render_calibration as RC  # noqa: E402
import spec as SPEC  # noqa: E402
from materials import builder as MATERIALS  # noqa: E402

GOLDEN = os.path.join(CHARSYS, "materials", "r2_frozen_graphs.json")
R2_IDS = {"hoodie fleece/3", "trouser pile/3", "vest felt/3", "cuff fleece/3", "brushed cotton/3", "skin-felt/3"}
RESULTS = []


def check(name, ok, detail=None):
    RESULTS.append(bool(ok))
    print(f"[test_materials_r2] {'PASS' if ok else 'FAIL'} {name}" + ("" if detail is None else f" {detail}"))


def resolved_digest(name):
    return hashlib.sha256(json.dumps(MATERIALS.resolve_preset(name), sort_keys=True).encode()).hexdigest()


def material_paths(a, b, path=""):
    """Paths where two specs differ (dicts recursed, lists recursed index-wise when equally long)."""
    if isinstance(a, dict) and isinstance(b, dict):
        out = []
        for k in sorted(set(a) | set(b), key=str):
            out += material_paths(a.get(k), b.get(k), f"{path}.{k}")
        return out
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        out = []
        for i, (x, y) in enumerate(zip(a, b)):
            out += material_paths(x, y, f"{path}[{i}]")
        return out
    return [] if a == b else [path]


def is_material_path(path):
    if path.startswith(".materials.assignments."):
        return True
    if path.startswith(".clothing.garments["):
        rest = path.split("]", 1)[1]
        return rest.startswith(".material.") or rest == ".material" or rest.startswith(".materials.")
    return False


def main():
    # 1. library
    r2 = MATERIALS.load_r2_library()
    check("schema / family", r2["schema"] == MATERIALS.R2_SCHEMA and r2["family"] == "presets/3")
    check("the six T-092 ids", set(r2["presets"]) == R2_IDS, sorted(r2["presets"]))
    v1, v2 = MATERIALS.load_library(), MATERIALS.load_skin_library()
    check("no id reused from presets/1 or presets/2", not (set(r2["presets"]) & (set(v1["presets"]) | set(v2["presets"]))))
    check("validator clean", MATERIALS.validate_r2_library(r2) == [])
    check("presets.json and skin_presets.json name no presets/3 id",
          not any(n.endswith("/3") for n in list(v1["presets"]) + list(v2["presets"])))

    # 2. presets/1 and presets/2 resolve as on the input SHA
    golden = json.load(open(GOLDEN, encoding="utf-8"))
    frozen = list(v1["presets"]) + list(v2["presets"])
    check("resolved digests cover every presets/1 and presets/2 id", sorted(golden["resolved"]) == sorted(frozen))
    for name in frozen:
        check(f"{name}: resolves as on input {golden['input_sha']}", golden["resolved"].get(name) == resolved_digest(name))
        fam = MATERIALS.preset_family(name)
        check(f"{name}: family unchanged", fam == ("presets/2" if name in v2["presets"] else "presets/1"), fam)
    for name in v1["presets"]:
        check(f"{name}: library_for returns presets.json", MATERIALS.library_for(name)["schema"] == MATERIALS.SCHEMA)

    # 3. fabric presets: one uniform halo, quiet clumps and albedo
    for name, raw in r2["presets"].items():
        p = MATERIALS.resolve_preset(name)
        check(f"{name}: family tag presets/3", p.get("family") == "presets/3" and MATERIALS.is_r2_preset(name))
        if "skin" in raw:
            continue
        f = p["fibres"]
        check(f"{name}: fibre halo enabled", f["enabled"] and f["density_per_cm2"] > 0 and f["length_mm"] > 0)
        check(f"{name}: uniform halo (colour variation <= 0.2, lean variation <= 0.6)",
              f["color_variation"] <= 0.2 and f["lean_variation"] <= 0.6, (f["color_variation"], f["lean_variation"]))
        check(f"{name}: soft root and tip fade", f["root_transparency"] > 0 and f["tip_transparency"] > 0)
        check(f"{name}: quiet clumps (nap value gain <= 0.15)",
              not p["nap"]["enabled"] or p["nap"]["value_gain"] <= 0.15, p["nap"]["value_gain"])
        check(f"{name}: quiet albedo breakup (micro colour <= 0.15, lumps <= 0.06)",
              p["micro_relief"]["color_strength"] <= 0.15 and p["surface_detail"]["lump_albedo"] <= 0.06)
    for name in ("trouser pile/3", "vest felt/3"):
        p, old = MATERIALS.resolve_preset(name), MATERIALS.resolve_preset("fleece" if "trouser" in name else "felt")
        check(f"{name}: quieter than its presets/1 predecessor",
              p["micro_relief"]["color_strength"] < old["micro_relief"]["color_strength"] and
              p["fibre"]["strength"] < old["fibre"]["strength"] and
              p["fibres"]["color_variation"] < old["fibres"]["color_variation"])

    # 4. skin
    s = MATERIALS.resolve_preset("skin-felt/3")
    skin = s["skin"]
    check("skin-felt/3: non-emissive", skin["emission"] is False)
    check("skin-felt/3: no fibre curves", s["fibres"]["enabled"] is False)
    check("skin-felt/3: red-led subsurface radius", skin["subsurface_radius"][0] > skin["subsurface_radius"][1] >
          skin["subsurface_radius"][2])
    for part in ("crease", "warmth"):
        t = skin[part]["tint_srgb"]
        check(f"skin-felt/3: {part} tint warm (R >= G >= B)", t[0] >= t[1] >= t[2], t)
    check("skin-felt/3: warmth wider than the crease", skin["warmth"]["distance_fraction"] > skin["crease"]["distance_fraction"])
    s2 = MATERIALS.resolve_preset("skin-felt/2")
    check("skin-felt/3: warmer than skin-felt/2 (redder radius, lower white sheen)",
          skin["subsurface_radius"][2] <= s2["skin"]["subsurface_radius"][2] and
          s["surface"]["sheen_weight"] <= s2["surface"]["sheen_weight"])
    check("skin fuzz target below 3/255", s["targets"]["fuzz_rms_y255"]["range"][1] <= 3.0)
    bad = copy.deepcopy(r2)
    bad["presets"]["skin-felt/3"]["skin"]["emission"] = True
    bad["presets"]["skin-felt/3"]["skin"]["warmth"].update({"tint_srgb": [120, 160, 230], "strength": 0.9})
    errs = MATERIALS.validate_r2_library(bad)
    check("validator rejects emission, a cold and an over-strong warmth",
          any("emission" in e for e in errs) and any("warm (R >= G >= B)" in e for e in errs) and
          any("at most 0.6" in e for e in errs), errs)
    clash = copy.deepcopy(r2)
    clash["presets"]["felt"] = clash["presets"]["vest felt/3"]
    check("validator rejects a reused presets/1 id", any("must not reuse" in e for e in MATERIALS.validate_r2_library(clash)))
    asg = {"assignments": {"skin": {"preset": "skin-felt/3", "base_color_srgb": [236, 190, 166]}}}
    check("assignment with a presets/3 id validates", MATERIALS.validate_assignments(asg) == [])
    asg["assignments"]["skin"]["preset"] = "skin-felt/4"
    check("unknown id still rejected", MATERIALS.validate_assignments(asg) != [])

    # 5. lights
    lights = os.path.join(CHARSYS, "materials", "r2_lights.json")
    warm = RC.load("character_warm_indoor/1", lights)
    neutral = RC.load()
    check("warm rig loads from this task's file", warm["name"] == "character_warm_indoor/1")
    same_geo = all((a["azimuth_deg"], a["elevation_deg"], a["angle_deg"]) == (b["azimuth_deg"], b["elevation_deg"],
                                                                              b["angle_deg"])
                   for a, b in zip(warm["lights"], neutral["lights"])) and len(warm["lights"]) == len(neutral["lights"])
    check("warm rig keeps the neutral directions and softness", same_geo)

    def lum(prof):
        y = 0.0
        for L in prof["lights"]:
            r, g, b = RC.kelvin_rgb(L["kelvin"])
            y += L["strength"] * (0.2126 * r + 0.7152 * g + 0.0722 * b)
        return y
    check("warm rig keeps the neutral light luminance (+-3 %)", abs(lum(warm) / lum(neutral) - 1) <= 0.03,
          round(lum(warm) / lum(neutral), 4))
    check("warm rig is warmer", all(a["kelvin"] < b["kelvin"] for a, b in zip(warm["lights"], neutral["lights"])))
    check("render_calibration.json has no T-092 rig", "character_warm_indoor/1" not in
          json.load(open(RC.PATH, encoding="utf-8"))["profiles"])

    # 6. candidate overrides
    baseline = json.load(open(os.path.join(ROOT, "docs", "evaluation", "characters", "fidelity_baseline.json")))
    found = sorted(glob.glob(os.path.join(ROOT, "assets", "characters", "*", "spec", "candidates", "T-092",
                                          "*.override.json")))
    check("one T-092 candidate per character", sorted(json.load(open(p))["character_id"] for p in found) ==
          ["boy_yellow_hoodie", "girl_auburn_bun_glasses"], [os.path.relpath(p, ROOT) for p in found])
    for path in found:
        data = json.load(open(path))
        entry = baseline["characters"][data["character_id"]]
        # The candidate is built on its own "base" spec (T-092: 2.0.0 / 0.11.0); compare against that, not against
        # whatever is approved now (T-094 made 2.1.0 / 0.12.0 current on 2026-11-19).
        if data.get("base"):
            build, base = os.path.join(ROOT, data["base"]), []
        else:
            build, base = os.path.join(ROOT, entry["build"]), [os.path.join(ROOT, p) for p in entry.get("overrides", [])]
        approved, _ = SPEC.load(build, base)
        cand, _ = SPEC.load(build, base + [path])  # validates assignments and pins
        name = os.path.basename(path)
        check(f"{name}: top-level keys only materials / clothing", set(data["override"]) <= {"materials", "clothing"})
        check(f"{name}: clothing carries only garments", set(data["override"].get("clothing", {})) <= {"garments"})
        diffs = material_paths(approved, cand)
        check(f"{name}: differs from the approved spec only in material keys",
              diffs and all(is_material_path(p) for p in diffs), [p for p in diffs if not is_material_path(p)])
        check(f"{name}: generator pins unchanged", approved.get("generators") == cand.get("generators"))
        ids = [a["preset"] for a in cand["materials"]["assignments"].values()]
        for g in cand["clothing"]["garments"]:
            ids.append(g["material"]["preset"])
            ids += [m["preset"] for m in (g.get("materials") or {}).values()]
        check(f"{name}: every preset id resolves", all(MATERIALS.is_known_preset(i) for i in ids),
              [i for i in ids if not MATERIALS.is_known_preset(i)])
        check(f"{name}: opts into presets/3", any(MATERIALS.is_r2_preset(i) for i in ids))

    ok = all(RESULTS)
    print(f"[test_materials_r2] {'PASS' if ok else 'FAIL'} {sum(RESULTS)}/{len(RESULTS)}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
