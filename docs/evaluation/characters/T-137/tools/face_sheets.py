#!/usr/bin/env python3
"""T-137 evidence driver: strict sheet, 100 % eye crops, expression sheet and shot-size pupil measure for one part.

    python3 docs/evaluation/characters/T-137/tools/face_sheets.py <part.json> <strict|eyes|expr|pupils> --out <dir>
        [--preview] [--samples N]

part.json (next to the part's override): {"character", "task", "columns": [{"tag", "label", "role", "blend"}],
"strict": {"body", "face", "rows": [[name, label, framing, yaw, reference, ai_target]]}, "eyes": {"refs": [...]},
"expr": {"rows": [[preset, reference|null]], "frame_h", "dz"}}. Blend paths are local builds (not committed).
Shared pieces are used unchanged: tools/review/blender_render.py + strict_sheet.py (T-087), T-109 face_probe.py,
T-113 expr_sheet.py, T-123 render_masks.material + tools/review/readability.py."""
import argparse
import json
import os
import subprocess
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "review"))
BG, BAR, TXT = (92, 92, 96), (20, 20, 20), (240, 240, 240)


def blender(script, job, out):
    jp = os.path.join(out, "job.json")
    with open(jp, "w") as f:
        json.dump(job, f, indent=1)
    with open(os.path.join(out, "render_log.txt"), "w") as f:
        subprocess.run([sys.executable, os.path.join(ROOT, "tools", "bpy_blender.py"), "-b", "--factory-startup", "-P",
                        os.path.join(ROOT, script), "--", jp], stdout=f, stderr=subprocess.STDOUT, cwd=ROOT, check=True)


def ref_image(ref):
    if not ref:
        return None
    im = Image.open(os.path.join(ROOT, ref["file"])).convert("RGB")
    return im.crop(tuple(ref["crop"])) if ref.get("crop") else im


def fit(im, w, h):
    s = min(w / im.width, h / im.height)
    return im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)


def strict(part, out, a):
    import strict_sheet
    cfg = part["strict"]
    samples, px = (2, 120) if a.preview else (a.samples or 16, 360)
    views = [{"name": n, "yaw_deg": yaw, "elevation_deg": 5.0, **cfg[fr]} for n, _, fr, yaw, _, _ in cfg["rows"]]
    job = {"out": out, "engine": "cycles", "samples": samples, "px": px, "lens_mm": 70.0, "sensor_mm": 36.0,
           "calibration": "character_neutral/1", "views": views,
           "columns": [{"tag": c["tag"], "blend": os.path.abspath(c["blend"]), "comparison_pose": None}
                       for c in part["columns"]]}
    blender("tools/review/blender_render.py", job, out)
    rs = {"engine": "cycles", "samples": samples}
    resolved = {"character": part["character"], "task": part["task"], "compare": {"variant": "master (A-pose)"},
                "light": {"calibration": "character_neutral/1"}, "render": rs, "preview": rs,
                "recipe_sha256": "no-recipe(T-137-driver)",
                "columns": [{"tag": c["tag"], "label": c["label"], "role": c["role"]} for c in part["columns"]],
                "cameras": {"lens_mm": 70.0, "views": [{"name": n, "label": lab, "elevation_deg": 5.0, "framing": fr}
                                                       for n, lab, fr, _, _, _ in cfg["rows"]]},
                "references": {n: r for n, _, _, _, r, _ in cfg["rows"] if r},
                "ai_target": {"label": "AI target", "images": {n: t for n, _, _, _, _, t in cfg["rows"] if t}}}
    name = "strict_preview.jpg" if a.preview else "strict.jpg"
    print(name, strict_sheet.make_sheet(resolved, out, os.path.join(out, name),
                                        title_note="preview" if a.preview else ""))


def eyes(part, out, a):
    """Eye strip rendered at 1280 px (0.24 m wide): pasted 1:1, never resampled. Glasses stay on."""
    px = 1280
    job = {"out": out, "engine": "cycles", "samples": 2 if a.preview else (a.samples or 16), "px": px, "frame": "eyes",
           "views": part["eyes"].get("views", {"front": 0, "threequarter": -35}), "hide": ["fur"],
           "columns": [{"tag": c["tag"], "blend": os.path.abspath(c["blend"])} for c in part["columns"]]}
    blender("docs/evaluation/characters/T-109/face_probe.py", job, out)
    refs = [fit(ref_image(r), px, 10 ** 6) for r in part["eyes"].get("refs", [])]
    tiles = [(f"{c['label']} | {v} | 100 % (0.19 mm/px)", Image.open(os.path.join(out, c["tag"], v + ".png")).convert("RGB"))
             for v in job["views"] for c in part["columns"]]
    tiles += [(f"REFERENCE {r['label']} (scaled to width)", im) for r, im in zip(part["eyes"]["refs"], refs)]
    sheet = Image.new("RGB", (px, sum(im.height + 18 for _, im in tiles)), BG)
    d, y = ImageDraw.Draw(sheet), 0
    for text, im in tiles:
        d.rectangle((0, y, px, y + 17), fill=BAR)
        d.text((4, y + 3), f"{part['task']} {part['character']} | {text}", fill=TXT)
        sheet.paste(im, (0, y + 18))
        y += im.height + 18
    sheet.save(os.path.join(out, "eyes_100.jpg"), quality=92)
    print("eyes_100.jpg", sheet.size)


