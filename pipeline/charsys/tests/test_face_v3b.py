"""T-089b: face polish checks on top of face_generic/3 (T-089's test_face_v3.py, reused unchanged).

    python3 pipeline/charsys/tests/test_face_v3b.py [--blender <exe>] [--boy <master.blend>] [--girl <master.blend>]
        [--unit]   also run test_face_v3's Blender unit checks

Plain checks (no Blender): every test_face_v3 plain check, with the T-089b candidates in place of the T-089 ones
(published specs still pin face_generic/2, candidates pin face_generic/3, no character names in the shared v3 code),
plus: the new socket option corner_relax_iterations defaults to 0 (opt-in; face_generic/3 builds without it are
unchanged) and only the girl candidate sets it.
Build checks (a master per character: --boy/--girl, else built from the published spec + T-089b candidate):
  * every test_face_v3 build check with the same limits (felt eye; lid shells within their corner bounds; <= 10 % 3/4
    socket rim; cheek folds <= 45 deg and eye-corner folds no sharper than the published version; full blink closes
    in front and 3/4 within 1.25 x the published residue);
  * owner focus (OWNER_DECISIONS 2026-11-18 ~22:35Z), measured with T-089's measure_eyes.py (front, neutral):
      boy  heavy sleepy lids: opening height / width <= BOY_MAX_HW (T-089 candidate 0.62, reference about 0.45) and
           the eye size kept: visible width >= BOY_MIN_WIDTH_MM (T-089 candidate 62.5 mm on this tool);
      girl wider, rounder eyes: visible width >= GIRL_MIN_WIDTH_MM (T-089 candidate 61.25 mm, +8 %); rounder fuller
           face: the build report records the round-face options (outline superellipse, face width, cheek fullness)
           and the corner relax ran."""
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_face_v3 as V3  # noqa: E402

CHARS = V3.CHARS
V3.CASES = {
    "boy": (os.path.join(CHARS, "boy_yellow_hoodie", "spec", "boy_yellow_hoodie.2.0.0.spec.json"),
            os.path.join(CHARS, "boy_yellow_hoodie", "spec", "candidates", "T-089b", "boy_face3b.override.json")),
    "girl": (os.path.join(CHARS, "girl_auburn_bun_glasses", "spec", "girl_auburn_bun_glasses.0.11.0.spec.json"),
             os.path.join(CHARS, "girl_auburn_bun_glasses", "spec", "candidates", "T-089b", "girl_face3b.override.json")),
}
BOY_MAX_HW = 0.52
BOY_MIN_WIDTH_MM = 60.0
GIRL_MIN_WIDTH_MM = 66.0
check = V3.check


def plain_b():
    V3.plain()
    src = open(os.path.join(V3.CHARSYS, "face_v3", "socket.py")).read()
    check("socket corner_relax_iterations is opt-in (default 0)",
          re.search(r'_f\(cfg, "corner_relax_iterations", 0\)', src) is not None)
    for who, (_, ov) in V3.CASES.items():
        sock = json.load(open(ov))["override"]["face"]["eyes"].get("socket", {})
        want = who == "girl"
        check(f"{who} candidate {'sets' if want else 'does not set'} corner_relax_iterations",
              ("corner_relax_iterations" in sock) == want)


def master_for(blender, who):
    """The master test_face_v3.build_checks used (it builds into a temp dir when --boy/--girl is absent)."""
    m = V3.arg("--" + who)
    if m:
        return m
    spec, ov = V3.CASES[who]
    out = tempfile.mkdtemp(prefix=f"t089b_{who}_")
    r = subprocess.run([blender, "-b", "--factory-startup", "-P", os.path.join(V3.CHARSYS, "build_character.py"), "--",
                        "--spec", spec, "--override", ov, "--out", out, "--no-glb", "--no-compare"], capture_output=True, text=True)
    check(f"{who} T-089b candidate builds", r.returncode == 0, r.stderr[-400:] if r.returncode else "")
    sys.argv += ["--" + who, os.path.join(out, next(f for f in os.listdir(out) if f.endswith("_master.blend")))]
    return sys.argv[-1]


def focus_checks(blender, who, master):
    mj = tempfile.NamedTemporaryFile(suffix=".json", delete=False).name
    subprocess.run([blender, "-b", "--factory-startup", "-P", V3.MEASURE, "--", master, mj], capture_output=True, text=True)
    n = json.load(open(mj))["views"]["front"]["neutral"]
    w = min(n[s]["width_mm"] for s in ("L", "R"))
    hw = max(n[s]["height_mm"] / n[s]["width_mm"] for s in ("L", "R"))
    face = json.load(open(os.path.join(os.path.dirname(os.path.abspath(master)), "build_report.json")))["face"]
    if who == "boy":
        check(f"boy heavy lids: front opening height/width <= {BOY_MAX_HW}", hw <= BOY_MAX_HW, f"{hw:.3f}")
        check(f"boy eye size kept: front width >= {BOY_MIN_WIDTH_MM} mm", w >= BOY_MIN_WIDTH_MM, f"{w:.2f} mm")
    else:
        check(f"girl wider eyes: front width >= {GIRL_MIN_WIDTH_MM} mm", w >= GIRL_MIN_WIDTH_MM, f"{w:.2f} mm, h/w {hw:.3f}")
        sh = face.get("shape", {})
        check("girl rounder fuller face: round-face options in the build report",
              "outline" in sh and "face_width_m" in sh, json.dumps({k: sh.get(k) for k in ("outline", "face_width_m")}))
        check("girl corner relax ran", (face.get("lid_socket") or {}).get("corner_relaxed_vertices", 0) > 0)


def main():
    plain_b()
    blender = V3.arg("--blender")
    if blender:
        if "--unit" in sys.argv:
            V3.unit(blender)
        for who in V3.CASES:
            m = master_for(blender, who)
            V3.build_checks(blender, who)
            focus_checks(blender, who, m)
    R = V3.RESULTS
    print(f"[test_face_v3b] {'ALL PASS' if all(R) else 'FAIL'} {sum(R)}/{len(R)}")
    return 0 if all(R) else 1


if __name__ == "__main__":
    sys.exit(main())
