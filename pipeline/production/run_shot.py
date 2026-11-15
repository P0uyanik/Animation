"""Runs one shot end to end: character sources -> engine packages -> C++ engine animation (bake) -> Blender render.

    python3 pipeline/production/run_shot.py --shot episodes/<ep>/shots/<shot>/shot.scene.json --blender <blender>
        [--frames A-B] [--resolution W H] [--samples N] [--blend-only] [--video]
        [--stages prepare,bake,render,encode] [--run-dir <run-id or path>]

The shot file is an engine scene (plush.scene) plus a "production" block, the only place a shot names its cast's
sources (no character-specific code anywhere in the path):

  "production": {"cast": {"<scene character name>": {"version_dir": "<published store version>"}            or
                                                     {"spec": "<spec.json>", "overrides": [...]}           (unpublished:
                                                      built into the shot's build folder, never published)},
                 "profile": "pipeline/charsys/rig_profiles/humanoid_rigify.json",
                 "render": {"resolution": [w, h], "samples": n, "light_scale": x}}

Each character's "asset" in the scene is ignored and replaced by the package built here. Outputs go to
<shot dir>/build/ (masters for unpublished casts, packages, bake.json, frames, shot.blend, shot.mp4, run_shot.json).
Steps are cached by content hashes (a master or package is rebuilt only when its inputs change; a package also when
the exporter's EXPORTER_VERSION changes).

Workflow contract (used by the command line and by Plush Studio; see docs/PRODUCTION_PIPELINE.md):
- Stages: prepare (resolve the cast: masters, packages, <build>/shot.resolved.scene.json, <build>/cast.json,
  prepare.json), bake (engine), render (Blender), encode (mp4). --stages selects them (default: all; without
  --stages the encode stage runs only with --video, exactly as before). Prepare is idempotent: nothing in the cache,
  in assets/ or in published versions is written when its inputs are unchanged.
- --run-dir: a per-run output folder. A bare id means <shot dir>/build/runs/<id>/. The run's bake, frames, shot.blend,
  shot.mp4, run_shot.json, prepare.json, logs and status.json live there; the shared cache (masters, packages,
  resolved scene, cast.json) stays in <shot dir>/build/. <runs dir>/latest (a text file with the run id) is replaced
  only after the run succeeds. Without --run-dir everything goes exactly where it went before.
- status.json (plush.run_status/1) is rewritten atomically per stage and per finished frame.
- Cancel: SIGTERM (or SIGINT) stops the current step, removes a partly written frame, marks the run cancelled and
  leaves earlier runs and latest untouched. --mark-cancelled finalises a run whose process was killed forcibly."""
import argparse
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CHARSYS = os.path.join(ROOT, "pipeline", "charsys")
STAGES = ["prepare", "bake", "render", "encode"]


def exporter_script():
    """The engine-package exporter (PLUSH_EXPORT_ENGINE overrides it, e.g. for tests)."""
    return os.environ.get("PLUSH_EXPORT_ENGINE") or os.path.join(CHARSYS, "export_engine.py")


def exporter_version(path):
    """EXPORTER_VERSION of an exporter script (read from its source; "1" for exporters that predate it)."""
    m = re.search(r'^EXPORTER_VERSION\s*=\s*["\']([^"\']+)["\']', open(path).read(), re.M)
    return m.group(1) if m else "1"


def package_key(master_sha, exporter_ver):
    """Package cache key: the master's content hash and the exporter version (a new exporter re-exports)."""
    return hashlib.sha256(f"{master_sha}:exporter {exporter_ver}".encode()).hexdigest()[:16]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run(cmd, log):
    t = time.time()
    p = subprocess.run(cmd, capture_output=True, text=True)
    open(log, "w").write(p.stdout + p.stderr)
    if p.returncode != 0:
        raise SystemExit(f"step failed ({p.returncode}): {' '.join(cmd[:4])} ... see {log}\n{(p.stdout + p.stderr)[-1500:]}")
    return round(time.time() - t, 1)


def resolve(base, p):
    return p if os.path.isabs(p) else os.path.normpath(os.path.join(base, p))


