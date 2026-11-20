"""Plain-Python tests for hair round 6 (T-160: groom/5, groom_r6.py). No Blender.

    python3 pipeline/charsys/tests/test_hair_r6.py

Covers: groom_r6 declares groom/5 and the registry maps groom/5 to it (groom/4 stays on groom_r5); a hair spec
without groom/5 keys is lowered to itself with no jobs, so groom/4 specs build as before; no file under
assets/characters pins groom/5 (except the owner-approved candidates listed in
owner_approved_candidates.json, feature groom/5; R3, owner ~22:00Z); "stand" and "tips" are stripped into reshape jobs with the right object names and
ring sizes; malformed keys are refused; the reshape keeps every vertex count, removes the twist and the centre-line
jitter of a standing petal ("stand"), and thins / flattens / calms only the end of a lock ("tips"); the T-160
overrides (if present) validate. T-167 "clump": lowering, validation, zero setting is the identity, deterministic,
differs per clump index and seed, root fixed, bend / lumps / twist within their bounds; the T-167 overrides validate."""
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

sys.path.insert(0, HERE)
import test_guard_allowlist as GA  # noqa: E402

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
    pins, _allowed, aerr = GA.split(pins, "groom/5")  # R3 owner allowance (2026-11-20 ~22:00Z item 2)
    check("owner-approved candidate allowlist is valid", not aerr, aerr[:3])
    check("no file under assets/characters pins groom/5 (opt-in overrides only; except listed owner-approved candidates)",
          not pins, pins[:3] or None)
    neg = ["assets/characters/boy_yellow_hoodie/spec/boy_yellow_hoodie.98.7.6.spec.json",
           "assets/characters/boy_yellow_hoodie/versions/2.2.0/spec.json"]
    check("negative: a non-listed file pinning groom/5 still fails the guard", GA.split(neg, "groom/5")[0] == neg)

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

    # ---- clump (T-167)
    cl = dict(G6.CLUMP_DEFAULT, bend_m=0.01, twist_deg=40, lumps=0.2)
    sp = copy.deepcopy(plain)
    sp["structures"][1]["clump"] = {"bend_m": 0.01}
    low, jobs = G6.lower(sp)
    check("clump: stripped into a job with defaults filled in",
          "clump" not in low["structures"][1] and jobs[0]["clump"] == dict(G6.CLUMP_DEFAULT, bend_m=0.01), jobs)

    def cl_errs(idx, **kw):
        s2 = copy.deepcopy(plain)
        s2["structures"][idx]["clump"] = kw
        return [e for e in G6.validate(s2) if "clump" in e]
    check("clump refused: on a scalp_cap, out of range, unknown key, non-int seed", cl_errs(0, bend_m=0.01)
          and cl_errs(1, bend_m=0.2) and cl_errs(1, twist_deg=-5) and cl_errs(1, lumps=0.9)
          and cl_errs(1, lump_wavelength=0) and cl_errs(1, wander=1) and cl_errs(1, seed=1.5))
    check("clump accepted: masses and locks", not cl_errs(1, **cl) and not cl_errs(2, bend_m=0.004, seed=3))
    rings, poles = tube()
    same, spoles = G6.reshape_island(rings, poles, clump=dict(G6.CLUMP_DEFAULT), index=3)
    check("clump: all-zero setting leaves every vertex in place",
          all((a - b).length < 1e-9 for ra, rb in zip(same, rings) for a, b in zip(ra, rb))
          and all((a - b).length < 1e-9 for a, b in zip(spoles, poles)))
    new, npoles = G6.reshape_island(rings, poles, clump=cl, index=0)
    again, _ = G6.reshape_island(rings, poles, clump=cl, index=0)
    other, _ = G6.reshape_island(rings, poles, clump=cl, index=1)
    seeded, _ = G6.reshape_island(rings, poles, clump=dict(cl, seed=5), index=0)
    check("clump: ring and vertex counts unchanged",
          len(new) == len(rings) and all(len(a) == len(b) for a, b in zip(new, rings)))
    check("clump: deterministic (same index -> same positions)",
          all(a == b for ra, rb in zip(new, again) for a, b in zip(ra, rb)))

    def centre(r):
        return sum(r, Vector()) / len(r)
    d_tip = (centre(new[-1]) - centre(other[-1])).length
    check("clump: neighbours differ (index), and with the seed", d_tip > 1e-3
          and (centre(new[-1]) - centre(seeded[-1])).length > 1e-4, round(d_tip, 5))
    check("clump: root ring stays in place, root pole too",
          all((a - b).length < 1e-9 for a, b in zip(new[0], rings[0])) and (npoles[0] - poles[0]).length < 1e-9)
    off = [(centre(a) - centre(b)).length for a, b in zip(new, rings)]
    bound = 0.01 * 1.5 * 2
    check("clump: bend bounded by bend_m x 3 and grows from the root", max(off) <= bound + 1e-9 and off[2] < 0.1 * max(off),
          (round(max(off), 5), round(off[2], 6)))
    ratio = [ring_size(a) / ring_size(b) for a, b in zip(new, rings)]
    check("clump: section size within 1 +- lumps, and it varies", max(ratio) <= 1.2 + 1e-6 and min(ratio) >= 0.8 - 1e-6
          and max(ratio) - min(ratio) > 0.1, (round(min(ratio), 3), round(max(ratio), 3)))
    tw = abs((ring_angle(new[-1]) - ring_angle(rings[-1]) + math.pi) % (2 * math.pi) - math.pi)
    check("clump: twist at the tip within twist_deg", 0.0 < tw <= math.radians(40) + 1e-6, round(math.degrees(tw), 2))
    vals = [G6.clump_values(k) for k in range(40)]
    check("clump_values: in 0..1, no two clumps of 40 alike", all(0 <= x < 1 for v in vals for x in v)
          and len({tuple(round(x, 3) for x in v) for v in vals}) == 40)
    both, _ = G6.reshape_island(rings, poles, tips=tp, clump=cl, index=0)
    check("clump with tips: the end still thins", ring_size(both[-1]) < 0.4 * ring_size(rings[-1]))

    # ---- islands
    isl = G6.islands(7, [(0, 1), (1, 2), (3, 4), (5, 6), (4, 5)])
    check("islands: connected runs in order", isl == [[0, 1, 2], [3, 4, 5, 6]], isl)

    # ---- T-160 / T-167 overrides
    ev = os.path.join(ROOT, "docs", "evaluation", "characters")
    for p in sorted(glob.glob(os.path.join(ev, "T-160", "overrides", "*.json"))
                    + glob.glob(os.path.join(ev, "T-167", "overrides", "*.override.json"))
                    + glob.glob(os.path.join(ev, "T-167", "overrides", "not_selected", "*.override.json"))):
        o = json.load(open(p))["override"]
        errs = G6.validate(o["hair"]) if o.get("generators", {}).get("groom") == "groom/5" else ["not groom/5"]
        low, jobs = G6.lower(o["hair"])
        check(f"override {os.path.basename(p)}: groom/5, validates, has reshape jobs", not errs and jobs,
              errs[:2] or len(jobs))

    # ---- T-167 final selection: boy pinned to hair r6 (byte copy of the T-160 override), girls r7
    bp = os.path.join(ev, "T-167", "overrides", "bundle.json")
    if os.path.exists(bp):
        sel = json.load(open(bp))["overrides"]
        files = {c: os.path.join(ev, "T-167", "overrides", v["file"]) for c, v in sel.items()}
        check("bundle: three characters, every file exists", len(sel) == 3 and all(map(os.path.exists, files.values())),
              sorted(sel))
        check("bundle: boy r6, girls r7", sorted(v["hair"] for v in sel.values()) == ["r6", "r7", "r7"]
              and [v["hair"] for c, v in sel.items() if c.startswith("boy")] == ["r6"])
        for c, v in sel.items():
            if v["hair"] == "r6":
                src = os.path.join(ev, "T-160", "overrides", v["file"])
                check(f"bundle: {c} r6 pin is a byte copy of the T-160 override",
                      os.path.exists(src) and open(src, "rb").read() == open(files[c], "rb").read())
        top = [os.path.basename(p) for p in glob.glob(os.path.join(ev, "T-167", "overrides", "*.override.json"))]
        check("bundle: overrides/ holds exactly the selected files", sorted(top) == sorted(v["file"] for v in sel.values()),
              top)

    n_fail = RESULTS.count(False)
    print(f"[test_hair_r6] {len(RESULTS) - n_fail}/{len(RESULTS)} passed")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
