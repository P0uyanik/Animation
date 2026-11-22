"""Retry a package-renderer scene using a different graphics backend."""
from pathlib import Path
import os
import subprocess
import sys

work = Path("build/t208-run").resolve()
docs = Path(__file__).resolve().parent
shot, source, backend, frames = sys.argv[1:]
first, last = map(int, frames.split("-"))
out = work / f"{shot}-eevee-{frames}"
out.mkdir()
package, = (p for p in work.glob(f"e912*{shot}*") if p.is_dir())
cache = str(work / "cache")
env = dict(os.environ, TEMP=cache, TMP=cache, BLENDER_USER_RESOURCES=cache,
           T208_TIMES=str(out / "times.csv"))
cmd = ["D:/Animation/tools/blender-5.3/blender.exe", "-b", "--factory-startup", "--gpu-backend", backend,
       str(work / source / "shot.blend"), "--python-exit-code", "3", "-P", str(docs / "settings.py"),
       "-o", str(out / "frame_####"), "-s", str(first), "-e", str(last), "-a"]
with (out / "smi.csv").open("w") as smi, (out / "render.log").open("w") as log:
    monitor = subprocess.Popen(["nvidia-smi", "--query-gpu=timestamp,memory.used",
                                "--format=csv,noheader,nounits", "-lms", "500"], stdout=smi)
    try:
        subprocess.run(cmd, cwd=package, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    finally:
        monitor.terminate()
        monitor.wait()

