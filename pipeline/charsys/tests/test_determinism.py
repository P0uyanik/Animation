"""Build a character twice and require identical geometry fingerprints.

Plain-Python/check_all usage:
  python pipeline/charsys/tests/test_determinism.py --blender <blender> --out <new-dir>

Use ``--character all`` for the slower boy+girl audit. The default boy check is
the CI-sized regression test for the legacy hair_clumps path.
"""
import argparse
import json
import os
import subprocess
import sys


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
# Shared format-2 fingerprint tool (T-038). The frozen pipeline/blender/boy_pilot/fingerprint.py stays reserved for
# the v6 baseline comparison in verify_charsys.
FINGERPRINT = os.path.join(ROOT, "pipeline", "charsys", "fingerprint_v2.py")
CHARS = {
    "boy": ("boy_yellow_hoodie", "assets/characters/boy_yellow_hoodie/spec/boy_yellow_hoodie.spec.json"),
    "girl": ("girl_auburn_bun_glasses", "assets/characters/girl_auburn_bun_glasses/spec/girl_auburn_bun_glasses.spec.json"),
}


def clean_fingerprint(path):
    data = json.load(open(path, encoding="utf-8"))
    data.pop("file", None)
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blender", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--character", choices=["boy", "girl", "all"], default="boy")
    a = ap.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else None)
    out = os.path.abspath(a.out)
    if os.path.exists(out) and os.listdir(out):
        raise SystemExit("--out must be a new or empty folder")
    os.makedirs(out, exist_ok=True)

    sys.path.insert(0, os.path.join(ROOT, "pipeline", "charsys"))
    import determinism
    env = determinism.subprocess_env()
    selected = CHARS if a.character == "all" else {a.character: CHARS[a.character]}
    results = {}
    for label, (cid, spec) in selected.items():
        fingerprints = []
        strict_fingerprints = []
        for run in (1, 2):
            build = os.path.join(out, f"{label}_{run}")
            os.makedirs(build)
            cmd = [a.blender, "-b", "--factory-startup", "-t", "1", "-P",
                   os.path.join(ROOT, "pipeline", "charsys", "build_character.py"), "--",
                   "--spec", os.path.join(ROOT, spec), "--out", build, "--no-glb", "--no-compare"]
            log_path = os.path.join(build, "build.log")
            with open(log_path, "w", encoding="utf-8") as log:
                subprocess.run(cmd, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
            # Both grids are required to match; see pipeline/charsys/fingerprint_v2.py for why there are two.
            fp = os.path.join(build, "fingerprint_0.1mm.json")
            subprocess.run([a.blender, "-b", "--factory-startup", "-t", "1", "-P", FINGERPRINT, "--",
                            os.path.join(build, f"{cid}_master.blend"), fp, "--grid-m", "0.0001"],
                           cwd=ROOT, env=env, stdout=subprocess.DEVNULL, check=True)
            fingerprints.append(fp)
            strict_fp = os.path.join(build, "fingerprint_0.01mm.json")
            subprocess.run([a.blender, "-b", "--factory-startup", "-t", "1", "-P", FINGERPRINT, "--",
                            os.path.join(build, f"{cid}_master.blend"), strict_fp, "--grid-m", "0.00001"],
                           cwd=ROOT, env=env, stdout=subprocess.DEVNULL, check=True)
            strict_fingerprints.append(strict_fp)
        first, second = map(clean_fingerprint, fingerprints)
        strict_first, strict_second = map(clean_fingerprint, strict_fingerprints)
        changed = sorted(name for name in set(first["objects"]) | set(second["objects"])
                         if first["objects"].get(name) != second["objects"].get(name))
        strict_changed = sorted(name for name in set(strict_first["objects"]) | set(strict_second["objects"])
                                if strict_first["objects"].get(name) != strict_second["objects"].get(name))
        results[label] = {"pass": first == second and strict_first == strict_second,
                          "changed_objects": changed, "strict_changed_objects": strict_changed,
                          "fingerprints": [os.path.relpath(p, out) for p in fingerprints],
                          "strict_fingerprints": [os.path.relpath(p, out) for p in strict_fingerprints]}

    passed = all(item["pass"] for item in results.values())
    report = {"pass": passed, "characters": results}
    with open(os.path.join(out, "determinism.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1, sort_keys=True)
        f.write("\n")
    print(f"[test_determinism] {'PASS' if passed else 'FAIL'}: {json.dumps(results, sort_keys=True)}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
