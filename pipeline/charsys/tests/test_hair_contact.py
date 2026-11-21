"""Plain-Python tests for hair contact (T-183: groom_contact.py, opt-in keys of groom/5). No Blender.

    python3 pipeline/charsys/tests/test_hair_contact.py

Covers: no published version uses the keys, and a hair spec without them takes the previous path (strip returns the
same object, groom/5 validation and lowering unchanged); the keys are validated (good forms pass, malformed ones are
refused) and taken out of what the groom/4 path sees; the ear keep-out moves every point out of the volume by the
margin, leaves far points alone, spreads the move over the neighbours and is deterministic; the capsule fit recovers
a known capsule (blob and limb), honours percentile and pad, and refuses too few vertices; the T-183 candidate
override validates on the girl's current spec and changes nothing but hair keys."""
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

import groom_contact as CT  # noqa: E402
import groom_r6 as G6  # noqa: E402
import spec as SPEC  # noqa: E402

Vector = G6.Vector
RESULTS = []
OVERRIDE = "docs/evaluation/characters/T-183/candidates/girl_auburn_bun_glasses.hair_contact.override.json"


def check(name, ok, detail=None):
    RESULTS.append(bool(ok))
    print(f"[test_hair_contact] {'PASS' if ok else 'FAIL'} {name}{'' if detail is None else ' ' + str(detail)}")


def good_contact():
    return {"segments": True, "anchored_gravity": True, "colliders": [
        {"name": "hand_l", "bone": "DEF-hand.L", "fit": "blob", "groups": ["DEF-hand.L", "DEF-f_*.L"], "solid": True},
        {"name": "forearm_l", "bone": "DEF-forearm.L", "fit": "limb", "bones": ["DEF-forearm.L", "DEF-forearm.L.001"],
         "groups": ["DEF-forearm.L*"], "percentile": 25, "pad_m": 0.002},
        {"name": "ear_l", "bone": "head", "fit": "blob", "objects": ["ear.L"]}]}


def hair(extra=None, dyn_extra=None):
    h = {"generator": "groom/5",
         "structures": [{"type": "scalp_cap", "name": "cap"}],
         "dynamics": {"enabled": True, "colliders": [{"name": "head", "type": "sphere", "bone": "head", "radius": 0.1}]}}
    h.update(extra or {})
    h["dynamics"].update(dyn_extra or {})
    return h


