"""T-089: face_generic/3 (opt-in face round 3) checks.

    python3 pipeline/charsys/tests/test_face_v3.py [--blender <exe>] [--boy <master.blend>] [--girl <master.blend>]

Plain checks (no Blender):
  * face_generic_v3.py declares exactly face_generic/3; face_generic.py still declares only /1 and /2;
  * the published boy 2.0.0 and girl 0.11.0 specs still pin face_generic/2 (no published spec changed);
  * each T-089 candidate override loads on its published spec and pins face_generic/3 (generators and face);
  * the shared v3 code names no character (no character id, no "boy"/"girl").
Unit checks (in Blender, no build):
  * the module loads through the version registry and declares its pin;
  * felt eye mode on: no clear coat, rough base, one highlight, tagged eye/felt/1; off (layered/1, the default): the
    glossy eye keeps its coat;
  * lid-corner bound: a trimmed shell stays within its x bound (outer, inner) and behind-cut over the basis and
    rotations about the frame's x axis (the blink / wide / squint motion), and a shell without a trim is untouched;
  * the v3 socket cover radius equals face_generic/2's (r_out + clearance) wherever there is no trim.
Build checks (a master per character: --boy/--girl, else built from the published spec + T-089 candidate):
  * report face_generic/3 with the felt eye; every lid shell's measured corner extent <= its trim bound (+0.2 mm);
  * no socket rim at 3/4: <= 10 % of the shell vertices past the opening corner visible at yaw +-35 deg;
  * T-081's smoothing gain kept: cheek folds <= 45 deg and eye-corner folds no sharper than the published version's
    (the T-081 probe; FOLD_LIMITS);
  * a full blink closes both eyes in front and 3/4 (docs/evaluation/characters/T-089/measure_eyes.py).
Without --blender only the plain checks run."""
import ast
import glob
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CHARSYS = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(CHARSYS, "..", ".."))
sys.path.insert(0, CHARSYS)
import spec as SPEC  # noqa: E402

CHARS = os.path.join(ROOT, "assets", "characters")
CASES = {
    "boy": (os.path.join(CHARS, "boy_yellow_hoodie", "spec", "boy_yellow_hoodie.2.0.0.spec.json"),
            os.path.join(CHARS, "boy_yellow_hoodie", "spec", "candidates", "T-089", "boy_face3.override.json")),
    "girl": (os.path.join(CHARS, "girl_auburn_bun_glasses", "spec", "girl_auburn_bun_glasses.0.11.0.spec.json"),
             os.path.join(CHARS, "girl_auburn_bun_glasses", "spec", "candidates", "T-089", "girl_face3.override.json")),
}
# eye-corner fold limit (T-081 probe) = the published version's own value: the candidate may not be sharper.
# boy 2.0.0 never had the T-081 wall smoothing (measured 157.7 deg in T-089); girl 0.11.0 = T-081's 40.3 deg.
FOLD_LIMITS = {"boy": {"cheek": 45.0, "corner": 157.7}, "girl": {"cheek": 45.0, "corner": 40.33}}
MEASURE = os.path.join(ROOT, "docs", "evaluation", "characters", "T-089", "measure_eyes.py")
RESULTS = []


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def check(name, ok, detail=""):
    RESULTS.append(bool(ok))
    print(f"[test_face_v3] {'PASS' if ok else 'FAIL'} {name}{(': ' + detail) if detail else ''}")


def declared(path):
    for node in ast.parse(open(path).read()).body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "GENERATOR_VERSIONS" for t in node.targets):
            return tuple(ast.literal_eval(node.value))
    return None


