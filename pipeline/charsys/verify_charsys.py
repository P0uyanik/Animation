"""One-command verification of the character production pipeline with any Blender (plain Python driver).

    python3 pipeline/charsys/verify_charsys.py --blender <blender executable> --out <new or empty folder>

Steps (everything is written under --out; the store, the spec, v6 and its baseline are only read):
  1. build boy_yellow_hoodie from its spec with charsys (master + glTF, no fur)
  2. geometry fingerprint of that build, compared object by object with the frozen v6 baseline
     (docs/evaluation/boy_pilot/cloud_v6_baseline/geometry_fingerprint.json): proves the refactor reproduces v6
  3. asset-store tests on a temporary store (publish, immutability, identity lock, approve, restore, tamper detection)
  4. reuse test on the published version assets/characters/boy_yellow_hoodie/versions/<ver> (reopen, pose, episode
     linking with overrides, reopen shots, glTF import, master unchanged)
Writes CHARSYS_VERIFICATION.md and charsys_verification.json."""
import argparse
import json
import os
import subprocess
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CID = "boy_yellow_hoodie"
SPEC = os.path.join(ROOT, "assets", "characters", CID, "spec", f"{CID}.spec.json")
BASE_FP = os.path.join(ROOT, "docs", "evaluation", "boy_pilot", "cloud_v6_baseline", "geometry_fingerprint.json")


def compare_fingerprints(base, new, tol=5e-4):
    b, n = json.load(open(base))["objects"], json.load(open(new))["objects"]
    out = {"missing": sorted(set(b) - set(n)), "extra": sorted(set(n) - set(b)), "count_mismatch": [], "hash_differs": [],
           "worst_numeric_m": 0.0}
    for k in set(b) & set(n):
        x, y = b[k], n[k]
        if x["type"] != "MESH":
            if x != y:
                out["count_mismatch"].append(k)
            continue
        for f in ("vertices", "faces", "vertex_groups", "shape_keys", "materials"):
            if x[f] != y[f]:
                out["count_mismatch"].append(f"{k}.{f}")
        if x["vertices"]:
            xs = x["centroid"] + [x["rms_radius"]] + sum(x["bbox"], [])
            ys = y["centroid"] + [y["rms_radius"]] + sum(y["bbox"], [])
            out["worst_numeric_m"] = max(out["worst_numeric_m"], max(abs(p - q) for p, q in zip(xs, ys)))
        if x["coords_hash"] != y["coords_hash"]:
            out["hash_differs"].append(k)
    out["ok"] = not out["missing"] and not out["extra"] and not out["count_mismatch"] and out["worst_numeric_m"] <= tol
    return out


def main():
    raise SystemExit("T-127 probe: deliberately broken")
    ap = argparse.ArgumentParser()
    ap.add_argument("--blender", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--version", default="")
    a = ap.parse_args()
    out = os.path.abspath(a.out)
    for p in ("assets", "docs", "pipeline"):
        if os.path.commonpath([out, os.path.join(ROOT, p)]) == os.path.join(ROOT, p):
            raise SystemExit(f"--out must not be inside {p}/")
    if os.path.exists(out) and os.listdir(out):
        raise SystemExit("--out must be a new or empty folder")
    os.makedirs(out, exist_ok=True)
    store = os.path.join(ROOT, "assets", "characters", CID, "versions")
    ver = a.version or json.load(open(os.path.join(store, "index.json")))["pointers"]["reference"]
    log = open(os.path.join(out, "run.log"), "w")
    steps = {}

    def run(name, cmd):
        log.write(f"\n===== {name}: {' '.join(cmd)}\n")
        log.flush()
        t = time.time()
        r = subprocess.run(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        steps[name] = {"ok": r.returncode == 0, "seconds": round(time.time() - t, 1)}
        print(f"[verify_charsys] {name}: {'ok' if r.returncode == 0 else 'FAILED'}", flush=True)
        return r.returncode == 0

    bl = lambda script, *args: [a.blender, "-b", "--factory-startup", "-P", os.path.join(ROOT, script), "--", *args]  # noqa: E731
    build = os.path.join(out, "build")
    ok = run("build from spec", bl("pipeline/charsys/build_character.py", "--spec", SPEC, "--out", build, "--no-compare"))
    fp = os.path.join(out, "geometry_fingerprint.json")
    ok = ok and run("geometry fingerprint", bl("pipeline/blender/boy_pilot/fingerprint.py", os.path.join(build, f"{CID}_master.blend"), fp))
    eq = compare_fingerprints(BASE_FP, fp) if ok else {"ok": False}
    steps["equals v6 geometry"] = {"ok": eq["ok"]}
    run("asset store tests", [sys.executable, os.path.join(ROOT, "pipeline", "charsys", "tests", "test_store.py"), "--build", build,
                              "--out", os.path.join(out, "test_store.json")])
    run("reuse test", bl("pipeline/charsys/tests/reuse_test.py", os.path.join(store, ver), os.path.join(out, "reuse")))
    reuse = json.load(open(os.path.join(out, "reuse", "reuse_test.json"))) if os.path.exists(os.path.join(out, "reuse", "reuse_test.json")) else {}
    stt = json.load(open(os.path.join(out, "test_store.json"))) if os.path.exists(os.path.join(out, "test_store.json")) else {}
    verdict = "PASS" if all(s["ok"] for s in steps.values()) and reuse.get("pass") and stt.get("pass") else "FAIL"
    res = {"verdict": verdict, "version_tested": ver, "steps": steps, "v6_geometry": eq, "reuse": reuse, "store": stt}
    json.dump(res, open(os.path.join(out, "charsys_verification.json"), "w"), indent=1)
    L = [f"# Character pipeline verification: **{verdict}**", "", f"Blender: {reuse.get('blender', '?')}. Store version tested: {ver}.", "",
         "| Step | Result |", "| --- | --- |"]
    L += [f"| {k} | {'ok' if v['ok'] else 'FAILED'} |" for k, v in steps.items()]
    L += ["", f"v6 geometry: missing {eq.get('missing')}, extra {eq.get('extra')}, count mismatches {eq.get('count_mismatch')}, "
              f"worst numeric difference {eq.get('worst_numeric_m')} m, exact-hash differences (informational) {eq.get('hash_differs')}", "",
          "| Test | Check | Result | Detail |", "| --- | --- | --- | --- |"]
    for t, d in reuse.get("tests", {}).items():
        L += [f"| {t} | {c['check']} | {'PASS' if c['pass'] else 'FAIL'} | {json.dumps(c['detail']) if c['detail'] is not None else ''} |" for c in d["checks"]]
    L += [f"| store | {c['check']} | {'PASS' if c['pass'] else 'FAIL'} | {json.dumps(c['detail']) if c['detail'] is not None else ''} |"
          for c in stt.get("checks", [])]
    open(os.path.join(out, "CHARSYS_VERIFICATION.md"), "w").write("\n".join(L) + "\n")
    print(f"[verify_charsys] {verdict} -> {os.path.join(out, 'CHARSYS_VERIFICATION.md')}")


if __name__ == "__main__":
    main()