def expr(part, out, a):
    cfg, T, HEAD = part["expr"], 220, 16
    job = {"out": out, "samples": 2 if a.preview else (a.samples or 12), "px": 300, "frame": "face", "yaw": 0.0, "elev": 5.0,
           "columns": [{"tag": c["tag"], "blend": os.path.abspath(c["blend"])} for c in part["columns"]],
           "rows": [{"tag": n, "controls": {} if n == "Neutral" else {"face_" + n: 1.0}, "gaze_deg": [0.0, 0.0]}
                    for n, _ in cfg["rows"]]}
    for k in ("frame_h", "dz"):
        if k in cfg:
            job[k] = cfg[k]
    blender("docs/evaluation/characters/T-113/expr_sheet.py", job, out)
    per = 1 + len(part["columns"])
    nper = 2 if per >= 3 else 3
    nrow = -(-len(cfg["rows"]) // nper)
    sheet = Image.new("RGB", (per * T * nper, 22 + nrow * (T + HEAD)), BG)
    d = ImageDraw.Draw(sheet)
    d.text((6, 5), f"{part['task']} {part['character']} expressions | reference | " +
           " | ".join(c["label"] for c in part["columns"]) + f" | character_neutral/1, Cycles {job['samples']} spp", fill=TXT)
    for i, (name, ref) in enumerate(cfg["rows"]):
        x, y = (i % nper) * per * T, 22 + (i // nper) * (T + HEAD)
        ims = [ref_image(ref)] + [Image.open(p) if os.path.exists(p) else None
                                  for p in (os.path.join(out, name, c["tag"] + ".png") for c in part["columns"])]
        for j, im in enumerate(ims):
            if im is not None:
                im = fit(im.convert("RGB"), T, T)
                sheet.paste(im, (x + j * T + (T - im.width) // 2, y + HEAD + (T - im.height) // 2))
        d.rectangle((x, y, x + per * T - 1, y + HEAD - 1), fill=BAR)
        d.text((x + 4, y + 2), name + (f"  (ref {ref.get('label', '')})" if ref else ""), fill=TXT)
    sheet.save(os.path.join(out, "expressions.jpg"), quality=90)
    print("expressions.jpg", sheet.size, "missing:", open(os.path.join(out, "missing.json")).read().strip())


def pupils(part, out, a):
    """Pupil pixels at shot size (640 x 360): the T-123 ID material on each column's master, measured by readability.py.
    Frame 1 = medium shot (0.60 m frame height), frame 2 = wide (1.30 m); 50 mm lens, front, eye height. No cup."""
    import readability
    rows = []
    for c in part["columns"]:
        d = os.path.join(out, c["tag"])
        os.makedirs(d, exist_ok=True)
        subprocess.run([sys.executable, os.path.join(ROOT, "tools", "bpy_blender.py"), "-b", "--factory-startup",
                        os.path.abspath(c["blend"]), "-P", os.path.join(HERE, "pupil_masks.py"), "--", d],
                       stdout=open(os.path.join(d, "log.txt"), "w"), stderr=subprocess.STDOUT, cwd=ROOT, check=True)
        readability.main([d, "--frames", "1", "2", "--eye", "char.L=51", "--eye", "char.R=102", "--cup-threshold", "0",
                          "--pupil-threshold", "8", "--out", d])
        for line in open(os.path.join(d, "readability.csv")).read().splitlines()[1:]:
            rows.append(c["label"] + "," + line)
    head = open(os.path.join(out, part["columns"][0]["tag"], "readability.csv")).readline().strip()
    with open(os.path.join(out, "pupils.csv"), "w") as f:
        f.write("column," + head + "\n" + "\n".join(rows) + "\n")
    print(open(os.path.join(out, "pupils.csv")).read())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("part")
    ap.add_argument("what", choices=["strict", "eyes", "expr", "pupils"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--samples", type=int, default=0)
    a = ap.parse_args()
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)
    {"strict": strict, "eyes": eyes, "expr": expr, "pupils": pupils}[a.what](json.load(open(a.part)), out, a)


if __name__ == "__main__":
    main()
