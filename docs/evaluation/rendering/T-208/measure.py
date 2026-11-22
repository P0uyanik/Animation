"""Measure the original display-referred PNGs and join frame timings to MX350 samples."""
import csv
import json
from datetime import datetime
from pathlib import Path
import statistics

import numpy as np
from PIL import Image

work = Path("build/t208-run")
docs = Path(__file__).resolve().parent


def rgb(path):
    with Image.open(path) as image:
        return np.asarray(image.convert("RGB"), dtype=np.int16)


def mae(a, b):
    return round(float(np.abs(a - b).mean()), 3)


def read_samples(folder):
    data = []
    with (folder / "smi.csv").open() as f:
        for stamp, mib in csv.reader(f):
            data.append((datetime.strptime(stamp, "%Y/%m/%d %H:%M:%S.%f").timestamp(), int(mib)))
    return data


rows = []
for folder in sorted(work.glob("s*-*")):
    if not (folder / "times.csv").is_file():
        continue
    shot, engine, _ = folder.name.split("-", 2)
    report_path = folder / "shot_render.json"
    setup_s = json.loads(report_path.read_bytes())["setup_s"] if report_path.exists() else ""
    samples = read_samples(folder)
    previous = None
    for frame, start, end in csv.reader((folder / "times.csv").open()):
        frame, start, end = int(frame), float(start), float(end)
        png = folder / f"frame_{frame:04d}.png"
        current = rgb(png)
        pair = ""
        if engine == "cycles":
            other = list(work.glob(f"{shot}-eevee-*/{png.name}"))
            if other:
                pair = mae(current, rgb(other[0]))
        patch_mae = ""
        if previous is not None and shot in ("s020", "s030"):
            y, x = ((slice(650, 700), slice(50, 450)) if shot == "s020"
                    else (slice(600, 680), slice(1100, 1240)))
            patch_mae = mae(current[y, x], previous[y, x])
        peaks = [m for t, m in samples if start <= t <= end]
        rows.append(dict(shot=shot, engine=engine, backend="OpenGL" if engine == "eevee" else "CPU",
                         status="ok", package_setup_s=setup_s, frame=frame, seconds=round(end-start, 3),
                         frame_peak_mib=max(peaks, default=""), run_peak_mib=max(m for _, m in samples),
                         previous_frame_rgb_mae=mae(current, previous) if previous is not None else "",
                         stationary_patch_rgb_mae=patch_mae, matched_eevee_rgb_mae=pair))
        previous = current
failed = work / "vulkan-s020-125-172"
if failed.exists():
    samples = read_samples(failed)
    for frame, start, end in csv.reader((failed / "times.csv").open()):
        start, end = float(start), float(end)
        peaks = [m for t, m in samples if start <= t <= end]
        rows.append(dict(shot="s020", engine="eevee", backend="Vulkan", status="device_lost_run",
                         package_setup_s="", frame=int(frame), seconds=round(end-start, 3),
                         frame_peak_mib=max(peaks, default=""), run_peak_mib=max(m for _,m in samples),
                         previous_frame_rgb_mae="", stationary_patch_rgb_mae="", matched_eevee_rgb_mae=""))
with (docs / "bench.csv").open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
for engine in ("eevee", "cycles"):
    group = [r for r in rows if r["engine"] == engine and r["status"] == "ok"]
    if group:
        print(engine, len(group), "mean s", statistics.mean(r["seconds"] for r in group),
              "peak MiB", max(r["run_peak_mib"] for r in group))
for shot in ("s020", "s030"):
    diffs = [r["previous_frame_rgb_mae"] for r in rows if r["shot"] == shot and r["previous_frame_rgb_mae"] != ""]
    if diffs:
        print(shot, len(diffs), "mean/p95/max delta", statistics.mean(diffs), np.percentile(diffs, 95), max(diffs))