def main():
    # ---------------------------------------------------------------- released versions and specs without the keys
    used = []
    for p in sorted(glob.glob(os.path.join(ROOT, "assets", "characters", "*", "versions", "*", "spec*.json"))
                    + glob.glob(os.path.join(ROOT, "assets", "characters", "*", "spec", "*.json"))):
        try:
            d = json.load(open(p, encoding="utf-8"))
        except ValueError:
            continue
        h = d.get("hair") or (d.get("override") or {}).get("hair") if isinstance(d, dict) else None
        if isinstance(h, dict) and CT.has_keys(h):
            used.append(os.path.relpath(p, ROOT))
    check("no spec under assets/characters uses a T-183 key", not used, used)
    plain = hair()
    check("a hair spec without the keys: has_keys is false and strip returns the same object",
          not CT.has_keys(plain) and CT.strip(plain) is plain and CT.contact_spec(plain) is None)
    check("groom/5 lowers a spec without the keys to itself (the groom/4 path is unchanged)",
          G6.lower(CT.strip(plain))[0] is plain)
    check("validate: nothing to say without the keys", CT.validate(plain) == [])

    # ----------------------------------------------------------------------------------------- strip and validation
    full = hair({"ear_keepout": {"margin_m": 0.003}}, {"contact": good_contact()})
    before = copy.deepcopy(full)
    low = CT.strip(full)
    check("strip takes out both keys and leaves the rest", "ear_keepout" not in low and "contact" not in low["dynamics"]
          and low["structures"] is full["structures"] and low["dynamics"]["colliders"] == full["dynamics"]["colliders"])
    check("strip does not change its input", full == before)
    check("has_keys: either key alone", CT.has_keys(hair({"ear_keepout": {}})) and CT.has_keys(hair(None, {"contact": {}})))
    check("a good ear_keepout and contact block validate", CT.validate(full) == [], CT.validate(full))
    check("defaults validate (empty blocks)", CT.validate(hair({"ear_keepout": {}}, {"contact": {}})) == [])

    def refused(name, extra=None, dyn_extra=None):
        errs = CT.validate(hair(extra, dyn_extra))
        check(f"refused: {name}", bool(errs))

    refused("ear_keepout unknown key", {"ear_keepout": {"depth": 1}})
    refused("ear_keepout margin out of range", {"ear_keepout": {"margin_m": 0.5}})
    refused("ear_keepout smooth not an integer", {"ear_keepout": {"smooth": 2.5}})
    refused("ear_keepout objects empty", {"ear_keepout": {"objects": []}})
    refused("contact unknown key", None, {"contact": {"bounce": 1}})
    refused("contact segments not a bool", None, {"contact": {"segments": 1}})
    for label, change in (("no name", {"name": ""}), ("name of an existing collider", {"name": "head"}),
                          ("unknown fit", {"fit": "box"}), ("no bone", {"bone": ""}), ("percentile 0", {"percentile": 0}),
                          ("pad out of range", {"pad_m": 0.2}), ("solid not a bool", {"solid": "yes"}),
                          ("unknown key", {"radius": 0.1}), ("groups and objects", {"objects": ["ear.L"]})):
        c = good_contact()
        c["colliders"][0].update(change)
        refused(f"collider {label}", None, {"contact": c})
    c = good_contact()
    del c["colliders"][1]["bones"]
    refused("limb without bones", None, {"contact": c})
    c = good_contact()
    c["colliders"][2]["bones"] = ["head"]
    refused("blob with bones", None, {"contact": c})
    c = good_contact()
    c["colliders"].append(dict(c["colliders"][0]))
    refused("two colliders with one name", None, {"contact": c})

    # ------------------------------------------------------------------------------------------------- ear keep-out
    centre, radius, margin = Vector((0.0, 0.0, 0.0)), 0.02, 0.003
    axis = Vector((0.0, 1.0, 0.0))

    def inside(p):
        return (p - centre).length - radius

    def exits(p):
        d = p - centre
        if d.length >= radius:
            return centre + d.normalized() * (radius + margin)
        # the shorter way out along the y axis: the chord through p
        h2 = radius * radius - (d.x * d.x + d.z * d.z)
        half = math.sqrt(max(h2, 0.0))
        t = (half - d.y) if d.y >= 0 else -(half + d.y)
        return p + axis * (t + math.copysign(margin, t if t else 1.0))

    n = 21  # a flat sheet in the x-y plane through the sphere, 5 mm spacing, z = 4 mm
    pts = [Vector(((i - n // 2) * 0.005, (j - n // 2) * 0.005, 0.004)) for i in range(n) for j in range(n)]
    edges = [(i * n + j, i * n + j + 1) for i in range(n) for j in range(n - 1)] + \
            [(i * n + j, (i + 1) * n + j) for i in range(n - 1) for j in range(n)]
    for smooth in (0, 6):
        mv = CT.keepout_moves(pts, edges, inside, exits, margin, smooth)
        after = [p + mv.get(i, Vector()) for i, p in enumerate(pts)]
        worst = min(inside(p) for p in after)
        check(f"keep-out (smooth {smooth}): every point ends at least the margin outside",
              worst >= margin - 1e-9, round(worst * 1000, 3))
        was_in = [i for i, p in enumerate(pts) if inside(p) < margin]
        check(f"keep-out (smooth {smooth}): every point that was inside moved, mainly along the exit axis",
              all(i in mv and abs(mv[i].y) >= max(abs(mv[i].x), abs(mv[i].z)) for i in was_in if inside(pts[i]) < 0))
        far = [i for i, p in enumerate(pts) if abs(p.x) > 0.045 or abs(p.y) > 0.049]
        check(f"keep-out (smooth {smooth}): far points do not move", all(i not in mv for i in far))
        if smooth:
            ring = [i for i in mv if i not in was_in]
            pinned_max = max(mv[i].length for i in was_in)
            check("keep-out: the move is spread over neighbours, smaller than the largest direct move",
                  bool(ring) and all(0 < mv[i].length < pinned_max for i in ring), len(ring))
            again = CT.keepout_moves(pts, edges, inside, exits, margin, smooth)
            check("keep-out: deterministic", again.keys() == mv.keys() and all(again[i] == mv[i] for i in mv))
        else:
            check("keep-out (smooth 0): only the points inside move", set(mv) == set(was_in))
    check("keep-out: nothing inside -> no moves",
          CT.keepout_moves([Vector((0.1, 0.0, 0.0)), Vector((0.11, 0.0, 0.0))], [(0, 1)], inside, exits, margin, 6) == {})

    # ------------------------------------------------------------------------------------------------ capsule fit
    a, b, r = (0.0, 0.0, 0.1), (0.0, 0.0, 0.3), 0.03
    cloud = []
    for i in range(41):  # surface of a capsule along z
        z = a[2] + (b[2] - a[2]) * i / 40
        for k in range(24):
            ang = 2 * math.pi * k / 24
            cloud.append((r * math.cos(ang), r * math.sin(ang), z))
    for k in range(24):
        for m in range(1, 7):  # the two caps
            ang, el = 2 * math.pi * k / 24, 0.5 * math.pi * m / 6
            x, y = r * math.cos(el) * math.cos(ang), r * math.cos(el) * math.sin(ang)
            cloud.append((x, y, b[2] + r * math.sin(el)))
            cloud.append((x, y, a[2] - r * math.sin(el)))
    fa, fb, fr = CT.fit_capsule(cloud, "blob", percentile=95)
    lo, hi = sorted([fa, fb], key=lambda p: p[2])
    check("blob fit: axis, ends and radius of a known capsule (2 mm)",
          abs(fr - r) < 0.002 and math.dist(lo, a) < 0.006 and math.dist(hi, b) < 0.006, (fa, fb, round(fr, 4)))
    check("blob fit: the same call gives the same capsule", CT.fit_capsule(cloud, "blob", percentile=95) == (fa, fb, fr))
    la, lb, lr = CT.fit_capsule(cloud, "limb", axis=((0, 0, 0.08), (0, 0, 0.32)))
    check("limb fit: radius is the median distance to the bone axis, ends one radius inside",
          abs(lr - r) < 1e-6 and abs(la[2] - (0.08 + r)) < 1e-9 and abs(lb[2] - (0.32 - r)) < 1e-9, (la, lb, lr))
    thin = [(p[0] * (0.5 if i % 2 else 1.0), p[1] * (0.5 if i % 2 else 1.0), p[2]) for i, p in enumerate(cloud)]
    r25 = CT.fit_capsule(thin, "limb", axis=((0, 0, 0.08), (0, 0, 0.32)), percentile=25)[2]
    r90 = CT.fit_capsule(thin, "limb", axis=((0, 0, 0.08), (0, 0, 0.32)), percentile=90)[2]
    check("limb fit: a low percentile gives the inner radius, a high one the outer", abs(r25 - 0.015) < 1e-6 and abs(r90 - r) < 1e-6,
          (r25, r90))
    check("fit: pad_m is added to the radius",
          abs(CT.fit_capsule(cloud, "limb", axis=((0, 0, 0.08), (0, 0, 0.32)), pad=0.004)[2] - (r + 0.004)) < 1e-9)
    short = CT.fit_capsule(cloud, "limb", axis=((0, 0, 0.19), (0, 0, 0.21)))
    check("limb fit: a short bone keeps a > b order (ends at most 45 % inside)", short[0][2] < short[1][2], short)
    for label, call in (("too few vertices", lambda: CT.fit_capsule(cloud[:3], "blob")),
                        ("zero-length axis", lambda: CT.fit_capsule(cloud, "limb", axis=((0, 0, 0), (0, 0, 0))))):
        try:
            call()
            check(f"fit refuses: {label}", False)
        except ValueError:
            check(f"fit refuses: {label}", True)

    # ----------------------------------------------------------------------------------------- the T-183 candidate
    ov_path = os.path.join(ROOT, OVERRIDE)
    if os.path.isfile(ov_path):
        ov = json.load(open(ov_path, encoding="utf-8"))["override"]
        check("T-183 override: hair keys only", set(ov) == {"hair"} and set(ov["hair"]) <= {"ear_keepout", "dynamics"})
        base_path = os.path.join(ROOT, "assets", "characters", "girl_auburn_bun_glasses", "spec",
                                 "girl_auburn_bun_glasses.0.14.0.spec.json")
        base = json.load(open(base_path, encoding="utf-8"))
        merged = SPEC.deep_merge(copy.deepcopy(base), ov)
        check("T-183 override on the girl's current spec: the T-183 keys validate", CT.validate(merged["hair"]) == [],
              CT.validate(merged["hair"]))
        check("T-183 override on the girl's current spec: groom/5 validates", G6.validate(merged["hair"]) == [],
              G6.validate(merged["hair"])[:3])
        same = {k: v for k, v in merged["hair"].items() if k not in ("ear_keepout", "dynamics")}
        check("T-183 override: structures, fibres and binding are the released ones",
              same == {k: v for k, v in base["hair"].items() if k != "dynamics"})
        check("the released spec itself is unchanged by the merge", not CT.has_keys(base["hair"]))
    else:
        print(f"[test_hair_contact] note: {OVERRIDE} not present, candidate checks skipped")

    n_fail = RESULTS.count(False)
    print(f"[test_hair_contact] {len(RESULTS) - n_fail}/{len(RESULTS)} passed")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
