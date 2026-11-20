"""Plain-Python tests for hair round 5 (T-118: groom/4, groom_r5.py). No Blender.

    python3 pipeline/charsys/tests/test_hair_r5.py

Covers: groom_r5 declares groom/4 and the registry maps groom/4 to it (groom/3 stays on groom_r4); a hair spec
without groom/4 features is lowered to itself, so the current specs build as before; no character spec pins groom/4;
ring rows are lowered to explicit groom/3 masses without random numbers (bearings, stagger, channel gap); staggered
locks become single-lock structures with different end heights and keep their dynamics settings and curl
directions; malformed ring/stagger/turn specs are refused; the T-118 candidates validate and hold the round-5
targets (boy: taller crown petals of different heights, channels in every ring tier, fringe over the eyes ends
higher; girl: lower outer sweeps, staggered tapered curl ends, flower turned to the front quarter)."""
import copy
import glob
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CHARSYS = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(CHARSYS, "..", ".."))
sys.path.insert(0, CHARSYS)

import groom_r4 as G4  # noqa: E402
import groom_r5 as G5  # noqa: E402
import spec as SPEC  # noqa: E402
import versions as V  # noqa: E402

sys.path.insert(0, HERE)
import test_guard_allowlist as GA  # noqa: E402

RESULTS = []
CHARS = {"boy": ("boy_yellow_hoodie", "boy_yellow_hoodie.2.1.0.spec.json"),
         "girl": ("girl_auburn_bun_glasses", "girl_auburn_bun_glasses.0.12.0.spec.json")}


def check(name, ok, detail=None):
    RESULTS.append(bool(ok))
    print(f"[test_hair_r5] {'PASS' if ok else 'FAIL'} {name}{'' if detail is None else ' ' + str(detail)}")


def spec_of(key):
    cid, f = CHARS[key]
    return json.load(open(os.path.join(ROOT, "assets", "characters", cid, "spec", f)))


def candidate(key):
    cid = CHARS[key][0]
    p = os.path.join(ROOT, "docs", "evaluation", "characters", "T-118", "candidates", f"{cid}.hair_r5.override.json")
    return json.load(open(p))["override"] if os.path.exists(p) else None


def by_name(hs, name):
    return next((s for s in hs["structures"] if s.get("name") == name), None)


def angle(a, b):
    return math.degrees(math.acos(max(-1.0, min(1.0, sum(x * y for x, y in zip(a, b))))))


RING = {"type": "masses", "name": "ring", "rows": [
    {"count": 6, "pole": {"az": 180, "el": 60}, "ring": {"radius_deg": 20, "around": [-180, 180]}, "len_deg": 40,
     "width": 0.2, "hold": 0.4, "lift": [0.0, 0.04, 0.03], "depth": 0.7, "channel": {"gap": 0.25},
     "stagger": {"len": [1.0, 0.5], "lift": [1.0, 2.0, 0.5], "width": [1.0, 0.9]}}]}
LOCKS = {"type": "locks", "name": "curls", "style": "curly", "count": 3, "az": [100, 160], "el_root": [0, 5],
         "hang_radii": [0.17, 0.15], "z_end": [0.4, 0.44], "width": 0.04, "thick": 0.03, "mirror": True,
         "end_scale": 0.5, "curl": {"radius": 0.02, "pitch": 0.09},
         "stagger": {"z_end": [0.0, 0.05, -0.03], "end_scale": [1.0, 0.8], "mirror_shift": 1}}


def hair(*sts, **kw):
    return dict({"generator": "groom/4", "structures": [{"type": "scalp_cap", "name": "cap"}] + list(sts)}, **kw)


WAVY = {"type": "locks", "name": "waves", "style": "wavy", "count": 3, "az": [100, 160], "el_root": [0, 5],
        "hang_radii": [0.17, 0.15], "z_end": [0.4, 0.44], "width": 0.04, "thick": 0.03, "mirror": True,
        "wave": {"amplitude": 0.015, "wavelength": 0.12, "depth": 0.3},
        "stagger": {"z_end": [0.0, 0.05], "phase_deg": [0, 30]}}


