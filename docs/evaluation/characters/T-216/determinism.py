#!/usr/bin/env python3
"""T-216 export determinism of the P3 candidate (the T-056 full-mode procedure, applied to a spec + overrides).

    python3 docs/evaluation/characters/T-216/determinism.py <out dir> --spec <spec> --override <o> [--override ...] \
        [--runs 2] [--blender blender]

Per run: a clean single-thread build (build_character.py -t 1), fingerprint_v2 at 0.01 mm, and two exports:
export/5 (exporter pinned by an extra override, as test_export_determinism.py does; byte-reproducible by design)
and the candidate's own export/4 pin (geometry.bin and character.json compared; its manifest records the .blend hash,
which differs between builds by design). Writes <out>/determinism.json."""
import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
CHARSYS = os.path.join(ROOT, "pipeline", "charsys")


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def files(pkg, skip=()):
    return {f: sha(os.path.join(pkg, f)) for f in sorted(os.listdir(pkg)) if f not in skip}


def main():
    a = sys.argv[1:]
    out = os.path.abspath(a[0])
    spec = a[a.index("--spec") + 1]
    overrides = [a[i + 1] for i, x in enumerate(a) if x == "--override"]
    runs = int(a[a.index("--runs") + 1]) if "--runs" in a else 2
    bl = a[a.index("--blender") + 1] if "--blender" in a else "blender"
    os.makedirs(out, exist_ok=False)
    e5 = os.path.join(out, "export5.override.json")
    json.dump({"generators": {"exporter": "export/5"}}, open(e5, "w"))
    prof = os.path.join(CHARSYS, "rig_profiles", "humanoid_rigify.json")
    res = {"spec": spec, "overrides": overrides, "runs": []}
    for run in range(1, runs + 1):
        r = {}
        for tag, extra in (("export4", []), ("export5", [e5])):
            d = os.path.join(out, f"{tag}_{run}")
            os.makedirs(d)
            flags = ["--spec", spec, "--out", d, "--no-glb", "--no-compare"]
            for o in overrides + extra:
                flags += ["--override", o]
            with open(os.path.join(d, "build.log"), "w") as log:
                subprocess.run([bl, "-b", "--factory-startup", "-t", "1", "-P", os.path.join(CHARSYS, "build_character.py"),
                                "--", *flags], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
            master = next(os.path.join(d, f) for f in os.listdir(d) if f.endswith("_master.blend"))
            if tag == "export4":
                fp = os.path.join(d, "fingerprint.json")
                subprocess.run([bl, "-b", "--factory-startup", "-t", "1", "-P", os.path.join(CHARSYS, "fingerprint_v2.py"),
                                "--", master, fp, "--grid-m", "0.00001"], cwd=ROOT, stdout=subprocess.DEVNULL, check=True)
                fpd = json.load(open(fp))
                fpd.pop("file", None)
                r["fingerprint_sha256"] = hashlib.sha256(json.dumps(fpd, sort_keys=True).encode()).hexdigest()
            pkg = os.path.join(d, "package")
            with open(os.path.join(d, "export.log"), "w") as log:
                subprocess.run([bl, "-b", "--factory-startup", "-P", os.path.join(CHARSYS, "export_engine.py"), "--",
                                "--blend", master, "--profile", prof, "--out", pkg],
                               cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
            r[tag] = files(pkg, skip=("manifest.json",) if tag == "export4" else ())
            os.remove(master)
        res["runs"].append(r)
        print(json.dumps(r)[:300], flush=True)
    first = res["runs"][0]
    res["fingerprints_identical"] = all(x["fingerprint_sha256"] == first["fingerprint_sha256"] for x in res["runs"])
    res["export5_identical"] = all(x["export5"] == first["export5"] for x in res["runs"])
    res["export4_identical_without_manifest"] = all(x["export4"] == first["export4"] for x in res["runs"])
    res["pass"] = res["fingerprints_identical"] and res["export5_identical"] and res["export4_identical_without_manifest"]
    json.dump(res, open(os.path.join(out, "determinism.json"), "w"), indent=1)
    print({k: v for k, v in res.items() if k != "runs"})
    return 0 if res["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
