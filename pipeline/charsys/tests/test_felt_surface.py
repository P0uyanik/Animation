"""T-110 felt surface (presets/4): plain-Python checks of the preset fields and the opt-in path (no Blender).

    python3 pipeline/charsys/tests/test_felt_surface.py

1. presets_felt.json loads and validates; every id ends in /4, extends a presets/1..3 id and carries a valid halo
   (density, length, colour factors, opacity, ...);
2. the validator refuses bad fields (each case one broken copy of the library);
3. resolution: a /4 id is its base preset + patch + halo, family presets/4, base_family of the base; felt skin/4 is
   rougher, less specular and lighter in subsurface than skin-felt/3 (the less plastic skin);
4. opt-in: every presets/1..3 id resolves exactly as from its own library, without halo or base_family;
5. registry: materials presets/4 released, declared False until merge; the candidate overrides pin presets/4 and use
   only known ids.
Exit code 1 on any failure.
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

from materials import builder as M  # noqa: E402
from materials import felt_halo as FH  # noqa: E402
import versions as V  # noqa: E402

RESULTS = []


def check(name, ok, detail=None):
    RESULTS.append(bool(ok))
    print(f"[test_felt_surface] {'PASS' if ok else 'FAIL'} {name}" + ("" if detail is None else f" {detail}"))


def broken(mutate):
    data = M._felt_raw()
    data = copy.deepcopy(data)
    mutate(data)
    return M.validate_felt_library(data)


def main():
    raw = M._felt_raw()
    check("library validates", M.validate_felt_library(raw) == [], M.validate_felt_library(raw))
    lib = M.load_felt_library()
    check("schema / family", raw["schema"] == M.FELT_SCHEMA and raw["family"] == M.FELT_FAMILY == "presets/4")
    for name, p in raw["presets"].items():
        check(f"{name}: id ends in /4", name.endswith("/4"))
        check(f"{name}: extends a presets/1..3 id", M.preset_family(p["extends"]) in ("presets/1", "presets/2", "presets/3"),
              p["extends"])
        halo = lib["presets"][name]["halo"]
        check(f"{name}: halo valid and enabled", FH.halo_errors(halo, name) == [] and halo["enabled"] is True)
        check(f"{name}: halo has density, length and colour fields",
              all(k in halo for k in ("density_per_cm2", "length_mm", "color_value", "color_saturation")))

    # 2. refusals
    first = sorted(raw["presets"])[0]
    cases = {
        "negative density": lambda d: d["presets"][first].setdefault("halo", {}).update(density_per_cm2=-1),
        "zero length": lambda d: d["presets"][first].setdefault("halo", {}).update(length_mm=0),
        "opacity above 1": lambda d: d["presets"][first].setdefault("halo", {}).update(opacity=1.5),
        "colour value out of range": lambda d: d["presets"][first].setdefault("halo", {}).update(color_value=9),
        "unknown halo field": lambda d: d["presets"][first].setdefault("halo", {}).update(glow=1),
        "enabled not boolean": lambda d: d["halo_defaults"].update(enabled=1),
        "unknown extends": lambda d: d["presets"][first].update(extends="no such preset"),
        "extends a /4 id": lambda d: d["presets"][first].update(extends=first),
        "id without /4": lambda d: d["presets"].update({"felt-x": copy.deepcopy(d["presets"][first])}),
        "id reusing presets/1": lambda d: d["presets"].update({"felt": copy.deepcopy(d["presets"][first])}),
        "unknown preset key": lambda d: d["presets"][first].update(colour=[1, 2, 3]),
        "wrong schema": lambda d: d.update(schema="plush-studio.material-presets/3"),
        "patch breaks a base rule": lambda d: d["presets"][first].setdefault("patch", {}).setdefault(
            "fibres", {}).update(lod=2.0),
        "skin patch emissive": lambda d: d["presets"]["felt skin/4"]["patch"].setdefault("skin", {}).update(emission=True),
    }
    for label, mutate in cases.items():
        errors = broken(mutate)
        check(f"refuses: {label}", bool(errors), errors[:1])

    # 3. resolution
    for name, p in raw["presets"].items():
        r = M.resolve_preset(name)
        base = M.resolve_preset(p["extends"])
        check(f"{name}: family presets/4, base_family of the base",
              r["family"] == "presets/4" and r["base_family"] == base.get("family", "presets/1"))
        expect = M.deep_merge({k: v for k, v in base.items() if k not in ("family", "name")}, p.get("patch") or {})
        same = all(r[k] == v for k, v in expect.items() if k != "description")
        check(f"{name}: base preset + patch, nothing else changed", same)
        check(f"{name}: is_felt_preset / preset_family / is_known_preset",
              M.is_felt_preset(name) and M.preset_family(name) == "presets/4" and M.is_known_preset(name))
    s3, s4 = M.resolve_preset("skin-felt/3")["surface"], M.resolve_preset("felt skin/4")["surface"]
    check("felt skin/4: rougher", s4["roughness"] > s3["roughness"], (s3["roughness"], s4["roughness"]))
    check("felt skin/4: lower specular", s4["specular_ior_level"] < s3["specular_ior_level"])
    check("felt skin/4: lighter, shorter subsurface", s4["subsurface_weight"] < s3["subsurface_weight"] and
          s4["subsurface_scale_fraction"] < s3["subsurface_scale_fraction"])
    check("felt skin/4: stays non-emissive with the skin layers", M.resolve_preset("felt skin/4")["skin"]["emission"] is False
          and M.resolve_preset("felt skin/4")["skin"]["warmth"]["enabled"])
    check("felt skin/4: skin halo finer than every fabric halo",
          all(lib["presets"]["felt skin/4"]["halo"]["length_mm"] < lib["presets"][n]["halo"]["length_mm"]
              for n in lib["presets"] if n != "felt skin/4"))
    a = {"preset": "hoodie fleece/4", "base_color_srgb": [204, 152, 62], "reference_size_m": 0.3}
    check("assignment with a /4 id validates", M.validate_assignments({"assignments": {"x": a}}) == [])
    check("halo colour is the base colour scaled (value up, saturation down)",
          FH.halo_color_srgb((204, 152, 62), {"color_value": 1.0, "color_saturation": 1.0}) == (204.0, 152.0, 62.0) and
          max(FH.halo_color_srgb((100, 50, 25), {"color_value": 1.5, "color_saturation": 0.5})) > 100)
    st = FH.halo_settings({"density_per_cm2": 40, "length_mm": 2.0, "spread": 0.5, "radius_fraction": 0.1, "lod": 0.25},
                          0.512, 0.256, "wide")
    check("halo settings scale like the surface fibres (length x k, density / k^2, wide LOD)",
          abs(st["length"] - 0.004) < 1e-9 and abs(st["density"] - 40 * 10000 / 4 * 0.25) < 1e-6, st)

    # 4. opt-in: presets/1..3 unchanged
    for loader, fam in ((M.load_library, None), (M.load_skin_library, "presets/2"), (M.load_r2_library, "presets/3")):
        lib_x = loader()
        for name in lib_x["presets"]:
            direct = M.deep_merge(M.deep_merge(lib_x["defaults"], lib_x["presets"][name]), None)
            r = M.resolve_preset(name)
            r_cmp = {k: v for k, v in r.items() if k not in ("name", "family")}
            check(f"{name}: resolves as before (no halo, family {fam or 'none'})",
                  r_cmp == direct and "halo" not in r and r.get("family") == fam and not M.is_felt_preset(name))

    # 5. registry and candidates
    e = V.REGISTRY.entry("materials", "presets/4")
    check("registry: materials presets/4 released, declared False until merge",
          e["status"] == V.RELEASED and e["declared"] is False and e["module"] == "materials.builder")
    check("registry: presets/1..3 still released", all(V.REGISTRY.entry("materials", f"presets/{n}")["status"] ==
                                                       V.RELEASED for n in (1, 2, 3)))
    paths = sorted(glob.glob(os.path.join(ROOT, "assets", "characters", "*", "spec", "candidates", "T-110", "*.json")))
    check("two candidate overrides", len(paths) == 2, paths)
    for path in paths:
        doc = json.load(open(path, encoding="utf-8"))
        ids = []

        def walk(node):
            if isinstance(node, dict):
                if isinstance(node.get("preset"), str):
                    ids.append(node["preset"])
                for v in node.values():
                    walk(v)
            elif isinstance(node, list):
                for v in node:
                    walk(v)
        walk(doc["override"])
        name = os.path.basename(path)
        check(f"{name}: pins materials presets/4", doc["override"]["generators"] == {"materials": "presets/4"})
        check(f"{name}: every preset id known", all(M.is_known_preset(i) for i in ids),
              [i for i in ids if not M.is_known_preset(i)])
        check(f"{name}: skin opts into felt skin/4", doc["override"]["materials"]["assignments"]["skin"]["preset"] ==
              "felt skin/4")
        check(f"{name}: changes only material keys", set(doc["override"]) == {"generators", "materials", "clothing"})

    print(f"[test_felt_surface] {'ALL PASS' if all(RESULTS) else 'FAIL'} ({sum(RESULTS)}/{len(RESULTS)})")
    sys.exit(0 if all(RESULTS) else 1)


if __name__ == "__main__":
    main()
