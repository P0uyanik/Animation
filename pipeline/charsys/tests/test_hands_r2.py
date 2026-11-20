"""Plain-Python tests for the T-121 hand mesh (hands_r2.py, opt-in body.hands = "hands_r2/1"). No Blender.

    python3 pipeline/charsys/tests/test_hands_r2.py

Covers: the module declares hands_r2/1 and imports without bpy; the layout keeps the rig's finger names and the
three-segment split (bones .01-.03 per finger and thumb); on the recorded hand frames of the current boy and girl
specs (both sides) no two digits intersect at rest or at the full grasp, every neighbouring pair keeps a readable gap
at the knuckles and the remesh voxel is small enough to keep it open; the built r2 hands carry the same vertex groups
and weighted bones as the current hands (recorded from Blender builds); default builds are untouched (the hook only
runs on body.hands, no published or candidate spec sets it, and the recorded default-build fingerprint matches the
input commit)."""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CHARSYS = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(CHARSYS, "..", ".."))
EVAL = os.path.join(ROOT, "docs", "evaluation", "characters", "T-121")
sys.path.insert(0, CHARSYS)

import hands_r2 as HR  # noqa: E402

sys.path.insert(0, HERE)
import test_guard_allowlist as GA  # noqa: E402

RESULTS = []


def check(name, ok, detail=None):
    RESULTS.append(bool(ok))
    print(f"[test_hands_r2] {'PASS' if ok else 'FAIL'} {name}{'' if detail is None else ' ' + str(detail)}")


def frames():
    rec = json.load(open(os.path.join(EVAL, "hand_frames.json")))["characters"]
    for who, c in sorted(rec.items()):
        for s, f in sorted(c["frames"].items()):
            fr = {k: (tuple(v) if k not in ("sx", "thumb") else v) for k, v in f.items()}
            fr["thumb"] = tuple(tuple(p) for p in f["thumb"])
            yield who, s, fr, c["hand"], c["height_m"]


def test_declaration():
    check("module declares hands_r2/1", HR.GENERATOR_VERSIONS == ("hands_r2/1",))
    check("module imports without bpy", "bpy" not in sys.modules)


def test_bones():
    profile = json.load(open(os.path.join(CHARSYS, "rig_profiles", "rigify_human_metarig.json")))
    rig_fingers = sorted(profile["fingers"].values())
    for who, s, fr, hp, H in frames():
        lay = HR.layout(fr, hp, H)
        check(f"{who}.{s}: finger names = the rig profile's", sorted(lay["fingers"]) == rig_fingers, sorted(lay["fingers"]))
        check(f"{who}.{s}: three segments per digit (.01-.03)",
              all(len(f["joints"]) == 4 for f in lay["fingers"].values()) and len(lay["thumb"]["joints"]) == 4)
        thumb_in = [round(c, 9) for c in lay["thumb"]["joints"][-1]] == [round(c, 9) for c in fr["thumb"][2]]
        check(f"{who}.{s}: thumb kept where body_generic lays it out", thumb_in)


def test_vertex_groups():
    vg = json.load(open(os.path.join(EVAL, "hand_vertex_groups.json")))
    cur, new = vg["current"], vg["hands_r2"]
    check("same finger deform bones", cur["finger_deform_bones"] == new["finger_deform_bones"] and
          len(new["finger_deform_bones"]) == 2 * (4 * 3 + 4 + 3), len(new["finger_deform_bones"]))
    for s in ("L", "R"):
        check(f"hand.{s}: same vertex groups", cur[s]["vertex_groups"] == new[s]["vertex_groups"])
        check(f"hand.{s}: every finger and thumb bone carries weight",
              all(f"DEF-{n}.0{k}.{s}" in new[s]["groups_with_weight"]
                  for n in ("f_index", "f_middle", "f_ring", "f_pinky", "thumb") for k in (1, 2, 3)))
        check(f"hand.{s}: weighted groups = the current hand's", cur[s]["groups_with_weight"] == new[s]["groups_with_weight"])


def test_clearance():
    g = HR.FULL_GRASP
    neighbours = (("f_index", "f_middle"), ("f_middle", "f_ring"), ("f_pinky", "f_ring"))
    for who, s, fr, hp, H in frames():
        lay = HR.layout(fr, hp, H)
        rest = HR.clearances(lay, HR.pose(lay, fr))
        full = HR.clearances(lay, HR.pose(lay, fr, g["finger_curl_deg"], g["thumb_flex_deg"], g["thumb_oppose_deg"]))
        check(f"{who}.{s}: no digits intersect at rest", min(rest.values()) > 0, round(min(rest.values()) * 1000, 2))
        check(f"{who}.{s}: no digits intersect at the full grasp", min(full.values()) > 0, round(min(full.values()) * 1000, 2))
        gap = min(rest[p] for p in neighbours)
        check(f"{who}.{s}: knuckle gap >= 15% of the finger diameter (readable)", gap >= 0.15 * 2 * lay["radius"],
              f"{gap * 1000:.2f} mm")
        check(f"{who}.{s}: remesh voxel <= gap / 3 (gap stays open)", lay["voxel"] <= gap / 3.0)
        check(f"{who}.{s}: fan spread opens the tips (tip gap > knuckle gap)",
              all(_tip_gap(lay, a, b) > lay["gap"] for a, b in neighbours))
        check(f"{who}.{s}: plush fingers stay chubby (radius >= 0.7 x spec)",
              lay["radius"] >= 0.7 * hp["finger_radius"] * H, f"{lay['radius'] * 1000:.2f} mm")
    check("full grasp curls each joint", all(a >= 30 for a in g["finger_curl_deg"]))


def _tip_gap(lay, a, b):
    fa, fb = lay["fingers"][a], lay["fingers"][b]
    ta, tb = fa["joints"][-1], fb["joints"][-1]
    return sum((x - y) ** 2 for x, y in zip(ta, tb)) ** 0.5 - fa["tip_radius"] - fb["tip_radius"]


def test_default_untouched():
    src = open(os.path.join(CHARSYS, "build_character.py")).read()
    check("build hook only on body.hands", src.count("import hands_r2") == 1 and 'if spec["body"].get("hands"):' in src)
    pinned = []
    for p in glob.glob(os.path.join(ROOT, "assets", "characters", "**", "*.json"), recursive=True):
        try:
            d = json.load(open(p))
        except (ValueError, UnicodeDecodeError):
            continue
        d = d.get("override", d) if isinstance(d, dict) else {}
        if isinstance(d, dict) and isinstance(d.get("body"), dict) and "hands" in d["body"]:
            pinned.append(os.path.relpath(p, ROOT))
    pinned, allowed, aerr = GA.split(pinned, "body.hands")
    check("owner-approved candidate allowlist is valid (T-154)", not aerr, aerr[:3])
    check("no character spec or candidate in assets/ sets body.hands (except listed owner-approved candidates)",
          not pinned, pinned)
    rec = json.load(open(os.path.join(EVAL, "default_build_check.json")))
    check("recorded default build fingerprint = input commit's", rec["fingerprint_identical"] is True, rec["input"])


if __name__ == "__main__":
    test_declaration()
    test_bones()
    test_vertex_groups()
    test_clearance()
    test_default_untouched()
    print(f"[test_hands_r2] {sum(RESULTS)}/{len(RESULTS)} passed")
    sys.exit(0 if all(RESULTS) else 1)
