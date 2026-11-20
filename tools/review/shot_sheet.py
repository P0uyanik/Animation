#!/usr/bin/env python3
"""Shot evidence sheet (T-165): JSON-driven before/after frame grid with optional crops, at most 2048 px.

    python3 tools/review/shot_sheet.py <sheet.json> [--out sheet.jpg] [--lock PATH]

Use this instead of a per-task make_sheet script. The JSON:
    {
      "title": "T-NNN e910 before/after",
      "columns": [{"label": "before main@abc1234", "dir": "out/before"},
                  {"label": "after t-NNN@def5678", "dir": "out/after"}],
      "frames": [1, 24, 48],                    # one row per frame
      "pattern": "frame_{frame:04d}.png",       # file name in each column dir (default shown)
      "crops": [{"label": "face", "box": [0.35, 0.05, 0.65, 0.40]}],   # optional; fractions or pixels
      "out": "out/sheet.jpg", "max_px": 2048,
      "render": [{"cmd": ["python3", "pipeline/production/run_shot.py", "..."]}]   # optional, see below
    }
Each row is one frame: every column's full frame, then every crop of every column (same box for all columns, so
crops compare like with like). Missing files show as "not provided" tiles; the sheet still builds, and the
command exits 1 so a missing frame is not overlooked. Every tile of the sheet is scaled by one factor; the whole
sheet fits in max_px (default 2048, capped at 2048). Relative paths resolve against the JSON file's directory.
Optional "render" commands run first, one at a time, under the render queue lock (tools/render_queue.py); wrap a
recipe render the same way: `python3 tools/render_queue.py run -- python3 tools/review/recipe.py sheet ...`.
Writes <out> and <out>.json (inputs with sha256, missing list, size). Opt-in tool."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from recipe import sha256_file  # noqa: E402  (reuse the recipe's hashing)

SHEET_MAX_PX = 2048
TITLE_H, PAD = 24, 4


def load(path: Path) -> dict:
    spec = json.loads(path.read_text(encoding="utf-8"))
    problems = []
    if not spec.get("columns"):
        problems.append("columns: at least one {label, dir}")
    if not spec.get("frames"):
        problems.append("frames: at least one frame")
    for i, crop in enumerate(spec.get("crops", [])):
        box = crop.get("box", [])
        if len(box) != 4 or not (box[0] < box[2] and box[1] < box[3]):
            problems.append(f"crops[{i}].box must be [x0, y0, x1, y1] with x0 < x1, y0 < y1")
    if problems:
        raise ValueError("; ".join(problems))
    return spec


def crop_box(box, w: int, h: int) -> tuple[int, int, int, int]:
    if all(0 <= float(v) <= 1 for v in box):
        x0, y0, x1, y1 = (float(box[0]) * w, float(box[1]) * h, float(box[2]) * w, float(box[3]) * h)
    else:
        x0, y0, x1, y1 = (float(v) for v in box)
    x0, y0 = max(0, round(x0)), max(0, round(y0))
    return x0, y0, max(x0 + 1, min(w, round(x1))), max(y0 + 1, min(h, round(y1)))


def frame_path(base: Path, column: dict, pattern: str, frame) -> Path:
    d = Path(column["dir"])
    return (d if d.is_absolute() else base / d) / pattern.format(frame=frame)


def run_renders(spec: dict, lock: str) -> None:
    import render_queue  # tools/render_queue.py
    for job in spec.get("render", []):
        with render_queue.render_lock(label="shot_sheet", lock=Path(lock) if lock else None):
            code = subprocess.run(job["cmd"], cwd=job.get("cwd") or None).returncode
        if code:
            raise SystemExit(f"shot_sheet: render step failed (exit {code}): {job['cmd'][:3]}")


def build(spec: dict, base: Path, out: Path) -> dict:
    from PIL import Image, ImageDraw
    from strict_sheet import tile, HEAD_H

    pattern = spec.get("pattern", "frame_{frame:04d}.png")
    columns, frames, crops = spec["columns"], spec["frames"], spec.get("crops", [])
    max_px = min(int(spec.get("max_px", SHEET_MAX_PX)), SHEET_MAX_PX)
    inputs, missing, images = [], [], {}
    for frame in frames:
        for c in columns:
            p = frame_path(base, c, pattern, frame)
            if p.is_file():
                images[(str(frame), c["label"])] = Image.open(p).convert("RGB")
                inputs.append({"frame": frame, "column": c["label"], "path": str(p), "sha256": sha256_file(p)})
            else:
                missing.append(str(p))
    sample = next(iter(images.values()), None)
    fw, fh = (sample.width, sample.height) if sample else (640, 360)
    tiles_per_row = len(columns) * (1 + len(crops))
    # natural tile size: full frame at its own aspect; crops at the frame's tile height
    raw_w, raw_h = fw, fh + HEAD_H
    room_w = max_px - (tiles_per_row + 1) * PAD
    room_h = max_px - TITLE_H - (len(frames) + 1) * PAD
    scale = min(1.0, room_w / (tiles_per_row * raw_w), room_h / (len(frames) * raw_h))
    tw, th = max(32, int(raw_w * scale)), max(32, int(raw_h * scale))
    W = tiles_per_row * tw + (tiles_per_row + 1) * PAD
    H = TITLE_H + len(frames) * (th + PAD) + PAD
    sheet = Image.new("RGB", (W, H), (60, 60, 64))
    d = ImageDraw.Draw(sheet)
    d.text((PAD, 6), str(spec.get("title", ""))[:200], fill=(240, 240, 240))
    for r, frame in enumerate(frames):
        y = TITLE_H + r * (th + PAD)
        k = 0
        for c in columns:
            im = images.get((str(frame), c["label"]))
            cells = [(im, f"f{frame} {c['label']}")]
            for crop in crops:
                part = im.crop(crop_box(crop["box"], im.width, im.height)) if im is not None else None
                cells.append((part, f"f{frame} {c['label']} · {crop.get('label', 'crop')}"))
            for img, text in cells:
                sheet.paste(tile(img, tw, th, text, missing=img is None), (PAD + k * (tw + PAD), y))
                k += 1
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, quality=90)
    record = {"sheet": str(out), "size": [W, H], "max_px": max_px, "frames": frames,
              "columns": [c["label"] for c in columns], "crops": crops, "inputs": inputs, "missing": missing}
    Path(str(out) + ".json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("spec")
    parser.add_argument("--out", default="")
    parser.add_argument("--lock", default="", help="render lock path (default: tools/render_queue.py default)")
    args = parser.parse_args(argv)
    spec_path = Path(args.spec).resolve()
    try:
        spec = load(spec_path)
    except (OSError, ValueError) as exc:
        print(f"shot_sheet: invalid spec: {exc}", file=sys.stderr)
        return 2
    base = spec_path.parent
    out = Path(args.out or spec.get("out") or spec_path.with_suffix(".jpg"))
    out = out if out.is_absolute() else (Path.cwd() / out if args.out else base / out)
    run_renders(spec, args.lock)
    record = build(spec, base, out)
    print(f"shot_sheet: {out} {record['size'][0]}x{record['size'][1]} · {len(record['inputs'])} frame(s)"
          + (f" · MISSING {len(record['missing'])}: {record['missing'][0]}" if record["missing"] else ""))
    return 1 if record["missing"] else 0


if __name__ == "__main__":
    sys.exit(main())
