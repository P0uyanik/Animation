"""Plain-Python tests for hair round 4 (T-091: groom/3, groom_r4.py). No Blender.

    python3 pipeline/charsys/tests/test_hair_r4.py

Covers: groom_r4 declares groom/3 and the registry maps groom/3 to it; the T-091 candidate overrides validate and pin
groom/3 on the current approved specs; the round-4 targets are in the data (boy: fewer, larger masses than round 3,
rising crown petals; girl: centre parting with two swept sections per side, back sections, narrower and tapered
ringlets, a gathered scrunchie); malformed masses/scrunchie/directional specs are refused; masses rooted inside the
face keep-out are refused; no published character spec pins groom/3; groom/1 and groom/2 specs still validate."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CHARSYS = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(CHARSYS, "..", ".."))
sys.path.insert(0, CHARSYS)

import groom_hybrid as GH  # noqa: E402
import groom_r4 as G4  # noqa: E402
import versions as V  # noqa: E402

RESULTS = []
CHARS = {"boy": ("boy_yellow_hoodie", "boy_yellow_hoodie.2.0.0.spec.json"),
         "girl": ("girl_auburn_bun_glasses", "girl_auburn_bun_glasses.0.11.0.spec.json")}


def check(name, ok, detail=None):
    RESULTS.append(bool(ok))
    print(f"[test_hair_r4] {'PASS' if ok else 'FAIL'} {name}{'' if detail is None else ' ' + str(detail)}")


def spec_of(key):
    cid, f = CHARS[key]
    return json.load(open(os.path.join(ROOT, "assets", "characters", cid, "spec", f)))


def candidate(key, tag="hair_r4"):
    cid = CHARS[key][0]
    p = os.path.join(ROOT, "assets", "characters", cid, "spec", "candidates", "T-091", f"{cid}.{tag}.override.json")
    return json.load(open(p))["override"] if os.path.exists(p) else None


def by_name(hs, name):
    return next((s for s in hs["structures"] if s.get("name") == name), None)


def n_masses(st, spec_hair=None):
    return len(st.get("items") or []) + sum(int(r["count"]) for r in st.get("rows") or [])


def merged_hair(key, ov):
    import spec as SPEC
    return SPEC.deep_merge(spec_of(key), ov)["hair"]


def main():
    check("groom_r4 declares groom/3", "groom/3" in G4.GENERATOR_VERSIONS)
    e = V.REGISTRY.entry("groom", "groom/3")
    check("registry: groom/3 is implemented by groom_r4", e["module"] == "groom_r4", e["module"])

    for key in CHARS:
        ov = candidate(key)
        check(f"{key}: T-091 candidate present", ov is not None)
        if ov is None:
            continue
        check(f"{key}: candidate pins groom/3", ov["generators"]["groom"] == "groom/3"
              and ov["hair"]["generator"] == "groom/3")
        hs = merged_hair(key, ov)
        errs = G4.validate(hs)
        check(f"{key}: merged candidate hair validates", not errs, errs[:3])
        dov = candidate(key, "hair_r4_dirfibres")
        if dov is not None:
            dh = merged_hair(key, dov)
            check(f"{key}: directional-fibre variant validates and only adds the flag",
                  not G4.validate(dh) and dh["fibres"]["directional"]["enabled"] is True
                  and dh["structures"] == hs["structures"])
        spec = spec_of(key)
        check(f"{key}: approved spec does not pin groom/3",
              (spec.get("generators") or {}).get("groom") != "groom/3" and spec["hair"].get("generator") != "groom/3")
        check(f"{key}: approved spec (groom/2) still validates", not GH.validate(spec["hair"]))

    # boy: fewer, larger masses than round 3 (groom/2 clumps of the approved 2.0.0 spec)
    old = spec_of("boy")["hair"]
    old_n = sum(int(r["count"]) for s in old["structures"] if s["type"] == "clumps" for r in s["rows"])
    old_w = [sum(r["width"]) / 2 for s in old["structures"] if s["type"] == "clumps" for r in s["rows"]]
    boy = merged_hair("boy", candidate("boy"))
    ms = [s for s in boy["structures"] if s["type"] == "masses"]
    new_n = sum(n_masses(s) for s in ms)
    widths = [(sum(p["width"]) / 2 if isinstance(p["width"], list) else p["width"])
              for s in ms for p in (s.get("items") or []) + (s.get("rows") or [])]
    check("boy: fewer masses than round-3 clumps", 0 < new_n < old_n, (new_n, old_n))
    check("boy: masses larger than round-3 clumps (mean width)",
          sum(widths) / len(widths) > sum(old_w) / len(old_w), (round(sum(widths) / len(widths), 3),
                                                                 round(sum(old_w) / len(old_w), 3)))
    check("boy: masses are deep (depth >= 0.5)", all(float(p.get("depth", 0.8)) >= 0.5 for s in ms
                                                       for p in (s.get("items") or []) + (s.get("rows") or [])))
    check("boy: no groom/2 clumps left", not any(s["type"] == "clumps" for s in boy["structures"]))
    crown = by_name(boy, "crown")
    check("boy: crown petals rise (rising lift, tip higher than root)",
          crown is not None and all(len(it["lift"]) == 2 and it["lift"][1] > it["lift"][0] + 0.04
                                    for it in crown["items"]))

    # girl: centre parting, two swept sections per side, soft back transition, narrower, tapered, scrunchie
    g_old = spec_of("girl")["hair"]
    girl = merged_hair("girl", candidate("girl"))
    check("girl: crown part at the centre (az 0)", float(by_name(girl, "crown")["part"]["az"]) == 0.0)
    fr = by_name(girl, "fringe")
    roots = [it["root"][0] for it in fr["items"]]
    check("girl: two swept fringe sections per side of the parting",
          sum(a > 0 for a in roots) == 2 and sum(a < 0 for a in roots) == 2, roots)
    check("girl: fringe sections are mirrored", sorted(roots) == sorted(-a for a in roots))
    check("girl: no groom/2 felt fringe or sweep strands left",
          not any(by_name(girl, n) for n in ("fringe_part", "fringe_sweep")) and fr["type"] == "masses")
    check("girl: back sections present (soft transition into the ringlets)",
          by_name(girl, "back_sections") is not None and by_name(girl, "back_sections")["type"] == "masses")
    rings = [s for s in girl["structures"] if s["type"] == "locks"]
    old_rings = {s["name"]: s for s in g_old["structures"] if s["type"] == "locks"}
    check("girl: ringlets narrower (hang radii below 0.11.0)",
          all(s["hang_radii"][0] < old_rings[s["name"]]["hang_radii"][0] for s in rings))
    check("girl: ringlets taper (end_scale <= 0.6, tip radius < 1)",
          all(float(s["end_scale"]) <= 0.6 and float(s["curl"]["tip"]["radius"]) < 1.0 for s in rings))
    check("girl: curtain narrower than 0.11.0",
          by_name(girl, "curtain")["rest_radii"][0] < by_name(g_old, "curtain")["rest_radii"][0])
    sc = by_name(girl, "band")
    check("girl: the band is a gathered scrunchie", sc is not None and sc["type"] == "scrunchie"
          and int(sc["gathers"]) >= 6)
    check("girl: dynamics chains still name existing structures", not GH.validate_dynamics(
        dict(girl, structures=[dict(s, type="clumps") if s["type"] == "masses" else s for s in girl["structures"]])))

    # refusals
    base = {"structures": [{"type": "scalp_cap", "name": "cap"}], "face_keepout": {"az": 34, "el_min": 0}}

    def errs_with(*sts):
        return G4.validate(dict(base, structures=base["structures"] + list(sts)))

    check("masses without items/rows refused", any("items" in e for e in errs_with({"type": "masses", "name": "m"})))
    check("mass depth out of range refused", any("depth" in e for e in errs_with(
        {"type": "masses", "name": "m", "items": [{"root": [90, 30], "tip": [90, 0], "depth": 3}]})))
    check("mass without tip refused", any("tip" in e for e in errs_with(
        {"type": "masses", "name": "m", "items": [{"root": [90, 30]}]})))
    check("mass rooted inside the face keep-out refused", any("keep-out" in e for e in errs_with(
        {"type": "masses", "name": "m", "items": [{"root": [5, -10], "tip": [5, -30]}]})))
    check("scrunchie without a bun refused", any("bun" in e for e in errs_with(
        {"type": "scrunchie", "name": "s", "bun": 0})))
    check("bad directional flag refused", any("directional" in e for e in G4.validate(
        dict(base, fibres={"directional": {"enabled": "yes"}}))))
    check("valid minimal masses spec accepted", not errs_with(
        {"type": "masses", "name": "m", "items": [{"root": [90, 30], "tip": [90, 0], "width": 0.08}]}))

    # the base spec and every override never pin groom/3 (versioned specs may: the owner made boy 2.1.0 / girl 0.12.0,
    # which pin it, current on 2026-11-19 through T-094; candidates are opt-in)
    pinned = []
    for c in CHARS.values():
        d = os.path.join(ROOT, "assets", "characters", c[0], "spec")
        for f in os.listdir(d):
            if not f.endswith(".json"):
                continue
            versioned = f.endswith(".spec.json") and f != c[0] + ".spec.json"
            if versioned:
                continue  # a version spec: candidates are opt-in, approved ones were approved by the owner
            if "groom/3" in open(os.path.join(d, f)).read():
                pinned.append(f)
    check("no base spec or override outside candidates/ pins groom/3", not pinned, pinned)

    ok = all(RESULTS)
    print(f"[test_hair_r4] {'ALL PASS' if ok else 'FAILED'} ({sum(RESULTS)}/{len(RESULTS)})")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
