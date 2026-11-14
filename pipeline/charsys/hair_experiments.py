"""Controlled hair experiments for a character (plain Python orchestrator; Blender is run as a subprocess).

    python3 pipeline/charsys/hair_experiments.py --blender <blender executable> \
        [--variants H01_longer_tufts,H05_projecting_spikes] [--out renders/experiments/hair] [--sheet-only]

For every variant override in assets/characters/<id>/experiments/hair/*.json:
  build (charsys, compare file only, no glTF) -> 16-view harness -> comparison sheet -> region renders (6 measured views)
  -> pilot metrics. Each variant is stored in its own folder <out>/<variant>/; the spec and v6 are never changed.
Then writes <out>/summary.json and <out>/hair_multiview_sheet.jpg (head crops, reference outline in magenta)."""
import argparse
import glob
import json
import os
import subprocess
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CID = "boy_yellow_hoodie"
SPEC = os.path.join(ROOT, "assets", "characters", CID, "spec", f"{CID}.spec.json")
EXP = os.path.join(ROOT, "assets", "characters", CID, "experiments", "hair")
IDX = os.path.join(ROOT, "assets", "characters", CID, "references", "reference_index.json")
LMK = os.path.join(ROOT, "assets", "characters", CID, "references", "landmarks.json")
MEASURED = "orig07_front,val27_front,val27_threequarter_right,val27_side_right,val27_back,val27_back_threequarter"
SHEET_VIEWS = ["orig07_front", "val27_front", "val27_threequarter_right", "val27_side_right", "val27_back",
               "val27_back_threequarter", "canon29_threequarter_left", "canon29_back"]


