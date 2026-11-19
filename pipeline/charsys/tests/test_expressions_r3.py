"""T-113: expression library round 3 (per-character expression sets, SmileOpen / Pout in use, closed lids on the eyeball).

    python3 pipeline/charsys/tests/test_expressions_r3.py [--blender <exe>] [--boy <master.blend>] [--girl <master.blend>]

Plain checks (no Blender):
  * the face library validates: every preset (default and optional) is a mix of known action units, every engine
    expression names a preset, an optional preset or an action unit;
  * the per-character sets (BOY_SET, GIRL_SET below) exist as content/emotions/<char>_*.emotion.json, and no other
    <char>_* emotion is unlisted; each file is plush.emotion/1 with a face, an existing body clip, timing, and a
    reference; every face name resolves (engine expression, action unit, library or optional preset, or a preset the
    character's published spec lists);
  * calibration: every frame range cited in a reference ("<clip> <who> [a, b)") is a T-106 interval of that clip and
    character (docs/evaluation/animation/T-106/performance.csv), and each set has at least one cited range per emotion
    that comes from T-106 or names its reference images;
  * the shared library stays exactly 8 (the files without a boy_/girl_ prefix; test_emotions.cpp counts the same);
  * open smile and pout: girl_delighted (PB [255, 289), the open smile) plays smileOpen and not the library smile;
    boy_reluctant (the sulk) plays pout; no boy emotion smiles (his positive_style);
  * closed_fit is opt-in: face_generic_v3 calls fit_closed_lids only under eyes.lids.closed_fit, no published spec
    sets it, and the T-113 candidate overrides set it and list the presets the sets need.
Build checks (Blender; masters given with --boy/--girl, both optional):
  * lid dome: for those of Blink, Smile, Laugh and Squint that close the lid for that character (Blink.L >= 0.5 with
    the spec's overrides; the girl's Smile keeps her eyes open), each preset at 1.0, the upper-lid vertices visible from the front
    and from 3/4 (+-35 deg; no head skin, lower lid or the lid itself in between) lie within DOME_MM of the eyeball
    surface along the eye-centre ray (95th percentile; the published masters reach 6.0 mm (boy) and 8.6 mm (girl))
    and none lies inside the eyeball (>= 0 mm);
  * the fitted closed lid still covers the turned eye: Blink 1.0 with both eye controls turned over the spec's
    gaze range (yaw/pitch grid, as test_face_v3b turns them), no eyeball vertex of either eye is visible from the
    front (published masters: 0);
  * the master was built with closed_fit (build_report.json next to it: face.closed_fit on both sides)."""
import argparse
import csv
import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
EMO = os.path.join(ROOT, "content", "emotions")
CLIPS = os.path.join(ROOT, "content", "clips")
LIB = os.path.join(ROOT, "pipeline", "charsys", "face_library", "expressions.json")
PERF = os.path.join(ROOT, "docs", "evaluation", "animation", "T-106", "performance.csv")
CAND = os.path.join(ROOT, "docs", "evaluation", "characters", "T-113", "candidates")
SPECS = {"boy": os.path.join(ROOT, "assets", "characters", "boy_yellow_hoodie", "spec", "boy_yellow_hoodie.2.1.0.spec.json"),
         "girl": os.path.join(ROOT, "assets", "characters", "girl_auburn_bun_glasses", "spec",
                              "girl_auburn_bun_glasses.0.12.0.spec.json")}
# The per-character expression sets (T-097 first files + T-113).
BOY_SET = ["boy_interested", "boy_sleepy", "boy_unimpressed", "boy_reluctant", "boy_focused"]
GIRL_SET = ["girl_delighted", "girl_wonder", "girl_eager", "girl_shy", "girl_content"]
SETS = {"boy": BOY_SET, "girl": GIRL_SET}
SHARED_COUNT = 8
DOME_MM = {"boy": 3.5, "girl": 6.0}  # p95 visible closed-lid gap. Published: boy 6.05 (Smile), girl 5.51 (Blink) / 7.88 (Laugh) / 8.62 (Squint); the girl candidate clears a 26/26 deg gaze sweep (e908), so her Blink stays at the published level
DOME_KEYS = ("Blink", "Smile", "Laugh", "Squint")
EXTRA_UNITS = {"CheekRaise", "MouthPout"}  # optional units (T-109 presets; skipped where a face lacks them)
SIDE_UNITS = {f"{u}.{s}" for u in ("BrowDown", "BrowSad", "EyeSquint", "EyeWide", "MouthSmile", "MouthFrown", "MouthPout")
              for s in ("L", "R")}

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS " if ok else "FAIL ") + name + (f"  ({detail})" if detail else ""), flush=True)


