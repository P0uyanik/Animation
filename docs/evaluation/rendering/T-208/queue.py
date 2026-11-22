from pathlib import Path
import subprocess
import os
import sys


work = Path("build/t208-run")
runner = Path("docs/evaluation/rendering/T-208/run.py")


def run(shot, engine, frames):
    if (work / f"{shot}-{engine}-{frames}/shot_render.json").exists():
        return
    subprocess.run([sys.executable, "-B", str(runner), shot, engine, frames], check=True)



limit = False
for shot, frames in (("s020", (147, 167, 135)), ("s030", (93, 140, 117)), ("s010", (41, 184))):
    for index, frame in enumerate(frames):
        if limit and index >= 2:
            break
        run(shot, "cycles", str(frame))
        values = (work / f"{shot}-cycles-{frame}/times.csv").read_text().strip().split(",")
        if float(values[2]) - float(values[1]) > 360:
            limit = True


os.environ["T208_BACKEND"] = "opengl"
for frame in (41, 184):
    run("s010", "eevee", str(frame))
run("s030", "eevee", "93-140")