# ------------------------------------------------------------------ workflow helpers (run-dir mode and status)
class Cancelled(Exception):
    pass


def _on_signal(signum, frame):
    raise Cancelled(signal.Signals(signum).name)


def write_atomic(path, text):
    tmp = f"{path}.tmp{os.getpid()}"
    with open(tmp, "w") as f:
        f.write(text)
    os.replace(tmp, path)


def write_if_changed(path, text):
    """Writes only when the content differs, so an unchanged file keeps its hash and modification time."""
    if os.path.exists(path) and open(path).read() == text:
        return False
    write_atomic(path, text)
    return True


def png_complete(path):
    """A PNG is complete when it ends with the IEND chunk (a frame cut off by a cancel does not)."""
    try:
        with open(path, "rb") as f:
            if f.read(8) != b"\x89PNG\r\n\x1a\n":
                return False
            f.seek(0, 2)
            if f.tell() < 20:
                return False
            f.seek(-12, 2)
            return f.read(12)[4:8] == b"IEND"
    except OSError:
        return False


def frames_in(render_dir, fa, fb):
    return [f for f in range(fa, fb + 1) if png_complete(os.path.join(render_dir, f"frame_{f:04d}.png"))]


def remove_partial_frames(render_dir):
    removed = []
    if os.path.isdir(render_dir):
        for n in sorted(os.listdir(render_dir)):
            p = os.path.join(render_dir, n)
            if n.startswith("frame_") and n.endswith(".png") and not png_complete(p):
                os.remove(p)
                removed.append(n)
    return removed


