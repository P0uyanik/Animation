"""Workflow-contract tests for pipeline/production/run_shot.py (T-001).

    python3 pipeline/production/tests/test_run_shot_workflow.py --blender <blender> [--out <dir>]

1. Idempotent, cache-aware prepare (every shot under episodes/): prepare runs twice; the second reports every cast
   member as cached and changes nothing: sha256 + size + mtime_ns of every file under assets/, the shot's masters
   and packages, shot.resolved.scene.json and cast.json are identical before and after.
2. status.json contract (plush.run_status/1) and the latest pointer.
3. Cancel during a render (fake Blender that leaves a partly written frame): SIGTERM to the process group -> the run
   is marked cancelled, the partial frame is removed, the complete one kept, no process of the group is left,
   earlier runs and latest are untouched. Also: a forced kill finalised with --mark-cancelled.
4. A failing render: state failed with the error text; latest untouched.
5. Command-line default behaviour (no --run-dir, no --stages): outputs exactly where M3.2 wrote them, run_shot.json
   with the M3.2 keys, no runs/ folder touched.
Tests 3-5 use a fake Blender for the render step only (the real one prepares) and a copy of a shot in a temporary
episodes folder, so no repository shot is touched. Writes results to <out>/run_shot_workflow_tests.json."""
import argparse
import hashlib
import json
import os
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
import time
import zlib

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
RUN_SHOT = os.path.join(ROOT, "pipeline", "production", "run_shot.py")
results, failures = {}, []


def check(name, cond, detail=""):
    print(f"[{'PASS' if cond else 'FAIL'}] {name}{(': ' + str(detail)) if detail else ''}")
    if not cond:
        failures.append(name)
    return cond


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def snapshot(paths):
    snap = {}
    for p in paths:
        if os.path.isfile(p):
            files = [p]
        else:
            files = [os.path.join(d, f) for d, _, fs in os.walk(p) for f in fs]
        for f in files:
            st = os.stat(f)
            snap[os.path.relpath(f, ROOT)] = (sha(f), st.st_size, st.st_mtime_ns)
    return snap


def png(w=4, h=2):
    raw = b"".join(b"\x00" + bytes([200, 100, 50]) * w for _ in range(h))
    chunk = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


FAKE_BLENDER = r'''#!/usr/bin/env python3
# Fake Blender for the render step only: FAKE_MODE=ok | partial_then_hang | fail.
import json, os, sys, time
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
mode = os.environ.get("FAKE_MODE", "ok")
def arg(n, d=None):
    return args[args.index(n) + 1] if n in args else d
out = arg("--out"); fr = arg("--frames", "1-1"); a, _, b = fr.partition("-"); a, b = int(a), int(b or a)
os.makedirs(out, exist_ok=True)
good = open(os.environ["FAKE_PNG"], "rb").read()
if mode == "fail":
    print("fake blender: simulated render failure"); sys.exit(3)
for f in range(a, b + 1):
    p = os.path.join(out, f"frame_{f:04d}.png")
    if mode == "partial_then_hang" and f == a + 1:
        open(p, "wb").write(good[:len(good) // 2])   # a frame cut off while being written
        time.sleep(600)
    open(p, "wb").write(good)
json.dump({"frames": [a, b], "resolution": [4, 2], "samples": 1, "characters": {}}, open(os.path.join(out, "shot_render.json"), "w"))
'''


def run_shot(args, **kw):
    return subprocess.run([sys.executable, RUN_SHOT] + args, capture_output=True, text=True, **kw)


