"""Runs one shot end to end: character sources -> engine packages -> C++ engine animation (bake) -> Blender render.

    python3 pipeline/production/run_shot.py --shot episodes/<ep>/shots/<shot>/shot.scene.json --blender <blender>
        [--frames A-B] [--resolution W H] [--samples N] [--blend-only] [--video]

The shot file is an engine scene (plush.scene) plus a "production" block, the only place a shot names its cast's
sources (no character-specific code anywhere in the path):

  "production": {"cast": {"<scene character name>": {"version_dir": "<published store version>"}            or
                                                     {"spec": "<spec.json>", "overrides": [...]}           (unpublished:
                                                      built into the shot's build folder, never published)},
                 "profile": "pipeline/charsys/rig_profiles/humanoid_rigify.json",
                 "render": {"resolution": [w, h], "samples": n, "light_scale": x}}

Each character's "asset" in the scene is ignored and replaced by the package built here. Outputs go to
<shot dir>/build/ (masters for unpublished casts, packages, bake.json, frames, shot.blend, shot.mp4, run_shot.json).
Steps are cached by content hashes (a master or package is rebuilt only when its inputs change)."""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CHARSYS = os.path.join(ROOT, "pipeline", "charsys")


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shot", required=True)
    ap.add_argument("--blender", required=True)
    ap.add_argument("--engine", default=os.path.join(ROOT, "build", "apps", "render-cli", "plush-render"))
    ap.add_argument("--frames", default="")
    ap.add_argument("--resolution", type=int, nargs=2)
    ap.add_argument("--samples", type=int)
    ap.add_argument("--blend-only", action="store_true")
    ap.add_argument("--video", action="store_true")
    a = ap.parse_args()
    shot_path = os.path.abspath(a.shot)
    shot_dir = os.path.dirname(shot_path)
    out = os.path.join(shot_dir, "build")
    os.makedirs(os.path.join(out, "logs"), exist_ok=True)
    shot = json.load(open(shot_path))
    prod = shot.get("production") or {}
    profile = resolve(ROOT, prod.get("profile", "pipeline/charsys/rig_profiles/humanoid_rigify.json"))
    rep = {"shot": os.path.relpath(shot_path, ROOT), "steps": {}, "cast": {}}
    cast_for_blender = {}
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
        else:
            spec = resolve(ROOT, src["spec"])
            ovs = [resolve(ROOT, o) for o in src.get("overrides", [])]
            key = hashlib.sha256(b"".join(open(p, "rb").read() for p in [spec] + ovs)).hexdigest()[:16]
            bdir = os.path.join(out, "masters", f"{name}_{key}")
            cid = json.load(open(spec))["identity"]["id"]
            master = os.path.join(bdir, f"{cid}_master.blend")
            if not os.path.exists(master):
                cmd = [a.blender, "-b", "--factory-startup", "-P", os.path.join(CHARSYS, "build_character.py"), "--",
                       "--spec", spec, "--out", bdir, "--no-glb"] + sum((["--override", o] for o in ovs), [])
                rep["steps"][f"build_{name}_s"] = run(cmd, os.path.join(out, "logs", f"build_{name}.log"))
            status = "unpublished build from spec (experimental; not approved)"
        msha = sha256(master)
        # 2. engine package from the master (cached by the master's hash)
        pkg = os.path.join(out, "packages", f"{name}_{msha[:16]}")
        if not os.path.exists(os.path.join(pkg, "character.json")):
            cmd = [a.blender, "-b", "--factory-startup", "-P", os.path.join(CHARSYS, "export_engine.py"), "--",
                   "--blend", master, "--profile", profile, "--out", pkg]
            rep["steps"][f"export_{name}_s"] = run(cmd, os.path.join(out, "logs", f"export_{name}.log"))
        ch["asset"] = os.path.relpath(os.path.join(pkg, "character.json"), out)
        cast_for_blender[name] = {"master": master, "character_id": cid, "package": pkg}
        rep["cast"][name] = {"character_id": cid, "status": status, "master_sha256": msha, "package": os.path.relpath(pkg, ROOT)}
    # 3. engine animation -> bake (the scene with resolved packages lives in the build folder)
    resolved = os.path.join(out, "shot.resolved.scene.json")
    json.dump({k: v for k, v in shot.items() if k != "production"}, open(resolved, "w"), indent=1)
    bake = os.path.join(out, "bake.json")
    cmd = [a.engine, resolved, "--bake", bake] + (["--frames", a.frames] if a.frames else [])
    rep["steps"]["engine_bake_s"] = run(cmd, os.path.join(out, "logs", "bake.log"))
    json.dump(cast_for_blender, open(os.path.join(out, "cast.json"), "w"), indent=1)
    # 4. Blender render of the baked animation
    r = prod.get("render", {})
    res = a.resolution or r.get("resolution")
    cmd = [a.blender, "-b", "--factory-startup", "-P", os.path.join(CHARSYS, "shot_render.py"), "--", "--bake", bake,
           "--cast", os.path.join(out, "cast.json"), "--out", os.path.join(out, "render"),
           "--samples", str(a.samples or r.get("samples", 32)), "--light-scale", str(r.get("light_scale", 1.0))]
    cmd += (["--resolution", str(res[0]), str(res[1])] if res else []) + (["--frames", a.frames] if a.frames else [])
    cmd += ["--blend-only"] if a.blend_only else []
    rep["steps"]["blender_s"] = run(cmd, os.path.join(out, "logs", "render.log"))
    rep["render"] = json.load(open(os.path.join(out, "render", "shot_render.json")))
    # 5. video
    if a.video and not a.blend_only:
        num, den = shot.get("frameRate", [30, 1])
        start = rep["render"]["frames"][0]
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", f"{num}/{den}", "-start_number", str(start), "-i",
               os.path.join(out, "render", "frame_%04d.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
               os.path.join(out, "shot.mp4")]
        rep["steps"]["video_s"] = run(cmd, os.path.join(out, "logs", "video.log"))
    json.dump(rep, open(os.path.join(out, "run_shot.json"), "w"), indent=1)
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    sys.exit(main())
