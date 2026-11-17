"""Plain-Python tests for hair v3 (groom/2, pipeline/charsys/groom_hybrid.py, T-044). No Blender needed.

    python3 pipeline/charsys/tests/test_hair_v3.py

Covers: the module declares groom/2 and leaves groom/1 (groom.py) untouched and still declaring only groom/1; the
three T-044 candidate specs validate; the face keep-out is enforced as spec data (locks rooted in the face window and
felt fringe tips below the brow line are rejected; a malformed keep-out is rejected); clumps rows, curtains and felt
bows are validated; dynamics may name clumps (one chain per clump) but not unknown structures; the candidates pin
groom/2 while the characters' published specs stay on their old groom versions."""
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CHARSYS = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(CHARSYS, "..", ".."))
sys.path.insert(0, CHARSYS)

import groom as G1  # noqa: E402
import groom_hybrid as GH  # noqa: E402

CAND = os.path.join(ROOT, "docs", "evaluation", "characters", "T-044", "candidates")
RESULTS = []


def check(name, ok, detail=None):
    RESULTS.append(bool(ok))
    print(f"[test_hair_v3] {'PASS' if ok else 'FAIL'} {name}{'' if detail is None else ' ' + str(detail)}")


def candidates():
    out = {}
    for key in ("boy", "girl", "third"):
        p = os.path.join(CAND, f"{key}.hair_v3.json")
        if os.path.exists(p):
            out[key] = json.load(open(p))
    return out


def main():
    check("groom_hybrid declares groom/2", GH.GENERATOR_VERSIONS == ("groom/2",) and GH.GENERATOR == "groom/2")
    check("groom.py still declares only groom/1", G1.GENERATOR_VERSIONS == ("groom/1",) and G1.GENERATOR == "groom/1")
    check("groom/1 builder table unchanged by importing groom/2",
          set(G1.BUILDERS) == {"sweep", "fringe", "locks", "bun", "tie", "bow", "flowers", "felt_volume"},
          sorted(G1.BUILDERS))
    check("groom/2 adds clumps, curtain, felt_bow", GH.HYBRID_TYPES == {"clumps", "curtain", "felt_bow"}
          and GH.HYBRID_TYPES <= set(GH.BUILDERS))

    cands = candidates()
    check("three candidate specs present", set(cands) == {"boy", "girl", "third"}, sorted(cands))
    for key, c in cands.items():
        hs = c["overrides"]["hair"]
        errs = GH.validate(hs)
        check(f"{key}: candidate validates", not errs, errs[:3])
        check(f"{key}: candidate pins groom/2", c["overrides"]["generators"]["groom"] == "groom/2"
              and hs["generator"] == "groom/2")
        check(f"{key}: face keep-out is spec data", isinstance(hs.get("face_keepout"), dict))
        sp = json.load(open(os.path.join(ROOT, c["character_spec"])))
        if c["character_spec"].startswith("assets/"):
            check(f"{key}: published spec keeps its old groom version",
                  sp["hair"].get("generator") in ("hair_clumps/1", "hair_clumps/2", "groom/1")
                  and (sp.get("generators") or {}).get("groom") in (None, "groom/1", "hair_clumps/1"),
                  sp["hair"].get("generator"))
        groups = (hs.get("dynamics") or {}).get("structures", {})
        names = {s.get("name", s["type"]): s["type"] for s in hs["structures"]}
        check(f"{key}: every dynamics group is a clumps/locks/bun structure",
              all(names.get(g) in GH.CHAIN_TYPES for g in groups), {g: names.get(g) for g in groups})

    if "girl" in cands:
        base = cands["girl"]["overrides"]["hair"]
        bad = copy.deepcopy(base)
        bad["structures"].append({"type": "locks", "name": "face_lock", "style": "straight", "count": 1,
                                  "az": [-10, 10], "el_root": [20, 30], "hang_radii": [0.2, 0.2], "z_end": [0.6, 0.6],
                                  "width": 0.03, "thick": 0.02})
        check("keep-out rejects a lock rooted in the face window",
              any("face keep-out" in e for e in GH.validate(bad)))
        bad = copy.deepcopy(base)
        fr = next(s for s in bad["structures"] if s.get("name") == "fringe")
        fr["tip_el"] = [-20] + fr["tip_el"][1:]
        check("keep-out rejects a fringe tip below the brow line", any("fringe tip" in e for e in GH.validate(bad)))
        bad = copy.deepcopy(base)
        bad["face_keepout"] = {"az": 30}
        check("malformed keep-out rejected", any("face_keepout" in e for e in GH.validate(bad)))
        ok = copy.deepcopy(base)
        ok.pop("face_keepout")
        ok["structures"].append({"type": "locks", "name": "face_lock", "style": "straight", "count": 1,
                                 "az": [-10, 10], "el_root": [20, 30], "hang_radii": [0.2, 0.2], "z_end": [0.6, 0.6],
                                 "width": 0.03, "thick": 0.02})
        check("without a keep-out the same lock is allowed (opt-in)", not GH.validate(ok), GH.validate(ok)[:2])
        bad = copy.deepcopy(base)
        bad["structures"].append({"type": "felt_bow", "name": "bow2", "bun": 5})
        check("felt bow on a missing bun rejected", any("bun 5" in e for e in GH.validate(bad)))
        bad = copy.deepcopy(base)
        bad["structures"].append({"type": "felt_bow", "name": "bow3"})
        check("felt bow without a place rejected", any("felt_bow" in e for e in GH.validate(bad)))
        bad = copy.deepcopy(base)
        bad["structures"].append({"type": "curtain", "name": "c2", "az": [90, 270]})
        check("curtain needs root_el and z_end", sum("(curtain)" in e for e in GH.validate(bad)) == 2)
    if "boy" in cands:
        base = cands["boy"]["overrides"]["hair"]
        bad = copy.deepcopy(base)
        bad["structures"].append({"type": "clumps", "name": "x", "rows": [{"count": 2, "flow": "sideways"}]})
        errs = GH.validate(bad)
        check("clumps rows: missing keys and unknown flow rejected",
              any("needs 'az'" in e for e in errs) and any("flow must be" in e for e in errs), errs[:3])
        bad = copy.deepcopy(base)
        bad["dynamics"]["structures"]["nonexistent"] = {"bones": 2}
        check("dynamics on an unknown structure rejected", any("nonexistent" in e for e in GH.validate(bad)))
        check("dynamics on clumps accepted", "crown" in base["dynamics"]["structures"] and not GH.validate(base))
        check("groom/1 still rejects clumps (behaviour unchanged)",
              any("unknown" in e for e in G1.validate(base)))
    ok = all(RESULTS)
    print(f"[test_hair_v3] {'ALL PASS' if ok else 'FAILURES'} ({sum(RESULTS)}/{len(RESULTS)})")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
