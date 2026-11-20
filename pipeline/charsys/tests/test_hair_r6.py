"""Plain-Python tests for hair round 6 (T-160: groom/5, groom_r6.py). No Blender.

    python3 pipeline/charsys/tests/test_hair_r6.py

Covers: groom_r6 declares groom/5 and the registry maps groom/5 to it (groom/4 stays on groom_r5); a hair spec
without groom/5 keys is lowered to itself with no jobs, so groom/4 specs build as before; no file under
assets/characters pins groom/5; "stand" and "tips" are stripped into reshape jobs with the right object names and
ring sizes; malformed keys are refused; the reshape keeps every vertex count, removes the twist and the centre-line
jitter of a standing petal ("stand"), and thins / flattens / calms only the end of a lock ("tips"); the T-160
overrides (if present) validate."""
import copy
import glob
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CHARSYS = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(CHARSYS, "..", ".."))
sys.path.insert(0, CHARSYS)

import groom_r5 as G5  # noqa: E402
import groom_r6 as G6  # noqa: E402
import versions as V  # noqa: E402

Vector = G6.Vector

RESULTS = []


def check(name, ok, detail=None):
    RESULTS.append(bool(ok))
    print(f"[test_hair_r6] {'PASS' if ok else 'FAIL'} {name}{'' if detail is None else ' ' + str(detail)}")


def tube(n=30, seg=12, twist=0.0, jitter=0.0, radius=0.02, flat=0.6):
    """A straight vertical test tube (rings root -> tip, poles): optional twist per ring and centre jitter."""
    rings = []
    for i in range(n):
        c = Vector((jitter * math.sin(i * 2.1), jitter * math.cos(i * 1.7), 0.01 * i))
        a0 = twist * i
        rings.append([c + Vector((math.cos(a0 + 2 * math.pi * k / seg) * radius,
                                  math.sin(a0 + 2 * math.pi * k / seg) * radius * flat, 0.0)) for k in range(seg)])
    return rings, (Vector((0, 0, -0.005)), Vector((0, 0, 0.01 * (n - 1) + 0.005)))


def ring_angle(ring):
    c = sum(ring, Vector()) / len(ring)
    d = ring[0] - c
    return math.atan2(d.y, d.x)


def ring_size(ring):
    c = sum(ring, Vector()) / len(ring)
    return max((v - c).length for v in ring)


