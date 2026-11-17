"""T-065: face_generic/2 (opt-in face v2) checks.

    python3 pipeline/charsys/tests/test_face_v2.py --blender <exe> [--boy <master>] [--girl <master>] [--third <master>]

Unit checks (in Blender, no build): the version dispatch reads the face pin; the brow presets merge under the spec
values; the v2 rest shapes exist (soft_smile, parted) and bake_rest_shape_v2 keeps the released keys' absolute
targets while every other key moves with the rest; face_generic/1 does not reach any v2 code path.
Build checks (a master per candidate: --boy/--girl/--third, else built from the T-065 candidate overrides with
docs/evaluation/characters/T-065/build_candidate.py, which registers face_generic/2 in-process):
  * the report says face_generic/2; the lids are blended (at most 8 % of each upper lid shell visible from the
    front: the lid band; face_generic/1 shows the whole dome) and the socket skin follows EyeWide;
  * the T-046 face layer controls and the T-058 per-side units still exist as rig controls (boy: BrowDown.L/R,
    MouthSmile.L/R, MouthFrown.L/R, EyeSquint.L/R, MouthPout) and the engine expression map names the presets;
  * CheekRaise exists where face.cheeks is set; the soft_smile rest lifts the lip corners above the closed rest;
  * the third character's large wide-set eyes build without warnings and do not overlap; her iris is blue.
Without --blender nothing runs (exit 2)."""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CHARSYS = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(CHARSYS, "..", ".."))
EVID = os.path.join(ROOT, "docs", "evaluation", "characters", "T-065")
DRIVER = os.path.join(EVID, "build_candidate.py")
BOY = os.path.join(ROOT, "assets", "characters", "boy_yellow_hoodie", "spec", "boy_yellow_hoodie.2.0.0-dev.spec.json")
GIRL = os.path.join(ROOT, "assets", "characters", "girl_auburn_bun_glasses", "spec", "girl_auburn_bun_glasses.spec.json")
GIRL_010 = os.path.join(ROOT, "assets", "characters", "girl_auburn_bun_glasses", "spec", "girl_auburn_bun_glasses.0.10.0.override.json")
CANDIDATES = {
    "boy": ([BOY], os.path.join(EVID, "candidates", "boy_2.0-dev_face2.override.json")),
    "girl": ([GIRL, GIRL_010], os.path.join(EVID, "candidates", "girl_next_face2.override.json")),
    "third": ([GIRL, GIRL_010], os.path.join(EVID, "candidates", "third_headonly_face2.override.json")),
}
RESULTS = []


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok), detail))
    print(("PASS " if ok else "FAIL ") + name + (f"  ({detail})" if detail else ""))


def run_probe(blender, script, blend=None):
    with tempfile.TemporaryDirectory() as tmp:
        src, out = os.path.join(tmp, "probe.py"), os.path.join(tmp, "out.json")
        head = "bpy.ops.wm.open_mainfile(filepath=%r)\n" % blend if blend else ""
        open(src, "w").write("import bpy, json, sys\nsys.path.insert(0, %r)\n%sRESULT = {}\n%s\njson.dump(RESULT, open(%r, 'w'))\n"
                             % (CHARSYS, head, script, out))
        subprocess.run([blender, "-b", "--factory-startup", "-P", src, "--"], check=True, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)
        return json.load(open(out))


def build(blender, who):
    m = arg("--" + who)
    if m:
        return os.path.abspath(m), json.load(open(os.path.join(os.path.dirname(os.path.abspath(m)), "build_report.json")))
    specs, ov = CANDIDATES[who]
    out = tempfile.mkdtemp(prefix=f"t065_{who}_")
    cmd = [blender, "-b", "--factory-startup", "-P", DRIVER, "--", "--spec", specs[0]]
    for o in specs[1:] + [ov]:
        cmd += ["--override", o]
    subprocess.run(cmd + ["--out", out, "--no-glb", "--no-compare"], check=True, stdout=subprocess.DEVNULL)
    blend = next(os.path.join(out, f) for f in os.listdir(out) if f.endswith("_master.blend"))
    return blend, json.load(open(os.path.join(out, "build_report.json")))