def plain():
    check("face_generic_v3 declares face_generic/3", declared(os.path.join(CHARSYS, "face_generic_v3.py")) == ("face_generic/3",))
    check("face_generic declares only /1 and /2", declared(os.path.join(CHARSYS, "face_generic.py")) == ("face_generic/1", "face_generic/2"))
    for who, (spec, ov) in CASES.items():
        s, info = SPEC.load(spec)
        check(f"published {who} spec still pins face_generic/2", info["versions"]["generators"]["face"] == "face_generic/2")
        if not os.path.exists(ov):
            check(f"{who} candidate exists", False, ov)
            continue
        s, info = SPEC.load(spec, [ov])
        check(f"{who} candidate pins face_generic/3", info["versions"]["generators"]["face"] == "face_generic/3"
              and s["face"].get("generator") == "face_generic/3")
    ids = [os.path.basename(d) for d in glob.glob(os.path.join(CHARS, "*")) if os.path.isdir(d)]
    words = ids + ["boy", "girl"]
    hits = []
    for f in [os.path.join(CHARSYS, "face_generic_v3.py")] + sorted(glob.glob(os.path.join(CHARSYS, "face_v3", "*.py"))):
        low = open(f).read().lower()
        hits += [f"{os.path.basename(f)}:{w}" for w in words if w.lower() in low]
    check("shared v3 code names no character", not hits, ", ".join(hits))


UNIT = r'''
import bpy, json, math, sys
sys.path.insert(0, CHARSYS)
from mathutils import Matrix, Vector
import numpy as np
import versions as V, geom as G, face_features as FF
from face_v3 import felt_eye as FELT, lids as LIDS, socket as SOCKET
R = {}
mod = V.REGISTRY.load("face", "face_generic/3")
R["module"] = mod.__name__
R["declares"] = list(mod.GENERATOR_VERSIONS)
ecfg = {"iris": {"srgb": [92, 60, 40]}, "highlights": [[0.2, 0.1, 0.08], [-0.2, -0.05, 0.04, 0.7]]}
m = FELT.eye_material_felt("t_felt", dict(ecfg, felt={"roughness": 0.8}), 0.05)
p = m.node_tree.nodes["Principled BSDF"]
R["felt"] = {"coat": p.inputs["Coat Weight"].default_value, "rough": p.inputs["Roughness"].default_value,
             "tag": m.get("ps_face_shader"), "highlights": sum(1 for n in m.node_tree.nodes if n.type == "MAP_RANGE")}
g = FF.eye_material_layered("t_gloss", ecfg, 0.05)
R["gloss"] = {"coat": g.node_tree.nodes["Principled BSDF"].inputs["Coat Weight"].default_value, "tag": g.get("ps_face_shader"),
              "highlights": sum(1 for n in g.node_tree.nodes if n.type == "MAP_RANGE")}
# lid-corner bound: an upper lid shell in a rotated, offset eye frame, trimmed, then rotated about the frame's x axis
C = bpy.data.collections.new("t"); bpy.context.scene.collection.children.link(C)
T = Matrix.Translation((0.07, -0.1, 0.78)) @ Matrix.Rotation(0.2, 4, "Z") @ Matrix.Rotation(-0.15, 4, "Y")
out = {}
for sx, side in ((1, "L"), (-1, "R")):
    r_out = 0.054
    up = G.uv_sphere(f"lid_upper.{side}", (0, 0, 0), r_out, C, 64, 32)
    G.cut_by_plane(up, Vector((0, -0.9, 0.2)) * r_out, (0, 0.2, 1.0), keep_positive=True)
    G.apply_mods(up)
    up.data.transform(T)
    plain = up.copy(); plain.data = up.data.copy(); C.objects.link(plain)
    b = LIDS.trim_bounds({"trim": {"outer_deg": 60, "inner_deg": 70, "back": 0.3}}, r_out, r_out)["up"]
    LIDS.trim_shell(up, T, sx, *b)
    Ti = T.inverted()
    up.data.transform(Ti)
    up.shape_key_add(name="Basis")
    for deg in (-12, 25, 50, 70):
        k = up.shape_key_add(name=f"rot{deg}")
        Rx = Matrix.Rotation(math.radians(deg), 3, "X")
        for i, v in enumerate(up.data.vertices):
            k.data[i].co = Rx @ v.co
    up.data.transform(T, shape_keys=True)
    o, i = LIDS.corner_extent(up, T, sx)
    ys = [(Ti @ v.co).y for v in up.data.vertices]
    po, pi = LIDS.corner_extent(plain, T, sx)
    out[side] = {"outer": o, "inner": i, "bound_outer": b[0], "bound_inner": b[1], "max_y_basis": max(ys),
                 "bound_back": b[2], "untrimmed_outer": po, "untrimmed_inner": pi}
R["trim"] = out
R["no_trim_bounds"] = LIDS.trim_bounds({}, 0.05, 0.05) is None
uc = np.array([[0.6, -0.8, 0.0], [0.95, -0.31225, 0.0], [0.0, -1.0, 0.0]])
s = {"r": 0.05, "sx": 1}
R["socket_no_trim"] = SOCKET._trimmed_radius(uc, s, 0.054, 0.001, "up").tolist()
s["trim"] = {"up": {"outer_x": 0.8, "inner_x": None, "back_y": None, "soft": 0.1, "cover_margin": 0.05}}
R["socket_trim"] = SOCKET._trimmed_radius(uc, s, 0.054, 0.001, "up").tolist()
RESULT.update(R)
'''