def main():
    # ---- registry
    check("groom_r6 declares groom/5", G6.GENERATOR == "groom/5" and "groom/5" in G6.GENERATOR_VERSIONS)
    check("registry: groom/5 -> groom_r6, groom/4 -> groom_r5",
          V.load("groom", "groom/5") is G6 and V.load("groom", "groom/4") is G5)
    pins = []
    for p in glob.glob(os.path.join(ROOT, "assets", "characters", "**", "*.json"), recursive=True):
        try:
            txt = open(p).read()
        except OSError:
            continue
        if '"groom/5"' in txt:
            pins.append(os.path.relpath(p, ROOT))
    check("no file under assets/characters pins groom/5 (opt-in overrides only)", not pins, pins[:3] or None)

    # ---- lowering
    plain = {"generator": "groom/5", "structures": [
        {"type": "scalp_cap", "name": "cap"},
        {"type": "masses", "name": "crown", "items": [{"root": [0, 80], "tip": [0, 60]}]},
        {"type": "locks", "name": "back", "count": 2, "az": [120, 240], "z_end": [0.4, 0.45], "width": 0.04,
         "thick": 0.03}]}
    low, jobs = G6.lower(plain)
    check("spec without groom/5 keys: lowered to itself, no jobs", low is plain and jobs == [])
    sp = copy.deepcopy(plain)
    sp["structures"][1]["stand"] = {"smooth": 9}
    sp["structures"][1]["seg"] = 20
    sp["structures"][2].update(tips={"scale": 0.3}, mirror=True, stagger={"z_end": [0.0, 0.03]},
                               felt={"seg": 16}, finish="felt")
    low, jobs = G6.lower(sp)
    check("keys stripped from the lowered spec, other data kept",
          all(k not in s for s in low["structures"] for k in G6.R6_KEYS)
          and low["structures"][0] is sp["structures"][0] and low["structures"][2]["stagger"] == {"z_end": [0.0, 0.03]}
          and "stand" in sp["structures"][1])
    check("jobs: masses -> hair_<name> with its seg; staggered mirrored locks -> one object per lock, felt seg",
          jobs[0] == {"structure": "crown", "objects": ["hair_crown"], "seg": 20, "stand": {"smooth": 9}}
          and jobs[1]["objects"] == ["hair_back_00", "hair_back_01", "hair_back_r00", "hair_back_r01"]
          and jobs[1]["seg"] == 16 and jobs[1]["tips"] == dict(G6.TIPS_DEFAULT, scale=0.3), jobs)
    yarn = copy.deepcopy(sp)
    yarn["structures"][2]["finish"] = "yarn"
    check("yarn locks use the yarn ring size", G6.lower(yarn)[1][1]["seg"] == 12)

    # ---- validation
    def errs_with(idx, **kw):
        s = copy.deepcopy(plain)
        s["structures"][idx].update(kw)
        return [e for e in G6.validate(s) if "stand" in e or "tips" in e]
    check("refused: stand on locks", errs_with(2, stand={"smooth": 4}))
    check("refused: stand.smooth out of range / not int", errs_with(1, stand={"smooth": 99})
          and errs_with(1, stand={"smooth": 2.5}) and errs_with(1, stand={"passes": 3}))
    check("refused: tips on a scalp_cap", errs_with(0, tips={}))
    check("refused: tips values out of range / unknown key", errs_with(2, tips={"from": 0.99})
          and errs_with(2, tips={"scale": 2}) and errs_with(2, tips={"flatten": 1.0})
          and errs_with(2, tips={"power": 0}) and errs_with(2, tips={"taper": 1}))
    check("accepted: valid stand and tips", not errs_with(1, stand={"smooth": 0}, tips={"round": 0.5})
          and not errs_with(2, tips={"from": 0.5, "scale": 0.2, "power": 1.3, "flatten": 0.4, "calm": 0.5}))

    # ---- reshape: stand
    rings, poles = tube(twist=0.25, jitter=0.004)
    new, npoles = G6.reshape_island(rings, poles, stand={"smooth": 14})
    check("stand: ring and vertex counts unchanged", len(new) == len(rings) and all(len(a) == len(b) for a, b in zip(new, rings)))
    tw_old = abs(ring_angle(rings[-1]) - ring_angle(rings[0]) + 0.25 * 0) + 0.25 * (len(rings) - 1)
    span = [abs((ring_angle(r) - ring_angle(new[0]) + math.pi) % (2 * math.pi) - math.pi) for r in new]
    check("stand: no twist about the centre line (built: %.1f rad)" % tw_old, max(span) < 0.12, round(max(span), 4))

    def wobble(rs):
        cs = [sum(r, Vector()) / len(r) for r in rs]
        return max(((cs[i - 1] + cs[i + 1]) * 0.5 - cs[i]).length for i in range(1, len(cs) - 1))
    check("stand: centre-line jitter smoothed", wobble(new) < 0.15 * wobble(rings), (round(wobble(rings), 5), round(wobble(new), 5)))
    check("stand: section size kept, ends stay in place",
          all(abs(ring_size(a) - ring_size(b)) < 1e-4 for a, b in zip(new, rings))
          and (sum(new[0], Vector()) / 12 - sum(rings[0], Vector()) / 12).length < 1e-9
          and (npoles[0] - poles[0]).length < 4e-3)

    # ---- reshape: tips
    rings, poles = tube()
    tp = dict(G6.TIPS_DEFAULT, **{"from": 0.5, "scale": 0.25, "flatten": 0.4})
    new, npoles = G6.reshape_island(rings, poles, tips=tp)
    half = len(rings) // 2
    check("tips: unchanged before 'from'", all((a - b).length < 1e-9 for i in range(half) for a, b in zip(new[i], rings[i])))
    sizes = [ring_size(r) for r in new]
    check("tips: thins steadily to scale x size at the tip",
          all(sizes[i + 1] <= sizes[i] + 1e-9 for i in range(half, len(sizes) - 1))
          and abs(sizes[-1] / ring_size(rings[-1]) - 0.25) < 1e-6, round(sizes[-1] / ring_size(rings[-1]), 4))

    def depth(r):
        c = sum(r, Vector()) / len(r)
        return max(abs((v - c).y) for v in r)
    check("tips: depth flattened by a further (1 - flatten)",
          abs(depth(new[-1]) / depth(rings[-1]) - 0.25 * 0.6) < 1e-6, round(depth(new[-1]) / depth(rings[-1]), 4))
    check("tips: tip pole follows the last ring", (npoles[1] - poles[1]).length < 0.01 and (npoles[0] - poles[0]).length < 1e-9)
    rings, poles = tube(jitter=0.006)
    new, _ = G6.reshape_island(rings, poles, tips=dict(G6.TIPS_DEFAULT, **{"from": 0.5, "scale": 1.0, "calm": 1.0}))
    c_old = [sum(r, Vector()) / 12 for r in rings]
    c_new = [sum(r, Vector()) / 12 for r in new]
    check("tips.calm: centre line calmer at the end, untouched at the root",
          (c_new[3] - c_old[3]).length < 1e-6 and (c_new[-4] - c_old[-4]).length > 1e-3)
    s_round = G6.tip_scale(1.0, dict(G6.TIPS_DEFAULT, scale=0.8, round=0.5))[0]
    check("tips.round: rounded end closes the tip", s_round < 0.1, round(s_round, 4))

    # ---- islands
    isl = G6.islands(7, [(0, 1), (1, 2), (3, 4), (5, 6), (4, 5)])
    check("islands: connected runs in order", isl == [[0, 1, 2], [3, 4, 5, 6]], isl)

    # ---- T-160 overrides
    for p in sorted(glob.glob(os.path.join(ROOT, "docs", "evaluation", "characters", "T-160", "overrides", "*.json"))):
        o = json.load(open(p))["override"]
        errs = G6.validate(o["hair"]) if o.get("generators", {}).get("groom") == "groom/5" else ["not groom/5"]
        low, jobs = G6.lower(o["hair"])
        check(f"override {os.path.basename(p)}: groom/5, validates, has reshape jobs", not errs and jobs,
              errs[:2] or len(jobs))

    n_fail = RESULTS.count(False)
    print(f"[test_hair_r6] {len(RESULTS) - n_fail}/{len(RESULTS)} passed")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