UNIT = r'''
import numpy as np
import face_generic as FG, face_features as FF
RESULT["dispatch"] = [FG.face_version({"generators": {"face": "face_generic/2"}, "face": {}}),
                      FG.face_version({"face": {"generator": "face_generic/2"}}),
                      FG.face_version({"face": {"generator": "face_generic/1"}}),
                      FG.face_version({"generators": {"face": "face_generic/1"}, "face": {"generator": "face_generic/1"}})]
RESULT["declared"] = list(FG.GENERATOR_VERSIONS)
b = FF.brow_config({"shape": "flat_stroke", "thick_m": 0.009})
RESULT["brow_merge"] = [b["thick_m"], b["arch_m"]]
try:
    FF.brow_config({"shape": "nope"}); RESULT["brow_bad"] = False
except ValueError:
    RESULT["brow_bad"] = True
RESULT["rest_shapes"] = sorted(FF.REST_SHAPES_V2)
# bake_rest_shape_v2 on a 1-vertex mesh: keys A (baked, moves with the rest) and MouthFrown (released: absolute)
me = bpy.data.meshes.new("t"); me.from_pydata([(0, 0, 0)], [], []); ob = bpy.data.objects.new("t", me)
bpy.context.scene.collection.objects.link(ob)
ob.shape_key_add(name="Basis")
k = ob.shape_key_add(name="MouthSmile"); k.data[0].co = (0, 0, 1)
k = ob.shape_key_add(name="MouthFrown"); k.data[0].co = (0, 0, -1)
k = ob.shape_key_add(name="EyeWide"); k.data[0].co = (1, 0, 0)
FF.bake_rest_shape_v2([ob], "soft_smile", {"MouthSmile": 0.5})
kb = ob.data.shape_keys.key_blocks
RESULT["bake"] = {n: list(kb[n].data[0].co) for n in ("Basis", "MouthSmile", "MouthFrown", "EyeWide")}
RESULT["basis_co"] = list(ob.data.vertices[0].co)
# face_generic/1's build never calls a v2 function: its source path stops before build_v2
import inspect
src = inspect.getsource(FG.build)
RESULT["v1_isolated"] = ("build_v2(" in src and "lid_socket" not in src and "shape_face_v2" not in src
                         and "bake_rest_shape_v2" not in src and "build_brows_v2" not in src)
'''

PROBE = r'''
import numpy as np
from mathutils import Vector
rig = next(o for o in bpy.data.objects if o.type == "ARMATURE" and "ps_face_parts" in o.keys())
RESULT["controls"] = sorted(k[5:] for k in rig.keys() if k.startswith("face_"))
coll = next(c for c in bpy.data.collections if "ps_engine_expressions" in c.keys())
RESULT["engine"] = json.loads(coll["ps_engine_expressions"])
head = bpy.data.objects[json.loads(rig["ps_face_parts"])["head"]]
RESULT["head_keys"] = [k.name for k in head.data.shape_keys.key_blocks]
m = bpy.data.objects["mouth"]
kb = m.data.shape_keys.key_blocks
n = int(m["ps_lip_rows"]); seam = list(m["ps_seam_rows"])[0]
co = [kb["Basis"].data[seam * n + i].co for i in range(n)]
RESULT["corner_lift_m"] = (co[0].z + co[-1].z) / 2 - co[n // 2].z
eyes = [bpy.data.objects["eye.L"], bpy.data.objects["eye.R"]]
RESULT["eye_gap_m"] = (eyes[0].matrix_world.translation - eyes[1].matrix_world.translation).length
RESULT["eye_extent_x_m"] = max((eyes[0].matrix_world @ v.co).x for v in eyes[0].data.vertices) - eyes[0].matrix_world.translation.x
mat = eyes[0].active_material
ramp = next(nd for nd in mat.node_tree.nodes if nd.type == "VALTORGB")
mid = ramp.color_ramp.evaluate(0.4)
RESULT["iris_mid_rgb"] = [mid[0], mid[1], mid[2]]
'''


