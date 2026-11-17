#!/usr/bin/env python3
"""Full all-character regression and unchanged-character guard (delivery plan §5.1, §5.2; T-041).

    python tools/regression/run.py --blender <blender> --out <dir> [--character <id> ...] [--jobs N]
        [--base origin/main] [--no-fidelity] [--write-baseline] [--noise]

For every character in assets/characters (or the given ones), in parallel:
  1. build      pipeline/charsys/build_character.py (spec + the overrides of its current version, no GLB/compare)
  2. fingerprint pipeline/charsys/fingerprint_v2.py at 0.01 mm
  3. export     pipeline/charsys/export_engine.py (engine package; digest without the .blend byte hash)
  4. renders    pipeline/charsys/tools/groom_turnaround.py with the fixed cameras of tools/regression/views.json
                (turnaround + face close-up, low samples, fixed seed, OIDN)
  5. fidelity   tools/fidelity/run.py, score vs docs/evaluation/characters/fidelity_baseline.json (drop > 2 = FAIL)
  6. compare    against the approved baseline docs/evaluation/regression/baselines/<id>/<spec version>/
Characters whose spec inputs are unchanged versus --base must be identical to the approved baseline (= main):
fingerprint byte-equal, export digest equal, every render within the measured noise threshold
(tools/regression/render_noise_threshold.json). Any difference is a FAIL, even if it looks better. Characters
whose spec changed are reported (differences listed, path B: owner review); only their fidelity can fail.

--write-baseline writes baseline candidates (golden.json, fingerprint.json, renders) to <out>/baselines/; they become
approved only when the Supervisor commits them under docs/evaluation/regression/baselines (guarded path).
--noise builds and renders every character twice and reports the differences (the noise-threshold measurement).
Writes <out>/<id>/result.json per character and <out>/regression.json. Exit 1 if any character fails.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import tiers  # noqa: E402

VIEWS = HERE / "views.json"
NOISE = HERE / "render_noise_threshold.json"
SCHEMA = "plush-studio.regression/1"
GOLDEN_SCHEMA = "plush-studio.regression-golden/1"


def run_logged(command, log: Path, env=None) -> int:
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8", errors="replace") as handle:
        handle.write("$ " + " ".join(str(c) for c in command) + "\n")
        handle.flush()
        return subprocess.run([str(c) for c in command], cwd=ROOT, stdout=handle, stderr=subprocess.STDOUT,
                              env=env).returncode


def blender_env() -> dict:
    sys.path.insert(0, str(ROOT / "pipeline" / "charsys"))
    import determinism  # noqa: E402
    return determinism.subprocess_env()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical(data) -> bytes:
    return (json.dumps(data, indent=1, sort_keys=True) + "\n").encode("utf-8")


def load_image(path: Path):
    import numpy as np
    from PIL import Image
    with Image.open(path) as image:
        return np.asarray(image.convert("RGBA"), dtype=np.float64) / 255.0


def image_difference(a: Path, b: Path) -> dict:
    import numpy as np
    x, y = load_image(a), load_image(b)
    if x.shape != y.shape:
        return {"rmse": 1.0, "changed_fraction": 1.0, "max_abs": 1.0, "shape_mismatch": [list(x.shape), list(y.shape)]}
    diff = np.abs(x - y)
    return {"rmse": round(float(np.sqrt((diff ** 2).mean())), 6),
            "changed_fraction": round(float((diff.max(axis=2) > 8 / 255).mean()), 6),
            "max_abs": round(float(diff.max()), 6)}


def within_noise(diff: dict, noise: dict) -> bool:
    return diff["rmse"] <= noise["max_rmse"] and diff["changed_fraction"] <= noise["max_changed_fraction"]


EXPORT_GRID_M = 1e-5        # position quantization for the order-independent triangle hash (as fingerprint_v2)
EXPORT_TOLERANCE = 1e-5     # absolute tolerance on per-buffer statistics (mean, rms, min, max)
DTYPES = {"float32": "<f4", "uint32": "<u4", "uint16": "<u2", "uint8": "u1", "int32": "<i4", "int16": "<i2"}


def _buffers(node, path=""):
    if isinstance(node, dict):
        if {"offset", "count", "dtype"} <= set(node):
            yield path, node
            return
        for key, value in node.items():
            yield from _buffers(value, f"{path}/{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _buffers(value, f"{path}[{index}]")


def export_summary(package: Path) -> dict:
    """Order-independent summary of an engine package (T-041 finding: two identical builds export the same
    geometry with a different triangle order and float noise <= 1e-6, so raw bytes cannot be compared).
    meta_sha256: character.json without byte hashes (exact). Per buffer: count plus mean/rms/min/max (compared with
    EXPORT_TOLERANCE). Per mesh: a hash of the sorted set of triangles, each the sorted triple of its vertex positions
    quantized to 0.01 mm, and a hash of the sorted per-vertex joint tuples (exact)."""
    import numpy as np
    meta = json.loads((package / "character.json").read_text(encoding="utf-8"))
    meta.get("source", {}).pop("blend_sha256", None)  # the .blend container bytes are not reproducible
    for entry in meta.get("files", {}).values():
        if isinstance(entry, dict):
            entry.pop("sha256", None)
    raw = (package / "geometry.bin").read_bytes() if (package / "geometry.bin").is_file() else b""
    out = {"meta_sha256": hashlib.sha256(canonical(meta)).hexdigest(), "buffers": {}, "meshes": {}}

    def array(desc):
        dtype = np.dtype(DTYPES[desc["dtype"]])
        return np.frombuffer(raw, dtype, int(desc["count"]), int(desc["offset"]))

    for path, desc in _buffers(meta):
        if path.endswith("/indices"):
            continue  # vertex numbering is not reproducible; triangle_set_sha256 covers the topology
        values = array(desc).astype(np.float64)
        stats = [int(values.size)]
        if values.size:
            stats += [round(float(values.mean()), 7), round(float(np.sqrt((values ** 2).mean())), 7),
                      round(float(values.min()), 7), round(float(values.max()), 7)]
        out["buffers"][path] = stats
    for mesh in meta.get("meshes", []):
        if not all(k in mesh for k in ("positions", "indices")):
            continue
        pos = array(mesh["positions"]).astype(np.float64).reshape(-1, 3)
        scaled = pos / EXPORT_GRID_M
        q = (np.sign(scaled) * np.floor(np.abs(scaled) + 0.5)).astype("<i8")
        tri = array(mesh["indices"]).astype(np.int64).reshape(-1, 3)
        corners = np.ascontiguousarray(q[tri])             # (T, 3 corners, xyz)
        record = np.dtype([("x", "<i8"), ("y", "<i8"), ("z", "<i8")])
        corners = np.sort(corners.view(record).reshape(-1, 3), axis=1)   # canonical corner order per triangle
        tris = np.ascontiguousarray(corners).view("<i8").reshape(-1, 9)
        tris = tris[np.lexsort(tris.T[::-1])]               # canonical triangle order
        entry = {"vertices": int(pos.shape[0]), "triangles": int(tri.shape[0]),
                 "triangle_set_sha256": hashlib.sha256(np.ascontiguousarray(tris).tobytes()).hexdigest()}
        if "joints" in mesh:
            joints = array(mesh["joints"]).astype("<i8").reshape(pos.shape[0], -1)
            per_vertex = np.concatenate([q, joints], axis=1)
            per_vertex = per_vertex[np.lexsort(per_vertex.T[::-1])]
            entry["vertex_joints_sha256"] = hashlib.sha256(np.ascontiguousarray(per_vertex).tobytes()).hexdigest()
        out["meshes"][mesh.get("part", mesh.get("source_object", str(len(out["meshes"]))))] = entry
    return out


def export_differences(old: dict, new: dict) -> list[str]:
    diffs = []
    if old.get("meta_sha256") != new.get("meta_sha256"):
        diffs.append("character.json")
    for kind in ("meshes", "buffers"):
        a, b = old.get(kind, {}), new.get(kind, {})
        for key in sorted(set(a) | set(b)):
            x, y = a.get(key), b.get(key)
            if x is None or y is None:
                diffs.append(f"{key} {'added' if x is None else 'removed'}")
            elif kind == "meshes" and x != y:
                diffs.append(f"mesh {key}: " + ", ".join(k for k in sorted(set(x) | set(y)) if x.get(k) != y.get(k)))
            elif kind == "buffers" and (x[0] != y[0] or len(x) != len(y)
                                        or any(abs(u - v) > EXPORT_TOLERANCE for u, v in zip(x[1:], y[1:]))):
                diffs.append(f"buffer {key}")
    return diffs


class Step(Exception):
    pass


def produce(cfg: dict, blender: str, out: Path, env: dict, fidelity: bool) -> dict:
    """Build, fingerprint, export and render one character into `out`; return the measured data."""
    cid = cfg["character"]
    log = out / "regression.log"
    build = out / "build"
    timings = {}

    def step(name, command):
        started = time.monotonic()
        code = run_logged(command, log, env)
        timings[name] = round(time.monotonic() - started, 1)
        if code:
            raise Step(f"{name} failed (exit {code}); see {log.as_posix()}")

    command = [blender, "-b", "--factory-startup", "-P", ROOT / "pipeline/charsys/build_character.py", "--",
               "--spec", ROOT / cfg["spec"], "--out", build, "--no-glb", "--no-compare"]
    for item in cfg["overrides"]:
        command += ["--override", ROOT / item]
    step("build", command)
    master = build / f"{cid}_master.blend"
    if not master.is_file():
        raise Step(f"build produced no {master.name}")
    step("fingerprint", [blender, "-b", "--factory-startup", "-P", ROOT / "pipeline/charsys/fingerprint_v2.py", "--",
                         master, out / "fingerprint.raw.json", "--grid-m", "0.00001"])
    fingerprint = json.loads((out / "fingerprint.raw.json").read_text(encoding="utf-8"))
    fingerprint.pop("file", None)
    (out / "fingerprint.json").write_bytes(canonical(fingerprint))
    step("export", [blender, "-b", "--factory-startup", "-P", ROOT / "pipeline/charsys/export_engine.py", "--",
                    "--blend", master, "--profile", ROOT / cfg["profile"], "--out", out / "engine_package"])
    export = export_summary(out / "engine_package")
    step("probe", [blender, "-b", "--factory-startup", "-P", HERE / "probe_head.py", "--", master, out / "head.json"])
    head = json.loads((out / "head.json").read_text(encoding="utf-8"))
    views = json.loads(VIEWS.read_text(encoding="utf-8"))
    close = views["closeup"]
    x, y, z = head["center"]
    width = close["width_head_lengths"] * head["length_m"]
    renders = out / "renders"
    step("renders", [blender, "-b", "--factory-startup", "-P", ROOT / "pipeline/charsys/tools/groom_turnaround.py",
                     "--", master, VIEWS, renders, "--height", views["render"]["height"],
                     "--samples", views["render"]["samples"], "--engine", views["render"]["engine"],
                     "--closeup", f"{close['id']}:{close['yaw_deg']}:{close['elevation_deg']}:{x},{y},{z}:{width:.6f}"])
    names = [v["id"] for v in views["views"]] + [close["id"]]
    images = {name: renders / f"{name}.png" for name in names}
    missing = [name for name, path in images.items() if not path.is_file()]
    if missing:
        raise Step("renders missing: " + ", ".join(missing))
    result = {"fingerprint_sha256": hashlib.sha256((out / "fingerprint.json").read_bytes()).hexdigest(),
              "export": export, "renders": {name: sha256_file(path) for name, path in images.items()},
              "head": head, "timings_s": timings}
    if fidelity:
        entry = cfg["fidelity"]
        started = time.monotonic()
        fout = out / "fidelity"
        command = [sys.executable, ROOT / "tools/fidelity/run.py", "--character", cid, "--build", master,
                   "--blender", blender, "--out", fout]
        baseline = json.loads(tiers.FIDELITY_BASELINE.read_text(encoding="utf-8"))
        command += ["--height", baseline["render"]["height"], "--samples", baseline["render"]["samples"]]
        code = run_logged(command, log, env)
        timings["fidelity"] = round(time.monotonic() - started, 1)
        if code:
            raise Step(f"fidelity failed (exit {code}); see {log.as_posix()}")
        score = json.loads((fout / "fidelity.json").read_text(encoding="utf-8"))["overall"]["score"]
        maximum = float(baseline["policy"]["maximum_score_drop"])
        drop = round(float(entry["score"]) - float(score), 4)
        result["fidelity"] = {"score": round(float(score), 4), "baseline": entry["score"], "drop": drop,
                              "maximum_drop": maximum, "ok": drop <= maximum}
    return result


def baseline_dir(root: Path, cfg: dict) -> Path:
    return root / cfg["character"] / cfg["spec_version"]


def compare(cfg: dict, data: dict, out: Path, golden_root: Path, unchanged: bool, noise: dict) -> list[dict]:
    """Checks for one character; returns [{name, ok, detail}]."""
    checks = []

    def check(name, ok, detail=""):
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    if "fidelity" in data:
        f = data["fidelity"]
        check("fidelity", f["ok"], f"{f['score']:.2f} vs {float(f['baseline']):.2f} (drop {f['drop']:+.2f}, max {f['maximum_drop']})")
    gdir = baseline_dir(golden_root, cfg)
    gfile = gdir / "golden.json"
    if not gfile.is_file():
        check("baseline", not unchanged, f"no approved baseline at {gdir.relative_to(ROOT).as_posix() if gdir.is_relative_to(ROOT) else gdir}"
              + ("" if unchanged else " (spec changed: new baseline needs owner approval)"))
        return checks
    golden = json.loads(gfile.read_text(encoding="utf-8"))
    label = "identical to main" if unchanged else "vs baseline (spec changed, owner review)"
    if unchanged and golden.get("spec_inputs_sha256") != cfg["spec_inputs_sha256"]:
        check("baseline", False, "approved baseline was made from different spec inputs (stale baseline)")
    fp_ok = golden.get("fingerprint_sha256") == data["fingerprint_sha256"]
    detail = ""
    if not fp_ok and (gdir / "fingerprint.json").is_file():
        old = json.loads((gdir / "fingerprint.json").read_text(encoding="utf-8"))
        new = json.loads((out / "fingerprint.json").read_text(encoding="utf-8"))
        objs = sorted(n for n in set(old.get("objects", {})) | set(new.get("objects", {}))
                      if old.get("objects", {}).get(n) != new.get("objects", {}).get(n))
        detail = "objects differ: " + ", ".join(objs[:6]) + (f" (+{len(objs) - 6})" if len(objs) > 6 else "")
        if not objs:
            detail = "non-object fields differ (armatures/version)"
    check("fingerprint", fp_ok or not unchanged, ("byte-equal" if fp_ok else detail) + f" [{label}]")
    differing = export_differences(golden.get("export", {}), data["export"])
    ex_ok = not differing
    check("engine export", ex_ok or not unchanged,
          ("equal" if ex_ok else "differs: " + ", ".join(differing[:6]) + (f" (+{len(differing) - 6})" if len(differing) > 6 else ""))
          + f" [{label}]")
    worst = {}
    bad = []
    for name in data["renders"]:
        ref = gdir / "renders" / f"{name}.png"
        if not ref.is_file():
            bad.append(f"{name}: no baseline image")
            continue
        diff = image_difference(ref, out / "renders" / f"{name}.png")
        worst[name] = diff
        if not within_noise(diff, noise):
            bad.append(f"{name} rmse {diff['rmse']:.4f} changed {diff['changed_fraction']:.4f}")
    data["render_differences"] = worst
    top = max(worst.values(), key=lambda d: d["rmse"]) if worst else {"rmse": 0, "changed_fraction": 0}
    check("renders", not bad or not unchanged,
          (f"within noise (max rmse {top['rmse']:.4f} <= {noise['max_rmse']}, changed {top['changed_fraction']:.4f} <= "
           f"{noise['max_changed_fraction']})" if not bad else "; ".join(bad)) + f" [{label}]")
    return checks


def write_baseline(cfg: dict, data: dict, out: Path, dest_root: Path, blender: str) -> Path:
    dest = baseline_dir(dest_root, cfg)
    if dest.exists():
        shutil.rmtree(dest)
    (dest / "renders").mkdir(parents=True)
    for name in data["renders"]:
        shutil.copy2(out / "renders" / f"{name}.png", dest / "renders" / f"{name}.png")
    shutil.copy2(out / "fingerprint.json", dest / "fingerprint.json")
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True).stdout.strip()
    views = json.loads(VIEWS.read_text(encoding="utf-8"))
    golden = {"schema": GOLDEN_SCHEMA, "character": cfg["character"], "spec_version": cfg["spec_version"],
              "spec_inputs": cfg["inputs"], "spec_inputs_sha256": cfg["spec_inputs_sha256"],
              "fingerprint_sha256": data["fingerprint_sha256"], "export": data["export"], "renders": data["renders"],
              "render": views["render"], "source_commit": commit,
              "blender": json.loads((out / "fingerprint.json").read_text(encoding="utf-8")).get("blender", ""),
              "note": "Regression baseline candidate. Approved only once committed by the Supervisor (guarded path)."}
    (dest / "golden.json").write_bytes(canonical(golden))
    return dest


def regress(cid: str, a, env: dict, unchanged_ids: set[str], noise: dict) -> dict:
    out = Path(a.out) / cid
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    started = time.monotonic()
    result = {"schema": SCHEMA, "character": cid, "unchanged": cid in unchanged_ids, "checks": []}
    try:
        cfg = tiers.character_config(cid)
        result.update(spec_version=cfg["spec_version"], spec_inputs_sha256=cfg["spec_inputs_sha256"])
        if a.noise:
            first = produce(cfg, a.blender, out / "run1", env, False)
            second = produce(cfg, a.blender, out / "run2", env, False)
            diffs = {name: image_difference(out / "run1" / "renders" / f"{name}.png",
                                            out / "run2" / "renders" / f"{name}.png") for name in first["renders"]}
            result["noise"] = {"fingerprint_equal": first["fingerprint_sha256"] == second["fingerprint_sha256"],
                               "export_equal": not export_differences(first["export"], second["export"]),
                               "export_differences": export_differences(first["export"], second["export"]), "renders": diffs,
                               "timings_s": [first["timings_s"], second["timings_s"]]}
            result["checks"].append({"name": "build determinism", "ok": result["noise"]["fingerprint_equal"]
                                     and result["noise"]["export_equal"], "detail": ""})
        else:
            data = produce(cfg, a.blender, out, env, not a.no_fidelity)
            result["measured"] = data
            result["checks"] = compare(cfg, data, out, Path(a.baselines), cid in unchanged_ids, noise)
            if a.write_baseline:
                result["baseline_written"] = write_baseline(cfg, data, out, Path(a.out) / "baselines", a.blender).as_posix()
    except (Step, ValueError, OSError, KeyError, json.JSONDecodeError) as exc:
        result["checks"].append({"name": "run", "ok": False, "detail": str(exc)})
    result["ok"] = bool(result["checks"]) and all(c["ok"] for c in result["checks"])
    result["seconds"] = round(time.monotonic() - started, 1)
    (out / "result.json").write_bytes(canonical(result))
    return result


def summary(results: list[dict]) -> str:
    parts = []
    for r in results:
        failed = [c for c in r["checks"] if not c["ok"]]
        state = "PASS" if r["ok"] else "FAIL"
        kind = "unchanged" if r.get("unchanged") else "changed"
        text = f"{state} {r['character']} ({kind})"
        if failed:
            text += ": " + "; ".join(f"{c['name']} {c['detail']}" for c in failed)
        parts.append(text)
    return "\n".join(parts)


def write_gate_report(path: Path, report: dict) -> None:
    """One "Blender tier" check per character job; the verdict job merges it with the gate's own Blender tier."""
    subchecks, parts = [], []
    for r in report["results"]:
        failed = [c for c in r["checks"] if not c["ok"]]
        fidelity = r.get("measured", {}).get("fidelity")
        note = f", fidelity {fidelity['score']:.2f}" if fidelity else ""
        kind = "unchanged, identical to main" if r.get("unchanged") else "spec changed, owner review"
        detail = "; ".join(f"{c['name']}: {c['detail']}" for c in failed) or kind + note
        subchecks.append({"name": f"regression {r['character']}", "ok": r["ok"], "detail": detail, "log": ""})
        parts.append(f"{r['character']} {'PASS' if r['ok'] else 'FAIL'} ({detail})" if not r["ok"] else
                     f"{r['character']} PASS{note}")
    ok = report["ok"] and bool(report["results"])
    gate = {"schema": "plush.quality-gate/1", "verdict": "PASS" if ok else "FAIL",
            "platform": "linux-regression", "characters": report["characters"],
            "checks": [{"name": "Blender tier", "ok": ok, "detail": "regression " + ", ".join(parts),
                        "subchecks": subchecks, "seconds": report["seconds"]}]}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(gate, indent=2) + "\n", encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--blender", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--character", action="append", default=[], help="default: every character in assets/characters")
    ap.add_argument("--jobs", type=int, default=0, help="parallel characters (default: all)")
    ap.add_argument("--base", default="", help="ref whose spec inputs define 'unchanged' (default: none changed)")
    ap.add_argument("--changed", default=None, help="comma-separated changed characters (overrides --base)")
    ap.add_argument("--baselines", default=str(tiers.BASELINES))
    ap.add_argument("--no-fidelity", action="store_true")
    ap.add_argument("--write-baseline", action="store_true")
    ap.add_argument("--noise", action="store_true", help="build and render twice; report the differences")
    ap.add_argument("--gate-report", default="", help="also write a tools/check_all.py-style report (CI verdict)")
    a = ap.parse_args(argv)
    ids = a.character or tiers.character_ids()
    unknown = sorted(set(ids) - set(tiers.character_ids()))
    if unknown:
        raise SystemExit(f"unknown characters: {', '.join(unknown)}")
    if a.changed is not None:
        changed = {c for c in a.changed.split(",") if c}
    elif a.base:
        changed = set(tiers.changed_characters(tiers.git_changed(a.base)))
    else:
        changed = set()
    unchanged = set(ids) - changed
    noise = json.loads(NOISE.read_text(encoding="utf-8"))
    env = blender_env()
    Path(a.out).mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    with concurrent.futures.ThreadPoolExecutor(max_workers=a.jobs or len(ids) or 1) as pool:
        results = list(pool.map(lambda cid: regress(cid, a, env, unchanged, noise), ids))
    report = {"schema": SCHEMA, "ok": all(r["ok"] for r in results), "characters": ids,
              "changed_characters": sorted(changed & set(ids)), "seconds": round(time.monotonic() - started, 1),
              "noise_threshold": noise, "results": results}
    (Path(a.out) / "regression.json").write_bytes(canonical(report))
    if a.gate_report:
        write_gate_report(Path(a.gate_report), report)
    print(summary(results))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
