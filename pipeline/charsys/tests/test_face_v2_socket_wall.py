"""T-081: face_generic/2 socket-wall smoothing (opt-in) and the girl 0.11.0 version.

    python3 pipeline/charsys/tests/test_face_v2_socket_wall.py --blender <exe> [--girl011 <master.blend>]

Plain checks (no Blender):
  * 0.11.0 spec loads and pins face_generic/2, body_generic/2, groom/2; brown iris; the rest mouth is the closed
    gentle smile with lifted cheeks (soft_smile, MouthWide 0, CheekRaise > 0); it references personality 1.0.0;
  * 0.11.0 is the current version (owner decision 2026-11-18): fidelity baseline and approved pointer agree; it pins
    presets/2 for its skin-felt/2 skin;
  * the new socket options default to the T-065 behaviour (no spec except 0.11.0 sets them).
Build checks (a master built from the 0.11.0 spec; --girl011 reuses one):
  * the wall smoothing ran (report lid_socket.wall_smoothed_vertices > 0);
  * no sharp folds on body_skin around the eyes: cheek and eye-corner edges <= 45 deg dihedral (0.10.0 had cheek
    folds up to 150 deg, the unsmoothed face v2 corner folds up to 92 deg); upper lid shells <= 8 % visible.
Without --blender only the plain checks run."""
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

GIRL = os.path.join(ROOT, "assets", "characters", "girl_auburn_bun_glasses", "spec")
SPEC_011 = os.path.join(GIRL, "girl_auburn_bun_glasses.0.11.0.spec.json")
RESULTS = []

PROBE = r'''
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
'''


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def check(name, ok, detail=""):
    RESULTS.append(bool(ok))
    print(f"[test_face_v2_socket_wall] {'PASS' if ok else 'FAIL'} {name}{(': ' + detail) if detail else ''}")


def plain():
    s, info = SPEC.load(SPEC_011)
    g = info["versions"]["generators"]
    check("0.11.0 pins face_generic/2, body_generic/2, groom/2",
          (g["face"], g["body"], g["groom"]) == ("face_generic/2", "body_generic/2", "groom/2"), str(g))
    iris = (s["face"]["eyes"].get("iris") or {}).get("srgb")
    check("brown eyes kept", iris is not None and iris[0] > iris[2] and iris[1] > iris[2], str(iris))
    m = s["face"]["mouth"]
    mix = m.get("rest_mix") or {}
    check("rest = closed gentle smile with lifted cheeks", m.get("rest_shape") == "soft_smile" and mix.get("MouthWide", 0) == 0
          and mix.get("CheekRaise", 0) > 0 and mix.get("MouthSmile", 0) > 0, json.dumps(mix))
    p = (s.get("animation") or {}).get("personality") or {}
    check("references personality profile 1.0.0", p.get("profile") == "girl_auburn_bun_glasses" and p.get("profile_version") == "1.0.0"
          and os.path.exists(os.path.join(ROOT, p.get("path", "-"))))
    check("socket wall smoothing opted in", s["face"]["eyes"]["socket"].get("wall_smooth_iterations", 0) > 0)
    # 0.11.0 is the current version since the owner decision of 2026-11-18 (docs/process/OWNER_DECISIONS.md): the
    # fidelity baseline builds it, the asset store's approved pointer names it, and 0.10.0 stays published
    base = json.load(open(os.path.join(ROOT, "docs", "evaluation", "characters", "fidelity_baseline.json")))
    cur = base["characters"]["girl_auburn_bun_glasses"]
    index = json.load(open(os.path.join(ROOT, "assets", "characters", "girl_auburn_bun_glasses", "versions", "index.json")))
    check("current version: fidelity baseline and approved pointer both name 0.11.0",
          cur["build"].endswith("girl_auburn_bun_glasses.0.11.0.spec.json") and not cur.get("overrides")
          and index["pointers"]["approved"] == "0.11.0" and "0.10.0" in index["versions"],
          f"{cur['build']} / approved {index['pointers']['approved']}")
    check("0.11.0 pins the presets/2 skin family it uses", s["generators"].get("materials") == "presets/2"
          and s["materials"]["assignments"]["skin"]["preset"] == "skin-felt/2")
    others = [f for f in glob.glob(os.path.join(ROOT, "assets", "characters", "*", "spec", "*.json")) if os.path.abspath(f) != SPEC_011]
    users = [os.path.basename(f) for f in others if any(k in open(f).read() for k in ("wall_smooth_iterations", "corner_blend_deg", "corner_close_deg"))]
    check("no other spec sets the new socket options", not users, ", ".join(users))


def build_checks(blender):
    master = arg("--girl011")
    if not master:
        out = tempfile.mkdtemp(prefix="t081_")
        r = subprocess.run([blender, "-b", "--factory-startup", "-P", os.path.join(CHARSYS, "build_character.py"), "--",
                            "--spec", SPEC_011, "--out", out, "--no-glb", "--no-compare"], capture_output=True, text=True)
        check("0.11.0 builds", r.returncode == 0, r.stderr[-400:] if r.returncode else "")
        master = os.path.join(out, "girl_auburn_bun_glasses_master.blend")
    rep = json.load(open(os.path.join(os.path.dirname(master), "build_report.json")))
    f = rep["face"]
    check("wall smoothing ran", f["lid_socket"].get("wall_smoothed_vertices", 0) > 0, str(f["lid_socket"].get("wall_smoothed_vertices")))
    ups = [v for k, v in f["lid_shell_exposed"].items() if k.startswith("lid_upper")]
    check("upper lid shells <= 8 % visible", ups and max(ups) <= 0.08, str(f["lid_shell_exposed"]))
    probe = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False)
    probe.write(PROBE)
    probe.close()
    r = subprocess.run([blender, "-b", "--factory-startup", "-P", probe.name, "--", master,
                        os.path.join(os.path.dirname(master), "build_report.json")], capture_output=True, text=True)
    line = next((l for l in r.stdout.splitlines() if l.startswith("PROBE ")), None)
    check("fold probe ran", line is not None, r.stderr[-400:])
    if line:
        d = json.loads(line[6:])
        check("no sharp cheek folds (<= 45 deg)", d["cheek"] <= 45.0, f"{d['cheek']:.1f} deg")
        check("no sharp eye-corner folds (<= 45 deg)", d["corner"] <= 45.0, f"{d['corner']:.1f} deg")


def main():
    plain()
    blender = arg("--blender")
    if blender:
        build_checks(blender)
    else:
        print("[test_face_v2_socket_wall] build checks skipped (no --blender)")
    print(f"[test_face_v2_socket_wall] {'ALL PASS' if all(RESULTS) else 'FAIL'} {sum(RESULTS)}/{len(RESULTS)}")
    return 0 if all(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
