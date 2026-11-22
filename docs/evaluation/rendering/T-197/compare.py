"""Summarize one complete matched run. Use original display-referred PNGs for metrics."""
import csv
import os
from datetime import datetime
from pathlib import Path
from statistics import mean
import sys

import numpy as np
from PIL import Image, ImageDraw

BUILD = Path("build/t197") / os.environ.get("T197_RUN", "review")
OUT = Path(__file__).resolve().parent
CROPS = {
    "sheet-front": (380, 0, 900, 720),
    "prop-boat": (160, 70, 1120, 680),
    "sheet-threequarter": (380, 0, 900, 720),
    "sheet-face_front": (240, 20, 1040, 700),
}


def read_rows(path):
    with path.open(newline="") as fp:
        return list(csv.reader(fp))


def render_stats(engine):
    folder = BUILD / engine
    samples = []
    for stamp, memory, _ in read_rows(folder / "smi.csv"):
        t = datetime.strptime(stamp.strip(), "%Y/%m/%d %H:%M:%S.%f").timestamp()
        if memory.strip().isdigit():
            samples.append((t, int(memory)))
    rows = {}
    for view, warmup, sec, start, end in read_rows(folder / "times.csv"):
        usage = [m for t, m in samples if float(start) <= t <= float(end)]
        rows[view] = dict(view=view, engine=engine, warmup=warmup, seconds=float(sec),
                          frame_peak_MiB=max(usage), run_peak_MiB=max(m for _, m in samples),
                          vram_samples=len(usage))
    return rows


def main(engine):
    cpu, gpu = render_stats("cycles"), render_stats(engine)
    if list(cpu) != list(gpu):
        raise ValueError("Incomplete matched pair")
    rows = []
    for view, ref in cpu.items():
        im = [Image.open(BUILD / dev / (view + ".png")).convert("RGB") for dev in ("cycles", engine)]
        assert im[0].size == im[1].size == (1280, 720)
        delta = np.abs(np.asarray(im[0], dtype=np.int16) - np.asarray(im[1], dtype=np.int16))
        stats = {"pair_rgb8_mae": round(float(delta.mean()), 3),
                 "pair_rgb8_rmse": round(float(np.sqrt(np.mean(np.square(delta, dtype=np.float64)))), 3),
                 "pair_rgb8_max": int(delta.max())}
        rows.extend([ref, dict(gpu[view], **stats)])
        if ref["warmup"] == "True":
            continue
        box = CROPS[view]
        w, h = box[2]-box[0], box[3]-box[1]
        canvas = Image.new("RGB", (2*w, h+28), "#202126")
        draw = ImageDraw.Draw(canvas)
        for i, label in enumerate(("Cycles CPU", "EEVEE MX350")):
            draw.text((i*w+9, 7), f"{label}   |   {view}   |   1:1", fill="white")
            canvas.paste(im[i].crop(box), (i*w, 28))
        canvas.save(OUT / (view + ".jpg"), quality=95, subsampling=0)
    with (OUT / "bench.csv").open("w", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(rows[0])+list(stats))
        writer.writeheader()
        writer.writerows(rows)
    for batch in (cpu, gpu):
        print(mean(r["seconds"] for r in batch.values() if r["warmup"] == "False"))
    print(rows)


if __name__ == "__main__":
    main(sys.argv[1])