def third_character():
    """T-126b: designed wave phase and the hair-surface accessory seat (generic), and the third character's override."""
    low, info = G5.lower(hair(WAVY))
    locks = [s for s in low["structures"] if s["type"] == "locks"]
    check("wave phase: staggered wavy locks validate", G5.validate(hair(WAVY)) == [], G5.validate(hair(WAVY)))
    check("wave phase: every lock is built straight and carries its designed wave",
          len(locks) == 6 and all(s["wave"]["amplitude"] == 0.0 and s[G5.WAVE_KEY]["amplitude"] == 0.015
                                  and s[G5.WAVE_KEY]["wavelength"] == 0.12 and s[G5.WAVE_KEY]["depth"] == 0.3
                                  for s in locks))
    check("wave phase: the list repeats over the locks; the mirrored side adds 180 degrees",
          [s[G5.WAVE_KEY]["phase_deg"] for s in locks] == [0, 30, 0, 180, 210, 180])
    check("wave phase: the source spec is not changed by lowering", WAVY["wave"]["amplitude"] == 0.015
          and G5.WAVE_KEY not in WAVY)
    plain = dict(WAVY, stagger={"z_end": [0.0, 0.05]})
    check("wave phase: staggered locks without phase_deg keep the groom/3 wave (no designed wave)",
          all(G5.WAVE_KEY not in s and s["wave"]["amplitude"] == 0.015
              for s in G5.lower(hair(plain))[0]["structures"] if s["type"] == "locks"))
    curly = dict(LOCKS, stagger=dict(LOCKS["stagger"], phase_deg=[0, 30]))
    check("wave phase: refused on locks that are not wavy", any("phase_deg" in e for e in G5.validate(hair(curly))))
    check("wave phase: an empty phase list is refused",
          G5.validate(hair(dict(WAVY, stagger={"phase_deg": []}))) != [])
    check("wave phase: depth outside 0..1 is refused",
          G5.validate(hair(dict(WAVY, wave=dict(WAVY["wave"], depth=1.5)))) != [])
    bow = {"type": "felt_bow", "name": "bow", "az": -40, "el": 45, "out": 0.004, "size": 0.1}
    check("accessory seat: \"hair\" validates on a felt bow", G5.validate(hair(dict(bow, seat="hair"))) == [])
    check("accessory seat: an unknown seat is refused",
          any("seat" in e for e in G5.validate(hair(dict(bow, seat="scalp_top")))))
    check("accessory seat: a spec with only a seat is still a groom/3 spec for the build (lowered to itself)",
          G5.lower(hair(dict(bow, seat="hair")))[0]["structures"][1].get("seat") == "hair"
          and not G5.lower(hair(dict(bow, seat="hair")))[1])
    src = open(os.path.join(CHARSYS, "groom_r5.py")).read()
    names = [os.path.basename(os.path.dirname(os.path.dirname(p))) for p in
             glob.glob(os.path.join(ROOT, "assets", "characters", "*", "references", ""))]
    check("groom_r5 names no character", names and not any(n in src for n in names), names)
    p = os.path.join(ROOT, "docs", "evaluation", "characters", "T-126", "hair", "candidates",
                     "girl_white_hair_blue_dress.hair.override.json")
    if not os.path.exists(p):
        return
    ov = json.load(open(p))["override"]
    hs = ov["hair"]
    check("third: the override changes only generators.groom and hair, and pins groom/4",
          set(ov) == {"generators", "hair"} and ov["generators"] == {"groom": "groom/4"} and hs["generator"] == "groom/4")
    check("third: the hair validates", G5.validate(hs) == [], G5.validate(hs)[:3])
    buns = by_name(hs, "buns")["buns"]
    check("third: two top buns, mirrored, wrapped in opposite directions",
          len(buns) == 2 and buns[0]["az"] == -buns[1]["az"] and buns[0]["el"] >= 45
          and {b["wrap"] for b in buns} == {"cw", "ccw"} and all(b["turns"] >= 1 for b in buns))
    wav = [s for s in hs["structures"] if s["type"] == "locks"]
    check("third: every lock structure is wavy with a designed phase, staggered tapered ends",
          len(wav) >= 4 and all(s["style"] == "wavy" and s["stagger"].get("phase_deg") and s["stagger"].get("z_end")
                                and s["end_scale"] < 0.6 for s in wav))
    back = by_name(hs, "back_locks")["stagger"]["phase_deg"]
    check("third: neighbouring back locks wave roughly together (phase spread under a quarter wave)",
          max(((a - b + 180) % 360) - 180 for a in back for b in back) <= 90, back)
    check("third: fringe clumps and wavy side locks in front of the ears",
          len(by_name(hs, "fringe")["items"]) >= 5 and by_name(hs, "side_locks").get("mirror")
          and by_name(hs, "side_locks")["az"][0] > hs["face_keepout"]["az"])
    bw = by_name(hs, "bow")
    tails = [l for l in bw["loops"] if 180 < l["angle_deg"] % 360 < 360]
    check("third: a felt bow (two loops, two shorter and narrower tails), seated on the hair surface",
          bw["type"] == "felt_bow" and bw.get("seat") == "hair" and len(bw["loops"]) == 4 and len(tails) == 2
          and all(t["width"] < l["width"] and t["length"] < l["length"] for t in tails for l in bw["loops"]
                  if l not in tails) and not any(s["type"] == "flowers" for s in hs["structures"]))
    low, info = G5.lower(hs)
    dyn = low["dynamics"]["structures"]
    check("third: every lowered lock keeps a dynamics chain setting; buns have one",
          all(s["name"] in dyn for s in low["structures"] if s["type"] == "locks") and "buns" in dyn)


