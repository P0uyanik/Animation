"""Summarize the completed Blender runs and make a 1:1 face crop comparison."""
import csv
import json
import os
from pathlib import Path
from statistics import mean
import numpy as np
from PIL import Image, ImageDraw

BASE = Path("build") / os.environ.get("T173_RUN", "t173")
OUT = Path(__file__).resolve().parent
rows = []
crops = []
cpu_mean = None
matched = {"2", "3"}  # The original CUDA side view was interrupted by multi-hour sampling gaps.
for preset in ("final720", "legacy128"):
    for device in ("CPU", "OPTIX", "CUDA"):
        run = BASE / f"{preset}-{device}"
        if not run.is_dir():
            continue
        samples = list(csv.reader((run / "smi.csv").read_text().splitlines()))
        peak = max((int(s[1]) for s in samples if len(s) == 3 and s[1].strip().isdigit()), default="")
        timing_file = run / "times.csv"
        timings = list(csv.reader(timing_file.read_text().splitlines())) if timing_file.exists() else []
        if not timings:
            rows.append(dict(preset=preset, device=device, status="failed", run_peak_MiB=peak))
            print(preset, device, "failed", peak)
            continue
        measured = [float(t) for frame, warm, t in timings if warm == "False" and frame in matched]
        avg = mean(measured)
        if (preset, device) == ("final720", "CPU"):
            cpu_mean = avg
        speed = cpu_mean / avg
        metrics = []
        for frame, warm, sec in timings:
            row = dict(preset=preset, device=device, status="rendered", frame=frame, warmup=warm,
                       seconds=sec, matched_view=frame in matched, run_peak_MiB=peak, matched_mean_s=round(avg,3),
                       vs_final720_cpu=round(speed,3) if speed else "", estimate_192_min=round(avg*3.2,2))
            if preset == "final720" and warm == "False":
                with Image.open(run / f"{frame}.png") as src:
                    image = src.convert("RGB")
                if device != "CPU":
                    with Image.open(BASE / f"final720-CPU/{frame}.png") as cpu:
                        delta = np.abs(np.asarray(image, dtype=np.int16) - np.asarray(cpu.convert("RGB"), dtype=np.int16))
                    mae = delta.mean()
                    mse = np.mean(np.square(delta, dtype=np.float64))
                    row.update(rgb8_mae=round(mae,4), rgb8_rmse=round(np.sqrt(mse),4),
                               rgb8_max=delta.max())
                    metrics.append((mae,mse,delta.max()))
                if frame == "2":
                    crops.append((device,image.crop((440,25,840,345))))
            rows.append(row)
        requested = json.loads((run / "requested.json").read_text())
        finished = {int(frame) for frame, _, _ in timings}
        for frame in requested:
            if frame not in finished:
                rows.append(dict(preset=preset, device=device, frame=frame, status="incomplete",
                                 matched_view=False, run_peak_MiB=peak))
        print(preset, device, avg, speed, avg*3.2, peak, metrics)
with (OUT / "bench.csv").open("w", newline="") as file:
    writer = csv.DictWriter(file, fieldnames="preset device status frame warmup seconds matched_view run_peak_MiB matched_mean_s vs_final720_cpu estimate_192_min rgb8_mae rgb8_rmse rgb8_max".split())
    writer.writeheader()
    writer.writerows(rows)
canvas = Image.new("RGB",(400*len(crops),350),"#222222")
draw = ImageDraw.Draw(canvas)
for col,(device,crop) in enumerate(crops):
    canvas.paste(crop,(400*col,30))
    draw.text((400*col+10,9),f"{device}   |   FRONT   |   1:1",fill="white")
canvas.save(OUT / "front.jpg", quality=95, subsampling=0)
