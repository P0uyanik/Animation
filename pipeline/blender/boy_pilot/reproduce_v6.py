"""Reproduce the boy_yellow_hoodie pilot v6 with a given Blender installation and compare it with the frozen cloud
v6 baseline (docs/evaluation/boy_pilot/cloud_v6_baseline/). Run with any Python 3.9+ that has numpy and Pillow,
from the repository root:

    python pipeline/blender/boy_pilot/reproduce_v6.py --blender "<path to blender executable>" [--out out/local_v6]

Safety: everything is written under --out, which must be a new or empty folder outside docs/ and outside the cloud
results. Tracked files are never modified; the colour calibration is NOT re-run (the committed albedo calibration
is used, exactly as for v6). Steps: environment check -> build -> geometry fingerprint -> 16-view harness ->
comparison sheet -> region renders -> metrics -> rig/expression/glTF tests -> comparison with the baseline.
Results: <out>/VERIFICATION.md and <out>/verification.json."""
import argparse
import json
import os
import platform
import subprocess
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
BASE = os.path.join(ROOT, "docs", "evaluation", "boy_pilot", "cloud_v6_baseline")
IDX = os.path.join(ROOT, "assets", "characters", "boy_yellow_hoodie", "references", "reference_index.json")
LMK = os.path.join(ROOT, "assets", "characters", "boy_yellow_hoodie", "references", "landmarks.json")
PILOT = os.path.join(ROOT, "pipeline", "blender", "boy_pilot")
MEASURED = "orig07_front,val27_front,val27_threequarter_right,val27_side_right,val27_back,val27_back_threequarter"
TOL = {"render_alpha_iou": 0.98, "render_mean_abs_rgb": 6.0, "metric_iou": 0.01, "contour_pct": 0.15,
       "landmark_pct": 1.5, "dE2000": 1.5, "bbox_m": 0.0005}