class Status:
    """status.json (plush.run_status/1) of one run; rewritten atomically on every change."""

    def __init__(self, path, data):
        self.path, self.data = path, data
        self.write()

    def set(self, **kw):
        self.data.update(kw)
        self.write()

    def write(self):
        self.data["updated"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        write_atomic(self.path, json.dumps(self.data, indent=1))


def run_streamed(cmd, log, poll=None):
    """Like run(), but the log is written while the step runs (Studio shows its tail) and `poll` is called twice a
    second (frame progress). On cancel the step is stopped: SIGTERM, then SIGKILL after 10 s."""
    t = time.time()
    with open(log, "w") as lf:
        p = subprocess.Popen(cmd, stdout=lf, stderr=subprocess.STDOUT, text=True)
        try:
            while p.poll() is None:
                if poll:
                    poll()
                time.sleep(0.5)
        except BaseException:
            if p.poll() is None:
                p.terminate()
                try:
                    p.wait(10)
                except subprocess.TimeoutExpired:
                    p.kill()
                    p.wait()
            raise
    if poll:
        poll()
    if p.returncode != 0:
        text = open(log).read()
        raise SystemExit(f"step failed ({p.returncode}): {' '.join(cmd[:4])} ... see {log}\n{text[-1500:]}")
    return round(time.time() - t, 1)


def mark_cancelled(run_out, reason):
    sp = os.path.join(run_out, "status.json")
    st = json.load(open(sp)) if os.path.exists(sp) else {"format": "plush.run_status", "version": 1}
    removed = remove_partial_frames(os.path.join(run_out, "render"))
    if st.get("state") in ("done", "failed", "cancelled"):
        return st
    fa, fb = st.get("frames", [0, -1])
    st.update(state="cancelled", error=reason, removed_partial_frames=removed,
              frames_done=len(frames_in(os.path.join(run_out, "render"), fa, fb)))
    Status(sp, st)
    return st


# ------------------------------------------------------------------ stages
def prepare(shot, shot_path, out, logs, blender, rep):
    """Resolves the cast: masters (published, or built from a spec), engine packages, the resolved scene and
    cast.json in the shared build folder. Cached by content hashes; unchanged inputs write nothing."""
    prod = shot.get("production") or {}
    profile = resolve(ROOT, prod.get("profile", "pipeline/charsys/rig_profiles/humanoid_rigify.json"))
    cast_for_blender, report = {}, {}
    for ch in shot["characters"]:
        name = ch["name"]
        src = prod.get("cast", {}).get(name)
        if src is None:
            raise SystemExit(f"production.cast has no source for character {name}")
        # 1. master: a published version (manifest-checked by the Blender side) or an unpublished build from a spec
        if "version_dir" in src:
            vdir = resolve(ROOT, src["version_dir"])
            man = json.load(open(os.path.join(vdir, "manifest.json")))
            cid = man["character_id"]
            master = os.path.join(vdir, f"{cid}_master.blend")
            if sha256(master) != man["files"][f"{cid}_master.blend"]["sha256"]:
                raise SystemExit(f"{name}: master does not match its manifest")
            status = f"published {man['version']}"
            master_state = "published (read only)"
        else:
            spec = resolve(ROOT, src["spec"])
            ovs = [resolve(ROOT, o) for o in src.get("overrides", [])]
            key = hashlib.sha256(b"".join(open(p, "rb").read() for p in [spec] + ovs)).hexdigest()[:16]
            bdir = os.path.join(out, "masters", f"{name}_{key}")
            cid = json.load(open(spec))["identity"]["id"]
            master = os.path.join(bdir, f"{cid}_master.blend")
            master_state = "cached"
            if not os.path.exists(master):
                cmd = [blender, "-b", "--factory-startup", "-P", os.path.join(CHARSYS, "build_character.py"), "--",
                       "--spec", spec, "--out", bdir, "--no-glb"] + sum((["--override", o] for o in ovs), [])
                rep["steps"][f"build_{name}_s"] = run(cmd, os.path.join(logs, f"build_{name}.log"))
                master_state = "built"
            status = "unpublished build from spec (experimental; not approved)"
        msha = sha256(master)
        # 2. engine package from the master (cached by the master's hash and the exporter version)
        exporter = exporter_script()
        pkg = os.path.join(out, "packages", f"{name}_{package_key(msha, exporter_version(exporter))}")
        package_state = "cached"
        if not os.path.exists(os.path.join(pkg, "character.json")):
            cmd = [blender, "-b", "--factory-startup", "-P", exporter, "--",
                   "--blend", master, "--profile", profile, "--out", pkg]
            rep["steps"][f"export_{name}_s"] = run(cmd, os.path.join(logs, f"export_{name}.log"))
            package_state = "built"
        ch["asset"] = os.path.relpath(os.path.join(pkg, "character.json"), out)
        cast_for_blender[name] = {"master": master, "character_id": cid, "package": pkg}
        rep["cast"][name] = {"character_id": cid, "status": status, "master_sha256": msha, "package": os.path.relpath(pkg, ROOT)}
        report[name] = {"character_id": cid, "source": status, "master": os.path.relpath(master, ROOT),
                        "master_state": master_state, "package": os.path.relpath(pkg, ROOT), "package_state": package_state,
                        "from_cache": master_state != "built" and package_state != "built"}
    # the scene with resolved packages lives in the build folder (rewritten only when its content changes)
    resolved = os.path.join(out, "shot.resolved.scene.json")
    scene_written = write_if_changed(resolved, json.dumps({k: v for k, v in shot.items() if k != "production"}, indent=1))
    cast_written = write_if_changed(os.path.join(out, "cast.json"), json.dumps(cast_for_blender, indent=1))
    prep = {"format": "plush.prepare", "version": 1, "shot": os.path.relpath(shot_path, ROOT),
            "resolved_scene": os.path.relpath(resolved, ROOT), "resolved_scene_written": scene_written,
            "cast_json_written": cast_written, "cast": report,
            "all_cached": all(r["from_cache"] for r in report.values()) and not scene_written and not cast_written}
    return resolved, prep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shot", required=True)
    ap.add_argument("--blender")
    ap.add_argument("--engine", default=os.path.join(ROOT, "build", "apps", "render-cli", "plush-render"))
    ap.add_argument("--frames", default="")
    ap.add_argument("--resolution", type=int, nargs=2)
    ap.add_argument("--samples", type=int)
    ap.add_argument("--blend-only", action="store_true")
    ap.add_argument("--video", action="store_true")
    ap.add_argument("--stages", default="", help="comma-separated subset of prepare,bake,render,encode (default: all)")
    ap.add_argument("--run-dir", default="", help="per-run output folder (a bare id: <shot dir>/build/runs/<id>)")
    ap.add_argument("--mark-cancelled", action="store_true", help="finalise a run whose process was killed (needs --run-dir)")
    a = ap.parse_args()
    if not a.blender and not a.mark_cancelled:
        ap.error("the following arguments are required: --blender")
    shot_path = os.path.abspath(a.shot)
    shot_dir = os.path.dirname(shot_path)
    out = os.path.join(shot_dir, "build")
    if a.run_dir:
        bare = os.sep not in a.run_dir and "/" not in a.run_dir and not a.run_dir.startswith(".")
        run_out = os.path.join(out, "runs", a.run_dir) if bare else os.path.abspath(a.run_dir)
    else:
        run_out = out
    if a.mark_cancelled:
        if not a.run_dir:
            ap.error("--mark-cancelled needs --run-dir")
        print(json.dumps(mark_cancelled(run_out, "killed"), indent=1))
        return 0
    stages = [s.strip() for s in a.stages.split(",") if s.strip()] if a.stages else list(STAGES)
    for s in stages:
        if s not in STAGES:
            ap.error(f"unknown stage {s} (stages: {','.join(STAGES)})")
    stages = [s for s in STAGES if s in stages]
    encode = "encode" in stages and (a.video or bool(a.stages)) and not a.blend_only
    if a.run_dir and os.path.exists(os.path.join(run_out, "status.json")):
        raise SystemExit(f"run folder {run_out} already holds a run (runs are never overwritten)")
    logs = os.path.join(run_out, "logs")
    os.makedirs(logs, exist_ok=True)
    shot = json.load(open(shot_path))
    prod = shot.get("production") or {}
    r = prod.get("render", {})
    res = a.resolution or r.get("resolution")
    if a.frames:
        x, _, y = a.frames.partition("-")
        fa, fb = int(x), int(y or x)
    else:
        fa, fb = shot.get("frameStart", 1), shot.get("frameEnd", 48)
    eff_res = list(res) if res else [shot.get("render", {}).get("width", 1280), shot.get("render", {}).get("height", 720)]
    status = Status(os.path.join(run_out, "status.json"), {
        "format": "plush.run_status", "version": 1, "run_id": os.path.basename(run_out) if a.run_dir else "",
        "shot": os.path.relpath(shot_path, ROOT), "run_dir": run_out, "pid": os.getpid(), "state": "running",
        "stage": stages[0] if stages else "", "stages": stages, "stages_done": [], "frames": [fa, fb],
        "frames_done": 0, "frames_total": fb - fa + 1, "resolution": eff_res, "samples": a.samples or r.get("samples", 32),
        "light_scale": r.get("light_scale", 1.0), "exposure_ev": shot.get("render", {}).get("exposureEV", 0.0),
        "blend_only": a.blend_only, "error": "", "started": time.strftime("%Y-%m-%dT%H:%M:%S")})
    old = {s: signal.signal(s, _on_signal) for s in (signal.SIGTERM, signal.SIGINT)}
    try:
        rep = stages_run(a, shot, shot_path, out, run_out, logs, stages, encode, status, fa, fb, res, r)
    except Cancelled as e:
        for s, h in old.items():
            signal.signal(s, signal.SIG_IGN)
        mark_cancelled(run_out, f"cancelled ({e})")
        print(f"[run_shot] cancelled: {run_out}", file=sys.stderr)
        return 143
    except SystemExit as e:
        removed = remove_partial_frames(os.path.join(run_out, "render"))
        status.set(state="failed", error=str(e.code), removed_partial_frames=removed)
        raise
    except Exception as e:
        status.set(state="failed", error=f"{type(e).__name__}: {e}")
        raise
    for s, h in old.items():
        signal.signal(s, h)
    status.set(state="done", stage="", error="")
    if a.run_dir:  # only a successful run replaces latest
        write_atomic(os.path.join(os.path.dirname(run_out), "latest"), os.path.basename(run_out) + "\n")
    print(json.dumps(rep, indent=1))
    return 0


def stages_run(a, shot, shot_path, out, run_out, logs, stages, encode, status, fa, fb, res, r):
    streamed = bool(a.run_dir)
    step = (lambda cmd, log, poll=None: run_streamed(cmd, log, poll)) if streamed else (lambda cmd, log, poll=None: run(cmd, log))
    rep = {"shot": os.path.relpath(shot_path, ROOT), "steps": {}, "cast": {}}
    done = []

    def stage(name):
        status.set(stage=name, stages_done=list(done))

    resolved = os.path.join(out, "shot.resolved.scene.json")
    if "prepare" in stages:
        stage("prepare")
        if not a.blender:
            raise SystemExit("prepare needs --blender")
        resolved, prep = prepare(shot, shot_path, out, logs, a.blender, rep)
        if streamed:
            write_atomic(os.path.join(run_out, "prepare.json"), json.dumps(prep, indent=1))
        write_if_changed(os.path.join(out, "prepare.json"), json.dumps(prep, indent=1))
        if streamed:  # (the default run_shot.json keeps its M3.2 keys)
            rep["prepare"] = {"all_cached": prep["all_cached"], "cast": {n: {k: c[k] for k in ("master_state", "package_state")}
                                                                           for n, c in prep["cast"].items()}}
        done.append("prepare")
    elif not os.path.exists(resolved) or not os.path.exists(os.path.join(out, "cast.json")):
        raise SystemExit(f"shot is not prepared ({resolved} missing): run the prepare stage first")
    else:
        rep["cast"] = {n: {"character_id": c["character_id"], "package": os.path.relpath(c["package"], ROOT)}
                       for n, c in json.load(open(os.path.join(out, "cast.json"))).items()}
    # 3. engine animation -> bake
    bake = os.path.join(run_out, "bake.json")
    if "bake" in stages:
        stage("bake")
        cmd = [a.engine, resolved, "--bake", bake] + (["--frames", a.frames] if a.frames else [])
        rep["steps"]["engine_bake_s"] = step(cmd, os.path.join(logs, "bake.log"))
        done.append("bake")
    # 4. Blender render of the baked animation
    render_dir = os.path.join(run_out, "render")
    if "render" in stages:
        stage("render")
        if not os.path.exists(bake):
            raise SystemExit(f"no bake in {run_out}: run the bake stage first")
        cmd = [a.blender, "-b", "--factory-startup", "-P", os.path.join(CHARSYS, "shot_render.py"), "--", "--bake", bake,
               "--cast", os.path.join(out, "cast.json"), "--out", render_dir,
               "--samples", str(a.samples or r.get("samples", 32)), "--light-scale", str(r.get("light_scale", 1.0))]
        cmd += (["--resolution", str(res[0]), str(res[1])] if res else []) + (["--frames", a.frames] if a.frames else [])
        cmd += ["--blend-only"] if a.blend_only else []
        progress = {"n": -1}

        def poll():
            n = len(frames_in(render_dir, fa, fb))
            if n != progress["n"]:
                progress["n"] = n
                status.set(frames_done=n)

        rep["steps"]["blender_s"] = step(cmd, os.path.join(logs, "render.log"), poll)
        rep["render"] = json.load(open(os.path.join(render_dir, "shot_render.json")))
        status.set(frames_done=len(frames_in(render_dir, fa, fb)), render_report=rep["render"])
        done.append("render")
    # 5. video
    if encode:
        stage("encode")
        num, den = shot.get("frameRate", [30, 1])
        start = rep["render"]["frames"][0] if "render" in rep else fa
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", f"{num}/{den}", "-start_number", str(start), "-i",
               os.path.join(render_dir, "frame_%04d.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
               os.path.join(run_out, "shot.mp4")]
        rep["steps"]["video_s"] = step(cmd, os.path.join(logs, "video.log"))
        done.append("encode")
    status.set(stages_done=list(done))
    json.dump(rep, open(os.path.join(run_out, "run_shot.json"), "w"), indent=1)
    return rep


if __name__ == "__main__":
    sys.exit(main())