def run_probe(blender, script):
    with tempfile.TemporaryDirectory() as tmp:
        src, out = os.path.join(tmp, "probe.py"), os.path.join(tmp, "out.json")
        open(src, "w").write("import json\nCHARSYS = %r\nRESULT = {}\n%s\njson.dump(RESULT, open(%r, 'w'))\n" % (CHARSYS, script, out))
        r = subprocess.run([blender, "-b", "--factory-startup", "-P", src, "--"], capture_output=True, text=True)
        if not os.path.exists(out):
            check("unit probe ran", False, (r.stdout + r.stderr)[-800:])
            return None
        return json.load(open(out))


def unit(blender):
    R = run_probe(blender, UNIT)
    if R is None:
        return
    check("registry loads face_generic/3 from face_generic_v3", R["module"] == "face_generic_v3" and R["declares"] == ["face_generic/3"])
    f, g = R["felt"], R["gloss"]
    check("felt eye on: matte (no coat, rough), one highlight", f["coat"] == 0.0 and f["rough"] >= 0.7 and f["highlights"] == 1
          and f["tag"] == "eye/felt/1", json.dumps(f))
    check("felt eye off (default layered/1): glossy coat kept", g["coat"] > 0.5 and g["tag"] == "eye/layered/1"
          and g["highlights"] == 2, json.dumps(g))
    tol = 1e-5
    for side, t in R["trim"].items():
        check(f"lid-corner bound {side}: outer/inner extent <= trim bound over all rotations",
              t["outer"] <= t["bound_outer"] + tol and t["inner"] <= t["bound_inner"] + tol,
              f"outer {t['outer']:.5f} <= {t['bound_outer']:.5f}, inner {t['inner']:.5f} <= {t['bound_inner']:.5f}")
        check(f"back cut {side}: shell kept in front of y = -back", t["max_y_basis"] <= -t["bound_back"] + tol,
              f"{t['max_y_basis']:.5f} <= {-t['bound_back']:.5f}")
        check(f"untrimmed shell reaches past the bound {side} (the cut did something)", t["untrimmed_outer"] > t["bound_outer"] + 1e-3)
    check("no trim configured -> no bounds", R["no_trim_bounds"])
    check("socket cover radius = v2 (r_out + clearance) without trim", all(abs(v - 0.055) < 1e-12 for v in R["socket_no_trim"]),
          str(R["socket_no_trim"]))
    st = R["socket_trim"]
    check("socket cover falls to the eyeball past the trim, unchanged inside it",
          abs(st[2] - 0.055) < 1e-12 and abs(st[0] - 0.055) < 1e-12 and st[1] < 0.0535, str(st))


PROBE_FOLDS = r'''
import bpy, bmesh, json, math, sys
argv = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.open_mainfile(filepath=argv[0])
eyes = json.load(open(argv[1]))["face"]["eyes"]
sk = bpy.data.objects["body_skin"]
dg = bpy.context.evaluated_depsgraph_get()
ev = sk.evaluated_get(dg)
me = ev.to_mesh()
bm = bmesh.new(); bm.from_mesh(me); bm.transform(sk.matrix_world); bm.normal_update()
out = {"cheek": 0.0, "corner": 0.0}
for e in eyes.values():
    cx, cy, cz = e["centre_m"]; r = e["radius_m"]
    for ed in bm.edges:
        if len(ed.link_faces) != 2:
            continue
        m = (ed.verts[0].co + ed.verts[1].co) / 2
        dx, dz = m.x - cx, m.z - cz
        if abs(dx) > 0.06 or not (-0.075 < dz < 0.0) or m.y > cy + 0.02:
            continue
        n0, n1 = ed.link_faces[0].normal, ed.link_faces[1].normal
        if n0.y > 0.2 and n1.y > 0.2:
            continue
        dist = math.hypot(dx, dz)
        reg = "cheek" if dist > r * 1.25 else ("corner" if abs(dx) > 0.7 * r else None)
        if reg:
            out[reg] = max(out[reg], math.degrees(n0.angle(n1, 0)))
print("PROBE " + json.dumps(out))
'''  # the T-081 fold probe (test_face_v2_socket_wall.py), unchanged


