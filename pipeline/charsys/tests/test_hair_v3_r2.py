"""Plain-Python tests for hair v3 round 2 (T-070: groom/2 changes in pipeline/charsys/groom_hybrid.py). No Blender.

    python3 pipeline/charsys/tests/test_hair_v3_r2.py

Covers: the T-070 candidate specs (docs/evaluation/characters/T-070/candidates) validate and pin groom/2; the new
opt-in data is validated (clump lift [root, peak, tip] + lift_peak; fibre layer shaft_radius_mm / tip_ratio); specs
without the new keys (the T-044 candidates) still validate unchanged; no published character spec pins groom/2."""
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CHARSYS = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(CHARSYS, "..", ".."))
sys.path.insert(0, CHARSYS)

import groom_hybrid as GH  # noqa: E402

EVAL = os.path.join(ROOT, "docs", "evaluation", "characters")
RESULTS = []


def check(name, ok, detail=None):
    RESULTS.append(bool(ok))
    print(f"[test_hair_v3_r2] {'PASS' if ok else 'FAIL'} {name}{'' if detail is None else ' ' + str(detail)}")


def load(task, key):
    p = os.path.join(EVAL, task, "candidates", f"{key}.hair_v3.json")
    return json.load(open(p)) if os.path.exists(p) else None


def main():
    for key in ("boy", "girl", "third"):
        c = load("T-070", key)
        check(f"T-070 {key}: candidate present", c is not None)
        if c is None:
            continue
        hs = c["overrides"]["hair"]
        errs = GH.validate(hs)
        check(f"T-070 {key}: candidate validates", not errs, errs[:3])
        check(f"T-070 {key}: candidate pins groom/2", c["overrides"]["generators"]["groom"] == "groom/2")
        spec = json.load(open(os.path.join(ROOT, c["character_spec"])))
        if not c["character_spec"].startswith("docs/"):
            check(f"T-070 {key}: published spec does not pin groom/2",
                  (spec.get("generators") or {}).get("groom") != "groom/2"
                  and (spec.get("hair") or {}).get("generator") != "groom/2")
        old = load("T-044", key)
        if old is not None:
            check(f"T-044 {key}: round-1 candidate still validates (new keys are opt-in)",
                  not GH.validate(old["overrides"]["hair"]))

    base = load("T-070", "boy")["overrides"]["hair"]
    arched = [s for s in base["structures"] if s["type"] == "clumps"
              and any(len(r.get("lift", [])) == 3 for r in s["rows"])]
    check("boy candidate uses the arched lift", bool(arched))
    bad = copy.deepcopy(base)
    clumps = next(s for s in bad["structures"] if s["type"] == "clumps")
    clumps["rows"][0]["lift"] = [0.0, 0.01, 0.02, 0.03]
    check("lift with 4 values rejected", any("lift must be" in e for e in GH.validate(bad)))
    bad = copy.deepcopy(base)
    clumps = next(s for s in bad["structures"] if s["type"] == "clumps")
    clumps["rows"][0]["lift_peak"] = 1.2
    check("lift_peak outside 0.05..0.95 rejected", any("lift_peak" in e for e in GH.validate(bad)))

    third = load("T-070", "third")["overrides"]["hair"]
    check("third candidate uses fixed fibre shafts",
          all("shaft_radius_mm" in layer for layer in third["fibres"]["layers"]))
    bad = copy.deepcopy(third)
    bad["fibres"]["layers"][0]["shaft_radius_mm"] = 0.0
    check("zero shaft radius rejected", any("shaft_radius_mm" in e for e in GH.validate(bad)))
    bad = copy.deepcopy(third)
    bad["fibres"]["layers"][0]["tip_ratio"] = 1.5
    check("tip_ratio above 1 rejected", any("tip_ratio" in e for e in GH.validate(bad)))

    ok = all(RESULTS)
    print(f"[test_hair_v3_r2] {'ALL PASS' if ok else 'FAILED'} ({sum(RESULTS)}/{len(RESULTS)})")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