def test_idempotent_prepare(blender, shots):
    out = {}
    published = []
    for shot in shots:
        sj = json.load(open(shot))
        for src in sj.get("production", {}).get("cast", {}).values():
            if "version_dir" in src:
                published.append(os.path.join(ROOT, src["version_dir"]))
    for shot in shots:
        build = os.path.join(os.path.dirname(shot), "build")
        first = run_shot(["--shot", shot, "--blender", blender, "--stages", "prepare", "--run-dir", f"t001-prepare-a-{os.getpid()}"])
        check(f"prepare 1 ok ({os.path.relpath(shot, ROOT)})", first.returncode == 0, first.stderr[-500:])
        watched = [os.path.join(ROOT, "assets"), os.path.join(build, "masters"), os.path.join(build, "packages"),
                   os.path.join(build, "shot.resolved.scene.json"), os.path.join(build, "cast.json")] + published
        before = snapshot([p for p in watched if os.path.exists(p)])
        time.sleep(1.1)  # so a rewrite would show in the modification time
        second = run_shot(["--shot", shot, "--blender", blender, "--stages", "prepare", "--run-dir", f"t001-prepare-b-{os.getpid()}"])
        check(f"prepare 2 ok ({os.path.relpath(shot, ROOT)})", second.returncode == 0, second.stderr[-500:])
        after = snapshot([p for p in watched if os.path.exists(p)])
        rep = json.load(open(os.path.join(build, "runs", f"t001-prepare-b-{os.getpid()}", "prepare.json")))
        changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
        name = os.path.relpath(shot, ROOT)
        check(f"second prepare reports everything cached ({name})", rep["all_cached"] and all(c["from_cache"] for c in rep["cast"].values()),
              {n: (c["master_state"], c["package_state"]) for n, c in rep["cast"].items()})
        check(f"second prepare changes no file: hashes, sizes, mtimes ({name})", not changed, changed[:5])
        check(f"resolved scene and cast.json not rewritten ({name})", not rep["resolved_scene_written"] and not rep["cast_json_written"])
        st = json.load(open(os.path.join(build, "runs", f"t001-prepare-b-{os.getpid()}", "status.json")))
        check(f"status contract after prepare ({name})", st["format"] == "plush.run_status" and st["state"] == "done"
              and st["stages"] == ["prepare"] and st["stages_done"] == ["prepare"])
        check(f"latest -> the successful run ({name})", open(os.path.join(build, "runs", "latest")).read().strip() == f"t001-prepare-b-{os.getpid()}")
        out[name] = {"files_compared": len(before), "files_changed": changed,
                     "first_prepare": json.load(open(os.path.join(build, "runs", f"t001-prepare-a-{os.getpid()}", "prepare.json")))["cast"],
                     "second_prepare": rep["cast"], "second_all_cached": rep["all_cached"],
                     "watched": [os.path.relpath(p, ROOT) for p in watched if os.path.exists(p)]}
    results["idempotent_prepare"] = out


def wait_for(cond, seconds):
    t = time.time()
    while time.time() - t < seconds:
        if cond():
            return True
        time.sleep(0.05)
    return False