def build_checks(blender, who):
    spec, ov = CASES[who]
    if not os.path.exists(ov):
        return
    master = arg("--" + who)
    if not master:
        out = tempfile.mkdtemp(prefix=f"t089_{who}_")
        r = subprocess.run([blender, "-b", "--factory-startup", "-P", os.path.join(CHARSYS, "build_character.py"), "--",
                            "--spec", spec, "--override", ov, "--out", out, "--no-glb", "--no-compare"],
                           capture_output=True, text=True)
        check(f"{who} candidate builds", r.returncode == 0, r.stderr[-400:] if r.returncode else "")
        master = next((os.path.join(out, f) for f in os.listdir(out) if f.endswith("_master.blend")), "")
    rep_path = os.path.join(os.path.dirname(os.path.abspath(master)), "build_report.json")
    f = json.load(open(rep_path))["face"]
    check(f"{who}: face_generic/3 with the felt eye", f.get("generator") == "face_generic/3" and bool(f.get("felt_eye")))
    bad = []
    for side, t in (f.get("lid_trim") or {}).items():
        for zone, name in (("up", f"lid_upper.{side}"), ("lo", f"lid_lower.{side}")):
            bo, bi, _ = t["bounds_m"][zone]
            ext = f["lid_corner_extent_m"][name]
            if bo is not None and ext["outer"] > bo + 2e-4:
                bad.append(f"{name} outer {ext['outer']} > {bo}")
            if bi is not None and ext["inner"] > bi + 2e-4:
                bad.append(f"{name} inner {ext['inner']} > {bi}")
    check(f"{who}: lid shells within their corner bounds (every lid key)", f.get("lid_trim") and not bad, "; ".join(bad))
    ex3 = [v["fraction"] for y in f.get("lid_shell_exposed_3q", {}).values() for v in y.values()]
    check(f"{who}: no socket rim at 3/4 (<= 10 % past-corner shell visible)", ex3 and max(ex3) <= 0.10, str(ex3))
    probe = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False)
    probe.write(PROBE_FOLDS)
    probe.close()
    r = subprocess.run([blender, "-b", "--factory-startup", "-P", probe.name, "--", master, rep_path], capture_output=True, text=True)
    line = next((l for l in r.stdout.splitlines() if l.startswith("PROBE ")), None)
    check(f"{who}: fold probe ran", line is not None, r.stderr[-400:])
    if line:
        d = json.loads(line[6:])
        lim = FOLD_LIMITS[who]
        check(f"{who}: skin smoothness no worse than the published version (cheek <= {lim['cheek']}, corner <= {lim['corner']} deg)",
              d["cheek"] <= lim["cheek"] and d["corner"] <= lim["corner"], f"cheek {d['cheek']:.1f}, corner {d['corner']:.1f} deg")
    mj = tempfile.NamedTemporaryFile(suffix=".json", delete=False).name
    subprocess.run([blender, "-b", "--factory-startup", "-P", MEASURE, "--", master, mj], capture_output=True, text=True)
    m = json.load(open(mj))["views"]
    shut = {v: [s for s in ("L", "R") if m[v]["blink100"][s].get("visible") and m[v]["blink100"][s]["area_mm2"] > 2.0]
            for v in ("front", "threequarter")}
    check(f"{who}: full blink closes both eyes (front, 3/4)", not any(shut.values()), json.dumps(shut))


def main():
    plain()
    blender = arg("--blender")
    if blender:
        unit(blender)
        for who in CASES:
            build_checks(blender, who)
    print(f"[test_face_v3] {'ALL PASS' if all(RESULTS) else 'FAIL'} {sum(RESULTS)}/{len(RESULTS)}")
    return 0 if all(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