def die(msg):
    sys.exit(f"[reproduce_v6] {msg}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blender", required=True, help="Blender executable (e.g. blender, blender.exe or .../Blender.app/Contents/MacOS/Blender)")
    ap.add_argument("--out", default=os.path.join("out", "local_v6"))
    a = ap.parse_args()
    try:
        import numpy  # noqa: F401
        from PIL import Image  # noqa: F401
    except ImportError as e:
        die(f"this Python needs numpy and Pillow ({e}); install with: python -m pip install numpy pillow")
    out = os.path.abspath(a.out)
    for forbidden in (os.path.join(ROOT, "docs"), os.path.join(ROOT, "renders", "compare", "boy_pilot", "v6"), os.path.join(ROOT, "pipeline"),
                      os.path.join(ROOT, "assets")):
        if out == forbidden or out.startswith(forbidden + os.sep):
            die(f"refusing to write into {forbidden} (would touch tracked files or the v6 baseline); choose another --out")
    if os.path.isdir(out) and os.listdir(out):
        die(f"{out} is not empty; choose a new --out folder (existing results are never overwritten)")
    if not os.path.isdir(BASE):
        die(f"baseline folder missing: {BASE}")
    os.makedirs(out, exist_ok=True)
    log = open(os.path.join(out, "run.log"), "w")
    steps, t_all = [], time.time()

    def run(name, cmd):
        t = time.time()
        log.write(f"\n===== {name}: {' '.join(cmd)}\n")
        log.flush()
        r = subprocess.run(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        steps.append({"step": name, "ok": r.returncode == 0, "seconds": round(time.time() - t, 1), "returncode": r.returncode})
        print(f"[reproduce_v6] {name}: {'ok' if r.returncode == 0 else 'FAILED (see run.log)'} in {time.time() - t:.0f} s", flush=True)
        return r.returncode == 0

    def blender(name, script, *args):
        return run(name, [a.blender, "-b", "--factory-startup", "-P", os.path.join(PILOT if "/" not in script else ROOT, script), "--", *args])

    py = sys.executable
    build, harness, report, regions, rig = (os.path.join(out, d) for d in ("build", "harness", "report", "regions", "rig_tests"))
    master, compare, glb = (os.path.join(build, f) for f in ("boy_yellow_hoodie_pilot_master.blend", "boy_yellow_hoodie_pilot_compare.blend",
                                                              "boy_yellow_hoodie_pilot.glb"))
    ok = run("blender --version", [a.blender, "--version"])
    ok = ok and blender("environment check", "env_check.py", os.path.join(out, "environment.json"))
    env = json.load(open(os.path.join(out, "environment.json"))) if os.path.exists(os.path.join(out, "environment.json")) else {}
    if env and not env.get("ok"):
        print("[reproduce_v6] WARNING: environment check reported missing features; continuing to collect evidence", flush=True)
    ok = ok and blender("build (model, rig, weights, fur, glTF)", "build_boy_pilot.py", "--out", build, "--stage", "all", "--fur-scale", "1.0")
    ok = ok and blender("geometry fingerprint", "fingerprint.py", master, os.path.join(out, "geometry_fingerprint.json"))
    ok = ok and blender("16-view harness", "pipeline/blender/compare_harness.py", "--subject", compare, "--index", IDX, "--out", harness,
                        "--samples", "48", "--fill", "0.94", "--keep-materials")
    ok = ok and run("comparison sheet", [py, os.path.join(ROOT, "pipeline", "compare_sheet.py"), "--index", IDX, "--blender", harness, "--out",
                                         report, "--label", "boy_yellow_hoodie pilot v6 (local Blender)"])
    ok = ok and blender("region renders", "render_regions.py", compare, IDX, regions, MEASURED, "32")
    ok = ok and run("metrics", [py, os.path.join(ROOT, "pipeline", "pilot_metrics.py"), "--index", IDX, "--harness", harness, "--regions",
                                regions, "--landmarks", LMK, "--out", os.path.join(report, "extra_metrics.json")])
    ok = ok and blender("rig / expression / glTF tests", "rig_tests.py", master, glb, rig)
    res = compare_with_baseline(out, env, steps, time.time() - t_all)
    print(f"[reproduce_v6] finished: {res['verdict']} -> {os.path.join(out, 'VERIFICATION.md')}", flush=True)


def compare_with_baseline(out, env, steps, total):
    import numpy as np
    from PIL import Image
    R = {"environment": env, "platform": f"{platform.system()} {platform.release()} ({platform.machine()})", "steps": steps,
         "total_seconds": round(total, 1), "checks": {}}
    C = R["checks"]
    build = os.path.join(out, "build")
    files = {f: os.path.getsize(os.path.join(build, f)) if os.path.exists(os.path.join(build, f)) else None
             for f in ("boy_yellow_hoodie_pilot_master.blend", "boy_yellow_hoodie_pilot_compare.blend", "boy_yellow_hoodie_pilot.glb")}
    C["files_exist"] = {"ok": all(files.values()), "sizes": files}
    fpl, fpb = os.path.join(out, "geometry_fingerprint.json"), os.path.join(BASE, "geometry_fingerprint.json")
    if os.path.exists(fpl):
        L, B = json.load(open(fpl))["objects"], json.load(open(fpb))["objects"]
        missing, extra = sorted(set(B) - set(L)), sorted(set(L) - set(B))
        counts = [n for n in B if n in L and B[n]["type"] == "MESH" and (B[n]["vertices"], B[n]["faces"]) != (L[n]["vertices"], L[n]["faces"])]
        hashes = [n for n in B if n in L and B[n]["type"] == "MESH" and B[n]["coords_hash"] != L[n]["coords_hash"]]
        bbox = max((float(np.abs(np.array(B[n]["bbox"]) - np.array(L[n]["bbox"])).max()) for n in B
                    if n in L and B[n]["type"] == "MESH" and B[n]["bbox"] and L[n]["bbox"]), default=0.0)
        rigs = {n: (B[n], L.get(n)) for n in B if B[n]["type"] == "ARMATURE"}
        groups = [n for n in B if n in L and B[n]["type"] == "MESH" and B[n]["vertex_groups"] != L[n]["vertex_groups"]]
        keys = [n for n in B if n in L and B[n]["type"] == "MESH" and B[n]["shape_keys"] != L[n]["shape_keys"]]
        cen = max((float(np.abs(np.array(B[n]["centroid"]) - np.array(L[n]["centroid"])).max()) for n in B
                   if n in L and B[n]["type"] == "MESH" and B[n].get("centroid") and L[n].get("centroid")), default=0.0)
        rms = max((abs(B[n]["rms_radius"] - L[n]["rms_radius"]) for n in B
                   if n in L and B[n]["type"] == "MESH" and B[n].get("rms_radius") is not None and L[n].get("rms_radius") is not None), default=0.0)
        C["geometry"] = {"ok": not (missing or extra or counts) and max(bbox, cen, rms) <= TOL["bbox_m"],
                         "max_centroid_difference_m": round(cen, 7), "max_rms_radius_difference_m": round(rms, 7),
                         "identical_vertices": not hashes, "objects_baseline": len(B), "objects_local": len(L),
                         "missing": missing, "extra": extra, "count_mismatch": counts, "coordinate_hash_mismatch": hashes,
                         "max_bbox_difference_m": round(bbox, 6), "vertex_group_mismatch": groups, "shape_key_mismatch": keys,
                         "rig": {n: {"baseline": b, "local": l} for n, (b, l) in rigs.items()}}
    # Renders: local vs cloud harness images, per view
    rows, worst_iou, worst_rgb = [], 1.0, 0.0
    for f in sorted(os.listdir(os.path.join(BASE, "harness"))):
        if not f.endswith(".png"):
            continue
        lp = os.path.join(out, "harness", f)
        if not os.path.exists(lp):
            rows.append({"view": f[:-4], "missing": True})
            worst_iou = 0.0
            continue
        bimg = np.asarray(Image.open(os.path.join(BASE, "harness", f)).convert("RGBA"), float)
        limg = np.asarray(Image.open(lp).convert("RGBA"), float)
        if bimg.shape != limg.shape:
            rows.append({"view": f[:-4], "size_mismatch": [list(bimg.shape), list(limg.shape)]})
            worst_iou = 0.0
            continue
        ba, la = bimg[..., 3] > 127, limg[..., 3] > 127
        iou = float((ba & la).sum() / max(1, (ba | la).sum()))
        both = ba & la
        rgb = float(np.abs(bimg[..., :3][both] - limg[..., :3][both]).mean()) if both.any() else 255.0
        rows.append({"view": f[:-4], "alpha_iou_vs_cloud": round(iou, 4), "mean_abs_rgb_vs_cloud": round(rgb, 2)})
        worst_iou, worst_rgb = min(worst_iou, iou), max(worst_rgb, rgb)
    C["renders"] = {"ok": worst_iou >= TOL["render_alpha_iou"] and worst_rgb <= TOL["render_mean_abs_rgb"],
                    "worst_alpha_iou": round(worst_iou, 4), "worst_mean_abs_rgb": round(worst_rgb, 2), "views": rows}
    # Metrics vs the cloud v6 metrics
    lm, bm = os.path.join(out, "report", "extra_metrics.json"), os.path.join(BASE, "extra_metrics.json")
    if os.path.exists(lm):
        L, B = json.load(open(lm)), json.load(open(bm))
        diffs, bad = {}, []
        for v, be in B["views"].items():
            le = L["views"].get(v)
            if le is None:
                bad.append(f"{v}: missing")
                continue
            d = {"iou": round(le["iou"] - be["iou"], 4), "contour": round(le["contour_mean_pct_height"] - be["contour_mean_pct_height"], 3),
                 "hair_contour": round(le["hair_contour_mean_pct_head"] - be["hair_contour_mean_pct_head"], 3)}
            if abs(d["iou"]) > TOL["metric_iou"] or abs(d["contour"]) > TOL["contour_pct"]:
                bad.append(f"{v}: silhouette metrics")
            if "landmarks" in be:
                d["landmark_error_pct"] = {k: round(le["landmarks"][k]["error_pct"] - x["error_pct"], 2) for k, x in be["landmarks"].items()}
                if any(abs(x) > TOL["landmark_pct"] for x in d["landmark_error_pct"].values()):
                    bad.append(f"{v}: landmarks")
            if "colour" in be and "colour" in le:
                d["dE2000"] = {k: round(le["colour"][k]["dE2000"] - x["dE2000"], 2) for k, x in be["colour"].items() if k in le["colour"]}
                if any(abs(x) > TOL["dE2000"] for x in d["dE2000"].values()):
                    bad.append(f"{v}: colour")
            diffs[v] = d
        C["metrics"] = {"ok": not bad, "problems": bad, "summary_cloud": B["summary"], "summary_local": L["summary"], "per_view_difference": diffs}
    rl, rb = os.path.join(out, "rig_tests", "rig_tests.json"), os.path.join(BASE, "rig_tests.json")
    if os.path.exists(rl):
        L, B = json.load(open(rl)), json.load(open(rb))
        same = {k: L["gltf_roundtrip"].get(k) == B["gltf_roundtrip"].get(k) for k in ("armatures", "joints", "meshes", "skinned_meshes", "morph_targets")}
        C["rig_and_gltf"] = {"ok": all(same.values()) and L["rig"]["bones"] == B["rig"]["bones"], "fields_equal": same,
                             "local": L["gltf_roundtrip"], "cloud": B["gltf_roundtrip"],
                             "bones": {"local": L["rig"]["bones"], "cloud": B["rig"]["bones"]}}
    all_steps = all(s["ok"] for s in steps)
    checks_ok = all(c.get("ok") for c in C.values()) and len(C) >= 5
    R["verdict"] = ("REPRODUCED" if all_steps and checks_ok else
                    "RAN WITH DIFFERENCES" if all_steps else "FAILED (a step did not complete)")
    json.dump(R, open(os.path.join(out, "verification.json"), "w"), indent=1)
    md = [f"# Local reproduction of pilot v6: {R['verdict']}", "",
          f"- Blender: {env.get('blender', '?')} (Python {env.get('python', '?')}, numpy {env.get('numpy', '?')}, Rigify {env.get('rigify', '?')})",
          f"- Platform: {R['platform']}", f"- Total time: {R['total_seconds']} s", "", "| Step | Result | Seconds |", "| --- | --- | --- |"]
    md += [f"| {s['step']} | {'ok' if s['ok'] else 'FAILED'} | {s['seconds']} |" for s in steps]
    md += ["", "| Check against the cloud v6 baseline | Result |", "| --- | --- |"]
    for k, c in C.items():
        extra = {"geometry": lambda c: f"{c['objects_local']}/{c['objects_baseline']} objects; vertex/face count mismatches "
                                       f"{len(c['count_mismatch'])}; max bbox / centroid / spread diff {c['max_bbox_difference_m']} / "
                                       f"{c['max_centroid_difference_m']} / {c['max_rms_radius_difference_m']} m; exact coordinate "
                                       f"hash differs for {len(c['coordinate_hash_mismatch'])} object(s) (float rounding, informational)",
                 "renders": lambda c: f"worst silhouette IoU vs cloud {c['worst_alpha_iou']}; worst mean RGB diff {c['worst_mean_abs_rgb']}",
                 "metrics": lambda c: f"local mean IoU {c['summary_local']['mean_iou']} vs cloud {c['summary_cloud']['mean_iou']}; problems: {c['problems'] or 'none'}",
                 "files_exist": lambda c: ", ".join(f"{n}: {s}" for n, s in c["sizes"].items()),
                 "rig_and_gltf": lambda c: f"bones {c['bones']}; glTF fields equal: {all(c['fields_equal'].values())}"}.get(k, lambda c: "")(c)
        md.append(f"| {k} | {'PASS' if c.get('ok') else 'DIFFERENT'}: {extra} |")
    if env.get("checks"):
        md += ["", "Environment checks: " + ", ".join(f"{k}: {'yes' if v else 'NO'}" for k, v in env["checks"].items())]
    md += ["", f"Tolerances: {TOL}", "Details: verification.json; logs: run.log; sheet: report/comparison_sheet.png"]
    open(os.path.join(out, "VERIFICATION.md"), "w").write("\n".join(md) + "\n")
    return R


if __name__ == "__main__":
    main()
