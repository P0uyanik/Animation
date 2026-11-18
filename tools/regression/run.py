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
  5. fidelity   tools/fidelity/run.py, score vs docs/evaluation/characters/fidelity_baseline.json (drop > 2 = PASS,
                flagged "needs owner review": T-087 rule change, tools/fidelity/ci.compare_score)
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
sys.path.insert(0, str(HERE.parent))
from fidelity import ci as fidelity_ci  # noqa: E402  (T-087: one fidelity-drop policy for every gate path)

VIEWS = HERE / "views.json"
NOISE = HERE / "render_noise_threshold.json"
SCHEMA = "plush-studio.regression/1"
GOLDEN_SCHEMA = "plush-studio.regression-golden/1"
BASELINE_IMAGES = "images"  # not "renders": the repository .gitignore excludes every renders/ folder


def run_logged(command, log: Path, env=None, cwd: Path = ROOT) -> int:
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8", errors="replace") as handle:
        handle.write("$ " + " ".join(str(c) for c in command) + "\n")
        handle.flush()
        return subprocess.run([str(c) for c in command], cwd=cwd, stdout=handle, stderr=subprocess.STDOUT,
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


POSITION_TOLERANCE_M = 1e-5   # 0.01 mm, the fingerprint grid
ATTRIBUTE_TOLERANCE = 1e-4    # normals and skin weights


def _match_vertices(a, b, tolerance):
    """Index map a -> b pairing every vertex with one within `tolerance` (or None). Sorted order pairs almost all;
    near-ties in the sort key (two vertices within float noise in x) are resolved by nearest neighbour."""
    import numpy as np
    if a.shape != b.shape:
        return None
    oa, ob = np.lexsort(a.T[::-1]), np.lexsort(b.T[::-1])
    mapping = np.empty(len(a), dtype=np.int64)
    mapping[oa] = ob
    bad = np.nonzero(np.abs(a - b[mapping]).max(axis=1) > tolerance)[0]
    if len(bad) > max(64, len(a) // 100):
        return None
    for i in bad:
        nearest = int(np.argmin(np.abs(b - a[i]).max(axis=1)))
        if np.abs(b[nearest] - a[i]).max() > tolerance:
            return None
        mapping[i] = nearest
    if len(np.unique(mapping)) != len(mapping):
        return None
    return mapping


def export_package_differences(new_pkg: Path, ref_pkg: Path) -> list[str]:
    """Tolerance-aware equality of two engine packages built on the same machine (T-041 finding: the exporter writes
    a different triangle/vertex order and float noise of about 1 ulp, so neither bytes nor quantized hashes are
    stable). character.json must be equal (without byte hashes); every mesh must have the same vertices (within
    0.01 mm), the same triangles (as index sets after matching), equal joints and weights/normals within 1e-4; every
    other buffer (e.g. morph targets) within the statistics tolerance."""
    import numpy as np
    new_sum, ref_sum = export_summary(new_pkg), export_summary(ref_pkg)
    diffs = []
    if new_sum["meta_sha256"] != ref_sum["meta_sha256"]:
        diffs.append("character.json")
    metas, raws = [], []
    for pkg in (new_pkg, ref_pkg):
        metas.append(json.loads((pkg / "character.json").read_text(encoding="utf-8")))
        raws.append((pkg / "geometry.bin").read_bytes() if (pkg / "geometry.bin").is_file() else b"")

    def arr(raw, desc, width):
        values = np.frombuffer(raw, np.dtype(DTYPES[desc["dtype"]]), int(desc["count"]), int(desc["offset"]))
        return values.reshape(-1, width) if width else values

    meshes = [{m.get("part", str(i)): m for i, m in enumerate(meta.get("meshes", []))} for meta in metas]
    covered = set()
    for name in sorted(set(meshes[0]) | set(meshes[1])):
        m_new, m_ref = meshes[0].get(name), meshes[1].get(name)
        if m_new is None or m_ref is None:
            diffs.append(f"mesh {name} {'removed' if m_new is None else 'added'}")
            continue
        index = next(i for i, m in enumerate(metas[0]["meshes"]) if m is m_new)
        covered.update(f"/meshes[{index}]/{k}" for k in ("positions", "normals", "indices", "joints", "weights"))
        if "positions" not in m_new or "positions" not in m_ref:
            continue
        pa, pb = arr(raws[0], m_new["positions"], 3).astype(float), arr(raws[1], m_ref["positions"], 3).astype(float)
        mapping = _match_vertices(pa, pb, POSITION_TOLERANCE_M)
        if mapping is None:
            diffs.append(f"mesh {name}: vertices")
            continue
        if "indices" in m_new:
            ta = np.sort(mapping[arr(raws[0], m_new["indices"], 3).astype(np.int64)], axis=1)
            tb = np.sort(arr(raws[1], m_ref["indices"], 3).astype(np.int64), axis=1)
            ta, tb = ta[np.lexsort(ta.T[::-1])], tb[np.lexsort(tb.T[::-1])]
            if ta.shape != tb.shape or not np.array_equal(ta, tb):
                diffs.append(f"mesh {name}: triangles")
        for key, exact in (("joints", True), ("weights", False), ("normals", False)):
            if key not in m_new or key not in m_ref:
                continue
            width = 3 if key == "normals" else 4
            va = arr(raws[0], m_new[key], width).astype(float)
            vb = arr(raws[1], m_ref[key], width).astype(float)[mapping]
            same = va.shape == vb.shape and bool(np.array_equal(va, vb) if exact
                                                  else np.abs(va - vb).max(initial=0) <= ATTRIBUTE_TOLERANCE)
            if not same:
                diffs.append(f"mesh {name}: {key}")
    for path in sorted(set(new_sum["buffers"]) | set(ref_sum["buffers"])):
        if path in covered:
            continue
        x, y = new_sum["buffers"].get(path), ref_sum["buffers"].get(path)
        if x is None or y is None or x[0] != y[0] or any(abs(u - v) > EXPORT_TOLERANCE for u, v in zip(x[1:], y[1:])):
            diffs.append(f"buffer {path}")
    return diffs


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


def fidelity_result(score: float, baseline: float, maximum: float) -> dict:
    """Fidelity entry of a character result. T-087: a drop above `maximum` passes, flagged "needs owner review"
    (tools/fidelity/ci.compare_score, the policy of every gate path); image checks are unaffected."""
    drop = round(float(baseline) - float(score), 4)
    policy = fidelity_ci.compare_score(score, baseline, maximum)
    return {"score": round(float(score), 4), "baseline": baseline, "drop": drop, "maximum_drop": maximum,
            "ok": policy.ok, "needs_owner_review": policy.needs_owner_review}


def owner_review_note(result: dict) -> str:
    f = result.get("measured", {}).get("fidelity") or {}
    return (f"; {fidelity_ci.OWNER_REVIEW_FLAG.upper()}: fidelity drop {f['drop']:+.2f} > {f['maximum_drop']}"
            if f.get("needs_owner_review") else "")


def produce(cfg: dict, blender: str, out: Path, env: dict, fidelity: bool) -> dict:
    """Build, export and render one character from the checkout cfg["root"] (this one, or a worktree of the
    comparison ref) into `out`; return the measured data. Fingerprint tool, cameras and probe always come from this
    checkout, so a comparison measures the pipeline, not the measuring tools."""
    cid = cfg["character"]
    src = Path(cfg.get("root") or ROOT)
    log = out / "regression.log"
    build = out / "build"
    timings = {}

    def step(name, command):
        started = time.monotonic()
        code = run_logged(command, log, env, src)
        timings[name] = round(time.monotonic() - started, 1)
        if code:
            raise Step(f"{name} failed (exit {code}); see {log.as_posix()}")

    # Fidelity renders the build variant its reference views match (fidelity_index.json render_variant): the
    # compare build (arms lowered, fur) is made only when fidelity needs it; the master is saved before it.
    index = src / "assets" / "characters" / cid / "references" / "annotations" / "fidelity_index.json"
    variant = json.loads(index.read_text(encoding="utf-8")).get("render_variant", "master") if index.is_file() else "master"
    command = [blender, "-b", "--factory-startup", "-P", src / "pipeline/charsys/build_character.py", "--",
               "--spec", src / cfg["spec"], "--out", build, "--no-glb"]
    if not (fidelity and variant == "compare"):
        command.append("--no-compare")
    for item in cfg["overrides"]:
        command += ["--override", src / item]
    step("build", command)
    master = build / f"{cid}_master.blend"
    if not master.is_file():
        raise Step(f"build produced no {master.name}")
    step("fingerprint", [blender, "-b", "--factory-startup", "-P", ROOT / "pipeline/charsys/fingerprint_v2.py", "--",
                         master, out / "fingerprint.raw.json", "--grid-m", "0.00001"])
    fingerprint = json.loads((out / "fingerprint.raw.json").read_text(encoding="utf-8"))
    fingerprint.pop("file", None)
    (out / "fingerprint.json").write_bytes(canonical(fingerprint))
    step("export", [blender, "-b", "--factory-startup", "-P", src / "pipeline/charsys/export_engine.py", "--",
                    "--blend", master, "--profile", src / cfg["profile"], "--out", out / "engine_package"])
    export = export_summary(out / "engine_package")
    step("probe", [blender, "-b", "--factory-startup", "-P", HERE / "probe_head.py", "--", master, out / "head.json"])
    head = json.loads((out / "head.json").read_text(encoding="utf-8"))
    views = json.loads(VIEWS.read_text(encoding="utf-8"))
    close = views["closeup"]
    x, y, z = head["center"]
    width = close["width_head_lengths"] * head["length_m"]
    renders = out / "renders"
    step("renders", [blender, "-b", "--factory-startup", "-P", src / "pipeline/charsys/tools/groom_turnaround.py",
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
        result["fidelity"] = fidelity_result(score, entry["score"], maximum)
    return result


def baseline_dir(root: Path, cfg: dict) -> Path:
    return root / cfg["character"] / cfg["spec_version"]


def fingerprint_difference(old: dict, new: dict) -> str:
    objs = sorted(n for n in set(old.get("objects", {})) | set(new.get("objects", {}))
                  if old.get("objects", {}).get(n) != new.get("objects", {}).get(n))
    if not objs:
        return "non-object fields differ (armatures/version)"
    parts = []
    for name in objs[:6]:
        a, b = old.get("objects", {}).get(name) or {}, new.get("objects", {}).get(name) or {}
        keys = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
        extra = ""
        if "centroid" in keys and a.get("centroid") and b.get("centroid"):
            extra = f", centroid moved {max(abs(x - y) for x, y in zip(a['centroid'], b['centroid'])) * 1000:.4f} mm"
        parts.append(f"{name} ({', '.join(keys)}{extra})")
    return "objects differ: " + "; ".join(parts) + (f" (+{len(objs) - 6})" if len(objs) > 6 else "")


def identity_checks(data: dict, fp_new: Path, ref: dict, fp_ref: Path, images_new: Path, images_ref: Path,
                    noise: dict) -> list[tuple[str, bool, str]]:
    """(aspect, equal, detail) for fingerprint, engine export and renders of two results."""
    out = []
    fp_ok = ref.get("fingerprint_sha256") == data["fingerprint_sha256"]
    detail = "byte-equal"
    if not fp_ok:
        detail = (fingerprint_difference(json.loads(fp_ref.read_text(encoding="utf-8")),
                                         json.loads(fp_new.read_text(encoding="utf-8")))
                  if fp_ref.is_file() else "differs")
    out.append(("fingerprint", fp_ok, detail))
    new_pkg, ref_pkg = fp_new.parent / "engine_package", fp_ref.parent / "engine_package"
    if (new_pkg / "character.json").is_file() and (ref_pkg / "character.json").is_file():
        differing = export_package_differences(new_pkg, ref_pkg)
        how = "equal (vertices matched within 0.01 mm)"
    else:  # stored baseline: only the order-independent summary exists
        differing = export_differences(ref.get("export", {}), data["export"])
        how = "summary equal"
    out.append(("engine export", not differing, how if not differing else "differs: " + ", ".join(differing[:6])
                + (f" (+{len(differing) - 6})" if len(differing) > 6 else "")))
    bad, worst = [], {}
    for name in data["renders"]:
        other = images_ref / f"{name}.png"
        if not other.is_file():
            bad.append(f"{name}: no image")
            continue
        diff = image_difference(other, images_new / f"{name}.png")
        worst[name] = diff
        if not within_noise(diff, noise):
            bad.append(f"{name} rmse {diff['rmse']:.4f} changed {diff['changed_fraction']:.4f}")
    top = max(worst.values(), key=lambda d: d["rmse"]) if worst else {"rmse": 0, "changed_fraction": 0}
    out.append(("renders", not bad, (f"within noise (max rmse {top['rmse']:.4f} <= {noise['max_rmse']}, changed "
                                     f"{top['changed_fraction']:.4f} <= {noise['max_changed_fraction']})")
                if not bad else "; ".join(bad)))
    return out


def compare(cfg: dict, data: dict, out: Path, golden_root: Path, unchanged: bool, noise: dict,
            reference: dict | None = None, ref_out: Path | None = None, ref_label: str = "") -> list[dict]:
    """Checks for one character; returns [{name, ok, detail}].

    With `reference` (the same character built from the comparison ref, normally origin/main, on this machine) an
    unchanged character must be identical to it; the approved baseline is then compared for information only
    (builds are only reproducible on the same CPU family). Without a reference the baseline comparison is strict."""
    checks = []

    def check(name, ok, detail=""):
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    if "fidelity" in data:
        f = data["fidelity"]
        check("fidelity", f["ok"], f"{f['score']:.2f} vs {float(f['baseline']):.2f} (drop {f['drop']:+.2f}, max {f['maximum_drop']})"
              + (f"; {fidelity_ci.OWNER_REVIEW_FLAG.upper()} (drop above the maximum, PASS with warning)"
                 if f.get("needs_owner_review") else ""))
    if reference is not None:
        label = f"identical to {ref_label}" if unchanged else f"vs {ref_label} (spec changed, owner review)"
        for aspect, equal, detail in identity_checks(data, out / "fingerprint.json", reference,
                                                     ref_out / "fingerprint.json", out / "renders",
                                                     ref_out / "renders", noise):
            check(f"{aspect} vs {ref_label}", equal or not unchanged, f"{detail} [{label}]")
    gdir = baseline_dir(golden_root, cfg)
    gfile = gdir / "golden.json"
    if not gfile.is_file():
        check("baseline", not unchanged, f"no approved baseline at {gdir.relative_to(ROOT).as_posix() if gdir.is_relative_to(ROOT) else gdir}"
              + ("" if unchanged else " (spec changed: new baseline needs owner approval)"))
        return checks
    golden = json.loads(gfile.read_text(encoding="utf-8"))
    if unchanged and golden.get("spec_inputs_sha256") != cfg["spec_inputs_sha256"]:
        check("baseline", False, "approved baseline was made from different spec inputs (stale baseline)")
    strict = unchanged and reference is None
    label = ("identical to the approved baseline" if strict else
             "vs approved baseline, information" + ("" if unchanged else " (spec changed, owner review)"))
    results = identity_checks(data, out / "fingerprint.json", golden, gdir / "fingerprint.json", out / "renders",
                              gdir / BASELINE_IMAGES, noise)
    data["baseline_comparison"] = {aspect: {"equal": equal, "detail": detail} for aspect, equal, detail in results}
    for aspect, equal, detail in results:
        check(aspect if strict else f"{aspect} vs baseline", equal or not strict, f"{detail} [{label}]")
    return checks


def write_baseline(cfg: dict, data: dict, out: Path, dest_root: Path, blender: str) -> Path:
    dest = baseline_dir(dest_root, cfg)
    if dest.exists():
        shutil.rmtree(dest)
    (dest / BASELINE_IMAGES).mkdir(parents=True)
    for name in data["renders"]:
        shutil.copy2(out / "renders" / f"{name}.png", dest / BASELINE_IMAGES / f"{name}.png")
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
        try:
            cfg = tiers.character_config(cid)
        except tiers.NotBuildable as exc:
            # Explicitly reported (never silent): a character with references but no spec cannot be built yet.
            result["checks"].append({"name": "not buildable yet", "ok": True, "detail": str(exc)})
            result["not_buildable"] = True
            result["ok"] = True
            result["seconds"] = round(time.monotonic() - started, 1)
            (out / "result.json").write_bytes(canonical(result))
            return result
        result.update(spec_version=cfg["spec_version"], spec_inputs_sha256=cfg["spec_inputs_sha256"])
        if a.noise:
            first = produce(cfg, a.blender, out / "run1", env, False)
            second = produce(cfg, a.blender, out / "run2", env, False)
            diffs = {name: image_difference(out / "run1" / "renders" / f"{name}.png",
                                            out / "run2" / "renders" / f"{name}.png") for name in first["renders"]}
            result["noise"] = {"fingerprint_equal": first["fingerprint_sha256"] == second["fingerprint_sha256"],
                               "export_equal": not export_package_differences(out / "run1" / "engine_package",
                                                                              out / "run2" / "engine_package"),
                               "export_differences": export_package_differences(out / "run1" / "engine_package",
                                                                                out / "run2" / "engine_package"), "renders": diffs,
                               "timings_s": [first["timings_s"], second["timings_s"]]}
            result["checks"].append({"name": "build determinism", "ok": result["noise"]["fingerprint_equal"]
                                     and result["noise"]["export_equal"], "detail": ""})
        else:
            reference = ref_out = None
            if a.against_root:
                try:
                    ref_cfg = tiers.character_config(cid, Path(a.against_root))
                except ValueError as exc:  # e.g. a new character that is not on the comparison ref yet
                    result["reference"] = f"not built from {a.against}: {exc}"
                    if cid in unchanged_ids:
                        raise Step(f"unchanged character cannot be built from {a.against}: {exc}")
                else:
                    ref_out = out / "reference"
                    reference = produce(ref_cfg, a.blender, ref_out, env, False)
                    result["reference"] = {"ref": a.against, "commit": a.against_commit,
                                           "spec_inputs_sha256": ref_cfg["spec_inputs_sha256"], "measured": reference}
            data = produce(cfg, a.blender, out, env, not a.no_fidelity)
            result["measured"] = data
            result["checks"] = compare(cfg, data, out, Path(a.baselines), cid in unchanged_ids, noise,
                                       reference, ref_out, a.against)
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
        text += owner_review_note(r)
        parts.append(text)
    return "\n".join(parts)


def write_gate_report(path: Path, report: dict) -> None:
    """One "Blender tier" check per character job; the verdict job merges it with the gate's own Blender tier."""
    subchecks, parts = [], []
    for r in report["results"]:
        failed = [c for c in r["checks"] if not c["ok"]]
        fidelity = r.get("measured", {}).get("fidelity")
        note = (f", fidelity {fidelity['score']:.2f}" if fidelity else "") + owner_review_note(r)
        kind = ("references only, not buildable yet" if r.get("not_buildable") else
                "unchanged, identical to main" if r.get("unchanged") else "spec changed, owner review")
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
    ap.add_argument("--against", default="", help="also build every character from this ref (git worktree) on this "
                    "machine; unchanged characters must be identical to it (CI: origin/main)")
    a = ap.parse_args(argv)
    a.out = str(Path(a.out).resolve())  # Blender runs with the source checkout as working directory
    if a.gate_report:
        a.gate_report = str(Path(a.gate_report).resolve())
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
    a.against_root = a.against_commit = ""
    worktree = None
    if a.against:
        commit = subprocess.run(["git", "rev-parse", "--verify", f"{a.against}^{{commit}}"], cwd=ROOT, text=True,
                                capture_output=True)
        if commit.returncode:
            raise SystemExit(f"--against ref not found: {a.against}")
        a.against_commit = commit.stdout.strip()
        worktree = Path(a.out).resolve() / "_against_worktree"
        if worktree.exists():
            subprocess.run(["git", "worktree", "remove", "--force", str(worktree)], cwd=ROOT, capture_output=True)
            shutil.rmtree(worktree, ignore_errors=True)
        subprocess.run(["git", "worktree", "add", "--detach", str(worktree), a.against_commit], cwd=ROOT, check=True,
                       capture_output=True)
        a.against_root = str(worktree)
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=a.jobs or len(ids) or 1) as pool:
            results = list(pool.map(lambda cid: regress(cid, a, env, unchanged, noise), ids))
    finally:
        if worktree is not None:
            subprocess.run(["git", "worktree", "remove", "--force", str(worktree)], cwd=ROOT, capture_output=True)
    report = {"schema": SCHEMA, "ok": all(r["ok"] for r in results), "characters": ids,
              "against": {"ref": a.against, "commit": a.against_commit} if a.against else None,
              "changed_characters": sorted(changed & set(ids)), "seconds": round(time.monotonic() - started, 1),
              "noise_threshold": noise, "results": results}
    (Path(a.out) / "regression.json").write_bytes(canonical(report))
    if a.gate_report:
        write_gate_report(Path(a.gate_report), report)
    print(summary(results))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