def load(p):
    return json.load(open(p, encoding="utf-8"))


def t106_intervals():
    out = {}
    with open(PERF, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out.setdefault((r["clip"], r["character"]), set()).add((int(r["first_frame"]), int(r["end_frame_exclusive"])))
    return out


def cited_ranges(ref):
    """[(clip, who, a, b)] for every '<clip> <who> [a, b)' (and following '[c, d)' of the same clip/who) in a text."""
    out = []
    parts = re.split(r"\b(paperboat|watertable|PB|WT)\b", ref)
    for i in range(1, len(parts) - 1, 2):
        clip = {"PB": "paperboat", "WT": "watertable"}.get(parts[i], parts[i])
        m = re.match(r"\s+(boy|girl)\b", parts[i + 1])
        if not m:
            continue
        for a, b in re.findall(r"\[(\d+),\s*(\d+)\)", parts[i + 1]):
            out.append((clip, m.group(1), int(a), int(b)))
    return out


def plain():
    lib = load(LIB)
    units = set(lib["action_units"]) | EXTRA_UNITS
    presets = dict(lib["presets"])
    optional = dict(lib.get("optional_presets", {}))
    bad = [(n, u) for n, p in {**presets, **optional}.items() for u in p if u not in units]
    check("library presets are mixes of known action units", not bad, str(bad[:5]))
    eng = lib["engine_expressions"]
    check("every engine expression names a preset or an action unit",
          all(v in presets or v in optional or v in units for v in eng.values()))
    check("SmileOpen and Pout are optional presets with engine names smileOpen / pout",
          "SmileOpen" in optional and "Pout" in optional and eng.get("smileOpen") == "SmileOpen" and eng.get("pout") == "Pout")
    perf = t106_intervals()
    files = sorted(f for f in os.listdir(EMO) if f.endswith(".emotion.json"))
    shared = [f for f in files if not f.startswith(("boy_", "girl_"))]
    check("shared emotion library stays exactly 8", len(shared) == SHARED_COUNT, str(shared))
    for who, names in SETS.items():
        spec = load(SPECS[who])["face"]["expressions"]
        custom = set(spec.get("custom") or {})
        on_disk = sorted(f[: -len(".emotion.json")] for f in files if f.startswith(who + "_"))
        check(f"{who}: every {who}_* emotion is in the listed set", sorted(names) == on_disk, f"{on_disk} vs {sorted(names)}")
        check(f"{who}: set has at least 4 expressions", len(names) >= 4, str(len(names)))
        for n in names:
            p = os.path.join(EMO, n + ".emotion.json")
            if not os.path.isfile(p):
                check(f"{n}: file exists", False)
                continue
            e = load(p)
            ok = (e.get("format"), e.get("version"), e.get("name")) == ("plush.emotion", 1, n)
            check(f"{n}: plush.emotion/1, named after its file", ok)
            check(f"{n}: has a face, timing and an existing body clip",
                  bool(e.get("face")) and {"onset", "hold", "release"} <= set(e.get("timing", {}))
                  and os.path.isfile(os.path.join(CLIPS, e["body"]["clip"] + ".clip.json")))
            unknown = [k for k in e["face"] if not (k in eng or k in units or k in SIDE_UNITS or k in presets
                                                    or k in optional or k in custom)]
            check(f"{n}: every face name resolves", not unknown, str(unknown))
            check(f"{n}: face weights in [-1, 1]", all(-1.0 <= float(v) <= 1.0 for v in e["face"].values()))
            ref = e.get("reference", "")
            cites = cited_ranges(ref)
            wrong = [c for c in cites if (c[2], c[3]) not in perf.get((c[0], c[1]), set()) or c[1] != who]
            check(f"{n}: cites T-106 frame ranges of {who} (or its reference images)",
                  (cites and not wrong) or "references" in ref, f"cited {len(cites)}, not T-106 {wrong}")
    d = load(os.path.join(EMO, "girl_delighted.emotion.json"))
    check("girl_delighted (PB [255, 289) open smile) plays SmileOpen, not the library smile",
          d["face"].get("smileOpen", 0) > 0 and "smile" not in d["face"] and "Smile" not in d["face"])
    check("girl_delighted cites PB [255, 289)", ("paperboat", "girl", 255, 289) in cited_ranges(d["reference"]))
    r = load(os.path.join(EMO, "boy_reluctant.emotion.json"))
    check("boy_reluctant (the sulk) plays pout", r["face"].get("pout", 0) > 0)
    smiles = [n for n in BOY_SET if {"smile", "Smile", "MouthSmile", "smileOpen", "laugh", "happy"} & set(load(os.path.join(EMO, n + ".emotion.json"))["face"])]
    check("no boy emotion smiles (positive_style)", not smiles, str(smiles))
    src = open(os.path.join(ROOT, "pipeline", "charsys", "face_generic_v3.py"), encoding="utf-8").read()
    check("closed_fit is opt-in in face_generic_v3",
          re.search(r'if \(ecfg\.get\("lids"\) or \{\}\)\.get\("closed_fit"\):[^\n]*\n(\s+.*\n){0,2}\s+.*fit_closed_lids', src) is not None)
    for who, sp in SPECS.items():
        s = load(sp)
        check(f"{who}: published spec does not set closed_fit (default output unchanged)",
              "closed_fit" not in (s["face"]["eyes"].get("lids") or {}))
        ov = load(os.path.join(CAND, f"{who}_t113.override.json"))["override"]["face"]
        need = "Pout" if who == "boy" else "SmileOpen"
        check(f"{who}: T-113 candidate sets closed_fit and lists {need}",
              bool(ov["eyes"]["lids"].get("closed_fit")) and need in ov["expressions"]["optional"])
    lids_src = open(os.path.join(ROOT, "pipeline", "charsys", "face_v3", "lids.py"), encoding="utf-8").read()
    names = re.findall(r"boy_|girl_|yellow|auburn|hoodie", lids_src)
    check("no character names in face_v3/lids.py", not names, str(names))


PROBE = r'''
import bpy, json, math, sys
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
a = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.open_mainfile(filepath=a[0])
rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
def tree(ob, dg):
    e = ob.evaluated_get(dg); me = e.to_mesh(); mw = e.matrix_world
    t = BVHTree.FromPolygons([mw @ v.co for v in me.vertices], [p.vertices[:] for p in me.polygons]); e.to_mesh_clear(); return t
out = {}
for ctl in a[1].split(","):
    for k in [k for k in rig.keys() if k.startswith("face_")]:
        rig[k] = 0.0
    rig["face_" + ctl] = 1.0
    rig.update_tag(); bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    occ = [tree(o, dg) for o in bpy.data.objects if o.type == "MESH" and o.name.startswith(("garment.collider.body_skin", "lid_lower", "head"))]
    gaps = []
    for side, sx in (("L", 1), ("R", -1)):
        eye = bpy.data.objects[f"eye.{side}"]; te = tree(eye, dg); c = eye.evaluated_get(dg).matrix_world.translation
        up = bpy.data.objects[f"lid_upper.{side}"].evaluated_get(dg); me = up.to_mesh(); mw = up.matrix_world
        pts = [mw @ v.co for v in me.vertices]
        tl = BVHTree.FromPolygons(pts, [p.vertices[:] for p in me.polygons])
        for yaw in (0.0, -sx * 35.0):
            ya = math.radians(yaw); d = Vector((math.sin(ya), -math.cos(ya), 0.0))
            for w in pts:
                rd = w - c
                if rd.normalized().y > -0.3:
                    continue
                o = w + d * 2e-4
                if any(t.ray_cast(o, d, 1.0)[0] is not None for t in occ + [tl]):
                    continue
                h = te.ray_cast(c, rd.normalized(), 1.0)
                if h[0] is not None:
                    gaps.append((rd.length - (h[0] - c).length) * 1000)
        up.to_mesh_clear()
    g = np.array(gaps) if gaps else np.array([float("nan")])
    out[ctl] = {"n": len(gaps), "p95_mm": round(float(np.nanpercentile(g, 95)), 3), "min_mm": round(float(np.nanmin(g)), 3),
                "median_mm": round(float(np.nanmedian(g)), 3)}
for k in [k for k in rig.keys() if k.startswith("face_")]:
    rig[k] = 0.0
rig["face_Blink"] = 1.0
gy, gp = (float(v) for v in json.loads(a[2]))
leak = {}
for yaw in (-gy, 0.0, gy):
    for pitch in (-gp, 0.0, gp):
        for s in "LR":
            b = rig.pose.bones[f"eye.{s}"]
            b.rotation_mode = "XYZ"
            b.rotation_euler = (math.radians(pitch), 0.0, math.radians(yaw))
        rig.update_tag(); bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get()
        occ = [tree(o, dg) for o in bpy.data.objects if o.type == "MESH" and o.name.startswith(("lid_upper", "lid_lower", "lash", "garment.collider.body_skin", "head"))]
        n = 0
        for s in "LR":
            e = bpy.data.objects[f"eye.{s}"].evaluated_get(dg); me = e.to_mesh(); mw = e.matrix_world
            d = Vector((0, -1, 0))
            n += sum(1 for v in me.vertices if all(t.ray_cast(mw @ v.co + d * 2e-4, d, 1.0)[0] is None for t in occ))
            e.to_mesh_clear()
        leak[f"{yaw:+.0f},{pitch:+.0f}"] = n
out["blink_gaze_visible_eye_vertices"] = leak
print("PROBE_JSON " + json.dumps(out))
'''


def probe(blender, blend, gaze=(16.0, 8.0)):
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(PROBE)
    r = subprocess.run([blender, "-b", "--factory-startup", "-P", f.name, "--", os.path.abspath(blend), ",".join(DOME_KEYS),
                        json.dumps(list(gaze))],
                       capture_output=True, text=True)
    os.unlink(f.name)
    line = next((l for l in r.stdout.splitlines() if l.startswith("PROBE_JSON ")), None)
    if line is None:
        raise RuntimeError(r.stdout[-2000:] + r.stderr[-2000:])
    return json.loads(line[len("PROBE_JSON "):])


def closed_presets(who, blend):
    """The DOME_KEYS presets whose upper lids close (Blink.L >= 0.5) for this master: library weights with the spec's
    expression overrides (spec.resolved.json next to the master, else the published spec)."""
    lib = load(LIB)
    rs = os.path.join(os.path.dirname(blend), "spec.resolved.json")
    spec = load(rs if os.path.isfile(rs) else SPECS[who])
    over = (spec["face"].get("expressions") or {}).get("override") or {}
    out = set()
    for k in DOME_KEYS:
        w = dict(lib["presets"].get(k, {}))
        w.update(over.get(k, {}))
        if float(w.get("Blink.L", 0.0)) >= 0.5:
            out.add(k)
    return out


def builds(blender, masters):
    for who, blend in masters.items():
        rep_path = os.path.join(os.path.dirname(blend), "build_report.json")
        if os.path.isfile(rep_path):
            face = load(rep_path).get("face") or {}
            cf = face.get("closed_fit") or (face.get("report") or {}).get("closed_fit") or {}
            check(f"{who}: master built with closed_fit on both sides", set(cf) >= {"L", "R"}, rep_path)
        m = probe(blender, blend, load(SPECS[who])["face"]["eyes"].get("gaze_range_deg", [20.0, 12.0]))
        leak = m.pop("blink_gaze_visible_eye_vertices")
        check(f"{who}: closed lid covers the turned eyes (Blink 1, gaze grid)", max(leak.values()) == 0, json.dumps(leak))
        closed = closed_presets(who, blend)
        for key in DOME_KEYS:
            v = m[key]
            if key not in closed:
                print(f"INFO {who} {key}: the lid does not close in this preset (Blink.L < 0.5), not a closed lid: {json.dumps(v)}")
                continue
            check(f"{who} {key}: visible closed lid within {DOME_MM[who]} mm of the eyeball (p95)",
                  v["n"] > 0 and v["p95_mm"] <= DOME_MM[who], json.dumps(v))
            check(f"{who} {key}: no visible lid inside the eyeball", v["min_mm"] >= 0.0, json.dumps(v))
        print("DOME " + who + " " + json.dumps(m), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blender")
    ap.add_argument("--boy")
    ap.add_argument("--girl")
    a = ap.parse_args()
    plain()
    masters = {k: v for k, v in (("boy", a.boy), ("girl", a.girl)) if v}
    if masters:
        if not a.blender:
            check("build checks need --blender", False)
        else:
            builds(a.blender, masters)
    else:
        print("SKIP build checks (no --boy/--girl master)")
    n_fail = sum(1 for _, ok, _ in results if not ok)
    print(f"{len(results) - n_fail}/{len(results)} PASS")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