def test_cancel_fail_default(blender, tmp):
    # a copy of a shot in a temporary episodes folder (published cast only: prepare needs one package export)
    src = os.path.join(ROOT, "episodes", "e900_workflow_test", "shots", "s010", "shot.scene.json")
    sdir = os.path.join(tmp, "episodes", "etest", "shots", "s001")
    os.makedirs(sdir)
    shot = os.path.join(sdir, "shot.scene.json")
    shutil.copy(src, shot)
    build = os.path.join(sdir, "build")
    fake = os.path.join(tmp, "fake_blender.py")
    open(fake, "w").write(FAKE_BLENDER)
    os.chmod(fake, 0o755)
    open(os.path.join(tmp, "good.png"), "wb").write(png())
    env = dict(os.environ, FAKE_PNG=os.path.join(tmp, "good.png"))
    r = run_shot(["--shot", shot, "--blender", blender, "--stages", "prepare,bake", "--run-dir", "ok1", "--frames", "11-13"])
    check("prepare+bake run on the temporary shot", r.returncode == 0, r.stderr[-800:])
    status = lambda rid: json.load(open(os.path.join(build, "runs", rid, "status.json")))
    latest = lambda: open(os.path.join(build, "runs", "latest")).read().strip()
    earlier = snapshot([os.path.join(build, "runs", "ok1")])
    # --- graceful cancel with a partly written frame
    p = subprocess.Popen([sys.executable, RUN_SHOT, "--shot", shot, "--blender", fake, "--stages", "bake,render",
                          "--run-dir", "cancel1", "--frames", "11-14"], env=dict(env, FAKE_MODE="partial_then_hang"),
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    rdir = os.path.join(build, "runs", "cancel1", "render")
    partial = os.path.join(rdir, "frame_0012.png")
    check("fake render wrote a partial frame", wait_for(lambda: os.path.exists(partial), 30))
    check("status shows the render stage and 1 finished frame", wait_for(lambda: status("cancel1")["frames_done"] == 1, 5),
          {k: status("cancel1")[k] for k in ("stage", "frames_done", "frames_total")})
    members_before = subprocess.run(["ps", "-o", "pid,pgid,args", "-g", str(p.pid)], capture_output=True, text=True).stdout
    os.killpg(p.pid, signal.SIGTERM)
    p.wait(30)
    gone = wait_for(lambda: subprocess.run(["ps", "-o", "pid=", "-g", str(p.pid)], capture_output=True, text=True).stdout.strip() == "", 10)
    st = status("cancel1")
    check("cancel: state cancelled", st["state"] == "cancelled", st.get("error"))
    check("cancel: partial frame removed", not os.path.exists(partial), st.get("removed_partial_frames"))
    check("cancel: complete frame kept", os.path.exists(os.path.join(rdir, "frame_0011.png")))
    check("cancel: no process of the job's group left", gone)
    check("cancel: latest untouched", latest() == "ok1")
    check("cancel: earlier run untouched", snapshot([os.path.join(build, "runs", "ok1")]) == earlier)
    results["cancel_graceful"] = {"status": st, "group_before": members_before, "exit_code": p.returncode}
    # --- forced kill, finalised by --mark-cancelled (what Studio does after SIGKILL)
    p = subprocess.Popen([sys.executable, RUN_SHOT, "--shot", shot, "--blender", fake, "--stages", "bake,render",
                          "--run-dir", "kill1", "--frames", "11-14"], env=dict(env, FAKE_MODE="partial_then_hang"),
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    partial = os.path.join(build, "runs", "kill1", "render", "frame_0012.png")
    wait_for(lambda: os.path.exists(partial), 30)
    os.killpg(p.pid, signal.SIGKILL)
    p.wait(30)
    check("killed run is left 'running' before finalising", status("kill1")["state"] == "running")
    r = run_shot(["--shot", shot, "--run-dir", "kill1", "--mark-cancelled"])
    st = status("kill1")
    check("--mark-cancelled: state cancelled, partial frame removed", r.returncode == 0 and st["state"] == "cancelled" and not os.path.exists(partial),
          st.get("removed_partial_frames"))
    check("forced kill: latest untouched", latest() == "ok1")
    results["cancel_forced"] = {"status": st}
    # --- failure
    r = subprocess.run([sys.executable, RUN_SHOT, "--shot", shot, "--blender", fake, "--stages", "bake,render", "--run-dir", "fail1",
                        "--frames", "11-12"], env=dict(env, FAKE_MODE="fail"), capture_output=True, text=True)
    st = status("fail1")
    check("failure: exit code != 0, state failed with the error text", r.returncode != 0 and st["state"] == "failed"
          and "simulated render failure" in st["error"], st["error"][-200:])
    check("failure: latest untouched", latest() == "ok1")
    results["failure"] = {"status": st}
    # --- runs are never overwritten
    r = run_shot(["--shot", shot, "--blender", fake, "--stages", "bake", "--run-dir", "ok1"])
    check("an existing run folder is refused", r.returncode != 0 and "never overwritten" in r.stderr)
    # --- command-line default behaviour: outputs where M3.2 put them, M3.2 run_shot.json keys, runs/ untouched
    runs_before = snapshot([os.path.join(build, "runs")])
    r = subprocess.run([sys.executable, RUN_SHOT, "--shot", shot, "--blender", fake, "--frames", "11-12"], env=dict(env, FAKE_MODE="ok"),
                       capture_output=True, text=True)
    check("default run ok", r.returncode == 0, r.stderr[-500:])
    rep = json.load(open(os.path.join(build, "run_shot.json")))
    check("default: run_shot.json has the M3.2 keys", sorted(rep) == ["cast", "render", "shot", "steps"], sorted(rep))
    check("default: M3.2 output locations", all(os.path.exists(os.path.join(build, f)) for f in
          ("bake.json", "cast.json", "shot.resolved.scene.json", "render/frame_0011.png", "render/frame_0012.png", "render/shot_render.json")))
    check("default: no mp4 without --video", not os.path.exists(os.path.join(build, "shot.mp4")))
    check("default: runs/ untouched", snapshot([os.path.join(build, "runs")]) == runs_before)
    check("default: steps as in M3.2", sorted(rep["steps"]) == ["blender_s", "engine_bake_s"], sorted(rep["steps"]))
    results["default_cli"] = {"run_shot_json_keys": sorted(rep), "steps": sorted(rep["steps"])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blender", required=True)
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    shots = sorted(os.path.join(d, "shot.scene.json") for d in
                   (os.path.join(ROOT, "episodes", e, "shots", s) for e in sorted(os.listdir(os.path.join(ROOT, "episodes")))
                    for s in sorted(os.listdir(os.path.join(ROOT, "episodes", e, "shots"))))
                   if os.path.exists(os.path.join(d, "shot.scene.json")))
    test_idempotent_prepare(a.blender, shots)
    tmp = tempfile.mkdtemp(prefix="plush_t001_")
    try:
        test_cancel_fail_default(a.blender, tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    results["failures"] = failures
    if a.out:
        os.makedirs(a.out, exist_ok=True)
        json.dump(results, open(os.path.join(a.out, "run_shot_workflow_tests.json"), "w"), indent=1)
    n = sum(1 for _ in failures)
    print(f"[test_run_shot_workflow] {'ALL PASS' if not n else f'{n} FAILED'}")
    return 1 if n else 0


if __name__ == "__main__":
    sys.exit(main())
