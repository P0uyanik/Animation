"""Run one verified package through the repository renderer, with the benchmark prelude."""
import os
from pathlib import Path
import subprocess
import sys

root = Path.cwd()
sys.path.insert(0, str(root / "tools/pc"))
import render_package

shot, engine, frames = sys.argv[1:]
work = root / "build/t208-run"
package, = work.glob(f"*{shot}*.zip")
out = work / f"{shot}-{engine}-{frames}"
out.mkdir()
cache = work / "cache"
cache.mkdir(exist_ok=True)
os.environ.update(T208_TIMES=str(out / "times.csv"), TEMP=str(cache), TMP=str(cache),
                  BLENDER_USER_RESOURCES=str(cache), PYTHONDONTWRITEBYTECODE="1")
base_command = render_package.render_command


def command(*args):
    cmd, settings = base_command(*args)
    pos = cmd.index("-P")
    cmd[pos:pos] = ["--gpu-backend", os.environ.get("T208_BACKEND", "vulkan"), "--python-exit-code", "3",
                    "-P", str(Path(__file__).with_name("settings.py").resolve())]
    return cmd, settings


render_package.render_command = command
with (out / "smi.csv").open("w") as log:
    monitor = subprocess.Popen(["nvidia-smi", "--query-gpu=timestamp,memory.used",
                                "--format=csv,noheader,nounits", "-lms", "500"], stdout=log)
    try:
        status = render_package.main([str(package), "--engine", engine, "--profile", "review",
                                      "--resolution", "1280", "720", "--samples", "16",
                                      "--blender", "D:/Animation/tools/blender-5.3/blender.exe",
                                      "--out", str(out), "--frames", frames])
    finally:
        monitor.terminate()
        monitor.wait()
sys.exit(status)