def main():
    check("groom_r5 declares groom/4", G5.GENERATOR_VERSIONS == ("groom/4",))
    check("registry: groom/4 is implemented by groom_r5", V.REGISTRY.entry("groom", "groom/4")["module"] == "groom_r5")
    check("registry: groom/3 is still implemented by groom_r4",
          V.REGISTRY.entry("groom", "groom/3")["module"] == "groom_r4" and G4.GENERATOR_VERSIONS == ("groom/3",))
    check("registry: groom/4 loads", V.REGISTRY.load("groom", "groom/4") is G5)

    # default builds: the current specs use no groom/4 feature and are lowered to themselves
    for key in CHARS:
        sp = spec_of(key)
        check(f"{key}: current spec pins groom/3", sp["generators"]["groom"] == "groom/3")
        low, info = G5.lower(sp["hair"])
        check(f"{key}: current hair is lowered to itself (groom/4 build = groom/3 build)", low is sp["hair"] and not info)
        check(f"{key}: current hair validates as groom/4 with the groom/3 result",
              G5.validate(sp["hair"]) == G4.validate(sp["hair"]) == [])
    pinned = []
    for p in glob.glob(os.path.join(ROOT, "assets", "characters", "**", "*.json"), recursive=True):
        try:
            d = json.load(open(p))
        except ValueError:
            continue
        g = (d.get("generators") or {}).get("groom") if isinstance(d, dict) else None
        g = g or ((d.get("override") or {}).get("generators") or {}).get("groom") if isinstance(d, dict) else None
        if g == "groom/4":
            pinned.append(os.path.relpath(p, ROOT))
    pinned, allowed, aerr = GA.split(pinned, "groom/4")
    check("owner-approved candidate allowlist is valid (T-154)", not aerr, aerr[:3])
    check("no file under assets/characters pins groom/4 (except listed owner-approved candidates)", not pinned, pinned[:3])

    # ring rows
    items, info = G5.ring_items(RING["rows"][0], 0.15)
    fr = G5.ring_frame({"az": 180, "el": 60})
    roots = [G5.direction(*it["root"]) for it in items]
    tips = [G5.direction(*it["tip"]) for it in items]
    check("ring: one explicit mass per count", len(items) == 6 and all("ring" not in it for it in items))
    check("ring: roots lie radius_deg from the pole", all(abs(angle(r, fr[0]) - 20) < 0.01 for r in roots),
          [round(angle(r, fr[0]), 3) for r in roots])
    check("ring: stagger.len repeats over the masses (40, 20, 40, ...)",
          all(abs(angle(t, fr[0]) - (60 if k % 2 == 0 else 40)) < 0.01 for k, t in enumerate(tips)))
    check("ring: stagger.lift scales the peak and tip lift, not the root",
          [it["lift"] for it in items[:3]] == [[0.0, 0.04, 0.03], [0.0, 0.08, 0.06], [0.0, 0.02, 0.015]])
    check("ring: bearing 0 points to the face, +90 to the left",
          G5.az_el(G5.ring_dir(fr, 30, 0))[1] > 60 and G5.ring_dir(fr, 30, 90)[0] > 0.4
          and G5.ring_dir(G5.ring_frame({"az": 0, "el": 90}), 30, 0)[1] < -0.4)
    share = [0.15 * math.sin(math.radians(20 + L * 0.4)) * math.radians(60) for L in (40, 20)]
    check("ring: channel limits the width to (1 - gap) of the share at the end of the hold",
          all(abs(it["width"] - 0.75 * share[k % 2]) < 1e-4 for k, it in enumerate(items)),
          [it["width"] for it in items[:2]])
    check("ring: channel narrows the root and reports the smallest gap",
          all(0.15 <= it["root_width"] < 1 for it in items) and abs(info["channel_min_gap_m"] - 0.25 * share[1]) < 1e-3)
    check("ring: lowering is deterministic", G5.ring_items(RING["rows"][0], 0.15) == (items, info))
    low, info = G5.lower(hair(RING), 0.15)
    st = by_name(low, "ring")
    check("ring: lowered structure is plain groom/3 (items only) and validates",
          "rows" not in st and len(st["items"]) == 6 and G4.validate(low) == [] and G5.validate(hair(RING)) == [])
    mixed = copy.deepcopy(RING)
    mixed["rows"].append({"count": 2, "az": [100, 140], "el": [10, 20], "len_deg": [30, 40]})
    st = by_name(G5.lower(hair(mixed))[0], "ring")
    check("ring: groom/3 rows of the same structure are kept", len(st["rows"]) == 1 and len(st["items"]) == 6)

    # staggered locks
    dyn = {"enabled": True, "structures": {"curls": {"bones": 3}}}
    low, info = G5.lower(hair(LOCKS, dynamics=dyn))
    subs = [s for s in low["structures"] if s["type"] == "locks"]
    check("locks: one structure per lock and side", [s["name"] for s in subs] ==
          ["curls_00", "curls_01", "curls_02", "curls_r00", "curls_r01", "curls_r02"] and info["staggered_locks"] == {"curls": 6})
    check("locks: z_end offsets repeat; mirror_shift moves the right side along the list",
          [s["z_end"][0] for s in subs] == [0.4, 0.45, 0.37, 0.45, 0.37, 0.4], [s["z_end"][0] for s in subs])
    check("locks: end_scale factors apply", [s["end_scale"] for s in subs[:3]] == [0.5, 0.4, 0.5])
    check("locks: each lock keeps its azimuth slot (right side mirrored)",
          subs[1]["az"] == [120.0, 140.0] and subs[4]["az"] == [-120.0, -140.0] and all(
              s["count"] == 1 and "mirror" not in s and "stagger" not in s for s in subs))
    check("locks: curl directions alternate as in the unlowered structure",
          [s["curl"]["direction"] for s in subs] == ["ccw", "cw", "ccw", "cw", "ccw", "cw"])
    check("locks: dynamics settings follow the lowered names",
          set(low["dynamics"]["structures"]) == {s["name"] for s in subs} and G5.validate(hair(LOCKS, dynamics=dyn)) == [])
    check("lower does not change its input", "stagger" in LOCKS and "curls" in dyn["structures"])

    # refusals
    def bad(st):
        return bool(G5.validate(hair(st)))
    r = RING["rows"][0]
    check("refused: stagger without ring", bad(dict(RING, rows=[{k: v for k, v in r.items() if k != "ring"}])))
    check("refused: ring without radius_deg", bad(dict(RING, rows=[dict(r, ring={"around": [0, 90]})])))
    check("refused: ring spanning more than 360 degrees", bad(dict(RING, rows=[dict(r, ring={"radius_deg": 20, "around": [0, 400]})])))
    check("refused: channel gap outside 0..0.8", bad(dict(RING, rows=[dict(r, channel={"gap": 0.9})])))
    check("refused: unknown or non-positive stagger entries",
          bad(dict(RING, rows=[dict(r, stagger={"depth": [1]})])) and bad(dict(RING, rows=[dict(r, stagger={"len": [0]})])))
    check("refused: malformed locks stagger", bad(dict(LOCKS, stagger={"z_end": 0.1})) and bad(dict(LOCKS, stagger={"zz": [1]})))
    fl = {"type": "flowers", "name": "flowers", "bun": 0, "items": [{"around_deg": 30, "turn": {"toward": [20], "amount": 0.5}}]}
    bun = {"type": "bun", "name": "bun", "buns": [{"az": 180, "el": 80, "radius": 0.1, "height": 0.1}]}
    check("refused: malformed flower turn", bool(G5.validate(hair(bun, fl))))
    fl["items"][0]["turn"] = {"toward": [20, 30], "amount": 0.5}
    check("accepted: flower turn", G5.validate(hair(bun, fl)) == [], G5.validate(hair(bun, fl))[:2])
    bow = {"type": "felt_bow", "name": "bow", "az": 60, "el": 60, "loops": [{"angle_deg": 0, "length": 0.03, "width": 0.02,
                                                                             "thick": 0.01}]}
    check("accepted: felt_bow turn and flower attach (one attachment rule for both accessories)",
          G5.validate(hair(bun, dict(bow, turn={"toward": [30, 20], "amount": 0.5}), dict(fl, items=[dict(
              fl["items"][0], attach={"az": 60, "el": 55, "out": 0.01})]))) == [])
    check("refused: malformed felt_bow turn and flower attach", bool(G5.validate(hair(bun, dict(bow, turn={"amount": 2}))))
          and bool(G5.validate(hair(bun, dict(fl, items=[dict(fl["items"][0], attach={"az": 60})])))))
    check("refused: a ring mass rooted inside the face keep-out", bool(G5.validate(hair(
        dict(RING, rows=[dict(r, pole={"az": 0, "el": 0}, ring={"radius_deg": 2, "around": [-180, 180]})]),
        face_keepout={"az": 34, "el_min": 5}))))

    # T-118 candidates
    for key in CHARS:
        ov = candidate(key)
        check(f"{key}: T-118 candidate present", ov is not None)
        if ov is None:
            continue
        check(f"{key}: candidate pins groom/4 and changes only generators.groom and hair generator/structures",
              ov["generators"] == {"groom": "groom/4"} and set(ov) == {"generators", "hair"}
              and set(ov["hair"]) == {"generator", "structures"} and ov["hair"]["generator"] == "groom/4")
        cur = spec_of(key)
        hs = SPEC.deep_merge(cur, ov)["hair"]
        errs = G5.validate(hs)
        check(f"{key}: merged candidate hair validates", not errs, errs[:3])
        low, info = G5.lower(hs)
        check(f"{key}: lowered candidate is valid groom/3 data", G4.validate(low) == [])
        check(f"{key}: dynamics structure names of the current spec still resolve",
              all(any(re.fullmatch(n + r"(_r?\d\d)?", s.get("name", "")) for s in low["structures"])
                  for n in cur["hair"]["dynamics"]["structures"]))
        if key == "boy":
            cc, nc = by_name(cur["hair"], "crown"), by_name(low, "crown")
            old = [it["lift"][-1] for it in cc["items"]]
            new = [it["lift"][-1] for it in nc["items"]]
            check("boy: crown petals are taller and of different heights",
                  max(new) > max(old) + 0.03 and len(set(new)) >= 4 and max(new) - min(new) >= 0.04, (old[:2], new))
            tiers = [by_name(hs, n)["rows"][0] for n in ("whorl", "top", "top_outer")]
            check("boy: three ring tiers round one whorl, each with a channel gap and staggered lengths",
                  all(t.get("channel", {}).get("gap", 0) >= 0.1 and len(set(t["stagger"]["len"])) >= 3 for t in tiers)
                  and len({json.dumps(t["pole"]) for t in tiers}) == 1
                  and tiers[0]["ring"]["radius_deg"] < tiers[1]["ring"]["radius_deg"] < tiers[2]["ring"]["radius_deg"])
            check("boy: every tier keeps an open channel", all(i["channel_min_gap_m"] > 0.004 for n in
                                                              ("whorl", "top", "top_outer") for i in info[n]), info)
            keep = hs["face_keepout"]
            eye = [it for it in by_name(low, "fringe")["items"] if abs(it["root"][0]) < 20]
            was = [it for it in by_name(cur["hair"], "fringe")["items"] if abs(it["root"][0]) < 20]
            check("boy: the fringe clumps over the eyes end higher and closer to the forehead (pickup sightline)",
                  all(a["tip"][1] >= b["tip"][1] + 6 and a["lift"][-1] < b["lift"][-1] for a, b in zip(eye, was))
                  and all(it["tip"][1] > keep["el_min"] for it in eye))
        else:
            fr, was = by_name(low, "fringe")["items"], by_name(cur["hair"], "fringe")["items"]
            outer = [(a, b) for a, b in zip(fr, was) if abs(b["root"][0]) > 10]
            check("girl: outer sweeps end lower and are wider", len(outer) == 2 and all(
                a["tip"][1] <= b["tip"][1] - 6 and a["width"] > b["width"] for a, b in outer))
            for n in ("ringlets_back", "ringlets_back_b"):
                ends = [s["z_end"][0] for s in low["structures"] if re.fullmatch(n + r"_\d\d", s.get("name", ""))]
                check(f"girl: {n} ends are staggered (neighbours differ, spread >= 6 cm)",
                      len(ends) == by_name(cur["hair"], n)["count"] and max(ends) - min(ends) >= 0.06
                      and all(abs(a - b) >= 0.02 for a, b in zip(ends, ends[1:])), ends)
            locks = [s for s in low["structures"] if s["type"] == "locks"]
            check("girl: every ringlet has a tapered end (end scale <= 0.4; was 0.55)",
                  all(s["end_scale"] <= 0.4 for s in locks) and by_name(cur["hair"], "ringlets_back")["end_scale"] == 0.55)
            f0, f1 = by_name(cur["hair"], "flowers")["items"][0], by_name(hs, "flowers")["items"][0]
            check("girl: one flower, nearer the front and turned to the front quarter",
                  len(by_name(hs, "flowers")["items"]) == 1 and abs(f1["around_deg"]) < abs(f0["around_deg"])
                  and 0 < f1["turn"]["toward"][0] < 45 and f1["turn"]["amount"] > 0)
    third_character()
    n = len(RESULTS)
    print(f"[test_hair_r5] {sum(RESULTS)}/{n} passed")
    return 0 if all(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