def run(log, cmd):
    log.write(f"\n===== {' '.join(cmd)}\n")
    log.flush()
    t = time.time()
    r = subprocess.run(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    return r.returncode == 0, round(time.time() - t, 1)


def run_variant(a, name, out):
    os.makedirs(out, exist_ok=True)
    log = open(os.path.join(out, "run.log"), "w")
    bl = lambda script, *args: [a.blender, "-b", "--factory-startup", "-P", os.path.join(ROOT, script), "--", *args]  # noqa: E731
    build, harness, report, regions = (os.path.join(out, d) for d in ("build", "harness", "report", "regions"))
    compare = os.path.join(build, f"{CID}_compare.blend")
    steps = [("build", bl("pipeline/charsys/build_character.py", "--spec", SPEC, "--override", os.path.join(EXP, name + ".json"),
                          "--out", build, "--no-glb")),
             ("harness", bl("pipeline/blender/compare_harness.py", "--subject", compare, "--index", IDX, "--out", harness,
                            "--samples", "48", "--fill", "0.94", "--keep-materials",
                            *(["--views", ",".join(SHEET_VIEWS)] if a.sheet_views_only else []))),
             ("sheet", [sys.executable, os.path.join(ROOT, "pipeline", "compare_sheet.py"), "--index", IDX, "--blender", harness,
                        "--out", report, "--label", f"{CID} hair {name}"]),
             ("regions", bl("pipeline/blender/boy_pilot/render_regions.py", compare, IDX, regions, MEASURED, "32")),
             ("metrics", [sys.executable, os.path.join(ROOT, "pipeline", "pilot_metrics.py"), "--index", IDX, "--harness", harness,
                          "--regions", regions, "--landmarks", LMK, "--out", os.path.join(report, "extra_metrics.json")])]
    times = {}
    for step, cmd in steps:
        ok, s = run(log, cmd)
        times[step] = s
        if not ok:
            return {"variant": name, "ok": False, "failed_step": step, "seconds": times}
    for f in glob.glob(os.path.join(build, f"{CID}_compare.blend")):  # 38 MB evaluation file: not needed after rendering
        os.remove(f)
    return {"variant": name, "ok": True, "seconds": times}


def summarise(out, names):
    S = {}
    for n in names:
        p = os.path.join(out, n, "report", "extra_metrics.json")
        m = os.path.join(out, n, "report", "measurements.json")
        if not os.path.exists(p):
            continue
        e = json.load(open(p))
        meas = json.load(open(m))
        V = e["views"]
        hb = json.load(open(os.path.join(out, n, "build", "build_report.json")))["hair"]
        S[n] = {"description": json.load(open(os.path.join(EXP, n + ".json")))["description"],
                "mean_iou": round(sum(v["iou"] for v in V.values()) / len(V), 4),
                "mean_hair_contour_pct_head": round(sum(v["hair_contour_mean_pct_head"] for v in V.values()) / len(V), 2),
                "mean_hair_contour_p95_pct_head": round(sum(v["hair_contour_p95_pct_head"] for v in V.values()) / len(V), 2),
                "mean_contour_pct_height": round(sum(v["contour_mean_pct_height"] for v in V.values()) / len(V), 2),
                "hair_dE2000_mean": round(sum(v["colour"]["hair"]["dE2000"] for v in V.values()) / len(V), 1)
                if all("hair" in v.get("colour", {}) for v in V.values()) else None,
                "head_fraction_err_pct": None, "hair_build": hb,
                "per_view": {k: {"iou": v["iou"], "hair_contour": v["hair_contour_mean_pct_head"]} for k, v in V.items()}}
        hf = [(x["subject"]["head_fraction"] / x["reference"]["head_fraction"] - 1) * 100
              for x in meas["views"] if "subject" in x and x["id"] in V]
        wh = [(x["subject"]["width_head"] / x["reference"]["width_head"] - 1) * 100
              for x in meas["views"] if "subject" in x and x["id"] in V]
        S[n]["head_fraction_err_pct"] = round(sum(hf) / len(hf), 1) if hf else None
        S[n]["head_width_err_pct"] = round(sum(wh) / len(wh), 1) if wh else None
    return S


def sheet(out, names, S):
    import numpy as np
    from PIL import Image, ImageDraw, ImageFilter
    sys.path.insert(0, os.path.join(ROOT, "pipeline"))
    import compare_sheet as CS
    vdir = os.path.join(os.path.dirname(IDX), "views")
    CW, CH = 200, 200
    def crop_head(img, mask, frac=0.42):
        x0, y0, x1, y1 = CS.bbox(mask)
        h = (y1 - y0) * frac
        cx = (x0 + x1) / 2
        box = (int(cx - h * 0.62), int(y0 - h * 0.08), int(cx + h * 0.62), int(y0 + h))
        return img.crop(box).resize((CW, CH), Image.LANCZOS)
    def outline(mask):
        return np.asarray(Image.fromarray(mask.astype(np.uint8) * 255).filter(ImageFilter.FIND_EDGES)) > 0
    rows = []
    # reference row
    cells = []
    for v in SHEET_VIEWS:
        ref = Image.open(os.path.join(vdir, v + ".png")).convert("RGB")
        mp = os.path.join(vdir, v + "_mask.png")
        mask = (np.asarray(Image.open(mp)) > 127) if os.path.exists(mp) else (np.asarray(ref.convert("L")) < 245)
        cells.append(crop_head(ref, mask))
    rows.append(("reference", cells))
    for n in names:
        hd = os.path.join(out, n, "harness")
        if not os.path.isdir(hd):
            continue
        cells = []
        for v in SHEET_VIEWS:
            rgba = Image.open(os.path.join(hd, v + ".png")).convert("RGBA")
            sub = np.asarray(rgba)[:, :, 3] > 127
            grey = Image.new("RGBA", rgba.size, (150, 150, 150, 255))
            grey.alpha_composite(rgba)
            mp = os.path.join(vdir, v + "_mask.png")
            if os.path.exists(mp):  # align to the reference frame and draw the reference outline in magenta
                ref_mask = np.asarray(Image.open(mp)) > 127
                rx0, ry0, rx1, ry1 = CS.bbox(ref_mask)
                sx0, sy0, sx1, sy1 = CS.bbox(sub)
                s = (ry1 - ry0) / (sy1 - sy0)
                c = grey.crop((sx0, sy0, sx1, sy1)).resize((max(1, round((sx1 - sx0) * s)), ry1 - ry0), Image.BILINEAR)
                canvas = Image.new("RGB", (ref_mask.shape[1], ref_mask.shape[0]), (150, 150, 150))
                canvas.paste(c.convert("RGB"), (round((rx0 + rx1) / 2 - c.width / 2), ry0))
                arr = np.asarray(canvas).copy()
                arr[outline(ref_mask)] = (255, 0, 255)
                cells.append(crop_head(Image.fromarray(arr), ref_mask))
            else:
                cells.append(crop_head(grey.convert("RGB"), sub))
        s = S.get(n, {})
        rows.append((f"{n}\nIoU {s.get('mean_iou', '?')}  hair {s.get('mean_hair_contour_pct_head', '?')}%", cells))
    LW = 210
    img = Image.new("RGB", (LW + CW * len(SHEET_VIEWS), 24 + CH * len(rows)), (30, 30, 30))
    d = ImageDraw.Draw(img)
    for j, v in enumerate(SHEET_VIEWS):
        d.text((LW + j * CW + 4, 6), v, fill=(230, 230, 230))
    for i, (lab, cells) in enumerate(rows):
        y = 24 + i * CH
        d.multiline_text((6, y + 8), lab, fill=(255, 255, 255))
        for j, c in enumerate(cells):
            img.paste(c, (LW + j * CW, y))
    p = os.path.join(out, "hair_multiview_sheet.jpg")
    img.save(p, quality=88)
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blender", required=True)
    ap.add_argument("--variants", default="")
    ap.add_argument("--out", default=os.path.join(ROOT, "renders", "experiments", "hair"))
    ap.add_argument("--sheet-only", action="store_true")
    ap.add_argument("--sheet-views-only", action="store_true", help="harness renders only the 8 sheet views (half the time)")
    ap.add_argument("--sheet-variants", default="", help="rows of the multi-view sheet (default: all)")
    a = ap.parse_args()
    names = a.variants.split(",") if a.variants else sorted(os.path.splitext(os.path.basename(p))[0]
                                                             for p in glob.glob(os.path.join(EXP, "*.json")))
    os.makedirs(a.out, exist_ok=True)
    runs = {}
    if not a.sheet_only:
        for n in names:
            t = time.time()
            runs[n] = run_variant(a, n, os.path.join(a.out, n))
            print(f"[hair_experiments] {n}: {'ok' if runs[n]['ok'] else 'FAILED ' + runs[n]['failed_step']} "
                  f"({time.time() - t:.0f} s)", flush=True)
    all_names = sorted(d for d in os.listdir(a.out) if os.path.isdir(os.path.join(a.out, d)))
    S = summarise(a.out, all_names)
    json.dump({"runs": runs, "variants": S}, open(os.path.join(a.out, "summary.json"), "w"), indent=1)
    print(json.dumps({k: {x: v[x] for x in ("mean_iou", "mean_hair_contour_pct_head", "mean_contour_pct_height",
                                             "head_fraction_err_pct", "head_width_err_pct")} for k, v in S.items()}, indent=1))
    rows = a.sheet_variants.split(",") if a.sheet_variants else all_names
    print("[hair_experiments] sheet:", sheet(a.out, rows, S))


if __name__ == "__main__":
    main()
