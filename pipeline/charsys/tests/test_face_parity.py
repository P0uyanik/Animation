"""T-213: face export parity, knob-free master check and Blender build pin (pipeline/charsys/face_parity.py).

    python3 pipeline/charsys/tests/test_face_parity.py [--blender <exe>]

Checks (each line PASS/FAIL; exit code 1 on any FAIL):
  plain    (no Blender, no numpy) the module imports without bpy; the in-between expansion matches the engine's rule
           on hand-worked cases, and engine/model/character.cpp expandInbetweens is the version it mirrors (a change
           there fails here until the mirror is re-checked); the quantization bounds have the derived values; the
           build pin accepts the pinned build, refuses another one loudly and accepts it only with an override that
           names exactly that build; the knob classifier allows ARMATURE / vertex-group MASK only and flags Warp,
           Hook, Lattice, Surface Deform, Geometry Nodes and viewport/render splits; key rules flag a non-Basis
           relative key, a vertex group and a muted key.
  blender  (--blender; needs assets/characters/girl_auburn_bun_glasses 0.14.0, about 3 min) the current auburn
           master passes (knob-free, rest, raw deltas, neutral / half-blink / smile+blink within the bound); a
           broken temporary copy (a live Lattice modifier, its lattice object scaled 10 %, on lid_upper.L and the
           Blink key of lid_upper.R made relative to another key) fails both the knob-free check and parity.
           Nothing under assets/ is written.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CHARSYS = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(CHARSYS, "..", ".."))
sys.path.insert(0, CHARSYS)
RESULTS = []
# sha256 (first 16 hex) of the expandInbetweens function text in engine/model/character.cpp that
# face_parity.expand_inbetweens mirrors. If the engine changes it, re-check the mirror and update this value.
ENGINE_EXPAND_SHA16 = "f6c695056392a075"
AUBURN = ("girl_auburn_bun_glasses", "0.14.0")


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def check(name, ok, detail=None):
    RESULTS.append(bool(ok))
    print(f"[test_face_parity] {'PASS' if ok else 'FAIL'} {name}" + ("" if detail is None else f" {detail}"), flush=True)


def close(a, b):
    return set(a) == set(b) and all(abs(a[k] - b[k]) < 1e-12 for k in a)


def plain():
    import face_parity as FP
    check("module imports without bpy / numpy", "bpy" not in sys.modules and "numpy" not in sys.modules)
    ch = {"X": [[0.25, "X@25"], [0.5, "X@50"], [0.75, "X@75"]], "Y": [[0.75, "Y@75"]]}
    cases = [({"X": 0.0}, {}), ({"X": 0.25}, {"X@25": 1.0}), ({"X": 0.5}, {"X@50": 1.0}),
             ({"X": 0.375}, {"X@25": 0.5, "X@50": 0.5}), ({"X": 0.875}, {"X@75": 0.5, "X": 0.5}),
             ({"X": 1.0}, {"X": 1.0}), ({"X": 0.1}, {"X@25": 0.4}), ({"Y": 0.6}, {"Y@75": 0.8}),
             ({"Z": 0.3, "X": 0.5}, {"Z": 0.3, "X@50": 1.0})]
    bad = [(w, FP.expand_inbetweens(ch, w), e) for w, e in cases if not close(FP.expand_inbetweens(ch, w), e)]
    check("in-between expansion follows the engine rule (base block 0 below the last stop)", not bad, bad or None)
    src = open(os.path.join(ROOT, "engine", "model", "character.cpp")).read()
    m = re.search(r"^std::vector<float> expandInbetweens.*?^}\n", src, re.S | re.M)
    sha = hashlib.sha256(m.group(0).encode()).hexdigest()[:16] if m else None
    check("engine expandInbetweens is the version face_parity mirrors", sha == ENGINE_EXPAND_SHA16,
          f"{sha} (expected {ENGINE_EXPAND_SHA16}; re-check expand_inbetweens, then update the value)")
    u = FP.ulp32(1.6)
    check("float32 ulp at 1.6 m is 2^-23 m", u == 2.0 ** -23)
    b4 = FP.quant_bound("4", 1.6, 0.09, 0.0)
    check("export/4 rest bound = ulp/2 + 2 ulp (0.000298 mm at 1.6 m)", abs(b4 - 2.5 * u) < 1e-15, f"{b4 * 1e3:.6f} mm")
    b4w = FP.quant_bound("4", 1.6, 0.09, 2.0)
    exp = 0.5 * u + 2 * (1e-7 + FP.ulp32(0.09) / 2) + 4 * u
    check("export/4 bound with two active blocks", abs(b4w - exp) < 1e-15, f"{b4w * 1e3:.6f} mm")
    b5 = FP.quant_bound("5", 1.6, 0.09, 1.0)
    check("export/5 bound covers half the position grid and half the delta grid",
          b5 >= 2.0 ** -16 + 2.0 ** -15 and b5 < 2.0 ** -16 + 2.0 ** -15 + 1e-6, f"{b5 * 1e3:.6f} mm")
    check("raw delta bound export/4 = drop threshold + ulp/2", FP.delta_bound("4", 0.09) == 1e-7 + FP.ulp32(0.09) / 2)
    pin = FP.BLENDER_PIN
    r = FP.check_pin(pin["version"], pin["build_hash"])
    check("pinned build accepted without override", r["override"] is None)
    try:
        FP.check_pin("5.4.0", "abcdef123456")
        check("another build is refused", False)
    except FP.PinError as exc:
        check("another build is refused with the override named", "--accept-blender 5.4.0+abcdef123456" in str(exc))
    r = FP.check_pin("5.4.0", "abcdef123456", accept="5.4.0+abcdef123456")
    check("override naming exactly the running build is accepted and recorded", r["override"] == "5.4.0+abcdef123456")
    try:
        FP.check_pin("5.4.0", "abcdef123456", accept="5.4.0+000000000000")
        check("override for a different build is refused", False)
    except FP.PinError:
        check("override for a different build is refused", True)

    def mod(t, v=True, r=True, **kw):
        return {"name": t.lower(), "type": t, "show_viewport": v, "show_render": r, **kw}
    check("ARMATURE + vertex-group MASK allowed", FP.classify_modifiers([mod("ARMATURE"), mod("MASK", mode="VERTEX_GROUP")]) == [])
    for t in ("WARP", "HOOK", "LATTICE", "SURFACE_DEFORM", "NODES"):
        p = FP.classify_modifiers([mod("ARMATURE"), mod(t)])
        check(f"live {t} flagged as a fit helper", len(p) == 1 and "fit helper" in p[0], p)
    check("unknown deformer flagged", len(FP.classify_modifiers([mod("SUBSURF")])) == 1)
    check("viewport/render split flagged", any("viewport and render" in x for x in FP.classify_modifiers([mod("ARMATURE", r=False)])))
    kp = FP.key_rule_problems([{"name": "A", "relative_key": "Basis", "vertex_group": "", "mute": False},
                               {"name": "B", "relative_key": "A", "vertex_group": "", "mute": False},
                               {"name": "C", "relative_key": "Basis", "vertex_group": "lid", "mute": False},
                               {"name": "D", "relative_key": "Basis", "vertex_group": "", "mute": True}], "Basis")
    check("key rules: non-Basis relative, vertex group, muted flagged; a clean key not", len(kp) == 3 and
          sorted(x.split("'")[1] for x in kp) == ["B", "C", "D"], kp)
    check("current characters list starts with auburn", FP.current_characters()[:1] == ["girl_auburn_bun_glasses"]
          if os.path.isdir(os.path.join(ROOT, "assets", "characters")) else True)


BREAK = r'''
import bpy, sys
src, dst = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.open_mainfile(filepath=src)
lid = bpy.data.objects["lid_upper.L"]
lat = bpy.data.lattices.new("fit_knob_lattice")
lo = bpy.data.objects.new("fit_knob_lattice", lat)
root = next(c for c in bpy.data.collections if c.get("ps_character_id"))
root.objects.link(lo)
lo.location = lid.matrix_world.translation
lo.scale = (0.2, 0.2, 0.2)
bpy.context.view_layer.update()
m = lid.modifiers.new("fit_knob", "LATTICE")
m.object = lo
lo.scale = (0.22, 0.22, 0.22)  # 10 % after binding: the knob deforms rest and keys
kb = bpy.data.objects["lid_upper.R"].data.shape_keys.key_blocks
kb["Blink"].relative_key = kb["Blink@75"]
bpy.ops.wm.save_as_mainfile(filepath=dst, compress=False)
'''


def blender(exe):
    cid, ver = AUBURN
    master = os.path.join(ROOT, "assets", "characters", cid, "versions", ver, f"{cid}_master.blend")
    if not os.path.isfile(master):
        check("auburn master present", False, master)
        return
    fp = os.path.join(CHARSYS, "face_parity.py")
    with tempfile.TemporaryDirectory(prefix="t213_") as t:
        out = os.path.join(t, "good.json")
        r = subprocess.run([exe, "-b", "--factory-startup", "-P", fp, "--", "--blend", master, "--no-sweep",
                            "--out", out], capture_output=True, text=True)
        rep = json.load(open(out)) if os.path.isfile(out) else {}
        check("auburn 0.14.0 passes (exit 0)", r.returncode == 0 and rep.get("pass"), r.returncode)
        if rep:
            core = {e["name"]: e for e in rep["parity"]["expressions"]}
            check("knob-free on auburn", rep["knob_free"]["pass"], rep["knob_free"]["problems"])
            check("neutral / half_blink / smile_blink present and within the bound",
                  all(core.get(n, {}).get("pass") for n in ("neutral", "half_blink", "smile_blink")),
                  {n: (round(core[n]["max_mm"], 6), round(core[n]["bound_mm"], 6)) for n in core})
            check("pin recorded", rep["blender"]["running"]["build_hash"] == rep["blender"]["pinned"]["build_hash"])
        broken = os.path.join(t, "broken.blend")
        sc = os.path.join(t, "break.py")
        open(sc, "w").write(BREAK)
        r = subprocess.run([exe, "-b", "--factory-startup", "-P", sc, "--", master, broken], capture_output=True, text=True)
        check("broken copy written", r.returncode == 0 and os.path.isfile(broken), r.stderr[-400:])
        out = os.path.join(t, "broken.json")
        r = subprocess.run([exe, "-b", "--factory-startup", "-P", fp, "--", "--blend", broken, "--no-sweep",
                            "--out", out], capture_output=True, text=True)
        rep = json.load(open(out)) if os.path.isfile(out) else {}
        check("broken copy fails (exit 1)", r.returncode == 1 and rep and not rep["pass"], r.returncode)
        if rep:
            kp = json.dumps(rep["knob_free"]["problems"])
            check("knob-free flags the live Lattice, the lattice object and the relative key",
                  "LATTICE" in kp and "lattice object" in kp and "relative to 'Blink@75'" in kp, kp[:300])
            hb = next(e for e in rep["parity"]["expressions"] if e["name"] == "half_blink")
            check("parity fails at half-blink on the knob-deformed lid",
                  not hb["pass"] and any("lid_upper.L" in p for p in hb["problems"]), hb["problems"][:3])
            sb = next(e for e in rep["parity"]["expressions"] if e["name"] == "smile_blink")
            check("parity fails at smile+blink on the re-based key",
                  any("lid_upper.R" in p for p in sb["problems"]), sb["problems"][:3])


def main():
    plain()
    exe = arg("--blender")
    if exe:
        blender(exe)
    print(f"[test_face_parity] {sum(RESULTS)}/{len(RESULTS)} passed")
    return 0 if all(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
