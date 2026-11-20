"""Build a character twice and require identical geometry fingerprints.

Plain-Python/check_all usage:
  python pipeline/charsys/tests/test_determinism.py --blender <blender> --out <new-dir>

Use ``--character all`` for the slower boy+girl audit. The default boy check is
the CI-sized regression test for the legacy hair_clumps path.

T-158: ``--character current`` builds the current versions (boy 2.2.0, girl 0.13.0) and the third character's
candidate spec; ``--runs N`` (default 2) builds each N times and requires every run to match run 1; ``--jobs N``
runs builds in parallel (each build stays single-threaded, -t 1).
"""
import argparse
import concurrent.futures
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
CURRENT = {  # T-158: current published versions + the third character (candidate spec, not published)
    "boy_2.2.0": ("boy_yellow_hoodie", "assets/characters/boy_yellow_hoodie/spec/boy_yellow_hoodie.2.2.0.spec.json"),
    "girl_0.13.0": ("girl_auburn_bun_glasses",
                    "assets/characters/girl_auburn_bun_glasses/spec/girl_auburn_bun_glasses.0.13.0.spec.json"),
    "third_0.1.0": ("girl_white_hair_blue_dress", "assets/characters/girl_white_hair_blue_dress/spec/candidates/"
                    "T-126a/girl_white_hair_blue_dress.0.1.0.spec.json"),
}


def clean_fingerprint(path):
    data = json.load(open(path, encoding="utf-8"))
    data.pop("file", None)
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blender", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--character", choices=["boy", "girl", "all", "current"], default="boy")
    ap.add_argument("--runs", type=int, default=2)
    ap.add_argument("--jobs", type=int, default=1)
    a = ap.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else None)
    if a.runs < 2:
        raise SystemExit("--runs must be at least 2")
    out = os.path.abspath(a.out)
    if os.path.exists(out) and os.listdir(out):
        raise SystemExit("--out must be a new or empty folder")
    os.makedirs(out, exist_ok=True)

    sys.path.insert(0, os.path.join(ROOT, "pipeline", "charsys"))
    import determinism
    env = determinism.subprocess_env()
    if a.character == "current":
        selected = CURRENT
    else:
        selected = CHARS if a.character == "all" else {a.character: CHARS[a.character]}

    def build_and_fingerprint(label, cid, spec, run):
        build = os.path.join(out, f"{label}_{run}")
        os.makedirs(build)
        cmd = [a.blender, "-b", "--factory-startup", "-t", "1", "-P",
               os.path.join(ROOT, "pipeline", "charsys", "build_character.py"), "--",
               "--spec", os.path.join(ROOT, spec), "--out", build, "--no-glb", "--no-compare"]
        log_path = os.path.join(build, "build.log")
        with open(log_path, "w", encoding="utf-8") as log:
            subprocess.run(cmd, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
        # Both grids are required to match; see pipeline/charsys/fingerprint_v2.py for why there are two.
        fps = []
        for name, grid in (("fingerprint_0.1mm.json", "0.0001"), ("fingerprint_0.01mm.json", "0.00001")):
            fp = os.path.join(build, name)
            subprocess.run([a.blender, "-b", "--factory-startup", "-t", "1", "-P", FINGERPRINT, "--",
                            os.path.join(build, f"{cid}_master.blend"), fp, "--grid-m", grid],
                           cwd=ROOT, env=env, stdout=subprocess.DEVNULL, check=True)
            fps.append(fp)
        return fps

    jobs = [(label, cid, spec, run) for label, (cid, spec) in selected.items() for run in range(1, a.runs + 1)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, a.jobs)) as pool:
        done = dict(zip(jobs, pool.map(lambda j: build_and_fingerprint(*j), jobs)))

    def changed_objects(x, y):
        return sorted(name for name in set(x["objects"]) | set(y["objects"])
                      if x["objects"].get(name) != y["objects"].get(name))

    results = {}
    for label, (cid, spec) in selected.items():
        runs = [done[(label, cid, spec, run)] for run in range(1, a.runs + 1)]
        coarse = [clean_fingerprint(r[0]) for r in runs]
        strict = [clean_fingerprint(r[1]) for r in runs]
        changed = {f"run_{i + 1}": changed_objects(coarse[0], c) for i, c in enumerate(coarse) if i and c != coarse[0]}
        strict_changed = {f"run_{i + 1}": changed_objects(strict[0], c) for i, c in enumerate(strict)
                          if i and c != strict[0]}
        same = all(c == coarse[0] for c in coarse) and all(c == strict[0] for c in strict)
        results[label] = {"pass": same, "runs": a.runs, "spec": spec,
                          # run 2 vs run 1 lists kept as before; per-run lists (vs run 1) for N > 2
                          "changed_objects": changed.get("run_2", []), "strict_changed_objects": strict_changed.get("run_2", []),
                          "changed_by_run": changed, "strict_changed_by_run": strict_changed,
                          "fingerprints": [os.path.relpath(r[0], out) for r in runs],
                          "strict_fingerprints": [os.path.relpath(r[1], out) for r in runs]}

    passed = all(item["pass"] for item in results.values())
    report = {"pass": passed, "characters": results}
    with open(os.path.join(out, "determinism.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1, sort_keys=True)
        f.write("\n")
    print(f"[test_determinism] {'PASS' if passed else 'FAIL'}: {json.dumps(results, sort_keys=True)}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
