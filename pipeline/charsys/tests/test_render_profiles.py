"""T-166 tests: final720 is the default render profile and HEVC 10-bit the default delivery encode; the previous
128 spp / 0.01 preset (legacy128) and the H.264 8-bit fallback still resolve. Fast: no Blender.

    python3 pipeline/charsys/tests/test_render_profiles.py
"""
import ast
import argparse
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
CHARSYS = os.path.join(ROOT, "pipeline", "charsys")
FAILS = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f" {detail}"))
    if not ok:
        FAILS.append(name)


P = json.load(open(os.path.join(CHARSYS, "render_profiles.json")))
prof = P["profiles"]


def shot_render_parse(argv):
    """The real shot_render.parse (bpy-free), pulled out of the source and run against `argv`."""
    src = open(os.path.join(CHARSYS, "shot_render.py")).read()
    fn = next(n for n in ast.parse(src).body if isinstance(n, ast.FunctionDef) and n.name == "parse")
    ns = {"argparse": argparse, "json": json, "os": os, "sys": type("S", (), {"argv": ["x", "--"] + argv})}
    ns["__file__"] = os.path.join(CHARSYS, "shot_render.py")
    exec(compile(ast.Module([fn], []), "shot_render.parse", "exec"), ns)
    return ns["parse"]()


base = ["--bake", "b", "--cast", "c", "--out", "o"]

# --- profiles
check("default profile is final720", P["default_profile"] == "final720")
f = prof["final720"]
check("final720 = 1280x720, 128 spp, adaptive 0.05, persistent data",
      f["resolution"] == [1280, 720] and f["samples"] == 128 and f["cycles"] == {"adaptive_threshold": 0.05}
      and f["render"] == {"use_persistent_data": True})
check("old preset still selectable by name (legacy128: 128 spp, adaptive 0.01, no forced resolution)",
      prof["legacy128"]["samples"] == 128 and prof["legacy128"]["cycles"] == {"adaptive_threshold": 0.01}
      and "resolution" not in prof["legacy128"] and "render" not in prof["legacy128"])
check("review profile unchanged", prof["review"]["samples"] == 16 and prof["review"]["cycles"] == {"adaptive_threshold": 0.05})

# --- shot_render.parse
a = shot_render_parse(base)
check("shot_render default -> final720", a.profile == "final720" and a.resolution == [1280, 720] and a.samples == 128
      and a.profile_data["cycles"]["adaptive_threshold"] == 0.05)
a = shot_render_parse(base + ["--profile", "legacy128"])
check("shot_render --profile legacy128 -> 128 spp, 0.01, resolution from the bake",
      a.samples == 128 and a.resolution is None and a.profile_data["cycles"]["adaptive_threshold"] == 0.01)
a = shot_render_parse(base + ["--samples", "8", "--resolution", "64", "36"])
check("explicit --samples/--resolution still override the profile", a.samples == 8 and a.resolution == [64, 36])
try:
    shot_render_parse(base + ["--profile", "nope"])
    check("shot_render unknown profile refused", False)
except SystemExit:
    check("shot_render unknown profile refused", True)

# --- delivery encode
enc = P["encode"]
check("default encode is hevc10", enc["default"] == "hevc10")
h, x = enc["codecs"]["hevc10"]["args"], enc["codecs"]["h264"]["args"]
check("hevc10 = x265 10-bit", "libx265" in h and "yuv420p10le" in h and h[h.index("-crf") + 1] == "18")
check("h264 fallback = x264 8-bit", "libx264" in x and "yuv420p" in x and "yuv420p10le" not in x)
src = open(os.path.join(ROOT, "pipeline", "production", "run_shot.py")).read()
check("run_shot encode step takes its args from the codec table", "*a.encode_args" in src and '"libx264"' not in src)
check("run_shot passes the profile to shot_render", '"--profile", a.profile' in src)
r = subprocess.run([sys.executable, os.path.join(ROOT, "pipeline", "production", "run_shot.py"), "--shot", "x", "--blender", "b",
                    "--codec", "nope"], capture_output=True, text=True)
check("run_shot unknown codec refused", r.returncode == 2 and "unknown --codec" in r.stderr, r.stderr[-200:])
r = subprocess.run([sys.executable, os.path.join(ROOT, "pipeline", "production", "run_shot.py"), "--shot", "x", "--blender", "b",
                    "--profile", "nope"], capture_output=True, text=True)
check("run_shot unknown profile refused", r.returncode == 2 and "unknown --profile" in r.stderr, r.stderr[-200:])

# --- both encodes really run (tiny synthetic clip) when ffmpeg has the encoders
def have(name):
    p = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True, text=True)
    return name in p.stdout
for key, enc_name, pix in (("hevc10", "libx265", "yuv420p10le"), ("h264", "libx264", "yuv420p")):
    if not have(enc_name):
        print(f"SKIP encode {key}: ffmpeg has no {enc_name}")
        continue
    with tempfile.TemporaryDirectory() as t:
        out = os.path.join(t, "o.mp4")
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=size=128x72:rate=24:duration=0.5",
               *enc["codecs"][key]["args"], out]
        r = subprocess.run(cmd, capture_output=True, text=True)
        probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=pix_fmt",
                                "-of", "csv=p=0", out], capture_output=True, text=True).stdout.strip() if r.returncode == 0 else ""
        check(f"encode {key} runs and yields {pix}", r.returncode == 0 and probe == pix, r.stderr[-200:] + probe)

print("[test_render_profiles] " + ("FAILED: " + ", ".join(FAILS) if FAILS else "ALL PASS"))
sys.exit(1 if FAILS else 0)