def main():
    blender = arg("--blender")
    if not blender:
        print("needs --blender")
        return 2
    u = run_probe(blender, UNIT)
    check("version dispatch reads the face pin", u["dispatch"] == [2, 2, 1, 1], str(u["dispatch"]))
    check("face_generic declares /1 and /2", u["declared"] == ["face_generic/1", "face_generic/2"], str(u["declared"]))
    check("brow preset merges under spec values", u["brow_merge"][0] == 0.009 and u["brow_merge"][1] > 0, str(u["brow_merge"]))
    check("unknown brow preset is an error", u["brow_bad"])
    check("v2 rest shapes include soft_smile and parted", {"soft_smile", "parted"} <= set(u["rest_shapes"]), str(u["rest_shapes"]))
    bk = u["bake"]
    check("soft_smile rest: basis moves by the mix", abs(u["basis_co"][2] - 0.5) < 1e-6, str(u["basis_co"]))
    check("released keys keep their absolute targets", abs(bk["MouthSmile"][2] - 1.0) < 1e-6 and abs(bk["MouthFrown"][2] + 1.0) < 1e-6,
          f"MouthSmile {bk['MouthSmile']}, MouthFrown {bk['MouthFrown']}")
    check("other keys move with the rest", abs(bk["EyeWide"][2] - 0.5) < 1e-6 and abs(bk["EyeWide"][0] - 1.0) < 1e-6, str(bk["EyeWide"]))
    check("face_generic/1 build path never calls v2 code", u["v1_isolated"])
    for who in ("boy", "girl", "third"):
        blend, rep = build(blender, who)
        f = rep["face"]
        check(f"{who}: built with face_generic/2", f.get("generator") == "face_generic/2" and rep["versions"]["generators"]["face"] == "face_generic/2")
        ex = f.get("lid_shell_exposed", {})
        ups = [v for k, v in ex.items() if k.startswith("lid_upper")]
        check(f"{who}: lids blended (upper lid shells <= 8 % visible from the front)", ups and max(ups) <= 0.08, str(ex))
        check(f"{who}: no build warnings", not f.get("warnings"), str(f.get("warnings")))
        p = run_probe(blender, PROBE, blend)
        check(f"{who}: socket skin follows EyeWide", "EyeWide" in p["head_keys"])
        need = {"Blink.L", "Blink.R", "EyeWide", "EyeSquint", "BrowUp.L", "BrowUp.R", "BrowDown", "BrowSad", "MouthSmile",
                "MouthFrown", "JawOpen", "MouthO"}
        if who == "boy":
            need |= {"BrowDown.L", "BrowDown.R", "MouthSmile.L", "MouthSmile.R", "MouthFrown.L", "MouthFrown.R",
                     "EyeSquint.L", "EyeSquint.R", "MouthPout", "Bored"}
        missing = sorted(need - set(p["controls"]))
        check(f"{who}: T-046 / T-058 controls present", not missing, "missing " + ", ".join(missing) if missing else "")
        check(f"{who}: engine expression map (happy/sad/angry/surprised)",
              {"happy", "sad", "angry", "surprised"} <= set(p["engine"]), str(sorted(p["engine"])))
        if who in ("girl", "third"):
            check(f"{who}: CheekRaise action unit", "CheekRaise" in p["controls"] and "CheekRaise" in p["head_keys"])
            check(f"{who}: soft_smile rest lifts the lip corners", p["corner_lift_m"] > 0.003, f"{p['corner_lift_m'] * 1000:.1f} mm")
        if who == "third":
            check("third: large wide-set eyes do not overlap", p["eye_gap_m"] > 2 * p["eye_extent_x_m"],
                  f"centres {p['eye_gap_m'] * 1000:.0f} mm apart, half-width {p['eye_extent_x_m'] * 1000:.0f} mm")
            r, g, b = p["iris_mid_rgb"]
            check("third: blue iris", b > r and b > g, str([round(v, 3) for v in p["iris_mid_rgb"]]))
    bad = [n for n, ok, _ in RESULTS if not ok]
    print(f"{len(RESULTS) - len(bad)}/{len(RESULTS)} PASS" + (": FAILED " + ", ".join(bad) if bad else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
