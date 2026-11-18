"""Plain-Python tests for hair v3 round 3 (T-079: groom/2 candidate data, no generator change). No Blender.

    python3 pipeline/charsys/tests/test_hair_v3_r3.py

Covers: the T-079 candidate specs (docs/evaluation/characters/T-079/candidates) validate and pin groom/2; the round-3
targets are present in the data (boy: whorl pole at the top of the head, no arched/hooked crown tufts; girl: varied
ringlet sets and a swept fringe, four-lobe bun kept; third: blunt-tipped soft fringe); the round-1/2 candidates still
validate; no published character spec pins groom/2 (approved versions unchanged)."""
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
    print(f"[test_hair_v3_r3] {'PASS' if ok else 'FAIL'} {name}{'' if detail is None else ' ' + str(detail)}")


def load(task, key):
    p = os.path.join(EVAL, task, "candidates", f"{key}.hair_v3.json")
    return json.load(open(p)) if os.path.exists(p) else None


def structure(hs, name):
    return next((s for s in hs["structures"] if s.get("name") == name), None)


def main():
    for key in ("boy", "girl", "third"):
        c = load("T-079", key)
        check(f"T-079 {key}: candidate present", c is not None)
        if c is None:
            continue
        errs = GH.validate(c["overrides"]["hair"])
        check(f"T-079 {key}: candidate validates", not errs, errs[:3])
        check(f"T-079 {key}: candidate pins groom/2", c["overrides"]["generators"]["groom"] == "groom/2")
        if not c["character_spec"].startswith("docs/"):
            spec = json.load(open(os.path.join(ROOT, c["character_spec"])))
            check(f"T-079 {key}: published spec does not pin groom/2",
                  (spec.get("generators") or {}).get("groom") != "groom/2"
                  and (spec.get("hair") or {}).get("generator") != "groom/2")
        for task in ("T-044", "T-070"):
            old = load(task, key)
            if old is not None:
                check(f"{task} {key}: earlier candidate still validates", not GH.validate(old["overrides"]["hair"]))

    boy = load("T-079", "boy")["overrides"]["hair"]
    crown = structure(boy, "crown")
    check("boy: whorl pole at the top of the head (el >= 75)", float(crown["rows"][0]["pole"]["el"]) >= 75)
    check("boy: crown tufts rise straight (no arched/hooked lift)", len(crown["rows"][0]["lift"]) == 2)
    check("boy: whorl rosette present", structure(boy, "whorl") is not None)

    girl = load("T-079", "girl")["overrides"]["hair"]
    rings = [s for s in girl["structures"] if s["type"] == "locks" and s["name"].startswith("ringlets")]
    radii = {round(float(s["curl"]["radius"]), 4) for s in rings}
    check("girl: ringlet sets with varied coil radii", len(radii) >= 3, sorted(radii))
    check("girl: ringlets carry per-lock jitter and wobble",
          all(float(s["curl"].get("jitter", 0)) >= 0.15 and float(s["curl"].get("wobble", 0)) >= 0.15 for s in rings))
    sweep = structure(girl, "fringe_sweep")
    check("girl: swept fringe strands present", sweep is not None and sweep["rows"][0]["flow"] == "toward")
    bun = structure(girl, "bun")
    check("girl: four-lobe bun kept", len(bun["buns"][0]["felt_lobes"]) == 4)

    third = load("T-079", "third")["overrides"]["hair"]
    fr = structure(third, "fringe")
    check("third: soft fringe with blunt tips (taper_power >= 3)",
          all(float(r.get("taper_power", 2.4)) >= 3.0 for r in fr["rows"]))

    ok = all(RESULTS)
    print(f"[test_hair_v3_r3] {'ALL PASS' if ok else 'FAILED'} ({sum(RESULTS)}/{len(RESULTS)})")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
